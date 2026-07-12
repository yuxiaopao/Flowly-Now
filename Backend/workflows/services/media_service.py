"""Media upload and public URL helpers for multimodal / video translation workflows."""
from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpeg', '.mpg', '.m4v'}
ALLOWED_VIDEO_MIME_PREFIXES = ('video/',)


class MediaServiceError(Exception):
    """Raised when media upload or URL resolution fails."""


def get_media_public_base_url() -> str:
    base = (
        getattr(settings, 'MEDIA_PUBLIC_BASE_URL', '')
        or getattr(settings, 'PUBLIC_API_BASE_URL', '')
        or 'http://127.0.0.1:8000'
    )
    return str(base).rstrip('/')


def build_public_media_url(relative_path: str) -> str:
    """Build a publicly reachable URL for a file under MEDIA_ROOT."""
    rel = str(relative_path).replace('\\', '/').lstrip('/')
    media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
    if not media_url.startswith('/'):
        media_url = f'/{media_url}'
    return f"{get_media_public_base_url()}{media_url}/{rel}"


def local_path_from_public_url(url: str) -> Optional[Path]:
    """Map a public media URL back to a local MEDIA_ROOT path when possible."""
    if not url:
        return None
    parsed = urlparse(url)
    media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
    path = parsed.path or ''
    prefix = media_url if media_url.startswith('/') else f'/{media_url}'
    if prefix in path:
        rel = path.split(prefix, 1)[-1].lstrip('/')
        if rel:
            return Path(settings.MEDIA_ROOT) / rel
    return None


def ensure_public_url(path_or_url: str, *, download_dir: Optional[Path] = None) -> str:
    """
    Return a public HTTP(S) URL.
    - http(s) URLs pass through unchanged.
    - Local absolute/relative paths under MEDIA_ROOT become public URLs.
    - Other local paths are copied into media storage when download_dir is set.
    """
    value = str(path_or_url or '').strip()
    if not value:
        raise MediaServiceError('媒体路径或 URL 不能为空')
    if value.lower().startswith(('http://', 'https://')):
        return value

    media_root = Path(settings.MEDIA_ROOT)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = media_root / value.lstrip('/')

    if candidate.exists():
        try:
            rel = candidate.resolve().relative_to(media_root.resolve())
            return build_public_media_url(str(rel).replace('\\', '/'))
        except ValueError:
            pass

    if candidate.exists():
        return build_public_media_url(str(candidate.name))

    raise MediaServiceError(f'无法解析为公网 URL 的本地路径: {value}')


def resolve_local_media_path(path_or_url: str, *, subdir: str = 'video_translation/work') -> Path:
    """Resolve input to a local filesystem path, downloading remote URLs when needed."""
    value = str(path_or_url or '').strip()
    if not value:
        raise MediaServiceError('媒体路径或 URL 不能为空')

    if value.lower().startswith(('http://', 'https://')):
        local = local_path_from_public_url(value)
        if local and local.exists():
            return local
        return download_url_to_media(value, subdir=subdir)

    media_root = Path(settings.MEDIA_ROOT)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = media_root / value.lstrip('/')
    if candidate.exists():
        return candidate.resolve()

    public = ensure_public_url(value)
    return download_url_to_media(public, subdir=subdir)


def download_url_to_media(url: str, *, subdir: str = 'video_translation/work') -> Path:
    """Download a remote file into MEDIA_ROOT/subdir and return local path."""
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower() or '.bin'
    dest_dir = Path(settings.MEDIA_ROOT) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex}{ext}"
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    logger.info('Downloaded media %s -> %s', url, dest)
    return dest


def save_output_file(source_path: Union[str, Path], *, subdir: str = 'video_translation/output') -> dict:
    """Persist a generated artifact under media and return metadata."""
    src = Path(source_path)
    if not src.exists():
        raise MediaServiceError(f'输出文件不存在: {source_path}')
    dest_dir = Path(settings.MEDIA_ROOT) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex}{src.suffix or '.bin'}"
    dest.write_bytes(src.read_bytes())
    rel = dest.relative_to(Path(settings.MEDIA_ROOT))
    public_url = build_public_media_url(str(rel).replace('\\', '/'))
    return {
        'local_path': str(dest),
        'relative_path': str(rel).replace('\\', '/'),
        'public_url': public_url,
        'filename': dest.name,
        'size_bytes': dest.stat().st_size,
    }


def upload_video(
    file_obj: Union[UploadedFile, BinaryIO],
    *,
    user_id: Optional[int] = None,
    original_name: Optional[str] = None,
) -> dict:
    """Save an uploaded video file and return media metadata."""
    max_mb = int(getattr(settings, 'VIDEO_TRANSLATION_MAX_FILE_MB', 200))
    max_bytes = max_mb * 1024 * 1024

    name = original_name or getattr(file_obj, 'name', '') or 'upload.mp4'
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise MediaServiceError(f'不支持的视频格式: {ext or "unknown"}')

    content_type = getattr(file_obj, 'content_type', '') or mimetypes.guess_type(name)[0] or ''
    if content_type and not content_type.startswith(ALLOWED_VIDEO_MIME_PREFIXES):
        raise MediaServiceError(f'不支持的内容类型: {content_type}')

    if hasattr(file_obj, 'size') and file_obj.size and file_obj.size > max_bytes:
        raise MediaServiceError(f'视频文件超过上限 {max_mb}MB')

    uid = uuid.uuid4().hex
    user_part = str(user_id) if user_id else 'anonymous'
    rel_dir = Path('uploads') / 'video' / user_part
    dest_dir = Path(settings.MEDIA_ROOT) / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uid}{ext}"
    dest_path = dest_dir / filename

    if hasattr(file_obj, 'chunks'):
        total = 0
        with dest_path.open('wb') as out:
            for chunk in file_obj.chunks():
                total += len(chunk)
                if total > max_bytes:
                    dest_path.unlink(missing_ok=True)
                    raise MediaServiceError(f'视频文件超过上限 {max_mb}MB')
                out.write(chunk)
    else:
        data = file_obj.read()
        if len(data) > max_bytes:
            raise MediaServiceError(f'视频文件超过上限 {max_mb}MB')
        dest_path.write_bytes(data)

    rel = (rel_dir / filename).as_posix()
    return {
        'media_id': uid,
        'filename': filename,
        'local_path': str(dest_path),
        'relative_path': rel,
        'public_url': build_public_media_url(rel),
        'size_bytes': dest_path.stat().st_size,
    }


def resolve_media_id(media_id: str) -> Optional[dict]:
    """Find uploaded media by media_id (uuid hex in filename)."""
    if not media_id:
        return None
    uploads_root = Path(settings.MEDIA_ROOT) / 'uploads' / 'video'
    if not uploads_root.exists():
        return None
    for path in uploads_root.rglob(f'{media_id}.*'):
        if path.is_file():
            rel = path.relative_to(Path(settings.MEDIA_ROOT)).as_posix()
            return {
                'media_id': media_id,
                'local_path': str(path),
                'relative_path': rel,
                'public_url': build_public_media_url(rel),
            }
    return None
