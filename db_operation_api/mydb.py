# Standard libraries
import logging
# PyPI
import psycopg2

log_format = '[%(levelname)s] %(message)s\n'


class MyDBError(RuntimeError):
    pass


class MyDB(object):
    def __init__(self, db_host, db_user, db_password,
                 db_port, database, verbose):
        raise NotImplementedError("Base class 'MyDB' must not be instanciated.")

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        raise NotImplementedError("Derived classes must implement open().")

    def close(self):
        self.cursor.close()
        self._conn.close()
        self.cursor = None
        self._conn = None
        logging.debug("The database connection has been closed.")

    def execute_sql_command(self, query, *args):
        raise NotImplementedError("Derived classes must implement execute_sql_command().")

    def insert_values_into_table(self, table_name, args_map):
        place_holder = ', '.join('%s' for i in range(len(args_map)))
        field_names = ', '.join(key for key in args_map.keys())

        args = tuple(val for val in args_map.values())

        query = "INSERT INTO {} ({}) VALUES ({});".format(table_name, field_names, place_holder)
        self.execute_sql_command(query, *args)

    def update_table(self, table_name, args_map, condition_map):
        conditions = " AND ".join(
            "{} = %s".format(key) for key in condition_map.keys()
        )
        fields = ', '.join(
            "{} = %s".format(key) for key in args_map.keys()
        )
        args = (
            tuple(val for val in args_map.values()) +
            tuple(val for val in condition_map.values())
        )
        query = (
            "UPDATE {} SET {} WHERE {};".format(table_name, fields, conditions)
        )

        self.execute_sql_command(query, *args)

    def get_fields_by_conditions(self, table_name, field_list, condition_map=None):

        if condition_map:
            conditions = " WHERE " + " AND ".join(
                "{} = %s".format(key) for key in condition_map.keys()
            )
            args = (val for val in condition_map.values())
        else:
            conditions = ""
            args = ()

        fields = ', '.join(field_list)

        query = (
            "SELECT {} FROM {} {};"
            .format(fields, table_name, conditions)
        )

        rows = self.execute_sql_command(query, *args)
        return rows

    def db_already_exists(self, db_name):
        query = (
            "SELECT EXISTS("
            "    SELECT datname FROM pg_catalog.pg_database"
            "    WHERE lower(datname) = lower(%s)"
            ");"
        )

        rows = self.execute_sql_command(query, db_name)
        return rows[0][0]  # bool

    def table_already_exists(self, table_name):
        query = (
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_catalog.pg_class c"
            "  JOIN   pg_catalog.pg_namespace n ON n.oid = c.relnamespace"
            "  WHERE  n.nspname = 'public'"
            "  AND    c.relname = %s"
            "  AND    c.relkind = 'r'"
            ");"
        )

        rows = self.execute_sql_command(query, table_name)

        return rows[0][0]  # bool

    def reset_table(self, table_name):
        query = "DELETE FROM {};".format(table_name)
        self.execute_sql_command(query, table_name)


class PostgreSqlDB(MyDB):

    def __init__(self, db_host='localhost', db_user='dja1', db_password='_MY_DB_PASSWORD_',
                 db_port=5432, database='template1', verbose=False):

        self.config = {
            'host': db_host,
            'user': db_user,
            'password': db_password,
            'port': db_port,
            'database': database,
        }

        if verbose:
            log_level = logging.DEBUG
        else:
            log_level = logging.WARNING

        logging.basicConfig(level=log_level, format=log_format)

        self._conn = None
        self.cursor = None

    def open(self):
        if self._conn:
            # nested with blocks are forbidden
            raise MyDBError('Already connected to database.')
        else:
            self._conn = psycopg2.connect(**self.config)
            self._conn.autocommit = True
            self.cursor = self._conn.cursor()
            if not self.cursor:
                raise MyDBError('Fail to establish a databae cursor.')

            logging.debug("A database connection has been established.")

            return self

    def execute_sql_command(self, query, *args):

        self.cursor.execute(query, args)
        try:
            ret = self.cursor.fetchall()
        except psycopg2.ProgrammingError as e:
            if 'no results to fetch' in str(e):
                ret = None
            else:
                raise

        # self._conn.commit()
        return ret
