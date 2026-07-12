"""End-to-end video translation orchestration."""
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
from workflows.services.video_translation.constants import DASHSCOPE_TTS_VOICES
from workflows.services.video_translation.segment_pipeline import (
    build_subtitle_file,
    persist_subtitle_artifact,
    synthesize_segment_tts,
    translate_segments,
)
from workflows.services.video_translation.video_retalk_client import VideoRetalkError, submit_videoretalk_task

logger = logging.getLogger(__name__)


class VideoTranslationPipeline:
    """Orchestrates ASR → translate → TTS → lip sync → subtitle burn-in."""

    def __init__(
        self,
        *,
        asr_call: Callable[[str, str], Dict[str, Any]],
        llm_call: Callable[[str], str],
        tts_call: Callable[[str, str, str], str],
        dashscope_credential: Callable[[], tuple],
        poll_dashscope_task: Callable[..., Dict[str, Any]],
        progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        render_template: Optional[Callable[[str, Dict[str, Any]], str]] = None,
    ):
        self.asr_call = asr_call
        self.llm_call = llm_call
        self.tts_call = tts_call
        self.dashscope_credential = dashscope_credential
        self.poll_dashscope_task = poll_dashscope_task
        self.progress = progress or (lambda step, meta: None)
        self.render_template = render_template

    def _report(self, step: str, **meta: Any) -> None:
        self.progress(step, meta)

    def run(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not is_ffmpeg_available():
            return {
                'success': False,
                'error': '服务器未安装 FFmpeg。请安装 FFmpeg 并配置 FFMPEG_BINARY 环境变量。',
            }

        try:
            video_public_url, local_video = self._resolve_video_input(node_config, context)
            max_duration = int(getattr(settings, 'VIDEO_TRANSLATION_MAX_DURATION_SEC', 300))
            probe = probe_media(local_video)
            duration = float(probe.get('duration') or 0)
            if duration > max_duration:
                return {
                    'success': False,
                    'error': f'视频时长 {duration:.1f}s 超过上限 {max_duration}s',
                }

            source_lang = node_config.get('source_language') or node_config.get('sourceLanguage') or 'zh'
            target_langs = self._normalize_target_languages(node_config)
            subtitle_format = (node_config.get('subtitle_format') or node_config.get('subtitleFormat') or 'srt').lower()
            burn_subs = node_config.get('burn_subtitles', node_config.get('burnSubtitles', True))
            lip_sync = node_config.get('lip_sync', node_config.get('lipSync', True))
            voice = node_config.get('voice') or ''
            ref_face = node_config.get('face_ref_image_url') or node_config.get('faceRefImageUrl') or ''
            video_extension = bool(node_config.get('video_extension', node_config.get('videoExtension', False)))

            self._report('transcribe', status='running', video_url=video_public_url)
            asr_result = self.asr_call(video_public_url, source_lang)
            if not asr_result.get('success'):
                return asr_result
            asr_output = asr_result.get('output') or {}
            source_segments = asr_output.get('segments') or []
            if not source_segments and asr_output.get('text'):
                source_segments = [{'start': 0, 'end': min(duration, 5), 'text': asr_output.get('text', '')}]

            self._report('transcribe', status='completed', segment_count=len(source_segments))

            results: List[Dict[str, Any]] = []
            work_dir = Path(settings.MEDIA_ROOT) / 'video_translation' / 'work' / uuid.uuid4().hex
            work_dir.mkdir(parents=True, exist_ok=True)

            for target_lang in target_langs:
                lang_result = self._process_language(
                    video_public_url=video_public_url,
                    local_video=local_video,
                    source_segments=source_segments,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    subtitle_format=subtitle_format,
                    burn_subs=burn_subs,
                    lip_sync=lip_sync,
                    voice=voice,
                    ref_face=ref_face,
                    video_extension=video_extension,
                    total_duration=duration,
                    work_dir=work_dir,
                )
                results.append(lang_result)

            return {
                'success': True,
                'output': {
                    'results': results,
                    'source_segments': source_segments,
                    'source_video_url': video_public_url,
                    'provider': node_config.get('provider', 'dashscope'),
                },
            }
        except (MediaServiceError, VideoPostprocessError, VideoRetalkError) as exc:
            logger.exception('Video translation pipeline failed')
            return {'success': False, 'error': str(exc)}
        except Exception as exc:
            logger.exception('Video translation pipeline unexpected error')
            return {'success': False, 'error': str(exc)}

    def _process_language(
        self,
        *,
        video_public_url: str,
        local_video: Path,
        source_segments: Sequence[Dict[str, Any]],
        source_lang: str,
        target_lang: str,
        subtitle_format: str,
        burn_subs: bool,
        lip_sync: bool,
        voice: str,
        ref_face: str,
        video_extension: bool,
        total_duration: float,
        work_dir: Path,
    ) -> Dict[str, Any]:
        self._report('translate', status='running', target_language=target_lang)
        translated = translate_segments(
            source_segments,
            source_lang=source_lang,
            target_lang=target_lang,
            llm_call=self.llm_call,
        )
        self._report('translate', status='completed', target_language=target_lang)

        subtitle_srt = build_subtitle_file(translated, 'srt')
        subtitle_vtt = build_subtitle_file(translated, 'vtt') if subtitle_format in ('vtt', 'both') else ''
        subtitle_main = subtitle_vtt if subtitle_format == 'vtt' else subtitle_srt

        self._report('synthesize', status='running', target_language=target_lang)
        seg_audio_paths = synthesize_segment_tts(
            translated,
            voice=voice or DASHSCOPE_TTS_VOICES.get(target_lang),
            target_lang=target_lang,
            tts_call=self.tts_call,
            work_dir=work_dir / f'tts_{target_lang}',
        )
        dubbed_audio = concat_segment_audio(
            translated,
            seg_audio_paths,
            total_duration=total_duration,
            work_dir=work_dir / f'concat_{target_lang}',
        )
        dubbed_meta = save_output_file(dubbed_audio, subdir='video_translation/audio')
        dubbed_public = dubbed_meta['public_url']
        self._report('synthesize', status='completed', target_language=target_lang, audio_url=dubbed_public)

        lip_sync_applied = False
        working_video = local_video
        final_public_url = video_public_url

        if lip_sync:
            self._report('lip_sync', status='running', target_language=target_lang)
            try:
                api_key, base_url = self.dashscope_credential()
                retalk = submit_videoretalk_task(
                    video_url=video_public_url,
                    audio_url=dubbed_public,
                    api_key=api_key,
                    base_url=base_url,
                    ref_image_url=ref_face,
                    video_extension=video_extension,
                    poll_task=self.poll_dashscope_task,
                    timeout_seconds=900,
                )
                retalk_url = retalk['video_url']
                working_video = resolve_local_media_path(retalk_url, subdir='video_translation/retalk')
                lip_sync_applied = True
                self._report('lip_sync', status='completed', target_language=target_lang, video_url=retalk_url)
            except VideoRetalkError as exc:
                logger.warning('VideoRetalk failed, falling back to mux: %s', exc)
                self._report('lip_sync', status='degraded', target_language=target_lang, error=str(exc))
                muxed = mux_audio_video(local_video, dubbed_audio, output_path=work_dir / f'mux_{target_lang}.mp4')
                working_video = muxed
        else:
            muxed = mux_audio_video(local_video, dubbed_audio, output_path=work_dir / f'mux_{target_lang}.mp4')
            working_video = muxed

        if burn_subs and subtitle_main:
            self._report('burn_subtitles', status='running', target_language=target_lang)
            subs_path = write_subtitle_file(subtitle_main, fmt='vtt' if subtitle_format == 'vtt' else 'srt', work_dir=work_dir)
            final_local = burn_subtitles(working_video, subs_path, output_path=work_dir / f'final_{target_lang}.mp4')
            self._report('burn_subtitles', status='completed', target_language=target_lang)
        else:
            final_local = working_video

        final_meta = save_output_file(final_local, subdir='video_translation/output')
        final_public_url = final_meta['public_url']

        sub_artifact = persist_subtitle_artifact(subtitle_srt, 'srt')
        sub_vtt_artifact = persist_subtitle_artifact(subtitle_vtt, 'vtt') if subtitle_vtt else None

        return {
            'target_language': target_lang,
            'video_url': final_public_url,
            'dubbed_audio_url': dubbed_public,
            'subtitles': subtitle_srt,
            'subtitles_vtt': subtitle_vtt or None,
            'subtitle_url': sub_artifact.get('public_url'),
            'subtitle_vtt_url': (sub_vtt_artifact or {}).get('public_url'),
            'segments': translated,
            'lip_sync_applied': lip_sync_applied,
            'burn_subtitles_applied': bool(burn_subs and subtitle_main),
        }

    def _resolve_video_input(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> tuple:
        self._report('resolve_input', status='running')
        raw = (
            node_config.get('video_input')
            or node_config.get('videoInput')
            or node_config.get('inputPath')
            or node_config.get('input')
            or context.get('video_input')
            or context.get('video_url')
            or context.get('video')
            or ''
        )
        if isinstance(raw, dict):
            raw = raw.get('video_url') or raw.get('url') or raw.get('public_url') or ''

        media_id = node_config.get('media_id') or node_config.get('mediaId') or context.get('media_id')
        if media_id and not str(raw).strip():
            meta = resolve_media_id(str(media_id))
            if meta:
                raw = meta['public_url']

        if not str(raw).strip():
            raise MediaServiceError('请提供 video_input、media_id 或上游 video_url')

        template = str(raw).strip()
        if '{' in template and '}' in template and self.render_template:
            template = self.render_template(template, context)

        public_url = ensure_public_url(template)
        local = resolve_local_media_path(public_url)
        self._report('resolve_input', status='completed', video_url=public_url)
        return public_url, local

    @staticmethod
    def _normalize_target_languages(node_config: Dict[str, Any]) -> List[str]:
        langs = (
            node_config.get('target_languages')
            or node_config.get('targetLanguages')
            or node_config.get('target_language')
            or node_config.get('targetLanguage')
            or ['en']
        )
        if isinstance(langs, str):
            langs = [x.strip() for x in langs.split(',') if x.strip()]
        return [str(x) for x in langs if x]
