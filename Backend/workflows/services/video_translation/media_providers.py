"""Non-DashScope ASR/TTS providers for video translation pipeline."""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

from workflows.services.media_service import MediaServiceError

logger = logging.getLogger(__name__)

_whisper_model = None


def _whisper_model_size() -> str:
    return getattr(settings, 'WHISPER_MODEL_SIZE', 'base') or 'base'


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise MediaServiceError(
                'local_whisper 需要 faster-whisper。请执行: pip install faster-whisper'
            ) from exc
        device = getattr(settings, 'WHISPER_DEVICE', 'cpu') or 'cpu'
        compute_type = getattr(settings, 'WHISPER_COMPUTE_TYPE', 'int8') or 'int8'
        logger.info('Loading faster-whisper model=%s device=%s', _whisper_model_size(), device)
        _whisper_model = WhisperModel(_whisper_model_size(), device=device, compute_type=compute_type)
    return _whisper_model


def transcribe_local_whisper(
    local_path: Path,
    *,
    language: str = 'zh',
    format: str = 'srt',
) -> Dict[str, Any]:
    """Transcribe audio/video with faster-whisper (local, no API key)."""
    if not local_path.exists():
        raise MediaServiceError(f'媒体文件不存在: {local_path}')

    model = _get_whisper_model()
    lang = None if not language or language in ('auto', '') else language
    segments_iter, info = model.transcribe(str(local_path), language=lang, vad_filter=True)

    segments: List[Dict[str, Any]] = []
    for seg in segments_iter:
        segments.append({
            'start': float(seg.start or 0),
            'end': float(seg.end or 0),
            'text': (seg.text or '').strip(),
        })

    if not segments:
        segments_iter, info = model.transcribe(str(local_path), language=lang, vad_filter=False)
        for seg in segments_iter:
            segments.append({
                'start': float(seg.start or 0),
                'end': float(seg.end or 0),
                'text': (seg.text or '').strip(),
            })

    full_text = ' '.join(s['text'] for s in segments if s['text']).strip()
    if not full_text and not segments:
        duration = float(getattr(info, 'duration', None) or 5.0)
        placeholder = '（未识别到语音内容）'
        segments = [{'start': 0.0, 'end': max(1.0, duration), 'text': placeholder}]
        full_text = placeholder

    if format == 'vtt':
        content = _segments_to_vtt(full_text, segments)
    elif format == 'srt':
        content = _segments_to_srt(full_text, segments)
    else:
        content = full_text

    return {
        'success': True,
        'output': {
            'subtitles': content,
            'format': format,
            'text': full_text,
            'segments': segments,
            'source_segments': segments,
            'provider': 'local_whisper',
            'model': _whisper_model_size(),
        },
    }


def synthesize_edge_tts(
    text: str,
    *,
    voice: str,
    output_path: Path,
) -> Path:
    """Synthesize speech with edge-tts (free Microsoft neural voices)."""
    if not str(text or '').strip():
        raise MediaServiceError('TTS 文本不能为空')
    try:
        import edge_tts
    except ImportError as exc:
        raise MediaServiceError(
            'edge_tts 未安装。请执行: pip install edge-tts'
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))

    asyncio.run(_run())
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise MediaServiceError('edge-tts 未生成有效音频文件')
    return output_path


def synthesize_pyttsx3(
    text: str,
    *,
    output_path: Path,
    voice_id: Optional[str] = None,
    rate: Optional[int] = None,
    language: Optional[str] = None,
) -> Path:
    """Offline TTS via Windows SAPI / espeak (pyttsx3)."""
    if not str(text or '').strip():
        raise MediaServiceError('TTS 文本不能为空')
    try:
        import pyttsx3
    except ImportError as exc:
        raise MediaServiceError('pyttsx3 未安装。请执行: pip install pyttsx3') from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        engine = pyttsx3.init()
        selected = voice_id or (_pick_sapi_voice(engine, language) if language else None)
        if selected:
            try:
                engine.setProperty('voice', selected)
            except Exception:
                logger.warning('Failed to set pyttsx3 voice=%s', selected)
        if rate:
            engine.setProperty('rate', int(rate))
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
    except Exception as exc:
        logger.warning('pyttsx3 synthesis failed lang=%s: %s', language, exc)
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass

    if output_path.exists() and output_path.stat().st_size >= 500:
        return output_path

    # No matching language voice / synthesis failed — emit silent WAV so pipeline continues
    duration = max(0.5, min(8.0, len(str(text)) / 6.0))
    logger.warning(
        'pyttsx3 empty audio for lang=%s text_len=%s; using silent placeholder (%.1fs)',
        language, len(str(text)), duration,
    )
    from workflows.services.video_postprocess import create_silent_audio
    fmt = 'wav' if output_path.suffix.lower() == '.wav' else 'mp3'
    create_silent_audio(duration, output_path, fmt=fmt)
    if not output_path.exists() or output_path.stat().st_size < 100:
        raise MediaServiceError(
            f'pyttsx3 无法为语言 {language or "?"} 生成音频，且静音占位失败。'
            f'请安装 Windows 对应语言语音包。'
        )
    return output_path


def _pick_sapi_voice(engine, language: str) -> Optional[str]:
    """Pick a SAPI voice matching language code (zh/en/ja/ko...)."""
    lang = (language or '').lower().split('-')[0]
    aliases = {
        'zh': ('zh', 'chinese', 'huihui'),
        'en': ('en', 'english', 'zira', 'david'),
        'ja': ('ja', 'jp', 'japanese'),
        'ko': ('ko', 'kr', 'korean'),
    }
    needles = aliases.get(lang, (lang,))
    try:
        voices = engine.getProperty('voices') or []
    except Exception:
        return None
    for voice in voices:
        blob = ' '.join([
            str(getattr(voice, 'id', '') or ''),
            str(getattr(voice, 'name', '') or ''),
            ' '.join(str(x) for x in (getattr(voice, 'languages', None) or [])),
        ]).lower()
        if any(n in blob for n in needles):
            return voice.id
    return None


def synthesize_pyttsx3_to_work_dir(
    text: str,
    *,
    voice_id: Optional[str] = None,
    work_dir: Path,
    fmt: str = 'wav',
) -> Path:
    ext = fmt if fmt.startswith('.') else f'.{fmt}'
    dest = work_dir / f'pyttsx3_{uuid.uuid4().hex}{ext}'
    return synthesize_pyttsx3(text, output_path=dest, voice_id=voice_id)

def synthesize_edge_tts_to_work_dir(
    text: str,
    *,
    voice: str,
    work_dir: Path,
    fmt: str = 'mp3',
) -> Path:
    ext = fmt if fmt.startswith('.') else f'.{fmt}'
    dest = work_dir / f'edge_{uuid.uuid4().hex}{ext}'
    return synthesize_edge_tts(text, voice=voice, output_path=dest)


def _seconds_to_srt_time(seconds: float) -> str:
    import datetime
    td = datetime.timedelta(seconds=max(0.0, float(seconds)))
    h = td.seconds // 3600
    m = (td.seconds % 3600) // 60
    s = td.seconds % 60
    ms = td.microseconds // 1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def _seconds_to_vtt_time(seconds: float) -> str:
    import datetime
    td = datetime.timedelta(seconds=max(0.0, float(seconds)))
    h = td.seconds // 3600
    m = (td.seconds % 3600) // 60
    s = td.seconds % 60
    ms = td.microseconds // 1000
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'


def _segments_to_srt(text: str, segments: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, seg in enumerate(segments or [], 1):
        start = _seconds_to_srt_time(seg.get('start', 0))
        end = _seconds_to_srt_time(seg.get('end', 0))
        body = str(seg.get('text', '')).strip()
        if body:
            lines.append(f'{i}\n{start} --> {end}\n{body}\n')
    if not lines:
        lines.append(f'1\n00:00:00,000 --> 00:00:05,000\n{text}\n')
    return '\n'.join(lines)


def _segments_to_vtt(text: str, segments: List[Dict[str, Any]]) -> str:
    lines = ['WEBVTT\n']
    for seg in segments or []:
        start = _seconds_to_vtt_time(seg.get('start', 0))
        end = _seconds_to_vtt_time(seg.get('end', 0))
        body = str(seg.get('text', '')).strip()
        if body:
            lines.append(f'{start} --> {end}\n{body}\n')
    if len(lines) == 1:
        lines.append(f'00:00:00.000 --> 00:00:05.000\n{text}\n')
    return '\n'.join(lines)
