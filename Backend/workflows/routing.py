"""
WebSocket routing for workflows.
"""

from django.urls import re_path
from . import consumers

UUID_PATTERN = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

websocket_urlpatterns = [
    re_path(rf'ws/workflow/(?P<workflow_id>{UUID_PATTERN})/$', consumers.WorkflowConsumer.as_asgi()),
    re_path(rf'ws/execution/(?P<execution_id>{UUID_PATTERN})/$', consumers.ExecutionConsumer.as_asgi()),
    re_path(r'ws/monitoring/$', consumers.MonitoringConsumer.as_asgi()),
]
