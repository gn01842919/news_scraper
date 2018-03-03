import unittest
from database import MyPostgreSqlDB
import psycopg2
import mysql.connector
import time


class MyPostgreSqlDBBasicTest(unittest.TestCase):

    def test_db_open_and_close(self):
        conn = MyPostgreSqlDB(database=None, verbose=False).open()
        self.assertIsInstance(conn, MyPostgreSqlDB)
        self.assertIsInstance(conn.cursor, mysql.connector.cursor.MySQLCursor)

        # Test invalid database name
        with self.assertRaises(mysql.connector.errors.ProgrammingError):
            MyPostgreSqlDB(database='not_exist_db').open()

        # Open database twice
        with self.assertRaises(RuntimeError):
            conn.open()

        conn.close()
        self.assertIsNone(conn._conn)
        self.assertIsNone(conn.cursor)

    def test_with_statement(self):
        db = MyPostgreSqlDB(database=None, verbose=False)

        with db as conn:
            self.assertIsInstance(conn, MyPostgreSqlDB)
            self.assertIsInstance(conn.cursor, mysql.connector.cursor.MySQLCursor)

        self.assertIsNone(conn._conn)
        self.assertIsNone(conn.cursor)

    # def test_db_already_exists(self):
    #     with MyPostgreSqlDB(database=None, verbose=False) as conn:
    #         self.assertTrue(conn.db_already_exists('INFORMATION_SCHEMA'))
    #         self.assertTrue(conn.db_already_exists('mysql'))
    #         self.assertTrue(conn.db_already_exists('PERFORMANCE_SCHEMA'))
    #         self.assertFalse(conn.db_already_exists('no_such_database_name'))

    def test_invalid_command(self):
        with MyPostgreSqlDB(database=None, verbose=False) as conn:
            with self.assertRaises(mysql.connector.errors.ProgrammingError):
                conn.execute_sql_command("invalid command;")

    def test_execute_sql_command_with_no_args(self):
        with MyPostgreSqlDB(database=None, verbose=False) as conn:
            rv = conn.execute_sql_command("SHOW DATABASES;")
            self.assertIn(('mysql',), rv)
            self.assertIn(('performance_schema',), rv)
            self.assertIn(('information_schema',), rv)


class MyPostgreSqlDBOperationsTest(unittest.TestCase):

    def setUp(self):
        self.tmp_db_name = 'my_unittest_temp_db'
        self.tmp_table_name = 'test_table'
        self.conn = MyPostgreSqlDB(database=None, verbose=False).open()

    def tearDown(self):
        try:
            self.conn.cursor.execute("DROP DATABASE IF EXISTS {};".format(self.tmp_db_name))
        except mysql.connector.errors.DatabaseError:
            # the database does not exist
            pass
        self.conn._conn.close()
        self.conn.cursor.close()

    def create_the_testing_database(self):
        self.conn.execute_sql_command("CREATE DATABASE {};".format(self.tmp_db_name))
        self.conn.execute_sql_command("USE {};".format(self.tmp_db_name))

    def drop_the_testing_database(self):
        self.conn.execute_sql_command("DROP DATABASE {};".format(self.tmp_db_name))

    def create_the_testing_table(self):
        query = ("CREATE TABLE {}"
                 "("
                 "  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,"
                 "  title VARCHAR(100) NOT NULL,"
                 "  url VARCHAR(100) NOT NULL,"
                 "  time INT UNSIGNED NOT NULL,"
                 "  score FLOAT NOT NULL DEFAULT '0.00',"
                 "  note TEXT"
                 ");".format(self.tmp_table_name)
                 )

        self.conn.execute_sql_command(query)

    def drop_the_testing_table(self):
        self.conn.execute_sql_command("DROP TABLE {}".format(self.tmp_table_name))

    def test_db_operations(self):
        self.assertFalse(self.conn.db_already_exists(self.tmp_db_name))

        self.create_the_testing_database()

        self.assertTrue(self.conn.db_already_exists(self.tmp_db_name))

        self.drop_the_testing_database()

        self.assertFalse(self.conn.db_already_exists(self.tmp_db_name))

    def test_table_operations(self):
        self.create_the_testing_database()

        self.assertFalse(self.conn.table_already_exists(self.tmp_table_name))

        self.create_the_testing_table()

        self.assertTrue(self.conn.table_already_exists(self.tmp_table_name))

        self.drop_the_testing_table()

        self.assertFalse(self.conn.table_already_exists(self.tmp_table_name))

        self.drop_the_testing_database()

    def test_execute_sql_command_with_one_arg(self):
        self.create_the_testing_database()
        self.create_the_testing_table()

        insert_query = ("INSERT INTO {}"
                        "(title, url, time, note)"
                        "VALUES"
                        "('one_arg_query', 'http://url', %s, 'Some notes.');"
                        .format(self.tmp_table_name)
                        )

        self.conn.execute_sql_command(insert_query, time.time())
        query = 'SELECT * FROM {} WHERE id = %s;'.format(self.tmp_table_name)
        rows = self.conn.execute_sql_command(query, 1)

        self.assertEqual(len(rows), 1)

        self.drop_the_testing_database()

    def test_execute_sql_command_with_multiple_args(self):
        self.create_the_testing_database()
        self.create_the_testing_table()

        insert_query = ("INSERT INTO {}"
                        "(title, url, time, score, note)"
                        "VALUES"
                        "(%s, %s, {}, {}, %s);"
                        .format(self.tmp_table_name, int(time.time()), 0.0)
                        )

        self.conn.execute_sql_command(insert_query, '3_args_query', 'http://localhost:8080', 'Some other notes.')

        query = 'SELECT * FROM {} WHERE id = %s AND title = %s AND score = %s;'.format(self.tmp_table_name)
        rows = self.conn.execute_sql_command(query, 1, '3_args_query', 0.0)

        self.assertEqual(len(rows), 1)

        self.drop_the_testing_database()


if __name__ == '__main__':
    unittest.main()
