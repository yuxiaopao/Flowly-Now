"""
Audit log API views.
"""

import json

from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models

from ..models.audit import AuditLog, LoginHistory, DataExport
from ..serializers.audit_serializers import (
    AuditLogSerializer,
    LoginHistorySerializer,
    DataExportSerializer,
)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audit logs."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action', 'level', 'target_type']

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent audit logs."""
        limit = int(request.query_params.get('limit', 50))
        logs = AuditLog.objects.all()[:limit]
        data = [{
            'id': log.id,
            'user': log.user.username if log.user else 'System',
            'action': log.action,
            'action_display': log.get_action_display(),
            'level': log.level,
            'description': log.description,
            'target_type': log.target_type,
            'target_id': log.target_id,
            'ip_address': log.ip_address,
            'created_at': log.created_at
        } for log in logs]
        return Response(data)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get audit logs for a specific user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        limit = int(request.query_params.get('limit', 50))
        logs = AuditLog.objects.filter(user_id=user_id)[:limit]
        data = [{
            'id': log.id,
            'action': log.action,
            'action_display': log.get_action_display(),
            'description': log.description,
            'created_at': log.created_at
        } for log in logs]
        return Response(data)

    @action(detail=False, methods=['get'])
    def by_resource(self, request):
        """Get audit logs for a specific resource."""
        resource_type = request.query_params.get('resource_type')
        resource_id = request.query_params.get('resource_id')

        if not resource_type or not resource_id:
            return Response(
                {'error': 'resource_type and resource_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = AuditLog.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id
        )
        return Response(AuditLogSerializer(logs, many=True).data)


class LoginHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for login history."""

    serializer_class = LoginHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LoginHistory.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent login history."""
        limit = int(request.query_params.get('limit', 10))
        history = self.get_queryset()[:limit]
        return Response(LoginHistorySerializer(history, many=True).data)

    @action(detail=False, methods=['get'])
    def locations(self, request):
        """Get unique login locations."""
        locations = self.get_queryset().exclude(
            country=''
        ).values('country', 'city').annotate(
            count=models.Count('id'),
            last_login=models.Max('created_at')
        ).order_by('-count')
        return Response(list(locations))


def _serialize_export_rows(queryset, fields):
    return list(queryset.values(*fields))


def _build_export_payload(export):
    """Build export payload from the user's data."""
    user = export.user
    payload = {
        'export_type': export.export_type,
        'format': export.format,
        'exported_at': timezone.now().isoformat(),
        'user_id': user.id,
        'username': user.username,
    }

    if export.export_type in ('full', 'workflows'):
        from workflows.models import Workflow
        from tenants.access import get_accessible_workflow_queryset

        payload['workflows'] = _serialize_export_rows(
            get_accessible_workflow_queryset(user).filter(
                models.Q(owner=user) | models.Q(is_public=True)
            ).order_by('-created_at')[:500],
            ['id', 'name', 'description', 'status', 'created_at', 'updated_at'],
        )

    if export.export_type in ('full', 'executions'):
        from workflows.models import WorkflowExecution
        from tenants.access import get_accessible_workflow_queryset, get_accessible_tenant_ids

        payload['executions'] = _serialize_export_rows(
            WorkflowExecution.objects.filter(
                workflow__in=get_accessible_workflow_queryset(user),
            ).filter(
                models.Q(workflow__owner=user)
                | models.Q(triggered_by=user)
                | models.Q(workflow__tenant_id__in=get_accessible_tenant_ids(user))
            ).distinct().order_by('-created_at')[:500],
            ['id', 'workflow_id', 'status', 'started_at', 'completed_at', 'duration_ms'],
        )

    if export.export_type in ('full', 'audit_logs'):
        payload['audit_logs'] = _serialize_export_rows(
            AuditLog.objects.filter(user=user).order_by('-created_at')[:500],
            ['id', 'action', 'level', 'description', 'target_type', 'target_id', 'created_at'],
        )

    return payload


def _render_export_bytes(export):
    payload = _build_export_payload(export)
    if export.format == 'json':
        return json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'), 'application/json'
    if export.format == 'csv':
        lines = ['section,key,value']
        for section, rows in payload.items():
            if isinstance(rows, list):
                lines.append(f'{section},count,{len(rows)}')
            else:
                lines.append(f'meta,{section},{rows}')
        return '\n'.join(lines).encode('utf-8'), 'text/csv'
    return json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'), 'application/json'


class DataExportViewSet(viewsets.ModelViewSet):
    """ViewSet for data exports."""

    serializer_class = DataExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DataExport.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download export file (authenticated blob)."""
        export = self.get_object()
        if export.status != 'completed':
            return Response({'error': 'Export not ready'}, status=status.HTTP_400_BAD_REQUEST)
        if export.expires_at and export.expires_at < timezone.now():
            return Response({'error': 'Export expired'}, status=status.HTTP_410_GONE)

        content, content_type = _render_export_bytes(export)
        export.download_count += 1
        export.file_size = len(content)
        export.save(update_fields=['download_count', 'file_size'])

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{export.file_name or f"export_{export.id}.{export.format}"}"'
        return response

    @action(detail=False, methods=['post'])
    def request_export(self, request):
        """Request a new data export."""
        export_type = request.data.get('export_type', 'full')
        export_format = request.data.get('format', 'json')

        export = DataExport.objects.create(
            user=request.user,
            export_type=export_type,
            format=export_format,
            status='pending'
        )

        content, _ = _render_export_bytes(export)
        export.status = 'completed'
        export.file_name = f"export_{export.id}.{export_format}"
        export.file_size = len(content)
        export.file_url = request.build_absolute_uri(
            f'/api/v1/data-export/{export.id}/download/'
        )
        export.completed_at = timezone.now()
        export.save()

        return Response(
            DataExportSerializer(export).data,
            status=status.HTTP_201_CREATED
        )
