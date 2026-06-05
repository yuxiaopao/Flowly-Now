"""
URL patterns for augmentation app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AugmentationJobViewSet

router = DefaultRouter()
router.register(r'', AugmentationJobViewSet, basename='augmentation')

urlpatterns = [
    path('', include(router.urls)),
]
