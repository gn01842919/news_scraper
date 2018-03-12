"""This module defines parsers to parse RSS feeds.
"""
# Standard library
import logging
from concurrent import futures
from datetime import datetime
from timeit import default_timer as timer
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
# PyPI
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
# Local modules
from settings import FEED_PARSER_CONFIG
from local_news_parsers import DefaultHtmlNewsParser, get_local_parser_registry
import scraper_utils
from scraper_models import NewsRSSEntry, RssFeed


def get_raw_feed_obj(url):
    """Checks that the url is valid, and retrieves the RSS feed by the url.

    Args:
        url (str): The RSS link to retrieve.

    Returns:
        dict: A dictionary representing the RSS feed.
            For more details, please refer to `feedparser documentation`_

    Raises:
        HTTPError: If the HTTP errors occurrs when retrieving the RSS feed.
        URLError: If the url is incorrect or has some problems.

    .. _feedparser documentation:
        https://pythonhosted.org/feedparser/introduction.html

    """

    # 'feedparser' does not raise exceptions when RSS url returns 404 Error
    # So use urlopen() to force raising HTTPError or URLError
    with urlopen(url):
        pass

    return feedparser.parse(url)


def _get_rss_source_name_by_title(title):
    """Get news RSS source name by feed title
    """

    title = title.lower()

    if 'google' in title:
        return 'google'
    elif 'yahoo' in title:
        return 'yahoo'
    else:
        return 'others'


def _get_content_from_local_source(
        news_source, local_news_link, html_parser):
    """Get news content from a local news link.
    """

    try:
        description = html_parser.get_news_content_from_url(local_news_link).strip()
    except HTTPError as err:
        scraper_utils.log_warning(
            "HTTP Error %d for local news '%s'" % (err.code, local_news_link)
        )
        return None
    except URLError as err:
        scraper_utils.log_warning(
            "URL Error [%s] for local news '%s'" % (err.reason, local_news_link)
        )
        return None

    return "(Extracted from '%s')\n%s" % (news_source, description)


def _pickle_feed_object_to_file(url, feed):
    """Use pickle to store a RSS feed into file.

    This is used to generate input data to mock HTTP resources for unit testw.
    """
    from time import strftime
    import pickle

    filename = url.replace(':', '.').replace('/', '_').replace('?', '-')
    filename = filename.replace('&', '-').replace('=', '_').replace('%', '_')

    logging.info("Creating [%s] which contains pickle object of RSS feed.")
    with open(filename + strftime('-%m%d') + '.txt', 'wb') as outfile:
        pickle.dump(feed, outfile)


class RSSFeedParser(object):
    """Base class for RSS feed parsers.

    Can be instanciated directly, while it is recommended to inherit from this class.

    """

    @classmethod
    def parse_feed(cls, feed, category=None):
        """Parse a raw RSS feed, and extract interested information.

        The extracted information includes all news entries inside the feed.

        Args:
            feed (dict): Raw RSS feed object.
                Typically this can be obtained by calling ``get_raw_feed_obj()``.

            category (str, optional): Category of the RSS source.
                This will be added to news entries inside the RSS feed as tags.

        Returns:
            RssFeed: A RssFeed containing interested information of the raw RSS feed.

        """

        # _pickle_feed_object_to_file(url, feed)

        title = cls._get_title(feed.feed)
        subtitle = cls._get_subtitle(feed.feed)
        language = cls._get_language(feed.feed)
        published_time = cls._get_time(feed.feed)
        feed_link = cls._get_link(feed.feed)

        entries = tuple(
            cls._get_entries_from_feed(feed.entries, feed_link, category)
        )

        return RssFeed(title, subtitle, feed_link, language, published_time, entries)

    @classmethod
    def _get_entries_from_feed(cls, entries, feed_link, category):
        """
        Note that _get_description(entry) may take time for some news sources
        such as Google News because it has to acquire the news content from
        one of the local news sources.

        Therefore, retrieve entries in parallel.
        """
        start_time = timer()
        news_source = _get_rss_source_name_by_title(feed_link)

        if not entries:
            return None

        with futures.ThreadPoolExecutor(
            max_workers=FEED_PARSER_CONFIG["max_workers"]
        ) as executor:

            future_url_map = {}

            for entry in entries:
                # For description
                future_obj = executor.submit(cls._get_description, entry)
                future_url_map[future_obj] = NewsRSSEntry(
                    cls._get_title(entry),
                    "",
                    cls._get_link(entry),
                    cls._get_time(entry),
                    news_source,
                    category
                )

            done_iter = futures.as_completed(
                future_url_map,
                timeout=FEED_PARSER_CONFIG["html_parser_worker_timeout"]
            )
            try:
                for future_obj in done_iter:
                    news_rss_entry = future_url_map[future_obj]
                    news_rss_entry.description = future_obj.result()

                    yield news_rss_entry

            except futures.TimeoutError as err:
                news_rss_entry = future_url_map[future_obj]
                scraper_utils.log_warning(
                    "Timeout in _get_entries_from_feed() when processing the news entry:\n"
                    "%s"
                    "\tRSS [%s] '%s'\n"
                    "\tError Message: %s\n"
                    % (repr(news_rss_entry), category, feed_link, str(err))
                )

            msg = (
                "RSS [%s %s] Completed in %f seconds: %d news entries."
                % (news_source, category, timer() - start_time, len(entries))
            )
            logging.debug(msg)

    @staticmethod
    def _get_title(feed):
        return feed.title

    @classmethod
    def _get_subtitle(cls, feed):
        try:
            return feed.subtitle.strip()
        except AttributeError:
            return cls._get_description(feed)

    @staticmethod
    def _get_description(feed):
        return feed.description.strip()

    @staticmethod
    def _get_link(feed):
        return feed.link

    @staticmethod
    def _get_language(feed):
        return feed.language

    @staticmethod
    def _get_time(feed):
        try:
            # Using datetime.datetime(*feed.feed.published_parsed[:-3]) can not
            # preserve original timezone information
            # So use dateutil.parser().parse(feed.feed.published) instead
            # Reference:
            # https://stackoverflow.com/questions/20867795/python-how-to-get-timezone-from-rss-feed
            published_time = date_parser.parse(feed.published)

        except AttributeError:
            # feed.published is not provided
            published_time = datetime.utcnow()

        return published_time


class YahooFeedParser(RSSFeedParser):
    """RSS feed parser for Yahoo RSS news sources.
    """
    pass


class GoogleFeedParser(RSSFeedParser):
    """RSS feed parser for Google RSS news sources.

    Note that the description of news entries of Google RSS sources does not
    contain the news content, but contains urls of local news sources.

    So ``self._get_description()`` is overridden to parse the local news
    sources to the the news content.

    """

    @staticmethod
    def _get_description(feed):
        """Get description (news content) of the news.

        For Google RSS news, feed.description is a list of same news
        from different local sources.

        This method gets the real news content from one of the local sources.

        """

        bsobj = BeautifulSoup(feed.description, "html.parser")
        local_news_sources_li = bsobj.findAll("li")
        # Example:
        #   <li>
        #     <a href="http://www.cna.com.tw/news/aopl/201802110062-1.aspx" target="_blank">
        #          以色列攻擊敘利亞境內伊朗目標美力挺
        #     </a>
        #     &nbsp;&nbsp;
        #     <font color="#6F6F6F">
        #         中央社即時新聞
        #     </font>
        #   </li>

        # If no proper parser is found for all local news sources,
        # one of the sources in candidates will be parsed by default_parser.
        candidates = []
        html_parser = None

        for local_src in local_news_sources_li:
            news_title = local_src.a.get_text()
            news_source = local_src.font.get_text()
            try:
                news_link = local_src.a["href"]
            except AttributeError:
                continue

            news_domain_name = scraper_utils.extract_domain_name_from_url(news_link)
            parsers_registry = get_local_parser_registry()

            for local_source in parsers_registry:
                # Decide which parser should be used to parse the news content.
                # Note that domain_name is generally longer than local_source.
                if local_source in news_domain_name:
                    # A proper parser (html_parser) is found.
                    html_parser = parsers_registry[local_source]()

                    news_content = _get_content_from_local_source(
                        news_source, news_link, html_parser
                    )
                    if news_content:
                        return news_content
                    else:
                        continue

                else:
                    # No proper parser is found.
                    # Add this news_source to candidates
                    candidates.append([news_title, news_source, news_link])

        # No proper parser is found for any of local news sources.
        # So use the default parser to parse the first local news source.

        for news_title, news_source, news_link in candidates:
            html_parser = DefaultHtmlNewsParser()

            news_content = _get_content_from_local_source(
                news_source, news_link, html_parser
            )
            if news_content:
                return news_content
            else:
                continue

        # All candidates fail
        # This is very unlikely to happen
        msg = "No candidate local news source works for GoogleNews '%s'.\n" % feed.title
        msg += "\tThe raw description is: %s" % feed.description
        scraper_utils.log_warning(msg)

        return feed.description
