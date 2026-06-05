"""
Serializers for website generator app.
"""

from rest_framework import serializers
from .models import GeneratedSite


class GeneratedSiteSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedSite model."""

    website_type_display = serializers.CharField(source='get_website_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frontend_display = serializers.CharField(source='get_frontend_framework_display', read_only=True)
    backend_display = serializers.CharField(source='get_backend_framework_display', read_only=True)

    class Meta:
        model = GeneratedSite
        fields = [
            'id', 'name', 'description',
            'model_path', 'model_type', 'labels', 'framework',
            'website_type', 'website_type_display',
            'frontend_framework', 'frontend_display',
            'backend_framework', 'backend_display',
            'output_dir', 'status', 'status_display',
            'generated_files', 'error_message',
            'inference_endpoint', 'port',
            'tenant', 'created_by', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'status', 'generated_files', 'error_message', 'created_by', 'created_at', 'completed_at']


class GeneratedSiteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a GeneratedSite."""

    class Meta:
        model = GeneratedSite
        fields = [
            'name', 'description',
            'model_path', 'model_type', 'labels', 'framework',
            'website_type', 'frontend_framework', 'backend_framework',
            'output_dir', 'port', 'tenant'
        ]

    def validate(self, data):
        import os
        output_dir = data.get('output_dir', '')
        if output_dir and os.path.exists(output_dir):
            if os.listdir(output_dir):
                raise serializers.ValidationError({'output_dir': '输出目录必须为空文件夹'})
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class GeneratedSiteUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a GeneratedSite."""

    class Meta:
        model = GeneratedSite
        fields = ['name', 'description', 'status', 'error_message']
