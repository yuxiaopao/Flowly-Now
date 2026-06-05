# -*- coding: utf-8 -*-
"""
数据库表完整性检测脚本
检查所有核心表是否存在

使用方式:
    cd e:\Flowly-now\Backend
    python scripts/check_database_tables.py
"""

import os
import sys
from typing import Dict, List, Set

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 核心表定义 (模块名 -> 表名列表)
EXPECTED_TABLES: Dict[str, List[str]] = {
    "工作流核心": [
        "workflows",
        "nodes",
        "edges",
        "workflow_executions",
        "node_executions",
        "variables",
        "tools",
        "api_credentials",
        "audit_logs",
        "workflow_webhook_delivery_logs",
    ],
    "Agent": [
        "agents",
        "agent_conversations",
        "agent_messages",
    ],
    "Prompt模板": [
        "prompt_templates",
        "prompt_categories",
        "prompt_usages",
        "prompt_versions",
        "prompt_ratings",
    ],
    "租户": [
        "tenants",
        "tenant_memberships",
        "tenant_invitations",
        "tenant_usage",
    ],
    "监控": [
        "execution_logs",
        "alert_rules",
        "alerts",
        "metrics",
        "notification_channels",
    ],
    "RAG知识库": [
        "vector_stores",
        "document_collections",
        "documents",
        "chunks",
        "rag_pipelines",
    ],
    "网关": [
        "model_providers",
        "ai_models",
        "user_api_keys",
        "api_call_logs",
    ],
    "计费": [
        "price_tiers",
        "subscriptions",
        "payments",
        "invoices",
        "usage_records",
        "coupons",
        "coupon_usages",
    ],
    "集成": [
        "webhooks",
        "webhook_deliveries",
        "integrations",
        "integration_templates",
    ],
    "品牌": [
        "branding_configs",
        "email_templates",
        "custom_domains",
        "theme_presets",
    ],
    "市场": [
        "template_categories",
        "marketplace_workflow_templates",
        "template_installs",
        "template_ratings",
        "template_comments",
        "marketplace_template_favorites",
    ],
    "模板": [
        "workflow_templates",
        "template_versions",
        "template_usages",
    ],
    "NL转工作流": [
        "nl_sessions",
    ],
    "Django认证": [
        "users",
        "groups",
        "permissions",
    ],
    "Django Admin": [
        "django_admin_log",
    ],
}


def get_all_expected_tables() -> Set[str]:
    """获取所有期望的表名"""
    tables = set()
    for module_tables in EXPECTED_TABLES.values():
        tables.update(module_tables)
    return tables


def check_database_tables():
    """检查数据库表"""
    print("="*60)
    print("数据库表完整性检测")
    print("="*60)

    try:
        # 导入 Django
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import django
        django.setup()

        from django.db import connection
        from django.conf import settings

        # 获取数据库配置
        db_config = settings.DATABASES.get('default', {})
        db_engine = db_config.get('ENGINE', '')
        db_name = db_config.get('NAME', '')

        print(f"\n数据库类型: {db_engine}")
        print(f"数据库名称: {db_name}")

        # 根据数据库类型查询表列表
        existing_tables: Set[str] = set()

        if 'mysql' in db_engine.lower():
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            existing_tables = {row[0] for row in cursor.fetchall()}

        elif 'postgresql' in db_engine.lower():
            cursor = connection.cursor()
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}

        elif 'sqlite' in db_engine.lower():
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

        else:
            print(f"\n警告: 不支持的数据库类型: {db_engine}")
            print("尝试使用 Django 模型检测...")

            # 回退到 Django 模型检测
            from django.apps import apps
            for model in apps.get_models():
                if hasattr(model, '_meta'):
                    existing_tables.add(model._meta.db_table)

        print(f"\n检测到 {len(existing_tables)} 张表")

        # 检查每个模块的表
        all_expected = get_all_expected_tables()
        missing_tables: Dict[str, List[str]] = {}
        found_tables: Dict[str, List[str]] = {}

        for module, tables in EXPECTED_TABLES.items():
            module_missing = []
            module_found = []

            for table in tables:
                if table in existing_tables:
                    module_found.append(table)
                else:
                    module_missing.append(table)

            if module_missing:
                missing_tables[module] = module_missing
            if module_found:
                found_tables[module] = module_found

        # 输出结果
        print("\n" + "-"*60)
        print("模块表状态:")
        print("-"*60)

        for module in sorted(EXPECTED_TABLES.keys()):
            expected = EXPECTED_TABLES[module]
            found = found_tables.get(module, [])
            missing = missing_tables.get(module, [])

            if not missing:
                print(f"\n✓ {module}: {len(found)}/{len(expected)} 表完整")
            else:
                print(f"\n✗ {module}: {len(found)}/{len(expected)} 表缺失")

            if missing:
                print(f"  缺失: {', '.join(missing)}")

        # 汇总
        print("\n" + "="*60)
        print("汇总")
        print("="*60)

        total_expected = len(all_expected)
        total_found = len(all_expected - {t for tables in missing_tables.values() for t in tables})
        total_missing = total_expected - total_found

        print(f"期望表数: {total_expected}")
        print(f"存在表数: {total_found}")
        print(f"缺失表数: {total_missing}")

        if total_missing == 0:
            print("\n✓ 所有核心表都存在！")
            return True
        else:
            print("\n✗ 存在缺失的表，可能需要运行数据库迁移")

            # 尝试运行迁移
            print("\n建议运行以下命令:")
            print("  python manage.py makemigrations")
            print("  python manage.py migrate")

            return False

    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保在 Backend 目录下运行此脚本")
        return False
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    success = check_database_tables()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
