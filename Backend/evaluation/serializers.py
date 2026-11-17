"""Compatible path aliases resolve only to authorized, registered resources."""
from rest_framework import serializers
from .constants import CLASSIFICATION_METRICS, DETECTION_METRICS
from .models import EvaluationJob


class EvaluationParametersSerializer(serializers.Serializer):
    label_column = serializers.CharField(required=False, max_length=200)
    features = serializers.ListField(child=serializers.CharField(max_length=200), required=False, allow_empty=True)
    metrics = serializers.ListField(child=serializers.ChoiceField(choices=sorted(set(CLASSIFICATION_METRICS + DETECTION_METRICS))),
        required=False, allow_empty=False)
    split = serializers.ChoiceField(choices=('test', 'val'), default='test')
    image_size = serializers.IntegerField(min_value=8, max_value=1024, default=224)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError('评测参数包含未知字段。')
        return super().to_internal_value(data)

    def validate_features(self, values):
        if len(set(values)) != len(values):
            raise serializers.ValidationError('特征列不能重复。')
        return values


class EvaluationJobSerializer(serializers.ModelSerializer):
    training_job_id = serializers.UUIDField(required=False)
    dataset_id = serializers.UUIDField(required=False)
    training_dataset_id = serializers.UUIDField(required=False)
    parameters = EvaluationParametersSerializer(required=False)
    model_path = serializers.CharField(required=False, allow_blank=True, max_length=500)
    test_dataset_path = serializers.CharField(required=False, allow_blank=True, max_length=500)
    created_by_id = serializers.IntegerField(read_only=True, allow_null=True)
    tenant_id = serializers.IntegerField(read_only=True, allow_null=True)
    workflow_id = serializers.UUIDField(read_only=True, allow_null=True)
    node_id = serializers.UUIDField(read_only=True, allow_null=True)
    execution_id = serializers.UUIDField(read_only=True, allow_null=True)
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = EvaluationJob
        fields = ['id', 'job_id', 'name', 'model_path', 'test_dataset_path', 'training_job_id', 'dataset_id',
            'training_dataset_id', 'parameters', 'metrics', 'metrics_history', 'status', 'error_message', 'error_code',
            'created_by_id', 'tenant_id', 'workflow_id', 'node_id', 'execution_id', 'artifact_snapshot',
            'verification_status', 'created_at', 'started_at', 'completed_at', 'lease_expires_at']
        read_only_fields = ['id', 'job_id', 'metrics', 'metrics_history', 'status', 'error_message', 'error_code',
            'created_at', 'started_at', 'completed_at', 'lease_expires_at', 'artifact_snapshot']

    def validate(self, attrs):
        if attrs.get('dataset_id') and attrs.get('training_dataset_id'):
            raise serializers.ValidationError('请选择一种数据集关联。')
        return attrs

    def get_verification_status(self, obj):
        if obj.status != 'completed':
            return 'not_completed'
        snapshot = obj.artifact_snapshot if isinstance(obj.artifact_snapshot, dict) else {}
        if snapshot.get('artifact_sha256') and snapshot.get('dataset_sha256') and obj.metrics.get('sample_count', 0) > 0:
            return 'verified' if obj.training_job_id and (obj.dataset_id or obj.training_dataset_id) else 'verified_source_removed'
        return 'legacy_unverified'
