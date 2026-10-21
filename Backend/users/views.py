"""
User authentication views.
"""

from rest_framework import status, generics, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.authtoken.models import Token
from django.contrib.auth import update_session_auth_hash, logout
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.db import transaction
import logging
from .serializers import (
    UserSerializer, UserCreateSerializer, LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, validate_account_password
)
from .authentication import generate_tokens, verify_refresh_token, revoke_session
from .models import User

logger = logging.getLogger(__name__)


# =============================================================================
# Audit logging helpers
# =============================================================================
def _log_audit(user, action, resource_type, resource_id, request, status_val='success', error_message=None):
    """Log an audit event. Import here to avoid circular imports."""
    try:
        from workflows.models import AuditLog
        with transaction.atomic():
            AuditLog.objects.create(
                user=user,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id or '',
                status=status_val,
                error_message=error_message or '',
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
            )
    except Exception:
        logger.exception('审计日志写入失败：%s %s', action, resource_type)

def _get_client_ip(request):
    """Extract client IP from request, handling proxies."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        from admin.models import UserTermsAcceptance
        from admin.services.config_service import get_active_legal_document
        from admin.models import SystemSetting

        if not SystemSetting.get('allow_registration', True):
            return Response(
                {'error': '系统当前不允许新用户注册'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        terms_version = request.data.get('terms_version')
        privacy_version = request.data.get('privacy_version')
        agree_terms = serializer.validated_data['agree_terms']

        if SystemSetting.get('require_terms_on_register', True):
            if not agree_terms:
                return Response(
                    {'error': '请先阅读并同意服务条款与隐私政策'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            terms_doc = get_active_legal_document('terms')
            privacy_doc = get_active_legal_document('privacy')
            if terms_doc and terms_version != terms_doc.version:
                return Response(
                    {'error': '服务条款版本已更新，请刷新页面后重新确认'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if privacy_doc and privacy_version != privacy_doc.version:
                return Response(
                    {'error': '隐私政策版本已更新，请刷新页面后重新确认'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user = serializer.save()

        default_role = SystemSetting.get('default_role', 'user')
        if default_role in ('admin', 'developer', 'user'):
            user.role = default_role
            user.execution_limit = SystemSetting.get('default_execution_limit', 1000)
            user.save(update_fields=['role', 'execution_limit'])

        client_ip = _get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        for doc in ([get_active_legal_document('terms'), get_active_legal_document('privacy')] if agree_terms else []):
            if doc:
                UserTermsAcceptance.objects.create(
                    user=user,
                    document=doc,
                    document_version=doc.version,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )

        tokens = generate_tokens(user)
        user_serializer = UserSerializer(user)

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': user_serializer.data
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """User login endpoint."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            _log_audit(
                user=None,
                action='login_failure',
                resource_type='user',
                resource_id=serializer.initial_data.get('username', ''),
                request=request,
                status_val='failure',
                error_message=str(serializer.errors)
            )
            return Response({'errors': serializer.errors}, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data['user']
        tokens = generate_tokens(user)
        user_serializer = UserSerializer(user)

        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])

        _log_audit(
            user=user,
            action='login',
            resource_type='user',
            resource_id=str(user.id),
            request=request,
            status_val='success'
        )

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': user_serializer.data
        })


class TokenRefreshView(APIView):
    """Refresh access token using refresh token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payload = verify_refresh_token(refresh_token)

        if not payload:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        tokens = generate_tokens(user, session_id=payload['sid'])
        user_serializer = UserSerializer(user)

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': user_serializer.data
        })


class LogoutView(APIView):
    """User logout endpoint."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if isinstance(request.auth, str):
            revoke_session(request.auth)
        elif isinstance(request.auth, Token):
            request.auth.delete()
        logout(request)

        return Response({'message': '登出成功'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update current user profile."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Change user password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        # Update session to prevent logout
        update_session_auth_hash(request, request.user)

        Token.objects.filter(user=request.user).delete()
        return Response({'message': '密码修改成功', **generate_tokens(request.user)})


class PasswordResetRequestView(APIView):
    """Request password reset email."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            if not user.has_usable_password():
                return Response({'message': '如果邮箱存在，您将收到重置链接，请同时检查垃圾邮件。'})

            # Generate password reset token
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Build reset URL
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uidb64}&token={token}"

            # Send email
            subject = '重置您的 Flowly 密码'
            message = f"""
您好 {user.username}，

您收到此邮件是因为请求重置 Flowly 账户的密码。

请点击以下链接重置您的密码：
{reset_url}

此链接将在 {settings.PASSWORD_RESET_TIMEOUT // 60} 分钟后过期，使用后立即失效。

如果您没有请求重置密码，请忽略此邮件。

谢谢，
Flowly 团队
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Don't reveal that the email doesn't exist
            pass
        except Exception:
            logger.exception('密码重置邮件发送失败')
            return Response({'error': '邮件服务暂时不可用，请稍后重试或联系管理员'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Always return success to prevent email enumeration
        return Response({
            'message': ('当前为本地测试环境，重置邮件仅记录在服务端日志，未发送到邮箱。'
                        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
                        else '如果邮箱存在，您将收到重置链接，请同时检查垃圾邮件。')
        })


class PasswordResetConfirmView(APIView):
    """Confirm password reset with token."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.select_for_update().get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': '无效的重置链接'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify token
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': '重置链接已过期，请重新申请'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_account_password(new_password, user)
        except ValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.messages}) from exc

        # Set new password; password-bound JWTs and existing sessions expire.
        user.set_password(new_password)
        user.save()
        Token.objects.filter(user=user).delete()

        return Response({
            'message': '密码重置成功'
        })

