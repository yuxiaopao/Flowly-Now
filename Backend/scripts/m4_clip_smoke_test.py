#!/usr/bin/env python
"""M4 CLIP retrieval smoke: pairs.jsonl → index → ClipRetrievalGenerator site."""
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
REPORT = REPO / 'test-reports' / 'm4-smoke-result.json'


def _make_jpeg(path: Path, color=(200, 100, 50)):
    from PIL import Image
    Image.new('RGB', (32, 32), color=color).save(path, format='JPEG')


def main():
    from training.clip_service import build_retrieval_index
    from website_generator.generators.clip_retrieval import ClipRetrievalGenerator

    tmp = tempfile.mkdtemp(prefix='flowly_m4_')
    ds = Path(tmp) / 'dataset'
    img_dir = ds / 'images'
    img_dir.mkdir(parents=True)

    pairs = []
    samples = [
        ('cat_orange.jpg', '一只橘猫在沙发上', (220, 120, 40)),
        ('dog_park.jpg', '公园里的金毛犬', (180, 160, 60)),
        ('product_shoe.jpg', '红色运动鞋商品图', (200, 40, 40)),
        ('face_portrait.jpg', '人物肖像照片', (140, 140, 160)),
        ('food_pizza.jpg', '美味披萨特写', (210, 180, 80)),
    ]
    for i in range(10):
        for name, text, color in samples:
            fn = f'{i}_{name}'
            _make_jpeg(img_dir / fn, color)
            pairs.append({'image': f'images/{fn}', 'text': text})

    with open(ds / 'pairs.jsonl', 'w', encoding='utf-8') as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')

    index_dir = Path(tmp) / 'index'
    idx = build_retrieval_index(str(ds), str(index_dir))
    assert idx.get('success'), idx

    site_dir = Path(tmp) / 'site'
    gen = ClipRetrievalGenerator({
        'output_dir': str(site_dir),
        'index_dir': str(index_dir),
        'metrics': idx.get('metrics', {}),
        'website_type': 'clip_retrieval',
        'name': 'CLIP 检索演示',
        'port': 49153,
        'wizard': {'siteName': 'CLIP 检索演示', 'usageDescription': '文本搜图'},
    })
    gen_result = gen.generate()
    assert gen_result.get('success') is not False

    html = (site_dir / 'frontend' / 'index.html').read_text(encoding='utf-8')
    app_py = (site_dir / 'backend' / 'app.py').read_text(encoding='utf-8')
    checks = {
        'index_built': (index_dir / 'metadata.json').is_file(),
        'r_at_5_positive': (idx.get('metrics') or {}).get('r_at_5', 0) > 0,
        'four_tabs': all(t in html for t in ('文本搜图', '以图搜图', '图库浏览', 'API')),
        'search_api': '/search/text' in app_py,
        'clip_runtime': '_query_vector_text' in app_py,
        'backend_index': (site_dir / 'backend' / 'index' / 'metadata.json').is_file(),
    }
    result = {'passed': all(checks.values()), 'checks': checks, 'metrics': idx.get('metrics')}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
