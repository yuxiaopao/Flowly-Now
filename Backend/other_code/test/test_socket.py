import pymysql, os, sys
sys.path.insert(0, r'e:\Flowly-now\Backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from django.conf import settings

db = settings.DATABASES['default']

# Try socket connection on Windows
socket_paths = [
    r'C:\ProgramData\MySQL\MySQL Server 8.0\mysql.sock',
    r'C:\ProgramData\MySQL\MySQL Server 8.0\MySQLServer80\mysql.sock',
    r'C:\xampp\mysql\mysql.sock',
    r'C:\mysql\socket\mysql.sock',
    '',
]

for sock in socket_paths:
    if sock and not os.path.exists(sock):
        continue
    try:
        kw = {'host': db['HOST'], 'port': int(db['PORT']), 'user': db['USER'], 'password': db['PASSWORD'], 'database': db['NAME']}
        if sock:
            kw['unix_socket'] = sock
        conn = pymysql.connect(**kw)
        print(f"SUCCESS via socket: {sock or 'TCP'}")
        with conn.cursor() as c:
            c.execute("SHOW DATABASES LIKE %s", [db['NAME']])
            result = c.fetchone()
            print(f"Database '{db['NAME']}' exists: {result is not None}")
        conn.close()
        break
    except Exception as e:
        print(f"Socket {sock or 'TCP'} FAILED: {e}")
