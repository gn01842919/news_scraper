import logging
import os
from urllib.error import HTTPError, URLError
from concurrent import futures
from news_sources import news_source_registry
from scraping_rules_creator import read_rules_from_file

default_log_format = '[%(levelname)s] (%(asctime)s) %(message)s'
MAX_WORKERS = 10
RSS_WORKER_TIMEOUT = 10


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


def retrieve_registered_news_by_rss(num_of_workers, worker_timeout):
    """Retrieve RSS news by a thread pool
    """
    stdout_logger = logging.getLogger('standard_output')
    invalid_url_logger = logging.getLogger('invalid_rss_urls')

    with futures.ThreadPoolExecutor(max_workers=num_of_workers) as executor:
        future_url_map = {}

        # For each registered news source, put it into thread pool
        for class_name, NewsSourceClass in news_source_registry.items():
            news_src = NewsSourceClass()

            for category in news_src.categories:
                future_obj = executor.submit(news_src.get_feed_object, category)
                future_url_map[future_obj] = news_src._get_rss_url(category)

        stdout_logger.info("There are %d RSS feeds to retrieve." % len(future_url_map))

        done_iter = futures.as_completed(future_url_map, timeout=worker_timeout)

        for future_obj in done_iter:
            url = future_url_map[future_obj]
            try:
                feed_obj = future_obj.result()
            except HTTPError as e:
                invalid_url_logger.warning("HTTP Error %d for '%s'" % (e.code, url))
            except URLError as e:
                invalid_url_logger.warning("URL Error [%s] for '%s'" % (e.reason, url))
            else:
                yield feed_obj


def get_news_entries(num_of_workers, worker_timeout):
    feeds = retrieve_registered_news_by_rss(num_of_workers, worker_timeout)
    return tuple(entry for feed in feeds for entry in feed.entries)


def set_rules_to_news_entry(news_entries, scraping_rules):
    for entry in news_entries:
        entry.set_rules(scraping_rules)


def get_target_news_by_scraping_rules(news_entries, scraping_rules):
    for news in news_entries:
        if news.total_score > 0:
            yield news


def main():

    # Set up loggers
    http_error_log_path = os.path.join(os.getcwd(), 'RSS_URL_Problems.log')
    setup_logger('invalid_rss_urls', logfile=http_error_log_path, to_console=True)
    setup_logger('standard_output', to_console=True, level=logging.DEBUG)
    stdout_logger = logging.getLogger('standard_output')

    # Get scraping rules
    scraping_rules = read_rules_from_file('test.rule')

    # Get news from RSS feeds and apply rules
    news_entries = get_news_entries(
        num_of_workers=MAX_WORKERS,
        worker_timeout=RSS_WORKER_TIMEOUT
    )
    set_rules_to_news_entry(news_entries, scraping_rules)

    # Filter the news by the rules (So target_news is the news of interest)
    target_news = tuple(get_target_news_by_scraping_rules(news_entries, scraping_rules))

    stdout_logger.info(
        'Record %d news out of total %d news.' % (len(target_news), len(news_entries))
    )

    for news in target_news:
        print(repr(news))


if __name__ == '__main__':
    main()
