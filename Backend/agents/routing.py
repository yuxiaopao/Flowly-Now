"""
WebSocket routing for agents app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/agent/(?P<agent_id>[a-zA-Z0-9_-]+)/$',
        consumers.DesktopAgentConsumer.as_asgi()
    ),
]
