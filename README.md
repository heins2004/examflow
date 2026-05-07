# ExamFlow - Online Exam System

ExamFlow is a powerful, creative, and multipurpose online examination system built with Django and MySQL-compatible databases. It features a polished UI, a robust exam engine, and a custom admin dashboard.

## Tech Stack
- Frontend: Bootstrap 5, Vanilla JS, Chart.js
- Backend: Python 3.10+, Django 4.2+
- Database: MySQL 8.x or TiDB Cloud with `mysqlclient` or `PyMySQL`

## Installation & Setup

1. **Clone or Download the Project**
2. **Create a Virtual Environment:**
   `python -m venv venv`
   `.\venv\Scripts\activate` (Windows)
3. **Install dependencies:**
   `pip install -r requirements.txt`
4. **Database Setup via XAMPP or TiDB Cloud:**
   - Open XAMPP Control Panel, start Apache and MySQL.
   - Go to phpMyAdmin and create a database named `examflow_db` with `utf8mb4_unicode_ci` collation.
   - In the project root, copy `.env.example` to `.env` and adjust the DB credentials if needed:
     ```
     SECRET_KEY='change-this-secret-key'
     DEBUG=True
     DB_ENGINE='mysql'
     DB_NAME='examflow_db'
     DB_USER='root'
     DB_PASSWORD=''  # Set this to your actual password if MySQL uses one
     DB_HOST='127.0.0.1'
     DB_PORT='3306'
     ```
   - For TiDB Cloud, use the connection values from the cluster connect dialog. If your TiDB setup requires TLS CA validation, also set:
     ```
     DB_SSL_MODE='VERIFY_IDENTITY'
     DB_SSL_CA_PATH='/absolute/path/to/ca.pem'
     ```
5. **Run Migrations:**
   `python manage.py makemigrations`
   `python manage.py migrate`
6. **Seed Initial Data (Admin & Sample Exams):**
   `python manage.py seed_data`
   *This creates an admin (`admin321` / `admin@$321`), a student (`student` / `student`), and sample questions.*
7. **Run the Server:**
   `python manage.py runserver`

## Render + TiDB Deployment

Use the included Render setup files to deploy this project publicly.

1. Push this repository to GitHub.
2. Create a TiDB Cloud cluster and database.
3. In TiDB Cloud, copy the MySQL connection values for host, port, database, username, and password.
4. On Render, create a new Web Service from your GitHub repo.
5. Render should use:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn examflow.wsgi:application`
6. Add these environment variables in Render:
   - `SECRET_KEY`: generate a strong random value
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: your Render hostname, or `*` if you want to keep it open
   - `CSRF_TRUSTED_ORIGINS`: your Render URL, for example `https://your-service.onrender.com`
   - `DB_ENGINE`: `mysql`
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: from TiDB
   - `DB_SSL_MODE`: `VERIFY_IDENTITY` when required by your TiDB cluster
   - `DB_SSL_CA_PATH`: path to the uploaded TiDB CA certificate if you use one
7. Deploy. The build script will collect static files, run migrations, and seed the default admin.

After the first successful deploy, log in with:
- Username: `admin321`
- Password: `admin@$321`

## GitHub Notes
- Commit `.env.example`, not `.env`.
- Do not commit `venv/`, `db.sqlite3`, generated `staticfiles/`, uploaded `media/` content, or Python cache folders.
- If you want sample screenshots in the repository, add them intentionally instead of committing the whole `media/` directory.

## Note for Windows Users
The project is configured for MySQL by default. If `mysqlclient` is not available, the project can still work with `PyMySQL` because [__init__.py](examflow/__init__.py) installs it as a MySQLdb-compatible backend.

## Screenshots
*(Add screenshots here)*
