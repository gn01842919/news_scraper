"""
"""

# Standard library
import logging
from concurrent import futures
from timeit import default_timer as timer
from urllib.error import HTTPError, URLError
# Local modules
import news_data
import scraper_utils
from local_news_parsers import update_local_news_sources_list
from news_sources import news_source_registry
from scraping_rules_reader import read_rules_from_file

MAX_WORKERS = 200
RSS_WORKER_TIMEOUT = 120


def get_news_entries(num_of_workers, worker_timeout):
    feeds = retrieve_registered_news_by_rss(num_of_workers, worker_timeout)

    return tuple(entry for feed in feeds for entry in feed.entries)


def retrieve_registered_news_by_rss_sequentially():

    for class_name, NewsSourceClass in news_source_registry.items():
        news_src = NewsSourceClass()
        for category in news_src.categories:
            try:
                feed_obj = news_src.get_feed_object(category)
            except (HTTPError, URLError):
                # These errors are logged in rss_parsers.py
                continue

            yield feed_obj


def retrieve_registered_news_by_rss(num_of_workers, worker_timeout):
    """Retrieve RSS news by a thread pool
    """
    result_map = {}
    with futures.ThreadPoolExecutor(max_workers=num_of_workers) as executor:
        future_news_source_map = {}
        future_news_entry_map = {}

        # For each registered news source, put it into thread pool
        for class_name, NewsSourceClass in news_source_registry.items():
            news_src = NewsSourceClass()

            for category in news_src.categories:
                future_obj = executor.submit(news_src.get_raw_feed_object, category)
                future_news_source_map[future_obj] = (news_src, category)
                # future_news_source_map[future_obj] = news_src._get_rss_url(category)

        logging.info("Retrieving %d RSS feeds concurrently." % len(future_news_source_map))

        done_iter = futures.as_completed(future_news_source_map, timeout=worker_timeout)

        try:

            for future_obj in done_iter:
                news_src, category = future_news_source_map[future_obj]
                url = news_src._get_rss_url(category)
                logging.info("RSS feed [%s] is retrieved." % category)
                try:
                    raw_feed = future_obj.result()
                except HTTPError as e:
                    scraper_utils.log_warning("HTTP Error %d for RSS feed '%s'" % (e.code, url))
                except URLError as e:
                    scraper_utils.log_warning("URL Error [%s] for RSS feed '%s'" % (e.reason, url))
                else:
                    news_feed_obj, news_entries_done_iter, future_map = news_src.feed_parser.parse_feed_with_threadpool(
                        raw_feed, executor, future_news_entry_map, category
                    )
                    result_map[news_feed_obj] = (news_entries_done_iter, future_map)

        except futures.TimeoutError as e:
            scraper_utils.log_warning("Timeout in news_collector: %s" % str(e))

        print("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFinalllllyyyyyyyyyyyyyyyyy")

        for news_feed_obj, (done_iter, future_map) in result_map.items():
            news_entries = news_src.feed_parser.yield_news_entry_given_done_future_iters(
                done_iter, future_map
            )
            news_feed_obj.entries = tuple(news_entries)
            yield news_feed_obj


def main():
    start_time = timer()
    # Set up loggers

    # Error / Warning log
    # if to_console is set to True, warning msgs will be print twice.
    # Because root logger will also display it.
    scraper_utils.setup_logger(
        'error_log', level=logging.WARNING, logfile='error.log', to_console=False
    )

    # root logger
    logging.basicConfig(level=logging.DEBUG, format=scraper_utils.default_log_format)

    # Get scraping rules
    scraping_rules = read_rules_from_file('test.rule')

    # Get news from RSS feeds and apply rules
    news_entries = get_news_entries(MAX_WORKERS, RSS_WORKER_TIMEOUT)
    news_data.set_rules_to_news_entries(news_entries, scraping_rules)

    # Recored local news sources for future development
    logging.info("Updating 'local_news_sources.txt'...")
    update_local_news_sources_list(news_entries, 'local_news_sources.txt')

    with open('output.txt', 'w') as f:
        for news in news_entries:
            print(repr(news), file=f)

    # Filter the news by the rules (So target_news is the news of interest)
    target_news = tuple(
        news_data.get_target_news_by_scraping_rules(news_entries, scraping_rules)
    )

    logging.info(
        'Record %d news out of total %d news.' % (len(target_news), len(news_entries))
    )

    # for news in target_news:
    #     print(repr(news))

    logging.info("Done. Elapsed time: %f seconds" % (timer() - start_time))


if __name__ == '__main__':
    main()
