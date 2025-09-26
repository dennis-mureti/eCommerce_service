"""
Staging settings for E-commerce API.
Similar to production but with debugging enabled.
"""
from .production import *

# Enable debugging for staging
DEBUG = True

# Less strict security for staging
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Different cache timeout
CACHES['default']['TIMEOUT'] = 60

# Email backend for staging
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging for staging
LOGGING['handlers']['file']['filename'] = '/var/log/ecommerce/staging.log'
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['ecommerce']['level'] = 'DEBUG'
