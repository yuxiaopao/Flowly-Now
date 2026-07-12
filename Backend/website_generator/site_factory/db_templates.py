"""SQLite / MySQL schema and helper templates for generated sites."""

from __future__ import annotations

from typing import List, Optional

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS inference_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    latency_ms REAL,
    mode TEXT DEFAULT 'image',
    detections_json TEXT
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    rating INTEGER,
    created_at TEXT NOT NULL
);
"""

SCHEMA_MYSQL = """
CREATE TABLE IF NOT EXISTS inference_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at VARCHAR(64) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    latency_ms DOUBLE,
    mode VARCHAR(32) DEFAULT 'image',
    detections_json TEXT
);

CREATE TABLE IF NOT EXISTS app_settings (
    `key` VARCHAR(255) PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT,
    rating INT,
    created_at VARCHAR(64) NOT NULL
);
"""

# Backward-compatible alias
SCHEMA_SQL = SCHEMA_SQLITE

INIT_DB_PY = '''
"""Initialize site database (SQLite default, optional MySQL)."""
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(DB_DIR, 'schema.sql')
DB_PATH = os.path.join(DB_DIR, 'app.db')
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()


def _mysql_config():
    return {
        'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
        'port': int(os.environ.get('MYSQL_PORT', '3306')),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DATABASE', 'flowly_site'),
    }


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    with open(SCHEMA_PATH, encoding='utf-8') as f:
        schema = f.read()
    if DB_ENGINE == 'mysql':
        return _init_mysql(schema)
    return _init_sqlite(schema)


def _init_sqlite(schema):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema)
        for col_sql in (
            "ALTER TABLE inference_logs ADD COLUMN mode TEXT DEFAULT 'image'",
            "ALTER TABLE inference_logs ADD COLUMN detections_json TEXT",
        ):
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass
        conn.commit()
    finally:
        conn.close()
    return DB_PATH


def _init_mysql(schema):
    import pymysql
    cfg = _mysql_config()
    conn = pymysql.connect(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['password'],
        database=cfg['database'],
        charset='utf8mb4',
    )
    try:
        with conn.cursor() as cur:
            for stmt in [s.strip() for s in schema.split(';') if s.strip()]:
                cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()
    return f"mysql://{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"


def log_inference(input_summary, output_summary, latency_ms):
    import datetime
    init_db()
    ts = datetime.datetime.utcnow().isoformat()
    if DB_ENGINE == 'mysql':
        import pymysql
        cfg = _mysql_config()
        conn = pymysql.connect(
            host=cfg['host'], port=cfg['port'], user=cfg['user'],
            password=cfg['password'], database=cfg['database'], charset='utf8mb4',
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO inference_logs (created_at, input_summary, output_summary, latency_ms) VALUES (%s, %s, %s, %s)',
                    (ts, input_summary, output_summary, latency_ms),
                )
            conn.commit()
        finally:
            conn.close()
        return
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            'INSERT INTO inference_logs (created_at, input_summary, output_summary, latency_ms) VALUES (?, ?, ?, ?)',
            (ts, input_summary, output_summary, latency_ms),
        )
        conn.commit()
    finally:
        conn.close()


def log_inference_extended(mode, input_summary, boxes, latency_ms):
    import datetime
    import json
    init_db()
    ts = datetime.datetime.utcnow().isoformat()
    output_summary = f'{len(boxes or [])} detections'
    detections_json = json.dumps(boxes or [], ensure_ascii=False)
    mode = mode or 'image'
    if DB_ENGINE == 'mysql':
        import pymysql
        cfg = _mysql_config()
        conn = pymysql.connect(
            host=cfg['host'], port=cfg['port'], user=cfg['user'],
            password=cfg['password'], database=cfg['database'], charset='utf8mb4',
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO inference_logs (created_at, input_summary, output_summary, latency_ms, mode, detections_json) VALUES (%s, %s, %s, %s, %s, %s)',
                    (ts, input_summary, output_summary, latency_ms, mode, detections_json),
                )
            conn.commit()
        finally:
            conn.close()
        return
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            'INSERT INTO inference_logs (created_at, input_summary, output_summary, latency_ms, mode, detections_json) VALUES (?, ?, ?, ?, ?, ?)',
            (ts, input_summary, output_summary, latency_ms, mode, detections_json),
        )
        conn.commit()
    finally:
        conn.close()


def list_inference_history(limit=50):
    init_db()
    limit = max(1, min(int(limit or 50), 200))
    if DB_ENGINE == 'mysql':
        import pymysql
        cfg = _mysql_config()
        conn = pymysql.connect(
            host=cfg['host'], port=cfg['port'], user=cfg['user'],
            password=cfg['password'], database=cfg['database'], charset='utf8mb4',
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, created_at, input_summary, output_summary, latency_ms, mode, detections_json FROM inference_logs ORDER BY id DESC LIMIT %s',
                    (limit,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()
        return [_row_to_history_item(r) for r in rows]
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            'SELECT id, created_at, input_summary, output_summary, latency_ms, mode, detections_json FROM inference_logs ORDER BY id DESC LIMIT ?',
            (limit,),
        )
        return [_row_to_history_item(tuple(row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_inference_record(record_id):
    import json
    init_db()
    if DB_ENGINE == 'mysql':
        import pymysql
        cfg = _mysql_config()
        conn = pymysql.connect(
            host=cfg['host'], port=cfg['port'], user=cfg['user'],
            password=cfg['password'], database=cfg['database'], charset='utf8mb4',
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, created_at, input_summary, output_summary, latency_ms, mode, detections_json FROM inference_logs WHERE id = %s',
                    (int(record_id),),
                )
                row = cur.fetchone()
        finally:
            conn.close()
        if not row:
            return None
        item = _row_to_history_item(row)
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                'SELECT id, created_at, input_summary, output_summary, latency_ms, mode, detections_json FROM inference_logs WHERE id = ?',
                (int(record_id),),
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if not row:
            return None
        item = _row_to_history_item(tuple(row))
    try:
        item['detections'] = json.loads(item.pop('detections_json') or '[]')
    except Exception:
        item['detections'] = []
    return item


def _row_to_history_item(row):
    return {
        'id': row[0],
        'created_at': row[1],
        'input_summary': row[2],
        'output_summary': row[3],
        'latency_ms': row[4],
        'mode': row[5] if len(row) > 5 else 'image',
        'detections_json': row[6] if len(row) > 6 else '[]',
    }
'''


def normalize_db_engine(value: Optional[str]) -> str:
    engine = (value or 'sqlite').strip().lower()
    return 'mysql' if engine == 'mysql' else 'sqlite'


def get_schema_sql(db_engine: str = 'sqlite') -> str:
    return SCHEMA_MYSQL if normalize_db_engine(db_engine) == 'mysql' else SCHEMA_SQLITE


def get_init_db_py(db_engine: str = 'sqlite') -> str:
    return INIT_DB_PY.strip() + '\n'


def extra_requirements(db_engine: str = 'sqlite') -> List[str]:
    if normalize_db_engine(db_engine) == 'mysql':
        return ['pymysql>=1.1.0']
    return []
