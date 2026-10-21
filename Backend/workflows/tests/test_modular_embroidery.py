"""Exercise module provenance, rendering, native merge and failure-point resume."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from scripts.create_modular_embroidery_workflow import ENCODING, MODEL_CONFIG, MOTION_TEMPLATE, make_graph
from workflows.models import Edge, Node, Workflow, WorkflowExecution
from workflows.services import embroidery_module_job as job
from workflows.services.media_service import local_path_from_public_url
from workflows.services.partial_retry import prepare_continue
from workflows.services.video_postprocess import concat_videos, probe_media, VideoPostprocessError
from workflows.services.workflow_executor import WorkflowExecutor


def create_clip(path, seconds, color='navy'):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                    f'color=c={color}:s=64x64:r=30', '-t', str(seconds), '-an',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-video_track_timescale',
                    str(ENCODING['timescale']), str(path)], check=True, capture_output=True, timeout=30)


class ModuleSourceTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = patch.object(job, 'ASSET_ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        frames = self.root / 'source/keyframes'
        frames.mkdir(parents=True)
        (frames / 'start.png').write_bytes(b'test-start')
        (frames / 'end.png').write_bytes(b'test-end')
        self.module = {'id': 'test', 'source_directory': 'source', 'shot': {
            'id': 'test', 'prompt': 'test only', 'seed': 1, 'image': 'start.png',
            'end_image': 'end.png', 'conditions': []},
            'model_spec': {**MODEL_CONFIG, 'width': 64, 'height': 64, 'seconds': 1}}

    def test_prompt_seed_and_frame_content_invalidate_generation_cache(self):
        original, _ = job.build_request(self.module, {})
        for changed in ({'prompt': 'new test prompt'}, {'seed': 2}):
            updated, _ = job.build_request(self.module, changed)
            self.assertNotEqual(original['fingerprint'], updated['fingerprint'])
        (self.root / 'source/keyframes/end.png').write_bytes(b'new frame')
        updated, _ = job.build_request(self.module, {})
        self.assertNotEqual(original['fingerprint'], updated['fingerprint'])
        changed = copy.deepcopy(self.module)
        changed['model_spec'].update(guidance_scale=2.5, negative_prompt='hands')
        guided, _ = job.build_request(changed, {})
        self.assertNotEqual(updated['fingerprint'], guided['fingerprint'])

    def test_invalid_inputs_and_missing_frames_are_rejected(self):
        for changed in ({'prompt': ''}, {'seed': -1}, {'seed': True}, {'seed': '2'}):
            with self.assertRaises(ValueError):
                job.build_request(self.module, changed)
        with self.assertRaises(ValueError):
            job.asset_path('../outside')
        for name in ('../../outside.png', 'missing.png'):
            broken = copy.deepcopy(self.module)
            broken['shot']['image'] = name
            with self.assertRaises(ValueError):
                job.build_request(broken, {})

    def test_first_frame_only_generation_has_a_distinct_cache_and_requires_no_end_asset(self):
        original, _ = job.build_request(self.module, {})
        self.module['shot']['end_image'] = None
        (self.root / 'source/keyframes/end.png').unlink()
        request, _ = job.build_request(self.module, {})
        self.assertEqual(set(request['keyframe_hashes']), {'start.png'})
        self.assertNotEqual(request['fingerprint'], original['fingerprint'])
        del self.module['shot']['end_image']
        request, _ = job.build_request(self.module, {})
        self.assertEqual(set(request['keyframe_hashes']), {'start.png'})
        for invalid in ('', False, 12):
            self.module['shot']['end_image'] = invalid
            with self.assertRaisesRegex(ValueError, '结束关键帧'):
                job.build_request(self.module, {})

    def test_wan_mode_rejects_unsupported_end_conditions_and_checks_model_origin(self):
        self.module['model_spec']['model_family'] = 'wan'
        with self.assertRaisesRegex(ValueError, '仅支持'):
            job.build_request(self.module, {})
        self.module['shot']['end_image'] = None
        request, directory = job.build_request(self.module, {})
        clip = directory / 'clips/test.mp4'
        create_clip(clip, 1)
        record = {'provider': 'wan_local', 'model': 'Wan-AI/test', 'prompt': 'test only',
                  'seed': 1, 'last_frame': None, 'sha256': job.digest(clip)}
        clip.with_suffix('.json').write_text(json.dumps(record), encoding='utf-8')
        self.assertEqual(job.read_source(directory, request)[0], clip)
        request['spec']['model_family'] = 'ltx'
        with self.assertRaisesRegex(ValueError, '真实 AI'):
            job.read_source(directory, request)
        self.module['model_spec']['model_family'] = 'unrecognized'
        with self.assertRaisesRegex(ValueError, '不支持'):
            job.build_request(self.module, {})

    def test_experimental_wan_keyframes_require_valid_interior_indices_and_new_cache(self):
        self.module['model_spec'].update(model_family='wan', condition_mode='keyframes', fps=24, seconds=65/24)
        self.module['shot']['conditions'] = [{'image': 'start.png', 'frame_index': 32}]
        request, _ = job.build_request(self.module, {})
        self.assertEqual(set(request['keyframe_hashes']), {'start.png', 'end.png'})
        self.module['shot']['conditions'][0]['frame_index'] = 28
        changed, _ = job.build_request(self.module, {})
        self.assertNotEqual(changed['fingerprint'], request['fingerprint'])
        for index in (0, 3, 64, 65, True):
            self.module['shot']['conditions'][0]['frame_index'] = index
            with self.assertRaisesRegex(ValueError, '中间关键帧'):
                job.build_request(self.module, {})
        self.module['shot']['conditions'] = [{'image': 'start.png', 'frame_index': 32}] * 2
        with self.assertRaisesRegex(ValueError, '中间关键帧'):
            job.build_request(self.module, {})

    def test_vace_control_video_is_hashed_and_cannot_escape_asset_root(self):
        self.module['model_spec']['model_family'] = 'vace'
        self.module['shot'].update(end_image=None, control_video='control.mp4')
        source = self.root / 'control.mp4'
        source.write_bytes(b'test-only-control-one')
        first, _ = job.build_request(self.module, {})
        source.write_bytes(b'test-only-control-two')
        second, _ = job.build_request(self.module, {})
        self.assertNotEqual(first['control_video_hash'], second['control_video_hash'])
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])
        for path in ('../control.mp4', 'missing.mp4'):
            self.module['shot']['control_video'] = path
            with self.assertRaises(ValueError):
                job.build_request(self.module, {})

    def test_source_requires_proof_exact_request_and_unchanged_bytes(self):
        request, directory = job.build_request(self.module, {})
        clip = directory / 'clips/test.mp4'
        self.assertIsNone(job.read_source(directory, request))
        create_clip(clip, 1)
        record = {'provider': 'ltx_local', 'model': 'Lightricks/test-fixture',
                  'prompt': 'test only', 'seed': 1, 'conditions': [], 'last_frame': 'end.png',
                  'sha256': job.digest(clip), 'request_fingerprint': request['fingerprint']}
        def save():
            clip.with_suffix('.json').write_text(json.dumps(record), encoding='utf-8')
        save()
        self.assertEqual(job.read_source(directory, request, require_fingerprint=True)[0], clip)
        first_only = copy.deepcopy(request)
        first_only['shot']['end_image'] = None
        self.assertIsNone(job.read_source(directory, first_only))
        record['last_frame'] = None
        save()
        self.assertEqual(job.read_source(directory, first_only)[0], clip)
        record['last_frame'] = 'end.png'
        record['seed'] = 2
        save()
        self.assertIsNone(job.read_source(directory, request))
        record['seed'] = 1
        record['request_fingerprint'] = 'old-request'
        save()
        self.assertIsNone(job.read_source(directory, request, require_fingerprint=True))
        record['sha256'] = 'incorrect'
        save()
        with self.assertRaisesRegex(ValueError, '校验值'):
            job.read_source(directory, request)
        record['provider'] = 'unverified'
        save()
        with self.assertRaisesRegex(ValueError, '真实 AI'):
            job.read_source(directory, request)

    def test_render_checks_frame_range_and_output_duration(self):
        source, target = self.root / 'in.mp4', self.root / 'out.mp4'
        create_clip(source, 1)
        encoding = {**ENCODING, 'width': 64, 'height': 64}
        edit = {**MOTION_TEMPLATE, 'seconds': 0.5, 'end_frame': 15}
        self.assertEqual(job.render_clip(source, target, edit, encoding)['streams'][0]['nb_frames'], '15')
        with self.assertRaisesRegex(ValueError, '范围'):
            job.render_clip(source, target, {**edit, 'end_frame': 31}, encoding)
        with self.assertRaisesRegex(ValueError, '不完整'):
            job.render_clip(source, target, {**edit, 'seconds': 1}, encoding)

    def test_stationary_camera_clip_is_scaled_without_padding_or_retiming(self):
        source, target = self.root / 'native.mp4', self.root / 'delivery.mp4'
        create_clip(source, 1)
        encoding = {**ENCODING, 'width': 128, 'height': 96}
        edit = {**MOTION_TEMPLATE, 'seconds': 0.5, 'end_frame': 15}
        media = job.render_clip(source, target, edit, encoding)
        self.assertEqual(media['streams'][0]['width'], 128)
        self.assertEqual(media['streams'][0]['height'], 96)
        self.assertEqual(media['streams'][0]['nb_frames'], '15')

    def test_generation_cancellation_kills_child_and_releases_its_lock(self):
        request, directory = job.build_request(self.module, {})
        execution = Mock(pk='test-execution', status='cancelled')
        process = Mock()
        process.poll.return_value = None
        lock_value = str(execution.pk) + ':' + request['fingerprint']
        with patch.object(job.cache, 'add', return_value=True), patch.object(job.cache, 'get', return_value=lock_value), \
                patch.object(job.cache, 'delete') as release, patch.object(job.subprocess, 'Popen', return_value=process), \
                patch.object(job, 'stop_process') as stop:
            with self.assertRaisesRegex(RuntimeError, '取消'):
                job.run_generation(execution, request, directory, self.root / 'generated')
            stop.assert_called_once_with(process)
            release.assert_called_once_with(job.GPU_LOCK)

    def test_timeout_stops_generation_and_does_not_remove_another_lease(self):
        request, directory = job.build_request(self.module, {})
        execution = Mock(pk='test-execution', status='running')
        process = Mock()
        process.poll.return_value = None
        with patch.object(job.cache, 'add', return_value=True), patch.object(job.cache, 'get', return_value='different-owner'), \
                patch.object(job.cache, 'delete') as release, patch.object(job.subprocess, 'Popen', return_value=process), \
                patch.object(job, 'stop_process') as stop, patch.object(job.time, 'monotonic', side_effect=[0, request['spec']['timeout_seconds'] + 1]):
            with self.assertRaises(TimeoutError):
                job.run_generation(execution, request, directory, self.root / 'timeout')
            stop.assert_called_once_with(process)
            release.assert_not_called()

    def test_windows_cancellation_terminates_the_interpreter_tree(self):
        process = Mock(pid=12345)
        with patch.object(job.os, 'name', 'nt'), patch.object(job.subprocess, 'run') as run:
            job.stop_process(process)
            self.assertEqual(run.call_args.args[0], ['taskkill', '/PID', '12345', '/T', '/F'])
            process.wait.assert_called_once()

    def test_busy_gpu_does_not_start_process(self):
        request, directory = job.build_request(self.module, {})
        with patch.object(job.cache, 'add', return_value=False), patch.object(job.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError, '使用中'):
                job.run_generation(Mock(pk='other'), request, directory, self.root / 'generated')
            spawn.assert_not_called()

    def test_preserve_merge_keeps_unequal_durations_and_rejects_wrong_total(self):
        paths = [self.root / 'one.mp4', self.root / 'two.mp4']
        create_clip(paths[0], 0.5)
        create_clip(paths[1], 1, 'white')
        with override_settings(MEDIA_ROOT=self.root):
            result = concat_videos(paths, target_duration_sec=1.5, fill_mode='preserve')
            self.assertEqual(probe_media(result)['duration'], 1.5)
            self.assertEqual(probe_media(result)['streams'][0]['nb_frames'], '45')
            with self.assertRaisesRegex(VideoPostprocessError, '总时长'):
                concat_videos(paths, target_duration_sec=2, fill_mode='preserve')


class ModularWorkflowTests(TestCase):
    def test_failure_resume_preserves_completed_modules_and_builds_real_video(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            root = Path(directory)
            durations = [0.5, 1, 0.5]
            modules = [{'id': f'fixture-{i}', 'caption': f'test {i}', 'edit': {'seconds': seconds},
                        'shot': {'prompt': 'test fixture only', 'seed': i}}
                       for i, seconds in enumerate(durations)]
            spec = {'seconds': sum(durations), 'modules': modules, 'disclosure': 'TEST FIXTURES ONLY'}
            owner = get_user_model().objects.create_user(username='modular-test')
            workflow = Workflow.objects.create(owner=owner, name='test modular graph', config={'embroidery_spec': spec})
            nodes, edges = make_graph(spec)
            for node in nodes:
                Node.objects.create(workflow=workflow, **node)
            for edge in edges:
                Edge.objects.create(workflow=workflow, source_node_id=edge['source'], target_node_id=edge['target'])
            paths = []
            for i, seconds in enumerate(durations):
                path = root / f'fixture-{i}.mp4'
                create_clip(path, seconds, ('navy', 'gray', 'white')[i])
                paths.append(path)
            calls, failed_once = [], set()
            def module_fixture(parameters, context):
                index = int(parameters['module_id'].split('-')[-1])
                calls.append(index)
                if index == 1 and index not in failed_once:
                    failed_once.add(index)
                    raise RuntimeError('deliberate test module failure')
                return {'video_url': str(paths[index]), 'duration': durations[index],
                        'provider': 'ltx_local', 'model': 'Lightricks/test-fixture', 'source_sha256': job.digest(paths[index])}
            execution = WorkflowExecution.objects.create(workflow=workflow, version=workflow.version, triggered_by=owner, trigger_type='api')
            with patch.object(job, 'generate_node', side_effect=module_fixture):
                WorkflowExecutor(workflow, execution, parallel_enabled=False).execute()
                execution.refresh_from_db()
                self.assertEqual(execution.status, 'failed')
                self.assertEqual(calls, [0, 1])
                prepare_continue(execution, mode='auto')
                WorkflowExecutor(workflow, execution, parallel_enabled=False).execute(resume=True)
            execution.refresh_from_db()
            self.assertEqual(execution.status, 'completed', execution.error_message)
            self.assertEqual(calls, [0, 1, 1, 2])
            final = local_path_from_public_url(execution.output_data['variables']['final_video'])
            self.assertEqual(probe_media(final)['duration'], sum(durations))
            self.assertEqual(execution.node_executions.filter(status='completed').count(), len(nodes))


class GuidanceTests(SimpleTestCase):
    def test_negative_and_positive_branches_run_separately_without_changing_batch_order(self):
        import torch
        from scripts.generate_embroidery_module import sequential_guidance
        calls = []
        def forward(**kwargs):
            calls.append(kwargs)
            return (kwargs['hidden_states'] + kwargs['encoder_hidden_states'],)
        hidden = torch.tensor([[1., 2.], [3., 4.]])
        prompt = torch.tensor([[10., 20.], [30., 40.]])
        with patch.object(torch.cuda, 'empty_cache'):
            result = sequential_guidance(forward)(hidden_states=hidden, encoder_hidden_states=prompt,
                timestep=torch.tensor([[2.], [2.]]), video_coords=torch.ones(2, 3, 4),
                attention_kwargs={'test': True}, return_dict=False)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call['hidden_states'].shape[0] == 1 for call in calls))
        self.assertTrue(torch.equal(result[0], hidden + prompt))
        self.assertTrue(all(call['video_coords'].shape == (1, 3, 4) for call in calls))
        self.assertEqual(calls[0]['attention_kwargs'], {'test': True})

    def test_single_batch_keeps_native_forward(self):
        import torch
        from scripts.generate_embroidery_module import sequential_guidance
        forward = Mock(return_value=('result',))
        inputs = {'hidden_states': torch.ones(1, 2), 'return_dict': False}
        self.assertEqual(sequential_guidance(forward)(**inputs), ('result',))
        forward.assert_called_once_with(**inputs)
