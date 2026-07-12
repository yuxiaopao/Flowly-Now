import pymysql, sys
sys.path.insert(0, r'e:\Flowly-now\Backend')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from django.conf import settings
print(f"DB host: {settings.DATABASES['default']['HOST']}")
print(f"DB port: {settings.DATABASES['default']['PORT']}")
print(f"DB name: {settings.DATABASES['default']['NAME']}")
try:
    conn = pymysql.connect(
        host='127.0.0.1', port=3306,
        user=settings.DATABASES['default']['USER'],
        password=settings.DATABASES['default']['PASSWORD'],
        database=settings.DATABASES['default']['NAME'],
    )
    print("Direct MySQL connection: OK")
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) FROM training_jobs")
        print(f"Training jobs: {c.fetchone()}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
