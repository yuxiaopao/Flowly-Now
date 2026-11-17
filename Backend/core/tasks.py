"""Scheduled personal backups; each policy is independently locked and committed."""

import logging

from celery import shared_task
from django.utils import timezone

from core.models.audit import PersonalBackupPolicy, DataRestoreOperation
from core.services.personal_backups import run_one_backup, record_backup_failure

logger = logging.getLogger(__name__)


@shared_task
def run_due_personal_backups():
    now = timezone.now()
    policy_ids = list(PersonalBackupPolicy.objects.filter(
        enabled=True, next_run_at__lte=now,
    ).values_list('id', flat=True))
    result = {'completed': 0, 'failed': 0}
    for policy_id in policy_ids:
        try:
            if run_one_backup(policy_id, now):
                result['completed'] += 1
        except PersonalBackupPolicy.DoesNotExist:
            continue
        except Exception:
            logger.exception('Personal backup failed for policy %s', policy_id)
            record_backup_failure(policy_id, now)
            result['failed'] += 1
    DataRestoreOperation.objects.filter(expires_at__lt=now, completed_at__isnull=True).delete()
    return result
