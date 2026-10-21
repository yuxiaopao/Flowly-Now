"""Download public safetensors weights for free local AI video inference."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import struct
import threading
import time

import requests

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / '.cache/ltx-models'
CHUNK_SIZE = 32 * 1024 * 1024
WORKERS = 4
MODELS = [
    ('ltxv-2b-0.9.8-distilled-fp8.safetensors',
     'https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltxv-2b-0.9.8-distilled-fp8.safetensors'),
    ('t5xxl_fp8_e4m3fn.safetensors',
     'https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors'),
]


def download(name, url):
    FOLDER.mkdir(parents=True, exist_ok=True)
    path = FOLDER / name
    manifest = path.with_suffix('.download.json')
    head = requests.head(url, allow_redirects=True, timeout=60)
    head.raise_for_status()
    size = int(head.headers['Content-Length'])
    state = json.loads(manifest.read_text()) if manifest.exists() else {'size': size, 'chunks': []}
    if state['size'] != size:
        raise ValueError('Remote model size changed')
    completed = set(state['chunks'])
    lock = threading.Lock()
    if not path.exists():
        with path.open('wb') as destination:
            destination.truncate(size)

    def part(index):
        start = index * CHUNK_SIZE
        end = min(size - 1, start + CHUNK_SIZE - 1)
        if index in completed:
            return
        for attempt in range(4):
            try:
                with requests.get(url, headers={'Range': f'bytes={start}-{end}'}, stream=True, timeout=90) as response:
                    response.raise_for_status()
                    if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{size}':
                        raise ValueError('Server did not return the requested model range')
                    count = 0
                    with path.open('r+b') as destination:
                        destination.seek(start)
                        for data in response.iter_content(1024 * 1024):
                            destination.write(data)
                            count += len(data)
                    if count != end - start + 1:
                        raise IOError('Incomplete model chunk')
                with lock:
                    completed.add(index)
                    state['chunks'] = sorted(completed)
                    manifest.write_text(json.dumps(state), encoding='utf-8')
                return
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))

    print(json.dumps({'model': name, 'status': 'downloading', 'bytes': size}), flush=True)
    count = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
    last_report = time.monotonic()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(part, index) for index in range(count)]
        for future in as_completed(futures):
            future.result()
            if time.monotonic() - last_report >= 20:
                print(json.dumps({'model': name, 'downloaded_chunks': len(completed), 'total_chunks': count}), flush=True)
                last_report = time.monotonic()
    with path.open('rb') as source:
        header_size = struct.unpack('<Q', source.read(8))[0]
        header = json.loads(source.read(header_size))
    checksum = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    state.update(status='completed', sha256=checksum, tensors=len(header)-1, source=url)
    manifest.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print(json.dumps({'model': name, 'status': 'completed', 'sha256': checksum, 'tensors': len(header)-1}), flush=True)


if __name__ == '__main__':
    for name, url in MODELS:
        download(name, url)
