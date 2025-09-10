import os

# Ensure the app uses production-safe defaults when run by WSGI servers
os.environ.setdefault('FLASK_DEBUG', '0')

from app import app as application  # WSGI entrypoint


