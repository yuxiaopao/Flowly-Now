"""Segment-level translation and TTS for video translation."""
from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import httpx
from django.conf import settings

from workflows.services.media_service import download_url_to_media, save_output_file
from workflows.services.video_postprocess import adjust_audio_duration, probe_media
from workflows.services.video_translation.constants import DASHSCOPE_TTS_VOICES

logger = logging.getLogger(__name__)


class SegmentPipelineError(Exception):
    pass


def build_subtitle_file(segments: Sequence[Dict[str, Any]], fmt: str = 'srt') -> str:
    """Build SRT or VTT from segment list."""
    if fmt == 'vtt':
        return _segments_to_vtt(segments)
    return _segments_to_srt(segments)


def _seconds_to_srt_time(seconds: float) -> str:
    import datetime
    td = datetime.timedelta(seconds=max(float(seconds or 0), 0))
    h = td.seconds // 3600
    m = (td.seconds % 3600) // 60
    s = td.seconds % 60
    ms = td.microseconds // 1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def _seconds_to_vtt_time(seconds: float) -> str:
    import datetime
    td = datetime.timedelta(seconds=max(float(seconds or 0), 0))
    h = td.seconds // 3600
    m = (td.seconds % 3600) // 60
    s = td.seconds % 60
    ms = td.microseconds // 1000
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'


def _segments_to_srt(segments: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, seg in enumerate(segments, 1):
        text = str(seg.get('translated_text') or seg.get('text') or '').strip()
        if not text:
            continue
        start = _seconds_to_srt_time(seg.get('start', 0))
        end = _seconds_to_srt_time(seg.get('end', 0))
        lines.append(f'{i}\n{start} --> {end}\n{text}\n')
    return '\n'.join(lines) if lines else '1\n00:00:00,000 --> 00:00:01,000\n \n'


def _segments_to_vtt(segments: Sequence[Dict[str, Any]]) -> str:
    lines = ['WEBVTT\n']
    for seg in segments:
        text = str(seg.get('translated_text') or seg.get('text') or '').strip()
        if not text:
            continue
        start = _seconds_to_vtt_time(seg.get('start', 0))
        end = _seconds_to_vtt_time(seg.get('end', 0))
        lines.append(f'{start} --> {end}\n{text}\n')
    if len(lines) == 1:
        lines.append('00:00:00.000 --> 00:00:01.000\n \n')
    return '\n'.join(lines)


def translate_segments(
    segments: Sequence[Dict[str, Any]],
    *,
    source_lang: str,
    target_lang: str,
    llm_call: Callable[[str], str],
) -> List[Dict[str, Any]]:
    """Translate subtitle segments while preserving timestamps."""
    if not segments:
        return []

    payload = [
        {'index': i, 'text': str(seg.get('text') or '').strip()}
        for i, seg in enumerate(segments)
        if str(seg.get('text') or '').strip()
    ]
    if not payload:
        return [dict(seg) for seg in segments]

    src_label = source_lang or 'auto'
    tgt_label = target_lang or 'en'
    prompt = (
        f'You are a professional subtitle translator. Translate the following subtitle segments '
        f'from {src_label} to {tgt_label}. Preserve meaning, tone, and brevity suitable for on-screen subtitles. '
        f'Return ONLY valid JSON array: [{{"index": 0, "translated_text": "..."}}].\n\n'
        f'Segments:\n{json.dumps(payload, ensure_ascii=False, indent=2)}'
    )
    raw = llm_call(prompt)
    translated_map = _parse_translation_json(raw)

    result: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments):
        item = dict(seg)
        item['source_text'] = seg.get('text', '')
        item['translated_text'] = translated_map.get(i, seg.get('text', ''))
        item['target_language'] = target_lang
        result.append(item)
    return result


def _parse_translation_json(raw: str) -> Dict[int, str]:
    text = (raw or '').strip()
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning('Failed to parse translation JSON, falling back to original text')
        return {}

    mapping: Dict[int, str] = {}
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            idx = row.get('index')
            val = row.get('translated_text') or row.get('text')
            if idx is not None and val is not None:
                mapping[int(idx)] = str(val).strip()
    return mapping


def synthesize_segment_tts(
    segments: Sequence[Dict[str, Any]],
    *,
    voice: Optional[str] = None,
    target_lang: str = 'en',
    tts_call: Callable[[str, str, str], str],
    work_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Synthesize TTS for each translated segment.
    tts_call(text, voice, fmt) -> local audio path or public URL.
    Returns list of local audio paths aligned with segments.
    """
    work = work_dir or Path(settings.MEDIA_ROOT) / 'video_translation' / 'tts' / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)
    selected_voice = voice or DASHSCOPE_TTS_VOICES.get(target_lang, 'longanyang')

    paths: List[Path] = []
    for i, seg in enumerate(segments):
        text = str(seg.get('translated_text') or seg.get('text') or '').strip()
        if not text:
            silent = work / f'silent_{i}.mp3'
            start = float(seg.get('start') or 0)
            end = float(seg.get('end') or start)
            dur = max(end - start, 0.1)
            from workflows.services.video_postprocess import create_silent_audio
            create_silent_audio(dur, silent)
            paths.append(silent)
            continue

        audio_ref = tts_call(text, selected_voice, 'mp3')
        if str(audio_ref).lower().startswith(('http://', 'https://')):
            local = download_url_to_media(audio_ref, subdir=f'video_translation/tts/{uuid.uuid4().hex}')
        else:
            local = Path(audio_ref)
        start = float(seg.get('start') or 0)
        end = float(seg.get('end') or start)
        target = max(end - start, 0.1)
        aligned = work / f'seg_{i}_aligned.mp3'
        adjust_audio_duration(local, target, output_path=aligned)
        paths.append(aligned)
    return paths


def persist_subtitle_artifact(content: str, fmt: str) -> dict:
    work = Path(settings.MEDIA_ROOT) / 'video_translation' / 'subtitles'
    work.mkdir(parents=True, exist_ok=True)
    ext = 'vtt' if fmt == 'vtt' else 'srt'
    path = work / f'{uuid.uuid4().hex}.{ext}'
    path.write_text(content, encoding='utf-8')
    return save_output_file(path, subdir='video_translation/subtitles')
