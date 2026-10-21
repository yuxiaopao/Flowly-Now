"""Exercise video conditioning input and the actual quantized VACE network."""
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase


class VaceEmbroideryTests(SimpleTestCase):
    def test_unquantized_generation_rejects_insufficient_memory_before_loading_models(self):
        from scripts.generate_vace_embroidery_module import check_memory_budget, GIB
        spec = {'transformer_precision': 'bf16_offload',
                'memory_budget': {'available_ram_gib': 8, 'available_commit_gib': 16}}
        for state in ({'available_ram': 2*GIB, 'available_commit': 20*GIB},
                      {'available_ram': 10*GIB, 'available_commit': 5*GIB}):
            with patch('scripts.generate_vace_embroidery_module.memory_snapshot', return_value=state), self.assertRaises(MemoryError):
                check_memory_budget(spec)
        with patch('scripts.generate_vace_embroidery_module.memory_snapshot',
                   return_value={'available_ram': 10*GIB, 'available_commit': 20*GIB}):
            check_memory_budget(spec)
        with self.assertRaises(ValueError):
            check_memory_budget({'transformer_precision': 'bf16_offload'})
        check_memory_budget({'transformer_precision': 'nf4'})

    def test_unquantized_group_offload_preserves_vace_control_output(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for group offload')
        from diffusers import WanVACETransformer3DModel
        config = dict(num_attention_heads=2, attention_head_dim=16, in_channels=4,
                      out_channels=4, text_dim=64, freq_dim=16, ffn_dim=64, num_layers=1,
                      vace_layers=[0], vace_in_channels=12)
        model = WanVACETransformer3DModel(**config).to(device='cuda', dtype=torch.bfloat16).eval()
        arguments = dict(hidden_states=torch.randn(1, 4, 2, 4, 4, device='cuda', dtype=torch.bfloat16),
            timestep=torch.tensor([500.], device='cuda'),
            encoder_hidden_states=torch.randn(1, 8, 64, device='cuda', dtype=torch.bfloat16),
            control_hidden_states=torch.randn(1, 12, 2, 4, 4, device='cuda', dtype=torch.bfloat16),
            control_hidden_states_scale=torch.tensor([1.0], device='cuda'), return_dict=False)
        with torch.inference_mode():
            expected = model(**arguments)[0]
        model.to('cpu')
        model.enable_group_offload(onload_device=torch.device('cuda'), offload_device=torch.device('cpu'),
                                  offload_type='block_level', num_blocks_per_group=1, use_stream=False)
        with torch.inference_mode():
            actual = model(**arguments)[0]
        self.assertTrue(torch.isfinite(actual).all())
        self.assertTrue(torch.allclose(actual, expected, atol=0.01, rtol=0.01))
        self.assertEqual(model.blocks[0].attn1.to_q.weight.device.type, 'cpu')
        del model, actual, expected, arguments
        torch.cuda.empty_cache()

    def test_control_sampling_preserves_timing_and_rejects_out_of_bounds_requests(self):
        import cv2
        import numpy as np
        from scripts.generate_vace_embroidery_module import prepare_control
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = cv2.VideoWriter(str(root / 'control.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), 16, (64, 64))
            self.assertTrue(writer.isOpened())
            for index in range(33):
                writer.write(np.full((64, 64, 3), index*6, dtype=np.uint8))
            writer.release()
            shot = {'control_start_seconds': 0.25, 'control_crop': [0, 0, 64, 64]}
            spec = {'seconds': 17/16, 'fps': 16, 'width': 32, 'height': 32}
            frames, masks = prepare_control(root, shot, spec)
            self.assertEqual(len(frames), 17)
            values = [np.asarray(frame).mean() for frame in frames]
            self.assertTrue(all(after > before for before, after in zip(values, values[1:])))
            self.assertTrue(all(np.asarray(mask).min() == 255 for mask in masks))
            with self.assertRaisesRegex(ValueError, 'padding is forbidden'):
                prepare_control(root, {**shot, 'control_start_seconds': 1.5}, spec)
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                prepare_control(root, {**shot, 'control_crop': [10, 0, 64, 64]}, spec)

    def test_quantized_vace_forward_uses_video_control(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for actual VACE NF4 execution')
        from accelerate import init_empty_weights
        from diffusers import WanVACETransformer3DModel
        from safetensors.torch import save_file
        from scripts.generate_wan_embroidery_module import load_weights
        config = dict(num_attention_heads=2, attention_head_dim=16, in_channels=4,
                      out_channels=4, text_dim=64, freq_dim=16, ffn_dim=64, num_layers=1,
                      vace_layers=[0], vace_in_channels=12)
        original = WanVACETransformer3DModel(**config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tiny-vace.safetensors'
            save_file({key: value.to(torch.bfloat16) for key, value in original.state_dict().items()}, str(path))
            with init_empty_weights():
                model = WanVACETransformer3DModel(**config)
            model = load_weights(model, path)
            arguments = dict(hidden_states=torch.randn(1, 4, 2, 4, 4, device='cuda', dtype=torch.bfloat16),
                timestep=torch.tensor([500.], device='cuda'),
                encoder_hidden_states=torch.randn(1, 8, 64, device='cuda', dtype=torch.bfloat16),
                control_hidden_states_scale=torch.tensor([1.0], device='cuda'), return_dict=False)
            with torch.inference_mode():
                control = torch.randn(1, 12, 2, 4, 4, device='cuda', dtype=torch.bfloat16)
                active = model(control_hidden_states=control, **arguments)[0]
                zero = model(control_hidden_states=torch.zeros_like(control), **arguments)[0]
            self.assertEqual(tuple(active.shape), (1, 4, 2, 4, 4))
            self.assertTrue(torch.isfinite(active).all())
            self.assertGreater(float((active-zero).abs().max()), 0)
        del model, active, zero, control, arguments
        torch.cuda.empty_cache()
