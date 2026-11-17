"""Media node execution, provider protocols and local model lifecycle.

The orchestration layer supplies identity, credentials, context rendering, chat and
progress callbacks explicitly; this module does not import LangChainService.
"""
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import httpx
from PIL import Image
from django.conf import settings
from django.utils import timezone

from config.constants import HTTP_TOOL_TIMEOUT
from .execution_errors import LocalImageModelError, WorkflowExecutionError

logger = logging.getLogger(__name__)

IMAGE_GENERATION_TIMEOUT = 60
VIDEO_GENERATION_TIMEOUT = 300
AUDIO_GENERATION_TIMEOUT = 120
ZIMAGE_SUPPORTED_DTYPES = {'auto', 'bfloat16', 'float16', 'float32'}
_zimage_pipeline = None
_zimage_pipeline_key = None


def _normalize_image_size(size):
    """Parse WIDTHxHEIGHT strings safely."""
    if not size:
        return (
            getattr(settings, 'ZIMAGE_DEFAULT_WIDTH', 1024),
            getattr(settings, 'ZIMAGE_DEFAULT_HEIGHT', 1024),
        )

    match = re.fullmatch(r'(\d{2,5})x(\d{2,5})', str(size).strip())
    if not match:
        raise LocalImageModelError(f'无效图片尺寸格式: {size}，应为 WIDTHxHEIGHT')

    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise LocalImageModelError(f'无效图片尺寸: {size}')
    return width, height

def _resolve_zimage_dtype(torch_module, dtype_name: str):
    """Resolve configured dtype to a torch dtype."""
    normalized = (dtype_name or 'auto').strip().lower()
    if normalized not in ZIMAGE_SUPPORTED_DTYPES:
        raise LocalImageModelError(
            f'不支持的 Z-Image dtype: {dtype_name}，可选值: {", ".join(sorted(ZIMAGE_SUPPORTED_DTYPES))}'
        )

    if normalized == 'auto':
        if torch_module.cuda.is_available() and hasattr(torch_module.cuda, 'is_bf16_supported') and torch_module.cuda.is_bf16_supported():
            return torch_module.bfloat16
        if torch_module.cuda.is_available():
            return torch_module.float16
        return torch_module.float32

    return getattr(torch_module, normalized)

def _build_media_url(path: str) -> str:
    normalized = str(path).replace('\\', '/')
    media_root = str(settings.MEDIA_ROOT).replace('\\', '/')
    if normalized.startswith(media_root):
        relative = normalized[len(media_root):].lstrip('/')
        return f"{settings.MEDIA_URL}{relative}"
    return normalized


class MediaNodeExecutor:
    """Execute media nodes using only explicitly supplied runtime dependencies."""

    def __init__(
        self, *, user_id: Optional[int], credential: Callable,
        render_template: Callable, report_progress: Callable, run_llm: Callable,
    ):
        self.user_id = user_id
        self._get_credential = credential
        self._render_template = render_template
        self._report_progress = report_progress
        self.run_llm_node = run_llm

    def _resolve_prompt_from_context(
        self,
        node_config: Dict[str, Any],
        context: Dict[str, Any],
        *,
        field: str = 'prompt',
    ) -> str:
        """Resolve prompt/text from node template plus upstream execution context."""
        template = node_config.get(field) or node_config.get('text') or ''
        prompt = self._render_template(str(template), context) if template else ''
        prompt = str(prompt or '').strip()
        if prompt and not re.search(r'\{[a-zA-Z_][\w.]*\}', prompt):
            return prompt
        # Prefer media-specific fields already on the flattened context
        # (includes _branch_upstream overlay from the executor).
        for key in (
            'image_prompt', 'video_motion_prompt', 'prompt', 'text',
            'user_input', 'userInput', 'input', 'description', 'scene', 'action',
        ):
            candidate = context.get(key)
            if candidate is not None and str(candidate).strip():
                # Skip unresolved templates
                text = str(candidate).strip()
                if re.search(r'\{[a-zA-Z_][\w.]*\}', text):
                    continue
                return text
        nested = context.get('input_data')
        if isinstance(nested, dict):
            for key in (
                'image_prompt', 'video_motion_prompt', 'prompt', 'text',
                'user_input', 'userInput', 'input', 'description',
            ):
                candidate = nested.get(key)
                if candidate is not None and str(candidate).strip():
                    text = str(candidate).strip()
                    if re.search(r'\{[a-zA-Z_][\w.]*\}', text):
                        continue
                    return text
        # Last resort: only use node_outputs when a single shot owns the key.
        # Never last-wins across parallel branches (that caused identical 12-shot media).
        nos = context.get('node_outputs')
        if isinstance(nos, dict):
            prefer = []
            tmpl = str(template or '')
            if 'image_prompt' in tmpl or field == 'prompt':
                prefer.extend(['image_prompt', 'video_motion_prompt', 'prompt'])
            if 'video_motion' in tmpl:
                prefer = ['video_motion_prompt', 'image_prompt', 'prompt']
            if not prefer:
                prefer = ['image_prompt', 'video_motion_prompt', 'prompt']
            for key in prefer:
                matches = []
                for out in nos.values():
                    if isinstance(out, dict) and out.get(key):
                        matches.append(str(out.get(key)).strip())
                if len(matches) == 1:
                    return matches[0]
        return prompt

    def _resolve_input_image(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Resolve image-to-video / image-editing input from config templates or upstream output."""
        raw = (
            node_config.get('inputImage')
            or node_config.get('input_image')
            or node_config.get('input_image_url')
            or node_config.get('image')
            or context.get('inputImage')
            or context.get('input_image')
            or context.get('image')
            or ''
        )
        if raw:
            rendered = self._render_template(str(raw), context) if '{' in str(raw) else str(raw)
            rendered = str(rendered or '').strip()
            if rendered and not re.search(r'\{[a-zA-Z_][a-zA-Z0-9_.]*\}', rendered):
                return rendered

        images = context.get('images')
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                return str(first.get('url') or first.get('path') or '').strip()
            if isinstance(first, str):
                return first.strip()
        return ''

    def _resolve_reference_images(self, config: Dict, context: Dict, *, encode_local=False) -> list:
        references = config.get('referenceImages') or config.get('reference_images') or []
        if not isinstance(references, list):
            raise ValueError('参考图片必须是URL数组')
        resolved = []
        for value in references:
            if not isinstance(value, str):
                raise ValueError('参考图片地址必须是字符串')
            url = self._render_template(value, context)
            if '{' in url or '}' in url:
                raise ValueError('参考图片变量尚未生成')
            if encode_local:
                from pathlib import Path
                import base64
                import mimetypes
                from .media_service import local_path_from_public_url
                path = local_path_from_public_url(url)
                if path is not None:
                    path = path.resolve()
                    if not path.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not path.is_file():
                        raise ValueError('参考图片必须是已上传的媒体文件')
                    if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp') or path.stat().st_size > 15*1024*1024:
                        raise ValueError('参考图片格式无效或超过15MB')
                    url = 'data:'+mimetypes.guess_type(path.name)[0]+';base64,'+base64.b64encode(path.read_bytes()).decode('ascii')
            resolved.append(url)
        return resolved

    @staticmethod
    def _format_video_progress_message(status: str, progress: Any, provider: str = '') -> str:
        pct = int(progress or 0)
        label = {'agnes': 'Agnes', 'dashscope': '百炼'}.get(provider, provider or 'AI')
        if status in ('queued', 'pending', 'waiting'):
            return f'{label} 排队中…（图生视频通常 3–8 分钟，可继续编辑画布）'
        if status in ('processing', 'running', 'in_progress', 'in-progress'):
            return f'{label} 生成中 {pct}%' if pct else f'{label} 生成中…'
        return f'{label} 视频任务处理中…'

    def _poll_replicate_prediction(self, prediction_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """
        Poll Replicate prediction status until completed or timeout.

        Args:
            prediction_id: Replicate prediction ID returned from initial request
            timeout_seconds: Maximum wait time (default 5 minutes)

        Returns:
            Final prediction result dictionary
        """
        api_key = self._get_credential('replicate')
        headers = {'Authorization': f'Bearer {api_key}'}

        poll_interval = 5  # seconds between polls
        max_attempts = timeout_seconds // poll_interval

        with httpx.Client(timeout=timeout_seconds + 30) as client:
            for attempt in range(max_attempts):
                resp = client.get(
                    f'https://api.replicate.com/v1/predictions/{prediction_id}',
                    headers=headers
                )
                resp.raise_for_status()
                pred = resp.json()

                status = pred.get('status')
                if status == 'succeeded':
                    return pred
                elif status == 'failed':
                    error = pred.get('error') or 'Unknown error'
                    raise WorkflowExecutionError(f'Replicate prediction failed: {error}')
                elif status == 'canceled':
                    raise WorkflowExecutionError('Replicate prediction was canceled')

                # Still processing, wait before next poll
                time.sleep(poll_interval)

        raise WorkflowExecutionError(f'Replicate prediction timed out after {timeout_seconds}s')

    def _dashscope_credential(self) -> tuple:
        """
        Resolve (api_key, base_url) for DashScope (阿里云百炼) REST calls.
        DB-stored credential takes priority over the DASHSCOPE_API_KEY environment variable.
        """
        api_key = self._get_credential('dashscope') or (getattr(settings, 'DASHSCOPE_API_KEY', '') or '').strip()
        if not api_key:
            raise WorkflowExecutionError(
                'DashScope API Key 未配置。请在 .env 中设置 DASHSCOPE_API_KEY，或在「凭证中心」新增 dashscope 类型的凭证。',
                'configuration'
            )
        base_url = (getattr(settings, 'DASHSCOPE_BASE_URL', '') or 'https://dashscope.aliyuncs.com/api/v1').rstrip('/')
        return api_key, base_url

    def _dashscope_httpx_client(self, timeout: float = 60) -> 'httpx.Client':
        """DashScope HTTP client — disable system proxy to avoid SSL EOF on Windows."""
        return httpx.Client(timeout=timeout, trust_env=False)

    @staticmethod
    def _normalize_dashscope_video_model(model: str, input_image: str) -> str:
        """Map UI model ids to DashScope Wanx video model names."""
        raw = (model or '').strip()
        aliases = {
            'wan2.1-i2v-turbo': 'wanx2.1-i2v-turbo',
            'wan2.1-i2v-plus': 'wanx2.1-i2v-plus',
            'wan2.1-t2v-turbo': 'wanx2.1-t2v-turbo',
            'wan2.1-t2v-plus': 'wanx2.1-t2v-plus',
        }
        if raw in aliases:
            raw = aliases[raw]
        if input_image:
            if raw and 'i2v' in raw:
                return raw
            if raw and 't2v' in raw:
                return 'wanx2.1-i2v-turbo'
            return raw or 'wanx2.1-i2v-turbo'
        if raw and raw.startswith(('wanx', 'wan2')):
            return raw
        return 'wanx2.1-t2v-turbo'

    def _dashscope_error_detail(self, resp: 'httpx.Response') -> str:
        """Extract a human-readable error message from a DashScope error response."""
        try:
            data = resp.json()
            code = data.get('code') or data.get('error', {}).get('code')
            message = data.get('message') or data.get('error', {}).get('message')
            if code or message:
                return f'{code}: {message}'
        except Exception:
            pass
        return resp.text[:500]

    def _poll_dashscope_task(
        self,
        task_id: str,
        api_key: str,
        base_url: str,
        timeout_seconds: int = 300,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """
        Poll a DashScope async task (image/video/audio-transcription generation)
        until it reaches a terminal state, returning the `output` payload.
        """
        headers = {'Authorization': f'Bearer {api_key}'}
        max_attempts = max(1, timeout_seconds // poll_interval)

        with self._dashscope_httpx_client(timeout=30) as client:
            for _ in range(max_attempts):
                resp = client.get(f'{base_url}/tasks/{task_id}', headers=headers)
                if resp.status_code >= 400:
                    raise WorkflowExecutionError(f'DashScope 任务查询失败: {self._dashscope_error_detail(resp)}')
                data = resp.json()
                output = data.get('output', {}) or {}
                task_status = output.get('task_status')
                if task_status == 'SUCCEEDED':
                    return output
                if task_status in ('FAILED', 'CANCELED', 'UNKNOWN'):
                    message = output.get('message') or data.get('message') or f'任务状态: {task_status}'
                    raise WorkflowExecutionError(f'DashScope 任务执行失败: {message}')
                time.sleep(poll_interval)

        raise WorkflowExecutionError(f'DashScope 任务超时（{timeout_seconds}s），task_id={task_id}')

    def _agnes_credential(self, credential_id=None) -> tuple:
        """Resolve (api_key, base_url) for Agnes AI OpenAI-compatible API."""
        if credential_id:
            from workflows.models import APICredential
            try:
                credential = APICredential.objects.get(pk=credential_id,owner_id=self.user_id,service_type='agnes',is_active=True)
            except (APICredential.DoesNotExist, ValueError) as exc:
                raise WorkflowExecutionError('指定的Agnes凭证不存在、未启用或不属于当前用户','configuration') from exc
            if not credential.verify_integrity():
                raise WorkflowExecutionError('Agnes凭证完整性检查失败','configuration')
            api_key = credential.get_decrypted_data()
            credential.update_last_used()
        else:
            api_key = self._get_credential('agnes') or (getattr(settings, 'AGNES_API_KEY', '') or '').strip()
        if not api_key:
            raise WorkflowExecutionError(
                'Agnes API Key 未配置。请在 .env 中设置 AGNES_API_KEY，或在「凭证中心」新增 agnes 类型的凭证。',
                'configuration'
            )
        base_url = (getattr(settings, 'AGNES_BASE_URL', '') or 'https://apihub.agnes-ai.com/v1').rstrip('/')
        return api_key, base_url

    def _agnes_httpx_client(self, timeout: float = 60) -> 'httpx.Client':
        """Agnes HTTP client — disable system proxy to avoid SSL EOF on Windows."""
        return httpx.Client(timeout=timeout, trust_env=False)

    def _agnes_error_detail(self, resp: 'httpx.Response') -> str:
        try:
            data = resp.json()
            err = data.get('error') or {}
            if isinstance(err, dict):
                message = err.get('message') or data.get('message')
                if message:
                    return str(message)
            if data.get('message'):
                return str(data['message'])
        except Exception:
            pass
        return resp.text[:500]

    @staticmethod
    def _extract_agnes_video_url(result: Optional[Dict[str, Any]]) -> str:
        """Extract playable video URL from Agnes task payload (top-level or nested)."""
        if not isinstance(result, dict):
            return ''
        for key in ('url', 'video_url', 'video', 'output_url'):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        metadata = result.get('metadata')
        if isinstance(metadata, dict):
            for key in ('url', 'video_url', 'video', 'output_url'):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        data = result.get('data')
        if isinstance(data, dict):
            nested = MediaNodeExecutor._extract_agnes_video_url(data)
            if nested:
                return nested
        output = result.get('output')
        if isinstance(output, dict):
            nested = MediaNodeExecutor._extract_agnes_video_url(output)
            if nested:
                return nested
        if isinstance(output, str) and output.strip():
            return output.strip()
        results = result.get('results')
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                nested = MediaNodeExecutor._extract_agnes_video_url(first)
                if nested:
                    return nested
            if isinstance(first, str) and first.strip():
                return first.strip()
        return ''

    def _poll_agnes_video_task(
        self,
        task_id: str,
        api_key: str,
        base_url: str,
        timeout_seconds: int = 900,
        poll_interval: int = 5,
        progress_meta: Optional[Dict[str, Any]] = None,
        model: str = '',
    ) -> Dict[str, Any]:
        """Poll Agnes video generation task until completed."""
        headers = {'Authorization': f'Bearer {api_key}'}
        max_attempts = max(1, timeout_seconds // poll_interval)
        ssl_retries = 0
        max_ssl_retries = 5
        from .agnes_video import poll_request
        poll_url, poll_params = poll_request(base_url, task_id, model)
        with self._agnes_httpx_client(timeout=60) as client:
            for _ in range(max_attempts):
                try:
                    resp = client.get(poll_url, headers=headers, params=poll_params)
                except httpx.HTTPError as exc:
                    ssl_retries += 1
                    if ssl_retries > max_ssl_retries:
                        raise WorkflowExecutionError(f'Agnes 视频任务查询网络错误: {exc}') from exc
                    time.sleep(min(poll_interval, 5))
                    continue
                ssl_retries = 0
                if resp.status_code >= 400:
                    raise WorkflowExecutionError(f'Agnes 视频任务查询失败: {self._agnes_error_detail(resp)}')
                data = resp.json()
                status = (data.get('status') or '').lower()
                progress = data.get('progress', 0)
                self._report_progress({
                    **(progress_meta or {}),
                    'status': status,
                    'task_status': status,
                    'progress': progress,
                    'task_id': task_id,
                    'provider': 'agnes',
                    'message': self._format_video_progress_message(status, progress, 'agnes'),
                })
                if status in ('completed', 'succeeded', 'success'):
                    return data
                if status in ('failed', 'error', 'canceled', 'cancelled'):
                    raise WorkflowExecutionError(
                        f"Agnes 视频生成失败: {data.get('error') or status}"
                    )
                time.sleep(poll_interval)
        raise WorkflowExecutionError(f'Agnes 视频任务超时（{timeout_seconds}s），task_id={task_id}')

    def _get_zimage_pipeline(self, model_id: str, device: str, dtype_name: str, enable_cpu_offload: bool):
        """Lazily load and cache the local Z-Image pipeline."""
        global _zimage_pipeline, _zimage_pipeline_key

        cache_key = (model_id, device, dtype_name, enable_cpu_offload)
        if _zimage_pipeline is not None and _zimage_pipeline_key == cache_key:
            return _zimage_pipeline

        try:
            import torch
            from diffusers import ZImagePipeline
        except ImportError as exc:
            raise LocalImageModelError(
                '本地 Z-Image-Turbo 依赖未安装，请先安装 torch、transformers、accelerate、safetensors 和最新 diffusers。'
            ) from exc

        torch_dtype = _resolve_zimage_dtype(torch, dtype_name)

        try:
            pipe = ZImagePipeline.from_pretrained(
                model_id,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=False,
            )
        except Exception as exc:
            raise LocalImageModelError(f'加载 Z-Image-Turbo 模型失败: {exc}') from exc

        try:
            if enable_cpu_offload:
                pipe.enable_model_cpu_offload()
            else:
                target_device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
                pipe.to(target_device)
        except Exception as exc:
            raise LocalImageModelError(f'初始化 Z-Image-Turbo 运行设备失败: {exc}') from exc

        _zimage_pipeline = pipe
        _zimage_pipeline_key = cache_key
        return pipe

    def _run_zimage_local_generation(
        self,
        prompt: str,
        model: str,
        size: str,
        n: int,
        node_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate images with a local Z-Image-Turbo pipeline."""
        if not prompt:
            raise LocalImageModelError('Z-Image-Turbo 生成失败：prompt 不能为空')

        import torch

        model_id = model or getattr(settings, 'ZIMAGE_MODEL_ID', 'Tongyi-MAI/Z-Image-Turbo')
        device = node_config.get('device') or getattr(settings, 'ZIMAGE_DEVICE', 'cuda')
        dtype_name = node_config.get('dtype') or getattr(settings, 'ZIMAGE_DTYPE', 'auto')
        enable_cpu_offload = node_config.get('enable_cpu_offload')
        if enable_cpu_offload is None:
            enable_cpu_offload = getattr(settings, 'ZIMAGE_ENABLE_CPU_OFFLOAD', True)

        width, height = _normalize_image_size(size)
        num_images = max(1, int(n or 1))
        num_inference_steps = int(node_config.get('num_inference_steps') or getattr(settings, 'ZIMAGE_NUM_INFERENCE_STEPS', 9))
        guidance_scale = float(node_config.get('guidance_scale') if node_config.get('guidance_scale') is not None else getattr(settings, 'ZIMAGE_GUIDANCE_SCALE', 0.0))
        seed = node_config.get('seed')

        if device == 'cuda' and not torch.cuda.is_available():
            raise LocalImageModelError('Z-Image-Turbo 配置为 CUDA，但当前环境未检测到可用 NVIDIA GPU')

        pipeline = self._get_zimage_pipeline(model_id, device, dtype_name, bool(enable_cpu_offload))

        generator = None
        generator_device = 'cuda' if device == 'cuda' and torch.cuda.is_available() else 'cpu'
        if seed is not None and str(seed).strip() != '':
            generator = torch.Generator(generator_device).manual_seed(int(seed))

        try:
            result = pipeline(
                prompt=prompt,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                num_images_per_prompt=num_images,
                generator=generator,
            )
        except RuntimeError as exc:
            if 'out of memory' in str(exc).lower():
                raise LocalImageModelError(
                    'Z-Image-Turbo 显存不足。你的 RTX 4060 8GB 建议启用 CPU offload，并避免高并发或过大分辨率。'
                ) from exc
            raise LocalImageModelError(f'Z-Image-Turbo 推理失败: {exc}') from exc
        except Exception as exc:
            raise LocalImageModelError(f'Z-Image-Turbo 推理失败: {exc}') from exc

        output_dir = settings.MEDIA_ROOT / 'generated' / 'zimage'
        output_dir.mkdir(parents=True, exist_ok=True)

        images = []
        for index, image in enumerate(result.images or []):
            if not isinstance(image, Image.Image):
                raise LocalImageModelError('Z-Image-Turbo 返回了无法识别的图片对象')

            filename = f"zimage_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{index + 1}.png"
            output_path = output_dir / filename
            image.save(output_path)
            images.append({
                'path': str(output_path),
                'url': _build_media_url(str(output_path)),
                'width': image.width,
                'height': image.height,
                'provider': 'zimage_local',
                'model': model_id,
            })

        return {
            'success': True,
            'output': {
                'images': images,
                'count': len(images),
                'provider': 'zimage_local',
                'model': model_id,
                'device': device,
                'dtype': dtype_name,
                'width': width,
                'height': height,
                'num_inference_steps': num_inference_steps,
                'guidance_scale': guidance_scale,
                'cpu_offload_enabled': bool(enable_cpu_offload),
            }
        }

    def _image_generation_demo_output(self, prompt: str) -> Dict[str, Any]:
        import hashlib
        seed = int(hashlib.md5(str(prompt or 'demo').encode('utf-8')).hexdigest()[:8], 16) % 100000
        return {
            'success': True,
            'output': {
                'images': [{
                    'url': f'https://picsum.photos/seed/{seed}/1024/1024',
                    'revised_prompt': f'[Demo Mode] {prompt}',
                }],
                'count': 1,
                'demo': True,
            },
        }

    def run_image_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Image Generation Node
        Generates images from text prompts using various providers.
        """
        provider = node_config.get('provider', 'openai')
        if provider == 'zimage_local':
            model = node_config.get('model') or getattr(settings, 'ZIMAGE_MODEL_ID', 'Tongyi-MAI/Z-Image-Turbo')
        elif provider == 'dashscope':
            model = node_config.get('model') or 'wanx2.1-t2i-turbo'
        elif provider == 'agnes':
            model = node_config.get('model') or 'agnes-image-2.1-flash'
        else:
            model = node_config.get('model', 'dall-e-3')
        prompt = self._resolve_prompt_from_context(node_config, context, field='prompt')
        size = node_config.get('size', '1024x1024')
        quality = node_config.get('quality', 'standard')
        style = node_config.get('style', 'vivid')
        n = node_config.get('n', 1)

        try:
            if provider == 'openai':
                api_key = self._get_credential('openai')
                if not api_key or node_config.get('demo_mode'):
                    return self._image_generation_demo_output(prompt)
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
                response = client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    style=style,
                    n=n
                )
                images = [{'url': img.url, 'revised_prompt': getattr(img, 'revised_prompt', '')} for img in response.data]
                return {'success': True, 'output': {'images': images, 'count': len(images)}}
            elif provider == 'agnes':
                api_key, base_url = self._agnes_credential(node_config.get('credentialId') or node_config.get('credential_id'))
                from openai import OpenAI
                agnes_model = model if model and model.startswith('agnes-image') else 'agnes-image-2.1-flash'
                allowed_sizes = {'1024x1024', '1792x1024', '1024x1792', '1024x768', '768x1024', '1K','2K','3K','4K'}
                agnes_size = (size or '1024x1024').replace('*', 'x').replace('X', 'x')
                if agnes_size not in allowed_sizes:
                    agnes_size = '1024x1024'
                client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=0)
                references = self._resolve_reference_images(node_config, context, encode_local=True)
                extra_body = {}
                if references:
                    extra_body['extra_body'] = {'image': references, 'response_format': 'url'}
                if node_config.get('ratio'):
                    extra_body['ratio'] = node_config['ratio']
                # Agnes often returns 503 busy — retry with backoff, do NOT fake picsum stills.
                attempts = max(1, int(node_config.get('max_retries') or 5))
                last_err = None
                for attempt in range(attempts):
                    try:
                        response = client.images.generate(
                            model=agnes_model,
                            prompt=prompt,
                            size=agnes_size,
                            n=max(1, min(4, int(n or 1))),
                            **({'extra_body': extra_body} if extra_body else {}),
                        )
                        images = []
                        for img in response.data:
                            item = {'url': getattr(img, 'url', '') or ''}
                            if getattr(img, 'b64_json', None):
                                item['base64'] = img.b64_json
                            if getattr(img, 'revised_prompt', None):
                                item['revised_prompt'] = img.revised_prompt
                            if item.get('url') or item.get('base64'):
                                images.append(item)
                        if not images:
                            raise WorkflowExecutionError('Agnes image generation returned empty images')
                        return {
                            'success': True,
                            'output': {
                                'images': images,
                                'count': len(images),
                                'provider': 'agnes',
                                'model': agnes_model,
                            }
                        }
                    except Exception as exc:
                        last_err = exc
                        msg = str(exc)
                        retriable = any(
                            tok in msg
                            for tok in (
                                'timed out', 'Timeout', 'Connection', '503',
                                'Service busy', 'ServiceUnavailable', '429', '502', '504',
                                '500', 'do_request_failed', 'upstream_error',
                            )
                        )
                        logger.warning(
                            'Agnes image attempt %s/%s failed: %s',
                            attempt + 1, attempts, msg[:200],
                        )
                        if (not retriable) or attempt >= attempts - 1:
                            break
                        # Longer backoff on provider busy
                        time.sleep(min(45.0, 4.0 * (2 ** attempt)))
                # Secondary provider: OpenAI-compatible image API when configured
                openai_key = self._get_credential('openai')
                if openai_key and node_config.get('allow_provider_fallback', True):
                    try:
                        logger.warning(
                            'Agnes image failed (%s); trying OpenAI image fallback', last_err,
                        )
                        oa = OpenAI(
                            api_key=openai_key,
                            base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None,
                            timeout=120.0,
                            max_retries=0,
                        )
                        oa_model = 'dall-e-3'
                        oa_size = agnes_size if agnes_size in {'1024x1024', '1792x1024', '1024x1792'} else '1024x1024'
                        response = oa.images.generate(
                            model=oa_model,
                            prompt=(prompt or '')[:3900],
                            size=oa_size,
                            n=1,
                        )
                        images = [
                            {
                                'url': getattr(img, 'url', '') or '',
                                'revised_prompt': getattr(img, 'revised_prompt', '') or '',
                            }
                            for img in response.data
                            if getattr(img, 'url', None)
                        ]
                        if images:
                            return {
                                'success': True,
                                'output': {
                                    'images': images,
                                    'count': len(images),
                                    'provider': 'openai-fallback',
                                    'model': oa_model,
                                    'warning': f'agnes failed; used openai fallback: {last_err}',
                                },
                            }
                    except Exception as oa_exc:
                        logger.warning('OpenAI image fallback failed: %s', oa_exc)
                return {
                    'success': False,
                    'error': f'Agnes image generation failed after {attempts} attempts: {last_err}',
                }
            elif provider == 'dashscope':
                api_key, base_url = self._dashscope_credential()
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'X-DashScope-Async': 'enable',
                }
                ds_model = model if model and model.startswith(('wanx', 'wan2')) else 'wanx2.1-t2i-turbo'
                allowed_sizes = {'1024*1024', '720*1280', '1280*720'}
                ds_size = (size or '1024x1024').replace('x', '*').replace('X', '*')
                if ds_size not in allowed_sizes:
                    ds_size = '1024*1024'
                payload = {
                    'model': ds_model,
                    'input': {'prompt': prompt},
                    'parameters': {'size': ds_size, 'n': max(1, min(4, int(n or 1)))},
                }
                with httpx.Client(timeout=IMAGE_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/aigc/text2image/image-synthesis',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 图像生成任务创建失败: {self._dashscope_error_detail(resp)}')
                    task_id = (resp.json().get('output') or {}).get('task_id')
                if not task_id:
                    raise WorkflowExecutionError('DashScope 图像生成任务创建失败：未返回 task_id')
                result = self._poll_dashscope_task(task_id, api_key, base_url, timeout_seconds=180, poll_interval=3)
                images = [{'url': item.get('url', '')} for item in result.get('results', []) if item.get('url')]
                return {
                    'success': True,
                    'output': {
                        'images': images,
                        'count': len(images),
                        'provider': 'dashscope',
                        'model': ds_model,
                        'task_id': task_id,
                    }
                }
            elif provider == 'stability':
                api_key = self._get_credential('stability')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'text_prompts': [{'text': prompt}],
                    'cfg_scale': 7, 'height': 1024, 'width': 1024,
                    'samples': n, 'steps': 30
                }
                with httpx.Client(timeout=IMAGE_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    images = [{'base64': art['base64']} for art in result.get('artifacts', [])]
                    return {'success': True, 'output': {'images': images, 'count': len(images)}}
            elif provider == 'flux':
                api_key = self._get_credential('replicate')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'version': 'latest',
                    'input': {'prompt': prompt, 'num_inference_steps': 25, 'guidance_scale': 3.5, 'num_images': n}
                }
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.replicate.com/v1/predictions',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    pred = resp.json()
                    prediction_id = pred['id']

                # Poll until prediction completes
                final_pred = self._poll_replicate_prediction(prediction_id, timeout_seconds=300)
                output = final_pred.get('output', [])

                if isinstance(output, list):
                    images = []
                    for item in output:
                        if isinstance(item, dict):
                            images.append({'url': item.get('url', ''), 'width': item.get('width'), 'height': item.get('height')})
                        elif isinstance(item, str):
                            images.append({'url': item})
                    return {'success': True, 'output': {'images': images, 'count': len(images)}}
                return {'success': True, 'output': {'images': [], 'raw_output': output}}
            elif provider == 'zimage_local':
                return self._run_zimage_local_generation(
                    prompt=prompt,
                    model=model,
                    size=size,
                    n=n,
                    node_config=node_config,
                )
            elif provider == 'replicate':
                api_key = self._get_credential('replicate')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'version': model,
                    'input': {'prompt': prompt, 'num_outputs': n}
                }
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.replicate.com/v1/predictions',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    pred = resp.json()
                    prediction_id = pred['id']

                # Poll until prediction completes
                final_pred = self._poll_replicate_prediction(prediction_id, timeout_seconds=300)
                output = final_pred.get('output', [])

                if isinstance(output, list):
                    images = []
                    for item in output:
                        if isinstance(item, dict):
                            images.append({'url': item.get('url', ''), 'width': item.get('width'), 'height': item.get('height')})
                        elif isinstance(item, str):
                            images.append({'url': item})
                    return {'success': True, 'output': {'images': images, 'count': len(images)}}
                return {'success': True, 'output': {'images': [], 'raw_output': output}}
            else:
                return {'success': False, 'error': f'Unknown image provider: {provider}'}
        except Exception as e:
            err = str(e)
            if provider == 'openai' and any(token in err for token in ('AuthenticationError', 'Unauthorized', '401', 'invalid_api_key')):
                logger.warning('OpenAI image generation auth failed, using demo output: %s', e)
                return self._image_generation_demo_output(prompt)
            return {'success': False, 'error': str(e)}

    def _video_generation_demo_output(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = '720p',
        input_image: str = '',
        *,
        shot_index: int = 0,
        title: str = '',
        action: str = '',
    ) -> Dict[str, Any]:
        """Distinct local placeholder per shot — never reuse one stock URL."""
        import re
        from workflows.services.media_service import save_output_file
        from workflows.services.video_postprocess import render_storyboard_placeholder_clip

        idx = int(shot_index or 0)
        if idx <= 0:
            m = re.search(r'[Ss]hot\s*(\d+)', str(prompt or ''))
            if not m:
                m = re.search(r'镜\s*(\d+)', str(prompt or ''))
            idx = int(m.group(1)) if m else (abs(hash(str(prompt or 'demo'))) % 12) + 1
        title = title or (str(prompt or '').split('.')[0][:40] if prompt else f'镜头{idx}')
        action = action or str(prompt or '')[:80]
        try:
            local = render_storyboard_placeholder_clip(
                shot_index=idx,
                title=title,
                action=action,
                duration_sec=float(duration or 5),
            )
            saved = save_output_file(local, subdir='workflow_placeholders')
            video_url = saved.get('public_url') or saved.get('local_path') or str(local)
        except Exception as exc:
            logger.warning('placeholder clip render failed, using remote stub: %s', exc)
            video_url = 'https://www.w3schools.com/html/mov_bbb.mp4'
        return {
            'success': True,
            'output': {
                'video_url': video_url,
                'thumbnail': input_image or '',
                'status': 'completed',
                'duration': float(duration or 5),
                'fps': fps,
                'resolution': resolution,
                'demo': True,
                'provider': 'local-placeholder',
                'prompt': prompt,
                'input_image': input_image,
                'shot_index': idx,
                'mode': 'placeholder',
            },
        }

    def _execute_agnes_video_generation(
        self,
        *,
        model: str,
        prompt: str,
        duration: int,
        resolution: str,
        input_image: str,
        timeout_seconds: int = 180,
        mode: str = None,
        reference_images: list = None,
        last_frame: str = None,
        seed: int = None,
        submit_attempts: int = 6,
        credential_id: str = None,
        submit_interval_seconds: int = 0,
    ) -> Dict[str, Any]:
        api_key, base_url = self._agnes_credential(credential_id)
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        agnes_model = model if model and model.startswith('agnes-video') else 'agnes-video-v2.0'
        from .agnes_video import MODERN_MODELS, build_video_payload, reserve_submission
        payload = build_video_payload(agnes_model, prompt, duration, resolution, input_image, mode=mode, reference_images=reference_images, last_frame=last_frame, seed=seed)
        created = None
        last_create_err = ''
        with self._agnes_httpx_client(timeout=min(120, VIDEO_GENERATION_TIMEOUT)) as client:
            attempts = max(1, min(6, int(submit_attempts)))
            for attempt in range(attempts):
                reserve_submission(self.user_id,submit_interval_seconds,lambda:self._report_progress({'status':'queued','progress':0,'provider':'agnes','message':'等待当前账号视频请求窗口，按限速提交'}))
                resp = client.post(f'{base_url}/videos', headers=headers, json=payload)
                if resp.status_code < 400:
                    created = resp.json()
                    break
                detail = self._agnes_error_detail(resp)
                last_create_err = detail
                detail_l = str(detail).lower()
                # Provider backpressure — wait and retry instead of soft-failing the shot
                if any(tok in detail_l for tok in ('queue is full', 'rate limit', 'too many', '429', 'busy')):
                    if attempt == attempts-1:
                        break
                    wait_s = min(90, 10 * (attempt + 1))
                    logger.warning(
                        'Agnes video queue busy (attempt %s/%s), sleep %ss: %s',
                        attempt + 1, attempts, wait_s, detail,
                    )
                    time.sleep(wait_s)
                    continue
                raise WorkflowExecutionError(f'Agnes 视频生成任务创建失败: {detail}')
            if created is None:
                raise WorkflowExecutionError(
                    f'Agnes 视频生成任务创建失败（队列繁忙已重试）: {last_create_err}'
                )
        task_id = (created or {}).get('id') or (created or {}).get('task_id')
        poll_id = (created or {}).get('video_id') if agnes_model in MODERN_MODELS else task_id
        if not poll_id:
            raise WorkflowExecutionError(f'Agnes 视频生成未返回 task_id: {created}')
        progress_meta = {
            'input_image': input_image,
            'prompt': prompt,
            'mode': 'image_to_video' if input_image else 'text_to_video',
        }
        self._report_progress({
            **progress_meta,
            'status': 'queued',
            'task_status': 'queued',
            'progress': 0,
            'task_id': task_id,
            'provider': 'agnes',
            'message': self._format_video_progress_message('queued', 0, 'agnes'),
        })
        result = self._poll_agnes_video_task(
            poll_id, api_key, base_url,
            timeout_seconds=max(60, int(timeout_seconds or 180)),
            poll_interval=5,
            progress_meta=progress_meta,
            model=agnes_model,
        )
        video_url = self._extract_agnes_video_url(result)
        if not video_url:
            raise WorkflowExecutionError(f'Agnes 视频生成完成但未返回 video_url: {result}')
        return {
            'success': True,
            'output': {
                'video_url': video_url,
                'status': 'completed',
                'provider': 'agnes',
                'model': agnes_model,
                'task_id': task_id,
                'video_id': poll_id,
                'duration': float(result.get('seconds') or duration or 5),
                'resolution': resolution,
                'prompt': prompt,
                'input_image': input_image if payload.get('mode') != 'reference' else '',
                'mode': 'reference_to_video' if payload.get('mode') == 'reference' else ('image_to_video' if input_image else 'text_to_video'),
                'generation_mode': payload.get('mode'),
                'reference_images': reference_images or [],
            },
        }

    def run_video_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Video Generation Node
        Generates videos from text or images.
        """
        provider = node_config.get('provider', 'replicate')
        model = node_config.get('model', '')
        prompt = self._resolve_prompt_from_context(node_config, context, field='prompt')
        duration = node_config.get('duration', 4)
        fps = node_config.get('fps', 24)
        resolution = node_config.get('resolution', '720p')
        input_image = self._resolve_input_image(node_config, context)
        # Demo / picsum stills are not useful for Agnes i2v — prefer text-to-video.
        if input_image and any(
            tok in str(input_image).lower()
            for tok in ('picsum.photos', 'demo', 'placeholder')
        ):
            logger.info('Skipping non-production input_image for video: %s', str(input_image)[:120])
            input_image = ''
        resolution_map = {'720p': 720, '1080p': 1080, '4k': 2160}
        height = resolution_map.get(resolution, 720)
        shot_index = 0
        try:
            shot_index = int(
                context.get('shot_index')
                or (context.get('variables') or {}).get('shot_index')
                or 0
            )
        except Exception:
            shot_index = 0
        shot_title = str(context.get('title') or '')
        shot_action = str(context.get('action') or '')

        try:
            # Demo mode: no API key needed, return a simulated video result
            import os
            if not os.environ.get('REPLICATE_API_KEY') and provider == 'replicate':
                return self._video_generation_demo_output(
                    prompt=prompt,
                    duration=duration,
                    fps=fps,
                    resolution=resolution,
                    input_image=input_image,
                    shot_index=shot_index,
                    title=shot_title,
                    action=shot_action,
                )
            if provider == 'agnes':
                # Always call Agnes. Missing still → text-to-video with motion prompt.
                # Do NOT short-circuit to local title-card placeholders.
                try:
                    return self._execute_agnes_video_generation(
                        model=model,
                        prompt=prompt,
                        duration=duration,
                        resolution=resolution,
                        input_image=input_image if (
                            input_image and not any(
                                tok in str(input_image).lower()
                                for tok in ('picsum.photos', 'placeholder', 'demo')
                            )
                        ) else '',
                        timeout_seconds=int(
                            node_config.get('timeout')
                            or node_config.get('timeout_seconds')
                            or 600
                        ),
                        mode=node_config.get('mode'),
                        reference_images=self._resolve_reference_images(node_config, context),
                        last_frame=self._render_template(node_config.get('lastFrame') or node_config.get('last_frame') or '', context),
                        seed=node_config.get('seed'),
                        submit_attempts=node_config.get('submit_attempts', 6),
                        credential_id=node_config.get('credentialId') or node_config.get('credential_id'),
                        submit_interval_seconds=node_config.get('submit_interval_seconds',0),
                    )
                except Exception as agnes_exc:
                    logger.error('Agnes video failed: %s', agnes_exc)
                    return {
                        'success': False,
                        'error': f'Agnes video generation failed: {agnes_exc}',
                    }
            if provider == 'dashscope':
                api_key, base_url = self._dashscope_credential()
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'X-DashScope-Async': 'enable',
                }
                ds_model = self._normalize_dashscope_video_model(model, input_image)
                ds_resolution_map = {'720p': '720P', '1080p': '1080P', '4k': '1080P', '480p': '480P'}
                ds_input = {'prompt': prompt}
                if input_image:
                    ds_input['img_url'] = input_image
                ds_parameters = {
                    'resolution': ds_resolution_map.get(str(resolution or '720p').lower(), '720P'),
                }
                fixed_duration_models = {
                    'wanx2.1-t2v-turbo', 'wanx2.1-t2v-plus', 'wan2.1-t2v-turbo',
                    'wan2.1-t2v-plus', 'wan2.2-t2v-plus',
                    'wanx2.1-i2v-turbo', 'wanx2.1-i2v-plus', 'wan2.1-i2v-turbo', 'wan2.1-i2v-plus',
                }
                if ds_model not in fixed_duration_models:
                    ds_parameters['duration'] = max(1, min(15, int(duration or 5)))
                elif input_image and 'i2v' in ds_model:
                    ds_parameters['duration'] = max(3, min(5, int(duration or 5)))
                payload = {
                    'model': ds_model,
                    'input': ds_input,
                    'parameters': ds_parameters,
                }
                with self._dashscope_httpx_client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/aigc/video-generation/video-synthesis',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 视频生成任务创建失败: {self._dashscope_error_detail(resp)}')
                    task_id = (resp.json().get('output') or {}).get('task_id')
                if not task_id:
                    raise WorkflowExecutionError('DashScope 视频生成任务创建失败：未返回 task_id')
                result = self._poll_dashscope_task(task_id, api_key, base_url, timeout_seconds=600, poll_interval=10)
                video_url = result.get('video_url') or ''
                if not video_url and result.get('results'):
                    first = result['results'][0] if isinstance(result['results'], list) else {}
                    if isinstance(first, dict):
                        video_url = first.get('url') or first.get('video_url') or ''
                if not video_url:
                    raise WorkflowExecutionError(f'DashScope 视频生成完成但未返回 video_url: {result}')
                actual_duration = ds_parameters.get('duration', 5)
                return {
                    'success': True,
                    'output': {
                        'video_url': video_url,
                        'status': 'completed',
                        'provider': 'dashscope',
                        'model': ds_model,
                        'task_id': task_id,
                        'duration': actual_duration,
                        'fps': 30,
                        'resolution': resolution,
                        'prompt': prompt,
                        'input_image': input_image,
                        'mode': 'image_to_video' if input_image else 'text_to_video',
                    },
                }
            if provider == 'replicate':
                api_key = self._get_credential('replicate')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                inp = {'prompt': prompt, 'num_frames': duration * fps, 'fps': fps}
                if input_image:
                    inp['input_image'] = input_image
                payload = {'version': model or 'latest', 'input': inp}
                with httpx.Client(timeout=HTTP_TOOL_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.replicate.com/v1/predictions',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    pred = resp.json()
                    prediction_id = pred['id']

                # Poll until prediction completes
                final_pred = self._poll_replicate_prediction(prediction_id, timeout_seconds=300)
                output = final_pred.get('output', {})
                video_url = output.get('video') or output.get('url') or ''
                if isinstance(output, list):
                    video_url = output[0] if output else ''
                return {
                    'success': True,
                    'output': {
                        'video_url': video_url,
                        'status': 'completed',
                        'prediction_id': prediction_id,
                        'output': output
                    }
                }
            elif provider == 'runway':
                api_key = self._get_credential('runway')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {'prompt': prompt, 'model': model or 'gen3a_turbo', 'duration': duration}
                with httpx.Client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.runwayml.com/v1/video_generation',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    return {'success': True, 'output': resp.json()}
            elif provider == 'pika':
                api_key = self._get_credential('pika')
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                payload = {'prompt': prompt, 'model': model or 'pika-2.0', 'duration': duration}
                with httpx.Client(timeout=VIDEO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        'https://api.pika.art/v1/generate',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    return {'success': True, 'output': resp.json()}
            else:
                return {'success': False, 'error': f'Unknown video provider: {provider}'}
        except Exception as e:
            err = str(e)
            import os
            # DashScope 鉴权/调用失败时，若上游有图则自动降级 Agnes 图生视频
            if provider == 'dashscope' and input_image:
                try:
                    agnes_key = self._get_credential('agnes') or (getattr(settings, 'AGNES_API_KEY', '') or '').strip()
                    if agnes_key:
                        logger.warning('DashScope 视频生成失败，降级 Agnes 图生视频: %s', e)
                        return self._execute_agnes_video_generation(
                            model='agnes-video-v2.0',
                            prompt=prompt,
                            duration=duration,
                            resolution=resolution,
                            input_image=input_image,
                        )
                except Exception as agnes_err:
                    err = f'{err}; Agnes 降级失败: {agnes_err}'
            if provider == 'replicate' and not os.environ.get('REPLICATE_API_KEY'):
                logger.warning('Replicate 未配置 API Key，使用 demo 视频: %s', e)
                return self._video_generation_demo_output(
                    prompt, duration, fps, resolution, input_image=input_image
                )
            logger.error('Video generation failed (%s): %s', provider, e)
            return {'success': False, 'error': f'视频生成失败 ({provider}): {err}'}

    def _audio_generation_demo_output(self, text: str, audio_format: str = 'mp3') -> Dict[str, Any]:
        return {
            'success': True,
            'output': {
                'audio_url': 'https://www.w3schools.com/html/horse.mp3',
                'format': audio_format,
                'duration_est': max(1, len(str(text or '')) / 5),
                'demo': True,
                'text': text,
            },
        }

    def _synthesize_audio_with_fallbacks(
        self,
        *,
        text: str,
        voice: str,
        audio_format: str,
        speed: float,
        preferred: str,
        target_language: str = 'zh',
    ) -> Dict[str, Any]:
        """Try multiple TTS backends so short-drama finishing never dies on network TTS."""
        from pathlib import Path as _Path
        import base64
        import tempfile

        preferred = (preferred or 'auto').lower()
        order = []
        if preferred in ('edge_tts', 'agnes', 'agnes-tts', 'agnes_tts'):
            order = ['edge_tts', 'gtts', 'pyttsx3']
        elif preferred == 'gtts':
            order = ['gtts', 'pyttsx3', 'edge_tts']
        elif preferred in ('pyttsx3', 'local_tts'):
            order = ['pyttsx3', 'gtts', 'edge_tts']
        else:
            order = ['pyttsx3', 'gtts', 'edge_tts']

        errors = []
        for backend in order:
            try:
                if backend == 'edge_tts':
                    from workflows.services.video_translation.constants import EDGE_TTS_VOICES
                    from workflows.services.video_translation.media_providers import synthesize_edge_tts
                    ds_voice = voice if voice and '-' in str(voice) else EDGE_TTS_VOICES.get(
                        target_language or 'zh', 'zh-CN-XiaoxiaoNeural',
                    )
                    if target_language in ('zh', 'zh-cn', 'cn') and (not voice or voice == 'alloy'):
                        ds_voice = 'zh-CN-XiaoxiaoNeural'
                    tmp = _Path(tempfile.gettempdir()) / f'flowly_edge_tts_{uuid.uuid4().hex}.{audio_format or "mp3"}'
                    synthesize_edge_tts(text, voice=ds_voice, output_path=tmp)
                    audio_b64 = base64.b64encode(tmp.read_bytes()).decode()
                    return {
                        'success': True,
                        'output': {
                            'audio_base64': audio_b64,
                            'format': audio_format or 'mp3',
                            'provider': 'edge_tts',
                            'voice': ds_voice,
                            'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                        },
                    }
                if backend == 'gtts':
                    from gtts import gTTS
                    from workflows.services.video_translation.constants import GTTS_LANG_CODES
                    lang = GTTS_LANG_CODES.get(target_language or 'zh', 'zh-cn')
                    if target_language in ('zh', 'zh-cn', 'cn'):
                        lang = 'zh-cn'
                    tmp = _Path(tempfile.gettempdir()) / f'flowly_gtts_{uuid.uuid4().hex}.mp3'
                    gTTS(text or ' ', lang=lang).save(str(tmp))
                    audio_b64 = base64.b64encode(tmp.read_bytes()).decode()
                    return {
                        'success': True,
                        'output': {
                            'audio_base64': audio_b64,
                            'format': 'mp3',
                            'provider': 'gtts',
                            'voice': lang,
                            'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                        },
                    }
                if backend == 'pyttsx3':
                    from workflows.services.video_translation.media_providers import synthesize_pyttsx3
                    tmp = _Path(tempfile.gettempdir()) / f'flowly_pyttsx3_{uuid.uuid4().hex}.wav'
                    synthesize_pyttsx3(
                        text or ' ',
                        output_path=tmp,
                        voice_id=voice if voice and voice != 'alloy' else None,
                        language=target_language,
                    )
                    audio_b64 = base64.b64encode(tmp.read_bytes()).decode()
                    return {
                        'success': True,
                        'output': {
                            'audio_base64': audio_b64,
                            'format': 'wav',
                            'provider': 'pyttsx3',
                            'voice': voice or 'system-default',
                            'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                        },
                    }
            except Exception as exc:
                errors.append(f'{backend}: {exc}')
                logger.warning('TTS backend %s failed: %s', backend, exc)

        logger.error('All TTS backends failed: %s', errors)
        out = self._audio_generation_demo_output(text, audio_format or 'mp3')
        out['output']['warning'] = '; '.join(errors)[:500]
        out['output']['fallback'] = True
        return out

    def run_audio_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audio/TTS Generation Node
        Generates audio from text using TTS providers.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'tts-1')
        text_template = node_config.get('text') or node_config.get('prompt') or ''
        text = self._render_template(text_template, context) if text_template else (context.get('text') or context.get('prompt') or '')
        voice = node_config.get('voice', 'alloy')
        speed = node_config.get('speed', 1.0)
        audio_format = node_config.get('format', 'mp3')

        try:
            if provider == 'openai':
                api_key = self._get_credential('openai')
                if not api_key or node_config.get('demo_mode'):
                    return self._audio_generation_demo_output(text, audio_format)
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
                response = client.audio.speech.create(
                    model=model, input=text, voice=voice,
                    response_format=audio_format, speed=speed
                )
                import base64
                audio_bytes = response.content
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return {'success': True, 'output': {'audio_base64': audio_b64, 'format': audio_format, 'duration_est': len(text) / (5 * speed)}}
            elif provider == 'dashscope':
                api_key, base_url = self._dashscope_credential()
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                ds_model = model if model and model.startswith('cosyvoice') else 'cosyvoice-v3-flash'
                ds_voice = voice if voice and voice not in ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer') else 'longanyang'
                ds_format = audio_format if audio_format in ('mp3', 'wav', 'pcm', 'opus') else 'mp3'
                payload = {
                    'model': ds_model,
                    'input': {'text': text, 'voice': ds_voice, 'format': ds_format},
                }
                with httpx.Client(timeout=AUDIO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/audio/tts/SpeechSynthesizer',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 语音合成失败: {self._dashscope_error_detail(resp)}')
                    data = resp.json()
                audio_url = ((data.get('output') or {}).get('audio') or {}).get('url', '')
                if not audio_url:
                    raise WorkflowExecutionError(f'DashScope 语音合成未返回音频地址: {data}')
                return {
                    'success': True,
                    'output': {
                        'audio_url': audio_url,
                        'format': ds_format,
                        'provider': 'dashscope',
                        'model': ds_model,
                        'voice': ds_voice,
                        'duration_est': max(1, len(text) / (5 * (speed or 1.0))),
                    }
                }
            elif provider == 'elevenlabs':
                api_key = self._get_credential('elevenlabs')
                headers = {'xi-api-key': api_key, 'Content-Type': 'application/json'}
                payload = {'text': text, 'model_id': model or 'eleven_monolingual_v1',
                            'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75, 'speed': speed}}
                with httpx.Client(timeout=AUDIO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'https://api.elevenlabs.io/v1/text-to-speech/{voice}',
                        headers=headers, json=payload
                    )
                    resp.raise_for_status()
                    import base64
                    audio_b64 = base64.b64encode(resp.content).decode()
                    return {'success': True, 'output': {'audio_base64': audio_b64, 'format': 'mp3'}}
            elif provider == 'azure':
                subscription_key = self._get_credential('azure_tts')
                region = node_config.get('region', 'eastus')
                headers = {'Ocp-Apim-Subscription-Key': subscription_key, 'Content-Type': 'application/ssml+xml'}
                ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="{voice}"><prosody rate="{speed}">{text}</prosody></voice></speak>'
                with httpx.Client(timeout=AUDIO_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
                        headers=headers, data=ssml.encode()
                    )
                    resp.raise_for_status()
                    import base64
                    audio_b64 = base64.b64encode(resp.content).decode()
                    return {'success': True, 'output': {'audio_base64': audio_b64, 'format': 'mp3'}}
            elif provider in (
                'edge_tts', 'gtts', 'pyttsx3', 'local_tts', 'auto',
                'agnes', 'agnes-tts', 'agnes_tts',
            ):
                # Cascading TTS: edge → gTTS → local pyttsx3 → demo (never hard-fail film)
                return self._synthesize_audio_with_fallbacks(
                    text=text,
                    voice=voice,
                    audio_format=audio_format,
                    speed=speed or 1.0,
                    preferred=provider,
                    target_language=(
                        node_config.get('target_language')
                        or context.get('target_language')
                        or node_config.get('language')
                        or 'zh'
                    ),
                )
            else:
                return {'success': False, 'error': f'Unknown audio provider: {provider}'}
        except Exception as e:
            err = str(e)
            if provider == 'openai' and any(token in err for token in ('AuthenticationError', 'Unauthorized', '401', 'invalid_api_key')):
                logger.warning('OpenAI audio generation auth failed, using demo output: %s', e)
                return self._audio_generation_demo_output(text, audio_format)
            logger.warning('Audio generation failed (%s), falling back: %s', provider, e)
            try:
                return self._synthesize_audio_with_fallbacks(
                    text=text,
                    voice=voice,
                    audio_format=audio_format,
                    speed=speed or 1.0,
                    preferred='auto',
                    target_language=node_config.get('language') or 'zh',
                )
            except Exception:
                return self._audio_generation_demo_output(text, audio_format)

    def run_subtitle_generation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Subtitle Generation Node
        Generates subtitles from audio/video via local_whisper, OpenAI Whisper, or DashScope Paraformer.
        """
        input_path = (
            node_config.get('inputPath')
            or node_config.get('input_path')
            or node_config.get('input')
            or context.get('inputPath')
            or context.get('input')
            or context.get('video_url')
            or context.get('audio_url')
            or context.get('url')
            or ''
        )
        language = node_config.get('language', 'zh')
        format = node_config.get('format', 'srt')
        default_provider = getattr(settings, 'VIDEO_TRANSLATION_ASR_PROVIDER', 'local_whisper') or 'local_whisper'
        provider = (node_config.get('provider') or default_provider).strip().lower()
        rendered_path = (
            self._render_template(str(input_path), context)
            if '{' in str(input_path)
            else str(input_path)
        )
        if not rendered_path or '{' in rendered_path:
            urls = context.get('video_urls') if isinstance(context.get('video_urls'), list) else []
            first_list_url = next((u for u in urls if isinstance(u, str) and u.strip()), '')
            rendered_path = (
                context.get('video_url')
                or context.get('source_video_url')
                or context.get('public_url')
                or first_list_url
                or ''
            )
            if not rendered_path or '{' in str(rendered_path):
                raise WorkflowExecutionError(
                    '字幕节点缺少可用 video_url（上游拼接未产出或模板未解析）'
                )

        try:
            if provider == 'dashscope':
                if not rendered_path.lower().startswith(('http://', 'https://')):
                    raise WorkflowExecutionError('DashScope 语音识别要求公网可访问的音频/视频 URL')
                result = self._run_dashscope_subtitle_generation(rendered_path, language, format)
            elif provider == 'local_whisper':
                from workflows.services.media_service import resolve_local_media_path
                from workflows.services.video_translation.media_providers import transcribe_local_whisper
                local_path = resolve_local_media_path(rendered_path)
                result = transcribe_local_whisper(local_path, language=language, format=format)
            else:
                from workflows.services.media_service import resolve_local_media_path
                api_key = self._get_credential('openai')
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
                local_path = resolve_local_media_path(rendered_path) if rendered_path else None
                if not local_path or not local_path.exists():
                    raise WorkflowExecutionError('OpenAI Whisper 需要可读取的本地媒体文件或 URL')
                with open(local_path, 'rb') as f:
                    transcript = client.audio.transcriptions.create(
                        model='whisper-1', file=f, language=language
                    )
                text = transcript.text
                segments = getattr(transcript, 'segments', [])
                if format == 'srt':
                    content = self._text_to_srt(text, segments)
                elif format == 'vtt':
                    content = self._text_to_vtt(text, segments)
                else:
                    content = text
                result = {
                    'success': True,
                    'output': {
                        'subtitles': content,
                        'format': format,
                        'text': text,
                        'segments': segments,
                        'source_segments': segments,
                        'provider': 'openai',
                        'model': 'whisper-1',
                    },
                }

            if result.get('success') and isinstance(result.get('output'), dict):
                output = result['output']
                video_url = context.get('source_video_url') or context.get('video_url') or rendered_path
                if video_url:
                    output.setdefault('video_url', video_url)
                    output.setdefault('source_video_url', video_url)
                if context.get('duration'):
                    output.setdefault('duration', context.get('duration'))
            return result
        except ImportError:
            return {'success': False, 'error': 'openai library required. Install with: pip install openai'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _run_dashscope_subtitle_generation(self, input_url: str, language: str, format: str) -> Dict[str, Any]:
        """Generate subtitles from a public audio/video URL via DashScope Paraformer 录音文件识别 API."""
        if not input_url or not str(input_url).lower().startswith(('http://', 'https://')):
            raise WorkflowExecutionError('DashScope 语音识别要求提供公网可访问的音频/视频 URL（inputPath/input）')

        api_key, base_url = self._dashscope_credential()
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable',
        }
        language_hints = [language] if language and language not in ('auto', '') else ['zh', 'en']
        payload = {
            'model': 'paraformer-v2',
            'input': {'file_urls': [input_url]},
            'parameters': {'language_hints': language_hints},
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(f'{base_url}/services/audio/asr/transcription', headers=headers, json=payload)
            if resp.status_code >= 400:
                raise WorkflowExecutionError(f'DashScope 语音识别任务创建失败: {self._dashscope_error_detail(resp)}')
            task_id = (resp.json().get('output') or {}).get('task_id')
        if not task_id:
            raise WorkflowExecutionError('DashScope 语音识别任务创建失败：未返回 task_id')

        result = self._poll_dashscope_task(task_id, api_key, base_url, timeout_seconds=300, poll_interval=5)
        results = result.get('results', [])
        if not results:
            raise WorkflowExecutionError('DashScope 语音识别未返回结果')
        first = results[0]
        if first.get('subtask_status') == 'FAILED':
            raise WorkflowExecutionError(f"DashScope 语音识别失败: {first.get('message', '未知错误')}")
        transcription_url = first.get('transcription_url')
        if not transcription_url:
            raise WorkflowExecutionError('DashScope 语音识别结果缺少 transcription_url')

        with httpx.Client(timeout=60) as client:
            trans_resp = client.get(transcription_url)
            trans_resp.raise_for_status()
            transcript_data = trans_resp.json()

        transcripts = transcript_data.get('transcripts', [])
        full_text = ' '.join(t.get('text', '') for t in transcripts).strip()
        segments = []
        for t in transcripts:
            for sentence in t.get('sentences', []):
                segments.append({
                    'start': (sentence.get('begin_time') or 0) / 1000.0,
                    'end': (sentence.get('end_time') or 0) / 1000.0,
                    'text': sentence.get('text', ''),
                })

        if format == 'srt':
            content = self._text_to_srt(full_text, segments)
        elif format == 'vtt':
            content = self._text_to_vtt(full_text, segments)
        else:
            content = full_text

        return {
            'success': True,
            'output': {
                'subtitles': content,
                'format': format,
                'text': full_text,
                'segments': segments,
                'source_segments': segments,
                'provider': 'dashscope',
                'model': 'paraformer-v2',
                'task_id': task_id,
            }
        }

    def _text_to_srt(self, text: str, segments: list) -> str:
        import datetime
        lines = []
        for i, seg in enumerate(segments or [], 1):
            start = self._seconds_to_srt_time(seg.get('start', 0))
            end = self._seconds_to_srt_time(seg.get('end', 0))
            lines.append(f"{i}\n{start} --> {end}\n{seg.get('text', '').strip()}\n")
        if not lines:
            lines.append(f"1\n00:00:00,000 --> 00:00:05,000\n{text}\n")
        return '\n'.join(lines)

    def _text_to_vtt(self, text: str, segments: list) -> str:
        lines = ['WEBVTT\n']
        for seg in segments or []:
            start = self._seconds_to_vtt_time(seg.get('start', 0))
            end = self._seconds_to_vtt_time(seg.get('end', 0))
            lines.append(f"{start} --> {end}\n{seg.get('text', '').strip()}\n")
        if len(lines) == 1:
            lines.append("00:00:00.000 --> 00:00:05.000\n" + text + "\n")
        return '\n'.join(lines)

    def _seconds_to_srt_time(self, seconds: float) -> str:
        import datetime
        td = datetime.timedelta(seconds=seconds)
        h = td.seconds // 3600
        m = (td.seconds % 3600) // 60
        s = td.seconds % 60
        ms = td.microseconds // 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        import datetime
        td = datetime.timedelta(seconds=seconds)
        h = td.seconds // 3600
        m = (td.seconds % 3600) // 60
        s = td.seconds % 60
        ms = td.microseconds // 1000
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def run_video_translation_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Video Translation Node — ASR → translate → TTS → VideoRetalk lip sync → burn subtitles.
        """
        from workflows.services.media_service import download_url_to_media, save_output_file
        from workflows.services.video_translation.pipeline import VideoTranslationPipeline

        def asr_call(video_url: str, language: str) -> Dict[str, Any]:
            fmt = node_config.get('subtitle_format') or node_config.get('subtitleFormat') or 'srt'
            if fmt == 'both':
                fmt = 'srt'
            asr_provider = (
                node_config.get('asr_provider')
                or node_config.get('provider')
                or getattr(settings, 'VIDEO_TRANSLATION_ASR_PROVIDER', 'local_whisper')
            )
            return self.run_subtitle_generation_node(
                {'provider': asr_provider, 'inputPath': video_url, 'language': language, 'format': fmt},
                {**context, 'video_url': video_url, 'source_video_url': video_url},
            )

        def llm_call(prompt: str) -> str:
            model = (
                node_config.get('translation_model')
                or node_config.get('model')
                or getattr(settings, 'NL_WORKFLOW_MODEL', None)
                or getattr(settings, 'DEFAULT_LLM_MODEL', 'qwen2.5-coder:7b')
            )
            result = self.run_llm_node(
                {'prompt': prompt, 'model': model, 'temperature': 0.3, 'max_tokens': 4096},
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'LLM 翻译失败')
            return (result.get('output') or {}).get('text') or ''

        def tts_call(text: str, voice: str, fmt: str) -> str:
            tts_provider = (
                node_config.get('tts_provider')
                or getattr(settings, 'VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3')
            )
            result = self.run_audio_generation_node(
                {
                    'provider': tts_provider,
                    'model': node_config.get('tts_model') or 'tts-1',
                    'text': text,
                    'voice': voice,
                    'format': fmt,
                    'target_language': node_config.get('target_language'),
                },
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'TTS 合成失败')
            output = result.get('output') or {}
            audio_url = output.get('audio_url')
            if audio_url:
                local = download_url_to_media(audio_url, subdir='video_translation/tts')
                return str(local)
            import base64
            import tempfile
            audio_b64 = output.get('audio_base64')
            if audio_b64:
                tmp = Path(tempfile.gettempdir()) / f'flowly_tts_{uuid.uuid4().hex}.{fmt}'
                tmp.write_bytes(base64.b64decode(audio_b64))
                saved = save_output_file(tmp, subdir='video_translation/tts')
                return saved['local_path']
            raise WorkflowExecutionError('TTS 未返回音频')

        def progress(step: str, meta: Dict[str, Any]) -> None:
            self._report_progress({
                'video_translation_step': step,
                **meta,
            })

        pipeline = VideoTranslationPipeline(
            asr_call=asr_call,
            llm_call=llm_call,
            tts_call=tts_call,
            dashscope_credential=self._dashscope_credential,
            poll_dashscope_task=self._poll_dashscope_task,
            progress=progress,
            render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
        )
        result = pipeline.run(node_config, context)
        if result.get('success'):
            output = result.get('output') or {}
            primary = (output.get('results') or [{}])[0]
            output['video_url'] = primary.get('video_url')
            output['subtitles'] = primary.get('subtitles')
            output['lip_sync_applied'] = primary.get('lip_sync_applied')
            result['output'] = output
        return result

    def run_video_upload_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_video_upload
        try:
            return run_video_upload(
                node_config,
                context,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_subtitle_translate_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_subtitle_translate

        def llm_call(prompt: str) -> str:
            model = (
                node_config.get('translation_model')
                or node_config.get('model')
                or getattr(settings, 'NL_WORKFLOW_MODEL', None)
                or getattr(settings, 'DEFAULT_LLM_MODEL', 'qwen2.5-coder:7b')
            )
            result = self.run_llm_node(
                {'prompt': prompt, 'model': model, 'temperature': 0.3, 'max_tokens': 4096},
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'LLM 翻译失败')
            return (result.get('output') or {}).get('text') or ''

        try:
            return run_subtitle_translate(
                node_config,
                context,
                llm_call=llm_call,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_segment_dubbing_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.media_service import download_url_to_media, save_output_file
        from workflows.services.video_translation.node_runners import run_segment_dubbing

        def tts_call(text: str, voice: str, fmt: str) -> str:
            tts_provider = (
                node_config.get('provider')
                or node_config.get('tts_provider')
                or getattr(settings, 'VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3')
            )
            # Local SAPI TTS always emits WAV; normalize format so FFmpeg can probe it
            audio_format = 'wav' if str(tts_provider).lower() in ('pyttsx3', 'local_tts') else (fmt or 'mp3')
            result = self.run_audio_generation_node(
                {
                    'provider': tts_provider,
                    'model': node_config.get('tts_model') or 'tts-1',
                    'text': text,
                    'voice': voice,
                    'format': audio_format,
                    'target_language': node_config.get('target_language'),
                },
                context,
            )
            if not result.get('success'):
                raise WorkflowExecutionError(result.get('error') or 'TTS 合成失败')
            output = result.get('output') or {}
            audio_url = output.get('audio_url')
            if audio_url:
                return str(download_url_to_media(audio_url, subdir='video_translation/tts'))
            import base64
            import tempfile
            audio_b64 = output.get('audio_base64')
            if audio_b64:
                out_fmt = output.get('format') or audio_format or 'wav'
                tmp = Path(tempfile.gettempdir()) / f'flowly_tts_{uuid.uuid4().hex}.{out_fmt}'
                tmp.write_bytes(base64.b64decode(audio_b64))
                return save_output_file(tmp, subdir='video_translation/tts')['local_path']
            raise WorkflowExecutionError('TTS 未返回音频')

        try:
            return run_segment_dubbing(node_config, context, tts_call=tts_call)
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_lip_sync_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_lip_sync
        try:
            return run_lip_sync(
                node_config,
                context,
                dashscope_credential=self._dashscope_credential,
                poll_dashscope_task=self._poll_dashscope_task,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_subtitle_burn_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from workflows.services.video_translation.node_runners import run_subtitle_burn
        try:
            return run_subtitle_burn(
                node_config,
                context,
                render_template=lambda tpl, ctx: self._render_template(tpl, ctx),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def run_image_editing_node(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Image Editing Node
        Edits existing images based on instructions.
        """
        provider = node_config.get('provider', 'openai')
        model = node_config.get('model', 'dall-e-2')
        # Resolve {images.0.url} etc. the same way as video_generation
        image = self._resolve_input_image(node_config, context)
        instruction_template = node_config.get('instruction') or node_config.get('prompt') or ''
        instruction = (
            self._render_template(instruction_template, context)
            if instruction_template
            else (context.get('instruction') or context.get('prompt') or '')
        )
        mask = node_config.get('mask', '')
        if mask and '{' in str(mask):
            mask = self._render_template(str(mask), context)

        try:
            if provider == 'openai':
                api_key = self._get_credential('openai')
                if not api_key:
                    return {
                        'success': True,
                        'output': {
                            'images': [{'url': f'https://picsum.photos/seed/{abs(hash(str(instruction))) % 100000}/1024/1024', 'revised_prompt': f'[Demo Mode] {instruction}'}],
                            'url': f'https://picsum.photos/seed/{abs(hash(str(instruction))) % 100000}/1024/1024',
                            'count': 1,
                            'demo': True
                        }
                    }
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=getattr(settings, 'OPENAI_BASE_URL', None) or None)
                image_file = None
                mask_file = None
                try:
                    if image:
                        image_file = open(image, 'rb') if not image.startswith('http') else None
                    if mask:
                        mask_file = open(mask, 'rb') if not mask.startswith('http') else None
                    response = client.images.edit(
                        model=model,
                        image=image_file,
                        mask=mask_file,
                        prompt=instruction,
                        n=1
                    )
                finally:
                    if image_file:
                        image_file.close()
                    if mask_file:
                        mask_file.close()
                return {'success': True, 'output': {'url': response.data[0].url, 'revised_prompt': response.data[0].revised_prompt}}
            elif provider == 'dashscope':
                if not image:
                    raise WorkflowExecutionError('DashScope 图像编辑需要提供原始图像 URL（image/inputImage）')
                api_key, base_url = self._dashscope_credential()
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                ds_model = model if model and model.startswith('wan') else 'wan2.6-image'
                content = [{'text': instruction}, {'image': image}]
                if mask:
                    content.append({'image': mask})
                payload = {
                    'model': ds_model,
                    'input': {'messages': [{'role': 'user', 'content': content}]},
                    'parameters': {'n': 1, 'watermark': False},
                }
                with httpx.Client(timeout=IMAGE_GENERATION_TIMEOUT) as client:
                    resp = client.post(
                        f'{base_url}/services/aigc/multimodal-generation/generation',
                        headers=headers, json=payload
                    )
                    if resp.status_code >= 400:
                        raise WorkflowExecutionError(f'DashScope 图像编辑失败: {self._dashscope_error_detail(resp)}')
                    data = resp.json()
                choices = (data.get('output') or {}).get('choices') or []
                image_url = ''
                for choice in choices:
                    for item in (choice.get('message', {}) or {}).get('content', []) or []:
                        if item.get('type') == 'image' and item.get('image'):
                            image_url = item['image']
                            break
                    if image_url:
                        break
                if not image_url:
                    raise WorkflowExecutionError(f'DashScope 图像编辑未返回图像结果: {data}')
                return {'success': True, 'output': {'url': image_url, 'provider': 'dashscope', 'model': ds_model}}
            else:
                return {'success': False, 'error': f'Unknown image editing provider: {provider}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
