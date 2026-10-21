"""Agnes video request contracts, including the incompatible 2.5 protocol.

Provider reference: https://wiki.agnes-ai.com/en/docs/agnes-video-25
"""
MODERN_MODELS = frozenset({"agnes-video-2.5", "agnes-video-2.5-flash"})
MIN_SECONDS = 4
MAX_SECONDS = 12
DEFAULT_ASPECT_RATIO = "16:9"
SUBMISSION_POLL_SECONDS = 5
RESOLUTION_TIERS = {
    "720p": "720P", "1080p": "1080P", "1k": "1K", "2k": "2K",
}


def build_video_payload(model, prompt, duration, resolution, input_image, *, mode=None, reference_images=None, last_frame=None, seed=None):
    payload = {"model": model, "prompt": prompt}
    if model not in MODERN_MODELS:
        if input_image:
            payload["image"] = input_image
        return payload
    try:
        seconds = float(duration)
    except (TypeError, ValueError) as exc:
        raise ValueError("Agnes 2.5 视频时长必须为4至12秒的整数") from exc
    if not MIN_SECONDS <= seconds <= MAX_SECONDS or not seconds.is_integer():
        raise ValueError("Agnes 2.5 视频时长必须为4至12秒的整数")
    size = RESOLUTION_TIERS.get(str(resolution).lower())
    if size is None:
        raise ValueError("Agnes 2.5 分辨率必须为720p、1080p、1k或2k")
    if model == "agnes-video-2.5-flash" and size != RESOLUTION_TIERS["720p"]:
        raise ValueError("Agnes Video 2.5 Flash仅支持720p")
    selected_mode = mode or ('keyframe' if input_image or last_frame else 'text')
    if selected_mode not in ('text','keyframe','reference'):
        raise ValueError('Agnes 视频生成模式必须为 text、keyframe 或 reference')
    references = reference_images or []
    if not isinstance(references,list) or any(not isinstance(url,str) or not url.startswith(('http://','https://')) for url in references):
        raise ValueError('视频参考图必须是公开可访问的 HTTP(S) URL 数组')
    if selected_mode == 'reference' and not references:
        raise ValueError('参考模式需要至少一张参考图')
    if selected_mode == 'reference' and len(references) > (5 if model.endswith('-flash') else 8):
        raise ValueError('视频参考图超过模型数量限制')
    if selected_mode != 'reference' and references:
        raise ValueError('参考图数组仅用于 reference 模式')
    if selected_mode == 'keyframe' and not (input_image or last_frame):
        raise ValueError('关键帧模式需要首帧或尾帧')
    payload.update({
        "mode": selected_mode,
        "seconds": str(int(seconds)), "size": size,
        "aspect_ratio": DEFAULT_ASPECT_RATIO,
    })
    if selected_mode == 'keyframe' and input_image:
        payload["first_frame"] = input_image
    if selected_mode == 'keyframe' and last_frame:
        payload['last_frame'] = last_frame
    if selected_mode == 'reference':
        payload['images'] = references
    if seed is not None:
        payload['seed'] = int(seed)
    return payload


def poll_request(base_url, task_id, model):
    if model in MODERN_MODELS:
        root = base_url.rstrip("/").removesuffix("/v1")
        return f"{root}/agnesapi", {"video_id": task_id, "model_name": model}
    return f"{base_url}/videos/{task_id}", {}


def reserve_submission(owner_id, interval_seconds, on_wait=None):
    """Keep all keys used by this workflow owner in one conservative RPM pool."""
    if interval_seconds <= 0:
        return
    from django.core.cache import cache
    import time
    key=f'agnes-video-submit:{owner_id}'
    interval=max(1,int(interval_seconds))
    while not cache.add(key,True,timeout=interval):
        if on_wait:
            on_wait()
        time.sleep(min(SUBMISSION_POLL_SECONDS,interval))
