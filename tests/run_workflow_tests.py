"""在独立数据库中运行工作流回归，不连接或清理业务数据库。"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.workflow_test_settings'

import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.test.utils import setup_databases, teardown_databases
import pytest

# 原迁移包含 MySQL 专用 SQL。行为测试按当前模型构建 SQLite 表；
# 此入口不验证迁移，真实 MySQL 联调由 verify_workflows 完成。
settings.MIGRATION_MODULES = {app.label: None for app in apps.get_app_configs()}
database = setup_databases(verbosity=0, interactive=False)
try:
    code = pytest.main([
        str(ROOT / 'Backend/workflows/tests'),
        str(ROOT / 'tests/backend/workflows'),
        '--ds=config.workflow_test_settings',
        '--override-ini=addopts=-q --tb=short',
    ])
finally:
    teardown_databases(database, verbosity=0)
sys.exit(code)
