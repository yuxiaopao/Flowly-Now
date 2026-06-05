import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, 'Backend')

import django
django.setup()

from django.db import connection
from datetime import datetime
import os

with connection.cursor() as cur:
    # Check migrations for workflows app
    cur.execute("SELECT app, name, applied FROM django_migrations WHERE app='workflows' ORDER BY applied")
    print('Workflows migrations:')
    for r in cur.fetchall():
        print(f'  {r[0]}.{r[1]} - {r[2]}')
    
    # Check if ExecutionCacheConfig table exists
    cur.execute("SHOW TABLES LIKE 'execution_cache_config'")
    exists = cur.fetchone()
    print(f'\nexecution_cache_config table exists: {exists is not None}')
    
    # Check all migrations count
    cur.execute("SELECT COUNT(*) FROM django_migrations")
    print(f'\nTotal migrations tracked: {cur.fetchone()[0]}')
    
    # Mark migration 0010 as applied since the table exists
    if exists:
        cur.execute(
            "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
            ('workflows', '0010_execution_cache', datetime.now())
        )
        print('Marked 0010_execution_cache as applied')
    
    # Check what's NOT applied
    cur.execute("""
        SELECT m.app, m.name FROM django_migrations m
        WHERE m.app = 'workflows'
        ORDER BY m.name
    """)
    applied = set((r[0], r[1]) for r in cur.fetchall())
    
    backend_path = os.path.join(os.path.dirname(__file__), 'Backend', 'workflows', 'migrations')
    all_migrations = set()
    if os.path.exists(backend_path):
        for f in os.listdir(backend_path):
            if f.endswith('.py') and f not in ('__init__.py', '__pycache__'):
                all_migrations.add(('workflows', f[:-3]))
    
    missing = all_migrations - applied
    if missing:
        print('\nMissing migrations:')
        for app, name in sorted(missing):
            print(f'  {app}.{name}')
