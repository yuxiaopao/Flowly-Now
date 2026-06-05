"""
Serializers for augmentation app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AugmentationJob

User = get_user_model()


class AugmentationJobSerializer(serializers.ModelSerializer):
    """Serializer for AugmentationJob model."""

    strategy_display = serializers.CharField(source='get_strategy_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    output_mode_display = serializers.CharField(source='get_output_mode_display', read_only=True)

    input_dataset_name = serializers.CharField(source='input_dataset.name', read_only=True)
    output_dataset_name = serializers.CharField(source='output_dataset.name', read_only=True, allow_null=True)

    creator_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    duration_seconds = serializers.FloatField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = AugmentationJob
        fields = [
            'id', 'input_dataset', 'input_dataset_name',
            'output_dataset', 'output_dataset_name',
            'strategy', 'strategy_display',
            'ratio', 'transformations',
            'augmented_count', 'original_count',
            'status', 'status_display',
            'output_mode', 'output_mode_display',
            'output_dir', 'output_name',
            'error_message', 'progress',
            'created_by', 'creator_name',
            'tenant',
            'created_at', 'started_at', 'completed_at',
            'duration_seconds', 'is_complete'
        ]
        read_only_fields = [
            'id', 'augmented_count', 'status', 'error_message', 'progress',
            'created_by', 'created_at', 'started_at', 'completed_at',
            'duration_seconds', 'is_complete', 'output_dataset'
        ]


class AugmentationJobListSerializer(serializers.ModelSerializer):
    """Serializer for AugmentationJob list view."""

    strategy_display = serializers.CharField(source='get_strategy_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    input_dataset_name = serializers.CharField(source='input_dataset.name', read_only=True)
    output_dataset_name = serializers.CharField(source='output_dataset.name', read_only=True, allow_null=True)

    creator_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)

    class Meta:
        model = AugmentationJob
        fields = [
            'id', 'input_dataset', 'input_dataset_name',
            'output_dataset', 'output_dataset_name',
            'strategy', 'strategy_display',
            'ratio', 'augmented_count', 'original_count',
            'status', 'status_display',
            'progress',
            'created_by', 'creator_name',
            'created_at', 'completed_at'
        ]


class AugmentationJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AugmentationJob."""

    class Meta:
        model = AugmentationJob
        fields = [
            'input_dataset', 'strategy', 'ratio',
            'transformations', 'output_mode', 'output_name', 'tenant'
        ]

    def validate_input_dataset(self, value):
        if not value.is_ready:
            raise serializers.ValidationError("输入数据集尚未准备就绪")
        return value

    def validate_ratio(self, value):
        if value < 1.0 or value > 20.0:
            raise serializers.ValidationError("增强倍数必须在 1.0 到 20.0 之间")
        return value


class AugmentationJobRunSerializer(serializers.Serializer):
    """Serializer for running augmentation job."""

    dataset_id = serializers.UUIDField(required=True, help_text='输入数据集ID')
    strategy = serializers.ChoiceField(
        choices=['geometric', 'color', 'noise', 'mixup', 'all'],
        default='all'
    )
    ratio = serializers.FloatField(default=2.0, min_value=1.0, max_value=20.0)
    transformations = serializers.ListField(required=False, default=list)
    output_mode = serializers.ChoiceField(
        choices=['create_new', 'overwrite'],
        default='create_new'
    )
    output_name = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AugmentationJobUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating AugmentationJob."""

    class Meta:
        model = AugmentationJob
        fields = ['output_name', 'transformations']


class AugmentationStatisticsSerializer(serializers.Serializer):
    """Serializer for augmentation statistics."""

    total_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    running_jobs = serializers.IntegerField()
    total_augmented_samples = serializers.IntegerField()
    total_original_samples = serializers.IntegerField()
