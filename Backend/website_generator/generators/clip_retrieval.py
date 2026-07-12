"""
CLIP retrieval website generator (M4).
Four-tab UI: text search, image search, gallery, API docs.
"""

import json
import os
import shutil
from .base import BaseGenerator

SEARCH_SCHEMA_EXTRA = """
CREATE TABLE IF NOT EXISTS search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    query_type TEXT,
    query_summary TEXT,
    result_count INTEGER,
    latency_ms REAL
);
"""

SEARCH_SCHEMA_EXTRA_MYSQL = """
CREATE TABLE IF NOT EXISTS search_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at VARCHAR(64) NOT NULL,
    query_type VARCHAR(64),
    query_summary TEXT,
    result_count INT,
    latency_ms DOUBLE
);
"""


class ClipRetrievalGenerator(BaseGenerator):
    """Generates CLIP retrieval demo site with /search/* APIs."""

    def __init__(self, config):
        super().__init__(config)
        self.index_dir = config.get('index_dir') or config.get('indexDir') or ''
        self.metrics = config.get('metrics') or {}
        self.base_model = config.get('base_model') or config.get('baseModel') or 'simple-bow'
        wizard = config.get('wizard') or {}
        self.top_k = int(wizard.get('topK') or wizard.get('top_k') or config.get('top_k') or 12)

    def get_upload_hint(self) -> str:
        hints = self.profile.get('copy_hints') or []
        if hints:
            return str(hints[0])
        return '输入描述文字，搜索相似图片'

    def _copy_index(self, backend_dir: str) -> str:
        index_dest = os.path.join(backend_dir, 'index')
        os.makedirs(index_dest, exist_ok=True)
        if self.index_dir and os.path.isdir(self.index_dir):
            for name in os.listdir(self.index_dir):
                src = os.path.join(self.index_dir, name)
                dst = os.path.join(index_dest, name)
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        return index_dest

    def generate_frontend(self) -> list:
        files = []
        title = self.get_site_title()
        subtitle = self.get_site_subtitle()
        primary = self.get_primary_color()
        disclaimer_html = self.get_disclaimer_html()
        example_queries = self.profile.get('copy_hints') or ['一只橘猫', '工业现场', '商品展示']
        examples_json = json.dumps(example_queries[:3], ensure_ascii=False)
        top_k = self.top_k

        index_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f14; color: #f4f4f5; min-height: 100vh; }}
    .header {{ padding: 20px 32px; border-bottom: 1px solid #2e2e42; }}
    .header h1 {{ font-size: 22px; color: {primary}; }}
    .header p {{ color: #a1a1aa; font-size: 13px; margin-top: 4px; }}
    .metrics {{ display: flex; gap: 16px; padding: 12px 32px; font-size: 12px; color: #71717a; border-bottom: 1px solid #2e2e42; flex-wrap: wrap; }}
    .metrics span strong {{ color: {primary}; }}
    .tabs {{ display: flex; gap: 4px; padding: 12px 32px; border-bottom: 1px solid #2e2e42; }}
    .tab {{ padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; color: #a1a1aa; background: transparent; border: none; }}
    .tab.active {{ background: {primary}22; color: {primary}; }}
    .panel {{ display: none; padding: 24px 32px; }}
    .panel.active {{ display: block; }}
    .search-row {{ display: flex; gap: 8px; max-width: 640px; margin-bottom: 16px; }}
    .search-row input {{ flex: 1; padding: 10px 14px; border-radius: 8px; border: 1px solid #2e2e42; background: #18181f; color: #f4f4f5; }}
    .btn {{ padding: 10px 18px; border-radius: 8px; border: none; background: {primary}; color: #000; font-weight: 600; cursor: pointer; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }}
    .card {{ background: #18181f; border: 1px solid #2e2e42; border-radius: 10px; overflow: hidden; }}
    .card img {{ width: 100%; aspect-ratio: 1; object-fit: cover; background: #0a0a0f; }}
    .card .meta {{ padding: 8px; font-size: 11px; }}
    .score {{ color: {primary}; font-weight: 600; }}
    .upload-zone {{ border: 2px dashed #2e2e42; border-radius: 12px; padding: 40px; text-align: center; max-width: 480px; cursor: pointer; }}
    .upload-zone:hover {{ border-color: {primary}; }}
    .api-block {{ background: #18181f; border: 1px solid #2e2e42; border-radius: 8px; padding: 16px; margin-bottom: 12px; font-size: 13px; }}
    .api-block code {{ color: {primary}; }}
    pre {{ background: #0a0a0f; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; margin-top: 8px; }}
    .site-disclaimer {{ padding: 16px 32px; font-size: 12px; color: #71717a; border-top: 1px solid #2e2e42; text-align: center; }}
    .empty {{ color: #71717a; font-size: 14px; padding: 24px 0; }}
  </style>
</head>
<body>
  <header class="header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </header>
  <div class="metrics" id="statsBar">加载统计…</div>
  <nav class="tabs">
    <button class="tab active" data-tab="text">文本搜图</button>
    <button class="tab" data-tab="image">以图搜图</button>
    <button class="tab" data-tab="gallery">图库浏览</button>
    <button class="tab" data-tab="api">API & 导出</button>
  </nav>

  <section class="panel active" id="panel-text">
    <div class="search-row">
      <input id="textQuery" placeholder="输入搜索描述，例如：{example_queries[0] if example_queries else '关键词'}" />
      <button class="btn" id="textSearchBtn">搜索</button>
    </div>
    <p class="empty" id="textHint">示例：{', '.join(example_queries[:3])}</p>
    <div class="grid" id="textResults"></div>
  </section>

  <section class="panel" id="panel-image">
    <div class="upload-zone" id="imageDrop">
      <p>点击或拖拽上传图片</p>
      <input type="file" id="imageFile" accept="image/*" hidden />
    </div>
    <div class="grid" id="imageResults" style="margin-top:16px"></div>
  </section>

  <section class="panel" id="panel-gallery">
    <div class="search-row">
      <input id="galleryFilter" placeholder="过滤 filename / caption" />
      <button class="btn" id="galleryBtn">刷新</button>
    </div>
    <div class="grid" id="galleryGrid"></div>
  </section>

  <section class="panel" id="panel-api">
    <div class="api-block"><strong>POST</strong> <code>/search/text</code> — 文本搜图</div>
    <div class="api-block"><strong>POST</strong> <code>/search/image</code> — 以图搜图（multipart）</div>
    <div class="api-block"><strong>GET</strong> <code>/gallery</code> — 分页图库</div>
    <div class="api-block"><strong>GET</strong> <code>/stats</code> — 索引统计</div>
    <pre id="curlExample">curl -X POST http://127.0.0.1:PORT/search/text \\
  -H "Content-Type: application/json" \\
  -d '{{"query":"示例","top_k":{top_k}}}'</pre>
  </section>

  {disclaimer_html}

  <script>
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.panel');
    tabs.forEach(t => t.addEventListener('click', () => {{
      tabs.forEach(x => x.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      t.classList.add('active');
      document.getElementById('panel-' + t.dataset.tab).classList.add('active');
    }}));

    function renderGrid(el, results) {{
      el.innerHTML = '';
      if (!results || !results.length) {{
        el.innerHTML = '<p class="empty">暂无结果</p>';
        return;
      }}
      results.forEach(r => {{
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<img src="${{r.image_url}}" alt="" /><div class="meta"><div class="score">${{(r.score*100).toFixed(1)}}%</div><div>${{r.caption || ''}}</div></div>`;
        el.appendChild(card);
      }});
    }}

    async function loadStats() {{
      try {{
        const res = await fetch('/stats');
        const data = await res.json();
        const m = data.metrics || {{}};
        document.getElementById('statsBar').innerHTML =
          `<span>索引 <strong>${{data.vector_count || 0}}</strong></span>` +
          `<span>模型 <strong>${{data.model || '-'}}</strong></span>` +
          `<span>R@5 <strong>${{((m.r_at_5||0)*100).toFixed(0)}}%</strong></span>`;
      }} catch (e) {{ document.getElementById('statsBar').textContent = '统计加载失败'; }}
    }}

    document.getElementById('textSearchBtn').addEventListener('click', async () => {{
      const q = document.getElementById('textQuery').value.trim();
      if (!q) return;
      const res = await fetch('/search/text', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ query: q, top_k: {top_k} }}) }});
      const data = await res.json();
      renderGrid(document.getElementById('textResults'), data.results);
      document.getElementById('textHint').textContent = '';
    }});

    const drop = document.getElementById('imageDrop');
    const fileInput = document.getElementById('imageFile');
    drop.addEventListener('click', () => fileInput.click());
    drop.addEventListener('dragover', e => {{ e.preventDefault(); drop.classList.add('dragover'); }});
    drop.addEventListener('drop', e => {{ e.preventDefault(); uploadImage(e.dataTransfer.files[0]); }});
    fileInput.addEventListener('change', e => uploadImage(e.target.files[0]));

    async function uploadImage(file) {{
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      fd.append('top_k', '{top_k}');
      const res = await fetch('/search/image', {{ method: 'POST', body: fd }});
      const data = await res.json();
      renderGrid(document.getElementById('imageResults'), data.results);
    }}

    async function loadGallery() {{
      const filter = document.getElementById('galleryFilter').value.trim();
      const url = '/gallery?page=1&page_size=24' + (filter ? '&q=' + encodeURIComponent(filter) : '');
      const res = await fetch(url);
      const data = await res.json();
      renderGrid(document.getElementById('galleryGrid'), (data.items || []).map(i => ({{
        image_url: i.image_url, score: 1, caption: i.caption
      }})));
    }}
    document.getElementById('galleryBtn').addEventListener('click', loadGallery);

    loadStats();
    loadGallery();
  </script>
</body>
</html>
"""
        files.append(self._write_file('frontend/index.html', index_html))
        return files

    def generate_backend(self) -> list:
        files = []
        backend_dir = os.path.join(self.output_dir, 'backend')
        self._copy_index(backend_dir)

        reqs = [
            'flask==3.0.3',
            'flask-cors==4.0.1',
            'pillow>=10.0.0',
            'numpy>=1.24.0',
        ]
        encoder = 'bow'
        meta_path = os.path.join(backend_dir, 'index', 'metadata.json')
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, encoding='utf-8') as mf:
                    encoder = json.load(mf).get('encoder', 'bow')
            except Exception:
                pass
        if encoder == 'clip':
            reqs.extend([
                'torch>=2.0.0',
                'ftfy',
                'regex',
                'tqdm',
                'git+https://github.com/openai/CLIP.git',
            ])
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))
        files.extend(self.write_db_scaffold(
            extra_sql=SEARCH_SCHEMA_EXTRA,
            extra_sql_mysql=SEARCH_SCHEMA_EXTRA_MYSQL,
        ))

        cfg = {
            'index_dir': 'index',
            'model': self.base_model,
            'port': self.port,
            'website_type': 'clip_retrieval',
            'metrics': self.metrics,
            'model_path': '',
        }
        files.append(self._write_file('backend/config.json', json.dumps(cfg, indent=2)))

        app_py = '''
import json
import math
import os
import re
import time
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = os.path.join(BASE, 'index')
CONFIG_PATH = os.path.join(BASE, 'config.json')
FRONTEND_DIR = os.path.join(BASE, '..', 'frontend')

with open(CONFIG_PATH, encoding='utf-8') as f:
    CONFIG = json.load(f)

PORT = int(os.environ.get('FLASK_RUN_PORT', CONFIG.get('port', ''' + str(self.port) + ''')))

META = {}
VOCAB = {}
VECTORS = []
ENCODER = 'bow'
CLIP_MODEL = None
CLIP_PREPROCESS = None
CLIP_DEVICE = 'cpu'


def _tokenize(text):
    text = (text or '').lower().strip()
    tokens = re.findall(r'[\\u4e00-\\u9fff]+|[a-z0-9]+', text)
    chars = list(text.replace(' ', ''))
    return tokens + [c for c in chars if c.strip()]


def _embed(text, vocab):
    vec = [0.0] * max(len(vocab), 1)
    for tok in _tokenize(text):
        idx = vocab.get(tok)
        if idx is not None:
            vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a, b):
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def load_index():
    global META, VOCAB, VECTORS, ENCODER, CLIP_MODEL, CLIP_PREPROCESS, CLIP_DEVICE
    meta_path = os.path.join(INDEX_DIR, 'metadata.json')
    vocab_path = os.path.join(INDEX_DIR, 'vocab.json')
    vec_npy = os.path.join(INDEX_DIR, 'vectors.npy')
    vec_json = os.path.join(INDEX_DIR, 'vectors.json')
    with open(meta_path, encoding='utf-8') as f:
        META = json.load(f)
    ENCODER = META.get('encoder') or 'bow'
    if os.path.isfile(vocab_path):
        with open(vocab_path, encoding='utf-8') as f:
            VOCAB = json.load(f)
    else:
        VOCAB = {}
    if os.path.isfile(vec_npy):
        import numpy as np
        VECTORS = np.load(vec_npy).tolist()
    elif os.path.isfile(vec_json):
        with open(vec_json, encoding='utf-8') as f:
            VECTORS = json.load(f)
    else:
        VECTORS = []


def _load_clip():
    global CLIP_MODEL, CLIP_PREPROCESS, CLIP_DEVICE
    if CLIP_MODEL is not None:
        return True
    try:
        import clip
        import torch
        model_name = META.get('model') or CONFIG.get('model') or 'ViT-B/32'
        CLIP_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
        CLIP_MODEL, CLIP_PREPROCESS = clip.load(model_name, device=CLIP_DEVICE)
        CLIP_MODEL.eval()
        return True
    except Exception:
        return False


def _query_vector_text(text):
    text = (text or '').strip()
    if not text:
        return _embed('', VOCAB)
    if ENCODER == 'clip' and _load_clip():
        try:
            import clip
            import torch
            tokens = clip.tokenize([text], truncate=True).to(CLIP_DEVICE)
            with torch.no_grad():
                feat = CLIP_MODEL.encode_text(tokens)
                feat = feat / feat.norm(dim=-1, keepdim=True)
            return feat.cpu().numpy()[0].tolist()
        except Exception:
            pass
    return _embed(text, VOCAB)


def _query_vector_image(file_storage):
    if ENCODER == 'clip' and _load_clip():
        try:
            import torch
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(file_storage.read())).convert('RGB')
            file_storage.stream.seek(0)
            tensor = CLIP_PREPROCESS(img).unsqueeze(0).to(CLIP_DEVICE)
            with torch.no_grad():
                feat = CLIP_MODEL.encode_image(tensor)
                feat = feat / feat.norm(dim=-1, keepdim=True)
            return feat.cpu().numpy()[0].tolist()
        except Exception:
            pass
    name = (file_storage.filename or 'image').rsplit('.', 1)[0]
    return _embed(name, VOCAB)


def search_by_vector(qvec, top_k=12):
    items = META.get('items', [])
    scored = []
    for i, item in enumerate(items):
        vec = VECTORS[i] if i < len(VECTORS) else _embed(item.get('caption', ''), VOCAB)
        score = _cosine(qvec, vec)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, item in scored[:top_k]:
        fn = item.get('filename') or item.get('id', '') + '.jpg'
        results.append({
            'id': item.get('id'),
            'score': round(float(score), 4),
            'image_url': f'/media/{fn}',
            'caption': item.get('caption') or item.get('text', ''),
        })
    return results


try:
    from db.init_db import init_db
    init_db()
except Exception:
    pass

load_index()


@app.route('/')
def index_page():
    if os.path.isfile(os.path.join(FRONTEND_DIR, 'index.html')):
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return jsonify({'health': '/health'})


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'website_type': 'clip_retrieval'})


@app.route('/stats')
def stats():
    return jsonify({
        'vector_count': META.get('vector_count', len(META.get('items', []))),
        'model': META.get('model') or CONFIG.get('model'),
        'encoder': ENCODER,
        'built_at': META.get('built_at'),
        'metrics': META.get('metrics') or CONFIG.get('metrics', {}),
    })


@app.route('/media/<path:filename>')
def media_file(filename):
    media_dir = os.path.join(INDEX_DIR, 'media')
    return send_from_directory(media_dir, filename)


@app.route('/search/text', methods=['POST'])
def search_text():
    started = time.time()
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()
    top_k = int(data.get('top_k') or 12)
    if not query:
        return jsonify({'error': 'query required'}), 400
    qvec = _query_vector_text(query)
    results = search_by_vector(qvec, top_k)
    return jsonify({'results': results, 'latency_ms': int((time.time() - started) * 1000)})


@app.route('/search/image', methods=['POST'])
def search_image():
    started = time.time()
    top_k = int(request.form.get('top_k') or 12)
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'file required'}), 400
    qvec = _query_vector_image(file)
    results = search_by_vector(qvec, top_k)
    return jsonify({'results': results, 'latency_ms': int((time.time() - started) * 1000)})


@app.route('/gallery')
def gallery():
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(48, max(1, int(request.args.get('page_size', 24))))
    q = (request.args.get('q') or '').lower()
    items = META.get('items', [])
    if q:
        items = [i for i in items if q in (i.get('caption') or '').lower() or q in (i.get('filename') or '').lower()]
    start = (page - 1) * page_size
    chunk = items[start:start + page_size]
    out = []
    for item in chunk:
        fn = item.get('filename') or item.get('id', '') + '.jpg'
        out.append({'id': item.get('id'), 'image_url': f'/media/{fn}', 'caption': item.get('caption', '')})
    return jsonify({'items': out, 'page': page, 'total': len(items)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
'''
        files.append(self._write_file('backend/app.py', app_py.strip() + '\n'))
        return files
