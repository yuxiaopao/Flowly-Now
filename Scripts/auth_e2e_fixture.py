"""Reset links and cleanup for explicitly named disposable browser QA accounts."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from users.models import User

username = sys.argv[1]
if not re.fullmatch(r'authqa_\d{13}', username):
    raise ValueError('Only explicitly named disposable auth QA accounts are allowed')
if '--cleanup' in sys.argv:
    User.objects.filter(username=username).delete()
    print(json.dumps({'cleaned': username}))
else:
    user = User.objects.get(username=username)
    print(json.dumps({'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                      'token': default_token_generator.make_token(user)}))
