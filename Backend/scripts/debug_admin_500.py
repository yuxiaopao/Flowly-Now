import os, re, requests, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
BASE = 'http://127.0.0.1:8000'
s = requests.Session()
r = s.get(BASE + '/admin/login/')
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)
s.post(BASE + '/admin/login/', data={
    'username': 'admin', 'password': 'admin123',
    'csrfmiddlewaretoken': token, 'next': '/admin/',
}, headers={'Referer': BASE + '/admin/login/'})
for path in [
    '/admin/integrations/integration/add/',
    '/admin/integrations/integrationtemplate/add/',
    '/admin/templates/workflowtemplate/add/',
]:
    resp = s.get(BASE + path)
    print('===', path, resp.status_code)
    for pat, label in [
        (r'Exception Type: ([^\n<]+)', 'TYPE'),
        (r'Exception Value: ([^\n<]+)', 'VAL'),
        (r'<pre class="exception_value">([^<]+)</pre>', 'PRE'),
    ]:
        m = re.search(pat, resp.text)
        if m:
            print(label + ':', m.group(1).strip())
