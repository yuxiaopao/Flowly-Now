"""Import user-supplied keys through a hidden prompt; persist only encrypted data."""
import getpass
import json

from create_butterfly_video_workflow import BACKEND_ROOT  # initializes Django
from django.contrib.auth import get_user_model
from workflows.models import APICredential

owner=get_user_model().objects.get(username='nlwftest')
results=[]
for index in (1,2):
    key=getpass.getpass(f'Agnes key {index}: ')
    if not key.startswith('sk-') or len(key)<20:
        raise ValueError('Invalid key format')
    credential,_=APICredential.objects.get_or_create(owner=owner,name=f'蝶羽共生纹视频·新增{index}',defaults={'service_type':'agnes','credential_type':'api_key','is_active':True,'credential_data':''})
    credential.set_encrypted_data(key);credential.save()
    if not credential.verify_integrity():raise RuntimeError('Credential encryption verification failed')
    results.append({'id':str(credential.pk),'name':credential.name,'encrypted':credential.is_encrypted})
    del key
print(json.dumps(results,ensure_ascii=True),flush=True)
