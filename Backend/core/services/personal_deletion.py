"""Password-confirmed deletion of an exact previewed personal workspace scope."""

import hashlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import Collector
from rest_framework.exceptions import ValidationError

from core.data_constants import (
    DEFAULT_CONFIRMATION_MAX_AGE, DEFAULT_MAX_SNAPSHOT_RECORDS,
    DELETE_CONFIRMATION_TEXT, DELETE_SIGNING_SALT, PERSONAL_DELETE_MODELS,
)
from core.models.audit import AuditAction, AuditLog
from core.services.personal_exports import json_bytes
from core.services.personal_restore import DataConflict


def _deletion_plan(user, *, lock=False):
    from agents.models import Agent, AgentExecution, AgentConversation
    from workflows.models import Workflow, WorkflowExecution, Node, NodeExecution, WorkflowTrigger

    workflows = Workflow.objects.filter(owner=user, tenant__isnull=True).order_by('id')
    agents = Agent.objects.filter(owner=user, tenant__isnull=True).order_by('id')
    if lock:
        workflows = workflows.select_for_update()
        agents = agents.select_for_update()
    workflow_rows, agent_rows = list(workflows), list(agents)
    workflow_ids = [row.pk for row in workflow_rows]
    agent_ids = [row.pk for row in agent_rows]
    if WorkflowExecution.objects.filter(workflow_id__in=workflow_ids, status__in=['queued', 'running']).exists():
        raise DataConflict('个人工作流仍有排队或运行任务，请先停止任务。')
    if AgentExecution.objects.filter(agent_id__in=agent_ids, status__in=['pending', 'running']).exists():
        raise DataConflict('个人 Agent 仍有运行任务，请先停止任务。')
    collector = Collector(using=workflows.db)
    if workflow_rows:
        collector.collect(workflow_rows)
    if agent_rows:
        collector.collect(agent_rows)
    # Legacy cross-workflow parent/FK links must not expand an owner's deletion
    # into another workspace, release snapshot, or another user's private chat.
    scoped_ids = {
        Workflow: set(workflow_ids), Agent: set(agent_ids),
        Node: set(Node.objects.filter(workflow_id__in=workflow_ids).values_list('pk', flat=True)),
        WorkflowExecution: set(WorkflowExecution.objects.filter(workflow_id__in=workflow_ids).values_list('pk', flat=True)),
        NodeExecution: set(NodeExecution.objects.filter(execution__workflow_id__in=workflow_ids).values_list('pk', flat=True)),
        WorkflowTrigger: set(WorkflowTrigger.objects.filter(workflow_id__in=workflow_ids).values_list('pk', flat=True)),
        AgentConversation: set(AgentConversation.objects.filter(agent_id__in=agent_ids, user=user).values_list('pk', flat=True)),
        AgentExecution: set(AgentExecution.objects.filter(agent_id__in=agent_ids).values_list('pk', flat=True)),
    }
    conflict_message = '清理会影响其他用户、团队或已发布资源，请先逐项处理这些关联。'
    for model, objects in collector.data.items():
        if model in scoped_ids and any(obj.pk not in scoped_ids[model] for obj in objects):
            raise DataConflict(conflict_message)
        for field in model._meta.fields:
            related = field.related_model if field.is_relation else None
            if related in scoped_ids and any(
                getattr(obj, field.attname) is not None and getattr(obj, field.attname) not in scoped_ids[related]
                for obj in objects
            ):
                raise DataConflict(conflict_message)
    for queryset in collector.fast_deletes:
        model = queryset.model
        if model in scoped_ids and queryset.exclude(pk__in=scoped_ids[model]).exists():
            raise DataConflict(conflict_message)
        for field in model._meta.fields:
            related = field.related_model if field.is_relation else None
            if related in scoped_ids and queryset.exclude(
                Q(**{f'{field.attname}__isnull': True}) | Q(**{f'{field.attname}__in': scoped_ids[related]})
            ).exists():
                raise DataConflict(conflict_message)
    identities = {model._meta.label_lower: sorted(str(obj.pk) for obj in objects)
                  for model, objects in collector.data.items()}
    for queryset in collector.fast_deletes:
        label = queryset.model._meta.label_lower
        identities.setdefault(label, []).extend(str(value) for value in queryset.values_list('pk', flat=True))
    identities = {label: sorted(set(values)) for label, values in identities.items()}
    if any(label not in PERSONAL_DELETE_MODELS and values for label, values in identities.items()):
        raise DataConflict('个人工作区仍有关联的发布或业务资源，请先解除关联，再进行清理。')
    if sum(map(len, identities.values())) > getattr(settings, 'PERSONAL_DATA_MAX_RECORDS', DEFAULT_MAX_SNAPSHOT_RECORDS):
        raise ValidationError('数据量超过单次清理上限，请先分批删除。')
    summary = {
        'workflows': len(workflow_rows), 'agents': len(agent_rows),
        'workflow_executions': len(identities.get('workflows.workflowexecution', [])),
        'agent_executions': len(identities.get('agents.agentexecution', [])),
        'nodes': len(identities.get('workflows.node', [])),
        'edges': len(identities.get('workflows.edge', [])),
        'conversations': len(identities.get('agents.agentconversation', [])),
        'related_records': sum(len(values) for label, values in identities.items()
                               if label not in {'workflows.workflow', 'agents.agent'}),
    }
    fingerprint = hashlib.sha256(json_bytes(identities)).hexdigest()
    return collector, summary, fingerprint


def preview_deletion(user):
    _, summary, digest = _deletion_plan(user)
    token = signing.dumps({'user': user.pk, 'digest': digest}, salt=DELETE_SIGNING_SALT)
    return {'summary': summary, 'confirmation_token': token, 'confirmation_text': DELETE_CONFIRMATION_TEXT,
            'notice': '仅清理个人工作流、Agent及关联执行记录和对话；团队、已发布应用、账号、凭证、知识库、备份和账单均保留。'}


@transaction.atomic
def delete_personal_data(user, data):
    password = data.get('password')
    if data.get('confirmation') != DELETE_CONFIRMATION_TEXT or not isinstance(password, str):
        raise ValidationError('请输入当前密码和完整确认文字。')
    current_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if not current_user.check_password(password):
        raise ValidationError({'password': '当前密码不正确。'})
    try:
        claims = signing.loads(data.get('confirmation_token', ''), salt=DELETE_SIGNING_SALT,
                              max_age=getattr(settings, 'PERSONAL_DATA_CONFIRMATION_SECONDS', DEFAULT_CONFIRMATION_MAX_AGE))
    except (signing.BadSignature, TypeError) as exc:
        raise ValidationError('清理确认已失效，请重新预览。') from exc
    if claims.get('user') != user.pk:
        raise ValidationError('清理确认不属于当前用户。')
    collector, summary, digest = _deletion_plan(user, lock=True)
    if claims.get('digest') != digest:
        raise DataConflict()
    from workflows.models import Workflow
    from agents.models import Agent
    deleted_ids = {'workflows': [str(item.pk) for item in collector.data.get(Workflow, [])],
                   'agents': [str(item.pk) for item in collector.data.get(Agent, [])]}
    collector.delete()
    AuditLog.objects.create(user=current_user, action=AuditAction.DATA_DELETE, description='用户确认清理个人工作区', metadata={'summary': summary})
    return {'summary': summary, 'deleted': True, 'deleted_ids': deleted_ids}
