"""
Health check API views.
"""

import os

from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


def _check_redis() -> bool:
    """Ping Redis using the same env vars as Celery/cache/channel layers."""
    import redis

    cache_url = os.getenv('REDIS_CACHE_URL', '').strip()
    if cache_url:
        client = redis.from_url(cache_url, socket_connect_timeout=2)
        client.ping()
        return True

    host = os.getenv('REDIS_HOST', 'localhost')
    port = int(os.getenv('REDIS_PORT', '6379'))
    client = redis.Redis(host=host, port=port, socket_connect_timeout=2)
    client.ping()
    return True


class HealthCheckView(APIView):
    """Health check endpoint."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Check system health."""
        health = {
            'status': 'healthy',
            'service': 'flowly-backend',
            'version': '1.0.0'
        }
        
        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health['database'] = 'connected'
        except Exception as e:
            health['database'] = 'disconnected'
            health['status'] = 'unhealthy'
            health['error'] = str(e)
        
        # Check Redis connection (optional — does not flip overall status)
        try:
            if _check_redis():
                health['redis'] = 'connected'
            else:
                health['redis'] = 'disconnected'
        except Exception:
            health['redis'] = 'disconnected'
        
        status_code = 200 if health['status'] == 'healthy' else 503
        return Response(health, status=status_code)


class PingView(APIView):
    """Simple ping endpoint."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return pong."""
        return Response({'message': 'pong'})
