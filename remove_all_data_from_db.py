"""Remove all data from the database created by ``news_scraper``".

Example:
    This module can be executed directly:

    .. code-block:: console

        $ python remove_all_data_from_db.py

"""
# Local modules
from db_news_api import NewsDatabaseAPI
from db_operation_api.mydb import get_database
from settings import DATABASE_CONFIG


def main():
    """Remove all data created by ``news_scraper``.
    """

    with get_database(DATABASE_CONFIG) as conn:
        db_api = NewsDatabaseAPI(conn)
        db_api.remove_all_rules_and_relations()
        db_api.reset_news_data()


if __name__ == '__main__':
    main()
