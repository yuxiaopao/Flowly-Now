from django.urls import path
from .views import DatasetListView, CategoryListView

urlpatterns = [
    path('datasets/', DatasetListView.as_view(), name='dataset-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
]
