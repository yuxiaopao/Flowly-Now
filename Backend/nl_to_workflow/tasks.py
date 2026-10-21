"""
Celery tasks for nl_to_workflow app.
Handles asynchronous workflow generation and processing.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone

logger = logging.getLogger(__name__)


def _append_assistant_message(session, content: str) -> None:
    messages = list(session.messages or [])
    messages.append({
        'role': 'assistant',
        'content': content,
        'timestamp': timezone.now().isoformat(),
    })
    session.messages = messages


@shared_task(
    bind=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    name='nl_to_workflow.generate_workflow_async',
)
def generate_workflow_async(self, session_id: str, model: str = None, temperature: float = None):
    """
    Asynchronously generate workflow from NL session description.

    Args:
        session_id: UUID string of the NL session
    """
    from .models import NLSession
    from .services import NLToWorkflowService

    try:
        session = NLSession.objects.get(id=session_id)
    except NLSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}

    session.status = 'processing'
    session.celery_task_id = self.request.id or session.celery_task_id or ''
    session.error_message = ''
    session.save(update_fields=['status', 'celery_task_id', 'error_message', 'updated_at'])

    try:
        kwargs = {'user': session.user}
        if model:
            kwargs['model'] = model
        if temperature is not None:
            kwargs['temperature'] = float(temperature)
        service = NLToWorkflowService(**kwargs)
        context = {
            'user_id': getattr(session.user, 'id', None),
            'session_id': str(session.id),
        }
        description = session.description or ''
        if session.conversation_summary:
            description = (
                f"【对话摘要】\n{session.conversation_summary}\n\n"
                f"【当前需求】\n{description}"
            )
        result = service.generate_workflow(description, context=context)

        if result.get('error') and not result.get('nodes'):
            session.status = 'failed'
            session.error_message = result.get('error', 'Generation failed')
            _append_assistant_message(session, f"生成失败：{session.error_message}")
            session.save()
            return {
                'session_id': str(session_id),
                'status': 'failed',
                'error': session.error_message,
            }

        session.workflow_json = result
        session.workflow_name = result.get('name') or session.workflow_name or session.name
        session.workflow = None
        session.status = 'completed'
        session.model_used = result.get('_llm_model') or session.model_used
        _append_assistant_message(
            session,
            f"已生成工作流: {session.workflow_name}"
            + (f"（{result.get('_generation_mode')}）" if result.get('_generation_mode') else ''),
        )
        session.save()
        return {
            'session_id': str(session_id),
            'status': 'completed',
            'workflow_json': session.workflow_json,
            'workflow_name': session.workflow_name,
        }

    except Exception as e:
        logger.exception('generate_workflow_async failed for %s', session_id)
        try:
            raise self.retry(exc=e, countdown=30)
        except MaxRetriesExceededError:
            NLSession.objects.filter(id=session_id).update(
                status='failed',
                error_message=f'Max retries exceeded: {e}',
            )
            return {'error': f'Max retries exceeded for session {session_id}', 'status': 'failed'}


@shared_task(
    bind=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    name='nl_to_workflow.continue_conversation_async',
)
def continue_conversation_async(
    self,
    session_id: str,
    message: str,
    mode: str = None,
    model: str = None,
):
    """Continue NL conversation asynchronously (generate/editor heavy turns)."""
    from .models import NLSession
    from .services import NLToWorkflowService

    try:
        session = NLSession.objects.get(id=session_id)
    except NLSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}

    session.status = 'processing'
    session.celery_task_id = self.request.id or session.celery_task_id or ''
    session.save(update_fields=['status', 'celery_task_id', 'updated_at'])

    try:
        kwargs = {'user': session.user}
        if model:
            kwargs['model'] = model
        service = NLToWorkflowService(**kwargs)

        messages = list(session.messages or [])
        messages.append({
            'role': 'user',
            'content': message,
            'timestamp': timezone.now().isoformat(),
        })

        result = service.continue_conversation(
            messages[:-1],
            message,
            current_workflow=session.workflow_json or None,
            mode=mode,
        )

        assistant_text = result.get('message') or ''
        messages.append({
            'role': 'assistant',
            'content': assistant_text,
            'timestamp': timezone.now().isoformat(),
        })
        session.messages = messages

        if result.get('workflow'):
            session.workflow_json = result['workflow']
            session.workflow = None
            if result['workflow'].get('name'):
                session.workflow_name = result['workflow']['name']

        if result.get('conversation_summary'):
            session.conversation_summary = result['conversation_summary']

        if result.get('error') and not result.get('workflow'):
            session.status = 'failed'
            session.error_message = result.get('error') or assistant_text or 'Continuation failed'
        else:
            session.status = 'completed'
            session.error_message = ''

        session.save()
        return {
            'session_id': str(session_id),
            'status': session.status,
            'response': assistant_text,
            'workflow_json': session.workflow_json if session.status == 'completed' else None,
            'suggestions': result.get('suggestions', []),
            'intent': result.get('intent'),
        }

    except Exception as e:
        logger.exception('continue_conversation_async failed for %s', session_id)
        try:
            raise self.retry(exc=e, countdown=30)
        except MaxRetriesExceededError:
            NLSession.objects.filter(id=session_id).update(
                status='failed',
                error_message=f'Max retries exceeded: {e}',
            )
            return {'error': f'Max retries exceeded for session {session_id}', 'status': 'failed'}


@shared_task(name='nl_to_workflow.cleanup_old_sessions')
def cleanup_old_sessions(days: int = 30):
    """Clean up old NL sessions."""
    from .models import NLSession

    cutoff = timezone.now() - timedelta(days=days)
    deleted_count, _ = NLSession.objects.filter(
        created_at__lt=cutoff,
        status__in=['completed', 'failed'],
    ).delete()
    return {'sessions_deleted': deleted_count}


@shared_task(name='nl_to_workflow.preview_workflow')
def preview_workflow(description: str, model: str = None, temperature: float = 0.7):
    """Generate a preview of the workflow without saving."""
    from .services import NLToWorkflowService

    kwargs = {}
    if model:
        kwargs['model'] = model
    if temperature != 0.7:
        kwargs['temperature'] = temperature

    service = NLToWorkflowService(**kwargs)
    return service.generate_workflow(description, include_validation=True)


@shared_task(name='nl_to_workflow.summarize_session')
def summarize_session_async(session_id: str):
    """Refresh conversation_summary for a long session."""
    from .models import NLSession
    from .services import NLToWorkflowService
    from .conversation_memory import summarize_messages

    try:
        session = NLSession.objects.get(id=session_id)
    except NLSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}

    service = NLToWorkflowService(user=session.user)

    def _call(messages):
        return service._call_llm(messages)

    summary = summarize_messages(
        session.messages or [],
        call_llm=_call if service.llm else None,
        existing_summary=session.conversation_summary or '',
    )
    session.conversation_summary = summary
    session.save(update_fields=['conversation_summary', 'updated_at'])
    return {'session_id': str(session_id), 'summary': summary}
