"""Unit test for rss_feed_parsers.py

Note that this is not maintained any more.
"""
import pickle
import unittest
from unittest.mock import patch
from news_scraper.rss_feed_parsers import GoogleFeedParser, YahooFeedParser


def mocked_rss_feed_parse(url):
    """To replase ``feedparser.parse`` function to mock scraping news from the Internet.

    HTTP connections take time, and RSS feeds change very frequently,
    so use mock to use previously stored RSS feed objects instead.
    """

    if 'google' in url and 'WORLD' in url:
        input_file = 'pickle-world-google-world-feed-0219.txt'
    elif 'yahoo' in url and 'politics' in url:
        input_file = 'pickle-yahoo-politics-feed-0219.txt'
    else:
        raise ValueError(
            'Mock rss feed url "%s" in is not yet implemented.' % url
        )

    with open(input_file, 'rb') as infile:
        feed = pickle.load(infile)

    return feed


class GoogleFeedParserTest(unittest.TestCase):
    """Test ``GoogleFeedParser``.
    """

    def setUp(self):
        """Set up RSS feed parser
        """
        self.parser = GoogleFeedParser()

    @patch('feedparser.parse', side_effect=mocked_rss_feed_parse)
    def test_parse_feed(self, mock_parse):
        """Test ``GoogleFeedParser.parse_feed() method.``
        """

        feed_url = (
            "https://news.google.com/news/rss/headlines/section/topic/"
            "WORLD?ned=zh-tw_tw&hl=zh-tw&gl=TW"
        )

        my_feed = self.parser.parse_feed(feed_url)

        mock_parse.assert_called_once_with(feed_url)

        self.assertEqual(my_feed.title, 'World - Google News')
        self.assertEqual(my_feed.subtitle, 'Google News')
        self.assertEqual(str(my_feed.published_time), '2018-02-19 09:13:44+00:00')
        self.assertEqual(len(my_feed.entries), 20)

        second_entry = my_feed.entries[1]
        self.assertEqual(
            second_entry.title,
            '川普批FBI忙通俄槍擊倖存者怒：沒良心'
        )
        self.assertEqual(
            second_entry.link,
            'http://www.cna.com.tw/news/firstnews/201802190013-1.aspx'
        )
        self.assertEqual(
            str(second_entry.published_time),
            '2018-02-19 02:15:00+00:00'
        )


class YahooFeedParserTest(unittest.TestCase):
    """Test ``YahooFeedParser``.
    """

    def setUp(self):
        """Set up RSS feed parser
        """
        self.parser = YahooFeedParser()

    @patch('feedparser.parse', side_effect=mocked_rss_feed_parse)
    def test_parse_feed(self, mock_parse):
        """Test ``YahooFeedParser.parse_feed() method.``
        """

        feed_url = 'https://tw.news.yahoo.com/rss/politics'

        my_feed = self.parser.parse_feed(feed_url)

        mock_parse.assert_called_once_with(feed_url)

        self.assertEqual(my_feed.title, '政治新聞 - Yahoo奇摩新聞')
        self.assertEqual(my_feed.subtitle, '瀏覽 Yahoo奇摩新聞上的政治頭條新聞及最新動態。尋找相關新聞報導、影音、照片和分析意見。')
        self.assertEqual(len(my_feed.entries), 30)

        second_entry = my_feed.entries[1]
        self.assertEqual(
            second_entry.title,
            '圍堵俄勢力 美兩驅逐艦進駐黑海'
        )
        self.assertEqual(
            second_entry.link,
            (
                "https://tw.news.yahoo.com/"
                "%E5%9C%8D%E5%A0%B5%E4%BF%84%E5%8B%A2%E5%8A%9B"
                "-%E7%BE%8E%E5%85%A9%E9%A9%85%E9%80%90%E8%89%A6"
                "%E9%80%B2%E9%A7%90%E9%BB%91%E6%B5%B7-090400259.html"
            )
        )
        self.assertEqual(
            str(second_entry.published_time),
            '2018-02-19 17:04:00+08:00'
        )


if __name__ == '__main__':

    unittest.main()
