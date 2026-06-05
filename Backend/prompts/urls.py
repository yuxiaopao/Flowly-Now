"""
URL patterns for prompts app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromptTemplateViewSet, PromptCategoryViewSet, MyPromptViewSet

router = DefaultRouter()
router.register(r'templates', PromptTemplateViewSet, basename='prompt-template')
router.register(r'categories', PromptCategoryViewSet, basename='prompt-category')
router.register(r'my-prompts', MyPromptViewSet, basename='my-prompt')

urlpatterns = [
    path('', include(router.urls)),
]
