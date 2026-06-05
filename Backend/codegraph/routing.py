"""
WebSocket routing for codegraph app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/(?P<project_id>\d+)/$', consumers.CodeGraphConsumer.as_asgi()),
    re_path(r'ws/(?P<project_id>\d+)/files/$', consumers.FileWatchConsumer.as_asgi()),
]
