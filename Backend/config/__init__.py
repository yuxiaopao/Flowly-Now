import os

# Celery gives environment URLs priority over Django settings, including eager mode.
if os.environ.get('DJANGO_SETTINGS_MODULE') in {
    'config.workflow_test_settings', 'config.project_test_settings', 'config.mysql_test_settings',
}:
    for broker_key in ('CELERY_BROKER_URL', 'CELERY_BROKER_READ_URL', 'CELERY_BROKER_WRITE_URL'):
        os.environ[broker_key] = 'memory://'
    os.environ['CELERY_RESULT_BACKEND'] = 'cache+memory://'

# Django and shared_task use the same application instance.
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    __all__ = ()
