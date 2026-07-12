"""
Admin app URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserManagementViewSet, TenantManagementViewSet,
    WorkflowManagementViewSet, AgentManagementViewSet,
    AuditLogListView, SystemUsageView, SystemHealthView,
    SystemSettingsView, CacheClearView,
    APIKeyManagementViewSet,
)
from .module_views import (
    PublicSiteConfigView,
    ModuleListView,
    ModuleSettingsView,
    LegalDocumentViewSet,
    UserTermsAcceptanceViewSet,
    FeatureVisibilityRuleViewSet,
    GatewayRouteRuleViewSet,
    PaymentProviderConfigViewSet,
    EmailSendLogViewSet,
    TestEmailView,
    BackupRecordViewSet,
    EnhancedBackupView,
)

router = DefaultRouter()
router.register(r'users', UserManagementViewSet, basename='admin-user')
router.register(r'tenants', TenantManagementViewSet, basename='admin-tenant')
router.register(r'workflows', WorkflowManagementViewSet, basename='admin-workflow')
router.register(r'agents', AgentManagementViewSet, basename='admin-agent')
router.register(r'api-keys', APIKeyManagementViewSet, basename='admin-api-key')
router.register(r'legal-documents', LegalDocumentViewSet, basename='admin-legal-document')
router.register(r'terms-acceptances', UserTermsAcceptanceViewSet, basename='admin-terms-acceptance')
router.register(r'feature-visibility', FeatureVisibilityRuleViewSet, basename='admin-feature-visibility')
router.register(r'gateway-routes', GatewayRouteRuleViewSet, basename='admin-gateway-route')
router.register(r'payment-providers', PaymentProviderConfigViewSet, basename='admin-payment-provider')
router.register(r'email-logs', EmailSendLogViewSet, basename='admin-email-log')
router.register(r'backup-records', BackupRecordViewSet, basename='admin-backup-record')

urlpatterns = [
    path('', include(router.urls)),
    path('usage/', SystemUsageView.as_view(), name='admin-usage'),
    path('health/', SystemHealthView.as_view(), name='admin-health'),
    path('settings/', SystemSettingsView.as_view(), name='admin-settings'),
    path('settings/modules/', ModuleListView.as_view(), name='admin-settings-modules'),
    path('settings/modules/<str:module>/', ModuleSettingsView.as_view(), name='admin-settings-module'),
    path('logs/', AuditLogListView.as_view(), name='admin-logs'),
    path('cache/clear/', CacheClearView.as_view(), name='admin-cache-clear'),
    path('backup/', EnhancedBackupView.as_view(), name='admin-backup'),
    path('email/test/', TestEmailView.as_view(), name='admin-email-test'),
]
