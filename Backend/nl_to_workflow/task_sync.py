"""
Helpers to keep NLSession status in sync with Celery task results.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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


def reconcile_session_with_celery(session) -> Dict[str, Any]:
    """
    If session is still processing but Celery already finished, sync DB state.

    Returns a small dict describing what happened:
      {recovered: bool, celery_state: str|None, detail: str}
    """
    task_id = (getattr(session, 'celery_task_id', None) or '').strip()
    info: Dict[str, Any] = {
        'recovered': False,
        'celery_state': None,
        'detail': '',
    }
    if not task_id:
        return info

    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        state = result.state
        info['celery_state'] = state
    except Exception as exc:
        logger.debug('celery reconcile lookup failed: %s', exc)
        info['celery_state'] = 'UNKNOWN'
        info['detail'] = str(exc)
        return info

    if session.status in ('completed', 'failed'):
        return info

    if state == 'SUCCESS':
        payload = result.result if isinstance(result.result, dict) else {}
        workflow = payload.get('workflow_json') or session.workflow_json or {}
        if payload.get('status') == 'failed' or (payload.get('error') and not (workflow or {}).get('nodes')):
            session.status = 'failed'
            session.error_message = payload.get('error') or session.error_message or '异步生成失败'
            session.save(update_fields=['status', 'error_message', 'updated_at'])
            info['recovered'] = True
            info['detail'] = 'synced failed from celery SUCCESS payload'
            return info

        if workflow and workflow.get('nodes'):
            session.workflow_json = workflow
            session.workflow_name = (
                payload.get('workflow_name')
                or workflow.get('name')
                or session.workflow_name
                or session.name
            )
            session.workflow = None
            session.status = 'completed'
            session.error_message = ''
            # Avoid duplicate assistant lines
            msgs = session.messages or []
            last = msgs[-1] if msgs else None
            note = f'已生成工作流: {session.workflow_name}'
            if not (isinstance(last, dict) and last.get('role') == 'assistant' and note in (last.get('content') or '')):
                _append_assistant_message(session, note)
            session.save()
            info['recovered'] = True
            info['detail'] = 'synced completed workflow from celery result'
            return info

        # Task success but no workflow in result — refresh from DB only
        session.refresh_from_db()
        if session.status == 'completed' and (session.workflow_json or {}).get('nodes'):
            info['recovered'] = True
            info['detail'] = 'session already completed in DB'
        return info

    if state in ('FAILURE', 'REVOKED'):
        err = None
        try:
            err = str(result.result) if result.result is not None else None
        except Exception:
            err = None
        session.status = 'failed'
        session.error_message = err or session.error_message or f'Celery task {state}'
        session.save(update_fields=['status', 'error_message', 'updated_at'])
        info['recovered'] = True
        info['detail'] = f'synced failed from celery {state}'
        return info

    return info


def enqueue_generate_for_session(
    session,
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
    """Enqueue generate_workflow_async and persist task id. Returns task_id."""
    from .tasks import generate_workflow_async

    session.status = 'processing'
    session.error_message = ''
    session.save(update_fields=['status', 'error_message', 'updated_at'])
    async_result = generate_workflow_async.delay(
        str(session.id),
        model=model,
        temperature=temperature,
    )
    task_id = async_result.id or ''
    session.celery_task_id = task_id
    session.save(update_fields=['celery_task_id', 'updated_at'])
    return task_id
