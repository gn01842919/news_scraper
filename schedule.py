"""
"""
# PyPI
from apscheduler.schedulers.blocking import BlockingScheduler
# Local modules
from collect_news_to_db import collect_news_by_rules_and_save_to_db


def scraper_schedule():
    scheduler = BlockingScheduler()
    scheduler.add_job(collect_news_by_rules_and_save_to_db, 'interval', hours=1)
    scheduler.start()


if __name__ == "__main__":
    # Runs once immediately
    collect_news_by_rules_and_save_to_db()

    # Then runs periodically
    scraper_schedule()
