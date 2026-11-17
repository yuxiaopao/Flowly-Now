"""Release definitions cannot be changed through model save/delete entrypoints."""
from config.application_messages import MESSAGES
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver
from workflows.models import Workflow, Node, Edge


@receiver(pre_save, sender=Workflow)
@receiver(pre_delete, sender=Workflow)
def protect_workflow_snapshot(sender, instance, **kwargs):
    if instance.pk and Workflow.all_objects.filter(pk=instance.pk, is_release_snapshot=True).exists():
        raise ValidationError(MESSAGES['immutable_snapshot'])


@receiver(pre_save, sender=Node)
@receiver(pre_delete, sender=Node)
@receiver(pre_save, sender=Edge)
@receiver(pre_delete, sender=Edge)
def protect_snapshot_graph(sender, instance, **kwargs):
    if Workflow.all_objects.filter(pk=instance.workflow_id, is_release_snapshot=True).exists():
        raise ValidationError(MESSAGES['immutable_snapshot'])
