import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='rootpassword', database='flowly_db')
cur = conn.cursor()
cur.execute("SELECT id, name, framework, training_kind, dataset_yaml_path, yolo_version FROM training_jobs ORDER BY id DESC LIMIT 10")
for row in cur.fetchall():
    print(f'  {row}')
cur.close()
conn.close()
