import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, 'Backend')

import django
django.setup()

from workflows.models import ExecutionCacheConfig

print('Model _meta.db_table:', ExecutionCacheConfig._meta.db_table)
print('Model _meta.label:', ExecutionCacheConfig._meta.label)
print('Model _meta.label_lower:', ExecutionCacheConfig._meta.label_lower)

from django.db import connection
with connection.cursor() as cur:
    cur.execute("SHOW TABLES LIKE 'execution_cache%'")
    print('Tables in DB:', [r[0] for r in cur.fetchall()])
    
    cur.execute("SHOW TABLES LIKE 'workflows_execution%'")
    print('workflows_execution tables:', [r[0] for r in cur.fetchall()])
