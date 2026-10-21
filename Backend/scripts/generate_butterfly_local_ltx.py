"""Generate neural video with public LTX weights on the local CUDA device."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = ROOT / '.cache/ltx-models'
OUTPUT = ROOT / 'output/butterfly-video/ai_60'
SPEC_PATH = ROOT / 'Backend/workflows/services/butterfly_ltx_spec.json'
sys.path.insert(0, str(ROOT / '.cache/ai-video-client'))
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

END_IMAGES = {
    '01-skeleton': 'ai-skeleton-native-01.png',
    '02-feather-growth': 'ai-feather-lines-native-01.png',
    '03-stitch-fill': 'ai-motif-native-01.png',
    '04-fusion': 'ai-motif-native-01.png',
    '06-garment-map': 'ai-garment-native-01.png',
    '07-cuffs': 'ai-garment-final-native-01.png',
    '08-final': 'ai-garment-final-native-01.png',
}


def event(**data):
    print(json.dumps(data, ensure_ascii=True, default=str), flush=True)
    (OUTPUT / 'local-ltx-progress.json').write_text(json.dumps({**data, 'updated_at': time.time()}, ensure_ascii=False, indent=2), encoding='utf-8')


def load_quantized(model, filename, mapping=None, quantize=True):
    """Stream each safetensor into its actual layer, avoiding a full CPU copy."""
    import bitsandbytes as bnb
    import torch
    from accelerate.utils import set_module_tensor_to_device
    from safetensors import safe_open

    with safe_open(filename, framework='pt', device='cpu') as source:
        raw = {key: source.get_tensor(key) for key in source.keys()}
        state = mapping(raw) if mapping else raw
        expected = {**dict(model.named_parameters()), **dict(model.named_buffers())}
        missing = sorted(set(expected) - set(state))
        if missing:
            raise ValueError('Missing model weights: ' + ', '.join(missing[:12]))
        for index, (key, old) in enumerate(expected.items()):
            value = state.pop(key).to(dtype=torch.bfloat16)
            parent_name, parameter = key.rsplit('.', 1) if '.' in key else ('', key)
            parent = model.get_submodule(parent_name) if parent_name else model
            if quantize and isinstance(parent, torch.nn.Linear) and parameter == 'weight' and not key.endswith('.wo.weight'):
                new = bnb.nn.Linear4bit(parent.in_features, parent.out_features, bias=parent.bias is not None,
                                       compute_dtype=torch.bfloat16, compress_statistics=True, quant_type='nf4')
                new.weight = bnb.nn.Params4bit(value, requires_grad=False, compress_statistics=True, quant_type='nf4').to('cuda')
                if parent.bias is not None:
                    new.bias = torch.nn.Parameter(parent.bias, requires_grad=False)
                model.set_submodule(parent_name, new)
            else:
                set_module_tensor_to_device(model, key, 'cuda' if quantize else 'cpu', value=value, dtype=torch.bfloat16)
            del value
            if index % 50 == 0:
                event(status='loading_quantized_weights', layer=index, total=len(expected), model=type(model).__name__)
    model.eval()
    if any(value.device.type == 'meta' for value in model.parameters()):
        raise ValueError('Uninitialized model parameter')
    return model


def embedding_path(shot):
    digest = hashlib.sha256(shot['prompt'].encode()).hexdigest()[:16]
    return OUTPUT / 'embeddings' / f'{shot["id"]}-{digest}-nf4wo16.safetensors'


def encode_prompts(shots):
    import torch
    from accelerate import init_empty_weights
    from safetensors.torch import save_file
    from transformers import T5Config, T5EncoderModel, T5TokenizerFast

    pending = [shot for shot in shots if not embedding_path(shot).is_file()]
    if not pending:
        return
    event(status='loading_text_encoder', pending=len(pending))
    config = T5Config.from_json_file(MODEL_ROOT / 'config/text_encoder/config.json')
    with init_empty_weights():
        encoder = T5EncoderModel(config)
    # T5 casts activations to wo.weight.dtype; packed uint8 NF4 weights corrupt that cast.
    encoder = load_quantized(encoder, str(MODEL_ROOT / 't5xxl_fp8_e4m3fn.safetensors'))
    tokenizer = T5TokenizerFast.from_pretrained(str(MODEL_ROOT / 'config/tokenizer'), local_files_only=True)
    for shot in pending:
        event(status='encoding_prompt', shot=shot['id'])
        tokens = tokenizer(shot['prompt'], padding='max_length', max_length=256, truncation=True, add_special_tokens=True, return_tensors='pt').to('cuda')
        with torch.inference_mode():
            embeddings = encoder(tokens.input_ids, attention_mask=tokens.attention_mask.bool())[0]
        path = embedding_path(shot)
        path.parent.mkdir(parents=True, exist_ok=True)
        save_file({'prompt_embeds': embeddings.cpu().contiguous(), 'prompt_attention_mask': tokens.attention_mask.bool().cpu().contiguous()}, str(path))
    del encoder, tokens, embeddings
    gc.collect()
    torch.cuda.empty_cache()


def load_pipeline():
    import torch
    from accelerate import init_empty_weights
    from accelerate.utils import set_module_tensor_to_device
    from diffusers import AutoencoderKLLTXVideo, FlowMatchEulerDiscreteScheduler, LTXConditionPipeline, LTXVideoTransformer3DModel
    from diffusers.loaders.single_file_utils import convert_ltx_transformer_checkpoint_to_diffusers, convert_ltx_vae_checkpoint_to_diffusers
    from safetensors import safe_open

    checkpoint = str(MODEL_ROOT / 'ltxv-2b-0.9.8-distilled-fp8.safetensors')
    event(status='loading_video_transformer')
    with init_empty_weights():
        transformer = LTXVideoTransformer3DModel.from_config(str(MODEL_ROOT / 'config/transformer/config.json'))
    transformer = load_quantized(transformer, checkpoint, convert_ltx_transformer_checkpoint_to_diffusers)
    event(status='loading_video_autoencoder')
    with init_empty_weights():
        vae = AutoencoderKLLTXVideo.from_config(str(MODEL_ROOT / 'config/vae/config.json'))
    with safe_open(checkpoint, framework='pt', device='cpu') as source:
        state = convert_ltx_vae_checkpoint_to_diffusers({key: source.get_tensor(key) for key in source.keys() if key.startswith('vae.')})
        expected = {**dict(vae.named_parameters()), **dict(vae.named_buffers())}
        if set(expected) - set(state):
            raise ValueError('Missing VAE parameters: ' + str(sorted(set(expected) - set(state))[:12]))
        for key in expected:
            set_module_tensor_to_device(vae, key, 'cpu', value=state.pop(key).to(torch.bfloat16), dtype=torch.bfloat16)
    vae.eval()
    scheduler = FlowMatchEulerDiscreteScheduler.from_config(str(MODEL_ROOT / 'config/scheduler/scheduler_config.json'))
    pipe = LTXConditionPipeline(scheduler=scheduler, vae=vae, text_encoder=None, tokenizer=None, transformer=transformer)
    pipe.vae.enable_tiling(tile_sample_min_height=256, tile_sample_min_width=256, tile_sample_min_num_frames=16,
                          tile_sample_stride_height=192, tile_sample_stride_width=192, tile_sample_stride_num_frames=8)
    pipe.vae.use_framewise_decoding = True
    pipe.vae.use_framewise_encoding = True
    # Denoising runs on CUDA. The VAE transfers separately for the encoding/decoding stages.
    pipe.enable_model_cpu_offload(device='cuda')
    return pipe


def generate(pipe, shot, spec, width, height):
    import subprocess
    import torch
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition
    from diffusers.utils import export_to_video
    from PIL import Image
    from safetensors.torch import load_file

    target = OUTPUT / 'clips' / (shot['id'] + '.mp4')
    proof = target.with_suffix('.json')
    if target.exists() and proof.exists():
        recorded = json.loads(proof.read_text(encoding='utf-8'))
        if (recorded.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest()
                and recorded.get('prompt') == shot['prompt']
                and recorded.get('seed') == shot.get('seed', spec['seed'])
                and recorded.get('last_frame') == END_IMAGES.get(shot['id'])
                and recorded.get('conditions', []) == shot.get('conditions', [])):
            event(status='reused', shot=shot['id'])
            return
        raise ValueError('Existing clip differs from its provenance')
    frame_count = round(spec['seconds'] * spec['fps'])
    if (frame_count - 1) % 8:
        raise ValueError('LTX frame count must be 8n+1')
    source = OUTPUT / 'keyframes' / shot['image']
    conditions = [LTXVideoCondition(image=Image.open(source).convert('RGB'), frame_index=0)]
    for condition in shot.get('conditions', []):
        index = condition['frame_index']
        if index <= 0 or index >= frame_count - 1 or index % 8:
            raise ValueError('Intermediate image condition must use an interior 8n frame')
        conditions.append(LTXVideoCondition(
            image=Image.open(OUTPUT / 'keyframes' / condition['image']).convert('RGB'), frame_index=index))
    end = END_IMAGES.get(shot['id'])
    if end:
        conditions.append(LTXVideoCondition(image=Image.open(OUTPUT / 'keyframes' / end).convert('RGB'), frame_index=frame_count - 1))
    embeds = load_file(str(embedding_path(shot)))
    timesteps = [1000, 993.7, 987.5, 981.2, 975.0, 909.4, 725.0, 421.9]
    event(status='generating', shot=shot['id'], width=width, height=height, frames=frame_count)
    started = time.monotonic()

    def progress(pipeline, step, timestep, callback_kwargs):
        event(status='denoising', shot=shot['id'], step=step + 1, steps=len(timesteps), seconds=round(time.monotonic() - started, 1))
        return callback_kwargs

    with torch.inference_mode():
        frames = pipe(conditions=conditions, prompt_embeds=embeds['prompt_embeds'].to('cuda'),
                      prompt_attention_mask=embeds['prompt_attention_mask'].to('cuda'), width=width, height=height,
                      num_frames=frame_count, frame_rate=spec['fps'], timesteps=timesteps, guidance_scale=1.0,
                      image_cond_noise_scale=0.025, decode_timestep=0.05, decode_noise_scale=0.025,
                      generator=torch.Generator('cuda').manual_seed(shot.get('seed', spec['seed'])), callback_on_step_end=progress,
                      output_type='pil').frames[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(target), fps=spec['fps'])
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height,nb_frames,r_frame_rate', '-of', 'json', str(target)], text=True, timeout=30))
    duration = float(metadata['format']['duration'])
    if abs(duration - spec['seconds']) > 0.05:
        raise ValueError('Model output has an incorrect duration')
    record = {'provider': 'ltx_local', 'model': 'Lightricks/ltxv-2b-0.9.8-distilled-fp8', 'quantization': 'NF4; T5 wo projection retained in BF16',
              'input_image': str(source), 'last_frame': end, 'conditions': shot.get('conditions', []),
              'prompt': shot['prompt'], 'seed': shot.get('seed', spec['seed']),
              'timesteps': timesteps, 'file': str(target), 'duration': duration, 'media': metadata,
              'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'generated_at': time.time()}
    proof.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    event(status='completed', shot=shot['id'], file=str(target), duration=duration)
    del frames
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--shots', type=int, nargs='+', required=True)
    parser.add_argument('--encode-only', action='store_true')
    parser.add_argument('--width', type=int, default=1024)
    parser.add_argument('--height', type=int, default=576)
    args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if any(i < 1 or i > len(spec['shots']) for i in args.shots) or args.width % 32 or args.height % 32:
        parser.error('Invalid shot selection or non-multiple-of-32 frame size')
    shots = [spec['shots'][i - 1] for i in args.shots]
    encode_prompts(shots)
    if not args.encode_only:
        pipeline = load_pipeline()
        for shot in shots:
            generate(pipeline, shot, spec, args.width, args.height)
