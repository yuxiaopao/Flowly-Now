"""Owned loopback API and actual filesystem Celery worker for UI acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Scripts.continuation_qa_guard import KIND, BROKER_KEYS, require_before_frameworks

SETTINGS_SOURCE = '''from Scripts.continuation_qa_guard import validate_environment, local_provider_url
from pathlib import Path
import json
qa_root, qa_manifest = validate_environment()
from config.project_test_settings import *
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(qa_root/'qa.sqlite3'), 'OPTIONS': {'timeout': 30}}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
MEDIA_ROOT = str(qa_root/'media')
BACKUP_DIR = str(qa_root/'backups')
LOGGING['handlers']['file']['filename'] = str(qa_root/'logs'/'django.log')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BROKER_URL = CELERY_BROKER_READ_URL = CELERY_BROKER_WRITE_URL = 'filesystem://'
CELERY_RESULT_BACKEND = 'cache+memory://'
CELERY_TASK_DEFAULT_QUEUE = qa_manifest['queue']
CELERY_BROKER_TRANSPORT_OPTIONS = {'data_folder_in': str(qa_root/'messages'), 'data_folder_out': str(qa_root/'messages'),
 'data_folder_processed': str(qa_root/'processed'), 'control_folder': str(qa_root/'control'), 'polling_interval': .1}
CELERY_WORKER_SEND_TASK_EVENTS = False
CELERY_TASK_SEND_SENT_EVENT = False
CELERY_BEAT_SCHEDULE = {}
EVALUATION_ARTIFACT_ROOTS = [str(qa_root/'model-artifacts')]
EVALUATION_DATA_ROOTS = [str(qa_root/'model-datasets'), str(qa_root/'media'/'datasets')]
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
INTEGRATIONS_ALLOWED_PRIVATE_HOSTS = ('127.0.0.1', 'localhost')
for secret_name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DASHSCOPE_API_KEY', 'AGNES_API_KEY',
 'VOLCENGINE_API_KEY', 'ARK_API_KEY', 'RAG_EMBEDDING_API_KEY', 'RAG_CHAT_API_KEY', 'LANGSMITH_API_KEY', 'LANGCHAIN_API_KEY'):
 globals()[secret_name] = ''
metadata_path = qa_root/'fixture_metadata.json'
if metadata_path.exists():
 fixture_metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
 RAG_CHAT_API_KEY = 'flowly-isolated-qa-fixture'
 RAG_CHAT_MODEL = 'gpt-4o-mini'
 RAG_CHAT_BASE_URL = local_provider_url(fixture_metadata['provider_base_url'])
'''


def prepare():
    root = ROOT / '.cache' / f'continuation-runtime-{uuid.uuid4().hex}'
    root.mkdir(parents=True)
    token = root.name.rsplit('-', 1)[-1]
    for name in ('messages', 'processed', 'control', 'media', 'model-artifacts', 'model-datasets', 'backups', 'tmp', 'logs'):
        (root / name).mkdir()
    (root / 'manifest.json').write_text(json.dumps({'kind': KIND, 'root': str(root), 'token': token,
        'queue': f'continuation-{token}'}), encoding='utf-8')
    (root / 'flowly_continuation_settings.py').write_text(SETTINGS_SOURCE, encoding='utf-8')
    return root


def clean_environment(root):
    allowed = {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP',
               'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'LANG', 'LC_ALL', 'TZ', 'PROCESSOR_ARCHITECTURE'}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(FLOWLY_QA_ROOT=str(root), FLOWLY_QA_TOKEN=root.name.rsplit('-', 1)[-1], FLOWLY_ISOLATED_QA='1',
        PYTHON_DOTENV_DISABLED='1', DJANGO_SETTINGS_MODULE='flowly_continuation_settings',
        CELERY_RESULT_BACKEND='cache+memory://', PYTHONUTF8='1', PYTHONUNBUFFERED='1',
        PYTHONPATH=os.pathsep.join((str(root), str(ROOT/'Backend'), str(ROOT))),
        DJANGO_SECRET_KEY='flowly-local-isolated-qa-only-secret', DEBUG='True',
        LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    env.update(TEMP=str(root/'tmp'), TMP=str(root/'tmp'))
    env.update({key: 'filesystem://' for key in BROKER_KEYS})
    return env


def launch(root, role):
    import psutil
    with (root/f'{role}.out.log').open('w', encoding='utf-8') as out, (root/f'{role}.err.log').open('w', encoding='utf-8') as err:
        command = [sys.executable, str(Path(__file__).resolve()), f'run-{role}']
        process = subprocess.Popen(command, cwd=ROOT/'Backend', env=clean_environment(root), stdout=out, stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    owned = psutil.Process(process.pid)
    record = {'pid': process.pid, 'created_at': owned.create_time(), 'command': command, 'root': str(root),
        'exe': owned.exe(), 'cwd': owned.cwd()}
    (root/f'{role}.process.json').write_text(json.dumps(record), encoding='utf-8')
    print(json.dumps(record), flush=True)


def stop(root):
    import psutil
    for role in ('worker', 'api'):
        path = root/f'{role}.process.json'
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        try:
            process = psutil.Process(record['pid'])
            expected = record['command']
            environment = process.environ()
            if (record['root'] != str(root) or process.create_time() != record['created_at'] or process.cmdline() != expected or
                    process.exe() != record['exe'] or process.cwd() != record['cwd'] or
                    Path(process.cwd()).resolve() != ROOT/'Backend' or
                    environment.get('FLOWLY_QA_ROOT') != str(root) or
                    environment.get('FLOWLY_QA_TOKEN') != root.name.rsplit('-', 1)[-1]):
                raise RuntimeError(f'Refusing to stop a process whose identity changed: {role}')
            owned = []
            for child in process.children(recursive=True):
                if child.name().lower() in ('conhost.exe', 'openconsole.exe'):
                    continue
                child_env = child.environ()
                if child_env.get('FLOWLY_QA_ROOT') == str(root) and child_env.get('FLOWLY_QA_TOKEN') == environment['FLOWLY_QA_TOKEN'] and Path(child.cwd()).resolve() == ROOT/'Backend':
                    owned.append((child, child.create_time()))
            for child, created in reversed(owned):
                if child.is_running() and child.create_time() == created:
                    child.terminate()
            process.terminate()
            _, alive = psutil.wait_procs([process, *(child for child, _ in owned)], timeout=8)
            for child in alive:
                identity = next((created for item, created in owned if item.pid == child.pid), record['created_at'])
                if child.create_time() == identity:
                    child.kill()
            print(json.dumps({'stopped': role, 'pid': record['pid']}), flush=True)
        except psutil.NoSuchProcess:
            print(json.dumps({'already_stopped': role}), flush=True)


def product_fixtures(user, root):
    from workflows.models import Workflow, Node, Edge
    from rag.models import VectorStore, DocumentCollection
    from rag.pipeline import DocumentProcessor
    from billing.models import Invoice
    from django.utils import timezone
    from datetime import timedelta
    from website_generator.models import GeneratedSite
    from tenants.models import Tenant, TenantMembership
    tenant = Tenant.objects.create(owner=user, name='QA 交付团队', slug='qa-application-context', status='active')
    TenantMembership.objects.create(tenant=tenant, user=user, role='owner', is_active=True)
    workflow = Workflow.objects.create(owner=user, name='QA 客服工作流')
    previous = None
    for kind, config in [('start', {}), ('text_template', {'template': 'Hello {{customerName}}'}), ('end', {})]:
        node = Node.objects.create(workflow=workflow, node_type=kind, name=kind, config=config)
        if previous:
            Edge.objects.create(workflow=workflow, source_node=previous, target_node=node)
        previous = node
    store = VectorStore.objects.create(owner=user, name='QA 本地知识存储', store_type='memory')
    collection = DocumentCollection.objects.create(owner=user, vector_store=store, name='QA Release Playbook', retrieval_mode='keyword')
    result = DocumentProcessor(collection).process_text('Release playbook. A release requires a successful test. Revoke an application key to deny invocation.', {'title': 'Release Playbook'})
    if not result.get('success'):
        raise RuntimeError('Real local document indexing failed')
    now = timezone.now()
    Invoice.objects.create(user=user, invoice_number='QA-BILL-001', subtotal='12.00', total='12.00',
        currency='CNY', status='paid', paid_at=now, period_start=now-timedelta(days=1), period_end=now,
        due_date=now, line_items=[{'description': 'QA persisted billing record', 'total': '12.00'}])
    weights = root/'qa-configuration-only.pt'
    weights.write_bytes(b'QA configuration fixture only; not an inference model')
    site_config = dict(created_by=user, website_type='detection', model_type='detection', model_path=str(weights),
        best_weight_path=str(weights), framework='ultralytics', labels=['helmet'], class_names=['helmet'],
        output_dir=str(root/'unused-site'), status='completed',
        site_brief={'wizard': {'siteName': 'QA识别', 'usageDescription': '仅验证配置重建'}},
        model_artifact_manifest={'trainingKind': 'yolo', 'modelType': 'detection', 'framework': 'ultralytics',
            'bestWeightPath': str(weights), 'labels': ['helmet']})
    GeneratedSite.objects.create(name='QA 历史识别项目（仅配置验证）', **site_config)
    source = Workflow.objects.create(owner=user, name='QA 网站源工作流')
    node = Node.objects.create(workflow=source, node_type='website_generator', name='QA 来源建站节点')
    GeneratedSite.objects.create(name='QA 有来源项目（仅回链验证）', source_workflow=source, source_node=node, source_recorded=True, **site_config)
    return {'tenant_id': tenant.pk, 'tenant_name': tenant.name}


def run_api(root):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from django.conf import settings
    from urllib.parse import urlsplit
    from Scripts.continuation_qa_guard import local_provider_url
    previous_path = root/'fixture_metadata.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else None
    if previous and not (previous.get('isolated') is True and previous.get('product_fixtures') is True and previous.get('async_evaluations') is True):
        raise RuntimeError('Cannot resume an unknown fixture database')
    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
            if self.path != '/v1/chat/completions' or not payload.get('messages'):
                self.send_error(404); return
            value = {'id': 'flowly-private-fixture', 'object': 'chat.completion', 'created': 1,
                'model': 'gpt-4o-mini', 'choices': [{'index': 0, 'message': {'role': 'assistant',
                'content': 'The release playbook requires a successful test before publishing. [1]'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}}
            body = json.dumps(value).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *_args):
            pass
    provider_port = urlsplit(local_provider_url(previous['provider_base_url'])).port if previous else 0
    provider = ThreadingHTTPServer(('127.0.0.1', provider_port), Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    settings.RAG_CHAT_MODEL, settings.RAG_CHAT_API_KEY = 'gpt-4o-mini', 'flowly-isolated-qa-fixture'
    settings.RAG_CHAT_BASE_URL = f'http://127.0.0.1:{provider.server_port}/v1'
    import django
    django.setup()
    from django.core.management import call_command
    from users.models import User
    call_command('migrate', run_syncdb=True, verbosity=0)
    if previous:
        user = User.objects.get(username='nlwftest@flowly.test', is_active=True)
        admin = User.objects.get(username='admin-fixture@flowly.test', is_active=True, is_superuser=True)
        metadata = previous
    else:
        user = User.objects.create_user(username='nlwftest@flowly.test', email='reliability-qa@flowly.test', password='Test123456!')
        admin = User.objects.create_superuser(username='admin-fixture@flowly.test', email='admin-fixture@flowly.test', password='FixtureAdmin123!')
        context = product_fixtures(user, root)
        metadata = {'isolated': True, 'product_fixtures': True, 'async_evaluations': True,
            'provider_base_url': settings.RAG_CHAT_BASE_URL, 'application_context': context}
    helper = ROOT/'Scripts'/'isolated_model_configuration_fixtures.py'
    if helper.exists():
        from Scripts.isolated_model_configuration_fixtures import create_model_configuration_provider, seed_model_configuration
        if previous and previous.get('model_configuration'):
            url = local_provider_url(previous['model_configuration']['gateway']['base_url'])
            model_provider = create_model_configuration_provider(port=urlsplit(url).port)
        else:
            model_provider = create_model_configuration_provider()
            metadata['model_configuration'] = seed_model_configuration(user, admin, f'http://127.0.0.1:{model_provider.server_port}/v1', root)
    (root/'fixture_metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    from django.http import JsonResponse
    from django.urls import path
    import config.urls
    config.urls.urlpatterns.append(path('api/v1/__isolated-qa__/', lambda request: JsonResponse(metadata)))
    print('Private continuation API ready; actual filesystem Celery tasks are not eager.', flush=True)
    from daphne.cli import CommandLineInterface
    CommandLineInterface().run(['-b', '127.0.0.1', '-p', '8000', 'config.asgi:application'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'launch-api', 'launch-worker', 'run-api', 'run-worker', 'stop'))
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    if args.action.startswith('run-'):
        root, metadata = require_before_frameworks()
        sys.path[:0] = [str(root), str(ROOT/'Backend')]
        if args.action == 'run-api':
            run_api(root)
        else:
            if not (root/'fixture_metadata.json').exists():
                raise RuntimeError('API fixtures must be ready before starting the worker')
            from config.celery import app
            app.worker_main(['worker', '--pool=threads', '--concurrency=2', '--loglevel=INFO', '--without-gossip',
                '--without-mingle', '--hostname='+metadata['queue']+'@localhost', '--queues='+metadata['queue']])
    elif args.action == 'prepare':
        print(prepare(), flush=True)
    else:
        root = args.root.resolve(strict=True)
        environment = clean_environment(root)
        from Scripts.continuation_qa_guard import validate_environment
        previous = Path.cwd()
        try:
            os.chdir(ROOT/'Backend'); validate_environment(environment)
        finally:
            os.chdir(previous)
        if args.action == 'stop':
            stop(root)
        else:
            launch(root, args.action.removeprefix('launch-'))


if __name__ == '__main__':
    main()
