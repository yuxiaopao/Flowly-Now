"""Fresh actor and team checks shared by HTTP and workflow evaluations."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from tenants.models import TenantMembership
from .constants import ACTIVE_TEAM_STATUSES, EvaluationFailure


def fresh_actor(user):
    actor = get_user_model().objects.filter(pk=getattr(user, 'pk', user), is_active=True).first()
    if not actor:
        raise EvaluationFailure('评测身份已失效，请重新登录。', 'permission_revoked', 403)
    return actor


def role(user, tenant):
    from tenants.models import Tenant
    tenant = Tenant.objects.filter(pk=tenant.pk, status__in=ACTIVE_TEAM_STATUSES).only('id', 'owner_id').first() if tenant else None
    if not tenant:
        return None
    if user.is_superuser or tenant.owner_id == user.pk:
        return 'owner'
    return TenantMembership.objects.filter(tenant=tenant, user=user, is_active=True).values_list('role', flat=True).first()


def visible_jobs(user):
    user = fresh_actor(user)
    from .models import EvaluationJob
    qs = EvaluationJob.objects.select_related('created_by', 'tenant', 'training_job', 'dataset', 'training_dataset')
    if user.is_superuser:
        return qs
    teams = TenantMembership.objects.filter(user=user, is_active=True, tenant__status__in=ACTIVE_TEAM_STATUSES).values('tenant_id')
    return qs.filter(Q(created_by=user, tenant__isnull=True) | Q(tenant_id__in=teams) |
                     Q(tenant__owner=user, tenant__status__in=ACTIVE_TEAM_STATUSES)).distinct()


def require_resource(user, resource):
    user = fresh_actor(user)
    tenant = getattr(resource, 'tenant', None)
    owner_id = resource.created_by_id
    if tenant:
        current_role = role(user, tenant)
        allowed = current_role in ('owner', 'admin') or current_role == 'member' and owner_id == user.pk
    else:
        allowed = user.is_superuser or owner_id == user.pk
    if not allowed:
        raise EvaluationFailure('模型或数据集不属于当前可管理空间。', 'resource_forbidden', 403)
    return resource


def require_manage(user, job):
    user = fresh_actor(user)
    if job.tenant_id:
        current_role = role(user, job.tenant)
        allowed = current_role in ('owner', 'admin') or current_role == 'member' and job.created_by_id == user.pk
    else:
        allowed = user.is_superuser or job.created_by_id == user.pk
    if not allowed:
        raise EvaluationFailure('仅评测所有者或团队管理员可执行此操作。', 'permission_denied', 403)
    return user


def workflow_source(user_id, context):
    from uuid import UUID
    from workflows.models import WorkflowExecution, NodeExecution
    internal = context.get('_execution')
    metadata = internal.get('metadata') if isinstance(internal, dict) else None
    if not isinstance(metadata, dict):
        metadata = context.get('metadata') or {}
    try:
        ids = {key: UUID(str(metadata[key])) for key in ('execution_id', 'workflow_id', 'node_id')}
    except (KeyError, ValueError, TypeError):
        raise EvaluationFailure('评测必须来自真实运行中的工作流节点。', 'untrusted_execution', 403) from None
    execution = WorkflowExecution.objects.select_related('workflow__owner', 'workflow__tenant', 'triggered_by').filter(
        pk=ids['execution_id'], workflow_id=ids['workflow_id'], status='running').first()
    actor = execution.triggered_by if execution else None
    if execution and not actor and execution.trigger_type == 'scheduled' and user_id is None:
        actor = execution.workflow.owner
    if not actor or user_id is not None and actor.pk != user_id:
        raise EvaluationFailure('评测执行身份不匹配。', 'untrusted_execution', 403)
    actor = fresh_actor(actor)
    workflow = execution.workflow
    if workflow.is_deleted or execution.tenant_id not in (None, workflow.tenant_id):
        raise EvaluationFailure('工作流来源空间已失效。', 'untrusted_execution', 403)
    if workflow.tenant_id:
        if role(actor, workflow.tenant) not in ('owner', 'admin', 'member'):
            raise EvaluationFailure('团队执行权限已失效。', 'permission_revoked', 403)
    elif actor.pk != workflow.owner_id and not actor.is_superuser:
        raise EvaluationFailure('无法使用其他用户的个人工作流。', 'permission_denied', 403)
    node_execution = NodeExecution.objects.select_related('node').filter(execution=execution,
        node_id=ids['node_id'], node__workflow=workflow, node__node_type='model_evaluation', status='running').first()
    if not node_execution:
        raise EvaluationFailure('评测必须来自真实运行中的评测节点。', 'untrusted_execution', 403)
    return actor, workflow, node_execution.node, execution
