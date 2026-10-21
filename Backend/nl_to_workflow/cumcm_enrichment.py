# -*- coding: utf-8 -*-
"""
CUMCM 全国大学生数学建模竞赛 — 完整工作流 enrichment / create template.

流水线：
  1) 赛题与数据输入（题目正文 + 附件/数据 JSON）
  2) 赛题解析、问题重述、子问题分解
  3) 数据预处理与描述性统计
  4) N 路子问题并行：模型建立 → 数值求解 → 结果分析
  5) 汇总 → 灵敏度分析 → 模型检验
  6) 论文分段撰写（摘要/重述/假设/建模/求解/分析/评价/参考文献）
  7) 组装 Markdown 论文并输出
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from nl_to_workflow.cumcm_prompts import (
    INTERPRET_SYSTEM,
    PROBLEM_ANALYSIS_SYSTEM,
    SENSITIVITY_SYSTEM,
    VALIDATION_SYSTEM,
    build_paper_section_specs,
    get_decompose_system,
    get_format_check_prompt,
    get_logic_adversarial_prompt,
    get_model_build_system,
    get_paper_section_prompt,
)
from nl_to_workflow.cumcm_run_config import (
    CumcmRunConfig,
    assert_strict_for_testing,
    get_testing_config,
)
from nl_to_workflow.cumcm_solvers import (
    build_chart_code,
    build_enhanced_preprocess_code,
    build_sensitivity_code,
    build_solver_code,
    build_table_figure_code,
)


SUBPROBLEM_COUNT = 3

_ENRICH_HINTS = (
    'cumcm',
    '数学建模',
    '建模竞赛',
    '全国大学生数学建模',
    '大学生数学建模',
    '数学建模竞赛',
    '国赛',
    '建模论文',
    '美赛',
    'mcm',
    'icm',
    'mathematical modeling contest',
    'math modeling',
    '灵敏度分析',
    '模型检验',
    '建模求解',
)

_STRONG_HINTS = (
    'cumcm',
    '全国大学生数学建模',
    '大学生数学建模竞赛',
    '数学建模竞赛',
    '国赛数学建模',
    'mcm/icm',
)


def is_cumcm_intent(message: str) -> bool:
    text = (message or '').lower()
    if any(h in text for h in _STRONG_HINTS):
        return True
    if '数学建模' in text and any(k in text for k in ('竞赛', '国赛', '论文', '求解', 'cumcm')):
        return True
    if '建模' in text and any(k in text for k in ('竞赛', '国赛', 'cumcm', '论文', '灵敏度')):
        return True
    return any(h in text for h in _ENRICH_HINTS if h in ('cumcm', 'mathematical modeling contest', 'math modeling'))


def is_cumcm_enrich_intent(message: str) -> bool:
    return is_cumcm_intent(message)


# 2025 高教社杯 CUMCM A题《烟幕干扰弹的投放策略》— 完整题面（供 agent 自行建模）
_A_PROBLEM_FULL_TEXT = """2025年高教社杯全国大学生数学建模竞赛题目
A题 烟幕干扰弹的投放策略

烟幕干扰弹主要通过化学燃烧或爆炸分散形成烟幕或气溶胶云团，在目标前方特定空域形成遮蔽，干扰敌方导弹，具有成本低、效费比高等优点。随着烟幕干扰技术的不断发展，现已有多种投放方式完成烟幕干扰弹的定点精确抛撒，即在抛撒前能精确控制烟幕干扰弹到达预定位置，通过时间引信时序控制起爆时间。

现考虑运用无人机完成烟幕干扰弹的投放策略问题。具有长续航能力的无人机挂载某型烟幕干扰弹在特定空域巡飞，受领任务后，无人机投放烟幕干扰弹在来袭武器和保护目标之间形成烟幕遮蔽。每架无人机投放两枚烟幕干扰弹至少间隔1 s。烟幕干扰弹脱离无人机后，在重力作用下运动。烟幕干扰弹起爆后瞬时形成球状烟幕云团，由于采用特定技术，该烟幕云团以3 m/s的速度匀速下沉。据试验数据知，云团中心10 m范围内的烟幕浓度在起爆20 s内可为目标提供有效遮蔽。

来袭武器为空地导弹，该型导弹飞行速度300 m/s。导弹的飞行方向直指一个为掩护某半径7 m、高10 m的圆柱形固定目标而专门设置的假目标。以假目标为原点，水平面为xy平面，真目标下底面的圆心为(0,200,0)。警戒雷达发现来袭导弹时，3枚导弹M1、M2、M3分别位于(20000,0,2000)、(19000,600,2100)、(18000,-600,1900)；5架无人机的位置信息分别为FY1(17800,0,1800)、FY2(12000,1400,1400)、FY3(6000,-3000,700)、FY4(11000,2000,1800)、FY5(13000,-2000,1300)。

在导弹来袭过程中，通过投放烟幕干扰弹尽量避免来袭导弹发现真目标。控制中心在警戒雷达发现目标时，立即向无人机指派任务。无人机受领任务后，可根据需要瞬时调整飞行方向，然后以70~140 m/s的速度等高度匀速直线飞行。每架无人机的航向、速度可不相同，但一旦确定就不再调整。

为实现更为有效的烟幕干扰效果，需设计烟幕干扰弹的投放策略，主要包括无人机飞行方向、飞行速度、烟幕干扰弹投放点、烟幕干扰弹起爆点等。请建立数学模型，针对不同情形，分别设计烟幕干扰弹的投放策略，使得多枚烟幕干扰弹对真目标的有效遮蔽时间尽可能长。不同烟幕干扰弹的遮蔽可不连续。

问题1 利用无人机FY1投放1枚烟幕干扰弹实施对M1的干扰，若FY1以120 m/s的速度朝向假目标方向飞行，受领任务1.5 s后即投放1枚烟幕干扰弹，间隔3.6 s后起爆。请给出烟幕干扰弹对M1的有效遮蔽时长。

问题2 利用无人机FY1投放1枚烟幕干扰弹实施对M1的干扰，确定FY1的飞行方向、飞行速度、烟幕干扰弹投放点、烟幕干扰弹起爆点，使得遮蔽时间尽可能长。

问题3 利用无人机FY1投放3枚烟幕干扰弹，实施对M1的干扰。请给出烟幕干扰弹的投放策略，并将结果保存到文件result1.xlsx中（模板文件见附件）。

问题4 利用FY1、FY2、FY3等3架无人机，各投放1枚烟幕干扰弹，实施对M1的干扰。请给出烟幕干扰弹的投放策略，并将结果保存到文件result2.xlsx中（模板文件见附件）。

问题5 利用5架无人机，每架无人机至多投放3枚烟幕干扰弹，实施对M1、M2、M3等3枚来袭导弹的干扰。请给出烟幕干扰弹的投放策略，并将结果保存到文件result3.xlsx中（模板文件见附件）。
"""

_PROBLEM_A_2025 = {
    'contest': 'CUMCM',
    'year': 2025,
    'problem_id': 'A',
    'title': '烟幕干扰弹的投放策略',
    'problem_text': _A_PROBLEM_FULL_TEXT,
    'source': 'Docs/2025年/A题 — 高教社杯全国大学生数学建模竞赛',
    'agent_instruction': (
        '请以国赛参赛队身份完成本题：先解析题意与参数，再按问题1~5递进建模；'
        '模型建立节点须输出可执行的 solver_type + parameters；'
        '数值求解节点将自动调用 numpy/scipy；论文节点输出完整 Markdown/Word。'
        'solver_hints 仅作兜底，优先采用你根据题面推导的参数。'
    ),
    'subproblem_hints': [
        '问题1：固定策略下FY1单弹对M1的有效遮蔽时长（运动学+几何遮蔽判定）',
        '问题2：优化FY1航向、速度、投放/起爆时机，最大化对M1遮蔽时长',
        '问题3：FY1投放3枚弹协同干扰M1（投放间隔≥1s），输出result1.xlsx',
        '问题4：FY1/FY2/FY3各1枚弹协同干扰M1，输出result2.xlsx',
        '问题5：5架无人机×至多3弹对M1/M2/M3综合干扰，输出result3.xlsx',
    ],
    # solver_hints：仅当 LLM 未给出可执行 parameters 时由数值节点兜底
    'solver_hints': [
        {
            'subproblem_index': 1,
            'solver_type': 'time_series',
            'parameters': {
                'series': [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                'forecast_steps': 5,
                'window': 3,
            },
        },
        {
            'subproblem_index': 2,
            'solver_type': 'monte_carlo',
            'parameters': {
                'baseline': {
                    'heading_rad': 3.14, 'speed': 120.0,
                    't_drop': 1.5, 't_fuse': 3.6,
                },
                'coefficients': {
                    'heading_rad': 0.2, 'speed': 0.08,
                    't_drop': 0.4, 't_fuse': 0.3,
                },
                'n_simulations': 400,
                'noise_std': 0.1,
                'seed': 2025,
            },
        },
        {
            'subproblem_index': 3,
            'solver_type': 'monte_carlo',
            'parameters': {
                'baseline': {
                    't_drop1': 1.5, 't_drop2': 3.0, 't_drop3': 5.0,
                    'fuse1': 3.6, 'fuse2': 3.6, 'fuse3': 3.6,
                    'speed': 120.0,
                },
                'coefficients': {
                    't_drop1': 0.2, 't_drop2': 0.2, 't_drop3': 0.2,
                    'fuse1': 0.15, 'fuse2': 0.15, 'fuse3': 0.15,
                    'speed': 0.05,
                },
                'n_simulations': 400,
                'noise_std': 0.1,
                'seed': 42,
            },
        },
        {
            'subproblem_index': 4,
            'solver_type': 'regression',
            'parameters': {
                'x': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
                'y': [0.8, 1.5, 2.1, 2.4, 2.2, 1.9, 1.4],
                'degree': 2,
            },
        },
        {
            'subproblem_index': 5,
            'solver_type': 'monte_carlo',
            'parameters': {
                'baseline': {
                    'assign_m1': 2, 'assign_m2': 2, 'assign_m3': 1,
                    'bombs_per_uav': 2, 'avg_cover': 3.5,
                },
                'coefficients': {
                    'assign_m1': 0.5, 'assign_m2': 0.5, 'assign_m3': 0.5,
                    'bombs_per_uav': 0.3, 'avg_cover': 1.0,
                },
                'n_simulations': 500,
                'noise_std': 0.12,
                'seed': 2025,
            },
        },
    ],
    'data': {
        'fake_target': [0, 0, 0],
        'true_target_center': [0, 200, 0],
        'true_target_radius': 7,
        'true_target_height': 10,
        'missile_speed': 300,
        'smoke_sink_speed': 3,
        'smoke_radius': 10,
        'smoke_valid_seconds': 20,
        'uav_speed_min': 70,
        'uav_speed_max': 140,
        'min_drop_interval': 1,
        'g': 9.8,
        'missiles': {
            'M1': [20000, 0, 2000],
            'M2': [19000, 600, 2100],
            'M3': [18000, -600, 1900],
        },
        'uavs': {
            'FY1': [17800, 0, 1800],
            'FY2': [12000, 1400, 1400],
            'FY3': [6000, -3000, 700],
            'FY4': [11000, 2000, 1800],
            'FY5': [13000, -2000, 1300],
        },
        'problem1_fixed': {
            'uav': 'FY1',
            'missile': 'M1',
            'speed': 120,
            'heading': 'toward_fake_target',
            't_drop': 1.5,
            't_fuse': 3.6,
            'reference_cover_time_s': 1.5,
            'm1_arrival_time_s': 67.0,
        },
        'missile_x': [20000, 19000, 18000],
        'missile_y': [0, 600, -600],
        'missile_z': [2000, 2100, 1900],
        'uav_x': [17800, 12000, 6000, 11000, 13000],
        'uav_y': [0, 1400, -3000, 2000, -2000],
        'uav_z': [1800, 1400, 700, 1800, 1300],
        'q1_cover_interval': [8.0, 9.5],
        'notes': '完整题面已写入 problem_text；请 agent 优先按题面建模，solver_hints 仅兜底。',
    },
    'attachments': [],
    'team_info': {'school': '', 'members': [], 'advisor': ''},
}

DEFAULT_INPUT = (
    "【已上传赛题】2025 高教社杯 CUMCM A题《烟幕干扰弹的投放策略》\n"
    "请工作流中的 Agent 按下列 JSON（含完整 problem_text）自行解析、分解、建模、求解并撰写论文。\n\n"
    + json.dumps(_PROBLEM_A_2025, ensure_ascii=False, indent=2)
)


DATA_PREPROCESS_CODE = build_enhanced_preprocess_code()

# Legacy alias kept for tests referencing module-level name
SOLVER_CODE_TEMPLATE = build_solver_code(1)

COLLECT_SUBPROBLEMS_CODE = r'''
import json
import re


def _loose_json(s):
    """Best-effort parse of LLM JSON: never raises, returns dict or None."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip().strip('`').replace('```json', '').replace('```', '')
    candidates = []
    if '{' in s:
        candidates.append(s[s.find('{'):s.rfind('}') + 1])
    m = re.search(r'\{.*\}', s, re.S)
    if m:
        candidates.append(m.group(0))
    candidates.append(s)
    for cand in candidates:
        for fix in (cand, re.sub(r',\s*([}\]])', r'\1', cand)):
            try:
                obj = json.loads(fix)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        # 截到最后一个可平衡的右括号再试（应对尾部截断）
        depth = 0
        last_ok = -1
        for i, ch in enumerate(cand):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    last_ok = i
        if last_ok > 0:
            try:
                obj = json.loads(re.sub(r',\s*([}\]])', r'\1', cand[:last_ok + 1]))
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
    return None


raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

items = []
parse_failures = []
for nid, out in nos.items():
    if not isinstance(out, dict):
        continue
    t = out.get('text') or ''
    if not isinstance(t, str):
        continue
    obj = _loose_json(t)
    if isinstance(obj, dict) and obj.get('subproblem_index') is not None:
        items.append(obj)
    elif obj is None and 'subproblem_index' in t:
        parse_failures.append(str(out.get('label') or nid))

items.sort(key=lambda x: int(x.get('subproblem_index') or 0))
output = {
    'subproblem_results': items,
    'count': len(items),
    'parse_failures': parse_failures,
    'text': json.dumps({'subproblem_results': items, 'parse_failures': parse_failures}, ensure_ascii=False),
}
'''

SENSITIVITY_NUMERIC_CODE = build_sensitivity_code()
CHART_GENERATION_CODE = build_chart_code(palette='bw')
TABLE_FIGURE_CODE = build_table_figure_code()

PAPER_SECTIONS = build_paper_section_specs(get_testing_config())

MERGE_PAPER_CODE = r'''
import json
import re
from datetime import datetime

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

sections = {}
order = [
    ('abstract', '## 摘要'),
    ('restatement', '## 一、问题重述'),
    ('analysis', '## 二、问题分析'),
    ('assumptions', '## 三、模型假设与符号说明'),
    ('tech_route', '## 技术路线'),
    ('method_compare', '## 候选方法对比'),
    ('modeling', '## 四、模型建立与求解'),
    ('results', '## 五、结果分析'),
    ('evaluation', '## 六、模型评价'),
    ('references', '## 参考文献'),
    ('ai_declaration', '## AI工具使用声明'),
]

keywords = {
    'abstract': ('摘要',),
    'restatement': ('问题重述',),
    'analysis': ('问题分析',),
    'assumptions': ('模型假设', '符号说明'),
    'tech_route': ('技术路线',),
    'method_compare': ('候选方法', '方法对比'),
    'modeling': ('模型建立', '建立与求解'),
    'results': ('结果分析',),
    'evaluation': ('模型评价',),
    'references': ('参考文献',),
    'ai_declaration': ('AI工具', 'AI 工具'),
}

def _strip_heading(text, heading):
    t = (text or '').strip()
    h = heading.lstrip('#').strip()
    if t.startswith('##'):
        first = t.split('\n', 1)[0].strip().lstrip('#').strip()
        if h in first or first in h:
            t = t.split('\n', 1)[1] if '\n' in t else ''
    return t.strip()

for key, kws in keywords.items():
    for out in nos.values():
        if not isinstance(out, dict):
            continue
        label = str(out.get('label') or out.get('name') or '')
        t = out.get('text') or out.get('content') or ''
        if any(kw in label for kw in kws) and isinstance(t, str) and len(t.strip()) > 20:
            sections[key] = _strip_heading(t.strip(), order[[x[0] for x in order].index(key)][1])
            break

for out in nos.values():
    if not isinstance(out, dict):
        continue
    label = str(out.get('label') or out.get('name') or '')
    t = out.get('text') or ''
    if '灵敏度' in label and isinstance(t, str) and t.strip():
        sections['sensitivity'] = t.strip()
    if '模型检验' in label and isinstance(t, str) and t.strip():
        sections['validation'] = t.strip()

title = 'CUMCM 数学建模论文'
for out in nos.values():
    if not isinstance(out, dict):
        continue
    t = out.get('text') or out.get('content') or ''
    if not isinstance(t, str) or 'problem_text' not in t:
        continue
    try:
        obj = json.loads(t[t.find('{'):t.rfind('}') + 1])
    except Exception:
        obj = None
    if isinstance(obj, dict):
        title = str(obj.get('title') or title).strip() or title
        break

sub_rows = []
table_md = ''
for out in nos.values():
    if not isinstance(out, dict):
        continue
    label = str(out.get('label') or out.get('name') or '')
    if '三线表' in label or 'TABLE' in label or '表格' in label:
        t = out.get('text') or out.get('table_markdown') or ''
        if isinstance(t, str) and '|' in t and len(t.strip()) > 30:
            table_md = t.strip()
            break
        try:
            obj = json.loads(t[t.find('{'):t.rfind('}') + 1] if '{' in t else t)
            if isinstance(obj, dict) and obj.get('table_markdown'):
                table_md = obj['table_markdown']
                break
        except Exception:
            pass

if not table_md:
    for out in nos.values():
        if not isinstance(out, dict):
            continue
        label = str(out.get('label') or out.get('name') or '')
        if '汇总' not in label:
            continue
        t = out.get('text') or ''
        try:
            obj = json.loads(t[t.find('{'):t.rfind('}') + 1] if '{' in t else t)
        except Exception:
            obj = None
        if isinstance(obj, dict):
            for item in obj.get('subproblem_results') or []:
                if not isinstance(item, dict):
                    continue
                idx = item.get('subproblem_index')
                st = item.get('solver_type') or item.get('model_type') or '-'
                comp = item.get('computed') if isinstance(item.get('computed'), dict) else {}
                ov = comp.get('objective_value')
                ov_s = f'{ov:.4g}' if isinstance(ov, (int, float)) else str(ov or '-')
                sub_rows.append((idx, st, ov_s, item.get('status') or 'ok'))

    if sub_rows:
        sub_rows.sort(key=lambda r: int(r[0] or 0))
        lines = ['**表 1 子问题求解汇总**', '', '| 子问题 | 求解类型 | 目标值/指标 | 状态 |', '|---|---|---|---|']
        for idx, st, ov, status in sub_rows:
            lines.append(f'| 问{idx} | {st} | {ov} | {status} |')
        table_md = '\n'.join(lines)

chart_md = []
for out in nos.values():
    if not isinstance(out, dict):
        continue
    label = str(out.get('label') or out.get('name') or '')
    if '图表' not in label:
        continue
    t = out.get('text') or ''
    try:
        obj = json.loads(t[t.find('{'):t.rfind('}') + 1] if '{' in t else t)
    except Exception:
        obj = None
    if isinstance(obj, dict):
        for md in obj.get('markdown_embeds') or []:
            if isinstance(md, str) and md.strip():
                chart_md.append(md.strip())
    embeds = out.get('markdown_embeds')
    if isinstance(embeds, list):
        for md in embeds:
            if isinstance(md, str) and md.strip():
                chart_md.append(md.strip())

parts = [f'# {title}\n', f'> 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}\n']
for key, heading in order:
    body = sections.get(key, '（待补充）')
    parts.append(f'\n{heading}\n\n{body}\n')
    if key == 'results' and table_md:
        parts.append(f'\n{table_md}\n')
    if key == 'modeling' and chart_md:
        parts.append('\n### 模型结果图表\n\n')
        parts.extend(md + '\n\n' for md in chart_md)

if sections.get('sensitivity'):
    parts.append(f'\n## 附录 A 灵敏度分析\n\n{sections["sensitivity"]}\n')
if sections.get('validation'):
    parts.append(f'\n## 附录 B 模型检验\n\n{sections["validation"]}\n')

if chart_md and not any('模型结果图表' in p for p in parts):
    parts.append('\n## 附录 C 模型图表\n\n')
    parts.extend(md + '\n\n' for md in chart_md)

markdown = ''.join(parts)
output = {
    'format': 'markdown',
    'content': markdown,
    'text': markdown,
    'table_markdown': table_md,
    'section_count': len([k for k in sections if sections[k]]),
}
'''


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


def _llm_node(
    name: str,
    x: float,
    y: float,
    system_prompt: str,
    user_template: str,
    *,
    temperature: float = 0.35,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    return _make_node(
        'llm',
        name,
        x,
        y,
        {
            'provider': 'agnes',
            'model': 'agnes-2.0-flash',
            'temperature': temperature,
            'max_tokens': max_tokens,
            'system_prompt': system_prompt,
            'systemPrompt': system_prompt,
            'user_template': user_template,
            'userTemplate': user_template,
            'input_variable': 'text',
            'retry_count': 2,
            'max_retries': 3,
            'timeout': 180,
        },
    )


def _pick_subproblem_code(index: int) -> str:
    return f'''
import json
import re

idx = {index}
raw = input if isinstance(input, dict) else {{}}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {{}}

text = ''
for out in nos.values():
    if not isinstance(out, dict):
        continue
    t = out.get('text') or ''
    if isinstance(t, str) and 'subproblems' in t:
        text = t
        break

item = {{'index': idx, 'title': f'子问题{{idx}}', 'description': ''}}
if text:
    s = text.strip().strip('`').replace('```json', '').replace('```', '')
    try:
        obj = json.loads(s[s.find('{{'):s.rfind('}}') + 1] if '{{' in s else s)
        subs = obj.get('subproblems') if isinstance(obj, dict) else []
        for sp in subs or []:
            if isinstance(sp, dict) and int(sp.get('index') or 0) == idx:
                item = sp
                break
        if not item.get('description') and isinstance(subs, list) and len(subs) >= idx:
            cand = subs[idx - 1]
            if isinstance(cand, dict):
                item = cand
    except Exception:
        pass

# Fallback: use subproblem_hints / solver_hints from original contest JSON
if not (item.get('description') or '').strip():
    problem = None
    for key in ('input', 'text', 'user_input', 'prompt'):
        val = raw.get(key)
        if isinstance(val, str) and '{{' in val:
            try:
                problem = json.loads(val[val.find('{{'):val.rfind('}}') + 1])
                break
            except Exception:
                pass
    if problem is None:
        for out in nos.values():
            if not isinstance(out, dict):
                continue
            for key in ('text', 'input', 'user_input', 'prompt'):
                t = out.get(key) or ''
                if isinstance(t, str) and 'subproblem_hints' in t:
                    try:
                        problem = json.loads(t[t.find('{{'):t.rfind('}}') + 1])
                        break
                    except Exception:
                        pass
            if problem:
                break
    if isinstance(problem, dict):
        hints = problem.get('subproblem_hints') or []
        if isinstance(hints, list) and len(hints) >= idx:
            desc = hints[idx - 1]
            if isinstance(desc, str) and desc.strip():
                item['description'] = desc.strip()
                item['title'] = item.get('title') or f'子问题{{idx}}'
        for h in problem.get('solver_hints') or []:
            if isinstance(h, dict) and int(h.get('subproblem_index') or 0) == idx:
                item['solver_type'] = h.get('solver_type')
                item['parameters'] = h.get('parameters')
                break

output = {{
    'subproblem_index': idx,
    'subproblem': item,
    'text': json.dumps(item, ensure_ascii=False),
}}
'''


def expand_cumcm_pipeline(
    workflow: Optional[Dict[str, Any]] = None,
    *,
    subproblem_count: int = SUBPROBLEM_COUNT,
    run_config: Optional[CumcmRunConfig] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Build full CUMCM 数学建模 graph.

    run_config: 对标出稿产品旋钮（审查/丰满度/黑白图/逻辑对抗/AI声明等）。
    """
    cfg = run_config or get_testing_config()
    # 测试默认路径强制最严格；显式传入 fast 等预设时不拦截
    if run_config is None:
        assert_strict_for_testing(cfg)
    subproblem_count = max(2, min(int(subproblem_count or SUBPROBLEM_COUNT), 5))
    changes: List[str] = []
    paper_specs = build_paper_section_specs(cfg)
    chart_code = build_chart_code(palette=cfg.chart_palette)

    start = _make_node('start', '开始', 80, 400)
    inp = _make_node(
        'input',
        '赛题与数据输入',
        280,
        400,
        {
            'input_type': 'text',
            'variable_name': 'input',
            'label': 'CUMCM 题目与数据(JSON)',
            'default_value': DEFAULT_INPUT,
            'placeholder': '粘贴赛题正文、数据与附件信息(JSON)',
            'run_config': cfg.to_dict(),
        },
    )

    problem_analysis = _llm_node(
        '赛题解析',
        560,
        400,
        PROBLEM_ANALYSIS_SYSTEM,
        '请解析以下 CUMCM 赛题输入，输出纯 JSON：\n{input}',
        temperature=0.25,
        max_tokens=1800,
    )

    decompose = _llm_node(
        '子问题分解',
        860,
        400,
        get_decompose_system(subproblem_count, cfg),
        (
            '基于赛题输入与下列分析结果，输出 {count} 个子问题的分解 JSON；'
            '每问至少 {n} 个候选模型：\n{{input}}'
        ).format(count=subproblem_count, n=cfg.min_models_per_subproblem),
        temperature=0.35,
        max_tokens=2200,
    )

    data_preprocess = _make_node(
        'code',
        '数据预处理与统计',
        1160,
        400,
        {
            'code': DATA_PREPROCESS_CODE,
            'language': 'python',
            'timeout': 60,
            'max_memory_mb': 512,
        },
    )

    # Parallel sub-problem chains
    sub_chains = []
    y0 = 60
    gap = 200
    for i in range(1, subproblem_count + 1):
        y = y0 + (i - 1) * gap
        pick = _make_node(
            'code',
            f'提取子问题{i}',
            1460,
            y,
            {'code': _pick_subproblem_code(i), 'language': 'python', 'timeout': 30, 'max_memory_mb': 256},
        )
        model_build = _llm_node(
            f'模型建立·问{i}',
            1760,
            y,
            get_model_build_system(cfg),
            (
                f'这是当前赛题的子问题 {i}。\n'
                f'请阅读上游输入中的完整 problem_text 与 data，针对该子问题建立数学模型，'
                f'输出纯 JSON（subproblem_index={i}）。优先自行推导 parameters：\n{{input}}'
            ),
            temperature=0.35,
            max_tokens=2800,
        )
        solver = _make_node(
            'code',
            f'数值求解·问{i}',
            2060,
            y,
            {
                'code': build_solver_code(i),
                'language': 'python',
                'timeout': 90,
                'max_memory_mb': 512,
            },
        )
        interpret = _llm_node(
            f'结果分析·问{i}',
            2360,
            y,
            INTERPRET_SYSTEM,
            '请撰写该子问题的结果分析：\n{input}',
            temperature=0.45,
            max_tokens=1200,
        )
        sub_chains.append({'pick': pick, 'model': model_build, 'solver': solver, 'interpret': interpret})

    collect = _make_node(
        'code',
        '汇总子问题结果',
        2660,
        400,
        {'code': COLLECT_SUBPROBLEMS_CODE, 'language': 'python'},
    )

    chart_gen = _make_node(
        'code',
        '自动生成模型图表',
        2960,
        400,
        {
            'code': chart_code,
            'language': 'python',
            'timeout': 90,
            'max_memory_mb': 512,
        },
    )

    table_figure = _make_node(
        'code',
        '生成结果三线表',
        2960,
        520,
        {'code': TABLE_FIGURE_CODE, 'language': 'python', 'timeout': 60, 'max_memory_mb': 256},
    )

    sensitivity_numeric = _make_node(
        'code',
        '数值灵敏度计算',
        3260,
        400,
        {
            'code': SENSITIVITY_NUMERIC_CODE,
            'language': 'python',
            'timeout': 90,
            'max_memory_mb': 512,
        },
    )

    sensitivity = _llm_node(
        '灵敏度分析',
        3560,
        320,
        SENSITIVITY_SYSTEM,
        '请基于下列数值灵敏度结果与各子问题汇总，撰写灵敏度分析章节：\n{input}',
        temperature=0.4,
        max_tokens=1200,
    )

    validation = _llm_node(
        '模型检验',
        3560,
        480,
        VALIDATION_SYSTEM,
        '请基于模型与结果撰写模型检验：\n{input}',
        temperature=0.4,
        max_tokens=1200,
    )

    logic_review = None
    if cfg.logic_adversarial_review:
        logic_review = _llm_node(
            '逻辑对抗复核',
            3710,
            400,
            get_logic_adversarial_prompt(cfg),
            (
                '编程后、写论文前：独立挑错（方向反/重复计量/外推过硬/漏变量/跨问矛盾/任务读歪）。'
                '输出纯 JSON：\n{input}'
            ),
            temperature=0.2,
            max_tokens=2000,
        )

    # Paper writing chain (sequential) — driven by run_config section catalog
    paper_nodes: List[Dict[str, Any]] = []
    px = 3860
    py = 80
    for idx, (key, title, prompt) in enumerate(paper_specs):
        tokens = 2200 if cfg.richness == 'rich' else 1500
        if key == 'references':
            tokens = 1400 if cfg.richness == 'rich' else 1000
        if key == 'ai_declaration':
            tokens = 600
        node = _llm_node(
            title,
            px,
            py + idx * 110,
            get_paper_section_prompt(title, prompt, cfg),
            '请结合上游赛题、模型、求解结果、逻辑复核与图表信息撰写本章节：\n{input}',
            temperature=0.45,
            max_tokens=tokens,
        )
        paper_nodes.append(node)

    merge_paper = _make_node(
        'code',
        '组装论文Markdown',
        4160,
        400,
        {'code': MERGE_PAPER_CODE, 'language': 'python'},
    )

    fmt_tokens = 8000 if cfg.review_mode == 'strict' else 4000
    format_check = _llm_node(
        '论文格式自检',
        4310,
        400,
        get_format_check_prompt(cfg),
        '请审查并修正下列 paper/main.md 草稿（docx-format-check），输出完整 Markdown 正文：\n{input}',
        temperature=0.2,
        max_tokens=fmt_tokens,
    )

    file_writer = _make_node(
        'file_writer',
        '保存论文文件',
        4460,
        400,
        {
            'path': 'paper/main.md',
            'content': '{content}',
            'format': 'text',
        },
    )

    table_writer = _make_node(
        'file_writer',
        '保存结果表格',
        4460,
        520,
        {
            'path': 'figures/TABLE_summary.md',
            'content': '{table_markdown}',
            'format': 'text',
        },
    )

    docx_writer = _make_node(
        'file_writer',
        '导出Word论文',
        4460,
        640,
        {
            'path': 'paper/main.docx',
            'content': '{content}',
            'format': 'docx',
        },
    )

    output = _make_node(
        'output',
        '输出建模成果',
        4760,
        400,
        {
            'output_variable': 'result',
            'format': 'json',
        },
    )
    end = _make_node('end', '结束', 5060, 400)

    nodes: List[Dict[str, Any]] = [
        start,
        inp,
        problem_analysis,
        decompose,
        data_preprocess,
        collect,
        chart_gen,
        table_figure,
        sensitivity_numeric,
        sensitivity,
        validation,
        merge_paper,
        format_check,
        file_writer,
        table_writer,
        docx_writer,
        output,
        end,
    ]
    if logic_review is not None:
        nodes.append(logic_review)
    for c in sub_chains:
        nodes.extend([c['pick'], c['model'], c['solver'], c['interpret']])
    nodes.extend(paper_nodes)

    def sid(n: Dict[str, Any]) -> str:
        return str(n['id'])

    edges: List[Dict[str, Any]] = [
        _edge(sid(start), sid(inp)),
        _edge(sid(inp), sid(problem_analysis)),
        _edge(sid(problem_analysis), sid(decompose)),
        _edge(sid(inp), sid(data_preprocess)),
        _edge(sid(decompose), sid(data_preprocess)),
    ]

    for c in sub_chains:
        edges.append(_edge(sid(data_preprocess), sid(c['pick'])))
        edges.append(_edge(sid(decompose), sid(c['pick'])))
        edges.append(_edge(sid(c['pick']), sid(c['model'])))
        edges.append(_edge(sid(c['model']), sid(c['solver'])))
        edges.append(_edge(sid(c['solver']), sid(c['interpret'])))
        edges.append(_edge(sid(c['interpret']), sid(collect)))

    edges.extend([
        _edge(sid(collect), sid(chart_gen)),
        _edge(sid(collect), sid(table_figure)),
        _edge(sid(collect), sid(sensitivity_numeric)),
        _edge(sid(collect), sid(sensitivity)),
        _edge(sid(collect), sid(validation)),
        _edge(sid(chart_gen), sid(merge_paper)),
        _edge(sid(table_figure), sid(merge_paper)),
        _edge(sid(sensitivity_numeric), sid(sensitivity)),
    ])

    # Paper chain: validation + sensitivity (+ optional logic review) → paper sections
    if paper_nodes:
        edges.append(_edge(sid(collect), sid(paper_nodes[0])))
        edges.append(_edge(sid(sensitivity), sid(paper_nodes[0])))
        edges.append(_edge(sid(validation), sid(paper_nodes[0])))
        if logic_review is not None:
            edges.append(_edge(sid(collect), sid(logic_review)))
            edges.append(_edge(sid(validation), sid(logic_review)))
            edges.append(_edge(sid(sensitivity), sid(logic_review)))
            edges.append(_edge(sid(logic_review), sid(paper_nodes[0])))
        for i in range(len(paper_nodes) - 1):
            edges.append(_edge(sid(paper_nodes[i]), sid(paper_nodes[i + 1])))
        edges.append(_edge(sid(paper_nodes[-1]), sid(merge_paper)))
    else:
        edges.append(_edge(sid(validation), sid(merge_paper)))

    edges.extend([
        _edge(sid(collect), sid(merge_paper)),
        _edge(sid(merge_paper), sid(format_check)),
        _edge(sid(format_check), sid(file_writer)),
        _edge(sid(format_check), sid(table_writer)),
        _edge(sid(format_check), sid(docx_writer)),
        _edge(sid(format_check), sid(output)),
        _edge(sid(file_writer), sid(output)),
        _edge(sid(table_writer), sid(output)),
        _edge(sid(docx_writer), sid(output)),
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
        'name': base_name or 'CUMCM 全国大学生数学建模·完整流水线',
        'description': (
            f'赛题解析 → 子问题分解({subproblem_count}问) → 数据预处理 → '
            f'并行建模求解 → 图表({cfg.chart_palette})/三线表 → 灵敏度/检验'
            + (' → 逻辑对抗复核' if cfg.logic_adversarial_review else '')
            + f' → 论文{len(paper_specs)}章节({cfg.richness}/{cfg.review_mode})'
            + f' → 格式自检 → Markdown/Word'
            + f' · 正文约{cfg.page_limit_body}页'
        ),
        '_cumcm_run_config': cfg.to_dict(),
        'nodes': nodes,
        'edges': deduped,
        '_generation_mode': 'template_cumcm',
        '_is_intelligent': True,
    }
    changes.append(
        f'重建为 CUMCM 完整流水线：{subproblem_count} 路并行 + 论文{len(paper_specs)}章节'
        f'（{cfg.contest}/{cfg.richness}/{cfg.review_mode}/palette={cfg.chart_palette}）'
    )
    changes.append(f'节点 {len(nodes)} / 连线 {len(deduped)}')
    return updated, changes


def enrich_cumcm_workflow(
    workflow: Optional[Dict[str, Any]],
    *,
    subproblem_count: int = SUBPROBLEM_COUNT,
    run_config: Optional[CumcmRunConfig] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    return expand_cumcm_pipeline(
        workflow, subproblem_count=subproblem_count, run_config=run_config
    )


def build_cumcm_workflow(
    description: str = '',
    *,
    subproblem_count: int = SUBPROBLEM_COUNT,
    run_config: Optional[CumcmRunConfig] = None,
) -> Dict[str, Any]:
    """NL create-template entry (from scratch)."""
    wf, _ = expand_cumcm_pipeline(
        None, subproblem_count=subproblem_count, run_config=run_config
    )
    if description:
        wf['description'] = (wf.get('description') or '') + f'\n用户需求：{description[:800]}'
    return wf
