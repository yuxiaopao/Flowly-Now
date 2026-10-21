"""Regression coverage for real quantized T5 execution and clip provenance gates."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase


class LocalLTXLoadingTests(SimpleTestCase):
    def test_browser_encoding_preserves_original_frames_and_provenance(self):
        import hashlib
        import subprocess
        from workflows.services.butterfly_ltx_job import probe_media,publish_clip
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'model.mp4';published=root/'published';published.mkdir()
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc=size=64x64:rate=30',
                            '-frames:v','15','-c:v','mpeg4',str(source)],check=True,capture_output=True,timeout=30)
            record={'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            target,digest=publish_clip(source,published,record)
            before=probe_media(source);after=probe_media(target)
            self.assertEqual(before['streams'][0]['codec_name'],'mpeg4')
            self.assertEqual(after['streams'][0]['codec_name'],'h264')
            self.assertEqual(after['streams'][0]['nb_frames'],'15')
            self.assertEqual(after['format']['duration'],before['format']['duration'])
            self.assertEqual(hashlib.sha256((published/'model.model.mp4').read_bytes()).hexdigest(),record['sha256'])
            proof=json.loads(target.with_suffix('.json').read_text(encoding='utf-8'))
            self.assertEqual(proof['sha256'],record['sha256'])
            self.assertEqual(proof['published_sha256'],digest)

    def test_cached_model_output_must_match_seed_and_intermediate_conditions(self):
        import hashlib
        from workflows.services.butterfly_ltx_job import read_clip
        shot={'id':'shot','prompt':'An empty linen surface','conditions':[{'image':'skeleton.png','frame_index':80}]}
        spec={'seconds':7.5,'seed':26841}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'clips').mkdir();clip=root/'clips/shot.mp4'
            clip.write_bytes(b'test-only-video-output')
            record={'provider':'ltx_local','model':'Lightricks/test','prompt':shot['prompt'],'duration':7.5,
                    'seed':spec['seed'],'conditions':shot['conditions'],'sha256':hashlib.sha256(clip.read_bytes()).hexdigest()}
            with patch('workflows.services.butterfly_ltx_job.SOURCE_DIRECTORY',root):
                clip.with_suffix('.json').write_text(json.dumps(record),encoding='utf-8')
                self.assertEqual(read_clip(shot,spec)[0],clip)
                record['conditions']=[]
                clip.with_suffix('.json').write_text(json.dumps(record),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'中间画面约束'):
                    read_clip(shot,spec)
                record['conditions']=shot['conditions'];record['seed']+=1
                clip.with_suffix('.json').write_text(json.dumps(record),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'镜头种子'):
                    read_clip(shot,spec)

    def test_t5_output_projection_does_not_cast_activations_to_packed_uint8(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA required for the actual NF4 regression')
        from accelerate import init_empty_weights
        from safetensors.torch import save_file
        from transformers import T5Config, T5EncoderModel
        from scripts.generate_butterfly_local_ltx import load_quantized
        config=T5Config(d_model=64,d_kv=16,d_ff=128,num_layers=1,num_heads=4,vocab_size=128,feed_forward_proj='gated-gelu')
        original=T5EncoderModel(config).eval()
        state={name:value.clone().to(torch.float8_e4m3fn) for name,value in original.state_dict().items()}
        with tempfile.TemporaryDirectory() as directory:
            weights=Path(directory)/'test-only-t5.safetensors';save_file(state,str(weights))
            with init_empty_weights():model=T5EncoderModel(config)
            model=load_quantized(model,str(weights))
            self.assertEqual(model.encoder.block[0].layer[1].DenseReluDense.wo.weight.dtype,torch.bfloat16)
            with torch.inference_mode():
                output=model(torch.tensor([[1,2,3,4],[9,8,7,6]],device='cuda')).last_hidden_state
            self.assertTrue(torch.isfinite(output).all())
            self.assertGreater(float((output[0]-output[1]).float().abs().mean()),0.05)
        del model,original,output
        torch.cuda.empty_cache()

    def test_film_rejects_missing_or_modified_provider_provenance(self):
        from scripts.finish_butterfly_ai_film import validate_clips
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'clips').mkdir();clip=root/'clips/shot.mp4';clip.write_bytes(b'test-only-tampered-media')
            spec={'shots':[{'id':'shot'}]}
            with self.assertRaisesRegex(ValueError,'Missing real model video'):
                validate_clips(spec,root)
            clip.with_suffix('.json').write_text(json.dumps({'provider':'local_animation','model':'Lightricks/test'}))
            with self.assertRaisesRegex(ValueError,'Unverified model origin'):
                validate_clips(spec,root)
            clip.with_suffix('.json').write_text(json.dumps({'provider':'ltx_local','model':'Lightricks/test','sha256':'wrong'}))
            with self.assertRaisesRegex(ValueError,'differs from recorded model output'):
                validate_clips(spec,root)
