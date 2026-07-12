"""
Serializers for datasets app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Dataset

User = get_user_model()


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model."""

    source_display = serializers.CharField(source='get_source_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    size_display = serializers.CharField(read_only=True)
    is_ready = serializers.BooleanField(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    creator_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description',
            'source', 'source_display',
            'file_path', 'url', 's3_path', 's3_bucket',
            'format', 'format_display',
            'size_bytes', 'size_display',
            'row_count', 'column_count', 'columns',
            'status', 'status_display',
            'error_message',
            'metadata',
            'tenant', 'created_by', 'creator_name', 'creator_email',
            'is_ready', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'row_count', 'column_count', 'columns',
            'status', 'error_message', 'created_by',
            'creator_name', 'creator_email', 'is_ready',
            'created_at', 'updated_at'
        ]


class DatasetListSerializer(serializers.ModelSerializer):
    """Serializer for Dataset list view."""

    source_display = serializers.CharField(source='get_source_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    size_display = serializers.CharField(read_only=True)
    is_ready = serializers.BooleanField(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description',
            'source', 'source_display', 'format', 'format_display',
            'size_bytes', 'size_display', 'row_count', 'column_count',
            'status', 'is_ready',
            'created_by', 'creator_name',
            'created_at', 'updated_at'
        ]


class DatasetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Dataset."""

    class Meta:
        model = Dataset
        fields = [
            'name', 'description',
            'source', 'file', 'url', 's3_path', 's3_bucket',
            'format', 'metadata',
            'tenant'
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class DatasetUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Dataset."""

    class Meta:
        model = Dataset
        fields = [
            'name', 'description',
            'format', 'metadata'
        ]


class DatasetPreviewSerializer(serializers.Serializer):
    """Serializer for dataset preview."""

    columns = serializers.ListField()
    rows = serializers.ListField()
    row_count = serializers.IntegerField()
    total_rows = serializers.IntegerField()
    preview_rows = serializers.IntegerField()


class DatasetStatsSerializer(serializers.Serializer):
    """Serializer for dataset statistics."""

    row_count = serializers.IntegerField()
    column_count = serializers.IntegerField()
    columns = serializers.ListField()
    size_bytes = serializers.IntegerField()
    size_display = serializers.CharField()
    format = serializers.CharField()
    source = serializers.CharField()
    null_counts = serializers.DictField(required=False)
    unique_counts = serializers.DictField(required=False)
    numeric_stats = serializers.DictField(required=False)
