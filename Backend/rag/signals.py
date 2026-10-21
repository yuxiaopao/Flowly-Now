"""Keep admin, cascade and scheduled deletion consistent with API deletion."""
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import Document
from .pipeline import RAGService, refresh_collection_stats


@receiver(pre_delete, sender=Document)
def remove_document_index(sender, instance, **kwargs):
    if Document.objects.filter(pk=instance.pk, status='processing').exists():
        raise ValueError('文档正在处理中，无法删除。')
    RAGService(instance.collection).delete_chunk_vectors(instance.chunks.all())


@receiver(post_delete, sender=Document)
def update_document_statistics(sender, instance, **kwargs):
    refresh_collection_stats(instance.collection_id)
