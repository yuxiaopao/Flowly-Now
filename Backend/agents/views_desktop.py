"""
Views for Desktop Agent management.
"""

import logging
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models_desktop import DesktopAgent
from .serializers_desktop import DesktopAgentSerializer, DesktopAgentRegisterSerializer

logger = logging.getLogger(__name__)


class DesktopAgentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DesktopAgent management.

    Agents can register themselves without authentication (using agent_id).
    Authenticated users can manage agents they own.
    """

    queryset = DesktopAgent.objects.all()

    def get_permissions(self):
        if self.action in ('register', 'heartbeat'):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'register':
            return DesktopAgentRegisterSerializer
        return DesktopAgentSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return DesktopAgent.objects.filter(owner=self.request.user)
        return DesktopAgent.objects.filter(owner__isnull=True)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register or re-register a desktop agent.
        Called by the agent on first startup and on reconnect.
        """
        serializer = DesktopAgentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        agent, created = DesktopAgent.objects.update_or_create(
            agent_id=serializer.validated_data['agent_id'],
            defaults={
                **serializer.validated_data,
                'status': 'online',
                'connected_at': timezone.now(),
            }
        )

        # If user is authenticated, associate the agent
        if request.user.is_authenticated:
            agent.owner = request.user
            agent.save(update_fields=['owner'])

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
            agent = DesktopAgent.objects.get(agent_id=agent_id)
            agent.status = request.data.get('status', 'online')
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
        queryset = DesktopAgent.objects.filter(
            gpu_available=True,
            supports_yolo_training=True,
            status__in=['online']
        )

        agents = queryset.select_related('owner')
        return Response(DesktopAgentSerializer(agents, many=True).data)

    @action(detail=False, methods=['post'])
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
            agent = DesktopAgent.objects.get(agent_id=agent_id, status='online')
        except DesktopAgent.DoesNotExist:
            return Response({'error': 'Agent not online'}, status=status.HTTP_404_NOT_FOUND)

        if not agent.supports_yolo_training:
            return Response(
                {'error': 'Agent does not support YOLO training'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Send training command to agent via its WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'agent_{agent_id}',
            {
                'type': 'training_command',
                'command': 'start',
                'job_config': job_config,
            }
        )

        # Update agent status
        agent.status = 'training'
        agent.save(update_fields=['status'])

        logger.info(f"Training dispatched to agent {agent_id}")
        return Response({
            'ok': True,
            'agent_id': agent_id,
            'cloud_url': agent.cloud_url,
            'status': 'dispatched',
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
            f'agent_{agent.agent_id}',
            {
                'type': 'get_status',
            }
        )

        return Response({'ok': True})
