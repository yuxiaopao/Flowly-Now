"""
Helper utilities and common functions.
"""

import os
import re
import hashlib
import random
import string
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.utils.text import slugify as django_slugify


# ============== Path Utilities ==============

def get_env_path():
    """Get .env file path."""
    return Path(__file__).resolve().parent.parent / '.env'


def ensure_directories():
    """Ensure all required directories exist."""
    base_dir = Path(__file__).resolve().parent.parent

    directories = [
        base_dir / 'logs',
        base_dir / 'media',
        base_dir / 'static',
        base_dir / 'staticfiles',
    ]

    for directory in directories:
        directory.mkdir(exist_ok=True)


# ============== String Utilities ==============

def slugify(text: str, allow_unicode: bool = False) -> str:
    """Convert to ASCII if allow_unicode is False."""
    return django_slugify(text, allow_unicode=allow_unicode)


def random_string(length: int = 32, chars: str = None) -> str:
    """Generate a random string."""
    chars = chars or string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def random_hex(length: int = 32) -> str:
    """Generate a random hex string."""
    return os.urandom(length // 2).hex()


def truncate(text: str, length: int = 100, suffix: str = '...') -> str:
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


def mask_sensitive(text: str, visible_start: int = 4, visible_end: int = 4) -> str:
    """Mask sensitive information, showing only first and last characters."""
    if len(text) <= visible_start + visible_end:
        return '*' * len(text)
    return text[:visible_start] + '*' * (len(text) - visible_start - visible_end) + text[-visible_end:]


# ============== JSON Utilities ==============

def safe_json_loads(value: Any, default: Any = None) -> Any:
    """Safely load JSON."""
    try:
        if isinstance(value, dict):
            return value
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(value: Any, default: str = '{}') -> str:
    """Safely dump JSON."""
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


# ============== Date/Time Utilities ==============

def now() -> datetime:
    """Get current datetime."""
    return timezone.now()


def parse_date(date_string: str, format: str = '%Y-%m-%d') -> Optional[datetime]:
    """Parse date string to datetime."""
    try:
        return datetime.strptime(date_string, format)
    except (ValueError, TypeError):
        return None


def format_datetime(dt: datetime, format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format datetime to string."""
    if not dt:
        return ''
    return dt.strftime(format)


def time_ago(dt: datetime) -> str:
    """Get human-readable time difference."""
    if not dt:
        return ''

    now = timezone.now()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return '刚刚'
    elif seconds < 3600:
        return f'{int(seconds / 60)}分钟前'
    elif seconds < 86400:
        return f'{int(seconds / 3600)}小时前'
    elif seconds < 604800:
        return f'{int(seconds / 86400)}天前'
    elif seconds < 2592000:
        return f'{int(seconds / 604800)}周前'
    elif seconds < 31536000:
        return f'{int(seconds / 2592000)}月前'
    else:
        return f'{int(seconds / 31536000)}年前'


# ============== Validation Utilities ==============

def is_valid_email(email: str) -> bool:
    """Validate email address."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """Validate URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def is_valid_slug(slug: str) -> bool:
    """Validate slug."""
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    return bool(re.match(pattern, slug))


# ============== Crypto Utilities ==============

def hash_string(text: str, algorithm: str = 'sha256') -> str:
    """Hash a string."""
    h = hashlib.new(algorithm)
    h.update(text.encode('utf-8'))
    return h.hexdigest()


def generate_token() -> str:
    """Generate a secure random token."""
    return hashlib.sha256(os.urandom(32)).hexdigest()


# ============== Cache Utilities ==============

def cache_get(key: str, default: Any = None) -> Any:
    """Get value from cache."""
    return cache.get(key, default)


def cache_set(key: str, value: Any, timeout: int = 300) -> None:
    """Set value in cache."""
    cache.set(key, value, timeout)


def cache_delete(key: str) -> None:
    """Delete value from cache."""
    cache.delete(key)


def cache_clear_pattern(pattern: str) -> None:
    """Clear all keys matching pattern."""
    from django.core.cache import caches
    for cache_alias in caches:
        c = caches[cache_alias]
        if hasattr(c, 'delete_pattern'):
            c.delete_pattern(pattern)


# ============== Request Utilities ==============

def get_client_ip(request) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def get_user_agent(request) -> str:
    """Get user agent from request."""
    return request.META.get('HTTP_USER_AGENT', '')


# ============== HTTP Utilities ==============

def fetch_url(url: str, timeout: int = 10, **kwargs) -> Optional[requests.Response]:
    """Fetch URL with error handling."""
    try:
        return requests.get(url, timeout=timeout, **kwargs)
    except requests.RequestException:
        return None


# ============== Model Utilities ==============

def get_model_fields(model) -> List[str]:
    """Get all field names from a model."""
    return [f.name for f in model._meta.get_fields()]


def get_model_field_types(model) -> Dict[str, str]:
    """Get field types from a model."""
    return {f.name: f.get_internal_type() for f in model._meta.get_fields()}


# ============== List/Dict Utilities ==============

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: Dict, sep: str = '.') -> Dict:
    """Unflatten dictionary."""
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def dict_get(d: Dict, path: str, default: Any = None) -> Any:
    """Get nested dict value using dot notation."""
    keys = path.split('.')
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def dict_set(d: Dict, path: str, value: Any) -> None:
    """Set nested dict value using dot notation."""
    keys = path.split('.')
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


# ============== Pagination Utilities ==============

def paginate(queryset, page: int = 1, page_size: int = 20) -> Dict:
    """Paginate queryset."""
    try:
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        start = (page - 1) * page_size
        end = start + page_size
        total = queryset.count()
        items = list(queryset[start:end])
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    except (ValueError, TypeError):
        return {
            'items': [],
            'total': 0,
            'page': 1,
            'page_size': page_size,
            'total_pages': 0
        }


# ============== File Utilities ==============

def get_file_extension(filename: str) -> str:
    """Get file extension."""
    return Path(filename).suffix.lower().lstrip('.')


def get_file_name(filename: str) -> str:
    """Get file name without extension."""
    return Path(filename).stem


def is_image_file(filename: str) -> bool:
    """Check if file is an image."""
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'}
    return get_file_extension(filename) in image_extensions


def is_document_file(filename: str) -> bool:
    """Check if file is a document."""
    doc_extensions = {'pdf', 'doc', 'docx', 'txt', 'md', 'rtf'}
    return get_file_extension(filename) in doc_extensions
