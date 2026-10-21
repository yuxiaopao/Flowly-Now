"""Build and run a native AI video workflow; never synthesize local substitute clips."""
import argparse
import json
from pathlib import Path
import shutil
import uuid

if __package__:
    from .create_butterfly_video_workflow import BACKEND_ROOT
else:
    from create_butterfly_video_workflow import BACKEND_ROOT
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from workflows.models import APICredential, Edge, Node, Workflow, WorkflowExecution
from workflows.services.media_service import build_public_media_url, local_path_from_public_url
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow
from workflows.services.partial_retry import prepare_continue

SPEC_PATH=BACKEND_ROOT/'workflows/services/butterfly_ai_video_spec.json'


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8'))


def prepare_reference_details(reference):
    """Crop source-board details for model inputs; these are never generated outputs."""
    from PIL import Image
    spec=load_spec();urls={}
    with Image.open(reference) as source:
        scale_x=source.width/spec['reference_source_size'][0];scale_y=source.height/spec['reference_source_size'][1]
        for name,box in spec['reference_crops'].items():
            target=reference.with_name(f'{reference.stem}-{name}-reference.png')
            source.crop(tuple(round(value*(scale_x if index%2==0 else scale_y)) for index,value in enumerate(box))).save(target)
            urls[name]=build_public_media_url(target.relative_to(settings.MEDIA_ROOT).as_posix())
    return urls


def make_graph(reference_url, credential_id, existing_ids=None, reference_details=None):
    spec=load_spec();nodes=[];edges=[]
    details=reference_details or {}
    def add(kind,name,config,x,y):
        if kind in ('image_generation','video_generation','subtitle_burn'):config={**config,'require_success':True}
        key=(existing_ids or {}).get(name) or str(uuid.uuid4());nodes.append({'id':key,'node_type':kind,'name':name,'config':config,'position_x':x,'position_y':y,'sort_order':len(nodes),'error_handling':'stop','timeout_seconds':spec['timeout_seconds']+300});return key
    def link(source,target):edges.append({'source':source,'target':target})
    start=add('start','开始·AI直接生成60秒视频',{},80,400)
    brief=add('variable','创新点一参考与生成规格',{'assignments':[{'name':'reference_url','value':reference_url,'source':'static'},{'name':'disclosure','value':spec['disclosure'],'source':'static'}]},340,400);link(start,brief)
    image_config={'provider':'agnes','model':spec['image_model'],'credentialId':credential_id,'size':spec['image_size'],'ratio':spec['ratio'],'n':1,'max_retries':spec['image_attempts'],'allow_provider_fallback':False}
    motif=add('image_generation','AI参考图·原图扩展为三维刺绣',dict(image_config,prompt=spec['style']+' '+spec['motif_image'],referenceImages=[details.get('motif',reference_url)]),620,400);link(brief,motif)
    motif_url='{node_outputs.'+motif+'.images.0.url}'
    garment=add('image_generation','AI参考图·同纹样三维服饰应用',dict(image_config,prompt=spec['style']+' '+spec['garment_image'],referenceImages=[details.get('garment',reference_url),motif_url]),900,400);link(motif,garment)
    garment_url='{node_outputs.'+garment+'.images.0.url}'
    videos=[];previous=garment
    for index,shot in enumerate(spec['shots']):
        references=[motif_url]+([garment_url] if index>=4 else [])
        video=add('video_generation',f'{index+1:02}·AI视频·{shot["name"]}',{'provider':'agnes','model':spec['video_model'],'credentialId':credential_id,'mode':'reference','referenceImages':references,'inputImage':'','prompt':spec['style']+' '+shot['motion'],'duration':spec['clip_seconds'],'fps':spec['fps'],'resolution':spec['resolution'],'seed':spec['seed'],'timeout':spec['timeout_seconds'],'submit_attempts':spec['video_submit_attempts'],'submit_interval_seconds':spec['video_submit_interval_seconds']},1220+index*570,400);link(previous,video);videos.append(video)
        check=add('code',f'{index+1:02}·校验AI镜头完整性',{'code':"node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"clip=node_outputs.get({video!r},{{}})\n"+"if not isinstance(clip,dict) or not clip.get('video_url') or clip.get('demo') or clip.get('error') or clip.get('provider')!='agnes' or not str(clip.get('model','')).startswith('agnes-video') or float(clip.get('duration',0))<10:\n    raise ValueError('AI镜头尚未真实生成，停止后续请求并保留已有产物')\noutput=clip\n"},1500+index*570,400);link(video,check);previous=check
    collector=("node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"required={videos!r}\n"+"clips=[]\nfor node_id in required:\n    clip=node_outputs.get(node_id,{})\n    if not isinstance(clip,dict) or not clip.get('video_url') or clip.get('demo') or clip.get('error') or clip.get('provider')!='agnes' or not str(clip.get('model','')).startswith('agnes-video'):\n        raise ValueError('缺少真实AI视频片段，停止合成：'+node_id)\n    if float(clip.get('duration',0))<10:\n        raise ValueError('AI片段不足10秒，禁止重复或拉长凑时长')\n    clips.append(clip['video_url'])\nif len(set(clips))!=len(required):\n    raise ValueError('AI镜头重复，停止合成')\noutput={'video_urls':clips}\n")
    collect=add('code','校验六段真实AI视频·禁止本地替代',{'code':collector},1590,400)
    link(previous,collect)
    merge=add('merge','合成60秒·六段各10秒',{'mode':'concat','target_duration_sec':spec['duration_seconds'],'clip_duration_sec':spec['clip_seconds'],'fill_mode':'none'},1890,400);link(collect,merge)
    gate=add('code','检查六镜合成完整性',{'code':"node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"result=node_outputs.get({merge!r},{{}})\n"+"if not result.get('concatenated') or result.get('clip_count')!=6 or result.get('error') or not result.get('video_url'):\n    raise ValueError('六段AI视频没有完整合成，禁止首片回退')\noutput=result\n"},2180,400);link(merge,gate)
    def timecode(t):return f'00:{t//60:02}:{t%60:02},000'
    subtitles='\n\n'.join(f'{i+1}\n{timecode(i*10)} --> {timecode((i+1)*10)}\n{s["caption"]}\n{spec["disclosure"]}' for i,s in enumerate(spec['shots']))+'\n'
    burn=add('subtitle_burn','烧录分镜说明与AI生成标识',{'video_input':'{video_url}','subtitles':subtitles,'subtitle_format':'srt'},2490,400);link(gate,burn)
    checked=add('code','确认AI标识已烧录',{'code':"node_outputs=input.get('input',input).get('node_outputs',{})\n"+f"result=node_outputs.get({burn!r},{{}})\n"+"if not result.get('burn_subtitles_applied') or not result.get('video_url'):\n    raise ValueError('AI说明未烧录，停止交付')\noutput=result\n"},2780,400);link(burn,checked)
    output=add('output','播放与下载60秒AI成片',{'template':'{video_url}','format':'video','output_variable':'final_video'},3080,400);link(checked,output)
    end=add('end','结束·六镜均来自AI视频模型',{},3380,400);link(output,end)
    for index,row in enumerate(nodes):
        row['position_x']=80+index*300
        row['position_y']=400
    return nodes,edges


@transaction.atomic
def create(reference,credential_id):
    owner=get_user_model().objects.get(username='nlwftest');credential=APICredential.objects.get(pk=credential_id,owner=owner,service_type='agnes',is_active=True)
    folder=Path(settings.MEDIA_ROOT)/'workflow_references'/str(owner.pk);folder.mkdir(parents=True,exist_ok=True)
    uploaded=folder/f'innovation_one_ai_{uuid.uuid4().hex[:8]}.png';shutil.copy2(reference,uploaded)
    reference_url=build_public_media_url(uploaded.relative_to(settings.MEDIA_ROOT).as_posix());spec=load_spec()
    details=prepare_reference_details(uploaded)
    workflow=Workflow.objects.create(owner=owner,name=spec['name'],description='用AI图像模型提取创新点一参考，六段10秒动态全部由AI视频模型生成；仅做拼接与字幕后期，不调用本地建模或本地动画渲染。',category='AI视频生成',tags=['蝶羽共生纹','60秒','AI直接生成','数字刺绣'],config={'video_spec':spec,'reference_url':reference_url,'reference_details':details})
    nodes,edges=make_graph(reference_url,str(credential.pk),reference_details=details)
    for row in nodes:Node.objects.create(workflow=workflow,**row)
    for row in edges:Edge.objects.create(workflow=workflow,source_node_id=row['source'],target_node_id=row['target'])
    validation=validate_workflow(workflow)
    if not validation['valid']:raise ValueError(validation)
    return workflow


@transaction.atomic
def update_graph(workflow,credential_id):
    reference=local_path_from_public_url(workflow.config['reference_url'])
    if not reference or not reference.is_file():raise ValueError('原始创新点一参考图不可用')
    details=prepare_reference_details(reference)
    nodes,edges=make_graph(workflow.config['reference_url'],credential_id,{node.name:str(node.pk) for node in workflow.nodes.all()},details)
    for row in nodes:
        key=row.pop('id');Node.objects.update_or_create(pk=key,workflow=workflow,defaults=row)
    workflow.edges.all().delete()
    for row in edges:Edge.objects.create(workflow=workflow,source_node_id=row['source'],target_node_id=row['target'])
    workflow.config={**workflow.config,'video_spec':load_spec(),'reference_details':details};workflow.save(update_fields=['config'])
    result=validate_workflow(workflow)
    if not result['valid']:raise ValueError(result)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reference',type=Path);parser.add_argument('--workflow');parser.add_argument('--credential',required=True);parser.add_argument('--update',action='store_true');parser.add_argument('--execute',action='store_true');parser.add_argument('--resume-execution');args=parser.parse_args()
    workflow=Workflow.objects.get(pk=args.workflow) if args.workflow else create(args.reference,args.credential)
    if args.update:update_graph(workflow,args.credential)
    folder=BACKEND_ROOT.parent/'output/butterfly-video/ai_60';folder.mkdir(parents=True,exist_ok=True)
    (folder/'workflow-id.txt').write_text(str(workflow.pk),encoding='utf-8')
    (folder/'workflow.json').write_text(json.dumps({'id':str(workflow.pk),'name':workflow.name,'spec':load_spec(),'nodes':list(workflow.nodes.values('id','name','node_type','config','position_x','position_y')),'edges':list(workflow.edges.values('source_node_id','target_node_id'))},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'workflow_id':str(workflow.pk),'validation':validate_workflow(workflow)},ensure_ascii=True),flush=True)
    if args.execute or args.resume_execution:
        if args.resume_execution:
            execution=WorkflowExecution.objects.get(pk=args.resume_execution,workflow=workflow)
            prepare_continue(execution)
            execution.trigger_source={**execution.trigger_source,'provider':load_spec()['video_model'],'credential_id':args.credential};execution.total_nodes=workflow.nodes.count();execution.save(update_fields=['trigger_source','total_nodes'])
        else:
            execution=WorkflowExecution.objects.create(workflow=workflow,version=workflow.version,triggered_by=workflow.owner,input_data={'reference_url':workflow.config['reference_url']},trigger_type='api',trigger_source={'method':'ai_video_generation','duration_seconds':60,'provider':load_spec()['video_model']})
        (folder/'execution-id.txt').write_text(str(execution.pk),encoding='utf-8');print(json.dumps({'execution_id':str(execution.pk)}),flush=True)
        WorkflowExecutor(workflow,execution,parallel_enabled=False).execute(resume=bool(args.resume_execution));execution.refresh_from_db()
        report={'workflow_id':str(workflow.pk),'execution_id':str(execution.pk),'status':execution.status,'error':execution.error_message,'ai_video_nodes':list(execution.node_executions.filter(node__node_type='video_generation').values('node__name','status','output_data','error_message'))}
        (folder/'execution-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True),flush=True)
        if execution.status!='completed':raise SystemExit(1)
        video=execution.output_data.get('variables',{}).get('final_video');path=local_path_from_public_url(video)
        if not path or not path.is_file():raise RuntimeError('AI成片没有保存到本地')
        shutil.copy2(path,folder/'蝶羽共生纹-60秒-AI直接生成.mp4')
