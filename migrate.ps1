$ErrorActionPreference = "Stop"
cd c:\xampp\htdocs\examflow
.\venv\Scripts\activate
python -c "import pymysql; conn = pymysql.connect(host='127.0.0.1', user='root', password=''); cursor = conn.cursor(); cursor.execute('CREATE DATABASE IF NOT EXISTS examflow_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'); cursor.close(); conn.close()"
python manage.py makemigrations
python manage.py migrate
