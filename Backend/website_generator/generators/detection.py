"""
Object Detection website generator.
Generates a complete full-stack website for object detection models (YOLO, SSD, etc.)
"""

import os
import json
from .base import BaseGenerator


class DetectionGenerator(BaseGenerator):
    """
    Generates a complete detection website:
    - Vue 3 frontend with image upload and bounding box display
    - Flask backend with detection model inference
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

        # index.html with bounding box canvas
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
    .header h1 { font-size: 24px; font-weight: 700; color: #f59e0b; }
    .header p { color: #a1a1aa; font-size: 14px; margin-top: 4px; }
    .main { flex: 1; padding: 40px; display: flex; flex-direction: column; align-items: center; gap: 24px; }
    .upload-zone { width: 100%; max-width: 800px; border: 2px dashed #2e2e42; border-radius: 12px; padding: 60px; text-align: center; cursor: pointer; transition: all 0.2s; }
    .upload-zone:hover, .upload-zone.dragover { border-color: #f59e0b; background: rgba(245,158,11,0.05); }
    .upload-zone p { color: #a1a1aa; font-size: 16px; }
    .upload-zone .hint { font-size: 12px; margin-top: 8px; color: #71717a; }
    .result-container { width: 100%; max-width: 800px; background: #18181f; border: 1px solid #2e2e42; border-radius: 12px; overflow: hidden; }
    .image-container { position: relative; background: #0f0f14; }
    .image-container img { display: block; max-width: 100%; }
    .image-container canvas { position: absolute; top: 0; left: 0; }
    .detection-stats { padding: 16px 24px; border-bottom: 1px solid #2e2e42; display: flex; gap: 24px; }
    .stat-item { display: flex; align-items: center; gap: 8px; }
    .stat-value { font-size: 20px; font-weight: 700; color: #f59e0b; }
    .stat-label { font-size: 12px; color: #a1a1aa; }
    .detection-list { padding: 16px 24px; max-height: 200px; overflow-y: auto; }
    .detection-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #2e2e42; }
    .detection-item:last-child { border-bottom: none; }
    .detection-label { font-weight: 600; color: #f4f4f5; min-width: 100px; }
    .detection-confidence { color: #a1a1aa; font-size: 13px; }
    .confidence-bar { flex: 1; height: 6px; background: #2e2e42; border-radius: 3px; overflow: hidden; }
    .confidence-fill { height: 100%; background: #f59e0b; border-radius: 3px; }
    .loading { color: #f59e0b; text-align: center; padding: 40px; font-size: 16px; }
    input[type="file"] { display: none; }
  </style>
</head>
<body>
  <div id="app">
    <div class="header">
      <h1>""" + self.name + """</h1>
      <p>""" + (self.description or 'AI-powered object detection service') + """</p>
    </div>
    <div class="main">
      <div class="upload-zone" :class="{dragover: isDragover}" @click="$refs.fileInput.click()" @dragover.prevent="isDragover=true" @dragleave="isDragover=false" @drop.prevent="handleDrop">
        <input type="file" ref="fileInput" @change="handleFileSelect" accept="image/*" />
        <p>点击或拖拽上传图片进行目标检测</p>
        <p class="hint">支持 JPG, PNG, WEBP 格式</p>
      </div>
      <div v-if="imageUrl" class="result-container">
        <div class="image-container" ref="imageContainer">
          <img :src="imageUrl" ref="imageElement" @load="onImageLoad" />
          <canvas ref="canvas"></canvas>
        </div>
        <div v-if="loading" class="loading">正在检测...</div>
        <template v-else-if="detections.length > 0">
          <div class="detection-stats">
            <div class="stat-item">
              <span class="stat-value">{{ detections.length }}</span>
              <span class="stat-label">检测到目标</span>
            </div>
          </div>
          <div class="detection-list">
            <div v-for="(det, i) in detections" :key="i" class="detection-item">
              <span class="detection-label">{{ det.label }}</span>
              <div class="confidence-bar">
                <div class="confidence-fill" :style="{width: (det.confidence * 100) + '%'}"></div>
              </div>
              <span class="detection-confidence">{{ (det.confidence * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </template>
        <div v-else-if="error" style="color: #ef4444; padding: 20px; text-align: center;">{{ error }}</div>
      </div>
    </div>
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>
  <script>
    const { createApp, ref, nextTick } = Vue
    createApp({
      setup() {
        const imageUrl = ref('')
        const isDragover = ref(false)
        const loading = ref(false)
        const detections = ref([])
        const error = ref('')
        const imageElement = ref(null)
        const canvas = ref(null)
        const imageContainer = ref(null)
        const API_URL = 'http://localhost:""" + str(self.port) + """/predict'

        const COLORS = ['#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

        function handleFileSelect(e) { const f = e.target.files[0]; if (f) processFile(f) }
        function handleDrop(e) { isDragover.value = false; const f = e.dataTransfer.files[0]; if (f) processFile(f) }

        function processFile(file) {
          imageUrl.value = URL.createObjectURL(file)
          loading.value = true; detections.value = []; error.value = ''
          const formData = new FormData()
          formData.append('file', file)
          axios.post(API_URL, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
            .then(r => { detections.value = r.data.boxes || []; drawBoxes(); loading.value = false })
            .catch(e => { error.value = (e.response && e.response.data && e.response.data.error) || e.message || '请求失败'; loading.value = false })
        }

        function onImageLoad() {
          if (detections.value.length > 0) drawBoxes()
        }

        function drawBoxes() {
          nextTick(() => {
            const img = imageElement.value
            const cv = canvas.value
            if (!img || !cv) return
            cv.width = img.naturalWidth
            cv.height = img.naturalHeight
            const ctx = cv.getContext('2d')
            ctx.clearRect(0, 0, cv.width, cv.height)
            detections.value.forEach((det, i) => {
              const color = COLORS[i % COLORS.length]
              ctx.strokeStyle = color
              ctx.fillStyle = color + '33'
              ctx.lineWidth = 3
              const x1 = det.x1 * cv.width
              const y1 = det.y1 * cv.height
              const x2 = det.x2 * cv.width
              const y2 = det.y2 * cv.height
              ctx.fillRect(x1, y1, x2 - x1, y2 - y1)
              ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
              ctx.font = 'bold 16px sans-serif'
              const label = det.label + ' ' + (det.confidence * 100).toFixed(0) + '%'
              const tw = ctx.measureText(label).width + 8
              ctx.fillStyle = color
              ctx.fillRect(x1, y1 - 24, tw, 24)
              ctx.fillStyle = '#000'
              ctx.fillText(label, x1 + 4, y1 - 6)
            })
          })
        }

        return { imageUrl, isDragover, loading, detections, error, handleFileSelect, handleDrop, onImageLoad, imageElement, canvas, imageContainer }
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
        reqs = ["flask>=3.0.0", "flask-cors>=4.0.0", "torch>=2.0.0", "pillow>=10.0.0", "numpy>=1.24.0", "opencv-python>=4.8.0"]
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))

        # config.json
        cfg = {
            'model_path': self.model_path,
            'labels': self.labels,
            'framework': self.framework,
            'port': self.port,
            'model_type': 'detection'
        }
        files.append(self._write_file('backend/config.json', json.dumps(cfg, indent=2)))

        # app.py - Flask app with YOLO detection
        app_py = """
import os
import json
import cv2
import numpy as np
from PIL import Image
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
model_h, model_w = 640, 640

def load_model():
    global model
    try:
        if FRAMEWORK == 'pytorch':
            import torch
            model = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
            if isinstance(model, dict) and 'model' in model:
                model = model['model']
            model.eval()
        else:
            print(f"Warning: Framework {FRAMEWORK} detection model not implemented. Using demo.")
            model = None
        print(f"Detection model loaded. Labels: {LABELS}")
    except FileNotFoundError:
        print(f"Warning: Model file not found at {MODEL_PATH}. Demo mode.")
        model = None
    except Exception as e:
        print(f"Warning: Could not load model: {e}. Demo mode.")
        model = None

def preprocess_image(img):
    \'\'\'Preprocess image for YOLO detection.\'\'\'
    orig_h, orig_w = img.shape[:2]
    scale = min(model_w / orig_w, model_h / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    resized = cv2.resize(img, (new_w, new_h))
    padded = np.full((model_h, model_w, 3), 114, dtype=np.uint8)
    pad_x = (model_w - new_w) // 2
    pad_y = (model_h - new_h) // 2
    padded[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
    blob = padded.astype(np.float32) / 255.0
    blob = blob.transpose(2, 0, 1)[None]
    return blob, scale, pad_x, pad_y

def postprocess_detections(outputs, scale, pad_x, pad_y, orig_w, orig_h, conf_thresh=0.25, iou_thresh=0.45):
    \'\'\'Postprocess YOLO outputs.\'\'\'
    boxes = []
    if model is None:
        n = len(LABELS) if LABELS else 3
        for i in range(min(3, n)):
            x1 = np.random.rand() * 0.6
            y1 = np.random.rand() * 0.6
            x2 = x1 + np.random.rand() * 0.3 + 0.1
            y2 = y1 + np.random.rand() * 0.3 + 0.1
            boxes.append({
                'x1': float(max(0, min(1, x1))),
                'y1': float(max(0, min(1, y1))),
                'x2': float(max(0, min(1, x2))),
                'y2': float(max(0, min(1, y2))),
                'label': LABELS[i] if LABELS else f'Object{i+1}',
                'confidence': round(0.5 + np.random.rand() * 0.45, 4)
            })
        return boxes

    try:
        import torch
        predictions = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
        if predictions.shape[-1] >= 5:
            x = predictions.clone()
            x[..., 0] = (predictions[..., 0] - pad_x) / scale / orig_w
            x[..., 1] = (predictions[..., 1] - pad_y) / scale / orig_h
            x[..., 2] = predictions[..., 2] / scale / orig_w
            x[..., 3] = predictions[..., 3] / scale / orig_h
            scores = x[..., 4:].max(dim=-1)[0]
            mask = scores > conf_thresh
            x = x[mask]
            scores = scores[mask]
            if len(x) == 0:
                return boxes
            labels = x[..., 5:].argmax(dim=-1)
            for i in range(len(x)):
                boxes.append({
                    'x1': float(max(0, min(1, x[i, 0] - x[i, 2]/2))),
                    'y1': float(max(0, min(1, x[i, 1] - x[i, 3]/2))),
                    'x2': float(max(0, min(1, x[i, 0] + x[i, 2]/2))),
                    'y2': float(max(0, min(1, x[i, 1] + x[i, 3]/2))),
                    'label': LABELS[labels[i]] if labels[i] < len(LABELS) else str(labels[i].item()),
                    'confidence': float(scores[i].item())
                })
    except Exception as e:
        print(f"Postprocessing error: {e}")
    return boxes

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400
    try:
        img_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'Invalid image'}), 400
        orig_h, orig_w = img.shape[:2]
        blob, scale, pad_x, pad_y = preprocess_image(img)
        if model is None:
            boxes = postprocess_detections(None, scale, pad_x, pad_y, orig_w, orig_h)
        else:
            import torch
            with torch.no_grad():
                outputs = model(torch.from_numpy(blob))
            boxes = postprocess_detections(outputs, scale, pad_x, pad_y, orig_w, orig_h)
        boxes.sort(key=lambda x: x['confidence'], reverse=True)
        return jsonify({'boxes': boxes, 'model_info': {'framework': FRAMEWORK, 'labels': LABELS, 'model_loaded': model is not None}})
    except Exception as e:
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model_loaded': model is not None, 'labels': LABELS})

if __name__ == '__main__':
    load_model()
    print(f"Starting detection server on port {PORT}...")
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
