"""
Object Detection website generator.
Generates a complete full-stack website for object detection models (YOLO, SSD, etc.)
"""

import os
import json
from .base import BaseGenerator
from .detection_fullsite_templates import (
    build_detection_backend_extensions,
    build_detection_index_html,
)
from ..site_factory.db_templates import extra_requirements
from ..site_factory.db_templates import SCHEMA_SQL, INIT_DB_PY  # noqa: F401 — re-export


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
      },
      '/api': {
        target: 'http://localhost:""" + str(self.port) + """',
        changeOrigin: true,
      }
    }
  }
})
"""
        files.append(self._write_file('frontend/vite.config.js', vite_config))

        index_html = build_detection_index_html(
            title=title,
            subtitle=subtitle,
            primary=primary,
            upload_hint=upload_hint,
            labels=self.labels or [],
            disclaimer_html=disclaimer_html,
            class_entities=(self.profile or {}).get('class_entities') or [],
            display_names=(self.profile or {}).get('class_display_names') or {},
        )
        files.append(self._write_file('frontend/index.html', index_html))
        return files

    def generate_backend(self) -> list:
        """Generate Flask backend files."""
        files = []

        # requirements.txt — pinned for reproducible QA
        reqs = [
            "flask==3.0.3",
            "flask-cors==4.0.1",
            "torch>=2.0.0",
            "pillow>=10.0.0",
            "numpy>=1.24.0",
            "opencv-python>=4.8.0",
            "ultralytics>=8.3.0",
        ]
        reqs.extend(extra_requirements(self.get_db_engine()))
        files.append(self._write_file('backend/requirements.txt', '\n'.join(reqs)))

        files.extend(self.write_db_scaffold())

        model_basename = os.path.basename(self.model_path) if self.model_path else 'best.pt'
        framework = self.framework or 'ultralytics'
        # config.json (basename only — weights copied into backend/ by BaseGenerator.generate)
        cfg = {
            'model_path': model_basename,
            'labels': self.labels,
            'framework': framework,
            'port': self.port,
            'model_type': 'detection',
            'db_engine': self.get_db_engine(),
            'required_features': self.config.get('required_features') or [],
            'model_artifact_manifest': self.config.get('model_artifact_manifest') or {},
        }
        files.append(self._write_file('backend/config.json', json.dumps(cfg, indent=2)))

        # app.py - Flask app with YOLO detection
        app_py = """
import os
import json
import time
import cv2
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

MODEL_PATH = os.path.join(os.path.dirname(__file__), CONFIG.get('model_path', 'best.pt'))
LABELS = CONFIG.get('labels', [])
FRAMEWORK = CONFIG.get('framework', 'ultralytics')
PORT = int(os.environ.get('FLASK_RUN_PORT', CONFIG.get('port', """ + str(self.port) + """)))

try:
    from db.init_db import init_db, log_inference
    init_db()
except Exception as _db_err:
    print(f"SQLite init warning: {_db_err}")
    def log_inference(*args, **kwargs):
        pass

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

model = None
model_h, model_w = 640, 640

def load_model():
    global model
    try:
        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(MODEL_PATH)
        if FRAMEWORK in ('ultralytics', 'yolo', 'pytorch'):
            try:
                from ultralytics import YOLO
                model = YOLO(MODEL_PATH)
                print(f"Ultralytics YOLO loaded from {MODEL_PATH}. Labels: {LABELS}")
                return
            except Exception as yolo_err:
                print(f"Ultralytics load failed ({yolo_err}), trying torch fallback")
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

@app.route('/')
def index_page():
    if os.path.isdir(FRONTEND_DIR) and os.path.isfile(os.path.join(FRONTEND_DIR, 'index.html')):
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return jsonify({'message': 'Frontend not found', 'health': '/health', 'predict': '/predict'})

@app.route('/predict', methods=['POST'])
def predict():
    started = time.time()
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
        if model is None:
            blob, scale, pad_x, pad_y = preprocess_image(img)
            boxes = postprocess_detections(None, scale, pad_x, pad_y, orig_w, orig_h)
        elif hasattr(model, 'predict'):
            boxes = []
            results = model.predict(source=img, conf=0.25, verbose=False)
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    xyxy = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = LABELS[cls_id] if cls_id < len(LABELS) else str(cls_id)
                    boxes.append({
                        'x1': float(xyxy[0] / orig_w),
                        'y1': float(xyxy[1] / orig_h),
                        'x2': float(xyxy[2] / orig_w),
                        'y2': float(xyxy[3] / orig_h),
                        'label': label,
                        'confidence': round(conf, 4),
                    })
        else:
            blob, scale, pad_x, pad_y = preprocess_image(img)
            import torch
            with torch.no_grad():
                outputs = model(torch.from_numpy(blob))
            boxes = postprocess_detections(outputs, scale, pad_x, pad_y, orig_w, orig_h)
        boxes.sort(key=lambda x: x['confidence'], reverse=True)
        latency_ms = (time.time() - started) * 1000
        mode = request.form.get('mode', 'image') or 'image'
        try:
            from db.init_db import log_inference_extended
            log_inference_extended(mode, file.filename, boxes, latency_ms)
        except Exception:
            try:
                log_inference(file.filename, f'{len(boxes)} detections', latency_ms)
            except Exception:
                pass
        return jsonify({'boxes': boxes, 'model_info': {'framework': FRAMEWORK, 'labels': LABELS, 'model_loaded': model is not None}, 'latency_ms': latency_ms})
    except Exception as e:
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model_loaded': model is not None, 'labels': LABELS, 'website_type': 'detection'})
""" + build_detection_backend_extensions() + """

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
