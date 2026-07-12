"""
Generate bulk subtype classification samples for NL2WF matrix tests.

Expands coverage beyond hand-written fixtures with templated utterances.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# (message_template_or_text, expected_subtype)
_TEMPLATES: List[Tuple[str, str]] = [
    # YOLO / CV
    ("YOLOv8 {n} epoch 训练 数据集 建站", "yolo_detection"),
    ("ultralytics 目标检测 识别网站", "yolo_detection"),
    ("物体检测 pipeline 标注数据集", "yolo_detection"),
    ("build yolo detection website mlops", "yolo_detection"),
    ("计算机视觉 模型训练 推理部署", "yolo_detection"),
    # QA
    ("{n}号 FAQ 问答机器人 webhook", "qa_bot"),
    ("智能客服 自动回答 用户问题", "qa_bot"),
    ("knowledge base Q&A bot llm", "qa_bot"),
    ("RAG 问答 知识库", "qa_bot"),
    # Email
    ("订单 {n} 完成 send email smtp", "email_sending"),
    ("用户注册 欢迎邮件 notification", "email_sending"),
    ("定时发送 报表邮件 manager", "email_sending"),
    ("alert email when error occurs", "email_sending"),
    # Data
    ("csv 数据清洗 转换 batch {n}", "data_processing"),
    ("excel etl 数据处理 pipeline", "data_processing"),
    ("json 数据转换 tool chain", "data_processing"),
    ("数据库 备份 定时任务", "data_processing"),
    # Translation
    ("英文 翻译 中文 translation {n}", "translation"),
    ("multilingual translation workflow", "translation"),
    ("把 用户输入 翻译成 英文", "translation"),
    # Moderation
    ("用户评论 内容审核 敏感词 {n}", "moderation"),
    ("content moderation filter ucg", "moderation"),
    ("违规检测 合规 检查", "moderation"),
    # Article
    ("根据主题 生成 博客 文章 {n}", "article_generation"),
    ("article generation 文案 创作", "article_generation"),
    # Customer service
    ("售后 工单 customer service {n}", "customer_service"),
    ("客服 分流 support ticket", "customer_service"),
    # Generic / integration
    ("webhook 触发 调用 API {n}", "generic"),
    ("定时任务 拉取 外部 接口", "generic"),
    ("slack 告警 通知 机器人", "generic"),
    ("飞书 消息 推送 workflow", "generic"),
    ("检测表单 字段 合法性 返回错误", "generic"),
    ("检测用户输入 是否为空 返回错误", "generic"),
    ("图片 OCR 识别 文字 输出", "generic"),
    ("pdf 解析 提取 文本", "generic"),
    ("收集 表单 写入 数据库", "data_processing"),
    ("http 请求 聚合 结果", "generic"),
]

# Extra fixed utterances (no template vars)
_FIXED: List[Tuple[str, str]] = [
    ("做一个智能问答系统 faq", "qa_bot"),
    ("send welcome email after signup", "email_sending"),
    ("process csv remove nulls export json", "data_processing"),
    ("moderation pipeline for comments", "moderation"),
    ("generate blog article from keywords", "article_generation"),
    ("yolo train dataset deploy site", "yolo_detection"),
    ("帮我设计 webhook POST 流程", "generic"),
    ("钉钉 机器人 告警 推送", "generic"),
    ("向量 检索 增强 问答", "qa_bot"),
    ("smtp 邮件 模板 通知", "email_sending"),
]


def generate_bulk_subtype_samples(start_id: int = 100, count: int = 100) -> List[Dict[str, str]]:
    """Return up to `count` bulk samples with ids BULK-{start_id:03d}+."""
    items: List[Tuple[str, str]] = []
    for tpl, sub in _TEMPLATES + _FIXED:
        for n in (1, 2, 3):
            msg = tpl.format(n=n) if "{n}" in tpl else tpl
            items.append((msg, sub))

    # Deduplicate by message while preserving order
    seen = set()
    unique: List[Tuple[str, str]] = []
    for msg, sub in items:
        key = (msg, sub)
        if key in seen:
            continue
        seen.add(key)
        unique.append((msg, sub))

    selected = unique[:count]
    return [
        {"id": f"BULK-{start_id + i:03d}", "message": msg, "subtype": sub}
        for i, (msg, sub) in enumerate(selected)
    ]
