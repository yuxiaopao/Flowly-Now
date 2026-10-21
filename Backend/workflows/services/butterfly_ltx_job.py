"""Native workflow adapter for actual, provenance-checked LTX AI video outputs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from django.conf import settings
from django.core.cache import cache
from workflows.models import WorkflowExecution
from workflows.execution_control import write_heartbeat
from .media_service import build_public_media_url

SPEC_PATH = Path(__file__).with_name('butterfly_ltx_spec.json')
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIRECTORY = PROJECT_ROOT / 'output/butterfly-video/ai_60'
SCRIPT_PATH = PROJECT_ROOT / 'Backend/scripts/generate_butterfly_local_ltx.py'
GPU_LOCK = 'workflow:local-ltx-video:cuda'
WAIT_SECONDS = 5
VIDEO_ENCODER = ('libx264', 'medium', '18')


def probe_media(path):
    return json.loads(subprocess.check_output([
        'ffprobe','-v','error','-show_entries',
        'format=duration:stream=codec_name,pix_fmt,width,height,nb_frames,r_frame_rate',
        '-of','json',str(path),
    ],text=True,timeout=30))


def publish_clip(source,folder,record):
    """Keep the exact model output and publish a browser-compatible encoding."""
    original=folder/(source.stem+'.model.mp4')
    target=folder/source.name
    shutil.copy2(source,original)
    before=probe_media(source)
    stream=before['streams'][0]
    if stream['codec_name']=='h264' and stream.get('pix_fmt')=='yuv420p':
        shutil.copy2(source,target)
    else:
        codec,preset,crf=VIDEO_ENCODER
        subprocess.run([
            'ffmpeg','-y','-v','error','-i',str(source),'-map','0:v:0','-an',
            '-c:v',codec,'-preset',preset,'-crf',crf,'-pix_fmt','yuv420p',
            '-movflags','+faststart',str(target),
        ],check=True,capture_output=True,timeout=180)
    after=probe_media(target)
    output_stream=after['streams'][0]
    if (output_stream['codec_name']!='h264'
        or output_stream['nb_frames']!=stream['nb_frames']
        or output_stream['r_frame_rate']!=stream['r_frame_rate']
        or output_stream['width']!=stream['width'] or output_stream['height']!=stream['height']
        or abs(float(after['format']['duration'])-float(before['format']['duration']))>0.05):
        raise ValueError('浏览器编码改变了真实 AI 视频的画幅、帧数或时长')
    published_sha=hashlib.sha256(target.read_bytes()).hexdigest()
    proof={**record,'model_output_file':str(original),'published_file':str(target),
           'published_sha256':published_sha,'published_media':after}
    target.with_suffix('.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    return target,published_sha


def read_clip(shot, spec):
    clip=SOURCE_DIRECTORY/'clips'/(shot['id']+'.mp4')
    proof=clip.with_suffix('.json')
    if not clip.is_file() or not proof.is_file():
        return None
    record=json.loads(proof.read_text(encoding='utf-8'))
    if record.get('provider') not in ('ltx_local','ltx_public') or not str(record.get('model','')).startswith('Lightricks/'):
        raise ValueError('镜头缺少真实 AI 视频来源')
    if record.get('prompt')!=shot['prompt'] or abs(float(record.get('duration',0))-spec['seconds'])>0.05:
        raise ValueError('镜头提示词或时长与工作流规格不符')
    if record['provider']=='ltx_local' and (
        record.get('seed')!=shot.get('seed',spec['seed'])
        or record.get('conditions',[])!=shot.get('conditions',[])
    ):
        raise ValueError('镜头种子或中间画面约束与工作流规格不符')
    if record.get('sha256')!=hashlib.sha256(clip.read_bytes()).hexdigest():
        raise ValueError('视频文件与 AI 生成记录不一致')
    return clip,record


def generate_node(parameters, input_data):
    spec=json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    index=int(parameters.get('shot_index',parameters.get('shotIndex',0)))
    if not 1<=index<=len(spec['shots']):
        raise ValueError('AI 分镜序号超出范围')
    metadata=(input_data.get('_execution') or {}).get('metadata') or input_data.get('metadata') or {}
    execution=WorkflowExecution.objects.select_related('workflow').get(pk=metadata.get('execution_id'))
    shot=spec['shots'][index-1]
    saved=read_clip(shot,spec)
    reused=bool(saved)
    if not saved:
        if not cache.add(GPU_LOCK,str(execution.pk),timeout=spec['timeout_seconds']+300):
            raise ValueError('本机 AI 视频模型正在运行，请等待当前生成结束后继续该节点')
        process=None
        try:
            log_directory=Path(settings.MEDIA_ROOT)/'butterfly_ai'/str(execution.workflow.owner_id)/str(execution.pk)
            log_directory.mkdir(parents=True,exist_ok=True)
            with (log_directory/(shot['id']+'.log')).open('w',encoding='utf-8') as log:
                process=subprocess.Popen([sys.executable,str(SCRIPT_PATH),'--shots',str(index)],cwd=PROJECT_ROOT,stdout=log,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+spec['timeout_seconds']
                while process.poll() is None:
                    if time.monotonic()>deadline:
                        raise TimeoutError('本机 AI 视频生成超时，保留已完成片段')
                    execution.refresh_from_db(fields=['status'])
                    if execution.status!='running':
                        raise RuntimeError('工作流已停止，取消当前 AI 推理')
                    write_heartbeat(execution)
                    time.sleep(WAIT_SECONDS)
            if process.returncode:
                raise RuntimeError('本机 AI 推理失败，请查看该执行的生成日志')
            saved=read_clip(shot,spec)
            if not saved:
                raise RuntimeError('AI 模型未返回完整视频文件')
        finally:
            if process and process.poll() is None:
                process.kill();process.wait(timeout=30)
            if cache.get(GPU_LOCK)==str(execution.pk):
                cache.delete(GPU_LOCK)
    source,record=saved
    folder=Path(settings.MEDIA_ROOT)/'butterfly_ai'/str(execution.workflow.owner_id)/str(execution.pk)
    folder.mkdir(parents=True,exist_ok=True)
    target,published_sha=publish_clip(source,folder,record)
    video_url=build_public_media_url(target.relative_to(settings.MEDIA_ROOT).as_posix())
    return {'video_url':video_url,'duration':record['duration'],'provider':record['provider'],'model':record['model'],
            'sha256':published_sha,'source_sha256':record['sha256'],'cached_model_output':reused,'generation_method':'AI image-to-video diffusion',
            'caption':shot['caption'],'status':'completed'}
