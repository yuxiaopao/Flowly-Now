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
