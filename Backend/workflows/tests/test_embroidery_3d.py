"""Check native geometry and failure gates without marking partial renders complete."""
import copy
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from workflows.models import Workflow, WorkflowExecution
from workflows.services import embroidery_3d as service
from workflows.services.embroidery_geometry import build_stitches
from workflows.services.langchain_service import LangChainService
from scripts.create_embroidery_3d_workflow import make_graph


class Embroidery3DTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='embroidery_test')
        self.workflow = Workflow.objects.create(owner=self.owner, name='3d test')
        self.execution = WorkflowExecution.objects.create(workflow=self.workflow,version=1,status='running')
        self.context = {'_execution': {'metadata': {'execution_id': str(self.execution.pk)}}}

    def test_geometry_preserves_four_wings_and_real_satin_thread_travel(self):
        rows = build_stitches(service.load_spec())
        self.assertEqual({row['role'] for row in rows}, {'bone','feather'})
        quadrants = set()
        for row in rows:
            points = np.array(row['points'])
            self.assertTrue(np.isfinite(points).all())
            self.assertGreater(len(points), 2)
            if row['role']=='feather':
                center=points[:,:2].mean(axis=0)
                quadrants.add(tuple(np.sign(center)))
            if row['kind']=='satin':
                self.assertLess(points[:,2].min(),0)
                self.assertGreater(points[:,2].max(),0)
                steps = np.linalg.norm(np.diff(points,axis=0),axis=1)
                above = (points[:-1,2]>=0)|(points[1:,2]>=0)
                self.assertLess(steps[above].max(),.18)
        self.assertEqual(len(quadrants),4)

    def test_invalid_operation_and_preset_are_rejected(self):
        for params in ({'operation':'shell','preset':'x'},{'operation':'render','preset':'x'}):
            with self.assertRaises(ValueError):
                service.execute(params,self.context)

    def test_prepare_rejects_missing_external_or_wrong_sized_reference(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            source=Path(directory)/'tiny.png'
            Image.new('RGB',(16,16)).save(source)
            with patch.object(service,'local_path_from_public_url',return_value=source):
                with self.assertRaisesRegex(ValueError,'尺寸'):
                    service.prepare({'reference_url':'tiny.png'},self.context)
            with patch.object(service,'local_path_from_public_url',return_value=None):
                with self.assertRaisesRegex(ValueError,'已上传'):
                    service.prepare({'reference_url':'https://external.test/a.png'},self.context)

    def test_no_blender_process_success_without_expected_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            process=Mock(returncode=0)
            process.poll.return_value=0
            with patch.object(service,'blender_binary',return_value=Path('blender.exe')),patch.object(service.subprocess,'Popen',return_value=process):
                with self.assertRaisesRegex(RuntimeError,'没有生成三维工程'):
                    service.run_blender('build',self.execution,Path(directory))
                (Path(directory)/'scene.blend').write_bytes(b'test')
                with self.assertRaisesRegex(RuntimeError,'全部预期产物'):
                    service.run_blender('animate',self.execution,Path(directory))

    def test_failed_process_and_cancellation_do_not_finish(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            process=Mock(returncode=1)
            process.poll.return_value=1
            with patch.object(service,'blender_binary',return_value=Path('blender.exe')),patch.object(service.subprocess,'Popen',return_value=process):
                with self.assertRaisesRegex(RuntimeError,'Blender'):
                    service.run_blender('build',self.execution,Path(directory))
            self.execution.status='cancelled';self.execution.save(update_fields=['status'])
            process=Mock(returncode=None);process.poll.return_value=None
            with patch.object(service,'blender_binary',return_value=Path('blender.exe')),patch.object(service.subprocess,'Popen',return_value=process),patch.object(service.time,'sleep'):
                with self.assertRaisesRegex(RuntimeError,'停止'):
                    service.run_blender('render',self.execution,Path(directory))
                process.terminate.assert_called_once()

    def test_missing_or_misnumbered_frames_reject_video_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'frames').mkdir()
            spec=copy.deepcopy(service.load_spec());spec.update(duration=1,fps=2)
            (root/'frames/00001.png').touch();(root/'frames/00003.png').touch()
            with patch.object(service,'load_spec',return_value=spec),patch.object(service.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'渲染不完整'):
                    service.finish(self.execution,root)
                run.assert_not_called()

    def test_tool_json_parameters_round_trip_and_errors(self):
        tool=LangChainService()
        result=tool.run_tool_node({'tool':'calculator','parameters':'{"expression":"2+3"}'},{})
        self.assertTrue(result['success'],result)
        for value in ('[1,2]','{bad',None):
            result=tool.run_tool_node({'tool':'calculator','parameters':value},{})
            self.assertFalse(result['success'])
            self.assertEqual(result['error_type'],'tool_error')

    def test_native_graph_has_all_six_real_operations(self):
        nodes,edges=make_graph('http://127.0.0.1:8000/media/source.png')
        self.assertEqual(len(nodes),8);self.assertEqual(len(edges),7)
        self.assertEqual([n['config']['parameters']['operation'] for n in nodes[1:-1]],['prepare','build','animate','previews','render','finish'])
        self.assertTrue(all(n['error_handling']=='stop' for n in nodes[1:-1]))
