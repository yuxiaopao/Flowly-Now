"""
Seed demo data for user-facing modules: marketplace templates, integrations,
prompt library, billing price tiers, and test-user owned content.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --email nlwftest@flowly.test
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from pathlib import Path

from billing.models import (
    BillingCycle,
    DEFAULT_PLAN_LIMITS,
    PlanType,
    PriceTier,
    Subscription,
    SubscriptionStatus,
)
from integrations.models import Integration, IntegrationTemplate
from prompts.models import PromptCategory, PromptTemplate
from training.models import TrainingJob, Dataset as TrainingDataset
from training.serializers import _get_user_tenant
from datasets.models import Dataset as ManagedDataset
from augmentation.models import AugmentationJob
from workflows.models import TemplateCategory, WorkflowTemplate
from rag.models import VectorStore
from gateway.models import ModelProvider, AIModel

User = get_user_model()

SAMPLE_WORKFLOW = {
    "nodes": [
        {
            "id": "trigger_1",
            "type": "trigger",
            "position": {"x": 80, "y": 200},
            "data": {"name": "trigger", "label": "手动触发"},
        },
        {
            "id": "llm_1",
            "type": "llm",
            "position": {"x": 320, "y": 200},
            "data": {
                "name": "llm",
                "label": "LLM 处理",
                "inputs": {
                    "prompt": {
                        "type": "expression",
                        "value": "{{ trigger_1.input }}",
                    }
                },
            },
        },
        {
            "id": "output_1",
            "type": "output",
            "position": {"x": 560, "y": 200},
            "data": {"name": "output", "label": "输出结果"},
        },
    ],
    "edges": [
        {"id": "e1", "source": "trigger_1", "target": "llm_1"},
        {"id": "e2", "source": "llm_1", "target": "output_1"},
    ],
}

PLAN_PRICES = {
    (PlanType.FREE, BillingCycle.MONTHLY): Decimal("0"),
    (PlanType.FREE, BillingCycle.YEARLY): Decimal("0"),
    (PlanType.STARTER, BillingCycle.MONTHLY): Decimal("99"),
    (PlanType.STARTER, BillingCycle.YEARLY): Decimal("990"),
    (PlanType.PROFESSIONAL, BillingCycle.MONTHLY): Decimal("299"),
    (PlanType.PROFESSIONAL, BillingCycle.YEARLY): Decimal("2990"),
    (PlanType.ENTERPRISE, BillingCycle.MONTHLY): Decimal("999"),
    (PlanType.ENTERPRISE, BillingCycle.YEARLY): Decimal("9990"),
}


class Command(BaseCommand):
    help = "Seed demo data for marketplace, integrations, prompts, and billing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="nlwftest@flowly.test",
            help="Test user email for owned templates/prompts",
        )

    def handle(self, *args, **options):
        email = options["email"]
        owner = User.objects.filter(email=email).first()
        if not owner:
            owner = User.objects.filter(is_superuser=True).first()
        if not owner:
            self.stdout.write(
                self.style.WARNING(
                    f"No user found for {email}; skipping user-owned demo content"
                )
            )

        with transaction.atomic():
            price_count = self._seed_price_tiers()
            integration_count = self._seed_integration_templates()
            category_count, template_count = self._seed_marketplace_templates(owner)
            prompt_category_count, prompt_count = self._seed_prompt_templates(owner)
            yolo_count = self._seed_yolo_demo_runs(owner) if owner else 0
            dataset_count = self._seed_demo_datasets(owner) if owner else 0
            augmentation_count = self._seed_augmentation_jobs(owner) if owner else 0
            vector_count = self._seed_vector_store(owner) if owner else 0
            gateway_model_count = self._seed_gateway_models()
            if owner:
                self._ensure_test_subscription(owner)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data seeded: "
                f"{price_count} price tiers, "
                f"{integration_count} integrations, "
                f"{category_count} template categories, "
                f"{template_count} workflow templates, "
                f"{prompt_category_count} prompt categories, "
                f"{prompt_count} prompts, "
                f"{yolo_count} yolo runs, "
                f"{dataset_count} datasets, "
                f"{augmentation_count} augmentation jobs, "
                f"{vector_count} vector stores, "
                f"{gateway_model_count} gateway models"
            )
        )

    def _seed_price_tiers(self):
        created = 0
        for plan_type, limits in DEFAULT_PLAN_LIMITS.items():
            for billing_cycle in (BillingCycle.MONTHLY, BillingCycle.YEARLY):
                price = PLAN_PRICES.get((plan_type, billing_cycle), Decimal("0"))
                _, was_created = PriceTier.objects.update_or_create(
                    plan_type=plan_type,
                    billing_cycle=billing_cycle,
                    defaults={
                        "price": price,
                        "currency": "CNY",
                        "max_workflows": limits["max_workflows"],
                        "max_executions_per_month": limits["max_executions_per_month"],
                        "max_team_members": limits["max_team_members"],
                        "max_storage_gb": limits["max_storage_gb"],
                        "max_api_calls_per_month": limits["max_api_calls_per_month"],
                        "max_agents": limits["max_agents"],
                        "enable_api_access": True,
                        "enable_webhooks": plan_type != PlanType.FREE,
                        "enable_advanced_nodes": plan_type
                        in (PlanType.PROFESSIONAL, PlanType.ENTERPRISE),
                        "enable_version_history": plan_type
                        in (PlanType.PROFESSIONAL, PlanType.ENTERPRISE),
                        "enable_priority_support": plan_type == PlanType.ENTERPRISE,
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
        return PriceTier.objects.filter(is_active=True).count()

    def _seed_integration_templates(self):
        templates = [
            {
                "name": "Zapier 自动化",
                "description": "将 Flowly 工作流与 Zapier 连接，触发数千种第三方应用。",
                "integration_type": Integration.IntegrationType.ZAPIER,
                "category": "automation",
                "icon": "zap",
                "color": "#ff4a00",
                "is_featured": True,
                "config_template": {"api_key": "", "webhook_url": ""},
                "required_config": ["api_key"],
                "trigger_events": ["workflow.completed", "execution.failed"],
                "supported_actions": ["trigger_workflow", "send_notification"],
            },
            {
                "name": "Make (Integromat)",
                "description": "可视化自动化平台，编排跨系统业务流程。",
                "integration_type": Integration.IntegrationType.MAKE,
                "category": "automation",
                "icon": "workflow",
                "color": "#6366f1",
                "is_featured": True,
                "config_template": {"scenario_id": "", "api_token": ""},
                "required_config": ["api_token"],
                "trigger_events": ["workflow.started", "workflow.completed"],
                "supported_actions": ["run_scenario", "sync_data"],
            },
            {
                "name": "n8n 自托管",
                "description": "连接自托管 n8n 实例，实现开源工作流编排。",
                "integration_type": Integration.IntegrationType.n8n,
                "category": "automation",
                "icon": "git-branch",
                "color": "#ea580c",
                "is_featured": True,
                "config_template": {"base_url": "", "api_key": ""},
                "required_config": ["base_url", "api_key"],
                "trigger_events": ["execution.completed"],
                "supported_actions": ["execute_workflow"],
            },
            {
                "name": "Microsoft Power Automate",
                "description": "与 Microsoft 365 生态集成，自动化办公流程。",
                "integration_type": Integration.IntegrationType.POWERAUTOMATE,
                "category": "automation",
                "icon": "cloud",
                "color": "#0078d4",
                "is_featured": False,
                "config_template": {"tenant_id": "", "flow_id": ""},
                "required_config": ["tenant_id"],
                "trigger_events": ["workflow.completed"],
                "supported_actions": ["trigger_flow"],
            },
            {
                "name": "Slack 通知",
                "description": "工作流执行完成后向 Slack 频道发送通知。",
                "integration_type": Integration.IntegrationType.CUSTOM,
                "category": "communication",
                "icon": "message-square",
                "color": "#4a154b",
                "is_featured": True,
                "config_template": {"webhook_url": "", "channel": "#general"},
                "required_config": ["webhook_url"],
                "trigger_events": ["execution.completed", "execution.failed"],
                "supported_actions": ["send_message"],
            },
            {
                "name": "Webhook 自定义集成",
                "description": "通过 HTTP Webhook 与任意外部系统对接。",
                "integration_type": Integration.IntegrationType.CUSTOM,
                "category": "data",
                "icon": "link",
                "color": "#10b981",
                "is_featured": False,
                "config_template": {"url": "", "method": "POST", "headers": {}},
                "required_config": ["url"],
                "trigger_events": ["workflow.started", "workflow.completed"],
                "supported_actions": ["http_request"],
            },
        ]

        for index, item in enumerate(templates, start=1):
            IntegrationTemplate.objects.update_or_create(
                name=item["name"],
                defaults={
                    **item,
                    "usage_count": 100 - index * 5,
                    "is_active": True,
                    "setup_guide": f"按照文档配置 {item['name']} 即可开始使用。",
                },
            )
        return IntegrationTemplate.objects.filter(is_active=True).count()

    def _seed_marketplace_templates(self, owner):
        categories = [
            {
                "slug": "ai-agent",
                "name": "AI Agent",
                "description": "自主执行复杂任务的 AI Agent 模板",
                "icon": "bot",
                "color": "#8b5cf6",
                "sort_order": 1,
            },
            {
                "slug": "rag-knowledge",
                "name": "RAG 知识库",
                "description": "基于私有知识库的智能问答",
                "icon": "book-open",
                "color": "#06b6d4",
                "sort_order": 2,
            },
            {
                "slug": "data-pipeline",
                "name": "数据处理",
                "description": "ETL 数据采集、清洗与转换",
                "icon": "database",
                "color": "#10b981",
                "sort_order": 3,
            },
            {
                "slug": "office-automation",
                "name": "办公自动化",
                "description": "文档处理、邮件自动化等办公场景",
                "icon": "file-text",
                "color": "#6366f1",
                "sort_order": 4,
            },
        ]

        category_map = {}
        for cat in categories:
            obj, _ = TemplateCategory.objects.update_or_create(
                slug=cat["slug"],
                defaults=cat,
            )
            category_map[cat["slug"]] = obj

        if not owner:
            return len(category_map), 0

        public_templates = [
            {
                "name": "LLM 文本翻译",
                "description": "输入文本，自动翻译为目标语言并输出结果。",
                "category": category_map["office-automation"],
                "tags": ["翻译", "LLM", "入门"],
                "difficulty": "beginner",
                "use_count": 128,
                "rating": 4.8,
                "rating_count": 42,
                "is_verified": True,
                "is_featured": True,
            },
            {
                "name": "RAG 知识库问答",
                "description": "检索私有文档并生成精准回答，适用于企业知识库。",
                "category": category_map["rag-knowledge"],
                "tags": ["RAG", "知识库", "问答"],
                "difficulty": "intermediate",
                "use_count": 96,
                "rating": 4.65,
                "rating_count": 31,
                "is_verified": True,
                "is_featured": True,
            },
            {
                "name": "数据 ETL 管道",
                "description": "从 API 拉取数据、清洗转换并写入目标存储。",
                "category": category_map["data-pipeline"],
                "tags": ["ETL", "数据", "自动化"],
                "difficulty": "intermediate",
                "use_count": 74,
                "rating": 4.5,
                "rating_count": 18,
                "is_verified": False,
                "is_featured": False,
            },
            {
                "name": "AI Agent 任务执行",
                "description": "带工具调用的自主 Agent，完成多步骤任务。",
                "category": category_map["ai-agent"],
                "tags": ["Agent", "工具调用", "进阶"],
                "difficulty": "advanced",
                "use_count": 112,
                "rating": 4.9,
                "rating_count": 55,
                "is_verified": True,
                "is_featured": True,
            },
        ]

        for item in public_templates:
            WorkflowTemplate.objects.update_or_create(
                name=item["name"],
                created_by=owner,
                defaults={
                    "description": item["description"],
                    "category": item["category"],
                    "tags": item["tags"],
                    "workflow_data": SAMPLE_WORKFLOW,
                    "difficulty": item["difficulty"],
                    "estimated_duration": "5-10 分钟",
                    "use_count": item["use_count"],
                    "rating": item["rating"],
                    "rating_count": item["rating_count"],
                    "is_verified": item["is_verified"],
                    "is_featured": item["is_featured"],
                    "is_active": True,
                    "is_public": True,
                },
            )

        private_templates = [
            {
                "name": "我的客服回复模板",
                "description": "团队内部使用的客服自动回复工作流。",
                "category": category_map["office-automation"],
                "tags": ["私有", "客服"],
                "difficulty": "beginner",
            },
            {
                "name": "周报生成器",
                "description": "汇总本周数据并生成 Markdown 周报。",
                "category": category_map["data-pipeline"],
                "tags": ["私有", "报告"],
                "difficulty": "beginner",
            },
        ]

        for item in private_templates:
            WorkflowTemplate.objects.update_or_create(
                name=item["name"],
                created_by=owner,
                defaults={
                    "description": item["description"],
                    "category": item["category"],
                    "tags": item["tags"],
                    "workflow_data": SAMPLE_WORKFLOW,
                    "difficulty": item["difficulty"],
                    "use_count": 5,
                    "is_active": True,
                    "is_public": False,
                },
            )

        return len(category_map), WorkflowTemplate.objects.filter(is_active=True).count()

    def _seed_prompt_templates(self, owner):
        categories = [
            {
                "slug": "writing",
                "name": "写作助手",
                "description": "文案、邮件、报告等写作场景",
                "icon": "pen-tool",
                "color": "#8b5cf6",
            },
            {
                "slug": "coding",
                "name": "代码助手",
                "description": "代码生成、审查与重构",
                "icon": "code",
                "color": "#06b6d4",
            },
            {
                "slug": "analysis",
                "name": "分析推理",
                "description": "数据分析与逻辑推理",
                "icon": "bar-chart",
                "color": "#f59e0b",
            },
        ]

        category_map = {}
        for cat in categories:
            obj, _ = PromptCategory.objects.update_or_create(
                slug=cat["slug"],
                defaults=cat,
            )
            category_map[cat["slug"]] = obj

        if not owner:
            return len(category_map), 0

        prompts = [
            {
                "name": "专业邮件撰写",
                "description": "根据要点生成专业商务邮件",
                "category": category_map["writing"],
                "prompt_type": "task",
                "template": (
                    "请根据以下要点撰写一封{{ tone }}语气的商务邮件：\n"
                    "收件人：{{ recipient }}\n"
                    "主题：{{ subject }}\n"
                    "要点：{{ points }}"
                ),
                "variables": [
                    {"name": "tone", "type": "string", "default": "正式"},
                    {"name": "recipient", "type": "string"},
                    {"name": "subject", "type": "string"},
                    {"name": "points", "type": "string"},
                ],
                "is_public": True,
                "is_featured": True,
                "use_count": 86,
            },
            {
                "name": "代码审查助手",
                "description": "审查代码质量、安全与性能问题",
                "category": category_map["coding"],
                "prompt_type": "system",
                "template": (
                    "你是一位资深工程师。请审查以下 {{ language }} 代码，"
                    "从可读性、性能、安全三方面给出建议：\n```\n{{ code }}\n```"
                ),
                "variables": [
                    {"name": "language", "type": "string"},
                    {"name": "code", "type": "string"},
                ],
                "is_public": True,
                "is_featured": True,
                "use_count": 64,
            },
            {
                "name": "数据分析摘要",
                "description": "将原始数据转化为结构化分析摘要",
                "category": category_map["analysis"],
                "prompt_type": "task",
                "template": (
                    "分析以下数据并输出：关键发现、趋势、异常值、行动建议。\n"
                    "数据：{{ data }}"
                ),
                "variables": [{"name": "data", "type": "string"}],
                "is_public": True,
                "is_featured": False,
                "use_count": 41,
            },
            {
                "name": "我的周报 Prompt",
                "description": "团队内部周报生成模板",
                "category": category_map["writing"],
                "prompt_type": "task",
                "template": "生成本周工作总结，包含：完成事项、阻塞问题、下周计划。\n输入：{{ notes }}",
                "variables": [{"name": "notes", "type": "string"}],
                "is_public": False,
                "is_featured": False,
                "use_count": 12,
            },
        ]

        for item in prompts:
            PromptTemplate.objects.update_or_create(
                name=item["name"],
                created_by=owner,
                defaults={
                    "description": item["description"],
                    "category": item["category"],
                    "prompt_type": item["prompt_type"],
                    "template": item["template"],
                    "variables": item["variables"],
                    "is_public": item["is_public"],
                    "is_featured": item["is_featured"],
                    "use_count": item["use_count"],
                    "is_active": True,
                },
            )

        return len(category_map), PromptTemplate.objects.filter(is_active=True).count()

    def _seed_yolo_demo_runs(self, owner):
        """Seed demo YOLO training jobs for the smoke test user."""
        tenant = _get_user_tenant(owner)
        now = timezone.now()

        def _loss_series(n, start, end):
            step = (end - start) / max(n - 1, 1)
            return [round(start + step * i, 4) for i in range(n)]

        def _metric_series(n, start, end):
            step = (end - start) / max(n - 1, 1)
            return [round(start + step * i, 4) for i in range(n)]

        demos = [
            {
                "name": "演示：交通标志检测",
                "status": "completed",
                "progress": 100,
                "current_epoch": 100,
                "total_epochs": 100,
                "best_epoch": 87,
                "best_fitness": 0.8234,
                "yolo_version": "v8",
                "model_variant": "n",
                "dataset_yaml_path": "demo/datasets/traffic_signs/data.yaml",
                "class_names": ["stop", "yield", "speed_limit"],
                "best_weight_path": "demo/weights/traffic_signs_best.pt",
                "loss_box_history": _loss_series(100, 1.2, 0.18),
                "loss_cls_history": _loss_series(100, 0.9, 0.12),
                "loss_dfl_history": _loss_series(100, 1.1, 0.15),
                "precision_history": _metric_series(100, 0.45, 0.91),
                "recall_history": _metric_series(100, 0.42, 0.88),
                "map50_history": _metric_series(100, 0.38, 0.82),
                "map50_95_history": _metric_series(100, 0.22, 0.61),
                "started_at": now - timedelta(hours=6),
                "completed_at": now - timedelta(hours=2),
            },
            {
                "name": "演示：工件缺陷检测",
                "status": "running",
                "progress": 45,
                "current_epoch": 45,
                "total_epochs": 100,
                "best_epoch": 42,
                "best_fitness": 0.7156,
                "yolo_version": "v11",
                "model_variant": "s",
                "dataset_yaml_path": "demo/datasets/defect_detection/data.yaml",
                "class_names": ["scratch", "dent", "crack"],
                "loss_box_history": _loss_series(45, 1.4, 0.35),
                "loss_cls_history": _loss_series(45, 1.0, 0.22),
                "loss_dfl_history": _loss_series(45, 1.2, 0.28),
                "precision_history": _metric_series(45, 0.35, 0.78),
                "recall_history": _metric_series(45, 0.32, 0.74),
                "map50_history": _metric_series(45, 0.28, 0.72),
                "map50_95_history": _metric_series(45, 0.15, 0.52),
                "eta_seconds": 4020,
                "started_at": now - timedelta(hours=1),
                "completed_at": None,
            },
            {
                "name": "演示：行人检测（失败样例）",
                "status": "failed",
                "progress": 12,
                "current_epoch": 12,
                "total_epochs": 100,
                "best_epoch": 8,
                "best_fitness": 0.2145,
                "yolo_version": "v8",
                "model_variant": "m",
                "dataset_yaml_path": "demo/datasets/pedestrian/data.yaml",
                "class_names": ["person"],
                "error_message": "GPU 内存不足：训练在第 12 轮中断",
                "loss_box_history": _loss_series(12, 1.5, 1.1),
                "loss_cls_history": _loss_series(12, 1.1, 0.85),
                "loss_dfl_history": _loss_series(12, 1.3, 0.95),
                "precision_history": _metric_series(12, 0.2, 0.35),
                "recall_history": _metric_series(12, 0.18, 0.31),
                "map50_history": _metric_series(12, 0.12, 0.21),
                "map50_95_history": _metric_series(12, 0.06, 0.11),
                "started_at": now - timedelta(days=1),
                "completed_at": now - timedelta(days=1) + timedelta(minutes=18),
            },
        ]

        for item in demos:
            TrainingJob.objects.update_or_create(
                name=item["name"],
                created_by=owner,
                training_kind="yolo",
                defaults={
                    "tenant": tenant,
                    "status": item["status"],
                    "progress": item["progress"],
                    "current_epoch": item["current_epoch"],
                    "total_epochs": item["total_epochs"],
                    "best_epoch": item["best_epoch"],
                    "best_fitness": item["best_fitness"],
                    "framework": "ultralytics",
                    "model_type": "detection",
                    "yolo_version": item["yolo_version"],
                    "model_variant": item["model_variant"],
                    "dataset_yaml_path": item["dataset_yaml_path"],
                    "class_names": item["class_names"],
                    "best_weight_path": item.get("best_weight_path", ""),
                    "error_message": item.get("error_message", ""),
                    "loss_box_history": item["loss_box_history"],
                    "loss_cls_history": item["loss_cls_history"],
                    "loss_dfl_history": item["loss_dfl_history"],
                    "precision_history": item["precision_history"],
                    "recall_history": item["recall_history"],
                    "map50_history": item["map50_history"],
                    "map50_95_history": item["map50_95_history"],
                    "eta_seconds": item.get("eta_seconds", 0),
                    "started_at": item.get("started_at"),
                    "completed_at": item.get("completed_at"),
                    "gpu_info": {"name": "NVIDIA RTX 4090 (demo)", "memory_total_mb": 24576},
                },
            )

        return TrainingJob.objects.filter(
            created_by=owner,
            training_kind="yolo",
        ).count()

    def _seed_demo_datasets(self, owner):
        """Seed demo training datasets for the smoke test user."""
        tenant = _get_user_tenant(owner)
        demo_dir = Path(settings.BASE_DIR) / "data" / "demo" / "datasets"
        demos = [
            {
                "name": "演示：客户流失预测",
                "description": "含客户特征与流失标签的 CSV 训练集",
                "file_path": str(demo_dir / "churn_prediction.csv"),
                "format": "csv",
                "size": 245760,
                "row_count": 10,
                "columns": ["customer_id", "tenure", "monthly_charges", "churn"],
            },
            {
                "name": "演示：产品评论情感",
                "description": "电商评论文本与情感标签 JSON 数据集",
                "file_path": str(demo_dir / "product_reviews.json"),
                "format": "json",
                "size": 512000,
                "row_count": 8,
                "columns": ["review_id", "text", "rating", "sentiment"],
            },
        ]

        for item in demos:
            if not Path(item["file_path"]).exists():
                continue
            TrainingDataset.objects.update_or_create(
                name=item["name"],
                created_by=owner,
                defaults={
                    "tenant": tenant,
                    "description": item["description"],
                    "file_path": item["file_path"],
                    "format": item["format"],
                    "size": item["size"],
                    "row_count": item["row_count"],
                    "columns": item["columns"],
                },
            )

        return TrainingDataset.objects.filter(created_by=owner).count()

    def _seed_augmentation_jobs(self, owner):
        """Seed demo augmentation jobs (datasets app + augmentation app)."""
        tenant = _get_user_tenant(owner)
        demo_dir = Path(settings.BASE_DIR) / "data" / "demo" / "datasets"
        now = timezone.now()

        input_dataset, _ = ManagedDataset.objects.update_or_create(
            name="演示：分类训练样本",
            created_by=owner,
            defaults={
                "tenant": tenant,
                "description": "数据增强模块演示用输入数据集",
                "source": "upload",
                "file_path": str(demo_dir / "churn_prediction.csv"),
                "format": "csv",
                "size_bytes": 245760,
                "row_count": 100,
                "column_count": 4,
                "columns": [
                    {"name": "customer_id", "type": "string"},
                    {"name": "tenure", "type": "number"},
                    {"name": "monthly_charges", "type": "number"},
                    {"name": "churn", "type": "number"},
                ],
                "status": "ready",
            },
        )

        output_dataset, _ = ManagedDataset.objects.update_or_create(
            name="演示：增强后样本集",
            created_by=owner,
            defaults={
                "tenant": tenant,
                "description": "几何增强输出数据集（演示）",
                "source": "upload",
                "file_path": str(demo_dir / "product_reviews.json"),
                "format": "json",
                "size_bytes": 512000,
                "row_count": 200,
                "column_count": 4,
                "status": "ready",
            },
        )

        jobs = [
            {
                "name_key": "演示：几何增强",
                "strategy": "geometric",
                "status": "completed",
                "progress": 100,
                "ratio": 2.0,
                "original_count": 100,
                "augmented_count": 200,
                "output_dataset": output_dataset,
                "started_at": now - timedelta(hours=3),
                "completed_at": now - timedelta(hours=2),
            },
            {
                "name_key": "演示：颜色增强",
                "strategy": "color",
                "status": "running",
                "progress": 62,
                "ratio": 3.0,
                "original_count": 100,
                "augmented_count": 186,
                "output_dataset": None,
                "started_at": now - timedelta(minutes=25),
                "completed_at": None,
            },
            {
                "name_key": "演示：噪声注入",
                "strategy": "noise",
                "status": "failed",
                "progress": 18,
                "ratio": 1.5,
                "original_count": 100,
                "augmented_count": 0,
                "output_dataset": None,
                "error_message": "演示：增强进程因磁盘空间不足中断",
                "started_at": now - timedelta(days=1),
                "completed_at": now - timedelta(days=1) + timedelta(minutes=12),
            },
        ]

        for item in jobs:
            AugmentationJob.objects.update_or_create(
                input_dataset=input_dataset,
                strategy=item["strategy"],
                created_by=owner,
                defaults={
                    "tenant": tenant,
                    "status": item["status"],
                    "progress": item["progress"],
                    "ratio": item["ratio"],
                    "original_count": item["original_count"],
                    "augmented_count": item["augmented_count"],
                    "output_dataset": item.get("output_dataset"),
                    "output_name": item["name_key"],
                    "error_message": item.get("error_message", ""),
                    "transformations": [{"type": item["strategy"], "enabled": True}],
                    "started_at": item.get("started_at"),
                    "completed_at": item.get("completed_at"),
                },
            )

        return AugmentationJob.objects.filter(created_by=owner).count()

    def _seed_vector_store(self, owner):
        """Ensure test user has a default vector store for RAG collections."""
        store, _ = VectorStore.objects.update_or_create(
            owner=owner,
            name="演示向量存储",
            defaults={
                "store_type": "chroma",
                "host": "127.0.0.1",
                "port": 8000,
                "collection": "flowly_demo",
                "dimension": 1536,
                "metric": "cosine",
                "is_default": True,
                "path": str(Path(settings.BASE_DIR) / "data" / "demo" / "vector_store"),
            },
        )
        VectorStore.objects.filter(owner=owner).exclude(id=store.id).update(is_default=False)
        return VectorStore.objects.filter(owner=owner).count()

    def _seed_gateway_models(self):
        """Seed at least one chat model for gateway / NL E2E."""
        ollama_model = getattr(settings, "OLLAMA_MODEL", "qwen2.5-coder:7b")
        provider, _ = ModelProvider.objects.update_or_create(
            slug="ollama",
            defaults={
                "name": "Ollama",
                "description": "Local Ollama models for dev/E2E",
                "is_active": True,
            },
        )
        AIModel.objects.filter(provider=provider, is_default=True).update(is_default=False)
        model, _ = AIModel.objects.update_or_create(
            provider=provider,
            model_id=ollama_model,
            defaults={
                "name": ollama_model,
                "model_type": "chat",
                "max_tokens": 4096,
                "supports_streaming": True,
                "is_active": True,
                "is_default": True,
                "context_window": 8192,
            },
        )
        return AIModel.objects.filter(is_active=True).count()

    def _ensure_test_subscription(self, user):
        Subscription.objects.get_or_create(
            user=user,
            defaults={
                "plan_type": PlanType.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "current_period_start": timezone.now(),
                "current_period_end": timezone.now() + timedelta(days=365),
            },
        )
