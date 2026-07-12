import os, sys
sys.path.insert(0, r'e:\Flowly-now\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Test the code path directly
from workflows.services.langchain_service import langchain_service

node_config = {
    'framework': 'ultralytics',
    'modelType': 'detection',
    'yoloVersion': 'yolov8',
    'modelVariant': 'n',
    'datasetPath': r'E:\Flowly-now\Backend\media\yolo_datasets\flowly_test\dataset.yaml',
    'hyperparameters': {'epochs': 5},
    'label': 'Test YOLO',
    'gpuEnabled': True,
    'checkpointing': True,
}
context = {}

result = langchain_service.run_model_training_node(node_config, context)
print('Result success:', result.get('success'))
print('Result output:', result.get('output', {}))

# Check DB
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='rootpassword', database='flowly_db')
cur = conn.cursor()
cur.execute("SELECT id, name, framework, training_kind, dataset_yaml_path, yolo_version FROM training_jobs ORDER BY id DESC LIMIT 5")
for row in cur.fetchall():
    print(f'  DB: {row}')
cur.close()
conn.close()
