"""CLIP retrieval / classification helpers (M4). Uses CLIP when available; BOW/resnet fallbacks otherwise."""

from __future__ import annotations

import json
import math
import os
import random
import re
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from datasets.ml_format_validators import validate_ml_dataset
from training.clip_trainer import run_clip_classification


def _validate_pairs(dataset_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    result = validate_ml_dataset(dataset_path, 'image_text_pairs')
    if not result.get('valid'):
        return False, result.get('error', 'validation failed'), {}
    stats = result.get('stats') or {}
    pairs_file = stats.get('pairs_file') or os.path.join(result['dataset_path'], 'pairs.jsonl')
    return True, '', {
        'dataset_path': result['dataset_path'],
        'pairs_path': pairs_file,
    }


def _tokenize(text: str) -> List[str]:
    text = (text or '').lower().strip()
    tokens = re.findall(r'[\u4e00-\u9fff]+|[a-z0-9]+', text)
    chars = list(text.replace(' ', ''))
    return tokens + [c for c in chars if c.strip()]


def _build_vocab(texts: List[str]) -> Dict[str, int]:
    freq: Dict[str, int] = {}
    for t in texts:
        for tok in _tokenize(t):
            freq[tok] = freq.get(tok, 0) + 1
    vocab = {tok: i for i, tok in enumerate(sorted(freq.keys()))}
    return vocab


def _embed(text: str, vocab: Dict[str, int]) -> List[float]:
    vec = [0.0] * max(len(vocab), 1)
    for tok in _tokenize(text):
        idx = vocab.get(tok)
        if idx is not None:
            vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _save_vectors(vectors: List[List[float]], path: str) -> None:
    try:
        import numpy as np
        np.save(path, np.array(vectors, dtype=np.float32))
    except ImportError:
        with open(path.replace('.npy', '.json'), 'w', encoding='utf-8') as f:
            json.dump(vectors, f)


def _recall_at_k(queries: List[Tuple[str, str]], index: List[Dict], vocab: Dict[str, int], k: int) -> float:
    """queries: (query_text, target_id); index entries have id, text, vector."""
    hits = 0
    for qtext, target_id in queries:
        qvec = _embed(qtext, vocab)
        scored = sorted(
            (( _cosine(qvec, item['vector']), item['id']) for item in index),
            reverse=True,
        )
        top_ids = [sid for _, sid in scored[:k]]
        if target_id in top_ids:
            hits += 1
    return hits / len(queries) if queries else 0.0


def _recall_at_k_clip(queries: List[Tuple[str, str]], index: List[Dict], k: int) -> float:
    hits = 0
    clip_bundle = None
    try:
        from training.clip_trainer import _try_load_clip
        clip_bundle = _try_load_clip('ViT-B/32')
    except Exception:
        pass

    for qtext, target_id in queries:
        qvec = None
        if clip_bundle:
            try:
                import clip
                import torch
                model, _, device, _ = clip_bundle
                tokens = clip.tokenize([qtext], truncate=True).to(device)
                with torch.no_grad():
                    feat = model.encode_text(tokens)
                    feat = feat / feat.norm(dim=-1, keepdim=True)
                qvec = feat.cpu().numpy()[0].tolist()
            except Exception:
                qvec = None
        if qvec is None:
            continue
        scored = sorted(
            ((_cosine(qvec, item['vector']), item['id']) for item in index),
            reverse=True,
        )
        top_ids = [sid for _, sid in scored[:k]]
        if target_id in top_ids:
            hits += 1
    return hits / len(queries) if queries else 0.0


def _build_clip_image_vectors(entries: List[Dict[str, str]], base_model: str) -> Tuple[Optional[List[List[float]]], str]:
    """Try OpenAI CLIP image embeddings; returns (vectors, encoder_name) or (None, '')."""
    try:
        from training.clip_trainer import _try_load_clip
        import torch
        from PIL import Image

        model_name = base_model if base_model and base_model != 'simple-bow' else 'ViT-B/32'
        bundle = _try_load_clip(model_name)
        if not bundle:
            return None, ''
        model, preprocess, device, _ = bundle
        vectors: List[List[float]] = []
        with torch.no_grad():
            for entry in entries:
                path = entry.get('image_path', '')
                if not os.path.isfile(path):
                    vectors.append([0.0])
                    continue
                img = Image.open(path).convert('RGB')
                tensor = preprocess(img).unsqueeze(0).to(device)
                feat = model.encode_image(tensor)
                feat = feat / feat.norm(dim=-1, keepdim=True)
                vectors.append(feat.cpu().numpy()[0].astype(float).tolist())
        return vectors, model_name
    except Exception:
        return None, ''


def build_retrieval_index(
    dataset_path: str,
    output_dir: str,
    *,
    base_model: str = 'simple-bow',
    holdout_ratio: float = 0.2,
    seed: int = 42,
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Build numpy/json vectors + metadata.json from image_text_pairs dataset.
    """
    ok, err, info = _validate_pairs(dataset_path)
    if not ok:
        return {'success': False, 'error': err}

    pairs_path = info['pairs_path']
    root = info['dataset_path']
    entries: List[Dict[str, str]] = []
    with open(pairs_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            image = (row.get('image') or row.get('image_path') or '').strip()
            text = (row.get('text') or row.get('caption') or '').strip()
            img_abs = image if os.path.isabs(image) else os.path.join(root, image)
            entries.append({'image': image, 'text': text, 'image_path': img_abs})

    os.makedirs(output_dir, exist_ok=True)
    media_dir = os.path.join(output_dir, 'media')
    os.makedirs(media_dir, exist_ok=True)

    texts = [e['text'] for e in entries]
    vocab = _build_vocab(texts)
    index_items: List[Dict[str, Any]] = []
    vectors: List[List[float]] = []
    encoder_used = base_model

    clip_vectors, clip_name = _build_clip_image_vectors(entries, base_model)
    use_clip = clip_vectors is not None and len(clip_vectors) == len(entries)

    total = len(entries)
    for i, entry in enumerate(entries):
        if progress_callback and i % max(1, total // 10) == 0:
            try:
                progress_callback({'progress': int(10 + 80 * i / max(total, 1)), 'phase': 'indexing'})
            except Exception:
                pass

        item_id = f'img_{i+1:04d}'
        ext = os.path.splitext(entry['image_path'])[1] or '.jpg'
        dest_name = f'{item_id}{ext}'
        dest_path = os.path.join(media_dir, dest_name)
        if os.path.isfile(entry['image_path']):
            shutil.copy2(entry['image_path'], dest_path)

        if use_clip:
            vec = clip_vectors[i]
            encoder_used = clip_name or 'ViT-B/32'
        else:
            vec = _embed(entry['text'], vocab)

        vectors.append(vec)
        index_items.append({
            'id': item_id,
            'filename': dest_name,
            'caption': entry['text'],
            'image': entry['image'],
            'text': entry['text'],
            'vector': vec,
        })

    # Hold-out evaluation
    rng = random.Random(seed)
    shuffled = list(index_items)
    rng.shuffle(shuffled)
    split = max(1, int(len(shuffled) * holdout_ratio))
    holdout = shuffled[:split]
    queries = [(item['text'], item['id']) for item in holdout]

    if use_clip:
        r1 = _recall_at_k_clip(queries, index_items, 1)
        r5 = _recall_at_k_clip(queries, index_items, 5)
        r10 = _recall_at_k_clip(queries, index_items, 10)
    else:
        r1 = _recall_at_k(queries, index_items, vocab, 1)
        r5 = _recall_at_k(queries, index_items, vocab, 5)
        r10 = _recall_at_k(queries, index_items, vocab, 10)

    vec_path = os.path.join(output_dir, 'vectors.npy')
    _save_vectors(vectors, vec_path)
    if not os.path.isfile(vec_path):
        vec_path = os.path.join(output_dir, 'vectors.json')

    meta = {
        'model': encoder_used,
        'encoder': 'clip' if use_clip else 'bow',
        'built_at': datetime.now(timezone.utc).isoformat(),
        'vector_count': len(index_items),
        'vocab_size': len(vocab),
        'items': [{k: v for k, v in item.items() if k != 'vector'} for item in index_items],
        'metrics': {
            'r_at_1': round(r1, 4),
            'r_at_5': round(r5, 4),
            'r_at_10': round(r10, 4),
        },
    }
    meta_path = os.path.join(output_dir, 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'vocab.json'), 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False)

    if progress_callback:
        try:
            progress_callback({'progress': 100, 'phase': 'done'})
        except Exception:
            pass

    return {
        'success': True,
        'index_dir': output_dir,
        'metadata_path': meta_path,
        'vector_path': vec_path,
        'metrics': meta['metrics'],
        'encoder': meta.get('encoder', 'bow'),
        'image_count': len(index_items),
        'duration_ms': 0,
    }


def run_zero_shot_classification(
    dataset_path: str,
    class_names: List[str],
    output_dir: str,
    *,
    base_model: str = 'ViT-B/32',
) -> Dict[str, Any]:
    """Zero-shot CLIP export (encoder manifest + class prompts)."""
    return run_clip_classification(
        mode='zero_shot',
        class_names=class_names,
        dataset_path=dataset_path or '',
        base_model=base_model,
        output_dir=output_dir,
    )


def run_finetune_classification(
    dataset_path: str,
    class_names: List[str],
    output_dir: str,
    *,
    base_model: str = 'ViT-B/32',
    epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    progress_callback=None,
) -> Dict[str, Any]:
    """Fine-tune linear probe on classification_folders dataset."""
    return run_clip_classification(
        mode='finetune',
        class_names=class_names,
        dataset_path=dataset_path,
        base_model=base_model,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        output_dir=output_dir,
        progress_callback=progress_callback,
    )
