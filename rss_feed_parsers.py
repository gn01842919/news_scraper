"""
"""

# Standard library
import logging
from datetime import datetime
from urllib.request import urlopen
# PyPI
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
# Local modules
import local_news_parsers
import scraper_utils
from news_data import NewsRSSEntry


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

    @classmethod
    def parse_feed(cls, url, category=None):

        _check_rss_url_is_valid(url)

        feed = feedparser.parse(url)

        # _pickle_feed_object_to_file_for_unit_tests(url, feed)

        title = cls._get_title(feed.feed)
        subtitle = cls._get_subtitle(feed.feed)
        feed_link = cls._get_link(feed.feed)
        language = cls._get_language(feed.feed)
        published_time = cls._get_time(feed.feed)

        entries = tuple(cls._get_entries_from_feed(feed.entries, feed_link, category))
        return MyFeed(title, subtitle, feed_link, language, published_time, entries)

    @classmethod
    def _get_entries_from_feed(cls, entries, feed_link, category):
        for entry in entries:
            title = cls._get_title(entry)
            description = cls._get_description(entry)
            link = cls._get_link(entry)
            published_time = cls._get_time(entry)
            news_source = _get_news_source_website_name_by_feed_title(feed_link)

            yield NewsRSSEntry(title, description, link, published_time, news_source, category)

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

                    return "(Extracted from '%s')\n%s" % (
                        news_source,
                        html_parser.get_news_content(news_link)
                    )

                else:
                    # No proper parser is found.
                    # Add this news_source to candidates
                    candidates.append([news_title, news_source, news_link])

        # No proper parser if found for any of local news sources
        # So use the default parser to parse the first local news source
        if candidates:
            html_parser = local_news_parsers.DefaultHtmlNewsParser()
            news_title, news_source, news_link = candidates[0]

            return "(Extracted from '%s' by default parser)\n%s" % (
                news_source,
                html_parser.get_news_content(news_link)
            )
        else:
            msg = "No candidate local news source for GoogleNews '%s'.\n" % feed.title
            msg += "\tThe raw description is: {}" % feed.description
            raise scraper_utils.NewsScraperError(msg)
