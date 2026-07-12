import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3307, user='root',
    password='rootpassword'
)
cur = conn.cursor()
cur.execute("SHOW DATABASES")
dbs = cur.fetchall()
print('Databases:', [db[0] for db in dbs])
cur.close()
conn.close()
