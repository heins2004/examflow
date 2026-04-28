import pymysql

passwords = ['', 'root', 'password', '1234', '12345', '123456']

for p in passwords:
    try:
        conn = pymysql.connect(host='127.0.0.1', user='root', password=p)
        print(f"SUCCESS with password: '{p}'")
        conn.close()
        break
    except Exception as e:
        print(f"Failed with '{p}': {e}")
