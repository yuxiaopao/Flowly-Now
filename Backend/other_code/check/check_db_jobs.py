import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3307, user='root',
    password='rootpassword', database='flowly_db'
)
cur = conn.cursor()

cur.execute("SELECT id, name, status, framework, training_kind, dataset_yaml_path FROM training_jobs ORDER BY id DESC LIMIT 10")
rows = cur.fetchall()
print(f'Training Jobs in DB:')
for row in rows:
    print(f'  {row}')

cur.close()
conn.close()
