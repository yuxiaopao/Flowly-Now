"""
Templates API URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TemplateCategoryViewSet, WorkflowTemplateViewSet,
    MyTemplateViewSet, TemplateVersionViewSet
)

router = DefaultRouter()
router.register(r'categories', TemplateCategoryViewSet, basename='template-category')
router.register(r'', WorkflowTemplateViewSet, basename='workflow-template')
router.register(r'my', MyTemplateViewSet, basename='my-template')
router.register(r'versions', TemplateVersionViewSet, basename='template-version')

urlpatterns = [
    path('', include(router.urls)),
]
