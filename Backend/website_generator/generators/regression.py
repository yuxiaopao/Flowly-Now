"""
Regression website generator.
Generates a complete full-stack website for regression models.
"""

import os
from .base import BaseGenerator


class RegressionGenerator(BaseGenerator):
    """
    Generates a complete regression website:
    - Vue 3 frontend with input form and prediction display
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
                "dev": "vite --port 3000",
                "build": "vite build",
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
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f14; color: #f4f4f5; min-height: 100vh; }
    .header { padding: 24px 40px; border-bottom: 1px solid #2e2e42; }
    .header h1 { font-size: 24px; font-weight: 700; color: #10b981; }
    .header p { color: #a1a1aa; font-size: 14px; margin-top: 4px; }
    .main { padding: 40px; max-width: 700px; margin: 0 auto; }
    .form-card { background: #18181f; border: 1px solid #2e2e42; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
    .form-card h3 { font-size: 14px; color: #a1a1aa; margin-bottom: 16px; }
    .form-row { margin-bottom: 16px; }
    .form-row label { display: block; font-size: 13px; color: #a1a1aa; margin-bottom: 6px; }
    .form-row input { width: 100%; padding: 10px 14px; background: #0f0f14; border: 1px solid #2e2e42; border-radius: 6px; color: #f4f4f5; font-size: 14px; }
    .form-row input:focus { outline: none; border-color: #10b981; }
    .submit-btn { width: 100%; padding: 12px; background: #10b981; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
    .submit-btn:hover { background: #059669; }
    .result-card { background: #18181f; border: 1px solid #2e2e42; border-radius: 12px; padding: 24px; text-align: center; }
    .result-card h3 { font-size: 14px; color: #a1a1aa; margin-bottom: 12px; }
    .prediction-value { font-size: 48px; font-weight: 700; color: #10b981; }
    .prediction-unit { font-size: 18px; color: #a1a1aa; }
  </style>
</head>
<body>
  <div id="app">
    <div class="header">
      <h1>""" + self.name + """</h1>
      <p>""" + (self.description or 'AI-powered prediction service') + """</p>
    </div>
    <div class="main">
      <div class="form-card">
        <h3>输入特征</h3>
        <div class="form-row">
          <label>特征 1</label>
          <input v-model="features[0]" type="number" step="any" placeholder="输入数值" />
        </div>
        <div class="form-row">
          <label>特征 2</label>
          <input v-model="features[1]" type="number" step="any" placeholder="输入数值" />
        </div>
        <button class="submit-btn" @click="predict" :disabled="loading">
          {{ loading ? '预测中...' : '开始预测' }}
        </button>
      </div>
      <div v-if="result" class="result-card">
        <h3>预测结果</h3>
        <div class="prediction-value">
          {{ result.prediction.toFixed(2) }}
          <span class="prediction-unit">{{ result.unit || '' }}</span>
        </div>
      </div>
      <div v-if="error" style="color: #ef4444; text-align: center; margin-top: 12px;">{{ error }}</div>
    </div>
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>
  <script>
    const { createApp, ref } = Vue
    createApp({
      setup() {
        const features = ref([0, 0])
        const result = ref(null)
        const error = ref('')
        const loading = ref(false)
        const API = 'http://localhost:""" + str(self.port) + """'
        function predict() {
          loading.value = true; error.value = ''; result.value = null
          axios.post(API + '/predict', { features: features.value.map(Number) })
            .then(r => { result.value = r.data; loading.value = false })
            .catch(e => { error.value = e.response?.data?.error || e.message; loading.value = false })
        }
        return { features, result, error, loading, predict }
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

        reqs = ["flask>=3.0.0", "flask-cors>=4.0.0", "torch>=2.0.0", "numpy>=1.24.0"]
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))

        import json
        cfg = {'model_path': self.model_path, 'labels': self.labels, 'framework': self.framework, 'port': self.port}
        files.append(self._write_file('backend/config.json', json.dumps(cfg, indent=2), json_dump=False))

        app_py = """import os, json
from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
import numpy as np

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

MODEL_PATH = CONFIG.get('model_path', 'model.pth')
FRAMEWORK = CONFIG.get('framework', 'pytorch')
PORT = CONFIG.get('port', """ + str(self.port) + """)

model = None

def load_model():
    global model
    try:
        model = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
        if isinstance(model, dict) and 'model' in model:
            model = model['model']
        model.eval()
        print("Model loaded successfully.")
    except FileNotFoundError:
        print(f"Warning: Model file not found at {MODEL_PATH}. Demo mode.")
        model = None
    except Exception as e:
        print(f"Warning: Could not load model: {e}. Demo mode.")
        model = None

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    features = data.get('features', [])
    if not features:
        return jsonify({'error': 'No features provided'}), 400
    try:
        features = np.array(features, dtype=np.float32)
        if model is None:
            prediction = float(np.random.randn() * 10 + 50)
        else:
            x = torch.tensor(features).unsqueeze(0)
            with torch.no_grad():
                prediction = float(model(x).item())
        return jsonify({'prediction': round(prediction, 4), 'unit': ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model_loaded': model is not None})

if __name__ == '__main__':
    load_model()
    print(f"Starting regression server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
"""
        files.append(self._write_file('backend/app.py', app_py))
        return files

    def _write_file(self, rel_path, content, json_dump=False):
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
