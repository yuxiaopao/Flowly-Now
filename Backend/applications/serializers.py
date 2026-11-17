"""Strict configuration boundaries; arbitrary invocation payload keys stay unchanged."""
from config.application_messages import MESSAGES
import json
import math
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from tenants.models import Tenant
from .access import can_edit, can_publish, team_role
from .constants import MAX_INPUT_BYTES, MAX_PROMPT_CHARS
from .models import Application, ApplicationRelease, ApplicationAPIKey, ApplicationRequest, ApplicationTestSuite


class StrictFieldsMixin:
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(MESSAGES['json_object'])
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: MESSAGES['unknown_field'] for key in sorted(unknown)})
        return super().to_internal_value(data)


def normalize_draft(kind, draft):
    if not isinstance(draft, dict):
        raise serializers.ValidationError({'draft': MESSAGES['object']})
    allowed = {'workflow_id'} if kind == 'workflow' else {'collection_id', 'system_prompt', 'top_k', 'min_similarity'}
    if set(draft) - allowed:
        raise serializers.ValidationError({'draft': MESSAGES['configuration_fields']})
    source = 'workflow_id' if kind == 'workflow' else 'collection_id'
    field = serializers.UUIDField()
    result = {source: str(field.run_validation(draft.get(source)))}
    if kind == 'knowledge':
        from rag.constants import DEFAULT_SYSTEM_PROMPT, DEFAULT_TOP_K, DEFAULT_MIN_SIMILARITY, MAX_TOP_K
        prompt = draft.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
        top_k = draft.get('top_k', DEFAULT_TOP_K)
        similarity = draft.get('min_similarity', DEFAULT_MIN_SIMILARITY)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
            raise serializers.ValidationError({'draft': MESSAGES['system_prompt']})
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
            raise serializers.ValidationError({'draft': MESSAGES['top_k']})
        if isinstance(similarity, bool) or not isinstance(similarity, (int, float)) or not math.isfinite(similarity) or not 0 <= similarity <= 1:
            raise serializers.ValidationError({'draft': MESSAGES['similarity']})
        result.update(system_prompt=prompt, top_k=top_k, min_similarity=similarity)
    return result


class ApplicationWriteSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    tenant_id = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), source='tenant', allow_null=True, required=False)
    required_evaluation_suite_id = serializers.PrimaryKeyRelatedField(queryset=ApplicationTestSuite.objects.filter(is_deleted=False),
        source='required_evaluation_suite', allow_null=True, required=False)

    class Meta:
        model = Application
        fields = ['name', 'description', 'kind', 'tenant_id', 'draft', 'required_evaluation_suite_id']
        extra_kwargs = {'description': {'max_length': 8000}}

    def validate(self, attrs):
        user = self.context['request'].user
        existing = self.instance
        if 'required_evaluation_suite' in attrs:
            suite = attrs['required_evaluation_suite']
            if not existing or not can_publish(user, existing):
                raise PermissionDenied('发布测试集门禁只能由应用发布者设置。')
            if suite and (suite.application_id != existing.pk or not suite.cases.filter(enabled=True).exists()):
                raise serializers.ValidationError('门禁必须选择本应用中至少有一条启用用例的测试集。')
        if existing and ('kind' in attrs and attrs['kind'] != existing.kind or
                         'tenant' in attrs and attrs['tenant'] != existing.tenant):
            raise serializers.ValidationError(MESSAGES['immutable_kind'])
        tenant = attrs.get('tenant', existing.tenant if existing else None)
        if tenant and team_role(user, tenant) not in ('owner', 'admin', 'member'):
            raise serializers.ValidationError({'tenant_id': MESSAGES['team_editor']})
        kind = attrs.get('kind', existing.kind if existing else None)
        draft = normalize_draft(kind, attrs.get('draft', existing.draft if existing else {}))
        from .services import resolve_source
        temporary = existing or Application(owner=user, tenant=tenant, kind=kind, draft=draft)
        resolve_source(temporary, draft)
        if 'draft' in attrs or not existing:
            attrs['draft'] = draft
        return attrs


class ReleaseSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.IntegerField(read_only=True)
    is_active = serializers.SerializerMethodField()
    knowledge_content_policy = serializers.SerializerMethodField()
    test_request_id = serializers.UUIDField(source='validated_by_request_id', read_only=True, allow_null=True)
    tested_at = serializers.DateTimeField(source='validated_by_request.completed_at', read_only=True, allow_null=True)
    evaluation_run_id = serializers.UUIDField(source='validated_by_evaluation_id', read_only=True, allow_null=True)

    class Meta:
        model = ApplicationRelease
        fields = ['id', 'application_id', 'version', 'fingerprint', 'configuration',
                  'knowledge_content_policy', 'created_by_id', 'created_at', 'is_active', 'test_request_id', 'tested_at', 'evaluation_run_id']

    def get_is_active(self, obj):
        return obj.application.active_release_id == obj.pk

    def get_knowledge_content_policy(self, obj):
        return 'live' if obj.application.kind == 'knowledge' else None


class ApplicationSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(read_only=True)
    tenant_id = serializers.IntegerField(read_only=True, allow_null=True)
    active_release = ReleaseSerializer(read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_publish = serializers.SerializerMethodField()
    draft_fingerprint = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    release_count = serializers.SerializerMethodField()
    required_evaluation_suite_id = serializers.UUIDField(read_only=True, allow_null=True)
    evaluation_gate = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ['id', 'name', 'description', 'kind', 'tenant_id', 'owner_id', 'draft',
                  'draft_fingerprint', 'tested_fingerprint', 'last_test_status', 'last_test_at',
                  'active_release', 'can_edit', 'can_publish', 'status', 'release_count', 'created_at', 'updated_at',
                  'required_evaluation_suite_id', 'evaluation_gate']

    def get_release_count(self, obj):
        return obj.release_count if hasattr(obj, 'release_count') else obj.releases.count()

    def get_status(self, obj):
        return 'published' if obj.active_release_id else 'unpublished' if self.get_release_count(obj) else 'draft'

    def get_can_edit(self, obj):
        return can_edit(self.context['request'].user, obj)

    def get_can_publish(self, obj):
        return can_publish(self.context['request'].user, obj)

    def get_draft_fingerprint(self, obj):
        from .services import draft_fingerprint, ApplicationFailure
        try:
            return draft_fingerprint(obj)[0]
        except ApplicationFailure:
            return None

    def get_evaluation_gate(self, obj):
        from .evaluation_service import required_evaluation_evidence
        from .services import draft_fingerprint, ApplicationFailure
        result = {'required': bool(obj.required_evaluation_suite_id), 'suite_id': str(obj.required_evaluation_suite_id) if obj.required_evaluation_suite_id else None,
                  'ready': True, 'run_id': None, 'reason': ''}
        if obj.required_evaluation_suite_id:
            try:
                run = required_evaluation_evidence(obj, draft_fingerprint(obj)[0])
                result['run_id'] = str(run.pk)
            except ApplicationFailure as exc:
                result.update(ready=False, reason=str(exc))
        return result


class InvocationSerializer(StrictFieldsMixin, serializers.Serializer):
    input_data = serializers.JSONField(default=dict)

    def validate_input_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(MESSAGES['input_object'])
        try:
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        except (ValueError, TypeError):
            raise serializers.ValidationError(MESSAGES['input_finite'])
        if len(raw) > MAX_INPUT_BYTES:
            from .services import ApplicationFailure
            raise ApplicationFailure(MESSAGES['input_limit'], 'input_limit', 413)
        return value


class APIKeySerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApplicationAPIKey
        fields = ['id', 'name', 'prefix', 'expires_at', 'revoked_at', 'last_used_at', 'created_at', 'is_active']


class APIKeyCreateSerializer(StrictFieldsMixin, serializers.Serializer):
    name = serializers.CharField(max_length=100)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError(MESSAGES['expiry'])
        return value


class RequestSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(read_only=True)
    release_id = serializers.UUIDField(read_only=True, allow_null=True)
    workflow_execution_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = ApplicationRequest
        fields = ['id', 'application_id', 'release_id', 'mode', 'status', 'input_data', 'output_data',
                  'error_code', 'error_message', 'latency_ms', 'total_tokens', 'cost', 'currency',
                  'workflow_execution_id', 'created_at', 'completed_at']
        fields += ['deadline_at']
