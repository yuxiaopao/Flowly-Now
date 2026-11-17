"""Safe local API/Worker/Beat commands; no queue purge or global process kill."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

if __package__:
    from .flowly_local_services import LocalServiceError, LocalServiceManager, ServiceSpec, run_bounded_command
    from .local_service_probe import check_api, check_beat
else:
    from flowly_local_services import LocalServiceError, LocalServiceManager, ServiceSpec, run_bounded_command
    from local_service_probe import check_api, check_beat

SERVICE_ORDER = ('api', 'worker', 'beat')
DEFAULT_OPTIONS = {'api_host': '127.0.0.1', 'api_port': 8000, 'workers': 2}


def _probe_command(workspace, executable, arguments, *, environment=None, timeout=8):
    command = (str(executable), str(Path(__file__).with_name('local_service_probe.py')), *arguments)
    try:
        result = run_bounded_command(command, cwd=workspace / 'Backend', workspace=workspace,
                                     timeout=timeout, environment=environment)
        data = json.loads(result.stdout.strip().splitlines()[-1])
        if not isinstance(data, dict) or data.get('ready') not in (True, False):
            raise ValueError('Invalid probe result')
        if result.returncode and data['ready']:
            raise ValueError('Probe failed')
        return data
    except (LocalServiceError, OSError, ValueError, IndexError):
        return {'ready': False, 'reason': '配置/就绪检查未通过或超时；检查进程已结束，未操作用户队列。'}


def build_service_specs(workspace, *, executable=None, api_host='127.0.0.1', api_port=8000, workers=2, celery_app='config', environment=None, api_health_host=None):
    root = Path(workspace).resolve(strict=True)
    backend = root / 'Backend'
    python = str(executable or root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
    state = root / '.cache' / 'local-services'
    workspace_id = hashlib.sha256(os.path.normcase(str(root)).encode()).hexdigest()[:16]
    node = f'flowly-{workspace_id}@{socket.gethostname()}'
    common = (python, '-m', 'celery', '--workdir', str(backend), '-A', celery_app)
    worker = (*common, 'worker', '-l', 'INFO', '--pool=threads', '--concurrency', str(workers), '--hostname', node)
    beat = (*common, 'beat', '-l', 'INFO', '--scheduler', 'flowly_beat_scheduler:ObservedPersistentScheduler',
            '--schedule', str(state / 'celerybeat-schedule'))
    inherited = os.environ.copy()
    for key, value in (environment or {}).items():
        if value is None:
            inherited.pop(key, None)
        else:
            inherited[key] = value
    script_path = str(Path(__file__).resolve().parent)
    inherited['PYTHONPATH'] = os.pathsep.join(filter(None, (str(backend), script_path, inherited.get('PYTHONPATH', ''))))
    # ServiceSpec.environment is a patch over the caller's environment. Keep
    # removals explicit so a later merge cannot reintroduce inherited secrets/URLs.
    service_environment = {**inherited, **{key: None for key, value in (environment or {}).items() if value is None}}
    beat_environment = {**service_environment, 'FLOWLY_SERVICE_WORKSPACE': str(root)}
    probe_host = '127.0.0.1' if api_host in ('0.0.0.0', '::') else api_host
    if ':' in probe_host:
        probe_host = '[' + probe_host + ']'
    return [
        ServiceSpec('api', (python, str(backend / 'manage.py'), 'runserver', f'{api_host}:{api_port}', '--noreload'), backend,
                    probe=lambda: check_api(f'http://{probe_host}:{api_port}/api/health/', host=api_health_host), environment=service_environment,
                    scope_tokens=('runserver',)),
        ServiceSpec('worker', worker, backend, environment=service_environment,
                    probe=lambda: _probe_command(root, python, ('worker', '--app', celery_app, '--destination', node), environment=inherited),
                    scope_tokens=('-m', 'celery', celery_app, 'worker')),
        ServiceSpec('beat', beat, backend, environment=beat_environment, probe=lambda: check_beat(root, beat),
                    scope_tokens=('-m', 'celery', celery_app, 'beat')),
    ]


def _options(root, arguments):
    filename = root / '.cache' / 'local-services' / 'launch-options.json'
    if filename.resolve() != filename:
        raise LocalServiceError('启动参数文件不能重定向到其他位置。')
    try:
        old = json.loads(filename.read_text(encoding='utf-8'))
    except FileNotFoundError:
        old = dict(DEFAULT_OPTIONS)
    except (OSError, ValueError):
        raise LocalServiceError('本项目启动参数记录损坏，请核对后处理；未操作任何进程。') from None
    if not isinstance(old, dict) or set(old) != set(DEFAULT_OPTIONS):
        raise LocalServiceError('本项目启动参数记录格式无效。')
    desired = {key: getattr(arguments, key) if getattr(arguments, key) is not None else old[key] for key in DEFAULT_OPTIONS}
    for value in (old, desired):
        if (not isinstance(value['api_host'], str) or not value['api_host'] or any(c in value['api_host'] for c in '\r\n /')
                or type(value['api_port']) is not int or not 1 <= value['api_port'] <= 65535
                or type(value['workers']) is not int or not 1 <= value['workers'] <= 64):
            raise LocalServiceError('启动地址、端口或 Worker 并发参数无效。')
    return filename, old, desired


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--action', choices=('start', 'status', 'stop', 'restart'), default='start')
    parser.add_argument('--services', nargs='+', choices=SERVICE_ORDER, default=list(SERVICE_ORDER))
    parser.add_argument('--api-host')
    parser.add_argument('--api-port', type=int)
    parser.add_argument('--workers', type=int)
    parser.add_argument('--startup-timeout', type=float, default=30)
    parser.add_argument('--stop-timeout', type=float, default=15)
    parser.add_argument('--json', action='store_true')
    arguments = parser.parse_args(argv)
    report = {'action': arguments.action, 'models': 'not_checked', 'product_ready': None, 'components': []}
    try:
        root = arguments.workspace.resolve(strict=True)
        filename, old, desired = _options(root, arguments)
        manager = LocalServiceManager(root, build_service_specs(root, **old), startup_timeout=arguments.startup_timeout, stop_timeout=arguments.stop_timeout)
        selected = [name for name in SERVICE_ORDER if name in arguments.services]
        if old != desired:
            if arguments.action not in ('start', 'restart') or set(selected) != set(SERVICE_ORDER):
                raise LocalServiceError('修改启动参数需选择全部服务并使用 start/restart；status/stop 始终使用已记录的参数。')
            if arguments.action == 'start' and any(manager.status(name)['status'] == 'running' for name in SERVICE_ORDER):
                raise LocalServiceError('服务仍在运行；调整参数请显式使用 restart，未启动重复进程。')
        if arguments.action in ('start', 'restart', 'status'):
            spec = manager.services['worker']
            configuration_arguments = ['configuration', '--django-settings', 'config.settings']
            if 'beat' in selected:
                configuration_arguments.append('--require-beat-schedule')
            configuration = _probe_command(root, spec.command[0], tuple(configuration_arguments), environment=dict(spec.environment or {}))
            report['configuration'] = configuration
            if not configuration['ready'] and arguments.action != 'status':
                raise LocalServiceError(configuration['reason'])
            manager.services['api'] = build_service_specs(root, **old, api_health_host=configuration.get('healthcheck_host'))[0]
        if arguments.action in ('stop', 'restart'):
            for name in reversed(selected):
                result = manager.stop(name)
                if arguments.action == 'stop':
                    report['components'].append(result)
        if arguments.action in ('start', 'restart'):
            manager = LocalServiceManager(root, build_service_specs(root, **desired, api_health_host=report['configuration'].get('healthcheck_host')), startup_timeout=arguments.startup_timeout, stop_timeout=arguments.stop_timeout)
            descriptor, temporary = tempfile.mkstemp(dir=filename.parent, prefix='launch-options-', suffix='.tmp')
            try:
                with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                    json.dump(desired, stream)
                os.replace(temporary, filename)
            finally:
                Path(temporary).unlink(missing_ok=True)
            for name in selected:
                report['components'].append(manager.start(name))
        elif arguments.action == 'status':
            for name in selected:
                try:
                    report['components'].append(manager.status(name))
                except LocalServiceError as error:
                    report['components'].append({'service': name, 'status': 'ownership_unverified', 'ready': False, 'reason': str(error)})
        report['infrastructure_ready'] = (bool(report['components']) and all(item.get('ready') is True for item in report['components'])
                                          and report.get('configuration', {}).get('ready', True))
        exit_code = 0 if arguments.action == 'stop' or report['infrastructure_ready'] else 2
    except (LocalServiceError, OSError, ValueError, KeyError) as error:
        report.update(infrastructure_ready=False, error=str(error))
        exit_code = 1
    if arguments.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        for item in report['components']:
            print(f"{item['service']}: {item['status']}，ready={item.get('ready')}，PID={item.get('pid')}，{item.get('reason', '')}")
        if report.get('error'):
            print(report['error'], file=sys.stderr)
        print('模型就绪未检查；进程/基础设施就绪不代表应用可以发布。')
        print('服务日志：' + str(arguments.workspace / '.cache' / 'local-services'))
    return exit_code


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    sys.exit(main())
