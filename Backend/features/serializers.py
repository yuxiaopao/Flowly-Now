"""
Features API Serializers
"""
from rest_framework import serializers
from .models import FeatureCategory, SystemFeature, FeatureAuditLog


class SystemFeatureSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    display_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemFeature
        fields = [
            'id', 'category', 'category_name', 'key', 'name', 'description',
            'value_type', 'value', 'default_value', 'choices',
            'min_value', 'max_value', 'step', 'placeholder', 'suffix',
            'group', 'order', 'is_enabled', 'is_visible', 'is_readonly',
            'display_value', 'source_file', 'source_line', 'created_at', 'updated_at',
        ]
        read_only_fields = ['key', 'source_file', 'source_line', 'created_at', 'updated_at']

    def get_display_value(self, obj):
        return obj.get_display_value()


class SystemFeatureUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemFeature
        fields = ['value', 'is_enabled', 'is_visible']


class FeatureAuditLogSerializer(serializers.ModelSerializer):
    feature_key = serializers.CharField(source='feature.key', read_only=True)
    feature_name = serializers.CharField(source='feature.name', read_only=True)
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True, allow_null=True)

    class Meta:
        model = FeatureAuditLog
        fields = [
            'id', 'feature', 'feature_key', 'feature_name',
            'action', 'old_value', 'new_value',
            'changed_by', 'changed_by_username',
            'ip_address', 'reason', 'created_at',
        ]
