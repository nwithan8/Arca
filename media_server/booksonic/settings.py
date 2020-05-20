import os

BOOKSONIC_URL = os.environ.get('BOOKSONIC_URL')
BOOKSONIC_USER = os.environ.get('BOOKSONIC_USER')
BOOKSONIC_PASS = os.environ.get('BOOKSONIC_PASS')
BOOKSONIC_SERVER_NAME = os.environ.get('BOOKSONIC_SERVER_NAME')

ADMIN_ROLE_NAME = os.environ.get('BOOKSONIC_ADMIN_ROLE')

DEFAULT_EMAIL = ''
USE_DEFAULT_PASSWORD = False  # If FALSE, random password generated each time
DEFAULT_PASSWORD = ''
