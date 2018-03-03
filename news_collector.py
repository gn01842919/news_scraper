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
from scraping_rules_reader import read_rules_from_file, read_rules_from_db_connection
from store_data_to_db import NewsDatabaseAPI
from db_operation_api.mydb import PostgreSqlDB

MAX_WORKERS = 10
RSS_WORKER_TIMEOUT = 120


def _recalculate_news_scores():
    # read news from db
    # compute scores
    # store back
    pass


def _read_news_from_db(conn, db_api, rules):
    query = "SELECT id, title, content, url, time from shownews_newsdata;"
    rows = conn.execute_sql_command(query)

    return {
        id: news_data.NewsRSSEntry(title, content, url, pub_time, '', rules=rules)
        for id, title, content, url, pub_time in rows
    }


def save_scraping_rules_into_database(databse_name, scraping_rules):
    with PostgreSqlDB(database=databse_name) as conn:

        db_api = NewsDatabaseAPI(conn, table_prefix="shownews_")

        # The sequence is essential
        # MUST store scraping_rules first, news_entries latter!
        for rule in scraping_rules:
            db_api.store_a_scraping_rule_to_db(rule)



def save_news_data_into_database(databse_name, news_entries):
    with PostgreSqlDB(database=databse_name) as conn:

        db_api = NewsDatabaseAPI(conn, table_prefix="shownews_")

        for news in news_entries:
            db_api.store_a_rss_news_entry_to_db(news)


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

    with PostgreSqlDB(database="my_focus_news") as conn:
        db_api = NewsDatabaseAPI(conn, table_prefix="shownews_")

        rules_from_db = read_rules_from_db_connection(conn)

        # If rules have changed ==> update scores in DB
        if set(scraping_rules) != set(rules_from_db.values()):
            logging.info("ScrapingRules have changed. Remove previous rules from DB.")
            db_api.reset_scraping_rules_and_relations()
            logging.info("Save new ScrapingRules into DB.")
            # Only rule, keywords, tags. This does not set relationship with news_data
            save_scraping_rules_into_database("my_focus_news", scraping_rules)
            # read from db again in order to get rule_id
            rules_from_db = read_rules_from_db_connection(conn)
            news_from_db = _read_news_from_db(conn, db_api, scraping_rules)

            rule_id_map = {value: key for key, value in rules_from_db.items()}

            for news_id, news in news_from_db.items():
                for rule, score in news.rule_score_map.items():
                    rule_id = rule_id_map[rule]
                    db_api._setup_news_rule_relationship(news_id, rule_id, score)

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

    save_news_data_into_database(
        "my_focus_news", news_entries=target_news
    )

    logging.info(
        'Record %d news out of total %d news.' % (len(target_news), len(news_entries))
    )

    for news in target_news:
        print(repr(news))

    logging.info("Done. Elapsed time: %f seconds" % (timer() - start_time))


if __name__ == '__main__':
    main()
