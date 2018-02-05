"""
To-Do:
    1. write unit tests
    2. Yahoo stock rss
"""

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
