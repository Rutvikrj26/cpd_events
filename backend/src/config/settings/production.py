"""Production settings."""

import os
import logging

from .base import *

# =============================================================================
# Sentry Error Tracking
# =============================================================================

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SENTRY_DSN = os.environ.get("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "production")


def _sanitize_sentry_event(event, hint):
    """
    Remove sensitive data from Sentry events before sending.
    """
    # Remove authorization headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        if "Authorization" in headers:
            headers["Authorization"] = "[Filtered]"
        if "Cookie" in headers:
            headers["Cookie"] = "[Filtered]"

    # Remove sensitive POST data
    if "request" in event and "data" in event["request"]:
        sensitive_keys = ["password", "token", "secret", "api_key", "credit_card", "stripe_"]
        data = event["request"]["data"]
        if isinstance(data, dict):
            for key in list(data.keys()):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    data[key] = "[Filtered]"

    return event


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR,  # Send errors as events
            ),
        ],
        # Performance monitoring
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% of transactions for profiling
        # Send PII (Personally Identifiable Information)?
        send_default_pii=False,  # Don't send user IPs, cookies by default
        # Environment
        environment=SENTRY_ENVIRONMENT,
        # Release tracking (set from CI/CD via environment variable)
        release=os.environ.get("GIT_COMMIT_SHA", "0.1.0"),
        # Error sampling
        sample_rate=1.0,  # Capture 100% of errors
        # Before send hook (sanitize sensitive data)
        before_send=_sanitize_sentry_event,
    )

    # Log successful initialization
    logging.getLogger("config.settings").info(f"Sentry initialized for environment: {SENTRY_ENVIRONMENT}")
else:
    logging.getLogger("config.settings").warning("SENTRY_DSN not configured - error tracking disabled")


DEBUG = False

# Security settings
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# HTTPS/Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}

# Cache configuration (Redis)
# Django 4.0+ has built-in Redis cache backend
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "KEY_PREFIX": "cpd_events",
        "TIMEOUT": 300,  # 5 minutes default timeout
    }
}

# Session configuration (use cache for sessions)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# =============================================================================
# Email Configuration (SMTP provider)
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("SMTP_SERVER") or os.environ.get("MAILGUN_SMTP_SERVER", "smtp.mailgun.org")
EMAIL_PORT = int(os.environ.get("SMTP_PORT") or os.environ.get("MAILGUN_SMTP_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("SMTP_LOGIN") or os.environ.get("MAILGUN_SMTP_LOGIN")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD") or os.environ.get("MAILGUN_SMTP_PASSWORD")
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "info@accredit.store")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "server@accredit.store")

# SMTP provider API (optional, for advanced features)
SMTP_API_KEY = os.environ.get("SMTP_API_KEY") or os.environ.get("MAILGUN_API_KEY")
SMTP_DOMAIN = os.environ.get("SMTP_DOMAIN") or os.environ.get("MAILGUN_DOMAIN")
SMTP_API_BASE_URL = os.environ.get("SMTP_API_BASE_URL") or os.environ.get("MAILGUN_API_BASE_URL", "https://api.mailgun.net/v3")

# CORS Settings
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = True

# Static files (CSS, JavaScript, Images)
# Use Google Cloud Storage or your preferred static files storage
STATIC_URL = os.environ.get("STATIC_URL", "/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / "mediafiles"

# =============================================================================
# Logging Configuration (Structured JSON Logging)
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",  # Changed from 'verbose' to 'json'
            "level": "INFO",
        },
        "console_errors": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "ERROR",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
            "formatter": "verbose",  # Email uses readable format
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console_errors", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console_errors", "mail_admins"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.environ.get("DB_LOG_LEVEL", "WARNING"),  # Set to DEBUG to see queries
            "propagate": False,
        },
        # App-specific loggers
        "accounts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "events": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "registrations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "certificates": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "billing": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "learning": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "integrations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Admin emails (for error notifications)
ADMINS = [
    ("Admin", os.environ.get("ADMIN_EMAIL", "info@accredit.store")),
]
MANAGERS = ADMINS

# =============================================================================
# Rate Limiting (django-ratelimit)
# =============================================================================
# Rate limits are also enforced at the DRF throttle level (see base.py REST_FRAMEWORK settings)
# django-ratelimit provides additional granular control for specific endpoints

# Cache backend for rate limiting (uses default Redis cache)
RATELIMIT_USE_CACHE = "default"

# Enable rate limiting in production
RATELIMIT_ENABLE = True

# Custom rate limit view (optional - returns 429 response)
# If not set, django-ratelimit returns 403 by default
# Our decorators handle this by checking request.limited flag
