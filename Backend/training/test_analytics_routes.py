from pathlib import Path
import tempfile
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import resolve
from rest_framework.test import APIRequestFactory

from training.views import YoloTrainingRunViewSet, _resolve_yolo_run_dir


class YoloAnalyticsRoutesTests(SimpleTestCase):
    def test_analytics_is_on_yolo_route_and_requires_authentication(self):
        match = resolve('/api/v1/training/yolo-runs/00000000-0000-4000-8000-000000000001/analytics/')
        self.assertIs(match.func.cls, YoloTrainingRunViewSet)
        response = match.func(APIRequestFactory().get('/'), **match.kwargs)
        self.assertEqual(response.status_code, 401)

    def test_running_directory_is_found_before_final_results_png_exists(self):
        with tempfile.TemporaryDirectory(prefix='flowly-live-plots-') as folder:
            run = Path(folder) / 'train'
            run.mkdir()
            (run / 'results.csv').write_text('epoch,train/box_loss\n1,0.2\n', encoding='utf-8')
            job = SimpleNamespace(best_weight_path='', model_path='', config={'output_dir': folder}, name='actual')
            self.assertEqual(_resolve_yolo_run_dir(job), run)
