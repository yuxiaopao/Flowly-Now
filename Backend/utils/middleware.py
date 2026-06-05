"""
Custom middleware classes.
"""

import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all requests."""

    def process_request(self, request):
        request._start_time = time.time()
        logger.debug(f"Request: {request.method} {request.path}")
        return None

    def process_response(self, request, response):
        duration = time.time() - getattr(request, '_start_time', time.time())
        logger.debug(
            f"Response: {request.method} {request.path} - "
            f"Status: {response.status_code} - Duration: {duration:.3f}s"
        )
        return response


class CORSCustomMiddleware(MiddlewareMixin):
    """Custom CORS middleware for API requests."""

    def process_response(self, request, response):
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Origin'] = getattr(
                settings, 'CORS_ALLOWED_ORIGINS', '*'
            )
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Allow-Credentials'] = 'true'

        return response


class JSONErrorMiddleware(MiddlewareMixin):
    """Middleware to convert error responses to JSON."""

    def process_response(self, request, response):
        if request.path.startswith('/api/') and response.status_code >= 400:
            try:
                data = json.loads(response.content.decode())
            except (json.JSONDecodeError, TypeError):
                data = {'error': response.content.decode() if response.content else 'Error'}

            return JsonResponse({
                'error': True,
                'message': data.get('detail', data.get('message', 'Error')),
                'details': data
            }, status=response.status_code)

        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Simple rate limiting middleware."""

    def process_request(self, request):
        if not request.path.startswith('/api/'):
            return None

        # Get client identifier
        if request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            from .helpers import get_client_ip
            identifier = f"ip:{get_client_ip(request)}"

        # Check rate limit
        from django.core.cache import cache
        key = f"rate_limit:{identifier}"
        limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 60)

        count = cache.get(key, 0)
        if count >= limit:
            return JsonResponse({
                'error': True,
                'code': 'rate_limit',
                'message': '请求过于频繁，请稍后再试'
            }, status=429)

        # Increment counter
        cache.set(key, count + 1, 60)
        return None


class TenantMiddleware(MiddlewareMixin):
    """Middleware to resolve tenant from request and enforce tenant isolation."""

    def process_request(self, request):
        # Initialize tenant to None
        request.tenant = None
        request.tenant_membership = None

        if not request.user.is_authenticated:
            return None

        # Try to get tenant from header or subdomain
        tenant_slug = request.headers.get('X-Tenant')
        if not tenant_slug:
            # Try to get from subdomain
            host = request.get_host()
            parts = host.split('.')
            if len(parts) >= 3:
                tenant_slug = parts[0]

        if tenant_slug:
            from tenants.models import Tenant
            try:
                request.tenant = Tenant.objects.get(slug=tenant_slug, status='active')
                # Get user's membership in this tenant
                from tenants.models import TenantMembership
                request.tenant_membership = TenantMembership.objects.filter(
                    tenant=request.tenant,
                    user=request.user,
                    is_active=True
                ).first()
            except Tenant.DoesNotExist:
                pass

        return None


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to enforce tenant data isolation.
    Automatically filters querysets based on the current tenant.
    """

    # Models that should be filtered by tenant
    TENANT_FILTERED_MODELS = [
        'workflows.Workflow',
        'workflows.WorkflowExecution',
        'agents.Agent',
        'agents.AgentExecution',
        'prompts.PromptTemplate',
        'rag.VectorStore',
        'rag.DocumentCollection',
    ]

    def process_request(self, request):
        # Only apply isolation for authenticated users
        if not hasattr(request, 'tenant') or not request.user.is_authenticated:
            return None

        # Attach tenant context to request for downstream use
        request.tenant_context = {
            'tenant': getattr(request, 'tenant', None),
            'membership': getattr(request, 'tenant_membership', None),
            'user': request.user,
            'is_tenant_admin': self._is_tenant_admin(request),
        }

        return None

    def _is_tenant_admin(self, request) -> bool:
        """Check if current user is a tenant admin."""
        membership = getattr(request, 'tenant_membership', None)
        if not membership:
            return False
        return membership.role in ['owner', 'admin']

    def _is_superuser(self, request) -> bool:
        """Check if current user is a superuser."""
        return getattr(request.user, 'is_superuser', False)


class TenantQuerySetMixin:
    """
    Mixin for ViewSets to automatically filter querysets by tenant.
    Usage: Inherit from this mixin and define model in your ViewSet.
    """

    def get_queryset(self):
        """Get filtered queryset based on tenant."""
        queryset = super().get_queryset()

        # Superusers can see all data
        if getattr(self.request.user, 'is_superuser', False):
            return queryset

        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            # No tenant context - filter by user's own data
            user_field = self._get_user_field()
            if user_field:
                filter_kwargs = {user_field: self.request.user}
                return queryset.filter(**filter_kwargs)
            return queryset.none()

        # Filter by tenant
        tenant_field = self._get_tenant_field()
        if tenant_field:
            filter_kwargs = {tenant_field: tenant}
            return queryset.filter(**filter_kwargs)

        # Fallback to user field
        user_field = self._get_user_field()
        if user_field:
            filter_kwargs = {user_field: self.request.user}
            return queryset.filter(**filter_kwargs)

        return queryset.none()

    def _get_user_field(self) -> Optional[str]:
        """Get the user foreign key field name."""
        if hasattr(self, 'model') and self.model:
            for field in self.model._meta.get_fields():
                if field.name == 'owner':
                    return 'owner'
                if field.name == 'user':
                    return 'user'
                if field.name == 'created_by':
                    return 'created_by'
        return None

    def _get_tenant_field(self) -> Optional[str]:
        """Get the tenant foreign key field name."""
        if hasattr(self, 'model') and self.model:
            for field in self.model._meta.get_fields():
                if field.name == 'tenant':
                    return 'tenant'
        return None
