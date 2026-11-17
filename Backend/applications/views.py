"""Small-team application draft/test/release/invoke HTTP contract."""
from config.application_messages import MESSAGES
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.authentication import JWTAuthentication

from .access import visible_applications, can_edit, can_publish, team_role
from .authentication import ApplicationKeyAuthentication
from .constants import OVERVIEW_DAYS
from .models import Application, ApplicationRelease, ApplicationAPIKey, ApplicationRequest
from .serializers import (ApplicationSerializer, ApplicationWriteSerializer, ReleaseSerializer,
    InvocationSerializer, APIKeySerializer, APIKeyCreateSerializer, RequestSerializer)
from .services import ApplicationFailure, publish_application, run_application, recover_expired_requests, reconcile_pending_tests
from .evaluation_views import ApplicationEvaluationActions


class ApplicationViewSet(ApplicationEvaluationActions, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ApplicationKeyAuthentication, TokenAuthentication, SessionAuthentication, JWTAuthentication]
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    def handle_exception(self, exc):
        if isinstance(exc, ApplicationFailure):
            return Response({'code': exc.status, 'message': str(exc), 'data': None, 'errors': {'reason': exc.code}}, status=exc.status)
        return super().handle_exception(exc)

    def get_queryset(self):
        qs = visible_applications(self.request.user).select_related('tenant', 'owner', 'active_release__validated_by_request').annotate(release_count=Count('releases', distinct=True))
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        for key in ('kind', 'tenant_id'):
            value = self.request.query_params.get(key)
            if value:
                if key == 'tenant_id' and not value.isdecimal():
                    raise ValidationError({'tenant_id': MESSAGES['integer']})
                qs = qs.filter(**{key: value})
        state = self.request.query_params.get('status')
        if state:
            if state == 'published':
                qs = qs.filter(active_release__isnull=False)
            elif state in ('draft', 'unpublished'):
                qs = qs.filter(active_release__isnull=True, release_count=0) if state == 'draft' else qs.filter(active_release__isnull=True, release_count__gt=0)
            else:
                raise ValidationError({'status': MESSAGES['status']})
        return qs.order_by('-updated_at')

    def get_serializer_class(self):
        return ApplicationWriteSerializer if self.action in ('create', 'update', 'partial_update') else ApplicationSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(ApplicationSerializer(serializer.instance, context=self.get_serializer_context()).data, status=201)

    def update(self, request, *args, **kwargs):
        existing = self.get_object()
        with transaction.atomic():
            instance = Application.objects.select_for_update().select_related('owner', 'tenant').get(pk=existing.pk)
            self.require_edit(instance)
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(ApplicationSerializer(serializer.instance, context=self.get_serializer_context()).data)

    def require_edit(self, application, publishing=False):
        if not (can_publish(self.request.user, application) if publishing else can_edit(self.request.user, application)):
            raise PermissionDenied(MESSAGES['editor_required'])

    @action(detail=True, methods=['get'])
    def readiness(self, request, pk=None):
        from .readiness import application_readiness
        return Response(application_readiness(self.get_object()))

    def perform_destroy(self, instance):
        self.require_edit(instance, publishing=True)
        with transaction.atomic():
            locked = Application.objects.select_for_update().get(pk=instance.pk)
            locked.is_deleted, locked.active_release = True, None
            locked.save(update_fields=['is_deleted', 'active_release', 'updated_at'])
            locked.api_keys.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())

    def paginate_values(self, values, serializer):
        page = self.paginate_queryset(values)
        if page is not None:
            return self.get_paginated_response(serializer(page, many=True, context=self.get_serializer_context()).data)
        return Response(serializer(values, many=True, context=self.get_serializer_context()).data)

    @action(detail=False, methods=['get'])
    def resources(self, request):
        from tenants.models import Tenant
        kind = request.query_params.get('kind')
        if kind not in ('knowledge', 'workflow'):
            raise ValidationError({'kind': MESSAGES['choose_kind']})
        tenant_id = request.query_params.get('tenant_id')
        if tenant_id:
            if not tenant_id.isdecimal():
                raise ValidationError({'tenant_id': MESSAGES['integer']})
            tenant = get_object_or_404(Tenant, pk=tenant_id)
            if team_role(request.user, tenant) not in ('owner', 'admin', 'member'):
                raise PermissionDenied()

        if kind == 'knowledge':
            from rag.models import DocumentCollection
            qs = DocumentCollection.objects.all()
        else:
            from workflows.models import Workflow
            qs = Workflow.objects.filter(is_deleted=False)
        qs = qs.filter(tenant_id=tenant_id) if tenant_id else qs.filter(owner=request.user, tenant__isnull=True)
        values = qs.order_by('name').values('id', 'name')
        page = self.paginate_queryset(values)
        return self.get_paginated_response(list(page)) if page is not None else Response(list(values))

    @action(detail=False, methods=['get'])
    def overview(self, request):
        applications = visible_applications(request.user).select_related('owner', 'tenant', 'active_release__validated_by_request').annotate(release_count=Count('releases', distinct=True))
        records = ApplicationRequest.objects.filter(application__in=applications, created_at__gte=timezone.now() - timedelta(days=OVERVIEW_DAYS))
        finished = records.filter(status__in=('completed', 'failed'))
        finished_count = finished.count()
        completed = finished.filter(status='completed').count()
        usage_complete = bool(finished_count) and not finished.filter(total_tokens__isnull=True).exists()
        cost_complete = bool(finished_count) and not finished.filter(cost__isnull=True).exists()
        summary = {
            'application_count': applications.count(),
            'published_count': applications.filter(active_release__isnull=False).count(),
            'draft_count': applications.filter(active_release__isnull=True).count(),
            'request_count': records.count(), 'failed_count': records.filter(status__in=('failed', 'rejected')).count(),
            'success_rate': completed / finished_count if finished_count else None,
            'avg_latency_ms': finished.aggregate(value=Avg('latency_ms'))['value'],
            'total_tokens': finished.aggregate(value=Sum('total_tokens'))['value'] if usage_complete else None,
            'total_cost': finished.aggregate(value=Sum('cost'))['value'] if cost_complete else None,
            'usage_complete': usage_complete and cost_complete,
            'recent_applications': ApplicationSerializer(applications.order_by('-updated_at')[:6], many=True, context=self.get_serializer_context()).data,
            'recent_requests': RequestSerializer(records.order_by('-created_at')[:8], many=True).data,
        }
        return Response(summary)

    def execution_response(self, record, status_code):
        data = RequestSerializer(record).data
        if status_code >= 400:
            return Response({'code': status_code, 'message': record.error_message, 'data': data, 'errors': {'reason': record.error_code}}, status=status_code)
        return Response(data, status=status_code)

    def perform_execution(self, request, mode):
        application = self.get_object()
        self.require_edit(application)
        serializer = InvocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = request.auth if isinstance(request.auth, ApplicationAPIKey) else None
        token = request.headers.get('Idempotency-Key')
        if token is not None and (not token.strip() or len(token) > 128):
            raise ValidationError({'Idempotency-Key': MESSAGES['idempotency_length']})
        record, status_code = run_application(application, request.user, serializer.validated_data['input_data'], mode, key, token)
        return self.execution_response(record, status_code)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        return self.perform_execution(request, 'test')

    @action(detail=True, methods=['post'])
    def invoke(self, request, pk=None):
        return self.perform_execution(request, 'invoke')

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        if request.data:
            raise ValidationError({'publish': MESSAGES['configuration_fields']})
        application = self.get_object()
        self.require_edit(application, publishing=True)
        release = publish_application(application, request.user)
        return Response(ReleaseSerializer(release).data, status=201)

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        application = self.get_object()
        self.require_edit(application, publishing=True)
        if set(request.data) != {'release_id'}:
            raise ValidationError({'release_id': MESSAGES['release_id']})
        from rest_framework.serializers import UUIDField
        release_id = UUIDField().run_validation(request.data.get('release_id'))
        with transaction.atomic():
            locked = Application.objects.select_for_update().get(pk=application.pk)
            release = get_object_or_404(ApplicationRelease, pk=release_id, application=locked)
            locked.active_release = release
            locked.save(update_fields=['active_release', 'updated_at'])
        return Response(ApplicationSerializer(locked, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        application = self.get_object()
        self.require_edit(application, publishing=True)
        with transaction.atomic():
            locked = Application.objects.select_for_update().get(pk=application.pk)
            locked.active_release = None
            locked.save(update_fields=['active_release', 'updated_at'])
        return Response(ApplicationSerializer(locked, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['get'])
    def releases(self, request, pk=None):
        return self.paginate_values(self.get_object().releases.select_related('application', 'validated_by_request'), ReleaseSerializer)

    @action(detail=True, methods=['get'])
    def requests(self, request, pk=None):
        application = self.get_object()
        recover_expired_requests(application)
        reconcile_pending_tests(application)
        qs = application.requests.all()
        for key, allowed in (('mode', ('test', 'invoke', 'evaluation')), ('status', ('completed', 'failed', 'running', 'rejected'))):
            value = request.query_params.get(key)
            if value:
                if value not in allowed:
                    raise ValidationError({key: MESSAGES['filter']})
                qs = qs.filter(**{key: value})
        return self.paginate_values(qs, RequestSerializer)

    @action(detail=True, methods=['get'], url_path=r'requests/(?P<request_id>[^/.]+)')
    def request_detail(self, request, pk=None, request_id=None):
        from rest_framework.serializers import UUIDField
        application = self.get_object()
        recover_expired_requests(application)
        reconcile_pending_tests(application)
        record = get_object_or_404(ApplicationRequest, application=application, pk=UUIDField().run_validation(request_id))
        return Response(RequestSerializer(record).data)

    @action(detail=True, methods=['get'], url_path=r'requests/(?P<request_id>[^/.]+)/execution')
    def request_execution(self, request, pk=None, request_id=None):
        from rest_framework.serializers import UUIDField
        from .execution_trace import execution_summary
        application = self.get_object()
        record = get_object_or_404(ApplicationRequest.objects.only('id', 'workflow_execution_id', 'workflow_manifest'),
            application=application, pk=UUIDField().run_validation(request_id))
        return Response(execution_summary(record))

    @action(detail=True, methods=['get', 'post'], url_path='api-keys')
    def api_keys(self, request, pk=None):
        application = self.get_object()
        self.require_edit(application, publishing=True)
        if request.method == 'GET':
            return self.paginate_values(application.api_keys.all(), APIKeySerializer)
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key, plaintext = ApplicationAPIKey.issue(application=application, created_by=request.user, **serializer.validated_data)
        return Response({**APIKeySerializer(key).data, 'api_key': plaintext}, status=201)

    @action(detail=True, methods=['post'], url_path=r'api-keys/(?P<key_id>[^/.]+)/revoke')
    def revoke_key(self, request, pk=None, key_id=None):
        from rest_framework.serializers import UUIDField
        application = self.get_object()
        self.require_edit(application, publishing=True)
        key = get_object_or_404(ApplicationAPIKey, pk=UUIDField().run_validation(key_id), application=application)
        if not key.revoked_at:
            key.revoked_at = timezone.now()
            key.save(update_fields=['revoked_at'])
        return Response(APIKeySerializer(key).data)
