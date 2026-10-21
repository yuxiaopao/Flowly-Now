"""实时资源访问权限，与 HTTP 接口共用租户边界。"""
from uuid import UUID

from channels.db import database_sync_to_async
from django.db.models import Q
from tenants.access import can_view_resource, get_accessible_tenant_ids, get_accessible_workflow_queryset

UNAUTHENTICATED_CLOSE_CODE = 4401
FORBIDDEN_CLOSE_CODE = 4403


@database_sync_to_async
def can_subscribe_workflow(user, workflow_id):
    return get_accessible_workflow_queryset(user).filter(pk=workflow_id).exists()


@database_sync_to_async
def can_subscribe_execution(user, execution_id):
    from workflows.models import WorkflowExecution
    queryset = WorkflowExecution.objects.filter(pk=execution_id, workflow__in=get_accessible_workflow_queryset(user))
    if not user.is_superuser:
        queryset = queryset.filter(Q(workflow__owner=user) | Q(triggered_by=user) | Q(workflow__tenant_id__in=get_accessible_tenant_ids(user)))
    return queryset.exists()


@database_sync_to_async
def can_subscribe_training(user, job_id):
    from training.models import TrainingJob
    lookup = Q(job_id=job_id)
    try:
        lookup |= Q(pk=UUID(str(job_id)))
    except ValueError:
        pass
    job = TrainingJob.objects.filter(lookup).first()
    return job is not None and can_view_resource(user, job)
