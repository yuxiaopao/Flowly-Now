"""Infrastructure evidence uses local HTTP and an isolated real Celery transport."""
from contextlib import contextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import socket
import sys
import threading
import time
import uuid

from kombu import Connection, Exchange, Queue
import psutil
import pytest

from Scripts.flowly_local_services import LocalServiceError, LocalServiceManager, run_bounded_command
from Scripts.local_service_cli import build_service_specs
from Scripts.local_service_probe import check_api, check_beat


@contextmanager
def health_server(status, payload):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            required = payload.get('_expected_host')
            self.send_response(400 if required and self.headers.get('Host') != required else status)
            self.send_header('Location', '/redirected/')
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/api/health/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('status,database,redis,expected', [
    (200, 'connected', 'connected', True),
    (200, 'connected', 'disconnected', False),
    (503, 'disconnected', 'connected', False),
    (302, 'connected', 'connected', False),
])
def test_api_readiness_requires_actual_database_cache_and_non_redirect_http(status, database, redis, expected):
    with health_server(status, {'database': database, 'redis': redis}) as url:
        assert check_api(url)['ready'] is expected


def test_api_readiness_uses_the_configured_allowed_host_for_a_loopback_probe():
    with health_server(200, {'database': 'connected', 'redis': 'connected', '_expected_host': 'allowed.example'}) as url:
        assert check_api(url)['ready'] is False
        assert check_api(url, host='allowed.example')['ready'] is True


def test_a_hanging_probe_is_bounded_and_its_real_process_tree_is_stopped(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    marker = root / 'probe.pid'
    code = f'import os,time,pathlib;pathlib.Path({str(marker)!r}).write_text(str(os.getpid()));time.sleep(60)'
    started = time.monotonic()
    with pytest.raises(LocalServiceError, match='超时'):
        run_bounded_command((sys.executable, '-c', code), cwd=root, workspace=root, timeout=0.4)
    assert time.monotonic() - started < 4
    assert marker.exists() and not psutil.pid_exists(int(marker.read_text()))


def test_final_child_environment_removes_parent_broker_without_importing_celery(tmp_path, monkeypatch):
    monkeypatch.setenv('CELERY_BROKER_URL', 'do-not-connect://parent-value')
    monkeypatch.setenv('CELERY_RESULT_BACKEND', 'do-not-connect://parent-result')
    root = tmp_path / 'workspace'
    (root / 'Backend').mkdir(parents=True)
    marker = root / 'actual-child-environment.json'
    code = (
        'import os,sys,json,time;from pathlib import Path;'
        f'Path({str(marker)!r}).write_text(json.dumps({{"broker_present":"CELERY_BROKER_URL" in os.environ,'
        '"result_present":"CELERY_RESULT_BACKEND" in os.environ,"celery_imported":"celery" in sys.modules,'
        '"django_imported":"django" in sys.modules}));time.sleep(60)'
    )
    original = next(spec for spec in build_service_specs(root, executable=sys.executable,
        environment={'CELERY_BROKER_URL': None, 'CELERY_RESULT_BACKEND': None}) if spec.name == 'worker')
    def probe():
        return {'ready': marker.exists(), 'reason': 'actual environment marker'}
    spec = replace(original, command=(sys.executable, '-c', code), probe=probe, scope_tokens=())
    manager = LocalServiceManager(root, [spec], startup_timeout=2, stop_timeout=2)
    try:
        assert manager.start('worker')['ready'] is True
        assert json.loads(marker.read_text()) == {'broker_present': False, 'result_present': False,
            'celery_imported': False, 'django_imported': False}
    finally:
        manager.stop('worker')


def clean_fixture_environment(root):
    allowed = {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP',
               'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'HOME', 'LANG', 'LC_ALL', 'TZ', 'PROCESSOR_ARCHITECTURE'}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    metadata = json.loads((root / 'fixture-manifest.json').read_text())
    environment['LC_FIXTURE_ROOT'] = str(root)
    environment['LC_FIXTURE_TOKEN'] = metadata['token']
    environment['CELERY_BROKER_URL'] = 'filesystem://'
    environment['CELERY_BROKER_READ_URL'] = 'filesystem://'
    environment['CELERY_BROKER_WRITE_URL'] = 'filesystem://'
    environment['CELERY_RESULT_BACKEND'] = 'cache+memory://'
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONPATH'] = os.pathsep.join((str(root / 'Backend'), str(Path(__file__).resolve().parents[2] / 'Scripts')))
    return environment


def make_celery_fixture(root):
    backend = root / 'Backend'
    backend.mkdir(parents=True)
    for name in ('messages', 'processed', 'control'):
        (root / name).mkdir()
    token = uuid.uuid4().hex
    node = 'flowly-' + hashlib.sha256(os.path.normcase(str(root.resolve())).encode()).hexdigest()[:16] + '@' + socket.gethostname()
    metadata = {'kind': 'flowly-isolated-lifecycle-fixture', 'root': str(root.resolve()), 'token': token,
                'queue': 'flowly-fixture-' + token, 'node': node,
                'probe': str(Path(__file__).resolve().parents[2] / 'Scripts/local_service_probe.py')}
    (root / 'fixture-manifest.json').write_text(json.dumps(metadata), encoding='utf-8')
    guard = r'''
import json,os,sys,runpy,hashlib,socket
from pathlib import Path
def validate_fixture():
    root=Path(os.environ['LC_FIXTURE_ROOT']).resolve(strict=True)
    if root.name != 'workspace' or not root.parent.name.startswith('test_') or not any(p.name.startswith('pytest-') for p in root.parents):
        raise RuntimeError('Not an isolated pytest fixture directory')
    metadata=json.loads((root/'fixture-manifest.json').read_text())
    if metadata['kind'] != 'flowly-isolated-lifecycle-fixture' or metadata['root'] != str(root) or metadata['token'] != os.environ['LC_FIXTURE_TOKEN']:
        raise RuntimeError('Fixture ownership does not match')
    expected_node='flowly-'+hashlib.sha256(os.path.normcase(str(root)).encode()).hexdigest()[:16]+'@'+socket.gethostname()
    if (len(metadata['token'])!=32 or metadata['queue'] != 'flowly-fixture-'+metadata['token'] or metadata['node']!=expected_node):
        raise RuntimeError('Fixture queue/node namespace is missing')
    if Path.cwd().resolve() != root/'Backend': raise RuntimeError('Unexpected fixture working directory')
    for folder in ('messages','processed','control'):
        path=root/folder
        if not path.is_dir() or path.resolve()!=path: raise RuntimeError('Fixture broker path escaped')
    for key in ('CELERY_BROKER_URL','CELERY_BROKER_READ_URL','CELERY_BROKER_WRITE_URL'):
        if os.environ.get(key) != 'filesystem://': raise RuntimeError('Fixture refuses a non-isolated broker')
    if os.environ.get('CELERY_RESULT_BACKEND') != 'cache+memory://': raise RuntimeError('Fixture refuses an external result backend')
    settings=os.environ.get('DJANGO_SETTINGS_MODULE')
    if settings:
        module=sys.modules.get('lifecycle_settings')
        if settings!='lifecycle_settings' or not module or Path(module.__file__).resolve()!=root/'Backend'/'lifecycle_settings.py':
            raise RuntimeError('Fixture refuses inherited Django settings')
    if '--hostname' in sys.argv and sys.argv[sys.argv.index('--hostname')+1] != metadata['node']: raise RuntimeError('Unexpected worker node')
    if '--destination' in sys.argv and sys.argv[sys.argv.index('--destination')+1] != metadata['node']: raise RuntimeError('Unexpected probe node')
    return metadata
if __name__=='__main__':
    try:
        assert 'celery' not in sys.modules and 'django' not in sys.modules
        assert not os.environ.get('DJANGO_SETTINGS_MODULE')
        metadata=validate_fixture()
    except Exception:
        print(json.dumps({'refused':True,'celery_imported':'celery' in sys.modules,'django_imported':'django' in sys.modules}))
        sys.exit(2)
    if sys.argv[1]=='--run-script':
        target=Path(sys.argv[2]).resolve()
        if str(target)!=metadata['probe']: raise RuntimeError('Unexpected fixture script')
        sys.argv=[str(target),*sys.argv[3:]];runpy.run_path(str(target),run_name='__main__')
    elif sys.argv[1]=='--run-module':
        if sys.argv[2]!='django': raise RuntimeError('Unexpected fixture module')
        sys.argv=['django',*sys.argv[3:]];runpy.run_module('django',run_name='__main__')
    else:
        sys.argv=['celery',*sys.argv[1:]];runpy.run_module('celery',run_name='__main__')
'''
    (backend / 'fixture_guard.py').write_text(guard, encoding='utf-8')
    source = r'''
from fixture_guard import validate_fixture
metadata=validate_fixture()
from celery import Celery
from pathlib import Path
import os,time
root=Path(metadata['root'])
app=Celery('lifecycle-fixture',broker='filesystem://',backend='cache+memory://',fixups=[])
assert app.conf.broker_url == app.conf.broker_read_url == app.conf.broker_write_url == 'filesystem://'
assert app.conf.result_backend == 'cache+memory://'
app.conf.update(broker_transport_options={
    'data_folder_in':str(root/'messages'),'data_folder_out':str(root/'messages'),
    'data_folder_processed':str(root/'processed'),'control_folder':str(root/'control'),
    'polling_interval':0.1},task_default_queue=metadata['queue'],
    beat_schedule={'proof':{'task':'lifecycle.proof','schedule':0.3}},worker_prefetch_multiplier=1)
@app.task(name='lifecycle.proof')
def proof():
    with (root/'completed-tasks.txt').open('a') as target: target.write('completed\n')
    return 'completed'
'''
    (backend / 'lifecycle_fixture_app.py').write_text(source, encoding='utf-8')
    compile(guard, 'fixture_guard.py', 'exec')
    compile(source, 'lifecycle_fixture_app.py', 'exec')
    return backend


@pytest.mark.parametrize('key,value', [
    ('CELERY_BROKER_URL', 'do-not-connect://forbidden'),
    ('CELERY_BROKER_READ_URL', 'do-not-connect://forbidden-read'),
    ('CELERY_RESULT_BACKEND', 'do-not-connect://forbidden-result'),
    ('DJANGO_SETTINGS_MODULE', 'config.settings'),
    ('LC_FIXTURE_ROOT', str(Path(__file__).resolve().parents[2])),
    ('LC_FIXTURE_TOKEN', 'different-fixture-token'),
])
def test_fixture_guard_rejects_ambient_services_and_nonfixture_paths_before_imports(tmp_path, key, value):
    root = tmp_path / 'workspace'
    backend = make_celery_fixture(root)
    environment = clean_fixture_environment(root)
    environment[key] = value
    result = run_bounded_command((sys.executable, str(backend / 'fixture_guard.py'), '--run-module', 'django', '--version'),
                                cwd=backend, workspace=root, environment=environment)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {'refused': True, 'celery_imported': False, 'django_imported': False}


def test_real_worker_and_beat_dispatch_a_task_without_removing_an_unrelated_queue(tmp_path, monkeypatch):
    monkeypatch.setenv('CELERY_BROKER_URL', 'do-not-connect://ambient-value')
    root = tmp_path / 'workspace'
    make_celery_fixture(root)
    environment = clean_fixture_environment(root)
    changes = {key: None for key in os.environ if key not in environment}
    changes.update(environment)
    specs = build_service_specs(root, executable=sys.executable, celery_app='lifecycle_fixture_app', environment=changes)
    guard = str(root / 'Backend' / 'fixture_guard.py')
    metadata = json.loads((root / 'fixture-manifest.json').read_text())
    def worker_probe():
        result = run_bounded_command((sys.executable, guard, '--run-script', metadata['probe'], 'worker',
            '--app', 'lifecycle_fixture_app', '--destination', metadata['node']), cwd=root / 'Backend', workspace=root,
            environment=environment, timeout=8)
        return json.loads(result.stdout.strip().splitlines()[-1])
    guarded = []
    for spec in specs:
        if spec.name in ('worker', 'beat'):
            command = (sys.executable, guard, *spec.command[3:])
            probe = worker_probe if spec.name == 'worker' else lambda command=command: check_beat(root, command)
            guarded.append(replace(spec, command=command, probe=probe, scope_tokens=()))
    manager = LocalServiceManager(root, guarded, startup_timeout=15, stop_timeout=3)
    options = {'data_folder_in': str(root / 'messages'), 'data_folder_out': str(root / 'messages'),
               'data_folder_processed': str(root / 'processed'), 'control_folder': str(root / 'control')}
    with Connection('filesystem://', transport_options=options) as connection:
        name = metadata['queue'] + '-never-consume'
        queue = Queue(name, Exchange(''), routing_key=name)
        connection.Producer().publish({'preserve': 'unrelated-queue'}, routing_key=name, declare=[queue], serializer='json')
    pending = {path: path.read_bytes() for path in (root / 'messages').glob('*never-consume.msg')}
    assert len(pending) == 1
    try:
        worker = manager.start('worker')
        assert worker['ready'] is True, worker
        beat = manager.start('beat')
        assert beat['ready'] is True and beat['evidence'] == 'scheduler_tick', beat
        deadline = time.monotonic() + 6
        marker = root / 'completed-tasks.txt'
        while time.monotonic() < deadline and not marker.exists():
            time.sleep(0.05)
        assert marker.exists() and 'completed' in marker.read_text()
        assert manager.status('worker')['ready'] is True
        assert manager.status('beat')['ready'] is True
    finally:
        manager.stop('beat')
        manager.stop('worker')
    assert {path: path.read_bytes() for path in pending} == pending
    assert check_beat(root, manager.services['beat'].command)['ready'] is False


def test_configuration_probe_reports_pending_migrations_without_applying_them(tmp_path):
    root = tmp_path / 'workspace'
    backend = make_celery_fixture(root)
    database = root / 'configuration.sqlite3'
    (backend / 'lifecycle_settings.py').write_text(
        "SECRET_KEY='private-fixture-never-return';INSTALLED_APPS=['django.contrib.contenttypes'];"
        f"DATABASES={{'default':{{'ENGINE':'django.db.backends.sqlite3','NAME':{str(database)!r}}}}};USE_TZ=True", encoding='utf-8')
    environment = clean_fixture_environment(root)
    probe = str(Path(__file__).resolve().parents[2] / 'Scripts/local_service_probe.py')
    guard = str(backend / 'fixture_guard.py')
    command = (sys.executable, guard, '--run-script', probe, 'configuration', '--app', 'lifecycle_fixture_app', '--django-settings', 'lifecycle_settings')
    pending = run_bounded_command(command, cwd=backend, workspace=root, environment=environment)
    response = json.loads(pending.stdout.strip().splitlines()[-1])
    assert pending.returncode == 1 and response['code'] == 'pending_migrations'
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    migrated = run_bounded_command((sys.executable, guard, '--run-module', 'django', 'migrate', '--settings=lifecycle_settings', '--noinput'),
                                  cwd=backend, workspace=root, environment=environment)
    assert migrated.returncode == 0, migrated.stderr
    ready = run_bounded_command(command, cwd=backend, workspace=root, environment=environment)
    assert ready.returncode == 0 and json.loads(ready.stdout.strip().splitlines()[-1])['ready'] is True
    assert 'private-fixture-never-return' not in ready.stdout + pending.stdout
    application = backend / 'lifecycle_fixture_app.py'
    application.write_text(application.read_text() + '\napp.conf.beat_schedule={}\n', encoding='utf-8')
    missing_schedule = run_bounded_command((*command, '--require-beat-schedule'), cwd=backend, workspace=root, environment=environment)
    assert missing_schedule.returncode == 1 and json.loads(missing_schedule.stdout.strip().splitlines()[-1])['code'] == 'beat_not_configured'
    without_beat = run_bounded_command(command, cwd=backend, workspace=root, environment=environment)
    assert without_beat.returncode == 0
