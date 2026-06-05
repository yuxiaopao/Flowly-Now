# -*- coding: utf-8 -*-
"""
前后端 API 路径一致性检测脚本
对比前端调用的 API 路径与后端实际提供的路径

使用方式:
    cd e:\Flowly-now\Backend
    python scripts/check_frontend_backend_alignment.py
"""

import os
import sys
import re
import json
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, 'Backend')
FRONTEND_ROOT = os.path.join(PROJECT_ROOT, 'Frontend')


@dataclass
class PathCheckResult:
    """路径检查结果"""
    frontend_path: str
    backend_path: str
    status: str  # 'match', 'missing_in_backend', 'missing_in_frontend', 'mismatch'
    message: str


def extract_frontend_api_paths() -> Set[str]:
    """从前端代码中提取所有 API 路径"""
    api_paths = set()
    frontend_api_dir = os.path.join(FRONTEND_ROOT, 'src', 'api')

    if not os.path.exists(frontend_api_dir):
        print(f"警告: 前端 API 目录不存在: {frontend_api_dir}")
        return api_paths

    # 匹配 request.get/post/put/delete/delete 调用
    patterns = [
        r"request\.(get|post|put|patch|delete|stream)\(['\"]([^'\"]+)['\"]",
        r"fetch\([^)]*\)",  # fetch 调用需要单独处理
    ]

    for filename in os.listdir(frontend_api_dir):
        if not filename.endswith(('.js', '.ts')):
            continue

        filepath = os.path.join(frontend_api_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取所有 API 路径
        for match in re.finditer(r"['\"](/[a-zA-Z0-9_/{}%-]+/)?['\"]", content):
            path = match.group(1)
            if path and path.startswith('/') and not path.startswith('//'):
                # 标准化路径: 移除末尾斜杠，统一格式
                normalized = path.rstrip('/') + '/'
                if 'api/' in normalized or normalized in ['/login/', '/register/', '/logout/']:
                    api_paths.add(normalized)

    # 手动提取更精确的路径
    for filename in os.listdir(frontend_api_dir):
        filepath = os.path.join(frontend_api_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 request.method('/path/', ...)
        for match in re.finditer(r"request\.(get|post|put|patch|delete)\(['\"`]([^'\"]+)['\"`]", content):
            path = match.group(2)
            if path.startswith('/'):
                normalized = path.rstrip('/') + '/'
                api_paths.add(normalized)

    return api_paths


def extract_backend_api_paths() -> Dict[str, List[str]]:
    """从后端 URL 配置中提取所有 API 路径"""
    # 尝试导入 Django 并获取 URL 配置
    try:
        sys.path.insert(0, BACKEND_ROOT)
        import django
        django.setup()

        from django.urls import get_resolver, URLPattern, URLResolver

        paths = {}

        def extract_paths(patterns, prefix='', app_name=''):
            for pattern in patterns:
                if hasattr(pattern, 'url_patterns'):
                    # 这是一个 include，递归处理
                    new_prefix = prefix + str(pattern.pattern)
                    new_app = pattern.namespace or app_name
                    extract_paths(pattern.url_patterns, new_prefix, new_app)
                elif hasattr(pattern, 'pattern'):
                    # 这是一个 URL 模式
                    path_str = prefix + str(pattern.pattern)
                    callback = pattern.callback

                    # 提取视图函数名
                    view_name = 'unknown'
                    if callback:
                        if hasattr(callback, '__name__'):
                            view_name = callback.__name__
                        elif hasattr(callback, 'view_class'):
                            view_name = callback.view_class.__name__

                    # 移除正则表达式中的参数部分
                    clean_path = re.sub(r'<[^>]+>', '{id}', path_str)
                    clean_path = clean_path.rstrip('/') + '/'

                    if 'api/' in clean_path:
                        if app_name not in paths:
                            paths[app_name] = []
                        paths[app_name].append({
                            'path': clean_path,
                            'original': path_str,
                            'view': view_name
                        })

        resolver = get_resolver()
        extract_paths(resolver.url_patterns)

        return paths

    except Exception as e:
        print(f"警告: 无法获取后端 URL 配置: {e}")
        return {}


def normalize_path(path: str) -> str:
    """标准化路径以便比较"""
    # 移除末尾斜杠
    path = path.rstrip('/')
    # 将 {id} 替换为具体 ID 格式
    path = re.sub(r'<[^>]*id[^>]*>', '{id}', path)
    # 移除其他参数
    path = re.sub(r'<[^>]+>', '', path)
    # 统一双斜杠
    path = path.replace('//', '/')
    return path


def check_alignment() -> List[PathCheckResult]:
    """检查前后端路径一致性"""
    results = []

    # 获取前端路径
    frontend_paths = extract_frontend_api_paths()
    print(f"前端 API 路径数量: {len(frontend_paths)}")

    # 获取后端路径
    backend_paths_dict = extract_backend_api_paths()
    print(f"后端 App 数量: {len(backend_paths_dict)}")

    # 展平后端路径
    backend_paths = {}
    for app_name, paths in backend_paths_dict.items():
        for path_info in paths:
            backend_paths[path_info['path']] = path_info['view']

    print(f"后端 API 路径数量: {len(backend_paths)}")

    # 检查每个前端路径
    for fp in sorted(frontend_paths):
        normalized_fp = normalize_path(fp)

        # 尝试在后端路径中查找匹配
        found = False
        for bp, view in backend_paths.items():
            normalized_bp = normalize_path(bp)

            # 完全匹配
            if normalized_fp == normalized_bp:
                results.append(PathCheckResult(
                    frontend_path=fp,
                    backend_path=bp,
                    status='match',
                    message=f'匹配 - {view}'
                ))
                found = True
                break
            # 前缀匹配 (例如 /workflows/ 应该匹配 /workflows/{id}/)
            elif normalized_fp.rstrip('/') in normalized_bp.rstrip('/') or \
                 normalized_bp.rstrip('/') in normalized_fp.rstrip('/'):
                results.append(PathCheckResult(
                    frontend_path=fp,
                    backend_path=bp,
                    status='match',
                    message=f'前缀匹配 - {view}'
                ))
                found = True
                break

        if not found:
            # 检查是否在后端存在但路径略有不同
            similar = []
            for bp in backend_paths:
                # 计算相似度
                if normalized_fp.split('/')[:-1] == normalize_path(bp).split('/')[:-1]:
                    similar.append((bp, backend_paths[bp]))

            if similar:
                results.append(PathCheckResult(
                    frontend_path=fp,
                    backend_path=similar[0][0],
                    status='mismatch',
                    message=f'可能不匹配，相似路径: {similar[0][1]}'
                ))
            else:
                results.append(PathCheckResult(
                    frontend_path=fp,
                    backend_path='N/A',
                    status='missing_in_backend',
                    message='后端未找到对应路径'
                ))

    return results


def print_report(results: List[PathCheckResult]):
    """打印检测报告"""
    print("\n" + "="*80)
    print("前后端 API 路径一致性检测报告")
    print("="*80)

    # 统计
    match_count = sum(1 for r in results if r.status == 'match')
    mismatch_count = sum(1 for r in results if r.status == 'mismatch')
    missing_count = sum(1 for r in results if r.status == 'missing_in_backend')

    print(f"\n总计: {len(results)}")
    print(f"匹配: {match_count}")
    print(f"不匹配: {mismatch_count}")
    print(f"缺失: {missing_count}")

    # 显示问题
    if mismatch_count > 0 or missing_count > 0:
        print("\n问题详情:")
        print("-" * 80)

        for r in results:
            if r.status != 'match':
                print(f"\n前端: {r.frontend_path}")
                print(f"后端: {r.backend_path}")
                print(f"状态: {r.status}")
                print(f"说明: {r.message}")

    # 保存报告
    report_dir = os.path.join(BACKEND_ROOT, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, 'frontend_backend_alignment.json')

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump([
            {
                'frontend_path': r.frontend_path,
                'backend_path': r.backend_path,
                'status': r.status,
                'message': r.message
            }
            for r in results
        ], f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存: {report_file}")


def main():
    """主函数"""
    print("开始检测前后端 API 路径一致性...")
    print(f"项目根目录: {PROJECT_ROOT}")

    results = check_alignment()
    print_report(results)

    return 0 if all(r.status == 'match' for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
