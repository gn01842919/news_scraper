"""
"""
# Standard library
import logging
from concurrent import futures
from timeit import default_timer as timer
from urllib.error import HTTPError, URLError
# Local modules
import scraper_utils
from scraper_config import NewsCollectorConfig
from db_news_api import NewsDatabaseAPI
from db_operation_api.mydb import PostgreSqlDB
from local_news_parsers import update_local_news_sources_list
from news_sources import news_source_registry
from scraping_rules_reader import get_rules_from_file


def collect_news_by_rules_and_save_to_db():

    debug = NewsCollectorConfig.DEBUG
    db_name = NewsCollectorConfig.DB_NAME
    table_prefix = NewsCollectorConfig.DB_TABLE_PREFIX
    rule_file = NewsCollectorConfig.RULE_FILE_NAME

    start_time = timer()

    # Set up loggers
    log_format = "[%(levelname)s] %(message)s\n"
    scraper_utils.setup_logger(
        'error_log',
        level=logging.WARNING,
        logfile='error.log',
        to_console=False,
        log_format=log_format
    )
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Get scraping rules
    rules_from_file = tuple(get_rules_from_file(rule_file))

    with PostgreSqlDB(database=db_name) as conn:
        db_api = NewsDatabaseAPI(conn, table_prefix=table_prefix)

        rules_from_db = db_api.get_scraping_rules()

        # If rules have changed ==> update scores in DB
        if set(rules_from_file) != set(rules_from_db.values()):
            logging.info("ScrapingRules have changed. Reload rules to DB.")

            db_api.remove_scraping_rules_and_relations()
            _save_scraping_rules_to_db(db_api, rules_from_file)

            _update_scores_with_new_rules_for_all_news_in_db(db_api, rules_from_file)

        # Get news from RSS feeds and apply rules
        news_entries = _retrieve_news_entries_and_set_scraping_rules(rules_from_file)

        # Filter the news by the rules (So target_news is the news of interest)
        target_news = tuple(
            news for news in news_entries if news.total_score > 0
        )

        # Save to db
        _save_news_data_to_db(db_api, target_news)

    if debug:
        # For future development
        logging.info("Updating 'local_news_sources.txt'...")
        update_local_news_sources_list(news_entries, 'local_news_sources.txt')

        # Record all news for debugging
        with open('output.txt', 'w') as f:
            for news in news_entries:
                print(repr(news), file=f)

        for news in target_news:
            print(repr(news))

    logging.info(
        'Recorded %d news out of total %d news.' % (len(target_news), len(news_entries))
    )

    logging.info("Elapsed time: %f seconds" % (timer() - start_time))


def _retrieve_news_entries_and_set_scraping_rules(scraping_rules):
    feeds = _retrieve_registered_news_by_rss()
    news_entries = tuple(entry for feed in feeds for entry in feed.entries)
    for news in news_entries:
        news.set_rules(scraping_rules)

    return news_entries


def _save_scraping_rules_to_db(db_api, scraping_rules):
    for rule in scraping_rules:
        db_api.store_a_scraping_rule(rule)


def _update_scores_with_new_rules_for_all_news_in_db(db_api, new_rules_to_apply):
    rules_from_db = db_api.get_scraping_rules()  # read from db again to get id
    rule_id_map = {value: key for key, value in rules_from_db.items()}

    news_from_db = db_api.get_news_data_and_setup_rule(new_rules_to_apply)

    for news_id, news in news_from_db.items():
        for rule, score in news.rule_score_map.items():
            rule_id = rule_id_map[rule]
            db_api._setup_news_rule_relationship(news_id, rule_id, score)


def _save_news_data_to_db(db_api, news_entries):
    for news in news_entries:
        db_api.store_a_news_data(news)


def _retrieve_registered_news_by_rss(
        num_of_workers=NewsCollectorConfig.MAX_WORKERS,
        worker_timeout=NewsCollectorConfig.RSS_WORKER_TIMEOUT):
    """Retrieve RSS news by a thread pool
    """

    with futures.ThreadPoolExecutor(max_workers=num_of_workers) as executor:
        future_map = {}

        # For each registered news source, put it into thread pool
        for class_name, NewsSourceClass in news_source_registry.items():
            news_src = NewsSourceClass()

            for category in news_src.categories:
                future_obj = executor.submit(news_src.get_raw_feed_object, category)
                future_map[future_obj] = (news_src, category)

        logging.info("Retrieving %d RSS feeds concurrently." % len(future_map))

        done_iter = futures.as_completed(future_map, timeout=worker_timeout)

        try:
            for future_obj in done_iter:
                news_src, category = future_map[future_obj]
                url = news_src._get_rss_url(category)
                try:
                    raw_feed = future_obj.result()
                except HTTPError as e:
                    scraper_utils.log_warning("HTTP Error %d for RSS feed '%s'" % (e.code, url))
                except URLError as e:
                    scraper_utils.log_warning("URL Error [%s] for RSS feed '%s'" % (e.reason, url))
                else:
                    yield news_src.parse_feed(raw_feed, category)

        except futures.TimeoutError as e:
            scraper_utils.log_warning("Timeout in news_collector: %s" % str(e))


if __name__ == '__main__':
    collect_news_by_rules_and_save_to_db()
