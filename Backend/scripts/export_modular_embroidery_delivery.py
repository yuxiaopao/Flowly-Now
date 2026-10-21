"""Verify and export the actual Flowly execution and both delivery videos."""
import json
import shutil
import subprocess

if __package__:
    from .create_modular_embroidery_workflow import OUTPUT, FINAL_NAME
else:
    from create_modular_embroidery_workflow import OUTPUT, FINAL_NAME
from workflows.models import Workflow, WorkflowExecution
from workflows.services.embroidery_module_job import build_request, digest, probe_media
from workflows.services.media_service import local_path_from_public_url


def main():
    workflow = Workflow.objects.get(pk=(OUTPUT / 'workflow-id.txt').read_text().strip())
    execution = WorkflowExecution.objects.get(pk=(OUTPUT / 'execution-id.txt').read_text().strip(), workflow=workflow)
    spec = workflow.config['embroidery_spec']
    if execution.status != 'completed' or execution.node_executions.exclude(status='completed').exists():
        raise ValueError('工作流尚未完整完成，不能导出交付版本')
    modules = {m['id']: m for m in spec['modules']}
    records, cursor = [], 0
    for result in execution.node_executions.select_related('node').order_by('node__sort_order'):
        params = result.node.config.get('parameters', {})
        if isinstance(params, str):
            params = json.loads(params)
        module_id = params.get('module_id')
        if module_id not in modules:
            continue
        module, record = modules[module_id], result.output_data
        request, _ = build_request(module, params)
        published = local_path_from_public_url(record['video_url'])
        source = record['source_file']
        if (record['request_fingerprint'] != request['fingerprint'] or record['sha256'] != digest(published)
                or record['source_sha256'] != digest(source) or record['edit'] != module['edit']):
            raise ValueError('实际输出不符合当前模块参数：' + module_id)
        duration = module['edit']['seconds']
        records.append({**record, 'timeline_start': cursor, 'timeline_end': cursor + duration})
        cursor += duration
    if len(records) != len(modules) or cursor != spec['seconds']:
        raise ValueError('镜头数量或总时长不完整')
    if len({r['source_sha256'] for r in records}) != len(records):
        raise ValueError('存在重复镜头')
    final = local_path_from_public_url(execution.output_data['variables']['final_video'])
    media = probe_media(final)
    stream = media['streams'][0]
    expected_frames = spec['seconds'] * spec['encoding']['fps']
    if (abs(float(media['format']['duration']) - spec['seconds']) > 0.001 or int(stream['nb_frames']) != expected_frames
            or stream['codec_name'] != 'h264' or stream['width'] != spec['encoding']['width']
            or stream['height'] != spec['encoding']['height']):
        raise ValueError('最终视频格式或帧数不正确')
    detection = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(final), '-vf', 'blackdetect=d=0.1:pix_th=0.10',
                                '-an', '-f', 'null', '-'], check=True, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=spec['encoding']['timeout_seconds'])
    black = [line for line in detection.stderr.splitlines() if 'black_start:' in line]
    if black:
        raise ValueError('成片出现黑场：' + repr(black))
    shutil.copy2(final, OUTPUT / FINAL_NAME)
    merge = execution.node_executions.get(node__node_type='merge').output_data
    clean = local_path_from_public_url(merge['video_url'])
    clean_name = '蝶羽共生纹-60秒-Flowly无字幕版.mp4'
    shutil.copy2(clean, OUTPUT / clean_name)
    fields = ('id', 'node_type', 'name', 'config', 'position_x', 'position_y', 'sort_order', 'timeout_seconds', 'error_handling')
    graph = {'id': str(workflow.pk), 'name': workflow.name, 'description': workflow.description,
             'config': workflow.config, 'nodes': list(workflow.nodes.order_by('sort_order').values(*fields)),
             'edges': list(workflow.edges.values('source_node_id', 'target_node_id'))}
    (OUTPUT / 'workflow-graph.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    manifest = {'status': 'encoded_pending_final_visual_review', 'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk),
                'workflow_status': execution.status, 'completed_nodes': execution.node_executions.count(),
                'video': str(OUTPUT / FINAL_NAME), 'clean_video': str(OUTPUT / clean_name),
                'seconds': cursor, 'frames': expected_frames, 'media': media,
                'sha256': digest(final), 'clean_sha256': digest(clean), 'black_intervals': [],
                'full_decode': 'passed in native workflow verification node', 'modules': records,
                'source_generation': 'Free local LTX neural video; native image_gen keyframes',
                'repeated_footage': False, 'still_padding': False}
    (OUTPUT / 'delivery-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'video': str(OUTPUT / FINAL_NAME), 'duration': cursor, 'frames': expected_frames,
                      'modules': len(records), 'native_execution': execution.status}), flush=True)


if __name__ == '__main__':
    main()
