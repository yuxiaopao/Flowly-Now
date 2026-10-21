"""Create the native 60-second geometry workflow, without external AI billing."""
import argparse
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from workflows.models import Edge, Node, Tool, Workflow, WorkflowExecution
from workflows.services.embroidery_3d import execute, load_spec, public
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow

STAGES = [('prepare','01·原图提取与丝线路径'),('build','02·三维骨架·羽形·服装建模'),('animate','03·逐针生成·分解融合·曲面映射'),('previews','04·三维效果图预览'),('render','05·60秒三维全片渲染'),('finish','06·字幕烧录与完整成片校验')]


def make_graph(reference_url):
    spec=load_spec()
    nodes=[{'id':str(uuid.uuid4()),'node_type':'start','name':'开始·创新点一三维数字刺绣','config':{},'position_x':80,'position_y':300,'sort_order':0}]
    for i,(operation,name) in enumerate(STAGES,1):
        nodes.append({'id':str(uuid.uuid4()),'node_type':'tool','name':name,'config':{'tool':'embroidery_3d','parameters':{'operation':operation,'preset':spec['preset'],'reference_url':reference_url},'description':name,'label':name},'position_x':80+i*290,'position_y':300,'sort_order':i,'timeout_seconds':spec['process_timeout']+60,'error_handling':'stop'})
    nodes.append({'id':str(uuid.uuid4()),'node_type':'end','name':'结束·视频与真实三维资产已保存','config':{},'position_x':80+7*290,'position_y':300,'sort_order':7})
    return nodes,[{'source':a['id'],'target':b['id']} for a,b in zip(nodes,nodes[1:])]


@transaction.atomic
def create(reference):
    spec=load_spec()
    owner=get_user_model().objects.get(username='nlwftest')
    with reference.open('rb') as image:
        relative=default_storage.save(f'workflow_references/{owner.pk}/innovation_one_3d.png',File(image))
    reference_url=public(Path(default_storage.path(relative)))
    Tool.objects.update_or_create(name='embroidery_3d',defaults={'display_name':'三维数字刺绣','description':'Blender丝线建模、逐针生成、服装曲面映射与视频渲染','tool_type':'builtin','is_public':True,'is_enabled':True,'category':'3D媒体','input_schema':{'type':'object','properties':{'operation':{'type':'string','description':'prepare / build / animate / previews / render / finish'},'preset':{'type':'string','default':spec['preset']},'reference_url':{'type':'string','description':'已上传的创新点一设计图地址'}}},'timeout_seconds':spec['process_timeout']})
    workflow=Workflow.objects.create(owner=owner,name=spec['name'],description='根据创新点一原平面设计图创建实际三维丝线曲线与服装网格；60秒完整展示骨架、羽形、逐针生成、三维环绕与曲面映射。没有真人刺绣，不使用AI图片冒充三维建模。',category='三维数字刺绣',tags=['蝶羽共生纹','三维模型','逐针生长','服装映射','60秒'],config={'reference_url':reference_url,'spec':spec,'renderer':'Blender 4.5 LTS','concept_only':True})
    nodes,edges=make_graph(reference_url)
    for row in nodes:
        Node.objects.create(workflow=workflow,**row)
    for row in edges:
        Edge.objects.create(workflow=workflow,source_node_id=row['source'],target_node_id=row['target'])
    validation=validate_workflow(workflow,{})
    if not validation['valid']:
        raise ValueError(validation)
    return workflow


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--workflow')
    parser.add_argument('--operation',choices=[x[0] for x in STAGES])
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    workflow=Workflow.objects.get(pk=args.workflow) if args.workflow else create(args.reference)
    report_root=ROOT.parent/'output/butterfly-video/three_d_60'
    report_root.mkdir(parents=True,exist_ok=True)
    (report_root/'workflow-id.txt').write_text(str(workflow.pk),encoding='utf-8')
    if args.execute:
        execution=WorkflowExecution.objects.create(workflow=workflow,triggered_by=workflow.owner,version=workflow.version,input_data={'reference_url':workflow.config['reference_url']},trigger_type='api',trigger_source={'method':'blender_3d','duration_seconds':60})
        (report_root/'execution-id.txt').write_text(str(execution.pk),encoding='utf-8')
        print(json.dumps({'workflow_id':str(workflow.pk),'execution_id':str(execution.pk)}),flush=True)
        WorkflowExecutor(workflow,execution,parallel_enabled=False).execute()
        execution.refresh_from_db()
        print(json.dumps({'status':execution.status,'error':execution.error_message},ensure_ascii=True),flush=True)
        if execution.status!='completed':
            raise SystemExit(1)
    elif args.operation:
        # Preview development is recorded honestly as a native tool execution.
        from workflows.models import NodeExecution
        state_path=report_root/'preview-execution-id.txt'
        if state_path.exists():
            execution=WorkflowExecution.objects.get(pk=state_path.read_text().strip())
        else:
            execution=WorkflowExecution.objects.create(workflow=workflow,triggered_by=workflow.owner,version=workflow.version,input_data={'reference_url':workflow.config['reference_url']},trigger_type='api',trigger_source={'method':'3d_model_development'})
            execution.mark_started()
            state_path.write_text(str(execution.pk),encoding='utf-8')
        node=workflow.nodes.get(config__parameters__operation=args.operation)
        record=NodeExecution.objects.create(execution=execution,node=node,node_version=1,status='running')
        try:
            result=execute(node.config['parameters'],{'_execution':{'metadata':{'execution_id':str(execution.pk)}}})
            record.status='completed'
            record.output_data=result
            record.save(update_fields=['status','output_data'])
            execution.update_node_status(node.pk,'completed',{'output':result})
            execution.output_data={'node_outputs':{str(row.node_id):row.output_data for row in execution.node_executions.all() if row.output_data}}
            execution.save(update_fields=['output_data'])
            print(json.dumps(result,ensure_ascii=True),flush=True)
        except BaseException as error:
            record.status='failed';record.error_message=str(error);record.save(update_fields=['status','error_message'])
            execution.mark_failed(str(error))
            raise
    else:
        print(json.dumps({'workflow_id':str(workflow.pk),'validation':validate_workflow(workflow,{})},ensure_ascii=True))
