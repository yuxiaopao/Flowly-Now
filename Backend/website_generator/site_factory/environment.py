"""Environment provision checks for generated sites."""

import os
import platform
import shutil
import socket
import sys
from typing import Any, Dict, List, Optional, Tuple


PORT_RANGE_START = 49152
PORT_RANGE_END = 49252


def pick_free_port(start: int = PORT_RANGE_START, end: int = PORT_RANGE_END) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start


def run_environment_checks(
    output_dir: str,
    model_path: str = '',
    site_id: str = '',
    runtime_mode: str = 'desktop',
    assigned_port: Optional[int] = None,
    db_engine: str = '',
    mysql_config: Optional[Dict[str, Any]] = None,
    custom_paths: Optional[List[str]] = None,
    require_path_grant: bool = False,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(key: str, label: str, ok: bool, detail: str):
        checks.append({'key': key, 'label': label, 'ok': ok, 'detail': detail})

    py_ver = f'{sys.version_info.major}.{sys.version_info.minor}'
    add('python', 'Python 版本', True, py_ver)

    granted_paths: List[str] = []
    if output_dir:
        exists = os.path.isdir(output_dir)
        add('output_dir', '输出目录', exists, output_dir if exists else f'目录不存在: {output_dir}')
        if exists:
            try:
                test_path = os.path.join(output_dir, '.flowly_write_test')
                with open(test_path, 'w', encoding='utf-8') as f:
                    f.write('ok')
                os.remove(test_path)
                add('output_writable', '目录可写', True, '读写正常')
                granted_paths.append(os.path.abspath(output_dir))
            except OSError as e:
                add('output_writable', '目录可写', False, str(e))
    else:
        add('output_dir', '输出目录', False, '未指定 outputDir')

    # Custom path permission grants (user-declared roots for datasets/weights/logs)
    for raw in custom_paths or []:
        path = str(raw or '').strip()
        if not path:
            continue
        abs_path = os.path.abspath(path)
        if os.path.isdir(abs_path):
            try:
                probe = os.path.join(abs_path, '.flowly_grant_probe')
                with open(probe, 'w', encoding='utf-8') as f:
                    f.write('ok')
                os.remove(probe)
                add(f'path_grant:{abs_path}', f'路径授权 {abs_path}', True, '可读可写')
                granted_paths.append(abs_path)
            except OSError as e:
                add(f'path_grant:{abs_path}', f'路径授权 {abs_path}', False, str(e))
        elif os.path.isfile(abs_path):
            add(f'path_grant:{abs_path}', f'路径授权 {abs_path}', True, '文件存在（只读检查）')
            granted_paths.append(abs_path)
        else:
            add(f'path_grant:{abs_path}', f'路径授权 {abs_path}', False, '路径不存在')

    if require_path_grant and not granted_paths:
        add('path_grant_required', '路径授权', False, '已开启 requirePathGrant，但未授权任何可用路径')

    backend_dir = os.path.join(output_dir, 'backend') if output_dir else ''
    app_py = os.path.join(backend_dir, 'app.py')
    add('backend_app', 'Flask 后端', os.path.isfile(app_py), app_py if os.path.isfile(app_py) else '缺少 backend/app.py')

    if model_path:
        mp_ok = os.path.isfile(model_path)
        add('model_path', '模型权重', mp_ok, model_path if mp_ok else f'文件不存在: {model_path}')
        if mp_ok:
            granted_paths.append(os.path.abspath(model_path))
    else:
        add('model_path', '模型权重', False, '未指定 modelPath（将使用 Demo 模式）')

    disk_gb = shutil.disk_usage(output_dir or os.getcwd()).free / (1024 ** 3)
    add('disk', '磁盘空间', disk_gb >= 1.0, f'剩余约 {disk_gb:.1f} GB')

    cuda_available = False
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_available else 'N/A'
        add('cuda', 'CUDA/GPU', True, gpu_name if cuda_available else '未检测到 GPU（将使用 CPU）')
    except ImportError:
        add('cuda', 'CUDA/GPU', True, 'PyTorch 未安装，推理可能为 Demo 模式')

    port = assigned_port or pick_free_port()
    add('port', '分配端口', True, str(port))

    engine = (db_engine or _read_db_engine(output_dir) or 'mysql').lower()
    if engine == 'mysql':
        mysql_cfg = mysql_config or _default_mysql_config_from_env()
        ping_ok, ping_detail = _mysql_ping(mysql_cfg)
        add('mysql_ping', 'MySQL 连接', ping_ok, ping_detail)
        if ping_ok:
            schema_ok, schema_detail = _mysql_schema_ready(mysql_cfg)
            add('mysql_schema', 'MySQL 表结构', schema_ok, schema_detail)
        # Persist engine into generated config when possible
        _persist_db_engine(output_dir, 'mysql', mysql_cfg)

    # Desktop demos: MySQL/CUDA/weights soft-warn so pipeline can continue;
    # operators still see failed checks in the report.
    soft_fail_keys = {'model_path', 'cuda', 'mysql_ping', 'mysql_schema'}
    if (runtime_mode or 'desktop').lower() != 'desktop':
        soft_fail_keys = {'model_path', 'cuda'}
    ready = all(c['ok'] for c in checks if c['key'] not in soft_fail_keys)

    # Deduplicate granted paths while preserving order
    seen = set()
    unique_granted = []
    for p in granted_paths:
        if p not in seen:
            seen.add(p)
            unique_granted.append(p)

    manifest = {
        'python': py_ver,
        'platform': platform.system(),
        'cuda_available': cuda_available,
        'disk_free_gb': round(disk_gb, 2),
        'assigned_port': port,
        'paths_granted': unique_granted,
        'custom_paths': list(custom_paths or []),
        'require_path_grant': bool(require_path_grant),
        'runtime_mode': runtime_mode,
        'site_id': site_id,
        'backend_dir': backend_dir,
        'db_engine': engine or 'mysql',
        'mysql_config': {k: v for k, v in (mysql_config or _default_mysql_config_from_env()).items() if k != 'password'},
        'stack': {'frontend': 'vue', 'backend': 'flask', 'database': engine or 'mysql'},
    }

    return {
        'ready': ready,
        'runtime_manifest': manifest,
        'checks': checks,
        'assigned_port': port,
    }


def _default_mysql_config_from_env() -> Dict[str, Any]:
    return {
        'host': os.environ.get('MYSQL_HOST') or os.environ.get('DB_HOST') or '127.0.0.1',
        'port': int(os.environ.get('MYSQL_PORT') or os.environ.get('DB_PORT') or 3306),
        'user': os.environ.get('MYSQL_USER') or os.environ.get('DB_USER') or 'root',
        'password': os.environ.get('MYSQL_PASSWORD') or os.environ.get('DB_PASSWORD') or '',
        'database': os.environ.get('MYSQL_DATABASE') or os.environ.get('DB_NAME') or 'flowly_site',
    }


def _persist_db_engine(output_dir: str, engine: str, mysql_config: Optional[Dict[str, Any]] = None) -> None:
    if not output_dir:
        return
    cfg_path = os.path.join(output_dir, 'backend', 'config.json')
    if not os.path.isfile(cfg_path):
        return
    try:
        import json
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
        cfg['db_engine'] = engine
        cfg['dbEngine'] = engine
        if mysql_config:
            cfg['mysql'] = {k: v for k, v in mysql_config.items() if k != 'password'}
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _read_db_engine(output_dir: str) -> str:
    if not output_dir:
        return 'mysql'
    cfg_path = os.path.join(output_dir, 'backend', 'config.json')
    if not os.path.isfile(cfg_path):
        return 'mysql'
    try:
        import json
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
        return str(cfg.get('db_engine') or cfg.get('dbEngine') or 'mysql')
    except Exception:
        return 'mysql'


def _mysql_ping(mysql_config: Dict[str, Any]) -> Tuple[bool, str]:
    host = mysql_config.get('host') or '127.0.0.1'
    port = int(mysql_config.get('port') or 3306)
    user = mysql_config.get('user') or 'root'
    password = mysql_config.get('password') or ''
    database = mysql_config.get('database') or 'flowly_site'
    if not user or not database:
        return False, 'MySQL 配置不完整（需 user/database）'
    try:
        import pymysql
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, charset='utf8mb4', connect_timeout=5,
        )
        conn.close()
        return True, f'{user}@{host}:{port}/{database}'
    except ImportError:
        return False, 'PyMySQL 未安装'
    except Exception as exc:
        return False, str(exc)


def _mysql_schema_ready(mysql_config: Dict[str, Any]) -> Tuple[bool, str]:
    host = mysql_config.get('host') or '127.0.0.1'
    port = int(mysql_config.get('port') or 3306)
    user = mysql_config.get('user') or 'root'
    password = mysql_config.get('password') or ''
    database = mysql_config.get('database') or 'flowly_site'
    try:
        import pymysql
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, charset='utf8mb4', connect_timeout=5,
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES LIKE 'inference_logs'")
                row = cur.fetchone()
            return (True, 'inference_logs 已存在') if row else (False, '缺少 inference_logs 表，请运行 init_db')
        finally:
            conn.close()
    except Exception as exc:
        return False, str(exc)
