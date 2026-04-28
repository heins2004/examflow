import pymysql

for port in [3306, 3307, 3308, 3309]:
    for p in ['', 'root']:
        try:
            conn = pymysql.connect(host='127.0.0.1', port=port, user='root', password=p)
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION(), @@version_comment")
            version, comment = cursor.fetchone()
            print(f"SUCCESS port {port} with password '{p}' -> {version} ({comment})")
            conn.close()
        except Exception as e:
            pass
