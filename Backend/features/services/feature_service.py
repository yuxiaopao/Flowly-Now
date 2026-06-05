"""
功能管理服务层
"""

import json
import logging
from typing import Any, Optional, Dict, List, Union

from django.core.cache import cache
from django.conf import settings

from features.models import SystemFeature, FeatureCategory, FeatureAuditLog

logger = logging.getLogger(__name__)

FEATURE_CACHE_KEY = "system_feature:"
FEATURE_CACHE_TTL = 300


class FeatureService:
    """统一的动态功能配置服务"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if FeatureService._initialized:
            return
        FeatureService._initialized = True

    def get(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        cache_key = FEATURE_CACHE_KEY + key
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        try:
            feature = SystemFeature.objects.select_related('category').get(key=key, is_enabled=True)
            value = feature.get_value()
        except SystemFeature.DoesNotExist:
            value = default
        if use_cache and value is not None:
            cache.set(cache_key, value, FEATURE_CACHE_TTL)
        return value

    def get_bool(self, key: str, default: bool = False) -> bool:
        return bool(self.get(key, default))

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def get_str(self, key: str, default: str = '') -> str:
        v = self.get(key, default)
        return str(v) if v is not None else default

    def set(
        self, key: str, value: Any,
        user=None, ip_address=None, reason: str = '', invalidate_cache: bool = True
    ) -> SystemFeature:
        feature = SystemFeature.objects.get(key=key)
        old_value = feature.value
        feature.value = value
        feature.save(update_fields=['value', 'updated_at'])
        if invalidate_cache:
            self.invalidate(key)
        self._log_change(feature, 'update', old_value, value, user, ip_address, reason)
        logger.info(f"Feature '{key}' updated: {old_value} -> {value}")
        return feature

    def toggle(self, key: str, user=None, ip_address=None) -> SystemFeature:
        feature = SystemFeature.objects.get(key=key)
        return self.set(key, not feature.get_value(), user, ip_address)

    def reset(self, key: str, user=None, ip_address=None) -> SystemFeature:
        feature = SystemFeature.objects.get(key=key)
        old_value = feature.value
        feature.value = None
        feature.save(update_fields=['value', 'updated_at'])
        self.invalidate(key)
        self._log_change(feature, 'reset', old_value, feature.default_value, user, ip_address)
        return feature

    def invalidate(self, key: str = None):
        if key:
            cache.delete(FEATURE_CACHE_KEY + key)
        else:
            cache.clear()

    def get_all_categories_with_features(self) -> List[Dict]:
        categories = FeatureCategory.objects.filter(
            features__is_visible=True
        ).distinct().prefetch_related('features').order_by('sort_order', 'name')

        result = []
        for cat in categories:
            features = cat.features.filter(is_visible=True).order_by('order', 'key')
            result.append({
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'description': cat.description,
                'icon': cat.icon,
                'sort_order': cat.sort_order,
                'features': [{
                    'id': f.id,
                    'key': f.key,
                    'name': f.name,
                    'description': f.description,
                    'value_type': f.value_type,
                    'value': f.get_value(),
                    'default_value': f.default_value,
                    'choices': f.choices,
                    'min_value': f.min_value,
                    'max_value': f.max_value,
                    'step': f.step,
                    'placeholder': f.placeholder,
                    'suffix': f.suffix,
                    'group': f.group,
                    'order': f.order,
                    'is_enabled': f.is_enabled,
                    'is_readonly': f.is_readonly,
                    'display_value': f.get_display_value(),
                } for f in features],
            })
        return result

    def _log_change(self, feature, action, old_value, new_value, user, ip_address, reason=''):
        FeatureAuditLog.objects.create(
            feature=feature,
            action=action,
            old_value=old_value,
            new_value=new_value,
            changed_by=user,
            ip_address=ip_address,
            reason=reason,
        )

    def export_config(self, keys: List[str] = None) -> str:
        qs = SystemFeature.objects.filter(is_enabled=True)
        if keys:
            qs = qs.filter(key__in=keys)
        config = {f.key: {'value': f.get_value(), 'updated_at': f.updated_at.isoformat() if f.updated_at else None} for f in qs}
        return json.dumps(config, ensure_ascii=False, indent=2)

    def import_config(self, config: Dict, strategy: str = 'merge', user=None, ip_address=None) -> Dict:
        results = {'updated': [], 'skipped': [], 'errors': []}
        for key, data in config.items():
            try:
                feature = SystemFeature.objects.get(key=key)
            except SystemFeature.DoesNotExist:
                results['skipped'].append(key)
                continue
            new_value = data.get('value') if isinstance(data, dict) else data
            if strategy == 'diff' and new_value == feature.default_value:
                results['skipped'].append(key)
                continue
            old_value = feature.value
            feature.value = new_value
            feature.save(update_fields=['value', 'updated_at'])
            self.invalidate(key)
            self._log_change(feature, 'update', old_value, new_value, user, ip_address)
            results['updated'].append(key)
        return results


_feature_service: Optional[FeatureService] = None


def get_feature_service() -> FeatureService:
    global _feature_service
    if _feature_service is None:
        _feature_service = FeatureService()
    return _feature_service


def fg(key: str, default: Any = None) -> Any:
    return get_feature_service().get(key, default)


def fg_bool(key: str, default: bool = False) -> bool:
    return get_feature_service().get_bool(key, default)
