"""
URL patterns for gateway app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ModelProviderViewSet, AIModelViewSet,
    UserAPIKeyViewSet, APICallLogViewSet,
    GatewayChatView, GatewayEmbeddingsView,
    GatewayHealthView
)

router = DefaultRouter()
router.register(r'providers', ModelProviderViewSet, basename='provider')
router.register(r'models', AIModelViewSet, basename='model')
router.register(r'api-keys', UserAPIKeyViewSet, basename='api-key')
router.register(r'logs', APICallLogViewSet, basename='api-log')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', GatewayChatView.as_view(), name='gateway-chat'),
    path('embeddings/', GatewayEmbeddingsView.as_view(), name='gateway-embeddings'),
    path('health/', GatewayHealthView.as_view(), name='gateway-health'),
]
