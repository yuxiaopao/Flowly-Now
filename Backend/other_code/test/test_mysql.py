import pymysql
try:
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='rootpassword', database='flowly_db')
    print("MySQL connection with password: OK")
    conn.close()
except Exception as e:
    print(f"With password: {e}")
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='', database='flowly_db')
        print("MySQL connection without password: OK")
        conn.close()
    except Exception as e2:
        print(f"Without password: {e2}")
        try:
            conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='')
            print("MySQL connection no DB, no password: OK")
            conn.close()
        except Exception as e3:
            print(f"No DB no password: {e3}")
