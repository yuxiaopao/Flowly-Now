"""Application keys authorize a single invocation endpoint, never management APIs."""
from config.application_messages import MESSAGES
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from .access import can_publish, visible_applications
from .constants import KEY_PREFIX
from .models import ApplicationAPIKey


class ApplicationKeyAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != b'bearer' or len(header) != 2:
            return None
        try:
            raw = header[1].decode('ascii')
        except UnicodeDecodeError:
            return None
        if not raw.startswith(KEY_PREFIX):
            return None
        if getattr(request.resolver_match, 'url_name', '') != 'application-invoke':
            raise AuthenticationFailed(MESSAGES['management_key'])
        key = ApplicationAPIKey.objects.select_related('created_by', 'application__tenant').filter(key_hash=ApplicationAPIKey.digest(raw)).first()
        if (not key or not key.is_active or str(key.application_id) != str(request.parser_context.get('kwargs', {}).get('pk')) or
                not visible_applications(key.created_by).filter(pk=key.application_id).exists() or
                not can_publish(key.created_by, key.application)):
            raise AuthenticationFailed(MESSAGES['invalid_key'])
        return key.created_by, key
