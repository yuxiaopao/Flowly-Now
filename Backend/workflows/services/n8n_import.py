"""
Convert n8n workflow JSON exports into Flowly workflow payloads.

n8n format reference: https://github.com/Zie619/n8n-workflows
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# n8n type suffix -> Flowly node_type (explicit mappings)
# ---------------------------------------------------------------------------
N8N_NODE_MAP: Dict[str, str] = {
    # Triggers (core)
    'manualTrigger': 'manual',
    'executeWorkflowTrigger': 'start',
    'workflowTrigger': 'start',
    'start': 'start',
    'webhook': 'webhook',
    'scheduleTrigger': 'schedule',
    'cron': 'schedule',
    'iCal': 'schedule',
    'formTrigger': 'form',
    'typeformTrigger': 'form',
    'jotFormTrigger': 'form',
    'wufooTrigger': 'form',
    'surveyMonkeyTrigger': 'form',
    'emailReadImap': 'email',
    'gmailTrigger': 'email',
    'postmarkTrigger': 'email',
    'errorTrigger': 'manual',
    'localFileTrigger': 'manual',
    'rssFeedReadTrigger': 'schedule',
    'togglTrigger': 'schedule',
    'n8nTrigger': 'webhook',
    'sseTrigger': 'webhook',
    'mqttTrigger': 'webhook',
    'amqpTrigger': 'webhook',
    'kafkaTrigger': 'webhook',
    'rabbitmqTrigger': 'webhook',
    # SaaS / event triggers -> webhook
    'activeCampaignTrigger': 'webhook',
    'acuitySchedulingTrigger': 'webhook',
    'affinityTrigger': 'webhook',
    'airtableTrigger': 'webhook',
    'asanaTrigger': 'webhook',
    'autopilotTrigger': 'webhook',
    'awsSnsTrigger': 'webhook',
    'bitbucketTrigger': 'webhook',
    'boxTrigger': 'webhook',
    'calTrigger': 'webhook',
    'calendlyTrigger': 'webhook',
    'chargebeeTrigger': 'webhook',
    'clickUpTrigger': 'webhook',
    'clockifyTrigger': 'webhook',
    'convertKitTrigger': 'webhook',
    'copperTrigger': 'webhook',
    'customerIoTrigger': 'webhook',
    'emeliaTrigger': 'webhook',
    'eventbriteTrigger': 'webhook',
    'facebookLeadAdsTrigger': 'webhook',
    'facebookTrigger': 'webhook',
    'figmaTrigger': 'webhook',
    'flowTrigger': 'webhook',
    'getResponseTrigger': 'webhook',
    'githubTrigger': 'webhook',
    'gitlabTrigger': 'webhook',
    'googleCalendarTrigger': 'webhook',
    'googleDriveTrigger': 'webhook',
    'googleSheetsTrigger': 'webhook',
    'gumroadTrigger': 'webhook',
    'helpScoutTrigger': 'webhook',
    'hubspotTrigger': 'webhook',
    'invoiceNinjaTrigger': 'webhook',
    'jiraTrigger': 'webhook',
    'keapTrigger': 'webhook',
    'lemlistTrigger': 'webhook',
    'linearTrigger': 'webhook',
    'mailchimpTrigger': 'webhook',
    'mailerLiteTrigger': 'webhook',
    'mailjetTrigger': 'webhook',
    'mauticTrigger': 'webhook',
    'microsoftOutlookTrigger': 'webhook',
    'netlifyTrigger': 'webhook',
    'notionTrigger': 'webhook',
    'onfleetTrigger': 'webhook',
    'payPalTrigger': 'webhook',
    'pipedriveTrigger': 'webhook',
    'postgresTrigger': 'webhook',
    'pushcutTrigger': 'webhook',
    'shopifyTrigger': 'webhook',
    'slackTrigger': 'webhook',
    'stravaTrigger': 'webhook',
    'stripeTrigger': 'webhook',
    'taigaTrigger': 'webhook',
    'telegramTrigger': 'webhook',
    'theHiveProjectTrigger': 'webhook',
    'theHiveTrigger': 'webhook',
    'trelloTrigger': 'webhook',
    'twilioTrigger': 'webhook',
    'webflowTrigger': 'webhook',
    'whatsAppTrigger': 'webhook',
    'wiseTrigger': 'webhook',
    'wooCommerceTrigger': 'webhook',
    'zendeskTrigger': 'webhook',
    # Core logic
    'set': 'set',
    'code': 'code',
    'function': 'code',
    'functionItem': 'code',
    'executeCommand': 'code',
    'ssh': 'code',
    'awsLambda': 'code',
    'debugHelper': 'variable',
    'httpRequest': 'http_request',
    'graphql': 'http_request',
    'if': 'condition',
    'switch': 'switch',
    'merge': 'merge',
    'splitInBatches': 'split',
    'splitOut': 'split',
    'filter': 'filter',
    'limit': 'filter',
    'aggregate': 'merge',
    'itemLists': 'data_transform',
    'sort': 'data_transform',
    'removeDuplicates': 'data_transform',
    'renameKeys': 'data_transform',
    'moveBinaryData': 'data_transform',
    'compareDatasets': 'data_transform',
    'crypto': 'data_transform',
    'exifData': 'data_transform',
    'totp': 'data_transform',
    'executionData': 'variable',
    'dateTime': 'datetime',
    'wait': 'delay',
    'delay': 'delay',
    'interval': 'delay',
    'stopAndError': 'end',
    'respondToWebhook': 'output',
    'noOp': 'variable',
    'html': 'text_template',
    'markdown': 'text_template',
    'documentGenerator': 'text_template',
    'DocumentGenerator': 'text_template',
    'xml': 'data_transform',
    'json': 'json_transform',
    'convertToFile': 'file_writer',
    'readBinaryFile': 'file_reader',
    'readBinaryFiles': 'file_reader',
    'readPDF': 'document_loader',
    'readWriteFile': 'file_reader',
    'writeBinaryFile': 'file_writer',
    'extractFromFile': 'file_reader',
    'spreadsheetFile': 'csv_transform',
    'compression': 'file_writer',
    'executeWorkflow': 'subworkflow',
    'flow': 'subworkflow',
    'form': 'form',
    # AI / ML
    'openAi': 'openai_api',
    'huggingFace': 'huggingface',
    'summarize': 'llm',
    'aiTransform': 'llm',
    'googleCloudNaturalLanguage': 'llm',
    'googlePerspective': 'llm',
    'googleTranslate': 'llm',
    'deepL': 'llm',
    'lingvaNex': 'llm',
    'awsComprehend': 'llm',
    'elevenLabs': 'audio_generation',
    'awsTranscribe': 'subtitle_generation',
    'youtubeTranscripter': 'subtitle_generation',
    'editImage': 'image_editing',
    'bannerbear': 'image_generation',
    'quickChart': 'http_request',
    'vectorStoreCouchbaseSearch': 'vector_store',
    'mcpClient': 'tool',
    'mcpClientTool': 'tool',
    # Email / messaging
    'emailSend': 'email',
    'gmail': 'email',
    'gmailTool': 'email',
    'emailSendTool': 'email',
    'microsoftOutlook': 'email',
    'microsoftOutlookTool': 'email',
    'lemlist': 'email',
    'mailchimp': 'email',
    'awsSes': 'email',
    'sendInBlue': 'email',
    'sendy': 'email',
    'mandrill': 'email',
    'mailgun': 'email',
    'mailjet': 'email',
    'convertKit': 'email',
    'customerIo': 'email',
    'emelia': 'email',
    'egoi': 'email',
    'getResponse': 'email',
    'iterable': 'email',
    'vero': 'email',
  # Integrations with Flowly node types
    'slack': 'slack',
    'slackTrigger': 'webhook',
    'mattermost': 'slack',
    'rocketchat': 'slack',
    'twake': 'slack',
    'zulip': 'slack',
    'line': 'slack',
    'discord': 'discord',
    'discordTool': 'discord',
    'telegram': 'telegram',
    'telegramTool': 'telegram',
    'microsoftTeams': 'microsoft_teams',
    'notion': 'notion',
    'notionTool': 'notion',
    'googleSheets': 'google_sheets',
    'googleSheetsTool': 'google_sheets',
    'googleDrive': 'google_drive',
    'googleDriveTool': 'google_drive',
    'dropbox': 'google_drive',
    'box': 'google_drive',
    'microsoftOneDrive': 'google_drive',
    'nextCloud': 'ftp',
    'github': 'github',
    'githubTool': 'github',
    'git': 'github',
    'gitlab': 'gitlab',
    'gitlabTool': 'gitlab',
    'jira': 'jira',
    'jiraTool': 'jira',
    'airtable': 'airtable',
    'airtableTool': 'airtable',
    'baserow': 'airtable',
    'baserowTool': 'airtable',
    'stackby': 'airtable',
    'trello': 'trello',
    'mySql': 'mysql',
    'mySqlTool': 'mysql',
    'postgres': 'postgres',
    'postgresTool': 'postgres',
    'supabase': 'postgres',
    'supabaseTool': 'postgres',
    'nocoDb': 'postgres',
    'crateDb': 'postgres',
    'questDb': 'postgres',
    'timescaleDb': 'postgres',
    'microsoftSql': 'postgres',
    'googleBigQuery': 'postgres',
    'snowflake': 'postgres',
    'mongoDb': 'mongodb',
    'mongoDbTool': 'mongodb',
    'googleFirebaseCloudFirestore': 'mongodb',
    'googleFirebaseRealtimeDatabase': 'mongodb',
    'redis': 'redis',
    'redisTool': 'redis',
    'elasticsearch': 'elasticsearch',
    'awsS3': 'aws_s3',
    's3': 'aws_s3',
    'googleCloudStorage': 'aws_s3',
    'ftp': 'ftp',
    'stripe': 'stripe',
    'chargebee': 'stripe',
    'paddle': 'stripe',
    'payPal': 'stripe',
    'twilio': 'twilio',
    'twilioTool': 'twilio',
    'vonage': 'twilio',
    'messageBird': 'twilio',
    'mocean': 'twilio',
    'msg91': 'twilio',
    'sms77': 'twilio',
    'plivo': 'twilio',
    'sendGrid': 'sendgrid',
    'openWeatherMap': 'http_request',
    'openWeatherMapTool': 'http_request',
    'rssFeedRead': 'rss_feed',
    'hackerNews': 'http_request',
    # Web scraping
    'htmlExtract': 'web_scraper',
    'airtop': 'web_scraper',
    'airtopTool': 'web_scraper',
    'brightData': 'web_scraper',
    'hdwWebParserTool': 'web_scraper',
    'nostrobotsread': 'web_scraper',
    'urlScanIo': 'web_scraper',
    'phantombuster': 'web_scraper',
    'hdwLinkedin': 'http_request',
    'hdwLinkedinManagement': 'http_request',
    # Push / alerts
    'signl4': 'push_notification',
    'pagerDuty': 'push_notification',
    'pushbullet': 'push_notification',
    'pushcut': 'push_notification',
    'pushover': 'push_notification',
    'gotify': 'push_notification',
    'Ntfy': 'push_notification',
    'awsSns': 'push_notification',
    'spontit': 'push_notification',
    # HTTP / SaaS (no dedicated Flowly integration)
    'hubspot': 'http_request',
    'pipedrive': 'http_request',
    'salesforce': 'http_request',
    'spotify': 'http_request',
    'googleCalendar': 'http_request',
    'googleCalendarTool': 'http_request',
    'googleDocs': 'http_request',
    'googleDocsTool': 'http_request',
    'googleSlides': 'http_request',
    'googleTasks': 'http_request',
    'googleTasksTool': 'http_request',
    'googleAnalytics': 'http_request',
    'googleAnalyticsTool': 'http_request',
    'googleBooks': 'http_request',
    'googleChat': 'http_request',
    'googleContacts': 'http_request',
    'gSuiteAdmin': 'http_request',
    'youTube': 'http_request',
    'wordpress': 'http_request',
    'wordpressTool': 'http_request',
    'whatsApp': 'http_request',
    'zendesk': 'http_request',
    'todoist': 'http_request',
    'twitter': 'http_request',
    'twitterTool': 'http_request',
    'klicktipp': 'http_request',
    'mautic': 'http_request',
    'facebookGraphApi': 'http_request',
    'clockify': 'http_request',
    'clearbit': 'http_request',
    'theHive': 'http_request',
    'theHiveProject': 'http_request',
    'bambooHr': 'http_request',
    'asana': 'http_request',
    'reddit': 'http_request',
    'linear': 'http_request',
    'uproc': 'http_request',
    'odoo': 'http_request',
    'strapi': 'http_request',
    'webflow': 'http_request',
    'humanticAi': 'http_request',
    'matrix': 'http_request',
    'orbit': 'http_request',
    'mailcheck': 'http_request',
    'wooCommerce': 'http_request',
    'wooCommerceTool': 'http_request',
    'clickUp': 'http_request',
    'zoom': 'http_request',
    'copper': 'http_request',
    'filemaker': 'http_request',
    'erpNext': 'http_request',
    'mindee': 'data_transform',
    'dropcontact': 'http_request',
    'ghost': 'http_request',
    'shopify': 'http_request',
    'raindrop': 'http_request',
    'quickbooks': 'http_request',
    'strava': 'http_request',
    'microsoftToDo': 'http_request',
    'wekan': 'http_request',
    'postBin': 'http_request',
    'wise': 'http_request',
    'autopilot': 'http_request',
    'bitwarden': 'http_request',
    'activeCampaign': 'http_request',
    'affinity': 'http_request',
    'agileCrm': 'http_request',
    'amqp': 'http_request',
    'apiTemplateIo': 'http_request',
    'automizy': 'http_request',
    'beeminder': 'http_request',
    'bitly': 'http_request',
    'Brandfetch': 'http_request',
    'circleCi': 'http_request',
    'cockpit': 'http_request',
    'coda': 'http_request',
    'coinGecko': 'http_request',
    'contentful': 'http_request',
    'cortex': 'http_request',
    'dataForSeo': 'http_request',
    'demio': 'http_request',
    'dhl': 'http_request',
    'discourse': 'http_request',
    'disqus': 'http_request',
    'drift': 'http_request',
    'evolutionApi': 'http_request',
    'freshdesk': 'http_request',
    'goToWebinar': 'http_request',
    'gong': 'http_request',
    'grist': 'http_request',
    'harvest': 'http_request',
    'helpScout': 'http_request',
    'highLevel': 'http_request',
    'homeAssistant': 'http_request',
    'intercom': 'http_request',
    'invoiceNinja': 'http_request',
    'kafka': 'http_request',
    'keap': 'http_request',
    'medium': 'http_request',
    'microsoftExcel': 'http_request',
    'mqtt': 'http_request',
    'nasa': 'http_request',
    'netlify': 'http_request',
    'netsuite': 'http_request',
    'oneSimpleApi': 'http_request',
    'onfleet': 'http_request',
    'openThesaurus': 'http_request',
    'peekalink': 'http_request',
    'philipsHue': 'http_request',
    'postHog': 'http_request',
    'profitWell': 'http_request',
    'quickbase': 'http_request',
    'rabbitmq': 'http_request',
    'rundeck': 'http_request',
    'salesmate': 'http_request',
    'securityScorecard': 'http_request',
    'segment': 'http_request',
    'sentryIo': 'http_request',
    'serviceNow': 'http_request',
    'storyblok': 'http_request',
    'taiga': 'http_request',
    'tapfiliate': 'http_request',
    'travisCi': 'http_request',
    'uplead': 'http_request',
    'uptimeRobot': 'http_request',
    'venafiTlsProtectCloud': 'http_request',
    'xero': 'http_request',
    'zammad': 'http_request',
    'zohoCrm': 'http_request',
    'mondayCom': 'http_request',
    'linkedIn': 'http_request',
    'openWeatherMap': 'http_request',
    'awsSqs': 'http_request',
    'awsTextract': 'document_loader',
    'awsRekognition': 'data_transform',
    'executeCommandTool': 'code',
    'httpRequestTool': 'http_request',
    'n8nTrainingCustomerMessenger': 'http_request',
    'yourls': 'http_request',
}

# Parent type when n8n suffix ends with Tool but has no explicit map entry.
N8N_TOOL_PARENT_FALLBACK: Dict[str, str] = {
    'httpRequest': 'http_request',
    'executeCommand': 'code',
    'openAi': 'openai_api',
}

SKIP_N8N_TYPES = frozenset({
    'stickyNote',
    'n8n',
    'n8nTrainingCustomerDatastore',
})

TRIGGER_SUFFIXES = frozenset(
    k for k, v in N8N_NODE_MAP.items() if v in (
        'manual', 'webhook', 'schedule', 'form', 'start', 'email',
    )
)

# Flowly-valid node types (subset used for fallback validation)
_VALID_FLOWLY_TYPES = frozenset({
    'start', 'end', 'llm', 'prompt', 'condition', 'tool', 'input', 'output',
    'code', 'loop', 'switch', 'delay', 'subworkflow', 'http_request',
    'data_transform', 'email', 'webhook', 'template', 'variable', 'rag',
    'image_generation', 'video_generation', 'audio_generation',
    'subtitle_generation', 'image_editing', 'file_reader', 'file_writer',
    'web_scraper', 'csv_transform', 'json_transform', 'merge', 'split',
    'filter', 'set', 'datetime', 'manual', 'schedule', 'form',
    'document_loader', 'vector_store', 'agent', 'openai_api', 'huggingface',
    'push_notification', 'rss_feed', 'slack', 'discord', 'telegram',
    'microsoft_teams', 'notion', 'google_sheets', 'google_drive', 'github',
    'gitlab', 'jira', 'airtable', 'trello', 'mysql', 'postgres', 'mongodb',
    'redis', 'elasticsearch', 'aws_s3', 'ftp', 'stripe', 'twilio', 'sendgrid',
})


def is_n8n_workflow(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if data.get('type') == 'flowly_workflow':
        return False
    nodes = data.get('nodes')
    if not isinstance(nodes, list) or not nodes:
        return False
    for node in nodes[:12]:
        if not isinstance(node, dict):
            continue
        t = str(node.get('type') or '')
        if t.startswith('n8n-nodes-base.') or t.startswith('@n8n/'):
            return True
    return 'connections' in data and bool(nodes)


def _n8n_suffix(node_type: str) -> str:
    t = (node_type or '').strip()
    if '.' in t:
        t = t.split('.')[-1]
    return t


def _resolve_tool_parent(suffix: str) -> Optional[str]:
    if not suffix.endswith('Tool'):
        return None
    parent = suffix[:-4]
    if parent in N8N_NODE_MAP:
        return N8N_NODE_MAP[parent]
    if parent in N8N_TOOL_PARENT_FALLBACK:
        return N8N_TOOL_PARENT_FALLBACK[parent]
    return 'tool'


def _map_node_type(n8n_type: str) -> Tuple[str, bool]:
    """Return (flowly_type, is_exact_map)."""
    suffix = _n8n_suffix(n8n_type)
    if suffix in SKIP_N8N_TYPES:
        return '', False
    from .workflow_validation import N8N_PAYLOAD_TRIGGERS
    compatible = suffix in N8N_PAYLOAD_TRIGGERS or n8n_type in ('n8n-nodes-base.httpRequest', 'n8n-nodes-base.noOp')
    if suffix in N8N_NODE_MAP:
        return N8N_NODE_MAP[suffix], compatible
    tool_parent = _resolve_tool_parent(suffix)
    if tool_parent:
        return tool_parent, False
    if suffix.endswith('Trigger'):
        return 'webhook', False
    # Langchain / AI community nodes
    raw = (n8n_type or '').lower()
    if 'langchain' in raw or 'lmchat' in raw or 'chain' in suffix.lower():
        if 'agent' in raw or 'agent' in suffix.lower():
            return 'agent', False
        if 'tool' in suffix.lower():
            return 'tool', False
        return 'llm', False
    return 'http_request', False


def _new_id() -> str:
    return str(uuid.uuid4())


def _safe_http_method(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else 'GET'
    return str(value or 'GET').upper()


def _node_position(node: dict, index: int) -> Dict[str, float]:
    pos = node.get('position') or [80 + (index % 6) * 220, 80 + (index // 6) * 140]
    if isinstance(pos, dict):
        return {'x': float(pos.get('x', 0)), 'y': float(pos.get('y', 0))}
    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
        return {'x': float(pos[0]), 'y': float(pos[1])}
    return {'x': 80.0, 'y': 80.0}


def _extract_code_body(params: dict) -> str:
    for key in ('pythonCode', 'jsCode', 'code', 'functionCode'):
        val = params.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ''


def _build_config(n8n_node: dict, flowly_type: str, exact: bool) -> dict:
    params = n8n_node.get('parameters') or {}
    cfg: Dict[str, Any] = {
        'n8n_type': n8n_node.get('type'),
        'n8n_parameters': params,
    }
    if n8n_node.get('credentials'):
        cfg['n8n_credentials'] = n8n_node.get('credentials')

    if flowly_type == 'code':
        body = _extract_code_body(params)
        if body:
            cfg['code'] = body
            cfg['language'] = 'python' if 'pythonCode' in params else 'javascript'

    if flowly_type == 'http_request':
        if params.get('url'):
            cfg['url'] = params.get('url')
        cfg['method'] = _safe_http_method(params.get('method') or params.get('requestMethod'))

    if flowly_type == 'webhook':
        if params.get('path'):
            cfg['path'] = params.get('path')
        cfg['method'] = _safe_http_method(params.get('httpMethod'))

    if flowly_type == 'schedule' and params.get('rule'):
        cfg['cron'] = params.get('rule')

    if flowly_type == 'set' and params.get('assignments'):
        cfg['assignments'] = params.get('assignments')

    if flowly_type == 'text_template':
        for key in ('html', 'markdown', 'text', 'content'):
            if params.get(key):
                cfg['template'] = params.get(key)
                break

    if flowly_type == 'llm' and params.get('text'):
        cfg['prompt'] = params.get('text')

    if flowly_type == 'subworkflow':
        if params.get('workflowId'):
            cfg['workflow_id'] = params.get('workflowId')
        if params.get('source'):
            cfg['source'] = params.get('source')

    if flowly_type == 'email':
        for key in ('subject', 'text', 'html', 'message', 'toEmail', 'sendTo'):
            if params.get(key):
                cfg[key] = params.get(key)

    if flowly_type == 'file_reader' and params.get('filePath'):
        cfg['file_path'] = params.get('filePath')

    if flowly_type == 'file_writer' and params.get('fileName'):
        cfg['file_name'] = params.get('fileName')

    if not exact:
        cfg['n8n_unmapped'] = True

    return cfg


def convert_n8n_workflow(
    data: dict,
    *,
    name_prefix: str = '[n8n] ',
    source_path: str = '',
) -> Dict[str, Any]:
    """
    Convert one n8n workflow dict to Flowly WorkflowCreateSerializer payload.
    """
    if not is_n8n_workflow(data):
        raise ValueError('Not a recognized n8n workflow export')

    raw_name = (data.get('name') or Path(source_path).stem or 'Imported n8n Workflow').strip()
    stem = Path(source_path).stem if source_path else ''
    if stem and stem not in raw_name:
        raw_name = f'{raw_name} ({stem})'
    if not raw_name.startswith('[n8n]'):
        wf_name = f'{name_prefix}{raw_name}'[:200]
    else:
        wf_name = raw_name[:200]

    n8n_nodes = data.get('nodes') or []
    flowly_nodes: List[dict] = []
    id_by_n8n_key: Dict[str, str] = {}
    name_to_id: Dict[str, str] = {}
    skipped = 0
    unmapped = 0
    has_start = False

    sort_order = 0
    for idx, n8n_node in enumerate(n8n_nodes):
        if not isinstance(n8n_node, dict):
            continue
        suffix = _n8n_suffix(n8n_node.get('type', ''))
        if suffix in SKIP_N8N_TYPES:
            skipped += 1
            continue

        flowly_type, exact = _map_node_type(n8n_node.get('type', ''))
        if not flowly_type:
            skipped += 1
            continue
        if not exact:
            unmapped += 1

        if suffix in TRIGGER_SUFFIXES and flowly_type in ('manual', 'webhook', 'schedule', 'form', 'start', 'email'):
            if not has_start and flowly_type != 'start':
                flowly_type = 'start'
            has_start = True

        node_id = _new_id()

        label = (n8n_node.get('name') or suffix or flowly_type)[:120]
        pos = _node_position(n8n_node, idx)
        node_config = _build_config(n8n_node, flowly_type, exact)
        flowly_nodes.append({
            'id': node_id,
            'type': flowly_type,
            'name': label,
            'position': pos,
            'sort_order': sort_order,
            'data': {
                'label': label,
                'config': node_config,
            },
            'config': node_config,
        })
        sort_order += 1

        keys = {str(n8n_node.get('id') or ''), str(n8n_node.get('name') or '')}
        for k in keys:
            if k:
                id_by_n8n_key[k] = node_id
        name_to_id[label] = node_id

    if not flowly_nodes:
        raise ValueError('No convertible nodes')

    if not has_start:
        start_id = _new_id()
        flowly_nodes.insert(0, {
            'id': start_id,
            'type': 'start',
            'name': '开始',
            'position': {'x': 40, 'y': 40},
            'sort_order': 0,
            'data': {'label': '开始', 'config': {'auto_inserted': True}},
            'config': {'auto_inserted': True},
        })
        has_start = True

    if not any(n['type'] == 'end' for n in flowly_nodes):
        end_id = _new_id()
        flowly_nodes.append({
            'id': end_id,
            'type': 'end',
            'name': '结束',
            'position': {'x': 40, 'y': 40 + len(flowly_nodes) * 40},
            'sort_order': len(flowly_nodes),
            'data': {'label': '结束', 'config': {'auto_inserted': True}},
            'config': {'auto_inserted': True},
        })

    edges: List[dict] = []
    seen_edges: Set[Tuple[str, str]] = set()
    connections = data.get('connections') or {}

    def resolve_id(key: str) -> Optional[str]:
        if not key:
            return None
        if key in id_by_n8n_key:
            return id_by_n8n_key[key]
        if key in name_to_id:
            return name_to_id[key]
        return None

    for src_key, outputs in connections.items():
        src_id = resolve_id(str(src_key))
        if not src_id:
            continue
        for branch in (outputs or {}).get('main') or []:
            if not isinstance(branch, list):
                continue
            for link in branch:
                if not isinstance(link, dict):
                    continue
                tgt_key = str(link.get('node') or '')
                tgt_id = resolve_id(tgt_key)
                if not tgt_id or tgt_id == src_id:
                    continue
                pair = (src_id, tgt_id)
                if pair in seen_edges:
                    continue
                seen_edges.add(pair)
                edges.append({
                    'id': _new_id(),
                    'source': src_id,
                    'target': tgt_id,
                    'source_handle': 'default',
                    'target_handle': 'default',
                    'label': link.get('type') or '',
                })

    if not edges and len(flowly_nodes) > 1:
        for i in range(len(flowly_nodes) - 1):
            edges.append({
                'id': _new_id(),
                'source': flowly_nodes[i]['id'],
                'target': flowly_nodes[i + 1]['id'],
                'source_handle': 'default',
                'target_handle': 'default',
            })

    description = (data.get('description') or '').strip()
    meta_note = f'从 n8n 导入（{source_path or "JSON 文件"}）。尚未兼容的节点：{unmapped}；跳过的说明节点：{skipped}。导入成功不代表所有业务节点可执行。'
    if description:
        description = f'{description}\n\n{meta_note}'
    else:
        description = meta_note

    return {
        'name': wf_name,
        'description': description[:4000],
        'tags': ['n8n-import', 'n8n-batch'],
        'config': {
            'import_source': 'n8n',
            'n8n_source_path': source_path,
            'n8n_node_count': len(n8n_nodes),
            'n8n_converted_nodes': len(flowly_nodes),
            'n8n_unmapped_nodes': unmapped,
            'n8n_skipped_nodes': skipped,
        },
        'nodes': flowly_nodes,
        'edges': edges,
        'meta': {
            'convertible': True,
            'unmapped_nodes': unmapped,
            'skipped_nodes': skipped,
            'edge_count': len(edges),
        },
    }


def convert_n8n_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding='utf-8'))
    return convert_n8n_workflow(data, source_path=str(p).replace('\\', '/'))
