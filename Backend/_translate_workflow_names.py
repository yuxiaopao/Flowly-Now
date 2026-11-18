import os, sys, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import requests
from workflows.models import Workflow

API = 'https://api.ming-ai.top/v1/chat/completions'
KEY = 'sk-nznNm21gQoQbmXEpavvNozXQVRMnRwOAYBhrtt4r9wQRR4Ha'
MODEL = 'gpt-5.6-luna'

HAS_CJK = re.compile(r'[\u4e00-\u9fff]')

workflows = list(Workflow.objects.filter(owner__username='nlwftest').only('id', 'name', 'description'))
to_translate = [w for w in workflows if not HAS_CJK.search(w.name or '')]

print(f'需要翻译名称的工作流: {len(to_translate)}', flush=True)

def translate_name(wf):
    text = (wf.name or '').strip()
    if not text:
        return wf.id, None, 'empty'
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': '你是中文本地化助手。把给定的英文工作流名称翻译成简洁中文，保留 [n8n] 前缀和末尾括号编号，只输出译文，不要解释。'},
            {'role': 'user', 'content': text},
        ],
        'max_tokens': 80,
        'temperature': 0.2,
    }
    try:
        r = requests.post(API, headers={'Authorization': f'Bearer {KEY}'}, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        content = (data.get('choices') or [{}])[0].get('message', {}).get('content') or ''
        content = content.strip().strip('"').strip()
        return wf.id, content or None, 'ok'
    except Exception as exc:
        return wf.id, None, str(exc)[:120]

results = {}
ok = fail = 0
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(translate_name, w): w.id for w in to_translate}
    for fut in as_completed(futures):
        wid, translated, status = fut.result()
        if status == 'ok' and translated and HAS_CJK.search(translated):
            results[wid] = translated
            ok += 1
        else:
            fail += 1
        if (ok + fail) % 50 == 0:
            print(f'进度 ok={ok} fail={fail}', flush=True)

for wid, translated in results.items():
    Workflow.objects.filter(id=wid).update(name=translated)

with open(r'E:\Flowly-now\test-results\run-20261117\nlwftest-name-translation.json', 'w', encoding='utf-8') as f:
    json.dump({'translated': ok, 'failed': fail, 'results': {str(k): v for k, v in results.items()}}, f, ensure_ascii=False, indent=2)
print(json.dumps({'translated': ok, 'failed': fail}, ensure_ascii=False))
