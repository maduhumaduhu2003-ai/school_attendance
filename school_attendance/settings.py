from pathlib import Path
import os
from decouple import config, Csv
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =================== ENVIRONMENT ===================
# 'local' or 'render'
#ENVIRONMENT = config('ENVIRONMENT', default='local')

# =================== SECURITY ===================
#SECRET_KEY = config('SECRET_KEY', default='unsafe-default-secret-key')
#DEBUG = config('DEBUG', default=(ENVIRONMENT == 'local'), cast=bool)
#ALLOWED_HOSTS = config(
#    'ALLOWED_HOSTS',
#    default='localhost,127.0.0.1,.onrender.com',
 #   cast=Csv()
#)

# ===================RAIL WAY SECURITY ===================
#SECRET_KEY = os.getenv('SECRET_KEY', 'unsafe-default-secret-key')
#DEBUG = os.getenv('DEBUG', 'True') == 'True'  # Convert string to boolean
#ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
ALLOWED_HOSTS=["*"]

# =================== DATABASE ===================
#if ENVIRONMENT == 'render':
   # DATABASES = {
   #     'default': {
    #        'ENGINE': config('PROD_DB_ENGINE', default='django.db.backends.postgresql'),
    #        'NAME': config('PROD_DB_NAME', default='render_db'),
     #       'USER': config('PROD_DB_USER', default='postgres'),
    #        'PASSWORD': config('PROD_DB_PASSWORD', default='postgres'),
    #        'HOST': config('PROD_DB_HOST', default='localhost'),
     #       'PORT': config('PROD_DB_PORT', default=5432, cast=int),
   #     }
 #   }
#else:  # local
   # DATABASES = {
     #   'default': {
     #       'ENGINE': config('LOCAL_DB_ENGINE', default='django.db.backends.sqlite3'),
     #       'NAME': config('LOCAL_DB_NAME', default=os.path.join(BASE_DIR, 'db.sqlite3')),
     #       'USER': config('LOCAL_DB_USER', default=''),
     #       'PASSWORD': config('LOCAL_DB_PASSWORD', default=''),
     #       'HOST': config('LOCAL_DB_HOST', default=''),
     #       'PORT': config('LOCAL_DB_PORT', default='', cast=str),
 #       }
 #   }
 
 
DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
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
# Use decouple for local, environment variables for production
AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default=os.getenv("AFRICASTALKING_USERNAME", ""))
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default=os.getenv("AFRICASTALKING_API_KEY", ""))
AFRICASTALKING_SENDER_ID = config('SENDER_ID', default=os.getenv("SENDER_ID", "School_SMS"))

# Optional: sanity check
if not AFRICASTALKING_USERNAME or not AFRICASTALKING_API_KEY:
    print("Warning: AfricasTalking credentials not set!")

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
