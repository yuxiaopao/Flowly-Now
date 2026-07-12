"""
Platform configuration service - validation, public config, runtime sync.
"""

import logging
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.runtime_config import get_runtime_config

from ..constants import (
    BOOLEAN_SETTING_KEYS,
    DEFAULT_SYSTEM_SETTINGS,
    INTEGER_SETTING_KEYS,
    PUBLIC_CONFIG_CACHE_KEY,
    PUBLIC_CONFIG_CACHE_TTL,
    SETTING_FIELD_LABELS,
    SETTING_MODULE_KEYS,
    SETTING_MODULE_LABELS,
    USER_ROLE_CHOICES,
)
from ..models import (
    FeatureVisibilityRule,
    LegalDocument,
    PaymentProviderConfig,
    SystemSetting,
)

logger = logging.getLogger(__name__)


def invalidate_public_config_cache():
    cache.delete(PUBLIC_CONFIG_CACHE_KEY)


def get_module_settings(module: str) -> Dict[str, Any]:
    keys = SETTING_MODULE_KEYS.get(module, [])
    all_settings = SystemSetting.get_all()
    return {key: all_settings.get(key, DEFAULT_SYSTEM_SETTINGS.get(key)) for key in keys}


def validate_module_settings(module: str, data: Dict[str, Any]) -> Dict[str, Any]:
    allowed_keys = set(SETTING_MODULE_KEYS.get(module, []))
    if not allowed_keys:
        raise ValidationError(f'未知模块: {module}')

    unknown = [key for key in data if key not in allowed_keys]
    if unknown:
        raise ValidationError(f"未知的设置项: {', '.join(unknown)}")

    cleaned = {}
    defaults = DEFAULT_SYSTEM_SETTINGS
    for key, value in data.items():
        if key in BOOLEAN_SETTING_KEYS:
            cleaned[key] = bool(value)
        elif key in INTEGER_SETTING_KEYS:
            try:
                cleaned[key] = int(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f'{SETTING_FIELD_LABELS.get(key, key)} 必须是整数') from exc
            if key == 'password_min_length' and cleaned[key] < 6:
                raise ValidationError('密码最小长度不能小于 6')
            if key == 'max_login_attempts' and cleaned[key] < 1:
                raise ValidationError('最大登录失败次数至少为 1')
        elif key == 'default_role':
            if value not in USER_ROLE_CHOICES:
                raise ValidationError(f'默认角色必须是: {", ".join(USER_ROLE_CHOICES)}')
            cleaned[key] = value
        elif key == 'default_tenant_id':
            cleaned[key] = int(value) if value not in (None, '', 'null') else None
        else:
            cleaned[key] = value if value is not None else defaults.get(key, '')

    return cleaned


def save_module_settings(module: str, data: Dict[str, Any], user=None) -> Dict[str, Any]:
    cleaned = validate_module_settings(module, data)
    SystemSetting.set_many(cleaned, user=user)
    invalidate_public_config_cache()
    return get_module_settings(module)


def build_module_schema(module: str) -> List[Dict[str, Any]]:
    keys = SETTING_MODULE_KEYS.get(module, [])
    all_settings = SystemSetting.get_all()
    schema = []
    for key in keys:
        default = DEFAULT_SYSTEM_SETTINGS.get(key)
        field_type = 'boolean' if key in BOOLEAN_SETTING_KEYS else (
            'integer' if key in INTEGER_SETTING_KEYS else 'string'
        )
        if key == 'default_role':
            field_type = 'choice'
        schema.append({
            'key': key,
            'label': SETTING_FIELD_LABELS.get(key, key),
            'type': field_type,
            'value': all_settings.get(key, default),
            'default': default,
            'choices': list(USER_ROLE_CHOICES) if key == 'default_role' else None,
        })
    return schema


def get_active_legal_document(doc_type: str) -> Optional[LegalDocument]:
    return LegalDocument.objects.filter(doc_type=doc_type, is_active=True).first()


def serialize_legal_document(doc: LegalDocument) -> Dict[str, Any]:
    return {
        'id': doc.id,
        'doc_type': doc.doc_type,
        'doc_type_display': doc.get_doc_type_display(),
        'version': doc.version,
        'title': doc.title,
        'content_html': doc.content_html,
        'content_markdown': doc.content_markdown,
        'is_active': doc.is_active,
        'require_acceptance': doc.require_acceptance,
        'effective_at': doc.effective_at.isoformat() if doc.effective_at else None,
        'created_at': doc.created_at.isoformat(),
        'updated_at': doc.updated_at.isoformat(),
        'acceptance_count': doc.acceptances.count(),
    }


def get_public_config() -> Dict[str, Any]:
    cached = cache.get(PUBLIC_CONFIG_CACHE_KEY)
    if cached is not None:
        return cached

    settings_map = SystemSetting.get_all()

    terms_doc = get_active_legal_document('terms')
    privacy_doc = get_active_legal_document('privacy')
    login_doc = get_active_legal_document('login')

    payment_providers = [{
        'provider': p.provider,
        'display_name': p.display_name,
        'is_enabled': p.is_enabled,
        'fee_rate': float(p.fee_rate),
    } for p in PaymentProviderConfig.objects.filter(is_enabled=True).order_by('sort_order')]

    config = {
        'site': {
            'name': settings_map.get('site_name', 'Flowly'),
            'description': settings_map.get('site_description', ''),
            'logo': settings_map.get('site_logo', ''),
            'favicon': settings_map.get('site_favicon', ''),
            'contact_email': settings_map.get('contact_email', ''),
            'contact_phone': settings_map.get('contact_phone', ''),
            'support_url': settings_map.get('support_url', ''),
            'footer_text': settings_map.get('footer_text', ''),
            'locale': settings_map.get('default_locale', 'zh-CN'),
            'timezone': settings_map.get('default_timezone', 'Asia/Shanghai'),
        },
        'auth': {
            'allow_registration': settings_map.get('allow_registration', True),
            'email_verification': settings_map.get('email_verification', False),
            'require_terms_on_register': settings_map.get('require_terms_on_register', True),
            'require_terms_on_login': settings_map.get('require_terms_on_login', False),
            'password_min_length': settings_map.get('password_min_length', 8),
        },
        'terms': {
            'terms': serialize_legal_document(terms_doc) if terms_doc else None,
            'privacy': serialize_legal_document(privacy_doc) if privacy_doc else None,
            'login': serialize_legal_document(login_doc) if login_doc else None,
        },
        'features': {
            'enable_marketplace': settings_map.get('enable_marketplace', True),
            'enable_nl_workflow': settings_map.get('enable_nl_workflow', True),
            'enable_api_docs': settings_map.get('enable_api_docs', True),
        },
        'defaults': {
            'role': settings_map.get('default_role', 'user'),
            'execution_limit': settings_map.get('default_execution_limit', 1000),
            'notification_enabled': settings_map.get('default_notification_enabled', True),
        },
        'payment': {
            'default_currency': settings_map.get('payment_default_currency', 'CNY'),
            'enable_refunds': settings_map.get('payment_enable_refunds', True),
            'providers': payment_providers,
        },
        'runtime': get_runtime_config(),
        'updated_at': timezone.now().isoformat(),
    }

    cache.set(PUBLIC_CONFIG_CACHE_KEY, config, PUBLIC_CONFIG_CACHE_TTL)
    return config


def get_effective_features_for_user(user=None) -> Dict[str, bool]:
    """Merge global settings with per-role/group visibility rules."""
    settings_map = SystemSetting.get_all()
    features = {
        'enable_marketplace': settings_map.get('enable_marketplace', True),
        'enable_nl_workflow': settings_map.get('enable_nl_workflow', True),
        'enable_api_docs': settings_map.get('enable_api_docs', True),
    }

    rules = FeatureVisibilityRule.objects.filter(is_enabled=True)
    for rule in rules:
        applies = False
        if rule.scope == 'global':
            applies = True
        elif rule.scope == 'role' and user and getattr(user, 'role', None) == rule.role:
            applies = True
        elif rule.scope == 'group' and user and rule.group_id:
            applies = user.groups.filter(pk=rule.group_id).exists()

        if applies and rule.feature_key in features:
            features[rule.feature_key] = rule.is_visible

    return features


def get_smtp_connection_params() -> Dict[str, Any]:
    settings_map = SystemSetting.get_all()
    return {
        'host': settings_map.get('smtp_host') or '',
        'port': int(settings_map.get('smtp_port') or 587),
        'username': settings_map.get('smtp_user') or '',
        'password': settings_map.get('smtp_password') or '',
        'use_tls': bool(settings_map.get('use_tls', True)),
        'from_email': settings_map.get('from_email') or '',
        'from_name': settings_map.get('from_name') or 'Flowly',
    }


def list_all_modules() -> List[Dict[str, str]]:
    return [
        {'id': module_id, 'label': SETTING_MODULE_LABELS.get(module_id, module_id)}
        for module_id in SETTING_MODULE_KEYS
    ]
