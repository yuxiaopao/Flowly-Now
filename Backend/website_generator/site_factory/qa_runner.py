"""Site QA runner: L1–L4 checks for generated sites."""

import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .qa_thresholds import evaluate_metrics_gate


def run_site_qa(
    output_dir: str,
    model_path: str = '',
    website_type: str = 'detection',
    qa_profile: str = 'default',
    metrics: Optional[Dict[str, Any]] = None,
    port: Optional[int] = None,
    skip_playwright: bool = False,
    generated_site_id: str = '',
) -> Dict[str, Any]:
    metrics = dict(metrics or {})
    qa_dir = os.path.join(output_dir, '.flowly', 'qa')
    os.makedirs(qa_dir, exist_ok=True)
    screenshots_dir = os.path.join(qa_dir, 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)

    layers = {'l1': 'skip', 'l2': 'skip', 'l3': 'skip', 'l4': 'skip'}
    layer_errors: List[str] = []
    screenshots: List[str] = []
    server_proc = None
    assigned_port = port or 49152

    try:
        l1_ok, l1_err = _run_l1(output_dir, model_path)
        layers['l1'] = 'pass' if l1_ok else 'fail'
        if not l1_ok:
            layer_errors.extend(l1_err)

        if l1_ok:
            assigned_port = _ensure_port_in_config(output_dir, assigned_port)
            l2_ok, l2_err, server_proc = _run_l2(output_dir, assigned_port, website_type)
            layers['l2'] = 'pass' if l2_ok else 'fail'
            if not l2_ok:
                layer_errors.extend(l2_err)

            if l2_ok:
                if skip_playwright:
                    layers['l3'] = 'skip'
                else:
                    wtype = (website_type or 'detection').lower()
                    if wtype in ('clip_retrieval', 'retrieval'):
                        l3_ok, l3_err, shots = _run_l3_clip_retrieval_playwright(
                            assigned_port, screenshots_dir,
                        )
                    else:
                        l3_ok, l3_err, shot = _run_l3_static_check(
                            output_dir, assigned_port, screenshots_dir, website_type,
                        )
                        shots = [shot] if shot else []
                    layers['l3'] = 'pass' if l3_ok else 'fail'
                    for shot in shots:
                        if shot:
                            screenshots.append(shot)
                    if not l3_ok:
                        layer_errors.extend(l3_err)

                l4_gate, l4_summary, l4_recs = evaluate_metrics_gate(
                    website_type, metrics, qa_profile,
                )
                layers['l4'] = 'pass' if l4_gate != 'red' else 'fail'
            else:
                l4_gate, l4_summary, l4_recs = 'red', '服务层检查失败，跳过指标评估。', []
                layers['l4'] = 'skip'
        else:
            l4_gate, l4_summary, l4_recs = 'red', '结构检查失败，跳过指标评估。', []
    finally:
        if server_proc:
            try:
                server_proc.terminate()
                server_proc.wait(timeout=5)
            except Exception:
                try:
                    server_proc.kill()
                except Exception:
                    pass

    if layers['l1'] == 'fail' or layers['l2'] == 'fail' or layers['l3'] == 'fail':
        gate = 'red'
        summary_zh = '；'.join(layer_errors[:3]) if layer_errors else '基础检查未通过。'
        recommendations = l4_recs if l4_recs else ['修复上述检查项后重新运行 QA']
    elif layers['l3'] == 'fail':
        gate = 'red'
        summary_zh = layer_errors[0] if layer_errors else '页面检查未通过。'
        recommendations = ['确认 Flask 已配置首页路由']
    else:
        gate = l4_gate
        summary_zh = l4_summary
        recommendations = l4_recs

    if gate == 'green' and layers['l3'] == 'skip':
        summary_zh = f'{summary_zh}（未执行 Playwright，仅 API 检查）'

    report = {
        'gate': gate,
        'profile': qa_profile,
        'website_type': website_type,
        'generated_site_id': generated_site_id,
        'metrics': metrics,
        'layers': layers,
        'layer_errors': layer_errors,
        'recommendations': recommendations,
        'summary_zh': summary_zh,
        'assigned_port': assigned_port,
        'screenshots': screenshots,
        'thresholds_used': {'source': 'qa-threshold-matrix.md'},
    }

    report_path = os.path.join(qa_dir, 'qa_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return {
        'gate': gate,
        'layers': layers,
        'metrics': metrics,
        'report_path': report_path,
        'summary_zh': summary_zh,
        'recommendations': recommendations,
        'assigned_port': assigned_port,
        'preview_url': f'http://127.0.0.1:{assigned_port}/',
        'qa_report': report,
    }


def _run_l1(output_dir: str, model_path: str, db_engine: str = 'sqlite') -> Tuple[bool, List[str]]:
    errors = []
    if not output_dir or not os.path.isdir(output_dir):
        errors.append('输出目录不存在')
        return False, errors

    backend = os.path.join(output_dir, 'backend')
    for rel in ('app.py', 'requirements.txt', 'config.json'):
        if not os.path.isfile(os.path.join(backend, rel)):
            errors.append(f'缺少 backend/{rel}')

    schema = os.path.join(backend, 'db', 'schema.sql')
    if not os.path.isfile(schema):
        errors.append('缺少 backend/db/schema.sql（数据库 scaffold）')

    engine = (db_engine or _read_config_db_engine(output_dir)).lower()
    if engine == 'mysql':
        mysql_cfg = _read_mysql_env()
        ok, detail = _mysql_l1_check(mysql_cfg)
        if not ok:
            errors.append(f'MySQL L1: {detail}')
    else:
        db_dir = os.path.join(backend, 'db')
        try:
            os.makedirs(db_dir, exist_ok=True)
            test_db = os.path.join(db_dir, '.write_test')
            with open(test_db, 'w') as f:
                f.write('1')
            os.remove(test_db)
        except OSError as e:
            errors.append(f'SQLite 目录不可写: {e}')

    if model_path and not os.path.isfile(model_path):
        errors.append(f'模型权重不可读: {model_path}')

    req = os.path.join(backend, 'requirements.txt')
    if os.path.isfile(req):
        with open(req, encoding='utf-8') as f:
            if not f.read().strip():
                errors.append('requirements.txt 为空')

    return len(errors) == 0, errors


def _read_config_db_engine(output_dir: str) -> str:
    cfg_path = os.path.join(output_dir, 'backend', 'config.json')
    if not os.path.isfile(cfg_path):
        return 'sqlite'
    try:
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
        return str(cfg.get('db_engine') or cfg.get('dbEngine') or 'sqlite')
    except Exception:
        return 'sqlite'


def _read_mysql_env() -> dict:
    return {
        'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
        'port': int(os.environ.get('MYSQL_PORT', '3306')),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DATABASE', 'flowly_site'),
    }


def _mysql_l1_check(mysql_cfg: dict) -> Tuple[bool, str]:
    try:
        import pymysql
        conn = pymysql.connect(
            host=mysql_cfg['host'], port=mysql_cfg['port'], user=mysql_cfg['user'],
            password=mysql_cfg['password'], database=mysql_cfg['database'],
            charset='utf8mb4', connect_timeout=5,
        )
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
            return True, '连接正常'
        finally:
            conn.close()
    except ImportError:
        return False, 'PyMySQL 未安装'
    except Exception as exc:
        return False, str(exc)


def _ensure_port_in_config(output_dir: str, port: int) -> int:
    cfg_path = os.path.join(output_dir, 'backend', 'config.json')
    if os.path.isfile(cfg_path):
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
        cfg['port'] = port
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    return port


def _run_l2(output_dir: str, port: int, website_type: str = 'detection') -> Tuple[bool, List[str], Any]:
    errors = []
    backend_dir = os.path.join(output_dir, 'backend')
    env = {**os.environ, 'FLASK_RUN_PORT': str(port)}
    proc = subprocess.Popen(
        [sys.executable, 'app.py'],
        cwd=backend_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(4)
    if proc.poll() is not None:
        err = proc.stderr.read().decode('utf-8', errors='replace')[:500]
        return False, [f'Flask 启动失败: {err}'], proc

    base = f'http://127.0.0.1:{port}'
    try:
        health = _http_get_json(f'{base}/health')
        if health.get('status') != 'ok':
            errors.append('health 检查未返回 ok')
    except Exception as e:
        errors.append(f'/health 不可达: {e}')

    if not errors:
        wtype = (website_type or 'detection').lower()
        if wtype in ('clip_retrieval', 'retrieval'):
            try:
                import requests
                resp = requests.post(
                    f'{base}/search/text',
                    json={'query': '测试', 'top_k': 3},
                    timeout=30,
                )
                if resp.status_code >= 400:
                    errors.append(f'/search/text 返回 {resp.status_code}: {resp.text[:200]}')
            except ImportError:
                errors.append('requests 未安装，无法测试 /search/text')
            except Exception as e:
                errors.append(f'/search/text 冒烟失败: {e}')
        else:
            try:
                import requests
                jpeg_bytes = _minimal_jpeg_bytes()
                resp = requests.post(
                    f'{base}/predict',
                    files={'file': ('test.jpg', jpeg_bytes, 'image/jpeg')},
                    timeout=30,
                )
                if resp.status_code >= 400:
                    errors.append(f'/predict 返回 {resp.status_code}: {resp.text[:200]}')
            except ImportError:
                errors.append('requests 未安装，无法测试 /predict')
            except Exception as e:
                errors.append(f'/predict 冒烟失败: {e}')

    return len(errors) == 0, errors, proc


def _minimal_jpeg_bytes() -> bytes:
    """Valid tiny JPEG for /predict smoke (opencv/PIL decodable)."""
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (64, 64), color=(128, 64, 32)).save(buf, format='JPEG')
        return buf.getvalue()
    except ImportError:
        pass
    # Fallback: 64x64 grey JPEG-like payload via numpy+cv2 if available
    try:
        import cv2
        import numpy as np
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode('.jpg', img)
        if ok:
            return encoded.tobytes()
    except ImportError:
        pass
    return b'\xff\xd8\xff\xe0' + b'\x00' * 100


def _run_l3_static_check(
    output_dir: str, port: int, screenshots_dir: str, website_type: str = 'detection',
) -> Tuple[bool, List[str], str]:
    """L3: verify index page served and contains expected UI."""
    errors = []
    shot_path = ''
    base = f'http://127.0.0.1:{port}'
    wtype = (website_type or 'detection').lower()
    try:
        html = _http_get_text(f'{base}/')
        if wtype in ('clip_retrieval', 'retrieval'):
            if '搜索' not in html and 'search' not in html.lower():
                errors.append('检索站首页未包含搜索 UI')
        elif '上传' not in html and 'upload' not in html.lower() and 'upload-zone' not in html:
            errors.append('首页未包含上传区域文案')
        shot_path = os.path.join(screenshots_dir, 'homepage.txt')
        with open(shot_path, 'w', encoding='utf-8') as f:
            f.write(html[:8000])
    except Exception as e:
        frontend_index = os.path.join(output_dir, 'frontend', 'index.html')
        if os.path.isfile(frontend_index):
            with open(frontend_index, encoding='utf-8') as f:
                html = f.read()
            if '上传' in html or 'upload' in html.lower() or 'upload-zone' in html or 'aria-label="上传' in html:
                shot_path = os.path.join(screenshots_dir, 'index_static_check.txt')
                with open(shot_path, 'w', encoding='utf-8') as f:
                    f.write('static index.html ok')
            else:
                errors.append('frontend/index.html 缺少上传 UI')
        else:
            errors.append(f'无法访问首页: {e}')

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f'{base}/', wait_until='networkidle', timeout=15000)
            png_path = os.path.join(screenshots_dir, 'playwright_home.png')
            page.screenshot(path=png_path)
            browser.close()
            shot_path = png_path
    except ImportError:
        pass
    except Exception as e:
        errors.append(f'Playwright 检查失败: {e}')

    return len(errors) == 0, errors, shot_path


def _run_l3_clip_retrieval_playwright(
    port: int, screenshots_dir: str,
) -> Tuple[bool, List[str], List[str]]:
    """L3 for CLIP retrieval sites: Tab1 text search, Tab2 upload, Tab4 API docs."""
    errors: List[str] = []
    shots: List[str] = []
    base = f'http://127.0.0.1:{port}'

    try:
        html = _http_get_text(f'{base}/')
        if '搜索' not in html and 'search' not in html.lower():
            errors.append('检索站首页未包含搜索 UI')
    except Exception as e:
        errors.append(f'无法访问首页: {e}')
        return False, errors, shots

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        shot_path = os.path.join(screenshots_dir, 'clip_l3_static.txt')
        with open(shot_path, 'w', encoding='utf-8') as f:
            f.write('playwright unavailable; static html ok')
        shots.append(shot_path)
        return len(errors) == 0, errors, shots

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f'{base}/', wait_until='networkidle', timeout=20000)

            home_shot = os.path.join(screenshots_dir, 'playwright_clip_home.png')
            page.screenshot(path=home_shot)
            shots.append(home_shot)

            # Tab1 — text search
            query_input = page.locator('#textQuery')
            if query_input.count() == 0:
                errors.append('Tab1 缺少 #textQuery 输入框')
            else:
                query_input.fill('测试')
                search_btn = page.locator('#textSearchBtn')
                if search_btn.count() == 0:
                    errors.append('Tab1 缺少搜索按钮 #textSearchBtn')
                else:
                    search_btn.click()
                    page.wait_for_timeout(800)
                    tab1_shot = os.path.join(screenshots_dir, 'playwright_clip_tab1_search.png')
                    page.screenshot(path=tab1_shot)
                    shots.append(tab1_shot)

            # Tab2 — image upload zone
            image_tab = page.locator('.tab[data-tab="image"]')
            if image_tab.count() == 0:
                errors.append('缺少「以图搜图」Tab')
            else:
                image_tab.click()
                page.wait_for_timeout(300)
                drop = page.locator('#imageDrop')
                if drop.count() == 0:
                    errors.append('Tab2 缺少上传区域 #imageDrop')
                else:
                    tab2_shot = os.path.join(screenshots_dir, 'playwright_clip_tab2_upload.png')
                    page.screenshot(path=tab2_shot)
                    shots.append(tab2_shot)

            # Tab4 — API docs
            api_tab = page.locator('.tab[data-tab="api"]')
            if api_tab.count() == 0:
                errors.append('缺少「API & 导出」Tab')
            else:
                api_tab.click()
                page.wait_for_timeout(300)
                content = page.content()
                if '/search/text' not in content:
                    errors.append('Tab4 未展示 /search/text API 文档')
                if '/search/image' not in content:
                    errors.append('Tab4 未展示 /search/image API 文档')
                tab4_shot = os.path.join(screenshots_dir, 'playwright_clip_tab4_api.png')
                page.screenshot(path=tab4_shot)
                shots.append(tab4_shot)

            browser.close()
    except Exception as e:
        errors.append(f'Playwright 检索站 Tab 检查失败: {e}')

    return len(errors) == 0, errors, shots


def _http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _http_get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read().decode('utf-8', errors='replace')
