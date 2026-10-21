"""Independent, resumable AI embroidery modules with verified source footage."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from django.conf import settings
from django.core.cache import cache

from workflows.execution_control import write_heartbeat
from workflows.models import WorkflowExecution
from .butterfly_ltx_job import GPU_LOCK, probe_media
from .media_service import build_public_media_url, local_path_from_public_url

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = PROJECT_ROOT / 'output/butterfly-video'
GENERATION_ROOT = ASSET_ROOT / 'flowly_modular_60/generations'
GENERATOR = PROJECT_ROOT / 'Backend/scripts/generate_embroidery_module.py'
LOCAL_MODELS = {
    'ltx': {'provider': 'ltx_local', 'prefix': 'Lightricks/', 'script': GENERATOR},
    'wan': {'provider': 'wan_local', 'prefix': 'Wan-AI/',
            'script': PROJECT_ROOT / 'Backend/scripts/generate_wan_embroidery_module.py'},
    'vace': {'provider': 'wan_vace_local', 'prefix': 'Wan-AI/',
             'script': PROJECT_ROOT / 'Backend/scripts/generate_vace_embroidery_module.py'},
}
MEDIA_FOLDER = 'embroidery_modules'
DURATION_TOLERANCE = 0.05
PROCESS_POLL_SECONDS = 3
PROCESS_SHUTDOWN_SECONDS = 30
LOCK_MARGIN_SECONDS = 120


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def asset_path(relative):
    path = (ASSET_ROOT / relative).resolve()
    if not path.is_relative_to(ASSET_ROOT.resolve()):
        raise ValueError('模块素材路径必须位于刺绣素材目录内')
    return path


def build_request(module, overrides):
    shot = copy.deepcopy(module['shot'])
    shot['prompt'] = overrides.get('prompt', shot['prompt'])
    shot['seed'] = overrides.get('seed', shot['seed'])
    if not isinstance(shot['prompt'], str) or not shot['prompt'].strip():
        raise ValueError('模块提示词不能为空')
    if isinstance(shot['seed'], bool) or not isinstance(shot['seed'], int) or not 0 <= shot['seed'] < 2**32:
        raise ValueError('模块种子必须为有效非负整数')
    if not shot['id'].replace('-', '').replace('_', '').isalnum():
        raise ValueError('模块标识包含非法字符')
    family = module['model_spec'].get('model_family', 'ltx')
    if family not in LOCAL_MODELS:
        raise ValueError('不支持的本机视频模型')
    if family == 'wan':
        mode = module['model_spec'].get('condition_mode', 'first_frame')
        if mode not in ('first_frame', 'keyframes'):
            raise ValueError('不支持的 Wan 关键帧模式')
        if mode == 'first_frame' and (shot.get('end_image') or shot.get('conditions')):
            raise ValueError('Wan 图生视频模式仅支持起始关键帧')
        if mode == 'keyframes':
            count = round(module['model_spec']['seconds'] * module['model_spec']['fps'])
            indices = [condition['frame_index'] for condition in shot.get('conditions', [])]
            if ((count - 1) % 4 or len(set(indices)) != len(indices) or
                    any(isinstance(index, bool) or not isinstance(index, int) or
                        not 0 < index < count - 1 or index % 4 for index in indices)):
                raise ValueError('Wan 中间关键帧必须为不重复的内部第 4n 帧')
    directory = asset_path(module['source_directory'])
    names = {shot['image'], *(c['image'] for c in shot.get('conditions', []))}
    if shot.get('end_image') is not None:
        if not isinstance(shot['end_image'], str) or not shot['end_image'].strip():
            raise ValueError('结束关键帧必须为有效路径或 null')
        names.add(shot['end_image'])
    hashes = {}
    for name in sorted(names):
        path = (directory / 'keyframes' / name).resolve()
        if not path.is_relative_to((directory / 'keyframes').resolve()) or not path.is_file():
            raise ValueError('缺少有效关键帧：' + name)
        hashes[name] = digest(path)
    request = {'shot': shot, 'spec': module['model_spec'], 'keyframe_hashes': hashes}
    if family == 'vace':
        if shot.get('end_image') or shot.get('conditions'):
            raise ValueError('VACE 动作参考模式仅接受一个外观参考图')
        video = asset_path(shot['control_video'])
        if not video.is_file() or video.suffix.lower() != '.mp4':
            raise ValueError('缺少有效动作参考视频')
        request['control_video_hash'] = digest(video)
    request['fingerprint'] = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    return request, directory


def read_source(directory, request, expected_sha=None, require_fingerprint=False):
    shot, spec = request['shot'], request['spec']
    source = directory / 'clips' / (shot['id'] + '.mp4')
    proof = source.with_suffix('.json')
    if not source.is_file() or not proof.is_file():
        return None
    record = json.loads(proof.read_text(encoding='utf-8'))
    model = LOCAL_MODELS[spec.get('model_family', 'ltx')]
    if record.get('provider') != model['provider'] or not record.get('model', '').startswith(model['prefix']):
        raise ValueError('模块视频缺少真实 AI 来源')
    if (record.get('prompt') != shot['prompt'] or record.get('seed') != shot['seed']
            or record.get('conditions', []) != shot.get('conditions', [])
            or record.get('last_frame') != shot.get('end_image')):
        return None
    if request.get('control_video_hash') != record.get('control_video_hash'):
        return None
    checksum = digest(source)
    if record.get('sha256') != checksum or (expected_sha and checksum != expected_sha):
        raise ValueError('模块视频文件与生成记录校验值不一致')
    if require_fingerprint and record.get('request_fingerprint') != request['fingerprint']:
        return None
    media = probe_media(source)
    stream = media['streams'][0]
    if (abs(float(media['format']['duration']) - spec['seconds']) > DURATION_TOLERANCE
            or int(stream['nb_frames']) != round(spec['seconds'] * spec['fps'])
            or stream['width'] != spec['width'] or stream['height'] != spec['height']
            or stream['r_frame_rate'] != f"{spec['fps']}/1"):
        raise ValueError('模块视频时长、尺寸或帧率不符合规格')
    return source, record


def run_generation(execution, request, source_directory, generation_directory):
    timeout = request['spec']['timeout_seconds']
    lock_value = str(execution.pk) + ':' + request['fingerprint']
    if not cache.add(GPU_LOCK, lock_value, timeout=timeout + LOCK_MARGIN_SECONDS):
        raise RuntimeError('免费本机视频模型正在使用中，可稍后继续此模块')
    process = None
    try:
        frames = generation_directory / 'keyframes'
        frames.mkdir(parents=True, exist_ok=True)
        for name in request['keyframe_hashes']:
            target = frames / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_directory / 'keyframes' / name, target)
        if request.get('control_video_hash'):
            control = asset_path(request['shot']['control_video'])
            if digest(control) != request['control_video_hash']:
                raise ValueError('动作参考视频在执行前发生变化')
            shutil.copy2(control, generation_directory / 'control.mp4')
        request_path = generation_directory / 'request.json'
        request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
        with (generation_directory / 'generation.log').open('w', encoding='utf-8') as log:
            generator = LOCAL_MODELS[request['spec'].get('model_family', 'ltx')]['script']
            process = subprocess.Popen([sys.executable, '-X', 'faulthandler', str(generator), '--request', str(request_path)],
                                       cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                execution.refresh_from_db(fields=['status'])
                if execution.status != 'running':
                    raise RuntimeError('执行已停止，当前 AI 模块已取消')
                if time.monotonic() >= deadline:
                    raise TimeoutError('AI 模块超时，可从此节点继续；已完成模块保留')
                write_heartbeat(execution)
                time.sleep(PROCESS_POLL_SECONDS)
        if process.returncode:
            raise RuntimeError(f'AI 模块生成失败（退出码 {process.returncode}），详见 ' + str(generation_directory / 'generation.log'))
    finally:
        if process and process.poll() is None:
            stop_process(process)
        if cache.get(GPU_LOCK) == lock_value:
            cache.delete(GPU_LOCK)


def stop_process(process):
    if os.name == 'nt':
        # Windows venv launchers spawn a second interpreter which also owns CUDA.
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       capture_output=True, timeout=PROCESS_SHUTDOWN_SECONDS, check=False)
    else:
        process.kill()
    process.wait(timeout=PROCESS_SHUTDOWN_SECONDS)


def render_clip(source, target, edit, encoding):
    stream = probe_media(source)['streams'][0]
    start, end = edit['start_frame'], edit['end_frame']
    factor = edit['retiming_factor']
    count = round(edit['seconds'] * encoding['fps'])
    if not 0 <= start < end <= int(stream['nb_frames']) or not math.isfinite(factor) or factor <= 0:
        raise ValueError('模块剪辑范围或速度无效')
    filters = f'trim=start_frame={start}:end_frame={end},setpts={factor}*(PTS-STARTPTS)'
    filters += ',' + (encoding['optical_flow'] if factor > 1 else f"fps={encoding['fps']}")
    filters += f',trim=end_frame={count},setpts=PTS-STARTPTS'
    if edit['zoom'] != [1, 1]:
        def value(pair):
            return f'({pair[0]}+({pair[1]}-{pair[0]})*on/{count-1})'
        zoom, x, y = (value(edit[key]) for key in ('zoom', 'x', 'y'))
        scale = encoding['sampling_scale']
        filters += (f",scale={encoding['width']*scale}:{encoding['height']*scale}:flags=lanczos"
                    f",zoompan=z='{zoom}':x='(iw-iw/zoom)*{x}':y='(ih-ih/zoom)*{y}'"
                    f":d=1:s={encoding['width']}x{encoding['height']}:fps={encoding['fps']}")
    else:
        filters += f",scale={encoding['width']}:{encoding['height']}:flags=lanczos,setsar=1"
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(source), '-vf', filters, '-an',
                    '-c:v', 'libx264', '-preset', encoding['preset'], '-crf', str(encoding['crf']),
                    '-pix_fmt', 'yuv420p', '-video_track_timescale', str(encoding['timescale']),
                    '-movflags', '+faststart', str(target)], check=True, capture_output=True,
                   timeout=encoding['timeout_seconds'])
    media = probe_media(target)
    out = media['streams'][0]
    if (int(out['nb_frames']) != count or out['codec_name'] != 'h264'
            or out['width'] != encoding['width'] or out['height'] != encoding['height']
            or abs(float(media['format']['duration']) - edit['seconds']) > DURATION_TOLERANCE):
        raise ValueError('模块剪辑结果不完整，禁止补静帧凑时长')
    return media


def generate_node(parameters, input_data):
    metadata = (input_data.get('_execution') or {}).get('metadata') or input_data.get('metadata') or {}
    execution = WorkflowExecution.objects.select_related('workflow').get(pk=metadata.get('execution_id'))
    spec = execution.workflow.config['embroidery_spec']
    matches = [m for m in spec['modules'] if m['id'] == parameters.get('module_id')]
    if len(matches) != 1:
        raise ValueError('当前工作流不存在该刺绣模块')
    module = matches[0]
    request, directory = build_request(module, parameters)
    saved = None
    if module.get('source_sha256') and module.get('source_keyframe_hashes') == request['keyframe_hashes']:
        saved = read_source(directory, request, module['source_sha256'])
    generation_directory = GENERATION_ROOT / str(execution.workflow.owner_id) / request['fingerprint']
    if not saved:
        saved = read_source(generation_directory, request, require_fingerprint=True)
    reused = bool(saved)
    if not saved:
        run_generation(execution, request, directory, generation_directory)
        saved = read_source(generation_directory, request, require_fingerprint=True)
        if not saved:
            raise RuntimeError('AI 模块没有产出与请求一致的真实视频')
    source, record = saved
    folder = Path(settings.MEDIA_ROOT) / MEDIA_FOLDER / str(execution.workflow.owner_id) / str(execution.pk)
    target = folder / (module['id'] + '.mp4')
    media = render_clip(source, target, module['edit'], spec['encoding'])
    result = {'module_id': module['id'], 'caption': module['caption'], 'duration': module['edit']['seconds'],
              'video_url': build_public_media_url(target.relative_to(settings.MEDIA_ROOT).as_posix()),
              'provider': record['provider'], 'model': record['model'], 'sha256': digest(target),
              'source_sha256': record['sha256'], 'source_file': str(source), 'cached_model_output': reused,
              'request_fingerprint': request['fingerprint'], 'keyframe_hashes': request['keyframe_hashes'],
              'prompt': request['shot']['prompt'], 'seed': request['shot']['seed'],
              'edit': module['edit'], 'media': media, 'status': 'completed'}
    target.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def verify_final(parameters, input_data):
    url = input_data.get('video_url')
    path = local_path_from_public_url(url)
    media = probe_media(path)
    if abs(float(media['format']['duration']) - parameters['seconds']) > DURATION_TOLERANCE:
        raise ValueError('工作流成片时长不正确')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'],
                   check=True, capture_output=True, timeout=parameters['timeout_seconds'])
    return {'video_url': url, 'duration': parameters['seconds'], 'sha256': digest(path),
            'full_decode': 'passed', 'media': media}
