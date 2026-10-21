"""
Django signals for workflow execution real-time updates.
"""

import logging
from django.dispatch import receiver, Signal
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# Custom signals
execution_started = Signal()
execution_node_started = Signal()
execution_node_completed = Signal()
execution_completed = Signal()
execution_failed = Signal()
execution_progress = Signal()
execution_output = Signal()


def get_channel_layer_safe():
    """Safely get channel layer, handling cases where it's not configured."""
    try:
        return get_channel_layer()
    except Exception as e:
        logger.debug(f"Channel layer not available: {e}")
        return None


def send_to_execution_group(execution_id, event_type, data):
    """Send event to execution WebSocket group."""
    channel_layer = get_channel_layer_safe()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f'execution_{execution_id}',
                {
                    'type': event_type,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")


def send_to_workflow_group(workflow_id, event_type, data):
    """Send event to workflow WebSocket group."""
    channel_layer = get_channel_layer_safe()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f'workflow_{workflow_id}',
                {
                    'type': event_type,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")


def send_to_user(user_id, event_type, data):
    """Send event to user's notification channel."""
    channel_layer = get_channel_layer_safe()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': event_type,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")


from monitoring.broadcasts import broadcast_to_monitoring


@receiver(execution_started)
def on_execution_started(sender, execution, **kwargs):
    """Handle execution started."""
    data = {
        'execution_id': execution.id,
        'workflow_id': execution.workflow_id,
        'workflow_name': execution.workflow.name,
        'status': execution.status,
        'started_at': execution.started_at.isoformat() if execution.started_at else None
    }
    
    # Send to execution group
    send_to_execution_group(execution.id, 'execution_start', data)
    
    # Send to workflow group
    send_to_workflow_group(execution.workflow_id, 'workflow_update', data)
    
    # Broadcast to monitoring
    broadcast_to_monitoring({
        'event': 'execution_started',
        'execution_id': execution.id,
        'workflow_id': execution.workflow_id
    })


@receiver(execution_node_started)
def on_execution_node_started(sender, execution, node_id, node_name, **kwargs):
    """Handle node execution started."""
    data = {
        'execution_id': execution.id,
        'node_id': node_id,
        'node_name': node_name,
        'status': 'running'
    }
    
    send_to_execution_group(execution.id, 'execution_node_start', data)


@receiver(execution_node_completed)
def on_execution_node_completed(sender, execution, node_id, node_name, result, **kwargs):
    """Handle node execution completed."""
    data = {
        'execution_id': execution.id,
        'node_id': node_id,
        'node_name': node_name,
        'status': 'completed',
        'result': result
    }
    
    send_to_execution_group(execution.id, 'execution_node_complete', data)


@receiver(execution_progress)
def on_execution_progress(sender, execution, progress, message, **kwargs):
    """Handle execution progress update."""
    data = {
        'execution_id': execution.id,
        'progress': progress,
        'message': message
    }
    
    send_to_execution_group(execution.id, 'execution_progress', data)


@receiver(execution_output)
def on_execution_output(sender, execution, output, **kwargs):
    """Handle execution streaming output."""
    data = {
        'execution_id': execution.id,
        'output': output
    }
    
    send_to_execution_group(execution.id, 'execution_output', data)


@receiver(execution_completed)
def on_execution_completed(sender, execution, **kwargs):
    """Handle execution completed."""
    data = {
        'execution_id': execution.id,
        'workflow_id': execution.workflow_id,
        'workflow_name': execution.workflow.name,
        'status': execution.status,
        'output_data': execution.output_data,
        'duration': execution.duration,
        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
    }
    
    # Send to execution group
    send_to_execution_group(execution.id, 'execution_complete', data)
    
    # Send to workflow group
    send_to_workflow_group(execution.workflow_id, 'workflow_update', data)
    
    # Notify user
    if execution.triggered_by:
        send_to_user(execution.triggered_by_id, 'notification', {
            'type': 'execution_completed',
            'execution_id': execution.id,
            'workflow_name': execution.workflow.name,
            'status': 'completed'
        })
    
    # Broadcast to monitoring
    broadcast_to_monitoring({
        'event': 'execution_completed',
        'execution_id': execution.id,
        'workflow_id': execution.workflow_id,
        'status': 'completed'
    })


@receiver(execution_failed)
def on_execution_failed(sender, execution, error, **kwargs):
    """Handle execution failed."""
    data = {
        'execution_id': execution.id,
        'workflow_id': execution.workflow_id,
        'workflow_name': execution.workflow.name,
        'status': 'failed',
        'error': error,
        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
    }
    
    # Send to execution group
    send_to_execution_group(execution.id, 'execution_error', data)
    
    # Send to workflow group
    send_to_workflow_group(execution.workflow_id, 'workflow_update', data)
    
    # Notify user
    if execution.triggered_by:
        send_to_user(execution.triggered_by_id, 'notification', {
            'type': 'execution_failed',
            'execution_id': execution.id,
            'workflow_name': execution.workflow.name,
            'error': error
        })
    
    # Broadcast to monitoring
    broadcast_to_monitoring({
        'event': 'execution_failed',
        'execution_id': execution.id,
        'workflow_id': execution.workflow_id,
        'status': 'failed',
        'error': error
    })
