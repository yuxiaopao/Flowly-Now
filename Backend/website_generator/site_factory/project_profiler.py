"""Rule-based project profiler for ML site factory (M2)."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional


# Keyword → (domain, scenario template, ui_tone, copy_hints, risk_notes)
_DOMAIN_RULES: List[Dict[str, Any]] = [
    {
        'keywords': ['happy', 'sad', 'angry', 'neutral', 'surprise', 'emotion', '情绪', '表情', 'fer'],
        'domain': '智能交互',
        'scenario': '面部表情情绪识别',
        'ui_tone': 'friendly',
        'copy_hints': [
            '上传人脸照片',
            '查看 happy / sad / angry / neutral / surprise 识别结果',
            '支持 JPG/PNG 实时推理',
        ],
        'risk_notes': ['侧脸或遮挡可能影响准确率', '低照度场景建议补光'],
        'display_map': {
            'happy': '开心',
            'sad': '悲伤',
            'angry': '愤怒',
            'neutral': '平静',
            'surprise': '惊讶',
        },
    },
    {
        'keywords': ['helmet', 'hardhat', '安全帽', 'no_helmet', 'head'],
        'domain': '工业安全',
        'scenario': '安全帽佩戴检测',
        'ui_tone': 'industrial_warning',
        'copy_hints': ['上传现场照片', '红框标注未佩戴区域', '支持 JPG/PNG'],
        'risk_notes': ['低照度场景误检率可能升高', '遮挡严重时建议人工复核'],
        'display_map': {
            'helmet': '已佩戴安全帽',
            'no_helmet': '未佩戴安全帽',
            'hardhat': '安全帽',
            'head': '头部',
        },
    },
    {
        'keywords': ['vest', 'reflective', '反光衣', 'uniform', '工装'],
        'domain': '工业安全',
        'scenario': '反光衣/工装穿戴检测',
        'ui_tone': 'industrial_warning',
        'copy_hints': ['上传工地或产线现场图', '查看未穿戴人员标注'],
        'risk_notes': ['远距离小目标可能漏检'],
        'display_map': {'vest': '反光衣', 'no_vest': '未穿反光衣'},
    },
    {
        'keywords': ['fire', 'smoke', '火焰', '烟雾'],
        'domain': '安防监控',
        'scenario': '烟火异常检测',
        'ui_tone': 'alert_red',
        'copy_hints': ['上传监控截图', '关注高置信度告警框'],
        'risk_notes': ['强反光可能造成误报', '建议结合人工值班流程'],
        'display_map': {'fire': '火焰', 'smoke': '烟雾'},
    },
    {
        'keywords': ['defect', 'scratch', 'crack', '瑕疵', '划痕'],
        'domain': '工业质检',
        'scenario': '表面缺陷检测',
        'ui_tone': 'quality_inspect',
        'copy_hints': ['上传产品表面照片', '查看缺陷框与类别'],
        'risk_notes': ['光照不均会影响检出率', '建议固定拍摄角度'],
        'display_map': {'defect': '缺陷', 'scratch': '划痕', 'crack': '裂纹'},
    },
    {
        'keywords': ['cat', 'dog', 'bird', 'pet'],
        'domain': '通用视觉',
        'scenario': '宠物/动物识别',
        'ui_tone': 'friendly',
        'copy_hints': ['上传宠物照片', '查看识别框与置信度'],
        'risk_notes': ['相似品种可能混淆'],
        'display_map': {},
    },
    {
        'keywords': ['tumor', 'lesion', '病灶', '医学', 'medical', 'xray', 'ct'],
        'domain': '医疗影像',
        'scenario': '医学影像辅助分析',
        'ui_tone': 'quality_inspect',
        'copy_hints': ['上传影像切片', '查看疑似区域标注', '结果仅供科研参考'],
        'risk_notes': ['不可作为临床诊断依据', '低对比度区域易漏检'],
        'display_map': {'tumor': '疑似病灶', 'normal': '正常'},
    },
    {
        'keywords': ['product', 'sku', '商品', '零售', 'shelf', '货架'],
        'domain': '智慧零售',
        'scenario': '商品识别与货架监测',
        'ui_tone': 'friendly',
        'copy_hints': ['上传货架照片', '查看商品识别结果'],
        'risk_notes': ['遮挡与反光可能影响识别率'],
        'display_map': {},
    },
]


def _normalize_names(class_names: List[str]) -> List[str]:
    out = []
    for item in class_names or []:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _match_rule(class_names: List[str]) -> Optional[Dict[str, Any]]:
    blob = ' '.join(class_names).lower()
    for rule in _DOMAIN_RULES:
        for kw in rule['keywords']:
            if kw.lower() in blob:
                return rule
    return None


def _build_display_names(class_names: List[str], rule: Optional[Dict[str, Any]]) -> Dict[str, str]:
    mapping = dict((rule or {}).get('display_map') or {})
    result: Dict[str, str] = {}
    for name in class_names:
        key = name.strip()
        if not key:
            continue
        low = key.lower()
        if low in mapping:
            result[key] = mapping[low]
        elif key in mapping:
            result[key] = mapping[key]
        else:
            result[key] = key.replace('_', ' ').replace('-', ' ')
    return result


def llm_enrich_available() -> bool:
    try:
        from django.conf import settings
        return bool(getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY'))
    except Exception:
        return bool(os.environ.get('OPENAI_API_KEY'))


def _default_page_sections(website_type: str, profile: Dict[str, Any]) -> List[str]:
    wtype = (website_type or 'detection').lower()
    if wtype in ('clip_retrieval', 'retrieval'):
        return ['hero', 'text_search', 'image_search', 'gallery', 'api_docs']
    if wtype == 'classification':
        return ['hero', 'upload', 'result_panel', 'disclaimer']
    return ['hero', 'upload', 'detection_canvas', 'metrics_hint', 'disclaimer']


def _default_api_endpoints(website_type: str) -> List[str]:
    wtype = (website_type or 'detection').lower()
    if wtype in ('clip_retrieval', 'retrieval'):
        return ['/health', '/search/text', '/search/image']
    if wtype == 'classification':
        return ['/health', '/predict']
    return ['/health', '/predict']


def build_project_profile(
    class_names: Optional[List[str]] = None,
    model_path: str = '',
    website_type: str = 'detection',
    sample_image_paths: Optional[List[str]] = None,
    use_llm: bool = False,
    metrics: Optional[Dict[str, Any]] = None,
    wizard_scenario: str = '',
) -> Dict[str, Any]:
    """
    Build profiler output. Rule engine first; optional LLM enriches copy (no code gen).
    """
    if not use_llm and llm_enrich_available():
        use_llm = True

    names = _normalize_names(list(class_names or []))
    wtype = (website_type or 'detection').lower()
    rule = _match_rule(names)

    if rule:
        profile = {
            'domain': rule['domain'],
            'scenario': rule['scenario'],
            'ui_tone': rule['ui_tone'],
            'copy_hints': list(rule['copy_hints']),
            'risk_notes': list(rule['risk_notes']),
            'recommended_template': wtype if wtype in ('detection', 'classification', 'clip_retrieval') else 'detection',
            'class_display_names': _build_display_names(names, rule),
        }
    else:
        label_preview = '、'.join(names[:4]) if names else '自定义类别'
        profile = {
            'domain': '通用 AI 视觉',
            'scenario': f'基于 {label_preview} 的智能识别',
            'ui_tone': 'neutral',
            'copy_hints': [
                '上传图片开始识别',
                f'当前支持类别：{label_preview}',
            ],
            'risk_notes': ['建议在正式环境前完成验证集评估'],
            'recommended_template': wtype if wtype in ('detection', 'classification', 'clip_retrieval') else 'detection',
            'class_display_names': _build_display_names(names, None),
        }

    profile['class_names'] = names
    profile['model_path'] = model_path or ''
    profile['website_type'] = wtype
    profile['sample_count'] = len(sample_image_paths or [])
    profile['metrics'] = dict(metrics or {})
    if wizard_scenario and not profile.get('scenario'):
        profile['scenario'] = wizard_scenario
    profile['page_sections'] = _default_page_sections(wtype, profile)
    profile['api_endpoints'] = _default_api_endpoints(wtype)
    profile['profiler_version'] = '1.1-rules'

    if use_llm:
        enriched = _try_llm_enrich(profile, names, metrics=profile.get('metrics'))
        if enriched:
            profile.update(enriched)
            profile['profiler_version'] = '1.1-rules+llm'

    return profile


def _try_llm_enrich(
    profile: Dict[str, Any],
    class_names: List[str],
    metrics: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Optional LLM copy polish — failures are silent."""
    try:
        from django.conf import settings
        if not getattr(settings, 'OPENAI_API_KEY', None) and not os.environ.get('OPENAI_API_KEY'):
            return None
    except Exception:
        return None
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.3, max_tokens=400)
        prompt = (
            '你是 ML 产品文案助手。根据以下 JSON 场景信息，仅输出 JSON，字段 copy_hints(3条中文)、'
            'risk_notes(2条中文)、scenario(一句中文)、page_sections(数组)、api_endpoints(数组)。不要生成代码。\n'
            f'类别: {class_names}\n指标: {json.dumps(metrics or {}, ensure_ascii=False)}\n'
            f'当前: {json.dumps(profile, ensure_ascii=False)}'
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        text = (resp.content or '').strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if not m:
            return None
        data = json.loads(m.group(0))
        out = {}
        for key in ('copy_hints', 'risk_notes', 'scenario', 'page_sections', 'api_endpoints'):
            if key in data and data[key]:
                out[key] = data[key]
        return out or None
    except Exception:
        return None


def write_profile_json(output_dir: str, profile: Dict[str, Any]) -> str:
    """Persist profile beside site output (optional)."""
    if not output_dir:
        return ''
    flowly_dir = os.path.join(output_dir, '.flowly')
    os.makedirs(flowly_dir, exist_ok=True)
    path = os.path.join(flowly_dir, 'profile.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return path


def build_retrieval_profile(
    index_dir: str = '',
    metrics: Optional[Dict[str, Any]] = None,
    sample_captions: Optional[List[str]] = None,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """Profile for CLIP retrieval sites (no class_names required)."""
    metrics = metrics or {}
    captions = list(sample_captions or [])
    vector_count = 0
    model_name = 'simple-bow'

    meta_path = os.path.join(index_dir, 'metadata.json') if index_dir else ''
    if meta_path and os.path.isfile(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            vector_count = int(meta.get('vector_count') or len(meta.get('items') or []))
            model_name = meta.get('model') or model_name
            if not captions:
                captions = [
                    str(item.get('caption') or item.get('text') or '')
                    for item in (meta.get('items') or [])[:5]
                    if item.get('caption') or item.get('text')
                ]
            meta_metrics = meta.get('metrics') or {}
            for key in ('r_at_1', 'r_at_5', 'r_at_10'):
                if key not in metrics and key in meta_metrics:
                    metrics[key] = meta_metrics[key]
        except Exception:
            pass

    copy_hints = captions[:3] if captions else ['一只橘猫', '工业现场照片', '商品展示图']
    r5 = metrics.get('r_at_5')
    risk_notes = ['索引规模较小时检索结果可能不稳定']
    if r5 is not None and float(r5) < 0.5:
        risk_notes.append('验证集 R@5 偏低，建议扩充图文对或更换 CLIP 模型')

    profile = {
        'domain': '多模态检索',
        'scenario': '图文相似度检索演示',
        'ui_tone': 'search_gallery',
        'copy_hints': copy_hints,
        'risk_notes': risk_notes,
        'recommended_template': 'clip_retrieval',
        'class_display_names': {},
        'class_names': [],
        'model_path': '',
        'website_type': 'clip_retrieval',
        'index_dir': index_dir or '',
        'vector_count': vector_count,
        'base_model': model_name,
        'metrics': metrics,
        'sample_count': vector_count,
        'profiler_version': '1.0-retrieval-rules',
    }

    if use_llm:
        enriched = _try_llm_enrich(profile, copy_hints)
        if enriched:
            profile.update(enriched)
            profile['profiler_version'] = '1.0-retrieval-rules+llm'

    return profile
