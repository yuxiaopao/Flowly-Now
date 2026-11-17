"""One collection lock order for content mutation and deletion cascades."""
from django.contrib.auth import get_user_model
from django.db import connections
from django.db.models import Q, QuerySet

from .models import Chunk, Document, DocumentCollection, VectorStore


def lock_collections(collection_ids, *, using='default'):
    locked = []
    for identity in sorted(set(collection_ids), key=str):
        collection = DocumentCollection.objects.using(using).select_for_update().filter(pk=identity).first()
        if collection is not None:
            locked.append(collection)
    return locked


def lock_deletion_collections(origin, collection_id, *, using='default'):
    """Collector signals run inside one transaction, before any rows are removed.

    Lock all root-selected collections in UUID order on the first signal, rather
    than acquiring locks in document creation order during a bulk deletion.
    The marker belongs to the actual Atomic object, so reusing a queryset in a
    later transaction cannot reuse a lock that has already been released.
    """
    blocks = connections[using].atomic_blocks
    boundary = blocks[-1] if blocks else None
    previous = getattr(origin, '_rag_deletion_lock_boundaries', {})
    if boundary is not None and previous.get(using) is boundary:
        return
    ids = {collection_id}
    if origin is not None:
        model = origin.model if isinstance(origin, QuerySet) else type(origin)
        model = model._meta.concrete_model
        roots = origin.values('pk') if isinstance(origin, QuerySet) else [origin.pk]
        collections = DocumentCollection.objects.using(using)
        if model is Document:
            ids.update(Document.objects.using(using).filter(pk__in=roots).values_list('collection_id', flat=True))
        elif model is Chunk:
            ids.update(Chunk.objects.using(using).filter(pk__in=roots).values_list('document__collection_id', flat=True))
        elif model is DocumentCollection:
            ids.update(collections.filter(pk__in=roots).values_list('pk', flat=True))
        elif model is VectorStore:
            ids.update(collections.filter(vector_store_id__in=roots).values_list('pk', flat=True))
        elif model is get_user_model()._meta.concrete_model:
            ids.update(collections.filter(Q(owner_id__in=roots) | Q(vector_store__owner_id__in=roots)).values_list('pk', flat=True))
    lock_collections(ids, using=using)
    if origin is not None and boundary is not None:
        origin._rag_deletion_lock_boundaries = {**previous, using: boundary}
