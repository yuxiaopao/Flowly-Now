"""
URL configuration for core app.
Registers health, notifications, and audit endpoints.
All endpoints are prefixed with 'api/v1/' via config/urls.py include.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.health_views import HealthCheckView, PingView
from .views.notification_views import NotificationViewSet, NotificationPreferenceViewSet
from .views.audit_views import AuditLogViewSet, LoginHistoryViewSet, DataExportViewSet
from .views.system_views import SystemCapabilitiesView


router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'audit', AuditLogViewSet, basename='audit')
router.register(r'login-history', LoginHistoryViewSet, basename='login-history')
router.register(r'data-export', DataExportViewSet, basename='data-export')


urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('ping/', PingView.as_view(), name='ping'),
    path('system/capabilities/', SystemCapabilitiesView.as_view(), name='system-capabilities'),
    path('', include(router.urls)),
]
