"""
NLP Text Classification website generator.
Generates a complete full-stack website for NLP text classification models.
"""

import os
import json
from .base import BaseGenerator


class NLPGGenerator(BaseGenerator):
    """
    Generates a complete NLP classification website:
    - Vue 3 frontend with text input and prediction display
    - Flask backend with text classifier inference
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
        files.append(self._write_file('frontend/package.json', json.dumps(pkg, indent=2)))

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

        # index.html with NLP classification UI
        index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>""" + self.name + """</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f14; color: #f4f4f5; min-height: 100vh; }
    .header { padding: 24px 40px; border-bottom: 1px solid #2e2e42; }
    .header h1 { font-size: 24px; font-weight: 700; color: #8b5cf6; }
    .header p { color: #a1a1aa; font-size: 14px; margin-top: 4px; }
    .main { flex: 1; padding: 40px; display: flex; flex-direction: column; align-items: center; gap: 24px; }
    .input-card { width: 100%; max-width: 700px; background: #18181f; border: 1px solid #2e2e42; border-radius: 12px; padding: 24px; }
    .input-card h3 { font-size: 14px; color: #a1a1aa; margin-bottom: 16px; }
    .textarea-wrapper { position: relative; margin-bottom: 16px; }
    .text-input { width: 100%; min-height: 150px; padding: 16px; background: #0f0f14; border: 1px solid #2e2e42; border-radius: 8px; color: #f4f4f5; font-size: 15px; font-family: inherit; resize: vertical; transition: border-color 0.2s; }
    .text-input:focus { outline: none; border-color: #8b5cf6; }
    .text-input::placeholder { color: #71717a; }
    .char-count { position: absolute; bottom: 8px; right: 12px; font-size: 12px; color: #71717a; }
    .submit-btn { width: 100%; padding: 12px; background: #8b5cf6; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    .submit-btn:hover { background: #7c3aed; }
    .submit-btn:disabled { background: #4c1d95; cursor: not-allowed; }
    .result-card { width: 100%; max-width: 700px; background: #18181f; border: 1px solid #2e2e42; border-radius: 12px; padding: 24px; }
    .result-card h3 { font-size: 14px; color: #a1a1aa; margin-bottom: 16px; }
    .primary-prediction { display: flex; align-items: center; gap: 16px; padding: 16px; background: rgba(139,92,246,0.1); border-radius: 8px; margin-bottom: 20px; }
    .primary-label { font-size: 28px; font-weight: 700; color: #8b5cf6; }
    .primary-confidence { font-size: 18px; color: #f4f4f5; }
    .confidence-badge { padding: 4px 12px; background: #8b5cf6; border-radius: 12px; font-size: 13px; font-weight: 600; color: white; }
    .all-predictions { border-top: 1px solid #2e2e42; padding-top: 16px; }
    .all-predictions h4 { font-size: 13px; color: #a1a1aa; margin-bottom: 12px; }
    .prediction-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
    .prediction-label { width: 100px; font-size: 13px; color: #a1a1aa; text-align: right; }
    .bar-wrapper { flex: 1; height: 20px; background: #2e2e42; border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; display: flex; align-items: center; padding-left: 8px; font-size: 11px; font-weight: 600; color: white; }
    .prediction-value { width: 60px; font-size: 13px; color: #f4f4f5; font-family: monospace; }
    .loading { text-align: center; padding: 40px; color: #8b5cf6; }
    .error { text-align: center; padding: 20px; color: #ef4444; }
    .suggestions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .suggestion-btn { padding: 6px 12px; background: #2e2e42; border: none; border-radius: 6px; color: #a1a1aa; font-size: 12px; cursor: pointer; transition: all 0.2s; }
    .suggestion-btn:hover { background: #3e3e52; color: #f4f4f5; }
  </style>
</head>
<body>
  <div id="app">
    <div class="header">
      <h1>""" + self.name + """</h1>
      <p>""" + (self.description or 'AI-powered text classification service') + """</p>
    </div>
    <div class="main">
      <div class="input-card">
        <h3>输入文本</h3>
        <div class="textarea-wrapper">
          <textarea
            class="text-input"
            v-model="inputText"
            placeholder="请输入需要分类的文本内容..."
            @input="updateCharCount"
          ></textarea>
          <span class="char-count">{{ charCount }} / {{ maxChars }}</span>
        </div>
        <div class="suggestions">
          <button class="suggestion-btn" v-for="s in suggestions" :key="s" @click="inputText = s">{{ s }}</button>
        </div>
        <button class="submit-btn" :disabled="!inputText.trim() || loading" @click="classify">
          {{ loading ? '分析中...' : '开始分类' }}
        </button>
      </div>
      <div v-if="loading" class="result-card loading">正在分析文本...</div>
      <div v-else-if="error" class="result-card error">{{ error }}</div>
      <div v-else-if="result" class="result-card">
        <h3>分类结果</h3>
        <div class="primary-prediction">
          <span class="primary-label">{{ result.label }}</span>
          <span class="primary-confidence">置信度</span>
          <span class="confidence-badge">{{ (result.confidence * 100).toFixed(1) }}%</span>
        </div>
        <div class="all-predictions">
          <h4>各类别置信度</h4>
          <div v-for="(prob, label) in result.probabilities" :key="label" class="prediction-bar">
            <span class="prediction-label">{{ label }}</span>
            <div class="bar-wrapper">
              <div class="bar-fill" :style="{width: (prob * 100) + '%', background: getBarColor(prob)}">{{ (prob * 100).toFixed(1) }}%</div>
            </div>
            <span class="prediction-value">{{ (prob * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>
  <script>
    const { createApp, ref } = Vue
    createApp({
      setup() {
        const inputText = ref('')
        const charCount = ref(0)
        const maxChars = ref(5000)
        const loading = ref(false)
        const result = ref(null)
        const error = ref('')
        const API = 'http://localhost:""" + str(self.port) + """'
        const suggestions = ref(['这部电影真的很棒！', '服务态度太差了，非常失望', '产品还行，但价格有点贵'])
        const COLORS = ['#8b5cf6', '#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#ec4899']

        function updateCharCount() { charCount.value = inputText.value.length }
        function getBarColor(prob) { return COLORS[Math.floor(prob * COLORS.length)] || '#8b5cf6' }

        function classify() {
          if (!inputText.value.trim()) return
          loading.value = true; error.value = ''; result.value = null
          axios.post(API + '/predict', { text: inputText.value })
            .then(r => { result.value = r.data; loading.value = false })
            .catch(e => { error.value = (e.response?.data?.error) || e.message || '请求失败'; loading.value = false })
        }

        return { inputText, charCount, maxChars, loading, result, error, suggestions, updateCharCount, getBarColor, classify }
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
        reqs = ["flask>=3.0.0", "flask-cors>=4.0.0", "torch>=2.0.0", "numpy>=1.24.0"]
        if self.framework == 'transformers':
            reqs.append("transformers>=4.30.0")
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))

        # config.json
        cfg = {
            'model_path': self.model_path,
            'labels': self.labels,
            'framework': self.framework,
            'port': self.port,
            'model_type': 'nlp_classification'
        }
        files.append(self._write_file('backend/config.json', json.dumps(cfg, indent=2)))

        # app.py - Flask app with text classification
        app_py = """
import os
import json
import re
import torch
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

MODEL_PATH = CONFIG.get('model_path', 'model.pt')
LABELS = CONFIG.get('labels', [])
FRAMEWORK = CONFIG.get('framework', 'pytorch')
PORT = CONFIG.get('port', """ + str(self.port) + """)

model = None
tokenizer = None

def load_model():
    global model, tokenizer
    try:
        if FRAMEWORK == 'transformers':
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
            model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
        elif FRAMEWORK == 'pytorch':
            model = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
            if isinstance(model, dict) and 'model' in model:
                model = model['model']
        model.eval()
        print(f"Model loaded. Labels: {LABELS}")
    except Exception as e:
        print(f"Warning: Could not load model: {e}. Demo mode.")
        model = None

def preprocess_text(text):
    \'\'\'Basic text preprocessing.\'\'\'
    text = text.strip()
    text = re.sub(r'\\s+', ' ', text)
    text = text[:512]  # Truncate to max length
    return text

def predict_mock():
    \'\'\'Return mock predictions for demo.\'\'\'
    n = len(LABELS) if LABELS else 3
    default_labels = LABELS or ['Positive', 'Neutral', 'Negative']
    probs = {l: round(max(0, 0.2 + (hash(l) % 100) / 500), 4) for l in default_labels}
    total = sum(probs.values())
    probs = {k: round(v / total, 4) for k, v in probs.items()}
    return probs

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        text = preprocess_text(text)
        if model is None:
            probs = predict_mock()
        elif FRAMEWORK == 'transformers' and tokenizer:
            inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
            with torch.no_grad():
                outputs = model(**inputs)
            probs_tensor = torch.softmax(outputs.logits, dim=-1)[0]
            probs = {LABELS[i]: round(probs_tensor[i].item(), 4) for i in range(len(LABELS))}
        else:
            probs = predict_mock()

        # Sort by probability
        sorted_probs = dict(sorted(probs.items(), key=lambda x: x[1], reverse=True))
        top_label = max(probs, key=probs.get)
        top_conf = max(probs.values())

        return jsonify({
            'label': top_label,
            'confidence': round(top_conf, 4),
            'probabilities': sorted_probs,
            'model_info': {'framework': FRAMEWORK, 'labels': LABELS, 'model_loaded': model is not None}
        })
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model_loaded': model is not None, 'labels': LABELS})

@app.route('/labels', methods=['GET'])
def get_labels():
    return jsonify({'labels': LABELS})

if __name__ == '__main__':
    load_model()
    print(f"Starting NLP classification server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
"""
        files.append(self._write_file('backend/app.py', app_py))
        return files

    def _write_file(self, relative_path: str, content: str) -> str:
        """Write content to a file."""
        full_path = os.path.join(self.output_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.generated_files.append(full_path)
        return full_path
