# -*- coding: utf-8 -*-
"""
苗绣纹样 → 融合系列 → 产品矩阵 工作流 enrichment / create template.

流水线：
  1) 大输入：多张苗绣纹样图 URL + 备注
  2) 并行识别分析各纹样（题材/色彩/几何/寓意）
  3) 融合策划：把多纹样基因合成为系列融合方案
  4) 并行生成一系列融合纹样图
  5) 产品矩阵：基于系列纹样生成文创产品效果图
  6) 汇总输出
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple


PATTERN_COUNT = 4
SERIES_COUNT = 6
PRODUCT_COUNT = 8

_ENRICH_HINTS = (
    '苗绣',
    '苗族刺绣',
    '纹样',
    '纹样识别',
    '纹样融合',
    '产品矩阵',
    '文创产品',
    '刺绣图案',
    '民族纹样',
    'miao embroidery',
    'pattern fusion',
    'product matrix',
)


def is_miao_embroidery_intent(message: str) -> bool:
    text = (message or '').lower()
    # Need at least one strong domain signal
    strong = ('苗绣', '苗族刺绣', 'miao embroidery', '纹样融合', '产品矩阵')
    if any(h in text for h in strong):
        return True
    # Soft: 纹样 + (识别|融合|产品)
    if '纹样' in text and any(k in text for k in ('识别', '分析', '融合', '产品', '文创')):
        return True
    return any(h in text for h in _ENRICH_HINTS if h in ('刺绣图案', '民族纹样', 'pattern fusion'))


def _nid() -> str:
    return str(uuid.uuid4())


def _node_data(node: Dict[str, Any]) -> Dict[str, Any]:
    data = node.get('data')
    return data if isinstance(data, dict) else {}


def _make_node(
    ntype: str,
    name: str,
    x: float,
    y: float,
    config: Optional[Dict[str, Any]] = None,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    nid = node_id or _nid()
    cfg = dict(config or {})
    return {
        'id': nid,
        'type': ntype,
        'name': name,
        'position': {'x': x, 'y': y},
        'config': cfg,
        'data': {
            'label': name,
            'type': ntype,
            'config': cfg,
            'description': '',
        },
    }


def _edge(source: str, target: str, edge_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        'id': edge_id or f'e-{_nid()[:8]}',
        'source': str(source),
        'target': str(target),
        'label': '',
    }


# 默认 4 类经典苗绣母题（无图时仍可走完整链路）
FALLBACK_PATTERNS: List[Dict[str, Any]] = [
    {
        'pattern_index': 1,
        'name': '蝴蝶妈妈',
        'region': '黔东南',
        'image_url': '',
        'notes': '蝴蝶对称展开，翅上点状几何填充，象征生命起源与繁衍。',
        'motif': 'butterfly',
        'colors': ['朱红', '靛蓝', '金线'],
        'geometry': '中轴对称、翅脉放射',
        'symbolism': '始祖庇佑、生命繁衍',
    },
    {
        'pattern_index': 2,
        'name': '龙纹盘旋',
        'region': '湘西',
        'image_url': '',
        'notes': '抽象龙身卷曲成环，鳞片呈三角连续纹，气势盘桓。',
        'motif': 'dragon',
        'colors': ['青绿', '银灰', '朱砂'],
        'geometry': '螺旋卷草、鳞片重复',
        'symbolism': '力量、护佑、丰收',
    },
    {
        'pattern_index': 3,
        'name': '八角花',
        'region': '黔南',
        'image_url': '',
        'notes': '八瓣放射花心，外圈锯齿边饰，适合四方连续铺陈。',
        'motif': 'octagon_flower',
        'colors': ['玫红', '姜黄', '藏青'],
        'geometry': '放射对称、四方连续',
        'symbolism': '团圆、光明、喜庆',
    },
    {
        'pattern_index': 4,
        'name': '鱼鸟相戏',
        'region': '桂北',
        'image_url': '',
        'notes': '鱼鸟对望构图，水波与羽纹交错，动势流畅。',
        'motif': 'fish_bird',
        'colors': ['湖蓝', '橙黄', '珍珠白'],
        'geometry': '对仗构图、波浪节奏',
        'symbolism': '年年有余、自由飞翔',
    },
]


DEFAULT_INPUT = (
    "【苗绣纹样素材】请在下方填写 2~4 张纹样图片的公网 URL（可替换示例）。\n"
    "也可只填文字描述，系统将按经典母题兜底分析。\n\n"
    + json.dumps(
        {
            'style_brief': '当代苗绣文创：保留民族基因，做现代极简与时尚延展',
            'product_categories': ['丝巾', '手提包', '外套刺绣贴片', '抱枕', '手机壳', '帆布袋'],
            'patterns': [
                {
                    'name': p['name'],
                    'image_url': p['image_url'] or f'https://picsum.photos/seed/miao{p["pattern_index"]}/768',
                    'notes': p['notes'],
                    'region': p['region'],
                }
                for p in FALLBACK_PATTERNS
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
)


ANALYZE_SYSTEM = (
    "你是苗绣纹样研究专家与视觉分析师。根据输入的单条纹样信息（可能含 image_url 与 notes），"
    "输出一个纯 JSON 对象（禁止 Markdown），字段必须包含："
    "pattern_index, name, motif_en, motif_zh, colors(数组), geometry, stitch_hints, symbolism, "
    "style_keywords(英文数组), image_prompt_seed(英文，可直接用于文生图复现该纹样特征), "
    "fusion_genes(数组，3-6个可被融合的设计基因短词)。"
    "若提供了 image_url，请结合 URL 与 notes 做尽可能具体的视觉推断；"
    "若无图或图不可见，严格依据 notes/名称做专业推断，不要编造无关现代元素。"
)

FUSION_SYSTEM = (
    f"你是苗绣创新设计总监。将多条纹样分析 JSON 融合成一套系列方案，输出纯 JSON 对象（禁止 Markdown），包含："
    f"1) fusion_concept: 中文融合理念（80字内）；"
    f"2) series: 长度恰好为{SERIES_COUNT}的数组，每项含 "
    "series_index(1-N), title, motif_blend, colorway, layout, "
    "image_prompt(英文文生图，强调 Miao embroidery textile pattern, flat lay, seamless or centered motif, "
    "high detail stitch texture, no photoreal human face)；"
    f"3) product_matrix: 长度恰好为{PRODUCT_COUNT}的数组，每项含 "
    "product_index(1-N), series_index(引用系列), product_type(中文品类), "
    "scene(使用场景), image_prompt(英文产品效果图提示，需写明把该系列纹样印在产品上，"
    "studio product photo, clean background)。"
    "硬性：系列纹样彼此有差异但同属一个设计语言；产品矩阵要覆盖至少4个不同品类。"
)

COLLECT_ANALYSES_CODE = r'''
import json

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and (
    'node_outputs' in raw['input'] or 'variables' in raw['input'] or 'text' in raw['input']
):
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

analyses = []
for key, out in nos.items():
    if not isinstance(out, dict):
        continue
    text = out.get('text') or out.get('result') or ''
    if not text and out.get('name') and out.get('motif_zh'):
        analyses.append(out)
        continue
    if isinstance(text, str) and text.strip().startswith('{'):
        try:
            cleaned = text.strip().strip('`').replace('```json', '').replace('```', '')
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            obj = json.loads(cleaned[start:end + 1] if start >= 0 and end > start else cleaned)
            if isinstance(obj, dict) and (obj.get('name') or obj.get('motif_zh') or obj.get('fusion_genes')):
                analyses.append(obj)
                continue
        except Exception:
            pass
    if out.get('fusion_genes') or out.get('image_prompt_seed') or out.get('motif_zh'):
        analyses.append(out)

seen = set()
uniq = []
for a in analyses:
    name = str(a.get('name') or a.get('motif_zh') or id(a))
    if name in seen:
        continue
    seen.add(name)
    uniq.append(a)

output = {
    'analyses': uniq,
    'count': len(uniq),
    'text': json.dumps(uniq, ensure_ascii=False),
}
'''.strip()

COLLECT_SERIES_CODE = r'''
import json

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

images = []
for key, out in nos.items():
    if not isinstance(out, dict):
        continue
    url = out.get('url') or out.get('image_url')
    imgs = out.get('images')
    if not url and isinstance(imgs, list) and imgs:
        first = imgs[0]
        url = first.get('url') if isinstance(first, dict) else first
    title = out.get('title') or out.get('name') or ''
    if url:
        images.append({'url': url, 'title': title, 'source': str(key)})

seen = set()
uniq = []
for item in images:
    u = item['url']
    if u in seen:
        continue
    seen.add(u)
    uniq.append(item)

output = {
    'series_images': uniq,
    'images': [{'url': i['url']} for i in uniq],
    'count': len(uniq),
    'text': json.dumps(uniq, ensure_ascii=False),
}
'''.strip()

COLLECT_PRODUCTS_CODE = r'''
import json

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

products = []
for key, out in nos.items():
    if not isinstance(out, dict):
        continue
    url = out.get('url') or out.get('image_url')
    imgs = out.get('images')
    if not url and isinstance(imgs, list) and imgs:
        first = imgs[0]
        url = first.get('url') if isinstance(first, dict) else first
    if url:
        products.append({
            'url': url,
            'product_type': out.get('product_type') or out.get('title') or '',
            'source': str(key),
        })

seen = set()
uniq = []
for item in products:
    if item['url'] in seen:
        continue
    seen.add(item['url'])
    uniq.append(item)

output = {
    'product_images': uniq,
    'images': [{'url': i['url']} for i in uniq],
    'count': len(uniq),
    'matrix_size': len(uniq),
    'text': json.dumps(uniq, ensure_ascii=False),
}
'''.strip()


def _pick_pattern_code(index: int) -> str:
    # 1-based index — embed fallback as ASCII-escaped JSON to survive Windows sandbox encoding
    fb = json.dumps(FALLBACK_PATTERNS[index - 1], ensure_ascii=True)
    return f'''
import json

idx = {index}
fallback = json.loads({fb!r})

raw = input if isinstance(input, dict) else {{}}
ext = raw.get('input_data') if isinstance(raw.get('input_data'), dict) else raw
text = ''
if isinstance(ext, dict):
    text = ext.get('text') or ext.get('input') or ext.get('user_input') or ''
    if not text and ext.get('patterns'):
        text = json.dumps(ext, ensure_ascii=False)
patterns = []
payload = None
if isinstance(text, str) and text.strip():
    s = text.strip()
    start = s.find('{{')
    end = s.rfind('}}')
    if start >= 0 and end > start:
        try:
            payload = json.loads(s[start:end + 1])
        except Exception:
            payload = None
if isinstance(payload, dict):
    patterns = payload.get('patterns') or []
elif isinstance(ext, dict) and isinstance(ext.get('patterns'), list):
    patterns = ext.get('patterns')

item = patterns[idx - 1] if isinstance(patterns, list) and len(patterns) >= idx else {{}}
if not isinstance(item, dict):
    item = {{}}

name = item.get('name') or fallback.get('name')
notes = item.get('notes') or fallback.get('notes')
image_url = item.get('image_url') or item.get('url') or fallback.get('image_url') or ''
region = item.get('region') or fallback.get('region') or ''

analysis_input = {{
    'pattern_index': idx,
    'name': name,
    'region': region,
    'image_url': image_url,
    'notes': notes,
    'fallback_genes': fallback.get('motif'),
    'fallback_colors': fallback.get('colors'),
    'fallback_geometry': fallback.get('geometry'),
    'fallback_symbolism': fallback.get('symbolism'),
}}

output = {{
    **analysis_input,
    'text': json.dumps(analysis_input, ensure_ascii=False),
    'prompt': notes,
}}
'''


def _pick_series_code(index: int) -> str:
    return f'''
import json
import re

idx = {index}
fb_titles = ["蝶龙共生", "八角新韵", "鱼鸟流金", "祖纹极简", "夜绣星芒", "织梦几何"]
fb_prompt = (
    "Miao embroidery textile pattern, flat centered motif, intricate stitch texture, "
    "traditional Guizhou colorway with modern spacing, seamless ornamental design, "
    f"variant {{idx}}, ultra detailed, no human face, studio lighting"
)

text = ''
raw = input if isinstance(input, dict) else {{}}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {{}}
# find fusion LLM text
for out in nos.values():
    if not isinstance(out, dict):
        continue
    t = out.get('text') or ''
    if isinstance(t, str) and 'series' in t and 'image_prompt' in t:
        text = t
        break
    if isinstance(out.get('series'), list):
        text = json.dumps(out, ensure_ascii=False)
        break

series = []
if text:
    s = text.strip().strip('`')
    s = s.replace('```json', '').replace('```', '')
    try:
        obj = json.loads(s[s.find('{{'):s.rfind('}}') + 1] if '{{' in s else s)
        if isinstance(obj, dict):
            series = obj.get('series') or []
        elif isinstance(obj, list):
            series = obj
    except Exception:
        # loose extract
        m = re.search(r'\\{{.*\\}}', s, re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
                series = obj.get('series') or [] if isinstance(obj, dict) else []
            except Exception:
                series = []

item = {{}}
for it in series:
    if isinstance(it, dict) and int(it.get('series_index') or 0) == idx:
        item = it
        break
if not item and isinstance(series, list) and len(series) >= idx:
    cand = series[idx - 1]
    item = cand if isinstance(cand, dict) else {{}}

title = item.get('title') or (fb_titles[idx - 1] if idx <= len(fb_titles) else f'融合纹样{{idx}}')
prompt = item.get('image_prompt') or fb_prompt
colorway = item.get('colorway') or ''
motif_blend = item.get('motif_blend') or ''

output = {{
    'series_index': idx,
    'title': title,
    'colorway': colorway,
    'motif_blend': motif_blend,
    'prompt': prompt,
    'image_prompt': prompt,
    'text': json.dumps({{'series_index': idx, 'title': title, 'prompt': prompt}}, ensure_ascii=False),
}}
'''


def _pick_product_code(index: int) -> str:
    return f'''
import json
import re

idx = {index}
fb_types = ["丝巾", "手提包", "外套刺绣贴片", "抱枕", "手机壳", "帆布袋", "杯垫", "笔记本封面"]
fb_prompt = (
    "Studio product photo, Miao embroidery pattern applied on product surface, "
    f"{{fb_types[idx - 1] if idx <= len(fb_types) else 'lifestyle product'}}, "
    "clean background, soft light, commercial catalog style, high detail textile print"
)

text = ''
raw = input if isinstance(input, dict) else {{}}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {{}}
for out in nos.values():
    if not isinstance(out, dict):
        continue
    t = out.get('text') or ''
    if isinstance(t, str) and 'product_matrix' in t:
        text = t
        break
    if isinstance(out.get('product_matrix'), list):
        text = json.dumps(out, ensure_ascii=False)
        break

matrix = []
if text:
    s = text.strip().strip('`').replace('```json', '').replace('```', '')
    try:
        obj = json.loads(s[s.find('{{'):s.rfind('}}') + 1] if '{{' in s else s)
        if isinstance(obj, dict):
            matrix = obj.get('product_matrix') or []
    except Exception:
        m = re.search(r'\\{{.*\\}}', s, re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
                matrix = obj.get('product_matrix') or [] if isinstance(obj, dict) else []
            except Exception:
                matrix = []

item = {{}}
for it in matrix:
    if isinstance(it, dict) and int(it.get('product_index') or 0) == idx:
        item = it
        break
if not item and isinstance(matrix, list) and len(matrix) >= idx:
    cand = matrix[idx - 1]
    item = cand if isinstance(cand, dict) else {{}}

ptype = item.get('product_type') or (fb_types[idx - 1] if idx <= len(fb_types) else f'产品{{idx}}')
prompt = item.get('image_prompt') or fb_prompt
series_index = item.get('series_index') or ((idx - 1) % {SERIES_COUNT}) + 1
scene = item.get('scene') or ''

output = {{
    'product_index': idx,
    'series_index': series_index,
    'product_type': ptype,
    'scene': scene,
    'title': ptype,
    'prompt': prompt,
    'image_prompt': prompt,
    'text': json.dumps({{'product_index': idx, 'product_type': ptype, 'prompt': prompt}}, ensure_ascii=False),
}}
'''


def expand_miao_embroidery_pipeline(
    workflow: Optional[Dict[str, Any]] = None,
    *,
    pattern_count: int = PATTERN_COUNT,
    series_count: int = SERIES_COUNT,
    product_count: int = PRODUCT_COUNT,
) -> Tuple[Dict[str, Any], List[str]]:
    """Build full 苗绣识别→融合→系列纹样→产品矩阵 graph."""
    pattern_count = max(2, min(int(pattern_count or PATTERN_COUNT), 6))
    series_count = max(3, min(int(series_count or SERIES_COUNT), 8))
    product_count = max(4, min(int(product_count or PRODUCT_COUNT), 12))
    changes: List[str] = []

    start = _make_node('start', '开始', 80, 320)
    inp = _make_node(
        'input',
        '苗绣纹样素材输入',
        280,
        320,
        {
            'input_type': 'text',
            'variable_name': 'input',
            'label': '纹样图片URL与备注(JSON)',
            'default_value': DEFAULT_INPUT,
            'placeholder': '粘贴含 patterns[].image_url 的 JSON',
        },
    )

    # Parallel analyze chains
    analyze_chains = []
    y0 = 40
    gap = 160
    for i in range(1, pattern_count + 1):
        y = y0 + (i - 1) * gap
        pick = _make_node(
            'code',
            f'提取纹样{i}',
            560,
            y,
            {'code': _pick_pattern_code(i), 'language': 'python'},
        )
        analyze = _make_node(
            'llm',
            f'识别分析·纹样{i}',
            860,
            y,
            {
                'provider': 'agnes',
                'model': 'agnes-llm-v1',
                'temperature': 0.3,
                'max_tokens': 1200,
                'system_prompt': ANALYZE_SYSTEM,
                'systemPrompt': ANALYZE_SYSTEM,
                'user_template': '请分析以下苗绣纹样素材，输出纯 JSON：\n{input}',
                'userTemplate': '请分析以下苗绣纹样素材，输出纯 JSON：\n{input}',
                'input_variable': 'text',
            },
        )
        analyze_chains.append({'pick': pick, 'analyze': analyze})

    collect_a = _make_node(
        'code',
        '汇总纹样分析',
        1160,
        320,
        {'code': COLLECT_ANALYSES_CODE, 'language': 'python'},
    )

    fusion = _make_node(
        'llm',
        '纹样融合策划',
        1460,
        320,
        {
            'provider': 'agnes',
            'model': 'agnes-llm-v1',
            'temperature': 0.55,
            'max_tokens': 2800,
            'system_prompt': FUSION_SYSTEM.replace(str(SERIES_COUNT), str(series_count)).replace(
                str(PRODUCT_COUNT), str(product_count)
            ),
            'systemPrompt': FUSION_SYSTEM.replace(str(SERIES_COUNT), str(series_count)).replace(
                str(PRODUCT_COUNT), str(product_count)
            ),
            'user_template': (
                '以下是多条苗绣纹样分析结果 JSON 数组，请输出融合系列 + 产品矩阵纯 JSON：\n{input}'
            ),
            'userTemplate': (
                '以下是多条苗绣纹样分析结果 JSON 数组，请输出融合系列 + 产品矩阵纯 JSON：\n{input}'
            ),
            'input_variable': 'text',
        },
    )

    # Series pattern image gens
    series_chains = []
    for i in range(1, series_count + 1):
        y = 40 + (i - 1) * 130
        pick = _make_node(
            'code',
            f'提取融合纹样{i}',
            1760,
            y,
            {'code': _pick_series_code(i), 'language': 'python'},
        )
        image = _make_node(
            'image_generation',
            f'生成融合纹样图{i}',
            2060,
            y,
            {
                'provider': 'agnes',
                'model': 'agnes-image-2.1-flash',
                'prompt': '{prompt}',
                'size': '1024x1024',
                'n': 1,
            },
        )
        series_chains.append({'pick': pick, 'image': image})

    collect_s = _make_node(
        'code',
        '汇总系列纹样图',
        2360,
        280,
        {'code': COLLECT_SERIES_CODE, 'language': 'python'},
    )

    # Product matrix gens (reuse fusion JSON via pick)
    product_chains = []
    for i in range(1, product_count + 1):
        y = 40 + (i - 1) * 110
        pick = _make_node(
            'code',
            f'提取产品{i}',
            2660,
            y,
            {'code': _pick_product_code(i), 'language': 'python'},
        )
        image = _make_node(
            'image_generation',
            f'生成产品效果图{i}',
            2960,
            y,
            {
                'provider': 'agnes',
                'model': 'agnes-image-2.1-flash',
                'prompt': '{prompt}',
                'size': '1024x1024',
                'n': 1,
            },
        )
        product_chains.append({'pick': pick, 'image': image})

    collect_p = _make_node(
        'code',
        '汇总产品矩阵',
        3260,
        320,
        {'code': COLLECT_PRODUCTS_CODE, 'language': 'python'},
    )

    packaging = _make_node(
        'llm',
        '产品矩阵文案包装',
        3560,
        320,
        {
            'provider': 'agnes',
            'model': 'agnes-llm-v1',
            'temperature': 0.5,
            'max_tokens': 1500,
            'system_prompt': (
                '你是文创品牌策划。根据上游产品矩阵与系列纹样信息，输出中文营销包装：'
                '品牌故事短段、系列命名、每类产品一句话卖点、适合电商主图的标题列表。纯文本即可。'
            ),
            'systemPrompt': (
                '你是文创品牌策划。根据上游产品矩阵与系列纹样信息，输出中文营销包装：'
                '品牌故事短段、系列命名、每类产品一句话卖点、适合电商主图的标题列表。纯文本即可。'
            ),
            'user_template': '请基于以下产品矩阵结果撰写包装文案：\n{input}',
            'userTemplate': '请基于以下产品矩阵结果撰写包装文案：\n{input}',
            'input_variable': 'text',
        },
    )

    output = _make_node(
        'output',
        '输出苗绣系列与产品矩阵',
        3860,
        320,
        {
            'output_variable': 'result',
            'format': 'json',
        },
    )
    end = _make_node('end', '结束', 4160, 320)

    nodes: List[Dict[str, Any]] = [
        start, inp, collect_a, fusion, collect_s, collect_p, packaging, output, end,
    ]
    for c in analyze_chains:
        nodes.extend([c['pick'], c['analyze']])
    for c in series_chains:
        nodes.extend([c['pick'], c['image']])
    for c in product_chains:
        nodes.extend([c['pick'], c['image']])

    def sid(n: Dict[str, Any]) -> str:
        return str(n['id'])

    edges: List[Dict[str, Any]] = [
        _edge(sid(start), sid(inp)),
    ]
    for c in analyze_chains:
        edges.append(_edge(sid(inp), sid(c['pick'])))
        edges.append(_edge(sid(c['pick']), sid(c['analyze'])))
        edges.append(_edge(sid(c['analyze']), sid(collect_a)))

    edges.append(_edge(sid(collect_a), sid(fusion)))

    for c in series_chains:
        edges.append(_edge(sid(fusion), sid(c['pick'])))
        edges.append(_edge(sid(c['pick']), sid(c['image'])))
        edges.append(_edge(sid(c['image']), sid(collect_s)))

    # Products also need fusion JSON — connect fusion → product picks,
    # and series collect as soft dependency so series images finish first.
    for c in product_chains:
        edges.append(_edge(sid(fusion), sid(c['pick'])))
        edges.append(_edge(sid(collect_s), sid(c['pick'])))
        edges.append(_edge(sid(c['pick']), sid(c['image'])))
        edges.append(_edge(sid(c['image']), sid(collect_p)))

    edges.extend([
        _edge(sid(collect_p), sid(packaging)),
        _edge(sid(collect_s), sid(output)),
        _edge(sid(packaging), sid(output)),
        _edge(sid(output), sid(end)),
    ])

    seen = set()
    deduped = []
    for e in edges:
        key = (e['source'], e['target'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    base_name = (workflow or {}).get('name') if isinstance(workflow, dict) else None
    updated = {
        'id': (workflow or {}).get('id') if isinstance(workflow, dict) else None,
        'name': base_name or '苗绣纹样识别融合·系列图·产品矩阵',
        'description': (
            f'输入多张苗绣纹样 → {pattern_count}路并行识别分析 → 融合策划 → '
            f'{series_count}张系列纹样图 → {product_count}张产品矩阵效果图 → 文案包装输出'
        ),
        'nodes': nodes,
        'edges': deduped,
    }
    changes.append(
        f'重建为「{pattern_count}路纹样识别 → 融合 → {series_count}系列纹样图 → '
        f'{product_count}产品矩阵」'
    )
    changes.append(f'节点 {len(nodes)} / 连线 {len(deduped)}')
    return updated, changes


def enrich_miao_embroidery_workflow(
    workflow: Optional[Dict[str, Any]],
    *,
    pattern_count: int = PATTERN_COUNT,
    series_count: int = SERIES_COUNT,
    product_count: int = PRODUCT_COUNT,
) -> Tuple[Dict[str, Any], List[str]]:
    return expand_miao_embroidery_pipeline(
        workflow,
        pattern_count=pattern_count,
        series_count=series_count,
        product_count=product_count,
    )


def build_miao_embroidery_workflow(description: str = '') -> Dict[str, Any]:
    """NL create-template entry (from scratch)."""
    wf, _ = expand_miao_embroidery_pipeline(None)
    if description:
        wf['description'] = (wf.get('description') or '') + f'\n用户需求：{description[:500]}'
    return wf
