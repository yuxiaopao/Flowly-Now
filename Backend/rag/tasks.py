"""
Celery tasks for RAG app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_document_async(document_id):
    """Process a document asynchronously - chunk and embed."""
    from .models import Document, Chunk
    
    try:
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()
        
        # Import document processor
        from rag.services import DocumentProcessor
        
        processor = DocumentProcessor(document.collection)
        chunks = processor.process_document(document)
        
        # Create chunk records
        chunk_count = 0
        for i, chunk_text in enumerate(chunks):
            Chunk.objects.create(
                document=document,
                content=chunk_text,
                chunk_index=i,
                metadata={'source': document.source_url or 'text'}
            )
            chunk_count += 1
        
        # Update document
        document.status = 'completed'
        document.chunk_count = chunk_count
        document.processed_at = timezone.now()
        document.save()
        
        # Update collection stats
        collection = document.collection
        collection.chunk_count = Chunk.objects.filter(document__collection=collection).count()
        collection.document_count = Document.objects.filter(collection=collection, status='completed').count()
        collection.save()
        
        return {
            'document_id': document_id,
            'chunks_created': chunk_count
        }
        
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {e}")
        Document.objects.filter(id=document_id).update(
            status='failed',
            error_message=str(e)
        )
        raise


@shared_task
def batch_process_documents(collection_id):
    """Process all pending documents in a collection."""
    from .models import Document
    
    documents = Document.objects.filter(
        collection_id=collection_id,
        status='pending'
    )
    
    results = []
    for doc in documents:
        try:
            result = process_document_async.delay(doc.id)
            results.append({
                'document_id': doc.id,
                'task_id': result.id
            })
        except Exception as e:
            logger.error(f"Failed to queue document {doc.id}: {e}")
    
    return results


@shared_task
def delete_document_vectors(document_id):
    """Delete document vectors from vector store."""
    from .models import Document, Chunk
    
    try:
        document = Document.objects.get(id=document_id)
        
        # Delete chunks
        chunks = Chunk.objects.filter(document=document)
        chunk_ids = [c.id for c in chunks]
        
        # Delete from vector store
        from rag.services import VectorStoreService
        service = VectorStoreService(document.collection.vector_store)
        
        for chunk in chunks:
            if chunk.vector_id:
                service.delete_vector(chunk.vector_id)
        
        # Delete chunk records
        chunks.delete()
        
        # Update document
        document.chunk_count = 0
        document.vector_ids = []
        document.save()
        
        return {
            'document_id': document_id,
            'chunks_deleted': len(chunk_ids)
        }
        
    except Exception as e:
        logger.error(f"Failed to delete document vectors: {e}")
        raise


@shared_task
def rebuild_collection_index(collection_id):
    """Rebuild the entire collection index."""
    from .models import DocumentCollection, Document, Chunk
    
    try:
        collection = DocumentCollection.objects.get(id=collection_id)
        documents = Document.objects.filter(
            collection=collection,
            status='completed'
        )
        
        total_chunks = 0
        for doc in documents:
            # Re-process each document
            process_document_async.delay(doc.id)
            total_chunks += doc.chunk_count
        
        return {
            'collection_id': collection_id,
            'documents': documents.count(),
            'chunks': total_chunks
        }
        
    except Exception as e:
        logger.error(f"Failed to rebuild collection index: {e}")
        raise


@shared_task
def cleanup_failed_documents(days=7):
    """Clean up documents that failed processing."""
    from .models import Document
    
    cutoff = timezone.now() - timedelta(days=days)
    failed = Document.objects.filter(
        status='failed',
        updated_at__lt=cutoff
    )
    
    count = failed.count()
    failed.delete()
    
    logger.info(f"Cleaned up {count} failed documents")
    return count


@shared_task
def update_collection_stats():
    """Update statistics for all collections."""
    from .models import DocumentCollection, Document, Chunk
    
    collections = DocumentCollection.objects.all()
    
    for collection in collections:
        collection.document_count = Document.objects.filter(
            collection=collection,
            status='completed'
        ).count()
        collection.chunk_count = Chunk.objects.filter(
            document__collection=collection
        ).count()
        collection.save()
    
    return collections.count()
