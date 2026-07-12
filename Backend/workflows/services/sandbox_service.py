"""
Docker-based sandbox for secure code execution.

Provides production-grade code execution with:
- Docker container isolation
- Resource limits (memory, CPU, time)
- Network isolation
- Container pool for performance optimization
- Fallback to subprocess if Docker is unavailable
"""

import json
import logging
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import queue
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == 'Windows'

# Check if resource module is available (not available on Windows)
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False


class SandboxError(Exception):
    """Base exception for sandbox errors."""
    pass


class SandboxTimeout(SandboxError):
    """Raised when code execution exceeds timeout."""
    pass


class SandboxMemoryLimit(SandboxError):
    """Raised when code exceeds memory limit."""
    pass


class SandboxContainerError(SandboxError):
    """Raised when Docker container fails."""
    pass


class DockerNotAvailable(SandboxError):
    """Raised when Docker is not available."""
    pass


@dataclass
class ContainerConfig:
    """Configuration for a sandbox container."""
    image: str = 'python:3.12-slim'
    memory_limit: str = '128m'
    cpu_limit: float = 0.5
    timeout_seconds: int = 30
    network_disabled: bool = True
    read_only: bool = True
    auto_remove: bool = True
    working_dir: str = '/code'


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: int = 0
    container_id: Optional[str] = None
    memory_used: Optional[str] = None
    cpu_time: Optional[float] = None


# ─────────────────────────────────────────────────────────────────
# Docker Container Pool
# ─────────────────────────────────────────────────────────────────

class ContainerPool:
    """
    Pool of pre-warmed Docker containers for fast execution.
    
    Features:
    - Lazy initialization of containers
    - Automatic cleanup of idle containers
    - Thread-safe pool management
    - Configurable pool size
    """
    
    def __init__(
        self,
        pool_size: int = 3,
        config: Optional[ContainerConfig] = None,
    ):
        self.pool_size = pool_size
        self.config = config or ContainerConfig()
        self._containers: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._docker_client = None
        self._initialized = False
        self._total_created = 0
        self._total_used = 0
    
    @property
    def docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            import docker
            return True
        except ImportError:
            return False
    
    def _get_client(self):
        """Get or create Docker client."""
        if self._docker_client is None:
            try:
                import docker
                self._docker_client = docker.from_env()
                self._docker_client.ping()
            except Exception as e:
                logger.warning(f"Docker not available: {e}")
                raise DockerNotAvailable(str(e))
        return self._docker_client
    
    def initialize(self) -> bool:
        """Initialize the container pool."""
        if self._initialized:
            return True
        
        try:
            client = self._get_client()
            
            # Pre-pull the image
            try:
                client.images.pull(self.config.image)
            except Exception:
                pass  # Image may already exist
            
            # Create initial containers
            for _ in range(self.pool_size):
                try:
                    container = self._create_container()
                    if container:
                        self._containers.put(container)
                        self._total_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create pool container: {e}")
            
            self._initialized = True
            logger.info(f"Container pool initialized with {self._containers.qsize()} containers")
            return True
            
        except DockerNotAvailable:
            logger.warning("Docker not available, will use subprocess fallback")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize container pool: {e}")
            return False
    
    def _create_container(self):
        """Create a new container."""
        client = self._get_client()
        
        # Container host config with resource limits
        host_config = client.api.create_host_config(
            mem_limit=self.config.memory_limit,
            cpu_period=100000,
            cpu_quota=int(100000 * self.config.cpu_limit),
            network_mode='none' if self.config.network_disabled else 'bridge',
            read_only=self.config.read_only,
            auto_remove=self.config.auto_remove,
            tmpfs={'/tmp': 'rw,noexec,nosuid,size=64m'},
        )
        
        container = client.api.create_container(
            image=self.config.image,
            command='sleep infinity',
            working_dir=self.config.working_dir,
            host_config=host_config,
            detach=True,
        )
        
        # Start the container
        client.api.start(container['Id'])
        
        return {
            'id': container['Id'],
            'created_at': time.time(),
            'client': client,
            'api': client.api,
        }
    
    def get_container(self, timeout: float = 10.0) -> Optional[Dict]:
        """Get a container from the pool."""
        try:
            return self._containers.get(timeout=timeout)
        except queue.Empty:
            # Try to create a new one
            try:
                container = self._create_container()
                if container:
                    self._total_created += 1
                    return container
            except Exception as e:
                logger.error(f"Failed to create emergency container: {e}")
            return None
    
    def return_container(self, container: Dict) -> None:
        """Return a container to the pool."""
        if container is None:
            return
        
        try:
            # Reset the container state
            api = container['api']
            container_id = container['id']
            
            # Stop any running process
            try:
                api.kill(container_id)
            except Exception:
                pass
            
            # Remove the container
            try:
                api.remove_container(container_id, force=True)
            except Exception:
                pass
            
            # Create a fresh container to replace it
            try:
                new_container = self._create_container()
                if new_container:
                    self._containers.put(new_container)
                    self._total_created += 1
            except Exception:
                pass
                
        except Exception as e:
            logger.warning(f"Error returning container to pool: {e}")
    
    def shutdown(self):
        """Shutdown the container pool."""
        while not self._containers.empty():
            try:
                container = self._containers.get_nowait()
                self.return_container(container)
            except queue.Empty:
                break
        
        if self._docker_client:
            try:
                self._docker_client.close()
            except Exception:
                pass
            self._docker_client = None
        
        self._initialized = False
    
    def get_stats(self) -> Dict:
        """Get pool statistics."""
        return {
            'pool_size': self.pool_size,
            'available': self._containers.qsize(),
            'total_created': self._total_created,
            'total_used': self._total_used,
            'initialized': self._initialized,
        }


# ─────────────────────────────────────────────────────────────────
# Subprocess Fallback (for when Docker is unavailable)
# ─────────────────────────────────────────────────────────────────

class SubprocessSandbox:
    """
    Subprocess-based sandbox fallback when Docker is unavailable.
    
    Provides process isolation with resource limits via resource module.
    """
    
    SAFE_BUILTINS = {
        'True': True, 'False': False, 'None': None,
        'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
        'bytearray': bytearray, 'bytes': bytes, 'callable': callable,
        'chr': chr, 'dict': dict, 'divmod': divmod,
        'enumerate': enumerate, 'filter': filter, 'float': float,
        'format': format, 'frozenset': frozenset, 'hash': hash,
        'hex': hex, 'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
        'iter': iter, 'len': len, 'list': list, 'map': map, 'max': max,
        'min': min, 'oct': oct, 'ord': ord, 'pow': pow, 'range': range,
        'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
        'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
        'tuple': tuple, 'zip': zip, 'type': type, 'vars': vars,
    }
    
    BLOCKED_NAMES = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'http', 'ftplib',
        'telnetlib', 'poplib', 'imaplib', 'smtplib', 'email', 'xml',
        'pickle', 'marshal', 'shelve', 'dbm', 'sqlite3', 'anydbm',
        'threading', 'multiprocessing', 'concurrent', 'asyncio', 'ctypes',
        'cffi', 'winreg', '_winreg', 'commands', 'pty', 'tty',
        'termios', 'fcntl', 'resource', 'signal', 'pwd', 'grp',
        'spwd', 'crypt', 'disk_usage', 'getpass', 'builtins',
        '__import__', 'eval', 'exec', 'compile', 'open', 'file',
        'input', 'print', 'breakpoint', 'exit', 'quit',
    }
    
    def __init__(self, timeout: int = 30, max_memory_mb: int = 128):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.max_file_size = 1 * 1024 * 1024
        self.max_processes = 1
    
    def execute(self, code: str, input_data: Dict[str, Any]) -> ExecutionResult:
        """Execute code in subprocess sandbox."""
        start_time = time.time()
        
        if not code or not code.strip():
            return ExecutionResult(
                success=False,
                error='No code provided',
                error_type='validation',
                duration_ms=int((time.time() - start_time) * 1000)
            )
        
        wrapper_code = self._build_wrapper(code)
        fd, temp_path = tempfile.mkstemp(suffix='.py', prefix='sandbox_')
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(wrapper_code)
            
            def set_limits():
                if RESOURCE_AVAILABLE and not IS_WINDOWS:
                    resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_mb * 1024 * 1024, resource.RLIM_INFINITY))
                    resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, resource.RLIM_INFINITY))
                    resource.setrlimit(resource.RLIMIT_FSIZE, (self.max_file_size, self.max_file_size))
                    resource.setrlimit(resource.RLIMIT_NPROC, (self.max_processes, self.max_processes))
            
            input_json = json.dumps(input_data, ensure_ascii=False)
            python_exe = sys.executable
            
            try:
                if IS_WINDOWS:
                    minimal_env = {
                        'PATH': os.environ.get('PATH', ''),
                        'SYSTEMROOT': os.environ.get('SYSTEMROOT', ''),
                        'TEMP': os.environ.get('TEMP', ''),
                        'TMP': os.environ.get('TMP', ''),
                    }
                    proc = subprocess.Popen(
                        [python_exe, temp_path],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=minimal_env
                    )
                else:
                    proc = subprocess.Popen(
                        [python_exe, temp_path],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        preexec_fn=set_limits,
                        env={}
                    )
                
                stdout, stderr = proc.communicate(
                    input=input_json.encode('utf-8'),
                    timeout=self.timeout + 5
                )
                exit_code = proc.returncode
                
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return ExecutionResult(
                    success=False,
                    error=f'Execution timeout ({self.timeout}s)',
                    error_type='timeout',
                    duration_ms=int((time.time() - start_time) * 1000)
                )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if exit_code == 0 and stdout:
                try:
                    result = json.loads(stdout.decode('utf-8'))
                    return ExecutionResult(
                        success=True,
                        output=result.get('output', {}),
                        duration_ms=duration_ms
                    )
                except json.JSONDecodeError:
                    return ExecutionResult(
                        success=False,
                        error=f'Invalid output format: {stdout.decode("utf-8")[:200]}',
                        error_type='output_format',
                        duration_ms=duration_ms
                    )
            else:
                error_msg = stderr.decode('utf-8', errors='replace') if stderr else 'Unknown error'
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + '...'
                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    error_type='runtime',
                    duration_ms=duration_ms
                )
                
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    def _build_wrapper(self, code: str) -> str:
        """Build wrapper script with restricted builtins."""
        blocked = repr(self.BLOCKED_NAMES)
        
        return f'''
import sys
import json
import traceback
import types

import math
import re
import datetime
import collections
import itertools
import functools
import decimal
import fractions

import builtins as _b
_orig_import = _b.__import__
_blocked = {blocked}

def _safe_import(name, *args, **kwargs):
    if name.split('.')[0] in _blocked:
        raise ImportError(f"Module '{{name}}' is not allowed")
    return _orig_import(name, *args, **kwargs)

_b.__import__ = _safe_import

_safe_builtins = {{}}
for _name in dir(_b):
    if _name.startswith('_'):
        continue
    if _name not in _blocked:
        try:
            _safe_builtins[_name] = getattr(_b, _name)
        except (AttributeError, TypeError):
            pass

input_json = sys.stdin.read()
input_data = json.loads(input_json) if input_json.strip() else {{}}

_safe_ns = {{
    '__builtins__': _safe_builtins,
    'input': input_data,
    'output': {{}},
    'math': math,
    're': re,
    'datetime': datetime,
    'collections': collections,
    'itertools': itertools,
    'functools': functools,
    'decimal': decimal,
    'fractions': fractions,
}}

try:
    exec({code!r}, _safe_ns, _safe_ns)
    output = _safe_ns.get('output', {{}})
    if not output:
        intermediate = {{k: v for k, v in _safe_ns.items() 
                  if not k.startswith('_') 
                  and k not in ['input', 'output', 'math', 're', 'datetime', 'collections', 
                               'itertools', 'functools', 'decimal', 'fractions']
                  and not callable(v)
                  and not isinstance(v, types.ModuleType)}}
        if intermediate:
            output = intermediate
except SystemExit:
    output = {{"__info__": "SystemExit called"}}
except Exception:
    tb = traceback.format_exc()
    sys.stderr.write(tb)
    sys.exit(1)

result = {{"output": output}}
sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str))
'''


# ─────────────────────────────────────────────────────────────────
# Docker Sandbox
# ─────────────────────────────────────────────────────────────────

class DockerSandbox:
    """
    Docker-based code execution sandbox.
    
    Features:
    - Container isolation for code execution
    - Memory, CPU, and time limits
    - Network isolation
    - Container pool for performance
    - Execution result streaming
    """
    
    def __init__(self, config: Optional[ContainerConfig] = None):
        self.config = config or ContainerConfig()
        self._pool: Optional[ContainerPool] = None
        self._docker_available = self._check_docker()
        self._subprocess_sandbox = SubprocessSandbox(
            timeout=self.config.timeout_seconds,
            max_memory_mb=int(self.config.memory_limit.rstrip('m'))
        )
    
    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            logger.info("Docker not available, using subprocess fallback")
            return False
    
    def _get_pool(self) -> ContainerPool:
        """Get or create container pool."""
        if self._pool is None:
            self._pool = ContainerPool(
                pool_size=3,
                config=self.config,
            )
            self._pool.initialize()
        return self._pool
    
    def execute(self, code: str, input_data: Dict[str, Any]) -> ExecutionResult:
        """
        Execute code in Docker container or subprocess fallback.
        
        Args:
            code: Python code to execute
            input_data: Input data passed as `input` variable
            
        Returns:
            ExecutionResult with success status, output, and metrics
        """
        start_time = time.time()
        
        # Validate code first
        validation = self.validate_code(code)
        if not validation['valid']:
            return ExecutionResult(
                success=False,
                error=', '.join(validation['errors']),
                error_type='validation',
                duration_ms=int((time.time() - start_time) * 1000)
            )
        
        if self._docker_available:
            try:
                return self._execute_in_container(code, input_data, start_time)
            except DockerNotAvailable:
                logger.info("Falling back to subprocess sandbox")
                self._docker_available = False
            except Exception as e:
                logger.warning(f"Docker execution failed, falling back: {e}")
                self._docker_available = False
        
        # Fallback to subprocess
        return self._execute_in_subprocess(code, input_data, start_time)
    
    def _execute_in_container(
        self,
        code: str,
        input_data: Dict[str, Any],
        start_time: float
    ) -> ExecutionResult:
        """Execute code in Docker container."""
        pool = self._get_pool()
        container = pool.get_container(timeout=10.0)
        
        if container is None:
            raise DockerNotAvailable("No containers available")
        
        try:
            container_id = container['id']
            api = container['api']
            
            # Prepare execution script
            exec_code = self._build_container_script(code, input_data)
            
            # Execute in container
            exec_result = api.exec_create(
                container_id,
                cmd=['python', '-c', exec_code],
                stdout=True,
                stderr=True,
            )
            
            timeout_buffer = 5
            start_wait = time.time()
            output = api.exec_start(exec_result['Id'], stream=False)
            
            while True:
                inspect = api.exec_inspect(exec_result['Id'])
                if not inspect.get('Running', False):
                    break
                if time.time() - start_wait > self.config.timeout_seconds + timeout_buffer:
                    raise SandboxTimeout(f"Execution timeout ({self.config.timeout_seconds}s)")
                time.sleep(0.1)
            
            exit_code = inspect.get('ExitCode', 1)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if exit_code == 0:
                try:
                    result = json.loads(output.decode('utf-8'))
                    return ExecutionResult(
                        success=True,
                        output=result.get('output', {}),
                        duration_ms=duration_ms,
                        container_id=container_id[:12],
                    )
                except json.JSONDecodeError:
                    return ExecutionResult(
                        success=False,
                        error=f'Invalid output: {output.decode("utf-8")[:200]}',
                        error_type='output_format',
                        duration_ms=duration_ms,
                        container_id=container_id[:12],
                    )
            else:
                raw_out = output.decode('utf-8', errors='replace')
                try:
                    parsed = json.loads(raw_out)
                    if isinstance(parsed, dict) and 'output' in parsed:
                        return ExecutionResult(
                            success=True,
                            output=parsed.get('output', {}),
                            duration_ms=duration_ms,
                            container_id=container_id[:12],
                        )
                except json.JSONDecodeError:
                    pass
                error_msg = raw_out
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + '...'
                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    error_type='runtime',
                    duration_ms=duration_ms,
                    container_id=container_id[:12],
                )
                
        finally:
            # Always return container to pool
            pool.return_container(container)
    
    def _execute_in_subprocess(
        self,
        code: str,
        input_data: Dict[str, Any],
        start_time: float
    ) -> ExecutionResult:
        """Execute code in subprocess sandbox."""
        return self._subprocess_sandbox.execute(code, input_data)
    
    def _build_container_script(self, code: str, input_data: Dict[str, Any]) -> str:
        """Build execution script for container."""
        escaped_code = code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        # Embed JSON as a string literal — raw json.dumps() uses null/true/false which are invalid Python.
        input_json_literal = json.dumps(json.dumps(input_data, ensure_ascii=False))
        
        return f'''
import json
import sys

input_data = json.loads({input_json_literal})
code = "{escaped_code}"

# Safe modules for container execution
import math
import re
import datetime
import collections
import itertools
import functools
import decimal
import fractions

_namespace = {{
    '__builtins__': {{}},
    'input': input_data,
    'output': {{}},
    'math': math,
    're': re,
    'datetime': datetime,
    'collections': collections,
    'itertools': itertools,
    'functools': functools,
    'decimal': decimal,
    'fractions': fractions,
}}

try:
    exec(code, _namespace, _namespace)
    output = _namespace.get('output', {{}})
    if not output:
        import types
        output = {{k: v for k, v in _namespace.items() 
                  if not k.startswith('_') 
                  and k not in ['input', 'output', 'math', 're', 'datetime', 'collections', 
                               'itertools', 'functools', 'decimal', 'fractions']
                  and not callable(v)
                  and not isinstance(v, types.ModuleType)}}
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(json.dumps({{"output": output}}, ensure_ascii=False, default=str))
'''
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """Pre-validate code for security issues."""
        errors = []
        
        dangerous_patterns = [
            ('import os', 'Disallowed module: os'),
            ('from os ', 'Disallowed module: os'),
            ('import subprocess', 'Disallowed module: subprocess'),
            ('from subprocess ', 'Disallowed module: subprocess'),
            ('import sys', 'Disallowed module: sys'),
            ('from sys ', 'Disallowed module: sys'),
            ('import threading', 'Disallowed module: threading'),
            ('import multiprocessing', 'Disallowed module: multiprocessing'),
            ('__import__', 'Disallowed builtin: __import__'),
            ('eval(', 'Disallowed builtin: eval'),
            ('exec(', 'Disallowed builtin: exec'),
            ('open(', 'Disallowed builtin: open'),
            ('file(', 'Disallowed builtin: file'),
            ('compile(', 'Disallowed builtin: compile'),
            ('input(', 'Disallowed builtin: input'),
            ('import socket', 'Disallowed module: socket'),
            ('import urllib', 'Disallowed module: urllib'),
            ('import http', 'Disallowed module: http'),
            ('resource.setrlimit', 'Disallowed: resource manipulation'),
            ('resource.getrlimit', 'Disallowed: resource manipulation'),
            ('signal.alarm', 'Disallowed: signal manipulation'),
            ('os.system', 'Disallowed: os.system'),
            ('os.popen', 'Disallowed: os.popen'),
            ('os.spawn', 'Disallowed: os.spawn'),
            ('os.fork', 'Disallowed: os.fork'),
            ('subprocess.run', 'Disallowed: subprocess'),
            ('subprocess.call', 'Disallowed: subprocess'),
            ('subprocess.Popen', 'Disallowed: subprocess'),
        ]
        
        for pattern, msg in dangerous_patterns:
            if pattern in code:
                errors.append(msg)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_stats(self) -> Dict:
        """Get sandbox statistics."""
        stats = {
            'docker_available': self._docker_available,
            'config': {
                'image': self.config.image,
                'memory_limit': self.config.memory_limit,
                'cpu_limit': self.config.cpu_limit,
                'timeout_seconds': self.config.timeout_seconds,
                'network_disabled': self.config.network_disabled,
            },
        }
        
        if self._pool:
            stats['pool'] = self._pool.get_stats()
        
        return stats
    
    def shutdown(self):
        """Shutdown the sandbox."""
        if self._pool:
            self._pool.shutdown()


# ─────────────────────────────────────────────────────────────────
# Main SandboxService (Facade)
# ─────────────────────────────────────────────────────────────────

class SandboxService:
    """
    Production-grade sandbox service for secure code execution.
    
    Features:
    - Docker container isolation (primary)
    - Subprocess fallback (secondary)
    - Container pool for performance
    - Configurable resource limits
    - Comprehensive security validation
    
    Usage:
        service = SandboxService()
        result = service.execute(code="print(input['x'] + input['y'])",
                                  input_data={'x': 1, 'y': 2})
        print(result.output)  # {'result': 3}
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_memory_mb: int = 128,
        cpu_limit: float = 0.5,
        docker_image: str = 'python:3.12-slim',
    ):
        """
        Initialize sandbox service.
        
        Args:
            timeout: Execution timeout in seconds (default: 30)
            max_memory_mb: Memory limit in MB (default: 128)
            cpu_limit: CPU limit as fraction (default: 0.5 = 50%)
            docker_image: Docker image for container isolation
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.cpu_limit = cpu_limit
        self.docker_image = docker_image
        
        # Create Docker sandbox configuration
        config = ContainerConfig(
            image=docker_image,
            memory_limit=f'{max_memory_mb}m',
            cpu_limit=cpu_limit,
            timeout_seconds=timeout,
            network_disabled=True,
        )
        
        self._docker_sandbox = DockerSandbox(config)
        
        # Backward compatibility: also expose subprocess-only mode
        self._subprocess_sandbox = SubprocessSandbox(
            timeout=timeout,
            max_memory_mb=max_memory_mb,
        )
    
    def execute(self, code: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute user code in sandbox.
        
        Args:
            code: User's Python code to execute
            input_data: Input data passed as `input` variable
            
        Returns:
            Dict with keys:
            - success (bool): Whether execution succeeded
            - output (dict): Execution output
            - error (str): Error message if failed
            - error_type (str): Type of error
            - duration_ms (int): Execution duration in ms
            - container_id (str): Docker container ID (if used)
        """
        result = self._docker_sandbox.execute(code, input_data)
        
        return {
            'success': result.success,
            'output': result.output,
            'error': result.error,
            'error_type': result.error_type,
            'duration_ms': result.duration_ms,
            'container_id': result.container_id,
        }
    
    def execute_subprocess_only(self, code: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute in subprocess-only mode (no Docker).
        
        Useful for environments where Docker is not available.
        """
        result = self._subprocess_sandbox.execute(code, input_data)
        
        return {
            'success': result.success,
            'output': result.output,
            'error': result.error,
            'error_type': result.error_type,
            'duration_ms': result.duration_ms,
        }
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code before execution."""
        return self._docker_sandbox.validate_code(code)
    
    def get_stats(self) -> Dict:
        """Get sandbox statistics."""
        return self._docker_sandbox.get_stats()
    
    def shutdown(self):
        """Shutdown sandbox and release resources."""
        self._docker_sandbox.shutdown()
    
    @property
    def docker_available(self) -> bool:
        """Check if Docker is available."""
        return self._docker_sandbox._docker_available


# ─────────────────────────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────────────────────────

_sandbox_service: Optional[SandboxService] = None
_sandbox_lock = threading.Lock()


def get_sandbox_service() -> SandboxService:
    """Get or create singleton sandbox service instance."""
    global _sandbox_service
    
    if _sandbox_service is None:
        with _sandbox_lock:
            if _sandbox_service is None:
                _sandbox_service = SandboxService()
    
    return _sandbox_service


@contextmanager
def sandbox_context(timeout: int = 30, max_memory_mb: int = 128):
    """
    Context manager for sandbox execution.
    
    Usage:
        with sandbox_context(timeout=60) as sandbox:
            result = sandbox.execute(code, input_data)
    """
    sandbox = SandboxService(timeout=timeout, max_memory_mb=max_memory_mb)
    try:
        yield sandbox
    finally:
        sandbox.shutdown()
