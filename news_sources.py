"""
have to do:
    pip install feedparser python-dateutil beautifulsoup4
"""
import feedparser
from dateutil import parser as date_parser
from datetime import datetime
from collections import namedtuple
from bs4 import BeautifulSoup

"""
To-Do:
    1. write unit tests
    2. Yahoo stock rss
"""

NewsEntry = namedtuple("NewsEntry", "title description link published_time")


class MyFeed:
    def __init__(self, title, subtitle, link, language, published_time, entries):
        self.title = title
        self.subtitle = subtitle
        self.link = link
        self.language = language
        self.published_time = published_time
        self.entries = entries  # Reference to a list of named_tuples

    def __str__(self):
        return (
            "++++++++++++++++++++\n"
            "[Title]    : {}\n"
            "[Subtitle] : {}\n"
            "[Link]     : {}\n"
            "[Language] : {}\n"
            "[Published]: {}\n"
            "[Entries #]: {}\n"
            "++++++++++++++++++++\n"
            .format(
                self.title, self.subtitle, self.link,
                self.language, self.published_time,
                len(self.entries)
            )
        )


class RSSFeedParser:

    @classmethod
    def parse_feed(cls, url):
        feed = feedparser.parse(url)

        title = cls._get_title_from_feed(feed.feed)
        subtitle = cls._get_subtitle_from_feed(feed.feed)
        link = cls._get_link_from_feed(feed.feed)
        language = cls._get_language_from_feed(feed.feed)
        published_time = cls._get_time_from_feed(feed.feed)

        entries = list(cls._get_entries_from_feed(feed.entries))
        return MyFeed(title, subtitle, link, language, published_time, entries)

    @classmethod
    def _get_entries_from_feed(cls, entries):
        for entry in entries:
            title = cls._get_title_from_feed(entry)
            description = cls._get_subtitle_from_feed(entry)
            link = cls._get_link_from_feed(entry)
            published_time = cls._get_time_from_feed(entry)
            yield NewsEntry(title, description, link, published_time)

    @staticmethod
    def _get_title_from_feed(feed):
        return feed.title

    @staticmethod
    def _get_subtitle_from_feed(feed):
        try:
            return feed.subtitle.strip()
        except AttributeError:
            return feed.description.strip()

    @staticmethod
    def _get_link_from_feed(feed):
        return feed.link

    @staticmethod
    def _get_language_from_feed(feed):
        return feed.language

    @staticmethod
    def _get_time_from_feed(feed):
        # Using datetime.datetime(*feed.feed.published_parsed[:-3]) can not
        # preserve original timezone information
        # So use dateutil.parser().parse(feed.feed.published) instead
        # Reference:
        #     https://stackoverflow.com/questions/20867795/python-how-to-get-timezone-from-rss-feed

        try:
            published_time = date_parser.parse(feed.published)
        except AttributeError:
            # feed.published is not provided
            published_time = datetime.utcnow()

        return published_time


class GoogleFeedParser(RSSFeedParser):

    @staticmethod
    def _get_subtitle_from_feed(feed):

        try:
            return feed.subtitle
        except AttributeError:
            # feed.description is a list of same news from different sources
            # So let's parse it

            output = ""

            bsobj = BeautifulSoup(feed.description, "html.parser")
            news_sources_li = bsobj.findAll("li")
            # <li>
            #     <a href="http://www.cna.com.tw/news/aopl/201802110062-1.aspx" target="_blank">
            #          以色列攻擊敘利亞境內伊朗目標美力挺
            #     </a>
            #     &nbsp;&nbsp;
            #     <font color="#6F6F6F">
            #         中央社即時新聞
            #     </font>
            # </li>
            for src in news_sources_li:
                news_title = src.a.get_text()
                news_source = src.font.get_text()
                output += "[{}] {}\n".format(news_source, news_title)

            return output.strip()


class YahooFeedParser(RSSFeedParser):
    pass


class GoogleNews:
    def __init__(self):
        self.base_url = 'https://news.google.com/news/rss/headlines/section/topic/'
        self.categories = ['WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY', 'ENTERTAINMENT', 'SPORTS', 'SCIENCE', 'HEALTH']

        params = '?ned=zh-tw_tw&hl=zh-tw&gl=TW'

        self.rss_map = {category: self.base_url + category + params for category in self.categories}
        self._add_rss_link_for_strange_format_ones()

    def _add_rss_link_for_strange_format_ones(self):

        other_rss_map = {
            'Taiwan': 'NATION.zh-TW_tw/%E5%8F%B0%E7%81%A3?ned=tw&hl=zh-tw&gl=TW',
        }
        self.categories.extend(key for key in other_rss_map.keys())
        self.rss_map.update(other_rss_map)

    def get_rss_url(self, category):
        return self.rss_map[category]

    def get_feed_object(self, category):
        rss_url = self.get_rss_url(category)
        return GoogleFeedParser.parse_feed(rss_url)


class YahooNews:

    def __init__(self):
        self.base_url = 'https://tw.news.yahoo.com/rss/'
        self.categories = ['politics', 'tech', 'health', 'intl']
        self.rss_map = {category: self.base_url + category for category in self.categories}
        self._add_stock_rss_links()

    def _add_stock_rss_links(self):
        '''
        Todo:
          https://tw.info.yahoo.com/rss/
            -> Stock related ones such as http://tw.stock.yahoo.com/rss/url/d/e/N2.html
        '''
        pass

    def get_rss_url(self, category):
        return self.rss_map[category]

    def get_feed_object(self, category):
        rss_url = self.get_rss_url(category)
        return YahooFeedParser.parse_feed(rss_url)


if __name__ == '__main__':

    google_news = GoogleNews()
    print(google_news.get_feed_object('WORLD'))

    entries = google_news.get_feed_object('WORLD').entries
    for i in range(2):
        entry = entries[i]
        print('-' * 10)
        print(entry.title)
        print(entry.description)
        print(entry.link)
        print(entry.published_time)
        print('-' * 10)

    yahoo_news = YahooNews()
    print(yahoo_news.get_feed_object('politics'))

    entries = yahoo_news.get_feed_object('politics').entries
    for i in range(2):
        entry = entries[i]
        print('-' * 10)
        print(entry.title)
        print(entry.description)
        print(entry.link)
        print(entry.published_time)
        print('-' * 10)
