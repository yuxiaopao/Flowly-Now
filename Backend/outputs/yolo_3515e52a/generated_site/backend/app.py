
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

MODEL_PATH = CONFIG.get('model_path', 'model.pt')
LABELS = CONFIG.get('labels', [])
FRAMEWORK = CONFIG.get('framework', 'pytorch')
PORT = int(os.environ.get('FLASK_RUN_PORT', CONFIG.get('port', 5000)))

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
    '''Preprocess image for YOLO detection.'''
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
    '''Postprocess YOLO outputs.'''
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
        blob, scale, pad_x, pad_y = preprocess_image(img)
        if model is None:
            boxes = postprocess_detections(None, scale, pad_x, pad_y, orig_w, orig_h)
        else:
            import torch
            with torch.no_grad():
                outputs = model(torch.from_numpy(blob))
            boxes = postprocess_detections(outputs, scale, pad_x, pad_y, orig_w, orig_h)
        boxes.sort(key=lambda x: x['confidence'], reverse=True)
        latency_ms = (time.time() - started) * 1000
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

if __name__ == '__main__':
    load_model()
    print(f"Starting detection server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
