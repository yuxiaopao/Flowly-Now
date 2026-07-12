"""DashScope VideoRetalk lip-sync client."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class VideoRetalkError(Exception):
    pass


def submit_videoretalk_task(
    *,
    video_url: str,
    audio_url: str,
    api_key: str,
    base_url: str,
    ref_image_url: str = '',
    video_extension: bool = False,
    query_face_threshold: int = 170,
    poll_task: Optional[Callable[..., Dict[str, Any]]] = None,
    timeout_seconds: int = 900,
) -> Dict[str, Any]:
    """Submit VideoRetalk task and poll until completion."""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'X-DashScope-Async': 'enable',
    }
    payload: Dict[str, Any] = {
        'model': 'videoretalk',
        'input': {
            'video_url': video_url,
            'audio_url': audio_url,
        },
        'parameters': {
            'video_extension': bool(video_extension),
            'query_face_threshold': int(query_face_threshold),
        },
    }
    if ref_image_url:
        payload['input']['ref_image_url'] = ref_image_url

    with httpx.Client(timeout=60, trust_env=False) as client:
        resp = client.post(
            f'{base_url.rstrip("/")}/services/aigc/image2video/video-synthesis/',
            headers=headers,
            json=payload,
        )
        if resp.status_code >= 400:
            raise VideoRetalkError(_error_detail(resp))
        data = resp.json()
        task_id = (data.get('output') or {}).get('task_id')
        if not task_id:
            raise VideoRetalkError(f'VideoRetalk 未返回 task_id: {data}')

    if poll_task:
        output = poll_task(task_id, api_key, base_url, timeout_seconds=timeout_seconds, poll_interval=5)
    else:
        output = _default_poll(task_id, api_key, base_url, timeout_seconds)

    video_url_out = output.get('video_url') or ''
    if not video_url_out:
        raise VideoRetalkError(f'VideoRetalk 完成但未返回 video_url: {output}')
    return {
        'video_url': video_url_out,
        'task_id': task_id,
        'usage': output.get('usage') or {},
        'lip_sync_applied': True,
    }


def _default_poll(task_id: str, api_key: str, base_url: str, timeout_seconds: int) -> Dict[str, Any]:
    headers = {'Authorization': f'Bearer {api_key}'}
    poll_interval = 5
    max_attempts = max(1, timeout_seconds // poll_interval)
    with httpx.Client(timeout=30, trust_env=False) as client:
        for _ in range(max_attempts):
            resp = client.get(f'{base_url.rstrip("/")}/tasks/{task_id}', headers=headers)
            if resp.status_code >= 400:
                raise VideoRetalkError(_error_detail(resp))
            data = resp.json()
            output = data.get('output') or {}
            status = output.get('task_status')
            if status == 'SUCCEEDED':
                return output
            if status in ('FAILED', 'CANCELED', 'UNKNOWN'):
                msg = output.get('message') or data.get('message') or status
                raise VideoRetalkError(f'VideoRetalk 任务失败: {msg}')
            time.sleep(poll_interval)
    raise VideoRetalkError(f'VideoRetalk 任务超时 ({timeout_seconds}s)')


def _error_detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        return str(data.get('message') or data.get('code') or data)[:500]
    except Exception:
        return (resp.text or '')[:500]
