"""Development media serving with byte ranges for browser playback and seeking."""
import mimetypes
from pathlib import Path
import re

from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed, StreamingHttpResponse
from django.utils.http import http_date, parse_http_date_safe
from django.views.static import serve

RANGE_PATTERN = re.compile(r'^bytes=(\d*)-(\d*)$')
STREAMING_EXTENSIONS = frozenset({'.mp4', '.webm', '.mov', '.mp3', '.wav', '.ogg', '.m4a'})
MEDIA_CHUNK_SIZE = 64 * 1024


def media_chunks(path, start, length):
    with path.open('rb') as stream:
        stream.seek(start)
        while length:
            chunk = stream.read(min(MEDIA_CHUNK_SIZE, length))
            if not chunk:
                break
            length -= len(chunk)
            yield chunk


def serve_media(request, path, document_root=None):
    if request.method not in ('GET', 'HEAD'):
        return HttpResponseNotAllowed(['GET', 'HEAD'])
    root = Path(document_root).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise Http404('Media file not found')
    if target.suffix.lower() not in STREAMING_EXTENSIONS:
        return serve(request, path, document_root=root)

    info = target.stat()
    length = info.st_size
    etag = f'"{info.st_mtime_ns:x}-{length:x}"'
    content_type = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
    range_header = request.headers.get('Range', '')
    if_range = request.headers.get('If-Range')
    if if_range and if_range != etag:
        date = parse_http_date_safe(if_range)
        if date is None or int(info.st_mtime) > date:
            range_header = ''

    # Multiple ranges are optional in HTTP; ignore them and serve the full file.
    match = RANGE_PATTERN.fullmatch(range_header) if ',' not in range_header else None
    if match:
        first, last = match.groups()
        if not first:
            suffix = int(last or 0)
            start, end = max(0, length - suffix), length - 1
        else:
            start, end = int(first), min(int(last), length - 1) if last else length - 1
        if length == 0 or (not first and not int(last or 0)) or start >= length or end < start:
            response = HttpResponse(status=416)
            response['Content-Range'] = f'bytes */{length}'
        else:
            response = HttpResponse(status=206, content_type=content_type) if request.method == 'HEAD' else StreamingHttpResponse(media_chunks(target, start, end-start+1), status=206, content_type=content_type)
            response['Content-Range'] = f'bytes {start}-{end}/{length}'
            response['Content-Length'] = str(end-start+1)
    else:
        response = HttpResponse(content_type=content_type) if request.method == 'HEAD' else FileResponse(target.open('rb'), content_type=content_type)
        response['Content-Length'] = str(length)
    response['Accept-Ranges'] = 'bytes'
    response['Last-Modified'] = http_date(info.st_mtime)
    response['ETag'] = etag
    return response
