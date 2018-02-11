"""
have to do:
    pip install feedparser python-dateutil
"""

import feedparser
from datetime import datetime
from dateutil import parser, tz

# url = 'https://news.google.com/news/rss/headlines/section/topic/WORLD?ned=zh-tw_tw&hl=zh-tw&gl=TW'
url = 'https://tw.news.yahoo.com/rss/politics'

# feed.feed.title can also be retrieved as
# feed['feed']['title']
# This may apply to most other attributes...

feed = feedparser.parse(url)

print(feed.feed.title)
print(feed.feed.subtitle)
print(feed.feed.link)
print(feed.feed.language)
# print(feed.feed.published)
# print(feed.feed.published_parsed)

# Using datetime.datetime(*feed.feed.published_parsed[:-3]) can not
# preserve original timezone information
# So use dateutil.parser().parse(feed.feed.published) instead
# Reference:
#     https://stackoverflow.com/questions/20867795/python-how-to-get-timezone-from-rss-feed

# dt2 = parser.parse(feed.feed.published)
# print('+' * 10)
# print(feed.feed.published)
# print(dt2)
# print(dt2.utcoffset())
# print(dt2.astimezone(tz.tzutc()))
# print('+' * 10)

for entry in feed.entries:
    print(entry.title)
    print(entry.description)
    print(entry.link)
    # print(datetime(*entry.published_parsed[:-3]))
    # remember to compare two types of timezone
    # to assure that timezone is correct
    # print(entry.keys())
    published_time = parser.parse(entry.published)
    print(published_time)
