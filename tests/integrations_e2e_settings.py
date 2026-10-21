"""Controlled HTTP fixtures for Chrome DevTools checks; never use in production.

Use a disposable integrations_qa_ account. Start the receiver below, run Django
on port 8001 with this module, then run Scripts/integrations_chrome_mcp.mjs.
PYTHONPATH must include the repository root and Backend directory.
"""
from config.settings import *
from integrations.catalog import API_ENDPOINTS

INTEGRATIONS_ALLOWED_PRIVATE_HOSTS = ('127.0.0.1',)
CELERY_TASK_ALWAYS_EAGER = True
API_ENDPOINTS['github'] = (
    'http://127.0.0.1:8766/github/user',
    'http://127.0.0.1:8766/github/repos',
)
