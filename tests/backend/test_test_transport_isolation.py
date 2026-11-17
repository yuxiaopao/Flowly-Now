"""Eager execution must not leave test control messages bound to an ambient Redis."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from django.conf import settings

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT/'Backend' if (ROOT/'Backend').is_dir() else Path(settings.BASE_DIR)


@pytest.mark.parametrize('module', ['config.workflow_test_settings', 'config.project_test_settings', 'config.mysql_test_settings'])
def test_official_test_profiles_override_inherited_broker_and_result_urls(module):
    environment = dict(os.environ, DJANGO_SETTINGS_MODULE=module, PYTHON_DOTENV_DISABLED='1', DEBUG='True',
        DJANGO_SECRET_KEY='isolated-transport-test-only-secret', FLOWLY_TEST_MYSQL_PORT='1', FLOWLY_TEST_MYSQL_PASSWORD='not-used',
        CELERY_BROKER_URL='redis://do-not-connect.invalid:1/0', CELERY_BROKER_READ_URL='redis://do-not-connect.invalid:1/1',
        CELERY_BROKER_WRITE_URL='redis://do-not-connect.invalid:1/2', CELERY_RESULT_BACKEND='redis://do-not-connect.invalid:1/3',
        PYTHONPATH=os.pathsep.join((str(BACKEND), str(ROOT))))
    code = '''from config.celery import app
from django.conf import settings
import json
print(json.dumps({'broker':app.conf.broker_url,'read':app.conf.broker_read_url,'write':app.conf.broker_write_url,
 'result':app.conf.result_backend,'configured':settings.CELERY_BROKER_URL,'eager':settings.CELERY_TASK_ALWAYS_EAGER}))
'''
    process = subprocess.run([sys.executable, '-c', code], cwd=BACKEND, env=environment, capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    values = json.loads(process.stdout.strip().splitlines()[-1])
    assert values == {'broker': 'memory://', 'read': 'memory://', 'write': 'memory://',
        'result': 'cache+memory://', 'configured': 'memory://', 'eager': True}


def test_custom_isolated_worker_bootstrap_preserves_its_explicit_filesystem_transport():
    environment = dict(os.environ, DJANGO_SETTINGS_MODULE='custom_isolated_fixture_settings', PYTHON_DOTENV_DISABLED='1',
        CELERY_BROKER_URL='filesystem://', CELERY_BROKER_READ_URL='filesystem://', CELERY_BROKER_WRITE_URL='filesystem://',
        CELERY_RESULT_BACKEND='cache+memory://', PYTHONPATH=os.pathsep.join((str(BACKEND), str(ROOT))))
    code = "import config,os,json;print(json.dumps({key:os.environ[key] for key in ('CELERY_BROKER_URL','CELERY_BROKER_READ_URL','CELERY_BROKER_WRITE_URL','CELERY_RESULT_BACKEND')}))"
    process = subprocess.run([sys.executable, '-c', code], cwd=BACKEND, env=environment, capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout.strip().splitlines()[-1]) == {
        'CELERY_BROKER_URL': 'filesystem://', 'CELERY_BROKER_READ_URL': 'filesystem://',
        'CELERY_BROKER_WRITE_URL': 'filesystem://', 'CELERY_RESULT_BACKEND': 'cache+memory://'}
