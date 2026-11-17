"""
Views for Desktop Agent management.
"""

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework.exceptions import APIException
from training.models import TrainingJob

from .models_desktop import DesktopAgent
from .serializers_desktop import DesktopAgentSerializer, DesktopAgentRegisterSerializer
from .desktop_jobs import bind_training_job, desktop_agent_group

logger = logging.getLogger(__name__)


class DesktopAgentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DesktopAgent management.

    Cloud-connected agents are authenticated and private to their owner.
    """

    queryset = DesktopAgent.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('register', 'create'):
            return DesktopAgentRegisterSerializer
        return DesktopAgentSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return DesktopAgent.objects.filter(owner=self.request.user)
        return DesktopAgent.objects.none()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        return self.register(request)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register or re-register a desktop agent.
        Called by the agent on first startup and on reconnect.
        """
        serializer = DesktopAgentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        values = {**serializer.validated_data, 'status': 'online', 'connected_at': timezone.now()}
        with transaction.atomic():
            agent, created = DesktopAgent.objects.select_for_update().get_or_create(
                agent_id=values['agent_id'], defaults={**values, 'owner': request.user},
            )
            if agent.owner_id != request.user.pk:
                return Response({'error': '设备已存在，请使用新的 Agent ID 注册',
                                 'errors': {'code': 'agent_identity_conflict'}}, status=status.HTTP_409_CONFLICT)
            if not created:
                for field, value in values.items():
                    setattr(agent, field, value)
                agent.save()

        logger.info(f"DesktopAgent {'registered' if created else 'updated'}: {agent.agent_id}")
        return Response(
            DesktopAgentSerializer(agent).data,
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def heartbeat(self, request):
        """
        Agent heartbeat — update last_seen and status.
        Called periodically by the desktop agent.
        """
        agent_id = request.data.get('agent_id')
        if not agent_id:
            return Response({'error': 'agent_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = self.get_queryset().get(agent_id=agent_id)
            agent.status = serializers.ChoiceField(choices=DesktopAgent.STATUS_CHOICES).run_validation(
                request.data.get('status', 'online'))
            agent.last_seen = timezone.now()
            agent.save(update_fields=['status', 'last_seen'])
            return Response({'ok': True, 'status': agent.status})
        except DesktopAgent.DoesNotExist:
            return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        List all online agents that support YOLO training.
        Used by the cloud when dispatching a training job.
        """
        queryset = self.get_queryset().filter(
            gpu_available=True,
            supports_yolo_training=True,
            status__in=['online']
        )

        agents = queryset.select_related('owner')
        return Response(DesktopAgentSerializer(agents, many=True).data)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def dispatch_training(self, request):
        """
        Dispatch a training job to a specific agent via WebSocket.

        Request body: { "agent_id": "...", "job_config": {...} }
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        agent_id = request.data.get('agent_id')
        job_config = request.data.get('job_config', {})

        if not agent_id:
            return Response({'error': 'agent_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = self.get_queryset().select_for_update().get(agent_id=agent_id, status='online')
        except DesktopAgent.DoesNotExist:
            return Response({'error': 'Agent not online'}, status=status.HTTP_404_NOT_FOUND)

        if not agent.supports_yolo_training:
            return Response(
                {'error': 'Agent does not support YOLO training'},
                status=status.HTTP_400_BAD_REQUEST
            )

        job, job_config = bind_training_job(request.user, agent, job_config)

        agent.status = 'training'
        agent.save(update_fields=['status'])

        def publish_command():
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(desktop_agent_group(agent.pk), {
                    'type': 'training_command', 'command': 'start', 'job_config': job_config,
                })
            except Exception as error:
                TrainingJob.objects.filter(pk=job.pk, status='queued').update(
                    status='failed', error_message='训练指令发送失败，请重试', completed_at=timezone.now(),
                )
                DesktopAgent.objects.filter(pk=agent.pk, status='training').update(status='online')
                logger.exception('Failed to dispatch training to %s', agent_id)
                failure = APIException('训练指令发送失败，请重试')
                failure.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                raise failure from error

        transaction.on_commit(publish_command)

        logger.info(f"Training dispatched to agent {agent_id}")
        return Response({
            'ok': True,
            'agent_id': agent_id,
            'cloud_url': agent.cloud_url,
            'status': 'dispatched',
            'job_id': str(job.pk),
        })

    @action(detail=True, methods=['post'])
    def wake_training(self, request, pk=None):
        """
        Wake up a specific agent to check for pending training commands.
        """
        try:
            agent = self.get_object()
        except Exception:
            return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)

        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            desktop_agent_group(agent.pk),
            {
                'type': 'get_status',
            }
        )

        return Response({'ok': True})
