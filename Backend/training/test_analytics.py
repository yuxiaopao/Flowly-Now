import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase

from training.analytics import build_run_analytics


class YoloAnalyticsTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='flowly-analytics-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.job = SimpleNamespace(pk='run-id', name='actual run', config={}, metrics_history=[],
                                   class_names=['a', 'b'], model_type='classification', status='completed',
                                   yolo_version='v26', model_variant='m', current_epoch=0,
                                   total_epochs=2, best_epoch=2, workflow_id='workflow', node_id='node',
                                   dataset_id=None, dataset_path='dataset')

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data), encoding='utf-8')

    def test_csv_wins_over_stale_synced_history_and_partial_rows(self):
        (self.root / 'results.csv').write_text(
            'epoch,time,metrics/accuracy_top1,lr/pg0\n1,2,0,0.1\n2,4,0.9,0.05\n2,4,\n3,NaN,0.9,0.1\n', encoding='utf-8')
        self.job.metrics_history = [{'epoch': 1, 'val_acc': 1}]
        data = build_run_analytics(self.job, self.root)
        self.assertEqual(len(data['history']), 2)
        self.assertEqual(data['history'][0]['metrics/accuracy_top1'], 0)
        self.assertEqual(data['history'][-1]['metrics/accuracy_top1'], 0.9)
        self.assertEqual(data['history_source'], 'results.csv')

    def test_synced_history_retains_zero_and_nested_detection_fields(self):
        self.job.model_type = 'detection'
        self.job.metrics_history = [{'epoch': 1, 'loss': {'box': 0, 'cls': 0.3}, 'metrics': {'mAP50': 0, 'precision': 0.2}}]
        data = build_run_analytics(self.job, None)
        self.assertEqual(data['history'][0]['train/box_loss'], 0)
        self.assertEqual(data['history'][0]['metrics/mAP50(B)'], 0)
        self.assertEqual(data['task'], 'detect')

    def test_legacy_columns_and_zero_based_epochs_are_normalized(self):
        self.job.model_type = 'detection'
        (self.root / 'results.csv').write_text(
            'epoch,metrics/mAP_0.5,metrics/mAP_0.5:0.95,x/lr0\n0,0.7,0.5,0.01\n1,0.8,0.6,0.005\n', encoding='utf-8')
        data = build_run_analytics(self.job, self.root)
        self.assertEqual([row['epoch'] for row in data['history']], [1, 2])
        self.assertEqual(data['history'][0]['metrics/mAP50-95(B)'], 0.5)
        self.assertEqual(data['history'][1]['lr/pg0'], 0.005)

    def test_task_inference_handles_mask_pose_and_obb(self):
        for field, task in [('metrics/mAP50(M)', 'segment'), ('metrics/mAP50(P)', 'pose'), ('train/angle_loss', 'obb')]:
            with self.subTest(task=task):
                (self.root / 'results.csv').write_text(f'epoch,{field}\n1,0.5\n', encoding='utf-8')
                self.assertEqual(build_run_analytics(self.job, self.root)['task'], task)

    def test_reports_preserve_test_and_validation_provenance(self):
        self.write('test-report.json', {'classes': ['b', 'a'], 'images': 10, 'confusion_matrix': [[3, 1], [2, 4]], 'top1': 0.7})
        data = build_run_analytics(self.job, self.root)
        self.assertEqual([item['key'] for item in data['classes']], ['b', 'a'])
        self.assertEqual(data['reports']['test']['confusion_matrix'][0], [3, 1])
        self.assertIsNone(data['reports']['validation'])

    def test_corrupt_and_invalid_matrices_are_explicitly_unavailable(self):
        (self.root / 'val-report.json').write_text('{', encoding='utf-8')
        self.write('test-report.json', {'classes': ['a', 'b'], 'confusion_matrix': [[1], [2]]})
        data = build_run_analytics(self.job, self.root)
        self.assertIsNone(data['reports']['validation'])
        self.assertIsNone(data['reports']['test']['confusion_matrix'])
        self.assertEqual(len(data['warnings']), 2)

    def test_empty_run_has_no_invented_metrics_or_matrix(self):
        data = build_run_analytics(self.job, self.root)
        self.assertEqual(data['history'], [])
        self.assertEqual(data['reports'], {'validation': None, 'test': None})

    def test_symlinked_report_cannot_escape_run_directory(self):
        with tempfile.TemporaryDirectory(prefix='flowly-outside-') as other:
            source = Path(other) / 'report.json'
            source.write_text('{}', encoding='utf-8')
            try:
                (self.root / 'test-report.json').symlink_to(source)
            except OSError:
                self.skipTest('This Windows account cannot create symbolic links')
            data = build_run_analytics(self.job, self.root)
            self.assertIsNone(data['reports']['test'])
            self.assertTrue(data['warnings'])
