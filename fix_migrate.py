import MySQLdb
conn = MySQLdb.connect(host='localhost', port=3306, user='root', passwd='xp594120xt')
cur = conn.cursor()
cur.execute("DROP DATABASE IF EXISTS flowly")
cur.execute("CREATE DATABASE flowly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
conn.commit()
print("Database recreated")
