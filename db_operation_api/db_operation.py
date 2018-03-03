# Standard libraries
import logging
import random
from datetime import datetime
# PyPI
import pytz
# Local modules
from mydb import PostgreSqlDB


# duplicate in news_to_db.py
def insert_values_to_table(conn, table_name, args_map):

    place_holder = ', '.join('%s' for i in range(len(args_map)))
    field_names = ', '.join(key for key in args_map.keys())

    args = [val for val in args_map.values()]

    query = "INSERT INTO {} ({}) VALUES ({});".format(table_name, field_names, place_holder)
    conn.execute_sql_command(query, *args)


def create_database(db_name, conn):
    if not conn.db_already_exists(db_name):
        conn.execute_sql_command("CREATE DATABASE {};".format(db_name))
    else:
        logging.info('Database {} already exists.'.format(db_name))


def drop_database_if_exists(db_name, conn):
    conn.execute_sql_command("DROP DATABASE IF EXISTS {};".format(db_name))


def initialize_database(conn, db_name):

    drop_database_if_exists(db_name, conn)

    logging.info("Initializing database '{}' and tables needed...".format(db_name))

    create_database(db_name, conn)
    _create_testing_tables(conn)


def _create_testing_tables(conn, table_name):
    """
    create database with name db_name
    Do nothing if it already exists
    """
    query = (
        "CREATE TABLE {}"
        "("
        "   id serial PRIMARY KEY NOT NULL,"
        "   title CHAR(50) NOT NULL,"
        "   url CHAR(50) NOT NULL,"
        "   time INT NOT NULL,"
        "   score REAL NOT NULL DEFAULT '0.00',"
        "   note TEXT"
        ");"
    )

    _create_table(conn, table_name, query)


def _create_table(conn, table_name, query, *args):

    if conn.table_already_exists(table_name):
        logging.info("Table '{}' already exists. Skip it.".format(table_name))
        return False
    else:
        query = query.format(table_name)
        conn.execute_sql_command(query, *args)
        return True


class _PgsqlTableCreator(object):

    def __init__(self, conn):
        self.conn = conn

    def _create_main_table(self, table_name):

        query = (
            "CREATE TABLE {}"
            "("
            "   id serial PRIMARY KEY NOT NULL,"
            "   title CHAR(50) NOT NULL,"
            "   url CHAR(50) NOT NULL,"
            "   time INT NOT NULL,"
            "   score REAL NOT NULL DEFAULT '0.00',"
            "   note TEXT"
            ");"
        )

        self._create_table(table_name, query)


if __name__ == '__main__':

    test_name = str(random.randint(1, 100000))

    with PostgreSqlDB(database="my_focus_news") as conn:
        insert_values_to_table(conn, 'shownews_newscategory', {'name': test_name})

        test_time = datetime(2017, 7, 4, 12, 30, 51, tzinfo=pytz.UTC)
        text_args = {
            'title': test_name,
            'url': 'http://abcdefg.com/' + test_name,
            'time': test_time,
            'read_time': test_time,
            'creation_time': test_time,
            'last_modified_time': test_time
        }
        normal_args = {}
        insert_values_to_table(conn, 'shownews_newsdata', text_args)

        args = {'name': test_name, 'active': False}
        insert_values_to_table(conn, 'shownews_scrapingrule', args)

        args = {'name': test_name, 'to_include': True}
        insert_values_to_table(conn, 'shownews_newskeyword', args)

        # args = {'scrapingrule_id': random.randint(1, 10), 'newskeyword_id': random.randint(1, 10)}
        # insert_values_to_table(conn, 'shownews_scrapingrule_keywords', args)
