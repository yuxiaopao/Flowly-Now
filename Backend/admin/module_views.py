"""
Platform configuration module views for admin API and Django admin panels.
"""

import logging
import os

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.db import models
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.audit import AuditAction

from .constants import SETTING_MODULE_LABELS
from .models import (
    BackupRecord,
    EmailSendLog,
    FeatureVisibilityRule,
    GatewayRouteRule,
    LegalDocument,
    PaymentProviderConfig,
    UserTermsAcceptance,
)
from .serializers import (
    BackupRecordSerializer,
    EmailSendLogSerializer,
    FeatureVisibilityRuleSerializer,
    GatewayRouteRuleSerializer,
    LegalDocumentSerializer,
    PaymentProviderConfigSerializer,
    TestEmailSerializer,
    UserTermsAcceptanceSerializer,
)
from .services.config_service import (
    build_module_schema,
    get_module_settings,
    get_public_config,
    get_smtp_connection_params,
    invalidate_public_config_cache,
    list_all_modules,
    save_module_settings,
    serialize_legal_document,
)
from .views import BackupView, IsSuperUser, _audit

logger = logging.getLogger(__name__)


class PublicSiteConfigView(APIView):
    """Public read-only site configuration for the user-facing frontend."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(get_public_config())


class ModuleSettingsView(APIView):
    """GET/PATCH settings for a specific configuration module."""

    permission_classes = [IsSuperUser]

    def get(self, request, module):
        if module not in SETTING_MODULE_LABELS:
            return Response({'error': '未知模块'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'module': module,
            'label': SETTING_MODULE_LABELS[module],
            'schema': build_module_schema(module),
            'values': get_module_settings(module),
        })

    def patch(self, request, module):
        if module not in SETTING_MODULE_LABELS:
            return Response({'error': '未知模块'}, status=status.HTTP_404_NOT_FOUND)
        try:
            values = save_module_settings(module, request.data or {}, user=request.user)
        except ValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        _audit(
            request, AuditAction.SETTINGS_UPDATE,
            f'更新配置模块 [{SETTING_MODULE_LABELS[module]}]',
            target_type='system_settings', target_name=module,
        )
        invalidate_public_config_cache()
        return Response({'success': True, 'values': values})


class ModuleListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        return Response({'modules': list_all_modules()})


class LegalDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = LegalDocumentSerializer
    queryset = LegalDocument.objects.all()

    def get_queryset(self):
        qs = LegalDocument.objects.all()
        doc_type = self.request.query_params.get('doc_type')
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        return qs.annotate(acceptance_count=models.Count('acceptances'))

    def perform_create(self, serializer):
        doc = serializer.save(created_by=self.request.user)
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'创建法律文档 {doc.title}', target_type='legal_document', target_id=doc.id)

    def perform_update(self, serializer):
        doc = serializer.save()
        invalidate_public_config_cache()
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'更新法律文档 {doc.title}', target_type='legal_document', target_id=doc.id)

    def perform_destroy(self, instance):
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'删除法律文档 {instance.title}', target_type='legal_document', target_id=instance.id)
        instance.delete()
        invalidate_public_config_cache()


class UserTermsAcceptanceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = UserTermsAcceptanceSerializer
    queryset = UserTermsAcceptance.objects.select_related('user', 'document').all()


class FeatureVisibilityRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = FeatureVisibilityRuleSerializer
    queryset = FeatureVisibilityRule.objects.select_related('group').all()

    def perform_create(self, serializer):
        rule = serializer.save(updated_by=self.request.user)
        invalidate_public_config_cache()
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'创建功能可见性规则 {rule.feature_key}', target_type='feature_visibility', target_id=rule.id)

    def perform_update(self, serializer):
        rule = serializer.save(updated_by=self.request.user)
        invalidate_public_config_cache()
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'更新功能可见性规则 {rule.feature_key}', target_type='feature_visibility', target_id=rule.id)

    def perform_destroy(self, instance):
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'删除功能可见性规则 {instance.feature_key}', target_type='feature_visibility', target_id=instance.id)
        instance.delete()
        invalidate_public_config_cache()


class GatewayRouteRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = GatewayRouteRuleSerializer
    queryset = GatewayRouteRule.objects.all()

    def perform_create(self, serializer):
        rule = serializer.save(updated_by=self.request.user)
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'创建网关路由 {rule.name}', target_type='gateway_route', target_id=rule.id)

    def perform_update(self, serializer):
        rule = serializer.save(updated_by=self.request.user)
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'更新网关路由 {rule.name}', target_type='gateway_route', target_id=rule.id)

    def perform_destroy(self, instance):
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'删除网关路由 {instance.name}', target_type='gateway_route', target_id=instance.id)
        instance.delete()


class PaymentProviderConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = PaymentProviderConfigSerializer
    queryset = PaymentProviderConfig.objects.all()

    def perform_create(self, serializer):
        item = serializer.save(updated_by=self.request.user)
        invalidate_public_config_cache()
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'创建支付渠道 {item.display_name}', target_type='payment_provider', target_id=item.id)

    def perform_update(self, serializer):
        item = serializer.save(updated_by=self.request.user)
        invalidate_public_config_cache()
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'更新支付渠道 {item.display_name}', target_type='payment_provider', target_id=item.id)

    def perform_destroy(self, instance):
        _audit(self.request, AuditAction.SETTINGS_UPDATE, f'删除支付渠道 {instance.display_name}', target_type='payment_provider', target_id=instance.id)
        instance.delete()
        invalidate_public_config_cache()


class EmailSendLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = EmailSendLogSerializer
    queryset = EmailSendLog.objects.all()


class TestEmailView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        serializer = TestEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        smtp = get_smtp_connection_params()

        log = EmailSendLog.objects.create(
            to_email=data['to_email'],
            subject=data['subject'],
            template_key='test',
            status='queued',
            sent_by=request.user,
        )

        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=smtp['host'] or django_settings.EMAIL_HOST,
                port=smtp['port'] or django_settings.EMAIL_PORT,
                username=smtp['username'] or django_settings.EMAIL_HOST_USER,
                password=smtp['password'] or django_settings.EMAIL_HOST_PASSWORD,
                use_tls=smtp['use_tls'],
            )
            from_email = smtp['from_email'] or django_settings.DEFAULT_FROM_EMAIL
            if smtp['from_name'] and from_email:
                from_email = f"{smtp['from_name']} <{from_email}>"

            email = EmailMessage(
                subject=data['subject'],
                body=data['message'],
                from_email=from_email,
                to=[data['to_email']],
                connection=connection,
            )
            email.send(fail_silently=False)
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save(update_fields=['status', 'sent_at'])
            _audit(request, AuditAction.OTHER, f'发送测试邮件至 {data["to_email"]}', target_type='email')
            return Response({'success': True, 'log_id': log.id})
        except Exception as exc:
            log.status = 'failed'
            log.error_message = str(exc)
            log.save(update_fields=['status', 'error_message'])
            logger.exception('Test email failed')
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BackupRecordViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = BackupRecordSerializer
    queryset = BackupRecord.objects.select_related('created_by').all()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        record = self.get_object()
        if not os.path.isfile(record.file_path):
            raise Http404('备份文件不存在')
        return FileResponse(open(record.file_path, 'rb'), as_attachment=True, filename=record.name)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove(self, request, pk=None):
        record = self.get_object()
        if os.path.isfile(record.file_path):
            os.remove(record.file_path)
        _audit(request, AuditAction.SETTINGS_UPDATE, f'删除备份 {record.name}', target_type='backup', target_id=record.id)
        record.delete()
        return Response({'success': True})


class EnhancedBackupView(BackupView):
    """Extend backup API to persist BackupRecord entries."""

    def post(self, request):
        response = super().post(request)
        if response.status_code != 200:
            return response

        data = response.data
        for artifact in data.get('artifacts', []):
            path = os.path.join(django_settings.BACKUP_DIR, artifact['name'])
            BackupRecord.objects.create(
                name=artifact['name'],
                file_path=path,
                backup_type=artifact.get('type', request.data.get('type', 'full')),
                size=artifact.get('size', 0),
                status='completed',
                include_media=bool(request.data.get('include_media', True)),
                created_by=request.user,
            )
        return response

    def get(self, request):
        db_records = BackupRecordSerializer(
            BackupRecord.objects.all()[:100], many=True
        ).data
        file_response = super().get(request)
        return Response({
            'records': db_records,
            'files': file_response.data.get('results', []),
        })
