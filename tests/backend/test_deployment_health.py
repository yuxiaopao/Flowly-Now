"""Check container health semantics against a real local HTTP responder."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import threading

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('flowly_container_health', ROOT / 'docker' / 'healthcheck.py')
health = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health)


@pytest.mark.parametrize(('status', 'expected'), [(200, True), (204, True), (301, False), (503, False)])
def test_http_health_requires_success_without_following_redirects(status, expected):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.headers['Host'])
            self.send_response(status)
            if status == 301:
                self.send_header('Location', '/another-page')
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        assert health.healthy(f'http://127.0.0.1:{server.server_port}/api/health/', 'configured.example') is expected
        assert requests == ['configured.example']
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@pytest.mark.parametrize(('environment', 'expected'), [
    ({'ALLOWED_HOSTS': 'public.example,another.example'}, 'public.example'),
    ({'ALLOWED_HOSTS': '.public.example'}, 'public.example'),
    ({'ALLOWED_HOSTS': '*'}, '127.0.0.1'),
    ({'ALLOWED_HOSTS': 'public.example', 'HEALTHCHECK_HOST': 'health.example'}, 'health.example'),
])
def test_health_host_uses_the_operator_domain_or_explicit_override(environment, expected):
    assert health.health_host(environment) == expected


def test_production_workers_share_existing_data_and_outputs_without_source_mounts():
    configuration = yaml.safe_load((ROOT / 'docker-compose.prod.yml').read_text(encoding='utf-8'))
    services = configuration['services']
    assert {'backend', 'celery', 'celery-beat', 'frontend'} <= services.keys()
    for name in ('backend', 'celery'):
        volumes = services[name]['volumes']
        for directory in ('data', 'outputs', 'logs', 'backups'):
            assert any(value.endswith(f':/app/{directory}') and f'./Backend/{directory}' in value for value in volumes)
        assert not any(value.endswith(':/app') for value in volumes)
        assert 'flowly_now_media:/app/media' in volumes
        assert 'flowly_now_static:/app/staticfiles' in volumes
