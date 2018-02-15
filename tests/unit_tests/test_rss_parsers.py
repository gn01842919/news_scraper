import unittest
from news_scrapper.rss_parsers import GoogleFeedParser


class GoogleFeedParserTest(unittest.TestCase):

    def setUp(self):
        self.parser = GoogleFeedParser()

    def test_nothing(self):
        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()
