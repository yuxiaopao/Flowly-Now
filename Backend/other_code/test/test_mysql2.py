import pymysql, sys
sys.path.insert(0, r'e:\Flowly-now\Backend')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from django.conf import settings
db = settings.DATABASES['default']
print(f"HOST={db['HOST']}, PORT={db['PORT']}, NAME={db['NAME']}, USER={db['USER']}")
try:
    conn = pymysql.connect(host=db['HOST'], port=int(db['PORT']), user=db['USER'], password=db['PASSWORD'], database=db['NAME'])
    print("Connection: OK")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    # Try without password
    try:
        conn = pymysql.connect(host=db['HOST'], port=int(db['PORT']), user=db['USER'], password='', database=db['NAME'])
        print("Connection (no pass): OK")
        conn.close()
    except Exception as e2:
        print(f"No pass error: {e2}")
        # Try without database
        try:
            conn = pymysql.connect(host=db['HOST'], port=int(db['PORT']), user=db['USER'], password='')
            print("Connection (no pass no db): OK")
            conn.close()
        except Exception as e3:
            print(f"No pass no db error: {e3}")
