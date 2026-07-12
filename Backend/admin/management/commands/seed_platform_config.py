"""
Seed default platform configuration (legal documents).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from admin.models import LegalDocument


class Command(BaseCommand):
    help = 'Seed default legal documents and platform config'

    def handle(self, *args, **options):
        defaults = [
            {
                'doc_type': 'terms',
                'version': '1.0.0',
                'title': 'Flowly 服务条款',
                'content_html': '<h1>服务条款</h1><p>欢迎使用 Flowly 智能工作流平台。使用本服务即表示您同意遵守相关条款。</p>',
                'is_active': True,
            },
            {
                'doc_type': 'privacy',
                'version': '1.0.0',
                'title': 'Flowly 隐私政策',
                'content_html': '<h1>隐私政策</h1><p>我们重视您的隐私，将按照本政策收集和使用您的个人信息。</p>',
                'is_active': True,
            },
            {
                'doc_type': 'login',
                'version': '1.0.0',
                'title': '登录协议',
                'content_html': '<h1>登录协议</h1><p>登录即表示您确认已阅读并同意相关条款。</p>',
                'is_active': True,
            },
        ]

        for item in defaults:
            doc, created = LegalDocument.objects.update_or_create(
                doc_type=item['doc_type'],
                version=item['version'],
                defaults={
                    'title': item['title'],
                    'content_html': item['content_html'],
                    'is_active': item['is_active'],
                    'require_acceptance': True,
                    'effective_at': timezone.now(),
                },
            )
            action = '创建' if created else '更新'
            self.stdout.write(self.style.SUCCESS(f'{action} {doc}'))

        self.stdout.write(self.style.SUCCESS('平台默认配置种子数据完成'))
