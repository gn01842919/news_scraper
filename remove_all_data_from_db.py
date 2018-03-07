from db_news_api import NewsDatabaseAPI
from db_operation_api.mydb import PostgreSqlDB


if __name__ == '__main__':
    with PostgreSqlDB(database="my_focus_news") as conn:
        db_api = NewsDatabaseAPI(conn, table_prefix="shownews_")
        db_api.remove_scraping_rules_and_relations()
        db_api.reset_news_data()
