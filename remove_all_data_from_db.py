"""Remove all data from the database specified by the settings in "scraper_config.py".
"""
# Local modules
from db_news_api import NewsDatabaseAPI
from db_operation_api.mydb import PostgreSqlDB
from scraper_config import NewsCollectorConfig


if __name__ == '__main__':

    db_config = {
        "db_host": NewsCollectorConfig.DB_HOST,
        "db_port": NewsCollectorConfig.DB_PORT,
        "db_user": NewsCollectorConfig.DB_USER,
        "db_password": NewsCollectorConfig.DB_PASSWORD,
        "database": NewsCollectorConfig.DB_NAME,
    }

    with PostgreSqlDB(**db_config) as conn:
        db_api = NewsDatabaseAPI(conn)
        db_api.remove_scraping_rules_and_relations()
        db_api.reset_news_data()
