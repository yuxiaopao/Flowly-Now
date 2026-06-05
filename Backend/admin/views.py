"""
Admin API views for system management.
"""

from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from users.models import User
from workflows.models import Workflow, WorkflowExecution
from agents.models import Agent
from tenants.models import Tenant
from billing.models import Subscription, UsageRecord


class IsSuperUser(IsAuthenticated):
    """Permission check for super users only."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser  # type: ignore[reportAttributeAccessIssue]
        )


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""

    queryset = User.objects.all()
    serializer_class = None  # Use users serializer
    permission_classes = [IsSuperUser]

    def list(self, request):
        """Get paginated user list."""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '')

        queryset = User.objects.annotate(
            tenant_name=Count('tenant_memberships__tenant__name')
        )

        if search:
            queryset = queryset.filter(
                username__icontains=search
            ) | queryset.filter(
                email__icontains=search
            )

        total = queryset.count()
        users = queryset.order_by('-date_joined')[
            (page - 1) * page_size: page * page_size
        ]

        from users.serializers import UserSerializer
        data = UserSerializer(users, many=True).data

        # Add tenant info
        for user, item in zip(users, data):
            if hasattr(user, 'profile') and user.profile.tenant:
                item['tenant_name'] = user.profile.tenant.name
            else:
                item['tenant_name'] = None

        return Response({
            'results': data,
            'total': total,
            'page': page,
            'page_size': page_size
        })

    def retrieve(self, request, pk=None):
        """Get user detail."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        from users.serializers import UserSerializer
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """Update user."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update allowed fields
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        if 'is_superuser' in request.data:
            user.is_superuser = request.data['is_superuser']

        user.save()
        return Response({'success': True})

    def destroy(self, request, pk=None):
        """Delete user."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_superuser:
            return Response(
                {'error': 'Cannot delete superuser'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


class WorkflowManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for workflow management."""

    queryset = Workflow.objects.all()
    serializer_class = None
    permission_classes = [IsSuperUser]

    def list(self, request):
        """Get paginated workflow list."""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        queryset = Workflow.objects.select_related('owner')

        total = queryset.count()
        workflows = queryset.order_by('-created_at')[
            (page - 1) * page_size: page * page_size
        ]

        data = [{
            'id': w.id,
            'name': w.name,
            'description': w.description,
            'owner_id': w.owner_id,
            'owner_name': w.owner.username,
            'status': w.status,
            'is_public': w.is_public,
            'node_count': len(w.nodes) if w.nodes else 0,
            'execution_count': w.executions.count(),
            'created_at': w.created_at,
            'updated_at': w.updated_at
        } for w in workflows]

        return Response({
            'results': data,
            'total': total,
            'page': page,
            'page_size': page_size
        })


class AgentManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for agent management."""

    queryset = Agent.objects.all()
    serializer_class = None
    permission_classes = [IsSuperUser]

    def list(self, request):
        """Get paginated agent list."""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        queryset = Agent.objects.select_related('owner')

        total = queryset.count()
        agents = queryset.order_by('-created_at')[
            (page - 1) * page_size: page * page_size
        ]

        data = [{
            'id': a.id,
            'name': a.name,
            'description': a.description,
            'owner_id': a.owner_id,
            'owner_name': a.owner.username,
            'agent_type': a.agent_type,
            'status': a.status,
            'created_at': a.created_at,
            'updated_at': a.updated_at
        } for a in agents]

        return Response({
            'results': data,
            'total': total,
            'page': page,
            'page_size': page_size
        })


class SystemUsageView(APIView):
    """API for system usage statistics."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        """Get system usage statistics."""
        days = int(request.query_params.get('days', 30))
        cutoff = timezone.now() - timedelta(days=days)

        # User stats
        total_users = User.objects.count()
        new_users = User.objects.filter(date_joined__gte=cutoff).count()

        # Workflow stats
        total_workflows = Workflow.objects.count()
        new_workflows = Workflow.objects.filter(created_at__gte=cutoff).count()

        # Execution stats
        total_executions = WorkflowExecution.objects.count()
        recent_executions = WorkflowExecution.objects.filter(created_at__gte=cutoff).count()

        # Agent stats
        total_agents = Agent.objects.count()
        active_agents = Agent.objects.filter(status='active').count()

        # Tenant stats
        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(status='active').count()

        # Usage costs
        total_cost = UsageRecord.objects.filter(
            created_at__gte=cutoff
        ).aggregate(total=Sum('cost'))['total'] or 0

        return Response({
            'period_days': days,
            'users': {
                'total': total_users,
                'new': new_users
            },
            'workflows': {
                'total': total_workflows,
                'new': new_workflows
            },
            'executions': {
                'total': total_executions,
                'recent': recent_executions
            },
            'agents': {
                'total': total_agents,
                'active': active_agents
            },
            'tenants': {
                'total': total_tenants,
                'active': active_tenants
            },
            'costs': {
                'total': float(total_cost)
            }
        })


class SystemHealthView(APIView):
    """API for system health check."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        """Get system health status."""
        health = {
            'api': True,
            'database': True,
            'redis': True,
            'celery': True,
            'timestamp': timezone.now().isoformat()
        }

        # Check database
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            health['database'] = False

        # Check Redis
        try:
            import redis
            from django.conf import settings
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            r = redis.Redis(host=redis_host, port=redis_port, db=0)
            r.ping()
        except Exception:
            health['redis'] = False

        # Check Celery
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if not stats:
                health['celery'] = False
        except Exception:
            health['celery'] = False

        return Response(health)


class SystemSettingsView(APIView):
    """API for system settings."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        """Get system settings."""
        return Response({
            'site_name': 'Flowly',
            'allow_registration': True,
            'email_verification': False,
            'default_role': 'member',
            'rate_limit_per_minute': 60,
            'max_tokens': 4096,
            'execution_timeout': 300,
            'enable_api_logging': True,
            'enable_cost_tracking': True
        })

    def patch(self, request):
        """Update system settings."""
        # In production, save to database/cache
        return Response({'success': True})


class APIKeyManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for API key management."""

    permission_classes = [IsSuperUser]
    serializer_class = None

    def list(self, request):
        """Get API keys."""
        # In production, query from database
        return Response([])

    def create(self, request):
        """Create API key."""
        return Response({
            'id': 'new_key',
            'key': 'fl_sk_' + 'x' * 32,
            'created_at': timezone.now().isoformat()
        })

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke API key."""
        return Response({'success': True})
