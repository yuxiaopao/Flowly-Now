"""
Index imported [n8n] workflows as Soft RAG training corpus for 语创 (FlowSpeak).

Usage:
  python manage.py index_n8n_training_data
  python manage.py index_n8n_training_data --promote-templates --promote-limit 300
  python manage.py index_n8n_training_data --min-quality 0.3 --report /app/data/n8n_corpus_report.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from nl_to_workflow.n8n_corpus import (
    build_corpus_from_db,
    corpus_stats,
    default_corpus_path,
    promote_entries_to_templates,
    save_corpus,
)


class Command(BaseCommand):
    help = 'Build n8n Soft RAG training corpus for 语创 workflow generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='',
            help='Corpus JSON path (default: Backend/data/n8n_training_corpus.json)',
        )
        parser.add_argument(
            '--min-quality',
            type=float,
            default=0.25,
            help='Minimum quality score to keep (0-1)',
        )
        parser.add_argument(
            '--min-nodes',
            type=int,
            default=2,
            help='Minimum node count to keep',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Max workflows to scan (0 = all)',
        )
        parser.add_argument(
            '--promote-templates',
            action='store_true',
            help='Also promote top entries into WorkflowTemplate (n8n-community)',
        )
        parser.add_argument(
            '--promote-limit',
            type=int,
            default=300,
            help='Max templates to promote',
        )
        parser.add_argument(
            '--user',
            default='',
            help='Owner email/username for promoted templates',
        )
        parser.add_argument(
            '--report',
            default='',
            help='Optional report JSON path',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Build in memory only; do not write corpus file',
        )

    def handle(self, *args, **options):
        limit = options['limit'] or None
        self.stdout.write('Scanning [n8n] workflows...')
        entries = build_corpus_from_db(
            min_quality=float(options['min_quality']),
            min_nodes=int(options['min_nodes']),
            limit=limit,
        )
        self.stdout.write(f'Corpus candidates: {len(entries)}')

        out_path = Path(options['output']) if options['output'] else default_corpus_path()
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f'Dry-run: would write {out_path} ({len(entries)} entries)'))
        else:
            saved = save_corpus(entries, out_path)
            self.stdout.write(self.style.SUCCESS(f'Wrote corpus: {saved}'))

        promote_result = {'created': 0, 'updated': 0, 'skipped': 0}
        if options['promote_templates']:
            user = None
            user_key = (options.get('user') or '').strip()
            if user_key:
                User = get_user_model()
                user = (
                    User.objects.filter(email__iexact=user_key).first()
                    or User.objects.filter(username__iexact=user_key).first()
                )
                if not user:
                    self.stdout.write(self.style.WARNING(f'User not found: {user_key}'))
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING(
                        f'Dry-run: would promote up to {options["promote_limit"]} templates'
                    )
                )
            else:
                promote_result = promote_entries_to_templates(
                    entries,
                    max_promote=int(options['promote_limit']),
                    user=user,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        'Promoted templates: '
                        f"created={promote_result['created']} "
                        f"updated={promote_result['updated']} "
                        f"skipped={promote_result['skipped']}"
                    )
                )

        stats = {
            'corpus_count': len(entries),
            'corpus_path': str(out_path),
            'avg_quality': round(
                sum(e.quality_score for e in entries) / len(entries), 4
            ) if entries else 0.0,
            'top_categories': {},
            'promote': promote_result,
            'dry_run': bool(options['dry_run']),
        }
        for e in entries:
            stats['top_categories'][e.category] = stats['top_categories'].get(e.category, 0) + 1
        stats['top_categories'] = dict(
            sorted(stats['top_categories'].items(), key=lambda kv: -kv[1])[:20]
        )

        if not options['dry_run']:
            stats.update(corpus_stats(out_path))

        report_path = options.get('report') or ''
        if report_path:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(report_path).write_text(
                json.dumps(stats, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            self.stdout.write(f'Report: {report_path}')

        self.stdout.write(self.style.SUCCESS(
            f"Done. corpus={stats['corpus_count']} avg_quality={stats['avg_quality']}"
        ))
