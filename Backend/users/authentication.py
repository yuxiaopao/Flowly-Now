"""
JWT Authentication for REST Framework.
"""

import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.authtoken.models import Token
from .models import User


class JWTAuthentication(authentication.BaseAuthentication):
    """JWT Token Authentication."""

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            return None

        return self.authenticate_token(token)

    def authenticate_token(self, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token 已过期')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('无效的 Token')

        try:
            user = User.objects.get(id=payload.get('user_id'))
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('用户不存在')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('用户已被禁用')

        return (user, token)


def generate_tokens(user):
    """Generate access and refresh tokens for user."""

    access_payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow(),
        'type': 'access'
    }

    refresh_payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }

    access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')

    return {
        'access': access_token,
        'refresh': refresh_token
    }


def verify_refresh_token(token):
    """Verify and decode refresh token."""

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )

        if payload.get('type') != 'refresh':
            return None

        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
