"""Run Chrome MCP regression fixtures on loopback with a fresh SQLite database."""
import os
import sys
import tempfile
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'Backend'), str(ROOT)]
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.project_test_settings'
os.environ['DEBUG'] = 'True'

import config.project_test_settings as qa_settings

qa_settings.DATABASES['default']['NAME'] = str(Path(tempfile.mkdtemp(prefix='flowly-reliability-')) / 'qa.sqlite3')
qa_settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DASHSCOPE_API_KEY', 'AGNES_API_KEY',
            'VOLCENGINE_API_KEY', 'ARK_API_KEY', 'RAG_EMBEDDING_API_KEY', 'RAG_CHAT_API_KEY',
            'LANGSMITH_API_KEY', 'LANGCHAIN_API_KEY'):
    setattr(qa_settings, key, '')
    os.environ[key] = ''
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

if os.getenv('FLOWLY_QA_PRODUCT_FIXTURES') == '1':
    class FixtureProvider(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', '0'))
            payload = json.loads(self.rfile.read(length))
            if self.path != '/v1/chat/completions' or not payload.get('messages'):
                self.send_error(404)
                return
            # Explicit transport fixture. This does not verify real model quality.
            body = json.dumps({'id': 'flowly-qa-fixture', 'object': 'chat.completion',
                'created': 1, 'model': 'gpt-4o-mini', 'choices': [{'index': 0,
                    'message': {'role': 'assistant', 'content': 'The release playbook requires a successful test before publishing. [1]'},
                    'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    fixture_server = ThreadingHTTPServer(('127.0.0.1', 0), FixtureProvider)
    threading.Thread(target=fixture_server.serve_forever, daemon=True).start()
    qa_settings.RAG_CHAT_MODEL = 'gpt-4o-mini'
    qa_settings.RAG_CHAT_API_KEY = 'flowly-isolated-qa-fixture'
    qa_settings.RAG_CHAT_BASE_URL = f'http://127.0.0.1:{fixture_server.server_port}/v1'

import django

django.setup()

from django.core.management import call_command
from users.models import User
from daphne.cli import CommandLineInterface

call_command('migrate', run_syncdb=True, verbosity=0)
user = User.objects.create_user(
    username=os.getenv('FLOWLY_E2E_USERNAME', 'nlwftest@flowly.test'),
    email='reliability-qa@flowly.test',
    password=os.getenv('FLOWLY_E2E_PASSWORD', 'Test123456!'),
)
if os.getenv('FLOWLY_QA_PRODUCT_FIXTURES') == '1':
    from workflows.models import Workflow, Node, Edge
    from rag.models import VectorStore, DocumentCollection
    from rag.pipeline import DocumentProcessor
    from billing.models import Invoice
    from django.utils import timezone
    from datetime import timedelta

    workflow = Workflow.objects.create(owner=user, name='QA 客服工作流')
    start = Node.objects.create(workflow=workflow, node_type='start', name='输入')
    text = Node.objects.create(workflow=workflow, node_type='text_template', name='生成回复', config={'template': 'Hello {{customerName}}'})
    end = Node.objects.create(workflow=workflow, node_type='end', name='输出')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=text)
    Edge.objects.create(workflow=workflow, source_node=text, target_node=end)
    store = VectorStore.objects.create(owner=user, name='QA 本地知识存储', store_type='memory')
    collection = DocumentCollection.objects.create(owner=user, vector_store=store, name='QA Release Playbook', retrieval_mode='keyword')
    ingested = DocumentProcessor(collection).process_text('Release playbook. A release requires a successful test. Revoke an application key to deny invocation.', {'title': 'Release Playbook'})
    if not ingested.get('success'):
        raise RuntimeError('QA document fixture could not be indexed')
    now = timezone.now()
    Invoice.objects.create(user=user, invoice_number='QA-BILL-001', subtotal='12.00', total='12.00',
        currency='CNY', status='paid', paid_at=now, period_start=now - timedelta(days=1), period_end=now,
        due_date=now, line_items=[{'description': 'QA persisted billing record', 'total': '12.00'}])
    from website_generator.models import GeneratedSite
    fixture_root = Path(tempfile.mkdtemp(prefix='flowly-site-qa-'))
    weight = fixture_root / 'qa-best.pt'
    weight.write_bytes(b'QA configuration fixture only; not a model')
    site_config = dict(created_by=user, website_type='detection', model_type='detection',
        model_path=str(weight), best_weight_path=str(weight), framework='ultralytics',
        labels=['helmet'], class_names=['helmet'], output_dir=str(fixture_root / 'unused-site'),
        status='completed', site_brief={'wizard': {'siteName': 'QA识别', 'usageDescription': '仅验证配置重建'}},
        model_artifact_manifest={'trainingKind': 'yolo', 'modelType': 'detection', 'framework': 'ultralytics',
                                 'bestWeightPath': str(weight), 'labels': ['helmet']})
    GeneratedSite.objects.create(name='QA 历史识别项目（仅配置验证）', **site_config)
    source_workflow = Workflow.objects.create(owner=user, name='QA 网站源工作流')
    source_node = Node.objects.create(workflow=source_workflow, node_type='website_generator', name='QA 来源建站节点')
    GeneratedSite.objects.create(name='QA 有来源项目（仅回链验证）', source_workflow=source_workflow,
        source_node=source_node, source_recorded=True, **site_config)
    print('Product fixtures ready: one real workflow, indexed collection and persisted invoice; local HTTP model fixture only.', flush=True)
print('Isolated reliability backend ready on 127.0.0.1:8000; business databases are not connected.', flush=True)
from django.http import JsonResponse
from django.urls import path
import config.urls
config.urls.urlpatterns.append(path('api/v1/__isolated-qa__/', lambda request: JsonResponse({
    'isolated': True, 'product_fixtures': os.getenv('FLOWLY_QA_PRODUCT_FIXTURES') == '1',
})))
CommandLineInterface().run(['-b', '127.0.0.1', '-p', '8000', 'config.asgi:application'])
