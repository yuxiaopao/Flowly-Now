# -*- coding: utf-8 -*-
"""
CUMCM 数学建模 — 集中式 Prompt 管理。

整合项目根目录 prompts/ 下的学术写作规范（docx、公式、图表、表格），
并为工作流各 LLM 节点提供版本化 system prompt。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from nl_to_workflow.cumcm_run_config import (
    CumcmRunConfig,
    LOGIC_ADVERSARIAL_SYSTEM,
    build_run_config_prompt_block,
    default_cumcm_config,
    paper_section_keys,
    section_length_hint,
)
from nl_to_workflow.cumcm_solvers import solver_catalog_for_prompt


# ---------------------------------------------------------------------------
# Prompt file loader (prompts/ at repo root)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPTS_DIR = _REPO_ROOT / 'prompts'
_CUMCM_PACK_DIR = _REPO_ROOT / 'Docs' / 'cumcm-full'
_CUMCM_PROMPTS_DIR = _CUMCM_PACK_DIR / 'prompts'
_FORMAT_REFERENCE = _CUMCM_PACK_DIR / 'format-reference' / 'reference_structure_comp_cumcm.md'


@lru_cache(maxsize=32)
def load_prompt_file(name: str) -> str:
    """Load markdown prompt from cumcm-full pack first, then repo prompts/."""
    for base in (_CUMCM_PROMPTS_DIR, _PROMPTS_DIR):
        path = base / name
        if path.is_file():
            return path.read_text(encoding='utf-8').strip()
    return ''


@lru_cache(maxsize=1)
def load_format_reference() -> str:
    if _FORMAT_REFERENCE.is_file():
        return _FORMAT_REFERENCE.read_text(encoding='utf-8').strip()
    return ''


def _compose_paper_writing_rules() -> str:
    """Merge docx + traps + figure language + table rules + format reference."""
    parts = [
        load_prompt_file('docx_write_markdown.md'),
        load_prompt_file('academic_docx_traps.md'),
        load_prompt_file('paper_figure_lang_zh.md'),
        load_prompt_file('course_docx_table_md.md'),
        load_prompt_file('course_docx_png_only.md'),
        load_format_reference(),
    ]
    return '\n\n---\n\n'.join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Pipeline node prompts (used by cumcm_enrichment.py)
# ---------------------------------------------------------------------------

PROBLEM_ANALYSIS_SYSTEM = (
    "你是 CUMCM comp-prob-analysis 阶段专家（对标 Modex 国赛流水线）。"
    "根据赛题 JSON，输出纯 JSON（禁止 Markdown），字段："
    "problem_restatement(中文问题重述，200字内)；"
    "problem_background(问题背景，150字内)；"
    "key_variables(数组，每项含 symbol/name/unit/meaning)；"
    "problem_type(如优化/评价/预测/机理/混合)；"
    "data_summary(已有数据与缺失数据说明)；"
    "assumptions(数组，3-8条合理假设)；"
    "overall_strategy(整体建模路线，150字内)；"
    "analysis_outline(问题分析要点，数组，3-6条)；"
    "recommended_solvers(数组，每项含 subproblem_index, solver_type, rationale, parameters)。"
    "parameters 须可直接用于下游 scipy 求解；"
    "solver_type 取值参考：" + solver_catalog_for_prompt()
)

DECOMPOSE_SYSTEM_TEMPLATE = (
    "你是 CUMCM 建模教练。根据赛题全文与上游分析 JSON，输出纯 JSON（禁止 Markdown），字段："
    "subproblems: 数组，长度恰好为{count}，每项含 "
    "index(1-N), title(中文), description(该问要做什么，须引用题面条件), "
    "model_candidates(数组，2-4个候选模型名), recommended_model(推荐模型), "
    "solver_type(必填，与下游数值节点一致), "
    "variables(数组), constraints(数组), objective(若有), "
    "solution_approach(求解思路), expected_outputs(期望数值/图表/结论)。"
    "硬性：必须严格对应题面「问题1…问题N」原文要求，逐条摘录各问的题面原文关键句，"
    "递进且互不重复；子问题划分只能来自题面本身，禁止编造与题面无关的子问题。"
)

MODEL_BUILD_SYSTEM = (
    "你是 CUMCM comp-modeling 阶段专家。针对单个子问题，结合赛题全文 problem_text 与 data 参数，"
    "输出纯 JSON（禁止 Markdown），字段："
    "subproblem_index, model_name, model_type, solver_type, "
    "symbols(数组：symbol/meaning/unit), "
    "assumptions(数组), objective_function(文字或 LaTeX，供论文引用), "
    "constraints(数组), "
    "algorithm(求解算法名与步骤), "
    "computation_plan(数组：numpy/scipy 求解步骤), "
    "parameters(对象，键值对数值参数，须与 solver_type 严格匹配且可直接执行), "
    "figure_plan(数组：建议图表 type/title/columns，图题≤15字且无公式), "
    "table_plan(数组：建议三线表 name/columns，对应 figures/TABLE_*.md), "
    "expected_results(数组)。\n"
    "建模原则（通用）：先从题面识别问题类型（机理/优化/评价/预测/仿真），"
    "再选匹配的 solver_type；固定策略求值类问题可用 time_series/optimization，"
    "策略优化类可用 optimization/monte_carlo/integer_programming，"
    "数据拟合类可用 regression。parameters 必须从题面数据自行推导，禁止空对象。\n"
    + solver_catalog_for_prompt()
    + "\n仅当无法从题面推导参数时，才可参考上游 solver_hints；能推导则覆盖 hints。"
    + "\n论文公式请用 $...$ 或独立 $$...$$ 块，每个块公式需编号 (1)(2)…"
)

INTERPRET_SYSTEM = (
    "你是 CUMCM 论文撰写助手。根据上游模型建立 JSON 与数值求解结果 JSON，"
    "输出中文「结果分析」段落（纯文本，300-500字），包含："
    "主要数值结果解读、合理性讨论、与题目要求的对应；"
    "建议绘制的图表（中文图题≤15字，变量符号放正文不用在图题写 $公式$）；"
    "若适合，给出一段可嵌入 paper/main.md 的三线表 Markdown 草稿（含 |---|---| 分隔行）。"
)

SENSITIVITY_SYSTEM = (
    "你是 CUMCM 建模专家。根据各子问题汇总 JSON 与数值灵敏度计算结果，"
    "撰写「灵敏度分析」章节（纯文本，250-400字）："
    "选取 2-3 个关键参数，讨论 ±10%~20% 扰动对目标/结论的影响，引用数值扰动结果；"
    "可给出半定量结论与政策/工程含义。"
)

VALIDATION_SYSTEM = (
    "你是 CUMCM 评审专家。根据模型与结果，撰写「模型检验」章节（纯文本，200-350字）："
    "包括残差/一致性/极端情形/交叉验证思路（依题而定），指出模型局限与改进方向。"
)

# Paper section catalog (filtered/ordered by CumcmRunConfig)
_PAPER_SECTION_CATALOG: Dict[str, tuple] = {
    'abstract': (
        '摘要',
        '撰写 CUMCM 论文摘要（纯文本，{length}）：问题、方法、主要结果、结论。'
        '末尾单独一行：**关键词**：词1；词2；词3（冒号在加粗外）。',
    ),
    'restatement': (
        '问题重述',
        '撰写「一、问题重述」（{length}）。标题用 ## 一、问题重述。'
        '含问题背景与待解决问题；标签写法 **问题一**：内容（冒号在 ** 外）。',
    ),
    'analysis': (
        '问题分析',
        '撰写「二、问题分析」（{length}）。标题用 ## 二、问题分析。'
        '分条说明各子问题建模思路、数据需求与求解路线；过程式叙述，禁止空泛套话。',
    ),
    'assumptions': (
        '模型假设与符号说明',
        '撰写「三、模型假设与符号说明」（{length}）：'
        '### 3.1 模型假设 + ### 3.2 符号说明（Markdown 三线表）。',
    ),
    'tech_route': (
        '技术路线',
        '撰写总技术路线说明（{length}）。标题用 ## 技术路线（或并入问题分析末尾小节）。'
        '只描述**一张总图**的逻辑：数据→建模→求解→检验→论文；不要为每问单独画雷同框图。',
    ),
    'method_compare': (
        '候选方法对比',
        '撰写候选方法对比（{length}）。标题用 ## 候选方法对比 或并入各问建模前。'
        '至少对比 2–3 类方法（机理/优化/仿真等），用三线表给出选用理由；禁止只写最终方法。',
    ),
    'modeling': (
        '模型建立与求解',
        '撰写「四、模型建立与求解」（{length}）。按子问题分 ### 4.N 小节；'
        '块级公式各自独占 $$...$$ \\tag{n}；引用求解 JSON 中的 objective_value。',
    ),
    'results': (
        '结果分析',
        '撰写「五、结果分析」（{length}）。必须引用 figures/TABLE_*.md 风格三线表与图表结论。',
    ),
    'evaluation': (
        '模型评价',
        '撰写「六、模型评价」（{length}）：优点、灵敏度/鲁棒性、不足与改进。',
    ),
    'references': (
        '参考文献',
        '列出参考文献（{length}），格式 [1] 作者. 题名[J]. 期刊, 年, 卷(期): 页码.',
    ),
    'ai_declaration': (
        'AI工具使用声明',
        '按竞赛规范撰写「AI 工具使用声明」（{length}）。标题用 ## AI工具使用声明。'
        '说明是否使用 AI、用途边界；若使用则列工具名，细节可放附录。内容须具体、避免模板套话。',
    ),
}


def build_paper_section_specs(config: Optional[CumcmRunConfig] = None) -> List[tuple]:
    """Return [(key, title, instruction), ...] for active run config."""
    cfg = config or default_cumcm_config()
    specs: List[tuple] = []
    for key in paper_section_keys(cfg):
        title, tmpl = _PAPER_SECTION_CATALOG[key]
        length = section_length_hint(cfg, key) or '适中篇幅'
        # Avoid str.format — templates contain LaTeX like \\tag{n}
        specs.append((key, title, tmpl.replace('{length}', length)))
    return specs


# Backward-compatible default (国赛 standard)
PAPER_SECTION_SPECS: List[tuple] = build_paper_section_specs(default_cumcm_config())

FORMAT_CHECK_SYSTEM = (
    "你是 docx-format-check 步骤审查员。输入为组装后的 paper/main.md 草稿。"
    "对照 Modex 竞赛 Markdown 规范，输出**修正后的完整 Markdown**（不要 JSON，不要解释）。"
    "检查项：# 标题唯一；章节从 ## 起；**标签**：内容（冒号在加粗外）；"
    "图题 ![图 N：描述](...) 独占行；三线表 |---|---|；禁止 LaTeX \\section/\\cite；"
    "块公式编号用 \\tag{n} 与公式同行。"
)

FORMAT_CHECK_SYSTEM_FAST = (
    "你是 docx-format-check 快速审查员。只修明显格式硬伤，输出修正后的完整 Markdown。"
    "必查：# 唯一；## 章节；图题独占行；三线表分隔行。少改表述，省额度。"
)

PAPER_WRITING_RULES = _compose_paper_writing_rules()

CHART_STYLE_RULES = (
    load_prompt_file('paper_figure_lang_zh.md') or load_prompt_file('nature_figure_lang.md')
    or (
        '图表 axis/legend/annotate 用中文；变量符号如 R²、RMSE 可保留英文；'
        '图题≤15中文字，禁止在图题中使用 $公式$。'
    )
)


def get_paper_section_prompt(
    title: str,
    base_instruction: str,
    config: Optional[CumcmRunConfig] = None,
) -> str:
    """Full system prompt for a paper section LLM node."""
    cfg = config or default_cumcm_config()
    rules_excerpt = PAPER_WRITING_RULES[:4500] if PAPER_WRITING_RULES else ''
    return (
        f"{base_instruction}\n\n"
        f"{build_run_config_prompt_block(cfg)}\n\n"
        f"## 输出格式规范（Modex cumcm-full，必须遵守）\n{rules_excerpt}\n\n"
        "只输出该章节正文 Markdown 片段，不要输出 JSON，不要用 ``` 代码块包裹全文。"
    )


def get_format_check_prompt(config: Optional[CumcmRunConfig] = None) -> str:
    cfg = config or default_cumcm_config()
    head = FORMAT_CHECK_SYSTEM if cfg.review_mode == 'strict' else FORMAT_CHECK_SYSTEM_FAST
    rules_budget = 5000 if cfg.review_mode == 'strict' else 2200
    rules = (PAPER_WRITING_RULES[:rules_budget] if PAPER_WRITING_RULES else load_format_reference())
    return (
        f"{head}\n\n"
        f"{build_run_config_prompt_block(cfg)}\n\n"
        f"## 规范全文\n{rules}"
    )


def get_logic_adversarial_prompt(config: Optional[CumcmRunConfig] = None) -> str:
    cfg = config or default_cumcm_config()
    return f"{LOGIC_ADVERSARIAL_SYSTEM}\n\n{build_run_config_prompt_block(cfg)}"


def get_decompose_system(
    subproblem_count: int,
    config: Optional[CumcmRunConfig] = None,
) -> str:
    cfg = config or default_cumcm_config()
    base = DECOMPOSE_SYSTEM_TEMPLATE.replace('{count}', str(subproblem_count))
    extra = (
        f"\n每问 model_candidates 至少 {cfg.min_models_per_subproblem} 个；"
        f"必须给出 recommended_model 与选用理由。"
        f"\n{build_run_config_prompt_block(cfg)}"
    )
    return base + extra


def get_model_build_system(config: Optional[CumcmRunConfig] = None) -> str:
    cfg = config or default_cumcm_config()
    return MODEL_BUILD_SYSTEM + f"\n{build_run_config_prompt_block(cfg)}"


def get_merge_paper_preamble() -> str:
    """Instructions embedded in merge code comments / LLM post-process."""
    return (
        "论文结构：# 标题 → ## 摘要 → ## 一、… → 参考文献 → 附录。"
        "图表用 ![图 N 说明](...) 或嵌入三线表；图题简短无公式。"
    )


# ---------------------------------------------------------------------------
# NL workflow generation prompt (prompts.py integration)
# ---------------------------------------------------------------------------

CUMCM_WORKFLOW_GENERATION_SYSTEM = """你是 CUMCM / 全国大学生数学建模竞赛工作流设计专家。

## 任务
当用户需要「数学建模竞赛 / CUMCM / 国赛论文」流水线时，生成**确定性多阶段工作流**（非简单 start→llm→end）。

## 必须包含的阶段（按顺序）
1. **input** — 赛题与数据 JSON（problem_text, data, attachments, solver_hints）
2. **llm** — 赛题解析（输出 JSON：重述、变量、假设、策略）
3. **llm** — 子问题分解（2~5 问，每问含 solver_type）
4. **code** — 数据预处理（numpy 描述统计）
5. **并行子链路**（每问一条）：code 提取 → llm 模型建立 → code 数值求解 → llm 结果分析
6. **code** — 汇总子问题结果
7. **code** — 自动生成模型图表（matplotlib，中文标签，base64）
8. **code** — 数值灵敏度计算
9. **llm** — 灵敏度分析 + 模型检验
10. **llm×8** — 论文分段（摘要/重述/假设/建模/求解/分析/评价/参考文献）
11. **code** — 组装 paper/main.md（遵守 docx Markdown 规范）
12. **file_writer** — 保存 paper/main.md、figures/TABLE_summary.md、paper/main.docx
13. **output** + **end**

## 数值求解 solver_type（code 节点自动路由）
linear_programming | integer_programming | regression | time_series | optimization | monte_carlo | generic

## Code 节点约束
- 沙箱可用：numpy, scipy, pandas, matplotlib(Agg)
- 禁止 os/subprocess/eval；输出赋值给 output 变量
- 含 node_outputs 的 collect/汇总脚本需能读取上游 text JSON

## 论文写作约束（来自 prompts/ 规范）
- 输出 Markdown 而非 LaTeX；块公式 $$...$$ (n) 独占行
- 图题≤15字、中文、禁止图题内 $公式$
- 三线表 |---|---|；**标签**：内容（冒号在加粗外）
- 图表 axis/legend 用中文

## 禁止
- 不要用单个 llm 节点代替完整建模流水线
- 不要省略 code 数值求解与图表生成节点
- 不要编造 scipy 无法执行的 solver 参数结构"""


def cumcm_few_shot_example() -> Dict[str, str]:
    """Few-shot for LLM fallback generation (simplified skeleton)."""
    return {
        'input': '帮我搭建 CUMCM 全国大学生数学建模完整工作流，3个子问题，需要线性规划、灵敏度分析和论文输出',
        'output': json.dumps({
            'name': 'CUMCM 全国大学生数学建模·完整流水线',
            'description': '赛题解析→3问并行建模求解→图表→灵敏度→论文 Markdown 输出',
            'nodes': [
                {'id': 'start_1', 'type': 'start', 'name': '开始', 'position': {'x': 80, 'y': 400}, 'config': {}},
                {
                    'id': 'input_1', 'type': 'input', 'name': '赛题与数据输入',
                    'position': {'x': 280, 'y': 400},
                    'config': {'input_type': 'text', 'variable_name': 'input', 'label': 'CUMCM JSON'},
                },
                {
                    'id': 'llm_parse', 'type': 'llm', 'name': '赛题解析',
                    'position': {'x': 560, 'y': 400},
                    'config': {
                        'provider': 'agnes', 'model': 'agnes-2.0-flash', 'temperature': 0.25,
                        'system_prompt': 'CUMCM 赛题解析，输出纯 JSON',
                        'user_template': '解析赛题：\n{input}',
                    },
                },
                {
                    'id': 'code_preprocess', 'type': 'code', 'name': '数据预处理',
                    'position': {'x': 860, 'y': 400},
                    'config': {'language': 'python', 'code': '# numpy 描述统计\noutput = {"text": "..."}'},
                },
                {
                    'id': 'code_chart', 'type': 'code', 'name': '自动生成模型图表',
                    'position': {'x': 1160, 'y': 400},
                    'config': {'language': 'python', 'code': '# matplotlib 中文图表\noutput = {"markdown_embeds": []}'},
                },
                {
                    'id': 'file_writer_1', 'type': 'file_writer', 'name': '保存论文',
                    'position': {'x': 1460, 'y': 400},
                    'config': {'path': 'paper/main.md', 'content': '{content}'},
                },
                {'id': 'output_1', 'type': 'output', 'name': '输出成果', 'position': {'x': 1760, 'y': 400}, 'config': {}},
                {'id': 'end_1', 'type': 'end', 'name': '结束', 'position': {'x': 2060, 'y': 400}, 'config': {}},
            ],
            'edges': [
                {'id': 'e1', 'source': 'start_1', 'target': 'input_1', 'label': ''},
                {'id': 'e2', 'source': 'input_1', 'target': 'llm_parse', 'label': ''},
                {'id': 'e3', 'source': 'llm_parse', 'target': 'code_preprocess', 'label': ''},
                {'id': 'e4', 'source': 'code_preprocess', 'target': 'code_chart', 'label': ''},
                {'id': 'e5', 'source': 'code_chart', 'target': 'file_writer_1', 'label': ''},
                {'id': 'e6', 'source': 'file_writer_1', 'target': 'output_1', 'label': ''},
                {'id': 'e7', 'source': 'output_1', 'target': 'end_1', 'label': ''},
            ],
        }, ensure_ascii=False),
    }


def cumcm_conversation_hints() -> str:
    """Extra system hint for ConversationPrompt when CUMCM intent detected."""
    return (
        "\n\n## CUMCM 数学建模竞赛（当前用户意图相关）\n"
        "确认：赛题来源（A/B/C 题）、子问题数量（通常 2~4 问）、是否有数据文件/附件、"
        "需要的求解类型（线性规划/回归/时间序列/蒙特卡洛等）、是否要自动生成图表与 Word 兼容 Markdown 论文。\n"
        "就绪后生成完整流水线（非单个 LLM 节点）。"
    )
