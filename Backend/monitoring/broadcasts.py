"""根据资源所有者与租户投递监控事件，避免全局频道泄露私有信息。"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.apps import apps
from workflows.execution_control import make_json_safe

logger = logging.getLogger(__name__)
PUBLIC_EVENTS = frozenset({'model_status_changed', 'branding_cache_invalidated'})
TENANT_SCOPED_EVENTS = frozenset({
    'branding_cache_invalidated', 'webhook_created', 'webhook_delivery',
    'execution_started', 'execution_completed', 'execution_failed',
})
RESOURCE_REFERENCES = (
    ('execution_id', 'workflows', 'WorkflowExecution'),
    ('workflow_id', 'workflows', 'Workflow'),
    ('session_id', 'nl_to_workflow', 'NLSession'),
    ('rule_id', 'monitoring', 'AlertRule'),
    ('payment_id', 'billing', 'Payment'),
    ('invoice_id', 'billing', 'Invoice'),
    ('webhook_id', 'integrations', 'Webhook'),
    ('template_id', 'prompts', 'PromptTemplate'),
)
OWNER_KEYS = ('user_id', 'owner_id', 'creator_id', 'created_by', 'installed_by')


def monitoring_groups(data):
    groups = set()
    for key in OWNER_KEYS:
        if data.get(key):
            groups.add(f'monitoring_{data[key]}')
    tenant_id = data.get('tenant_id')
    if tenant_id and data.get('event') in TENANT_SCOPED_EVENTS:
        groups.add(f'monitoring_tenant_{tenant_id}')
    if any(data.get(key) for key in OWNER_KEYS):
        return groups
    for key, app, model in RESOURCE_REFERENCES:
        if not data.get(key):
            continue
        resource = apps.get_model(app, model).objects.filter(pk=data[key]).first()
        if not resource:
            continue
        if key == 'execution_id':
            if resource.triggered_by_id:
                groups.add(f'monitoring_{resource.triggered_by_id}')
            resource = resource.workflow
        owner_id = getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None) or getattr(resource, 'user_id', None)
        tenant_id = getattr(resource, 'tenant_id', None)
        if owner_id:
            groups.add(f'monitoring_{owner_id}')
        if tenant_id and data.get('event') in TENANT_SCOPED_EVENTS:
            groups.add(f'monitoring_tenant_{tenant_id}')
        if groups:
            return groups
        if getattr(resource, 'is_public', False):
            return {'monitoring_public'}
    if data.get('event') in PUBLIC_EVENTS:
        return groups or {'monitoring_public'}
    return groups


def broadcast_to_monitoring(data):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        for group in monitoring_groups(data):
            async_to_sync(channel_layer.group_send)(group, {'type': 'metric_update', 'data': make_json_safe(data)})
    except Exception:
        logger.exception('监控事件投递失败：%s', data.get('event'))
