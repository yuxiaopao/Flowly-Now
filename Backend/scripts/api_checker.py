# -*- coding: utf-8 -*-
"""
API 完整性检测脚本
使用 Django REST Framework 的 Router 提取端点进行检测

使用方式:
    # 1. 启动后端服务
    cd e:\Flowly-now\Backend
    python manage.py runserver

    # 2. 另开终端执行检测
    cd e:\Flowly-now\Backend
    python scripts/api_checker.py
"""

import os
import sys
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# 路径前缀 → 模块名映射
_PATH_MODULE_MAP = [
    ('/workflows', '工作流'),
    ('/agents', 'Agent'),
    ('/auth', '认证'),
    ('/prompts', 'Prompt'),
    ('/tenants', '租户'),
    ('/monitoring', '监控'),
    ('/rag', 'RAG'),
    ('/gateway', '网关'),
    ('/billing', '计费'),
    ('/integrations', '集成'),
    ('/branding', '品牌'),
    ('/marketplace', '市场'),
    ('/templates', '模板'),
    ('/nl-workflow', 'NL转工作流'),
    ('/admin', '管理'),
    ('/health', '健康检查'),
    ('/ping', '健康检查'),
]

_PATH_PARAM_PATTERN = re.compile(r'\{[^}]+\}')

_PATH_MODULE_MAP.sort(key=lambda x: -len(x[0]))

# Derive AUTH_REQUIRED_PREFIXES from _PATH_MODULE_MAP automatically
_PUBLIC_MODULES = frozenset({'health', 'ping'})
AUTH_REQUIRED_PREFIXES = tuple(
    f'/api/v1/{p}/' for p, _ in _PATH_MODULE_MAP if p.lstrip('/') not in _PUBLIC_MODULES
)
_NO_AUTH_PATHS = ('/api/health/', '/api/ping/', '/api/docs/', '/api/schema/',
                   '/api/v1/auth/login/', '/api/v1/auth/register/')

def _path_to_module(path: str) -> str:
    for prefix, name in _PATH_MODULE_MAP:
        if path.startswith(prefix):
            return name
    return '其他'

# 将 Backend 目录添加到 Python 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 配置
BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10

# 需要认证的路径前缀
AUTH_REQUIRED_PREFIXES = (
    '/api/v1/auth/', '/api/v1/workflows/', '/api/v1/agents/',
    '/api/v1/prompts/', '/api/v1/tenants/', '/api/v1/monitoring/',
    '/api/v1/rag/', '/api/v1/gateway/', '/api/v1/billing/',
    '/api/v1/integrations/', '/api/v1/branding/', '/api/v1/marketplace/',
    '/api/v1/templates/', '/api/v1/nl-workflow/', '/api/v1/admin/',
)

# 不需要认证的路径
NO_AUTH_PATHS = (
    '/api/health/', '/api/ping/', '/api/docs/', '/api/schema/',
    '/api/v1/auth/login/', '/api/v1/auth/register/',
)


@dataclass
class EndpointResult:
    """端点检测结果"""
    _STATUS_ICON = {'pass': '[PASS]', 'fail': '[FAIL]', 'warning': '[WARN]', 'auth_required': '[AUTH]', 'skip': '[SKIP]'}

    path: str
    method: str
    view_name: str = ""
    status: str = 'skip'
    status_code: int = 0
    message: str = ""
    response_time: float = 0.0

    def __str__(self):
        icon = self._STATUS_ICON.get(self.status, '[?]')
        ms = f"{round(self.response_time * 1000)}ms" if self.response_time > 0 else ''
        return f"{icon} {self.method.upper():6} {self.path}{' (' + ms + ')' if ms else ''} - {self.message}"


class APIEndpointChecker:
    """API 端点检测器"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.endpoints: List[Tuple[str, str, str]] = []  # (path, method, view_name)
        self.all_results: List[EndpointResult] = []
        self.token: Optional[str] = None

    def print_section(self, title: str):
        """打印分节标题"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")

    def print_subsection(self, title: str):
        """打印子标题"""
        print(f"\n--- {title} ---")

    def extract_endpoints_from_routes(self) -> int:
        """从 Django URL routes 中提取端点"""
        self.print_section("提取 API 端点")

        try:
            import django
            django.setup()

            from django.urls import URLPattern, URLResolver
            from rest_framework.routers import DefaultRouter, SimpleRouter

            endpoints = {}

            def get_all_urls(patterns, prefix=''):
                """递归获取所有 URL"""
                for pattern in patterns:
                    if isinstance(pattern, URLResolver):
                        # 嵌套的 URL
                        new_prefix = prefix + str(pattern.pattern).lstrip('^')
                        get_all_urls(pattern.url_patterns, new_prefix)
                    elif isinstance(pattern, URLPattern):
                        # 叶子 URL
                        path = prefix + str(pattern.pattern)
                        # 清理路径
                        path = path.replace('^', '').replace('$', '')
                        # 处理命名的正则参数 (?P<pk>[^/.]+)/ -> {pk}/
                        path = re.sub(r'\(\?P<(\w+)>\[.*?\]\+\?', r'{\1}', path)
                        path = re.sub(r'\(\?P<(\w+)>\[\^\./\]?\+\?', r'{\1}', path)
                        path = re.sub(r'\(\?P<(\w+)>\[[\^/\]]+\)\+', r'{\1}', path)
                        path = re.sub(r'\(\?P<(\w+)>[^)]+\)', r'{\1}', path)
                        # 处理 Django 路径参数
                        path = re.sub(r'<(\w+):(\w+)>', r'{\2}', path)
                        path = re.sub(r'<(\w+)>', r'{\1}', path)
                        
                        # 去除尾部的 ? 或 /?
                        path = re.sub(r'\?/?$', '', path)
                        if not path.endswith('/'):
                            path += '/'
                        
                        # 获取视图名
                        view_name = 'unknown'
                        if pattern.callback:
                            if hasattr(pattern.callback, 'view_class'):
                                view_name = pattern.callback.view_class.__name__
                            elif hasattr(pattern.callback, '__name__'):
                                view_name = pattern.callback.__name__
                        
                        if path not in endpoints:
                            endpoints[path] = {'methods': set(), 'view': view_name}
                        endpoints[path]['methods'].add('GET')

            # 从主 urls 导入
            from config.urls import urlpatterns
            get_all_urls(urlpatterns)

            # 转换为列表
            for path, info in endpoints.items():
                for method in info['methods']:
                    # 过滤掉无效路径
                    if 'api/' in path and '{format}' not in path and '<drf_format' not in path:
                        self.endpoints.append((path, method, info['view']))

            self.endpoints.sort(key=lambda x: (x[0], x[1]))

            print(f"发现 {len(self.endpoints)} 个 API 端点\n")

            # 按模块分组显示
            modules = self._group_endpoints_by_module()
            for module, module_endpoints in sorted(modules.items()):
                print(f"  {module}: {len(module_endpoints)} 个端点")

            return len(self.endpoints)

        except ImportError as e:
            print(f"导入错误: {e}")
            print("请确保在 Backend 目录下运行此脚本")
            return 0
        except Exception as e:
            print(f"提取端点出错: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _group_endpoints_by_module(self) -> Dict[str, List]:
        """按模块分组端点"""
        modules = defaultdict(list)
        for path, method, view_name in self.endpoints:
            modules[_path_to_module(path)].append((path, method))

        return dict(modules)

    def _requires_auth(self, path: str) -> bool:
        """检查路径是否需要认证"""
        if path.startswith(NO_AUTH_PATHS):
            return False
        return path.startswith(AUTH_REQUIRED_PREFIXES)

    def try_get_auth_token(self) -> bool:
        """尝试获取认证 Token"""
        self.print_subsection("获取认证 Token")

        try:
            import requests
            session = requests.Session()

            response = session.post(
                f"{self.base_url}/api/v1/auth/login/",
                json={"username": "admin", "password": "admin123"},
                timeout=TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access') or data.get('access_token')
                if self.token:
                    print("[PASS] 认证成功")
                    return True
            elif response.status_code == 401:
                print("[WARN] 登录失败 (401)，部分 API 将跳过")
            else:
                print(f"[WARN] 登录请求返回: {response.status_code}")
        except Exception as e:
            print(f"[WARN] 获取 Token 失败: {e}")

        return False

    def check_endpoint(self, session, path: str, method: str) -> EndpointResult:
        """检测单个端点"""
        clean_path = path.lstrip('/')
        url = f"{self.base_url}/{clean_path}"
        url = _PATH_PARAM_PATTERN.sub('1', url)

        start_time = time.time()
        result = EndpointResult(path=path, method=method, status='skip')

        try:
            if method == 'GET':
                response = session.get(url, timeout=TIMEOUT)
            elif method == 'POST':
                response = session.post(url, json={}, timeout=TIMEOUT)
            elif method == 'PUT':
                response = session.put(url, json={}, timeout=TIMEOUT)
            elif method == 'PATCH':
                response = session.patch(url, json={}, timeout=TIMEOUT)
            elif method == 'DELETE':
                response = session.delete(url, timeout=TIMEOUT)
            else:
                response = session.request(method, url, timeout=TIMEOUT)

            result.response_time = time.time() - start_time
            result.status_code = response.status_code

            if response.status_code == 200:
                result.status = 'pass'
                result.message = 'OK'
            elif response.status_code == 201:
                result.status = 'pass'
                result.message = 'Created'
            elif response.status_code == 204:
                result.status = 'pass'
                result.message = 'No Content'
            elif response.status_code == 401:
                if self._requires_auth(path):
                    result.status = 'auth_required'
                    result.message = '需要认证'
                else:
                    result.status = 'warning'
                    result.message = '意外返回 401'
            elif response.status_code == 403:
                result.status = 'warning'
                result.message = '权限不足'
            elif response.status_code == 404:
                result.status = 'fail'
                result.message = '端点不存在'
            elif 400 <= response.status_code < 500:
                result.status = 'warning'
                result.message = f'客户端错误 ({response.status_code})'
            elif response.status_code >= 500:
                result.status = 'fail'
                result.message = f'服务器错误 ({response.status_code})'
            else:
                result.status = 'warning'
                result.message = f'HTTP {response.status_code}'

        except Exception as e:
            result.status = 'fail'
            result.response_time = time.time() - start_time
            result.message = f'错误: {str(e)[:50]}'

        return result

    def check_all_endpoints(self) -> List[EndpointResult]:
        """检测所有端点"""
        self.print_section("检测 API 端点")

        import requests
        session = requests.Session()
        if self.token:
            session.headers.update({"Authorization": f"Bearer {self.token}"})

        total = len(self.endpoints)
        print(f"共 {total} 个端点待检测...\n")

        results = []
        current_module = ""

        for i, (path, method, view_name) in enumerate(self.endpoints, 1):
            module = _path_to_module(path)
            if module != current_module:
                current_module = module
                print(f"\n[{module}]")

            result = self.check_endpoint(session, path, method)
            result.view_name = view_name
            results.append(result)
            self.all_results.append(result)

            icon = {'pass': '+', 'fail': 'X', 'warning': '!', 'auth_required': '?', 'skip': '-'}
            print(f"  [{i:3}/{total}] {icon.get(result.status, '?')} {method:6} {path}")

        return results

    def generate_report(self) -> Dict:
        """生成检测报告"""
        self.print_section("检测报告")

        total = len(self.all_results)
        passed = sum(1 for r in self.all_results if r.status == 'pass')
        failed = sum(1 for r in self.all_results if r.status == 'fail')
        warnings = sum(1 for r in self.all_results if r.status == 'warning')
        auth_required = sum(1 for r in self.all_results if r.status == 'auth_required')
        skipped = sum(1 for r in self.all_results if r.status == 'skip')

        print(f"\n总计: {total}")
        print(f"  通过: {passed} ({passed*100//total if total else 0}%)")
        print(f"  失败: {failed}")
        print(f"  警告: {warnings}")
        print(f"  需要认证: {auth_required}")
        print(f"  跳过: {skipped}")

        print("\n按模块统计:")
        modules = defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0})

        for r in self.all_results:
            module = _path_to_module(r.path)
            modules[module]['total'] += 1
            if r.status == 'pass':
                modules[module]['passed'] += 1
            elif r.status == 'fail':
                modules[module]['failed'] += 1
            elif r.status in ['warning', 'auth_required']:
                modules[module]['warnings'] += 1

        for module, stats in sorted(modules.items()):
            pct = stats['passed'] * 100 // stats['total'] if stats['total'] else 0
            status_icon = 'OK' if stats['failed'] == 0 else 'FAIL'
            print(f"  [{status_icon}] {module:12} {stats['passed']:3}/{stats['total']:3} ({pct:3}%)")

        if failed > 0:
            print("\n失败详情:")
            for r in self.all_results:
                if r.status == 'fail':
                    print(f"  X {r.method.upper()} {r.path} - {r.message}")

        if warnings > 0:
            print("\n警告详情:")
            for r in self.all_results:
                if r.status == 'warning':
                    print(f"  ! {r.method.upper()} {r.path} - {r.message}")

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "total_endpoints": total,
            "summary": {
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "auth_required": auth_required,
                "skipped": skipped
            },
            "by_module": dict(modules),
            "results": [
                {
                    "path": r.path,
                    "method": r.method,
                    "view": r.view_name,
                    "status": r.status,
                    "status_code": r.status_code,
                    "message": r.message,
                    "response_time_ms": round(r.response_time * 1000, 2)
                }
                for r in self.all_results
            ]
        }

        reports_dir = os.path.join(BACKEND_DIR, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(reports_dir, f"api_check_{timestamp}.json")

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存: {report_file}")

        return report

    def check_server_status(self) -> bool:
        """检查服务器状态"""
        import requests
        try:
            response = requests.get(f"{self.base_url}/api/health/", timeout=5)
            return response.status_code < 500
        except requests.RequestException:
            return False

    def run_full_check(self):
        """执行完整检测"""
        print("="*70)
        print("  Flowly API 完整性检测")
        print("="*70)
        print(f"目标服务器: {self.base_url}")
        print(f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.check_server_status():
            print(f"\n[FAIL] 无法连接到 {self.base_url}")
            print("请确保后端服务正在运行: python manage.py runserver")
            return None

        print(f"[PASS] 服务器连接正常")

        if not self.extract_endpoints_from_routes():
            print("[FAIL] 未发现任何 API 端点")
            return

        self.try_get_auth_token()
        self.check_all_endpoints()
        report = self.generate_report()

        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Flowly API 完整性检测')
    parser.add_argument('--url', '-u', default=BASE_URL, help=f'API 服务器地址 (默认: {BASE_URL})')
    parser.add_argument('--timeout', '-t', type=int, default=TIMEOUT, help=f'请求超时秒数 (默认: {TIMEOUT})')
    args = parser.parse_args()

    checker = APIEndpointChecker(args.url)
    success = checker.run_full_check()

    if success:
        sys.exit(0 if success['summary']['failed'] == 0 else 1)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
