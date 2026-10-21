"""JWT authentication with password-bound, individually revocable sessions."""
from datetime import timedelta
from uuid import uuid4

import jwt
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework import authentication, exceptions

from .models import RevokedSession, User

ALGORITHM = 'HS256'
ACCESS = 'access'
REFRESH = 'refresh'


def decode_token(token, expected_type):
    if not isinstance(token, str):
        raise exceptions.AuthenticationFailed('无效的登录凭证')
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM],
                             options={'require': ['exp', 'iat', 'user_id', 'type', 'sid', 'auth_hash']})
        if payload['type'] != expected_type or not isinstance(payload['user_id'], int):
            raise ValueError
        if not isinstance(payload['sid'], str) or not isinstance(payload['auth_hash'], str):
            raise ValueError
        user = User.objects.get(pk=payload['user_id'], is_active=True)
        if not constant_time_compare(payload['auth_hash'], user.get_session_auth_hash()):
            raise ValueError
        if RevokedSession.objects.filter(session_id=payload['sid']).exists():
            raise ValueError
        return payload, user
    except (jwt.InvalidTokenError, ValueError, TypeError, User.DoesNotExist):
        raise exceptions.AuthenticationFailed('登录已过期，请重新登录') from None


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        parts = authentication.get_authorization_header(request).split()
        if not parts or parts[0].lower() != b'bearer':
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed('无效的登录凭证')
        try:
            token = parts[1].decode('ascii')
        except UnicodeDecodeError:
            raise exceptions.AuthenticationFailed('无效的登录凭证') from None
        return self.authenticate_token(token)

    def authenticate_token(self, token):
        _, user = decode_token(token, ACCESS)
        return user, token


def generate_tokens(user, session_id=None):
    now = timezone.now()
    common = {'user_id': user.pk, 'iat': now, 'sid': session_id or str(uuid4()),
              'auth_hash': user.get_session_auth_hash()}
    return {
        token_type: jwt.encode({**common, 'type': token_type, 'exp': now + timedelta(seconds=lifetime)},
                               settings.SECRET_KEY, algorithm=ALGORITHM)
        for token_type, lifetime in (
            (ACCESS, settings.AUTH_ACCESS_TOKEN_SECONDS),
            (REFRESH, settings.AUTH_REFRESH_TOKEN_SECONDS),
        )
    }


def verify_refresh_token(token):
    try:
        payload, _ = decode_token(token, REFRESH)
        return payload
    except exceptions.AuthenticationFailed:
        return None


def revoke_session(token):
    payload, _ = decode_token(token, ACCESS)
    now = timezone.now()
    RevokedSession.objects.filter(expires_at__lt=now).delete()
    RevokedSession.objects.get_or_create(session_id=payload['sid'], defaults={
        'expires_at': now + timedelta(seconds=settings.AUTH_REFRESH_TOKEN_SECONDS),
    })
