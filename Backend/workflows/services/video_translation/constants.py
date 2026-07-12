"""Constants for video translation workflow."""

VIDEO_TRANSLATION_LANGUAGES = {
    'zh': '中文',
    'en': 'English',
    'ja': '日本語',
    'ko': '한국어',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'ru': 'Русский',
    'pt': 'Português',
    'ar': 'العربية',
}

VIDEO_TRANSLATION_LANGUAGE_CHOICES = list(VIDEO_TRANSLATION_LANGUAGES.keys())

DASHSCOPE_TTS_VOICES = {
    'zh': 'longanyang',
    'en': 'longxiaochun',
    'ja': 'longlaotie',
    'ko': 'longxiaochun',
    'es': 'longxiaochun',
    'fr': 'longxiaochun',
    'de': 'longxiaochun',
    'ru': 'longxiaochun',
    'pt': 'longxiaochun',
    'ar': 'longxiaochun',
}

OPENAI_TTS_VOICES = {
    'zh': 'alloy',
    'en': 'alloy',
    'ja': 'nova',
    'ko': 'nova',
    'es': 'nova',
    'fr': 'nova',
    'de': 'nova',
    'ru': 'nova',
    'pt': 'nova',
    'ar': 'nova',
}

EDGE_TTS_VOICES = {
    'zh': 'zh-CN-XiaoxiaoNeural',
    'en': 'en-US-JennyNeural',
    'ja': 'ja-JP-NanamiNeural',
    'ko': 'ko-KR-SunHiNeural',
    'es': 'es-ES-ElviraNeural',
    'fr': 'fr-FR-DeniseNeural',
    'de': 'de-DE-KatjaNeural',
    'ru': 'ru-RU-SvetlanaNeural',
    'pt': 'pt-BR-FranciscaNeural',
    'ar': 'ar-SA-ZariyahNeural',
}

GTTS_LANG_CODES = {
    'zh': 'zh-cn',
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'es': 'es',
    'fr': 'fr',
    'de': 'de',
    'ru': 'ru',
    'pt': 'pt',
    'ar': 'ar',
}

DEFAULT_ASR_PROVIDER = 'local_whisper'
DEFAULT_TTS_PROVIDER = 'pyttsx3'
DEFAULT_LIP_SYNC_PROVIDER = 'ffmpeg'

PIPELINE_STEPS = (
    'resolve_input',
    'transcribe',
    'translate',
    'synthesize',
    'lip_sync',
    'burn_subtitles',
    'finalize',
)
