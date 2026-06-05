# -*- coding: utf-8 -*-
"""
Flowly 完整性检测入口脚本
运行所有检测: API可用性、数据库表、前后端一致性

使用方式:
    # 确保后端服务正在运行
    cd e:\Flowly-now\Backend
    python manage.py runserver

    # 新开终端运行检测
    cd e:\Flowly-now\Backend
    python scripts/run_all_checks.py
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime

# 项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')


def print_header(title: str):
    """打印标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_subheader(title: str):
    """打印副标题"""
    print(f"\n--- {title} ---")


def run_script(script_name: str, description: str) -> bool:
    """运行检测脚本"""
    print_subheader(description)

    script_path = os.path.join(SCRIPT_DIR, script_name)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"运行失败: {e}")
        return False


def check_server_running(base_url: str = "http://127.0.0.1:8000") -> bool:
    """检查服务器是否运行"""
    print_subheader("检查后端服务状态")

    try:
        import requests
        response = requests.get(f"{base_url}/api/health/", timeout=5)
        if response.status_code < 500:
            print(f"✓ 后端服务正在运行: {base_url}")
            return True
        else:
            print(f"✗ 后端服务返回错误: {response.status_code}")
            return False
    except ImportError:
        print("⚠ requests 模块未安装，跳过服务器检查")
        print("  请手动确保后端服务已启动: python manage.py runserver")
        return True
    except Exception as e:
        print(f"✗ 无法连接到后端服务: {e}")
        print("\n请先启动后端服务:")
        print("  cd e:\\Flowly-now\\Backend")
        print("  python manage.py runserver")
        return False


def generate_summary_report():
    """生成汇总报告"""
    print_header("生成汇总报告")

    reports_dir = os.path.join(PROJECT_ROOT, 'reports')

    if not os.path.exists(reports_dir):
        print("报告目录不存在")
        return

    # 查找最新的报告文件
    report_files = []
    for filename in os.listdir(reports_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(reports_dir, filename)
            report_files.append((filepath, os.path.getmtime(filepath)))

    report_files.sort(key=lambda x: x[1], reverse=True)

    print(f"\n发现 {len(report_files)} 个报告文件")

    # 创建汇总报告
    summary = {
        "generated_at": datetime.now().isoformat(),
        "reports": []
    }

    for filepath, _ in report_files[:10]:  # 最近10个报告
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
                summary["reports"].append({
                    "file": os.path.basename(filepath),
                    "content": content
                })
        except Exception as e:
            print(f"读取报告失败 {filepath}: {e}")

    # 保存汇总报告
    os.makedirs(REPORTS_DIR, exist_ok=True)
    summary_file = os.path.join(REPORTS_DIR, f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n汇总报告已保存: {summary_file}")


def main():
    """主函数"""
    print_header("Flowly 完整性检测套件")

    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 检查服务器状态
    server_ok = check_server_running()

    results = {}

    if server_ok:
        # 2. 运行 API 检测
        results['api_check'] = run_script(
            'api_checker.py',
            '检测 API 端点可用性'
        )

        # 3. 运行前后端一致性检测
        results['alignment_check'] = run_script(
            'check_frontend_backend_alignment.py',
            '检测前后端 API 路径一致性'
        )
    else:
        print("\n由于服务器未运行，跳过需要服务器的检测")

    # 4. 数据库表检测 (不需要服务器运行)
    results['database_check'] = run_script(
        'check_database_tables.py',
        '检测数据库表完整性'
    )

    # 5. 生成汇总报告
    generate_summary_report()

    # 打印最终结果
    print_header("检测完成")

    print("\n结果汇总:")
    for check_name, success in results.items():
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {check_name}: {status}")

    all_passed = all(results.values())
    print(f"\n总体状态: {'✓ 全部通过' if all_passed else '✗ 存在失败项'}")

    print("\n报告文件位置:")
    print(f"  {os.path.join(PROJECT_ROOT, 'reports')}")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
