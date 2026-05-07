try:
    import MySQLdb  # Prefer mysqlclient when available.
except ImportError:
    MySQLdb = None

if MySQLdb is None:
    try:
        import pymysql
    except ImportError:
        pymysql = None

    if pymysql is not None:
        pymysql.install_as_MySQLdb()

        import MySQLdb

        MySQLdb.version_info = (2, 2, 1, 'final', 0)
