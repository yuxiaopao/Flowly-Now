"""Build the modular sewing demonstration and execute it through Flowly."""
import argparse
import copy
import json
import shutil
import uuid

if __package__:
    from .create_butterfly_video_workflow import BACKEND_ROOT
else:
    from create_butterfly_video_workflow import BACKEND_ROOT
from django.contrib.auth import get_user_model
from workflows.models import Edge, Node, Workflow, WorkflowExecution
from workflows.services.media_service import local_path_from_public_url
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow
from workflows.services.embroidery_module_job import build_request, LOCAL_MODELS

ROOT = BACKEND_ROOT.parent
ASSETS = ROOT / 'output/butterfly-video'
OUTPUT = ASSETS / 'flowly_modular_60'
HANDLER = 'workflows.services.embroidery_module_job.'
TITLE = '蝶羽共生纹｜分模块走线刺绣 · 斜襟服装 · 60秒'
FINAL_NAME = '蝶羽共生纹-60秒-Flowly分模块刺绣版.mp4'
MODEL_CONFIG = {
    'width': 1024, 'height': 576, 'fps': 30, 'seconds': 5.1,
    'seed': 36854, 'timeout_seconds': 1200, 'cpu_threads': 4, 'gpu_memory_fraction': 0.70,
    'vae_tiling': {'tile_sample_min_height': 128, 'tile_sample_min_width': 128,
                   'tile_sample_min_num_frames': 16, 'tile_sample_stride_height': 96,
                   'tile_sample_stride_width': 96, 'tile_sample_stride_num_frames': 8},
}
ENCODING = {
    'width': 1024, 'height': 576, 'fps': 30, 'sampling_scale': 2, 'preset': 'medium',
    'crf': 18, 'timescale': 15360, 'timeout_seconds': 600,
    'optical_flow': 'minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir',
}
MOTION_TEMPLATE = {'seconds': 5, 'start_frame': 0, 'end_frame': 150, 'retiming_factor': 1,
                   'zoom': [1, 1], 'x': [0.5, 0.5], 'y': [0.5, 0.5]}


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def make_spec():
    recent = load_json(ASSETS / 'ai_stitched_60/delivery-spec.json')
    edits = {m['id']: m for m in load_json(ASSETS / 'ai_stitched_60/edit-spec.json')['motions']}
    original = load_json(BACKEND_ROOT / 'workflows/services/butterfly_ltx_spec.json')
    modules = []

    def retained(folder, source_spec, shot_id, caption, edit):
        shot = copy.deepcopy(next(s for s in source_spec['shots'] if s['id'] == shot_id))
        record = load_json(ASSETS / folder / 'clips' / (shot_id + '.json'))
        shot['end_image'] = record['last_frame']
        shot['seed'] = record['seed']
        model_spec = {**MODEL_CONFIG, 'seconds': source_spec['seconds']}
        modules.append({'id': shot_id, 'caption': caption, 'source_directory': folder,
                        'source_sha256': record['sha256'], 'shot': shot,
                        'model_spec': model_spec, 'edit': {**MOTION_TEMPLATE, **edit}})

    retained('ai_stitched_60', recent, '01-axis-loops', '模块一｜中轴起线 · 穿出布面', edits['01-axis-loops'])
    retained('ai_stitched_60', recent, '02-axis-tighten-v2', '模块一｜中轴收线 · 逐针落定', edits['02-axis-tighten-v2'])
    retained('ai_stitched_60', recent, '04-diamond-macro-v2', '模块二｜菱格转角 · 沿折线逐针收紧',
             {**edits['04-diamond-macro-v2'], 'seconds': 10, 'retiming_factor': 2.7})
    modules[-1]['id'] = 'diamond-travel'
    captions = {'curve': '凤羽轮廓 · 沿 S 形逐针走线', 'feather': '蓝线羽片 · 逐根填绣'}
    for index, (name, caption) in enumerate(captions.items(), start=1):
        prefix = name + '-travel'
        end = prefix + '-end.png' if name != 'feather' else 'feather-end.png'
        path_description = (
            'A single small blue arc travels along the S shaped dotted path from lower left '
            'to upper right. It contracts down and leaves short separated flat blue segments '
            'behind. The parallel ivory segmented curve remains unchanged.'
            if name == 'curve' else
            'A single small blue arc travels along the curved rib from lower left to upper right. '
            'It contracts down into one fine flat transverse blue line, then the next arc forms '
            'just ahead and contracts down. Parallel blue lines gradually fill the bare sector. '
            'The curved rib and the distant diamond stay unchanged.')
        prompt = (
            'ABSTRACT COMPUTER ANIMATION of ONLY blue filaments on an EMPTY ivory cloth surface. '
            'The surrounding cloth stays EMPTY in EVERY frame. Only blue lines and cloth exist. '
            + path_description +
            ' Every completed line lies flat and remains motionless. All points where blue lines '
            'meet the cloth stay fixed. Only the slender active arc changes curvature and height. '
            'Constant thin filament diameter, tiny silky fibers, delicate contact shadows. '
            'Invisible tension underneath the surface drives the movement. Empty foreground and '
            'empty background, no external object ever enters. Fixed oblique camera and constant '
            'soft side light. No people, hands, fingers, skin, needles or tools. '
            'Fine material motion study, no large shape moving or floating.')
        shot = {'id': prefix, 'image': prefix + '-start.png', 'end_image': end,
                'seed': MODEL_CONFIG['seed'] + index + 1000, 'prompt': prompt,
                'conditions': [
                    {'image': prefix + '-start.png', 'frame_index': 16},
                    {'image': prefix + '-mid.png', 'frame_index': 48},
                    {'image': prefix + '-mid.png', 'frame_index': 80},
                    {'image': end, 'frame_index': 112},
                    {'image': end, 'frame_index': 136},
                ]}
        edit = {**MOTION_TEMPLATE, 'seconds': 10, 'end_frame': 153, 'retiming_factor': 2,
                'zoom': [1.01, 1.035], 'x': [0.35, 0.65], 'y': [0.6, 0.4]}
        model_spec = MODEL_CONFIG
        if name == 'feather':
            model_spec = {**MODEL_CONFIG, 'guidance_scale': 2.5, 'guidance_rescale': 0.7,
                'negative_prompt': 'A human hand, fingers, human skin, fingernails, a person sewing, hands holding a needle, embroidery tools, a metallic needle, human arms, an object entering the frame, fingers covering the cloth, floating detached shapes, thick rubber cords, deformed geometry, chaotic camera rotation.'}
            # Exclude the later distorted tuft while retaining the advancing thread.
            edit.update(end_frame=84, retiming_factor=3.7)
        modules.append({'id': prefix, 'caption': f'模块{index+2}｜' + caption,
                        'source_directory': 'flowly_modular_60', 'shot': shot,
                        'model_spec': model_spec, 'edit': edit})
    retained('ai_stitched_60', recent, '08-feather-fill-v2', '模块五｜米白填绣 · 细线收紧',
             {**MOTION_TEMPLATE, 'zoom': [1.04, 1.06], 'x': [0.5, 0.7]})
    retained('ai_stitched_60', recent, '10-finished-motif-wide', '蝶骨凤羽共生 · 完整刺绣纹样', edits['10-finished-motif-wide'])
    retained('ai_60', original, '06-garment-map', '纹样入衣 · 沿斜襟重组',
             {**MOTION_TEMPLATE, 'end_frame': 225, 'retiming_factor': 0.68})
    retained('ai_60', original, '08-final', '斜襟与袖口呼应 · 服装呈现',
             {**MOTION_TEMPLATE, 'start_frame': 75, 'end_frame': 225})
    spec = {'title': TITLE, 'seconds': 60, 'encoding': ENCODING, 'modules': modules,
            'disclosure': '', 'workflow_timeout_seconds': 5400}
    if sum(m['edit']['seconds'] for m in modules) != spec['seconds']:
        raise ValueError('分模块时长必须恰好为 60 秒')
    for module in modules:
        if module.get('source_sha256'):
            module['source_keyframe_hashes'] = build_request(module, {})[0]['keyframe_hashes']
    return spec


def make_graph(spec):
    nodes, edges = [], []
    def add(kind, name, config):
        index = len(nodes)
        row, column = divmod(index, 4)
        if row % 2:
            column = 3 - column
        node = {'id': str(uuid.uuid4()), 'node_type': kind, 'name': name, 'config': config,
                'position_x': 80 + column * 410, 'position_y': 120 + row * 250,
                'sort_order': index, 'timeout_seconds': MODEL_CONFIG['timeout_seconds'] + ENCODING['timeout_seconds'],
                'error_handling': 'stop'}
        nodes.append(node)
        if index:
            edges.append({'source': nodes[-2]['id'], 'target': node['id']})
        return node['id']
    add('start', '开始｜分模块 AI 刺绣', {})
    add('variable', '45秒刺绣＋5秒纹样＋10秒服装', {'assignments': [
        {'name': 'film_title', 'source': 'static', 'value': TITLE},
        {'name': 'disclosure', 'source': 'static', 'value': spec['disclosure']},
    ]})
    required = []
    for module in spec['modules']:
        family = module.get('model_spec', {}).get('model_family', 'ltx')
        node_id = add('tool', module['caption'], {'tool': 'ltx_embroidery_module',
            'handler': HANDLER + 'generate_node', 'require_success': True,
            'description': f'免费 {family.upper()} 视频生成；每段独立关键帧、提示词、种子、缓存与剪辑。修改种子可重生成此模块；失败可从当前节点继续。',
            'parameters': {'module_id': module['id'], 'prompt': module['shot']['prompt'], 'seed': module['shot']['seed']}})
        required.append((node_id, module['edit']['seconds'], LOCAL_MODELS[family]['provider']))
    code = ("outputs=input.get('input',input).get('node_outputs',{})\n"
            f"required={required!r}\nurls=[]\nchecksums=[]\n"
            "for node_id,seconds,provider in required:\n"
            "    row=outputs.get(node_id,{})\n"
            "    if row.get('provider')!=provider or not row.get('video_url') or not row.get('source_sha256') or abs(float(row.get('duration',0))-seconds)>0.01:\n"
            "        raise ValueError('刺绣模块缺失或时长错误，禁止跳过')\n"
            "    urls.append(row['video_url'])\n    checksums.append(row['source_sha256'])\n"
            "if len(set(checksums))!=len(required):\n    raise ValueError('禁止重复镜头凑时长')\n"
            "output={'video_urls':urls}\n")
    add('code', '逐段校验 AI 来源、顺序与时长', {'code': code})
    merge = add('merge', '保留各模块节奏 · 拼接60秒', {'mode': 'concat', 'target_duration_sec': spec['seconds'],
                                                        'fill_mode': 'preserve', 'require_success': True})
    add('code', '检查全部模块完成拼接', {'code':
        "outputs=input.get('input',input).get('node_outputs',{})\n" + f"row=outputs.get({merge!r},{{}})\n" +
        f"if not row.get('concatenated') or row.get('clip_count')!={len(required)} or row.get('error'):\n" +
        "    raise ValueError('模块未全部拼接成功')\noutput=row\n"})
    def stamp(seconds):
        value = round(seconds * 1000)
        return f'{value//3600000:02}:{value//60000%60:02}:{value//1000%60:02},{value%1000:03}'
    captions, cursor = [], 0
    for index, module in enumerate(spec['modules']):
        end = cursor + module['edit']['seconds']
        text = '\n'.join(line for line in (module['caption'], spec['disclosure']) if line)
        captions.append(f"{index+1}\n{stamp(cursor)} --> {stamp(end)}\n{text}")
        cursor = end
    add('subtitle_burn', '烧录模块说明', {'video_input': '{video_url}', 'subtitles': '\n\n'.join(captions),
                                            'subtitle_format': 'srt', 'require_success': True})
    add('tool', '成片完整解码与60秒校验', {'tool': 'verify_embroidery_film', 'handler': HANDLER + 'verify_final',
         'parameters': {'seconds': spec['seconds'], 'timeout_seconds': ENCODING['timeout_seconds']}, 'require_success': True})
    add('output', '播放与下载｜60秒分模块刺绣', {'template': '{video_url}', 'format': 'video', 'output_variable': 'final_video'})
    add('end', '完成｜斜襟服装版本', {})
    return nodes, edges


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default='nlwftest')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--workflow-id')
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.workflow_id:
        workflow = Workflow.objects.get(pk=args.workflow_id, owner__username=args.username)
        spec = workflow.config['embroidery_spec']
    else:
        spec = make_spec()
        owner = get_user_model().objects.get(username=args.username)
        workflow = Workflow.objects.create(owner=owner, name=TITLE, category='AI视频生成',
            description='独立模块缝制中轴、菱格、S形凤羽与羽片，保留45秒刺绣过程，恢复斜襟蓝灰羽纹服装。免费本机AI视频模型；支持失败节点继续和单模块重生成。',
            tags=['免费AI视频', '模块刺绣', '60秒', '斜襟服装'],
            config={'embroidery_spec': spec, 'timeout_seconds': spec['workflow_timeout_seconds']})
        nodes, edges = make_graph(spec)
        for node in nodes:
            Node.objects.create(workflow=workflow, **node)
        for edge in edges:
            Edge.objects.create(workflow=workflow, source_node_id=edge['source'], target_node_id=edge['target'])
        validation = validate_workflow(workflow)
        if not validation['valid']:
            raise ValueError(validation)
        (OUTPUT / 'workflow-graph.json').write_text(json.dumps({'workflow_id': str(workflow.pk), 'nodes': nodes, 'edges': edges}, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUTPUT / 'workflow-id.txt').write_text(str(workflow.pk), encoding='utf-8')
    (OUTPUT / 'film-spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'workflow_id': str(workflow.pk), 'modules': len(spec['modules'])}), flush=True)
    if args.execute:
        execution = WorkflowExecution.objects.create(workflow=workflow, version=workflow.version, triggered_by=workflow.owner,
            trigger_type='api', trigger_source={'method': 'modular_embroidery', 'duration_seconds': spec['seconds']})
        (OUTPUT / 'execution-id.txt').write_text(str(execution.pk), encoding='utf-8')
        WorkflowExecutor(workflow, execution, parallel_enabled=False).execute()
        execution.refresh_from_db()
        result = {'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'status': execution.status,
                  'error': execution.error_message, 'output': execution.output_data}
        (OUTPUT / 'execution-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print(json.dumps({k: v for k, v in result.items() if k != 'output'}), flush=True)
        if execution.status != 'completed':
            raise RuntimeError(execution.error_message)
        final = local_path_from_public_url(execution.output_data['variables']['final_video'])
        shutil.copy2(final, OUTPUT / FINAL_NAME)


if __name__ == '__main__':
    main()
