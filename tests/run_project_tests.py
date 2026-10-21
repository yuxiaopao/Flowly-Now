"""从项目根目录运行全量后端测试，业务数据库不会被连接。"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'Backend'), str(ROOT)]
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.project_test_settings'
os.environ['PYTHONUTF8'] = '1'
os.chdir(ROOT / 'Backend')

import pytest

DEFAULT_SUITES = (
    'tests/backend', 'tests/nl_workflow', 'Backend/workflows/tests',
    'Backend/core/tests', 'Backend/website_generator/tests',
    'Backend/nl_to_workflow/tests', 'Backend/tests',
)

if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    print('测试数据库：独立 SQLite 内存；准备收集全部测试。', flush=True)
    arguments = sys.argv[1:]
    has_selection = any(not arg.startswith('-') and Path(arg.split('::', 1)[0]).exists() for arg in arguments)
    if not has_selection:
        arguments = [*[str(ROOT / suite) for suite in DEFAULT_SUITES], *arguments]
    sys.exit(pytest.main([
        *arguments, '-c', str(ROOT / 'pytest.ini'),
        '--ds=config.project_test_settings', '--import-mode=importlib',
        '--override-ini=addopts=-q --tb=short', '-p', 'no:cacheprovider',
    ]))
