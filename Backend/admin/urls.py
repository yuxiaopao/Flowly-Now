"""
Admin API URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserManagementViewSet, WorkflowManagementViewSet,
    AgentManagementViewSet, SystemUsageView,
    SystemHealthView, SystemSettingsView, APIKeyManagementViewSet
)

router = DefaultRouter()
router.register(r'users', UserManagementViewSet, basename='admin-user')
router.register(r'workflows', WorkflowManagementViewSet, basename='admin-workflow')
router.register(r'agents', AgentManagementViewSet, basename='admin-agent')
router.register(r'api-keys', APIKeyManagementViewSet, basename='admin-api-key')

urlpatterns = [
    path('', include(router.urls)),
    path('usage/', SystemUsageView.as_view(), name='admin-usage'),
    path('health/', SystemHealthView.as_view(), name='admin-health'),
    path('settings/', SystemSettingsView.as_view(), name='admin-settings'),
]
