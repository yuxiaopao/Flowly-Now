"""Serializers for workflow triggers."""

import uuid
from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from .scheduling import WorkflowTrigger, TriggerExecution, TriggerType


def _config_from_trigger(trigger: WorkflowTrigger) -> dict:
    mappings = []
    if isinstance(trigger.input_mapping, dict):
        mappings = trigger.input_mapping.get('mappings') or trigger.input_mapping.get('input_mappings') or []
    return {
        'schedule_type': trigger.schedule_type or 'once',
        'scheduled_at': trigger.scheduled_at.isoformat() if trigger.scheduled_at else '',
        'interval_seconds': trigger.interval_seconds,
        'cron_expression': trigger.cron_expression or '',
        'auth_type': trigger.webhook_secret and 'signature' or 'none',
        'webhook_secret': trigger.webhook_secret or '',
        'max_executions': trigger.max_executions,
        'input_mappings': mappings,
    }


def _apply_config_to_trigger(trigger: WorkflowTrigger, config: dict) -> None:
    if not isinstance(config, dict):
        return
    trigger.schedule_type = config.get('schedule_type') or trigger.schedule_type or 'once'
    scheduled_at = config.get('scheduled_at')
    if scheduled_at:
        if isinstance(scheduled_at, str):
            try:
                trigger.scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            except ValueError:
                trigger.scheduled_at = None
        else:
            trigger.scheduled_at = scheduled_at
    trigger.interval_seconds = config.get('interval_seconds') or trigger.interval_seconds
    trigger.cron_expression = config.get('cron_expression') or trigger.cron_expression or ''
    trigger.webhook_secret = config.get('webhook_secret') or trigger.webhook_secret or ''
    max_exec = config.get('max_executions')
    if max_exec is not None:
        trigger.max_executions = max_exec or None
    mappings = config.get('input_mappings')
    if mappings is not None:
        trigger.input_mapping = {'mappings': mappings}


class WorkflowTriggerSerializer(serializers.ModelSerializer):
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    workflow_id = serializers.UUIDField(source='workflow.id', read_only=True)
    config = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTrigger
        fields = [
            'id', 'workflow_id', 'name', 'description',
            'trigger_type', 'trigger_type_display',
            'schedule_type', 'scheduled_at', 'interval_seconds', 'cron_expression',
            'webhook_path', 'webhook_secret', 'webhook_url',
            'input_mapping', 'config',
            'status', 'is_enabled', 'max_executions', 'execution_count',
            'last_triggered_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'execution_count', 'last_triggered_at', 'created_at', 'updated_at', 'webhook_path',
        ]

    def get_config(self, obj):
        return _config_from_trigger(obj)

    def get_webhook_url(self, obj):
        if obj.trigger_type != TriggerType.WEBHOOK or not obj.webhook_path:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/v1/workflows/triggers/{obj.id}/webhook/')
        return f'/api/v1/workflows/triggers/{obj.id}/webhook/'


class WorkflowTriggerWriteSerializer(serializers.ModelSerializer):
    config = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = WorkflowTrigger
        fields = [
            'name', 'description', 'trigger_type', 'is_enabled',
            'schedule_type', 'scheduled_at', 'interval_seconds', 'cron_expression',
            'webhook_secret', 'max_executions', 'config',
        ]

    def _ensure_webhook_path(self, trigger: WorkflowTrigger) -> None:
        if trigger.trigger_type == TriggerType.WEBHOOK and not trigger.webhook_path:
            trigger.webhook_path = uuid.uuid4().hex

    def create(self, validated_data):
        config = validated_data.pop('config', {}) or {}
        workflow = validated_data.pop('workflow', None) or self.context['workflow']
        user = self.context.get('request').user if self.context.get('request') else None
        trigger = WorkflowTrigger(workflow=workflow, created_by=user, **validated_data)
        _apply_config_to_trigger(trigger, config)
        self._ensure_webhook_path(trigger)
        trigger.save()
        return trigger

    def update(self, instance, validated_data):
        config = validated_data.pop('config', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if config is not None:
            _apply_config_to_trigger(instance, config)
        self._ensure_webhook_path(instance)
        instance.save()
        return instance


class TriggerExecutionSerializer(serializers.ModelSerializer):
    trigger_id = serializers.IntegerField(source='trigger.id', read_only=True)
    duration_ms = serializers.FloatField(read_only=True)

    class Meta:
        model = TriggerExecution
        fields = [
            'id', 'trigger_id', 'execution_id', 'workflow_execution_id',
            'trigger_source', 'event_data', 'status', 'error_message',
            'queued_at', 'started_at', 'completed_at', 'duration_ms',
        ]


class CronPreviewSerializer(serializers.Serializer):
    expression = serializers.CharField()
    count = serializers.IntegerField(default=5, min_value=1, max_value=20)
