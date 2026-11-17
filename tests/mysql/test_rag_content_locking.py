"""Actual InnoDB collection locks precede bulk/admin content mutations."""
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.db import connection, connections, transaction

from rag.admin import DocumentAdmin
from rag.models import Document, DocumentCollection, VectorStore, Chunk
from rag.pipeline import RAGService

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize('operation', ['document_bulk', 'collection_bulk', 'store_cascade',
    'owner_cascade', 'chunk_bulk', 'admin_mark_failed'])
def test_bulk_and_admin_mutations_wait_for_every_collection_before_cleanup(user, operation):
    assert connection.vendor == 'mysql', 'Run with the isolated MySQL test settings.'
    store = VectorStore.objects.create(owner=user, name='Locked content', store_type='memory')
    collections = [DocumentCollection.objects.create(owner=user, name=f'Locked {index}', vector_store=store)
                   for index in range(2)]
    documents = [Document.objects.create(collection=row, title='Protected evidence', content='Evidence', status='completed')
                 for row in collections]
    for document in documents:
        Chunk.objects.create(document=document, content='Evidence')
    collection_ids = [row.pk for row in collections]
    document_ids = [row.pk for row in documents]
    owner_id, store_id = user.pk, store.pk
    started, finished, cleanup = threading.Event(), threading.Event(), threading.Event()
    errors = []
    original_cleanup = RAGService.delete_chunk_vectors

    def observe_cleanup(service, chunks):
        cleanup.set()
        return original_cleanup(service, chunks)

    def mutate():
        try:
            started.set()
            selected = Document.objects.filter(pk__in=document_ids).order_by('-collection_id')
            if operation == 'document_bulk':
                selected.delete()
            elif operation == 'collection_bulk':
                DocumentCollection.objects.filter(pk__in=collection_ids).order_by('-pk').delete()
            elif operation == 'store_cascade':
                VectorStore.objects.filter(pk=store_id).delete()
            elif operation == 'owner_cascade':
                type(user).objects.filter(pk=owner_id).delete()
            elif operation == 'chunk_bulk':
                Chunk.objects.filter(document_id__in=document_ids).delete()
            else:
                DocumentAdmin(Document, admin.site).mark_as_failed(SimpleNamespace(user=user), selected)
        except Exception as exc:
            errors.append(exc)
        finally:
            connections.close_all()
            finished.set()

    task = threading.Thread(target=mutate, daemon=True)
    try:
        with patch.object(RAGService, 'delete_chunk_vectors', observe_cleanup):
            with transaction.atomic():
                # Hold the second lock in the canonical UUID order. The
                # mutation must acquire the entire set before remote cleanup.
                DocumentCollection.objects.select_for_update().get(pk=max(collection_ids, key=str))
                task.start()
                assert started.wait(5)
                assert not cleanup.wait(.3), 'Remote deletion started before all collection locks were held.'
                assert not finished.is_set(), errors
                assert Document.objects.filter(pk__in=document_ids, status='completed').count() == 2
            task.join(10)
        assert not task.is_alive() and not errors
        if operation == 'admin_mark_failed':
            assert Document.objects.filter(pk__in=document_ids, status='failed').count() == 2
        elif operation == 'chunk_bulk':
            assert not Chunk.objects.filter(document_id__in=document_ids).exists()
        else:
            assert not Document.objects.filter(pk__in=document_ids).exists()
    finally:
        task.join(10)
