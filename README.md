# ExamFlow - Online Exam System

ExamFlow is a powerful, creative, and multipurpose online examination system built with Django and MySQL through XAMPP/phpMyAdmin. It features a polished UI, a robust exam engine, and a custom admin dashboard.

## Tech Stack
- Frontend: Bootstrap 5, Vanilla JS, Chart.js
- Backend: Python 3.10+, Django 4.2+
- Database: MySQL 8.x (via XAMPP/phpMyAdmin) with `mysqlclient` or `PyMySQL`

## Installation & Setup

1. **Clone or Download the Project**
2. **Create a Virtual Environment:**
   `python -m venv venv`
   `.\venv\Scripts\activate` (Windows)
3. **Install dependencies:**
   `pip install -r requirements.txt`
4. **Database Setup via XAMPP:**
   - Open XAMPP Control Panel, start Apache and MySQL.
   - Go to phpMyAdmin and create a database named `examflow_db` with `utf8mb4_unicode_ci` collation.
   - In the project root, copy `.env.example` to `.env` and adjust the DB credentials if needed:
     ```
     DB_ENGINE='mysql'
     DB_NAME='examflow_db'
     DB_USER='root'
     DB_PASSWORD=''  # Set this to your actual password if MySQL uses one
     DB_HOST='127.0.0.1'
     DB_PORT='3306'
     ```
5. **Run Migrations:**
   `python manage.py makemigrations`
   `python manage.py migrate`
6. **Seed Initial Data (Admin & Sample Exams):**
   `python manage.py seed_data`
   *This creates an admin (admin/admin), a student (student/student), and sample questions.*
7. **Run the Server:**
   `python manage.py runserver`

## GitHub Notes
- Commit `.env.example`, not `.env`.
- Do not commit `venv/`, `db.sqlite3`, generated `staticfiles/`, uploaded `media/` content, or Python cache folders.
- If you want sample screenshots in the repository, add them intentionally instead of committing the whole `media/` directory.

## Note for Windows Users
The project is configured for MySQL by default. If `mysqlclient` is not available, the project can still work with `PyMySQL` because [__init__.py](examflow/__init__.py) installs it as a MySQLdb-compatible backend.

## Screenshots
*(Add screenshots here)*
