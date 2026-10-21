# -*- coding: utf-8 -*-
"""
Deterministic short-drama enrichment for the workflow editor assistant.

Target graph shape (user intent):
  1) One large input accepts full chapter / outline content
  2) Fan-out into N visible parallel shot chains (each shows content + image + video)
  3) Fan-in to one finishing chain that concatenates a ~60s short drama
"""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple


SHOT_COUNT = 12
SHOT_DURATION_SEC = 5

_ENRICH_HINTS = (
    '1分钟',
    '一分钟',
    '60秒',
    '短剧',
    '大制作',
    '12镜',
    '12个镜头',
    '十二镜',
    '分别生成',
    '汇总',
    '成片',
    '整合',
    '并行',
    '12条',
    '十二条',
    '分链路',
    '分镜链路',
    '章节',
)


def is_short_drama_enrich_intent(message: str) -> bool:
    text = message or ''
    return any(h in text for h in _ENRICH_HINTS)


def is_short_drama_intent(message: str) -> bool:
    """NL create gate: require clear short-drama / 12-shot signals (avoid bare「章节」)."""
    text = message or ''
    strong = (
        '短剧', '1分钟', '一分钟', '60秒', '12镜', '十二镜', '12个镜头',
        '12条', '十二条', '分镜链路', '并行分镜', '武侠短剧',
    )
    if any(k in text for k in strong):
        return True
    # Weaker pairs: 分镜 + (并行|汇总|成片)
    if '分镜' in text and any(k in text for k in ('并行', '汇总', '成片', '整合')):
        return True
    return False


def build_short_drama_workflow(
    description: str = '',
    *,
    shot_count: int = SHOT_COUNT,
) -> Dict[str, Any]:
    """NL/template entry: empty shell → 章节输入 → N 并行分镜 → 汇总成片."""
    shot_count = max(4, min(int(shot_count or SHOT_COUNT), 24))
    empty: Dict[str, Any] = {
        'name': '',
        'description': description or '',
        'nodes': [],
        'edges': [],
    }
    updated, _ = expand_to_parallel_shot_pipeline(empty, shot_count=shot_count)
    if description:
        updated['description'] = description
    updated['_generation_mode'] = 'template_short_drama'
    updated['_is_intelligent'] = True
    return updated


def _node_data(node: Dict[str, Any]) -> Dict[str, Any]:
    data = node.get('data')
    return data if isinstance(data, dict) else {}


def _get_config(node: Dict[str, Any]) -> Dict[str, Any]:
    cfg = node.get('config')
    if isinstance(cfg, dict) and cfg:
        return dict(cfg)
    nested = _node_data(node).get('config')
    if isinstance(nested, dict):
        return dict(nested)
    return {}


def _set_config(node: Dict[str, Any], cfg: Dict[str, Any], name: Optional[str] = None) -> None:
    node['config'] = cfg
    data = _node_data(node)
    if not data:
        data = {}
        node['data'] = data
    data['config'] = cfg
    data['type'] = node.get('type') or data.get('type')
    if name:
        node['name'] = name
        data['label'] = name
    elif node.get('name'):
        data.setdefault('label', node['name'])
    elif data.get('label'):
        node['name'] = data['label']


def _nid() -> str:
    return str(uuid.uuid4())


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


def _find_nodes(workflow: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    by_role: Dict[str, Dict[str, Any]] = {}
    for node in workflow.get('nodes') or []:
        if not isinstance(node, dict):
            continue
        ntype = node.get('type') or _node_data(node).get('type') or ''
        name = (node.get('name') or _node_data(node).get('label') or '')
        if ntype == 'start':
            by_role['start'] = node
        elif ntype == 'end':
            by_role['end'] = node
        elif ntype == 'input':
            by_role['input'] = node
        elif ntype == 'output':
            by_role['output'] = node
        elif ntype == 'merge' or '拼接' in name:
            if '图' in name:
                by_role['merge_images'] = node
            else:
                by_role.setdefault('merge', node)
        elif ntype == 'audio_generation' or '配音' in name:
            by_role['audio'] = node
        elif ntype == 'subtitle_burn' or '烧录' in name:
            by_role['burn'] = node
        elif ntype == 'subtitle_generation' or ('字幕' in name and '烧录' not in name):
            by_role['subtitle'] = node
        elif ntype == 'llm':
            if '大纲' in name or '章节' in name or '剧情' in name or '分镜表' in name:
                by_role['chapters'] = node
            elif '旁白' in name:
                by_role['narration'] = node
            elif '包装' in name:
                by_role['packaging'] = node
        elif ntype in ('data_transform', 'json_transform') or '拆分' in name:
            by_role['parse'] = node
        elif ntype == 'code' and ('汇总' in name or '清单' in name):
            by_role['collect'] = node
    return by_role


CHAPTER_SYSTEM = (
    f"你是武侠短剧编剧。把用户提供的章节/剧情内容，整理为长度恰好为{SHOT_COUNT}的纯JSON数组（禁止Markdown）。"
    "每个元素代表约5秒的一个镜头，字段必须包含："
    "shot_index(1-12), title, beat(起|承|转|合|终), scene, action, dialogue, emotion, duration_sec, "
    "image_prompt(英文文生图提示词), video_motion_prompt(英文图生视频动态提示)。"
    "【最重要】12镜必须严格按整章叙事弧递进：场景、人物站位、动作、对白、image_prompt、"
    "video_motion_prompt 全部互不相同；禁止复制粘贴同一段提示词；禁止12镜同一构图。"
    "建议结构：1建立环境 2少年入场 3发现女侠 4对峙试探 5剑意交锋 6追兵将至 "
    "7女侠护势 8破门开战 9双人联手 10绝境对峙 11一剑定江湖 12雨歇收束。"
    "若原文已是分镜列表则对齐补全字段；若是散文则拆成完整叙事弧。"
    f"每个 duration_sec 固定为 {SHOT_DURATION_SEC}。"
)

CHAPTER_USER = (
    f"以下是完整章节/剧情内容，请输出恰好{SHOT_COUNT}个镜头的JSON数组：\n{{input}}"
)

DEFAULT_CHAPTER_INPUT = (
    "【章节正文】\n"
    "少年剑客雨夜破庙遇白衣女侠，一剑定江湖。\n"
    "荒山暴雨，少年负伤闯入破庙；白衣女侠现身试探；剑意初显；追杀逼近；对决升温；"
    "绝境一剑定江湖；余韵门派震动，少年成长收束。\n"
    "请按起承转合拆成12个约5秒镜头，供下游并行分镜生产。"
)


# Deterministic 12-beat storyboard for the default wuxia theme.
# Used when LLM/parse output is missing so parallel chains never collapse
# into the same empty "镜头N" + identical motion prompt.
FALLBACK_SHOTS: List[Dict[str, Any]] = [
    {
        'shot_index': 1, 'title': '暴雨破庙', 'beat': '起',
        'scene': '荒山古庙外景·雨夜',
        'action': '闪电劈亮残破庙顶，暴雨如注，镜头从远景缓缓推近庙门。',
        'dialogue': '', 'emotion': '压抑肃杀',
        'image_prompt': 'Cinematic wide shot, ancient ruined Chinese temple on stormy mountain, heavy rain, lightning over broken roof, night, dark blue tone, wuxia film still, ultra detailed',
        'video_motion_prompt': 'Slow zoom toward temple gate, rain sheets, lightning flash, wind tearing roof tiles',
    },
    {
        'shot_index': 2, 'title': '少年闯入', 'beat': '起',
        'scene': '破庙门槛',
        'action': '黑衣少年剑客推开朽门，雨水顺衣摆滴落，手按剑柄警惕扫视。',
        'dialogue': '', 'emotion': '警惕沉稳',
        'image_prompt': 'Medium shot young Chinese swordsman in soaked black robes pushing old wooden temple door, hand on sword hilt, rain dripping, tense eyes, dark interior beyond',
        'video_motion_prompt': 'Door creaks open, swordsman steps inside, water drips from sleeves, camera follows',
    },
    {
        'shot_index': 3, 'title': '白影现形', 'beat': '起',
        'scene': '破庙内殿阴影',
        'action': '烛火摇曳，少年目光锁定角落里静坐的白色身影。',
        'dialogue': '谁？', 'emotion': '疑惑紧张',
        'image_prompt': 'Over-shoulder shot inside ruined temple, flickering candle, mysterious white-robed woman silhouette in shadow, dust motes, atmospheric wuxia tension',
        'video_motion_prompt': 'Slow rack focus to white silhouette, candle flame flickers, dust drifts',
    },
    {
        'shot_index': 4, 'title': '女侠起身', 'beat': '承',
        'scene': '破庙佛龛前',
        'action': '白衣女侠缓缓起身，衣袂无风自动，眼神清冷打量少年。',
        'dialogue': '伤者，不该来此处。', 'emotion': '清冷试探',
        'image_prompt': 'Full shot elegant white-robed Chinese swordswoman rising before broken Buddha niche, flowing sleeves, cold gaze, rainy night temple, cinematic lighting',
        'video_motion_prompt': 'Woman rises gracefully, sleeves flow, slight turn toward swordsman',
    },
    {
        'shot_index': 5, 'title': '剑意初显', 'beat': '承',
        'scene': '庙内空地',
        'action': '少年拔剑寸许，剑气激起积水涟漪；女侠指尖轻点，剑意对撞无声。',
        'dialogue': '', 'emotion': '试探较劲',
        'image_prompt': 'Close medium shot two swords, black-robed youth and white-robed heroine, faint sword qi rippling puddles on temple floor, sparks of energy, wuxia cinematic',
        'video_motion_prompt': 'Blade slides from scabbard an inch, water ripples, invisible qi clash shimmer',
    },
    {
        'shot_index': 6, 'title': '追兵将至', 'beat': '承',
        'scene': '庙外山道',
        'action': '远处火把连成一线，黑衣杀手纵身掠过树梢，杀气逼近破庙。',
        'dialogue': '搜！别让他跑了！', 'emotion': '危机逼近',
        'image_prompt': 'Night mountain path, torch line of assassins in black, leaping between wet trees toward ruined temple, rain, suspenseful wuxia wide shot',
        'video_motion_prompt': 'Torches advance through rain, assassins leap between branches toward camera',
    },
    {
        'shot_index': 7, 'title': '女侠护势', 'beat': '转',
        'scene': '破庙门槛内侧',
        'action': '女侠侧身挡在少年前，白袖一挥成护势，雨丝在袖风前偏转。',
        'dialogue': '今夜，我不许他们进门。', 'emotion': '决意护持',
        'image_prompt': 'Dramatic side shot white-robed swordswoman shielding wounded youth at temple threshold, sleeve creating wind barrier against rain, heroic wuxia composition',
        'video_motion_prompt': 'Sleeve sweep creates wind, rain deflects, she steps protectively forward',
    },
    {
        'shot_index': 8, 'title': '刀光破门', 'beat': '转',
        'scene': '庙门碎裂瞬间',
        'action': '杀手刀光劈开庙门，木屑飞溅，少年与女侠同时拔剑迎击。',
        'dialogue': '', 'emotion': '爆发冲突',
        'image_prompt': 'Action still, temple door exploding inward, flying wood splinters, dual swords drawn by youth and white-robed heroine facing masked assassins, rain and sparks',
        'video_motion_prompt': 'Door shatters, splinters fly, both draw swords into fighting stance',
    },
    {
        'shot_index': 9, 'title': '双剑交错', 'beat': '转',
        'scene': '庙内混战',
        'action': '少年与女侠背靠背拆招，剑光如网，数名杀手倒地溅起水花。',
        'dialogue': '', 'emotion': '默契激战',
        'image_prompt': 'Dynamic fight scene inside ruined temple, young swordsman and white-robed heroine back-to-back, sword trails as light nets, fallen assassins, rain through broken roof',
        'video_motion_prompt': 'Fast sword exchanges, spinning back-to-back, assassins knocked into puddles',
    },
    {
        'shot_index': 10, 'title': '绝境对峙', 'beat': '合',
        'scene': '佛龛前空地',
        'action': '最后一名蒙面首领逼近，女侠腕伤；少年握剑站到最前。',
        'dialogue': '剩下的，我来。', 'emotion': '悲壮决绝',
        'image_prompt': 'Tense standoff before broken Buddha, wounded white-robed heroine behind, young black-robed swordsman facing masked assassin leader, rain, low angle heroic framing',
        'video_motion_prompt': 'Youth steps forward into frame, grip tightens on sword, leader advances slowly',
    },
    {
        'shot_index': 11, 'title': '一剑定江湖', 'beat': '合',
        'scene': '破庙中央',
        'action': '少年全力一剑，剑气贯穿雨幕，定格在首领喉前半寸，杀局瞬止。',
        'dialogue': '退。', 'emotion': '锋芒立威',
        'image_prompt': 'Climax freeze-frame, young swordsman finishing strike, visible sword qi cutting through rain toward masked leader throat, white-robed heroine watching, epic wuxia lighting',
        'video_motion_prompt': 'Explosive forward thrust, sword qi streak through rain, leader freezes, rain hangs in air',
    },
    {
        'shot_index': 12, 'title': '雨歇余韵', 'beat': '终',
        'scene': '破庙外阶·雨渐停',
        'action': '追杀散去，女侠微微颔首；少年收剑，远处天边微亮。',
        'dialogue': '江湖路远，后会有期。', 'emotion': '释然成长',
        'image_prompt': 'Quiet ending shot on wet temple steps, rain easing, white-robed heroine nodding, young swordsman sheathing sword, faint dawn light on horizon, poetic wuxia',
        'video_motion_prompt': 'Slow pull-back, rain softens, sword returns to scabbard, dawn glow rises',
    },
]


def _pick_script(shot_index: int) -> str:
    # Embed fallback for this shot so sandbox has a concrete distinct beat.
    fb = FALLBACK_SHOTS[shot_index - 1] if 1 <= shot_index <= len(FALLBACK_SHOTS) else FALLBACK_SHOTS[0]
    fb_json = json.dumps(fb, ensure_ascii=False)
    return f'''
import json
SHOT_INDEX = {shot_index}
FALLBACK = json.loads({fb_json!r})
raw = input if isinstance(input, dict) else {{'value': input}}
vars_ = raw.get('variables') if isinstance(raw.get('variables'), dict) else {{}}
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {{}}

def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith('```'):
            text = text.strip('`')
            if text.lower().startswith('json'):
                text = text[4:].strip()
        # Extract JSON array even if wrapped in prose
        if '[' in text and ']' in text:
            try:
                start = text.index('[')
                end = text.rindex(']') + 1
                parsed = json.loads(text[start:end])
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for key in ('items', 'shots', 'chapters', 'scenes', 'data', 'result'):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
        except Exception:
            return []
    if isinstance(value, dict):
        for key in ('items', 'shots', 'chapters', 'scenes', 'data', 'result'):
            if isinstance(value.get(key), list):
                return value[key]
        # nested text field may hold JSON array
        for key in ('text', 'content', 'output', 'result'):
            if isinstance(value.get(key), str):
                got = _as_list(value.get(key))
                if got:
                    return got
    return []

items = _as_list(raw)
if not items:
    items = _as_list(vars_)
if not items:
    for key in ('items', 'shots', 'chapters', 'scenes', 'data', 'result', 'text', 'output', 'content'):
        if key in raw:
            items = _as_list(raw.get(key))
            if items:
                break
# Fan-in from upstream LLM / parse via node_outputs
if not items and nos:
    for out in nos.values():
        items = _as_list(out)
        if items:
            break
        if isinstance(out, dict):
            for val in out.values():
                items = _as_list(val)
                if items:
                    break
        if items:
            break

item = {{}}
if isinstance(items, list) and items:
    # Prefer matching shot_index, else positional
    for cand in items:
        if isinstance(cand, dict) and int(cand.get('shot_index') or 0) == SHOT_INDEX:
            item = cand
            break
    if not item and len(items) >= SHOT_INDEX:
        cand = items[SHOT_INDEX - 1]
        item = cand if isinstance(cand, dict) else {{'scene': str(cand), 'title': f'镜头{{SHOT_INDEX}}'}}

# Hard fallback: never allow empty identical prompts across shots
if not isinstance(item, dict) or not (item.get('scene') or item.get('action') or item.get('image_prompt')):
    item = dict(FALLBACK)

# If LLM returned duplicated prompts across the array, force this shot's FALLBACK
# so parallel branches never collapse to the same generation.
dup_hit = 0
if isinstance(items, list):
    my_img = str((item or {{}}).get('image_prompt') or '').strip()
    my_act = str((item or {{}}).get('action') or '').strip()
    if my_img or my_act:
        for cand in items:
            if not isinstance(cand, dict):
                continue
            if my_img and str(cand.get('image_prompt') or '').strip() == my_img:
                dup_hit += 1
            elif my_act and str(cand.get('action') or '').strip() == my_act:
                dup_hit += 1
if dup_hit >= 3:
    item = dict(FALLBACK)

title = item.get('title') or FALLBACK['title']
scene = item.get('scene') or item.get('scene_description') or FALLBACK['scene']
action = item.get('action') or FALLBACK['action']
dialogue = item.get('dialogue') or item.get('on_screen_text') or FALLBACK.get('dialogue') or ''
emotion = item.get('emotion') or FALLBACK.get('emotion') or ''
image_prompt = (
    item.get('image_prompt')
    or item.get('prompt')
    or FALLBACK['image_prompt']
)
motion = (
    item.get('video_motion_prompt')
    or item.get('motion')
    or FALLBACK['video_motion_prompt']
)
# Force shot identity into prompts so image/video providers cannot collapse
image_prompt = f"Shot {{SHOT_INDEX}}/12: {{title}}. " + str(image_prompt)
motion = f"Shot {{SHOT_INDEX}}/12 unique action: {{action[:80]}}. " + str(motion)
display = (
    f"[镜{{SHOT_INDEX}}/12] {{title}}\\n"
    f"场景：{{scene}}\\n动作：{{action}}\\n对白：{{dialogue}}\\n情绪：{{emotion}}"
)
shot_key = f"shot_{{SHOT_INDEX:02d}}"
output = {{
    'shot_index': item.get('shot_index') or SHOT_INDEX,
    'title': title,
    'beat': item.get('beat') or FALLBACK.get('beat') or '',
    'scene': scene,
    'action': action,
    'dialogue': dialogue,
    'emotion': emotion,
    'duration_sec': item.get('duration_sec') or {SHOT_DURATION_SEC},
    'image_prompt': image_prompt,
    'video_motion_prompt': motion,
    # Unique keys survive parallel last-wins pollution on shared names
    shot_key + '_image_prompt': image_prompt,
    shot_key + '_video_motion_prompt': motion,
    shot_key + '_title': title,
    'prompt': image_prompt,
    'text': display,
    'content': display,
}}
'''.strip()


STORYBOARD_SYSTEM = (
    "你是电影分镜师。把当前这一镜整理为可拍摄分镜JSON（禁止Markdown），字段："
    "shot_index, title, scene_description(中文详细画面), camera_angle, characters, lighting, motion, "
    "image_prompt(英文), video_motion_prompt(英文), on_screen_text。"
    "保持雨夜破庙、白衣女侠、少年剑客、剑气的视觉连续性。"
)

STORYBOARD_USER = "请把以下单镜内容扩写为完整分镜JSON（仅输出JSON）：\n{input}"

COLLECT_PARALLEL_SCRIPT = r'''
# Collect 12 parallel shot videos/images in shot_index order
raw = input if isinstance(input, dict) else {}
vars_ = raw.get('variables') if isinstance(raw.get('variables'), dict) else {}
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

shots = []
seen_urls = set()

def consider(obj):
    if not isinstance(obj, dict):
        return
    video_url = obj.get('video_url') or obj.get('video')
    image_url = obj.get('image_url')
    if not image_url and isinstance(obj.get('images'), list) and obj['images']:
        g0 = obj['images'][0]
        image_url = g0.get('url') if isinstance(g0, dict) else g0
    shot_index = obj.get('shot_index')
    title = obj.get('title') or ''
    scene = obj.get('scene_description') or obj.get('scene') or obj.get('text') or ''
    if video_url or image_url or shot_index is not None:
        key = video_url or f"{shot_index}:{title}:{scene[:40]}"
        if key in seen_urls:
            return
        seen_urls.add(key)
        shots.append({
            'shot_index': shot_index,
            'title': title,
            'scene': scene,
            'image_url': image_url or '',
            'video_url': video_url or '',
        })

for out in nos.values():
    consider(out)
    if isinstance(out, dict):
        for val in out.values():
            if isinstance(val, dict):
                consider(val)

consider(raw)
consider(vars_)

# Keep entries that look like shot deliverables
usable = [s for s in shots if s.get('video_url') or s.get('image_url') or s.get('shot_index')]
usable.sort(key=lambda s: (999 if s.get('shot_index') in (None, '') else int(s.get('shot_index') or 999)))

video_urls = []
images = []
for s in usable:
    u = s.get('video_url')
    if u and u not in video_urls:
        video_urls.append(u)
    if s.get('image_url'):
        images.append({'url': s['image_url'], 'shot_index': s.get('shot_index')})

output = {
    'shots': usable,
    'shot_count': len(usable),
    'images': images,
    'image_count': len(images),
    'video_urls': video_urls,
    'clip_count': len(video_urls),
    'video_url': video_urls[-1] if video_urls else '',
    'text': f'已汇总 {len(video_urls)} 段分镜视频、{len(images)} 张分镜图，准备拼接约60秒成片。',
    'items': [{'video_url': u} for u in video_urls],
}
'''.strip()

NARRATION_SYSTEM = (
    "你是短剧旁白撰稿人。根据全部镜头清单与成片信息，写一段可朗读约60秒的中文旁白。"
    "要求有起承转合、画面感强、适合配音与字幕，分段用换行，不要输出JSON。"
)
NARRATION_USER = "根据以下镜头汇总与剧情生成约60秒旁白：\n{input}"

PACKAGING_SYSTEM = (
    "你是短剧宣发文案。根据成片信息写JSON（禁止Markdown）："
    "title, tagline, synopsis_30s, hashtags(数组), poster_text。"
)


def expand_to_parallel_shot_pipeline(
    workflow: Dict[str, Any],
    *,
    shot_count: int = SHOT_COUNT,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Rebuild graph as:
      input(章节) → 12镜大纲 → JSON拆分 → 12 parallel chains → 汇总 → 成片精修 → output
    """
    if not isinstance(workflow, dict):
        return workflow, []

    roles = _find_nodes(workflow if workflow.get('nodes') else {'nodes': []})
    changes: List[str] = []

    def reuse_or_make(role: str, ntype: str, name: str, x: float, y: float, config: Dict[str, Any]) -> Dict[str, Any]:
        existing = roles.get(role)
        if existing and (existing.get('type') or _node_data(existing).get('type')) == ntype:
            node = copy.deepcopy(existing)
            _set_config(node, config, name=name)
            node['position'] = {'x': x, 'y': y}
            data = _node_data(node)
            data['label'] = name
            data['type'] = ntype
            node['data'] = data
            node['type'] = ntype
            node['name'] = name
            return node
        return _make_node(ntype, name, x, y, config)

    start = reuse_or_make('start', 'start', '开始', 80, 40, {})
    inp = reuse_or_make(
        'input',
        'input',
        '章节内容输入(大文本)',
        300,
        40,
        {
            'inputType': 'text',
            'input_type': 'text',
            'input_name': 'chapters',
            'variableName': 'chapters',
            'label': '章节/分镜正文',
            'placeholder': '粘贴完整章节或分镜大纲…',
            'default': DEFAULT_CHAPTER_INPUT,
            'user_input': DEFAULT_CHAPTER_INPUT,
            'userInput': DEFAULT_CHAPTER_INPUT,
            'value': DEFAULT_CHAPTER_INPUT,
        },
    )
    chapters = reuse_or_make(
        'chapters',
        'llm',
        f'LLM整理为{shot_count}镜分镜表',
        560,
        40,
        {
            'model': 'agnes-llm-v1',
            'temperature': 0.55,
            'max_tokens': 8192,
            'system_prompt': CHAPTER_SYSTEM.replace(str(SHOT_COUNT), str(shot_count)),
            'user_template': CHAPTER_USER.replace(str(SHOT_COUNT), str(shot_count)),
        },
    )
    parse = reuse_or_make(
        'parse',
        'data_transform',
        'JSON镜头数组拆分',
        820,
        40,
        {'operation': 'parse_array', 'target_field': 'items'},
    )

    # Parallel layout (matches editor screenshot):
    #   same stage → one horizontal row; each shot → one vertical column
    #   分镜内容(上) → 关键帧图(中) → 视频片段(下) → 汇总扇入
    col_w = 240
    base_x = 80
    y_pick, y_img, y_vid = 220, 420, 620
    chains: List[Dict[str, Dict[str, Any]]] = []
    for i in range(1, shot_count + 1):
        x = base_x + (i - 1) * col_w
        pick = _make_node(
            'code',
            f'镜{i:02d}-分镜内容(展示)',
            x,
            y_pick,
            {
                'language': 'python',
                'code': _pick_script(i),
                'script': _pick_script(i),
                'input_variable': 'input',
            },
        )
        image = _make_node(
            'image_generation',
            f'镜{i:02d}-关键帧图(展示)',
            x,
            y_img,
            {
                'provider': 'agnes',
                'model': 'agnes-image-2.1-flash',
                # Prefer unique per-shot key; fallback to branch-local image_prompt
                'prompt': f'{{shot_{i:02d}_image_prompt}}',
                'n': 1,
                'size': '1024x1024',
                'max_retries': 5,
            },
        )
        video = _make_node(
            'video_generation',
            f'镜{i:02d}-视频片段(展示)',
            x,
            y_vid,
            {
                'provider': 'agnes',
                'model': 'agnes-video-v2.0',
                'prompt': f'{{shot_{i:02d}_video_motion_prompt}}',
                'duration': SHOT_DURATION_SEC,
                'resolution': '720p',
                'input_image': '{images.0.url}',
                'max_retries': 3,
                'timeout': 600,
            },
        )
        chains.append({'pick': pick, 'image': image, 'video': video})

    grid_mid_x = base_x + ((shot_count - 1) * col_w) / 2.0
    y_join = 820
    collect = reuse_or_make(
        'collect',
        'code',
        '汇总12镜素材清单',
        grid_mid_x,
        y_join,
        {'language': 'python', 'code': COLLECT_PARALLEL_SCRIPT, 'script': COLLECT_PARALLEL_SCRIPT},
    )
    merge = reuse_or_make(
        'merge',
        'merge',
        '成片视频拼接',
        grid_mid_x,
        y_join + 180,
        {
            'mode': 'concat',
            'strategy': 'concat_videos',
            'merge_key': 'video_url',
            'ordered': True,
            'target_duration_sec': 60,
            'clip_duration_sec': SHOT_DURATION_SEC,
            'fill_mode': 'stretch',
        },
    )
    finish_y = y_join + 180
    finish_x0 = grid_mid_x + 280
    narration = reuse_or_make(
        'narration',
        'llm',
        '成片旁白文案',
        finish_x0,
        finish_y,
        {
            'model': 'agnes-llm-v1',
            'temperature': 0.7,
            'max_tokens': 4096,
            'system_prompt': NARRATION_SYSTEM,
            'user_template': NARRATION_USER,
        },
    )
    audio = reuse_or_make(
        'audio',
        'audio_generation',
        '旁白配音(展示)',
        finish_x0 + 260,
        finish_y,
        {
            # auto: local pyttsx3 → gTTS → edge_tts → demo (never hard-fail film)
            'provider': 'auto',
            'model': 'auto-tts',
            'prompt': '{text}',
            'text': '{text}',
            'voice': 'zh-CN-XiaoxiaoNeural',
            'language': 'zh',
        },
    )
    subtitle = reuse_or_make(
        'subtitle',
        'subtitle_generation',
        '字幕时间轴生成',
        finish_x0 + 520,
        finish_y,
        {
            'provider': 'local_whisper',
            'language': 'zh',
            'format': 'srt',
            'input_path': '{video_url}',
            'burn_in': False,
        },
    )
    burn = reuse_or_make(
        'burn',
        'subtitle_burn',
        '字幕烧录成片',
        finish_x0 + 780,
        finish_y,
        {
            'video_url': '{video_url}',
            'subtitle_url': '{subtitle_url}',
            'language': 'zh',
        },
    )
    packaging = reuse_or_make(
        'packaging',
        'llm',
        '成片包装文案',
        finish_x0 + 1040,
        finish_y,
        {
            'model': 'agnes-llm-v1',
            'temperature': 0.7,
            'max_tokens': 2048,
            'system_prompt': PACKAGING_SYSTEM,
            'user_template': '根据以下成片与旁白生成宣发包装JSON：\n{input}',
        },
    )
    output = reuse_or_make(
        'output',
        'output',
        '最终成片输出(展示)',
        finish_x0 + 1300,
        finish_y,
        {
            'format': 'json',
            'template': '{video_url}',
            'output_variable': 'final_film',
        },
    )
    end = reuse_or_make('end', 'end', '结束', finish_x0 + 1560, finish_y, {})

    nodes: List[Dict[str, Any]] = [
        start,
        inp,
        chapters,
        parse,
        collect,
        merge,
        narration,
        audio,
        subtitle,
        burn,
        packaging,
        output,
        end,
    ]
    for chain in chains:
        nodes.extend([chain['pick'], chain['image'], chain['video']])

    def sid(node: Dict[str, Any]) -> str:
        return str(node['id'])

    edges: List[Dict[str, Any]] = [
        _edge(sid(start), sid(inp)),
        _edge(sid(inp), sid(chapters)),
        _edge(sid(chapters), sid(parse)),
    ]
    for chain in chains:
        edges.append(_edge(sid(parse), sid(chain['pick'])))
        edges.append(_edge(sid(chain['pick']), sid(chain['image'])))
        edges.append(_edge(sid(chain['image']), sid(chain['video'])))
        edges.append(_edge(sid(chain['video']), sid(collect)))

    edges.extend(
        [
            _edge(sid(collect), sid(merge)),
            _edge(sid(merge), sid(narration)),
            _edge(sid(narration), sid(audio)),
            _edge(sid(merge), sid(subtitle)),
            _edge(sid(audio), sid(subtitle)),
            _edge(sid(subtitle), sid(burn)),
            _edge(sid(burn), sid(packaging)),
            _edge(sid(packaging), sid(output)),
            _edge(sid(output), sid(end)),
        ]
    )

    seen = set()
    deduped = []
    for e in edges:
        key = (e['source'], e['target'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    updated = {
        'id': workflow.get('id'),
        'name': f'武侠短剧·{shot_count}路并行分镜→1分钟成片',
        'description': (
            f'大输入接收章节内容 → 拆成{shot_count}条并行分镜链路（各自展示脚本/图/视频）→ '
            '汇总拼接旁白字幕，整合为约1分钟短剧成片'
        ),
        'nodes': nodes,
        'edges': deduped,
    }
    changes.append(f'重建为「章节大输入 → {shot_count}条并行分镜链路 → 汇总成片」')
    changes.append(
        f'节点 {len(nodes)} / 连线 {len(deduped)}（每镜：内容展示→关键帧→视频，再汇总成片）'
    )
    return updated, changes


def expand_to_production_pipeline(
    workflow: Dict[str, Any],
    *,
    shot_count: int = SHOT_COUNT,
) -> Tuple[Dict[str, Any], List[str]]:
    """Backward-compatible entry: prefer parallel-shot production graph."""
    return expand_to_parallel_shot_pipeline(workflow, shot_count=shot_count)


def _light_enrich_short_drama(
    workflow: Dict[str, Any],
    *,
    shot_count: int = SHOT_COUNT,
) -> Tuple[Dict[str, Any], List[str]]:
    return expand_to_parallel_shot_pipeline(workflow, shot_count=shot_count)


def enrich_short_drama_workflow(
    workflow: Dict[str, Any],
    *,
    shot_count: int = SHOT_COUNT,
) -> Tuple[Dict[str, Any], List[str]]:
    """Primary entry used by editor assistant."""
    try:
        return expand_to_parallel_shot_pipeline(workflow, shot_count=shot_count)
    except Exception:
        updated = copy.deepcopy(workflow)
        return updated, ['短剧 enrichment 扩展失败，已保留原图']
