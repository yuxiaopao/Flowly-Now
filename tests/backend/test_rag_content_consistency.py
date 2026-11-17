"""Knowledge content changes retain atomic deletion and fresh patch semantics."""
import pytest
from django.contrib import admin
from types import SimpleNamespace
from django.db.models.signals import pre_delete
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from rag.models import DocumentCollection, Document, Chunk, VectorStore
from rag.pipeline import DocumentProcessor, RAGService
from rag.serializers import DocumentSerializer
from rag.views import DocumentViewSet
from rag.admin import DocumentAdmin

pytestmark = pytest.mark.django_db(transaction=True)
BASE = '/api/v1/rag'


@pytest.fixture
def content(user):
    store = VectorStore.objects.create(owner=user, name='Content consistency', store_type='memory')
    collection = DocumentCollection.objects.create(owner=user, name='Content consistency', vector_store=store, retrieval_mode='keyword')
    result = DocumentProcessor(collection).process_text('Original workflow evidence.', {'title': 'Evidence'})
    assert result['success']
    return collection, Document.objects.get(pk=result['document_id'])


def test_collection_delete_rolls_back_content_when_parent_delete_fails(authenticated_client, content):
    collection, document = content
    chunk_ids = list(document.chunks.values_list('id', flat=True))

    def reject_collection(sender, instance, **kwargs):
        if instance.pk == collection.pk:
            raise ValidationError('Isolated parent deletion failure.')

    pre_delete.connect(reject_collection, sender=DocumentCollection, weak=False)
    try:
        response = authenticated_client.delete(f'{BASE}/collections/{collection.pk}/')
    finally:
        pre_delete.disconnect(reject_collection, sender=DocumentCollection)
    assert response.status_code == 400
    assert DocumentCollection.objects.filter(pk=collection.pk).exists()
    assert Document.objects.filter(pk=document.pk).exists()
    assert set(Chunk.objects.filter(document_id=document.pk).values_list('pk', flat=True)) == set(chunk_ids)
    assert RAGService(collection).retrieve('workflow')


def test_partial_document_update_preserves_content_committed_before_its_lock(user, content):
    collection, document = content
    serializer = DocumentSerializer(document, data={'metadata': {'team': 'new'}}, partial=True)
    serializer.is_valid(raise_exception=True)
    # Another editor committed after this request loaded its instance, before
    # it obtained the shared collection lock. A metadata PATCH must keep it.
    Document.objects.filter(pk=document.pk).update(content='New committed workflow evidence.')
    request = APIRequestFactory().patch('/', {'metadata': {'team': 'new'}}, format='json')
    force_authenticate(request, user=user)
    view = DocumentViewSet()
    view.action_map = {'patch': 'partial_update'}
    view.request = view.initialize_request(request)
    view.perform_update(serializer)
    document.refresh_from_db()
    assert document.content == 'New committed workflow evidence.'
    assert document.metadata == {'team': 'new'} and document.status == 'completed'
    assert 'New committed' in document.chunks.get().content


def test_document_delete_and_clear_keep_real_statistics(authenticated_client, content):
    collection, document = content
    second = DocumentProcessor(collection).process_text('Second evidence.', {'title': 'Second'})
    assert second['success']
    response = authenticated_client.delete(f'{BASE}/documents/{document.pk}/')
    assert response.status_code == 204
    collection.refresh_from_db()
    assert collection.document_count == 1 and collection.chunk_count == 1
    response = authenticated_client.delete(f'{BASE}/collections/{collection.pk}/clear/')
    assert response.status_code == 200
    collection.refresh_from_db()
    assert collection.document_count == collection.chunk_count == 0
    assert not collection.documents.exists()


def test_bulk_admin_failure_and_cleanup_keep_content_consistent(user, content):
    from datetime import timedelta
    from django.utils import timezone
    from rag.tasks import cleanup_failed_documents
    collection, first = content
    other = DocumentCollection.objects.create(owner=user, name='Second collection', vector_store=collection.vector_store)
    result = DocumentProcessor(other).process_text('Another workflow evidence.', {'title': 'Other'})
    assert result['success']
    ids = [first.pk, result['document_id']]
    selected = Document.objects.filter(pk__in=ids).order_by('-collection_id')
    DocumentAdmin(Document, admin.site).mark_as_failed(SimpleNamespace(user=user), selected)
    assert selected.filter(status='failed').count() == 2
    Document.objects.filter(pk__in=ids).update(updated_at=timezone.now()-timedelta(days=8))
    assert cleanup_failed_documents(days=7) == 2
    assert not Document.objects.filter(pk__in=ids).exists()
    for row in (collection, other):
        row.refresh_from_db()
        assert row.document_count == row.chunk_count == 0
