"""
Serializers for tenants app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tenant, TenantMembership, TenantInvitation, TenantUsage, TeamSkill, SkillAssignment, TeamTask, TaskAssignee, TeamActivity

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """Simple user serializer."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar']


class TenantMembershipSerializer(serializers.ModelSerializer):
    """Serializer for TenantMembership."""

    user = UserSimpleSerializer(read_only=True)
    invited_by_name = serializers.CharField(source='invited_by.username', read_only=True)

    class Meta:
        model = TenantMembership
        fields = [
            'id', 'user', 'role', 'permissions', 'is_active',
            'joined_at', 'invited_by_name'
        ]


class TenantUsageSerializer(serializers.ModelSerializer):
    """Serializer for TenantUsage."""

    workflow_limit = serializers.IntegerField(source='tenant.max_workflows', read_only=True)
    execution_limit = serializers.IntegerField(source='tenant.max_executions_per_month', read_only=True)
    user_limit = serializers.IntegerField(source='tenant.max_users', read_only=True)

    workflows_remaining = serializers.SerializerMethodField()
    executions_remaining = serializers.SerializerMethodField()
    users_remaining = serializers.SerializerMethodField()

    class Meta:
        model = TenantUsage
        fields = [
            'current_month_workflows', 'current_month_executions', 'current_month_users',
            'total_workflows_created', 'total_executions', 'total_api_calls',
            'total_tokens_used', 'last_reset_at',
            'workflow_limit', 'execution_limit', 'user_limit',
            'workflows_remaining', 'executions_remaining', 'users_remaining'
        ]

    def get_workflows_remaining(self, obj):
        return max(0, obj.tenant.max_workflows - obj.current_month_workflows)

    def get_executions_remaining(self, obj):
        return max(0, obj.tenant.max_executions_per_month - obj.current_month_executions)

    def get_users_remaining(self, obj):
        return max(0, obj.tenant.max_users - obj.current_month_users)


class TenantListSerializer(serializers.ModelSerializer):
    """Serializer for Tenant list view."""

    owner = UserSimpleSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'description', 'status', 'plan',
            'owner', 'custom_domain', 'member_count',
            'max_users', 'max_workflows', 'max_executions_per_month',
            'subscription_end', 'created_at'
        ]

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class TenantDetailSerializer(serializers.ModelSerializer):
    """Serializer for Tenant detail view."""

    owner = UserSimpleSerializer(read_only=True)
    memberships = TenantMembershipSerializer(many=True, read_only=True)
    usage = TenantUsageSerializer(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'description', 'status', 'plan',
            'owner', 'settings', 'custom_domain',
            'max_users', 'max_workflows', 'max_executions_per_month',
            'billing_email', 'subscription_id', 'subscription_end',
            'memberships', 'usage',
            'created_at', 'updated_at'
        ]


class TenantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Tenant."""

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'description',
            'billing_email', 'custom_domain'
        ]

    def validate_slug(self, value):
        """Validate slug is unique."""
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError('此标识已被使用')
        return value

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        tenant = Tenant.objects.create(**validated_data)

        # Create membership for owner
        TenantMembership.objects.create(
            tenant=tenant,
            user=validated_data['owner'],
            role='owner'
        )

        # Create usage record
        TenantUsage.objects.create(tenant=tenant)

        return tenant


class TenantUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Tenant."""

    class Meta:
        model = Tenant
        fields = [
            'name', 'description', 'status', 'plan',
            'settings', 'custom_domain',
            'max_users', 'max_workflows', 'max_executions_per_month',
            'billing_email'
        ]


class TenantMembershipCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating TenantMembership."""

    email = serializers.EmailField(write_only=True)

    class Meta:
        model = TenantMembership
        fields = ['email', 'role']

    def validate_email(self, value):
        """Validate email belongs to existing user."""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('该邮箱的用户不存在')
        return value


class TenantInvitationSerializer(serializers.ModelSerializer):
    """Serializer for TenantInvitation."""

    invited_by_name = serializers.CharField(source='invited_by.username', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = TenantInvitation
        fields = [
            'id', 'tenant', 'tenant_name', 'email', 'role',
            'invited_by', 'invited_by_name', 'status',
            'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'invited_by', 'status', 'created_at']


class JoinTenantSerializer(serializers.Serializer):
    """Serializer for joining a tenant with invitation."""

    token = serializers.CharField(required=True)


# ============ Team Skill / Task Assignment Serializers ============

class SkillAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for SkillAssignment."""

    user = UserSimpleSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True, allow_null=True)

    class Meta:
        model = SkillAssignment
        fields = [
            'id', 'skill', 'user', 'user_id', 'role',
            'proficiency_level', 'assigned_by', 'assigned_by_name',
            'assigned_at', 'is_active'
        ]
        read_only_fields = ['id', 'assigned_by', 'assigned_at']


class TeamSkillListSerializer(serializers.ModelSerializer):
    """Serializer for TeamSkill list view."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assignee_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    class Meta:
        model = TeamSkill
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'keywords', 'mastery_level', 'status', 'status_display',
            'assignee_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]

    def get_assignee_count(self, obj):
        return obj.assignments.filter(is_active=True).count()


class TeamSkillDetailSerializer(serializers.ModelSerializer):
    """Serializer for TeamSkill detail view with assignments."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assignments = SkillAssignmentSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    class Meta:
        model = TeamSkill
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'keywords', 'node_types', 'instructions', 'examples',
            'mastery_level', 'status', 'status_display',
            'assignments', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]


class TeamSkillCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating TeamSkill."""

    class Meta:
        model = TeamSkill
        fields = [
            'id', 'name', 'description', 'category',
            'keywords', 'node_types', 'instructions', 'examples',
            'mastery_level', 'status'
        ]

    def create(self, validated_data):
        validated_data['tenant'] = self.context['tenant']
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskAssigneeSerializer(serializers.ModelSerializer):
    """Serializer for TaskAssignee."""

    user = UserSimpleSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True, allow_null=True)

    class Meta:
        model = TaskAssignee
        fields = [
            'id', 'user', 'user_id', 'role',
            'assigned_at', 'assigned_by', 'assigned_by_name'
        ]


class TeamTaskListSerializer(serializers.ModelSerializer):
    """Serializer for TeamTask list view."""

    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True, allow_null=True)
    linked_skill_name = serializers.CharField(source='linked_skill.name', read_only=True, allow_null=True)
    assignee_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = TeamTask
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'linked_skill', 'linked_skill_name',
            'status', 'status_display',
            'priority', 'priority_display',
            'due_date', 'owner', 'owner_name',
            'progress', 'assignee_count',
            'is_overdue', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'completed_at'
        ]

    def get_assignee_count(self, obj):
        return obj.task_assignees.count()

    def get_is_overdue(self, obj):
        from django.utils import timezone
        if obj.due_date and obj.status not in ['done', 'cancelled']:
            return obj.due_date < timezone.now()
        return False


class TeamTaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for TeamTask detail view with assignees."""

    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    owner = UserSimpleSerializer(read_only=True)
    linked_skill = TeamSkillListSerializer(read_only=True)
    task_assignees = TaskAssigneeSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = TeamTask
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'linked_skill',
            'status', 'status_display',
            'priority', 'priority_display',
            'due_date', 'owner', 'progress',
            'task_assignees',
            'is_overdue', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'completed_at'
        ]

    def get_is_overdue(self, obj):
        from django.utils import timezone
        if obj.due_date and obj.status not in ['done', 'cancelled']:
            return obj.due_date < timezone.now()
        return False


class TeamTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating TeamTask."""

    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    owner_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = TeamTask
        fields = [
            'id', 'title', 'description', 'category',
            'linked_skill', 'status', 'priority',
            'due_date', 'owner_id', 'assignee_ids', 'progress'
        ]

    def create(self, validated_data):
        assignee_ids = validated_data.pop('assignee_ids', [])
        owner_id = validated_data.pop('owner_id', None)
        validated_data['tenant'] = self.context['tenant']
        validated_data['created_by'] = self.context['request'].user

        if owner_id:
            try:
                validated_data['owner'] = User.objects.get(id=owner_id)
            except User.DoesNotExist:
                pass

        task = TeamTask.objects.create(**validated_data)

        for uid in assignee_ids:
            try:
                user = User.objects.get(id=uid)
                TaskAssignee.objects.create(
                    task=task,
                    user=user,
                    assigned_by=self.context['request'].user
                )
            except User.DoesNotExist:
                continue

        return task


class TeamTaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating TeamTask."""

    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    owner_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = TeamTask
        fields = [
            'title', 'description', 'category',
            'linked_skill', 'status', 'priority',
            'due_date', 'owner_id', 'assignee_ids', 'progress',
            'completed_at'
        ]

    def update(self, instance, validated_data):
        assignee_ids = validated_data.pop('assignee_ids', None)
        owner_id = validated_data.pop('owner_id', None)

        if assignee_ids is not None:
            instance.task_assignees.all().delete()
            for uid in assignee_ids:
                try:
                    user = User.objects.get(id=uid)
                    TaskAssignee.objects.create(
                        task=instance,
                        user=user,
                        assigned_by=self.context['request'].user
                    )
                except User.DoesNotExist:
                    continue

        if owner_id is not None:
            if owner_id:
                try:
                    instance.owner = User.objects.get(id=owner_id)
                except User.DoesNotExist:
                    pass
            else:
                instance.owner = None

        return super().update(instance, validated_data)


class TeamActivitySerializer(serializers.ModelSerializer):
    """Serializer for TeamActivity."""

    user = UserSimpleSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = TeamActivity
        fields = [
            'id', 'user', 'action', 'action_display',
            'target_type', 'target_id', 'description',
            'metadata', 'created_at'
        ]
