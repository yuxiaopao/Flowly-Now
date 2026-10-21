"""Build and execute the real, free LTX AI generation and finishing workflow."""
import argparse
import json
from pathlib import Path
import shutil
import uuid

if __package__:
    from .create_butterfly_video_workflow import BACKEND_ROOT
else:
    from create_butterfly_video_workflow import BACKEND_ROOT
from django.contrib.auth import get_user_model
from workflows.models import Edge, Node, Workflow, WorkflowExecution
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow
from workflows.services.media_service import local_path_from_public_url

SPEC_PATH=BACKEND_ROOT/'workflows/services/butterfly_ltx_spec.json'
OUTPUT=BACKEND_ROOT.parent/'output/butterfly-video/ai_60'


def graph(spec):
    nodes=[];edges=[]
    def add(kind,name,config):
        index=len(nodes);row=index//5;column=index%5 if row%2==0 else 4-index%5
        item={'id':str(uuid.uuid4()),'node_type':kind,'name':name,'config':config,'sort_order':index,
              'position_x':80+column*360,'position_y':160+row*230,'timeout_seconds':spec['timeout_seconds']+300,'error_handling':'stop'}
        nodes.append(item)
        if len(nodes)>1:edges.append({'source':nodes[-2]['id'],'target':item['id']})
        return item['id']
    add('start','开始｜免费 AI 生成 60 秒视频',{})
    add('variable','八镜头规格与 AI 生成说明',{'assignments':[{'name':'film_title','value':'蝶羽共生纹','source':'static'},
        {'name':'disclosure','value':'AI 生成概念演示；视频由 LTX 扩散模型生成，未调用本地建模动画','source':'static'}]})
    clips=[]
    for index,shot in enumerate(spec['shots']):
        clips.append(add('tool',f'AI 镜头 {index+1:02}｜{shot["caption"][3:]}',{'tool':'ltx_ai_video','handler':'workflows.services.butterfly_ltx_job.generate_node',
            'parameters':{'shot_index':index+1},'require_success':True,
            'description':'调用免费本机 AI 视频模型；存在与提示词、时长、校验值一致的真实模型输出时复用，避免重复推理。'}))
    code="node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"required={clips!r}\n"+"clips=[]\nchecksums=[]\nfor node_id in required:\n    clip=node_outputs.get(node_id,{})\n    if clip.get('provider') not in ('ltx_local','ltx_public') or not str(clip.get('model','')).startswith('Lightricks/') or not clip.get('video_url') or abs(float(clip.get('duration',0))-7.5)>0.05 or not clip.get('sha256'):\n        raise ValueError('缺少真实且完整的 AI 镜头，禁止本地动画替代或拉长补时')\n    clips.append(clip['video_url'])\n    checksums.append(clip['sha256'])\nif len(set(checksums))!=len(required):\n    raise ValueError('视频镜头重复')\noutput={'video_urls':clips}\n"
    add('code','校验八段真实 AI 视频与时长',{'code':code})
    merge=add('merge','拼接 60 秒｜八段各 7.5 秒',{'mode':'concat','target_duration_sec':60,'clip_duration_sec':7.5,'fill_mode':'none'})
    add('code','检查八镜合成完整性',{'code':"node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"result=node_outputs.get({merge!r},{{}})\n"+"if not result.get('concatenated') or result.get('clip_count')!=8 or not result.get('video_url') or result.get('error'):\n    raise ValueError('八镜头没有完整合成')\noutput=result\n"})
    def timestamp(seconds):
        ms=round(seconds*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    srt='\n\n'.join(f'{i+1}\n{timestamp(i*spec["seconds"])} --> {timestamp((i+1)*spec["seconds"])}\n{shot["caption"]}\nAI 生成概念演示'for i,shot in enumerate(spec['shots']))+'\n'
    burn=add('subtitle_burn','烧录分镜说明与 AI 标识',{'video_input':'{video_url}','subtitles':srt,'subtitle_format':'srt','require_success':True})
    add('code','检查字幕与最终视频',{'code':"node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"result=node_outputs.get({burn!r},{{}})\n"+"if not result.get('burn_subtitles_applied') or not result.get('video_url'):\n    raise ValueError('AI 标识没有写入成片')\noutput=result\n"})
    add('output','播放与下载 60 秒 AI 成片',{'template':'{video_url}','format':'video','output_variable':'final_video'})
    add('end','结束｜真实 AI 片段已完成合成',{})
    return nodes,edges


def create_and_run(username,execute):
    spec=json.loads(SPEC_PATH.read_text(encoding='utf-8'));owner=get_user_model().objects.get(username=username)
    workflow=Workflow.objects.create(owner=owner,name='蝶羽共生纹｜免费 LTX AI 生成 60 秒成片',
        description='以原稿生成的关键帧为输入，LTX 视频扩散模型生成八个7.5秒镜头；真实片段按提示词、时长与文件校验值复用。当前画布原生执行模型产物校验、拼接与字幕。未调用Blender建模或图片轮播补时。',
        category='AI视频生成',tags=['蝶羽共生纹','AI直接生成','免费模型','60秒'],config={'video_spec':spec,'generation_script':str(BACKEND_ROOT/'scripts/generate_butterfly_local_ltx.py')})
    nodes,edges=graph(spec)
    for row in nodes:Node.objects.create(workflow=workflow,**row)
    for row in edges:Edge.objects.create(workflow=workflow,source_node_id=row['source'],target_node_id=row['target'])
    validation=validate_workflow(workflow)
    if not validation['valid']:raise ValueError(validation)
    (OUTPUT/'ltx-workflow-id.txt').write_text(str(workflow.pk),encoding='utf-8')
    (OUTPUT/'ltx-workflow.json').write_text(json.dumps({'id':str(workflow.pk),'name':workflow.name,'spec':spec,'nodes':nodes,'edges':edges},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'workflow_id':str(workflow.pk),'validation':validation}),flush=True)
    if execute:
        execution=WorkflowExecution.objects.create(workflow=workflow,version=workflow.version,triggered_by=owner,trigger_type='api',trigger_source={'method':'free_ltx_ai_video','duration_seconds':60})
        (OUTPUT/'ltx-execution-id.txt').write_text(str(execution.pk),encoding='utf-8')
        WorkflowExecutor(workflow,execution,parallel_enabled=False).execute();execution.refresh_from_db()
        result={'workflow_id':str(workflow.pk),'execution_id':str(execution.pk),'status':execution.status,'error':execution.error_message,'output':execution.output_data}
        (OUTPUT/'ltx-execution-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items()if k!='output'},ensure_ascii=True),flush=True)
        if execution.status!='completed':raise RuntimeError(execution.error_message)
        final=local_path_from_public_url(execution.output_data['variables']['final_video'])
        shutil.copy2(final,OUTPUT/'蝶羽共生纹-60秒-AI工作流版.mp4')
    return workflow


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--username',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    create_and_run(args.username,args.execute)
