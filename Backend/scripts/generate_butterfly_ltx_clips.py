"""Generate actual free LTX video clips and preserve their provider responses."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / 'Backend/workflows/services/butterfly_ltx_spec.json'
OUTPUT = ROOT / 'output/butterfly-video/ai_60'
CLIENT_DIRECTORY = Path(os.environ.get('FLOWLY_GRADIO_CLIENT_DIR', ROOT / '.cache/ai-video-client'))


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    temporary.replace(path)


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=width,height,nb_frames,r_frame_rate', '-of', 'json', str(path),
    ], text=True, timeout=30))


def generate_clip(client, spec, shot, handle_file):
    import requests
    source = OUTPUT / 'keyframes' / shot['image']
    if not source.is_file():
        raise FileNotFoundError(source)
    target = OUTPUT / 'clips' / (shot['id'] + '.mp4')
    provenance = target.with_suffix('.json')
    if target.is_file() and provenance.is_file():
        saved = json.loads(provenance.read_text(encoding='utf-8'))
        if saved.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest():
            print(json.dumps({'shot': shot['id'], 'status': 'reused', 'file': str(target)}), flush=True)
            return
        raise ValueError('Cached clip differs from its recorded provider output')
    progress = OUTPUT / 'ltx-progress.json'
    state = {'shot': shot['id'], 'status': 'submitting', 'model': spec['model'], 'started_at': time.time()}
    write_json(progress, state)
    print(json.dumps(state), flush=True)
    job = client.submit(
        prompt=shot['prompt'], negative_prompt=spec['negative_prompt'],
        input_image_filepath=handle_file(str(source.resolve())), input_video_filepath=None,
        height_ui=spec['height'], width_ui=spec['width'], mode='image-to-video',
        duration_ui=spec['seconds'], ui_frames_to_use=9, seed_ui=spec['seed'],
        randomize_seed=False, ui_guidance_scale=1, improve_texture_flag=True,
        api_name=spec['api_name'],
    )
    deadline = time.monotonic() + spec['timeout_seconds']
    while not job.done():
        status = job.status()
        state.update(status=str(status.code), rank=status.rank, updated_at=time.time())
        write_json(progress, state)
        print(json.dumps(state), flush=True)
        if time.monotonic() >= deadline:
            raise TimeoutError('Existing remote generation is still pending; do not duplicate its submission')
        time.sleep(spec['poll_seconds'])
    result = job.result()
    raw = {**state, 'status': 'generated', 'provider': spec['provider'], 'space_url': spec['space_url'],
           'prompt': shot['prompt'], 'input_image': str(source), 'result': result}
    write_json(OUTPUT / (shot['id'] + '-provider-result.json'), raw)
    url = result[0]['video']['url']
    if not url or not url.startswith(spec['space_url'] + '/'):
        raise ValueError('Unexpected LTX output location')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Download for the requested editing/concatenation, preserving the raw output.
    with requests.get(url, stream=True, timeout=90) as response:
        response.raise_for_status()
        with target.open('wb') as destination:
            for chunk in response.iter_content(1024 * 1024):
                destination.write(chunk)
    metadata = probe(target)
    duration = float(metadata['format']['duration'])
    if abs(duration - spec['seconds']) > 0.08:
        raise ValueError(f'Actual model clip duration {duration} differs from the requested duration')
    record = {**raw, 'status': 'completed', 'video_url': url, 'file': str(target),
              'duration': duration, 'media': metadata, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    write_json(provenance, record)
    write_json(progress, record)
    print(json.dumps({'shot': shot['id'], 'status': 'completed', 'duration': duration, 'file': str(target)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--shots', type=int, nargs='+', required=True)
    args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if any(index < 1 or index > len(spec['shots']) for index in args.shots):
        parser.error('Shot index is outside the configured film')
    sys.path.insert(0, str(CLIENT_DIRECTORY))
    from gradio_client import Client, handle_file
    client = Client(spec['space_url'], verbose=False, download_files=False,
                    httpx_kwargs={'timeout': 120.0})
    for index in args.shots:
        shot = spec['shots'][index - 1]
        try:
            generate_clip(client, spec, shot, handle_file)
        except Exception as error:
            write_json(OUTPUT / 'ltx-progress.json', {'shot': shot['id'], 'status': 'failed', 'error': str(error), 'updated_at': time.time()})
            print(json.dumps({'shot': shot['id'], 'error': str(error)}, ensure_ascii=True), flush=True)
            raise
