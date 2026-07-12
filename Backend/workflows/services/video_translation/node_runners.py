"""Standalone node runners for split video localization pipeline."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from django.conf import settings

from workflows.services.media_service import (
    MediaServiceError,
    ensure_public_url,
    resolve_local_media_path,
    resolve_media_id,
    save_output_file,
)
from workflows.services.video_postprocess import (
    VideoPostprocessError,
    burn_subtitles,
    concat_segment_audio,
    is_ffmpeg_available,
    mux_audio_video,
    probe_media,
    write_subtitle_file,
)
from workflows.services.video_translation.constants import (
    DASHSCOPE_TTS_VOICES,
    EDGE_TTS_VOICES,
    OPENAI_TTS_VOICES,
)
from workflows.services.video_translation.segment_pipeline import (
    build_subtitle_file,
    persist_subtitle_artifact,
    synthesize_segment_tts,
    translate_segments,
)
from workflows.services.video_translation.video_retalk_client import VideoRetalkError, submit_videoretalk_task

logger = logging.getLogger(__name__)


def _cfg(node_config: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in node_config and node_config[key] not in (None, ''):
            return node_config[key]
    return default


def _ctx(context: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        val = context.get(key)
        if val not in (None, ''):
            return val
    node_outputs = context.get('node_outputs') or {}
    if isinstance(node_outputs, dict):
        for output in reversed(list(node_outputs.values())):
            if not isinstance(output, dict):
                continue
            for key in keys:
                if key in output and output[key] not in (None, ''):
                    return output[key]
    return default


def _render(value: Any, render_template: Optional[Callable[[str, Dict[str, Any]], str]], context: Dict[str, Any]) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    if '{' in text and '}' in text and render_template:
        return render_template(text, context).strip()
    return text


def run_video_upload(
    node_config: Dict[str, Any],
    context: Dict[str, Any],
    *,
    render_template: Optional[Callable[[str, Dict[str, Any]], str]] = None,
) -> Dict[str, Any]:
    """Resolve uploaded or URL video to a public URL with metadata."""
    raw = _cfg(
        node_config,
        'video_url', 'videoUrl', 'video_input', 'videoInput', 'public_url', 'publicUrl',
    ) or _ctx(context, 'video_url', 'video_input', 'public_url')
    media_id = _cfg(node_config, 'media_id', 'mediaId') or _ctx(context, 'media_id')

    if media_id and not str(raw).strip():
        meta = resolve_media_id(str(media_id))
        if meta:
            raw = meta['public_url']

    if not str(raw).strip():
        raise MediaServiceError('请上传视频或填写公网视频 URL')

    template = _render(raw, render_template, context)
    public_url = ensure_public_url(template)
    local = resolve_local_media_path(public_url)
    probe = probe_media(local)
    duration = float(probe.get('duration') or 0)
    max_duration = int(getattr(settings, 'VIDEO_TRANSLATION_MAX_DURATION_SEC', 300))
    if duration > max_duration:
        raise MediaServiceError(f'视频时长 {duration:.1f}s 超过上限 {max_duration}s')

    return {
        'success': True,
        'output': {
            'video_url': public_url,
            'source_video_url': public_url,
            'media_id': media_id or '',
            'duration': duration,
            'has_audio': bool(probe.get('has_audio')),
        },
    }


def run_subtitle_translate(
    node_config: Dict[str, Any],
    context: Dict[str, Any],
    *,
    llm_call: Callable[[str], str],
    render_template: Optional[Callable[[str, Dict[str, Any]], str]] = None,
) -> Dict[str, Any]:
    """Translate ASR segments to a single target language."""
    segments = _cfg(node_config, 'segments', 'source_segments') or _ctx(
        context, 'source_segments', 'segments'
    )
    if isinstance(segments, str):
        raise MediaServiceError('segments 必须是上游 ASR 输出的数组')

    source_lang = _cfg(node_config, 'source_language', 'sourceLanguage') or _ctx(context, 'source_language') or 'zh'
    target_lang = _cfg(node_config, 'target_language', 'targetLanguage', 'target_lang') or 'en'
    target_lang = str(target_lang).strip().lower()

    translated = translate_segments(
        segments or [],
        source_lang=source_lang,
        target_lang=target_lang,
        llm_call=llm_call,
    )
    subtitle_format = (_cfg(node_config, 'subtitle_format', 'subtitleFormat') or 'srt').lower()
    subtitle_srt = build_subtitle_file(translated, 'srt')
    subtitle_vtt = build_subtitle_file(translated, 'vtt') if subtitle_format in ('vtt', 'both') else ''

    source_video_url = _ctx(context, 'source_video_url', 'video_url')
    return {
        'success': True,
        'output': {
            'segments': translated,
            'source_segments': segments,
            'subtitles': subtitle_vtt if subtitle_format == 'vtt' else subtitle_srt,
            'subtitles_srt': subtitle_srt,
            'subtitles_vtt': subtitle_vtt or None,
            'target_language': target_lang,
            'source_language': source_lang,
            'source_video_url': source_video_url,
            'video_url': source_video_url,
        },
    }


def run_segment_dubbing(
    node_config: Dict[str, Any],
    context: Dict[str, Any],
    *,
    tts_call: Callable[[str, str, str], str],
) -> Dict[str, Any]:
    """Synthesize per-segment TTS and concat dubbed audio track."""
    if not is_ffmpeg_available():
        raise VideoPostprocessError('服务器未安装 FFmpeg')

    segments = _cfg(node_config, 'segments') or _ctx(context, 'segments')
    if not segments:
        raise MediaServiceError('缺少上游 segments，请先连接字幕翻译或 ASR 节点')

    target_lang = _cfg(node_config, 'target_language', 'targetLanguage') or _ctx(context, 'target_language') or 'en'
    provider = (_cfg(node_config, 'provider', 'tts_provider', 'ttsProvider') or 'pyttsx3').strip().lower()
    voice = _cfg(node_config, 'voice') or ''
    if not voice:
        if provider == 'edge_tts':
            voice = EDGE_TTS_VOICES.get(str(target_lang), 'en-US-JennyNeural')
        elif provider == 'openai':
            voice = OPENAI_TTS_VOICES.get(str(target_lang), 'alloy')
        elif provider == 'dashscope':
            voice = DASHSCOPE_TTS_VOICES.get(str(target_lang), 'longanyang')
    total_duration = float(
        _cfg(node_config, 'duration', 'total_duration')
        or _ctx(context, 'duration', 'total_duration')
        or 0
    )
    if not total_duration and segments:
        total_duration = max(float(s.get('end') or 0) for s in segments)

    work_dir = Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)

    seg_paths = synthesize_segment_tts(
        segments,
        voice=voice,
        target_lang=str(target_lang),
        tts_call=tts_call,
        work_dir=work_dir / 'tts',
    )
    dubbed_local = concat_segment_audio(
        segments,
        seg_paths,
        total_duration=total_duration,
        work_dir=work_dir / 'concat',
    )
    dubbed_meta = save_output_file(dubbed_local, subdir='video_translation/audio')

    source_video_url = _ctx(context, 'source_video_url', 'video_url')
    return {
        'success': True,
        'output': {
            'dubbed_audio_url': dubbed_meta['public_url'],
            'segments': segments,
            'target_language': target_lang,
            'voice': voice,
            'source_video_url': source_video_url,
            'video_url': source_video_url,
            'duration': total_duration,
        },
    }


def run_lip_sync(
    node_config: Dict[str, Any],
    context: Dict[str, Any],
    *,
    dashscope_credential: Callable[[], tuple],
    poll_dashscope_task: Callable[..., Dict[str, Any]],
    render_template: Optional[Callable[[str, Dict[str, Any]], str]] = None,
) -> Dict[str, Any]:
    """Apply lip sync when provider=dashscope; otherwise FFmpeg audio mux."""
    if not is_ffmpeg_available():
        raise VideoPostprocessError('服务器未安装 FFmpeg')

    video_ref = _cfg(
        node_config, 'video_input', 'videoInput', 'video_url', 'source_video_url',
    ) or _ctx(context, 'source_video_url', 'video_url')
    video_ref = _render(video_ref, render_template, context) or _ctx(context, 'source_video_url', 'video_url')

    audio_ref = _cfg(
        node_config, 'audio_input', 'audioInput', 'dubbed_audio_url', 'audio_url',
    ) or _ctx(context, 'dubbed_audio_url', 'audio_url')
    audio_ref = _render(audio_ref, render_template, context) or _ctx(context, 'dubbed_audio_url')

    if not video_ref:
        raise MediaServiceError('缺少源视频 URL')
    if not audio_ref:
        raise MediaServiceError('缺少配音音频 URL')

    video_public = ensure_public_url(video_ref)
    audio_public = ensure_public_url(audio_ref)
    local_video = resolve_local_media_path(video_public)
    local_audio = resolve_local_media_path(audio_public)

    lip_sync_enabled = bool(_cfg(node_config, 'lip_sync', 'lipSync', default=True))
    lip_provider = (
        _cfg(node_config, 'provider', 'lip_sync_provider', 'lipSyncProvider')
        or getattr(settings, 'VIDEO_TRANSLATION_LIP_SYNC_PROVIDER', 'ffmpeg')
        or 'ffmpeg'
    ).strip().lower()
    use_videoretalk = lip_sync_enabled and lip_provider == 'dashscope'
    ref_face = _cfg(node_config, 'face_ref_image_url', 'faceRefImageUrl') or ''
    video_extension = bool(_cfg(node_config, 'video_extension', 'videoExtension', default=False))
    target_lang = _cfg(node_config, 'target_language', 'targetLanguage') or _ctx(context, 'target_language') or ''

    lip_sync_applied = False
    working_video = local_video

    if use_videoretalk:
        try:
            api_key, base_url = dashscope_credential()
            retalk = submit_videoretalk_task(
                video_url=video_public,
                audio_url=audio_public,
                api_key=api_key,
                base_url=base_url,
                ref_image_url=ref_face,
                video_extension=video_extension,
                poll_task=poll_dashscope_task,
                timeout_seconds=900,
            )
            working_video = resolve_local_media_path(retalk['video_url'], subdir='video_translation/retalk')
            lip_sync_applied = True
        except VideoRetalkError as exc:
            logger.warning('VideoRetalk failed, mux fallback: %s', exc)
            work_dir = Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
            work_dir.mkdir(parents=True, exist_ok=True)
            working_video = mux_audio_video(
                local_video, local_audio, output_path=work_dir / f'mux_{target_lang or "out"}.mp4'
            )
    else:
        work_dir = Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
        work_dir.mkdir(parents=True, exist_ok=True)
        working_video = mux_audio_video(
            local_video, local_audio, output_path=work_dir / f'mux_{target_lang or "out"}.mp4'
        )

    saved = save_output_file(working_video, subdir='video_translation/lipsync')
    lang_suffix = f'_{target_lang}' if target_lang else ''
    output_key = f'video_url{lang_suffix}'

    output = {
        'video_url': saved['public_url'],
        output_key: saved['public_url'],
        'lip_sync_applied': lip_sync_applied,
        'target_language': target_lang,
        'source_video_url': video_public,
        'dubbed_audio_url': audio_public,
    }
    return {'success': True, 'output': output}


def run_subtitle_burn(
    node_config: Dict[str, Any],
    context: Dict[str, Any],
    *,
    render_template: Optional[Callable[[str, Dict[str, Any]], str]] = None,
) -> Dict[str, Any]:
    """Burn subtitles into video via FFmpeg."""
    if not is_ffmpeg_available():
        raise VideoPostprocessError('服务器未安装 FFmpeg')

    video_ref = _cfg(node_config, 'video_input', 'videoInput', 'video_url') or _ctx(context, 'video_url')
    video_ref = _render(video_ref, render_template, context) or _ctx(context, 'video_url')
    if not video_ref:
        raise MediaServiceError('缺少待烧录视频 URL')

    segments = _cfg(node_config, 'segments') or _ctx(context, 'segments')
    subtitles = _cfg(node_config, 'subtitles') or _ctx(context, 'subtitles', 'subtitles_srt')
    subtitle_format = (_cfg(node_config, 'subtitle_format', 'subtitleFormat') or 'srt').lower()
    target_lang = _cfg(node_config, 'target_language', 'targetLanguage') or _ctx(context, 'target_language') or ''

    if not subtitles and segments:
        subtitles = build_subtitle_file(segments, 'vtt' if subtitle_format == 'vtt' else 'srt')

    local_video = resolve_local_media_path(ensure_public_url(video_ref))
    work_dir = Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)

    if subtitles:
        subs_path = write_subtitle_file(
            subtitles,
            fmt='vtt' if subtitle_format == 'vtt' else 'srt',
            work_dir=work_dir,
        )
        final_local = burn_subtitles(
            local_video,
            subs_path,
            output_path=work_dir / f'final_{target_lang or "out"}.mp4',
        )
    else:
        final_local = local_video

    saved = save_output_file(final_local, subdir='video_translation/output')
    sub_artifact = persist_subtitle_artifact(subtitles, subtitle_format) if subtitles else None
    lang_suffix = f'_{target_lang}' if target_lang else ''
    output_key = f'video_url{lang_suffix}'

    output = {
        'video_url': saved['public_url'],
        output_key: saved['public_url'],
        'target_language': target_lang,
        'subtitle_url': (sub_artifact or {}).get('public_url'),
        'subtitles': subtitles,
        'burn_subtitles_applied': bool(subtitles),
    }
    return {'success': True, 'output': output}
