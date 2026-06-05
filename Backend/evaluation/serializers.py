"""
Serializers for evaluation app.
"""

from rest_framework import serializers
from .models import EvaluationJob


class EvaluationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationJob
        fields = ['id', 'job_id', 'name', 'model_path', 'test_dataset_path',
                  'metrics', 'status', 'error_message', 'created_at', 'completed_at']
        read_only_fields = ['id', 'job_id', 'metrics', 'status', 'error_message', 'created_at', 'completed_at']
