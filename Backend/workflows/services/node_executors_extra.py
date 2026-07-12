"""
扩展节点执行器：控制流 + 第三方集成
供 LangChainService 委托调用
"""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict
from xml.etree import ElementTree

import requests

logger = logging.getLogger(__name__)


def _render_template(value: Any, input_data: Dict, render_fn) -> Any:
    if isinstance(value, str):
        return render_fn(value, input_data)
    if isinstance(value, dict):
        return {k: _render_template(v, input_data, render_fn) for k, v in value.items()}
    if isinstance(value, list):
        return [_render_template(v, input_data, render_fn) for v in value]
    return value


def run_switch_node(service, node_config: Dict, input_data: Dict) -> Dict:
    branches = node_config.get('branches') or []
    default_branch = node_config.get('defaultBranch', '默认')
    matched = default_branch

    for branch in branches:
        expression = branch.get('expression') or ''
        field = branch.get('field') or ''
        operator = branch.get('operator') or 'equals'
        expected = branch.get('value')

        result = False
        if expression:
            rendered = service._render_template(expression, input_data)
            try:
                result = bool(eval(rendered, {'__builtins__': {}}, {'input': input_data}))
            except Exception:
                result = bool(rendered)
        elif field:
            actual = service._get_nested_value(input_data, field)
            if operator == 'equals':
                result = str(actual) == str(expected)
            elif operator == 'not_equals':
                result = str(actual) != str(expected)
            elif operator == 'contains':
                result = str(expected) in str(actual)
            elif operator == 'greater_than':
                result = float(actual or 0) > float(expected or 0)
            elif operator == 'less_than':
                result = float(actual or 0) < float(expected or 0)

        if result:
            matched = branch.get('label') or branch.get('id') or matched
            break

    return {
        'success': True,
        'output': {'matched_branch': matched},
        'branch': matched,
    }


def run_merge_node(service, node_config: Dict, input_data: Dict) -> Dict:
    mode = node_config.get('mode') or 'combine'
    items = input_data.get('items') if isinstance(input_data.get('items'), list) else [input_data]

    if mode == 'override':
        output = items[-1] if items else input_data
    elif mode == 'zip':
        output = {'merged': items}
    else:
        if all(isinstance(i, dict) for i in items):
            merged = {}
            for item in items:
                merged.update(item)
            output = merged
        else:
            output = {'items': items}

    return {'success': True, 'output': output}


def run_filter_node(service, node_config: Dict, input_data: Dict) -> Dict:
    conditions = node_config.get('conditions') or []
    combine_mode = node_config.get('combineMode') or 'and'
    items = input_data.get('items') if isinstance(input_data.get('items'), list) else [input_data]

    def match_item(item: Dict) -> bool:
        results = []
        for cond in conditions:
            field = cond.get('field') or ''
            operator = cond.get('operator') or 'equals'
            expected = cond.get('value')
            actual = service._get_nested_value(item, field) if field else item

            if operator == 'equals':
                results.append(str(actual) == str(expected))
            elif operator == 'not_equals':
                results.append(str(actual) != str(expected))
            elif operator == 'contains':
                results.append(str(expected) in str(actual))
            elif operator == 'exists':
                results.append(actual is not None and actual != '')
            else:
                results.append(False)

        if not results:
            return True
        return all(results) if combine_mode == 'and' else any(results)

    filtered = [i for i in items if match_item(i if isinstance(i, dict) else {'value': i})]
    return {'success': True, 'output': {'items': filtered, 'count': len(filtered)}}


def run_split_node(service, node_config: Dict, input_data: Dict) -> Dict:
    batch_size = int(node_config.get('batchSize') or 10)
    field = node_config.get('field') or 'items'
    source = service._get_nested_value(input_data, field) if field else input_data
    if not isinstance(source, list):
        source = [source]

    batches = [source[i:i + batch_size] for i in range(0, len(source), batch_size)]
    return {
        'success': True,
        'output': {
            'batches': batches,
            'batch_count': len(batches),
            'total_items': len(source),
        },
    }


def run_set_node(service, node_config: Dict, input_data: Dict) -> Dict:
    output = {}
    fields = node_config.get('fields') or []

    for field in fields:
        name = field.get('name')
        if not name:
            continue
        value = service._render_template(str(field.get('value', '')), input_data)
        output[name] = value

    return {'success': True, 'output': output}


def run_datetime_node(service, node_config: Dict, input_data: Dict) -> Dict:
    operation = node_config.get('operation') or 'format'
    fmt = node_config.get('format') or '%Y-%m-%d %H:%M:%S'
    now = datetime.now(timezone.utc)

    if operation == 'now':
        output = now.isoformat()
    elif operation == 'parse':
        raw = service._render_template(node_config.get('input') or '', input_data)
        try:
            parsed = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            output = parsed.isoformat()
        except ValueError:
            output = str(raw)
    else:
        py_fmt = (
            fmt.replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d')
            .replace('HH', '%H').replace('mm', '%M').replace('ss', '%S')
        )
        output = now.strftime(py_fmt)

    return {'success': True, 'output': {'datetime': output}}


def run_rss_feed_node(service, node_config: Dict, input_data: Dict) -> Dict:
    url = service._render_template(node_config.get('url') or '', input_data)
    max_items = int(node_config.get('maxItems') or 20)
    if not url:
        return {'success': False, 'error': 'RSS Feed URL 不能为空'}

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.content)
    items = []
    for item in root.findall('.//item')[:max_items]:
        items.append({
            'title': (item.findtext('title') or '').strip(),
            'link': (item.findtext('link') or '').strip(),
            'description': (item.findtext('description') or '').strip(),
            'pubDate': (item.findtext('pubDate') or '').strip(),
        })
    if not items:
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry')[:max_items]:
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            items.append({
                'title': (entry.findtext('{http://www.w3.org/2005/Atom}title') or '').strip(),
                'link': link_el.get('href', '') if link_el is not None else '',
                'description': (entry.findtext('{http://www.w3.org/2005/Atom}summary') or '').strip(),
            })

    return {'success': True, 'output': {'items': items, 'count': len(items)}}


def run_integration_node(service, node_type: str, node_config: Dict, input_data: Dict) -> Dict:
    from .credential_resolver import resolve_integration_credentials

    resolved_config = resolve_integration_credentials(service, node_config)
    operation = resolved_config.get('operation') or ''
    config = _render_template(resolved_config, input_data, service._render_template)

    handlers = {
        'slack': _exec_slack,
        'discord': _exec_discord,
        'telegram': _exec_telegram,
        'feishu': _exec_feishu,
        'dingtalk': _exec_dingtalk,
        'wechat_work': _exec_wechat_work,
        'notion': _exec_notion,
        'github': _exec_github,
        'redis': _exec_redis,
        'mysql': _exec_mysql,
        'postgres': _exec_postgres,
        'mongodb': _exec_mongodb,
        'openai_api': _exec_openai_api,
        'huggingface': _exec_huggingface,
        'rss_feed': lambda cfg, inp: run_rss_feed_node(service, cfg, inp),
    }

    handler = handlers.get(node_type)
    if handler:
        try:
            if node_type == 'rss_feed':
                return handler(config, input_data)
            result = handler(config, input_data)
            return {'success': True, 'output': result}
        except Exception as exc:
            logger.exception('Integration node %s failed', node_type)
            return {'success': False, 'error': str(exc)}

    return {
        'success': True,
        'output': {
            'integration': node_type,
            'operation': operation,
            'config': config,
            'input': input_data,
            'message': f'集成节点 {node_type}/{operation} 已排队，请配置凭证后执行',
        },
    }


def _exec_slack(config: Dict, input_data: Dict) -> Dict:
    token = config.get('token') or config.get('credentialToken') or config.get('apiKey')
    channel = config.get('channel')
    text = config.get('text') or ''
    if not token:
        return {'simulated': True, 'channel': channel, 'text': text}
    resp = requests.post(
        'https://slack.com/api/chat.postMessage',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'channel': channel, 'text': text},
        timeout=30,
    )
    return resp.json()


def _exec_discord(config: Dict, input_data: Dict) -> Dict:
    webhook_url = config.get('webhookUrl')
    if not webhook_url:
        return {'simulated': True, 'content': config.get('content')}
    resp = requests.post(
        webhook_url,
        json={'content': config.get('content'), 'username': config.get('username', 'Flowly')},
        timeout=30,
    )
    return {'status_code': resp.status_code, 'body': resp.text}


def _exec_telegram(config: Dict, input_data: Dict) -> Dict:
    token = config.get('botToken') or config.get('credentialToken')
    chat_id = config.get('chatId')
    text = config.get('text') or ''
    if not token:
        return {'simulated': True, 'chatId': chat_id, 'text': text}
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    resp = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=30)
    return resp.json()


def _exec_notion(config: Dict, input_data: Dict) -> Dict:
    token = config.get('credentialToken')
    if not token:
        return {'simulated': True, 'operation': config.get('operation'), 'title': config.get('title')}
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    if config.get('operation') == 'create_page':
        db_id = config.get('databaseId')
        body = {
            'parent': {'database_id': db_id},
            'properties': {
                'Name': {'title': [{'text': {'content': config.get('title') or 'Untitled'}}]},
            },
        }
        resp = requests.post('https://api.notion.com/v1/pages', headers=headers, json=body, timeout=30)
        return resp.json()
    return {'simulated': True}


def _exec_github(config: Dict, input_data: Dict) -> Dict:
    token = config.get('credentialToken')
    owner = config.get('owner')
    repo = config.get('repo')
    title = config.get('title') or 'Issue from Flowly'
    body = config.get('body') or ''
    if not token:
        return {'simulated': True, 'owner': owner, 'repo': repo, 'title': title}
    resp = requests.post(
        f'https://api.github.com/repos/{owner}/{repo}/issues',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'},
        json={'title': title, 'body': body},
        timeout=30,
    )
    return resp.json()


def _exec_redis(config: Dict, input_data: Dict) -> Dict:
    try:
        import redis
    except ImportError:
        return {'simulated': True, 'key': config.get('key'), 'value': config.get('value')}
    host = config.get('host') or 'localhost'
    port = int(config.get('port') or 6379)
    client = redis.Redis(host=host, port=port, decode_responses=True)
    op = config.get('operation') or 'get'
    key = config.get('key') or ''
    if op == 'set':
        client.set(key, config.get('value') or '', ex=int(config.get('ttl') or 0) or None)
        return {'key': key, 'status': 'ok'}
    if op == 'delete':
        return {'deleted': client.delete(key)}
    return {'key': key, 'value': client.get(key)}


def _parse_json_value(raw, fallback):
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _db_connection_fields(config: Dict) -> Dict[str, Any]:
    return {
        'host': config.get('host') or 'localhost',
        'port': int(config.get('port') or 0),
        'user': config.get('user') or config.get('username') or '',
        'password': config.get('password') or config.get('credentialToken') or '',
        'database': config.get('database') or config.get('db') or '',
    }


def _exec_mysql(config: Dict, input_data: Dict) -> Dict:
    fields = _db_connection_fields(config)
    if not fields['user'] or not fields['database']:
        return {
            'simulated': True,
            'query': config.get('query'),
            'message': '请配置 MySQL 凭证（host/user/password/database）后执行',
        }

    try:
        import MySQLdb
    except ImportError as exc:
        return {'success': False, 'error': f'mysqlclient 未安装: {exc}'}

    port = fields['port'] or 3306
    query = (config.get('query') or '').strip()
    operation = config.get('operation') or 'execute_query'
    params = _parse_json_value(config.get('parameters'), [])

    conn = MySQLdb.connect(
        host=fields['host'],
        port=port,
        user=fields['user'],
        passwd=fields['password'],
        db=fields['database'],
        charset='utf8mb4',
    )
    try:
        cursor = conn.cursor()
        if operation in ('execute_query', 'insert', 'update'):
            cursor.execute(query, params if isinstance(params, (list, tuple)) else ())
            if query.lower().strip().startswith('select'):
                columns = [col[0] for col in (cursor.description or [])]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {'operation': operation, 'rows': rows, 'rowcount': len(rows)}
            conn.commit()
            return {'operation': operation, 'rowcount': cursor.rowcount, 'lastrowid': cursor.lastrowid}
        return {'success': False, 'error': f'不支持的 MySQL 操作: {operation}'}
    finally:
        conn.close()


def _exec_postgres(config: Dict, input_data: Dict) -> Dict:
    fields = _db_connection_fields(config)
    if not fields['user'] or not fields['database']:
        return {
            'simulated': True,
            'query': config.get('query'),
            'message': '请配置 PostgreSQL 凭证（host/user/password/database）后执行',
        }

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError as exc:
        return {'success': False, 'error': f'psycopg2 未安装: {exc}'}

    port = fields['port'] or 5432
    query = (config.get('query') or '').strip()
    operation = config.get('operation') or 'execute_query'
    params = _parse_json_value(config.get('parameters'), [])

    conn = psycopg2.connect(
        host=fields['host'],
        port=port,
        user=fields['user'],
        password=fields['password'],
        dbname=fields['database'],
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params if isinstance(params, (list, tuple)) else ())
            if query.lower().strip().startswith('select'):
                rows = [dict(row) for row in cursor.fetchall()]
                return {'operation': operation, 'rows': rows, 'rowcount': len(rows)}
            conn.commit()
            return {'operation': operation, 'rowcount': cursor.rowcount}
    finally:
        conn.close()


def _exec_mongodb(config: Dict, input_data: Dict) -> Dict:
    fields = _db_connection_fields(config)
    database_name = config.get('database') or fields['database']
    collection_name = config.get('collection') or ''
    operation = config.get('operation') or 'find'

    if not database_name or not collection_name:
        return {
            'simulated': True,
            'operation': operation,
            'message': '请配置 MongoDB 凭证及 database/collection 后执行',
        }

    try:
        from pymongo import MongoClient
    except ImportError as exc:
        return {'success': False, 'error': f'pymongo 未安装: {exc}'}

    host = fields['host']
    port = fields['port'] or 27017
    auth_source = config.get('authSource') or 'admin'
    uri = config.get('connectionUri') or config.get('uri')
    if not uri:
        if fields['user'] and fields['password']:
            uri = (
                f"mongodb://{fields['user']}:{fields['password']}@{host}:{port}/"
                f"{database_name}?authSource={auth_source}"
            )
        else:
            uri = f"mongodb://{host}:{port}/{database_name}"

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        collection = client[database_name][collection_name]
        if operation == 'find':
            filter_doc = _parse_json_value(config.get('filter'), {})
            limit = int(config.get('limit') or 20)
            docs = list(collection.find(filter_doc).limit(limit))
            for doc in docs:
                doc['_id'] = str(doc.get('_id'))
            return {'operation': operation, 'documents': docs, 'count': len(docs)}
        if operation == 'insert':
            document = _parse_json_value(config.get('document') or config.get('data'), {})
            result = collection.insert_one(document)
            return {'operation': operation, 'inserted_id': str(result.inserted_id)}
        if operation == 'update':
            filter_doc = _parse_json_value(config.get('filter'), {})
            update_doc = _parse_json_value(config.get('update'), {'$set': {}})
            result = collection.update_many(filter_doc, update_doc)
            return {
                'operation': operation,
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
            }
        if operation == 'aggregate':
            pipeline = _parse_json_value(config.get('pipeline'), [])
            docs = list(collection.aggregate(pipeline))
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            return {'operation': operation, 'documents': docs, 'count': len(docs)}
        return {'success': False, 'error': f'不支持的 MongoDB 操作: {operation}'}
    finally:
        client.close()


def _exec_db_stub(config: Dict, input_data: Dict) -> Dict:
    return {'simulated': True, 'query': config.get('query'), 'message': '请配置数据库凭证后执行'}


def _exec_openai_api(config: Dict, input_data: Dict) -> Dict:
    api_key = config.get('credentialToken') or config.get('apiKey')
    if not api_key:
        return {'simulated': True, 'model': config.get('model')}
    messages_raw = config.get('messages') or '[]'
    try:
        messages = json.loads(messages_raw) if isinstance(messages_raw, str) else messages_raw
    except json.JSONDecodeError:
        messages = [{'role': 'user', 'content': str(messages_raw)}]
    resp = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'model': config.get('model') or 'gpt-4o', 'messages': messages},
        timeout=120,
    )
    return resp.json()


def _exec_huggingface(config: Dict, input_data: Dict) -> Dict:
    token = config.get('credentialToken') or config.get('apiKey')
    model_id = config.get('modelId') or ''
    inputs = config.get('inputs') or ''
    if not token:
        return {'simulated': True, 'modelId': model_id, 'inputs': inputs}
    resp = requests.post(
        f'https://api-inference.huggingface.co/models/{model_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'inputs': inputs},
        timeout=120,
    )
    return resp.json()


def _exec_feishu(config: Dict, input_data: Dict) -> Dict:
    webhook_url = config.get('webhookUrl') or config.get('webhook_url')
    text = config.get('text') or config.get('content') or ''
    if webhook_url:
        resp = requests.post(
            webhook_url,
            json={'msg_type': 'text', 'content': {'text': text}},
            timeout=30,
        )
        return {'status_code': resp.status_code, 'body': resp.json() if resp.content else {}}

    app_id = config.get('appId') or config.get('app_id')
    app_secret = config.get('appSecret') or config.get('app_secret') or config.get('credentialToken')
    if not app_id or not app_secret:
        return {'simulated': True, 'text': text, 'message': '请配置飞书 Webhook 或 App 凭证'}

    token_resp = requests.post(
        'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
        json={'app_id': app_id, 'app_secret': app_secret},
        timeout=30,
    )
    token_data = token_resp.json()
    tenant_token = token_data.get('tenant_access_token')
    if not tenant_token:
        return {'error': token_data}

    receive_id = config.get('receiveId') or config.get('chatId') or config.get('channel')
    msg_resp = requests.post(
        'https://open.feishu.cn/open-apis/im/v1/messages',
        params={'receive_id_type': config.get('receiveIdType', 'chat_id')},
        headers={'Authorization': f'Bearer {tenant_token}', 'Content-Type': 'application/json'},
        json={
            'receive_id': receive_id,
            'msg_type': 'text',
            'content': json.dumps({'text': text}),
        },
        timeout=30,
    )
    return msg_resp.json()


def _exec_dingtalk(config: Dict, input_data: Dict) -> Dict:
    webhook_url = config.get('webhookUrl') or config.get('webhook_url') or config.get('credentialToken')
    text = config.get('text') or config.get('content') or ''
    if not webhook_url:
        return {'simulated': True, 'text': text, 'message': '请配置钉钉机器人 Webhook'}

    payload = {'msgtype': 'text', 'text': {'content': text}}
    secret = config.get('secret')
    url = webhook_url
    if secret:
        import hashlib
        import hmac
        import base64
        import urllib.parse
        import time as time_mod
        timestamp = str(round(time_mod.time() * 1000))
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}timestamp={timestamp}&sign={sign}'

    resp = requests.post(url, json=payload, timeout=30)
    return {'status_code': resp.status_code, 'body': resp.json() if resp.content else {}}


def _exec_wechat_work(config: Dict, input_data: Dict) -> Dict:
    webhook_url = config.get('webhookUrl') or config.get('webhook_url')
    text = config.get('text') or config.get('content') or ''
    if not webhook_url:
        return {'simulated': True, 'text': text, 'message': '请配置企业微信机器人 Webhook'}

    resp = requests.post(
        webhook_url,
        json={'msgtype': 'text', 'text': {'content': text}},
        timeout=30,
    )
    return {'status_code': resp.status_code, 'body': resp.json() if resp.content else {}}
