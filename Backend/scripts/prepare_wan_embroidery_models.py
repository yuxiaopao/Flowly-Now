"""Download public Wan weights and their official Diffusers configuration."""
from pathlib import Path
import requests

if __package__:
    from . import prepare_butterfly_local_models as downloader
else:
    import prepare_butterfly_local_models as downloader

ROOT = Path(__file__).resolve().parents[2] / '.cache/wan-models'
CONFIG_REPO = 'https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers/resolve/main/'
WEIGHTS_REPO = 'https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/'
CONFIG_FILES = ['transformer/config.json', 'text_encoder/config.json', 'vae/config.json',
                'scheduler/scheduler_config.json', 'tokenizer/tokenizer_config.json',
                'tokenizer/special_tokens_map.json', 'tokenizer/spiece.model', 'tokenizer/tokenizer.json']
WEIGHTS = [('wan2.2_ti2v_5B_fp16.safetensors', WEIGHTS_REPO + 'diffusion_models/wan2.2_ti2v_5B_fp16.safetensors'),
           ('umt5_xxl_fp8_e4m3fn_scaled.safetensors', WEIGHTS_REPO + 'text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors'),
           ('wan2.2_vae_diffusers.safetensors', CONFIG_REPO + 'vae/diffusion_pytorch_model.safetensors')]


if __name__ == '__main__':
    for name in CONFIG_FILES:
        target = ROOT / 'config' / name
        if target.is_file():
            continue
        response = requests.get(CONFIG_REPO + name, timeout=60)
        response.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
    downloader.FOLDER = ROOT
    for name, url in WEIGHTS:
        downloader.download(name, url)
