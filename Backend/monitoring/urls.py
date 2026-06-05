"""
URL patterns for monitoring app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExecutionLogViewSet, AlertRuleViewSet, AlertViewSet,
    MetricViewSet, NotificationChannelViewSet, NotificationViewSet,
    AnalyticsViewSet, ExecutionStatsViewSet, ActiveExecutionsViewSet,
    HealthCheckViewSet, ResourceUsageViewSet, ExecutionTrendViewSet
)

router = DefaultRouter()
router.register(r'logs', ExecutionLogViewSet, basename='log')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'rules', AlertRuleViewSet, basename='rule')
router.register(r'metrics', MetricViewSet, basename='metric')
router.register(r'channels', NotificationChannelViewSet, basename='channel')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'stats', ExecutionStatsViewSet, basename='stats')
router.register(r'active-executions', ActiveExecutionsViewSet, basename='active-execution')
router.register(r'health', HealthCheckViewSet, basename='health')
router.register(r'resources', ResourceUsageViewSet, basename='resources')
router.register(r'trend', ExecutionTrendViewSet, basename='trend')

urlpatterns = [
    path('', include(router.urls)),
]
