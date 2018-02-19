import unittest
import pickle
import sys


def mocked_rss_feed_parse(url):

    if 'google' in url and 'WORLD' in url:
        input_file = 'pickle-world-google-world-feed.txt'
    elif 'yahoo' in url and 'politics' in url:
        input_file = 'pickle-yahoo-politics-feed.txt'
    else:
        raise ValueError(
            'Mock rss feed url "%s" in is not yet implemented.' % url
        )

    with open(input_file, 'rb') as f:
        feed = pickle.load(f)

    return feed


if __name__ == '__main__':

    mocked_rss_feed_parse('https://tw.news.yahoo.com/rss/politics')
