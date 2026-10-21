"""Publish an actual completed 3D run's model viewer and portable deliverables."""
import argparse
import json
import shutil
import zipfile

from create_embroidery_3d_workflow import ROOT
from workflows.models import WorkflowExecution
from workflows.services.embroidery_3d import build_viewer, job_context, public, load_spec


def publish(execution_id):
    execution,directory=job_context({'_execution':{'metadata':{'execution_id':execution_id}}})
    if execution.status!='completed' or not (directory/'verification.json').is_file():
        raise ValueError('只有经过成片校验的真实执行可以发布')
    viewer=build_viewer(directory)
    output=dict(execution.output_data)
    output['website_url']=public(viewer)
    execution.output_data=output
    execution.save(update_fields=['output_data'])
    execution.workflow.config={**execution.workflow.config,'spec':load_spec()}
    execution.workflow.save(update_fields=['config'])
    destination=ROOT.parent/'output/butterfly-video/three_d_60'
    names={'butterfly_3d_60s.mp4':'蝶羽共生纹-60秒-三维数字刺绣.mp4','scene.blend':'蝶羽共生纹-三维动画工程.blend','pattern.glb':'蝶羽共生纹-三维纹样.glb','garment.glb':'蝶羽共生纹-三维服装.glb','preview_35.png':'蝶羽共生纹-三维融合效果.png','preview_56.png':'蝶羽共生纹-三维服装效果.png'}
    for source,target in names.items():
        shutil.copy2(directory/source,destination/target)
    readme={'workflow_id':str(execution.workflow_id),'execution_id':str(execution.pk),'viewer_url':public(viewer),'video_url':public(directory/'butterfly_3d_60s.mp4'),'verification':json.loads((directory/'verification.json').read_text(encoding='utf-8')),'disclosure':load_spec()['disclosure'],'model_method':'根据中轴、菱格、S形羽线重建连续三维几何；不是低分辨率截图的逐像素复刻','files':names}
    (destination/'deliverables.json').write_text(json.dumps(readme,ensure_ascii=False,indent=2),encoding='utf-8')
    workflow=execution.workflow
    graph={'name':workflow.name,'description':workflow.description,'config':workflow.config,'nodes':list(workflow.nodes.values('id','node_type','name','config','position_x','position_y','sort_order','timeout_seconds','error_handling')),'edges':list(workflow.edges.values('source_node_id','target_node_id'))}
    (destination/'workflow.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (destination/'README.md').write_text('蝶羽共生纹｜60秒三维数字刺绣\n\n视频包含平面参考、骨架生成、羽形生长、分解融合、三维环绕和服装曲面映射。没有真人或手部。\n\nscene.blend 保留完整动画、丝线几何和服装变形目标，源纹样图片已打包。pattern.glb / garment.glb 是可旋转的实际网格。viewer.html 使用包内 Three.js，可在本地 HTTP 服务中打开。GLB 不包含逐针动画，动画在 Blender 工程与 MP4 中。\n\n这是根据设计板的结构原则重建的三维概念模型，非实物成品或工艺验证，也不是截图的逐像素复刻。\n\n原生工作流：'+str(workflow.pk)+'\n执行记录：'+str(execution.pk)+'\n',encoding='utf-8')
    package=destination/'蝶羽共生纹-60秒三维完整素材包.zip'
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as bundle:
        for source in ['butterfly_3d_60s.mp4','scene.blend','pattern.glb','garment.glb','viewer.html','geometry.json','spec.json','verification.json','scene_report.json','captions.ass']:
            bundle.write(directory/source,source)
        for path in directory.glob('reference_*.png'):
            bundle.write(path,path.name)
        for path in directory.glob('preview_*.png'):
            bundle.write(path,path.name)
        for path in (directory/'vendor').rglob('*'):
            if path.is_file():bundle.write(path,path.relative_to(directory).as_posix())
        for name in ['workflow.json','README.md','deliverables.json']:
            bundle.write(destination/name,name)
    for preview in WorkflowExecution.objects.filter(workflow=execution.workflow,status='running',trigger_source__method='3d_model_development'):
        preview.status='cancelled';preview.error_message='三维预览迭代结束；正式60秒成片已另行完整执行。';preview.save(update_fields=['status','error_message'])
    print(json.dumps(readme,ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('execution_id');publish(parser.parse_args().execution_id)
