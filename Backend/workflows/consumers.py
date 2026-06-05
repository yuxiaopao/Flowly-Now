"""
WebSocket consumers for real-time updates.
"""

import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class WorkflowConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for workflow updates."""

    async def connect(self):
        self.workflow_id = self.scope['url_route']['kwargs']['workflow_id']
        self.room_group_name = f'workflow_{self.workflow_id}'
        self.user = self.scope.get('user')

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'workflow_id': self.workflow_id
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))

            elif message_type == 'get_status':
                await self.handle_get_status()

            elif message_type == 'subscribe':
                await self.handle_subscribe(data)

            elif message_type == 'node_drag':
                await self.handle_node_drag(data)

            elif message_type == 'save_workflow':
                await self.handle_save_workflow(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def handle_get_status(self):
        """Get current workflow status."""
        workflow_data = await self.get_workflow_status()
        await self.send(text_data=json.dumps({
            'type': 'workflow_status',
            'data': workflow_data
        }))

    async def handle_subscribe(self, data):
        """Subscribe to specific events."""
        events = data.get('events', ['all'])
        await self.send(text_data=json.dumps({
            'type': 'subscribed',
            'events': events
        }))

    async def handle_node_drag(self, data):
        """Handle node drag event for real-time collaboration."""
        node_id = data.get('node_id')
        position = data.get('position', {})
        user_id = self.scope.get('user').id if self.scope.get('user') else None

        # Broadcast to other users in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'node_position_update',
                'data': {
                    'node_id': node_id,
                    'position': position,
                    'user_id': user_id
                }
            }
        )

    async def handle_save_workflow(self, data):
        """Handle workflow save request."""
        try:
            from .services import WorkflowExecutor
            from .models import Workflow, WorkflowExecution

            workflow = await self.get_workflow_instance()
            if workflow:
                # Broadcast save event
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'workflow_saved',
                        'data': {
                            'workflow_id': workflow.id,
                            'saved_by': self.scope.get('user').id if self.scope.get('user') else None
                        }
                    }
                )

        except Exception as e:
            logger.exception(f"WebSocket error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def get_workflow_status(self):
        """Get workflow status from database."""
        try:
            from .models import Workflow, WorkflowExecution

            workflow = Workflow.objects.get(id=self.workflow_id)
            recent_executions = WorkflowExecution.objects.filter(
                workflow=workflow
            ).order_by('-started_at')[:5]

            return {
                'id': workflow.id,
                'name': workflow.name,
                'status': workflow.status,
                'node_count': workflow.nodes.count(),
                'recent_executions': [
                    {
                        'id': e.id,
                        'status': e.status,
                        'started_at': e.started_at.isoformat() if e.started_at else None
                    }
                    for e in recent_executions
                ]
            }
        except Exception as e:
            return {'error': str(e)}

    @database_sync_to_async
    def get_workflow_instance(self):
        """Get workflow instance."""
        try:
            from .models import Workflow
            return Workflow.objects.get(id=self.workflow_id)
        except Exception:
            return None

    async def workflow_update(self, event):
        """Handle workflow update events."""
        await self.send(text_data=json.dumps({
            'type': 'workflow_update',
            'data': event['data']
        }))

    async def node_update(self, event):
        """Handle node update events."""
        await self.send(text_data=json.dumps({
            'type': 'node_update',
            'data': event['data']
        }))

    async def node_position_update(self, event):
        """Handle node position update events (real-time collaboration)."""
        await self.send(text_data=json.dumps({
            'type': 'node_position_update',
            'data': event['data']
        }))

    async def workflow_saved(self, event):
        """Handle workflow saved event."""
        await self.send(text_data=json.dumps({
            'type': 'workflow_saved',
            'data': event['data']
        }))

    async def user_cursor(self, event):
        """Handle user cursor position updates."""
        await self.send(text_data=json.dumps({
            'type': 'user_cursor',
            'data': event['data']
        }))


class ExecutionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for execution updates.
    
    Handles:
    - execution_start: Workflow execution started
    - node_start: Node execution started
    - node_complete: Node execution completed
    - node_error: Node execution failed
    - stream_output: Streaming output from a node
    - execution_complete: Workflow execution completed successfully
    - execution_error: Workflow execution failed
    - execution_progress: Progress update
    - execution_cancelled: Execution was cancelled
    """

    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'execution_{self.execution_id}'
        self.user = self.scope.get('user')

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'execution_id': self.execution_id
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))

            elif message_type == 'cancel':
                await self.handle_cancel()

            elif message_type == 'get_status':
                await self.handle_get_status()

            elif message_type == 'subscribe':
                await self.handle_subscribe(data)

            elif message_type == 'pause':
                await self.handle_pause()

            elif message_type == 'resume':
                await self.handle_resume()

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def handle_cancel(self):
        """Cancel the execution."""
        from .tasks import execute_workflow_task

        try:
            execution = await self.get_execution()
            if execution and execution.status == 'running':
                execution.status = 'cancelled'
                execution.save()

                await self.send(text_data=json.dumps({
                    'type': 'execution_cancelled',
                    'data': {'execution_id': self.execution_id}
                }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_pause(self):
        """Pause the execution."""
        try:
            execution = await self.get_execution()
            if execution and execution.status == 'running':
                execution.status = 'paused'
                execution.save()

                await self.send(text_data=json.dumps({
                    'type': 'execution_paused',
                    'data': {'execution_id': self.execution_id}
                }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_resume(self):
        """Resume a paused execution."""
        try:
            execution = await self.get_execution()
            if execution and execution.status == 'paused':
                execution.status = 'running'
                execution.save()

                await self.send(text_data=json.dumps({
                    'type': 'execution_resumed',
                    'data': {'execution_id': self.execution_id}
                }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_get_status(self):
        """Get current execution status."""
        execution_data = await self.get_execution_status()
        await self.send(text_data=json.dumps({
            'type': 'execution_status',
            'data': execution_data
        }))

    async def handle_subscribe(self, data):
        """Subscribe to specific event types."""
        events = data.get('events', ['all'])
        await self.send(text_data=json.dumps({
            'type': 'subscribed',
            'execution_id': self.execution_id,
            'events': events
        }))

    @database_sync_to_async
    def get_execution(self):
        """Get execution from database."""
        try:
            from .models import WorkflowExecution
            return WorkflowExecution.objects.get(id=self.execution_id)
        except Exception:
            return None

    @database_sync_to_async
    def get_execution_status(self):
        """Get execution status from database."""
        try:
            from .models import WorkflowExecution

            execution = WorkflowExecution.objects.select_related(
                'workflow'
            ).get(id=self.execution_id)

            return {
                'id': execution.id,
                'workflow_id': execution.workflow_id,
                'workflow_name': execution.workflow.name,
                'status': execution.status,
                'trigger_type': execution.trigger_type,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration': execution.duration,
                'node_status': execution.node_status or {},
                'output_data': execution.output_data,
                'error_message': execution.error_message
            }
        except Exception as e:
            return {'error': str(e)}

    async def execution_start(self, event):
        """Handle execution start event."""
        await self.send(text_data=json.dumps({
            'type': 'execution_start',
            'data': event['data']
        }))

    async def execution_node_start(self, event):
        """Handle node execution start event."""
        await self.send(text_data=json.dumps({
            'type': 'node_start',
            'data': event['data']
        }))

    async def execution_node_complete(self, event):
        """Handle node execution complete event."""
        await self.send(text_data=json.dumps({
            'type': 'node_complete',
            'data': event['data']
        }))

    async def execution_node_error(self, event):
        """Handle node execution error event."""
        await self.send(text_data=json.dumps({
            'type': 'node_error',
            'data': event['data']
        }))

    async def execution_output(self, event):
        """Handle execution output event (for streaming)."""
        await self.send(text_data=json.dumps({
            'type': 'stream_output',
            'data': event['data']
        }))

    async def execution_complete(self, event):
        """Handle execution complete event."""
        await self.send(text_data=json.dumps({
            'type': 'execution_complete',
            'data': event['data']
        }))

    async def execution_error(self, event):
        """Handle execution error event."""
        await self.send(text_data=json.dumps({
            'type': 'execution_error',
            'data': event['data']
        }))

    async def execution_progress(self, event):
        """Handle execution progress event."""
        await self.send(text_data=json.dumps({
            'type': 'execution_progress',
            'data': event['data']
        }))

    async def execution_cancelled(self, event):
        """Handle execution cancelled event."""
        await self.send(text_data=json.dumps({
            'type': 'execution_cancelled',
            'data': event['data']
        }))

    async def execution_paused(self, event):
        """Handle execution paused event."""
        await self.send(text_data=json.dumps({
            'type': 'execution_paused',
            'data': event['data']
        }))

    async def node_status(self, event):
        """
        Handle node status update event.
        Provides comprehensive node execution status including queued, running, completed, failed.
        """
        await self.send(text_data=json.dumps({
            'type': 'node_status',
            'node_id': event.get('node_id'),
            'node_type': event.get('node_type'),
            'node_name': event.get('node_name'),
            'status': event.get('status'),  # queued, running, completed, failed, skipped
            'progress': event.get('progress', 0),
            'output': event.get('output'),
            'error': event.get('error'),
            'timestamp': event.get('timestamp'),
            'execution_id': self.execution_id,
        }))


class MonitoringConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for monitoring updates."""

    async def connect(self):
        self.room_group_name = 'monitoring'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'channel': 'monitoring'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
            elif message_type == 'subscribe_metrics':
                await self.send(text_data=json.dumps({
                    'type': 'metrics_subscription_confirmed'
                }))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in WebSocket message: {text_data[:100]}")

    async def metric_update(self, event):
        """Handle metric update event."""
        await self.send(text_data=json.dumps({
            'type': 'metric_update',
            'data': event['data']
        }))

    async def alert_notification(self, event):
        """Handle alert notification event."""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': event['data']
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for user notifications."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'channel': 'notifications'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
            elif message_type == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in notification message: {text_data[:100] if text_data else 'empty'}")

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read."""
        try:
            from monitoring.models import Notification
            Notification.objects.filter(
                id=notification_id,
                owner=self.user
            ).update(is_read=True)
        except Exception as e:
            logger.warning(f"Failed to mark notification {notification_id} as read: {e}")

    async def notification(self, event):
        """Handle notification event."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
