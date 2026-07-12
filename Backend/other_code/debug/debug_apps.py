import os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

import django
django.setup()

from django.apps import apps

try:
    cfg = apps.get_app_config('datasets')
    print(f'datasets app: label={cfg.label}, name={cfg.name}, path={cfg.path}')
except Exception as e:
    print(f'datasets app NOT registered: {e}')

try:
    cfg2 = apps.get_app_config('augmentation')
    print(f'augmentation app: label={cfg2.label}, name={cfg2.name}')
except Exception as e:
    print(f'augmentation app NOT registered: {e}')

# Try to get the lazy reference
from django.apps.registry import Apps
temp_apps = Apps()
try:
    # This is what Django does internally - it tries to resolve the lazy reference
    from django.db.models.fields.related_descriptors import ForeignKeyDeferredAttribute
    print('OK: Apps registry working')
except Exception as e:
    print(f'Error: {e}')
