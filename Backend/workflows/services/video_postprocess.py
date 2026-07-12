"""FFmpeg-based video/audio post-processing for video translation pipeline."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from django.conf import settings

logger = logging.getLogger(__name__)


class VideoPostprocessError(Exception):
    """Raised when FFmpeg/ffprobe operations fail."""


def ffmpeg_binary() -> str:
    return getattr(settings, 'FFMPEG_BINARY', 'ffmpeg') or 'ffmpeg'


def ffprobe_binary() -> str:
    return getattr(settings, 'FFPROBE_BINARY', 'ffprobe') or 'ffprobe'


def _run_cmd(args: Sequence[str], *, timeout: int = 600) -> subprocess.CompletedProcess:
    if not shutil.which(args[0]):
        raise VideoPostprocessError(
            f'未找到 {args[0]}。请安装 FFmpeg 并配置 FFMPEG_BINARY/FFPROBE_BINARY 环境变量。'
        )
    try:
        return subprocess.run(
            list(args),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or '').strip()
        raise VideoPostprocessError(stderr or f'FFmpeg 命令失败: {" ".join(args)}') from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoPostprocessError(f'FFmpeg 命令超时: {" ".join(args)}') from exc


def probe_media(path: str | Path) -> Dict[str, Any]:
    """Return duration and stream metadata via ffprobe."""
    src = str(path)
    proc = _run_cmd([
        ffprobe_binary(),
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        src,
    ])
    data = json.loads(proc.stdout or '{}')
    fmt = data.get('format') or {}
    streams = data.get('streams') or []
    duration = float(fmt.get('duration') or 0)
    has_video = any(s.get('codec_type') == 'video' for s in streams)
    has_audio = any(s.get('codec_type') == 'audio' for s in streams)
    return {
        'duration': duration,
        'has_video': has_video,
        'has_audio': has_audio,
        'format': fmt,
        'streams': streams,
    }


def extract_audio(video_path: str | Path, *, output_path: Optional[str | Path] = None, fmt: str = 'wav') -> Path:
    """Extract audio track from video."""
    src = Path(video_path)
    if output_path:
        dest = Path(output_path)
    else:
        dest = src.with_suffix(f'.{fmt}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    codec = 'pcm_s16le' if fmt == 'wav' else 'libmp3lame'
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-i', str(src),
        '-vn',
        '-acodec', codec,
        str(dest),
    ])
    return dest


def adjust_audio_duration(audio_path: str | Path, target_sec: float, *, output_path: Optional[Path] = None) -> Path:
    """Stretch/compress audio to target duration using atempo (clamped 0.5-2.0 per pass)."""
    src = Path(audio_path)
    info = probe_media(src)
    current = float(info.get('duration') or 0)
    if current <= 0 or target_sec <= 0:
        return src
    if abs(current - target_sec) < 0.05:
        return src

    dest = output_path or src.with_name(f'{src.stem}_aligned{src.suffix}')
    ratio = current / target_sec
    filters: List[str] = []
    remaining = ratio
    while remaining > 2.0:
        filters.append('atempo=2.0')
        remaining /= 2.0
    while remaining < 0.5:
        filters.append('atempo=0.5')
        remaining /= 0.5
    if abs(remaining - 1.0) > 0.01:
        filters.append(f'atempo={remaining:.4f}')
    filter_expr = ','.join(filters) if filters else 'anull'
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-i', str(src),
        '-filter:a', filter_expr,
        str(dest),
    ])
    return dest


def _pad_or_trim_segment(audio_path: Path, target_sec: float, work_dir: Path) -> Path:
    info = probe_media(audio_path)
    current = float(info.get('duration') or 0)
    out = work_dir / f'seg_{uuid.uuid4().hex}{audio_path.suffix or ".mp3"}'
    if current <= 0:
        _run_cmd([
            ffmpeg_binary(), '-y',
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
            '-t', f'{max(target_sec, 0.1):.3f}',
            str(out),
        ])
        return out
    if current > target_sec + 0.02:
        return adjust_audio_duration(audio_path, target_sec, output_path=out)
    if current < target_sec - 0.02:
        pad = target_sec - current
        _run_cmd([
            ffmpeg_binary(), '-y',
            '-i', str(audio_path),
            '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=mono:d={pad:.3f}',
            '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[outa]',
            '-map', '[outa]',
            str(out),
        ])
        return out
    shutil.copy2(audio_path, out)
    return out


def concat_segment_audio(
    segments: Sequence[Dict[str, Any]],
    audio_files: Sequence[str | Path],
    *,
    total_duration: Optional[float] = None,
    work_dir: Optional[Path] = None,
) -> Path:
    """
    Build a single audio track aligned to segment timestamps.
    Each segment dict must include start/end; audio_files order matches segments.
    """
    if len(segments) != len(audio_files):
        raise VideoPostprocessError('segments 与 audio_files 数量不一致')

    work = work_dir or Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)

    if not segments:
        silent = work / 'silent.mp3'
        dur = total_duration or 1.0
        _run_cmd([
            ffmpeg_binary(), '-y',
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
            '-t', f'{dur:.3f}',
            '-c:a', 'libmp3lame',
            str(silent),
        ])
        return silent

    timeline_end = total_duration
    if timeline_end is None:
        timeline_end = max(float(s.get('end') or 0) for s in segments)
    timeline_end = max(timeline_end, float(segments[-1].get('end') or 0), 0.5)

    delayed_paths: List[Path] = []
    for seg, audio in zip(segments, audio_files):
        start = float(seg.get('start') or 0)
        end = float(seg.get('end') or start)
        target = max(end - start, 0.1)
        aligned = _pad_or_trim_segment(Path(audio), target, work)
        start_ms = int(max(start, 0) * 1000)
        delayed = work / f'delay_{uuid.uuid4().hex}.mp3'
        _run_cmd([
            ffmpeg_binary(), '-y',
            '-i', str(aligned),
            '-af', f'adelay={start_ms}|{start_ms}',
            str(delayed),
        ])
        delayed_paths.append(delayed)

    if len(delayed_paths) == 1:
        final = work / 'dubbed.mp3'
        shutil.copy2(delayed_paths[0], final)
        return final

    inputs: List[str] = []
    for p in delayed_paths:
        inputs.extend(['-i', str(p)])
    n = len(delayed_paths)
    filter_parts = ''.join(f'[{i}:a]' for i in range(n))
    filter_complex = f'{filter_parts}amix=inputs={n}:duration=longest:dropout_transition=0[outa]'
    final = work / 'dubbed.mp3'
    _run_cmd([
        ffmpeg_binary(), '-y',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', '[outa]',
        '-t', f'{timeline_end:.3f}',
        str(final),
    ])
    return final


def mux_audio_video(video_path: str | Path, audio_path: str | Path, *, output_path: Optional[Path] = None) -> Path:
    """Replace video audio track with dubbed audio."""
    video = Path(video_path)
    audio = Path(audio_path)
    dest = output_path or video.with_name(f'{video.stem}_dubbed{video.suffix}')
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-i', str(video),
        '-i', str(audio),
        '-c:v', 'copy',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        str(dest),
    ])
    return dest


def _escape_subtitles_path(path: Path) -> str:
    """Escape path for ffmpeg subtitles filter on Windows."""
    s = str(path.resolve()).replace('\\', '/').replace(':', '\\:')
    return s


def burn_subtitles(
    video_path: str | Path,
    subtitle_path: str | Path,
    *,
    output_path: Optional[Path] = None,
) -> Path:
    """Burn SRT/VTT subtitles into video."""
    video = Path(video_path)
    subs = Path(subtitle_path)
    dest = output_path or video.with_name(f'{video.stem}_subbed{video.suffix}')
    subs_filter = _escape_subtitles_path(subs)
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-i', str(video),
        '-vf', f"subtitles='{subs_filter}':force_style='FontSize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2'",
        '-c:a', 'copy',
        str(dest),
    ])
    return dest


def write_subtitle_file(content: str, *, fmt: str = 'srt', work_dir: Optional[Path] = None) -> Path:
    work = work_dir or Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)
    ext = 'vtt' if fmt == 'vtt' else 'srt'
    path = work / f'subtitles.{ext}'
    path.write_text(content, encoding='utf-8')
    return path


def create_silent_audio(duration_sec: float, output_path: Path, *, fmt: str = 'mp3') -> Path:
    """Create a silent audio clip of given duration."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    codec = 'libmp3lame' if fmt == 'mp3' else 'pcm_s16le'
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
        '-t', f'{max(float(duration_sec or 0), 0.1):.3f}',
        '-c:a', codec,
        str(output_path),
    ])
    return output_path


def is_ffmpeg_available() -> bool:
    return bool(shutil.which(ffmpeg_binary()) and shutil.which(ffprobe_binary()))
