"""RSS news sources are written as code in this module.

Attributes:
    _NEWS_SOURCE_REGISTRY (dict): Registry of news sources.
        <Key>: Name of the class.
        <Value>: The news source class.

        When writing a class that inherits the base class ``NewsSource``,
        it is registered in ``_NEWS_SOURCE_REGISTRY`` automatically.

"""
# Local modules
import scraper_utils
import rss_feed_parsers

_NEWS_SOURCE_REGISTRY = {}


def get_news_source_registry():
    """Get registered news source classes.

    Returns:
        dict: ``_NEWS_SOURCE_REGISTRY``

    """
    return _NEWS_SOURCE_REGISTRY


def _register_news_source(cls):
    # pytlint will complain if I add "global _NEWS_SOURCE_REGISTRY" here.
    _NEWS_SOURCE_REGISTRY[cls.__name__] = cls


class NewsMeta(type):
    """Meta class for ``NewsSource`` to register subclasses.

    To register classes except the base class to ``_NEWS_SOURCE_REGISTRY``.
    """
    def __new__(mcs, name, bases, class_dict):
        cls = type.__new__(mcs, name, bases, class_dict)

        # Should not register the abstract base class (NewsSource)
        if bases != (object,):
            _register_news_source(cls)

        return cls


class NewsSource(object, metaclass=NewsMeta):
    """Base class for news sources.

    Subclasses of this class are registered to ``_NEWS_SOURCE_REGISTRY``.
    Note that this class can not be instanciated.

    """

    def __init__(self):
        msg = "Do not instantiate class '%s'!" % self.__class__.__name__
        scraper_utils.log_warning(msg, is_error=True)

        # To make pylint happy
        self.base_url = None
        self.categories = None
        self.rss_map = {}
        self.feed_parser = None

        raise NotImplementedError(msg)

    def get_raw_feed_object(self, category):
        """Get feed oject given a category of the RSS source.

        Args:
            category (str): Which category of the RSS source to retrieve.

        Returns:
            dict: A dictionary representing the RSS feed.
                For more details, please refer to `feedparser documentation`_

        .. _feedparser documentation:
            https://pythonhosted.org/feedparser/introduction.html

        """
        rss_url = self.get_rss_url(category)

        # This will get RSS content from web.
        raw_feed = rss_feed_parsers.get_raw_feed_obj(rss_url)

        # raw_feed_obj.feed.link may have stupid errors, such as:
        # https://news.google.coms/rss/headlines/section/topic/NATION.zh-TW_tw/%E5%8F%B0%E7%81%A3?ned=tw&hl=zh-tw&gl=TW
        # Note the "google.coms" <== stupid typing error
        # So... do not use it, use rss_url instead
        raw_feed.feed.link = rss_url

        return raw_feed

    def parse_feed(self, raw_feed, category):
        """Parse a raw RSS feed and extract necessary information.

        Note that this will call ``rss_feed_parsers.RSSFeedParser.parse_feed``,
        which will process news entries in the feed by a thread pool.

        Args:
            raw_feed (dict): The return value of ``self.get_raw_feed_object(category)``.
            category (str): The category of the RSS source to parse.

        Returns:
            scraper_models.RssFeed: A class that contains only interested fields of a RSS feed.

        """
        return self.feed_parser.parse_feed(raw_feed, category)

    def get_rss_url(self, category):
        """Get the link of a RSS feed specified by ``category``.
        """
        return self.rss_map[category]

    def _add_weird_form_rss_links(self, rss_map_to_add):
        self.categories.extend(key for key in rss_map_to_add.keys())
        self.rss_map.update(rss_map_to_add)


class GoogleNews(NewsSource):
    """Google RSS news sources.

    Args:
        base_url (str): Base url for Google RSS news sources.

        categories (list(str)): Categories of Google RSS news sources.
            Each category corresponds to a RSS news source.

        rss_map (dict): Key: A category. Value: URL of the RSS news source of the category.

        feed_parser (rss_feed_parsers.GoogleFeedParser): The feed parser to parse RSS feeds.

    """

    def __init__(self):
        self.base_url = 'https://news.google.com/news/rss/headlines/section/topic/'
        self.categories = [
            'WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY',
            'ENTERTAINMENT', 'SPORTS', 'SCIENCE', 'HEALTH'
        ]

        params = '?ned=zh-tw_tw&hl=zh-tw&gl=TW'

        self.rss_map = {category: self.base_url + category + params for category in self.categories}
        self._add_other_rss_sources()
        self.feed_parser = rss_feed_parsers.GoogleFeedParser

    def _add_other_rss_sources(self):
        """Add RSS links that does not follow the general rules.
        """

        other_rss_map = {
            'Taiwan': self.base_url + 'NATION.zh-TW_tw/%E5%8F%B0%E7%81%A3?ned=tw&hl=zh-tw&gl=TW',
        }
        super()._add_weird_form_rss_links(other_rss_map)


class YahooNews(NewsSource):
    """Yahoo RSS news sources.

    Args:
        base_url (str): Base url for Yahoo RSS news sources.

        categories (list(str)): Categories of Yahoo RSS news sources.
            Each category corresponds to a RSS news source.

        rss_map (dict): Key: A category. Value: URL of the RSS news source of the category.

        feed_parser (rss_feed_parsers.YahooFeedParser): The feed parser to parse RSS feeds.

    """

    def __init__(self):
        self.base_url = 'https://tw.news.yahoo.com/rss/'
        self.categories = ['politics', 'tech', 'health', 'intl']
        self.rss_map = {category: self.base_url + category for category in self.categories}
        self._add_stock_rss_links()
        self.feed_parser = rss_feed_parsers.YahooFeedParser

    def _add_stock_rss_links(self):
        base_url = 'https://tw.stock.yahoo.com/rss/url/d/e/'
        stock_rss_map = {
            'N2': base_url + 'N2.html',
            'N3': base_url + 'N3.html',
            'N4': base_url + 'N4.html',
            'N7': base_url + 'N7.html',
            'N11': base_url + 'N11.html',
            'R2': base_url + 'R2.html',
            'R3': base_url + 'R3.html',
            'R4': base_url + 'R4.html',
            'R6': base_url + 'R6.html',
        }
        self._add_weird_form_rss_links(stock_rss_map)
