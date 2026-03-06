"""
Responsible for: managing MySQL connections.
"""

import mysql.connector
from mysql.connector.connection import MySQLConnection
from contextlib import contextmanager


# Connection parameters — move to .env / config in production
_DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'root',
    'database': 'heritage_monitor',
}


class DBConnection:
    """
    Provides MySQL connections.

    Use as a context manager to ensure the connection is always closed:

        conn_mgr = DBConnection()
        with conn_mgr.get() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(...)
    """

    def __init__(self, config: dict | None = None):
        self._config = config or _DB_CONFIG

    @contextmanager
    def get(self):
        """
        Yield an open MySQLConnection and close it automatically.

        Usage:
            with db.get() as conn:
                ...
        """
        conn: MySQLConnection = mysql.connector.connect(**self._config)
        try:
            yield conn
        finally:
            conn.close()

    def raw(self) -> MySQLConnection:
        """
        Return a raw connection for callers that manage lifecycle themselves.
        Caller is responsible for calling .close().
        """
        return mysql.connector.connect(**self._config)