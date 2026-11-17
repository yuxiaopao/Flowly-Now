"""
WebSocket consumer for Desktop Agent connections.

Protocol:
    Connect:    ws://host/ws/agent/<agent_id>/
    Receive:    agent_registered, training_command, ping, get_status
    Send:      agent_registered ack, training_started, training_progress,
               training_complete, training_error, training_cancelled,
               training_command ack, pong, status_report
"""

import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from users.websocket_permissions import UNAUTHENTICATED_CLOSE_CODE, FORBIDDEN_CLOSE_CODE
from .desktop_jobs import (
    ACTIVE_DESKTOP_STATUSES, DESKTOP_AGENT_CONFIG_KEY, DESKTOP_AGENT_RECORD_CONFIG_KEY,
    TRAINING_EVENTS, apply_training_event, desktop_agent_group,
)

logger = logging.getLogger(__name__)


class DesktopAgentConsumer(AsyncJsonWebsocketConsumer):
    """
    Handles long-lived WebSocket connections from Flowly Desktop Agent apps.

    The agent connects to the cloud server and receives training commands,
    while also pushing real-time training progress back to the cloud.
    """

    async def connect(self):
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=UNAUTHENTICATED_CLOSE_CODE)
            return
        self.agent_pk = await self._owned_agent_pk()
        if not self.agent_pk:
            await self.close(code=FORBIDDEN_CLOSE_CODE)
            return
        self.group_name = desktop_agent_group(self.agent_pk)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"Agent WS connected: {self.agent_id}")

        await self.send_json({
            'type': 'connected',
            'agent_id': self.agent_id,
            'message': 'Connected to Flowly cloud',
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"Agent WS disconnected: {self.agent_id}, close_code: {close_code}")

    async def receive_json(self, content):
        """Handle messages from the desktop agent."""
        if not isinstance(content, dict):
            return
        if not await self._check_owner():
            return
        msg_type = content.get('type', 'unknown')
        logger.debug(f"Agent message [{self.agent_id}]: {msg_type}")

        if msg_type == 'agent_registered':
            await self._handle_agent_registered(content)
        elif msg_type in TRAINING_EVENTS:
            groups = await database_sync_to_async(apply_training_event)(
                self.user, self.agent_id, content, agent_record_id=self.agent_pk,
            )
            for job_id in groups or ():
                await self.channel_layer.group_send(f'training_{job_id}', {
                    'type': f'training_{msg_type}', 'data': content,
                })
        elif msg_type == 'pong':
            pass  # Heartbeat response, no action needed
        elif msg_type == 'status_report':
            await self._handle_status_report(content)
        else:
            logger.debug(f"Unknown agent message type: {msg_type}")

    # ---- Message Handlers ----

    async def _handle_agent_registered(self, content):
        """Agent announced itself. Update DesktopAgent record."""
        if content.get('agentId') != self.agent_id:
            await self.close(code=FORBIDDEN_CLOSE_CODE)
            return
        await database_sync_to_async(self._update_agent_record)(
            self.agent_id,
            content.get('hostname'),
            content.get('platform'),
            content.get('gpu'),
            content.get('capabilities', []),
        )
        await self.send_json({
            'type': 'agent_registered_ack',
            'agent_id': content.get('agentId'),
            'status': 'registered',
        })

    async def _handle_status_report(self, content):
        """Agent status report (response to get_status from cloud)."""
        logger.debug(f"Agent status report: {content.get('agentId')}")

    # ---- DB Updates ----

    @database_sync_to_async
    def _owned_agent_pk(self):
        from .models_desktop import DesktopAgent
        queryset = DesktopAgent.objects.filter(agent_id=self.agent_id, owner=self.user)
        if getattr(self, 'agent_pk', None):
            queryset = queryset.filter(pk=self.agent_pk)
        return queryset.values_list('pk', flat=True).first()

    async def _check_owner(self):
        if await self._owned_agent_pk():
            return True
        await self.close(code=FORBIDDEN_CLOSE_CODE)
        return False

    def _update_agent_record(self, agent_id, hostname, platform, gpu, capabilities):
        """Update or create DesktopAgent record."""
        try:
            from agents.models_desktop import DesktopAgent
            from training.models import TrainingJob
            with transaction.atomic():
                agents = DesktopAgent.objects.select_for_update().filter(
                    pk=self.agent_pk, agent_id=agent_id, owner=self.user,
                )
                agent = agents.first()
                if agent is None:
                    return
                assignment = Q(**{f'config__{DESKTOP_AGENT_RECORD_CONFIG_KEY}': str(agent.pk)}) | Q(**{
                    f'config__{DESKTOP_AGENT_CONFIG_KEY}': agent_id,
                    f'config__{DESKTOP_AGENT_RECORD_CONFIG_KEY}__isnull': True,
                })
                busy = TrainingJob.objects.filter(
                    assignment, created_by=self.user, status__in=ACTIVE_DESKTOP_STATUSES,
                ).exists()
                agents.update(
                    hostname=hostname or '', platform=platform or '', gpu_info=gpu or {},
                    capabilities=capabilities, status='training' if busy else 'online',
                    last_seen=timezone.now(),
                )
            logger.info(f"DesktopAgent record updated: {agent_id}")
        except Exception as e:
            logger.error(f"Failed to update DesktopAgent record: {e}")

    # ---- Group Broadcast (receive from channel layer) ----

    async def get_status(self, event):
        """Cloud requests current agent status."""
        if not await self._check_owner():
            return
        await self.send_json({'type': 'get_status'})

    async def training_command(self, event):
        """Handle training_command broadcast from channel layer → forward to agent WebSocket."""
        if not await self._check_owner():
            return
        # Extract job_config and command, remove internal fields
        cmd = {k: v for k, v in event.items() if k != 'type'}
        await self.send_json({
            'type': 'training_command',
            'payload': cmd,
        })
