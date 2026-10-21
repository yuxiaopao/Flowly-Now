"""Free local video-guided embroidery trial with the official Wan VACE model."""
import argparse
import ctypes
import gc
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

if __package__:
    from .generate_wan_embroidery_module import ROOT, load_weights, encode_prompts, configure_vae_offload, decode_latents, event
else:
    from generate_wan_embroidery_module import ROOT, load_weights, encode_prompts, configure_vae_offload, decode_latents, event

MODELS = ROOT / '.cache/wan-vace-models'
MODEL_ID = 'Wan-AI/Wan2.1-VACE-1.3B-diffusers'
GIB = 1024 ** 3


def memory_snapshot():
    if os.name == 'nt':
        class MemoryStatus(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                ('total_ram', ctypes.c_ulonglong), ('available_ram', ctypes.c_ulonglong),
                ('total_commit', ctypes.c_ulonglong), ('available_commit', ctypes.c_ulonglong),
                ('total_virtual', ctypes.c_ulonglong), ('available_virtual', ctypes.c_ulonglong),
                ('extended_virtual', ctypes.c_ulonglong)]
        state = MemoryStatus()
        state.length = ctypes.sizeof(state)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            raise ctypes.WinError()
        return {'available_ram': state.available_ram, 'available_commit': state.available_commit}
    import psutil
    available = psutil.virtual_memory().available
    return {'available_ram': available, 'available_commit': available + psutil.swap_memory().free}


def check_memory_budget(spec):
    if spec.get('transformer_precision', 'nf4') != 'bf16_offload':
        return
    limits = spec.get('memory_budget')
    if not isinstance(limits, dict) or set(limits) != {'available_ram_gib', 'available_commit_gib'}:
        raise ValueError('Unquantized VACE requires an explicit memory budget')
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or
           not math.isfinite(value) or value <= 0 for value in limits.values()):
        raise ValueError('Memory budget values must be positive finite GiB values')
    state = memory_snapshot()
    for resource in ('available_ram', 'available_commit'):
        if state[resource] < limits[resource + '_gib'] * GIB:
            raise MemoryError(f'Unquantized VACE stopped before model loading: {resource} '
                              f'{state[resource]/GIB:.2f} GiB, configured minimum '
                              f'{limits[resource + "_gib"]:g} GiB')


def prepare_control(directory, shot, spec):
    """Sample the authorized reference at native timing, without repeats or holds."""
    import cv2
    from PIL import Image
    count = round(spec['seconds'] * spec['fps'])
    source = directory / 'control.mp4'
    capture = cv2.VideoCapture(str(source))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        start = shot['control_start_seconds']
        if not capture.isOpened() or fps <= 0 or start < 0:
            raise ValueError('Invalid control video or start time')
        indices = [round((start + index/spec['fps']) * fps) for index in range(count)]
        if indices[-1] >= total:
            raise ValueError('Control clip is too short; frame padding is forbidden')
        crop = shot['control_crop']
        if len(crop) != 4 or any(isinstance(n, bool) or not isinstance(n, int) for n in crop):
            raise ValueError('Control crop must contain four integers')
        left, top, width, height = crop
        frames = []
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            success, frame = capture.read()
            if not success:
                raise ValueError('Could not decode control frame')
            if not (left >= 0 and top >= 0 and width > 0 and height > 0 and
                    left+width <= frame.shape[1] and top+height <= frame.shape[0]):
                raise ValueError('Control crop exceeds reference video')
            frame = frame[top:top+height, left:left+width]
            frame = cv2.resize(frame, (spec['width'], spec['height']), interpolation=cv2.INTER_AREA)
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        # White regions are regenerated, with the original motion in VACE's reactive stream.
        masks = [Image.new('L', (spec['width'], spec['height']), 255) for _ in frames]
        return frames, masks
    finally:
        capture.release()


def generate(request, directory):
    check_memory_budget(request['spec'])
    importlib.import_module('pyarrow')
    import torch
    from accelerate import init_empty_weights
    from diffusers import AutoencoderKLWan, UniPCMultistepScheduler, WanVACEPipeline, WanVACETransformer3DModel
    from diffusers.loaders.single_file_utils import convert_wan_transformer_to_diffusers
    from diffusers.utils import export_to_video
    from PIL import Image
    shot, spec = request['shot'], request['spec']
    precision = spec.get('transformer_precision', 'nf4')
    if precision not in ('nf4', 'bf16_offload'):
        raise ValueError('Unsupported VACE transformer precision')
    count = round(spec['seconds'] * spec['fps'])
    if (count-1) % 4 or spec['width'] % 16 or spec['height'] % 16:
        raise ValueError('VACE requires 4n+1 frames and dimensions divisible by 16')
    if shot.get('end_image') or shot.get('conditions'):
        raise ValueError('Motion-reference mode uses the reference video and one appearance image')
    control = directory / 'control.mp4'
    if hashlib.sha256(control.read_bytes()).hexdigest() != request['control_video_hash']:
        raise ValueError('Control video checksum mismatch')
    frames, masks = prepare_control(directory, shot, spec)
    torch.set_num_threads(spec['cpu_threads'])
    torch.cuda.set_per_process_memory_fraction(spec['gpu_memory_fraction'])
    torch.backends.cudnn.benchmark = False
    embeddings = encode_prompts(shot, spec, directory)
    for name in ('wan2.1_vace_1.3B_fp16.safetensors', 'wan2.1_vae_diffusers.safetensors'):
        path = MODELS / name
        manifest = path.with_suffix('.download.json')
        if (not manifest.is_file() or json.loads(manifest.read_text()).get('status') != 'completed'):
            raise ValueError('Local model download is incomplete: ' + name)
    with init_empty_weights():
        transformer = WanVACETransformer3DModel.from_config(json.loads((MODELS / 'config/transformer/config.json').read_text()))
    transformer = load_weights(transformer, MODELS / 'wan2.1_vace_1.3B_fp16.safetensors',
        convert_wan_transformer_to_diffusers, quantized=precision == 'nf4', weight_dtype=torch.bfloat16)
    if precision == 'bf16_offload':
        transformer.enable_group_offload(onload_device=torch.device('cuda'), offload_device=torch.device('cpu'),
            offload_type='block_level', num_blocks_per_group=1, use_stream=False)
    with init_empty_weights():
        vae = AutoencoderKLWan.from_config(json.loads((MODELS / 'config/vae/config.json').read_text()))
    vae = load_weights(vae, MODELS / 'wan2.1_vae_diffusers.safetensors', quantized=False,
                       weight_dtype=getattr(torch, spec['vae_dtype']))
    scheduler = UniPCMultistepScheduler.from_config(json.loads((MODELS / 'config/scheduler/scheduler_config.json').read_text()), flow_shift=spec['flow_shift'])
    pipe = WanVACEPipeline(tokenizer=None, text_encoder=None, vae=vae, scheduler=scheduler, transformer=transformer)
    pipe.vae.enable_tiling(**spec['vae_tiling'])
    configure_vae_offload(pipe)
    start = time.monotonic()
    def progress(pipeline, step, timestep, kwargs):
        event(status='denoising', step=step+1, steps=spec['num_inference_steps'], elapsed=round(time.monotonic()-start, 1))
        return kwargs
    event(status='generating', model=MODEL_ID, frames=count)
    with Image.open(directory / 'keyframes' / shot['image']) as source:
        reference = source.convert('RGB')
    with torch.inference_mode():
        latents = pipe(video=frames, mask=masks, reference_images=[reference],
            conditioning_scale=spec['conditioning_scale'],
            prompt_embeds=embeddings['positive'].to('cuda'), negative_prompt_embeds=embeddings['negative'].to('cuda'),
            width=spec['width'], height=spec['height'], num_frames=count,
            num_inference_steps=spec['num_inference_steps'], guidance_scale=spec['guidance_scale'],
            generator=torch.Generator('cuda').manual_seed(shot['seed']), callback_on_step_end=progress,
            max_sequence_length=spec['max_sequence_length'], output_type='latent').frames
    from safetensors.torch import save_file
    save_file({'latents': latents.cpu().contiguous()}, str(directory / 'generated-latents.safetensors'),
              metadata={'request_fingerprint': request['fingerprint']})
    pipe.transformer = None
    del transformer, embeddings
    gc.collect()
    torch.cuda.empty_cache()
    event(status='decoding')
    pipe.vae.enable_tiling(**spec['decode_tiling'])
    with torch.inference_mode():
        # VACE's latent output includes one prefix frame per appearance reference.
        frames = decode_latents(pipe, latents[:, :, 1:])[0]
    target = directory / 'clips' / (shot['id'] + '.mp4')
    target.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(target), fps=spec['fps'])
    media = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=width,height,nb_frames,r_frame_rate', '-of', 'json', str(target)], text=True, timeout=30))
    if int(media['streams'][0]['nb_frames']) != count:
        raise ValueError('Incomplete VACE generation')
    record = {'provider': 'wan_vace_local', 'model': MODEL_ID, 'quantization': precision,
        'prompt': shot['prompt'], 'seed': shot['seed'], 'last_frame': None, 'conditions': [],
        'request_fingerprint': request['fingerprint'], 'keyframe_hashes': request['keyframe_hashes'],
        'control_video_hash': request['control_video_hash'], 'control_video': shot['control_video'],
        'control_crop': shot['control_crop'], 'control_start_seconds': shot['control_start_seconds'],
        'input_image': shot['image'], 'negative_prompt': spec['negative_prompt'],
        'duration': float(media['format']['duration']), 'media': media, 'generated_at': time.time(),
        'file': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    target.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    event(status='completed', file=str(target), duration=record['duration'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    generate(json.loads(args.request.read_text(encoding='utf-8')), args.request.resolve().parent)
