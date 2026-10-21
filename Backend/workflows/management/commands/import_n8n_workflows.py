"""
Batch import n8n workflow JSON files into Flowly.

Usage:
  python manage.py import_n8n_workflows --root /path/to/n8n-workflows/workflows --user nlwftest@flowly.test
  python manage.py import_n8n_workflows --root ... --limit 50 --dry-run
"""

from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from workflows.models import Workflow
from workflows.serializers import WorkflowCreateSerializer
from workflows.services.n8n_import import convert_n8n_file, is_n8n_workflow


class Command(BaseCommand):
    help = 'Import n8n workflow JSON exports into Flowly workflows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--root',
            type=str,
            required=True,
            help='Root directory containing n8n workflow JSON files',
        )
        parser.add_argument(
            '--user',
            type=str,
            default='nlwftest@flowly.test',
            help='Owner email/username for imported workflows',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Max files to import (0 = all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Convert only, do not persist',
        )
        parser.add_argument(
            '--report',
            type=str,
            default='',
            help='Write JSON report to this path',
        )
        parser.add_argument(
            '--purge-n8n',
            action='store_true',
            help='Delete existing [n8n] tagged workflows for user before import',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip if workflow with same name already exists for user',
        )

    def handle(self, *args, **options):
        root = Path(options['root']).expanduser().resolve()
        if not root.is_dir():
            raise CommandError(f'Root not found: {root}')

        User = get_user_model()
        user = User.objects.filter(email=options['user']).first() or User.objects.filter(
            username=options['user']
        ).first()
        if not user:
            raise CommandError(f'User not found: {options["user"]}')

        files = sorted(root.rglob('*.json'))
        if options['limit'] and options['limit'] > 0:
            files = files[: options['limit']]

        self.stdout.write(f'Found {len(files)} JSON files under {root}')

        report = {
            'total': len(files),
            'imported': 0,
            'skipped_existing': 0,
            'failed': 0,
            'dry_run': bool(options['dry_run']),
            'items': [],
        }

        if options.get('purge_n8n'):
            qs = Workflow.objects.filter(owner=user, name__startswith='[n8n]')
            deleted, _ = qs.delete()
            self.stdout.write(self.style.WARNING(f'Purged {deleted} existing [n8n] workflows'))

        existing_names = set(
            Workflow.objects.filter(owner=user, name__startswith='[n8n]').values_list('name', flat=True)
        )

        for path in files:
            item = {'path': str(path), 'status': 'pending'}
            try:
                payload = convert_n8n_file(path)
                item['name'] = payload['name']
                item['nodes'] = len(payload.get('nodes') or [])
                item['edges'] = len(payload.get('edges') or [])
                item['unmapped'] = payload.get('meta', {}).get('unmapped_nodes', 0)

                if options.get('skip_existing') and payload['name'] in existing_names:
                    item['status'] = 'skipped_existing'
                    report['skipped_existing'] += 1
                    report['items'].append(item)
                    continue

                if options['dry_run']:
                    item['status'] = 'dry_run_ok'
                    report['imported'] += 1
                    report['items'].append(item)
                    continue

                with transaction.atomic():
                    serializer = WorkflowCreateSerializer(data=payload)
                    serializer.is_valid(raise_exception=True)
                    wf = serializer.save(owner=user)
                    item['workflow_id'] = str(wf.id)
                    item['status'] = 'imported'
                    existing_names.add(payload['name'])
                    report['imported'] += 1
            except Exception as exc:
                item['status'] = 'failed'
                item['error'] = str(exc)[:500]
                report['failed'] += 1
            report['items'].append(item)

        summary = (
            f"Done: imported={report['imported']} failed={report['failed']} "
            f"skipped={report['skipped_existing']} dry_run={report['dry_run']}"
        )
        self.stdout.write(self.style.SUCCESS(summary))

        if options['report']:
            out = Path(options['report'])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            self.stdout.write(f'Report written: {out}')
