"""
WebSocket consumers for real-time training progress streaming.
"""
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging
from users.websocket_permissions import can_subscribe_training, UNAUTHENTICATED_CLOSE_CODE, FORBIDDEN_CLOSE_CODE

logger = logging.getLogger(__name__)


class TrainingConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for streaming training progress updates.
    
    Connect: ws://host/ws/training/<job_id>/
    Send: nothing (receive-only, client can send ping)
    Receive: JSON events with types:
        - connected: Connection confirmation
        - training_started: Training job has started
        - epoch_start: New epoch began
        - epoch_complete: Epoch finished with metrics
        - training_complete: Training finished successfully
        - training_error: Training encountered an error
        - training_cancelled: Training was cancelled
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.job_id = self.scope['url_route']['kwargs']['job_id']
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=UNAUTHENTICATED_CLOSE_CODE)
            return
        if not await can_subscribe_training(self.user, self.job_id):
            await self.close(code=FORBIDDEN_CLOSE_CODE)
            return
        self.group_name = f'training_{self.job_id}'
        
        # Join the training group for this job
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        logger.info(f"WebSocket connected for training job {self.job_id}")
        
        # Send connection confirmation
        await self.send_json({
            'type': 'connected',
            'job_id': self.job_id,
            'message': 'Connected to training progress stream',
            'group': self.group_name
        })

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'group_name'):
            # Leave the training group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for training job {self.job_id}, close_code: {close_code}")

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        Currently only supports ping for keep-alive.
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type', '')
            
            if msg_type == 'ping':
                # Respond with pong to keep connection alive
                await self.send_json({'type': 'pong'})
            elif msg_type == 'status':
                # Client can request current status
                await self.send_json({
                    'type': 'status_response',
                    'job_id': self.job_id,
                    'connected': True
                })
            else:
                logger.debug(f"Received unhandled message type: {msg_type}")
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    # Training event handlers - these receive events from the channel layer
    # The type field in the event dict determines which handler is called
    # (e.g., 'training_started' -> training_training_started)
    
    async def training_training_started(self, event):
        """Handle training_started event from channel layer."""
        await self.send_json(event['data'])

    async def training_epoch_start(self, event):
        """Handle epoch_start event from channel layer."""
        await self.send_json(event['data'])

    async def training_epoch_complete(self, event):
        """Handle epoch_complete event from channel layer."""
        await self.send_json(event['data'])

    async def training_progress(self, event):
        """Handle progress update event from channel layer."""
        await self.send_json(event['data'])

    async def training_training_complete(self, event):
        """Handle training_complete event from channel layer."""
        await self.send_json(event['data'])

    async def training_training_error(self, event):
        """Handle training_error event from channel layer."""
        await self.send_json(event['data'])

    async def training_training_cancelled(self, event):
        """Handle training_cancelled event from channel layer."""
        await self.send_json(event['data'])
