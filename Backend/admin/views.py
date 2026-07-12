"""
Admin API views for system management.
"""

import gzip
import io
import logging
import os
import shutil
from datetime import timedelta

from django.conf import settings as django_settings
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from billing.models import UsageRecord
from core.models.audit import AuditAction, AuditLog
from monitoring.models import Alert
from tenants.models import Tenant
from users.models import User
from users.serializers import UserSerializer
from workflows.models import Workflow, WorkflowExecution

from .constants import (
    BACKUP_DUMPDATA_EXCLUDES, BACKUP_TYPE_DATABASE, BACKUP_TYPE_FILES,
    BACKUP_TYPE_FULL, BACKUP_TYPES, DEFAULT_SYSTEM_SETTINGS,
)
from .models import SystemSetting
from .serializers import (
    AdminResetPasswordSerializer, AdminTenantCreateSerializer,
    AdminTenantSerializer, AdminTenantUpdateSerializer,
    AdminUserCreateSerializer, AdminUserUpdateSerializer,
)

logger = logging.getLogger(__name__)


class IsSuperUser(IsAuthenticated):
    """Permission check for super users only."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser  # type: ignore[reportAttributeAccessIssue]
        )


def _get_client_ip(request):
    """Extract client IP from request headers."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _audit(request, action, description, level='info', target_type='', target_id='', target_name=''):
    """Write an audit log entry for an admin operation."""
    try:
        AuditLog.log(
            action=action,
            description=description,
            user=request.user,
            level=level,
            target_type=target_type,
            target_id=str(target_id),
            target_name=target_name,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_method=request.method,
            request_path=request.path,
        )
    except Exception:
        logger.exception('Failed to write audit log for admin action %s', action)


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]

    def list(self, request):
        """Get paginated user list."""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '')

        queryset = User.objects.all()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )

        total = queryset.count()
        users = queryset.prefetch_related(
            'tenant_memberships__tenant'
        ).order_by('-date_joined')[(page - 1) * page_size: page * page_size]

        data = UserSerializer(users, many=True).data
        for user, item in zip(users, data):
            membership = next(
                (m for m in user.tenant_memberships.all() if m.is_active),
                None
            )
            item['tenant_name'] = membership.tenant.name if membership else None
            item['is_active'] = user.is_active

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
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(UserSerializer(user).data)

    def create(self, request):
        """Create a new user."""
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        _audit(
            request, AuditAction.USER_CREATE,
            f'管理员创建用户 {user.username}',
            target_type='user', target_id=user.pk, target_name=user.username
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """Update user fields (email/role/is_active/is_superuser/phone)."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if user == request.user and request.data.get('is_active') is False:
            return Response(
                {'error': '不能禁用当前登录的管理员账号'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        _audit(
            request, AuditAction.USER_UPDATE,
            f'管理员更新用户 {user.username}',
            target_type='user', target_id=user.pk, target_name=user.username
        )
        return Response(UserSerializer(user).data)

    def destroy(self, request, pk=None):
        """Delete user."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_superuser:
            return Response(
                {'error': '不能删除超级管理员'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user == request.user:
            return Response(
                {'error': '不能删除当前登录的账号'},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = user.username
        user_pk = user.pk
        user.delete()

        _audit(
            request, AuditAction.USER_DELETE,
            f'管理员删除用户 {username}',
            level='warning',
            target_type='user', target_id=user_pk, target_name=username
        )
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """Reset a user's password to the provided value."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AdminResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])

        _audit(
            request, AuditAction.PASSWORD_RESET,
            f'管理员重置用户 {user.username} 的密码',
            level='warning',
            target_type='user', target_id=user.pk, target_name=user.username
        )
        return Response({'success': True})


class TenantManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for tenant management (all tenants, superuser only)."""

    queryset = Tenant.objects.all()
    serializer_class = AdminTenantSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = Tenant.objects.select_related('owner').prefetch_related('memberships')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(slug__icontains=search)
            )
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminTenantCreateSerializer
        if self.action in ['update', 'partial_update']:
            return AdminTenantUpdateSerializer
        return AdminTenantSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()

        _audit(
            request, AuditAction.OTHER,
            f'管理员创建租户 {tenant.name}',
            target_type='tenant', target_id=tenant.pk, target_name=tenant.name
        )
        return Response(
            AdminTenantSerializer(tenant).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        tenant = self.get_object()
        serializer = self.get_serializer(tenant, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()

        _audit(
            request, AuditAction.OTHER,
            f'管理员更新租户 {tenant.name}',
            target_type='tenant', target_id=tenant.pk, target_name=tenant.name
        )
        return Response(AdminTenantSerializer(tenant).data)

    def destroy(self, request, *args, **kwargs):
        tenant = self.get_object()
        name = tenant.name
        tenant_pk = tenant.pk
        tenant.delete()

        _audit(
            request, AuditAction.DATA_DELETE,
            f'管理员删除租户 {name}',
            level='warning',
            target_type='tenant', target_id=tenant_pk, target_name=name
        )
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
            'node_count': w.nodes.count(),
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
            'is_active': a.is_active,
            'created_at': a.created_at,
            'updated_at': a.updated_at
        } for a in agents]

        return Response({
            'results': data,
            'total': total,
            'page': page,
            'page_size': page_size
        })


class AuditLogListView(APIView):
    """API for querying audit logs from the admin panel."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        queryset = AuditLog.objects.select_related('user')

        level = request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)

        action_filter = request.query_params.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        total = queryset.count()
        logs = queryset[(page - 1) * page_size: page * page_size]

        data = [{
            'id': log.id,
            'timestamp': log.created_at,
            'level': log.level,
            'user': log.user.username if log.user else 'System',
            'action': log.get_action_display(),
            'action_code': log.action,
            'resource': log.target_name or log.target_type or '-',
            'ip_address': log.ip_address or '-',
            'description': log.description,
            'details': {
                'description': log.description,
                'target_type': log.target_type,
                'target_id': log.target_id,
                'changes': log.changes,
                'request_method': log.request_method,
                'request_path': log.request_path,
            }
        } for log in logs]

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

        total_users = User.objects.count()
        new_users = User.objects.filter(date_joined__gte=cutoff).count()

        total_workflows = Workflow.objects.count()
        new_workflows = Workflow.objects.filter(created_at__gte=cutoff).count()

        total_executions = WorkflowExecution.objects.count()
        recent_executions = WorkflowExecution.objects.filter(queued_at__gte=cutoff).count()

        total_agents = Agent.objects.count()
        active_agents = Agent.objects.filter(is_active=True).count()

        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(status='active').count()

        active_alerts = Alert.objects.filter(status='active').count()

        total_cost = UsageRecord.objects.filter(
            created_at__gte=cutoff
        ).aggregate(total=Sum('total_cost'))['total'] or 0

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
            'alerts': {
                'active': active_alerts
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
            redis_host = getattr(django_settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(django_settings, 'REDIS_PORT', 6379)
            r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=2)
            r.ping()
        except Exception:
            health['redis'] = False

        # Check Celery
        try:
            from celery import current_app
            inspect = current_app.control.inspect(timeout=2)
            stats = inspect.stats()
            if not stats:
                health['celery'] = False
        except Exception:
            health['celery'] = False

        return Response(health)


class SystemSettingsView(APIView):
    """API for system settings (persisted in database)."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        """Get system settings merged over defaults."""
        return Response(SystemSetting.get_all())

    def patch(self, request):
        """Update system settings; unknown keys are rejected."""
        data = request.data or {}
        unknown_keys = [key for key in data if key not in DEFAULT_SYSTEM_SETTINGS]
        if unknown_keys:
            return Response(
                {'error': f"未知的设置项: {', '.join(unknown_keys)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        SystemSetting.set_many(data, user=request.user)

        _audit(
            request, AuditAction.SETTINGS_UPDATE,
            f"管理员更新系统设置: {', '.join(data.keys())}",
            target_type='system_settings'
        )
        return Response({'success': True, 'settings': SystemSetting.get_all()})


class CacheClearView(APIView):
    """API for clearing the application cache."""

    permission_classes = [IsSuperUser]

    def post(self, request):
        """Clear the default Django cache."""
        try:
            cache.clear()
        except Exception as exc:
            logger.exception('Cache clear failed')
            return Response(
                {'error': f'清理缓存失败: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _audit(
            request, AuditAction.OTHER,
            '管理员清理系统缓存',
            target_type='cache'
        )
        return Response({'success': True})


class BackupView(APIView):
    """API for creating system backups (database dump and/or media files)."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        """List existing backup files."""
        backup_dir = django_settings.BACKUP_DIR
        if not os.path.isdir(backup_dir):
            return Response({'results': []})

        files = []
        for name in sorted(os.listdir(backup_dir), reverse=True):
            path = os.path.join(backup_dir, name)
            if os.path.isfile(path):
                files.append({
                    'name': name,
                    'size': os.path.getsize(path),
                    'created_at': timezone.datetime.fromtimestamp(
                        os.path.getmtime(path), tz=timezone.get_current_timezone()
                    ).isoformat()
                })
        return Response({'results': files})

    def post(self, request):
        """Create a backup. type: full | database | files."""
        backup_type = request.data.get('type', BACKUP_TYPE_FULL)
        compress = bool(request.data.get('compress', True))
        include_media = bool(request.data.get('include_media', True))

        if backup_type not in BACKUP_TYPES:
            return Response(
                {'error': f'无效的备份类型: {backup_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        backup_dir = django_settings.BACKUP_DIR
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        artifacts = []

        try:
            if backup_type in (BACKUP_TYPE_FULL, BACKUP_TYPE_DATABASE):
                artifacts.append(self._backup_database(backup_dir, timestamp, compress))

            if backup_type in (BACKUP_TYPE_FULL, BACKUP_TYPE_FILES) and include_media:
                media_artifact = self._backup_media(backup_dir, timestamp)
                if media_artifact:
                    artifacts.append(media_artifact)
        except Exception as exc:
            logger.exception('Backup failed')
            return Response(
                {'error': f'备份失败: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _audit(
            request, AuditAction.DATA_EXPORT,
            f'管理员创建系统备份 ({backup_type})',
            target_type='backup',
            target_name=', '.join(a['name'] for a in artifacts) or '-'
        )
        return Response({'success': True, 'artifacts': artifacts})

    def _backup_database(self, backup_dir, timestamp, compress):
        """Dump all business data with dumpdata."""
        filename = f'db_backup_{timestamp}.json'
        buffer = io.StringIO()
        call_command(
            'dumpdata',
            *[f'--exclude={app}' for app in BACKUP_DUMPDATA_EXCLUDES],
            '--natural-foreign',
            stdout=buffer
        )
        content = buffer.getvalue().encode('utf-8')

        if compress:
            filename += '.gz'
            path = os.path.join(backup_dir, filename)
            with gzip.open(path, 'wb') as f:
                f.write(content)
        else:
            path = os.path.join(backup_dir, filename)
            with open(path, 'wb') as f:
                f.write(content)

        return {'name': filename, 'size': os.path.getsize(path), 'type': 'database'}

    def _backup_media(self, backup_dir, timestamp):
        """Archive the media directory."""
        media_root = str(django_settings.MEDIA_ROOT)
        if not os.path.isdir(media_root) or not os.listdir(media_root):
            return None

        base_name = os.path.join(backup_dir, f'media_backup_{timestamp}')
        archive_path = shutil.make_archive(base_name, 'zip', media_root)
        return {
            'name': os.path.basename(archive_path),
            'size': os.path.getsize(archive_path),
            'type': 'files'
        }


class APIKeyManagementViewSet(viewsets.ViewSet):
    """ViewSet for API key management (gateway user keys)."""

    permission_classes = [IsSuperUser]

    def list(self, request):
        """Get all user API keys registered in the gateway."""
        from gateway.models import UserAPIKey

        keys = UserAPIKey.objects.select_related('user').order_by('-created_at')
        data = [{
            'id': k.id,
            'user': k.user.username,
            'name': k.name,
            'provider': k.provider,
            'is_active': k.is_active,
            'last_used_at': k.last_used_at,
            'created_at': k.created_at,
        } for k in keys]
        return Response({'results': data, 'total': len(data)})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke (deactivate) a user API key."""
        from gateway.models import UserAPIKey

        try:
            key = UserAPIKey.objects.get(pk=pk)
        except UserAPIKey.DoesNotExist:
            return Response(
                {'error': 'API Key 不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        key.is_active = False
        key.save(update_fields=['is_active'])

        _audit(
            request, AuditAction.API_KEY_REVOKE,
            f'管理员撤销用户 {key.user.username} 的 API Key',
            level='warning',
            target_type='api_key', target_id=key.pk
        )
        return Response({'success': True})
