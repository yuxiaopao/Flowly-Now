"""
NL2WF dialogue test matrix — multi-scenario, multi-turn conversation fixtures.

Used by scripts/nl2wf_dialogue_e2e.py and tests/backend/test_nl2wf_dialogue_matrix.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Single-turn: intent + subtype classification (no LLM required)
# ---------------------------------------------------------------------------

INTENT_SUBTYPE_CASES: List[Dict[str, Any]] = [
    # YOLO / MLOps
    {"id": "ST-Y01", "message": "我想做 YOLO 目标检测，训练完还要建站", "subtype": "yolo_detection", "intent": "chat"},
    {"id": "ST-Y02", "message": "ultralytics yolov8 本地训练识别网站", "subtype": "yolo_detection", "intent": "chat"},
    {"id": "ST-Y03", "message": "标注数据集上传后做物体检测 MLOps 全链路", "subtype": "yolo_detection", "intent": "chat"},
    # QA / 客服 — yolo 不应误判为 qa（无 yolo 关键词）
    {"id": "ST-Q01", "message": "帮我做一个 FAQ 问答机器人", "subtype": "qa_bot", "intent": "create"},
    {"id": "ST-Q02", "message": "智能客服自动回复用户问题", "subtype": "qa_bot", "intent": "chat"},
    {"id": "ST-Q03", "message": "问答机器人接收 webhook 问题并 LLM 回答", "subtype": "qa_bot", "intent": "chat"},
    # 邮件
    {"id": "ST-E01", "message": "用户注册后自动发送欢迎邮件", "subtype": "email_sending", "intent": "chat"},
    {"id": "ST-E02", "message": "send email notification when order completes", "subtype": "email_sending", "intent": "chat"},
    {"id": "ST-E03", "message": "定时发送报表邮件给 manager@company.com", "subtype": "email_sending", "intent": "chat"},
    # 数据处理
    {"id": "ST-D01", "message": "读取 CSV 清洗后输出 JSON", "subtype": "data_processing", "intent": "chat"},
    {"id": "ST-D02", "message": "ETL pipeline for excel data transformation", "subtype": "data_processing", "intent": "chat"},
    # 翻译
    {"id": "ST-T01", "message": "把英文文章翻译成中文", "subtype": "translation", "intent": "modify"},
    {"id": "ST-T02", "message": "multilingual translation workflow", "subtype": "translation", "intent": "chat"},
    # 审核
    {"id": "ST-M01", "message": "用户评论内容审核过滤敏感词", "subtype": "moderation", "intent": "chat"},
    {"id": "ST-M02", "message": "content moderation for UGC posts", "subtype": "moderation", "intent": "chat"},
    # 文章生成
    {"id": "ST-A01", "message": "根据主题自动生成博客文章", "subtype": "article_generation", "intent": "create"},
    # 客服（customer_service subtype via keywords）
    {"id": "ST-C01", "message": "售后工单 customer service 分流", "subtype": "customer_service", "intent": "chat"},
    # 修改 / 删除
    {"id": "ST-I01", "message": "把 LLM 节点改成 gpt-4", "subtype": "generic", "intent": "modify"},
    {"id": "ST-I02", "message": "删除第二个节点", "subtype": "generic", "intent": "delete"},
    {"id": "ST-I03", "message": "添加一个条件分支", "subtype": "generic", "intent": "modify"},
    # 闲聊
    {"id": "ST-G01", "message": "你好", "subtype": "generic", "intent": "chat"},
    {"id": "ST-G02", "message": "谢谢", "subtype": "generic", "intent": "chat"},
    # 生成指令
    {"id": "ST-GEN01", "message": "现在就生成工作流", "subtype": "generic", "intent": "create"},
    {"id": "ST-GEN02", "message": "开始生成", "subtype": "generic", "intent": "create"},
    # 边界：含「检测」但非 YOLO
    {"id": "ST-B01", "message": "检测用户输入是否为空然后发通知", "subtype": "generic", "intent": "chat"},
    # 边界：含「机器人」但 YOLO 优先
    {"id": "ST-B02", "message": "YOLO 检测机器人项目训练", "subtype": "yolo_detection", "intent": "chat"},
]

# ---------------------------------------------------------------------------
# Mock generation: aggregated description -> expected node types (offline)
# ---------------------------------------------------------------------------

GENERATION_CASES: List[Dict[str, Any]] = [
    {
        "id": "GEN-Y01",
        "description": "YOLO 目标检测 数据集 训练 30 epoch 识别网站",
        "must_have_types": ["dataset_upload", "yolo_training", "website_generator"],
        "must_not_have_types": [],
        "min_nodes": 8,
    },
    {
        "id": "GEN-Q01",
        "description": "做一个 FAQ 问答机器人，用户输入问题 LLM 回答",
        "must_have_types": ["llm", "input"],
        "must_not_have_types": ["yolo_training"],
        "min_nodes": 4,
    },
    {
        "id": "GEN-E01",
        "description": "新用户注册后 send email welcome notification smtp",
        "must_have_types": ["email"],
        "must_not_have_types": ["yolo_training"],
        "min_nodes": 4,
    },
    {
        "id": "GEN-D01",
        "description": "读取 CSV 数据清洗转换 ETL 输出",
        "must_have_types": ["tool"],
        "must_not_have_types": ["yolo_training"],
        "min_nodes": 4,
    },
    {
        "id": "GEN-T01",
        "description": "英文翻译成中文 translation workflow",
        "must_have_types": ["llm"],
        "must_not_have_types": ["yolo_training", "email"],
        "min_nodes": 3,
    },
    {
        "id": "GEN-M01",
        "description": "用户评论内容审核 moderation 过滤敏感内容",
        "must_have_types": ["llm"],
        "must_not_have_types": ["yolo_training"],
        "min_nodes": 3,
    },
    {
        "id": "GEN-CS01",
        "description": "customer service 售后工单 webhook 分流 LLM 分类",
        "must_have_types": ["llm"],
        "must_not_have_types": ["yolo_training"],
        "min_nodes": 3,
    },
    {
        "id": "GEN-A01",
        "description": "根据主题自动生成博客文章 article generation",
        "must_have_types": ["llm"],
        "must_not_have_types": ["yolo_training"],
        "min_nodes": 3,
    },
]

# ---------------------------------------------------------------------------
# Multi-turn dialogue flows (service-layer, offline mock LLM where needed)
# ---------------------------------------------------------------------------

DIALOGUE_FLOWS: List[Dict[str, Any]] = [
    {
        "id": "FLOW-YOLO-01",
        "title": "YOLO 两轮对话 + 生成指令",
        "turns": [
            {"role": "user", "content": "我想做 YOLO 目标检测，有标注数据集，训练后生成识别网站"},
            {"role": "assistant", "content": "请确认训练 epochs 和站点名称。"},
            {
                "role": "user",
                "content": "训练 30 epoch，网站名叫工业检测系统。现在就生成工作流",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["dataset_upload", "yolo_training", "project_profiler", "site_qa"],
            "min_nodes": 8,
            "forbidden_types": [],
        },
    },
    {
        "id": "FLOW-YOLO-02",
        "title": "YOLO 模糊首轮 + 规则对话兜底",
        "turns": [
            {"role": "user", "content": "我想做 yolo", "mode": "chat", "action": "chat_only"},
        ],
        "expect": {
            "chat_contains_any": ["YOLO", "数据集", "训练", "网站"],
            "ready_to_generate": False,
        },
    },
    {
        "id": "FLOW-QA-01",
        "title": "客服问答 生成模式",
        "turns": [
            {
                "role": "user",
                "content": "帮我做一个智能客服 FAQ 问答机器人，接收用户问题用 LLM 回答",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training", "dataset_upload"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-EMAIL-01",
        "title": "邮件自动化 对话后生成",
        "turns": [
            {"role": "user", "content": "订单完成后自动发邮件通知客户，SMTP 发送"},
            {"role": "assistant", "content": "请确认收件人和模板。"},
            {
                "role": "user",
                "content": "收件人 customer@example.com，主题订单完成。可以生成了",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["email"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-DATA-01",
        "title": "CSV 数据处理",
        "turns": [
            {
                "role": "user",
                "content": "上传 CSV 文件，清洗空值并转换格式后导出 JSON",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["tool"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-TRANS-01",
        "title": "翻译工作流",
        "turns": [
            {
                "role": "user",
                "content": "把用户输入的英文文本翻译成中文并输出",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training", "email"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-MOD-01",
        "title": "审核内容",
        "turns": [
            {
                "role": "user",
                "content": "审核用户提交的评论，检测敏感内容并标记",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-GREET-01",
        "title": "纯问候不应触发生成",
        "turns": [
            {"role": "user", "content": "你好", "mode": "chat", "action": "chat_only"},
        ],
        "expect": {
            "no_workflow": True,
            "ready_to_generate": False,
        },
    },
    {
        "id": "FLOW-GEN-CMD-01",
        "title": "仅生成指令无上下文",
        "turns": [
            {
                "role": "user",
                "content": "做一个定时发送报表邮件的工作流，每天 9 点发送。现在就生成工作流",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["email"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-MIX-01",
        "title": "英文 YOLO 描述",
        "turns": [
            {
                "role": "user",
                "content": "Build a YOLOv8 detection pipeline: upload dataset, train 50 epochs, deploy detection website",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["yolo_training", "dataset_upload"],
            "min_nodes": 8,
        },
    },
    {
        "id": "FLOW-NON-YOLO-01",
        "title": "含检测但非 YOLO — 不应走 MLOps 模板",
        "turns": [
            {
                "role": "user",
                "content": "检测表单字段是否合法，不合法则发邮件提醒管理员",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "forbidden_types": ["yolo_training", "dataset_upload"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-CS-01",
        "title": "售后客服 三轮澄清后生成",
        "turns": [
            {"role": "user", "content": "做一个 customer service 售后工单分流"},
            {"role": "assistant", "content": "请说明工单来源和分流规则。"},
            {"role": "user", "content": "来自 webhook，按优先级分给不同客服组"},
            {
                "role": "user",
                "content": "用 LLM 做初步分类。现在就生成工作流",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-ARTICLE-01",
        "title": "博客文章生成",
        "turns": [
            {
                "role": "user",
                "content": "根据用户输入的主题自动生成博客文章并输出 markdown",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training", "email"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-DATA-02",
        "title": "数据处理 两轮对话",
        "turns": [
            {"role": "user", "content": "我需要处理 Excel 数据"},
            {"role": "assistant", "content": "请说明输入格式和期望输出。"},
            {
                "role": "user",
                "content": "读取 excel 清洗空值后导出 JSON。可以生成了",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["tool"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-TRANS-02",
        "title": "翻译 深度思考后生成",
        "turns": [
            {"role": "user", "content": "多语言 translation workflow"},
            {"role": "assistant", "content": "请确认源语言和目标语言。"},
            {
                "role": "user",
                "content": "英文翻译成中文。现在就生成工作流",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training", "email"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-YOLO-03",
        "title": "YOLO 英文三轮",
        "turns": [
            {"role": "user", "content": "I need ultralytics YOLOv8 training"},
            {"role": "assistant", "content": "Do you have a labeled dataset?"},
            {"role": "user", "content": "Yes, YOLO format dataset uploaded"},
            {
                "role": "user",
                "content": "Train 40 epochs and deploy detection website. Generate now",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["yolo_training", "dataset_upload"],
            "min_nodes": 8,
        },
    },
    {
        "id": "FLOW-WEBHOOK-01",
        "title": "通用 webhook 触发",
        "turns": [
            {
                "role": "user",
                "content": "帮我设计一个 webhook 触发流程，收到 POST 后调用 LLM 并返回 JSON",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 3,
        },
    },
    {
        "id": "FLOW-EMAIL-02",
        "title": "欢迎邮件 单轮生成",
        "turns": [
            {
                "role": "user",
                "content": "用户注册后自动发送欢迎邮件 notification email",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["email"],
            "forbidden_types": ["yolo_training"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-QA-02",
        "title": "FAQ 深度思考两轮",
        "turns": [
            {"role": "user", "content": "想做一个 FAQ 问答机器人"},
            {"role": "assistant", "content": "请说明输入来源。"},
            {
                "role": "user",
                "content": "用户通过 webhook 提交问题，LLM 回答。现在就生成工作流",
                "mode": "chat",
                "action": "generate",
            },
        ],
        "expect": {
            "must_have_types": ["llm"],
            "forbidden_types": ["yolo_training", "dataset_upload"],
            "min_nodes": 4,
        },
    },
    {
        "id": "FLOW-BOUNDARY-01",
        "title": "检测输入非 YOLO",
        "turns": [
            {
                "role": "user",
                "content": "检测用户输入是否为空，为空则返回错误提示",
                "mode": "generate",
                "action": "generate",
            },
        ],
        "expect": {
            "forbidden_types": ["yolo_training", "dataset_upload"],
            "min_nodes": 3,
        },
    },
]

# Bulk single-message subtype samples for statistical coverage
BULK_SUBTYPE_SAMPLES: List[Dict[str, str]] = [
    {"id": f"BULK-{i:03d}", "message": msg, "subtype": sub}
    for i, (msg, sub) in enumerate([
        ("YOLO 训练 数据集 网站", "yolo_detection"),
        ("目标检测 ultralytics 建站", "yolo_detection"),
        ("FAQ 问答 bot", "qa_bot"),
        ("智能问答系统", "qa_bot"),
        ("发送邮件 smtp 通知", "email_sending"),
        ("email alert workflow", "email_sending"),
        ("csv 数据清洗 etl", "data_processing"),
        ("excel 批量处理", "data_processing"),
        ("翻译 多语言", "translation"),
        ("translation english chinese", "translation"),
        ("内容审核 敏感词", "moderation"),
        ("content filter moderation", "moderation"),
        ("写文章 博客", "article_generation"),
        ("customer service 售后", "customer_service"),
        ("帮我设计一个 webhook 触发流程", "generic"),
        ("定时任务 调用 API", "generic"),
        ("收集表单 写入数据库", "data_processing"),
        ("图片压缩 上传 OSS", "generic"),
        ("slack 通知 异常", "generic"),
        ("飞书 机器人 告警", "generic"),
        ("用户注册 welcome email", "email_sending"),
        ("定时报表邮件 manager", "email_sending"),
        ("webhook POST LLM 返回", "generic"),
        ("检测表单字段合法性", "generic"),
        ("敏感词过滤 moderation", "moderation"),
        ("YOLOv8 train deploy website", "yolo_detection"),
        ("标注数据集 物体检测 pipeline", "yolo_detection"),
        ("RAG 知识库问答", "qa_bot"),
        ("订单完成 send notification email", "email_sending"),
        ("JSON 数据转换 tool", "data_processing"),
        ("英文译中文 translation", "translation"),
        ("自动生成 文案 博客", "article_generation"),
        ("工单 售后 support", "customer_service"),
        ("Slack 告警 webhook", "generic"),
        ("图片 OCR 识别文字", "generic"),
        ("API 定时拉取数据", "data_processing"),
        ("PDF 解析 提取文本", "generic"),
        ("数据库备份 定时任务", "data_processing"),
        ("用户评论 审核 LLM", "moderation"),
    ], start=1)
]
