"""
Celery tasks for nl_to_workflow app.
Handles asynchronous workflow generation and processing.
"""

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def generate_workflow_async(self, session_id: int):
    """
    Asynchronously generate workflow from natural language description.

    Args:
        session_id: ID of the NL session
    """
    try:
        from .models import NLSession
        from .services import NLToWorkflowService

        session = NLSession.objects.get(id=session_id)

        # Update session status
        session.status = 'processing'
        session.save()

        # Generate workflow
        service = NLToWorkflowService()
        result = service.generate_workflow(session.description, session.name)

        if 'error' not in result:
            session.workflow_json = result
            session.workflow_name = result.get('name', session.name)
            session.status = 'completed'
        else:
            session.status = 'failed'
            session.error_message = result.get('error', 'Generation failed')

        session.save()

        return {
            'session_id': session_id,
            'status': session.status,
            'workflow_json': session.workflow_json if session.status == 'completed' else None,
            'error': session.error_message
        }

    except NLSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}
    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            from .models import NLSession
            NLSession.objects.filter(id=session_id).update(
                status='failed',
                error_message=f'Max retries exceeded: {str(e)}'
            )
            return {'error': f'Max retries exceeded for session {session_id}'}


@shared_task(bind=True, max_retries=3)
def continue_conversation_async(self, session_id: int, message: str):
    """
    Continue NL conversation with additional message.

    Args:
        session_id: ID of the NL session
        message: Additional message from user
    """
    try:
        from .models import NLSession
        from .services import NLToWorkflowService

        session = NLSession.objects.get(id=session_id)

        # Update status
        session.status = 'processing'
        session.save()

        # Continue generation
        service = NLToWorkflowService()
        result = service.continue_conversation(session.messages, message, session.workflow_json)

        if 'error' not in result:
            session.status = 'completed'
            if result.get('workflow'):
                session.workflow_json = result['workflow']
        else:
            session.status = 'failed'
            session.error_message = result.get('message', 'Continuation failed')

        session.save()

        return {
            'session_id': session_id,
            'status': session.status,
            'response': result.get('message'),
            'workflow_json': session.workflow_json if session.status == 'completed' else None,
            'suggestions': result.get('suggestions', [])
        }

    except NLSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}
    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            from .models import NLSession
            NLSession.objects.filter(id=session_id).update(
                status='failed',
                error_message=f'Max retries exceeded: {str(e)}'
            )
            return {'error': f'Max retries exceeded for session {session_id}'}


@shared_task
def cleanup_old_sessions(days: int = 30):
    """
    Clean up old NL sessions.

    Args:
        days: Number of days to keep sessions
    """
    from datetime import timedelta

    from .models import NLSession

    cutoff = timezone.now() - timedelta(days=days)

    deleted_count, _ = NLSession.objects.filter(
        created_at__lt=cutoff,
        status__in=['completed', 'failed']
    ).delete()

    return {'sessions_deleted': deleted_count}


@shared_task
def preview_workflow(description: str, model: str = None, temperature: float = 0.7):
    """
    Generate a preview of the workflow without saving.

    Args:
        description: NL description of the workflow
        model: Optional model override
        temperature: Optional temperature override
    """
    from .services import NLToWorkflowService

    kwargs = {}
    if model:
        kwargs['model'] = model
    if temperature != 0.7:
        kwargs['temperature'] = temperature

    service = NLToWorkflowService(**kwargs)
    result = service.generate_workflow(description, include_validation=True)

    return result


@shared_task
def save_generated_workflow(session_id: int):
    """
    Save the generated workflow from a session.

    Args:
        session_id: ID of the NL session
    """
    try:
        from .models import NLSession
        from workflows.models import Workflow
        from workflows.serializers import WorkflowSerializer

        session = NLSession.objects.get(id=session_id)

        if not session.workflow_json:
            return {'error': 'No generated workflow to save'}

        # Create workflow from generated data
        workflow_data = dict(session.workflow_json)
        workflow_data['name'] = session.workflow_name or f"Generated Workflow {session_id}"
        workflow_data['description'] = session.description

        serializer = WorkflowSerializer(data=workflow_data)
        if serializer.is_valid():
            workflow = serializer.save(owner=session.user)
            session.workflow = workflow
            session.save()
            return {
                'session_id': session_id,
                'workflow_id': workflow.id
            }
        else:
            return {
                'error': 'Invalid workflow data',
                'details': serializer.errors
            }

    except NLSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}


@shared_task
def generate_workflow_suggestions(description: str, current_workflow: dict = None):
    """
    Generate suggestions for workflow improvement.

    Args:
        description: Current description
        current_workflow: Optional current workflow dict
    """
    from .services import NLToWorkflowService

    service = NLToWorkflowService()
    if current_workflow:
        suggestions = service._generate_suggestions(current_workflow)
    else:
        suggestions = service.generate_suggestions(description)

    return {
        'description': description,
        'suggestions': suggestions
    }
