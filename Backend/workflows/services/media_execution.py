"""Record real local media jobs and imported deliverables in execution history.

These records explicitly describe a media job, rather than claiming that canvas
nodes or a cloud video provider executed. Failed provider records stay intact.
"""
from django.core.exceptions import PermissionDenied
from django.db import transaction

from workflows.models import ExecutionLog, Workflow, WorkflowExecution

MEDIA_EXECUTION_KIND = 'external_media'


@transaction.atomic
def begin_media_execution(workflow, actor, *, input_data=None, source_details=None, archive_key=None):
    locked = Workflow.objects.select_for_update().get(pk=workflow.pk)
    if actor.pk != locked.owner_id:
        raise PermissionDenied('只能为自己拥有的工作流登记成片记录')
    source = {**(source_details or {}), 'kind': MEDIA_EXECUTION_KIND}
    if archive_key:
        source['archive_key'] = str(archive_key)
        existing = locked.executions.filter(
            trigger_source__kind=MEDIA_EXECUTION_KIND,
            trigger_source__archive_key=str(archive_key),
        ).first()
        if existing:
            return existing
    execution = WorkflowExecution.objects.create(
        workflow=locked, version=locked.version, triggered_by=actor,
        trigger_type='api', trigger_source=source, input_data=input_data or {},
        total_nodes=0, executed_nodes=0, failed_nodes=0,
    )
    execution.mark_started()
    ExecutionLog.objects.create(
        execution=execution, message='开始登记成片任务；画布节点及云视频服务执行状态独立保留',
        details={'source': source},
    )
    return execution


@transaction.atomic
def report_media_progress(execution, percent):
    current = WorkflowExecution.objects.select_for_update().get(pk=execution.pk)
    if (current.trigger_source or {}).get('kind') != MEDIA_EXECUTION_KIND:
        raise ValueError('只能更新成片任务的进度')
    if current.status != 'running':
        raise ValueError(f'成片任务已停止：{current.status}')
    current.progress = min(99, max(0, int(percent)))
    current.save(update_fields=['progress'])


@transaction.atomic
def complete_media_execution(execution, output_data):
    current = WorkflowExecution.objects.select_for_update().get(pk=execution.pk)
    if (current.trigger_source or {}).get('kind') != MEDIA_EXECUTION_KIND:
        raise ValueError('此记录不是成片任务，不能改写工作流节点执行结果')
    if current.status == 'completed':
        return current
    if current.status != 'running':
        raise ValueError(f'成片任务不能完成：{current.status}')
    if not isinstance(output_data, dict) or not any(
        output_data.get(key) for key in ('video_url', 'images', 'audio_url', 'files')
    ):
        raise ValueError('成片任务必须包含已生成并保存的产物')
    current.mark_completed(output_data)
    ExecutionLog.objects.create(
        execution=current, message='成片与配套产物已保存，可在执行详情中预览及下载',
        details={'source_kind': MEDIA_EXECUTION_KIND},
    )
    return current


@transaction.atomic
def fail_media_execution(execution, error, *, partial_outputs=None):
    current = WorkflowExecution.objects.select_for_update().get(pk=execution.pk)
    if (current.trigger_source or {}).get('kind') != MEDIA_EXECUTION_KIND:
        raise ValueError('只能更新成片任务的失败状态')
    if current.status != 'running':
        return current
    if partial_outputs:
        current.output_data = partial_outputs
        current.save(update_fields=['output_data'])
    current.mark_failed(str(error))
    ExecutionLog.objects.create(execution=current, level='ERROR', message=str(error))
    return current
