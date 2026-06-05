"""
Marketplace API URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WorkflowTemplateViewSet, TemplateCategoryViewSet,
    MyTemplatesViewSet, InstalledTemplatesViewSet
)

router = DefaultRouter()
router.register(r'templates', WorkflowTemplateViewSet, basename='workflow-template')
router.register(r'categories', TemplateCategoryViewSet, basename='template-category')
router.register(r'my-templates', MyTemplatesViewSet, basename='my-template')
router.register(r'installed', InstalledTemplatesViewSet, basename='installed-template')

urlpatterns = [
    path('', include(router.urls)),
]
