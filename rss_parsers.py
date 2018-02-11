import feedparser
from dateutil import parser as date_parser
from datetime import datetime
from collections import namedtuple
from bs4 import BeautifulSoup


NewsEntry = namedtuple("NewsEntry", "title description link published_time")


class MyFeed:
    def __init__(self, title, subtitle, link, language, published_time, entries):
        self.title = title
        self.subtitle = subtitle
        self.link = link
        self.language = language
        self.published_time = published_time
        self.entries = entries  # Reference to a tuple of NewsEntry

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

        entries = tuple(cls._get_entries_from_feed(feed.entries))
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
