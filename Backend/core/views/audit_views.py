"""
Audit log API views.
"""

from django.http import HttpResponse
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models

from ..models.audit import AuditLog, LoginHistory, DataExport, PersonalBackupPolicy
from ..serializers.audit_serializers import (
    AuditLogSerializer,
    LoginHistorySerializer,
    DataExportSerializer,
    DataExportRequestSerializer,
    PersonalBackupPolicySerializer,
)
from core.services.personal_exports import create_export, render_export
from core.services.personal_restore import preview_restore, confirm_restore
from core.services.personal_backups import save_backup_policy
from core.services.personal_deletion import preview_deletion, delete_personal_data
from rest_framework.exceptions import ValidationError
from core.data_constants import SNAPSHOT_VERSION


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


class DataExportViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for data exports."""

    serializer_class = DataExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DataExport.objects.filter(user=self.request.user).annotate(
            _restorable=models.Case(models.When(
                status='completed', format='json', export_type__in=['full', 'workflows', 'agents'],
                snapshot__schema_version=SNAPSHOT_VERSION, then=models.Value(True),
            ), default=models.Value(False), output_field=models.BooleanField()),
        ).defer('snapshot')

    @action(detail=False, methods=['get'])
    def delete_preview(self, request):
        return Response(preview_deletion(request.user))

    @action(detail=False, methods=['post'])
    def delete_personal_data(self, request):
        return Response(delete_personal_data(request.user, request.data))

    @action(detail=False, methods=['get', 'patch'])
    def backup_settings(self, request):
        policy, _ = PersonalBackupPolicy.objects.get_or_create(user=request.user)
        if request.method == 'PATCH':
            serializer = PersonalBackupPolicySerializer(policy, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            policy = save_backup_policy(request.user, serializer.validated_data)
        return Response(PersonalBackupPolicySerializer(policy).data)

    @action(detail=True, methods=['post'])
    def restore_preview(self, request, pk=None):
        return Response(preview_restore(self.get_object()))

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        export = self.get_object()
        if request.data.get('confirm') is not True or not isinstance(request.data.get('confirmation_token'), str):
            raise ValidationError('请先预览并明确确认恢复为副本。')
        result, created = confirm_restore(request.user, export.pk, request.data['confirmation_token'])
        return Response(result, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download export file (authenticated blob)."""
        export = self.get_object()
        if export.status != 'completed':
            return Response({'error': 'Export not ready'}, status=status.HTTP_400_BAD_REQUEST)
        if export.expires_at and export.expires_at < timezone.now():
            return Response({'error': 'Export expired'}, status=status.HTTP_410_GONE)

        content, content_type = render_export(export)
        DataExport.objects.filter(pk=export.pk).update(download_count=models.F('download_count') + 1)

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{export.file_name or f"export_{export.id}.{export.format}"}"'
        return response

    @action(detail=False, methods=['post'])
    def request_export(self, request):
        """Request a new data export."""
        serializer = DataExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        export = create_export(request.user, serializer.validated_data)

        return Response(
            DataExportSerializer(export).data,
            status=status.HTTP_201_CREATED
        )
