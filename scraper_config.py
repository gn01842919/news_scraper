"""Configurations of the ``news_scraper`` package.
"""


class FeedParserConfig(object):
    """Settings for module rss_feed_parsers.py
    """
    MAX_WORKERS = 10
    HTML_PARSER_WORKER_TIMEOUT = 60


class NewsCollectorConfig(object):
    """Settings mainly for collect_news_to_db.py
    """
    DEBUG = False
    MAX_WORKERS = 10
    RSS_WORKER_TIMEOUT = 120
    RULE_FILE_NAME = "rule.json"
    ERROR_LOG = "error.log"
    DB_HOST = "db"
    DB_PORT = 5432
    DB_USER = "dja1"
    DB_PASSWORD = "_MY_DB_PASSWORD_"
    DB_NAME = "my_focus_news"
