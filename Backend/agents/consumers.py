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
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class DesktopAgentConsumer(AsyncJsonWebsocketConsumer):
    """
    Handles long-lived WebSocket connections from Flowly Desktop Agent apps.

    The agent connects to the cloud server and receives training commands,
    while also pushing real-time training progress back to the cloud.
    """

    async def connect(self):
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.group_name = f'agent_{self.agent_id}'

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
        msg_type = content.get('type', 'unknown')
        logger.debug(f"Agent message [{self.agent_id}]: {msg_type}")

        if msg_type == 'agent_registered':
            await self._handle_agent_registered(content)
        elif msg_type == 'training_progress':
            await self._handle_training_progress(content)
        elif msg_type == 'training_started':
            await self._handle_training_started(content)
        elif msg_type == 'training_complete':
            await self._handle_training_complete(content)
        elif msg_type == 'training_error':
            await self._handle_training_error(content)
        elif msg_type == 'training_cancelled':
            await self._handle_training_cancelled(content)
        elif msg_type == 'pong':
            pass  # Heartbeat response, no action needed
        elif msg_type == 'status_report':
            await self._handle_status_report(content)
        else:
            logger.debug(f"Unknown agent message type: {msg_type}")

    # ---- Message Handlers ----

    async def _handle_agent_registered(self, content):
        """Agent announced itself. Update DesktopAgent record."""
        await sync_to_async(self._update_agent_record)(
            content.get('agentId'),
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

    async def _handle_training_started(self, content):
        """Forward training_started to any frontend subscribed sessions."""
        await self.channel_layer.group_send(
            f'training_{content.get("jobId", "")}',
            {
                'type': 'training_event',
                'event': 'training_started',
                **content,
            }
        )
        logger.info(f"Agent training started: {content.get('jobId')}")

    async def _handle_training_progress(self, content):
        """Forward training progress to training group."""
        job_id = content.get('jobId', '')
        await self.channel_layer.group_send(
            f'training_{job_id}',
            {
                'type': 'training_event',
                'event': 'training_progress',
                **content,
            }
        )

    async def _handle_training_complete(self, content):
        """Agent training finished. Update TrainingJob, forward to training group."""
        job_id = content.get('jobId', '')

        # Update TrainingJob in DB
        if content.get('result'):
            await sync_to_async(self._update_training_result)(job_id, content['result'])

        await self.channel_layer.group_send(
            f'training_{job_id}',
            {
                'type': 'training_event',
                'event': 'training_complete',
                **content,
            }
        )
        logger.info(f"Agent training complete: {job_id}")

    async def _handle_training_error(self, content):
        """Training failed on agent side."""
        job_id = content.get('jobId', '')
        await self.channel_layer.group_send(
            f'training_{job_id}',
            {
                'type': 'training_event',
                'event': 'training_error',
                **content,
            }
        )

    async def _handle_training_cancelled(self, content):
        """Training cancelled by agent."""
        job_id = content.get('jobId', '')
        await self.channel_layer.group_send(
            f'training_{job_id}',
            {
                'type': 'training_event',
                'event': 'training_cancelled',
                **content,
            }
        )

    async def _handle_status_report(self, content):
        """Agent status report (response to get_status from cloud)."""
        logger.debug(f"Agent status report: {content.get('agentId')}")

    # ---- DB Updates ----

    def _update_agent_record(self, agent_id, hostname, platform, gpu, capabilities):
        """Update or create DesktopAgent record."""
        try:
            from agents.models_desktop import DesktopAgent
            DesktopAgent.objects.update_or_create(
                agent_id=agent_id,
                defaults={
                    'hostname': hostname or '',
                    'platform': platform or '',
                    'gpu_info': gpu or {},
                    'capabilities': capabilities,
                    'status': 'online',
                }
            )
            logger.info(f"DesktopAgent record updated: {agent_id}")
        except Exception as e:
            logger.error(f"Failed to update DesktopAgent record: {e}")

    def _update_training_result(self, job_id, result):
        """Update TrainingJob with result from desktop agent."""
        try:
            from training.models import TrainingJob
            tj = TrainingJob.objects.filter(id=job_id).first()
            if not tj:
                logger.warning(f"TrainingJob not found: {job_id}")
                return

            if result.get('success'):
                tj.status = 'completed'
                if result.get('final_metrics'):
                    tj.current_metric = result['final_metrics'].get('mAP50', 0)
                    tj.best_fitness = result['final_metrics'].get('fitness', 0)
                tj.best_weight_path = result.get('best_weight_path', '')
                tj.last_weight_path = result.get('last_weight_path', '')
                tj.duration_seconds = result.get('duration_seconds', 0)
            else:
                tj.status = 'failed'
                tj.error_message = result.get('error', 'Training failed on agent')

            tj.save()
            logger.info(f"TrainingJob {job_id} updated from agent result")
        except Exception as e:
            logger.error(f"Failed to update TrainingJob {job_id}: {e}")

    # ---- Group Broadcast (receive from channel layer) ----

    async def get_status(self, event):
        """Cloud requests current agent status."""
        await self.send_json({'type': 'get_status'})

    async def training_command(self, event):
        """Handle training_command broadcast from channel layer → forward to agent WebSocket."""
        # Extract job_config and command, remove internal fields
        cmd = {k: v for k, v in event.items() if k not in ('type')}
        await self.send_json({
            'type': 'training_command',
            'payload': cmd,
        })

    async def training_event(self, event):
        """Handle broadcast from channel layer → send to agent."""
        event_type = event.pop('type', 'training_event')
        await self.send_json({
            'type': event_type,
            **event,
        })
