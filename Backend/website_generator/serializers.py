"""Serializers for generated ML websites."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from rest_framework import serializers

from .models import GeneratedSite


DEFAULT_REQUIRED_FEATURES = ['imageRecognition', 'videoRecognition', 'factRecognition', 'historyRecords']
FIXED_FRONTEND_FRAMEWORK = 'vue'
FIXED_BACKEND_FRAMEWORK = 'flask'
FIXED_DB_ENGINE = 'mysql'


class GeneratedSiteSerializer(serializers.ModelSerializer):
    """Read serializer for generated sites."""

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
            'model_artifact_manifest', 'site_brief', 'required_features',
            'theme_profile', 'environment_config', 'agent_memory_enabled',
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
    """Create serializer for the training-to-site contract."""

    training_job_id = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = GeneratedSite
        fields = [
            'name', 'description',
            'model_path', 'model_type', 'labels', 'framework',
            'training_job_id', 'training_run_id',
            'model_artifact_manifest', 'site_brief', 'required_features',
            'theme_profile', 'environment_config', 'agent_memory_enabled',
            'yolo_version', 'yolo_variant', 'best_weight_path', 'last_weight_path',
            'class_names', 'website_type', 'frontend_framework', 'backend_framework',
            'output_dir', 'port', 'tenant', 'show_in_nav',
        ]
        extra_kwargs = {
            'model_path': {'required': False, 'allow_blank': True},
            'output_dir': {'required': False, 'allow_blank': True},
            'framework': {'required': False, 'allow_blank': True},
            'model_type': {'required': False, 'allow_blank': True},
            'website_type': {'required': False},
            'frontend_framework': {'required': False},
            'backend_framework': {'required': False},
            'labels': {'required': False},
            'class_names': {'required': False},
            'agent_memory_enabled': {'required': False},
        }

    def validate(self, data):
        training_job_id = data.pop('training_job_id', '') or data.get('training_run_id', '')
        if training_job_id:
            data['training_run_id'] = training_job_id

        manifest = dict(data.get('model_artifact_manifest') or {})
        if training_job_id and not manifest:
            manifest = self._manifest_from_training_job(training_job_id)
            data['model_artifact_manifest'] = manifest

        if manifest:
            self._apply_manifest_defaults(data, manifest)

        if not data.get('training_run_id') and not data.get('model_path'):
            raise serializers.ValidationError(
                'training_run_id, training_job_id, model_artifact_manifest, or model_path is required'
            )

        output_dir = data.get('output_dir', '')
        if output_dir and os.path.exists(output_dir) and os.listdir(output_dir):
            raise serializers.ValidationError({'output_dir': 'Output directory must be empty'})

        data['frontend_framework'] = FIXED_FRONTEND_FRAMEWORK
        data['backend_framework'] = FIXED_BACKEND_FRAMEWORK
        data['required_features'] = _normalize_required_features(data.get('required_features'))
        data['site_brief'] = _normalize_json_object(data.get('site_brief'))
        data['theme_profile'] = _normalize_json_object(data.get('theme_profile'))
        environment_config = _normalize_json_object(data.get('environment_config'))
        environment_config['dbEngine'] = FIXED_DB_ENGINE
        data['environment_config'] = environment_config
        data.setdefault('agent_memory_enabled', True)
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        if validated_data.get('show_in_nav') is None:
            validated_data['show_in_nav'] = True
        return super().create(validated_data)

    def _manifest_from_training_job(self, training_job_id: str) -> Dict[str, Any]:
        from training.models import TrainingJob

        try:
            from training.artifacts import build_model_artifact_manifest

            return build_model_artifact_manifest(TrainingJob.objects.get(id=training_job_id))
        except TrainingJob.DoesNotExist as exc:
            raise serializers.ValidationError({'training_run_id': f'Training job {training_job_id} does not exist'}) from exc

    def _apply_manifest_defaults(self, data: Dict[str, Any], manifest: Dict[str, Any]) -> None:
        data.setdefault('model_path', manifest.get('bestWeightPath') or manifest.get('modelPath') or '')
        data.setdefault('best_weight_path', manifest.get('bestWeightPath') or '')
        data.setdefault('last_weight_path', manifest.get('lastWeightPath') or '')
        data.setdefault('labels', manifest.get('labels') or [])
        data.setdefault('class_names', manifest.get('classNames') or manifest.get('labels') or [])
        data.setdefault('framework', manifest.get('framework') or 'pytorch')
        data.setdefault('model_type', manifest.get('modelType') or manifest.get('taskType') or 'classification')
        data.setdefault('website_type', _website_type_from_manifest(manifest))
        if manifest.get('trainingJobId'):
            data.setdefault('training_run_id', manifest['trainingJobId'])


class GeneratedSiteUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating generated-site metadata."""

    class Meta:
        model = GeneratedSite
        fields = [
            'name', 'description', 'status', 'error_message', 'show_in_nav',
            'site_brief', 'required_features', 'theme_profile', 'environment_config',
            'agent_memory_enabled',
        ]


def _normalize_required_features(value: Any) -> List[str]:
    values = value or DEFAULT_REQUIRED_FEATURES
    if isinstance(values, str):
        values = [item.strip() for item in values.replace('\n', ',').split(',') if item.strip()]
    normalized: List[str] = []
    for item in list(values):
        key = str(item).strip()
        if key and key not in normalized:
            normalized.append(key)
    for feature in DEFAULT_REQUIRED_FEATURES:
        if feature not in normalized:
            normalized.append(feature)
    return normalized


def _normalize_json_object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _website_type_from_manifest(manifest: Dict[str, Any]) -> str:
    task_type = (manifest.get('taskType') or manifest.get('modelType') or '').lower()
    if task_type == 'retrieval':
        return 'clip_retrieval'
    if task_type == 'detection':
        return 'detection'
    return 'classification'
