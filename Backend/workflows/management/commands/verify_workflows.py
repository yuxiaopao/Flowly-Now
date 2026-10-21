"""Audit every selected workflow and execute its local, self-contained cases."""
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from workflows.models import Workflow, WorkflowExecution
from workflows.services.langchain_service import LangChainService
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow


LOCAL_NODE_TYPES = frozenset({
    'start', 'end', 'manual', 'trigger', 'input', 'output', 'variable', 'set',
    'condition', 'switch', 'filter', 'split', 'json_transform', 'json_parser',
    'csv_transform', 'data_transform', 'transform', 'text_template', 'template',
    'datetime', 'delay', 'code',
})
LOCAL_HTTP_HOSTS = frozenset({'localhost', '127.0.0.1', '::1'})
REPORT_STATUSES = {
    'passed': '本地执行通过', 'failed': '本地执行失败', 'blocked': '执行前检查未通过',
    'needs_environment': '需要凭据、服务或业务测试数据', 'noop_only': '仅触发或空操作，未验证业务功能',
    'ready': '本地执行前检查通过，尚未运行',
}


class VerificationService(LangChainService):
    def execute_node(self, node_type, node_config, input_data, **kwargs):
        kwargs['use_cache'] = False
        return super().execute_node(node_type, node_config, input_data, **kwargs)


def local_node(node):
    if node.node_type in LOCAL_NODE_TYPES:
        return True
    cfg = node.config or {}
    if node.node_type in ('http', 'http_request'):
        return urlparse(cfg.get('url') or '').hostname in LOCAL_HTTP_HOSTS and cfg.get('method', 'GET').upper() in ('GET', 'HEAD')
    return False


def sample_inputs(nodes, supplied):
    inputs = dict(supplied)
    synthetic = []
    for node in nodes:
        if node.node_type != 'input':
            continue
        cfg = node.config or {}
        name = cfg.get('variable_name') or cfg.get('input_name') or cfg.get('variableName') or cfg.get('inputName') or 'input'
        if name in inputs or cfg.get('default') is not None or cfg.get('default_value') is not None:
            continue
        if cfg.get('required', True):
            inputs[name] = '中文工作流验证输入'
            synthetic.append(name)
    return inputs, synthetic


class Command(BaseCommand):
    help = '逐项核查指定账号的全部工作流；可执行本地流程并生成中文报告（不使用缓存）'

    def add_arguments(self, parser):
        parser.add_argument('--user', required=True)
        parser.add_argument('--report-dir', required=True)
        parser.add_argument('--execute-local', action='store_true')
        parser.add_argument('--inputs-file', help='按工作流 UUID 索引的业务测试输入 JSON')

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['user']).first() or get_user_model().objects.filter(email=options['user']).first()
        if not user:
            raise CommandError('未找到指定账号')
        dest = Path(options['report_dir']).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        inputs = json.loads(Path(options['inputs_file']).read_text(encoding='utf-8')) if options.get('inputs_file') else {}
        workflows = Workflow.objects.filter(owner=user, is_deleted=False).prefetch_related('nodes', 'edges').order_by('created_at')
        report = {'user_id': user.id, 'total': workflows.count(), 'items': []}
        validator = VerificationService(user_id=user.id)
        for index, wf in enumerate(workflows, 1):
            nodes = list(wf.nodes.all())
            input_data, synthetic = sample_inputs(nodes, inputs.get(str(wf.id), {}))
            preflight = validate_workflow(wf, input_data, validator)
            item = {'id': str(wf.id), 'name': wf.name, 'node_count': len(nodes), 'preflight': preflight,
                    'synthetic_input_fields': synthetic, 'status': 'blocked' if not preflight['valid'] else 'needs_environment'}
            item['environment_node_types'] = sorted({n.node_type for n in nodes if not local_node(n)})
            if preflight['valid'] and all(local_node(n) for n in nodes):
                item['status'] = 'ready'
                if options['execute_local']:
                    execution = WorkflowExecution.objects.create(workflow=wf, status='pending', input_data=input_data,
                        triggered_by=user, trigger_type='manual', version=wf.version,
                        trigger_source={'verification': 'local_workflow_verification', 'synthetic_input_fields': synthetic})
                    executor = WorkflowExecutor(wf, execution, parallel_enabled=False)
                    executor.langchain_service = VerificationService(user_id=user.id)
                    try:
                        executor.execute()
                        execution.refresh_from_db()
                        results = executor.node_results
                        bad = [str(nid) for nid, result in results.items() if not result.get('success') or result.get('error') or result.get('soft_failed') or result.get('used_fallback')]
                        item.update({'execution_id': str(execution.id), 'execution_status': execution.status,
                            'executed_node_count': len(results), 'failed_node_ids': bad,
                            'node_results': [{'id': str(nid), 'success': bool(result.get('success')), 'cached': bool(result.get('cached')), 'error': result.get('error'), 'skipped': bool(result.get('skipped'))} for nid, result in results.items()]})
                        item['status'] = 'passed' if execution.status == 'completed' and not bad else 'failed'
                        if item['status'] == 'failed':
                            item['error'] = execution.error_message or '节点结果存在失败、回退或软失败'
                        elif all(n.node_type in ('start', 'end', 'manual', 'trigger') or (n.config or {}).get('n8n_type') == 'n8n-nodes-base.noOp' for n in nodes):
                            item['status'] = 'noop_only'
                    except Exception as exc:
                        item.update({'status': 'failed', 'error': str(exc), 'execution_id': str(execution.id)})
                        execution.mark_failed(error_message=str(exc))
            report['items'].append(item)
            if index % 100 == 0 or index == report['total']:
                self.stdout.write(f'已核查 {index}/{report["total"]}，结果：{dict(Counter(i["status"] for i in report["items"]))}')
                self._write_report(dest, report)
        self._write_report(dest, report)
        self.stdout.write(self.style.SUCCESS(f'报告已保存：{dest}'))

    def _write_report(self, dest, report):
        report['summary'] = dict(Counter(item['status'] for item in report['items']))
        (dest / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = ['# 工作流逐项验证报告', '', f'范围：账号 {report["user_id"]} 的 {report["total"]} 个工作流。',
            '', '本地执行关闭节点缓存；仅运行本地计算和本机只读 HTTP 请求。合成输入仅用于测试数据通路，不代表真实业务验收。',
            '导入模板需要兼容适配、凭据及业务输入；执行前检查通过也不代表业务执行通过。', '', '| 结果 | 数量 |', '| --- | ---: |']
        lines.extend(f'| {REPORT_STATUSES[k]} | {v} |' for k, v in report['summary'].items())
        lines.extend(['', '| 工作流 | 结果 | 节点数 | 原因或执行记录 |', '| --- | --- | ---: | --- |'])
        for item in report['items']:
            name = item['name'].replace('|', '／').replace('\n', ' ')
            detail = item.get('error') or '；'.join(item['preflight']['errors']) or ('执行记录：' + item['execution_id'] if item.get('execution_id') else '所需节点：' + '、'.join(item['environment_node_types']))
            detail = detail.replace('|', '／').replace('\n', ' ')
            lines.append(f'| [{name}](http://localhost:5200/workflows/{item["id"]}/edit) | {REPORT_STATUSES[item["status"]]} | {item["node_count"]} | {detail} |')
        (dest / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
