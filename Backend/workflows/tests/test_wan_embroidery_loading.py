"""Check the low-memory Wan loader against actual scaled FP8 tensors."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase


class WanLoadingTests(SimpleTestCase):
    def test_keyframes_constrain_only_requested_times_and_decode_restores_scaling(self):
        import torch
        from types import SimpleNamespace
        from PIL import Image
        from diffusers.video_processor import VideoProcessor
        from scripts.generate_wan_embroidery_module import configure_keyframes, decode_latents
        config = SimpleNamespace(latents_mean=[0.1, 0.2, 0.3], latents_std=[0.5, 1, 2])
        class TinyVAE:
            dtype = torch.float32
            def __init__(self):
                self.config = config
            def encode(self, pixels):
                value = torch.nn.functional.adaptive_avg_pool3d(pixels, (1, 8, 8))
                return SimpleNamespace(latent_dist=SimpleNamespace(mode=lambda: value))
            def decode(self, value, return_dict=False):
                self.decoded = value.clone()
                return (value,)
        def prepare():
            latents = torch.randn(1, 3, 17, 8, 8)
            first = torch.full((1, 3, 1, 8, 8), 0.25)
            mask = torch.ones(1, 1, 17, 8, 8)
            mask[:, :, 0] = 0
            return latents, first, mask
        pipe = SimpleNamespace(vae=TinyVAE(), video_processor=VideoProcessor(vae_scale_factor=8),
                               vae_scale_factor_temporal=4, prepare_latents=prepare)
        shot = {'end_image': 'end.png', 'conditions': [{'image': 'mid.png', 'frame_index': 32}]}
        spec = {'seconds': 65/24, 'fps': 24, 'height': 64, 'width': 64}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'keyframes').mkdir()
            Image.new('RGB', (64, 64), 'white').save(root / 'keyframes/mid.png')
            Image.new('RGB', (64, 64), 'black').save(root / 'keyframes/end.png')
            configure_keyframes(pipe, shot, spec, root)
            latents, condition, mask = pipe.prepare_latents()
            self.assertEqual(tuple(condition.shape), tuple(latents.shape))
            self.assertEqual(torch.where(mask[0, 0, :, 0, 0] == 0)[0].tolist(), [0, 8, 16])
            self.assertTrue(torch.equal(condition[:, :, 0], torch.full_like(condition[:, :, 0], 0.25)))
            mean = torch.tensor(config.latents_mean).view(1, 3, 1, 1)
            std = torch.tensor(config.latents_std).view(1, 3, 1, 1)
            self.assertTrue(torch.allclose(condition[:, :, 8] * std + mean, torch.ones(1, 3, 8, 8)))
            self.assertTrue(torch.allclose(condition[:, :, 16] * std + mean, -torch.ones(1, 3, 8, 8)))
            decode_latents(pipe, condition)
            self.assertTrue(torch.allclose(pipe.vae.decoded[:, :, 8], torch.ones(1, 3, 8, 8)))
            for index in (0, 3, 65, True):
                with self.assertRaises(ValueError):
                    configure_keyframes(pipe, {'conditions': [{'image': 'mid.png', 'frame_index': index}]}, spec, root)

    def test_only_vae_moves_between_cpu_and_gpu_while_quantized_transformer_stays_resident(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for staged VAE execution')
        from types import SimpleNamespace
        from diffusers.utils.accelerate_utils import apply_forward_hook
        from scripts.generate_wan_embroidery_module import configure_vae_offload
        import bitsandbytes as bnb
        class TinyVAE(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.ones(1, dtype=torch.bfloat16))
            @apply_forward_hook
            def encode(self, value):
                return value * self.weight
            @apply_forward_hook
            def decode(self, value):
                return value + self.weight
        pipe = SimpleNamespace(vae=TinyVAE(), transformer=bnb.nn.Linear4bit(64, 64,
            compute_dtype=torch.bfloat16, quant_type='nf4').to('cuda'))
        pointer = pipe.transformer.weight.data_ptr()
        configure_vae_offload(pipe)
        encoded = pipe.vae.encode(torch.ones(1, device='cuda', dtype=torch.bfloat16))
        self.assertEqual(encoded.device.type, 'cuda')
        self.assertEqual(pipe.vae.weight.device.type, 'cpu')
        with torch.inference_mode():
            output = pipe.transformer(torch.ones(1, 64, device='cuda', dtype=torch.bfloat16))
            decoded = pipe.vae.decode(encoded)
        self.assertTrue(torch.isfinite(output).all())
        self.assertEqual(pipe.transformer.weight.data_ptr(), pointer)
        self.assertEqual(pipe.vae.weight.device.type, 'cuda')
        self.assertEqual(float(decoded[0]), 2.0)
        del pipe, encoded, decoded, output
        torch.cuda.empty_cache()

    def test_prompt_encoder_masks_padding_in_inference_mode_and_reuses_verified_cache(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for the local prompt encoder')
        from safetensors.torch import save_file
        from transformers import UMT5Config, UMT5EncoderModel, BatchEncoding
        from scripts import generate_wan_embroidery_module as wan
        config = UMT5Config(d_model=64, d_kv=16, d_ff=128, num_layers=1,
                           num_heads=4, vocab_size=128, feed_forward_proj='gated-gelu', tie_word_embeddings=False)
        encoder = UMT5EncoderModel(config)
        encoder.set_input_embeddings(encoder.shared)
        def tokenize(*args, **kwargs):
            return BatchEncoding({'input_ids': torch.tensor([[1, 2, 3, 4, 0, 0, 0, 0]]),
                                  'attention_mask': torch.tensor([[1, 1, 1, 1, 0, 0, 0, 0]])})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'config/text_encoder'
            folder.mkdir(parents=True)
            config.to_json_file(folder / 'config.json')
            save_file({key: value.to(torch.bfloat16).clone() for key, value in encoder.state_dict().items()},
                      str(root / 'umt5_xxl_fp8_e4m3fn_scaled.safetensors'))
            with patch.object(wan, 'MODELS', root), patch('transformers.T5TokenizerFast.from_pretrained', return_value=tokenize):
                result = wan.encode_prompts({'prompt': 'moving thread'}, {'negative_prompt': 'human', 'max_sequence_length': 8}, root)
                self.assertEqual(set(result), {'positive', 'negative'})
                self.assertTrue(torch.isfinite(result['positive']).all())
                self.assertTrue(torch.equal(result['positive'][:, 4:], torch.zeros(1, 4, 64, dtype=torch.bfloat16)))
                with patch.object(wan, 'load_weights', side_effect=AssertionError('cached request must not reload weights')):
                    cached = wan.encode_prompts({'prompt': 'moving thread'}, {'negative_prompt': 'human', 'max_sequence_length': 8}, root)
                self.assertTrue(torch.equal(cached['positive'], result['positive']))
        del encoder, result, cached
        torch.cuda.empty_cache()

    def test_streamed_tensor_reader_preserves_values_and_rejects_truncated_payload(self):
        import json
        import struct
        import torch
        from safetensors.torch import save_file
        from scripts.generate_wan_embroidery_module import TensorFile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'streamed.safetensors'
            tensor = torch.arange(12, dtype=torch.bfloat16).reshape(3, 4)
            save_file({'matrix': tensor, 'scalar': torch.tensor(0.5)}, str(path))
            with TensorFile(path) as source:
                self.assertTrue(torch.equal(source.get('matrix'), tensor))
                self.assertEqual(float(source.get('scalar')), 0.5)
            header = json.dumps({'bad': {'dtype': 'F32', 'shape': [4], 'data_offsets': [0, 16]}}).encode()
            path.write_bytes(struct.pack('<Q', len(header)) + header + b'\x00' * 4)
            with TensorFile(path) as source, self.assertRaisesRegex(ValueError, 'Invalid tensor'):
                source.get('bad')

    def test_scaled_fp8_is_restored_before_quantization_and_cpu_table_stays_on_cpu(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for actual NF4 execution')
        from accelerate import init_empty_weights
        from safetensors.torch import save_file
        from transformers import UMT5Config, UMT5EncoderModel
        from scripts.generate_wan_embroidery_module import load_weights
        config = UMT5Config(d_model=64, d_kv=16, d_ff=128, num_layers=1,
                           num_heads=4, vocab_size=128, feed_forward_proj='gated-gelu', tie_word_embeddings=False)
        original = UMT5EncoderModel(config).eval()
        original.set_input_embeddings(original.shared)
        state = {}
        scale = 0.5
        for key, value in original.state_dict().items():
            state[key] = (value / scale).to(torch.float8_e4m3fn)
            if key.endswith('.weight'):
                state[key[:-7] + '.scale_weight'] = torch.tensor(scale)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test-only-scaled.safetensors'
            save_file(state, str(path))
            with init_empty_weights():
                encoder = UMT5EncoderModel(config)
                encoder.set_input_embeddings(encoder.shared)
            encoder = load_weights(encoder, path, offload_embedding=True)
            self.assertEqual(encoder.shared.weight.device.type, 'cpu')
            self.assertEqual(encoder.shared.weight.dtype, torch.bfloat16)
            self.assertTrue(torch.allclose(encoder.shared.weight.float(), original.shared.weight.float(), atol=0.15, rtol=0.08))
            embedding = encoder.shared
            embedding.forward = lambda ids: torch.nn.functional.embedding(ids.cpu(), embedding.weight).to(ids.device)
            encoder.set_input_embeddings(embedding)
            for block in encoder.encoder.block:
                if hasattr(block.layer[0].SelfAttention, 'relative_attention_bias'):
                    block.layer[0].SelfAttention.relative_attention_bias.to('cuda')
            self.assertEqual(encoder.encoder.block[0].layer[1].DenseReluDense.wo.weight.dtype, torch.bfloat16)
            with torch.inference_mode():
                output = encoder(torch.tensor([[1, 2, 3, 4], [4, 3, 2, 1]], device='cuda')).last_hidden_state
            self.assertTrue(torch.isfinite(output).all())
            self.assertGreater(float((output[0] - output[1]).float().abs().mean()), 0.01)
        del output, encoder, embedding, block
        torch.cuda.empty_cache()

    def test_missing_weight_is_rejected_before_inference(self):
        import torch
        from safetensors.torch import save_file
        from scripts.generate_wan_embroidery_module import load_weights
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing.safetensors'
            save_file({'unused': torch.ones(1)}, str(path))
            with self.assertRaisesRegex(ValueError, 'Missing Wan parameters'):
                load_weights(torch.nn.Linear(4, 4), path)

    def test_wan_transformer_rebuilds_rotary_buffers_and_runs_quantized_forward(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for actual Wan NF4 execution')
        from accelerate import init_empty_weights
        from diffusers import WanTransformer3DModel
        from safetensors.torch import save_file
        from scripts.generate_wan_embroidery_module import load_weights
        config = dict(num_attention_heads=2, attention_head_dim=16, in_channels=4,
                      out_channels=4, text_dim=64, freq_dim=16, ffn_dim=64, num_layers=1)
        original = WanTransformer3DModel(**config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tiny-wan.safetensors'
            save_file({key: value.to(torch.bfloat16) for key, value in original.state_dict().items()}, str(path))
            with init_empty_weights():
                model = WanTransformer3DModel(**config)
            model = load_weights(model, path)
            self.assertFalse(model.rope.freqs_cos.is_meta)
            with torch.inference_mode():
                result = model(hidden_states=torch.randn(1, 4, 2, 4, 4, device='cuda', dtype=torch.bfloat16),
                    timestep=torch.tensor([500.], device='cuda'),
                    encoder_hidden_states=torch.randn(1, 8, 64, device='cuda', dtype=torch.bfloat16), return_dict=False)[0]
            self.assertEqual(tuple(result.shape), (1, 4, 2, 4, 4))
            self.assertTrue(torch.isfinite(result).all())
        del result, model
        torch.cuda.empty_cache()
