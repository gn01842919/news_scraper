"""This module abstracts some common SQL operations.

Example:
    with PostgreSqlDB(**db_config) as conn:
        rows = conn.get_fields_by_conditions(
            "table_name",
            ("title", "content", "url"),
            {"id": some_obj.id}
        )
    print(rows)

Attributes:
    log_format (str): log format for the "logging" module

"""

# Standard libraries
import logging
# PyPI
import psycopg2

log_format = "[%(levelname)s] %(message)s\n"


class MyDBError(RuntimeError):
    pass


class MyDB(object):
    """Base class for database connectors (such as PostgreSqlDB).

    This should not be instanciated directly.
    Please inherit it and overide at least the following methods:
        __init__()
        open()
        execute_sql_command()

    """

    def __init__(self, db_host, db_user, db_password,
                 db_port, database, verbose):
        """Must be overided by derived classes."""
        raise NotImplementedError("Base class 'MyDB' must not be instanciated.")

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        """Must be overided by derived classes."""
        raise NotImplementedError("Derived classes must implement open().")

    def close(self):
        """Close the database connection."""
        self.cursor.close()
        self._conn.close()
        self.cursor = None
        self._conn = None
        logging.debug("The database connection has been closed.")

    def execute_sql_command(self, query, *args):
        """Must be overided by derived classes."""
        raise NotImplementedError("Derived classes must implement execute_sql_command().")

    def insert_values_into_table(self, table_name, args_map):
        """Insert values into a table in the database.

        Args:
            table_name (str): Name of the table to insert values
            args_map (dict): <key, value> pairs to insert to the talbe.

        """
        place_holder = ", ".join("%s" for i in range(len(args_map)))
        field_names = ", ".join(key for key in args_map.keys())

        args = tuple(val for val in args_map.values())

        query = "INSERT INTO {} ({}) VALUES ({});".format(table_name, field_names, place_holder)
        self.execute_sql_command(query, *args)

    def update_table(self, table_name, args_map, condition_map):
        """Update table entries into the database.

        Args:
            table_name (str): Name of the table to update values
            args_map (dict): <key, value> pairs to update to the table.
            condition_map (dict, optional): <key, value> pairs of the conditions
                used in the "WHERE" statement of the SQL query.

        """
        conditions = " AND ".join(
            "{} = %s".format(key) for key in condition_map.keys()
        )
        fields = ", ".join(
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

    def reset_table(self, table_name):
        """Delete all data inside a table.

        Note that this will NOT delete the table itself.

        Args:
            table_name (str): Name of the table to reset

        """
        query = "DELETE FROM {};".format(table_name)
        self.execute_sql_command(query, table_name)

    def table_already_exists(self, table_name):
        """Check whether a table exists in the database.

        Args:
            table_name (str): Name of the table to check

        Returns:
            bool: True if the table already exists. False otherwise.

        """
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

    def db_already_exists(self, db_name):
        """Check whether a database exists in the database.

        Args:
            db_name (str): Name of the database to check

        Returns:
            bool: True if the database already exists. False otherwise.

        """
        query = (
            "SELECT EXISTS("
            "    SELECT datname FROM pg_catalog.pg_database"
            "    WHERE lower(datname) = lower(%s)"
            ");"
        )

        rows = self.execute_sql_command(query, db_name)
        return rows[0][0]  # bool

    def get_fields_by_conditions(self, table_name, field_list, condition_map=None):
        """Get values in the database specified by the filed list.

        This is encapsulates the "SELECT {} FROM {} WHERE {};" SQL queries.

        Args:
            table_name (str): Name of the database to get valuse
            field_list (list(str)): Fields to get values
            condition_map (dict, optional): <key, value> pairs of the conditions
                used in the "WHERE" statement of the SQL query.

        Returns:
            list(tuple): All rows of the query result.

        """
        if condition_map:
            conditions = " WHERE " + " AND ".join(
                "{} = %s".format(key) for key in condition_map.keys()
            )
            args = (val for val in condition_map.values())
        else:
            conditions = ""
            args = ()

        fields = ", ".join(field_list)

        query = (
            "SELECT {} FROM {} {};"
            .format(fields, table_name, conditions)
        )

        rows = self.execute_sql_command(query, *args)
        return rows


class PostgreSqlDB(MyDB):
    """APIs for common operations to a PostgreSQL database.

    An instance acts like the combination of a datbase connection and a database cursor.

    Note that it is recommended to use this class with the "with" statement,
    which will call self.open() implicitly.

    Attributes:
        db_host (str): Hostname of the database.
        db_user (str): Username of the database.
        db_password (str): Username of the database.
        db_port (int, optional): Port of the database. Defaults to 5432.
        database (str, optional): The database to use. Defaults to "template1"
        verbose (bool, optional): Whether to show debugging information.

    """

    def __init__(self, db_host, db_user, db_password,
                 db_port=5432, database="template1", verbose=False):

        self.config = {
            "host": db_host,
            "user": db_user,
            "password": db_password,
            "database": database,
            "port": db_port,
        }

        if verbose:
            log_level = logging.DEBUG
        else:
            log_level = logging.WARNING

        logging.basicConfig(level=log_level, format=log_format)

        self._conn = None
        self.cursor = None

    def open(self):
        """Opens a database connection.

        This initializes self._conn by calling psycopg2.connect()

        Returns:
            self

        Raises:
            MyDBError:
                1. If there the connection has been opened.
                2. If fails to establish a databae cursor.

        """
        if self._conn:
            # nested with blocks are forbidden
            raise MyDBError("Already connected to database.")
        else:
            self._conn = psycopg2.connect(**self.config)
            self._conn.autocommit = True
            self.cursor = self._conn.cursor()
            if not self.cursor:
                raise MyDBError("Fail to establish a databae cursor.")

            logging.debug("A database connection has been established.")

            return self

    def execute_sql_command(self, query, *args):
        """Executes a SQL command.

        This actualy pass the arguments to psycopg2.cursor.execute(query, args).

        Args:
            query (str): The SQL query to execute.
                Variables are specified by positional (%s) placeholders.
            *args: Variables specified by %s placeholders in the "query" argument.

        Returns:
            list(tuple): All rows of the query result.

        Raises:
            psycopg2.ProgrammingError: If there are any error in the query.

        """
        self.cursor.execute(query, args)
        try:
            ret = self.cursor.fetchall()
        except psycopg2.ProgrammingError as e:
            if "no results to fetch" in str(e):
                ret = None
            else:
                raise

        # self._conn.commit()
        return ret
