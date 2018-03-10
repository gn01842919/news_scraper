"""Configurations of "news_scraper"
"""


class FeedParserConfig(object):
    MAX_WORKERS = 10
    HTML_PARSER_WORKER_TIMEOUT = 60


class NewsCollectorConfig(object):
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
    DB_TABLE_PREFIX = "shownews_"
