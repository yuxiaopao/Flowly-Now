"""Bounded infrastructure evidence; never reveals credentials or checks user models."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import psutil

BEAT_STALE_SECONDS = 20


def check_api(url, host=None):
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None
    try:
        request = Request(url, headers={'Host': host} if host else {})
        with build_opener(NoRedirect).open(request, timeout=2) as response:
            data = json.loads(response.read(65537))
            checks = {'http': 200 <= response.status < 300, 'database': data.get('database') == 'connected',
                      'cache': data.get('redis') == 'connected'}
        ready = all(checks.values())
        return {'ready': ready, 'reason': 'API、数据库和缓存检查通过。' if ready else 'API 依赖未就绪，请检查数据库/Redis；健康页不能替代应用模型配置检查。', 'checks': checks}
    except (HTTPError, URLError, OSError, ValueError):
        return {'ready': False, 'reason': 'API 健康端点不可用或未返回有效依赖状态。'}


def check_beat(workspace, command):
    root = Path(workspace).resolve(strict=True)
    filename = root / '.cache' / 'local-services' / 'beat-heartbeat.json'
    try:
        if filename.resolve() != filename:
            raise ValueError('Unexpected heartbeat path')
        value = json.loads(filename.read_text(encoding='utf-8'))
        workspace_id = hashlib.sha256(os.path.normcase(str(root)).encode()).hexdigest()[:16]
        if value.get('event') != 'scheduler_tick' or value.get('workspace_id') != workspace_id:
            raise ValueError('Unexpected heartbeat owner')
        elapsed = time.time() - value['observed_at']
        process = psutil.Process(value['pid'])
        if not 0 <= elapsed <= BEAT_STALE_SECONDS or process.create_time() != value['created_at']:
            raise ValueError('Expired heartbeat')
        actual = process.cmdline()
        if (Path(process.cwd()).resolve() != root / 'Backend' or len(actual) != len(command)
                or [os.path.normcase(arg) for arg in actual[1:]] != [os.path.normcase(arg) for arg in command[1:]]):
            raise ValueError('Unexpected scheduler process')
        return {'ready': True, 'reason': '已观察到当前 Beat 的真实调度 tick；业务任务完成情况需另行核验。', 'evidence': 'scheduler_tick'}
    except (OSError, ValueError, KeyError, TypeError, psutil.Error):
        return {'ready': False, 'reason': '未取得当前项目 Beat 的新鲜调度心跳，不能确认调度就绪。'}


def check_configuration(django_settings=None, app_name='config', require_beat=False):
    try:
        healthcheck_host = None
        if django_settings:
            os.environ['DJANGO_SETTINGS_MODULE'] = django_settings
            import django
            django.setup()
            from django.conf import settings
            allowed = [value.strip().lstrip('.') for value in settings.ALLOWED_HOSTS if value.strip()]
            healthcheck_host = os.environ.get('HEALTHCHECK_HOST', '').strip() or (allowed[0] if allowed else '127.0.0.1')
            if healthcheck_host == '*':
                healthcheck_host = '127.0.0.1'
            from django.db import connection
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if pending:
                return {'ready': False, 'code': 'pending_migrations', 'reason': '数据库尚有未应用迁移，请先按部署流程备份并运行 manage.py migrate；启动器不会自动迁移。', 'pending_migration_count': len(pending)}
        from celery.app.utils import find_app
        app = find_app(app_name)
        if not app.conf.broker_url:
            return {'ready': False, 'code': 'broker_not_configured', 'reason': '缺少 CELERY_BROKER_URL。'}
        if require_beat and not app.conf.beat_schedule:
            return {'ready': False, 'code': 'beat_not_configured', 'reason': '未配置 Beat 定时任务；可先配置调度，或仅选择 API/Worker。'}
        return {'ready': True, 'reason': '运行配置可加载，迁移状态检查通过。', 'models': 'not_checked', 'healthcheck_host': healthcheck_host}
    except Exception as error:
        return {'ready': False, 'code': 'configuration_unavailable', 'reason': f'运行配置或数据库不可用（{type(error).__name__}）；请检查 .env 必填项、数据库与依赖。', 'models': 'not_checked'}


def check_worker(app_name, destination):
    try:
        from celery.app.utils import find_app
        app = find_app(app_name)
        app.conf.broker_connection_timeout = 1
        transport = dict(app.conf.broker_transport_options or {})
        transport.update(socket_connect_timeout=1, socket_timeout=1, retry_on_timeout=False,
                         retry_policy={'max_retries': 0})
        app.conf.broker_transport_options = transport
        reply = app.control.inspect(destination=[destination], timeout=1).ping()
        ready = isinstance(reply, dict) and reply.get(destination, {}).get('ok') == 'pong'
        return {'ready': ready, 'reason': '本项目指定 Worker 已响应 ping。' if ready else '本项目指定 Worker 未响应；请检查 broker、节点名称及 Worker 日志。', 'evidence': 'worker_ping' if ready else None}
    except Exception as error:
        return {'ready': False, 'reason': f'Worker/broker 检查失败（{type(error).__name__}）。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('configuration', 'worker'))
    parser.add_argument('--app', default='config')
    parser.add_argument('--destination')
    parser.add_argument('--django-settings')
    parser.add_argument('--require-beat-schedule', action='store_true')
    arguments = parser.parse_args()
    if arguments.mode == 'worker' and not arguments.destination:
        parser.error('worker 检查必须指定本项目节点名称。')
    result = (check_configuration(arguments.django_settings, arguments.app, arguments.require_beat_schedule) if arguments.mode == 'configuration'
              else check_worker(arguments.app, arguments.destination))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
