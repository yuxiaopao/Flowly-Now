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
            'training_run_id', 'yolo_version', 'yolo_variant',
            'best_weight_path', 'last_weight_path', 'class_names',
            'website_type', 'website_type_display',
            'frontend_framework', 'frontend_display',
            'backend_framework', 'backend_display',
            'output_dir', 'status', 'status_display', 'progress',
            'generated_files', 'error_message',
            'inference_endpoint', 'port',
            'codegraph_project_id', 'show_in_nav',
            'last_qa_gate', 'last_qa_report', 'last_preview_url',
            'preview_status', 'rag_collection_id', 'last_agent_reply',
            'tenant', 'created_by', 'created_at', 'completed_at',
        ]
        read_only_fields = [
            'id', 'status', 'progress', 'generated_files', 'error_message',
            'codegraph_project_id', 'last_qa_gate', 'last_qa_report', 'last_preview_url',
            'preview_status', 'rag_collection_id', 'last_agent_reply',
            'created_by', 'created_at', 'completed_at',
        ]


class GeneratedSiteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a GeneratedSite, with optional training_run_id."""

    class Meta:
        model = GeneratedSite
        fields = [
            'name', 'description',
            'model_path', 'model_type', 'labels', 'framework',
            'training_run_id', 'yolo_version', 'yolo_variant',
            'best_weight_path', 'last_weight_path', 'class_names',
            'website_type', 'frontend_framework', 'backend_framework',
            'output_dir', 'port', 'tenant', 'show_in_nav',
        ]

    def validate(self, data):
        import os
        training_run_id = data.get('training_run_id', '')
        model_path = data.get('model_path', '')

        if training_run_id and not model_path:
            try:
                from training.models import TrainingJob
                run = TrainingJob.objects.get(id=training_run_id)
                if run.training_kind != 'yolo':
                    raise serializers.ValidationError({'training_run_id': '只能关联 YOLO 训练运行'})
                data['model_path'] = run.best_weight_path or run.model_path or ''
                data['best_weight_path'] = run.best_weight_path or ''
                data['last_weight_path'] = run.last_weight_path or ''
                data['class_names'] = run.class_names or []
                data['labels'] = run.class_names or []
                data['yolo_version'] = run.yolo_version or ''
                data['yolo_variant'] = run.model_variant or ''
                data['framework'] = 'ultralytics'
                data['website_type'] = 'detection'
            except TrainingJob.DoesNotExist:
                raise serializers.ValidationError({'training_run_id': f'训练运行 {training_run_id} 不存在'})
            except Exception as e:
                raise serializers.ValidationError({'training_run_id': str(e)})

        if not training_run_id and not model_path:
            raise serializers.ValidationError('必须提供 training_run_id 或 model_path')

        output_dir = data.get('output_dir', '')
        if output_dir and os.path.exists(output_dir) and os.listdir(output_dir):
            raise serializers.ValidationError({'output_dir': '输出目录必须为空文件夹'})
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        if validated_data.get('show_in_nav') is None:
            validated_data['show_in_nav'] = True
        return super().create(validated_data)


class GeneratedSiteUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a GeneratedSite."""

    class Meta:
        model = GeneratedSite
        fields = ['name', 'description', 'status', 'error_message', 'show_in_nav']
