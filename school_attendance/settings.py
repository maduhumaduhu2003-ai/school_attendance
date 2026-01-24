from pathlib import Path
import os
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# =================== ENVIRONMENT ===================
ENVIRONMENT = config('ENVIRONMENT', default='local')  # 'local' or 'render'

# =================== SECURITY ===================
SECRET_KEY = config('SECRET_KEY', default='unsafe-default-secret-key')
DEBUG = config('DEBUG', default=(ENVIRONMENT == 'local'), cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

# =================== DATABASE ===================
if ENVIRONMENT == 'render':
    DATABASES = {
        'default': {
            'ENGINE': config('PROD_DB_ENGINE', default='django.db.backends.postgresql'),
            'NAME': config('PROD_DB_NAME', default='render_db'),
            'USER': config('PROD_DB_USER', default='postgres'),
            'PASSWORD': config('PROD_DB_PASSWORD', default='postgres'),
            'HOST': config('PROD_DB_HOST', default='localhost'),
            'PORT': config('PROD_DB_PORT', default=5432, cast=int),
        }
    }
else:  # local
    DATABASES = {
        'default': {
            'ENGINE': config('LOCAL_DB_ENGINE', default='django.db.backends.sqlite3'),
            'NAME': config('LOCAL_DB_NAME', default=os.path.join(BASE_DIR, 'db.sqlite3')),
            'USER': config('LOCAL_DB_USER', default=''),
            'PASSWORD': config('LOCAL_DB_PASSWORD', default=''),
            'HOST': config('LOCAL_DB_HOST', default=''),
            'PORT': config('LOCAL_DB_PORT', default='', cast=str),
        }
    }

# =================== EMAIL ===================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.example.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# =================== AFRICASTALKING ===================
AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default='')
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default='')

# =================== AUTH & MEDIA ===================
AUTH_USER_MODEL = 'attendance_app.User'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/admin-dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =================== STATIC FILES ===================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# =================== INSTALLED APPS ===================
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
