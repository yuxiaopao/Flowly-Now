"""
Emotion detection (facial expression) workflow helpers for NL2WF.

Routes NL prompts like「情绪检测系统」to the YOLO MLOps pipeline with
emotion-themed site copy and class labels (happy/sad/angry/neutral/surprise).
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .yolo_workflow import (
    _extract_epochs,
    _extract_model_variant,
    _extract_project_name,
    _extract_site_name,
    _normalize_text,
    aggregate_conversation_text,
    vueflow_to_nl_workflow,
)

logger = logging.getLogger(__name__)

EMOTION_TEMPLATE_SLUG = "emotion-detection-project"

EMOTION_STRONG_KEYWORDS: List[str] = [
    "情绪检测",
    "情绪识别",
    "情感检测",
    "情感识别",
    "面部表情",
    "表情识别",
    "人脸情绪",
    "面部情绪",
    "emotion detection",
    "emotion recognition",
    "facial emotion",
    "facial expression",
    "fer",
    "情绪检测系统",
    "情绪识别系统",
]

EMOTION_WEAK_KEYWORDS: List[str] = [
    "人脸",
    "面部",
    "表情",
    "happy",
    "sad",
    "angry",
    "neutral",
    "surprise",
    "训练",
    "数据集",
    "建站",
    "网站",
    "识别系统",
]

EMOTION_NEGATIVE_PHRASES: List[str] = [
    "文本情感",
    "评论情感",
    "nlp情感",
    "sentiment analysis",
    "情感分析服务",
    "用户评论",
    "文本情绪",
    "舆情",
]

EMOTION_PIPELINE_KEYWORDS: List[str] = [
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
    "yolo",
]

EMOTION_CHAT_QUESTIONS: List[str] = [
    "您的人脸表情数据集是 YOLO 标注格式，还是需要从上传开始？",
    "需要识别哪些情绪类别（如 happy / sad / angry / neutral / surprise）？",
    "训练完成后是否需要自动生成情绪识别网站（含 QA 与预览）？",
]

DEFAULT_EMOTION_CLASSES = ["happy", "sad", "angry", "neutral", "surprise"]


def is_emotion_detection_intent(text: str) -> bool:
    """True when user wants facial-emotion CV training + site, not text sentiment."""
    if not text or not text.strip():
        return False
    lower = _normalize_text(text)
    for phrase in EMOTION_NEGATIVE_PHRASES:
        if phrase.lower() in lower:
            if not any(kw in lower for kw in ("人脸", "面部", "yolo", "训练", "数据集", "facial")):
                return False
    for kw in EMOTION_STRONG_KEYWORDS:
        if kw.lower() in lower:
            return True
    weak_hits = sum(1 for kw in EMOTION_WEAK_KEYWORDS if kw.lower() in lower)
    if weak_hits >= 2 and any(k in lower for k in ("情绪", "情感", "表情", "emotion", "fer")):
        return True
    if "情绪" in lower and any(k in lower for k in ("检测", "识别", "训练", "系统", "网站")):
        return True
    return False


def emotion_intent_confidence(text: str) -> str:
    lower = _normalize_text(text)
    strong = sum(1 for kw in EMOTION_STRONG_KEYWORDS if kw.lower() in lower)
    if strong >= 2:
        return "high"
    if strong == 1:
        return "medium"
    if is_emotion_detection_intent(text):
        return "low"
    return "none"


def has_sufficient_emotion_detail(text: str) -> bool:
    if not is_emotion_detection_intent(text):
        return False
    lower = _normalize_text(text)
    pipeline_hits = sum(1 for kw in EMOTION_PIPELINE_KEYWORDS if kw in lower)
    if pipeline_hits >= 2 and len(text.strip()) >= 20:
        return True
    if emotion_intent_confidence(text) == "high" and len(text.strip()) >= 15:
        return True
    if "现在就生成" in text or "生成工作流" in text:
        if is_emotion_detection_intent(text):
            return True
    return False


def _fallback_emotion_workflow_nl() -> Dict[str, Any]:
    """Hardcoded NL-format emotion detection MLOps pipeline."""
    return {
        "name": "情绪检测系统",
        "description": "上传人脸表情数据集 → YOLO 训练 → 场景分析 → 情绪识别网站 → 环境 → QA → 预览 → Agent",
        "nodes": [
            {
                "id": "dataset_upload_1",
                "type": "dataset_upload",
                "name": "上传人脸表情数据集",
                "position": {"x": 80, "y": 200},
                "config": {
                    "format": "yolo",
                    "sourceType": "upload",
                    "classNames": DEFAULT_EMOTION_CLASSES,
                },
            },
            {
                "id": "yolo_training_1",
                "type": "yolo_training",
                "name": "情绪模型训练",
                "position": {"x": 280, "y": 200},
                "config": {
                    "trainingMode": "local",
                    "yoloVersion": "v8",
                    "modelVariant": "n",
                    "epochs": 50,
                    "batchSize": 16,
                    "imageSize": 640,
                    "dataSourceType": "upstream",
                    "classNames": DEFAULT_EMOTION_CLASSES,
                },
            },
            {
                "id": "project_profiler_1",
                "type": "project_profiler",
                "name": "情绪场景分析",
                "position": {"x": 480, "y": 200},
                "config": {
                    "websiteType": "detection",
                    "useLlmEnrich": False,
                    "wizardScenario": "面部表情情绪识别",
                },
            },
            {
                "id": "website_generator_1",
                "type": "website_generator",
                "name": "生成情绪识别网站",
                "position": {"x": 680, "y": 200},
                "config": {
                    "websiteType": "detection",
                    "projectType": "detection",
                    "framework": "ultralytics",
                    "frontendFramework": "vue",
                    "backendFramework": "flask",
                    "qaProfile": "default",
                    "wizard": {
                        "siteName": "情绪检测系统",
                        "usageDescription": "上传人脸照片，实时识别 happy / sad / angry / neutral / surprise 等情绪",
                        "primaryColor": "#8b5cf6",
                        "secondaryColor": "#6366f1",
                        "qaProfile": "default",
                        "websiteType": "detection",
                        "wizardCompleted": True,
                    },
                },
            },
            {
                "id": "environment_provision_1",
                "type": "environment_provision",
                "name": "环境配置",
                "position": {"x": 880, "y": 200},
                "config": {"runtimeMode": "desktop"},
            },
            {
                "id": "site_qa_1",
                "type": "site_qa",
                "name": "站点自查",
                "position": {"x": 1080, "y": 200},
                "config": {
                    "websiteType": "detection",
                    "qaProfile": "default",
                    "skipPlaywright": False,
                },
            },
            {
                "id": "site_preview_1",
                "type": "site_preview",
                "name": "站点预览",
                "position": {"x": 1280, "y": 200},
                "config": {"qaProfile": "default"},
            },
            {
                "id": "project_agent_1",
                "type": "project_agent",
                "name": "项目 Agent",
                "position": {"x": 1480, "y": 200},
                "config": {
                    "qaProfile": "default",
                    "autoQaAfterEdit": True,
                    "message": "",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "dataset_upload_1", "target": "yolo_training_1", "label": ""},
            {"id": "e2", "source": "yolo_training_1", "target": "project_profiler_1", "label": ""},
            {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1", "label": ""},
            {"id": "e4", "source": "website_generator_1", "target": "environment_provision_1", "label": ""},
            {"id": "e5", "source": "environment_provision_1", "target": "site_qa_1", "label": ""},
            {"id": "e6", "source": "site_qa_1", "target": "site_preview_1", "label": ""},
            {"id": "e7", "source": "site_preview_1", "target": "project_agent_1", "label": ""},
        ],
    }


def load_emotion_template_workflow() -> Dict[str, Any]:
    """Load emotion workflow from DB template or fallback."""
    try:
        from workflows.models import WorkflowTemplate

        template = WorkflowTemplate.objects.filter(
            name__icontains="情绪",
            is_active=True,
        ).first()
        if not template:
            template = WorkflowTemplate.objects.filter(
                tags__icontains="emotion",
                is_active=True,
            ).first()
        if template and template.workflow_data:
            wf = vueflow_to_nl_workflow(copy.deepcopy(template.workflow_data))
            wf["name"] = template.name or wf.get("name", "情绪检测系统")
            wf["description"] = template.description or wf.get("description", "")
            return wf
    except Exception as exc:
        logger.warning("Failed to load emotion template from DB: %s", exc)
    return copy.deepcopy(_fallback_emotion_workflow_nl())


def customize_emotion_workflow(workflow: Dict[str, Any], description: str) -> Dict[str, Any]:
    """Apply user-stated preferences from conversation text to the emotion template."""
    wf = copy.deepcopy(workflow)
    desc = description or ""

    project_name = _extract_project_name(desc)
    if project_name:
        wf["name"] = project_name
    elif is_emotion_detection_intent(desc) and not wf.get("name"):
        wf["name"] = "情绪检测系统"

    if desc.strip():
        wf["description"] = desc.strip()[:500]

    epochs = _extract_epochs(desc)
    site_name = _extract_site_name(desc)
    model_variant = _extract_model_variant(desc)

    for node in wf.get("nodes", []):
        ntype = node.get("type")
        config = node.setdefault("config", {})
        if ntype == "yolo_training":
            if epochs is not None:
                config["epochs"] = epochs
            if model_variant:
                config["modelVariant"] = model_variant
            config.setdefault("classNames", DEFAULT_EMOTION_CLASSES)
        elif ntype == "dataset_upload":
            config.setdefault("classNames", DEFAULT_EMOTION_CLASSES)
        elif ntype == "website_generator":
            wizard = config.setdefault("wizard", {})
            if site_name:
                wizard["siteName"] = site_name
                node["name"] = f"生成 {site_name}"
            wizard.setdefault("siteName", "情绪检测系统")
            wizard.setdefault("primaryColor", "#8b5cf6")
            wizard.setdefault(
                "usageDescription",
                "上传人脸照片，识别 happy / sad / angry / neutral / surprise 等情绪",
            )
        elif ntype == "project_profiler":
            config.setdefault("wizardScenario", "面部表情情绪识别")

    return wf


def build_emotion_detection_workflow(description: str) -> Dict[str, Any]:
    """Build a customized emotion-detection MLOps workflow from user description."""
    base = load_emotion_template_workflow()
    return customize_emotion_workflow(base, description)


def should_use_emotion_template(description: str) -> bool:
    """Use template-based generation when emotion CV intent is detected."""
    return is_emotion_detection_intent(description)


def emotion_chat_fallback_response(
    session_messages: List[Dict[str, Any]],
    user_message: str,
) -> Tuple[str, bool, List[str]]:
    """Rule-based emotion-detection conversation when LLM is unavailable."""
    combined = aggregate_conversation_text(session_messages, user_message)
    if not is_emotion_detection_intent(combined):
        return "", False, []

    if has_sufficient_emotion_detail(combined):
        summary_lines = [
            "根据您的描述，我理解您需要一套 **情绪检测全链路**：",
            "- 上传人脸表情 YOLO 标注数据集",
            "- 本地 YOLOv8 训练（实时曲线：loss / mAP / precision / recall）",
            "- 场景分析 → 自动生成情绪识别网站 → 环境配置 → QA → 预览 → 项目 Agent",
            "",
            "若以上理解无误，请切换到「生成工作流」或回复「现在就生成工作流」。",
        ]
        suggestions = [
            "现在就生成工作流",
            "训练 30 个 epoch，网站名叫情绪检测系统",
            "我还需要补充一些细节",
        ]
        return "\n".join(summary_lines), True, suggestions

    questions = EMOTION_CHAT_QUESTIONS[:3]
    message_parts = [
        "听起来您想搭建 **人脸情绪检测 + 建站** 的 MLOps 工作流。为生成准确流程，请补充：",
        "",
    ]
    for i, q in enumerate(questions, 1):
        message_parts.append(f"{i}. {q}")
    message_parts.extend([
        "",
        "您也可以直接说明：数据集来源、情绪类别、训练参数、是否需要自动建站。",
    ])
    suggestions = [
        "我有表情数据集，需要训练并生成情绪识别网站",
        "训练 20 epoch，站点名：情绪检测系统",
        "只需要训练，不需要建站",
    ]
    return "\n".join(message_parts), False, suggestions
