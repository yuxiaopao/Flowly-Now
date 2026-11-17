"""Real isolated processes exercise the public local-service lifecycle."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

import psutil
import pytest

from Scripts.flowly_local_services import LocalServiceError, LocalServiceManager, ServiceSpec


HELPER = '''
import argparse, json, pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer
parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True)
parser.add_argument('--service', required=True)
args = parser.parse_args()
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args): pass
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ready":true}')
server = HTTPServer(('127.0.0.1', 0), Handler)
pathlib.Path(args.workspace, args.service + '.port').write_text(str(server.server_port))
server.serve_forever()
'''


def fixture_manager(root, names=('api',)):
    backend = root / 'Backend'
    backend.mkdir(parents=True, exist_ok=True)
    helper = backend / 'fixture_service.py'
    helper.write_text(HELPER, encoding='utf-8')

    def probe(name):
        try:
            port = int((root / (name + '.port')).read_text())
            with urlopen(f'http://127.0.0.1:{port}/', timeout=0.2) as response:
                return {'ready': json.loads(response.read())['ready'], 'reason': 'fixture HTTP ready'}
        except (OSError, ValueError):
            return {'ready': False, 'reason': 'fixture is starting'}

    specs = [ServiceSpec(name, (sys.executable, '-u', str(helper), '--workspace', str(root), '--service', name),
                         backend, probe=lambda name=name: probe(name)) for name in names]
    return LocalServiceManager(root, specs, startup_timeout=3, stop_timeout=2)


def test_start_is_idempotent_and_stop_waits_for_the_owned_service_to_exit(tmp_path):
    manager = fixture_manager(tmp_path / 'workspace')
    try:
        first = manager.start('api')
        assert first['status'] == 'running' and first['ready'] is True
        assert psutil.pid_exists(first['pid'])
        second = manager.start('api')
        assert second['pid'] == first['pid'] and second['reused'] is True
        assert manager.status('api')['pid'] == first['pid']
        assert manager.stop('api')['status'] == 'stopped'
        assert not psutil.pid_exists(first['pid'])
    finally:
        manager.stop('api')


def test_worker_and_beat_have_independent_lifecycles_and_restart_replaces_only_that_role(tmp_path):
    manager = fixture_manager(tmp_path / 'workspace', ('worker', 'beat'))
    try:
        worker = manager.start('worker')
        beat = manager.start('beat')
        replacement = manager.restart('worker')
        assert replacement['pid'] != worker['pid']
        assert not psutil.pid_exists(worker['pid'])
        assert manager.status('beat')['pid'] == beat['pid']
        manager.stop('worker')
        assert manager.status('beat')['ready'] is True
    finally:
        manager.stop('worker')
        manager.stop('beat')


def test_another_workspace_is_never_stopped_even_when_its_pid_is_in_a_state_record(tmp_path):
    first = fixture_manager(tmp_path / 'first')
    second = fixture_manager(tmp_path / 'second')
    filename = first.state_directory / 'api.json'
    original = None
    try:
        own = first.start('api')
        foreign = second.start('api')
        original = filename.read_bytes()
        poisoned = json.loads(original)
        poisoned['identity'] = json.loads((second.state_directory / 'api.json').read_text())['identity']
        filename.write_text(json.dumps(poisoned), encoding='utf-8')
        with pytest.raises(LocalServiceError, match='工作区'):
            first.stop('api')
        assert psutil.pid_exists(own['pid']) and psutil.pid_exists(foreign['pid'])
        assert second.status('api')['ready'] is True
    finally:
        if original:
            filename.write_bytes(original)
        first.stop('api')
        second.stop('api')


def test_reused_pid_is_rejected_and_the_current_process_is_left_running(tmp_path):
    manager = fixture_manager(tmp_path / 'workspace')
    filename = manager.state_directory / 'api.json'
    original = None
    try:
        running = manager.start('api')
        original = filename.read_bytes()
        poisoned = json.loads(original)
        poisoned['identity']['created_at'] -= 60
        filename.write_text(json.dumps(poisoned), encoding='utf-8')
        with pytest.raises(LocalServiceError, match='PID 已复用'):
            manager.stop('api')
        assert psutil.pid_exists(running['pid'])
    finally:
        if original:
            filename.write_bytes(original)
        manager.stop('api')


def test_a_verified_unrecorded_project_process_is_reused_instead_of_duplicated(tmp_path):
    first = fixture_manager(tmp_path / 'workspace')
    second = fixture_manager(tmp_path / 'workspace')
    try:
        running = first.start('api')
        (first.state_directory / 'api.json').unlink()
        assert second.status('api')['managed'] is False
        reused = second.start('api')
        assert reused['pid'] == running['pid'] and reused['reused'] is True
        assert second.status('api')['managed'] is True
    finally:
        second.stop('api')


def test_startup_exit_is_a_failure_and_logs_are_retained(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    manager = LocalServiceManager(root, [ServiceSpec('worker', (sys.executable, '-c', 'print("fixture-config-missing"); raise SystemExit(42)'), root,
        probe=lambda: {'ready': False, 'reason': '等待 fixture'})], startup_timeout=1)
    try:
        result = manager.start('worker')
        assert result['status'] == 'failed' and result['ready'] is False
        assert 'fixture-config-missing' in (manager.state_directory / 'worker.log').read_text()
    finally:
        manager.stop('worker')


def test_running_without_a_readiness_probe_is_explicitly_unknown(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    manager = LocalServiceManager(root, [ServiceSpec('beat', (sys.executable, '-c', 'import time; time.sleep(60)'), root)])
    try:
        result = manager.start('beat')
        assert result['status'] == 'running' and result['ready'] is None
        assert '尚未取得就绪证据' in result['reason']
    finally:
        manager.stop('beat')


def test_a_controller_crash_releases_the_lock_and_a_new_controller_reuses_the_service(tmp_path):
    manager = fixture_manager(tmp_path / 'workspace')
    root = manager.workspace
    command = manager.services['api'].command
    repository = str(Path(__file__).resolve().parents[2])
    code = (
        f'import sys,os;sys.path.insert(0,{repository!r});'
        'from pathlib import Path;from Scripts.flowly_local_services import LocalServiceManager,ServiceSpec;'
        f'root=Path({str(root)!r});'
        f'spec=ServiceSpec("api",{command!r},root/"Backend",probe=lambda:os._exit(42));'
        'LocalServiceManager(root,[spec],startup_timeout=3).start("api")'
    )
    try:
        controller = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=5)
        assert controller.returncode == 42, controller.stderr.decode(errors='replace')
        result = manager.start('api')
        assert result['status'] == 'running' and result['reused'] is True
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not manager.status('api')['ready']:
            time.sleep(0.05)
        assert manager.status('api')['ready'] is True
    finally:
        # This fixture controller has really exited; release its file artifact
        # even against the pre-fix implementation so no fixture process leaks.
        lock = manager.state_directory / 'api.lock'
        lock.unlink(missing_ok=True)
        manager.stop('api')


def test_simultaneous_start_never_creates_two_role_processes(tmp_path):
    manager = fixture_manager(tmp_path / 'workspace')
    barrier = threading.Barrier(2)
    def start():
        barrier.wait(timeout=2)
        try:
            return manager.start('api')
        except LocalServiceError as error:
            return {'busy': str(error)}
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: start(), range(2)))
        started = [result for result in results if result.get('pid')]
        assert started and len({result['pid'] for result in started}) == 1
        assert manager.status('api')['pid'] == started[0]['pid']
    finally:
        manager.stop('api')


def test_ambiguous_existing_project_role_is_reported_without_starting_a_duplicate(tmp_path):
    original = fixture_manager(tmp_path / 'workspace')
    # Same service/workspace but deliberately different Python launch options.
    base = original.services['api']
    original.services['api'] = replace(base, command=(base.command[0], '-B', *base.command[1:]))
    expected = fixture_manager(tmp_path / 'workspace')
    expected.services['api'] = replace(base, scope_tokens=('--service', 'api'))
    filename = original.state_directory / 'api.json'
    snapshot = None
    try:
        running = original.start('api')
        snapshot = filename.read_bytes()
        filename.unlink()
        with pytest.raises(LocalServiceError, match='不同启动参数'):
            expected.start('api')
        assert psutil.pid_exists(running['pid'])
    finally:
        if snapshot:
            filename.write_bytes(snapshot)
        original.stop('api')
