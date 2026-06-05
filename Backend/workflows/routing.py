"""
WebSocket routing for workflows.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/workflow/(?P<workflow_id>\d+)/$', consumers.WorkflowConsumer.as_asgi()),
    re_path(r'ws/execution/(?P<execution_id>\d+)/$', consumers.ExecutionConsumer.as_asgi()),
    re_path(r'ws/monitoring/$', consumers.MonitoringConsumer.as_asgi()),
]
