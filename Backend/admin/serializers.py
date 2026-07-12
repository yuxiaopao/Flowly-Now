"""
Admin API serializers for user and tenant management.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import User
from tenants.models import Tenant, TenantMembership, TenantUsage


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating users from the admin panel."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    is_superuser = serializers.BooleanField(required=False, default=False)
    tenant_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'is_superuser', 'tenant_id']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError('邮箱已被使用')
        return value

    def validate_tenant_id(self, value):
        if value is not None and not Tenant.objects.filter(pk=value).exists():
            raise serializers.ValidationError('租户不存在')
        return value

    def create(self, validated_data):
        tenant_id = validated_data.pop('tenant_id', None)
        is_superuser = validated_data.pop('is_superuser', False)
        password = validated_data.pop('password')

        user = User.objects.create_user(password=password, **validated_data)
        if is_superuser:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=['is_superuser', 'is_staff'])
        elif user.role == 'admin':
            user.is_staff = True
            user.save(update_fields=['is_staff'])

        if tenant_id:
            TenantMembership.objects.get_or_create(
                tenant_id=tenant_id,
                user=user,
                defaults={'role': 'member'}
            )
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating users from the admin panel."""

    is_superuser = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = ['email', 'role', 'is_active', 'is_superuser', 'phone']

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('邮箱已被使用')
        return value

    def update(self, instance, validated_data):
        is_superuser = validated_data.pop('is_superuser', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if is_superuser is not None:
            instance.is_superuser = is_superuser
            if is_superuser:
                instance.is_staff = True
        instance.is_staff = instance.is_staff or instance.role == 'admin'
        instance.save()
        return instance


class AdminResetPasswordSerializer(serializers.Serializer):
    """Serializer for admin-initiated password resets."""

    password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )


class AdminTenantSerializer(serializers.ModelSerializer):
    """Serializer for listing tenants in the admin panel."""

    owner_username = serializers.CharField(source='owner.username', read_only=True)
    current_users = serializers.SerializerMethodField()
    current_workflows = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'description', 'status', 'plan',
            'owner', 'owner_username',
            'max_users', 'max_workflows', 'max_executions_per_month',
            'current_users', 'current_workflows',
            'billing_email', 'subscription_end',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_current_users(self, obj):
        return obj.memberships.filter(is_active=True).count()

    def get_current_workflows(self, obj):
        return obj.workflows.count()


class AdminTenantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tenants from the admin panel."""

    owner_id = serializers.IntegerField(required=True)

    class Meta:
        model = Tenant
        fields = [
            'name', 'slug', 'description', 'plan', 'status', 'owner_id',
            'max_users', 'max_workflows', 'max_executions_per_month',
            'billing_email'
        ]
        extra_kwargs = {
            'billing_email': {'required': False, 'allow_blank': True},
            'status': {'required': False},
        }

    def validate_slug(self, value):
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError('此标识已被使用')
        return value

    def validate_owner_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError('所有者不存在')
        return value

    def create(self, validated_data):
        owner = User.objects.get(pk=validated_data.pop('owner_id'))
        if not validated_data.get('billing_email'):
            validated_data['billing_email'] = owner.email or ''
        tenant = Tenant.objects.create(owner=owner, **validated_data)

        TenantMembership.objects.create(tenant=tenant, user=owner, role='owner')
        TenantUsage.objects.create(tenant=tenant)
        return tenant


class AdminTenantUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tenants from the admin panel."""

    class Meta:
        model = Tenant
        fields = [
            'name', 'description', 'plan', 'status',
            'max_users', 'max_workflows', 'max_executions_per_month',
            'billing_email', 'subscription_end'
        ]


# ─── Platform config module serializers ───

from .models import (
    BackupRecord,
    EmailSendLog,
    FeatureVisibilityRule,
    GatewayRouteRule,
    LegalDocument,
    PaymentProviderConfig,
    UserTermsAcceptance,
)


class LegalDocumentSerializer(serializers.ModelSerializer):
    acceptance_count = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = [
            'id', 'doc_type', 'version', 'title', 'content_html',
            'content_markdown', 'is_active', 'require_acceptance',
            'effective_at', 'created_at', 'updated_at', 'acceptance_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'acceptance_count']

    def get_acceptance_count(self, obj):
        return getattr(obj, 'acceptance_count', obj.acceptances.count())

    def validate(self, attrs):
        doc_type = attrs.get('doc_type', getattr(self.instance, 'doc_type', None))
        version = attrs.get('version', getattr(self.instance, 'version', None))
        if doc_type and version:
            qs = LegalDocument.objects.filter(doc_type=doc_type, version=version)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'version': '该类型下版本号已存在'})
        return attrs


class UserTermsAcceptanceSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = UserTermsAcceptance
        fields = [
            'id', 'user', 'username', 'document', 'document_title',
            'document_version', 'ip_address', 'accepted_at',
        ]
        read_only_fields = fields


class FeatureVisibilityRuleSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, default='')

    class Meta:
        model = FeatureVisibilityRule
        fields = [
            'id', 'feature_key', 'scope', 'role', 'group', 'group_name',
            'is_visible', 'is_enabled', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GatewayRouteRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayRouteRule
        fields = [
            'id', 'name', 'path_pattern', 'target_service', 'methods',
            'rate_limit_per_minute', 'is_enabled', 'priority', 'config',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProviderConfig
        fields = [
            'id', 'provider', 'display_name', 'is_enabled', 'config',
            'fee_rate', 'refund_rules', 'sort_order', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailSendLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSendLog
        fields = [
            'id', 'to_email', 'subject', 'template_key', 'status',
            'error_message', 'sent_at', 'created_at',
        ]
        read_only_fields = fields


class BackupRecordSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = BackupRecord
        fields = [
            'id', 'name', 'file_path', 'backup_type', 'size', 'status',
            'include_media', 'error_message', 'created_by', 'created_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by_name']


class TestEmailSerializer(serializers.Serializer):
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=500, default='Flowly 邮件测试')
    message = serializers.CharField(default='这是一封来自 Flowly 管理端的测试邮件。')

