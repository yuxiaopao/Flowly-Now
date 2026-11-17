"""Refuse external state before importing Django or Celery in continuation QA."""
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

WORKSPACE = Path(__file__).resolve().parents[1]
KIND = 'flowly-private-continuation-qa-v1'
BROKER_KEYS = ('CELERY_BROKER_URL', 'CELERY_BROKER_READ_URL', 'CELERY_BROKER_WRITE_URL')


def validate_environment(environment=None, *, workspace=WORKSPACE):
    env = os.environ if environment is None else environment
    root = Path(env['FLOWLY_QA_ROOT']).absolute()
    cache = (workspace / '.cache').resolve(strict=True)
    if root.parent != cache or not re.fullmatch(r'continuation-runtime-[0-9a-f]{32}', root.name):
        raise RuntimeError('QA root must be a namespaced private workspace cache directory')
    if root.resolve(strict=True) != root:
        raise RuntimeError('QA root may not redirect outside the private directory')
    for filename in ('manifest.json', 'flowly_continuation_settings.py', 'fixture_metadata.json', 'qa.sqlite3', 'qa.sqlite3-wal', 'qa.sqlite3-shm'):
        target = root / filename
        if target.resolve() != target:
            raise RuntimeError('QA file redirects outside its private root')
    metadata = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    token = root.name.rsplit('-', 1)[-1]
    if metadata != {'kind': KIND, 'root': str(root), 'token': token, 'queue': f'continuation-{token}'}:
        raise RuntimeError('QA ownership manifest is invalid')
    if env.get('FLOWLY_QA_TOKEN') != token or env.get('FLOWLY_ISOLATED_QA') != '1':
        raise RuntimeError('QA ownership token is missing')
    if env.get('PYTHON_DOTENV_DISABLED') != '1' or env.get('DJANGO_SETTINGS_MODULE') != 'flowly_continuation_settings':
        raise RuntimeError('QA refuses ambient Django settings or dotenv loading')
    if any(env.get(key) != 'filesystem://' for key in BROKER_KEYS) or env.get('CELERY_RESULT_BACKEND') != 'cache+memory://':
        raise RuntimeError('QA refuses an external Celery broker or result backend')
    forbidden = ('DATABASE_URL', 'REDIS_URL', 'DB_HOST', 'DB_NAME', 'DB_PASSWORD', 'MYSQL_HOST', 'RAG_CHAT_API_KEY', 'OPENAI_API_KEY')
    if any(env.get(key) for key in forbidden):
        raise RuntimeError('QA refuses inherited service configuration or credentials')
    for folder in ('messages', 'processed', 'control', 'media', 'model-artifacts', 'model-datasets', 'backups', 'tmp', 'logs'):
        target = root / folder
        if not target.is_dir() or target.resolve() != target:
            raise RuntimeError('QA storage must stay inside its private root')
    if Path.cwd().resolve() != (workspace / 'Backend').resolve():
        raise RuntimeError('QA child must use the project Backend working directory')
    return root, metadata


def local_provider_url(value):
    url = urlsplit(value)
    if (url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or
            url.path != '/v1' or url.username or url.password or url.query or url.fragment):
        raise RuntimeError('QA provider must remain on its explicit loopback HTTP fixture')
    return value


def require_before_frameworks():
    if 'django' in sys.modules or 'celery' in sys.modules:
        raise RuntimeError('QA guard must run before importing application frameworks')
    return validate_environment()
