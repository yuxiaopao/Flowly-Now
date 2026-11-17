"""Persist backup schedules and advance them after successful snapshots."""

from calendar import monthrange
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.data_constants import BACKUP_SCAN_INTERVAL_SECONDS, BACKUP_TASK_NAME, BACKUP_FREQUENCY_DAYS
from core.models.audit import PersonalBackupPolicy
from core.services.personal_exports import create_export

def scheduler_configured():
    return any(entry.get('task') == BACKUP_TASK_NAME for entry in getattr(settings, 'CELERY_BEAT_SCHEDULE', {}).values())


def next_backup_at(frequency, now):
    if frequency == 'monthly':
        month = now.month % 12 + 1
        year = now.year + (now.month == 12)
        return now.replace(year=year, month=month, day=min(now.day, monthrange(year, month)[1]))
    return now + timedelta(days=BACKUP_FREQUENCY_DAYS[frequency])


@transaction.atomic
def save_backup_policy(user, data):
    if data.get('enabled') and not scheduler_configured():
        raise ValidationError('服务端尚未配置备份调度，请先配置并运行 Celery Worker 和 Beat。')
    policy, _ = PersonalBackupPolicy.objects.get_or_create(user=user)
    policy = PersonalBackupPolicy.objects.select_for_update().get(pk=policy.pk)
    changed_schedule = not policy.enabled or data.get('frequency', policy.frequency) != policy.frequency
    for name, value in data.items():
        setattr(policy, name, value)
    if not policy.enabled:
        policy.next_run_at = None
    elif changed_schedule or policy.next_run_at is None:
        policy.next_run_at = next_backup_at(policy.frequency, timezone.now())
    policy.save()
    return policy


@transaction.atomic
def run_one_backup(policy_id, now):
    policy = PersonalBackupPolicy.objects.select_for_update().get(pk=policy_id)
    if not policy.enabled or policy.next_run_at is None or policy.next_run_at > now:
        return False
    create_export(policy.user, {'export_type': 'full', 'format': 'json'}, is_backup=True)
    older = list(policy.user.data_exports.filter(is_backup=True).order_by('-created_at', '-id').values_list('id', flat=True)[policy.keep_count:])
    if older:
        policy.user.data_exports.filter(pk__in=older).delete()
    policy.last_run_at = now
    policy.last_error = ''
    policy.next_run_at = next_backup_at(policy.frequency, now)
    policy.save(update_fields=['last_run_at', 'last_error', 'next_run_at', 'updated_at'])
    return True


@transaction.atomic
def record_backup_failure(policy_id, now):
    policy = PersonalBackupPolicy.objects.select_for_update().filter(pk=policy_id).first()
    if policy and policy.enabled:
        policy.last_error = '备份生成失败，请检查数据大小及服务日志。'
        policy.next_run_at = now + timedelta(seconds=BACKUP_SCAN_INTERVAL_SECONDS)
        policy.save(update_fields=['last_error', 'next_run_at', 'updated_at'])
