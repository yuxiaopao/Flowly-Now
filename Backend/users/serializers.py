"""
User authentication serializers.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
from .constants import (
    AVATAR_SHAPES, AVATAR_COLORS, AVATAR_EXPRESSIONS, AVATAR_STATES,
    AVATAR_MAX_BLOCKS, AVATAR_MIN_DURATION, AVATAR_MAX_DURATION,
)


def validate_account_password(password, user):
    from admin.models import SystemSetting
    from django.contrib.auth.password_validation import MinimumLengthValidator
    validate_password(password, user)
    MinimumLengthValidator(SystemSetting.get('password_min_length', 8)).validate(password, user)


def validate_unique_email(value, user_id=None):
    value = value.strip().lower()
    users = User.objects.filter(email__iexact=value)
    if user_id is not None:
        users = users.exclude(pk=user_id)
    if users.exists():
        raise serializers.ValidationError('此邮箱已注册，请登录或找回密码')
    return value


class AvatarBlockSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=AVATAR_STATES)
    duration = serializers.FloatField(min_value=AVATAR_MIN_DURATION, max_value=AVATAR_MAX_DURATION)

    def validate_duration(self, value):
        from math import isfinite
        if not isfinite(value):
            raise serializers.ValidationError('动画时长必须是有限数值')
        return value


class AvatarPreferencesSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=('robot', 'image'), required=False)
    shape = serializers.ChoiceField(choices=AVATAR_SHAPES, required=False)
    color = serializers.ChoiceField(choices=AVATAR_COLORS, required=False)
    expression = serializers.ChoiceField(choices=AVATAR_EXPRESSIONS, required=False)
    blocks = AvatarBlockSerializer(many=True, max_length=AVATAR_MAX_BLOCKS, required=False)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    avatar_preferences = AvatarPreferencesSerializer(required=False)

    def validate_avatar_preferences(self, value):
        image = self.initial_data.get('avatar') if 'avatar' in self.initial_data else getattr(self.instance, 'avatar', '')
        if value.get('mode') == 'image' and not image:
            raise serializers.ValidationError('请先上传头像图片')
        return value

    def update(self, instance, validated_data):
        from django.db import transaction
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=instance.pk)
            preferences = validated_data.pop('avatar_preferences', None)
            if preferences is not None:
                validated_data['avatar_preferences'] = {**user.avatar_preferences, **preferences}
            elif 'avatar' in validated_data:
                validated_data['avatar_preferences'] = {**user.avatar_preferences, 'mode': 'image' if validated_data['avatar'] else 'robot'}
            for field, value in validated_data.items():
                setattr(user, field, value)
            if validated_data:
                user.save(update_fields=[*validated_data, 'updated_at'])
            return user

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError('请输入邮箱地址')
        return validate_unique_email(value, self.instance.pk if self.instance else None)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'avatar', 'avatar_preferences', 'role', 'phone', 'bio',
            'is_staff', 'is_superuser',
            'default_model', 'total_executions', 'monthly_executions',
            'execution_limit', 'created_at', 'last_login_at'
        ]
        read_only_fields = [
            'id', 'role', 'is_staff', 'is_superuser',
            'total_executions', 'monthly_executions',
            'execution_limit', 'created_at', 'last_login_at'
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    agree_terms = serializers.BooleanField(write_only=True, required=False, default=False)
    email = serializers.EmailField(required=True)

    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'agree_terms'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': '两次输入的密码不一致'
            })
        try:
            validate_account_password(attrs['password'], User(**{key: value for key, value in attrs.items()
                                                       if key not in ('password_confirm', 'agree_terms')}))
        except ValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages}) from exc
        return attrs

    def validate_email(self, value):
        return validate_unique_email(value)

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.pop('agree_terms', None)
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Support both username and email login
        auth_kwargs = {'password': password}
        if '@' in username and not User.objects.filter(username=username).exists():
            # Input looks like an email, find the user by email first
            try:
                user_obj = User.objects.get(email__iexact=username)
                auth_kwargs['username'] = user_obj.username
            except User.DoesNotExist:
                auth_kwargs['username'] = username
            except User.MultipleObjectsReturned:
                raise serializers.ValidationError('此邮箱关联多个账号，请使用用户名登录') from None
        else:
            auth_kwargs['username'] = username

        user = authenticate(
            request=self.context.get('request'),
            **auth_kwargs
        )

        if not user:
            raise serializers.ValidationError('用户名或密码错误')

        if not user.is_active:
            raise serializers.ValidationError('用户已被禁用')

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': '两次输入的密码不一致'
            })
        return attrs

    def validate_new_password(self, value):
        validate_account_password(value, self.context['request'].user)
        return value

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('原密码错误')
        return value


class TokenSerializer(serializers.Serializer):
    """Serializer for token response."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField(required=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )
