"""
URL patterns for annotations app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnnotationProjectViewSet, AnnotationItemViewSet

# Main router for projects
router = DefaultRouter()
router.register(r'projects', AnnotationProjectViewSet, basename='annotation-project')

# URL patterns
urlpatterns = [
    # Project endpoints (from router)
    path('', include(router.urls)),
    
    # Item endpoints
    path(
        'items/<uuid:pk>/',
        AnnotationItemViewSet.as_view({'patch': 'partial_update'}),
        name='annotation-item-detail'
    ),
    path(
        'items/bulk_update/',
        AnnotationItemViewSet.as_view({'post': 'bulk_update'}),
        name='annotation-item-bulk-update'
    ),
]
