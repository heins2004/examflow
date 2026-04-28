import pymysql
import os

try:
    conn = pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='',
        database='examflow_db'
    )
    print("SUCCESS 127.0.0.1")
    conn.close()
except Exception as e:
    print(f"ERROR 127.0.0.1: {e}")

try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='examflow_db'
    )
    print("SUCCESS localhost")
    conn.close()
except Exception as e:
    print(f"ERROR localhost: {e}")
