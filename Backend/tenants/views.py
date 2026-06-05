"""
Views for tenants app.
"""

import secrets
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Tenant, TenantMembership, TenantInvitation, TenantUsage, TeamSkill, SkillAssignment, TeamTask, TaskAssignee, TeamActivity
from .serializers import (
    TenantListSerializer, TenantDetailSerializer, TenantCreateSerializer,
    TenantUpdateSerializer, TenantMembershipSerializer,
    TenantMembershipCreateSerializer, TenantInvitationSerializer,
    TenantUsageSerializer, JoinTenantSerializer,
    TeamSkillListSerializer, TeamSkillDetailSerializer, TeamSkillCreateSerializer,
    TeamTaskListSerializer, TeamTaskDetailSerializer, TeamTaskCreateSerializer, TeamTaskUpdateSerializer,
    SkillAssignmentSerializer, TeamActivitySerializer
)

User = get_user_model()


class TenantPermission:
    """Permission checks for tenants."""

    @staticmethod
    def is_member(user, tenant):
        """Check if user is a member of tenant."""
        return TenantMembership.objects.filter(
            user=user,
            tenant=tenant,
            is_active=True
        ).exists()

    @staticmethod
    def is_admin(user, tenant):
        """Check if user is admin or owner of tenant."""
        return TenantMembership.objects.filter(
            user=user,
            tenant=tenant,
            is_active=True,
            role__in=['owner', 'admin']
        ).exists()

    @staticmethod
    def can_edit(user, tenant):
        """Check if user can edit tenant resources."""
        return TenantMembership.objects.filter(
            user=user,
            tenant=tenant,
            is_active=True,
            role__in=['owner', 'admin', 'member']
        ).exists()


class TenantViewSet(viewsets.ModelViewSet):
    """ViewSet for Tenant."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get user's tenants."""
        return Tenant.objects.filter(
            Q(memberships__user=self.request.user, memberships__is_active=True)
        ).distinct().select_related('owner').prefetch_related('memberships')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TenantListSerializer
        elif self.action == 'create':
            return TenantCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TenantUpdateSerializer
        return TenantDetailSerializer

    def perform_create(self, serializer):
        """Create tenant and set owner."""
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        """Check permissions for update/delete."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        """Check admin permission for updates."""
        instance = self.get_object()
        if not TenantPermission.is_admin(request.user, instance):
            return Response(
                {'error': '只有管理员可以修改'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Check owner permission for delete."""
        instance = self.get_object()
        if instance.owner != request.user:
            return Response(
                {'error': '只有所有者可以删除'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """Get tenant usage statistics."""
        tenant = self.get_object()

        if not TenantPermission.is_member(request.user, tenant):
            return Response(
                {'error': '不是租户成员'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            usage = tenant.usage
        except TenantUsage.DoesNotExist:
            usage = TenantUsage.objects.create(tenant=tenant)

        serializer = TenantUsageSerializer(usage)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get tenant members."""
        tenant = self.get_object()

        if not TenantPermission.is_member(request.user, tenant):
            return Response(
                {'error': '不是租户成员'},
                status=status.HTTP_403_FORBIDDEN
            )

        memberships = tenant.memberships.filter(is_active=True)
        serializer = TenantMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Invite a user to tenant."""
        tenant = self.get_object()

        if not TenantPermission.is_admin(request.user, tenant):
            return Response(
                {'error': '只有管理员可以邀请'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TenantMembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']

        # Check if already a member
        if TenantMembership.objects.filter(tenant=tenant, user__email=email).exists():
            return Response(
                {'error': '该用户已是租户成员'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check user limit
        current_members = tenant.memberships.filter(is_active=True).count()
        if current_members >= tenant.max_users:
            return Response(
                {'error': '已达到用户数量上限'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create or get invitation
        invitation, created = TenantInvitation.objects.get_or_create(
            tenant=tenant,
            email=email,
            defaults={
                'role': role,
                'invited_by': request.user,
                'token': secrets.token_urlsafe(32),
                'expires_at': timezone.now() + timedelta(days=7)
            }
        )

        if not created:
            # Update existing invitation
            invitation.role = role
            invitation.invited_by = request.user
            invitation.token = secrets.token_urlsafe(32)
            invitation.status = 'pending'
            invitation.expires_at = timezone.now() + timedelta(days=7)
            invitation.save()

        return Response({
            'message': '邀请已发送',
            'invitation': TenantInvitationSerializer(invitation).data
        })

    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """Remove a member from tenant."""
        tenant = self.get_object()
        member_id = request.data.get('member_id')

        if not TenantPermission.is_admin(request.user, tenant):
            return Response(
                {'error': '只有管理员可以移除成员'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            membership = TenantMembership.objects.get(id=member_id, tenant=tenant)
        except TenantMembership.DoesNotExist:
            return Response(
                {'error': '成员不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Can't remove owner
        if membership.role == 'owner':
            return Response(
                {'error': '不能移除所有者'},
                status=status.HTTP_400_BAD_REQUEST
            )

        membership.delete()
        return Response({'message': '成员已移除'})


class TenantMembershipViewSet(viewsets.ModelViewSet):
    """ViewSet for TenantMembership."""

    serializer_class = TenantMembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter memberships for current user."""
        return TenantMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related('tenant', 'user')

    @action(detail=False, methods=['get'])
    def my_memberships(self, request):
        """Get all memberships for current user."""
        memberships = self.get_queryset()
        serializer = TenantMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class TenantInvitationViewSet(viewsets.ModelViewSet):
    """ViewSet for TenantInvitation."""

    serializer_class = TenantInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get invitations for user's tenants."""
        return TenantInvitation.objects.filter(
            Q(tenant__memberships__user=self.request.user) |
            Q(invited_by=self.request.user)
        ).distinct().select_related('tenant', 'invited_by')

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending invitations for current user."""
        invitations = self.get_queryset().filter(
            email=request.user.email,
            status='pending',
            expires_at__gt=timezone.now()
        )
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def join(self, request):
        """Join a tenant with invitation token."""
        serializer = JoinTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        try:
            invitation = TenantInvitation.objects.get(
                token=token,
                status='pending'
            )
        except TenantInvitation.DoesNotExist:
            return Response(
                {'error': '邀请无效或已过期'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if expired
        if invitation.expires_at < timezone.now():
            invitation.status = 'expired'
            invitation.save()
            return Response(
                {'error': '邀请已过期'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check email matches
        if invitation.email != request.user.email:
            return Response(
                {'error': '此邀请不属于您的邮箱'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check user limit
        if invitation.tenant.memberships.filter(is_active=True).count() >= invitation.tenant.max_users:
            return Response(
                {'error': '租户用户数量已达上限'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create membership
        TenantMembership.objects.create(
            tenant=invitation.tenant,
            user=request.user,
            role=invitation.role,
            invited_by=invitation.invited_by
        )

        # Update invitation status
        invitation.status = 'accepted'
        invitation.accepted_at = timezone.now()
        invitation.save()

        return Response({
            'message': '已加入租户',
            'tenant': TenantListSerializer(invitation.tenant).data
        })

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept an invitation."""
        invitation = self.get_object()

        if invitation.email != request.user.email:
            return Response(
                {'error': '此邀请不属于您'},
                status=status.HTTP_403_FORBIDDEN
            )

        if invitation.status != 'pending':
            return Response(
                {'error': '邀请状态无效'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create membership
        TenantMembership.objects.create(
            tenant=invitation.tenant,
            user=request.user,
            role=invitation.role,
            invited_by=invitation.invited_by
        )

        invitation.status = 'accepted'
        invitation.accepted_at = timezone.now()
        invitation.save()

        return Response({
            'message': '已加入租户',
            'tenant': TenantDetailSerializer(invitation.tenant).data
        })

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline an invitation."""
        invitation = self.get_object()

        if invitation.email != request.user.email:
            return Response(
                {'error': '此邀请不属于您'},
                status=status.HTTP_403_FORBIDDEN
            )

        invitation.status = 'declined'
        invitation.save()

        return Response({'message': '已拒绝邀请'})


class TenantUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for TenantUsage."""

    serializer_class = TenantUsageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get usage for user's tenants."""
        return TenantUsage.objects.filter(
            tenant__memberships__user=self.request.user,
            tenant__memberships__is_active=True
        ).select_related('tenant')

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Refresh usage stats."""
        tenant_id = request.data.get('tenant_id')

        try:
            tenant = Tenant.objects.get(
                id=tenant_id,
                memberships__user=request.user,
                memberships__is_active=True
            )
        except Tenant.DoesNotExist:
            return Response(
                {'error': '租户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update usage counts
        from workflows.models import Workflow, WorkflowExecution
        from django.db.models import Count

        usage, _ = TenantUsage.objects.get_or_create(tenant=tenant)

        usage.current_month_workflows = Workflow.objects.filter(
            owner__in=tenant.memberships.values_list('user', flat=True)
        ).count()

        usage.current_month_users = tenant.memberships.filter(is_active=True).count()

        # Count executions this month
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage.current_month_executions = WorkflowExecution.objects.filter(
            workflow__owner__in=tenant.memberships.values_list('user', flat=True),
            started_at__gte=month_start
        ).count()

        usage.save()

        serializer = TenantUsageSerializer(usage)
        return Response(serializer.data)


# ============ Team Skill / Task Assignment Viewsets ============

class TeamSkillPermission:
    """Permission checks for team skills."""

    @staticmethod
    def is_member(user, tenant):
        return TenantMembership.objects.filter(
            user=user, tenant=tenant, is_active=True
        ).exists()

    @staticmethod
    def is_admin(user, tenant):
        return TenantMembership.objects.filter(
            user=user, tenant=tenant, is_active=True,
            role__in=['owner', 'admin']
        ).exists()


class TeamSkillViewSet(viewsets.ModelViewSet):
    """ViewSet for TeamSkill."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamSkillListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TeamSkillCreateSerializer
        return TeamSkillDetailSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return TeamSkill.objects.filter(
                tenant_id=tenant_id,
                tenant__memberships__user=self.request.user,
                tenant__memberships__is_active=True
            ).select_related('tenant', 'created_by').prefetch_related('assignments')
        return TeamSkill.objects.none()

    def create(self, request, *args, **kwargs):
        tenant_id = request.data.get('tenant') or request.query_params.get('tenant_id')
        if not tenant_id:
            return Response({'error': '需要指定团队ID'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not TeamSkillPermission.is_admin(request.user, tenant):
            return Response({'error': '只有管理员可以创建技能'}, status=status.HTTP_403_FORBIDDEN)

        self.check_permissions(request)
        serializer = self.get_serializer(data=request.data)
        serializer.context['tenant'] = tenant
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()
        TeamActivity.objects.create(
            tenant=tenant, user=request.user,
            action='skill_created', target_type='teamskill', target_id=skill.id,
            description=f'创建技能: {skill.name}'
        )
        return Response(TeamSkillDetailSerializer(skill).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not TeamSkillPermission.is_admin(request.user, instance.tenant):
            return Response({'error': '只有管理员可以修改技能'}, status=status.HTTP_403_FORBIDDEN)
        response = super().update(request, *args, **kwargs)
        TeamActivity.objects.create(
            tenant=instance.tenant, user=request.user,
            action='skill_updated', target_type='teamskill', target_id=instance.id,
            description=f'更新技能: {instance.name}'
        )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not TeamSkillPermission.is_admin(request.user, instance.tenant):
            return Response({'error': '只有管理员可以删除技能'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign a skill to a user."""
        skill = self.get_object()
        if not TeamSkillPermission.is_admin(request.user, skill.tenant):
            return Response({'error': '只有管理员可以分配技能'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        role = request.data.get('role', 'contributor')
        proficiency = request.data.get('proficiency_level', 1)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        assignment, _ = SkillAssignment.objects.update_or_create(
            skill=skill, user=user,
            defaults={
                'role': role,
                'proficiency_level': proficiency,
                'assigned_by': request.user,
                'is_active': True
            }
        )
        TeamActivity.objects.create(
            tenant=skill.tenant, user=request.user,
            action='skill_assigned', target_type='teamskill', target_id=skill.id,
            description=f'为用户 {user.username} 分配技能: {skill.name}',
            metadata={'user_id': user.id, 'role': role}
        )
        return Response(SkillAssignmentSerializer(assignment).data)

    @action(detail=True, methods=['post'])
    def unassign(self, request, pk=None):
        """Remove a skill assignment."""
        skill = self.get_object()
        if not TeamSkillPermission.is_admin(request.user, skill.tenant):
            return Response({'error': '只有管理员可以移除分配'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        try:
            assignment = SkillAssignment.objects.get(skill=skill, user_id=user_id)
            assignment.delete()
            return Response({'message': '已移除技能分配'})
        except SkillAssignment.DoesNotExist:
            return Response({'error': '分配记录不存在'}, status=status.HTTP_404_NOT_FOUND)


class TeamTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for TeamTask."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamTaskListSerializer
        elif self.action == 'create':
            return TeamTaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TeamTaskUpdateSerializer
        return TeamTaskDetailSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            qs = TeamTask.objects.filter(
                tenant_id=tenant_id,
                tenant__memberships__user=self.request.user,
                tenant__memberships__is_active=True
            ).select_related('tenant', 'owner', 'created_by', 'linked_skill').prefetch_related('task_assignees__user')
            if self.request.query_params.get('status'):
                qs = qs.filter(status=self.request.query_params.get('status'))
            if self.request.query_params.get('priority'):
                qs = qs.filter(priority=self.request.query_params.get('priority'))
            if self.request.query_params.get('assignee_id'):
                qs = qs.filter(task_assignees__user_id=self.request.query_params.get('assignee_id'))
            return qs.distinct()
        return TeamTask.objects.none()

    def create(self, request, *args, **kwargs):
        tenant_id = request.data.get('tenant') or request.query_params.get('tenant_id')
        if not tenant_id:
            return Response({'error': '需要指定团队ID'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not TeamSkillPermission.is_member(request.user, tenant):
            return Response({'error': '您不是团队成员'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.context['tenant'] = tenant
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        TeamActivity.objects.create(
            tenant=tenant, user=request.user,
            action='task_created', target_type='teamtask', target_id=task.id,
            description=f'创建任务: {task.title}'
        )
        return Response(TeamTaskDetailSerializer(task).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status
        response = super().update(request, *args, **kwargs)

        if old_status != instance.status and instance.status == 'done':
            from django.utils import timezone
            instance.completed_at = timezone.now()
            instance.save()
            TeamActivity.objects.create(
                tenant=instance.tenant, user=request.user,
                action='task_completed', target_type='teamtask', target_id=instance.id,
                description=f'完成任务: {instance.title}'
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not TeamSkillPermission.is_admin(request.user, instance.tenant):
            return Response({'error': '只有管理员可以删除任务'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def assign_user(self, request, pk=None):
        """Assign a user to the task."""
        task = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'contributor')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        assignment, _ = TaskAssignee.objects.update_or_create(
            task=task, user=user,
            defaults={'assigned_by': request.user, 'role': role}
        )
        TeamActivity.objects.create(
            tenant=task.tenant, user=request.user,
            action='task_assigned', target_type='teamtask', target_id=task.id,
            description=f'为用户 {user.username} 分配任务: {task.title}',
            metadata={'user_id': user.id}
        )
        return Response(TaskAssigneeSerializer(assignment).data)

    @action(detail=True, methods=['post'])
    def unassign_user(self, request, pk=None):
        """Remove a user from the task."""
        task = self.get_object()
        user_id = request.data.get('user_id')
        try:
            assignee = TaskAssignee.objects.get(task=task, user_id=user_id)
            assignee.delete()
            return Response({'message': '已移除任务分配'})
        except TaskAssignee.DoesNotExist:
            return Response({'error': '分配记录不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change task status."""
        task = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(TeamTask.STATUS_CHOICES):
            return Response({'error': '无效的状态值'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = task.status
        task.status = new_status

        if new_status == 'done':
            from django.utils import timezone
            task.completed_at = timezone.now()
            task.progress = 100

        task.save()
        TeamActivity.objects.create(
            tenant=task.tenant, user=request.user,
            action='task_updated', target_type='teamtask', target_id=task.id,
            description=f'更新任务状态: {task.title} ({old_status} -> {new_status})'
        )
        return Response(TeamTaskDetailSerializer(task).data)


class TeamActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for TeamActivity."""

    serializer_class = TeamActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            qs = TeamActivity.objects.filter(
                tenant_id=tenant_id,
                tenant__memberships__user=self.request.user,
                tenant__memberships__is_active=True
            ).select_related('tenant', 'user')
            if self.request.query_params.get('action'):
                qs = qs.filter(action=self.request.query_params.get('action'))
            return qs[:100]
        return TeamActivity.objects.none()
