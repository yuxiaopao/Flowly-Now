#!/usr/bin/env python
"""CLIP retrieval index builder for Flowly Desktop Agent."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Desktop/training-scripts -> repo/Backend
BACKEND = Path(__file__).resolve().parents[2] / 'Backend'
if not BACKEND.is_dir():
    BACKEND = Path(__file__).resolve().parents[1] / 'Backend'
sys.path.insert(0, str(BACKEND))


def _stream(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Build CLIP retrieval index')
    parser.add_argument('--config', required=True)
    parser.add_argument('--job-id', default='')
    parser.add_argument('--output-dir', default='')
    parser.add_argument('--streaming', action='store_true')
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        _stream({'type': 'error', 'message': f'Config not found: {config_path}'})
        return 1

    with open(config_path, encoding='utf-8') as f:
        cfg = json.load(f)

    dataset_path = cfg.get('dataset_path') or cfg.get('datasetPath') or ''
    output_dir = args.output_dir or cfg.get('output_dir') or cfg.get('outputDir') or ''
    base_model = cfg.get('base_model') or cfg.get('baseModel') or 'simple-bow'
    job_id = args.job_id or cfg.get('job_id') or cfg.get('jobId') or f'clip-index-{int(time.time())}'

    if not dataset_path:
        _stream({'type': 'error', 'message': 'dataset_path is required'})
        return 1
    if not output_dir:
        output_dir = str(Path(dataset_path) / 'index')

    _stream({'type': 'clip_index_progress', 'jobId': job_id, 'progress': 0, 'phase': 'starting'})

    from training.clip_service import build_retrieval_index

    started = time.time()

    def _progress(payload: dict) -> None:
        if not args.streaming:
            return
        _stream({
            'type': 'clip_index_progress',
            'jobId': job_id,
            'progress': int(payload.get('progress') or 0),
            'phase': payload.get('phase', 'indexing'),
        })

    result = build_retrieval_index(
        dataset_path,
        output_dir,
        base_model=base_model,
        progress_callback=_progress,
    )

    duration_ms = int((time.time() - started) * 1000)
    result_path = Path(output_dir) / 'index_result.json'

    if not result.get('success'):
        out = {
            'success': False,
            'job_id': job_id,
            'error': result.get('error', 'Index build failed'),
            'duration_ms': duration_ms,
        }
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        _stream({'type': 'error', 'message': out['error'], 'jobId': job_id})
        return 1

    out = {
        'success': True,
        'job_id': job_id,
        'index_dir': result['index_dir'],
        'metadata_path': result.get('metadata_path', ''),
        'metrics': result.get('metrics', {}),
        'encoder': result.get('encoder', 'bow'),
        'image_count': result.get('image_count', 0),
        'duration_ms': duration_ms,
        'r_at_1': result.get('metrics', {}).get('r_at_1'),
        'r_at_5': result.get('metrics', {}).get('r_at_5'),
        'r_at_10': result.get('metrics', {}).get('r_at_10'),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    _stream({'type': 'clip_index_progress', 'jobId': job_id, 'progress': 100, 'phase': 'completed'})
    _stream({'type': 'clip_index_complete', 'jobId': job_id, 'result': out})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
