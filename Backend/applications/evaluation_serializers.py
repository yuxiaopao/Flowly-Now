"""Opaque inputs and explicit assertion contracts for application regressions."""
from rest_framework import serializers
from .evaluation_assertions import validate_assertions
from .models import ApplicationTestSuite, ApplicationTestCase, ApplicationEvaluationRun, ApplicationEvaluationResult
from .serializers import StrictFieldsMixin, InvocationSerializer


class SuiteSerializer(serializers.ModelSerializer):
    case_count = serializers.SerializerMethodField()
    enabled_case_count = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationTestSuite
        fields = ['id', 'name', 'description', 'revision', 'case_count', 'enabled_case_count', 'created_at', 'updated_at']

    def get_case_count(self, obj):
        return obj.cases.count()

    def get_enabled_case_count(self, obj):
        return obj.cases.filter(enabled=True).count()


class SuiteWriteSerializer(StrictFieldsMixin, serializers.Serializer):
    name = serializers.CharField(max_length=160)
    description = serializers.CharField(max_length=4000, allow_blank=True, required=False)


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTestCase
        fields = ['id', 'suite_id', 'name', 'input_data', 'assertions', 'enabled', 'position', 'created_at', 'updated_at']


class CaseWriteSerializer(StrictFieldsMixin, serializers.Serializer):
    name = serializers.CharField(max_length=160)
    input_data = serializers.JSONField(required=False)
    assertions = serializers.JSONField(required=False)
    enabled = serializers.BooleanField(required=False)
    position = serializers.IntegerField(min_value=0, max_value=10000, required=False)
    from_request_id = serializers.UUIDField(required=False, write_only=True)

    def validate_input_data(self, value):
        return InvocationSerializer().validate_input_data(value)

    def validate_assertions(self, value):
        return validate_assertions(value)

    def validate(self, attrs):
        if not self.partial and 'input_data' not in attrs and 'from_request_id' not in attrs:
            raise serializers.ValidationError({'input_data': '请提供输入 JSON 或本应用的真实请求 ID。'})
        if not self.partial and 'assertions' not in attrs:
            raise serializers.ValidationError({'assertions': '请提供至少一条断言。'})
        if 'input_data' in attrs and 'from_request_id' in attrs:
            raise serializers.ValidationError('input_data 与 from_request_id 只能选一个。')
        return attrs


class StartRunSerializer(StrictFieldsMixin, serializers.Serializer):
    suite_id = serializers.UUIDField()
    target = serializers.ChoiceField(choices=('draft', 'release'), default='draft')
    release_id = serializers.UUIDField(required=False)
    case_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=False, max_length=100)

    def validate(self, attrs):
        if attrs['target'] == 'release' and 'release_id' not in attrs or attrs['target'] == 'draft' and 'release_id' in attrs:
            raise serializers.ValidationError('发布目标需要 release_id；草稿目标不能带 release_id。')
        ids = attrs.get('case_ids')
        if ids and len(set(ids)) != len(ids):
            raise serializers.ValidationError('case_ids 不能重复。')
        if ids:
            attrs['case_ids'] = sorted(ids, key=str)
        return attrs


class EvaluationResultSerializer(serializers.ModelSerializer):
    request_id = serializers.UUIDField(read_only=True, allow_null=True)
    latency_ms = serializers.IntegerField(source='request.latency_ms', read_only=True, allow_null=True)

    class Meta:
        model = ApplicationEvaluationResult
        fields = ['id', 'case_id_snapshot', 'case_name', 'case_hash', 'position', 'status', 'request_id',
                  'assertion_results', 'error_code', 'error_message', 'latency_ms', 'started_at', 'completed_at']


class EvaluationRunSerializer(serializers.ModelSerializer):
    release_version = serializers.IntegerField(source='release.version', read_only=True, allow_null=True)
    is_stale = serializers.SerializerMethodField()
    corpus_changed = serializers.SerializerMethodField()
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationEvaluationRun
        fields = ['id', 'application_id', 'suite_id', 'suite_name', 'suite_revision', 'target', 'release_id',
                  'release_version', 'fingerprint', 'status', 'error_code', 'error_message', 'total', 'passed',
                  'failed', 'errors', 'skipped', 'pass_rate', 'runner_mode', 'is_stale', 'corpus_changed',
                  'created_at', 'started_at', 'completed_at', 'deadline_at', 'lease_expires_at']

    def get_is_stale(self, obj):
        from .evaluation_service import run_is_stale
        return run_is_stale(obj, self.context.setdefault('evaluation_staleness', {}))

    def get_corpus_changed(self, obj):
        return bool(obj.completed_at and obj.corpus_signature != obj.final_corpus_signature)

    def get_pass_rate(self, obj):
        settled = obj.passed + obj.failed + obj.errors
        return obj.passed / settled if settled else None


class EvaluationRunDetailSerializer(EvaluationRunSerializer):
    results = EvaluationResultSerializer(many=True, read_only=True)

    class Meta(EvaluationRunSerializer.Meta):
        fields = EvaluationRunSerializer.Meta.fields + ['results']
