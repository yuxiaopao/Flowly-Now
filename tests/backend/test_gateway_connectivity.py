"""Exercise gateway probes against local HTTP providers, never paid services."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.utils import timezone

from gateway.models import AIModel, ModelProvider
from workflows.models import APICredential

pytestmark = pytest.mark.django_db


@pytest.fixture
def local_provider(settings, monkeypatch):
    state = {'requests': [], 'mode': 'success'}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['requests'].append({'path': self.path, 'body': body, 'authorization': self.headers.get('Authorization'), 'anthropic_key': self.headers.get('x-api-key'), 'google_key': self.headers.get('x-goog-api-key'), 'azure_key': self.headers.get('api-key')})
            status = 200
            if state['mode'] == 'error':
                status, payload = 401, {'error': {'message': 'fixture rejected fixture-secret-value'}}
            elif state['mode'] == 'body_error':
                payload = {'error': 'fixture unavailable'}
            elif state['mode'] == 'malformed':
                payload = {'choices': ['invalid'], 'message': 'invalid', 'data': 'invalid', 'content': 'invalid', 'candidates': ['invalid']}
            elif self.path.endswith(':generateContent'):
                payload = {'candidates': [{'content': {'parts': [{'text': 'fixture answer'}]}}]}
            elif self.path.endswith('/api/chat'):
                payload = {'message': {'content': '' if state['mode'] == 'empty' else 'fixture answer'}, 'done': True, 'prompt_eval_count': 2, 'eval_count': 3}
            elif self.path.endswith('/messages'):
                payload = {'content': [{'type': 'text', 'text': 'fixture answer'}], 'usage': {'input_tokens': 2, 'output_tokens': 3}, 'stop_reason': 'end_turn'}
            elif self.path.endswith('/embeddings'):
                payload = {'data': [{'embedding': [0.1, 0.2, 0.3]}], 'model': body['model'], 'usage': {'prompt_tokens': 2, 'total_tokens': 2}}
            else:
                payload = {'id': 'fixture', 'object': 'chat.completion', 'model': body.get('model'), 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': '' if state['mode'] == 'empty' else 'fixture answer'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5}}
            encoded = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state['base'] = f'http://127.0.0.1:{server.server_port}'
    settings.OPENAI_API_KEY = 'fixture-fallback-key'
    settings.OPENAI_BASE_URL = state['base'] + '/fallback/v1'
    settings.OLLAMA_BASE_URL = state['base'] + '/ollama'
    from gateway import gateway_service
    monkeypatch.setattr(gateway_service, '_ollama_provider', None)
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def configure(user, provider, endpoint, *, active=True, model_type='chat'):
    catalog, _ = ModelProvider.objects.get_or_create(slug=provider, defaults={'name': provider})
    model = AIModel.objects.create(provider=catalog, name='Fixture model', model_id='llama-fixture' if provider == 'ollama' else 'fixture-model', model_type=model_type, is_default=True)
    credential = APICredential.objects.create(owner=user, credential_type='api_key', service_type=provider, name='Fixture credential', is_active=active, service_config={'endpoint': endpoint, 'model': model.model_id})
    credential.set_encrypted_data('fixture-secret-value')
    credential.save()
    return model, credential


def test_model_list_contains_metadata_consumed_by_the_management_page(api_client, user):
    model, _ = configure(user, 'custom', 'http://127.0.0.1:1/v1')
    api_client.force_authenticate(user)
    response = api_client.get('/api/v1/gateway/models/')
    payload = response.data.get('data', response.data) if isinstance(response.data, dict) else response.data
    rows = payload.get('results', payload) if isinstance(payload, dict) else payload
    row = next(item for item in rows if str(item['id']) == str(model.pk))
    assert row['provider_slug'] == 'custom'
    assert row['supports_streaming'] is True
    assert 'input_price' in row and 'output_price' in row


@pytest.mark.parametrize('provider,endpoint,suffix', [('custom', '/compat/v1', '/compat/v1/chat/completions'), ('anthropic', '/anthropic/v1', '/anthropic/v1/messages'), ('ollama', '/ollama', '/ollama/api/chat')])
def test_model_probe_uses_its_provider_endpoint_model_and_actual_prompt(api_client, user, local_provider, provider, endpoint, suffix):
    model, _ = configure(user, provider, local_provider['base'] + endpoint)
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/test/', {'prompt': 'Keep Customer_ID unchanged'}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['success'] is True
    assert response.data['response'] == 'fixture answer'
    sent = local_provider['requests'][-1]
    assert sent['path'] == suffix
    assert sent['body']['model'] == model.model_id
    assert sent['body']['messages'][-1]['content'] == 'Keep Customer_ID unchanged'


@pytest.mark.parametrize('mode', ['empty', 'error', 'body_error'])
def test_ollama_probe_cannot_report_empty_or_error_as_success(api_client, user, local_provider, mode):
    model, _ = configure(user, 'ollama', local_provider['base'] + '/ollama')
    local_provider['mode'] = mode
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/test/', {}, format='json')
    assert response.status_code >= 400
    assert response.data['success'] is False
    assert response.data.get('error')
    assert 'fixture-secret-value' not in json.dumps(response.data)


def test_verification_uses_the_selected_credential_and_never_exposes_its_secret(api_client, user, local_provider):
    model, credential = configure(user, 'anthropic', local_provider['base'] + '/anthropic/v1')
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/api-keys/{credential.pk}/verify/', {}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['valid'] is True
    assert local_provider['requests'][-1]['path'] == '/anthropic/v1/messages'
    assert local_provider['requests'][-1]['body']['model'] == model.model_id
    assert 'fixture-secret-value' not in json.dumps(response.data)


@pytest.mark.parametrize('disabled', ['credential', 'expired', 'model', 'provider'])
def test_disabled_or_expired_resources_are_rejected_before_network(api_client, user, local_provider, disabled):
    model, credential = configure(user, 'custom', local_provider['base'] + '/compat/v1')
    if disabled == 'credential':
        credential.is_active = False
        credential.save()
    elif disabled == 'expired':
        credential.expires_at = timezone.now()
        credential.save()
    elif disabled == 'model':
        model.is_active = False
        model.save()
    else:
        model.provider.is_active = False
        model.provider.save()
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/test/', {}, format='json')
    assert response.status_code >= 400
    assert local_provider['requests'] == []


def test_key_create_and_edit_return_only_masked_read_metadata(api_client, user):
    api_client.force_authenticate(user)
    response = api_client.post('/api/v1/gateway/api-keys/', {'name': 'Owned key', 'provider': 'custom', 'api_key': 'fixture-secret-value', 'endpoint': 'http://127.0.0.1:1/v1'}, format='json')
    assert response.status_code == 201, response.data
    assert response.data['id']
    assert response.data['masked_key']
    assert 'api_key' not in response.data
    assert 'fixture-secret-value' not in json.dumps(response.data)
    edited = api_client.put(f"/api/v1/gateway/api-keys/{response.data['id']}/", {'name': 'Renamed', 'provider': 'custom', 'is_active': False, 'endpoint': 'http://127.0.0.1:1/v1'}, format='json')
    assert edited.status_code == 200, edited.data
    assert edited.data['masked_key'] == response.data['masked_key']
    assert edited.data['is_active'] is False
    assert 'fixture-secret-value' not in json.dumps(edited.data)


def test_catalog_default_is_admin_only_and_preserves_defaults_of_other_types(api_client, user):
    provider = ModelProvider.objects.create(name='Default fixture', slug='default-fixture')
    previous = AIModel.objects.create(provider=provider, name='Previous', model_id='previous', is_default=True)
    selected = AIModel.objects.create(provider=provider, name='Selected', model_id='selected')
    embedding = AIModel.objects.create(provider=provider, name='Embedding', model_id='embed', model_type='embedding', is_default=True)
    api_client.force_authenticate(user)
    url = f'/api/v1/gateway/models/{selected.pk}/set_default/'
    assert api_client.post(url, {'is_default': True}, format='json').status_code == 403
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    set_response = api_client.post(url, {'is_default': True}, format='json')
    assert set_response.status_code == 200, set_response.data
    assert set_response.data['is_default'] is True
    assert set_response.data['provider_slug'] == provider.slug
    previous.refresh_from_db()
    embedding.refresh_from_db()
    assert previous.is_default is False
    assert embedding.is_default is True
    defaults = api_client.get('/api/v1/gateway/models/default_models/').data
    assert str(defaults['chat']['id']) == str(selected.pk)
    assert str(defaults['embedding']['id']) == str(embedding.pk)
    assert api_client.post(url, {'is_default': False}, format='json').status_code == 200
    selected.refresh_from_db()
    assert selected.is_default is False
    assert api_client.get('/api/v1/gateway/models/default_models/').data.get('chat') is None
    assert api_client.post(url, {'is_default': 'true'}, format='json').status_code == 400


@pytest.mark.parametrize('disabled', ['model', 'provider'])
def test_catalog_default_rejects_disabled_resources(api_client, user, disabled):
    model, _ = configure(user, 'custom', 'http://127.0.0.1:1/v1')
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    target = model if disabled == 'model' else model.provider
    target.is_active = False
    target.save(update_fields=['is_active'])
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/set_default/', {'is_default': True}, format='json')
    assert response.status_code == 404


@pytest.mark.parametrize('provider,endpoint,path', [('google', '/google/v1beta', '/google/v1beta/models/fixture-model:generateContent'), ('azure', '/azure', '/azure/openai/deployments/fixture-model/chat/completions?api-version=2024-02-01')])
def test_native_google_and_azure_use_the_configured_protocol(api_client, user, local_provider, provider, endpoint, path):
    model, _ = configure(user, provider, local_provider['base'] + endpoint)
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/test/', {'prompt': 'Native fixture'}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['response'] == 'fixture answer'
    sent = local_provider['requests'][-1]
    assert sent['path'] == path
    assert sent['google_key' if provider == 'google' else 'azure_key'] == 'fixture-secret-value'
    if provider == 'google':
        assert sent['body']['contents'][0]['parts'][0]['text'] == 'Native fixture'


def test_embedding_model_uses_embedding_api_instead_of_chat(api_client, user, local_provider):
    model, _ = configure(user, 'custom', local_provider['base'] + '/compat/v1', model_type='embedding')
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/test/', {'prompt': 'Embed this'}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['probe_type'] == 'embedding'
    assert local_provider['requests'][-1]['path'] == '/compat/v1/embeddings'
    assert local_provider['requests'][-1]['body']['input'] == ['Embed this']


@pytest.mark.parametrize('provider', ['custom', 'ollama', 'anthropic', 'google'])
def test_malformed_provider_payload_is_a_transparent_failure(api_client, user, local_provider, provider):
    model, _ = configure(user, provider, local_provider['base'] + '/fixture')
    local_provider['mode'] = 'malformed'
    api_client.force_authenticate(user)
    response = api_client.post(f'/api/v1/gateway/models/{model.pk}/test/', {}, format='json')
    assert response.status_code == 502, response.data
    assert response.data['error_code'] == 'empty_response'


def test_verify_cannot_use_another_owners_credential(api_client, user, django_user_model, local_provider):
    _, credential = configure(user, 'custom', local_provider['base'] + '/compat/v1')
    outsider = django_user_model.objects.create_user(username='gateway-outsider', email='gateway-outsider@example.test', password='fixture-password')
    api_client.force_authenticate(outsider)
    response = api_client.post(f'/api/v1/gateway/api-keys/{credential.pk}/verify/', {}, format='json')
    assert response.status_code == 404
    assert local_provider['requests'] == []
