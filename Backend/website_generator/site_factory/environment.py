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
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(key: str, label: str, ok: bool, detail: str):
        checks.append({'key': key, 'label': label, 'ok': ok, 'detail': detail})

    py_ver = f'{sys.version_info.major}.{sys.version_info.minor}'
    add('python', 'Python 版本', True, py_ver)

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
            except OSError as e:
                add('output_writable', '目录可写', False, str(e))
    else:
        add('output_dir', '输出目录', False, '未指定 outputDir')

    backend_dir = os.path.join(output_dir, 'backend') if output_dir else ''
    app_py = os.path.join(backend_dir, 'app.py')
    add('backend_app', 'Flask 后端', os.path.isfile(app_py), app_py if os.path.isfile(app_py) else '缺少 backend/app.py')

    if model_path:
        mp_ok = os.path.isfile(model_path)
        add('model_path', '模型权重', mp_ok, model_path if mp_ok else f'文件不存在: {model_path}')
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

    engine = (db_engine or _read_db_engine(output_dir)).lower()
    if engine == 'mysql':
        mysql_cfg = mysql_config or {}
        ping_ok, ping_detail = _mysql_ping(mysql_cfg)
        add('mysql_ping', 'MySQL 连接', ping_ok, ping_detail)
        if ping_ok:
            schema_ok, schema_detail = _mysql_schema_ready(mysql_cfg)
            add('mysql_schema', 'MySQL 表结构', schema_ok, schema_detail)

    ready = all(c['ok'] for c in checks if c['key'] not in ('model_path', 'cuda'))

    manifest = {
        'python': py_ver,
        'platform': platform.system(),
        'cuda_available': cuda_available,
        'disk_free_gb': round(disk_gb, 2),
        'assigned_port': port,
        'paths_granted': [output_dir] if output_dir else [],
        'runtime_mode': runtime_mode,
        'site_id': site_id,
        'backend_dir': backend_dir,
        'db_engine': engine or 'sqlite',
        'mysql_config': {k: v for k, v in (mysql_config or {}).items() if k != 'password'},
    }

    return {
        'ready': ready,
        'runtime_manifest': manifest,
        'checks': checks,
        'assigned_port': port,
    }


def _read_db_engine(output_dir: str) -> str:
    if not output_dir:
        return 'sqlite'
    cfg_path = os.path.join(output_dir, 'backend', 'config.json')
    if not os.path.isfile(cfg_path):
        return 'sqlite'
    try:
        import json
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
        return str(cfg.get('db_engine') or cfg.get('dbEngine') or 'sqlite')
    except Exception:
        return 'sqlite'


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
