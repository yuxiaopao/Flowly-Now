"""
URL configuration for training app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'training-jobs', views.TrainingJobViewSet)
router.register(r'yolo-runs', views.YoloTrainingRunViewSet, basename='yolo-run')
router.register(r'datasets', views.DatasetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
