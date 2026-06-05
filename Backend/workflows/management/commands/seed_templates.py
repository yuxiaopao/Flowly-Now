"""
Seed command for template categories.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management.base import BaseCommand
from workflows.models import TemplateCategory


class Command(BaseCommand):
    help = 'Seed template categories'

    def handle(self):
        categories = [
            {
                "name": "文生视频",
                "slug": "video-generation",
                "icon": "Video",
                "color": "#ec4899",
                "description": "从文本描述自动生成视频内容",
                "sort_order": 1,
            },
            {
                "name": "AI Agent",
                "slug": "ai-agent",
                "icon": "Bot",
                "color": "#8b5cf6",
                "description": "自主执行复杂任务的 AI Agent",
                "sort_order": 2,
            },
            {
                "name": "RAG 知识库",
                "slug": "rag-knowledge",
                "icon": "BookOpen",
                "color": "#06b6d4",
                "description": "基于私有知识库的智能问答",
                "sort_order": 3,
            },
            {
                "name": "模型训练",
                "slug": "model-training",
                "icon": "Brain",
                "color": "#f59e0b",
                "description": "端到端的机器学习模型训练与部署",
                "sort_order": 4,
            },
            {
                "name": "数据处理",
                "slug": "data-pipeline",
                "icon": "Database",
                "color": "#10b981",
                "description": "ETL 数据采集、清洗与转换",
                "sort_order": 5,
            },
            {
                "name": "办公自动化",
                "slug": "office-automation",
                "icon": "FileText",
                "color": "#6366f1",
                "description": "文档处理、邮件自动化等办公场景",
                "sort_order": 6,
            },
        ]

        for cat_data in categories:
            obj, created = TemplateCategory.objects.get_or_create(
                slug=cat_data["slug"],
                defaults=cat_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {obj.name}"))
            else:
                self.stdout.write(f"Category already exists: {obj.name}")

        self.stdout.write(self.style.SUCCESS("Template categories seeded successfully!"))
