"""
URL patterns for RAG app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VectorStoreViewSet, DocumentCollectionViewSet,
    DocumentViewSet, ChunkViewSet, RAGPipelineViewSet
)

router = DefaultRouter()
router.register(r'vector-stores', VectorStoreViewSet, basename='vector-store')
router.register(r'collections', DocumentCollectionViewSet, basename='collection')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'chunks', ChunkViewSet, basename='chunk')
router.register(r'pipelines', RAGPipelineViewSet, basename='rag-pipeline')

urlpatterns = [
    path('', include(router.urls)),
]
