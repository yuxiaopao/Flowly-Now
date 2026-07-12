"""
Classification website generator.
Generates a complete full-stack website for image/text classification models.
"""

import os
import json
from .base import BaseGenerator
from .modern_templates import get_modern_css_block


class ClassificationGenerator(BaseGenerator):
    """
    Generates a complete classification website:
    - Vue 3 frontend with drag-drop upload and prediction display
    - Flask backend with model inference endpoint
    - Docker configuration
    """

    def generate_frontend(self) -> list:
        """Generate Vue 3 frontend files."""
        files = []
        title = self.get_site_title()
        subtitle = self.get_site_subtitle()
        primary = self.get_primary_color()
        upload_hint = self.get_upload_hint()
        disclaimer_html = self.get_disclaimer_html()
        disclaimer_css = ''
        if disclaimer_html:
            disclaimer_css = (
                '    .site-disclaimer { padding: 16px 40px; font-size: 12px; color: #71717a; '
                'border-top: 1px solid #2e2e42; text-align: center; }\n'
            )
        display_names = self.profile.get('class_display_names') or {}
        label_map_js = json.dumps(display_names, ensure_ascii=False)

        # package.json
        pkg = {
            "name": f"{self.name.lower().replace(' ', '-')}-frontend",
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "vue": "^3.4.0",
                "axios": "^1.6.0",
                "element-plus": "^2.5.0"
            },
            "devDependencies": {
                "@vitejs/plugin-vue": "^5.0.0",
                "vite": "^5.0.0"
            }
        }
        files.append(self._write_file('frontend/package.json', json.dumps(pkg, indent=2, ensure_ascii=False)))

        # vite.config.js
        vite_config = """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/predict': {
        target: 'http://localhost:""" + str(self.port) + """',
        changeOrigin: true,
      }
    }
  }
})
"""
        files.append(self._write_file('frontend/vite.config.js', vite_config))

        modern_css = get_modern_css_block().replace('--site-primary, #f59e0b', primary)
        index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>""" + title + """</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root { --site-primary: """ + primary + """; --color-primary: """ + primary + """; }
""" + modern_css + """
    #app { min-height: 100vh; display: flex; flex-direction: column; flex: 1; }
    .header, .site-header { padding: 24px 40px; border-bottom: 1px solid var(--color-border, #2e2e42); }
    .header h1, .site-header h1 { font-size: 24px; font-weight: 700; color: var(--color-primary, """ + primary + """); }
    .header p, .site-header p { color: var(--color-text-muted, #a1a1aa); font-size: 14px; margin-top: 4px; }
    .main, .site-main { flex: 1; padding: 40px; display: flex; flex-direction: column; align-items: center; gap: 24px; max-width: 960px; margin: 0 auto; width: 100%; }
    .upload-zone { max-width: 600px; padding: 60px; }
    .upload-zone p { color: var(--color-text-muted, #a1a1aa); font-size: 16px; }
    .upload-zone .hint { font-size: 12px; margin-top: 8px; color: #71717a; }
    .result-card { width: 100%; max-width: 600px; background: var(--color-surface, #18181f); border: 1px solid var(--color-border, #2e2e42); border-radius: 12px; padding: 24px; }
    .result-card h3 { font-size: 14px; color: #a1a1aa; margin-bottom: 16px; }
    .prediction-label { font-size: 32px; font-weight: 700; color: """ + primary + """; }
    .confidence { font-size: 14px; color: #a1a1aa; margin: 8px 0 16px; }
    .bar-container { display: flex; flex-direction: column; gap: 8px; }
    .bar-row { display: flex; align-items: center; gap: 12px; }
    .bar-label { width: 80px; font-size: 13px; color: #a1a1aa; text-align: right; }
    .bar-track { flex: 1; height: 24px; background: #2e2e42; border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; background: """ + primary + """; border-radius: 4px; transition: width 0.5s ease; display: flex; align-items: center; padding-left: 8px; font-size: 12px; font-weight: 600; color: white; }
    .bar-value { width: 50px; font-size: 13px; color: #f4f4f5; font-family: monospace; }
    .preview-img { max-width: 100%; max-height: 300px; border-radius: 8px; margin-bottom: 16px; }
    .loading { color: """ + primary + """; }
    input[type="file"] { display: none; }
""" + disclaimer_css + """
  </style>
</head>
<body>
  <div id="app">
    <div class="header">
      <h1>""" + title + """</h1>
      <p>""" + subtitle + """</p>
    </div>
    <div class="main">
      <div class="upload-zone" :class="{dragover: isDragover}" @click="$refs.fileInput.click()" @dragover.prevent="isDragover=true" @dragleave="isDragover=false" @drop.prevent="handleDrop">
        <input type="file" ref="fileInput" @change="handleFileSelect" accept="image/*" />
        <p>""" + upload_hint + """</p>
        <p class="hint">支持 JPG, PNG, WEBP 格式</p>
      </div>
      <div v-if="imageUrl" class="result-card">
        <h3>分类结果</h3>
        <img v-if="imageUrl" :src="imageUrl" class="preview-img" />
        <div v-if="loading" class="loading">正在分析...</div>
        <div v-else-if="result">
          <div class="prediction-label">{{ result.label }}</div>
          <div class="confidence">置信度: {{ (result.confidence * 100).toFixed(1) }}%</div>
          <div class="bar-container">
            <div v-for="(prob, label) in result.probabilities" :key="label" class="bar-row">
              <span class="bar-label">{{ label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{width: (prob * 100) + '%'}">{{ (prob * 100).toFixed(0) }}%</div>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="error" style="color: #ef4444;">{{ error }}</div>
      </div>
    </div>
    """ + disclaimer_html + """
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>
  <script>
    const LABEL_DISPLAY = """ + label_map_js + """
    const displayLabel = (k) => LABEL_DISPLAY[k] || k
    const { createApp, ref } = Vue
    createApp({
      setup() {
        const imageUrl = ref('')
        const isDragover = ref(false)
        const loading = ref(false)
        const result = ref(null)
        const error = ref('')
        const API_URL = '/predict'
        function handleFileSelect(e) { const f = e.target.files[0]; if (f) processFile(f) }
        function handleDrop(e) { isDragover.value = false; const f = e.dataTransfer.files[0]; if (f) processFile(f) }
        function processFile(file) {
          imageUrl.value = URL.createObjectURL(file)
          loading.value = true; result.value = null; error.value = ''
          const formData = new FormData()
          formData.append('file', file)
          axios.post(API_URL, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
            .then(r => {
              const data = r.data
              if (data.label) data.label = displayLabel(data.label)
              if (data.probabilities) {
                const mapped = {}
                for (const [k, v] of Object.entries(data.probabilities)) {
                  mapped[displayLabel(k)] = v
                }
                data.probabilities = mapped
              }
              result.value = data
              loading.value = false
            })
            .catch(e => { error.value = (e.response && e.response.data && e.response.data.error) || e.message || '请求失败'; loading.value = false })
        }
        return { imageUrl, isDragover, loading, result, error, handleFileSelect, handleDrop }
      }
    }).mount('#app')
  </script>
</body>
</html>
"""
        files.append(self._write_file('frontend/index.html', index_html))
        return files

    def generate_backend(self) -> list:
        """Generate Flask backend files."""
        if self.framework == 'clip':
            return self._generate_clip_classification_backend()
        return self._generate_pytorch_classification_backend()

    def _generate_clip_classification_backend(self) -> list:
        """CLIP zero-shot / finetune classification site backend (M4.7)."""
        files = []
        reqs = [
            'flask>=3.0.0',
            'flask-cors>=4.0.0',
            'torch>=2.0.0',
            'pillow>=10.0.0',
            'numpy>=1.24.0',
            'ftfy',
            'regex',
            'tqdm',
            'git+https://github.com/openai/CLIP.git',
        ]
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))

        import json as _json
        model_dir = self.model_path
        if model_dir and os.path.isdir(model_dir):
            manifest_src = os.path.join(model_dir, 'manifest.json')
            model_src = os.path.join(model_dir, 'clip.pt')
            if not os.path.isfile(manifest_src):
                manifest_src = os.path.join(model_dir, 'clip_zero_shot.json')
        else:
            manifest_src = self.model_path if (self.model_path or '').endswith('.json') else ''
            model_src = self.model_path if (self.model_path or '').endswith('.pt') else ''

        cfg = {
            'model_path': 'clip.pt',
            'manifest_path': 'manifest.json',
            'labels': self.labels,
            'framework': 'clip',
            'port': self.port,
            'mode': 'zero_shot',
        }
        files.append(self._write_file('backend/config.json', _json.dumps(cfg, indent=2)))

        if manifest_src and os.path.isfile(manifest_src):
            with open(manifest_src, encoding='utf-8') as mf:
                files.append(self._write_file('backend/manifest.json', mf.read()))
        else:
            prompts = [f'a photo of a {l}' for l in (self.labels or ['class_a', 'class_b'])]
            files.append(self._write_file('backend/manifest.json', _json.dumps({
                'mode': 'zero_shot',
                'class_names': self.labels,
                'text_prompts': prompts,
                'base_model': 'ViT-B/32',
            }, ensure_ascii=False, indent=2)))

        if model_src and os.path.isfile(model_src):
            import shutil
            dest = os.path.join(self.output_dir, 'backend', 'clip.pt')
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(model_src, dest)

        app_py = f'''import io
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, encoding='utf-8') as f:
    CONFIG = json.load(f)

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), CONFIG.get('manifest_path', 'manifest.json'))
MODEL_PATH = os.path.join(os.path.dirname(__file__), CONFIG.get('model_path', 'clip.pt'))
LABELS = CONFIG.get('labels', [])
PORT = CONFIG.get('port', {self.port})

CLIP_MODEL = None
CLIP_PREPROCESS = None
CLIP_DEVICE = 'cpu'
MANIFEST = {{}}
TEXT_PROMPTS = []


def _load_manifest():
    global MANIFEST, TEXT_PROMPTS, LABELS
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding='utf-8') as f:
            MANIFEST = json.load(f)
    TEXT_PROMPTS = MANIFEST.get('text_prompts') or [f"a photo of a {{n}}" for n in (MANIFEST.get('class_names') or LABELS)]
    if not LABELS:
        LABELS = MANIFEST.get('class_names') or []


def _load_clip():
    global CLIP_MODEL, CLIP_PREPROCESS, CLIP_DEVICE
    if CLIP_MODEL is not None:
        return True
    try:
        import clip
        import torch
        base_model = MANIFEST.get('base_model') or 'ViT-B/32'
        CLIP_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
        CLIP_MODEL, CLIP_PREPROCESS = clip.load(base_model, device=CLIP_DEVICE)
        CLIP_MODEL.eval()
        return True
    except Exception as exc:
        print(f'CLIP load failed: {{exc}}')
        return False


def predict_demo():
    labels = LABELS or ['ClassA', 'ClassB', 'ClassC']
    probs = {{l: max(0.05, 0.3 + (hash(l) % 50) / 200) for l in labels}}
    total = sum(probs.values())
    probs = {{k: round(v / total, 4) for k, v in probs.items()}}
    best = max(probs, key=probs.get)
    return {{'label': best, 'confidence': probs[best], 'probabilities': probs, 'mode': 'demo'}}


def predict_clip_image(img: Image.Image):
    import clip
    import torch
    import torch.nn.functional as F
    labels = LABELS or MANIFEST.get('class_names') or []
    prompts = TEXT_PROMPTS or [f"a photo of a {{n}}" for n in labels]
    if not prompts:
        return predict_demo()
    tensor = CLIP_PREPROCESS(img).unsqueeze(0).to(CLIP_DEVICE)
    tokens = clip.tokenize(prompts, truncate=True).to(CLIP_DEVICE)
    with torch.no_grad():
        image_features = CLIP_MODEL.encode_image(tensor)
        text_features = CLIP_MODEL.encode_text(tokens)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        logits = (100.0 * image_features @ text_features.T)[0]
        probs = F.softmax(logits, dim=0).cpu().tolist()
    pairs = list(zip(labels or [f'class_{{i}}' for i in range(len(probs))], probs))
    best_label, best_prob = max(pairs, key=lambda x: x[1])
    return {{
        'label': best_label,
        'confidence': round(float(best_prob), 4),
        'probabilities': {{k: round(float(v), 4) for k, v in pairs}},
        'mode': 'zero_shot',
    }}


@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({{'error': 'No file provided'}}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({{'error': 'Empty filename'}}), 400
    try:
        img = Image.open(file.stream).convert('RGB')
        if _load_clip():
            result = predict_clip_image(img)
        else:
            result = predict_demo()
        return jsonify(result)
    except Exception as e:
        return jsonify({{'error': f'Prediction failed: {{str(e)}}'}}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({{
        'status': 'ok',
        'website_type': 'classification',
        'framework': 'clip',
        'model_loaded': CLIP_MODEL is not None,
        'labels': LABELS,
        'mode': MANIFEST.get('mode', 'zero_shot'),
    }})


@app.route('/labels', methods=['GET'])
def get_labels():
    return jsonify({{'labels': LABELS, 'prompts': TEXT_PROMPTS}})


if __name__ == '__main__':
    _load_manifest()
    _load_clip()
    print(f'Starting CLIP classification server on port {{PORT}}...')
    app.run(host='0.0.0.0', port=PORT, debug=False)
'''
        files.append(self._write_file('backend/app.py', app_py))
        files.append(self._write_file('backend/Dockerfile', '\n'.join([
            'FROM python:3.10-slim',
            'WORKDIR /app',
            'RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*',
            'COPY requirements.txt .',
            'RUN pip install -r requirements.txt --no-cache-dir',
            'COPY . .',
            f'EXPOSE {self.port}',
            'CMD ["python", "app.py"]',
        ])))
        files.append(self._write_file('backend/.env.example', '\n'.join([
            'MODEL_PATH=clip.pt',
            'MANIFEST_PATH=manifest.json',
            f'PORT={self.port}',
            'FRAMEWORK=clip',
        ])))
        files.extend(self.write_db_scaffold())
        return files

    def _generate_pytorch_classification_backend(self) -> list:
        """Standard PyTorch classifier backend."""
        files = []

        # requirements.txt
        reqs = ["flask>=3.0.0", "flask-cors>=4.0.0", "torch>=2.0.0", "pillow>=10.0.0", "numpy>=1.24.0"]
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))

        # config.json
        import json as _json
        cfg = {
            'model_path': self.model_path,
            'labels': self.labels,
            'framework': self.framework,
            'port': self.port,
        }
        files.append(self._write_file('backend/config.json', _json.dumps(cfg, indent=2)))

        # app.py - Flask inference server
        app_py_lines = [
            "import os",
            "import json",
            "import torch",
            "import numpy as np",
            "from PIL import Image",
            "from flask import Flask, request, jsonify",
            "from flask_cors import CORS",
            "",
            "app = Flask(__name__)",
            "CORS(app)",
            "",
            "CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')",
            "with open(CONFIG_PATH) as f:",
            "    CONFIG = json.load(f)",
            "",
            "MODEL_PATH = CONFIG.get('model_path', 'model.pth')",
            "LABELS = CONFIG.get('labels', [])",
            "FRAMEWORK = CONFIG.get('framework', 'pytorch')",
            "PORT = CONFIG.get('port', " + str(self.port) + ")",
            "",
            "model = None",
            "transform = None",
            "",
            "def load_model():",
            "    global model, transform",
            "    try:",
            "        import torchvision.transforms as T",
            "        transform = T.Compose([",
            "            T.Resize((224, 224)),",
            "            T.ToTensor(),",
            "            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])",
            "        ])",
            "",
            "        if FRAMEWORK == 'pytorch':",
            "            state = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)",
            "            model = state.get('model_state_dict', state) if isinstance(state, dict) else state",
            "            model.eval()",
            "        else:",
            '            print(f"Warning: Framework {FRAMEWORK} not implemented, using demo mode.")',
            "            model = None",
            '        print(f"Model loaded. Labels: {LABELS}")',
            "    except FileNotFoundError:",
            '        print(f"Model file not found at {MODEL_PATH}. Using demo mode.")',
            "        model = None",
            "    except Exception as e:",
            f'        print(f"Could not load model: {{e}}. Using demo mode.")',
            "        model = None",
            "",
            "def preprocess_image(file_storage):",
            '    """Preprocess uploaded image for the model."""',
            "    img = Image.open(file_storage).convert('RGB')",
            "    if transform:",
            "        return img, transform(img).unsqueeze(0)",
            "    return img, None",
            "",
            "def predict_demo():",
            "    n = len(LABELS) if LABELS else 3",
            "    probs = {l: max(0.05, 0.3 + (hash(l) % 50) / 200) for l in (LABELS or ['ClassA', 'ClassB', 'ClassC'])}",
            "    total = sum(probs.values())",
            "    probs = {k: round(v / total, 4) for k, v in probs.items()}",
            "    best = max(probs, key=probs.get)",
            "    return {'label': best, 'confidence': round(probs[best], 4), 'probabilities': probs}",
            "",
            "@app.route('/predict', methods=['POST'])",
            "def predict():",
            "    if 'file' not in request.files:",
            "        return jsonify({'error': 'No file provided'}), 400",
            "    file = request.files['file']",
            "    if not file.filename:",
            "        return jsonify({'error': 'Empty filename'}), 400",
            "    try:",
            "        img, img_tensor = preprocess_image(file)",
            "        if model is None:",
            "            result = predict_demo()",
            "        elif FRAMEWORK == 'pytorch' and img_tensor is not None:",
            "            with torch.no_grad():",
            "                output = model(img_tensor)",
            "                probs = torch.softmax(output[0], dim=0)",
            "                top_prob, top_idx = torch.max(probs, dim=0)",
            "                result = {",
            "                    'label': LABELS[top_idx.item()] if LABELS else str(top_idx.item()),",
            "                    'confidence': round(top_prob.item(), 4),",
            "                    'probabilities': {LABELS[i]: round(probs[i].item(), 4) for i in range(len(LABELS))} if LABELS else {}",
            "                }",
            "        else:",
            "            result = predict_demo()",
            "        return jsonify(result)",
            "    except Exception as e:",
            "        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500",
            "",
            "@app.route('/health', methods=['GET'])",
            "def health():",
            "    return jsonify({'status': 'ok', 'model_loaded': model is not None, 'labels': LABELS})",
            "",
            "@app.route('/labels', methods=['GET'])",
            "def get_labels():",
            "    return jsonify({'labels': LABELS})",
            "",
            "if __name__ == '__main__':",
            "    load_model()",
            f"    print(f'Starting inference server on port {self.port}...')",
            "    app.run(host='0.0.0.0', port=PORT, debug=False)",
        ]
        files.append(self._write_file('backend/app.py', '\n'.join(app_py_lines)))

        # Dockerfile for GPU inference
        dockerfile = [
            "FROM python:3.10-slim",
            "WORKDIR /app",
            "COPY requirements.txt .",
            "RUN pip install -r requirements.txt --no-cache-dir",
            "COPY . .",
            "EXPOSE " + str(self.port),
            "CMD [\"python\", \"app.py\"]",
        ]
        files.append(self._write_file('backend/Dockerfile', '\n'.join(dockerfile)))

        # .env.example
        env_example = [
            "MODEL_PATH=model.pth",
            "LABELS=cat,dog,bird",
            "PORT=" + str(self.port),
            "FRAMEWORK=pytorch",
        ]
        files.append(self._write_file('backend/.env.example', '\n'.join(env_example)))

        files.extend(self.write_db_scaffold())
        return files
