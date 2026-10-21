"""Isolated RAG browser verification. No production database or real model is used."""
from pathlib import Path
from config.project_test_settings import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(Path(BASE_DIR).parent / 'test-reports' / 'rag-browser.sqlite3')}}
SECRET_KEY = 'isolated-rag-browser-test-only-not-for-production'
PUBLIC_API_BASE_URL = 'http://127.0.0.1:8003'
FRONTEND_URL = 'http://127.0.0.1:5201'
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
RAG_CHAT_MODEL = 'rag-controlled-test'
RAG_CHAT_BASE_URL = 'http://127.0.0.1:8767/v1'
RAG_CHAT_API_KEY = 'controlled-test-only'
LOGGING = {'version': 1, 'disable_existing_loggers': False, 'handlers': {'console': {'class': 'logging.StreamHandler'}}, 'root': {'handlers': ['console'], 'level': 'WARNING'}}
