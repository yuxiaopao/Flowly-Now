import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3307, user='root',
    password='rootpassword', database='flowly_db'
)
cur = conn.cursor()

# List all training-related tables
cur.execute("SHOW TABLES LIKE '%train%'")
tables = cur.fetchall()
print('Train-related tables:', [t[0] for t in tables])

# Check training_jobs
cur.execute("SELECT id, name, status, framework FROM training_jobs ORDER BY id DESC LIMIT 5")
rows = cur.fetchall()
print(f'\nTraining Jobs ({len(rows)}):')
for row in rows:
    print(f'  id={row[0]} name={row[1]} status={row[2]} framework={row[3]}')

# Check YOLO runs
cur.execute("SHOW TABLES LIKE '%yolo%'")
yolo_tables = cur.fetchall()
print(f'\nYOLO tables: {[t[0] for t in yolo_tables]}')

cur.close()
conn.close()
