"""
Hardware capability detection and YOLO training recommendations.

Used when NL workflow generates YOLO / Site Factory graphs so training params
match the execution environment (client browser device + server worker).
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

# Pin pairs verified with ultralytics 8.4 in Docker E2E
PYTORCH_CPU = {
    'torch_version': '2.8.0+cpu',
    'torchvision_version': '0.23.0+cpu',
    'index_url': 'https://download.pytorch.org/whl/cpu',
    'variant': 'cpu',
}
PYTORCH_CUDA124 = {
    'torch_version': '2.8.0+cu124',
    'torchvision_version': '0.23.0+cu124',
    'index_url': 'https://download.pytorch.org/whl/cu124',
    'variant': 'cuda124',
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _detect_nvidia_gpus() -> List[Dict[str, Any]]:
    if shutil.which('nvidia-smi') is None:
        return []
    try:
        proc = subprocess.run(
            [
                'nvidia-smi',
                '--query-gpu=name,memory.total,driver_version',
                '--format=csv,noheader,nounits',
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            return []
        gpus: List[Dict[str, Any]] = []
        for line in (proc.stdout or '').strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                gpus.append({
                    'name': parts[0],
                    'memory_total_mb': _safe_int(parts[1]),
                    'driver_version': parts[2],
                })
        return gpus
    except Exception as exc:
        logger.debug('nvidia-smi failed: %s', exc)
        return []


def _detect_torch_runtime() -> Dict[str, Any]:
    info: Dict[str, Any] = {'installed': False}
    try:
        import torch  # noqa: WPS433

        info['installed'] = True
        info['version'] = torch.__version__
        info['cuda_available'] = bool(torch.cuda.is_available())
        if info['cuda_available']:
            info['cuda_device_name'] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info['cuda_memory_total_mb'] = int(getattr(props, 'total_memory', 0) // (1024 * 1024))
    except Exception as exc:
        info['error'] = str(exc)
    return info


def detect_server_hardware() -> Dict[str, Any]:
    """Detect hardware on the machine running Django/Celery."""
    mem = psutil.virtual_memory()
    gpus = _detect_nvidia_gpus()
    torch_info = _detect_torch_runtime()
    return {
        'source': 'server',
        'platform': platform.system(),
        'platform_release': platform.release(),
        'cpu_count': os.cpu_count() or psutil.cpu_count(logical=True) or 1,
        'memory_total_gb': round(mem.total / (1024 ** 3), 1),
        'memory_available_gb': round(mem.available / (1024 ** 3), 1),
        'gpus': gpus,
        'gpu_available': bool(gpus) or torch_info.get('cuda_available'),
        'torch': torch_info,
        'in_docker': os.path.exists('/.dockerenv') or os.getenv('YOLO_CONFIG_DIR') == '/opt/ultralytics',
    }


def normalize_client_capabilities(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize browser-reported capabilities from the frontend."""
    raw = raw if isinstance(raw, dict) else {}
    nav = raw.get('navigator') if isinstance(raw.get('navigator'), dict) else {}
    screen = raw.get('screen') if isinstance(raw.get('screen'), dict) else {}
    return {
        'source': 'client',
        'platform': str(raw.get('platform') or nav.get('platform') or ''),
        'cpu_cores': _safe_int(nav.get('hardwareConcurrency') or raw.get('cpuCores'), 0),
        'device_memory_gb': _safe_int(nav.get('deviceMemory') or raw.get('deviceMemoryGb'), 0),
        'screen_width': _safe_int(screen.get('width') or raw.get('screenWidth'), 0),
        'screen_height': _safe_int(screen.get('height') or raw.get('screenHeight'), 0),
        'user_agent': str(nav.get('userAgent') or raw.get('userAgent') or '')[:240],
        'prefer_local_training': bool(raw.get('preferLocalTraining', True)),
    }


def merge_hardware_profile(
    client: Optional[Dict[str, Any]] = None,
    server: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge client hints with server detection; server GPU wins for cloud training."""
    server = server or detect_server_hardware()
    client_norm = normalize_client_capabilities(client)
    execution_target = 'server'
    if client_norm.get('prefer_local_training') and client_norm.get('cpu_cores', 0) >= 4:
        execution_target = 'client_local'
    gpu_available = bool(server.get('gpu_available'))
    return {
        'client': client_norm,
        'server': server,
        'execution_target': execution_target,
        'gpu_available': gpu_available,
        'recommended_training_mode': 'cloud' if gpu_available and execution_target == 'server' else 'local',
    }


def recommend_pytorch_install(profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    profile = profile or merge_hardware_profile()
    server = profile.get('server') or {}
    if server.get('gpu_available'):
        spec = dict(PYTORCH_CUDA124)
        spec['install_command'] = (
            f"pip install torch=={spec['torch_version']} torchvision=={spec['torchvision_version']} "
            f"--index-url {spec['index_url']}"
        )
        return spec
    spec = dict(PYTORCH_CPU)
    spec['install_command'] = (
        f"pip install torch=={spec['torch_version']} torchvision=={spec['torchvision_version']} "
        f"--index-url {spec['index_url']}"
    )
    return spec


def recommend_yolo_training_config(profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return YOLO node defaults tuned to hardware."""
    profile = profile or merge_hardware_profile()
    server = profile.get('server') or {}
    mem_gb = float(server.get('memory_available_gb') or server.get('memory_total_gb') or 8)
    gpu = bool(profile.get('gpu_available'))

    if gpu:
        epochs, batch, imgsz, device, variant = 50, 16, 640, 'cuda', 'n'
        if mem_gb < 12:
            batch, imgsz, variant = 8, 512, 'n'
    elif mem_gb >= 16:
        epochs, batch, imgsz, device, variant = 10, 8, 640, 'cpu', 'n'
    elif mem_gb >= 8:
        epochs, batch, imgsz, device, variant = 5, 4, 512, 'cpu', 'n'
    else:
        epochs, batch, imgsz, device, variant = 1, 2, 320, 'cpu', 'n'

    pytorch = recommend_pytorch_install(profile)
    return {
        'trainingMode': profile.get('recommended_training_mode', 'local'),
        'device': device,
        'epochs': epochs,
        'batchSize': batch,
        'imageSize': imgsz,
        'modelVariant': variant,
        'yoloVersion': 'v8',
        'pytorch': pytorch,
        'hardware_summary_zh': _hardware_summary_zh(profile),
    }


def _hardware_summary_zh(profile: Dict[str, Any]) -> str:
    server = profile.get('server') or {}
    gpus = server.get('gpus') or []
    gpu_name = gpus[0]['name'] if gpus else ('CUDA' if profile.get('gpu_available') else '无独立 GPU')
    return (
        f"CPU {server.get('cpu_count', '?')} 核 · "
        f"内存 {server.get('memory_available_gb', '?')}GB 可用 · "
        f"GPU: {gpu_name} · "
        f"推荐训练模式: {profile.get('recommended_training_mode', 'local')}"
    )


def build_nl_hardware_context_text(profile: Optional[Dict[str, Any]] = None) -> str:
    """Text block injected into NL generation prompts."""
    profile = profile or merge_hardware_profile()
    rec = recommend_yolo_training_config(profile)
    pytorch = rec.get('pytorch') or {}
    lines = [
        '【运行环境硬件画像 — 生成 YOLO 工作流时必须参考】',
        rec.get('hardware_summary_zh', ''),
        f"- 建议 device={rec.get('device')} epochs={rec.get('epochs')} batch={rec.get('batchSize')} imgsz={rec.get('imageSize')}",
        f"- 建议 trainingMode={rec.get('trainingMode')} modelVariant={rec.get('modelVariant')}",
        f"- PyTorch 安装: {pytorch.get('install_command', '')}",
        '- 若用户已有 completed 的 YOLO 权重，优先配置 reuseTrainingJobId 避免重复训练',
    ]
    return '\n'.join(line for line in lines if line)


def get_system_capabilities(client: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    profile = merge_hardware_profile(client)
    return {
        'profile': profile,
        'pytorch': recommend_pytorch_install(profile),
        'yolo_training': recommend_yolo_training_config(profile),
        'context_text': build_nl_hardware_context_text(profile),
    }
