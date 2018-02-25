"""
"""
import logging
# Local modules
import scraper_utils
import rss_feed_parsers


news_source_registry = {}


def _register_news_source(cls):
    global news_source_registry
    news_source_registry[cls.__name__] = cls


class NewsMeta(type):
    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)

        # Should not register the abstract base class (NewsSource)
        if bases != (object,):
            _register_news_source(cls)

        return cls


class NewsSource(object, metaclass=NewsMeta):

    def __init__(self):
        msg = "Do not instantiate class '%s'!" % self.__class__.__name__
        scraper_utils.log_warning(msg, is_error=True)
        raise NotImplementedError(msg)

    def get_raw_feed_object(self, category):
        rss_url = self._get_rss_url(category)

        # This will get RSS content from web.
        # Need to wait for IO
        logging.info("Getting RSS from [%s]." % category)
        raw_feed = rss_feed_parsers.get_raw_feed_obj(rss_url)

        # raw_feed_obj.feed.link may have stupid errors, such as:
        # https://news.google.coms/rss/headlines/section/topic/NATION.zh-TW_tw/%E5%8F%B0%E7%81%A3?ned=tw&hl=zh-tw&gl=TW
        # Note the "google.coms" <== stupid typing error
        # So... do not use it, usr rss_url instead
        raw_feed.feed.link = rss_url

        return raw_feed

    def parse_feed(self, raw_feed, category):
        # parse_feed may need to get news content from local news sources
        # ==> need to wait for IO (web)
        return self.feed_parser.parse_feed(raw_feed, category)

    def _get_rss_url(self, category):
        return self.rss_map[category]


class GoogleNews(NewsSource):
    def __init__(self):
        self.base_url = 'https://news.google.com/news/rss/headlines/section/topic/'
        self.categories = [
            'WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY',
            'ENTERTAINMENT', 'SPORTS', 'SCIENCE', 'HEALTH'
        ]

        params = '?ned=zh-tw_tw&hl=zh-tw&gl=TW'

        self.rss_map = {category: self.base_url + category + params for category in self.categories}
        self._add_rss_link_for_strange_format_ones()
        self.feed_parser = rss_feed_parsers.GoogleFeedParser

    def _add_rss_link_for_strange_format_ones(self):

        other_rss_map = {
            'Taiwan': self.base_url + 'NATION.zh-TW_tw/%E5%8F%B0%E7%81%A3?ned=tw&hl=zh-tw&gl=TW',
        }
        self.categories.extend(key for key in other_rss_map.keys())
        self.rss_map.update(other_rss_map)


class YahooNews(NewsSource):

    def __init__(self):
        self.base_url = 'https://tw.news.yahoo.com/rss/'
        self.categories = ['politics', 'tech', 'health', 'intl']
        self.rss_map = {category: self.base_url + category for category in self.categories}
        self._add_stock_rss_links()
        self.feed_parser = rss_feed_parsers.YahooFeedParser

    def _add_stock_rss_links(self):
        '''
        Todo:
          https://tw.info.yahoo.com/rss/
            -> Stock related ones such as http://tw.stock.yahoo.com/rss/url/d/e/N2.html
        '''
        pass


if __name__ == '__main__':

    print(news_source_registry)

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
