"""
集成节点凭证解析：将 credentialId 解析为可执行的 token/密钥字段
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def resolve_integration_credentials(service, node_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并节点 config 与用户凭证数据。
    credentialId 指向 APICredential；解密后可为纯文本或 JSON。
    """
    merged = dict(node_config or {})
    credential_id = merged.get('credentialId')
    if not credential_id:
        return merged

    user_id = getattr(service, 'user_id', None)
    if not user_id:
        return merged

    try:
        from django.contrib.auth import get_user_model
        from workflows.models import APICredential

        User = get_user_model()
        user = User.objects.get(id=user_id)
        credential = APICredential.get_for_user(user, credential_id)
        if not credential:
            logger.warning('Credential %s not accessible for user %s', credential_id, user_id)
            return merged

        raw = credential.get_decrypted_data()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    merged.update(parsed)
            except json.JSONDecodeError:
                merged.setdefault('credentialToken', raw)
                merged.setdefault('apiKey', raw)
                merged.setdefault('token', raw)

        service_config = credential.service_config or {}
        if isinstance(service_config, dict):
            for key, value in service_config.items():
                merged.setdefault(key, value)

        credential.update_last_used()
    except Exception as exc:
        logger.warning('Failed to resolve credential %s: %s', credential_id, exc)

    return merged
