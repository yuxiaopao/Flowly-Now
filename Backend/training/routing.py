"""
WebSocket routing for training app.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/training/(?P<job_id>[a-zA-Z0-9_-]+)/$',
        consumers.TrainingConsumer.as_asgi()
    ),
]
