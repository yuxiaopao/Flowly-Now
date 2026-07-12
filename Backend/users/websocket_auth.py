"""
JWT authentication for Django Channels WebSocket connections.

Browsers cannot set Authorization headers on WebSocket handshakes, so the
frontend passes `?token=<access_token>` and this middleware resolves scope['user'].
"""
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from users.authentication import JWTAuthentication


@database_sync_to_async
def _get_user_from_token(token):
    if not token:
        return None
    try:
        auth = JWTAuthentication()
        user_auth = auth.authenticate_token(token)
        if user_auth:
            return user_auth[0]
    except Exception:
        return None
    return None


def _extract_token(scope):
    query = parse_qs(scope.get('query_string', b'').decode())
    token = (query.get('token') or [None])[0]
    if token:
        return token

    for header, value in scope.get('headers', []):
        if header.lower() != b'secure-web-socket-protocol':
            continue
        protocols = value.decode().split(',')
        for protocol in protocols:
            protocol = protocol.strip()
            if protocol.startswith('token.'):
                return protocol[len('token.'):]
    return None


class JWTQueryParamAuthMiddleware(BaseMiddleware):
    """Upgrade anonymous/session users when a valid JWT is supplied."""

    async def __call__(self, scope, receive, send):
        if scope.get('type') == 'websocket':
            token = _extract_token(scope)
            if token:
                user = await _get_user_from_token(token)
                if user is not None:
                    scope['user'] = user
            elif 'user' not in scope:
                scope['user'] = AnonymousUser()
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return AuthMiddlewareStack(JWTQueryParamAuthMiddleware(inner))
