"""Check provenance gates and full 60-second finishing with test-only provider mocks."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from scripts.create_butterfly_ai_video_workflow import make_graph
from workflows.models import APICredential, Edge, Node, Workflow, WorkflowExecution
from workflows.services.langchain_service import LangChainService
from workflows.services.media_service import local_path_from_public_url
from workflows.services.partial_retry import prepare_continue
from workflows.services.video_postprocess import probe_media
from workflows.services.workflow_executor import WorkflowExecutor


class ButterflyAIPipelineTests(TestCase):
    def test_each_image_model_receives_its_source_detail(self):
        details={'motif':'https://media.test/motif-detail.png','garment':'https://media.test/garment-detail.png'}
        nodes,_=make_graph('https://media.test/board.png','test-credential',reference_details=details)
        images=[row for row in nodes if row['node_type']=='image_generation']
        self.assertEqual(images[0]['config']['referenceImages'],[details['motif']])
        self.assertEqual(images[1]['config']['referenceImages'][0],details['garment'])
        self.assertIn(images[0]['id'],images[1]['config']['referenceImages'][1])

    def test_provider_failure_stops_at_first_required_video(self):
        owner=get_user_model().objects.create_user(username='ai_stop_test');workflow=Workflow.objects.create(owner=owner,name='TEST ONLY required AI video')
        nodes,edges=make_graph('https://media.test/source.png','test-credential')
        for row in nodes:Node.objects.create(workflow=workflow,**row)
        for row in edges:Edge.objects.create(workflow=workflow,source_node_id=row['source'],target_node_id=row['target'])
        execution=WorkflowExecution.objects.create(workflow=workflow,version=1,triggered_by=owner,input_data={})
        image={'success':True,'output':{'images':[{'url':'https://media.test/ref.png'}],'provider':'agnes'}}
        with patch.object(LangChainService,'run_image_generation_node',return_value=image),patch.object(LangChainService,'run_video_generation_node',return_value={'success':False,'error':'provider quota'}) as video:
            WorkflowExecutor(workflow,execution,parallel_enabled=False).execute()
        execution.refresh_from_db()
        self.assertEqual(execution.status,'failed')
        self.assertEqual(video.call_count,1)
        self.assertFalse(execution.node_executions.filter(node__node_type='merge').exists())

    def test_selected_credential_is_used_and_cannot_cross_user_boundary(self):
        User=get_user_model();owner=User.objects.create_user(username='ai_owner');other=User.objects.create_user(username='ai_other')
        credential=APICredential(owner=owner,name='specific',service_type='agnes',credential_type='api_key',is_active=True)
        credential.set_encrypted_data('test-key-not-a-live-provider-secret');credential.save()
        self.assertEqual(LangChainService(user_id=owner.pk)._agnes_credential(credential.pk)[0],'test-key-not-a-live-provider-secret')
        with self.assertRaisesRegex(Exception,'不属于当前用户'):
            LangChainService(user_id=other.pk)._agnes_credential(credential.pk)

    def test_real_graph_never_replaces_missing_ai_clip_with_local_animation(self):
        nodes,edges=make_graph('https://media.test/source.png','test-credential')
        videos=[node for node in nodes if node['node_type']=='video_generation']
        self.assertEqual(len(videos),6)
        self.assertEqual(len(nodes),23)
        self.assertEqual(len(edges),22)
        self.assertTrue(all(node['config']['mode']=='reference' for node in videos))
        self.assertTrue(all(node['config']['submit_interval_seconds']>=65 for node in videos))
        gate=next(node for node in nodes if node['name']=='校验六段真实AI视频·禁止本地替代')
        valid={node['id']:{'video_url':f'https://media.test/{i}.mp4','provider':'agnes','model':'agnes-video-2.5','duration':10} for i,node in enumerate(videos)}
        service=LangChainService()
        self.assertTrue(service.run_code_node(gate['config'],{'node_outputs':valid})['success'])
        for bad in ({},{**valid,videos[0]['id']:{'video_url':'https://media.test/x.mp4','provider':'local_render','duration':10}}, {**valid,videos[0]['id']:{**valid[videos[0]['id']],'duration':5}}):
            self.assertFalse(service.run_code_node(gate['config'],{'node_outputs':bad})['success'])

    def test_six_distinct_model_clips_finish_at_sixty_seconds(self):
        if not shutil.which('ffmpeg'):self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=Path(directory)):
            root=Path(directory);clips=[]
            for index,color in enumerate(('navy','gray','white','brown','silver','blue')):
                clip=root/f'clip{index}.mp4';subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',f'color=c={color}:s=320x180:r=24','-t','10','-c:v','libx264',str(clip)],check=True,capture_output=True,timeout=30);clips.append(clip)
            owner=get_user_model().objects.create_user(username='ai_video_test');workflow=Workflow.objects.create(owner=owner,name='TEST ONLY AI video finishing')
            nodes,edges=make_graph('https://media.test/source.png','test-credential')
            for row in nodes:Node.objects.create(workflow=workflow,**row)
            for row in edges:Edge.objects.create(workflow=workflow,source_node_id=row['source'],target_node_id=row['target'])
            execution=WorkflowExecution.objects.create(workflow=workflow,version=1,triggered_by=owner,input_data={})
            images={'success':True,'output':{'images':[{'url':'https://media.test/reference.png'}],'provider':'agnes','model':'agnes-image-2.5-flash'}}
            results=[{'success':True,'output':{'video_url':str(clip),'provider':'agnes','model':'agnes-video-2.5','duration':10,'generation_mode':'reference'}} for clip in clips]
            with patch.object(LangChainService,'run_image_generation_node',return_value=images),patch.object(LangChainService,'run_video_generation_node',side_effect=[results[0],{'success':False,'error':'TEST ONLY provider queue full'}]):
                WorkflowExecutor(workflow,execution,parallel_enabled=False).execute()
            execution.refresh_from_db();self.assertEqual(execution.status,'failed')
            first_output=execution.node_executions.get(node_id=next(row['id'] for row in nodes if row['node_type']=='video_generation')).output_data
            prepare_continue(execution)
            with patch.object(LangChainService,'run_image_generation_node') as image_retry,patch.object(LangChainService,'run_video_generation_node',side_effect=results[1:]) as video_retry:
                WorkflowExecutor(workflow,execution,parallel_enabled=False).execute(resume=True)
            image_retry.assert_not_called();self.assertEqual(video_retry.call_count,5)
            self.assertEqual(execution.node_executions.get(node_id=next(row['id'] for row in nodes if row['node_type']=='video_generation')).output_data,first_output)
            execution.refresh_from_db();self.assertEqual(execution.status,'completed',execution.error_message)
            final=local_path_from_public_url(execution.output_data['variables']['final_video']);self.assertTrue(final.is_file())
            self.assertAlmostEqual(probe_media(final)['duration'],60,places=1)
            self.assertEqual(execution.node_executions.filter(status='completed').count(),23)
