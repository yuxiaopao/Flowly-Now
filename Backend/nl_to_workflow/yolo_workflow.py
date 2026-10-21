"""
YOLO detection workflow helpers for NL2WF.

Provides intent detection, template loading/customization, and conversational
fallback when LLM is unavailable or for rule-based readiness checks.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

YOLO_TEMPLATE_SLUG = "yolo-detection-project"

# Strong signals — any one match is enough for yolo_detection subtype
YOLO_STRONG_KEYWORDS: List[str] = [
    "yolo",
    "ultralytics",
    "目标检测",
    "物体检测",
    "识别项目",
    "yolo训练",
    "yolo 训练",
    "yolo检测",
    "yolo 检测",
]

# Weaker signals — need at least two hits together with a strong-ish context
YOLO_WEAK_KEYWORDS: List[str] = [
    "训练模型",
    "模型训练",
    "标注数据集",
    "数据集",
    "建站",
    "识别网站",
    "识别系统",
    "推理",
    "bounding box",
    "bbox",
    "computer vision",
    "计算机视觉",
    "cv",
    "mlops",
]

# Non-ML「检测」语境 — 单独出现时不应触发 YOLO
YOLO_NEGATIVE_PHRASES: List[str] = [
    "检测表单", "表单检测", "字段检测", "检测字段",
    "检测敏感", "敏感内容", "内容审核", "检测是否",
    "检测用户输入", "输入检测", "合法性检测",
    "空值检测", "格式检测", "检测合法", "检测空",
]

YOLO_PIPELINE_KEYWORDS: List[str] = [
    "数据集",
    "训练",
    "建站",
    "网站",
    "预览",
    "qa",
    "环境",
    "全链路",
    "端到端",
    "pipeline",
    "工作流",
]

YOLO_V2_INTENT_KEYWORDS: List[str] = [
    "分工",
    "现代化",
    "后端搭建",
    "前端搭建",
    "ui美化",
    "ui 美化",
    "代码复查",
    "ai 优化",
    "ai优化",
    "精细建站",
    "美化",
    "排版",
]

YOLO_V2_TEMPLATE_SLUG = "yolo-detection-v2"

YOLO_CHAT_QUESTIONS: List[str] = [
    "您已有 YOLO 格式的标注数据集，还是需要从上传开始？",
    "训练完成后是否需要自动生成可部署的识别网站（含 QA 与预览）？",
    "期望的训练规模如何（例如 epochs、模型大小 n/s/m）？",
]


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def yolo_keyword_hits(text: str) -> Tuple[int, int]:
    """Return (strong_hits, weak_hits) for the given text."""
    lower = _normalize_text(text)
    strong = sum(1 for kw in YOLO_STRONG_KEYWORDS if kw in lower)
    weak = sum(1 for kw in YOLO_WEAK_KEYWORDS if kw in lower)
    return strong, weak


def is_yolo_detection_intent(text: str) -> bool:
    """True when the message likely describes a YOLO / detection MLOps workflow."""
    if not text or not text.strip():
        return False
    lower = _normalize_text(text)
    strong, weak = yolo_keyword_hits(text)
    if strong >= 1:
        return True
    if "检测" in lower:
        if any(neg in lower for neg in YOLO_NEGATIVE_PHRASES):
            return False
        if not any(
            k in lower
            for k in ("训练", "数据集", "模型", "网站", "yolo", "目标", "物体", "bounding", "标注")
        ):
            return False
    if weak >= 2:
        return True
    if "检测" in lower and any(k in lower for k in ("训练", "数据集", "模型", "网站", "yolo")):
        return True
    return False


def yolo_intent_confidence(text: str) -> str:
    """Return 'high', 'medium', or 'low' confidence for YOLO intent."""
    strong, weak = yolo_keyword_hits(text)
    if strong >= 1 and weak >= 1:
        return "high"
    if strong >= 1 or weak >= 2:
        return "medium"
    if is_yolo_detection_intent(text):
        return "low"
    return "none"


def has_sufficient_yolo_detail(text: str) -> bool:
    """
    Heuristic: enough YOLO pipeline context to generate a workflow.
    Requires YOLO intent plus at least two pipeline aspect keywords.
    """
    if not is_yolo_detection_intent(text):
        return False
    lower = _normalize_text(text)
    pipeline_hits = sum(1 for kw in YOLO_PIPELINE_KEYWORDS if kw in lower)
    if pipeline_hits >= 2 and len(text.strip()) >= 20:
        return True
    if yolo_intent_confidence(text) == "high" and len(text.strip()) >= 25:
        return True
    return False


def _fallback_yolo_workflow_nl() -> Dict[str, Any]:
    """Hardcoded NL-format YOLO pipeline — aliases to full Site Factory v2."""
    return _fallback_yolo_v2_workflow_nl()


def is_yolo_v2_site_factory_intent(text: str) -> bool:
    """True when user wants the v2 AI role-agent site factory chain."""
    if not is_yolo_detection_intent(text):
        return False
    lower = _normalize_text(text)
    return sum(1 for kw in YOLO_V2_INTENT_KEYWORDS if kw in lower) >= 1


def _fallback_yolo_v2_workflow_nl() -> Dict[str, Any]:
    """Hardcoded NL-format YOLO v2 pipeline with AI role agents (matches FE template)."""
    return {
        "name": "YOLO 识别项目",
        "description": "数据集 → YOLO 训练 → 场景分析 → 建站(Flask+Vue+MySQL) → 后端/前端/UI → 环境授权 → QA自修 → 预览 → 项目 Agent",
        "nodes": [
            {
                "id": "dataset_upload_1",
                "type": "dataset_upload",
                "name": "上传标注数据集",
                "position": {"x": 40, "y": 220},
                "config": {"format": "yolo", "sourceType": "upload"},
            },
            {
                "id": "yolo_training_1",
                "type": "yolo_training",
                "name": "YOLO 训练",
                "position": {"x": 240, "y": 220},
                "config": {
                    "trainingMode": "local",
                    "yoloVersion": "v8",
                    "modelVariant": "n",
                    "epochs": 50,
                    "batchSize": 16,
                    "imageSize": 640,
                    "dataSourceType": "upstream",
                },
            },
            {
                "id": "project_profiler_1",
                "type": "project_profiler",
                "name": "场景分析",
                "position": {"x": 440, "y": 220},
                "config": {"websiteType": "detection", "useLlmEnrich": True},
            },
            {
                "id": "website_generator_1",
                "type": "website_generator",
                "name": "生成识别网站",
                "position": {"x": 640, "y": 220},
                "config": {
                    "websiteType": "detection",
                    "projectType": "detection",
                    "framework": "ultralytics",
                    "frontendFramework": "vue",
                    "backendFramework": "flask",
                    "dbEngine": "mysql",
                    "qaProfile": "default",
                    "waitForCompletion": True,
                    "wizard": {
                        "siteName": "YOLO 识别系统",
                        "usageDescription": "上传现场图片，查看目标检测框与置信度",
                        "primaryColor": "#f59e0b",
                        "qaProfile": "default",
                        "websiteType": "detection",
                        "wizardCompleted": True,
                    },
                    "environmentConfig": {"dbEngine": "mysql"},
                },
            },
            {
                "id": "backend_setup_1",
                "type": "backend_setup",
                "name": "后端搭建",
                "position": {"x": 840, "y": 120},
                "config": {"agentMode": "auto", "allowCoreEdit": True, "autoQaAfterEdit": False},
            },
            {
                "id": "frontend_setup_1",
                "type": "frontend_setup",
                "name": "前端搭建",
                "position": {"x": 1040, "y": 120},
                "config": {"agentMode": "auto", "autoQaAfterEdit": False},
            },
            {
                "id": "ui_beautify_1",
                "type": "ui_beautify",
                "name": "UI 美化",
                "position": {"x": 1240, "y": 120},
                "config": {"agentMode": "auto", "autoQaAfterEdit": False},
            },
            {
                "id": "environment_provision_1",
                "type": "environment_provision",
                "name": "环境配置",
                "position": {"x": 1040, "y": 320},
                "config": {
                    "runtimeMode": "desktop",
                    "dbEngine": "mysql",
                    "requirePathGrant": True,
                    "customPaths": [],
                },
            },
            {
                "id": "site_qa_1",
                "type": "site_qa",
                "name": "站点自查",
                "position": {"x": 1240, "y": 320},
                "config": {
                    "websiteType": "detection",
                    "qaProfile": "default",
                    "skipPlaywright": False,
                    "autoFix": True,
                    "maxFixRounds": 2,
                },
            },
            {
                "id": "site_code_review_1",
                "type": "site_code_review",
                "name": "代码复查",
                "position": {"x": 1440, "y": 220},
                "config": {"agentMode": "auto", "maxRounds": 2, "autoQaAfterEdit": True},
            },
            {
                "id": "site_preview_1",
                "type": "site_preview",
                "name": "站点预览",
                "position": {"x": 1640, "y": 220},
                "config": {"qaProfile": "default"},
            },
            {
                "id": "project_agent_1",
                "type": "project_agent",
                "name": "项目 Agent",
                "position": {"x": 1840, "y": 220},
                "config": {
                    "qaProfile": "default",
                    "autoQaAfterEdit": True,
                    "syncSystemAgent": True,
                    "agentMemoryEnabled": True,
                    "message": "",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "dataset_upload_1", "target": "yolo_training_1"},
            {"id": "e2", "source": "yolo_training_1", "target": "project_profiler_1"},
            {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1"},
            {"id": "e4", "source": "website_generator_1", "target": "backend_setup_1"},
            {"id": "e5", "source": "backend_setup_1", "target": "frontend_setup_1"},
            {"id": "e6", "source": "frontend_setup_1", "target": "ui_beautify_1"},
            {"id": "e7", "source": "ui_beautify_1", "target": "environment_provision_1"},
            {"id": "e8", "source": "environment_provision_1", "target": "site_qa_1"},
            {"id": "e9", "source": "site_qa_1", "target": "site_code_review_1"},
            {"id": "e10", "source": "site_code_review_1", "target": "site_preview_1"},
            {"id": "e11", "source": "site_preview_1", "target": "project_agent_1"},
        ],
    }


def vueflow_to_nl_workflow(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert VueFlow template (data.label) to NL workflow (name/config)."""
    nodes_out = []
    for node in raw.get("nodes", []):
        data = node.get("data") or {}
        config = copy.deepcopy(data.get("config") or node.get("config") or {})
        nodes_out.append({
            "id": node.get("id"),
            "type": node.get("type", "llm"),
            "name": data.get("label") or node.get("name") or node.get("type", "Node"),
            "position": node.get("position") or {"x": 0, "y": 0},
            "config": config,
        })
    edges_out = []
    for i, edge in enumerate(raw.get("edges", [])):
        edges_out.append({
            "id": edge.get("id", f"edge_{i + 1}"),
            "source": edge.get("source"),
            "target": edge.get("target"),
            "label": edge.get("label", ""),
        })
    return {
        "name": raw.get("name", "YOLO 识别项目"),
        "description": raw.get("description", ""),
        "nodes": nodes_out,
        "edges": edges_out,
    }


def load_yolo_v2_template_workflow() -> Dict[str, Any]:
    """Load YOLO v2 workflow from DB template or fallback."""
    try:
        from workflows.models import WorkflowTemplate

        template = WorkflowTemplate.objects.filter(
            name__icontains="YOLO 识别项目 v2",
            is_active=True,
        ).first()
        if not template:
            template = WorkflowTemplate.objects.filter(
                name__icontains="v2",
                tags__icontains="ai-agents",
                is_active=True,
            ).first()
        if template and template.workflow_data:
            wf = vueflow_to_nl_workflow(copy.deepcopy(template.workflow_data))
            wf["name"] = template.name or wf.get("name", "YOLO 识别项目 v2")
            wf["description"] = template.description or wf.get("description", "")
            return wf
    except Exception as exc:
        logger.warning("Failed to load YOLO v2 template from DB: %s", exc)
    return copy.deepcopy(_fallback_yolo_v2_workflow_nl())


def load_yolo_template_workflow() -> Dict[str, Any]:
    """Load YOLO workflow from DB template or fallback."""
    try:
        from workflows.models import WorkflowTemplate

        template = WorkflowTemplate.objects.filter(
            name__icontains="YOLO 识别",
            is_active=True,
        ).first()
        if not template:
            template = WorkflowTemplate.objects.filter(
                tags__icontains="YOLO",
                is_active=True,
            ).first()
        if template and template.workflow_data:
            wf = vueflow_to_nl_workflow(copy.deepcopy(template.workflow_data))
            wf["name"] = template.name or wf.get("name", "YOLO 识别项目")
            wf["description"] = template.description or wf.get("description", "")
            return wf
    except Exception as exc:
        logger.warning("Failed to load YOLO template from DB: %s", exc)
    return copy.deepcopy(_fallback_yolo_workflow_nl())


def _extract_epochs(text: str) -> Optional[int]:
    lower = _normalize_text(text)
    patterns = [
        r"(\d+)\s*(?:个\s*)?epoch",
        r"epoch[s]?\s*[:=]?\s*(\d+)",
        r"训练\s*(\d+)\s*(?:轮|epoch|epochs)",
        r"(\d+)\s*(?:轮|epochs)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 500:
                return value
    return None


def _extract_site_name(text: str) -> Optional[str]:
    patterns = [
        r"(?:网站|站点|系统)(?:名称|名叫|叫做|名为)[:：]?\s*[「\"']?([^「\"'\n，。,]{2,30})",
        r"(?:叫做|名为|名叫)\s*[「\"']?([^「\"'\n，。,]{2,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_project_name(text: str) -> Optional[str]:
    patterns = [
        r"(?:项目|工作流)(?:名称|名叫|叫做|名为)[:：]?\s*[「\"']?([^「\"'\n，。,]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_model_variant(text: str) -> Optional[str]:
    lower = _normalize_text(text)
    for variant in ("n", "s", "m", "l", "x"):
        if re.search(rf"yolo\s*v?8{variant}\b|yolov8{variant}|模型\s*{variant}\b|variant\s*{variant}", lower):
            return variant
    return None


def customize_yolo_workflow(
    workflow: Dict[str, Any],
    description: str,
    *,
    hardware_profile: Optional[Dict[str, Any]] = None,
    reusable_weight: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply user-stated preferences from conversation text to the template."""
    from core.services.hardware_profile import merge_hardware_profile, recommend_yolo_training_config

    wf = copy.deepcopy(workflow)
    desc = description or ""

    project_name = _extract_project_name(desc)
    if project_name:
        wf["name"] = project_name
    elif is_yolo_detection_intent(desc) and not wf.get("name"):
        wf["name"] = "YOLO 识别项目"

    if desc.strip():
        wf["description"] = desc.strip()[:500]

    epochs = _extract_epochs(desc)
    site_name = _extract_site_name(desc)
    model_variant = _extract_model_variant(desc)

    profile = hardware_profile or merge_hardware_profile()
    hw_rec = recommend_yolo_training_config(profile)

    for node in wf.get("nodes", []):
        if node.get("type") == "yolo_training":
            config = node.setdefault("config", {})
            if epochs is not None:
                config["epochs"] = epochs
            elif "epochs" not in config:
                config["epochs"] = hw_rec.get("epochs", 50)
            if model_variant:
                config["modelVariant"] = model_variant
            else:
                config.setdefault("modelVariant", hw_rec.get("modelVariant", "n"))
            config.setdefault("batchSize", hw_rec.get("batchSize", 16))
            config.setdefault("imageSize", hw_rec.get("imageSize", 640))
            config.setdefault("device", hw_rec.get("device", "cpu"))
            config.setdefault("trainingMode", hw_rec.get("trainingMode", "local"))
            config.setdefault("yoloVersion", hw_rec.get("yoloVersion", "v8"))
            if reusable_weight:
                config["reuseTrainingJobId"] = reusable_weight.get("id")
                config["baseWeightUri"] = reusable_weight.get("best_weight_path") or config.get("baseWeightUri")
                config["skipTrainingIfReused"] = True
                node["name"] = node.get("name") or "YOLO 训练"
                node.setdefault("_reuse_hint", f"复用已有权重: {reusable_weight.get('name')}")
        elif node.get("type") == "website_generator":
            config = node.setdefault("config", {})
            wizard = config.setdefault("wizard", {})
            if site_name:
                wizard["siteName"] = site_name
                node["name"] = f"生成 {site_name}"
            if reusable_weight and reusable_weight.get("id"):
                config.setdefault("trainingRunId", reusable_weight.get("id"))

    wf["_hardware_profile"] = profile
    wf["_yolo_training_recommendation"] = hw_rec
    if reusable_weight:
        wf["_reused_training_job_id"] = reusable_weight.get("id")
    return wf


def build_yolo_workflow_with_context(
    description: str,
    *,
    user_id: Optional[int] = None,
    client_capabilities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build YOLO workflow with hardware tuning and optional weight reuse."""
    from core.services.hardware_profile import merge_hardware_profile
    from .user_assets_context import pick_reusable_yolo_weight

    profile = merge_hardware_profile(client_capabilities)
    reusable = pick_reusable_yolo_weight(user_id, description)
    base = build_yolo_detection_workflow(description)
    return customize_yolo_workflow(
        base,
        description,
        hardware_profile=profile,
        reusable_weight=reusable,
    )


def build_yolo_detection_v2_workflow(description: str) -> Dict[str, Any]:
    """Build YOLO v2 AI role-agent workflow from user description."""
    base = load_yolo_v2_template_workflow()
    return customize_yolo_workflow(base, description)


def build_yolo_detection_workflow(description: str) -> Dict[str, Any]:
    """Build YOLO MLOps workflow — Site Factory v2 (AI 分工) is the default."""
    # Prefer full role-agent chain unless user explicitly wants a minimal train-only path
    lower = (description or "").lower()
    minimal_hints = ("只要训练", "只训练", "不要建站", "不需要网站", "train only", "no website")
    if any(h in lower for h in minimal_hints) and not is_yolo_v2_site_factory_intent(description):
        base = load_yolo_template_workflow()
        return customize_yolo_workflow(base, description)
    return build_yolo_detection_v2_workflow(description)


def should_use_yolo_v2_template(description: str) -> bool:
    """v2 is default for detection+site intents."""
    lower = (description or "").lower()
    if any(h in lower for h in ("只要训练", "只训练", "不要建站", "不需要网站", "train only", "no website")):
        return False
    return True


def should_use_yolo_template(description: str) -> bool:
    """Use template-based generation when YOLO intent is detected."""
    return is_yolo_detection_intent(description)


def aggregate_conversation_text(
    session_messages: List[Dict[str, Any]],
    user_message: str,
) -> str:
    """Combine session history with latest user message for intent/detail checks."""
    parts: List[str] = []
    for msg in session_messages or []:
        content = (msg.get("content") or "").strip()
        if content and msg.get("role") == "user":
            parts.append(content)
    if user_message.strip():
        parts.append(user_message.strip())
    return "\n".join(parts)


def yolo_chat_fallback_response(
    session_messages: List[Dict[str, Any]],
    user_message: str,
) -> Tuple[str, bool, List[str]]:
    """
    Rule-based YOLO conversation when LLM is unavailable.

    Returns (message, ready_to ? generate, suggestions).
    """
    combined = aggregate_conversation_text(session_messages, user_message)
    if not is_yolo_detection_intent(combined):
        return "", False, []

    if has_sufficient_yolo_detail(combined):
        summary_lines = [
            "根据您的描述，我理解您需要一套 **YOLO 目标检测全链路**：",
            "- 上传 YOLO 格式标注数据集",
            "- 本地 YOLOv8 训练（可配置 epochs / 模型规格）",
            "- 场景分析 → 自动生成识别网站 → 环境配置 → QA → 预览 → 项目 Agent",
            "",
            "若以上理解无误，请切换到「生成工作流」或回复「现在就生成工作流」。",
        ]
        suggestions = [
            "现在就生成工作流",
            "训练 50 个 epoch，网站名叫现场检测系统",
            "我还需要补充一些细节",
        ]
        return "\n".join(summary_lines), True, suggestions

    # Partial YOLO intent — ask clarifying questions
    questions = YOLO_CHAT_QUESTIONS[:3]
    message_parts = [
        "听起来您想搭建 **YOLO 目标检测 + 建站** 的 MLOps 工作流。为生成准确流程，请补充：",
        "",
    ]
    for i, q in enumerate(questions, 1):
        message_parts.append(f"{i}. {q}")
    message_parts.extend([
        "",
        "您也可以直接说明：数据集来源、训练参数、是否需要自动建站与 QA。",
    ])
    suggestions = [
        "我有 YOLO 数据集，需要训练并生成识别网站",
        "训练 30 epoch，站点名：工业缺陷检测",
        "只需要训练，不需要建站",
    ]
    return "\n".join(message_parts), False, suggestions
