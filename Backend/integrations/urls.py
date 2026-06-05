"""
Integration API URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WebhookViewSet, IntegrationViewSet, IntegrationTemplateViewSet,
    webhook_receiver
)

router = DefaultRouter()
router.register(r'webhooks', WebhookViewSet, basename='webhook')
router.register(r'integrations', IntegrationViewSet, basename='integration')
router.register(r'templates', IntegrationTemplateViewSet, basename='integration-template')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook-receiver/', webhook_receiver, name='webhook-receiver'),
]
