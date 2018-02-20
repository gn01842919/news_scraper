import logging
import os
from urllib.error import HTTPError, URLError
from news_sources import news_source_registry
from scraping_rules_creator import read_rules_from_file

default_log_format = '[%(levelname)s] (%(asctime)s) %(message)s'


def setup_logger(
        name,
        level=logging.INFO,
        logfile=None,
        to_console=True,
        log_format=default_log_format):

    formatter = logging.Formatter(log_format)
    logger = logging.getLogger(name)

    logger.setLevel(level)

    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if to_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger


def retrieve_registered_news_by_rss():

    for class_name, NewsSourceClass in news_source_registry.items():
        news_src = NewsSourceClass()
        for category in news_src.categories:
            try:
                feed_obj = news_src.get_feed_object(category)
            except (HTTPError, URLError):
                # These errors are logged in rss_parsers.py
                continue

            yield feed_obj


def get_news_of_insterest_by_scraping_rules(news_entries, rules):

    for news in news_entries:
        if news.total_score > 0:
            yield news


if __name__ == '__main__':

    # set logger for HTTP and URL errors
    http_error_log_path = os.path.join(os.getcwd(), 'RSS_URL_Problems.log')
    setup_logger('invalid_rss_urls', logfile=http_error_log_path, to_console=True)
    setup_logger('standard_output', to_console=True, level=logging.DEBUG)

    feeds = retrieve_registered_news_by_rss()

    news_entries = tuple(entry for feed in feeds for entry in feed.entries)

    scraping_rules = read_rules_from_file('test.rule')

    for entry in news_entries:
        entry.set_rules(scraping_rules)

    target_news = tuple(get_news_of_insterest_by_scraping_rules(news_entries, scraping_rules))

    stdout_logger = logging.getLogger('standard_output')
    stdout_logger.info(
        'Record %d news out of total %d news.' % (len(target_news), len(news_entries))
    )

    for news in target_news:
        print(repr(news))
