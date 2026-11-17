"""Prepare card data without loading execution histories."""

from django.db.models import BooleanField, Case, Count, Exists, IntegerField, OuterRef, Prefetch, Subquery, Value, When
from django.db.models.functions import Coalesce

from config.constants import WORKFLOW_CARD_PREVIEW
from tenants.access import TENANT_ADMIN_ROLES
from tenants.models import TenantMembership
from workflows.models import Edge, Node, WorkflowExecution


def _related_count(model):
    counts = (
        model.objects.filter(workflow_id=OuterRef('pk'))
        .order_by()
        .values('workflow_id')
        .annotate(total=Count('pk'))
        .values('total')
    )
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def prepare_workflow_list(queryset, user):
    """Keep bounded preview rows separate from complete graph relations."""
    preview_nodes = Node.objects.only(
        'id', 'workflow_id', 'node_type', 'name', 'position_x', 'position_y',
    )[:WORKFLOW_CARD_PREVIEW['max_nodes']]
    preview_edges = Edge.objects.only(
        'id', 'workflow_id', 'source_node_id', 'target_node_id',
    )[:WORKFLOW_CARD_PREVIEW['max_edges']]
    tenant_admin = TenantMembership.objects.filter(
        user_id=user.pk, tenant_id=OuterRef('tenant_id'), is_active=True, role__in=TENANT_ADMIN_ROLES,
    )
    can_edit = Value(True, output_field=BooleanField()) if user.is_superuser else Case(
        When(owner_id=user.pk, then=Value(True)),
        default=Exists(tenant_admin),
        output_field=BooleanField(),
    )
    return queryset.annotate(
        _list_execution_count=_related_count(WorkflowExecution),
        _list_node_count=_related_count(Node),
        _list_can_edit=can_edit,
    ).prefetch_related(
        Prefetch('nodes', queryset=preview_nodes, to_attr='list_preview_nodes'),
        Prefetch('edges', queryset=preview_edges, to_attr='list_preview_edges'),
    )
