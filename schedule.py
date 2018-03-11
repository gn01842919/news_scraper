"""Schedule when to collect news (by collect_news_to_db.py).

If execute directly, will collect news immediately, and then periodically collects news.

Example:
    python schedule.py

"""
# PyPI
from apscheduler.schedulers.blocking import BlockingScheduler
# Local modules
from collect_news_to_db import collect_news_by_rules_and_save_to_db


def schedule_once_an_hour():
    """Run collect_news_by_rules_and_save_to_db() once an hour.
    """
    scheduler = BlockingScheduler()
    scheduler.add_job(collect_news_by_rules_and_save_to_db, 'interval', hours=1)
    scheduler.start()


if __name__ == "__main__":
    # Runs once immediately.
    collect_news_by_rules_and_save_to_db()

    # Then runs periodically.
    schedule_once_an_hour()
