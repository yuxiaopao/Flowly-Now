"""
Serializers for training app.
"""

import os
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TrainingJob, Dataset

User = get_user_model()


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
            if hasattr(request.user, 'tenant'):
                validated_data['tenant'] = request.user.tenant

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
    """Serializer for creating a training job."""

    class Meta:
        model = TrainingJob
        fields = [
            'workflow', 'node', 'execution', 'config', 'dataset_id',
            'dataset_path', 'framework', 'model_type', 'total_epochs'
        ]

    def create(self, validated_data):
        """Create training job with default values."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            if hasattr(request.user, 'tenant'):
                validated_data['tenant'] = request.user.tenant

        validated_data.setdefault('status', 'queued')
        validated_data.setdefault('progress', 0)
        validated_data.setdefault('current_epoch', 0)
        validated_data.setdefault('metrics', {})

        return super().create(validated_data)


class TrainingJobUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating training job status and progress."""

    class Meta:
        model = TrainingJob
        fields = [
            'status', 'progress', 'current_epoch', 'total_epochs',
            'metrics', 'error_message', 'model_path'
        ]


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
