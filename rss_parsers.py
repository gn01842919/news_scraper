import feedparser
import logging
from dateutil import parser as date_parser
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import HTTPError, URLError


def _check_url_is_valid(url):
    logger = logging.getLogger('invalid_rss_urls')

    try:
        with urlopen(url):
            pass
    except HTTPError as e:
        logger.warning("HTTP Error %d for '%s'" % (e.code, url))
        raise
    except URLError as e:
        logger.warning("URL Error [%s] for '%s'" % (e.reason, url))
        raise


def _get_news_source_website_name(title):

    title = title.lower()

    if 'google' in title:
        return 'google'
    elif 'yahoo' in title:
        return 'yahoo'
    else:
        return 'others'


class NewsEntry:
    def __init__(self, title, description, link, published_time, source, category=None, tags=None):
        self.title = title
        self.description = description
        self.link = link
        self.published_time = published_time
        self.source = source
        self.rule_score_map = {}  # rule ==> score, will be set in news_collector.py
        self.tags = tags.copy() if tags else set()  # .copy() -> shallow copy

        # Category defined by RSS feed link
        if category:
            self.tags.add(category)

    def set_rules(self, rules):
        for rule in rules:
            score = self._compute_score_by_rule(rule)
            self.rule_score_map[rule] = score
            self._set_tags_from_rules(rule, score)

    @property
    def total_score(self):
        if not self.rule_score_map:
            logger = logging.getLogger('standard_output')
            logger.warning('No scraping rule set for %s' % str(self))

        return sum(score for score in self.rule_score_map.values() if score > 0)

    def _set_tags_from_rules(self, rule, score):
        if score > 0:
            self.tags.update(rule.tags)  # shallow copy

    def _compute_score_by_rule(self, rule):
        """
        Score:
            < 0 ==> excluded     (by rule.excluded_keywords)
            > 0 ==> of interest  (by rule.included_keywords)
            = 0 ==> others (not of interest)
        """
        score = 0

        for keyword in rule.excluded_keywords:
            if keyword in self.title:
                score -= 1

        # Skip 'included_keywords' if this news should be excluded
        if score >= 0:
            for keyword in rule.included_keywords:
                # Should change to analyse the content of the news
                if keyword in self.title:
                    score += 1

        return score

    def __repr__(self):
        return (
            "====== <NewsEntry object at {}> ======\n"
            "  [Title]       : {}\n"
            "  [Description] : {}\n"
            "  [Link]        : {}\n"
            "  [Published]   : {}\n"
            "  [Source]      : {}\n"
            "  [Tags]        : {}\n"
            "  [Rules]       : {}\n"
            "==================================================\n"
            .format(
                hex(id(self)),
                self.title,
                self.description,
                self.link,
                self.published_time,
                self.source,
                self.tags,
                {str(rule): score for rule, score in self.rule_score_map.items()}
            )
        )

    def __str__(self):
        return "<NewsEntry '%s'>" % self.title


class MyFeed:
    def __init__(self, title, subtitle, link, language, published_time, entries):
        self.title = title
        self.subtitle = subtitle
        self.link = link
        self.language = language
        self.published_time = published_time
        self.entries = entries  # A tuple of NewsEntry

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


class RSSFeedParser:

    @classmethod
    def parse_feed(cls, url, category=None):

        _check_url_is_valid(url)

        feed = feedparser.parse(url)

        # # Used to generate input data for mock in unit test
        # filename = url.replace(':', '.').replace('/', '_')
        #            .replace('?', '-').replace('&', '-')
        #            .replace('=', '_').replace('%', '_')
        # print(repr(filename))
        # with open(filename + '.txt', 'wb') as f:
        #     import pickle
        #     pickle.dump(feed, f)

        title = cls._get_title_from_feed(feed.feed)
        subtitle = cls._get_subtitle_from_feed(feed.feed)
        feed_link = cls._get_link_from_feed(feed.feed)
        language = cls._get_language_from_feed(feed.feed)
        published_time = cls._get_time_from_feed(feed.feed)

        entries = tuple(cls._get_entries_from_feed(feed.entries, feed_link, category))
        return MyFeed(title, subtitle, feed_link, language, published_time, entries)

    @classmethod
    def _get_entries_from_feed(cls, entries, feed_link, category):
        for entry in entries:
            title = cls._get_title_from_feed(entry)
            description = cls._get_subtitle_from_feed(entry)
            link = cls._get_link_from_feed(entry)
            published_time = cls._get_time_from_feed(entry)
            news_source = _get_news_source_website_name(feed_link)

            yield NewsEntry(title, description, link, published_time, news_source, category)

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
            for src in news_sources_li:
                news_title = src.a.get_text()
                news_source = src.font.get_text()
                try:
                    news_link = src.a["href"]
                except AttributeError:
                    continue

                # ### The format of local news source are different
                # ### Do it someday....
                # html = urlopen(news_link)
                # inner_bsobj = BeautifulSoup(html, "html.parser")
                # # have to grab the news content and return it as discription

                output += "[{}] {}\n{}\n".format(news_source, news_title, news_link)

            return output.strip()
