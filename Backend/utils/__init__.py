"""
Utility functions and helpers.
"""

from .responses import (
    success_response,
    created_response,
    updated_response,
    deleted_response,
    error_response,
    validation_error_response,
    not_found_response,
    unauthorized_response,
    forbidden_response,
    server_error_response,
    paginated_response,
    stream_success_response,
    stream_error_response,
    stream_progress_response,
    UnifiedResponseMixin,
)

__all__ = [
    'success_response',
    'created_response',
    'updated_response',
    'deleted_response',
    'error_response',
    'validation_error_response',
    'not_found_response',
    'unauthorized_response',
    'forbidden_response',
    'server_error_response',
    'paginated_response',
    'stream_success_response',
    'stream_error_response',
    'stream_progress_response',
    'UnifiedResponseMixin',
]

import os
from pathlib import Path


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


def safe_json_loads(value, default=None):
    """Safely load JSON."""
    import json
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
