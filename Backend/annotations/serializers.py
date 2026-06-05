"""
Serializers for annotations app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AnnotationProject, AnnotationItem

User = get_user_model()


class AnnotationItemSerializer(serializers.ModelSerializer):
    """Serializer for AnnotationItem model."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    annotator_name = serializers.CharField(source='annotated_by.username', read_only=True)

    class Meta:
        model = AnnotationItem
        fields = [
            'id', 'project', 'data_id', 'data_content',
            'pre_label', 'label', 'status', 'status_display',
            'annotated_by', 'annotator_name', 'annotated_at',
            'created_at'
        ]
        read_only_fields = ['id', 'project', 'data_id', 'data_content', 'pre_label', 'created_at']


class AnnotationItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating AnnotationItem."""

    class Meta:
        model = AnnotationItem
        fields = ['label', 'status']

    def validate_status(self, value):
        if value not in ['pending', 'annotated', 'skipped']:
            raise serializers.ValidationError("Invalid status value.")
        return value


class AnnotationProjectListSerializer(serializers.ModelSerializer):
    """Serializer for AnnotationProject list view."""

    annotation_type_display = serializers.CharField(source='get_annotation_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)

    class Meta:
        model = AnnotationProject
        fields = [
            'id', 'name', 'annotation_type', 'annotation_type_display',
            'labels', 'dataset', 'dataset_name',
            'model_assisted', 'status', 'status_display',
            'total_items', 'annotated_items', 'progress_percentage',
            'tenant', 'created_by', 'creator_name',
            'created_at', 'updated_at'
        ]


class AnnotationProjectSerializer(serializers.ModelSerializer):
    """Serializer for AnnotationProject model."""

    annotation_type_display = serializers.CharField(source='get_annotation_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    items_count = serializers.SerializerMethodField()
    items_stats = serializers.SerializerMethodField()

    class Meta:
        model = AnnotationProject
        fields = [
            'id', 'name', 'annotation_type', 'annotation_type_display',
            'labels', 'dataset', 'dataset_name',
            'model_assisted', 'model_id', 'status', 'status_display',
            'total_items', 'annotated_items', 'progress_percentage',
            'items_count', 'items_stats',
            'tenant', 'created_by', 'creator_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_items', 'annotated_items', 'created_by', 'created_at', 'updated_at']

    def get_items_count(self, obj):
        return obj.items.count()

    def get_items_stats(self, obj):
        stats = {
            'total': obj.items.count(),
            'pending': obj.items.filter(status='pending').count(),
            'annotated': obj.items.filter(status='annotated').count(),
            'skipped': obj.items.filter(status='skipped').count(),
        }
        return stats


class AnnotationProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AnnotationProject."""

    class Meta:
        model = AnnotationProject
        fields = [
            'name', 'annotation_type', 'labels',
            'dataset', 'model_assisted', 'model_id', 'tenant'
        ]

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AnnotationProjectUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating AnnotationProject."""

    class Meta:
        model = AnnotationProject
        fields = [
            'name', 'annotation_type', 'labels',
            'model_assisted', 'model_id', 'status'
        ]


class PreLabelRequestSerializer(serializers.Serializer):
    """Serializer for pre-label generation request."""

    model_id = serializers.CharField(required=False, allow_blank=True)


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export request."""

    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
