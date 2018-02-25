"""
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
import local_news_parsers
import scraper_utils
from news_data import NewsRSSEntry


MAX_WORKERS = 10
HTML_PARSER_WORKER_TIMEOUT = 60


def _check_rss_url_is_valid(url):
    # 'feedparser' does not raise exceptions when RSS url returns 404 Error
    # So use urlopen() to force raising HTTPError and URLError
    with urlopen(url):
        pass


def _get_news_source_website_name_by_feed_title(title):

    title = title.lower()

    if 'google' in title:
        return 'google'
    elif 'yahoo' in title:
        return 'yahoo'
    else:
        return 'others'


def _generate_description_from_local_news_source_by_parser(
    news_title, news_source, local_news_link, html_parser
):

    try:
        description = html_parser.get_news_content(local_news_link).strip()
    except HTTPError as e:
        scraper_utils.log_warning("HTTP Error %d for local news '%s'" % (e.code, local_news_link))
        return None
    except URLError as e:
        scraper_utils.log_warning("URL Error [%s] for local news '%s'" % (e.reason, local_news_link))
        return None

    return "(Extracted from '%s')\n%s" % (news_source, description)


class MyFeed(object):
    def __init__(self, title, subtitle, link, language, published_time, entries):
        self.title = title
        self.subtitle = subtitle
        self.link = link
        self.language = language
        self.published_time = published_time
        self.entries = entries  # A tuple of NewsRSSEntry

    def __repr__(self):
        return (
            "======== <MyFeed object at {}> ========\n"
            "[Title]       : {}\n"
            "[Subtitle]    : {}\n"
            "[Link]        : {}\n"
            "[Language]    : {}\n"
            "[Published]   : {}\n"
            "[# of Entries]: {}\n"
            "===============================================\n"
            .format(
                hex(id(self)),
                self.title,
                self.subtitle,
                self.link,
                self.language,
                self.published_time,
                len(self.entries),
            )
        )


def _pickle_feed_object_to_file_for_unit_tests(url, feed):
    # Used to generate input data for mock in unit test
    import time.strftime
    import pickle

    filename = url.replace(':', '.').replace('/', '_').replace('?', '-')
    filename = filename.replace('&', '-').replace('=', '_').replace('%', '_')

    logging.info("Creating [%s] which contains pickle object of RSS feed.")
    with open(filename + time.strftime('-%m%d') + '.txt', 'wb') as f:
        pickle.dump(feed, f)


class RSSFeedParser(object):

    _description_depends_on_local_news_sources = False

    @classmethod
    def parse_feed(cls, url, category=None):

        _check_rss_url_is_valid(url)

        feed = feedparser.parse(url)

        # _pickle_feed_object_to_file_for_unit_tests(url, feed)

        title = cls._get_title(feed.feed)
        subtitle = cls._get_subtitle(feed.feed)
        language = cls._get_language(feed.feed)
        published_time = cls._get_time(feed.feed)
        # feed_link may have stupid errors, such as:
        # https://news.google.coms/rss/headlines/section/topic/NATION.zh-TW_tw/%E5%8F%B0%E7%81%A3?ned=tw&hl=zh-tw&gl=TW
        # So... do not use it.......
        # feed_link = cls._get_link(feed.feed)

        entries = tuple(
            cls._get_entries_from_feed(feed.entries, url, category)
        )

        return MyFeed(title, subtitle, url, language, published_time, entries)

    @classmethod
    def _get_entries_from_feed(cls, entries, feed_link, category):
        """
        Note that _get_description(entry) may take time for some news sources
        such as Google News because it has to acquire the news content from
        one of the local news sources.

        Therefore, retrieve entries in parallel.
        """
        start_time = timer()
        with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_url_map = {}

            for entry in entries:
                title = cls._get_title(entry)
                link = cls._get_link(entry)
                published_time = cls._get_time(entry)
                news_source = _get_news_source_website_name_by_feed_title(feed_link)

                tmp_news_entry = NewsRSSEntry(
                    title, "", link, published_time, news_source, category
                )

                # For description
                future_obj = executor.submit(cls._get_description, entry)
                future_url_map[future_obj] = tmp_news_entry

            if future_url_map:
                logging.info(
                    "Processing %d news entries for RSS [%s] '%s' concurrently..."
                    % (len(entries), category, feed_link)
                )

                done_iter = futures.as_completed(
                    future_url_map,
                    timeout=HTML_PARSER_WORKER_TIMEOUT
                )
                try:
                    for future_obj in done_iter:
                        description = future_obj.result()

                        news_rss_entry = future_url_map[future_obj]
                        news_rss_entry.description = description

                        yield news_rss_entry

                except futures.TimeoutError as e:
                    news_rss_entry = future_url_map[future_obj]
                    scraper_utils.log_warning(
                        "Timeout in _get_entries_from_feed() when processing the news entry:\n"
                        "%s"
                        "\tRSS [%s] '%s'\n"
                        "\tError Message: %s\n"
                        % (repr(news_rss_entry), category, feed_link, str(e))
                    )

                logging.info(
                    "Done in %f seconds: %d news entries for RSS [%s] '%s'"
                    % (timer() - start_time, len(entries), category, feed_link)
                )

    @classmethod
    def _get_entries_from_feed_sequentially(cls, entries, feed_link, category):
        logging.info(
            "<Sequentially> Processing %d news entries for RSS [%s] '%s' concurrently..."
            % (len(entries), category, feed_link)
        )
        start_time = timer()

        for entry in entries:
            title = cls._get_title(entry)
            link = cls._get_link(entry)
            published_time = cls._get_time(entry)
            news_source = _get_news_source_website_name_by_feed_title(feed_link)
            description = cls._get_description(entry)

            yield NewsRSSEntry(title, description, link, published_time, news_source, category)

        logging.info(
            "<Sequentially> Done in %f seconds: %d news entries for RSS [%s] '%s'"
            % (timer() - start_time, len(entries), category, feed_link)
        )

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
            #     https://stackoverflow.com/questions/20867795/python-how-to-get-timezone-from-rss-feed
            published_time = date_parser.parse(feed.published)

        except AttributeError:
            # feed.published is not provided
            published_time = datetime.utcnow()

        return published_time


class YahooFeedParser(RSSFeedParser):
    pass


class GoogleFeedParser(RSSFeedParser):

    @staticmethod
    def _get_description(feed):

        # feed.description is a list of same news from different local sources
        # Get the real news content from one of the local sources

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
            parsers_registry = local_news_parsers.parsers_registry

            for local_source in parsers_registry:
                # Decide which parser should be used to parse the news content.
                # Note that domain_name is generally longer than local_source.
                if local_source in news_domain_name:
                    # A proper parser (html_parser) is found.
                    html_parser = parsers_registry[local_source]()

                    result = _generate_description_from_local_news_source_by_parser(
                        news_title, news_source, news_link, html_parser
                    )
                    if result:
                        return result
                    else:
                        continue

                else:
                    # No proper parser is found.
                    # Add this news_source to candidates
                    candidates.append([news_title, news_source, news_link])

        # No proper parser is found for any of local news sources
        # So use the default parser to parse the first local news source

        for news_title, news_source, news_link in candidates:
            html_parser = local_news_parsers.DefaultHtmlNewsParser()

            result = _generate_description_from_local_news_source_by_parser(
                news_title, news_source, news_link, html_parser
            )
            if result:
                return result
            else:
                continue

        # All candidates fail
        # This is very unlikely to happen
        msg = "No candidate local news source works for GoogleNews '%s'.\n" % feed.title
        msg += "\tThe raw description is: {}" % feed.description
        scraper_utils.log_warning(msg)

        return feed.description
