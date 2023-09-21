"""
Django settings for speakybot project.

Generated by 'django-admin startproject' using Django 4.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import os

import dj_database_url

from pathlib import Path

from django.conf import settings
from environs import Env


env = Env()
env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    'DJ_SECRET_KEY', 'django-insecure-x0^82l@5%d8o*&_l@jn*x4_$p7z$@t$9e+-vxehkx=+0m)#q8#')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJ_DEBUG', True)

ALLOWED_HOSTS = env.list('DJ_ALLOWED_HOSTS', ['127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('DJ_CSRF_TRUSTED_ORIGINS', [])
TELEGRAM_TOKEN = env('TG_TOKEN')
# Application definition

BOT_MODE = env('BOT_MODE', 'polling')

LOG_LEVEL = env.int('LOG_LEVEL', 10)

TG_BOT_URL = env('BOT_UTL', 'https://google.com/')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/'
TG_SEND_MESSAGE_URL = settings.TELEGRAM_API_URL + 'sendMessage'

# YOOKASSA definition
# YOO_TOKEN = env('YOO_TOKEN', 'test_Ks28CdC0JlNMNJGi6yu3DQnYMyTasOQD001a9TMh3Wg')  # Дашин токен
# YOO_SHOP_ID = env('SHOP_ID', '322466')  # Дашин шоп id

YOO_TOKEN = env(
    'YOO_TOKEN', 'test_MC3lMB_QVPrNgwbvtTAYXMnBvPzc0Nez5-mzvCCchIk')  # Мой токен
YOO_SHOP_ID = env('SHOP_ID', '210134')  # Мой шоп id

INTERNAL_KEY = env('INTERNAL_KEY', 'qertywgbt4wef2d13fg4236j7k64jrydg')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # speakybot
    'user',
    'bot_parts',
    'templates',
    'product',
    'subscription',
    'payment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'speakybot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'admin_templates/')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'utils.context_processors.products',
            ],
        },
    },
]

WSGI_APPLICATION = 'speakybot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.parse(
        env('DJ_DB_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_DIR = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    STATIC_DIR,
]
STATIC_ROOT = './assets/'

MEDIA_URL = '/media/'
MEDIA_ROOT = env('MEDIA_ROOT', './media/')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
