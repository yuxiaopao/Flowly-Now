import sys
sys.path.insert(0, r'e:\Flowly-now\Backend')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from django.db import connection

with connection.cursor() as c:
    c.execute("SELECT app, name FROM django_migrations ORDER BY id")
    rows = c.fetchall()
    for row in rows:
        print(row)
