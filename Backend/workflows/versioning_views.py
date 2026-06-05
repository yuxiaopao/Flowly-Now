"""
Workflow versioning API views.
"""

import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Workflow, WorkflowVersion
from .serializers import WorkflowSerializer
from .versioning import WorkflowVersion as WorkflowVersionModel


class WorkflowVersionViewSet(viewsets.ViewSet):
    """ViewSet for workflow versions."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workflow_id = self.request.query_params.get('workflow_id')
        if workflow_id:
            return WorkflowVersionModel.objects.filter(
                workflow_id=workflow_id,
                workflow__owner=self.request.user
            )
        return WorkflowVersionModel.objects.none()

    @action(detail=False, methods=['post'])
    def create_version(self, request):
        """Create a new version of a workflow."""
        workflow_id = request.data.get('workflow_id')
        description = request.data.get('description', '')
        is_auto_save = request.data.get('is_auto_save', False)

        try:
            workflow = Workflow.objects.get(id=workflow_id, owner=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {'error': 'Workflow not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get next version number
        last_version = WorkflowVersionModel.objects.filter(
            workflow=workflow
        ).order_by('-version_number').first()

        next_version = (last_version.version_number + 1) if last_version else 1

        # Create version
        version = WorkflowVersionModel.objects.create(
            workflow=workflow,
            version_number=next_version,
            name=f"Version {next_version}",
            nodes=workflow.nodes,
            edges=workflow.edges,
            variables=workflow.variables,
            description=description,
            is_auto_save=is_auto_save,
            created_by=request.user
        )

        return Response({
            'id': version.id,
            'version_number': version.version_number,
            'created_at': version.created_at
        })

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore workflow to a specific version."""
        version = self.get_object()

        if version.workflow.owner != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create backup of current state
        self._create_backup(version.workflow, request.user)

        # Restore
        workflow = version.workflow
        workflow.nodes = version.nodes
        workflow.edges = version.edges
        workflow.variables = version.variables
        workflow.save()

        return Response({
            'message': 'Workflow restored successfully',
            'workflow': WorkflowSerializer(workflow).data
        })

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview a specific version."""
        version = self.get_object()
        return Response({
            'id': version.id,
            'version_number': version.version_number,
            'nodes': version.nodes,
            'edges': version.edges,
            'variables': version.variables,
            'description': version.description,
            'created_at': version.created_at,
            'created_by': version.created_by.username if version.created_by else None
        })

    @action(detail=False, methods=['get'])
    def list_by_workflow(self, request):
        """List all versions for a workflow."""
        workflow_id = request.query_params.get('workflow_id')

        if not workflow_id:
            return Response(
                {'error': 'workflow_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workflow = Workflow.objects.get(id=workflow_id, owner=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {'error': 'Workflow not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        versions = WorkflowVersionModel.objects.filter(workflow=workflow).order_by('-version_number')

        data = [{
            'id': v.id,
            'version_number': v.version_number,
            'name': v.name,
            'description': v.description,
            'node_count': v.node_count,
            'edge_count': v.edge_count,
            'is_auto_save': v.is_auto_save,
            'created_at': v.created_at,
            'created_by': v.created_by.username if v.created_by else None
        } for v in versions]

        return Response(data)

    @action(detail=False, methods=['post'])
    def compare(self, request):
        """Compare two versions."""
        version1_id = request.data.get('version1_id')
        version2_id = request.data.get('version2_id')

        try:
            version1 = WorkflowVersionModel.objects.get(id=version1_id)
            version2 = WorkflowVersionModel.objects.get(id=version2_id)
        except WorkflowVersionModel.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if version1.workflow.owner != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Calculate diff
        diff = self._calculate_diff(version1, version2)

        return Response({
            'version1': {
                'id': version1.id,
                'version_number': version1.version_number
            },
            'version2': {
                'id': version2.id,
                'version_number': version2.version_number
            },
            'diff': diff
        })

    def _create_backup(self, workflow, user):
        """Create a backup version before restoring."""
        last_version = WorkflowVersionModel.objects.filter(
            workflow=workflow
        ).order_by('-version_number').first()

        next_version = (last_version.version_number + 1) if last_version else 1

        return WorkflowVersionModel.objects.create(
            workflow=workflow,
            version_number=next_version,
            name=f"Auto-backup before restore",
            nodes=workflow.nodes,
            edges=workflow.edges,
            variables=workflow.variables,
            description="Automatic backup created before restore operation",
            is_auto_save=True,
            created_by=user
        )

    def _calculate_diff(self, version1, version2):
        """Calculate diff between two versions."""
        nodes1 = {n['id']: n for n in version1.nodes}
        nodes2 = {n['id']: n for n in version2.nodes}

        edges1 = {f"{e['source']}-{e['target']}": e for e in version1.edges}
        edges2 = {f"{e['source']}-{e['target']}": e for e in version2.edges}

        nodes_added = [nodes2[k] for k in set(nodes2.keys()) - set(nodes1.keys())]
        nodes_removed = [nodes1[k] for k in set(nodes1.keys()) - set(nodes2.keys())]
        nodes_modified = []

        for k in set(nodes1.keys()) & set(nodes2.keys()):
            if nodes1[k] != nodes2[k]:
                nodes_modified.append({
                    'id': k,
                    'before': nodes1[k],
                    'after': nodes2[k]
                })

        edges_added = [edges2[k] for k in set(edges2.keys()) - set(edges1.keys())]
        edges_removed = [edges1[k] for k in set(edges1.keys()) - set(edges2.keys())]

        return {
            'nodes': {
                'added': nodes_added,
                'removed': nodes_removed,
                'modified': nodes_modified
            },
            'edges': {
                'added': edges_added,
                'removed': edges_removed
            }
        }
