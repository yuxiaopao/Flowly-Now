"""
Serializers for training app.
"""

import os
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TrainingJob, Dataset
from tenants.access import get_accessible_tenant_ids

User = get_user_model()


def _get_user_tenant(user):
    """Return the user's primary active tenant, or None."""
    if not user or not user.is_authenticated:
        return None
    ids = get_accessible_tenant_ids(user)
    if not ids:
        return None
    from tenants.models import Tenant
    return Tenant.objects.filter(id=ids[0]).first()


class DatasetListSerializer(serializers.ModelSerializer):
    """Serializer for dataset list view."""

    created_by_name = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True
    )
    format_display = serializers.CharField(
        source='get_format_display',
        read_only=True
    )
    size_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'format', 'format_display',
            'size', 'size_formatted', 'row_count', 'columns',
            'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at']

    def get_size_formatted(self, obj):
        """Format size in human-readable format."""
        size = obj.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


class DatasetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a dataset with file upload."""

    file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'file', 'format',
            'size', 'row_count', 'columns'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        """Create dataset with file parsing."""
        file = validated_data.pop('file', None)
        request = self.context.get('request')

        if file:
            validated_data['file_path'] = file.name
            validated_data['size'] = file.size
            validated_data['format'] = os.path.splitext(file.name)[1][1:].lower()

            if validated_data['format'] == 'csv':
                import pandas as pd
                import io
                df = pd.read_csv(io.BytesIO(file.read()))
                validated_data['row_count'] = len(df)
                validated_data['columns'] = list(df.columns)
            elif validated_data['format'] == 'json':
                import json
                try:
                    data = json.load(file)
                    if isinstance(data, list):
                        validated_data['row_count'] = len(data)
                        if data:
                            validated_data['columns'] = list(data[0].keys()) if isinstance(data[0], dict) else []
                    elif isinstance(data, dict):
                        validated_data['row_count'] = 1
                        validated_data['columns'] = list(data.keys())
                except json.JSONDecodeError:
                    pass

        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            tenant = _get_user_tenant(request.user)
            if tenant:
                validated_data['tenant'] = tenant

        validated_data.setdefault('status', 'queued')
        validated_data.setdefault('progress', 0)
        validated_data.setdefault('current_epoch', 0)
        validated_data.setdefault('metrics', {})

        return super().create(validated_data)


class DatasetSerializer(serializers.ModelSerializer):
    """Full serializer for dataset detail view."""

    created_by_name = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True
    )
    format_display = serializers.CharField(
        source='get_format_display',
        read_only=True
    )
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'file_path', 'format', 'format_display',
            'size', 'row_count', 'columns', 'created_at',
            'created_by', 'created_by_name', 'tenant', 'tenant_name'
        ]
        read_only_fields = ['id', 'created_at']


class TrainingJobListSerializer(serializers.ModelSerializer):
    """Serializer for training job list view."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    framework_display = serializers.CharField(
        source='get_framework_display',
        read_only=True
    )
    model_type_display = serializers.CharField(
        source='get_model_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True
    )
    workflow_name = serializers.CharField(
        source='workflow.name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'name', 'status', 'status_display', 'framework', 'framework_display',
            'model_type', 'model_type_display', 'progress', 'current_epoch',
            'total_epochs', 'created_at', 'dataset_id', 'model_path',
            'created_by', 'created_by_name', 'workflow', 'workflow_name',
            'error_message'
        ]
        read_only_fields = ['id', 'created_at']


class TrainingJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a training job (all strategy kinds)."""

    base_weight_uri = serializers.CharField(required=False, write_only=True, allow_blank=True)
    training_kind = serializers.CharField(required=False, allow_blank=True)
    model_type = serializers.CharField(required=False, allow_blank=True)
    framework = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'name', 'workflow', 'node', 'execution', 'config', 'dataset_id',
            'dataset_path', 'dataset_yaml_path', 'class_names',
            'framework', 'model_type', 'training_kind', 'yolo_version', 'model_variant',
            'total_epochs', 'base_weight_uri',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'name': {'required': False},
            'total_epochs': {'required': False},
        }

    def validate(self, data):
        from .options import normalize_training_kind

        raw_kind = self.initial_data.get('training_kind') if hasattr(self, 'initial_data') else data.get('training_kind')
        model_type = data.get('model_type') or self.initial_data.get('model_type')
        kind = normalize_training_kind(raw_kind, model_type)
        data['training_kind'] = kind

        config = dict(data.get('config') or {})
        base_weight = (
            self.initial_data.get('base_weight_uri')
            or config.get('base_weight_uri')
            or ''
        )
        if base_weight:
            config['base_weight_uri'] = base_weight
        data['config'] = config

        if kind == 'yolo':
            data.setdefault('framework', 'ultralytics')
            data.setdefault('model_type', 'detection')
        elif kind == 'clip_ret':
            data.setdefault('framework', 'pytorch')
            data.setdefault('model_type', 'retrieval')
        elif kind == 'clip_cls':
            data.setdefault('framework', 'pytorch')
            data.setdefault('model_type', 'classification')
        elif kind == 'transformer':
            data.setdefault('framework', 'transformers')
            data.setdefault('model_type', model_type or 'classification')
        else:
            data.setdefault('framework', data.get('framework') or 'pytorch')
            data.setdefault('model_type', model_type or 'classifier')

        if not data.get('name'):
            data['name'] = f'{kind}-job'

        return data

    def create(self, validated_data):
        validated_data.pop('base_weight_uri', None)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            tenant = _get_user_tenant(request.user)
            if tenant:
                validated_data['tenant'] = tenant

        validated_data.setdefault('status', 'queued')
        validated_data.setdefault('progress', 0)
        validated_data.setdefault('current_epoch', 0)
        validated_data.setdefault('metrics', {})
        validated_data.setdefault('total_epochs', validated_data.get('total_epochs') or 10)

        return super().create(validated_data)


class TrainingJobUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating training job status and progress."""

    class Meta:
        model = TrainingJob
        fields = [
            'status', 'progress', 'current_epoch', 'total_epochs',
            'metrics', 'error_message', 'model_path'
        ]


class YoloTrainingRunCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a YOLO-specific training run."""

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'name', 'workflow', 'node', 'execution',
            'dataset_id', 'dataset_path', 'dataset_yaml_path', 'dataset_source_mode',
            'annotation_project_id', 'class_names', 'config',
            'framework', 'model_type', 'training_kind', 'yolo_version', 'model_variant',
            'total_epochs', 'status', 'progress', 'current_epoch', 'metrics', 'gpu_info',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'framework': {'required': False, 'default': 'ultralytics'},
            'model_type': {'required': False, 'default': 'detection'},
            'training_kind': {'required': False},
            'status': {'required': False},
            'progress': {'required': False},
            'current_epoch': {'required': False},
            'metrics': {'required': False},
            'gpu_info': {'required': False},
        }

    def validate(self, data):
        data['training_kind'] = 'yolo'
        data.setdefault('framework', 'ultralytics')
        data.setdefault('model_type', 'detection')

        if not data.get('dataset_yaml_path') and not data.get('dataset_path') and not data.get('annotation_project_id'):
            raise serializers.ValidationError({'dataset_yaml_path': 'YOLO训练必须提供 dataset_yaml_path、dataset_path 或 annotation_project_id'})

        if not data.get('yolo_version'):
            raise serializers.ValidationError({'yolo_version': 'YOLO训练必须指定 yolo_version'})

        if not data.get('model_variant'):
            raise serializers.ValidationError({'model_variant': 'YOLO训练必须指定 model_variant'})

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            tenant = _get_user_tenant(request.user)
            if tenant:
                validated_data['tenant'] = tenant

        validated_data.setdefault('status', 'queued')
        validated_data.setdefault('progress', 0)
        validated_data.setdefault('current_epoch', 0)
        validated_data.setdefault('metrics', {})
        validated_data.setdefault('gpu_info', {})
        return super().create(validated_data)


class YoloTrainingRunListSerializer(serializers.ModelSerializer):
    """List serializer for YOLO training runs."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True, allow_null=True)

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'name', 'status', 'status_display', 'training_kind',
            'yolo_version', 'model_variant', 'progress', 'current_epoch', 'total_epochs',
            'best_fitness', 'estimated_duration_seconds', 'eta_seconds',
            'created_at', 'created_by', 'created_by_name', 'workflow', 'workflow_name',
            'best_weight_path', 'error_message'
        ]


class YoloTrainingRunDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for YOLO training runs."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True, allow_null=True)
    node_name = serializers.CharField(source='node.name', read_only=True, allow_null=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, allow_null=True)

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'name', 'workflow', 'workflow_name', 'node', 'node_name', 'execution',
            'status', 'status_display', 'training_kind', 'framework', 'model_type',
            'dataset_id', 'dataset_path', 'dataset_yaml_path', 'dataset_source_mode',
            'annotation_project_id', 'class_names', 'config', 'gpu_info',
            'yolo_version', 'model_variant', 'progress', 'current_epoch', 'total_epochs',
            'current_loss', 'current_metric', 'learning_rate', 'best_epoch', 'best_fitness',
            'estimated_duration_seconds', 'eta_seconds', 'duration_seconds',
            'model_path', 'best_weight_path', 'last_weight_path', 'exported_artifacts',
            'metrics_history', 'loss_box_history', 'loss_cls_history', 'loss_dfl_history',
            'precision_history', 'recall_history', 'map50_history', 'map50_95_history',
            'preview_samples', 'metrics', 'error_message', 'job_id',
            'started_at', 'completed_at', 'created_at', 'updated_at',
            'created_by', 'created_by_name', 'tenant', 'tenant_name'
        ]
        read_only_fields = fields


class YoloTrainingRetrySerializer(serializers.Serializer):
    """Retry options for a YOLO training run."""

    mode = serializers.ChoiceField(choices=['from_scratch', 'from_checkpoint'], default='from_scratch')
    checkpoint_path = serializers.CharField(required=False, allow_blank=True)


class TrainingJobSerializer(serializers.ModelSerializer):
    """Full serializer for training job detail view."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    framework_display = serializers.CharField(
        source='get_framework_display',
        read_only=True
    )
    model_type_display = serializers.CharField(
        source='get_model_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True
    )
    workflow_name = serializers.CharField(
        source='workflow.name',
        read_only=True,
        allow_null=True
    )
    node_name = serializers.CharField(
        source='node.name',
        read_only=True,
        allow_null=True
    )
    execution_id = serializers.IntegerField(
        source='execution.id',
        read_only=True,
        allow_null=True
    )
    tenant_name = serializers.CharField(
        source='tenant.name',
        read_only=True,
        allow_null=True
    )
    duration = serializers.SerializerMethodField()
    duration_seconds = serializers.IntegerField(
        source='duration_seconds',
        read_only=True
    )
    current_loss = serializers.FloatField(read_only=True)
    current_metric = serializers.FloatField(read_only=True)
    metrics_history = serializers.JSONField(read_only=True)

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'name', 'workflow', 'workflow_name', 'node', 'node_name',
            'execution', 'execution_id', 'status', 'status_display',
            'config', 'dataset_id', 'dataset_path', 'model_path',
            'framework', 'framework_display', 'model_type', 'model_type_display',
            'gpu_info', 'progress', 'current_epoch', 'total_epochs',
            'current_loss', 'current_metric', 'duration_seconds', 'metrics_history',
            'metrics', 'error_message', 'job_id',
            'started_at', 'completed_at', 'duration',
            'created_at', 'created_by', 'created_by_name',
            'tenant', 'tenant_name'
        ]
        read_only_fields = [
            'id', 'created_at', 'started_at', 'completed_at'
        ]

    def get_duration(self, obj):
        """Calculate training duration in seconds."""
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None
