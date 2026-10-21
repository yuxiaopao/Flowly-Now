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


def render_storyboard_placeholder_clip(
    *,
    shot_index: int,
    title: str,
    action: str = '',
    duration_sec: float = 5.0,
    output_path: Optional[str | Path] = None,
    work_dir: Optional[Path] = None,
) -> Path:
    """Render a distinct local 720p clip for a storyboard beat.

    Uses Pillow title card + ffmpeg still-to-video so Chinese text works on Windows
    without fontconfig/drawtext issues.
    """
    from PIL import Image, ImageDraw, ImageFont

    work = work_dir or Path(settings.MEDIA_ROOT) / 'workflow_placeholders' / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path else (work / f'shot_{int(shot_index):02d}.mp4')
    frame_path = work / f'shot_{int(shot_index):02d}.png'

    palette = [
        (26, 35, 50), (42, 31, 51), (31, 42, 40), (51, 36, 26),
        (26, 42, 51), (42, 26, 34), (36, 48, 26), (48, 26, 42),
        (26, 48, 48), (48, 36, 26), (36, 26, 48), (26, 48, 36),
    ]
    bg = palette[(max(1, int(shot_index)) - 1) % len(palette)]
    img = Image.new('RGB', (1280, 720), bg)
    draw = ImageDraw.Draw(img)

    font_paths = [
        Path(r'C:\Windows\Fonts\msyh.ttc'),
        Path(r'C:\Windows\Fonts\msyhbd.ttc'),
        Path(r'C:\Windows\Fonts\simhei.ttf'),
        Path(r'C:\Windows\Fonts\simsun.ttc'),
    ]
    font_large = font_small = ImageFont.load_default()
    for fp in font_paths:
        if fp.exists():
            try:
                font_large = ImageFont.truetype(str(fp), 48)
                font_small = ImageFont.truetype(str(fp), 30)
                break
            except Exception:
                continue

    line1 = f'镜{int(shot_index):02d}  {title or ""}'.strip()
    line2 = (action or title or '')[:42]

    def _center_text(text: str, y: int, font, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = max(40, (1280 - tw) // 2)
        # background box
        pad = 14
        draw.rectangle(
            [x - pad, y - pad, x + tw + pad, y + (bbox[3] - bbox[1]) + pad],
            fill=(0, 0, 0, 160) if False else (0, 0, 0),
        )
        draw.text((x, y), text, font=font, fill=fill)

    _center_text(line1, 280, font_large, (255, 255, 255))
    _center_text(line2, 380, font_small, (255, 215, 168))
    # bottom narrative cue
    cue = f'Shot {int(shot_index):02d}/12 · Wuxia Short Drama'
    _center_text(cue, 620, font_small, (154, 164, 178))
    img.save(frame_path)

    _run_cmd([
        ffmpeg_binary(), '-y',
        '-loop', '1', '-i', str(frame_path),
        '-t', f'{float(duration_sec):.3f}',
        '-vf', 'fps=24,format=yuv420p',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        str(out),
    ], timeout=120)
    return out


def normalize_clip_to_duration(
    src: str | Path,
    *,
    duration_sec: float = 5.0,
    output_path: Optional[str | Path] = None,
    work_dir: Optional[Path] = None,
) -> Path:
    """Force a clip to exactly duration_sec (loop if short, trim if long)."""
    src_path = Path(src)
    if not src_path.exists():
        raise VideoPostprocessError(f'视频文件不存在: {src}')
    work = work_dir or src_path.parent
    work.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path else (work / f'{src_path.stem}_norm_{int(duration_sec)}s.mp4')
    # Loop input as needed, then hard-cut to target duration; re-encode for concat safety.
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-stream_loop', '-1',
        '-i', str(src_path),
        '-t', f'{float(duration_sec):.3f}',
        '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,'
               'pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-an',
        '-movflags', '+faststart',
        str(out),
    ], timeout=600)
    return out


def pad_concat_to_duration(
    local_paths: Sequence[Path],
    *,
    target_duration_sec: float,
    clip_duration_sec: float = 5.0,
    output_path: Optional[str | Path] = None,
    work_dir: Optional[Path] = None,
    fill_mode: str = 'stretch',
) -> Path:
    """Normalize clips to fill target_duration_sec without repeating the same beat.

    fill_mode:
      - stretch (default): each unique clip lasts target/n seconds (no visual loops)
      - loop: repeat playlist to fill slots (legacy; causes duplicate shots)
      - none: each clip fixed to clip_duration_sec, total may be shorter than target
      - preserve: concatenate existing timings; reject a mismatched total duration
    """
    if not local_paths:
        raise VideoPostprocessError('pad_concat_to_duration 需要至少一个视频')
    work = work_dir or Path(settings.MEDIA_ROOT) / 'workflow_concat' / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)

    n = len(local_paths)
    mode = (fill_mode or 'stretch').strip().lower()
    if mode == 'preserve':
        durations = [probe_media(path)['duration'] for path in local_paths]
        tolerance = 0.05
        if any(value <= 0 for value in durations) or abs(sum(durations) - float(target_duration_sec)) > tolerance:
            raise VideoPostprocessError('保留镜头时长拼接要求各片段总时长等于目标时长')
        result = concat_videos(local_paths, output_path=output_path, work_dir=work)
        if abs(probe_media(result)['duration'] - float(target_duration_sec)) > tolerance:
            raise VideoPostprocessError('拼接结果时长与目标不一致')
        return result
    if mode == 'loop':
        per_clip = float(clip_duration_sec)
        slots = max(1, int(round(float(target_duration_sec) / per_clip)))
    elif mode == 'none':
        per_clip = float(clip_duration_sec)
        slots = n
    else:
        # stretch unique clips evenly across the minute
        per_clip = max(1.0, float(target_duration_sec) / float(n))
        slots = n

    normalized: List[Path] = []
    for idx, path in enumerate(local_paths):
        normalized.append(
            normalize_clip_to_duration(
                path,
                duration_sec=per_clip,
                output_path=work / f'norm_{idx:03d}.mp4',
                work_dir=work,
            )
        )

    if mode == 'loop':
        playlist: List[Path] = []
        while len(playlist) < slots:
            playlist.extend(normalized)
        playlist = playlist[:slots]
    else:
        playlist = normalized

    list_file = work / 'concat_pad.txt'
    with list_file.open('w', encoding='utf-8') as fh:
        for path in playlist:
            escaped = str(path.resolve()).replace("'", r"'\''")
            fh.write(f"file '{escaped}'\n")

    out = Path(output_path) if output_path else (work / 'final_60s.mp4')
    out.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c', 'copy',
        str(out),
    ], timeout=1800)
    return out


def concat_videos(
    video_urls_or_paths: Sequence[str | Path],
    *,
    output_path: Optional[str | Path] = None,
    work_dir: Optional[Path] = None,
    target_duration_sec: Optional[float] = None,
    clip_duration_sec: float = 5.0,
    fill_mode: str = 'stretch',
) -> Path:
    """Concatenate multiple local/remote videos into one mp4 via ffmpeg concat demuxer.

    When target_duration_sec is set (e.g. 60), each clip is normalized to
    clip_duration_sec and the playlist is looped to fill ~1 minute.
    """
    if not video_urls_or_paths:
        raise VideoPostprocessError('concat_videos 需要至少一个视频')

    work = work_dir or Path(settings.MEDIA_ROOT) / 'workflow_concat' / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)

    local_paths: List[Path] = []
    for idx, src in enumerate(video_urls_or_paths):
        src_str = str(src).strip()
        if not src_str:
            continue
        dest = work / f'clip_{idx:03d}.mp4'
        if src_str.startswith('http://') or src_str.startswith('https://'):
            # Prefer httpx; Agnes CDN sometimes trips urllib SSL "key too weak".
            try:
                import httpx
                with httpx.Client(timeout=180, follow_redirects=True, trust_env=False, verify=False) as client:
                    resp = client.get(src_str)
                    resp.raise_for_status()
                    dest.write_bytes(resp.content)
            except Exception:
                import ssl
                import urllib.request
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(src_str, context=ctx, timeout=180) as resp:
                    dest.write_bytes(resp.read())
            local_paths.append(dest)
        else:
            path = Path(src_str)
            if not path.exists():
                raise VideoPostprocessError(f'视频文件不存在: {src_str}')
            local_paths.append(path)

    if not local_paths:
        raise VideoPostprocessError('没有可拼接的有效视频')

    if target_duration_sec and float(target_duration_sec) > 0:
        return pad_concat_to_duration(
            local_paths,
            target_duration_sec=float(target_duration_sec),
            clip_duration_sec=float(clip_duration_sec or 5.0),
            output_path=output_path,
            work_dir=work,
            fill_mode=fill_mode,
        )

    list_file = work / 'concat.txt'
    with list_file.open('w', encoding='utf-8') as fh:
        for path in local_paths:
            escaped = str(path.resolve()).replace("'", r"'\''")
            fh.write(f"file '{escaped}'\n")

    out = Path(output_path) if output_path else (work / 'final_concat.mp4')
    out.parent.mkdir(parents=True, exist_ok=True)
    _run_cmd([
        ffmpeg_binary(), '-y',
        '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c', 'copy',
        str(out),
    ], timeout=1800)
    return out


def is_ffmpeg_available() -> bool:
    return bool(shutil.which(ffmpeg_binary()) and shutil.which(ffprobe_binary()))
