"""Real connection checks, read-only resource pulls and webhook delivery."""
import base64
import hashlib
import hmac
import ipaddress
import json
import re
import socket
import time
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, quote

import httpx
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .catalog import (CONNECTORS, EVENT_LABELS, API_ENDPOINTS, SHEETS_ENDPOINT,
                      TELEGRAM_ENDPOINT, NOTION_VERSION, REQUEST_TIMEOUT,
                      MAX_RESPONSE_BYTES, RESULT_LIMIT, TEST_MESSAGE, MAX_FIELD_LENGTH, OFFICIAL_PROXY_HOSTS)
from .models import Integration, IntegrationDelivery


class ConnectorError(ValueError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def validate_url(url, connector):
    try:
        parsed = urlsplit(url)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        raise ConnectorError('Webhook 地址格式不正确。')
    if not host or parsed.username or parsed.password or parsed.fragment:
        raise ConnectorError('Webhook 地址必须包含主机，且不能包含用户名、密码或片段。')
    allowed = getattr(settings, 'INTEGRATIONS_ALLOWED_PRIVATE_HOSTS', ())
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and host in allowed):
        raise ConnectorError('Webhook 必须使用 HTTPS；内网 HTTP 需由管理员明确允许。')
    hosts = connector.get('hosts', ())
    if hosts and not any(host == suffix or (suffix.startswith('.') and host.endswith(suffix)) for suffix in hosts):
        raise ConnectorError('Webhook 域名与所选服务不匹配，请从该服务官方控制台复制地址。')
    return parsed, host, port


def validate_config(connector, config, secrets):
    if not isinstance(config, dict) or not isinstance(secrets, dict):
        raise ConnectorError('配置和凭证必须是对象。')
    fields = {f['key']: f for f in connector['fields']}
    extra = set(config) | set(secrets)
    if extra - set(fields) - {'events'}:
        raise ConnectorError('配置包含不支持的字段。')
    values = {**config, **secrets}
    for key, field in fields.items():
        value = values.get(key, '')
        if not isinstance(value, str) or len(value) > MAX_FIELD_LENGTH:
            raise ConnectorError(f"{field['label']}格式不正确或过长。")
        if field['required'] and not value.strip():
            raise ConnectorError(f"请填写{field['label']}。")
        if field['kind'] == 'url' and value:
            validate_url(value, connector)
    events = config.get('events', [])
    if not isinstance(events, list) or any(not isinstance(e, str) or e not in EVENT_LABELS for e in events):
        raise ConnectorError('订阅事件无效。')
    if connector['mode'] == 'api' and events:
        raise ConnectorError('此数据服务不支持事件通知。')
    if connector['id'] == 'google_sheets' and not re.fullmatch(r'[\w-]+', values['spreadsheet_id']):
        raise ConnectorError('请输入电子表格 ID，而非完整网址。')
    if connector['id'] == 'telegram' and not re.fullmatch(r'[\d]+:[\w-]+', values['token']):
        raise ConnectorError('Telegram Bot Token 格式不正确。')
    return values


def _request(method, url, *, headers=None, params=None, body=None):
    """Pin DNS to a validated address; do not follow redirects or ambient proxies."""
    parsed, host, port = validate_url(url, {})
    proxy = getattr(settings, 'INTEGRATIONS_HTTP_PROXY', '') if any(
        host == suffix or (suffix.startswith('.') and host.endswith(suffix)) for suffix in OFFICIAL_PROXY_HOSTS
    ) else ''
    addresses = []
    # Only known provider domains may delegate DNS to an explicitly trusted proxy.
    # Arbitrary webhook hosts still require local public-IP validation and pinning.
    if not proxy:
        try:
            addresses = socket.getaddrinfo(host, port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ConnectorError('无法解析服务域名，请检查地址或服务器网络。')
        allowed = getattr(settings, 'INTEGRATIONS_ALLOWED_PRIVATE_HOSTS', ())
        if not addresses or (host not in allowed and any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses)):
            raise ConnectorError('目标地址属于内网或保留网络，请由管理员配置允许的服务主机。')
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=False, trust_env=False, proxy=proxy or None) as client:
            request = client.build_request(method, url, headers=headers, params=params, content=body)
            if not proxy:
                request.url = request.url.copy_with(host=addresses[0][4][0])
                request.headers['Host'] = parsed.netloc
                request.extensions['sni_hostname'] = host
            response = client.send(request, stream=True)
            try:
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise ConnectorError('服务响应过大，请缩小查询范围。', response.status_code)
                    chunks.append(chunk)
                return response.status_code, b''.join(chunks).decode('utf-8', errors='replace')
            finally:
                response.close()
    except httpx.TimeoutException:
        raise ConnectorError('连接超时，请检查目标服务和服务器网络后重试。')
    except httpx.HTTPError:
        raise ConnectorError('无法连接目标服务，请检查网络、证书和地址。')


def _check_response(kind, status, text, read=False):
    if not 200 <= status < 300:
        reasons = {401: '凭证无效或已过期', 403: '权限不足或目标禁止访问', 404: '地址或资源不存在', 429: '请求过于频繁，请稍后重试'}
        raise ConnectorError(f"服务返回 HTTP {status}：{reasons.get(status, '请求未被接受，请检查配置和服务状态')}。", status)
    try:
        data = json.loads(text) if text else None
    except json.JSONDecodeError:
        data = None
    if kind == 'slack' and text.strip() != 'ok':
        raise ConnectorError('Slack 未确认消息发送成功，请检查 Webhook 与频道权限。', status)
    if kind in ('feishu', 'dingtalk', 'wechat_work'):
        key = 'code' if kind == 'feishu' else 'errcode'
        if not isinstance(data, dict) or data.get(key) != 0:
            code = data.get(key, 'unknown') if isinstance(data, dict) else 'invalid_response'
            raise ConnectorError(f'机器人拒绝了消息（错误码 {code}），请检查签名、关键词或访问限制。', status)
    if kind == 'telegram' and (not isinstance(data, dict) or data.get('ok') is not True):
        raise ConnectorError('Telegram 未确认消息发送成功，请检查 Token、Chat ID 与机器人权限。', status)
    if CONNECTORS[kind]['mode'] == 'api' and not isinstance(data, (dict, list)):
        raise ConnectorError('服务未返回有效 JSON 数据，无法确认连接。', status)
    if CONNECTORS[kind]['mode'] == 'api':
        valid = False
        if not read:
            identity_key = {'google_sheets': 'spreadsheetId', 'google_drive': 'user'}.get(kind, 'id')
            valid = isinstance(data, dict) and bool(data.get(identity_key))
        elif kind in ('github', 'gitlab'):
            valid = isinstance(data, list)
        elif kind == 'google_sheets':
            valid = isinstance(data, dict) and isinstance(data.get('range'), str) and isinstance(data.get('values', []), list)
        else:
            list_key = {'notion': 'results', 'airtable': 'bases', 'google_drive': 'files'}[kind]
            valid = isinstance(data, dict) and isinstance(data.get(list_key), list)
        if not valid:
            raise ConnectorError('服务响应缺少预期的身份或资源信息，无法确认操作成功。', status)
    return data


def _webhook_request(kind, values, payload):
    message = payload.get('message') or f"Flowly · {EVENT_LABELS.get(payload['event'], payload['event'])}\n{payload.get('workflow_name', '')}\n执行 ID：{payload.get('execution_id', '')}"
    if values.get('keyword'):
        message = f"{values['keyword']} {message}"
    url = values.get('webhook_url', '')
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Flowly-Integrations/1.0'}
    if kind == 'telegram':
        url = TELEGRAM_ENDPOINT.format(token=values['token'])
        body = {'chat_id': values['chat_id'], 'text': message}
    elif kind in ('feishu', 'dingtalk', 'wechat_work'):
        body = {'msg_type': 'text', 'content': {'text': message}} if kind == 'feishu' else {'msgtype': 'text', 'text': {'content': message}}
        if values.get('secret') and kind == 'feishu':
            stamp = str(int(time.time()))
            key = f"{stamp}\n{values['secret']}".encode()
            body.update(timestamp=stamp, sign=base64.b64encode(hmac.new(key, b'', hashlib.sha256).digest()).decode())
        if values.get('secret') and kind == 'dingtalk':
            stamp = str(int(time.time() * 1000))
            signature = base64.b64encode(hmac.new(values['secret'].encode(), f"{stamp}\n{values['secret']}".encode(), hashlib.sha256).digest()).decode()
            parts = urlsplit(url)
            query = [(k, v) for k, v in parse_qsl(parts.query) if k not in ('timestamp', 'sign')]
            url = urlunsplit(parts._replace(query=urlencode([*query, ('timestamp', stamp), ('sign', signature)])))
    elif kind == 'slack':
        body = {'text': message}
    elif kind == 'discord':
        body = {'content': message, 'allowed_mentions': {'parse': []}}
    elif kind == 'microsoft_teams':
        body = {'type': 'message', 'attachments': [{'contentType': 'application/vnd.microsoft.card.adaptive', 'content': {
            '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json', 'type': 'AdaptiveCard', 'version': '1.2',
            'body': [{'type': 'TextBlock', 'text': message, 'wrap': True}]}}]}
    else:
        body = payload
    content = json.dumps(body, ensure_ascii=False).encode()
    if values.get('token') and kind != 'telegram':
        headers['Authorization'] = f"Bearer {values['token']}"
    if kind == 'custom' and values.get('secret'):
        headers['X-Webhook-Signature'] = hmac.new(values['secret'].encode(), content, hashlib.sha256).hexdigest()
    return 'POST', url, headers, None, content


def _api_request(kind, values, read):
    headers = {'Authorization': f"Bearer {values['token']}", 'Accept': 'application/json', 'User-Agent': 'Flowly-Integrations/1.0'}
    method, params, body = 'GET', {}, None
    if kind == 'google_sheets':
        url = SHEETS_ENDPOINT.format(spreadsheet_id=quote(values['spreadsheet_id'], safe=''))
        if read:
            url += '/values/' + quote(values['range'], safe='')
        else:
            params = {'fields': 'spreadsheetId,properties.title'}
    else:
        url = API_ENDPOINTS[kind][int(read)]
    if kind == 'github':
        headers['Accept'] = 'application/vnd.github+json'
        if read:
            params = {'per_page': RESULT_LIMIT, 'sort': 'updated'}
    elif kind == 'gitlab' and read:
        params = {'membership': 'true', 'per_page': RESULT_LIMIT}
    elif kind == 'notion':
        headers.update({'Notion-Version': NOTION_VERSION, 'Content-Type': 'application/json'})
        if read:
            method, body = 'POST', json.dumps({'page_size': RESULT_LIMIT}).encode()
    elif kind == 'google_drive':
        params = {'pageSize': RESULT_LIMIT, 'fields': 'files(id,name,mimeType),nextPageToken'} if read else {'fields': 'user(displayName)'}
    return method, url, headers, params, body


def _summary(kind, data):
    """Keep only resource labels and IDs, never arbitrary provider payloads or tokens."""
    if kind == 'google_sheets':
        values = data.get('values', [])
        return {'range': data.get('range', ''), 'rows': values[:RESULT_LIMIT], 'count': min(len(values), RESULT_LIMIT), 'truncated': len(values) > RESULT_LIMIT}
    keys = {'notion': 'results', 'airtable': 'bases', 'google_drive': 'files'}
    rows = data if isinstance(data, list) else data.get(keys.get(kind, 'results'), [])
    if not isinstance(rows, list):
        raise ConnectorError('服务返回的资源列表格式不正确。')
    items = []
    for row in rows[:RESULT_LIMIT]:
        if not isinstance(row, dict):
            raise ConnectorError('服务返回的资源格式不正确。')
        name = row.get('full_name') or row.get('name') or row.get('path_with_namespace')
        if kind == 'notion':
            titles = row.get('title', [])
            for value in row.get('properties', {}).values():
                if isinstance(value, dict) and value.get('type') == 'title':
                    titles = value.get('title', [])
            name = ''.join(t.get('plain_text', '') for t in titles)
        items.append({'id': str(row.get('id', '')), 'name': name or '未命名'})
    return {'items': items, 'count': len(items), 'limited': True}


def run_check(integration, *, read=False, payload=None):
    started, version = time.monotonic(), integration.updated_at
    connector = CONNECTORS.get(integration.integration_type)
    result = {'success': False, 'message': '', 'status_code': None}
    try:
        if not connector:
            raise ConnectorError('此集成类型尚未实现。')
        values = validate_config(connector, integration.config, integration.get_secrets())
        spec = _api_request(connector['id'], values, read) if connector['mode'] == 'api' else _webhook_request(
            connector['id'], values, payload or {'event': 'connection.test', 'message': TEST_MESSAGE})
        method, url, headers, params, body = spec
        status, text = _request(method, url, headers=headers, params=params, body=body)
        data = _check_response(connector['id'], status, text, read)
        result.update(success=True, status_code=status, message='数据读取成功。' if read and connector['mode'] == 'api' else '目标服务已确认本次请求。')
        if read and connector['mode'] == 'api':
            result['data'] = _summary(connector['id'], data)
    except (ConnectorError, ValueError) as exc:
        result.update(success=False, message=str(exc), status_code=getattr(exc, 'status_code', None))
    except (TypeError, KeyError, AttributeError):
        result.update(success=False, message='服务响应格式不正确，无法确认操作成功。')
    result['duration_ms'] = round((time.monotonic() - started) * 1000)
    now = timezone.now()
    updates = dict(last_checked_at=now, verification_status='success' if result['success'] else 'failed',
                   is_connected=result['success'], last_error='' if result['success'] else result['message'])
    if read:
        updates.update(last_sync_at=now, sync_status='success' if result['success'] else 'failed',
                       total_syncs=F('total_syncs') + 1, failed_syncs=F('failed_syncs') + int(not result['success']))
        if result.get('data') is not None:
            updates['last_result'] = result['data']
    # An edit or disconnect during an in-flight request must win over its stale response.
    changed = Integration.objects.filter(pk=integration.pk, updated_at=version, is_active=True).update(**updates)
    if not changed:
        result.update(success=False, message='配置已变更或已断开，本次结果未用于更新连接状态。')
    if Integration.objects.filter(pk=integration.pk).exists():
        integration.refresh_from_db()
    return result


def deliver(integration, *, payload=None, event_key=None):
    payload = payload or {'event': 'connection.test', 'message': TEST_MESSAGE}
    delivery, created = IntegrationDelivery.objects.get_or_create(
        integration=integration, event_key=event_key or str(uuid.uuid4()),
        defaults={'event': payload['event'], 'payload': payload})
    if not created and delivery.status != 'pending':
        return delivery
    claimed = IntegrationDelivery.objects.filter(pk=delivery.pk, status='pending').update(status='sending')
    if not claimed:
        return delivery
    if not integration.is_active:
        result = {'success': False, 'message': '连接已停用，未发送。', 'status_code': None, 'duration_ms': 0}
    else:
        result = run_check(integration, read=True, payload=payload)
    delivery.status = 'success' if result['success'] else 'failed'
    delivery.message = result['message']
    delivery.status_code = result['status_code']
    delivery.duration_ms = result['duration_ms']
    delivery.completed_at = timezone.now()
    delivery.save(update_fields=['status', 'message', 'status_code', 'duration_ms', 'completed_at'])
    return delivery
