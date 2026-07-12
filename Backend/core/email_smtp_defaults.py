"""Global SMTP defaults for workflow email nodes."""
from __future__ import annotations

from typing import Any, Dict

from django.conf import settings


def _platform_smtp_overrides() -> Dict[str, Any]:
    try:
        from admin.services.config_service import get_smtp_connection_params

        return get_smtp_connection_params()
    except Exception:
        return {}


def get_global_smtp_defaults(*, include_secrets: bool = False) -> Dict[str, Any]:
    """
    Public defaults for UI prefill (password masked unless include_secrets=True).
    Priority: platform SystemSetting → Django settings (.env).
    """
    platform = _platform_smtp_overrides()

    server = (platform.get('host') or getattr(settings, 'EMAIL_HOST', '') or '').strip()
    port = int(platform.get('port') or getattr(settings, 'EMAIL_PORT', 587) or 587)
    use_tls = platform.get('use_tls')
    if use_tls is None:
        use_tls = bool(getattr(settings, 'EMAIL_USE_TLS', True))
    username = (platform.get('username') or getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    from_email = (
        platform.get('from_email')
        or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        or username
        or ''
    ).strip()
    from_name = (platform.get('from_name') or 'Flowly').strip()

    password = (platform.get('password') or getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip()
    has_password = bool(password)

    payload: Dict[str, Any] = {
        'server': server,
        'port': port,
        'useTls': bool(use_tls),
        'username': username,
        'fromEmail': from_email,
        'fromName': from_name,
        'hasPassword': has_password,
        'configured': bool(server and username and has_password),
    }
    if include_secrets:
        payload['password'] = password
    else:
        payload['password'] = '********' if has_password else ''
    return payload


def resolve_runtime_smtp_credentials() -> Dict[str, Any]:
    """Full SMTP credentials for backend email delivery."""
    data = get_global_smtp_defaults(include_secrets=True)
    return {
        'server': data.get('server', ''),
        'port': int(data.get('port', 587) or 587),
        'useTls': bool(data.get('useTls', True)),
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'fromEmail': data.get('fromEmail', ''),
        'fromName': data.get('fromName', 'Flowly'),
    }
