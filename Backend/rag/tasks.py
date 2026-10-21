"""Background entry points use the same transactional processor as HTTP ingestion."""
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from .models import Document, DocumentCollection
from .pipeline import DocumentProcessor, RAGService, refresh_collection_stats


@shared_task
def process_document_async(document_id):
    document = Document.objects.select_related('collection__vector_store').filter(id=document_id).first()
    if not document:
        return {'success': False, 'document_id': str(document_id), 'error': '文档不存在或已删除。'}
    result = DocumentProcessor(document.collection).process_document(document)
    return {**result, 'chunks_created': result.get('chunks', 0)}


@shared_task
def batch_process_documents(collection_id):
    return [{'document_id': str(doc.id), 'task_id': str(process_document_async.delay(str(doc.id)).id)}
            for doc in Document.objects.filter(collection_id=collection_id, status='pending')]


@shared_task
def delete_document_vectors(document_id):
    document = Document.objects.select_related('collection__vector_store').get(id=document_id)
    from django.db import transaction
    with transaction.atomic():
        DocumentCollection.objects.select_for_update().get(id=document.collection_id)
        if Document.objects.get(id=document_id).status == 'processing':
            raise ValueError('文档正在处理中，请稍后重试。')
        count = document.chunks.count()
        RAGService(document.collection).delete_vectors(list(document.chunks.exclude(embedding=[]).values_list('vector_id', flat=True)))
        document.chunks.all().delete()
        Document.objects.filter(id=document_id).update(status='pending', chunk_count=0, token_count=0, processed_at=None)
        refresh_collection_stats(document.collection_id)
    return {'document_id': str(document_id), 'chunks_deleted': count}


@shared_task
def rebuild_collection_index(collection_id):
    collection = DocumentCollection.objects.get(id=collection_id)
    processor = DocumentProcessor(collection)
    results = [processor.process_document(doc) for doc in collection.documents.all()]
    return {'collection_id': str(collection_id), 'documents': len(results),
            'completed': sum(r['success'] for r in results), 'results': results}


@shared_task
def cleanup_failed_documents(days=7):
    failed = Document.objects.filter(status='failed', updated_at__lt=timezone.now() - timedelta(days=days))
    count = failed.count()
    failed.delete()
    return count


@shared_task
def update_collection_stats():
    ids = list(DocumentCollection.objects.values_list('id', flat=True))
    for collection_id in ids:
        refresh_collection_stats(collection_id)
    return len(ids)
