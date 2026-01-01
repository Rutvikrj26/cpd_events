from .base import *

# Use in-memory SQLite for speed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Fast password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable rate limiting for tests
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/day',
    'user': '10000/day',
    'import': '10000/day',
    'auth': '10000/day',
}


# Disable Cloud Tasks
GOOGLE_CLOUD_PROJECT = 'test-project'
GOOGLE_CLOUD_LOCATION = 'us-central1'
GOOGLE_CLOUD_TASKS_QUEUE = 'test-queue'
