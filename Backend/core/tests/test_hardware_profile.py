"""Tests for hardware profile service."""

from django.test import SimpleTestCase

from core.services.hardware_profile import (
    merge_hardware_profile,
    normalize_client_capabilities,
    recommend_yolo_training_config,
)


class HardwareProfileTests(SimpleTestCase):
    def test_normalize_client_capabilities(self):
        raw = {
            'navigator': {'hardwareConcurrency': 8, 'deviceMemory': 16},
            'screen': {'width': 1920, 'height': 1080},
        }
        out = normalize_client_capabilities(raw)
        self.assertEqual(out['cpu_cores'], 8)
        self.assertEqual(out['device_memory_gb'], 16)

    def test_merge_and_recommend_cpu(self):
        profile = merge_hardware_profile(
            {'navigator': {'hardwareConcurrency': 4, 'deviceMemory': 8}},
            {
                'cpu_count': 4,
                'memory_available_gb': 8,
                'gpu_available': False,
                'gpus': [],
            },
        )
        rec = recommend_yolo_training_config(profile)
        self.assertEqual(rec['device'], 'cpu')
        self.assertIn('epochs', rec)
        self.assertIn('pytorch', rec)
