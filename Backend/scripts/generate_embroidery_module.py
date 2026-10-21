"""Run one Flowly embroidery module using the installed free LTX weights."""
import argparse
import json
from pathlib import Path

if __package__:
    from . import generate_butterfly_local_ltx as ltx
else:
    import generate_butterfly_local_ltx as ltx


def sequential_guidance(forward):
    """Evaluate CFG branches separately so both fit the laptop GPU."""
    def wrapped(*args, **kwargs):
        import torch
        hidden = kwargs.get('hidden_states')
        if hidden is None or hidden.shape[0] != 2 or kwargs.get('return_dict', True):
            return forward(*args, **kwargs)
        outputs = []
        for index in range(2):
            branch = {key: value[index:index+1] if isinstance(value, torch.Tensor) and value.ndim and value.shape[0] == 2 else value
                      for key, value in kwargs.items()}
            torch.cuda.empty_cache()
            outputs.append(forward(*args, **branch)[0])
        return (torch.cat(outputs, dim=0),)
    return wrapped


class GuidedPipeline:
    def __init__(self, pipeline, spec, embeddings):
        self.pipeline, self.spec, self.embeddings = pipeline, spec, embeddings

    def __call__(self, **kwargs):
        kwargs.update(guidance_scale=self.spec['guidance_scale'],
                      guidance_rescale=self.spec['guidance_rescale'],
                      negative_prompt_embeds=self.embeddings['prompt_embeds'].to('cuda'),
                      negative_prompt_attention_mask=self.embeddings['prompt_attention_mask'].to('cuda'))
        return self.pipeline(**kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8'))
    ltx.OUTPUT = args.request.resolve().parent
    shot, spec = request['shot'], request['spec']
    ltx.END_IMAGES = {shot['id']: shot.get('end_image')}
    import torch
    torch.set_num_threads(spec['cpu_threads'])
    torch.cuda.set_per_process_memory_fraction(spec['gpu_memory_fraction'])
    torch.backends.cudnn.benchmark = False
    negative = {'id': 'negative', 'prompt': spec.get('negative_prompt', '')}
    guided = spec.get('guidance_scale', 1) > 1
    ltx.encode_prompts([shot, negative] if guided else [shot])
    pipeline = ltx.load_pipeline()
    pipeline.vae.enable_tiling(**spec['vae_tiling'])
    pipeline.transformer.register_forward_pre_hook(lambda module, inputs: torch.cuda.empty_cache())
    runner = pipeline
    if guided:
        from safetensors.torch import load_file
        pipeline.transformer.forward = sequential_guidance(pipeline.transformer.forward)
        runner = GuidedPipeline(pipeline, spec, load_file(str(ltx.embedding_path(negative))))
    ltx.generate(runner, shot, spec, spec['width'], spec['height'])
    proof = ltx.OUTPUT / 'clips' / (shot['id'] + '.json')
    record = json.loads(proof.read_text(encoding='utf-8'))
    record['request_fingerprint'] = request['fingerprint']
    record['keyframe_hashes'] = request['keyframe_hashes']
    record['guidance_scale'] = spec.get('guidance_scale', 1)
    record['negative_prompt'] = spec.get('negative_prompt', '')
    proof.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
