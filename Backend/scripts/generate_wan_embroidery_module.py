"""Generate a Flowly image-to-video module using free local Wan 2.2 weights."""
import argparse
import gc
import hashlib
import importlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.cache/ai-video-client'))
MODELS = ROOT / '.cache/wan-models'
MODEL_ID = 'Wan-AI/Wan2.2-TI2V-5B'
# These layers' weight dtypes are used by upstream code to cast activations.
UNQUANTIZED_SUFFIXES = ('.wo.weight', 'condition_embedder.time_embedder.linear_1.weight')
MAX_HEADER_BYTES = 100 * 1024 * 1024


class TensorFile:
    """Read one safetensors tensor at a time without mapping the full checkpoint."""
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.source = self.path.open('rb')
        try:
            size = struct.unpack('<Q', self.source.read(8))[0]
            if not 0 < size <= MAX_HEADER_BYTES:
                raise ValueError('Invalid tensor-file header size')
            self.header = json.loads(self.source.read(size))
            self.start = 8 + size
            self.size = self.path.stat().st_size - self.start
            return self
        except Exception:
            self.source.close()
            raise

    def __exit__(self, *args):
        self.source.close()

    def keys(self):
        return set(self.header) - {'__metadata__'}

    def get(self, key):
        import torch
        types = {'F16': torch.float16, 'BF16': torch.bfloat16, 'F32': torch.float32,
                 'F64': torch.float64, 'F8_E4M3': torch.float8_e4m3fn,
                 'F8_E5M2': torch.float8_e5m2, 'I64': torch.int64, 'I32': torch.int32,
                 'I16': torch.int16, 'I8': torch.int8, 'U8': torch.uint8, 'BOOL': torch.bool}
        item = self.header[key]
        dtype = types[item['dtype']]
        begin, end = item['data_offsets']
        shape = item['shape']
        if (any(not isinstance(n, int) or n < 0 for n in shape) or
                not 0 <= begin <= end <= self.size or
                end-begin != math.prod(shape)*torch.empty((), dtype=dtype).element_size()):
            raise ValueError('Invalid tensor shape or offsets: ' + key)
        if begin == end:
            return torch.empty(shape, dtype=dtype)
        data = bytearray(end - begin)
        self.source.seek(self.start + begin)
        if self.source.readinto(data) != len(data):
            raise ValueError('Truncated tensor data: ' + key)
        return torch.frombuffer(data, dtype=dtype).reshape(shape)


def event(**data):
    print(json.dumps(data, ensure_ascii=True), flush=True)


def load_weights(model, path, converter=None, offload_embedding=False, quantized=True, weight_dtype=None):
    import bitsandbytes as bnb
    import torch
    from accelerate.utils import set_module_tensor_to_device
    with TensorFile(path) as source:
        state = {key: key for key in source.keys()}
        if converter:
            state = converter(state)
        persistent = set(model.state_dict())
        expected = {key: value for key, value in
                    {**dict(model.named_parameters()), **dict(model.named_buffers())}.items() if key in persistent}
        missing = set(expected) - set(state)
        if missing:
            raise ValueError('Missing Wan parameters: ' + ', '.join(sorted(missing)[:10]))
        for index, key in enumerate(expected):
            parent_name, parameter = key.rsplit('.', 1) if '.' in key else ('', key)
            parent = model.get_submodule(parent_name) if parent_name else model
            original_key = state.pop(key)
            value = source.get(original_key).to(weight_dtype or (torch.bfloat16 if quantized else torch.float32))
            scale_key = original_key.rsplit('.', 1)[0] + '.scale_weight'
            if parameter == 'weight' and scale_key in source.keys():
                value = value * source.get(scale_key).to(value.dtype)
            if quantized and isinstance(parent, torch.nn.Linear) and parameter == 'weight' and not key.endswith(UNQUANTIZED_SUFFIXES):
                replacement = bnb.nn.Linear4bit(parent.in_features, parent.out_features,
                    bias=parent.bias is not None, compute_dtype=torch.bfloat16,
                    compress_statistics=True, quant_type='nf4')
                replacement.weight = bnb.nn.Params4bit(value, requires_grad=False,
                    compress_statistics=True, quant_type='nf4').to('cuda')
                if parent.bias is not None:
                    replacement.bias = torch.nn.Parameter(parent.bias, requires_grad=False)
                model.set_submodule(parent_name, replacement)
            else:
                cpu = not quantized or (offload_embedding and isinstance(parent, torch.nn.Embedding))
                set_module_tensor_to_device(model, key, 'cpu' if cpu else 'cuda', value=value, dtype=value.dtype)
            del value
            if index % 50 == 0:
                event(status='loading', model=type(model).__name__, layer=index, total=len(expected))
    for key, value in model.named_buffers():
        if key not in persistent:
            if value.is_meta:
                raise ValueError('Uninitialized computed buffer: ' + key)
            set_module_tensor_to_device(model, key, 'cuda' if quantized else 'cpu', value=value)
    if any(parameter.device.type == 'meta' for parameter in model.parameters()):
        raise ValueError('Uninitialized Wan parameter')
    return model.eval()


def encode_prompts(shot, spec, directory):
    import torch
    from accelerate import init_empty_weights
    from safetensors.torch import load_file, save_file
    from transformers import UMT5Config, UMT5EncoderModel, T5TokenizerFast

    prompts = {'positive': shot['prompt'], 'negative': spec['negative_prompt']}
    cache_spec = {'prompts': prompts, 'model': MODEL_ID, 'max_sequence_length': spec['max_sequence_length']}
    fingerprint = hashlib.sha256(json.dumps(cache_spec, sort_keys=True).encode()).hexdigest()
    path = directory / 'embeddings' / (fingerprint + '.safetensors')
    if path.exists():
        return load_file(str(path))
    config = UMT5Config.from_json_file(MODELS / 'config/text_encoder/config.json')
    with init_empty_weights():
        encoder = UMT5EncoderModel(config)
        encoder.set_input_embeddings(encoder.shared)
    event(status='loading_text_encoder')
    encoder = load_weights(encoder, MODELS / 'umt5_xxl_fp8_e4m3fn_scaled.safetensors', offload_embedding=True)
    # Keep the 2 GB token table in system memory; only selected token vectors go to CUDA.
    embedding = encoder.shared
    embedding.forward = lambda ids: torch.nn.functional.embedding(ids.cpu(), embedding.weight).to(ids.device)
    encoder.set_input_embeddings(embedding)
    for block in encoder.encoder.block:
        attention = block.layer[0].SelfAttention
        if hasattr(attention, 'relative_attention_bias'):
            attention.relative_attention_bias.to('cuda')
    tokenizer = T5TokenizerFast.from_pretrained(str(MODELS / 'config/tokenizer'), local_files_only=True)
    result = {}
    for name, prompt in prompts.items():
        tokens = tokenizer(prompt, padding='max_length', max_length=spec['max_sequence_length'],
                           truncation=True, add_special_tokens=True, return_tensors='pt').to('cuda')
        event(status='encoding_prompt', branch=name)
        with torch.inference_mode():
            encoded = encoder(tokens.input_ids, attention_mask=tokens.attention_mask).last_hidden_state
            length = int(tokens.attention_mask.sum())
            encoded[:, length:] = 0
        if not torch.isfinite(encoded).all():
            raise ValueError('Non-finite Wan text embeddings')
        result[name] = encoded.cpu().contiguous()
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(result, str(path))
    del encoder, embedding, encoded, tokens
    gc.collect()
    torch.cuda.empty_cache()
    return result


def generate(request, directory):
    # Windows native imports crash when Arrow is first loaded after Torch in this
    # environment. Load Arrow first, as confirmed by isolated subprocess probes.
    importlib.import_module('pyarrow')
    import torch
    from accelerate import init_empty_weights
    from diffusers import AutoencoderKLWan, UniPCMultistepScheduler, WanImageToVideoPipeline, WanTransformer3DModel
    from diffusers.loaders.single_file_utils import convert_wan_transformer_to_diffusers
    from diffusers.utils import export_to_video
    from PIL import Image

    shot, spec = request['shot'], request['spec']
    if spec.get('condition_mode', 'first_frame') != 'keyframes' and (shot.get('end_image') or shot.get('conditions')):
        raise ValueError('This Wan image-to-video mode accepts a first frame only')
    count = round(spec['seconds'] * spec['fps'])
    if (count - 1) % 4 or spec['width'] % 32 or spec['height'] % 32:
        raise ValueError('Wan requires 4n+1 frames and dimensions divisible by 32')
    torch.set_num_threads(spec['cpu_threads'])
    torch.cuda.set_per_process_memory_fraction(spec['gpu_memory_fraction'])
    torch.backends.cudnn.benchmark = False
    embeddings = encode_prompts(shot, spec, directory)
    with init_empty_weights():
        transformer = WanTransformer3DModel.from_config(json.loads((MODELS / 'config/transformer/config.json').read_text()))
    event(status='loading_video_transformer')
    transformer = load_weights(transformer, MODELS / 'wan2.2_ti2v_5B_fp16.safetensors', convert_wan_transformer_to_diffusers)
    with init_empty_weights():
        vae = AutoencoderKLWan.from_config(json.loads((MODELS / 'config/vae/config.json').read_text()))
    event(status='loading_vae')
    vae = load_weights(vae, MODELS / 'wan2.2_vae_diffusers.safetensors', quantized=False,
                       weight_dtype=getattr(torch, spec['vae_dtype']))
    scheduler = UniPCMultistepScheduler.from_config(json.loads((MODELS / 'config/scheduler/scheduler_config.json').read_text()), flow_shift=spec['flow_shift'])
    pipe = WanImageToVideoPipeline(tokenizer=None, text_encoder=None, vae=vae,
        scheduler=scheduler, transformer=transformer, expand_timesteps=True)
    pipe.vae.enable_tiling(**spec['vae_tiling'])
    configure_vae_offload(pipe)
    if spec.get('condition_mode') == 'keyframes':
        configure_keyframes(pipe, shot, spec, directory)
    start = time.monotonic()
    def progress(pipeline, step, timestep, kwargs):
        event(status='denoising', step=step + 1, steps=spec['num_inference_steps'], elapsed=round(time.monotonic()-start, 1))
        return kwargs
    event(status='generating', frames=count, width=spec['width'], height=spec['height'])
    with torch.inference_mode():
        latents = pipe(image=Image.open(directory / 'keyframes' / shot['image']).convert('RGB'),
            prompt_embeds=embeddings['positive'].to('cuda'), negative_prompt_embeds=embeddings['negative'].to('cuda'),
            width=spec['width'], height=spec['height'], num_frames=count,
            num_inference_steps=spec['num_inference_steps'], guidance_scale=spec['guidance_scale'],
            generator=torch.Generator('cuda').manual_seed(shot['seed']),
            callback_on_step_end=progress, max_sequence_length=spec['max_sequence_length'], output_type='latent').frames
    from safetensors.torch import save_file
    save_file({'latents': latents.cpu().contiguous()}, str(directory / 'generated-latents.safetensors'),
              metadata={'request_fingerprint': request['fingerprint']})
    # Free NF4 storage without attempting its unsupported Windows CPU transfer.
    pipe.transformer = None
    del transformer, embeddings
    gc.collect()
    torch.cuda.empty_cache()
    event(status='decoding', elapsed=round(time.monotonic()-start, 1))
    pipe.vae.enable_tiling(**spec.get('decode_tiling', spec['vae_tiling']))
    with torch.inference_mode():
        frames = decode_latents(pipe, latents)[0]
    target = directory / 'clips' / (shot['id'] + '.mp4')
    target.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(target), fps=spec['fps'])
    media = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=width,height,nb_frames,r_frame_rate', '-of', 'json', str(target)], text=True, timeout=30))
    if int(media['streams'][0]['nb_frames']) != count:
        raise ValueError('Incomplete Wan generation')
    record = {'provider': 'wan_local', 'model': MODEL_ID, 'quantization': 'NF4; UMT5 scaled FP8 decoded before quantization; CPU token table',
        'prompt': shot['prompt'], 'seed': shot['seed'], 'last_frame': shot.get('end_image'),
        'conditions': shot.get('conditions', []), 'condition_mode': spec.get('condition_mode', 'first_frame'),
        'request_fingerprint': request['fingerprint'], 'keyframe_hashes': request['keyframe_hashes'],
        'input_image': shot['image'], 'negative_prompt': spec['negative_prompt'], 'guidance_scale': spec['guidance_scale'],
        'vae_dtype': spec['vae_dtype'],
        'duration': float(media['format']['duration']), 'media': media, 'generated_at': time.time(),
        'file': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    target.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    event(status='completed', file=str(target), duration=record['duration'])


def configure_keyframes(pipe, shot, spec, directory):
    """Experimental masked-latent constraints; this is not native Wan FLF support."""
    import torch
    from PIL import Image
    count = round(spec['seconds'] * spec['fps'])
    conditions = list(shot.get('conditions', []))
    if shot.get('end_image'):
        conditions.append({'image': shot['end_image'], 'frame_index': count - 1})
    indices = [item['frame_index'] for item in conditions]
    if (len(set(indices)) != len(indices) or any(isinstance(i, bool) or not isinstance(i, int)
            or not 0 < i < count or i % pipe.vae_scale_factor_temporal for i in indices)):
        raise ValueError('Keyframe indices must be distinct nonzero temporal-latent boundaries')
    original = pipe.prepare_latents
    def prepare(*args, **kwargs):
        latents, first, mask = original(*args, **kwargs)
        condition = first.expand_as(latents).clone()
        mean = torch.tensor(pipe.vae.config.latents_mean, device=latents.device, dtype=latents.dtype).view(1, -1, 1, 1, 1)
        std = torch.tensor(pipe.vae.config.latents_std, device=latents.device, dtype=latents.dtype).view(1, -1, 1, 1, 1)
        for item in conditions:
            with Image.open(directory / 'keyframes' / item['image']) as source:
                pixels = pipe.video_processor.preprocess(source.convert('RGB'), height=spec['height'], width=spec['width'])
            pixels = pixels.unsqueeze(2).to(device=latents.device, dtype=pipe.vae.dtype)
            encoded = pipe.vae.encode(pixels).latent_dist.mode().to(latents.dtype)
            index = item['frame_index'] // pipe.vae_scale_factor_temporal
            condition[:, :, index:index+1] = (encoded - mean) / std
            mask[:, :, index:index+1] = 0
            event(status='keyframe_encoded', frame=item['frame_index'], image=item['image'])
        return latents, condition, mask
    pipe.prepare_latents = prepare


def decode_latents(pipe, latents):
    import torch
    latents = latents.to(pipe.vae.dtype)
    mean = torch.tensor(pipe.vae.config.latents_mean, device=latents.device, dtype=latents.dtype).view(1, -1, 1, 1, 1)
    std = torch.tensor(pipe.vae.config.latents_std, device=latents.device, dtype=latents.dtype).view(1, -1, 1, 1, 1)
    video = pipe.vae.decode(latents * std + mean, return_dict=False)[0]
    return pipe.video_processor.postprocess_video(video, output_type='pil')


def configure_vae_offload(pipe):
    """Keep NF4 weights on CUDA; move only ordinary VAE weights between stages."""
    import torch
    from accelerate import cpu_offload_with_hook
    _, hook = cpu_offload_with_hook(pipe.vae, execution_device='cuda')
    encode = pipe.vae.encode
    def encode_and_release(*args, **kwargs):
        result = encode(*args, **kwargs)
        hook.offload()
        torch.cuda.empty_cache()
        return result
    pipe.vae.encode = encode_and_release


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    generate(json.loads(args.request.read_text(encoding='utf-8')), args.request.resolve().parent)
