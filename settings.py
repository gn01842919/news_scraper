"""Configurations of the ``news_scraper`` package.
"""

SCRAPER_CONFIG = {
    "debug": False,
    "max_workers": 10,
    "rss_worker_timeout": 120,
    "rule_file": "rule.json",
    "error_log": "error.log",
}

DATABASE_CONFIG = {
    "db_host": "db",
    "db_port": 5432,
    "db_user": "dja1",
    "db_password": "_MY_DB_PASSWORD_",
    "database": "my_focus_news",
}

FEED_PARSER_CONFIG = {
    "max_workers": 10,
    "html_parser_worker_timeout": 60,
}
