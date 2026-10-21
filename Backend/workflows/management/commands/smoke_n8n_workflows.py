"""
Smoke-execute imported n8n workflows (structure-only / simple graphs).

Usage:
  python manage.py smoke_n8n_workflows --user nlwftest@flowly.test --limit 30
"""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from workflows.models import Workflow, WorkflowExecution
from workflows.services.workflow_executor import WorkflowExecutor


class Command(BaseCommand):
    help = 'Smoke execute [n8n] imported workflows and write report'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, default='nlwftest@flowly.test')
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--report', type=str, default='/app/data/n8n_smoke_report.json')

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.filter(email=options['user']).first() or User.objects.filter(
            username=options['user']
        ).first()
        if not user:
            raise CommandError(f'User not found: {options["user"]}')

        qs = Workflow.objects.filter(owner=user, name__startswith='[n8n]').order_by('created_at')
        if options['limit']:
            qs = qs[: options['limit']]

        report = {'total': qs.count(), 'passed': 0, 'failed': 0, 'items': []}

        for wf in qs:
            item = {'id': str(wf.id), 'name': wf.name, 'status': 'pending'}
            execution = WorkflowExecution.objects.create(
                workflow=wf,
                status='pending',
                input_data={},
                triggered_by=user,
                trigger_type='manual',
                version=wf.version,
            )
            try:
                executor = WorkflowExecutor(wf, execution)
                executor.execute()
                execution.refresh_from_db()
                item['status'] = 'passed' if execution.status in ('completed', 'success') else 'failed'
                item['execution_status'] = execution.status
                if item['status'] == 'passed':
                    report['passed'] += 1
                else:
                    item['error'] = (execution.error_message or execution.status)[:400]
                    report['failed'] += 1
            except Exception as exc:
                item['status'] = 'failed'
                item['error'] = str(exc)[:400]
                report['failed'] += 1
            report['items'].append(item)

        self.stdout.write(
            self.style.SUCCESS(f"Smoke: passed={report['passed']} failed={report['failed']}")
        )
        if options['report']:
            with open(options['report'], 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
