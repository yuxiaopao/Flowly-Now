"""
URL routing for website generator app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GeneratedSiteViewSet

router = DefaultRouter()
router.register(r'', GeneratedSiteViewSet, basename='website-generator')

urlpatterns = [
    path('', include(router.urls)),
]
