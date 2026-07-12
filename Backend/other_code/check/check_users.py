import sys, os
sys.path.insert(0, r'e:\Flowly-now\Backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from users.models import User
users = User.objects.all()[:5]
for u in users:
    print(f"ID={u.id} username={u.username} email={u.email} is_superuser={u.is_superuser}")
