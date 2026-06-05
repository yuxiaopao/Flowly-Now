"""
Classification website generator.
Generates a complete full-stack website for image/text classification models.
"""

import os
from .base import BaseGenerator


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
        files.append(self._write_file('frontend/package.json', pkg, json_dump=True))

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

        # index.html
        index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>""" + self.name + """</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f14; color: #f4f4f5; min-height: 100vh; }
    #app { min-height: 100vh; display: flex; flex-direction: column; }
    .header { padding: 24px 40px; border-bottom: 1px solid #2e2e42; }
    .header h1 { font-size: 24px; font-weight: 700; color: #06b6d4; }
    .header p { color: #a1a1aa; font-size: 14px; margin-top: 4px; }
    .main { flex: 1; padding: 40px; display: flex; flex-direction: column; align-items: center; gap: 24px; }
    .upload-zone { width: 100%; max-width: 600px; border: 2px dashed #2e2e42; border-radius: 12px; padding: 60px; text-align: center; cursor: pointer; transition: all 0.2s; }
    .upload-zone:hover, .upload-zone.dragover { border-color: #06b6d4; background: rgba(6,182,212,0.05); }
    .upload-zone p { color: #a1a1aa; font-size: 16px; }
    .upload-zone .hint { font-size: 12px; margin-top: 8px; color: #71717a; }
    .result-card { width: 100%; max-width: 600px; background: #18181f; border: 1px solid #2e2e42; border-radius: 12px; padding: 24px; }
    .result-card h3 { font-size: 14px; color: #a1a1aa; margin-bottom: 16px; }
    .prediction-label { font-size: 32px; font-weight: 700; color: #06b6d4; }
    .confidence { font-size: 14px; color: #a1a1aa; margin: 8px 0 16px; }
    .bar-container { display: flex; flex-direction: column; gap: 8px; }
    .bar-row { display: flex; align-items: center; gap: 12px; }
    .bar-label { width: 80px; font-size: 13px; color: #a1a1aa; text-align: right; }
    .bar-track { flex: 1; height: 24px; background: #2e2e42; border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; background: #06b6d4; border-radius: 4px; transition: width 0.5s ease; display: flex; align-items: center; padding-left: 8px; font-size: 12px; font-weight: 600; color: white; }
    .bar-value { width: 50px; font-size: 13px; color: #f4f4f5; font-family: monospace; }
    .preview-img { max-width: 100%; max-height: 300px; border-radius: 8px; margin-bottom: 16px; }
    .loading { color: #f59e0b; }
    input[type="file"] { display: none; }
  </style>
</head>
<body>
  <div id="app">
    <div class="header">
      <h1>""" + self.name + """</h1>
      <p>""" + (self.description or 'AI-powered classification service') + """</p>
    </div>
    <div class="main">
      <div class="upload-zone" :class="{dragover: isDragover}" @click="$refs.fileInput.click()" @dragover.prevent="isDragover=true" @dragleave="isDragover=false" @drop.prevent="handleDrop">
        <input type="file" ref="fileInput" @change="handleFileSelect" accept="image/*" />
        <p>点击或拖拽上传图片进行分类</p>
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
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>
  <script>
    const { createApp, ref } = Vue
    createApp({
      setup() {
        const imageUrl = ref('')
        const isDragover = ref(false)
        const loading = ref(false)
        const result = ref(null)
        const error = ref('')
        const API_URL = 'http://localhost:""" + str(self.port) + """/predict'
        function handleFileSelect(e) { const f = e.target.files[0]; if (f) processFile(f) }
        function handleDrop(e) { isDragover.value = false; const f = e.dataTransfer.files[0]; if (f) processFile(f) }
        function processFile(file) {
          imageUrl.value = URL.createObjectURL(file)
          loading.value = true; result.value = null; error.value = ''
          const formData = new FormData()
          formData.append('file', file)
          axios.post(API_URL, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
            .then(r => { result.value = r.data; loading.value = false })
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

        return files

    def _write_file(self, rel_path, content, json_dump=False):
        """Write content to a file and return the path."""
        full_path = os.path.join(self.output_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            if json_dump:
                import json
                json.dump(content, f, indent=2, ensure_ascii=False)
            else:
                f.write(content)
        self.generated_files.append(full_path)
        return full_path
