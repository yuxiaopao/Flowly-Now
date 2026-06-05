"""
ASGI config for Flowly project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://channels.readthedocs.io/en/stable/deploying.html
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import WebSocket URL patterns from various apps
from workflows.routing import websocket_urlpatterns as workflow_websocket_urlpatterns
from training.routing import websocket_urlpatterns as training_websocket_urlpatterns
from codegraph.routing import websocket_urlpatterns as codegraph_websocket_urlpatterns

# Combine all WebSocket URL patterns
websocket_urlpatterns = (
    workflow_websocket_urlpatterns + 
    training_websocket_urlpatterns + 
    codegraph_websocket_urlpatterns
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
