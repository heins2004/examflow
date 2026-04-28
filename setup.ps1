$ErrorActionPreference = "Stop"
cd c:\xampp\htdocs\examflow
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
django-admin startproject examflow .
New-Item -ItemType Directory -Force -Path apps
New-Item -ItemType Directory -Force -Path apps\accounts
New-Item -ItemType Directory -Force -Path apps\exams
New-Item -ItemType Directory -Force -Path apps\dashboard
New-Item -ItemType File -Force -Path apps\__init__.py
python manage.py startapp accounts apps\accounts
python manage.py startapp exams apps\exams
python manage.py startapp dashboard apps\dashboard
New-Item -ItemType Directory -Force -Path templates
New-Item -ItemType Directory -Force -Path templates\accounts
New-Item -ItemType Directory -Force -Path templates\exams
New-Item -ItemType Directory -Force -Path templates\dashboard
New-Item -ItemType Directory -Force -Path static
New-Item -ItemType Directory -Force -Path static\css
New-Item -ItemType Directory -Force -Path static\js
New-Item -ItemType Directory -Force -Path static\images
New-Item -ItemType Directory -Force -Path media
