"""Fetch public VACE control weights; reuse the existing local UMT5 encoder."""
from pathlib import Path
import requests

if __package__:
    from . import prepare_butterfly_local_models as downloader
else:
    import prepare_butterfly_local_models as downloader

ROOT = Path(__file__).resolve().parents[2] / '.cache/wan-vace-models'
REPOSITORY = 'https://huggingface.co/Wan-AI/Wan2.1-VACE-1.3B-diffusers/resolve/main/'
CONFIG_FILES = ('transformer/config.json', 'vae/config.json', 'scheduler/scheduler_config.json')
WEIGHTS = (
    ('wan2.1_vace_1.3B_fp16.safetensors',
     'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_vace_1.3B_fp16.safetensors'),
    ('wan2.1_vae_diffusers.safetensors', REPOSITORY + 'vae/diffusion_pytorch_model.safetensors'),
)

if __name__ == '__main__':
    for name in CONFIG_FILES:
        target = ROOT / 'config' / name
        if not target.is_file():
            response = requests.get(REPOSITORY + name, timeout=60)
            response.raise_for_status()
            response.json()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)
    downloader.FOLDER = ROOT
    for name, url in WEIGHTS:
        downloader.download(name, url)
