"""Keep admin, cascade and scheduled deletion consistent with API deletion."""
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import Chunk, Document, DocumentCollection
from .mutations import lock_deletion_collections
from .pipeline import RAGService, refresh_collection_stats


@receiver(pre_delete, sender=Document)
def remove_document_index(sender, instance, using, origin=None, **kwargs):
    lock_deletion_collections(origin, instance.collection_id, using=using)
    if Document.objects.filter(pk=instance.pk, status='processing').exists():
        raise ValueError('文档正在处理中，无法删除。')
    RAGService(instance.collection).delete_chunk_vectors(instance.chunks.all())


@receiver(pre_delete, sender=Chunk)
@receiver(pre_delete, sender=DocumentCollection)
def lock_content_deletion(sender, instance, using, origin=None, **kwargs):
    collection_id = instance.pk if sender is DocumentCollection else instance.document.collection_id
    lock_deletion_collections(origin, collection_id, using=using)


@receiver(post_delete, sender=Document)
def update_document_statistics(sender, instance, **kwargs):
    refresh_collection_stats(instance.collection_id)
