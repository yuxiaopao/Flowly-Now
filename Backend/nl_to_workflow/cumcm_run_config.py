# -*- coding: utf-8 -*-
"""
CUMCM / 数学建模出稿运行配置。

对标市面「数模论文 AI」产品旋钮，但只落地能驱动现有流水线的参数：
写长/写短、审查强弱、图表配色、逻辑对抗复核、页数目标、AI 声明等。

注意：
- 「丰满模式 40–60 页」是华为杯量级目标，不应默认套到国赛 CUMCM（页数更紧）。
- LaTeX 封面/承诺书 PDF、DrawIO、视觉质检、人工检查点 依赖额外基建，本模块先留开关位。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, List, Literal, Optional


ContestKind = Literal['cumcm', 'huawei', 'generic']
ReviewMode = Literal['strict', 'fast']
Richness = Literal['standard', 'rich']
ChartPalette = Literal['bw', 'plain', 'modern', 'refined']
ChartStyle = Literal['academic', 'nature']
FlowchartEngine = Literal['html', 'drawio']
OutputFormat = Literal['docx', 'markdown', 'pdf_latex']


@dataclass(frozen=True)
class CumcmRunConfig:
    """Runtime knobs that reshape prompts / nodes / chart style."""

    contest: ContestKind = 'cumcm'
    problem_id: str = 'A'

    # 输出
    output_formats: tuple = ('markdown', 'docx')
    # pdf_latex / 封面承诺书：开关位，当前流水线未编译 LaTeX
    enable_latex_pdf: bool = False
    include_cover_and_commitment: bool = False

    # 审查
    review_mode: ReviewMode = 'strict'
    logic_adversarial_review: bool = True
    paper_improve_loops: int = 0  # 0=关；>0 需后续节点支持重编译循环

    # 篇幅 / 丰满度
    richness: Richness = 'standard'
    page_limit_body: int = 20  # 不含附录与参考文献
    min_figures: int = 8
    min_tables: int = 5
    min_models_per_subproblem: int = 2  # 候选方法对比下限
    process_narration: bool = True
    candidate_method_compare: bool = True

    # 图表
    chart_palette: ChartPalette = 'bw'
    chart_style: ChartStyle = 'academic'
    flowchart_engine: FlowchartEngine = 'html'
    flowchart_per_subproblem: bool = False  # False=只画一张总技术路线图
    chart_vision_qa: bool = False
    flowchart_vision_qa: bool = False

    # 合规
    ai_tool_declaration: bool = True
    human_checkpoints: bool = False

    # 自定义（执行时注入 prompt）
    custom_requirements: str = ''
    solution_outline: str = ''

    notes: str = ''

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['output_formats'] = list(self.output_formats)
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'CumcmRunConfig':
        if not data:
            return default_cumcm_config()
        base = default_cumcm_config()
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs: Dict[str, Any] = {}
        for k, v in data.items():
            if k not in allowed:
                continue
            if k == 'output_formats' and isinstance(v, list):
                kwargs[k] = tuple(v)
            else:
                kwargs[k] = v
        return replace(base, **kwargs)


# ---------------------------------------------------------------------------
# Presets（产品旋钮 → 工程默认）
# ---------------------------------------------------------------------------

def strictest_test_config() -> CumcmRunConfig:
    """测试专用最严格模式（E2E / 联调强制使用）。

    打开全部已落地质量闸：严格格式审查、逻辑对抗、候选方法对比、
    AI 声明、黑白印刷图、更高图表/模型下限、过程式叙述。
    视觉质检 / 论文改进循环为开关位（节点接上后即生效）。
    页数仍按国赛 ~20，不把华为杯 40–60 页误套进测试默认。
    """
    return CumcmRunConfig(
        contest='cumcm',
        problem_id='A',
        output_formats=('markdown', 'docx'),
        enable_latex_pdf=False,
        include_cover_and_commitment=False,
        review_mode='strict',
        logic_adversarial_review=True,
        paper_improve_loops=2,
        richness='standard',
        page_limit_body=20,
        min_figures=12,
        min_tables=8,
        min_models_per_subproblem=3,
        process_narration=True,
        candidate_method_compare=True,
        chart_palette='bw',
        chart_style='academic',
        flowchart_engine='html',
        flowchart_per_subproblem=False,
        chart_vision_qa=True,
        flowchart_vision_qa=True,
        ai_tool_declaration=True,
        human_checkpoints=False,
        notes=(
            '【测试强制·最严格】禁止 fast；完整审查+逻辑对抗+AI声明+黑白图；'
            '图表/表格/候选模型下限抬高；paper_improve_loops=2 / 视觉质检开关已开。'
        ),
    )


def get_testing_config() -> CumcmRunConfig:
    """Alias：所有自动化测试 / E2E 必须走最严格配置。"""
    return strictest_test_config()


def default_cumcm_config() -> CumcmRunConfig:
    """流水线默认 = 测试最严格模式（按产品要求：测试一律严格）。"""
    return strictest_test_config()


def rich_huawei_config() -> CumcmRunConfig:
    """华为杯丰满模式量级（对方产品文案）。"""
    return CumcmRunConfig(
        contest='huawei',
        richness='rich',
        page_limit_body=50,
        min_figures=30,
        min_tables=12,
        min_models_per_subproblem=3,
        process_narration=True,
        candidate_method_compare=True,
        review_mode='strict',
        logic_adversarial_review=True,
        paper_improve_loops=2,
        chart_palette='bw',
        chart_vision_qa=True,
        flowchart_vision_qa=True,
        flowchart_per_subproblem=False,
        ai_tool_declaration=True,
        notes='华为杯丰满模式：40–60 页目标；勿直接套到国赛。',
    )


def fast_review_config() -> CumcmRunConfig:
    """省额度：仅显式选用。测试 / E2E 禁止使用。"""
    return replace(
        CumcmRunConfig(
            contest='cumcm',
            richness='standard',
            page_limit_body=20,
            min_figures=8,
            min_tables=5,
            chart_palette='bw',
            ai_tool_declaration=True,
        ),
        review_mode='fast',
        logic_adversarial_review=False,
        chart_vision_qa=False,
        flowchart_vision_qa=False,
        paper_improve_loops=0,
        notes='快速审查：省额度。测试场景禁止使用本预设。',
    )


PRESETS: Dict[str, CumcmRunConfig] = {
    'strictest': strictest_test_config(),
    'test': strictest_test_config(),
    'testing': strictest_test_config(),
    'cumcm_default': strictest_test_config(),
    'huawei_rich': rich_huawei_config(),
    'fast': fast_review_config(),
}


def get_preset(name: str) -> CumcmRunConfig:
    key = (name or '').strip().lower()
    if key in PRESETS:
        return deepcopy(PRESETS[key])  # type: ignore[arg-type]
    return get_testing_config()


def assert_strict_for_testing(config: CumcmRunConfig) -> None:
    """Raise if a test/E2E path accidentally uses non-strict settings."""
    if config.review_mode != 'strict':
        raise ValueError(f'测试必须 review_mode=strict，当前={config.review_mode}')
    if not config.logic_adversarial_review:
        raise ValueError('测试必须开启 logic_adversarial_review')
    if config.chart_palette != 'bw':
        raise ValueError(f'测试要求黑白图 palette=bw，当前={config.chart_palette}')
    if not config.candidate_method_compare:
        raise ValueError('测试必须开启 candidate_method_compare')
    if not config.ai_tool_declaration:
        raise ValueError('测试必须开启 ai_tool_declaration')
    if config.min_models_per_subproblem < 3:
        raise ValueError('测试要求每问候选模型 ≥ 3')

# ---------------------------------------------------------------------------
# Prompt / length helpers
# ---------------------------------------------------------------------------

_SECTION_LENGTH_STANDARD: Dict[str, str] = {
    'abstract': '300字内',
    'restatement': '400-500字',
    'analysis': '400-600字',
    'assumptions': '完整假设 5-8 条 + 符号三线表',
    'modeling': '600-900字，按子问题分节，含公式编号',
    'results': '400-600字，必须引用表/图',
    'evaluation': '250-400字',
    'references': '8-12 条',
    'tech_route': '200-350字 + 可嵌入总技术路线说明',
    'method_compare': '300-500字，对比候选方法优劣与为何选用',
    'ai_declaration': '80-150字，说明使用的 AI 工具与用途',
}

_SECTION_LENGTH_RICH: Dict[str, str] = {
    'abstract': '400-500字',
    'restatement': '800-1200字，过程式叙述背景与约束',
    'analysis': '1000-1500字，每问独立分析段落',
    'assumptions': '假设分层（强/弱）+ 完整符号表 + 量纲说明',
    'modeling': '每问 800-1200字，含候选方法对比、算法伪步骤、复杂度',
    'results': '800-1200字，多表多图解读与误差讨论',
    'evaluation': '600-900字，灵敏度/推广/不足分小节',
    'references': '15-25 条',
    'tech_route': '400-600字，总技术路线图文字说明',
    'method_compare': '600-900字，至少对比 2-3 类方法并给出选用理由表',
    'ai_declaration': '120-200字，并提示参考文献可列 AI 工具',
}


def section_length_hint(config: CumcmRunConfig, key: str) -> str:
    table = _SECTION_LENGTH_RICH if config.richness == 'rich' else _SECTION_LENGTH_STANDARD
    return table.get(key, '')


def paper_section_keys(config: CumcmRunConfig) -> List[str]:
    """Ordered paper LLM section keys for the active profile."""
    keys = [
        'abstract',
        'restatement',
        'analysis',
        'assumptions',
        'tech_route',
    ]
    if config.candidate_method_compare:
        keys.append('method_compare')
    keys.extend(['modeling', 'results', 'evaluation', 'references'])
    if config.ai_tool_declaration:
        keys.append('ai_declaration')
    return keys


def chart_color_cycle(config: CumcmRunConfig) -> List[str]:
    """Matplotlib-friendly color list for solvers chart code."""
    if config.chart_palette == 'bw':
        return ['#000000', '#333333', '#666666', '#999999', '#222222']
    if config.chart_palette == 'plain':
        return ['#1f2937', '#4b5563', '#6b7280', '#9ca3af']
    if config.chart_palette == 'modern':
        return ['#2563eb', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
    # refined
    return ['#0f172a', '#334155', '#64748b', '#94a3b8', '#cbd5e1']


def build_run_config_prompt_block(config: CumcmRunConfig) -> str:
    """Inject into LLM system prompts so agents obey the same knobs."""
    formats = '、'.join(config.output_formats)
    lines = [
        '## 本场运行配置（必须遵守）',
        f'- 赛事：{config.contest} / 题号：{config.problem_id}',
        f'- 输出格式：{formats}'
        + ('；LaTeX→PDF 开关已开（若流水线未接编译器则仍以 Markdown/Word 为准）' if config.enable_latex_pdf else ''),
        f'- 审查模式：{"严格（完整审查）" if config.review_mode == "strict" else "快速（省额度）"}',
        f'- 正文页数目标（不含附录/参考文献）：约 {config.page_limit_body} 页',
        f'- 丰满度：{"丰满（过程式叙述 + 候选方法对比 + 扩章）" if config.richness == "rich" else "标准竞赛篇幅"}',
        f'- 图表下限：≥{config.min_figures} 张图，≥{config.min_tables} 张表',
        f'- 每问候选模型数：≥{config.min_models_per_subproblem}',
        f'- 图表配色：{config.chart_palette}（bw=纯黑白印刷友好）',
        f'- 图表风格：{config.chart_style}',
        f'- 流程图：{config.flowchart_engine}；'
        + ('每问一张求解流程图' if config.flowchart_per_subproblem else '只画一张总技术路线图（推荐）'),
        f'- 逻辑对抗复核：{"开启" if config.logic_adversarial_review else "关闭"}',
        f'- 论文改进循环：{config.paper_improve_loops} 轮'
        + ('（测试严格模式默认 2）' if config.paper_improve_loops >= 2 else ''),
        f'- 数据图视觉质检：{"开" if config.chart_vision_qa else "关"}；'
        f'流程图视觉质检：{"开" if config.flowchart_vision_qa else "关"}',
        f'- AI 工具使用声明：{"需要" if config.ai_tool_declaration else "不需要"}',
    ]
    if config.custom_requirements.strip():
        lines.append(f'- 自定义要求：{config.custom_requirements.strip()[:800]}')
    if config.solution_outline.strip():
        lines.append(f'- 用户解题大纲（优先参考）：{config.solution_outline.strip()[:1200]}')
    if config.notes.strip():
        lines.append(f'- 备注：{config.notes.strip()}')
    lines.append(
        '- 禁止为了「看起来长」而注水；篇幅目标服务于论证完整，不是凑字数。'
    )
    return '\n'.join(lines)


LOGIC_ADVERSARIAL_SYSTEM = (
    "你是独立审稿人（逻辑对抗复核）。在写论文之前，对上游「子问题分解 / 模型 / 数值结果」做对抗检查。"
    "输出纯 JSON（禁止 Markdown），字段："
    "fatal_issues(数组：方向反/重复计量/外推过硬/漏变量/跨问矛盾/任务读歪 等致命问题，每项含 code/detail/affected_subproblems),"
    "warnings(数组：非致命但应改),"
    "ok_to_write_paper(布尔),"
    "repair_plan(数组：若有 fatal，给出回炉步骤：改哪一问的模型/参数/目标),"
    "summary(中文 120字内)。"
    "标准从严：只要存在会让答辩翻车的逻辑错，ok_to_write_paper=false。"
)
