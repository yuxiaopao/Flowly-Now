"""
Health check API views.
"""

from django.db import connection
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


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
        
        # Check Redis connection
        try:
            if settings.CHANNEL_LAYERS:
                import redis
                redis_host = settings.REDIS_HOST if hasattr(settings, 'REDIS_HOST') else 'localhost'
                redis_port = settings.REDIS_PORT if hasattr(settings, 'REDIS_PORT') else 6379
                r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=1)
                r.ping()
                health['redis'] = 'connected'
        except Exception:
            health['redis'] = 'disconnected'
            # Redis is optional, don't mark as unhealthy
        
        status_code = 200 if health['status'] == 'healthy' else 503
        return Response(health, status=status_code)


class PingView(APIView):
    """Simple ping endpoint."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return pong."""
        return Response({'message': 'pong'})
