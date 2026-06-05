"""
Django signals for RAG app.
"""

from django.dispatch import receiver
from django.db.models.signals import post_save


@receiver(post_save, sender='rag.Document')
def document_processed(sender, instance, **kwargs):
    """Handle document processing completion."""
    if instance.status == 'completed' and instance.processed_at:
        # Update collection stats
        from .models import DocumentCollection, Chunk
        
        collection = instance.collection
        collection.document_count = Document.objects.filter(
            collection=collection,
            status='completed'
        ).count()
        collection.chunk_count = Chunk.objects.filter(
            document__collection=collection
        ).count()
        collection.save(update_fields=['document_count', 'chunk_count', 'updated_at'])


def get_channel_layer_safe():
    """Safely get channel layer."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


def notify_collection_progress(collection_id, progress, status):
    """Send progress update for document processing."""
    channel_layer = get_channel_layer_safe()
    if not channel_layer:
        return
    
    from asgiref.sync import async_to_sync
    
    try:
        async_to_sync(channel_layer.group_send)(
            f'collection_{collection_id}',
            {
                'type': 'processing_progress',
                'data': {
                    'collection_id': collection_id,
                    'progress': progress,
                    'status': status
                }
            }
        )
    except Exception:
        pass
