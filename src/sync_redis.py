"""
Script pour forcer la synchronisation Redis au démarrage
"""

import sys
import os
import time
import mysql.connector

from stocks.commands.write_stock import _populate_redis_from_mysql
from db import get_redis_conn, get_mysql_conn


def check_db_connection():
    """Check DB connection with 15 retries"""
    for i in range(15):
        try:
            mysql_conn = get_mysql_conn()
            mysql_conn.ping()
            mysql_conn.close()

            redis_conn = get_redis_conn()
            redis_conn.ping()
            return True
        except Exception as e:
            print(f"DB check {i + 1}/15 failed: {e}")
            if i < 14:
                time.sleep(2)
    return False


def sync_redis_with_mysql():
    """Force la synchronisation complète de Redis avec MySQL"""
    if not check_db_connection():
        print("DB connection failed")
        sys.exit(1)

    try:
        r = get_redis_conn()
        r.flushdb()
        _populate_redis_from_mysql(r)
        print("Redis sync done")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)