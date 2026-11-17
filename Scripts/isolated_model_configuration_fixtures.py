"""Private QA fixtures: loopback model transport and a tiny CPU-only classifier.

This module never imports Django or Torch until the explicit seed call. The QA
coordinator owns server shutdown and supplies an already isolated SQLite root.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

MODEL_IDS = {
    'normal': 'flowly-qa-normal',
    'alternate': 'flowly-qa-alternate',
    'empty': 'flowly-qa-empty',
    'error': 'flowly-qa-error',
    'embedding': 'flowly-qa-embedding',
}
MAX_BODY_BYTES = 65536


def create_model_configuration_provider(port=0):
    """Start one local HTTP fixture; return the server for coordinator cleanup."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, status, payload):
            content = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def authorized(self):
            return self.headers.get('Authorization', '').startswith('Bearer ')

        def do_GET(self):
            if not self.authorized():
                return self.respond(401, {'error': {'message': 'Fixture authentication required'}})
            if self.path != '/v1/models':
                return self.respond(404, {'error': {'message': 'Unknown fixture endpoint'}})
            self.respond(200, {'object': 'list', 'data': [{'id': value, 'object': 'model'} for value in MODEL_IDS.values()]})

        def do_POST(self):
            if not self.authorized():
                return self.respond(401, {'error': {'message': 'Fixture authentication required'}})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_BODY_BYTES:
                    return self.respond(413, {'error': {'message': 'Fixture body is empty or too large'}})
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Object body required')
            except (ValueError, TypeError):
                return self.respond(400, {'error': {'message': 'Invalid fixture JSON'}})
            model = data.get('model')
            # Keep only non-secret transport evidence. Never retain headers or prompts.
            self.server.requests_seen.append({'path': self.path, 'model': model})
            if model not in MODEL_IDS.values():
                return self.respond(400, {'error': {'message': 'Unknown fixture model'}})
            if self.path == '/v1/embeddings' and model == MODEL_IDS['embedding']:
                return self.respond(200, {'model': model, 'data': [{'index': 0, 'embedding': [.25, .5]}]})
            if self.path != '/v1/chat/completions':
                return self.respond(404, {'error': {'message': 'Unknown fixture endpoint'}})
            if model == MODEL_IDS['error']:
                return self.respond(200, {'error': {'message': 'Isolated provider fixture error'}})
            content = '' if model == MODEL_IDS['empty'] else 'Isolated provider connection confirmed.'
            self.respond(200, {'id': 'flowly-isolated-probe', 'object': 'chat.completion', 'model': model,
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}})

    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Fixture port must be a valid local port or zero')
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.requests_seen = []
    Thread(target=server.serve_forever, name='flowly-model-config-qa-provider', daemon=True).start()
    return server


def _private_root(settings, data_root):
    root = Path(data_root).resolve(strict=True)
    database = settings.DATABASES['default']
    if os.getenv('FLOWLY_ISOLATED_QA') != '1' or database['ENGINE'] != 'django.db.backends.sqlite3':
        raise RuntimeError('Model configuration fixtures require an explicitly isolated SQLite QA process')
    if not Path(database['NAME']).resolve().is_relative_to(root):
        raise RuntimeError('Refusing to seed a database outside the private QA root')
    if not Path(settings.MEDIA_ROOT).resolve().is_relative_to(root):
        raise RuntimeError('Refusing to write fixture files outside the private QA root')
    for current in (root, *root.parents):
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise RuntimeError('Private QA root cannot use symlinks or directory junctions')
    return root


def seed_model_configuration(user, admin, fixture_base_url, data_root):
    """Return JSON-safe IDs; no passwords, credentials, file paths or user models."""
    from django.conf import settings
    root = _private_root(settings, data_root)
    url = urlsplit(fixture_base_url)
    if (url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or
            url.path.rstrip('/') != '/v1' or url.query or url.fragment or url.username or url.password):
        raise RuntimeError('Model fixture endpoint must be the explicitly local HTTP provider')
    if not user.is_active or not admin.is_active or not (admin.is_staff or admin.is_superuser):
        raise RuntimeError('Model fixtures require active ordinary and catalog-admin identities')

    import torch
    from django.db import transaction
    from datasets.models import Dataset
    from gateway.models import AIModel, ModelProvider
    from training.models import Dataset as TrainingDataset, TrainingJob
    from workflows.models import APICredential, Edge, Node, NodeExecution, Workflow, WorkflowExecution
    from uuid import uuid4

    artifact_root, dataset_root = root / 'model-artifacts', root / 'model-datasets'
    artifact_root.mkdir(exist_ok=True)
    dataset_root.mkdir(exist_ok=True)
    # Synthetic fixed tensors, not a trained/downloaded/GPU model. Predictions are
    # deliberately opposite the held-out labels, so a real evaluator must return 0.
    config = {'input_dim': 2, 'hidden_dims': [], 'output_dim': 2, 'dropout': 0}
    model = torch.nn.Sequential(torch.nn.Linear(2, 2))
    with torch.no_grad():
        model[0].weight.copy_(torch.tensor([[-1., 0.], [1., 0.]]))
        model[0].bias.zero_()
    model_path = artifact_root / 'fixed-classifier.pt'
    torch.save({'model_state_dict': model.state_dict(), 'config': config}, model_path)
    csv = 'x1,x2,label\n-2,0,positive\n-1,1,positive\n1,0,negative\n2,1,negative\n'
    training_path, generic_path = dataset_root / 'training-domain.csv', dataset_root / 'generic-domain.csv'
    training_path.write_text(csv, encoding='utf-8')
    generic_path.write_text(csv, encoding='utf-8')

    with transaction.atomic():
        provider, _ = ModelProvider.objects.update_or_create(slug='custom', defaults={'name': 'QA Local Provider', 'is_active': True})
        models = {}
        for kind, model_id in MODEL_IDS.items():
            model_row, _ = AIModel.objects.update_or_create(provider=provider, model_id=model_id, defaults={
                'name': f'QA {kind.title()} Model', 'model_type': 'embedding' if kind == 'embedding' else 'chat',
                'is_active': True, 'is_default': kind == 'embedding', 'input_price': 0, 'output_price': 0})
            models[kind] = str(model_row.pk)
        credential = APICredential.objects.create(owner=admin, name='QA local model admin transport',
            service_type='custom', credential_type='api_key', is_active=True,
            service_config={'endpoint': fixture_base_url, 'model': MODEL_IDS['normal']})
        credential.set_encrypted_data(f'qa-synthetic-{uuid4()}')
        credential.save()
        source = Workflow.objects.create(owner=user, name='QA Fixed Classifier Source')
        training_node = Node.objects.create(workflow=source, node_type='model_training', name='QA Fixed Tensors')
        source_execution = WorkflowExecution.objects.create(workflow=source, version=1, triggered_by=user, status='completed')
        job = TrainingJob.objects.create(created_by=user, workflow=source, node=training_node, execution=source_execution,
            name='QA Fixed CPU Classifier', status='completed', framework='pytorch', training_kind='generic', model_type='classifier',
            config=config, model_path=str(model_path), class_names=['negative', 'positive'])
        NodeExecution.objects.create(execution=source_execution, node=training_node, node_version=1, status='completed',
            output_data={'training_run_id': str(job.pk), 'model_path': str(model_path)})
        training = TrainingDataset.objects.create(created_by=user, name='QA Training-Domain Zero F1',
            file_path=str(training_path), format='csv', size=len(csv.encode()), row_count=4, columns=['x1', 'x2', 'label'])
        generic = Dataset.objects.create(created_by=user, name='QA Generic-Domain Zero F1', source='upload', format='csv',
            status='ready', file_path=str(generic_path), size_bytes=len(csv.encode()), row_count=4, column_count=3)
        workflow = Workflow.objects.create(owner=user, name='QA Model Evaluation Editor')
        start = Node.objects.create(workflow=workflow, node_type='start', name='输入', position_x=0, position_y=0)
        evaluation = Node.objects.create(workflow=workflow, node_type='model_evaluation', name='QA Actual Zero F1', position_x=280, position_y=0,
            config={'evaluationModelSource': 'legacy', 'evaluationDatasetSource': 'legacy',
                'modelPath': str(job.pk), 'trainingRunId': str(job.pk), 'testDataset': str(training.pk),
                'metrics': ['accuracy', 'precision', 'recall', 'f1'], 'features': ['x1', 'x2'], 'labelColumn': 'label'})
        end = Node.objects.create(workflow=workflow, node_type='end', name='输出', position_x=560, position_y=0)
        Edge.objects.create(workflow=workflow, source_node=start, target_node=evaluation)
        Edge.objects.create(workflow=workflow, source_node=evaluation, target_node=end)

    return {'user_username': user.username, 'admin_username': admin.username,
        'gateway': {'base_url': fixture_base_url, 'provider_id': str(provider.pk), 'models': models, 'model_ids': MODEL_IDS},
        'evaluation': {'workflow_id': str(workflow.pk), 'node_id': str(evaluation.pk), 'training_job_id': str(job.pk),
            'training_dataset_id': str(training.pk), 'generic_dataset_id': str(generic.pk), 'expected_f1': 0},
        'scope': 'Local transport and synthetic fixed CPU inference only; no model quality or GPU training validation.'}
