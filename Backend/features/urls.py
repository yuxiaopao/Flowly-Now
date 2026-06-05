"""
Features URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SystemFeatureViewSet

router = DefaultRouter()
router.register(r'', SystemFeatureViewSet, basename='feature')

urlpatterns = [
    path('', include(router.urls)),
]
