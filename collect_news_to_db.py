"""This module collects news, filter them by rules, and store them to DB.

Example:
    This module can be executed directly::
        $ python collect_news_to_db.py

"""
# Standard library
import logging
from concurrent import futures
from timeit import default_timer as timer
from urllib.error import HTTPError, URLError
# Local modules
import scraper_utils
from settings import SCRAPER_CONFIG, DATABASE_CONFIG
from db_news_api import NewsDatabaseAPI
from db_operation_api.mydb import get_database
from local_news_parsers import update_local_news_sources_list
from news_sources import get_news_source_registry
from scraping_rules_reader import get_rules_from_file


def scrape_news_and_save_to_db():
    """Collect news, filter them by rules, and store them to DB.

    This method does the following:
        1. Read scraping rules from file.
        2. Read scraping rules from DB.
        3. If rules have changed, update the the rules in DB by rules from file.
        4. Retrieve news data from RSS news links.
        5. Filter the news by scraping rules, and save the result to DB.

    """
    debug = SCRAPER_CONFIG["debug"]
    rule_file = SCRAPER_CONFIG["rule_file"]
    error_log = SCRAPER_CONFIG["error_log"]

    start_time = timer()

    # Set up loggers
    log_format = "[%(levelname)s] %(message)s\n"
    scraper_utils.setup_logger(
        'error_log',
        level=logging.WARNING,
        logfile=error_log,
        to_console=False,
        log_format=log_format
    )
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Get scraping rules
    rules_from_file = tuple(get_rules_from_file(rule_file))

    with get_database(DATABASE_CONFIG) as conn:
        db_api = NewsDatabaseAPI(conn)

        rules_from_db = db_api.get_scraping_rules()

        # If rules have changed ==> update scores in DB
        if set(rules_from_file) != set(rules_from_db.values()):
            logging.info("ScrapingRules have changed. Reload rules to DB.")

            db_api.remove_all_rules_and_relations()
            _save_scraping_rules_to_db(db_api, rules_from_file)

            _update_scores_for_news_in_db(db_api, rules_from_file)

        # Get news from RSS feeds and apply rules
        news_entries = _scrape_news_data_and_set_rules(rules_from_file)

        # Filter the news by the rules (So target_news is the news of interest)
        target_news = tuple(
            news for news in news_entries if news.total_score > 0
        )

        # Save to db
        _save_news_data_to_db(db_api, target_news)

    if debug:
        # For future development
        logging.info("Updating 'local_news_sources.txt'...")
        update_local_news_sources_list(news_entries, "local_news_sources.txt")

        # Record all news for debugging
        with open('output.txt', 'w') as outfile:
            for news in news_entries:
                print(repr(news), file=outfile)

        for news in target_news:
            print(repr(news))

    msg = (
        "Recorded %d news out of total %d news. Elapsed time: %f seconds"
        % (len(target_news), len(news_entries), timer() - start_time)
    )
    logging.info(msg)


def _scrape_news_data_and_set_rules(scraping_rules):
    """Retrieve news entries from the Internet, and set scraping rules to them.
    """
    feeds = _scrape_registered_news_by_rss()
    news_entries = tuple(entry for feed in feeds for entry in feed.entries)
    for news in news_entries:
        news.set_rules(scraping_rules)

    return news_entries


def _save_scraping_rules_to_db(db_api, scraping_rules):
    for rule in scraping_rules:
        db_api.store_a_scraping_rule(rule)


def _update_scores_for_news_in_db(db_api, new_rules_to_apply):
    """Update scores with scraping rules for all news data in DB.
    """
    rules_from_db = db_api.get_scraping_rules()  # read from db again to get id
    rule_id_map = {value: key for key, value in rules_from_db.items()}

    news_from_db = db_api.get_news_data_and_setup_rule(new_rules_to_apply)

    for news_id, news in news_from_db.items():
        for rule, score in news.rule_score_map.items():
            rule_id = rule_id_map[rule]
            db_api.setup_news_rule_relationship(news_id, rule_id, score)


def _save_news_data_to_db(db_api, news_entries):
    for news in news_entries:
        db_api.store_a_news_data(news)


def _scrape_registered_news_by_rss(
        num_of_workers=SCRAPER_CONFIG["max_workers"],
        worker_timeout=SCRAPER_CONFIG["rss_worker_timeout"]):
    """Retrieve RSS news from the Internet with a thread pool.
    """

    with futures.ThreadPoolExecutor(max_workers=num_of_workers) as executor:
        future_map = {}

        # For each registered news source, put it into thread pool
        news_sources = get_news_source_registry()
        for news_source_class in news_sources.values():
            news_src = news_source_class()

            for category in news_src.categories:
                future_obj = executor.submit(news_src.get_raw_feed_object, category)
                future_map[future_obj] = (news_src, category)

        msg = "Retrieving %d RSS feeds concurrently." % len(future_map)
        logging.info(msg)

        done_iter = futures.as_completed(future_map, timeout=worker_timeout)

        try:
            for future_obj in done_iter:
                news_src, category = future_map[future_obj]
                url = news_src.get_rss_url(category)
                try:
                    raw_feed = future_obj.result()
                except HTTPError as err:
                    scraper_utils.log_warning(
                        "HTTP Error %d for RSS feed '%s'" % (err.code, url)
                    )
                except URLError as err:
                    scraper_utils.log_warning(
                        "URL Error [%s] for RSS feed '%s'" % (err.reason, url)
                    )
                else:
                    yield news_src.parse_feed(raw_feed, category)

        except futures.TimeoutError as err:
            scraper_utils.log_warning("Timeout in news_collector: %s" % str(err))


if __name__ == '__main__':
    scrape_news_and_save_to_db()
