"""Local service lifecycle with persisted, revalidated process ownership."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Callable, Mapping

import psutil


class LocalServiceError(RuntimeError):
    """An operation could not safely finish; no unrelated process is changed."""


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    command: tuple[str, ...]
    cwd: Path
    probe: Callable[[], dict] | None = None
    environment: Mapping[str, str | None] | None = None
    scope_tokens: tuple[str, ...] = ()


def _path(value):
    return os.path.normcase(str(Path(value).resolve()))


def _within(path, root):
    try:
        Path(path).resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _process_identity(process):
    with process.oneshot():
        return {'pid': process.pid, 'created_at': process.create_time(), 'executable': _path(process.exe()),
                'arguments': process.cmdline(), 'cwd': _path(process.cwd())}


def _stop_owned_tree(process, workspace, identity, timeout):
    try:
        if _process_identity(process) != identity:
            raise LocalServiceError('停止前进程身份已变化，拒绝发送终止信号。')
        descendants = process.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    identities = []
    for candidate in [*reversed(descendants), process]:
        try:
            snapshot = _process_identity(candidate)
        except psutil.NoSuchProcess:
            continue
        console_host = os.name == 'nt' and snapshot['executable'] == _path(Path(os.environ['SystemRoot']) / 'System32' / 'conhost.exe')
        if console_host:
            continue
        if not _within(snapshot['cwd'], workspace):
            raise LocalServiceError('子进程工作区无法确认，拒绝停止进程树。')
        identities.append((candidate, snapshot))
    for candidate, snapshot in identities:
        try:
            if _process_identity(candidate) != snapshot:
                raise LocalServiceError('停止前进程身份已变化，拒绝发送终止信号。')
            candidate.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs([candidate for candidate, _ in identities], timeout=timeout)
    if alive:
        raise LocalServiceError('服务尚未退出，未强制杀进程，也未启动替代进程。')


def run_bounded_command(command, *, cwd, workspace, timeout=5, environment=None):
    """Read-only probes share the same timeout and owned-tree stop guarantees."""
    child = subprocess.Popen(command, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
        start_new_session=os.name != 'nt')
    try:
        identity = _process_identity(psutil.Process(child.pid))
    except psutil.NoSuchProcess:
        identity = None
    try:
        output, error = child.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, child.returncode, output, error)
    except subprocess.TimeoutExpired:
        if identity:
            try:
                _stop_owned_tree(psutil.Process(child.pid), workspace, identity, 2)
            except psutil.NoSuchProcess:
                pass
        child.communicate(timeout=2)
        raise LocalServiceError('就绪检查超时，已停止本次检查进程。') from None


class LocalServiceManager:
    """Start, inspect and stop only processes whose current identity is proven."""

    def __init__(self, workspace, services, *, startup_timeout=30, stop_timeout=15):
        self.workspace = Path(workspace).resolve(strict=True)
        self.services = {service.name: service for service in services}
        self.startup_timeout = float(startup_timeout)
        self.stop_timeout = float(stop_timeout)
        if self.startup_timeout <= 0 or self.stop_timeout <= 0:
            raise ValueError('服务等待时间必须大于零。')
        self.state_directory = self.workspace / '.cache' / 'local-services'
        # Refuse junctions/symlinks that redirect lifecycle state outside this project.
        if self.state_directory.resolve() != self.state_directory:
            raise LocalServiceError('服务状态目录不能重定向到其他位置。')
        self.state_directory.mkdir(parents=True, exist_ok=True)
        self.workspace_id = hashlib.sha256(_path(self.workspace).encode()).hexdigest()[:16]
        self.children = {}
        for service in self.services.values():
            if not service.name.replace('-', '').replace('_', '').isalnum():
                raise ValueError('服务名称无效。')
            if not _within(service.cwd, self.workspace) or not Path(service.cwd).is_dir():
                raise LocalServiceError('服务工作目录必须位于当前项目内。')
            if not service.command or not Path(service.command[0]).is_file():
                raise LocalServiceError('服务解释器不存在，请先创建项目虚拟环境。')

    def _file(self, name):
        if name not in self.services:
            raise LocalServiceError('未知服务。')
        return self.state_directory / (name + '.json')

    def _write(self, name, value):
        destination = self._file(name)
        descriptor, filename = tempfile.mkstemp(dir=self.state_directory, prefix=name + '-', suffix='.tmp')
        temporary = Path(filename)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _read(self, name):
        filename = self._file(name)
        if filename.resolve() != filename:
            raise LocalServiceError('服务状态文件不能重定向到其他位置。')
        try:
            value = json.loads(filename.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            raise LocalServiceError('服务状态记录损坏；请核对本项目进程后处理记录，未停止任何进程。') from None
        if not isinstance(value, dict) or value.get('workspace_id') != self.workspace_id or value.get('service') != name:
            raise LocalServiceError('服务状态记录不属于当前项目，拒绝操作。')
        return value

    @staticmethod
    def _identity(process):
        return _process_identity(process)

    def _matches_service(self, process, spec):
        try:
            identity = self._identity(process)
            executables = {_path(spec.command[0]), _path(getattr(sys, '_base_executable', sys.executable))}
            arguments = identity['arguments']
            return (process.status() != psutil.STATUS_ZOMBIE and identity['cwd'] == _path(spec.cwd)
                    and identity['executable'] in executables and len(arguments) == len(spec.command)
                    and [os.path.normcase(arg) for arg in arguments[1:]] == [os.path.normcase(arg) for arg in spec.command[1:]])
        except (psutil.Error, OSError):
            return False

    def _record(self, name, process):
        return {'workspace_id': self.workspace_id, 'service': name, 'identity': self._identity(process)}

    def _process(self, name, record):
        identity = record.get('identity')
        if not isinstance(identity, dict) or not isinstance(identity.get('pid'), int):
            raise LocalServiceError('服务进程身份记录无效，拒绝操作。')
        try:
            process = psutil.Process(identity['pid'])
            if process.status() == psutil.STATUS_ZOMBIE:
                return None
            current = self._identity(process)
            if current['created_at'] != identity['created_at']:
                raise LocalServiceError('PID 已复用或进程身份/工作区已变化，拒绝操作该进程。')
            if current != identity or not self._matches_service(process, self.services[name]):
                # Windows can clear a terminating process's command/cwd before
                # the handle disappears. Never signal it based on partial data.
                try:
                    process.wait(timeout=0.05)
                    return None
                except psutil.TimeoutExpired:
                    raise LocalServiceError('PID 已复用或进程身份/工作区已变化，拒绝操作该进程。') from None
            return process
        except psutil.NoSuchProcess:
            return None
        except (psutil.AccessDenied, OSError):
            raise LocalServiceError('无法核实服务进程归属，拒绝操作。') from None

    def _discover(self, name):
        spec = self.services[name]
        matches = []
        for process in psutil.process_iter(['pid', 'name']):
            if not process.info['name'] or 'python' not in process.info['name'].lower():
                continue
            if self._matches_service(process, spec):
                matches.append(process)
            elif spec.scope_tokens:
                try:
                    arguments = process.cmdline()
                    # This weaker check only refuses ambiguous duplicates; it
                    # never grants permission to adopt or stop a process.
                    if _path(process.cwd()) == _path(spec.cwd) and all(token in arguments for token in spec.scope_tokens):
                        raise LocalServiceError('发现不同启动参数的本项目角色进程，拒绝重复启动；请先核实原进程配置。')
                except (psutil.Error, OSError):
                    pass
        # A Windows venv launcher and its child can share the exact same command.
        pids = {process.pid for process in matches}
        roots = []
        for process in matches:
            try:
                if process.ppid() not in pids:
                    roots.append(process)
            except psutil.NoSuchProcess:
                pass
        if len(roots) > 1:
            raise LocalServiceError('发现多个同角色项目进程，无法确定唯一归属，未创建或停止进程。')
        return roots[0] if roots else None

    @contextmanager
    def _lock(self, name):
        filename = self._file(name).with_suffix('.lock')
        if filename.resolve() != filename:
            raise LocalServiceError('服务操作锁不能重定向到其他位置。')
        with filename.open('a+b') as stream:
            if stream.tell() == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise LocalServiceError('另一个服务生命周期操作尚未结束，请稍后重试。') from None
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def status(self, name):
        spec = self.services[name]
        record = self._read(name)
        process = self._process(name, record) if record else self._discover(name)
        if process is None:
            return {'service': name, 'status': 'stopped', 'pid': None, 'ready': False, 'reason': '服务未运行。'}
        readiness = {'ready': None, 'reason': '仅确认进程存活，尚未取得就绪证据。'}
        if spec.probe:
            try:
                readiness = spec.probe()
                if not isinstance(readiness, dict) or readiness.get('ready') not in (True, False, None):
                    raise ValueError('Invalid readiness result')
            except Exception as error:
                readiness = {'ready': False, 'reason': f'就绪检查未通过（{type(error).__name__}）。'}
        return {**readiness, 'service': name, 'status': 'running', 'pid': process.pid, 'managed': record is not None}

    def start(self, name):
        with self._lock(name):
            result = self.status(name)
            if result['status'] == 'running':
                if not result['managed']:
                    self._write(name, self._record(name, psutil.Process(result['pid'])))
                return {**result, 'managed': True, 'reused': True}
            spec = self.services[name]
            environment = os.environ.copy()
            for key, value in (spec.environment or {}).items():
                if value is None:
                    environment.pop(key, None)
                else:
                    environment[key] = value
            logfile = self.state_directory / (name + '.log')
            if logfile.resolve() != logfile:
                raise LocalServiceError('服务日志不能重定向到其他位置。')
            with logfile.open('ab') as output:
                process = subprocess.Popen(spec.command, cwd=spec.cwd, env=environment, stdout=output, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                    start_new_session=os.name != 'nt')
            self.children[name] = process
            try:
                owned = psutil.Process(process.pid)
                self._write(name, self._record(name, owned))
            except psutil.NoSuchProcess:
                process.wait(timeout=self.stop_timeout)
                return {'service': name, 'status': 'failed', 'pid': None, 'ready': False, 'reason': '服务启动后立即退出，请查看本项目服务日志。'}
            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    return {'service': name, 'status': 'failed', 'pid': None, 'ready': False, 'reason': '服务启动后退出，请查看本项目服务日志。'}
                result = self.status(name)
                if result['ready'] is True or result['ready'] is None:
                    return {**result, 'reused': False}
                time.sleep(0.05)
            return {**result, 'reused': False, 'reason': '进程仍在运行，但在等待时间内未就绪。' + result.get('reason', '')}

    def stop(self, name):
        with self._lock(name):
            record = self._read(name)
            if not record:
                if self._discover(name):
                    raise LocalServiceError('项目进程尚未纳管；先运行 start 验证复用后再停止。')
                return {'service': name, 'status': 'stopped', 'pid': None, 'ready': False}
            process = self._process(name, record)
            if process is not None:
                _stop_owned_tree(process, self.workspace, record['identity'], self.stop_timeout)
                child = self.children.get(name)
                if child:
                    child.wait(timeout=self.stop_timeout)
            self._file(name).unlink()
            return {'service': name, 'status': 'stopped', 'pid': None, 'ready': False}

    def restart(self, name):
        self.stop(name)
        return self.start(name)
