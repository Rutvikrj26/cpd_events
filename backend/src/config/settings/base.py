"""
Django settings for CPD Events backend.

Base settings shared across all environments.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'common',
    'accounts',
    'events',
    'registrations',
    'certificates',
    'contacts',
    'integrations',
    'billing',
    'learning',
    'organizations',
    'feedback',
    'promo_codes',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_yasg',
    'corsheaders',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ... existing code ...


GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'dev-project')
GCP_LOCATION = os.environ.get('GCP_LOCATION', 'us-central1')
GCP_QUEUE_NAME = os.environ.get('GCP_QUEUE_NAME', 'default')
GCP_SA_EMAIL = os.environ.get('GCP_SA_EMAIL', 'service-account@example.com')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', '')  # Required for production

# GCP Emulators (for local development)
CLOUD_TASKS_EMULATOR_HOST = os.environ.get('CLOUD_TASKS_EMULATOR_HOST', '')
GCS_EMULATOR_HOST = os.environ.get('GCS_EMULATOR_HOST', '')

# Cloud Tasks Sync Mode
# When True, tasks execute synchronously instead of being pushed to Cloud Tasks queue.
# Useful for initial deployments or debugging. Set to False to enable async Cloud Tasks.
CLOUD_TASKS_SYNC = os.environ.get('CLOUD_TASKS_SYNC', 'true').lower() in ('true', '1', 'yes')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database - Override in environment-specific settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Encryption key for sensitive fields (generate new in production)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=')  # dev placeholder

# Site URL for generating absolute URLs
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

# =============================================================================
# Django REST Framework
# =============================================================================
from datetime import timedelta

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/min',
        'user': '10000/min',
        'auth': '100/hour',
    },
    # Rendering
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Exception handling
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    # Schema
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'uuid',
    'USER_ID_CLAIM': 'user_uuid',
}

# drf-yasg / Swagger Settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {'Bearer': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header'}},
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
}
SWAGGER_USE_COMPAT_RENDERERS = False

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]

# Zoom Integrations
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')
ZOOM_REDIRECT_URI = os.environ.get('ZOOM_REDIRECT_URI')
ZOOM_WEBHOOK_SECRET = os.environ.get('ZOOM_WEBHOOK_SECRET')

# =============================================================================
# Billing & Subscription Settings
# =============================================================================
# Stripe API Keys
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Billing configuration imported from common.config.billing
# These are re-exported here for backward compatibility with code that imports from settings
from common.config.billing import (
    PlatformFees,
    PricingConfig,
    StripePriceIds,
    DefaultPlan,
)

# Stripe Price IDs for each plan (set in Stripe Dashboard)
STRIPE_PRICE_IDS = StripePriceIds.as_dict()

# Platform fee for paid event registrations (percentage of transaction)
PLATFORM_FEE_PERCENT = PlatformFees.FEE_PERCENT

# Plan Pricing (in cents, for display purposes - actual pricing in Stripe)
BILLING_PRICES = {
    'attendee': PricingConfig.ATTENDEE,
    'starter': PricingConfig.STARTER_MONTHLY,
    'starter_annual': PricingConfig.STARTER_ANNUAL,
    'professional': PricingConfig.PROFESSIONAL_MONTHLY,
    'professional_annual': PricingConfig.PROFESSIONAL_ANNUAL,
    'premium': PricingConfig.PREMIUM_MONTHLY,
    'premium_annual': PricingConfig.PREMIUM_ANNUAL,
    'team': PricingConfig.TEAM_MONTHLY,
    'team_annual': PricingConfig.TEAM_ANNUAL,
    'enterprise': PricingConfig.ENTERPRISE,
    # Legacy plans
    'organizer': PricingConfig.ORGANIZER_MONTHLY,
    'organization': PricingConfig.ORGANIZATION_MONTHLY,
}

# Default plan for new organizers
BILLING_DEFAULT_PLAN = DefaultPlan.NAME

