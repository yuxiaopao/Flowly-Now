"""Bounded connectivity probes using the selected catalog provider and owned credential."""
import math
from urllib.parse import quote, urlsplit

import requests
from django.conf import settings

from config.constants import OPENAI_API_URL, ANTHROPIC_API_URL, OLLAMA_BASE_URL
from gateway.models import AIModel
from workflows.models import APICredential

PROVIDER_ALIASES = {'azure-openai': 'azure', 'google-genai': 'google'}
COMPATIBLE_PROVIDERS = frozenset({'openai', 'custom', 'deepseek', 'mistral', 'groq', 'dashscope', 'agnes'})
DEFAULT_ENDPOINTS = {'openai': OPENAI_API_URL, 'anthropic': ANTHROPIC_API_URL,
                     'google': 'https://generativelanguage.googleapis.com/v1beta'}
DEFAULT_PROMPT = 'Reply briefly to this connectivity test.'
PROBE_MAX_TOKENS = 32
MAX_PROMPT_LENGTH = 4000


class ProbeFailure(Exception):
    def __init__(self, message, *, status=400, code='configuration_error'):
        super().__init__(message)
        self.status = status
        self.code = code


def canonical_provider(provider):
    return PROVIDER_ALIASES.get(provider, provider)


def _object(value):
    return value if isinstance(value, dict) else {}


def _array(value):
    return value if isinstance(value, list) else []


def _check_credential(user, credential):
    if not user or not user.is_active or credential.owner_id != user.pk:
        raise ProbeFailure('无权使用此凭证。', status=403, code='permission_denied')
    if not credential.is_active or credential.is_expired():
        raise ProbeFailure('凭证已禁用或过期，请更新后再验证。', code='credential_unavailable')
    if credential.scope == 'tenant':
        from tenants.access import get_accessible_tenant_ids
        if not credential.tenant_id or credential.tenant_id not in get_accessible_tenant_ids(user):
            raise ProbeFailure('团队凭证当前不可用。', status=403, code='permission_denied')


def _owned_credential(user, provider):
    aliases = [provider] + [key for key, value in PROVIDER_ALIASES.items() if value == provider]
    rows = APICredential.objects.filter(owner=user, service_type__in=aliases, credential_type='api_key').order_by('-created_at')
    for credential in rows:
        if credential.is_active and not credential.is_expired():
            _check_credential(user, credential)
            return credential
    if rows.exists() or provider != 'ollama':
        raise ProbeFailure('此提供商没有可用的个人凭证，请先添加或启用未过期的凭证。', code='credential_unavailable')
    return None


def _request(method, url, *, key, headers, payload=None):
    timeout = float(getattr(settings, 'GATEWAY_PROBE_TIMEOUT_SECONDS', 15))
    try:
        response = requests.request(method, url, json=payload, headers=headers, timeout=timeout)
    except requests.Timeout as exc:
        raise ProbeFailure('模型服务连接超时。', status=504, code='upstream_timeout') from exc
    except requests.RequestException as exc:
        raise ProbeFailure('无法连接配置的模型服务，请检查地址与网络。', status=502, code='upstream_unavailable') from exc
    try:
        data = response.json()
    except (ValueError, TypeError) as exc:
        raise ProbeFailure('模型服务返回了无效 JSON。', status=502, code='invalid_response') from exc
    error = data.get('error') if isinstance(data, dict) else None
    if not response.ok or error:
        message = error.get('message', error.get('error', '模型服务拒绝请求。')) if isinstance(error, dict) else error
        message = str(message or '模型服务拒绝请求。')
        if key:
            message = message.replace(key, '[redacted]')
        raise ProbeFailure(f'模型服务 HTTP {response.status_code}：{message[:500]}', status=502, code='upstream_error')
    if not isinstance(data, dict):
        raise ProbeFailure('模型服务响应结构无效。', status=502, code='invalid_response')
    return data


def _probe(user, *, provider, model_id, model_type, credential=None, prompt=None):
    provider = canonical_provider(provider)
    if provider not in COMPATIBLE_PROVIDERS | {'anthropic', 'azure', 'google', 'ollama'}:
        raise ProbeFailure('此服务类型不是受支持的模型提供商。', code='unsupported_provider')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_LENGTH:
        raise ProbeFailure(f'测试提示不能为空，且不能超过 {MAX_PROMPT_LENGTH} 字。', code='invalid_input')
    config = _object(credential.service_config) if credential else {}
    key = credential.get_decrypted_data() if credential else ''
    if provider != 'ollama' and not key:
        raise ProbeFailure('凭证内容为空，请更新密钥。', code='credential_unavailable')
    endpoint = config.get('endpoint') or config.get('base_url') or DEFAULT_ENDPOINTS.get(provider)
    if provider == 'ollama' and not endpoint:
        endpoint = getattr(settings, 'OLLAMA_BASE_URL', OLLAMA_BASE_URL)
    if not isinstance(endpoint, str) or urlsplit(endpoint).scheme not in ('http', 'https') or not urlsplit(endpoint).netloc:
        raise ProbeFailure('请配置此提供商的有效 HTTP 或 HTTPS API Endpoint。', code='invalid_endpoint')
    if urlsplit(endpoint).username or urlsplit(endpoint).password or urlsplit(endpoint).query or urlsplit(endpoint).fragment:
        raise ProbeFailure('API Endpoint 不应包含登录信息、查询参数或片段。', code='invalid_endpoint')
    endpoint = endpoint.rstrip('/')
    model_name = str(model_id).removeprefix('models/')
    headers = {'Content-Type': 'application/json'}
    if provider == 'anthropic':
        headers.update({'x-api-key': key, 'anthropic-version': config.get('api_version') or '2023-06-01'})
    elif provider == 'azure':
        headers['api-key'] = key
    elif provider == 'google':
        headers['x-goog-api-key'] = key
    elif key:
        headers['Authorization'] = f'Bearer {key}'

    if model_type not in ('chat', 'embedding'):
        url = endpoint + ('/api/tags' if provider == 'ollama' else '/models')
        if provider == 'azure':
            url = endpoint + '/openai/models?api-version=' + quote(config.get('api_version') or '2024-02-01', safe='')
        data = _request('GET', url, key=key, headers=headers)
        items = data.get('models') if provider in ('google', 'ollama') else data.get('data')
        ids = [str(item.get('id') or item.get('name') or '').removeprefix('models/') for item in _array(items) if isinstance(item, dict)]
        if model_name not in ids:
            raise ProbeFailure('提供商目录中未找到此模型。', status=502, code='model_unavailable')
        result = {'response': '模型目录访问验证成功；本次没有执行图像或音频生成。', 'probe_type': 'catalog'}
    else:
        if model_type == 'embedding':
            if provider == 'anthropic':
                raise ProbeFailure('Anthropic 不提供此嵌入模型接口。', code='unsupported_capability')
            if provider == 'ollama':
                url, payload = endpoint + '/api/embed', {'model': model_id, 'input': [prompt]}
            elif provider == 'google':
                url = endpoint + '/models/' + quote(model_name, safe='') + ':embedContent'
                payload = {'model': 'models/' + model_name, 'content': {'parts': [{'text': prompt}]}}
            else:
                url, payload = endpoint + '/embeddings', {'model': model_id, 'input': [prompt]}
        elif provider == 'ollama':
            url, payload = endpoint + '/api/chat', {'model': model_id, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False, 'options': {'num_predict': PROBE_MAX_TOKENS}}
        elif provider == 'anthropic':
            url, payload = endpoint + '/messages', {'model': model_id, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': PROBE_MAX_TOKENS}
        elif provider == 'google':
            url = endpoint + '/models/' + quote(model_name, safe='') + ':generateContent'
            payload = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': PROBE_MAX_TOKENS}}
        else:
            url, payload = endpoint + '/chat/completions', {'model': model_id, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': PROBE_MAX_TOKENS}
        if provider == 'azure':
            operation = 'embeddings' if model_type == 'embedding' else 'chat/completions'
            deployment = config.get('deployment_name') or model_id
            url = endpoint + '/openai/deployments/' + quote(deployment, safe='') + '/' + operation + '?api-version=' + quote(config.get('api_version') or '2024-02-01', safe='')
        data = _request('POST', url, key=key, headers=headers, payload=payload)
        if model_type == 'embedding':
            vectors = data.get('embeddings') if provider == 'ollama' else [_object(data.get('embedding')).get('values')] if provider == 'google' else [item.get('embedding') for item in _array(data.get('data')) if isinstance(item, dict)]
            vectors = _array(vectors)
            if not vectors or any(not isinstance(vector, list) or not vector or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in vector) for vector in vectors):
                raise ProbeFailure('模型服务未返回有效嵌入向量。', status=502, code='empty_response')
            result = {'response': f'嵌入验证成功：{len(vectors)} 个向量，{len(vectors[0])} 维。', 'probe_type': 'embedding'}
        else:
            if provider == 'ollama':
                content = _object(data.get('message')).get('content')
            elif provider == 'anthropic':
                content = ''.join(str(item.get('text') or '') for item in _array(data.get('content')) if isinstance(item, dict) and item.get('type') == 'text')
            elif provider == 'google':
                candidates = _array(data.get('candidates'))
                parts = _array(_object(_object(candidates[0]).get('content')).get('parts')) if candidates else []
                content = ''.join(str(item.get('text') or '') for item in parts if isinstance(item, dict))
            else:
                choices = _array(data.get('choices'))
                content = _object(_object(choices[0]).get('message')).get('content') if choices else ''
            if not isinstance(content, str) or not content.strip():
                raise ProbeFailure('模型服务没有返回可用文本，不能判定测试成功。', status=502, code='empty_response')
            result = {'response': content.replace(key, '[redacted]') if key else content, 'probe_type': 'chat'}
    if credential:
        credential.update_last_used()
    return {**result, 'provider': provider, 'model_id': model_id}


def test_model_connection(user, model, prompt=DEFAULT_PROMPT):
    if not model.is_active or not model.provider.is_active:
        raise ProbeFailure('模型或提供商已禁用。', code='model_unavailable')
    provider = canonical_provider(model.provider.slug)
    return _probe(user, provider=provider, model_id=model.model_id, model_type=model.model_type,
                  credential=_owned_credential(user, provider), prompt=prompt)


def verify_credential(user, credential, model_id=None):
    _check_credential(user, credential)
    provider = canonical_provider(credential.service_type)
    config = credential.service_config or {}
    selected = model_id or config.get('model') or config.get('model_id') or config.get('deployment_name')
    if selected is not None and (not isinstance(selected, str) or not selected.strip() or len(selected) > 200):
        raise ProbeFailure('验证模型必须为不超过 200 字的模型 ID。', code='invalid_input')
    aliases = [provider] + [key for key, value in PROVIDER_ALIASES.items() if value == provider]
    catalog = AIModel.objects.filter(provider__slug__in=aliases, provider__is_active=True, is_active=True)
    model = catalog.filter(model_id=selected).first() if selected else catalog.order_by('-is_default', 'name').first()
    if not model and selected and AIModel.objects.filter(provider__slug__in=aliases, model_id=selected).exists():
        raise ProbeFailure('配置的验证模型或提供商已禁用。', code='model_unavailable')
    if not selected and not model:
        raise ProbeFailure('请配置验证模型，或添加此提供商的启用目录模型。', code='model_required')
    return _probe(user, provider=provider, model_id=selected or model.model_id,
                  model_type=model.model_type if model else 'chat', credential=credential, prompt=DEFAULT_PROMPT)
