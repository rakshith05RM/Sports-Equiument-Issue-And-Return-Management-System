"""
Centralized MySQL database connectivity using PyMySQL.

Every route imports get_db_connection() from this module instead of
opening its own connection, so credentials are configured in one place.
"""

import pymysql
import pymysql.cursors
from config import Config


def get_db_connection():
    """
    Returns a new PyMySQL connection using DictCursor, so query results
    behave like a list of dictionaries (row['column_name']) instead of tuples.
    """
    connection = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,  # we control commits explicitly (important for transactions)
    )
    return connection
