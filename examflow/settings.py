import importlib.util
import os
from pathlib import Path

try:
    from decouple import config
except ImportError:
    def config(name, default=None, cast=None):
        value = os.getenv(name, default)
        if cast is bool:
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}
        if cast and value is not None:
            return cast(value)
        return value

BASE_DIR = Path(__file__).resolve().parent.parent


def env_config(name, default=None, cast=None, legacy_names=None):
    names = [name, *(legacy_names or [])]
    for env_name in names:
        try:
            if cast is None:
                value = config(env_name, default=None)
            else:
                value = config(env_name, default=None, cast=cast)
        except Exception:
            continue
        if value not in (None, ""):
            return value
    return default

SECRET_KEY = env_config('SECRET_KEY', default='unsafe-secret-key')

DEBUG = env_config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.accounts',
    'apps.exams',
    'apps.dashboard',
]

if importlib.util.find_spec('crispy_forms') and importlib.util.find_spec('crispy_bootstrap5'):
    INSTALLED_APPS += [
        'crispy_forms',
        'crispy_bootstrap5',
    ]
    CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
    CRISPY_TEMPLATE_PACK = "bootstrap5"

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'examflow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'examflow.wsgi.application'

db_engine = str(env_config('DB_ENGINE', default='mysql', legacy_names=['EXAMFLOW_DB_ENGINE'])).strip().lower()

if db_engine == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env_config('DB_NAME', default='examflow_db', legacy_names=['EXAMFLOW_DB_NAME']),
            'USER': env_config('DB_USER', default='root', legacy_names=['EXAMFLOW_DB_USER']),
            'PASSWORD': env_config('DB_PASSWORD', default='', legacy_names=['EXAMFLOW_DB_PASSWORD']),
            'HOST': env_config('DB_HOST', default='127.0.0.1', legacy_names=['EXAMFLOW_DB_HOST']),
            'PORT': env_config('DB_PORT', default='3306', legacy_names=['EXAMFLOW_DB_PORT']),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
