"""
Branding API URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BrandingViewSet, EmailTemplateViewSet, CustomDomainViewSet, ThemePresetViewSet
)

router = DefaultRouter()
router.register(r'branding', BrandingViewSet, basename='branding')
router.register(r'email-templates', EmailTemplateViewSet, basename='email-template')
router.register(r'domains', CustomDomainViewSet, basename='custom-domain')
router.register(r'presets', ThemePresetViewSet, basename='theme-preset')

urlpatterns = [
    path('', include(router.urls)),
]
