"""Native workflow tools for reference-derived, reproducible 3D embroidery."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import cv2
import numpy as np
from PIL import Image
from django.conf import settings
from django.db import close_old_connections

from workflows.models import WorkflowExecution
from workflows.execution_control import write_heartbeat, heartbeat_interval_seconds
from .media_service import build_public_media_url, local_path_from_public_url

SPEC_PATH = Path(__file__).with_name('embroidery_3d_spec.json')
SCRIPT_PATH = Path(__file__).with_name('embroidery_3d_blender.py')
OPERATIONS = frozenset({'prepare', 'build', 'animate', 'previews', 'render', 'finish'})


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8'))


def job_context(input_data):
    metadata = (input_data.get('_execution') or {}).get('metadata') or input_data.get('metadata') or {}
    execution = WorkflowExecution.objects.select_related('workflow').get(pk=metadata.get('execution_id'))
    root = Path(settings.MEDIA_ROOT).resolve()
    directory = root / 'embroidery_3d' / str(execution.workflow.owner_id) / str(execution.pk)
    directory.mkdir(parents=True, exist_ok=True)
    return execution, directory


def public(path):
    return build_public_media_url(path.resolve().relative_to(Path(settings.MEDIA_ROOT).resolve()).as_posix())


def build_viewer(directory):
    modules = Path(settings.BASE_DIR).parent / 'Frontend/node_modules/three'
    files = {
        'build/three.module.js': 'vendor/three.module.js',
        'examples/jsm/controls/OrbitControls.js': 'vendor/controls/OrbitControls.js',
        'examples/jsm/loaders/GLTFLoader.js': 'vendor/loaders/GLTFLoader.js',
        'examples/jsm/utils/BufferGeometryUtils.js': 'vendor/utils/BufferGeometryUtils.js',
        'LICENSE': 'vendor/THREE-LICENSE.txt',
    }
    for source, target in files.items():
        destination = directory / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(modules / source, destination)
    viewer = directory / 'viewer.html'
    shutil.copy2(Path(__file__).with_name('embroidery_viewer.html'), viewer)
    return viewer


def thinning(mask):
    """Zhang-Suen skeleton, preserving the original reference's line connectivity."""
    image = np.pad((mask > 0).astype(np.uint8), 1)
    while True:
        changed = False
        for phase in (0, 1):
            p = [image[:-2, 1:-1], image[:-2, 2:], image[1:-1, 2:], image[2:, 2:], image[2:, 1:-1], image[2:, :-2], image[1:-1, :-2], image[:-2, :-2]]
            neighbors = sum(p)
            transitions = sum((p[i] == 0) & (p[(i+1) % 8] == 1) for i in range(8))
            if phase == 0:
                a, b = p[0]*p[2]*p[4], p[2]*p[4]*p[6]
            else:
                a, b = p[0]*p[2]*p[6], p[0]*p[4]*p[6]
            remove = (image[1:-1, 1:-1] == 1) & (neighbors >= 2) & (neighbors <= 6) & (transitions == 1) & (a == 0) & (b == 0)
            if remove.any():
                image[1:-1, 1:-1][remove] = 0
                changed = True
        if not changed:
            return image[1:-1, 1:-1]


def trace_paths(mask, spec):
    skeleton = thinning(mask)
    pixels = set(map(tuple, np.argwhere(skeleton)))
    offsets = [(y, x) for y in (-1, 0, 1) for x in (-1, 0, 1) if y or x]
    adjacency = {p: [(p[0]+dy, p[1]+dx) for dy, dx in offsets if (p[0]+dy, p[1]+dx) in pixels] for p in pixels}
    used, paths = set(), []
    starts = sorted(pixels, key=lambda p: (len(adjacency[p]) == 2, p))
    for start in starts:
        for next_pixel in adjacency[start]:
            edge = frozenset((start, next_pixel))
            if edge in used:
                continue
            path, previous, current = [start, next_pixel], start, next_pixel
            used.add(edge)
            while len(adjacency[current]) == 2:
                candidate = next(p for p in adjacency[current] if p != previous)
                edge = frozenset((current, candidate))
                if edge in used:
                    break
                used.add(edge)
                path.append(candidate)
                previous, current = current, candidate
            points = np.array([(x, y) for y, x in path], dtype=np.float32)
            length = np.linalg.norm(np.diff(points, axis=0), axis=1).sum()
            if length >= spec['trace']['minimum_path_pixels']:
                simplified = cv2.approxPolyDP(points[:, None, :], spec['trace']['smooth_tolerance'], False)[:, 0]
                paths.append(simplified.tolist())
    return paths


def prepare(params, input_data):
    execution, directory = job_context(input_data)
    spec = load_spec()
    reference = params.get('reference_url') or input_data.get('reference_url')
    source = local_path_from_public_url(reference)
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if source is None or not source.resolve().is_relative_to(media_root) or not source.is_file():
        raise ValueError('需要已上传的创新点一设计图')
    image = Image.open(source).convert('RGB')
    crops = {}
    for name, bounds in spec['crops'].items():
        if not (0 <= bounds[0] < bounds[2] <= image.width and 0 <= bounds[1] < bounds[3] <= image.height):
            raise ValueError('参考图尺寸与提取区域不匹配')
        path = directory / f'reference_{name}.png'
        image.crop(bounds).save(path)
        crops[name] = path
    motif = np.asarray(Image.open(crops['motif']).convert('RGB'))
    gray = cv2.cvtColor(motif, cv2.COLOR_RGB2GRAY)
    mask = np.uint8(gray < spec['trace']['threshold']) * 255
    paths = trace_paths(mask, spec)
    h, w = mask.shape
    world_w = spec['trace']['world_width']
    records = []
    centers = np.asarray(spec['diamonds'])
    for points in paths:
        normalized = np.asarray(points, dtype=float)
        normalized[:, 0] = (normalized[:, 0] / w - .5) * 2
        normalized[:, 1] = (.5 - normalized[:, 1] / h) * 2
        center = normalized.mean(axis=0)
        distance = np.abs(centers-center).sum(axis=1).min()
        role = 'bone' if abs(center[0]) < .12 or distance < .4 else 'feather'
        records.append({'role': role, 'kind': 'outline', 'points': [[float(x*world_w/2), float(y*world_w*h/w/2)] for x, y in normalized]})
    if len(records) < 40 or not any(row['role'] == 'bone' for row in records) or not any(row['role'] == 'feather' for row in records):
        raise ValueError('参考线条提取不足，不能生成有效的蝶羽三维纹样')
    from .embroidery_geometry import build_stitches
    stitches = build_stitches(spec)
    geometry = {'reference_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'source_dimensions': [w, h], 'paths': stitches, 'reference_traces': records, 'line_paths': len(paths), 'stitch_paths': len(stitches), 'source': str(crops['motif']), 'spec': spec, 'model_method': 'reference-derived continuous curves and directional satin stitch reconstruction'}
    (directory / 'geometry.json').write_text(json.dumps(geometry, ensure_ascii=False), encoding='utf-8')
    (directory / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'geometry_path': str(directory / 'geometry.json'), 'stitch_paths': len(stitches), 'reference_sha256': geometry['reference_sha256'], 'images': [{'url': public(path)} for path in crops.values()], 'files': [{'url': public(directory / 'geometry.json')}]}


def blender_binary():
    root = Path(settings.BASE_DIR).parent
    configured = os.environ.get('FLOWLY_BLENDER_PATH')
    candidates = [Path(configured)] if configured else list((root / '.cache/blender').glob('blender-*/blender.exe'))
    candidates += [Path(shutil.which('blender'))] if shutil.which('blender') else []
    for candidate in reversed(candidates):
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError('未安装 Blender；请配置 FLOWLY_BLENDER_PATH')


def run_blender(operation, execution, directory):
    spec = load_spec()
    log = directory / f'{operation}.log'
    command = [str(blender_binary()), '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(SCRIPT_PATH), '--', '--operation', operation, '--directory', str(directory)]
    start = time.monotonic()
    last_heartbeat = 0
    with log.open('wb') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            while process.poll() is None:
                time.sleep(spec['poll_seconds'])
                close_old_connections()
                state = WorkflowExecution.objects.filter(pk=execution.pk).values_list('status', flat=True).first()
                if state in ('cancelled', 'failed', 'timeout'):
                    raise RuntimeError(f'三维任务已停止：{state}')
                if time.monotonic()-last_heartbeat >= heartbeat_interval_seconds():
                    execution.refresh_from_db(fields=['context_data'])
                    progress_path = directory / 'render_progress.json'
                    extra = {'media_stage': operation}
                    if progress_path.exists():
                        extra['render_progress'] = json.loads(progress_path.read_text(encoding='utf-8'))
                    write_heartbeat(execution, extra=extra)
                    last_heartbeat = time.monotonic()
                if time.monotonic()-start > spec['process_timeout']:
                    raise TimeoutError('三维处理超时，保留已有模型和渲染帧供恢复')
            if process.returncode:
                raise RuntimeError(f'Blender {operation} 失败：{log.read_text(encoding="utf-8", errors="replace")[-2400:]}')
            if operation in ('build', 'animate') and not (directory / 'scene.blend').is_file():
                raise RuntimeError('Blender没有生成三维工程，不能将该节点标记为成功')
            expected_files = {'animate': ['pattern.glb','garment.glb','scene_report.json'], 'previews': [f'preview_{t:02}.png' for t in spec['preview_times']]}.get(operation, [])
            if any(not (directory / name).is_file() for name in expected_files):
                raise RuntimeError(f'Blender {operation} 没有生成全部预期产物')
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=20)
            raise
    return {'files': [{'url': public(path)} for path in directory.glob('*.blend')] + [{'url': public(path)} for path in directory.glob('*.glb')], 'images': [{'url': public(path)} for path in sorted(directory.glob('preview_*.png'))], 'stage': operation}


def finish(execution, directory):
    spec = load_spec()
    frames = sorted((directory / 'frames').glob('*.png'))
    expected = spec['duration'] * spec['fps']
    if [path.name for path in frames] != [f'{i:05}.png' for i in range(1,expected+1)]:
        raise ValueError(f'渲染不完整：需要 {expected} 帧，实际 {len(frames)} 帧')
    subtitle = directory / 'captions.ass'
    def timestamp(seconds):
        return f'0:{int(seconds)//60:02}:{seconds%60:05.2f}'
    header = '[Script Info]\nScriptType: v4.00+\nPlayResX: 1280\nPlayResY: 720\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Main,Microsoft YaHei,24,&H00F5F4EF,&H00F5F4EF,&H001D242D,&H901D242D,0,0,0,0,100,100,0,0,3,1,0,2,20,20,44,1\nStyle: Note,Microsoft YaHei,14,&H00D8D8D0,&H00D8D8D0,&H001D242D,&H901D242D,0,0,0,0,100,100,0,0,3,1,0,2,20,20,14,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    events = [f'Dialogue: 0,{timestamp(c["start"])},{timestamp(c["end"])},Main,,0,0,0,,{c["text"]}' for c in spec['captions']]
    events.append(f'Dialogue: 1,0:00:00.00,0:01:00.00,Note,,0,0,0,,{spec["disclosure"]}')
    subtitle.write_text(header+'\n'.join(events), encoding='utf-8')
    video = directory / 'butterfly_3d_60s.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', str(spec['fps']), '-i', 'frames/%05d.png', '-vf', 'subtitles=captions.ass', '-c:v', 'libx264', '-crf', str(spec['crf']), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', video.name], cwd=directory, check=True, timeout=600)
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True, timeout=600, capture_output=True)
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)]))
    stream = next(row for row in metadata['streams'] if row['codec_type'] == 'video')
    if abs(float(metadata['format']['duration'])-spec['duration']) > 1/spec['fps'] or int(stream['nb_frames']) != expected:
        raise ValueError('最终成片时长或帧数不正确')
    report = {'duration': float(metadata['format']['duration']), 'frames': expected, 'width': stream['width'], 'height': stream['height'], 'sha256': hashlib.sha256(video.read_bytes()).hexdigest(), 'method': 'Blender actual 3D curves, mesh garments, animated thread growth and mesh morph mapping', 'concept_only': True}
    (directory / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    viewer = build_viewer(directory)
    return {'video_url': public(video), 'website_url': public(viewer), 'images': [{'url': public(p)} for p in sorted(directory.glob('preview_*.png'))], 'files': [{'url': public(p)} for p in [directory/'scene.blend', directory/'pattern.glb', directory/'garment.glb', directory/'geometry.json', directory/'spec.json', directory/'verification.json']], 'subtitle_url': public(subtitle), 'verification': report, 'disclosure': spec['disclosure']}


def execute(params, input_data):
    operation = params.get('operation')
    if operation not in OPERATIONS or params.get('preset') != load_spec()['preset']:
        raise ValueError('三维刺绣操作或预设无效')
    if operation == 'prepare':
        return prepare(params, input_data)
    execution, directory = job_context(input_data)
    if not (directory / 'geometry.json').is_file():
        raise ValueError('缺少参考图与丝线路径，必须先执行提取节点')
    if operation == 'finish':
        return finish(execution, directory)
    return run_blender(operation, execution, directory)
