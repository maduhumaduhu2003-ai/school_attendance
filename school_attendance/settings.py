from pathlib import Path
import os
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# =================== SECURITY ===================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,.up.railway.app',
    cast=Csv()
)

# =================== DATABASE (RAILWAY ONLY) ===================
DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
    )
}

# =================== EMAIL ===================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# =================== AFRICASTALKING ===================
AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME')
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY')

# =================== AUTH ===================
AUTH_USER_MODEL = 'attendance_app.User'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/admin-dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# =================== MEDIA ===================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =================== STATIC ===================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# =================== APPS ===================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'attendance_app',
    'rest_framework',
    'widget_tweaks',
]

# =================== MIDDLEWARE ===================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =================== TEMPLATES ===================
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
                'attendance_app.context_processors.school_and_profile',
            ],
        },
    },
]

ROOT_URLCONF = 'school_attendance.urls'
WSGI_APPLICATION = 'school_attendance.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
