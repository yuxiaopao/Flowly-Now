"""
Mark stale workflow executions as failed or cancelled.

Useful after smoke tests or worker crashes leave executions stuck in running/pending.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from workflows.models import WorkflowExecution


class Command(BaseCommand):
    help = 'Mark stale pending/running workflow executions as failed or cancelled'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Treat executions older than this many hours as stale (default: 1)',
        )
        parser.add_argument(
            '--status',
            choices=['failed', 'cancelled'],
            default='failed',
            help='Target status for stale executions (default: failed)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only print what would be updated',
        )
        parser.add_argument(
            '--user-email',
            type=str,
            default='',
            help='Limit cleanup to executions owned by this user email',
        )
        parser.add_argument(
            '--force-active',
            action='store_true',
            help='Mark all active executions immediately (requires --user-email; ignores age cutoff)',
        )

    def handle(self, *args, **options):
        hours = max(1, options['hours'])
        target_status = options['status']
        dry_run = options['dry_run']
        user_email = (options['user_email'] or '').strip()
        force_active = options['force_active']

        if force_active and not user_email:
            self.stderr.write(self.style.ERROR('--force-active requires --user-email'))
            return

        cutoff = timezone.now() - timedelta(hours=hours)
        queryset = WorkflowExecution.objects.filter(
            status__in=['pending', 'queued', 'running', 'paused'],
        ).select_related('workflow', 'workflow__owner')

        if user_email:
            queryset = queryset.filter(workflow__owner__email=user_email)

        stale = []
        for execution in queryset:
            if force_active:
                stale.append(execution)
                continue
            reference_time = execution.started_at or execution.queued_at
            if reference_time and reference_time < cutoff:
                stale.append(execution)

        if not stale:
            self.stdout.write(self.style.SUCCESS('No stale executions found.'))
            return

        self.stdout.write(f'Found {len(stale)} stale execution(s) older than {hours}h')

        updated = 0
        for execution in stale:
            label = f'{execution.id} ({execution.workflow.name}) [{execution.status}]'
            if dry_run:
                self.stdout.write(f'  would mark {label} -> {target_status}')
                updated += 1
                continue

            if target_status == 'cancelled':
                execution.cancel()
            else:
                execution.mark_failed(
                    f'Stale execution auto-marked after exceeding {hours}h without completion'
                )
            updated += 1
            self.stdout.write(f'  marked {label} -> {target_status}')

        suffix = ' (dry run)' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(f'Processed {updated} execution(s){suffix}'))
