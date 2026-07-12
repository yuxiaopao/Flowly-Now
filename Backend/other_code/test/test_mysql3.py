import pymysql
# Try various common connection strings for the local MySQL
conn_strings = [
    {'host': 'localhost', 'port': 3306, 'user': 'root', 'password': '', 'database': ''},
    {'host': '127.0.0.1', 'port': 3306, 'user': 'root', 'password': '', 'database': ''},
    {'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': ''},
    {'host': 'localhost', 'port': 3306, 'user': 'flowly', 'password': 'flowly', 'database': ''},
    {'host': 'localhost', 'port': 3306, 'user': 'flowly', 'password': 'flowly123', 'database': ''},
    {'host': 'localhost', 'port': 3306, 'user': 'flowly', 'password': '', 'database': ''},
]
for cs in conn_strings:
    try:
        kw = {k: v for k, v in cs.items() if v}
        conn = pymysql.connect(**kw)
        print(f"OK: host={cs['host']} user={cs['user']} password='{cs['password']}'")
        conn.close()
        break
    except Exception as e:
        print(f"FAIL: host={cs['host']} user={cs['user']} password='{cs['password']}' -> {e}")
