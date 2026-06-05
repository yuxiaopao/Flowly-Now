"""
Audit log API views.
"""

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


class DataExportViewSet(viewsets.ModelViewSet):
    """ViewSet for data exports."""

    serializer_class = DataExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DataExport.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Get download URL for export."""
        export = self.get_object()
        if export.status != 'completed':
            return Response({'error': 'Export not ready'}, status=status.HTTP_400_BAD_REQUEST)
        if export.expires_at and export.expires_at < timezone.now():
            return Response({'error': 'Export expired'}, status=status.HTTP_410_GONE)

        export.download_count += 1
        export.save(update_fields=['download_count'])

        return Response({
            'download_url': export.file_url,
            'expires_at': export.expires_at
        })

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

        # In production, this would trigger an async task to process the export
        export.status = 'completed'
        export.file_name = f"export_{export.id}.{export_format}"
        export.file_url = f"/api/exports/{export.id}/download/"
        export.save()

        return Response(
            DataExportSerializer(export).data,
            status=status.HTTP_201_CREATED
        )
