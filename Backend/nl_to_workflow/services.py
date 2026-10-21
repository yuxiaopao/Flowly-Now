"""
NL to Workflow service for generating workflows from natural language.
"""

import copy
import json
import re
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Generator, Tuple
from django.conf import settings

from gateway.providers.registry import get_registry, register_default_providers, ProviderRegistry
from .constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    FALLBACK_MODEL,
    ERROR_MESSAGES,
    VALIDATION_MESSAGES,
    MODIFICATION_KEYWORDS,
    SUGGESTION_EXTRACTION_PATTERNS,
    SUPPORTED_NODE_TYPES,
    SUGGESTION_TEMPLATES,
    MAX_SUGGESTIONS,
    normalize_request_mode,
    resolve_initial_stream_mode,
    has_sufficient_workflow_detail,
    is_generate_command,
    FALLBACK_GRID_START_X, FALLBACK_GRID_START_Y,
    FALLBACK_GRID_SPACING_X, FALLBACK_GRID_SPACING_Y, FALLBACK_GRID_COLUMNS,
)
from .output_parser import WorkflowOutputParser
from .prompts import (
    WorkflowType,
    get_workflow_generation_prompt,
    format_workflow_prompt,
    get_modification_prompt,
    ConversationPrompt,
)
from .yolo_workflow import (
    aggregate_conversation_text,
    build_yolo_detection_workflow,
    has_sufficient_yolo_detail,
    is_yolo_detection_intent,
    should_use_yolo_template,
    yolo_chat_fallback_response,
)
from .emotion_workflow import (
    build_emotion_detection_workflow,
    emotion_chat_fallback_response,
    has_sufficient_emotion_detail,
    is_emotion_detection_intent,
    should_use_emotion_template,
)
from .node_config_normalize import normalize_node_config
from .multimodal_workflow import (
    build_multimodal_workflow,
    build_video_translation_workflow,
    is_multimodal_intent,
    is_video_translation_intent,
    multimodal_chat_fallback_response,
    should_use_multimodal_template,
    should_use_video_translation_template,
    wire_multimodal_workflow,
)
from .variable_wiring import wire_workflow_variable_refs
from .workflow_layout import auto_layout_workflow, is_layout_intent, pick_layout_direction
from .web_scrape_email_workflow import (
    build_web_scrape_email_workflow,
    web_scrape_email_chat_fallback_response,
    should_use_web_scrape_email_template,
    is_web_scrape_email_intent,
    has_sufficient_web_scrape_email_detail,
)
from .mobile_page_email_workflow import (
    build_mobile_page_email_workflow,
    mobile_page_email_chat_fallback_response,
    should_use_mobile_page_email_template,
    is_mobile_page_email_intent,
    has_sufficient_mobile_page_email_detail,
    extract_recipient_email,
)
from .agent_context import gather_generation_context, validate_generated_workflow_payload
from .conversation_memory import compress_messages_for_generation, should_summarize, summarize_messages
from .intelligence import (
    build_reference_context,
    classify_intent_with_llm,
    mark_llm_workflow,
    mark_offline_template,
    optimize_workflow_structure,
    plan_editor_action_with_llm,
    validation_error_text,
    OPTIMIZE_LLM_INSTRUCTION,
)

logger = logging.getLogger(__name__)

# Module-level constant for the workflow generation prompt template
# Using string concatenation instead of .format() to avoid brace escaping issues
FALLBACK_WORKFLOW_TEMPLATE = """
## 工作流结构要求

### 必须包含的节点
1. **start**: 开始节点 - 每个工作流只能有一个开始节点（自动放置在流程起点）
2. **end**: 结束节点 - 标记工作流结束（可以有多个）

### 可选节点类型（根据需求选择）
{node_types}

### 节点配置说明
- **LLM节点**: 必须指定 model（如 llama3, gpt-4, claude-3）
- **条件节点**: 必须配置 conditions 数组，指定判断字段和分支
- **工具节点**: 必须指定 tool_name 和 parameters
- **代码节点**: 必须提供可执行的代码

### 输出格式（必须是有效JSON）
请严格按照以下JSON格式输出，不要包含任何其他内容：

{{
    "name": "工作流名称（简洁、有意义）",
    "description": "工作流功能描述（1-2句话）",
    "nodes": [
        {{
            "id": "唯一ID（如 node_1, node_2...）",
            "type": "节点类型（start/end/input/llm/condition/tool/code/output）",
            "name": "节点显示名称",
            "position": {{"x": 数字, "y": 数字}},
            "config": {{
                // 节点类型相关的配置
                // LLM节点: {{"model": "模型名", "prompt": "提示词", "temperature": 0.7}}
                // 条件节点: {{"conditions": [{{"field": "字段", "operator": "equals", "value": "值"}}]}}
                // 工具节点: {{"tool_name": "工具名", "parameters": {{}}}}
            }}
        }}
    ],
    "edges": [
        {{
            "id": "唯一ID（如 edge_1, edge_2...）",
            "source": "源节点ID",
            "target": "目标节点ID",
            "label": "连线标签（如条件分支名称，可为空字符串）"
        }}
    ]
}}

## 工作流示例

### 示例1：简单顺序工作流（问答机器人）
输入：帮我做一个问答机器人，用户问问题，AI自动回答

输出：
{{
    "name": "智能问答机器人",
    "description": "接收用户问题，AI自动生成回答并返回",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 100}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "接收问题", "position": {{"x": 280, "y": 100}}, "config": {{"input_name": "user_question", "input_type": "text"}}}},
        {{"id": "node_3", "type": "llm", "name": "AI回答", "position": {{"x": 460, "y": 100}}, "config": {{"model": "llama3", "prompt": "你是一个专业的AI助手，请简洁准确地回答用户的问题：{{{{input.user_question}}}}", "temperature": 0.7}}}},
        {{"id": "node_4", "type": "output", "name": "返回结果", "position": {{"x": 640, "y": 100}}, "config": {{"format": "text"}}}},
        {{"id": "node_5", "type": "end", "name": "结束", "position": {{"x": 820, "y": 100}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}}
    ]
}}

### 示例2：条件分支工作流（评论处理）
输入：分析用户评论，如果是投诉就转人工，如果是表扬就回复感谢

输出：
{{
    "name": "评论智能分类处理",
    "description": "分析评论情感，自动分流处理投诉和表扬",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 150}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "接收评论", "position": {{"x": 280, "y": 150}}, "config": {{"input_name": "comment", "input_type": "text"}}}},
        {{"id": "node_3", "type": "llm", "name": "情感分析", "position": {{"x": 460, "y": 150}}, "config": {{"model": "llama3", "prompt": "分析以下评论的情感倾向，返回 positive 或 negative：{{{{input.comment}}}}", "temperature": 0.3}}}},
        {{"id": "node_4", "type": "condition", "name": "判断情感", "position": {{"x": 640, "y": 150}}, "config": {{"conditions": [{{"field": "sentiment", "operator": "equals", "value": "positive"}}]}}}},
        {{"id": "node_5", "type": "tool", "name": "回复感谢", "position": {{"x": 820, "y": 80}}, "config": {{"tool_name": "send_email", "parameters": {{"template": "thanks"}}}}}},
        {{"id": "node_6", "type": "tool", "name": "转人工", "position": {{"x": 820, "y": 220}}, "config": {{"tool_name": "transfer_to_agent", "parameters": {{}}}}}},
        {{"id": "node_7", "type": "output", "name": "处理完成", "position": {{"x": 1000, "y": 150}}, "config": {{"format": "json"}}}},
        {{"id": "node_8", "type": "end", "name": "结束", "position": {{"x": 1180, "y": 150}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": "表扬"}},
        {{"id": "edge_5", "source": "node_4", "target": "node_6", "label": "投诉"}},
        {{"id": "edge_6", "source": "node_5", "target": "node_7", "label": ""}},
        {{"id": "edge_7", "source": "node_6", "target": "node_7", "label": ""}},
        {{"id": "edge_8", "source": "node_7", "target": "node_8", "label": ""}}
    ]
}}

### 示例3：API调用工作流（数据获取）
输入：获取天气信息然后发送给用户

输出：
{{
    "name": "天气查询通知",
    "description": "查询指定城市的天气并发送给用户",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 150}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "输入城市", "position": {{"x": 280, "y": 150}}, "config": {{"input_name": "city", "input_type": "text", "placeholder": "请输入城市名称"}}}},
        {{"id": "node_3", "type": "tool", "name": "查询天气API", "position": {{"x": 460, "y": 150}}, "config": {{"tool_name": "http_request", "parameters": {{"url": "https://api.weather.com/v3/wx/conditions/current", "method": "GET", "headers": {{"Authorization": "Bearer xxx"}}}}}}}},
        {{"id": "node_4", "type": "code", "name": "格式化数据", "position": {{"x": 640, "y": 150}}, "config": {{"code": "def format_weather(data):\\n    return f'{{data.city}}今天气温{{data.temp}}度'"}}}}},
        {{"id": "node_5", "type": "output", "name": "发送结果", "position": {{"x": 820, "y": 150}}, "config": {{"format": "text"}}}},
        {{"id": "node_6", "type": "end", "name": "结束", "position": {{"x": 1000, "y": 150}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}},
        {{"id": "edge_5", "source": "node_5", "target": "node_6", "label": ""}}
    ]
}}

### 示例4：并行分支工作流（多任务处理）
输入：同时查询多个数据源并汇总结果

输出：
{{
    "name": "多源数据汇总",
    "description": "并行查询多个数据源并汇总结果",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 200}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "查询参数", "position": {{"x": 280, "y": 200}}, "config": {{"input_name": "query", "input_type": "text"}}}},
        {{"id": "node_3", "type": "tool", "name": "查询数据库", "position": {{"x": 460, "y": 100}}, "config": {{"tool_name": "db_query", "parameters": {{"sql": "SELECT * FROM products"}}}}}},
        {{"id": "node_4", "type": "tool", "name": "查询API", "position": {{"x": 460, "y": 200}}, "config": {{"tool_name": "http_request", "parameters": {{"url": "https://api.example.com/search"}}}}}},
        {{"id": "node_5", "type": "tool", "name": "查询缓存", "position": {{"x": 460, "y": 300}}, "config": {{"tool_name": "redis_get", "parameters": {{"key": "cache_key"}}}}}},
        {{"id": "node_6", "type": "llm", "name": "汇总结果", "position": {{"x": 640, "y": 200}}, "config": {{"model": "llama3", "prompt": "请汇总以下多个来源的数据，提取关键信息：{{{{input.data}}}}", "temperature": 0.3}}}},
        {{"id": "node_7", "type": "output", "name": "输出结果", "position": {{"x": 820, "y": 200}}, "config": {{"format": "json"}}}},
        {{"id": "node_8", "type": "end", "name": "结束", "position": {{"x": 1000, "y": 200}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": "数据库"}},
        {{"id": "edge_3", "source": "node_2", "target": "node_4", "label": "API"}},
        {{"id": "edge_4", "source": "node_2", "target": "node_5", "label": "缓存"}},
        {{"id": "edge_5", "source": "node_3", "target": "node_6", "label": ""}},
        {{"id": "edge_6", "source": "node_4", "target": "node_6", "label": ""}},
        {{"id": "edge_7", "source": "node_5", "target": "node_6", "label": ""}},
        {{"id": "edge_8", "source": "node_6", "target": "node_7", "label": ""}},
        {{"id": "edge_9", "source": "node_7", "target": "node_8", "label": ""}}
    ]
}}

### 示例5：循环处理工作流（批量处理）
输入：批量处理一批数据，对每条数据进行分析

输出：
{{
    "name": "批量数据处理",
    "description": "对批量数据进行逐条分析和统计",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 200}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "输入数据", "position": {{"x": 280, "y": 200}}, "config": {{"input_name": "data_batch", "input_type": "array"}}}},
        {{"id": "node_3", "type": "code", "name": "初始化计数器", "position": {{"x": 460, "y": 200}}, "config": {{"code": "count = 0\\nresults = []"}}}}},
        {{"id": "node_4", "type": "llm", "name": "分析单条数据", "position": {{"x": 640, "y": 200}}, "config": {{"model": "llama3", "prompt": "分析以下数据并返回关键信息：{{{{current_item}}}}", "temperature": 0.3}}}},
        {{"id": "node_5", "type": "code", "name": "收集结果", "position": {{"x": 820, "y": 200}}, "config": {{"code": "results.append(result)\\ncount += 1"}}}}},
        {{"id": "node_6", "type": "condition", "name": "检查是否完成", "position": {{"x": 1000, "y": 200}}, "config": {{"conditions": [{{"field": "count", "operator": "less_than", "value": "{{{{total_count}}}}"}}]}}}},
        {{"id": "node_7", "type": "output", "name": "输出汇总", "position": {{"x": 1180, "y": 200}}, "config": {{"format": "json"}}}},
        {{"id": "node_8", "type": "end", "name": "结束", "position": {{"x": 1360, "y": 200}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}},
        {{"id": "edge_5", "source": "node_5", "target": "node_6", "label": ""}},
        {{"id": "edge_6", "source": "node_6", "target": "node_4", "label": "继续"}},
        {{"id": "edge_7", "source": "node_6", "target": "node_7", "label": "完成"}},
        {{"id": "edge_8", "source": "node_7", "target": "node_8", "label": ""}}
    ]
}}

## 注意事项
1. 所有节点必须有唯一ID（建议使用 node_1, node_2, ...）
2. 所有连线必须有唯一ID（建议使用 edge_1, edge_2, ...）
3. 节点的 position 用于画布布局，x 表示水平位置，y 表示垂直位置
4. 使用 {{{{{variable}}}}} 语法引用变量
5. 只输出JSON，不要有其他内容
6. 避免创建循环依赖的工作流，否则会导致执行时无限循环

现在开始生成工作流（只输出JSON）："""


# ---------------------------------------------------------------------------
# Intent Analysis Keywords
# ---------------------------------------------------------------------------

INTENT_KEYWORDS = {
    'create': ['创建', '生成', '做一个', '帮我', '设计', 'build', 'create', 'generate', 'make', '新做', '做一下'],
    'modify': [
        '修改', '改一下', '把', '改成', '添加', '加上', '再加', '调整', '更新',
        'edit', 'modify', 'change', 'update', 'add',
        '增加', '增多', '增设', '新增', '加上', '加一个', '加个', '增加一个',
        '减少', '删掉', '删去', '删减', '去掉', '移除', '删除',
        '简化', '精简', '压缩', '合并', '拆分',
        '改成', '改称', '改为', '改成', '换个', '替换', '切换',
        '换掉', '重命名', '重新命名', '改名',
        '翻译成', '翻译成', '改成英文', '改成中文',
        '调整', '改动', '优化', '精简',
    ],
    'delete': [
        '删除', '移除', '不要', '去掉', 'delete', 'remove', 'drop',
        '删掉', '删掉', '删去', '去掉', '拿掉', '撤销', '取消',
        '清除', '清空', '丢弃',
    ],
}

# Workflow subtype detection keywords (emotion/yolo before qa_bot)
WORKFLOW_SUBTYPE_KEYWORDS = {
    'emotion_detection': [
        '情绪检测', '情绪识别', '情感检测', '情感识别', '面部表情', '表情识别',
        '人脸情绪', 'emotion detection', 'facial emotion', 'fer', '情绪检测系统',
    ],
    'yolo_detection': [
        'yolo', 'ultralytics', '目标检测', '物体检测', '识别项目',
        'yolo训练', 'yolo 训练', 'yolo检测', 'yolo 检测', 'bounding box',
        '计算机视觉', 'mlops', '识别网站', '检测模型',
    ],
    'qa_bot': ['问答', '问答机器人', 'faq', 'q&a', 'question', 'answer', '问题', '回答', 'qa bot'],
    'data_processing': ['数据', 'csv', 'excel', '处理', '清洗', '转换', 'etl', 'data', 'process', '文件处理'],
    'translation': ['翻译', 'translation', '多语言', 'language', '语言转换'],
    'moderation': ['审核', 'moderation', '过滤', 'content', '内容', '敏感', '检查', '合规'],
    'article_generation': ['文章', 'article', '生成文章', '写作', '写文章', '内容生成', '创作', '博客', '文案'],
    'customer_service': ['客服', 'customer service', 'support', '售后', '服务', '客户'],
    'email_sending': [
        '发邮件', '发送邮件', '发送email', '发email', '寄邮件',
        'send email', 'send a mail', 'email sending', '邮件发送',
        '发一封邮件', '发送一封邮件', '给我发邮件', 'send me',
        '邮件通知', '邮件提醒', '发送通知邮件', '自动发邮件',
        'smtp', '发件人', '收件人', '邮件模板', 'email template',
        'notification email', 'alert email', 'welcome email',
        'activation email', 'verification email', '邮件', 'email alert',
        '发邮箱', '发送邮箱',
    ],
    'cumcm': [
        'cumcm', '数学建模', '建模竞赛', '全国大学生数学建模', '大学生数学建模',
        '数学建模竞赛', '国赛数学建模', '建模论文', '灵敏度分析', '模型检验',
        'math modeling', 'mathematical modeling contest',
    ],
    'web_scrape_email': [
        '收集信息', '采集信息', '网站抓取', '网页抓取', '网站上', '从网站',
        'web scrape', 'scrape', '排版', '排版好', '排版之后',
    ],
    'mobile_page_email': [
        '手机网页', '移动端页面', '手机页面', 'h5页面', '响应式网页',
        'mobile page', 'mobile web', '手机网页详细', '详细手机网页',
        '手机端页面', '移动端网页',
    ],
    'generic': [],
}

# Retry/regenerate keywords
RETRY_KEYWORDS = ['重试', 'retry', '重新', 'regenerate', '再试', '再来', '重新生成', '再生成', 'try again']


def detect_workflow_subtype(message: str) -> str:
    """
    Detect workflow subtype from message.
    
    Args:
        message: User's message text
        
    Returns:
        Subtype: 'yolo_detection', 'qa_bot', 'data_processing', 'translation',
                 'moderation', 'article_generation', 'customer_service', or 'generic'
    """
    message_lower = message.lower()

    if is_web_scrape_email_intent(message):
        return 'web_scrape_email'

    if is_mobile_page_email_intent(message):
        return 'mobile_page_email'

    if is_emotion_detection_intent(message_lower):
        return 'emotion_detection'

    if is_yolo_detection_intent(message_lower):
        return 'yolo_detection'

    from nl_to_workflow.cumcm_enrichment import is_cumcm_intent
    if is_cumcm_intent(message):
        return 'cumcm'
    
    for subtype, keywords in WORKFLOW_SUBTYPE_KEYWORDS.items():
        if subtype == 'generic':
            continue
        for keyword in keywords:
            if keyword in message_lower:
                return subtype
    
    return 'generic'


def is_retry_intent(message: str) -> bool:
    """
    Detect if user wants to retry/regenerate.
    
    Args:
        message: User's message text
        
    Returns:
        True if retry intent detected
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in RETRY_KEYWORDS)


def analyze_intent(message: str) -> Dict[str, Any]:
    """
    Analyze user intent from message with enhanced subtype detection.
    
    Args:
        message: User's message text
        
    Returns:
        Dict with intent type, subtype, and retry flag
    """
    message_lower = message.lower()
    
    # Check for retry intent first
    is_retry = is_retry_intent(message_lower)
    
    # Check for delete intent first (most specific)
    for keyword in INTENT_KEYWORDS['delete']:
        if keyword in message_lower:
            return {
                'intent': 'delete',
                'subtype': detect_workflow_subtype(message_lower),
                'is_retry': is_retry
            }
    
    # Check for modify intent
    for keyword in INTENT_KEYWORDS['modify']:
        if keyword in message_lower:
            return {
                'intent': 'modify',
                'subtype': detect_workflow_subtype(message_lower),
                'is_retry': is_retry
            }
    
    # Check for create intent
    for keyword in INTENT_KEYWORDS['create']:
        if keyword in message_lower:
            return {
                'intent': 'create',
                'subtype': detect_workflow_subtype(message_lower),
                'is_retry': is_retry
            }
    
    return {
        'intent': 'chat',
        'subtype': detect_workflow_subtype(message_lower),
        'is_retry': is_retry
    }


# ---------------------------------------------------------------------------
# Node Position Calculator
# ---------------------------------------------------------------------------

def calculate_node_positions(
    node_count: int,
    start_x: int = FALLBACK_GRID_START_X,
    start_y: int = FALLBACK_GRID_START_Y,
    spacing_x: int = FALLBACK_GRID_SPACING_X,
    spacing_y: int = FALLBACK_GRID_SPACING_Y,
) -> List[Dict[str, int]]:
    """为缺少坐标的节点生成可用的网格位置。"""
    return [
        {
            'x': start_x + (index % FALLBACK_GRID_COLUMNS) * spacing_x,
            'y': start_y + (index // FALLBACK_GRID_COLUMNS) * spacing_y,
        }
        for index in range(max(0, node_count))
    ]


class NLToWorkflowService:
    """
    Service for converting natural language to workflow.

    Uses the provider registry to dynamically select an LLM provider
    based on the configured model. Supports Ollama (local), OpenAI,
    Anthropic, and any other registered provider.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        user=None,
    ):
        """
        Initialize NL to workflow service.

        Args:
            model: Model to use. If not provided, uses default from registry or settings.
            temperature: Sampling temperature for generation.
            max_tokens: Maximum tokens to generate.
            user: Django user for API key lookups.
        """
        self.model = model or getattr(settings, 'NL_WORKFLOW_MODEL', None)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.user = user
        self.client_capabilities: Optional[Dict[str, Any]] = None
        self._registry: Optional[ProviderRegistry] = None
        self._llm = None

    def __repr__(self):
        model = self._resolve_model()
        return f"<NLToWorkflowService model={model} temp={self.temperature}>"

    @property
    def registry(self) -> ProviderRegistry:
        """Lazy-initialized provider registry."""
        if self._registry is None:
            self._registry = get_registry()
            if not self._registry.get_all():
                register_default_providers()
        return self._registry

    def _get_provider_for_model(self, model: str):
        """Find the appropriate provider for a given model."""
        # Volcengine Ark / Doubao endpoint IDs (ep-xxxx) use OpenAI-compatible API
        if model and model.startswith('ep-'):
            openai_provider = self.registry.get('openai')
            if openai_provider:
                return openai_provider

        for name in self.registry.get_all():
            provider = self.registry.get(name)
            if provider and provider.supports_model(model):
                return provider
        return None

    @staticmethod
    def _normalize_stream_chunk(chunk) -> Dict[str, Any]:
        if isinstance(chunk, str):
            return json.loads(chunk)
        return chunk if isinstance(chunk, dict) else {}

    @staticmethod
    def _stream_chunk_error(chunk_data: Dict[str, Any]) -> Optional[str]:
        if chunk_data.get('type') == 'error':
            return chunk_data.get('error') or 'Unknown provider error'
        if chunk_data.get('error'):
            return chunk_data['error']
        return None

    @staticmethod
    def _format_provider_error(error: str) -> str:
        """Return user-friendly provider error with Volcengine hints when applicable."""
        text = str(error or '')
        lower = text.lower()
        if 'authenticationerror' in lower or 'api key format is incorrect' in lower:
            return (
                f"{text} — 请检查 Backend/.env 中 OPENAI_API_KEY（或 VOLCENGINE_API_KEY）"
                "是否为火山方舟「API Key 管理」中创建的密钥，且 endpoint 已在控制台开通。"
            )
        return text

    @staticmethod
    def _is_chat_generation_model(entry: Any, model_id: str) -> bool:
        """Return whether a provider model is suitable for NL workflow chat generation."""
        model_type = str(getattr(entry, 'model_type', 'chat') or 'chat').lower()
        normalized_id = (model_id or '').lower()
        non_chat_markers = (
            'embedding', 'embed', 'image', 'img', 'video', 'tts', 'whisper',
            'speech', 'audio', 'asr', 'ocr', 'rerank', 'moderation',
        )
        if model_type != 'chat':
            return False
        return not any(marker in normalized_id for marker in non_chat_markers)

    def _resolve_model(self) -> Optional[str]:
        """
        Resolve which model to use.
        Priority: instance model > settings default > first registry model with a live provider.
        """
        candidates: List[str] = []
        if self.model:
            candidates.append(self.model)
        default_model = getattr(settings, 'NL_WORKFLOW_MODEL', None)
        if default_model and default_model not in candidates:
            candidates.append(default_model)

        for model_id in candidates:
            if self._get_provider_for_model(model_id):
                return model_id

        try:
            for entry in self.registry.list_models():
                model_id = getattr(entry, 'model_id', None) or str(entry)
                if model_id and self._get_provider_for_model(model_id):
                    return model_id
        except Exception:
            pass

        return candidates[0] if candidates else None

    @property
    def llm(self):
        """Get the provider for the configured model."""
        if self._llm is not None:
            return self._llm

        model = self._resolve_model()
        if not model:
            logger.warning("No LLM model available for NL-to-workflow generation")
            return None

        provider = self._get_provider_for_model(model)
        if provider:
            self._llm = provider
            return provider

        provider_name = self.registry.find_provider_for_model(model)
        if provider_name:
            provider = self.registry.get(provider_name)
            if provider:
                self._llm = provider
                return provider

        # Last resort: first registered provider (Ollama local, etc.)
        for name in self.registry.get_all():
            provider = self.registry.get(name)
            if provider:
                logger.info("NL2WF using fallback provider %s (model %s unavailable)", name, model)
                self._llm = provider
                return provider

        return None

    def _prefer_llm_over_template(self) -> bool:
        """
        True when workflow should be designed by LLM autonomously.
        Templates are offline/dev fallback only (NL_WORKFLOW_USE_TEMPLATES=true).
        """
        if getattr(settings, 'NL_WORKFLOW_USE_TEMPLATES', False):
            return False
        return bool(self.llm)

    def _allow_offline_template(self) -> bool:
        """
        Offline domain templates are allowed only when:
        - forced via NL_WORKFLOW_USE_TEMPLATES, or
        - no LLM is available, or
        - explicit NL_WORKFLOW_TEMPLATE_FALLBACK after LLM failure.
        """
        if getattr(settings, 'NL_WORKFLOW_USE_TEMPLATES', False):
            return True
        if not self.llm:
            return True
        return bool(getattr(settings, 'NL_WORKFLOW_TEMPLATE_FALLBACK', False))

    def _stamp_offline_template(self, workflow: Optional[Dict[str, Any]], reason: str) -> Optional[Dict[str, Any]]:
        if not workflow:
            return None
        stamped = mark_offline_template(workflow, reason)
        stamped = self._normalize_workflow(stamped)
        stamped = self._validate_workflow(stamped)
        return self._attach_workflow_guidance(stamped)

    def resolve_intent(self, message: str) -> Dict[str, Any]:
        """
        AI-first intent: LLM structured classify when enabled, keyword fallback otherwise.
        Keyword-only analyze_intent() remains for tests / offline.
        """
        keyword = analyze_intent(message)
        use_llm = getattr(settings, 'NL_WORKFLOW_USE_LLM_INTENT', True) and bool(self.llm)
        if not use_llm:
            keyword['source'] = 'keyword'
            return keyword

        def _call(messages):
            return self._call_llm(messages, mock_description=message)

        llm_intent = classify_intent_with_llm(message, _call)
        if not llm_intent:
            keyword['source'] = 'keyword'
            return keyword

        # Keep keyword subtype if LLM returned generic and keywords found a domain
        if llm_intent.get('subtype') in (None, '', 'generic') and keyword.get('subtype') not in (None, '', 'generic'):
            llm_intent['subtype'] = keyword['subtype']
        llm_intent['is_retry'] = keyword.get('is_retry', False) or llm_intent.get('is_retry', False)
        return llm_intent

    def _template_fallback_workflow(self, description: str) -> Optional[Dict[str, Any]]:
        """Rule-based template fallback when LLM is unavailable or explicitly allowed."""
        workflow = None
        if should_use_emotion_template(description):
            workflow = self._build_emotion_workflow_from_description(description)
        elif should_use_yolo_template(description):
            workflow = self._build_yolo_workflow_from_description(
                description,
                context={'client_capabilities': self.client_capabilities},
            )
        elif should_use_video_translation_template(description):
            workflow = build_video_translation_workflow(description)
        elif should_use_multimodal_template(description):
            workflow = build_multimodal_workflow(description)
        elif should_use_web_scrape_email_template(description):
            workflow = build_web_scrape_email_workflow(description)
        elif should_use_mobile_page_email_template(description):
            workflow = build_mobile_page_email_workflow(description)
        else:
            from nl_to_workflow.short_drama_enrichment import (
                build_short_drama_workflow,
                is_short_drama_intent,
            )
            from nl_to_workflow.miao_embroidery_enrichment import (
                build_miao_embroidery_workflow,
                is_miao_embroidery_intent,
            )
            from nl_to_workflow.cumcm_enrichment import (
                build_cumcm_workflow,
                is_cumcm_intent,
            )
            if is_short_drama_intent(description):
                workflow = build_short_drama_workflow(description, shot_count=12)
            elif is_miao_embroidery_intent(description):
                workflow = build_miao_embroidery_workflow(description)
            elif is_cumcm_intent(description):
                workflow = build_cumcm_workflow(description)
        if workflow:
            return mark_offline_template(
                workflow,
                '无可用 LLM 或已启用离线模板模式，使用领域模板兜底（非智能生成）',
            )
        return workflow

    def _iter_llm_provider_models(self) -> List[Tuple[Any, str]]:
        """Yield (provider, model_id) candidates — configured model first, then registry, Ollama last."""
        seen: set = set()
        candidates: List[Tuple[Any, str]] = []

        def add(provider, model_id: str) -> None:
            key = (getattr(provider, 'name', id(provider)), model_id)
            if provider and model_id and key not in seen:
                seen.add(key)
                candidates.append((provider, model_id))

        primary_model = self._resolve_model()
        primary_provider = self.llm
        if primary_provider and primary_model:
            add(primary_provider, primary_model)
            if not getattr(settings, 'NL_WORKFLOW_TRY_ALL_MODELS', False):
                return candidates

        for name in self.registry.get_all():
            if name == 'ollama':
                continue
            provider = self.registry.get(name)
            if not provider:
                continue
            try:
                for entry in provider.list_models():
                    model_id = getattr(entry, 'model_id', None) or str(entry)
                    if not self._is_chat_generation_model(entry, model_id):
                        continue
                    add(provider, model_id)
            except Exception:
                continue

        ollama = self.registry.get('ollama')
        if ollama:
            try:
                for entry in ollama.list_models():
                    model_id = getattr(entry, 'model_id', None) or str(entry)
                    if not self._is_chat_generation_model(entry, model_id):
                        continue
                    add(ollama, model_id)
            except Exception:
                add(ollama, 'llama3.2:latest')

        return candidates

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        mock_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call the LLM through the provider registry.
        Falls back to mock response only when NL_WORKFLOW_USE_MOCK is enabled.

        Returns a dict with 'content' (response text) or 'error'.
        """
        if not self.registry.get_all():
            register_default_providers()

        candidates = self._iter_llm_provider_models()
        if not candidates:
            nl_debug_mode = getattr(settings, 'NL_WORKFLOW_USE_MOCK', False)
            use_mock = nl_debug_mode

            if use_mock:
                user_description = (mock_description or '').strip()
                if not user_description:
                    for msg in messages:
                        if msg.get('role') == 'user':
                            user_description = msg.get('content', '')
                            break

                from .constants import get_mock_workflow
                mock_workflow = get_mock_workflow(user_description)
                mock_workflow.setdefault('_generation_mode', 'mock')
                return {'content': json.dumps(mock_workflow)}

            return {'error': ERROR_MESSAGES['no_provider']}

        errors: List[str] = []
        for provider, model in candidates:
            try:
                chat_kwargs: Dict[str, Any] = {}
                if getattr(provider, 'provider_name', '') == 'ollama':
                    chat_kwargs['num_ctx'] = 4096
                max_tokens = min(self.max_tokens, 4096)
                if str(model).startswith('agnes-'):
                    max_tokens = min(max(self.max_tokens, 8192), 16384)
                response = provider.chat(
                    messages=messages,
                    model=model,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    **chat_kwargs,
                )
                if getattr(response, 'error', None):
                    err = self._format_provider_error(response.error)
                    errors.append(f'{model}: {err}')
                    logger.warning('NL2WF LLM candidate failed (%s): %s', model, err)
                    continue
                content = getattr(response, 'content', None) or ''
                if content.strip():
                    logger.info('NL2WF LLM succeeded with model=%s provider=%s', model, type(provider).__name__)
                    return {'content': content, '_llm_model': model}
                finish_reason = getattr(response, 'finish_reason', None) or 'unknown'
                output_tokens = getattr(response, 'output_tokens', None) or 0
                raw_response = getattr(response, 'raw_response', None) or {}
                reasoning_tokens = 0
                try:
                    details = raw_response.get('usage', {}).get('completion_tokens_details', {})
                    reasoning_tokens = details.get('reasoning_tokens') or 0
                except AttributeError:
                    reasoning_tokens = 0
                empty_error = (
                    f'{model}: provider returned empty chat content '
                    f'(finish_reason={finish_reason}, output_tokens={output_tokens}, '
                    f'reasoning_tokens={reasoning_tokens})'
                )
                errors.append(empty_error)
                logger.warning('NL2WF LLM candidate returned empty content: %s', empty_error)
            except Exception as exc:
                err = str(exc)
                errors.append(f'{model}: {err}')
                logger.warning('NL2WF LLM candidate exception (%s): %s', model, err)

        return {'error': ERROR_MESSAGES['llm_call_failed'].format(error='; '.join(errors[:3]))}

    def _stream_llm(
        self,
        messages: List[Dict[str, str]],
        mock_description: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream LLM response through the provider registry."""
        provider = self.llm
        model = self._resolve_model()

        if not provider:
            nl_debug_mode = getattr(settings, 'NL_WORKFLOW_USE_MOCK', False)
            use_mock = nl_debug_mode

            if use_mock:
                from .constants import get_mock_workflow
                user_description = (mock_description or '').strip()
                if not user_description:
                    for msg in messages:
                        if msg.get('role') == 'user':
                            user_description = msg.get('content', '')
                            break
                mock_workflow = get_mock_workflow(user_description)
                yield json.dumps({'type': 'content', 'content': json.dumps(mock_workflow)})
                return

            yield json.dumps({'error': ERROR_MESSAGES['no_provider']})
            return

        try:
            for chunk in provider.stream_chat(
                messages=messages,
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                chunk_data = self._normalize_stream_chunk(chunk)
                stream_error = self._stream_chunk_error(chunk_data)
                if stream_error:
                    yield json.dumps({'type': 'error', 'error': self._format_provider_error(stream_error)})
                    return
                yield json.dumps(chunk_data)
        except Exception as e:
            logger.exception(f"LLM stream failed: {e}")
            yield json.dumps({'error': str(e)})

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all models available for NL-to-workflow generation."""
        models = []
        seen = set()
        for m in self.registry.list_models():
            if m.model_type == 'chat' and m.model_id not in seen:
                seen.add(m.model_id)
                models.append({
                    'model_id': m.model_id,
                    'name': m.name,
                    'provider': m.provider,
                    'max_tokens': m.max_tokens,
                    'supports_streaming': m.supports_streaming,
                    'context_window': m.context_window,
                })

        # Ensure Volcengine catalog appears when Ark is configured
        base_url = getattr(settings, 'OPENAI_BASE_URL', '') or ''
        if 'volces.com' in base_url and getattr(settings, 'OPENAI_API_KEY', ''):
            from .constants import VOLCENGINE_ARK_CHAT_MODELS
            for item in VOLCENGINE_ARK_CHAT_MODELS:
                if item['model_id'] not in seen:
                    seen.add(item['model_id'])
                    models.insert(0, dict(item))

        return models

    def _attach_workflow_guidance(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach email and node config guidance metadata to workflow."""
        email_guidance = get_email_config_guidance(workflow_data)
        if email_guidance:
            workflow_data['_email_guidance'] = email_guidance
        node_guidance = get_node_config_guidance(workflow_data)
        if node_guidance:
            workflow_data['_node_guidance'] = node_guidance
        return workflow_data

    def _build_yolo_workflow_from_description(
        self,
        description: str,
        include_validation: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build and normalize a YOLO MLOps workflow from user description."""
        from nl_to_workflow.yolo_workflow import build_yolo_workflow_with_context

        user_id = getattr(self.user, 'id', None) if self.user else None
        client_caps = (context or {}).get('client_capabilities') or self.client_capabilities
        workflow_data = build_yolo_workflow_with_context(
            description,
            user_id=user_id,
            client_capabilities=client_caps,
        )
        workflow_data = self._normalize_workflow(workflow_data)
        if include_validation:
            workflow_data = self._validate_workflow(workflow_data)
        return self._attach_workflow_guidance(workflow_data)

    def _build_emotion_workflow_from_description(
        self,
        description: str,
        include_validation: bool = True,
    ) -> Dict[str, Any]:
        """Build and normalize an emotion-detection MLOps workflow from user description."""
        workflow_data = build_emotion_detection_workflow(description)
        workflow_data = self._normalize_workflow(workflow_data)
        if include_validation:
            workflow_data = self._validate_workflow(workflow_data)
        return self._attach_workflow_guidance(workflow_data)

    def _build_web_scrape_email_workflow_from_description(
        self,
        description: str,
        include_validation: bool = True,
    ) -> Dict[str, Any]:
        """Build website scrape → format → email workflow from user description."""
        workflow_data = build_web_scrape_email_workflow(description)
        workflow_data = self._normalize_workflow(workflow_data)
        if include_validation:
            workflow_data = self._validate_workflow(workflow_data)
        return self._attach_workflow_guidance(workflow_data)

    def _build_multimodal_workflow_from_description(
        self,
        description: str,
        *,
        include_validation: bool = True,
    ) -> Dict[str, Any]:
        """Build text/image/video pipeline with wired variable references."""
        workflow_data = build_multimodal_workflow(description)
        workflow_data = self._normalize_workflow(workflow_data)
        if include_validation:
            workflow_data = self._validate_workflow(workflow_data)
        return self._attach_workflow_guidance(workflow_data)

    def generate_workflow(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        include_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Generate workflow from natural language description.

        AI-first: LLM designs the graph with retry-on-validation-error.
        Domain templates are only used offline / when explicitly enabled.
        """
        context = dict(context or {})
        user_id = getattr(self.user, 'id', None) if self.user else context.get('user_id')
        if not context.get('reference_context'):
            context['reference_context'] = build_reference_context(description, user_id=user_id)
        context = self._enrich_context_with_agent_tools(description, context, user_id=user_id)

        # Deterministic domain pipelines (structured multi-stage graphs)
        from nl_to_workflow.short_drama_enrichment import (
            build_short_drama_workflow,
            is_short_drama_intent,
        )
        if is_short_drama_intent(description):
            workflow_data = build_short_drama_workflow(description, shot_count=12)
            workflow_data = self._normalize_workflow(workflow_data)
            if include_validation:
                workflow_data = self._validate_workflow(workflow_data)
            return self._attach_workflow_guidance(workflow_data)

        from nl_to_workflow.miao_embroidery_enrichment import (
            build_miao_embroidery_workflow,
            is_miao_embroidery_intent,
        )
        if is_miao_embroidery_intent(description):
            workflow_data = build_miao_embroidery_workflow(description)
            workflow_data = self._normalize_workflow(workflow_data)
            if include_validation:
                workflow_data = self._validate_workflow(workflow_data)
            return self._attach_workflow_guidance(workflow_data)

        from nl_to_workflow.cumcm_enrichment import (
            build_cumcm_workflow,
            is_cumcm_intent,
        )
        if is_cumcm_intent(description):
            workflow_data = build_cumcm_workflow(description)
            workflow_data = self._normalize_workflow(workflow_data)
            if include_validation:
                workflow_data = self._validate_workflow(workflow_data)
            return self._attach_workflow_guidance(workflow_data)

        # Forced / offline template path (no LLM)
        if not self._prefer_llm_over_template():
            fallback = self._template_fallback_workflow(description)
            if fallback:
                logger.info('Using offline template (LLM unavailable or USE_TEMPLATES=true)')
                return self._stamp_offline_template(
                    fallback,
                    fallback.get('_intelligence_note')
                    or '无可用 LLM，使用离线模板兜底（非智能生成）',
                ) or fallback
            return {
                'error': ERROR_MESSAGES.get('no_provider', '无可用模型'),
                'name': 'Generated Workflow',
                'description': description,
                'nodes': [],
                'edges': [],
                '_is_intelligent': False,
            }

        max_retries = max(0, int(getattr(settings, 'NL_WORKFLOW_GENERATE_RETRIES', 2)))
        last_error = None
        last_model = None

        for attempt in range(max_retries + 1):
            prompt = self._create_workflow_generation_prompt(description, context)
            if last_error:
                prompt = (
                    f"{prompt}\n\n"
                    f"【重要】上一轮生成失败（第 {attempt} 次重试），请根据错误修复并输出完整合法工作流 JSON：\n"
                    f"{last_error}"
                )

            result = self._call_llm(
                [{"role": "user", "content": prompt}],
                mock_description=description,
            )

            if 'error' in result:
                last_error = result['error']
                logger.warning(
                    'LLM workflow generation attempt %s failed: %s',
                    attempt + 1,
                    last_error,
                )
                continue

            last_model = result.get('_llm_model')
            workflow_data = WorkflowOutputParser.parse_workflow(result['content'])

            if 'error' in workflow_data:
                last_error = workflow_data['error']
                logger.warning(
                    'LLM workflow parse attempt %s failed: %s',
                    attempt + 1,
                    last_error,
                )
                continue

            workflow_data = self._normalize_workflow(workflow_data)
            if include_validation:
                workflow_data = WorkflowOutputParser.validate_workflow(workflow_data)
                err_text = validation_error_text(workflow_data)
                # Hard failure: empty nodes
                if not (workflow_data.get('nodes') or []):
                    last_error = err_text or '生成结果缺少节点'
                    continue
                if err_text and attempt < max_retries:
                    last_error = err_text
                    continue

            workflow_data = self._apply_agent_validation(workflow_data)
            agent_validation = workflow_data.get('_agent_validation') or {}
            if (
                agent_validation.get('errors')
                and not agent_validation.get('valid', True)
                and attempt < max_retries
            ):
                last_error = '; '.join(agent_validation['errors'])
                continue

            workflow_data = mark_llm_workflow(workflow_data, model=last_model)
            return self._attach_workflow_guidance(workflow_data)

        # Explicit opt-in only — never silent dead-template substitution by default
        if self._allow_offline_template() and getattr(settings, 'NL_WORKFLOW_TEMPLATE_FALLBACK', False):
            fallback = self._template_fallback_workflow(description)
            if fallback:
                logger.warning(
                    'LLM generation exhausted retries (%s); using offline template fallback',
                    last_error,
                )
                return self._stamp_offline_template(
                    fallback,
                    f'LLM 生成失败后启用离线模板兜底：{last_error}',
                ) or fallback

        return {
            'error': last_error or ERROR_MESSAGES.get('generation_failed', '工作流生成失败'),
            'name': 'Generated Workflow',
            'description': description,
            'nodes': [],
            'edges': [],
            '_is_intelligent': False,
            '_generation_mode': 'llm_failed',
        }

    def generate_workflow_streaming(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """
        Generate workflow with streaming output and progress updates.
        
        Yields JSON-serialized progress messages and final workflow.
        
        Args:
            description: User's natural language description
            context: Additional context for generation
            
        Yields:
            JSON-serialized dicts with progress updates and final workflow
        """
        # Initial progress
        yield json.dumps({
            'type': 'progress',
            'stage': 'starting',
            'message': '正在理解您的需求...',
            'progress': 10
        })

        context = dict(context or {})
        user_id = getattr(self.user, 'id', None) if self.user else context.get('user_id')
        if not context.get('reference_context'):
            context['reference_context'] = build_reference_context(description, user_id=user_id)
        context = self._enrich_context_with_agent_tools(description, context, user_id=user_id)

        from nl_to_workflow.cumcm_enrichment import build_cumcm_workflow, is_cumcm_intent
        if is_cumcm_intent(description):
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '检测到 CUMCM 数学建模需求，正在生成完整流水线...',
                'progress': 55,
            })
            workflow_data = build_cumcm_workflow(description)
            workflow_data = self._normalize_workflow(workflow_data)
            workflow_data = self._validate_workflow(workflow_data)
            workflow_data = self._attach_workflow_guidance(workflow_data)
            yield json.dumps({'type': 'workflow', 'workflow': workflow_data})
            yield json.dumps({
                'type': 'done',
                'message': f"已生成 CUMCM 工作流: {workflow_data.get('name', '未命名')}",
                'workflow': workflow_data,
                'progress': 100,
            })
            return

        if not self._prefer_llm_over_template() and should_use_web_scrape_email_template(description):
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '无 LLM，使用离线模板生成（非智能）...',
                'progress': 60,
            })
            tpl_workflow = self._stamp_offline_template(
                self._build_web_scrape_email_workflow_from_description(description),
                '无可用 LLM，使用离线模板兜底（非智能生成）',
            )
            yield json.dumps({'type': 'workflow', 'workflow': tpl_workflow})
            yield json.dumps({
                'type': 'done',
                'message': f"已生成工作流（离线模板）: {tpl_workflow.get('name', '未命名')}",
                'workflow': tpl_workflow,
                'progress': 100,
            })
            return

        if not self._prefer_llm_over_template() and should_use_video_translation_template(description):
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '无 LLM，使用离线模板生成（非智能）...',
                'progress': 60,
            })
            tpl_workflow = self._stamp_offline_template(
                build_video_translation_workflow(description),
                '无可用 LLM，使用离线模板兜底（非智能生成）',
            )
            yield json.dumps({'type': 'workflow', 'workflow': tpl_workflow})
            yield json.dumps({
                'type': 'done',
                'message': f"已生成工作流（离线模板）: {tpl_workflow.get('name', '未命名')}",
                'workflow': tpl_workflow,
                'progress': 100,
            })
            return

        if not self._prefer_llm_over_template() and should_use_multimodal_template(description):
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '无 LLM，使用离线模板生成（非智能）...',
                'progress': 40,
            })
            fallback = self._template_fallback_workflow(description)
            tpl_workflow = self._stamp_offline_template(
                fallback or build_multimodal_workflow(description),
                '无可用 LLM，使用离线模板兜底（非智能生成）',
            )
            yield json.dumps({'type': 'workflow', 'workflow': tpl_workflow})
            yield json.dumps({
                'type': 'done',
                'message': f"已生成工作流（离线模板）: {tpl_workflow.get('name', '未命名')}",
                'workflow': tpl_workflow,
                'progress': 100,
            })
            return

        yield json.dumps({
            'type': 'progress',
            'stage': 'generating',
            'message': 'AI 正在自主设计工作流结构...',
            'progress': 35,
        })

        messages = [
            {"role": "user", "content": self._create_workflow_generation_prompt(description, context)}
        ]
        
        # Yield parsing progress
        yield json.dumps({
            'type': 'progress',
            'stage': 'generating',
            'message': '正在生成工作流结构...',
            'progress': 30
        })
        
        provider = self.llm
        model = self._resolve_model()
        
        if not provider:
            # Use mock mode
            nl_debug_mode = getattr(settings, 'NL_WORKFLOW_USE_MOCK', False)
            use_mock = nl_debug_mode
            
            if use_mock:
                from .constants import get_mock_workflow
                mock_workflow = get_mock_workflow(description)
                mock_workflow = self._normalize_workflow(mock_workflow)
                mock_workflow = self._validate_workflow(mock_workflow)
                mock_workflow.setdefault('_generation_mode', 'mock')
                
                yield json.dumps({
                    'type': 'progress',
                    'stage': 'validating',
                    'message': '正在验证工作流结构...',
                    'progress': 70
                })
                
                email_guidance = get_email_config_guidance(mock_workflow)
                if email_guidance:
                    mock_workflow['_email_guidance'] = email_guidance

                node_guidance = get_node_config_guidance(mock_workflow)
                if node_guidance:
                    mock_workflow['_node_guidance'] = node_guidance
                
                yield json.dumps({
                    'type': 'progress',
                    'stage': 'complete',
                    'message': '工作流生成完成',
                    'progress': 100
                })
                yield json.dumps({'type': 'workflow', 'workflow': mock_workflow})
                yield json.dumps({
                    'type': 'done',
                    'message': f"已生成工作流: {mock_workflow.get('name', '未命名')}",
                    'workflow': mock_workflow,
                    'progress': 100,
                })
                return

            fallback = self._template_fallback_workflow(description)
            if fallback:
                fallback = self._stamp_offline_template(
                    fallback,
                    '无可用 LLM，使用离线模板兜底（非智能生成）',
                )
                yield json.dumps({'type': 'workflow', 'workflow': fallback})
                yield json.dumps({
                    'type': 'done',
                    'message': f"已生成工作流（离线模板）: {fallback.get('name', '未命名')}",
                    'workflow': fallback,
                    'progress': 100,
                })
                return

        try:
            full_content = ""
            generation_progress = 45

            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': 'AI 正在生成节点和连线...',
                'progress': 40
            })

            for chunk in provider.stream_chat(
                messages=messages,
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                chunk_data = self._normalize_stream_chunk(chunk)

                stream_error = self._stream_chunk_error(chunk_data)
                if stream_error:
                    yield json.dumps({'type': 'error', 'error': self._format_provider_error(stream_error)})
                    return

                content = chunk_data.get('content', '')
                if content:
                    full_content += content
                    generation_progress = min(88, generation_progress + 1)
                    yield json.dumps({
                        'type': 'token',
                        'content': content,
                        'progress': generation_progress,
                    })

                if chunk_data.get('type') == 'done':
                    yield json.dumps({
                        'type': 'progress',
                        'stage': 'parsing',
                        'message': '正在解析工作流...',
                        'progress': 60
                    })
            
            # Parse and validate using structured output parser
            workflow_data = WorkflowOutputParser.parse_workflow(full_content)
            
            if 'error' in workflow_data:
                yield json.dumps({
                    'type': 'progress',
                    'stage': 'repairing',
                    'message': '首轮解析失败，AI 正在自动修图重试...',
                    'progress': 65,
                })
                repaired = self.generate_workflow(description, context=context, include_validation=True)
                if repaired.get('error') or not repaired.get('nodes'):
                    yield json.dumps({
                        'type': 'error',
                        'error': repaired.get('error') or workflow_data.get('error'),
                    })
                    return
                workflow_data = repaired
            else:
                yield json.dumps({
                    'type': 'progress',
                    'stage': 'validating',
                    'message': '正在验证工作流...',
                    'progress': 80
                })
                workflow_data = self._normalize_workflow(workflow_data)
                workflow_data = WorkflowOutputParser.validate_workflow(workflow_data)
                err_text = validation_error_text(workflow_data)
                if err_text or not workflow_data.get('nodes'):
                    yield json.dumps({
                        'type': 'progress',
                        'stage': 'repairing',
                        'message': '校验未通过，AI 正在自动修图...',
                        'progress': 85,
                    })
                    repaired = self.generate_workflow(description, context=context, include_validation=True)
                    if repaired.get('nodes') and not repaired.get('error'):
                        workflow_data = repaired
                workflow_data = mark_llm_workflow(workflow_data)

            workflow_data = self._apply_agent_validation(workflow_data)

            # Attach email and node guidance to workflow data BEFORE yielding
            # This ensures guidance is persisted when session.workflow_json is saved
            email_guidance = get_email_config_guidance(workflow_data)
            if email_guidance:
                workflow_data['_email_guidance'] = email_guidance

            node_guidance = get_node_config_guidance(workflow_data)
            if node_guidance:
                workflow_data['_node_guidance'] = node_guidance

            yield json.dumps({
                'type': 'progress',
                'stage': 'complete',
                'message': '工作流生成完成',
                'progress': 100
            })

            yield json.dumps({
                'type': 'workflow',
                'workflow': workflow_data
            })

            # Yield email config guidance for UI (already in workflow_data)
            if email_guidance:
                yield json.dumps({
                    'type': 'email_guidance',
                    'email_guidance': email_guidance
                })

            # Yield general node config guidance for UI
            if node_guidance:
                yield json.dumps({
                    'type': 'node_guidance',
                    'node_guidance': node_guidance
                })

            yield json.dumps({
                'type': 'done',
                'message': f"已生成工作流: {workflow_data.get('name', '未命名')}",
                'workflow': workflow_data,
                'progress': 100
            })
            
        except Exception as e:
            logger.exception(f"Streaming workflow generation failed: {e}")
            yield json.dumps({
                'type': 'error',
                'error': str(e)
            })

    def _enrich_context_with_agent_tools(
        self,
        description: str,
        context: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Merge local ReAct tool retrieval into generation context (reference only)."""
        context = dict(context or {})
        if context.get('agent_context_text') or not getattr(settings, 'NL_WORKFLOW_USE_AGENT_CONTEXT', True):
            return context
        try:
            gathered = gather_generation_context(
                description,
                user_id=user_id,
                session_id=context.get('session_id'),
            )
            text = (gathered or {}).get('text') or ''
            extra_parts: List[str] = []
            client_caps = context.get('client_capabilities') or self.client_capabilities
            if client_caps or getattr(settings, 'NL_WORKFLOW_USE_HARDWARE_PROFILE', True):
                try:
                    from core.services.hardware_profile import build_nl_hardware_context_text, merge_hardware_profile
                    extra_parts.append(build_nl_hardware_context_text(merge_hardware_profile(client_caps)))
                except Exception as exc:
                    logger.debug('hardware context skip: %s', exc)
            if user_id:
                try:
                    from nl_to_workflow.user_assets_context import build_user_assets_context_text
                    assets_text = build_user_assets_context_text(user_id)
                    if assets_text:
                        extra_parts.append(assets_text)
                except Exception as exc:
                    logger.debug('user assets context skip: %s', exc)
            if extra_parts:
                text = '\n\n'.join([text] + extra_parts).strip()
            if text:
                context['agent_context_text'] = text
                existing = (context.get('reference_context') or '').strip()
                context['reference_context'] = f"{existing}\n\n{text}".strip() if existing else text
                context['_agent_context_source'] = gathered.get('source')
        except Exception as exc:
            logger.debug('agent context gather skipped: %s', exc)
        return context

    def _apply_agent_validation(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach tool-based validation metadata; does not strip the graph."""
        if not isinstance(workflow_data, dict) or not workflow_data.get('nodes'):
            return workflow_data
        try:
            validation = validate_generated_workflow_payload(workflow_data)
            workflow_data['_agent_validation'] = validation
        except Exception as exc:
            logger.debug('agent validation skipped: %s', exc)
        return workflow_data

    def _build_generation_description_from_messages(
        self,
        session_messages: List[Dict],
        user_message: str,
        existing_summary: str = '',
    ) -> Tuple[str, str]:
        """
        Aggregate conversation into a generation prompt.

        Returns:
            (description, updated_conversation_summary)
        """
        def _call(messages):
            return self._call_llm(messages)

        if getattr(settings, 'NL_CHAT_USE_SUMMARY', True):
            description, summary = compress_messages_for_generation(
                session_messages,
                user_message,
                call_llm=_call if self.llm else None,
                existing_summary=existing_summary or '',
            )
            return description, summary

        parts: List[str] = []
        for msg in session_messages:
            role = msg.get('role')
            content = (msg.get('content') or '').strip()
            if not content or role not in ('user', 'assistant'):
                continue
            prefix = '用户' if role == 'user' else '助手'
            parts.append(f"{prefix}：{content}")
        parts.append(f"用户：{user_message.strip()}")
        joined = '\n'.join(parts)
        description = (
            "请根据以下对话中确认的需求，生成完整的工作流 JSON。\n\n"
            f"{joined}\n\n"
            "请综合以上对话，生成满足用户最终需求的工作流。"
        )
        return description, existing_summary or ''

    def _maybe_refresh_conversation_summary(
        self,
        session_messages: List[Dict],
        existing_summary: str = '',
    ) -> str:
        if not should_summarize(session_messages):
            return existing_summary or ''

        def _call(messages):
            return self._call_llm(messages)

        return summarize_messages(
            session_messages,
            call_llm=_call if self.llm else None,
            existing_summary=existing_summary or '',
        )

    def _chat_suggestions(
        self,
        ready_to_generate: bool,
        has_workflow: bool,
        combined_text: str = '',
    ) -> List[str]:
        """Suggestions for conversational turns without workflow changes."""
        if is_emotion_detection_intent(combined_text):
            if ready_to_generate:
                return list(SUGGESTION_TEMPLATES.get('chat_ready', []))[:MAX_SUGGESTIONS]
            return list(SUGGESTION_TEMPLATES.get('chat_emotion', []))[:MAX_SUGGESTIONS]
        if is_yolo_detection_intent(combined_text):
            if ready_to_generate:
                return list(SUGGESTION_TEMPLATES.get('chat_ready', []))[:MAX_SUGGESTIONS]
            return list(SUGGESTION_TEMPLATES.get('chat_yolo', []))[:MAX_SUGGESTIONS]
        if ready_to_generate:
            return list(SUGGESTION_TEMPLATES.get('chat_ready', []))[:MAX_SUGGESTIONS]
        if has_workflow:
            return list(SUGGESTION_TEMPLATES.get('modify', []))[:MAX_SUGGESTIONS]
        return list(SUGGESTION_TEMPLATES.get('chat_no_workflow', []))[:MAX_SUGGESTIONS]

    @staticmethod
    def _resolve_request_mode(mode: Optional[str], has_workflow: bool) -> str:
        normalized = normalize_request_mode(mode)
        if normalized:
            return normalized
        return 'editor' if has_workflow else 'chat'

    def _handle_layout_intent(self, current_workflow: Dict[str, Any]) -> Dict[str, Any]:
        laid_out = auto_layout_workflow(current_workflow)
        return {
            'message': '已按数据流方向自动排布节点，并应用到画布。',
            'suggestions': self._generate_suggestions(laid_out),
            'workflow': laid_out,
            'changes': ['自动布局节点位置'],
            'intent': 'modify',
        }

    def _handle_optimize_intent(self, current_workflow: Dict[str, Any], user_message: str = '') -> Dict[str, Any]:
        """Structural optimize + optional LLM refine pass."""
        optimized, changes = optimize_workflow_structure(current_workflow)
        optimized = self._validate_workflow(optimized)

        if self.llm:
            try:
                modification_prompt = self._create_modification_prompt(
                    optimized,
                    f"{OPTIMIZE_LLM_INSTRUCTION}\n用户补充：{(user_message or '').strip()}",
                )
                result = self._call_llm([{"role": "user", "content": modification_prompt}])
                if 'error' not in result:
                    refined = WorkflowOutputParser.parse_modification(
                        result['content'], optimized
                    )
                    if 'error' not in refined and refined.get('nodes'):
                        refined = self._normalize_workflow(refined)
                        refined = self._validate_workflow(refined)
                        changes = changes + self._describe_changes(optimized, refined)
                        optimized = refined
                        changes.append('AI 智能完善')
            except Exception as exc:
                logger.warning('LLM optimize pass skipped: %s', exc)

        optimized['_optimized'] = True
        optimized['_is_intelligent'] = True
        return {
            'message': '已优化工作流结构与配置，并应用到画布。',
            'suggestions': self._generate_suggestions(optimized),
            'workflow': optimized,
            'changes': changes or ['优化工作流'],
            'intent': 'optimize',
        }

    def _apply_editor_tool_action(
        self,
        action: str,
        params: Dict[str, Any],
        current_workflow: Dict[str, Any],
        user_message: str,
        planner_message: str = '',
    ) -> Optional[Dict[str, Any]]:
        """Execute a planned editor tool against the canvas."""
        from nl_to_workflow.video_translation_workflow import (
            append_language_chain_to_workflow,
            apply_video_url_to_workflow,
            detect_target_languages,
            extract_url_from_message,
            get_video_translation_config_guidance,
            is_video_translation_workflow,
        )

        if action == 'layout':
            return self._handle_layout_intent(current_workflow)

        if action == 'optimize':
            return self._handle_optimize_intent(current_workflow, user_message)

        if action == 'config_check':
            if is_video_translation_workflow(current_workflow):
                summary, guidance_list, _missing = get_video_translation_config_guidance(
                    current_workflow
                )
                return {
                    'message': planner_message or summary,
                    'suggestions': self._generate_suggestions(current_workflow),
                    'workflow': current_workflow,
                    'changes': [],
                    'node_guidance': guidance_list or None,
                    'intent': 'chat',
                }
            node_guidance = get_node_config_guidance(current_workflow)
            return {
                'message': planner_message or (
                    '已检查节点配置。' + (
                        '发现待完善项，请查看右侧提示。' if node_guidance else '当前无明显缺失配置。'
                    )
                ),
                'suggestions': self._generate_suggestions(current_workflow),
                'workflow': current_workflow,
                'changes': [],
                'node_guidance': node_guidance or None,
                'intent': 'chat',
            }

        if action == 'set_video_url':
            url = (params.get('url') or extract_url_from_message(user_message) or '').strip()
            if not url:
                return None
            updated = apply_video_url_to_workflow(current_workflow, url)
            updated = self._validate_workflow(updated)
            return {
                'message': planner_message or f'已为「上传视频」节点设置公网 URL：{url}',
                'suggestions': self._generate_suggestions(updated),
                'workflow': updated,
                'changes': ['设置 video_upload 公网视频 URL'],
                'intent': 'modify',
            }

        if action == 'add_language':
            langs = params.get('languages') or detect_target_languages(user_message)
            if isinstance(langs, str):
                langs = [langs]
            langs = [str(x).strip() for x in (langs or []) if str(x).strip()]
            if not langs:
                return None
            updated = current_workflow
            changes = []
            for lang in langs:
                before_ids = {n.get('id') for n in updated.get('nodes', [])}
                updated = append_language_chain_to_workflow(
                    updated, lang, description=user_message
                )
                after_ids = {n.get('id') for n in updated.get('nodes', [])}
                if after_ids - before_ids:
                    changes.append(f'添加 {lang} 语言处理链')
            if not changes:
                return None
            updated = self._validate_workflow(updated)
            return {
                'message': planner_message or (
                    f"已为工作流添加语言链路：{', '.join(langs)}，并自动排布节点。"
                ),
                'suggestions': self._generate_suggestions(updated),
                'workflow': updated,
                'changes': changes,
                'intent': 'modify',
            }

        if action == 'generate':
            return self._handle_create_intent(user_message)

        if action == 'enrich_short_drama':
            from nl_to_workflow.short_drama_enrichment import enrich_short_drama_workflow

            shot_count = params.get('shot_count') or 12
            try:
                shot_count = int(shot_count)
            except (TypeError, ValueError):
                shot_count = 12
            shot_count = max(4, min(shot_count, 24))
            updated, changes = enrich_short_drama_workflow(
                current_workflow, shot_count=shot_count
            )
            if not changes:
                return None
            updated = self._normalize_workflow(updated)
            updated = self._validate_workflow(updated)
            return {
                'message': planner_message or (
                    f'已升级为「章节大输入 → {shot_count}条并行分镜链路 → 汇总成片」'
                    f'（每镜约5秒，拼接约1分钟短剧）。'
                ),
                'suggestions': self._generate_suggestions(updated),
                'workflow': updated,
                'changes': changes,
                'intent': 'modify',
            }

        if action == 'enrich_miao_embroidery':
            from nl_to_workflow.miao_embroidery_enrichment import enrich_miao_embroidery_workflow

            def _int(name, default):
                try:
                    return int(params.get(name) or default)
                except (TypeError, ValueError):
                    return default

            pattern_count = max(2, min(_int('pattern_count', 4), 6))
            series_count = max(3, min(_int('series_count', 6), 8))
            product_count = max(4, min(_int('product_count', 8), 12))
            updated, changes = enrich_miao_embroidery_workflow(
                current_workflow,
                pattern_count=pattern_count,
                series_count=series_count,
                product_count=product_count,
            )
            if not changes:
                return None
            updated = self._normalize_workflow(updated)
            updated = self._validate_workflow(updated)
            return {
                'message': planner_message or (
                    f'已升级为「{pattern_count}路苗绣纹样识别 → 融合策划 → '
                    f'{series_count}张系列纹样图 → {product_count}张产品矩阵」流水线。'
                ),
                'suggestions': self._generate_suggestions(updated),
                'workflow': updated,
                'changes': changes,
                'intent': 'modify',
            }

        if action == 'enrich_cumcm':
            from nl_to_workflow.cumcm_enrichment import enrich_cumcm_workflow

            try:
                subproblem_count = int(params.get('subproblem_count') or 3)
            except (TypeError, ValueError):
                subproblem_count = 3
            subproblem_count = max(2, min(subproblem_count, 5))
            updated, changes = enrich_cumcm_workflow(
                current_workflow,
                subproblem_count=subproblem_count,
            )
            if not changes:
                return None
            updated = self._normalize_workflow(updated)
            updated = self._validate_workflow(updated)
            return {
                'message': planner_message or (
                    f'已升级为 CUMCM 完整流水线：赛题解析 → {subproblem_count} 问并行建模求解 '
                    f'→ 灵敏度/检验 → 论文输出。'
                ),
                'suggestions': self._generate_suggestions(updated),
                'workflow': updated,
                'changes': changes,
                'intent': 'modify',
            }

        if action == 'modify':
            return None  # fall through to LLM modification path

        return None

    def _plan_and_apply_editor_action(
        self,
        user_message: str,
        current_workflow: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """AI-first editor: LLM plans an action, then tools execute it."""
        if not current_workflow or not current_workflow.get('nodes'):
            return None

        lower = (user_message or '').lower()
        # Fast path for explicit optimize/layout keywords even without LLM
        if is_layout_intent(user_message):
            return self._handle_layout_intent(current_workflow)
        if 'optimize' in lower or '/optimize' in lower or '优化' in (user_message or ''):
            return self._handle_optimize_intent(current_workflow, user_message)

        from nl_to_workflow.short_drama_enrichment import is_short_drama_enrich_intent
        if is_short_drama_enrich_intent(user_message):
            applied = self._apply_editor_tool_action(
                action='enrich_short_drama',
                params={'shot_count': 12},
                current_workflow=current_workflow,
                user_message=user_message,
                planner_message='检测到章节分镜/并行链路/1分钟短剧需求，正在重建为12路并行分镜→汇总成片。',
            )
            if applied:
                applied['planner'] = {'action': 'enrich_short_drama', 'source': 'keyword'}
                return applied

        from nl_to_workflow.miao_embroidery_enrichment import is_miao_embroidery_intent
        if is_miao_embroidery_intent(user_message):
            applied = self._apply_editor_tool_action(
                action='enrich_miao_embroidery',
                params={'pattern_count': 4, 'series_count': 6, 'product_count': 8},
                current_workflow=current_workflow,
                user_message=user_message,
                planner_message='检测到苗绣纹样识别/融合/产品矩阵需求，正在重建流水线。',
            )
            if applied:
                applied['planner'] = {'action': 'enrich_miao_embroidery', 'source': 'keyword'}
                return applied

        from nl_to_workflow.cumcm_enrichment import is_cumcm_enrich_intent
        if is_cumcm_enrich_intent(user_message):
            applied = self._apply_editor_tool_action(
                action='enrich_cumcm',
                params={'subproblem_count': 3},
                current_workflow=current_workflow,
                user_message=user_message,
                planner_message='检测到 CUMCM/数学建模竞赛需求，正在重建完整建模流水线。',
            )
            if applied:
                applied['planner'] = {'action': 'enrich_cumcm', 'source': 'keyword'}
                return applied

        planned = None
        if self.llm:
            def _call(messages):
                return self._call_llm(messages, mock_description=user_message)

            planned = plan_editor_action_with_llm(user_message, current_workflow, _call)

        if planned:
            action = planned.get('action') or 'chat'
            if action == 'chat':
                return None
            applied = self._apply_editor_tool_action(
                action=action,
                params=planned.get('params') or {},
                current_workflow=current_workflow,
                user_message=user_message,
                planner_message=planned.get('message') or '',
            )
            if applied:
                applied['planner'] = {'action': action, 'source': planned.get('source')}
                return applied
            if action == 'modify':
                return None

        # Weak fallback: deterministic tools when planner unavailable
        return self._try_editor_template_action(user_message, current_workflow)

    def _try_editor_template_action(
        self,
        user_message: str,
        current_workflow: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Deterministic editor tools (fallback when AI planner is unavailable)."""
        if not current_workflow or not current_workflow.get('nodes'):
            return None

        from nl_to_workflow.video_translation_workflow import (
            append_language_chain_to_workflow,
            apply_video_url_to_workflow,
            detect_target_languages,
            extract_url_from_message,
            get_video_translation_config_guidance,
            is_config_check_intent,
            is_video_translation_workflow,
            is_video_url_intent,
        )

        combined = user_message or ''
        lower = combined.lower()

        if 'optimize' in lower or '/optimize' in lower or '优化' in combined:
            return self._handle_optimize_intent(current_workflow, combined)

        if is_video_translation_workflow(current_workflow):
            if is_config_check_intent(combined):
                return self._apply_editor_tool_action(
                    'config_check', {}, current_workflow, combined
                )

            if is_video_url_intent(combined):
                url = extract_url_from_message(combined)
                return self._apply_editor_tool_action(
                    'set_video_url', {'url': url}, current_workflow, combined
                )
            add_lang_keywords = ('添加', '加上', '增加', '新增', '再来', '再加')
            if any(k in combined for k in add_lang_keywords):
                langs = detect_target_languages(combined)
                if langs:
                    return self._apply_editor_tool_action(
                        'add_language', {'languages': langs}, current_workflow, combined
                    )

        return None

    def _handle_chat_intent(
        self,
        session_messages: List[Dict],
        user_message: str,
        current_workflow: Optional[Dict] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run requirements-gathering conversation (non-streaming)."""
        combined = aggregate_conversation_text(session_messages, user_message)

        if is_emotion_detection_intent(combined) and not self.llm:
            msg, ready, suggestions = emotion_chat_fallback_response(session_messages, user_message)
            if msg:
                return {
                    "message": msg,
                    "suggestions": suggestions,
                    "workflow": current_workflow,
                    "intent": 'chat',
                    "ready_to_generate": ready or is_generate_command(user_message),
                }

        if is_yolo_detection_intent(combined) and not self.llm:
            msg, ready, suggestions = yolo_chat_fallback_response(session_messages, user_message)
            if msg:
                return {
                    "message": msg,
                    "suggestions": suggestions,
                    "workflow": current_workflow,
                    "intent": 'chat',
                    "ready_to_generate": ready or is_generate_command(user_message),
                }

        if is_web_scrape_email_intent(combined) and not self.llm:
            msg, ready, suggestions = web_scrape_email_chat_fallback_response(
                session_messages, user_message
            )
            if msg:
                return {
                    "message": msg,
                    "suggestions": suggestions,
                    "workflow": current_workflow,
                    "intent": 'chat',
                    "ready_to_generate": ready or is_generate_command(user_message),
                }

        if is_mobile_page_email_intent(combined) and not self.llm:
            msg, ready, suggestions = mobile_page_email_chat_fallback_response(
                session_messages, user_message
            )
            if msg:
                return {
                    "message": msg,
                    "suggestions": suggestions,
                    "workflow": current_workflow,
                    "intent": 'chat',
                    "ready_to_generate": ready or is_generate_command(user_message),
                }

        if is_video_translation_intent(combined) and not self.llm:
            msg, ready, suggestions = multimodal_chat_fallback_response(
                session_messages, user_message
            )
            if msg:
                return {
                    "message": msg,
                    "suggestions": suggestions,
                    "workflow": current_workflow,
                    "intent": 'chat',
                    "ready_to_generate": ready or is_generate_command(user_message),
                }

        if is_multimodal_intent(combined) and not self.llm and not is_video_translation_intent(combined):
            msg, ready, suggestions = multimodal_chat_fallback_response(
                session_messages, user_message
            )
            if msg:
                return {
                    "message": msg,
                    "suggestions": suggestions,
                    "workflow": current_workflow,
                    "intent": 'chat',
                    "ready_to_generate": ready or is_generate_command(user_message),
                }

        messages = ConversationPrompt.build_messages(
            session_messages, user_message, current_workflow, mode=mode
        )
        result = self._call_llm(messages)

        if 'error' in result:
            if is_emotion_detection_intent(combined):
                msg, ready, suggestions = emotion_chat_fallback_response(session_messages, user_message)
                if msg:
                    return {
                        "message": msg,
                        "suggestions": suggestions,
                        "workflow": current_workflow,
                        "intent": 'chat',
                        "ready_to_generate": ready or is_generate_command(user_message),
                    }
            if is_yolo_detection_intent(combined):
                msg, ready, suggestions = yolo_chat_fallback_response(session_messages, user_message)
                if msg:
                    return {
                        "message": msg,
                        "suggestions": suggestions,
                        "workflow": current_workflow,
                        "intent": 'chat',
                        "ready_to_generate": ready or is_generate_command(user_message),
                    }
            return {
                "message": f"处理失败: {result['error']}",
                "suggestions": self._chat_suggestions(False, bool(current_workflow), combined),
                "workflow": current_workflow,
                "intent": 'chat',
                "ready_to_generate": False,
            }

        raw_content = result.get('content', '')
        cleaned, ready_marker = ConversationPrompt.strip_ready_marker(raw_content)
        ready = (
            ready_marker
            or is_generate_command(user_message)
            or has_sufficient_emotion_detail(combined)
            or has_sufficient_yolo_detail(combined)
            or has_sufficient_web_scrape_email_detail(combined)
            or has_sufficient_mobile_page_email_detail(combined)
        )

        suggestions = self._extract_suggestions(cleaned)
        if not suggestions:
            suggestions = self._chat_suggestions(ready, bool(current_workflow), combined)

        return {
            "message": cleaned,
            "suggestions": suggestions,
            "workflow": current_workflow,
            "intent": 'chat',
            "ready_to_generate": ready,
        }

    def continue_conversation(
        self,
        session_messages: List[Dict],
        user_message: str,
        current_workflow: Optional[Dict] = None,
        mode: Optional[str] = None,
        existing_summary: str = '',
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Continue a conversation to refine or modify the workflow.
        
        Analyzes user intent and handles:
        - modify: Updates existing workflow based on feedback
        - delete: Removes nodes/edges from workflow
        - add: Adds new nodes/edges to workflow
        - chat: General conversation response
        
        Args:
            session_messages: Previous conversation messages
            user_message: Current user message
            current_workflow: Current workflow dict if available
            existing_summary: Prior conversation summary for long chats
            session_id: Optional NL session id for agent tool context
            
        Returns:
            Dict with message, suggestions, workflow updates, and changes
        """
        intent_info = self.resolve_intent(user_message)
        intent = intent_info.get('intent', 'chat')
        has_workflow = bool(current_workflow and current_workflow.get('nodes'))
        request_mode = self._resolve_request_mode(mode, has_workflow)
        conversation_summary = existing_summary or ''

        logger.info(
            f"Continue conversation - intent: {intent}, mode: {request_mode}, details: {intent_info}"
        )

        def _create_from_messages() -> Dict[str, Any]:
            nonlocal conversation_summary
            if session_messages:
                description, conversation_summary = self._build_generation_description_from_messages(
                    session_messages, user_message, existing_summary=conversation_summary
                )
            else:
                description = user_message.strip()
            result = self._handle_create_intent(
                description,
                context={'session_id': session_id} if session_id else None,
            )
            if conversation_summary:
                result['conversation_summary'] = conversation_summary
            return result

        # User explicitly selected「生成工作流」模式
        if request_mode == 'generate':
            return _create_from_messages()

        # 深度思考模式：对话优先；显式「生成工作流」指令则直接生成
        if request_mode == 'chat':
            if is_generate_command(user_message):
                return _create_from_messages()
            chat_result = self._handle_chat_intent(
                session_messages, user_message, current_workflow, mode=mode
            )
            refreshed = self._maybe_refresh_conversation_summary(
                list(session_messages or []) + [{'role': 'user', 'content': user_message}],
                existing_summary=conversation_summary,
            )
            if refreshed:
                chat_result['conversation_summary'] = refreshed
            return chat_result

        # 排布助手模式 — AI 规划后修改画布
        if request_mode == 'editor' and has_workflow:
            if intent == 'optimize':
                return self._handle_optimize_intent(current_workflow, user_message)

            planned_action = self._plan_and_apply_editor_action(user_message, current_workflow)
            if planned_action:
                return planned_action

            if is_generate_command(user_message):
                return _create_from_messages()

        if request_mode != 'chat' and intent == 'optimize' and current_workflow:
            return self._handle_optimize_intent(current_workflow, user_message)

        if request_mode != 'chat' and intent == 'modify' and current_workflow:
            # Handle workflow modification
            modification_prompt = self._create_modification_prompt(current_workflow, user_message)
            result = self._call_llm([{"role": "user", "content": modification_prompt}])

            if 'error' in result:
                return {
                    "message": f"修改失败: {result['error']}",
                    "suggestions": [],
                    "workflow": current_workflow,
                    "intent": intent
                }

            # Use structured output parser for modification
            updated_workflow = WorkflowOutputParser.parse_modification(
                result['content'],
                current_workflow
            )

            if 'error' in updated_workflow:
                return {
                    "message": f"解析修改结果失败: {updated_workflow['error']}",
                    "suggestions": [],
                    "workflow": current_workflow,
                    "intent": intent
                }
            
            updated_workflow = self._validate_workflow(updated_workflow)
            
            return {
                "message": "已根据您的要求修改工作流",
                "suggestions": self._generate_suggestions(updated_workflow),
                "workflow": updated_workflow,
                "changes": self._describe_changes(current_workflow, updated_workflow),
                "intent": intent
            }
        
        elif intent == 'delete' and current_workflow and request_mode != 'chat':
            # Handle node/edge deletion
            return self._handle_delete_intent(user_message, current_workflow)
        
        elif intent == 'create' and request_mode != 'chat':
            description = self._extract_workflow_description(user_message) or user_message.strip()
            return self._handle_create_intent(
                description,
                context={'session_id': session_id} if session_id else None,
            )

        elif request_mode == 'editor' and has_workflow:
            return self._handle_chat_intent(
                session_messages, user_message, current_workflow, mode='editor'
            )

        else:
            return self._handle_chat_intent(
                session_messages, user_message, current_workflow, mode=mode
            )

    def continue_conversation_streaming(
        self,
        session_messages: List[Dict],
        user_message: str,
        current_workflow: Optional[Dict] = None,
        mode: Optional[str] = None,
        existing_summary: str = '',
        session_id: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Stream conversation / modification / generation events.

        Yields JSON-serialized SSE payload dicts.
        """
        has_workflow = bool(current_workflow and current_workflow.get('nodes'))
        intent_info = self.resolve_intent(user_message)
        intent = intent_info.get('intent', 'chat')
        request_mode = self._resolve_request_mode(mode, has_workflow)
        conversation_summary = existing_summary or ''

        yield json.dumps({
            'type': 'intent',
            'intent': 'generate' if request_mode == 'generate' else intent,
            'mode': request_mode,
            'source': intent_info.get('source', 'keyword'),
            'progress': 5,
        })

        # 用户选择「生成工作流」— 仅此时生成
        if request_mode == 'generate':
            if session_messages:
                description, conversation_summary = self._build_generation_description_from_messages(
                    session_messages, user_message, existing_summary=conversation_summary
                )
            else:
                description = user_message.strip()
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '正在根据对话内容生成工作流...',
                'progress': 20,
            })
            gen_context = {'session_id': session_id} if session_id else None
            for chunk in self.generate_workflow_streaming(description, context=gen_context):
                yield chunk
            if conversation_summary:
                yield json.dumps({
                    'type': 'summary',
                    'conversation_summary': conversation_summary,
                })
            return

        # 排布助手：AI 规划 / 优化 / 布局
        if request_mode == 'editor' and has_workflow:
            planned_action = self._plan_and_apply_editor_action(user_message, current_workflow)
            if planned_action:
                yield json.dumps({
                    'type': 'progress',
                    'stage': planned_action.get('intent') or 'modify',
                    'message': planned_action.get('message') or '正在更新画布...',
                    'progress': 40,
                })
                workflow = planned_action.get('workflow')
                if workflow:
                    yield json.dumps({'type': 'workflow', 'workflow': workflow, 'progress': 85})
                payload = {
                    'type': 'done',
                    'message': planned_action.get('message', ''),
                    'workflow': workflow,
                    'suggestions': planned_action.get('suggestions', []),
                    'changes': planned_action.get('changes', []),
                    'intent': planned_action.get('intent', 'modify'),
                    'progress': 100,
                }
                if planned_action.get('node_guidance'):
                    payload['node_guidance'] = planned_action['node_guidance']
                yield json.dumps(payload)
                return

        # 排布助手 / 生成模式：modify/delete/optimize 直接改动画布
        if request_mode != 'chat' and intent == 'optimize' and has_workflow:
            response = self._handle_optimize_intent(current_workflow, user_message)
            workflow = response.get('workflow')
            if workflow:
                yield json.dumps({'type': 'workflow', 'workflow': workflow, 'progress': 85})
            yield json.dumps({
                'type': 'done',
                'message': response.get('message', ''),
                'workflow': workflow,
                'suggestions': response.get('suggestions', []),
                'changes': response.get('changes', []),
                'intent': 'optimize',
                'progress': 100,
            })
            return

        if request_mode != 'chat' and intent == 'modify' and has_workflow:
            yield json.dumps({
                'type': 'progress',
                'stage': 'modifying',
                'message': '正在修改工作流...',
                'progress': 20,
            })
            response = self.continue_conversation(
                session_messages, user_message, current_workflow, mode=mode
            )
            workflow = response.get('workflow')
            if workflow:
                yield json.dumps({'type': 'workflow', 'workflow': workflow, 'progress': 80})
            yield json.dumps({
                'type': 'done',
                'message': response.get('message', ''),
                'workflow': workflow,
                'suggestions': response.get('suggestions', []),
                'changes': response.get('changes', []),
                'intent': response.get('intent', intent),
                'ready_to_generate': response.get('ready_to_generate', False),
                'progress': 100,
            })
            return

        if request_mode != 'chat' and intent == 'delete' and has_workflow:
            response = self.continue_conversation(
                session_messages, user_message, current_workflow, mode=mode
            )
            workflow = response.get('workflow')
            if workflow:
                yield json.dumps({'type': 'workflow', 'workflow': workflow, 'progress': 80})
            yield json.dumps({
                'type': 'done',
                'message': response.get('message', ''),
                'workflow': workflow,
                'suggestions': response.get('suggestions', []),
                'intent': 'delete',
                'progress': 100,
            })
            return

        # 深度思考模式 + 显式「生成工作流」→ 根据对话内容生成
        if request_mode == 'chat' and is_generate_command(user_message):
            if session_messages:
                description, conversation_summary = self._build_generation_description_from_messages(
                    session_messages, user_message, existing_summary=conversation_summary
                )
            else:
                description = user_message.strip()
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '正在根据对话内容生成工作流...',
                'progress': 20,
            })
            gen_context = {'session_id': session_id} if session_id else None
            for chunk in self.generate_workflow_streaming(description, context=gen_context):
                yield chunk
            if conversation_summary:
                yield json.dumps({
                    'type': 'summary',
                    'conversation_summary': conversation_summary,
                })
            return

        # 深度思考 / 排布助手对话 — 不自动改动画布（除非上方已处理）
        yield json.dumps({
            'type': 'progress',
            'stage': 'thinking',
            'message': '正在理解您的需求...',
            'progress': 10,
        })

        messages = ConversationPrompt.build_messages(
            session_messages, user_message, current_workflow, mode=request_mode
        )

        provider = self.llm
        model = self._resolve_model()
        full_content = ''

        if not provider:
            chat_response = self._handle_chat_intent(
                session_messages, user_message, current_workflow, mode=request_mode
            )
            yield json.dumps({
                'type': 'token',
                'content': chat_response.get('message', ''),
            })
            yield json.dumps({
                'type': 'done',
                'message': chat_response.get('message', ''),
                'suggestions': chat_response.get('suggestions', []),
                'intent': 'chat',
                'ready_to_generate': chat_response.get('ready_to_generate', False),
                'progress': 100,
            })
            return

        try:
            token_progress = 15
            if request_mode == 'editor':
                chat_max_tokens = int(getattr(settings, 'NL_EDITOR_MAX_TOKENS', 1024))
            else:
                chat_max_tokens = int(getattr(settings, 'NL_CHAT_MAX_TOKENS', 512))
            for chunk in provider.stream_chat(
                messages=messages,
                model=model,
                temperature=self.temperature,
                max_tokens=chat_max_tokens,
            ):
                chunk_data = self._normalize_stream_chunk(chunk)

                stream_error = self._stream_chunk_error(chunk_data)
                if stream_error:
                    yield json.dumps({'type': 'error', 'error': self._format_provider_error(stream_error)})
                    return

                content_piece = chunk_data.get('content') or chunk_data.get('token') or ''
                if content_piece:
                    full_content += content_piece
                    token_progress = min(92, token_progress + 2)
                    yield json.dumps({
                        'type': 'token',
                        'content': content_piece,
                        'progress': token_progress,
                    })

            cleaned, ready_marker = ConversationPrompt.strip_ready_marker(full_content)
            combined = aggregate_conversation_text(session_messages, user_message)
            ready = (
                ready_marker
                or is_generate_command(user_message)
                or has_sufficient_yolo_detail(combined)
                or has_sufficient_web_scrape_email_detail(combined)
                or has_sufficient_mobile_page_email_detail(combined)
            )
            suggestions = self._extract_suggestions(cleaned)
            if not suggestions:
                suggestions = self._chat_suggestions(ready, has_workflow, combined)

            yield json.dumps({
                'type': 'done',
                'message': cleaned,
                'suggestions': suggestions,
                'intent': 'chat',
                'ready_to_generate': ready,
                'progress': 100,
            })
        except Exception as e:
            logger.exception(f"Streaming chat failed: {e}")
            yield json.dumps({'type': 'error', 'error': str(e)})

    def _extract_workflow_description(self, message: str) -> str:
        """
        Extract workflow description from creation message.
        
        Attempts to find the actual workflow description in a creation request.
        """
        # Remove common prefixes
        prefixes_to_remove = [
            '创建一个工作流：', '创建一个：', '做一个工作流：',
            '生成一个工作流：', '帮我做一个：', '帮我创建一个：',
            'create a workflow:', '生成一个：', '做一个：'
        ]
        
        description = message
        for prefix in prefixes_to_remove:
            if prefix in description.lower():
                idx = description.lower().find(prefix)
                description = description[idx + len(prefix):].strip()
                break
        
        # If description is too short, return empty
        if len(description) < 5:
            return ""
        
        return description

    def _handle_delete_intent(self, user_message: str, current_workflow: Dict) -> Dict[str, Any]:
        """
        Handle delete intent - remove nodes or edges from workflow.
        
        Args:
            user_message: User's delete request
            current_workflow: Current workflow dict
            
        Returns:
            Dict with updated workflow and changes
        """
        message_lower = user_message.lower()
        
        # Try to identify what to delete
        nodes = current_workflow.get('nodes', [])
        edges = current_workflow.get('edges', [])
        
        # Look for node type mentions
        node_to_delete = None
        for node in nodes:
            if node.get('type', '').lower() in message_lower:
                node_to_delete = node.get('id')
                break
            if node.get('name', '').lower() in message_lower:
                node_to_delete = node.get('id')
                break
        
        if node_to_delete:
            # Remove node and its connected edges
            new_nodes = [n for n in nodes if n.get('id') != node_to_delete]
            new_edges = [
                e for e in edges 
                if e.get('source') != node_to_delete and e.get('target') != node_to_delete
            ]
            
            updated_workflow = {
                **current_workflow,
                'nodes': new_nodes,
                'edges': new_edges
            }
            
            return {
                "message": f"已删除节点",
                "suggestions": self._generate_suggestions(updated_workflow),
                "workflow": updated_workflow,
                "changes": [f"删除了节点 {node_to_delete}"],
                "intent": "delete"
            }
        
        # No specific node found to delete
        return {
            "message": "没有找到要删除的节点。请具体说明要删除哪个节点。",
            "suggestions": ["删除某个特定类型的节点", "删除整个工作流重新开始"],
            "workflow": current_workflow,
            "intent": "delete"
        }

    def _handle_create_intent(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle new workflow creation intent.
        
        Args:
            description: Workflow description
            context: Optional generation context (session_id, reference, etc.)
            
        Returns:
            Dict with new workflow
        """
        try:
            workflow_data = self.generate_workflow(description, context=context)
            
            if 'error' in workflow_data:
                return {
                    "message": f"创建工作流失败: {workflow_data['error']}",
                    "suggestions": [],
                    "workflow": None,
                    "intent": "create"
                }
            
            return {
                "message": f"已创建新的工作流: {workflow_data.get('name', '未命名')}",
                "suggestions": self._generate_suggestions(workflow_data),
                "workflow": workflow_data,
                "changes": ["创建了新的工作流"],
                "intent": "create"
            }
        except Exception as e:
            logger.exception(f"Create intent failed: {e}")
            return {
                "message": f"创建工作流时出错: {str(e)}",
                "suggestions": [],
                "workflow": None,
                "intent": "create"
            }

    def _create_workflow_generation_prompt(self, description: str, context: Optional[Dict] = None) -> str:
        """Create comprehensive prompt for workflow generation with diverse few-shot examples."""
        intent_info = analyze_intent(description)
        subtype = intent_info.get('subtype', 'generic')
        subtype_map = {
            'emotion_detection': WorkflowType.EMOTION_DETECTION,
            'yolo_detection': WorkflowType.YOLO_DETECTION,
            'qa_bot': WorkflowType.QA_BOT,
            'data_processing': WorkflowType.DATA_PROCESSING,
            'translation': WorkflowType.TRANSLATION,
            'moderation': WorkflowType.MODERATION,
            'article_generation': WorkflowType.ARTICLE_GENERATION,
            'customer_service': WorkflowType.CUSTOMER_SERVICE,
            'email_sending': WorkflowType.EMAIL_SENDING,
            'web_scrape_email': WorkflowType.WEB_SCRAPE_EMAIL,
            'mobile_page_email': WorkflowType.MOBILE_PAGE_EMAIL,
            'cumcm': WorkflowType.CUMCM,
        }
        try:
            workflow_type = WorkflowType(subtype)
        except ValueError:
            workflow_type = subtype_map.get(subtype, WorkflowType.GENERIC)

        prompt_data = format_workflow_prompt(
            description=description,
            workflow_type=workflow_type,
            context=context
        )

        base = f"{prompt_data['system']}\n\n{prompt_data['user']}"
        reference = (context or {}).get('reference_context') if context else None
        if reference:
            base = (
                f"{base}\n\n"
                "【智能参考上下文 — 仅供启发，禁止原样复制为最终工作流】\n"
                f"{reference}"
            )
        base += (
            "\n\n【智能化硬性要求】\n"
            "- 必须根据用户需求自主设计节点与连线，禁止套用固定死模板整图。\n"
            "- 同类型需求允许不同结构，优先完整可执行。\n"
            "- provider/model 仅在缺省时给合理默认，不要强行 dashscope。\n"
        )
        return base

    def _create_modification_prompt(self, current_workflow: Dict, user_feedback: str) -> str:
        """Create prompt for modifying existing workflow."""
        # Use the new prompts module
        intent_info = analyze_intent(user_feedback)
        if intent_info.get('intent') == 'delete':
            prompt_data = get_modification_prompt(
                current_workflow,
                user_feedback,
                modification_type='delete'
            )
        else:
            prompt_data = get_modification_prompt(
                current_workflow,
                user_feedback,
                modification_type='modify'
            )

        return f"{prompt_data['system']}\n\n{prompt_data['user']}"

    def _analyze_intent(self, user_message: str) -> str:
        """Analyze user intent from message; returns intent string for callers/tests."""
        info = analyze_intent(user_message)
        if isinstance(info, dict):
            return info.get('intent', 'chat')
        return str(info or 'chat')

    def _get_intent_details(self, user_message: str) -> Dict[str, Any]:
        """
        Get detailed intent analysis including modification targets.
        
        Returns:
            Dict with intent type and extracted targets
        """
        message_lower = user_message.lower()
        intent = self._analyze_intent(user_message)
        
        result = {
            'intent': intent,
            'message': user_message,
            'targets': []
        }
        
        if intent == 'modify':
            # Extract modification targets (node names, etc.)
            # Look for quoted text or specific patterns
            patterns = [
                r'把(.+?)改成',
                r'把(.+?)改为',
                r'把(.+?)改成',
                r'添加(.+?)节点',
                r'添加(.+?)连接',
                r'删除(.+?)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                result['targets'].extend(matches)
        
        elif intent == 'delete':
            # Extract things to delete
            patterns = [
                r'删除(.+?)节点',
                r'删除(.+?)连接',
                r'删除(.+?)',
                r'移除(.+?)',
                r'不要(.+?)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                result['targets'].extend(matches)
        
        return result

    def _parse_workflow_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to workflow structure."""
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                workflow_data = json.loads(json_match.group())
                return self._normalize_workflow(workflow_data)
            except json.JSONDecodeError:
                pass

        code_block_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', response)
        if code_block_match:
            try:
                workflow_data = json.loads(code_block_match.group(1))
                return self._normalize_workflow(workflow_data)
            except json.JSONDecodeError:
                pass

        return {
            "error": "无法解析工作流描述",
            "raw_response": response[:500] if len(response) > 500 else response
        }

    def _normalize_email_node_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize email node config to the runtime shape expected by the executor."""
        normalized = dict(config or {})

        if not normalized.get('subject') and normalized.get('title'):
            normalized['subject'] = normalized.get('title', '')
        if not normalized.get('body') and normalized.get('content'):
            normalized['body'] = normalized.get('content', '')
        if not normalized.get('fromEmail') and normalized.get('from_email'):
            normalized['fromEmail'] = normalized.get('from_email', '')
        if normalized.get('is_html') is not None and normalized.get('isHtml') is None:
            normalized['isHtml'] = bool(normalized.get('is_html'))

        smtp_config = normalized.get('smtpConfig')
        if not isinstance(smtp_config, dict):
            smtp_config = {}

        legacy_smtp = str(normalized.get('smtp', '') or '').strip()
        if legacy_smtp and not smtp_config.get('server'):
            smtp_parts = legacy_smtp.split(':')
            smtp_config['server'] = smtp_parts[0].strip() if smtp_parts else ''
            if len(smtp_parts) > 1:
                try:
                    smtp_config['port'] = int(smtp_parts[1])
                except (TypeError, ValueError):
                    smtp_config['port'] = 587

        if 'smtpUsername' in normalized and not smtp_config.get('username'):
            smtp_config['username'] = normalized.get('smtpUsername', '')
        if 'smtpPassword' in normalized and not smtp_config.get('password'):
            smtp_config['password'] = normalized.get('smtpPassword', '')

        normalized['smtpConfig'] = {
            'server': smtp_config.get('server', '') or '',
            'port': int(smtp_config.get('port', 587) or 587),
            'useTls': bool(smtp_config.get('useTls', True)),
            'username': smtp_config.get('username', '') or '',
            'password': smtp_config.get('password', '') or ''
        }

        return normalized

    # Placeholder model names LLMs often hallucinate — not routable in Flowly
    _PLACEHOLDER_LLM_MODELS = frozenset({
        'llama3', 'llm3', 'llm', 'langchain', 'chatgpt', 'gpt', 'local',
        'default', 'auto', 'model',
    })

    def _is_valid_llm_model(self, model: Optional[str]) -> bool:
        """Return True if model is non-placeholder and supported by a registered provider."""
        if not model or not str(model).strip():
            return False
        model_id = str(model).strip()
        if model_id.lower() in self._PLACEHOLDER_LLM_MODELS:
            return False
        provider = self._get_provider_for_model(model_id)
        return bool(provider and provider.supports_model(model_id))

    def _normalize_llm_node_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure LLM nodes use a real, routable model (session/default), not LLM placeholders."""
        normalized = dict(config or {})
        model = str(normalized.get('model') or '').strip()
        resolved = self._resolve_model()
        if resolved and not self._is_valid_llm_model(model):
            normalized['model'] = resolved
        elif resolved and not model:
            normalized['model'] = resolved
        return normalized

    def _normalize_typed_node_config(self, node_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply type-specific config normalization for executable runtime schemas."""
        ntype = str(node_type or '').strip().lower()
        if ntype == 'email':
            return self._normalize_email_node_config(config)
        if ntype in ('llm', 'prompt', 'openai'):
            return self._normalize_llm_node_config(config)
        return normalize_node_config(ntype, config)

    def _normalize_workflow(self, workflow: Dict) -> Dict[str, Any]:
        """Normalize workflow structure with required fields.

        Supports both flat NL nodes (`config`/`name`) and VueFlow nodes (`data.config`/`data.label`).
        Always emits both shapes so editor apply + save never wipe configs.
        """
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])

        node_id_map = {}
        normalized_nodes = []
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            if 'id' not in node or not node.get('id'):
                node = {**node, 'id': f'node_{i + 1}'}
            node_id = node['id']
            node_id_map[node_id] = node_id

            data = node.get('data') if isinstance(node.get('data'), dict) else {}
            ntype = node.get('type') or data.get('type') or 'llm'
            label = (
                node.get('name')
                or data.get('label')
                or data.get('name')
                or str(ntype)
            )
            raw_cfg = node.get('config') if isinstance(node.get('config'), dict) else None
            if not raw_cfg:
                raw_cfg = data.get('config') if isinstance(data.get('config'), dict) else {}
            cfg = self._normalize_typed_node_config(ntype, raw_cfg or {})
            position = node.get('position') or {'x': 0, 'y': 0}
            merged_data = {**data, 'label': label, 'type': ntype, 'config': cfg}
            if 'description' not in merged_data:
                merged_data['description'] = node.get('description') or ''

            normalized_nodes.append({
                'id': node_id,
                'type': ntype,
                'name': label,
                'position': position,
                'config': cfg,
                'data': merged_data,
            })

        normalized_edges = []
        for i, edge in enumerate(edges):
            normalized_edge = {
                'id': edge.get('id', f'edge_{i + 1}'),
                'source': node_id_map.get(edge.get('source'), edge.get('source')),
                'target': node_id_map.get(edge.get('target'), edge.get('target')),
                'label': edge.get('label', '')
            }
            normalized_edges.append(normalized_edge)

        normalized = {
            'name': workflow.get('name', 'Generated Workflow'),
            'description': workflow.get('description', ''),
            'nodes': normalized_nodes,
            'edges': normalized_edges
        }
        for meta_key in ('_generation_mode', 'target_languages', '_intelligence_note', '_is_intelligent', '_llm_model', '_optimized'):
            if meta_key in workflow:
                normalized[meta_key] = workflow[meta_key]
        # 先按边自动传参（空字段），再补多模态默认值
        wired = wire_multimodal_workflow(wire_workflow_variable_refs(normalized))
        # 宽扇出：同类节点横排。短剧模板自带网格坐标，勿覆盖。
        gen_mode = str(wired.get('_generation_mode') or '')
        if 'short_drama' not in gen_mode and pick_layout_direction(
            wired.get('nodes') or [], wired.get('edges') or []
        ) == 'vertical':
            wired = auto_layout_workflow(wired, direction='vertical')
        return wired

    def _has_cycle_detection(self, workflow: Dict) -> Tuple[bool, List[str]]:
        """
        Detect cycles in workflow graph using DFS algorithm.
        
        Args:
            workflow: Workflow dict with nodes and edges
            
        Returns:
            Tuple of (has_cycle: bool, cycle_path: list of node IDs)
        """
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])
        
        # Build adjacency list
        graph = {}
        for node in nodes:
            graph[node.get('id')] = []
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source and target and source in graph and target in graph:
                graph[source].append(target)
        
        # DFS-based cycle detection
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> List[str]:
            """DFS traversal that returns cycle path if found."""
            if node_id not in graph:
                return []
            
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - extract the cycle path
                    cycle_start_idx = path.index(neighbor)
                    return path[cycle_start_idx:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node_id)
            return []
        
        # Check all nodes (in case graph is disconnected)
        for node in nodes:
            node_id = node.get('id')
            if node_id and node_id not in visited:
                cycle = dfs(node_id)
                if cycle:
                    return True, cycle
        
        return False, []
    
    def _estimate_workflow_cost(self, workflow: Dict) -> float:
        """
        Estimate workflow execution cost based on node types and count.
        
        Cost factors (in arbitrary units):
        - LLM nodes: high cost (depends on model)
        - HTTP/tool nodes: medium cost
        - Code nodes: medium cost
        - Other nodes: low cost
        
        Args:
            workflow: Workflow dict with nodes
            
        Returns:
            Estimated cost (float)
        """
        nodes = workflow.get('nodes', [])
        
        # Cost weights per node type
        COST_WEIGHTS = {
            'llm': 10.0,        # LLM calls are expensive
            'prompt': 5.0,       # Prompt processing
            'http': 3.0,         # HTTP requests
            'tool': 3.0,         # External tool calls
            'code': 2.0,         # Code execution
            'email': 2.0,       # Email sending
            'webhook': 2.0,     # Webhook calls
            'condition': 0.5,   # Simple condition check
            'input': 0.5,       # Input processing
            'output': 0.5,      # Output processing
            'start': 0.1,       # Minimal cost
            'end': 0.1,          # Minimal cost
        }
        
        total_cost = 0.0
        node_type_counts = {}
        
        for node in nodes:
            node_type = node.get('type', 'unknown')
            cost = COST_WEIGHTS.get(node_type, 1.0)
            
            # Adjust cost based on configuration
            config = node.get('config', {})
            
            # LLM nodes with larger context window cost more
            if node_type == 'llm':
                model = config.get('model', '')
                if 'gpt-4' in model.lower() or 'claude' in model.lower():
                    cost *= 2.0  # Premium models cost more
                elif 'gpt-3.5' in model.lower():
                    cost *= 0.5  # Cheaper models
                    
            # HTTP nodes with more parameters might be more expensive
            if node_type in ('http', 'tool'):
                params = config.get('parameters', {})
                cost += len(params) * 0.1
            
            total_cost += cost
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        
        # Add edge cost (communication overhead)
        edges = workflow.get('edges', [])
        total_cost += len(edges) * 0.1
        
        # Complexity multiplier based on node count
        node_count = len(nodes)
        if node_count > 20:
            total_cost *= 1.5  # Complex workflows have overhead
        elif node_count > 10:
            total_cost *= 1.2
        
        return round(total_cost, 2)
    
    def _generate_workflow_name(self, description: str) -> str:
        """
        Auto-generate workflow name from description.
        
        Args:
            description: User's workflow description
            
        Returns:
            Generated workflow name
        """
        # Common prefixes
        prefixes = ['自动化', '智能', '高效', '快捷', 'AI', '智能']
        
        # Extract key action and subject from description
        desc_lower = description.lower()
        
        # Action verbs mapping
        action_map = {
            '翻译': '翻译',
            '处理': '处理',
            '审核': '审核',
            '生成': '生成',
            '分析': '分析',
            '转换': '转换',
            '提取': '提取',
            '分类': '分类',
            '通知': '通知',
            '发送': '发送',
            '收集': '收集',
        }
        
        # Subject words mapping
        subject_map = {
            '数据': '数据',
            '文本': '文本',
            '文章': '文章',
            '图片': '图片',
            '邮件': '邮件',
            '文件': '文件',
            '评论': '评论',
            '内容': '内容',
            '用户': '用户',
            '订单': '订单',
        }
        
        # Find action and subject
        action = '工作流'
        subject = ''
        
        for keyword, label in action_map.items():
            if keyword in desc_lower:
                action = label
                break
        
        for keyword, label in subject_map.items():
            if keyword in desc_lower:
                subject = label
                break
        
        # If no subject found, try to extract from description
        if not subject:
            words = description.replace('，', ' ').replace(',', ' ').split()
            for word in words:
                if len(word) >= 2 and len(word) <= 4:
                    subject = word
                    break
        
        # Combine into name
        import random
        prefix = random.choice(prefixes)
        
        if subject:
            return f"{prefix}{action}{subject}"
        else:
            return f"{prefix}{action}"
    
    def _validate_workflow(self, workflow: Dict) -> Dict[str, Any]:
        """Validate workflow structure with enhanced checks including cycle detection."""
        errors = []
        warnings = []

        if not workflow.get('name'):
            # Auto-generate name if missing
            description = workflow.get('description', '')
            if description:
                workflow['name'] = self._generate_workflow_name(description)
            else:
                errors.append(VALIDATION_MESSAGES['missing_name'])

        if not workflow.get('nodes'):
            errors.append(VALIDATION_MESSAGES['missing_nodes'])

        node_types = [n.get('type') for n in workflow.get('nodes', [])]

        if 'start' not in node_types:
            warnings.append(VALIDATION_MESSAGES['missing_start'])

        if 'end' not in node_types:
            warnings.append(VALIDATION_MESSAGES['missing_end'])

        start_count = node_types.count('start')
        if start_count > 1:
            errors.append(VALIDATION_MESSAGES['multiple_starts'].format(count=start_count))

        connected_nodes = set()
        for edge in workflow.get('edges', []):
            if edge.get('source'):
                connected_nodes.add(edge.get('source'))
            if edge.get('target'):
                connected_nodes.add(edge.get('target'))

        node_ids = set(n.get('id') for n in workflow.get('nodes', []))
        disconnected = node_ids - connected_nodes - {'start'}

        if disconnected:
            warnings.append(VALIDATION_MESSAGES['disconnected_nodes'].format(
                nodes=', '.join(list(disconnected)[:3])
            ))
        
        # DAG Cycle Detection
        has_cycle, cycle_path = self._has_cycle_detection(workflow)
        if has_cycle:
            cycle_str = ' -> '.join(cycle_path[:6])  # Show first 6 nodes in cycle
            if len(cycle_path) > 6:
                cycle_str += ' -> ...'
            errors.append(f"工作流存在循环依赖: {cycle_str}。这会导致执行时无限循环，请修改工作流结构。")

        # Estimate workflow cost
        estimated_cost = self._estimate_workflow_cost(workflow)

        # Auto-calculate node positions if not provided
        nodes = workflow.get('nodes', [])
        needs_position_calc = any(
            n.get('position') is None or 
            n.get('position', {}).get('x') is None or
            n.get('position', {}).get('y') is None
            for n in nodes
        )
        
        if needs_position_calc:
            positions = calculate_node_positions(len(nodes))
            for i, node in enumerate(nodes):
                if node.get('position') is None:
                    node['position'] = positions[i]
                elif node['position'].get('x') is None or node['position'].get('y') is None:
                    node['position'] = positions[i]

        return {
            **workflow,
            'estimated_cost': estimated_cost,
            'validation': {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
        }

    def _describe_changes(self, old_workflow: Dict, new_workflow: Dict) -> List[str]:
        """Describe what changed between workflows."""
        changes = []

        if old_workflow.get('name') != new_workflow.get('name'):
            changes.append(f"名称: {old_workflow.get('name')} -> {new_workflow.get('name')}")

        old_node_ids = set(n.get('id') for n in old_workflow.get('nodes', []))
        new_node_ids = set(n.get('id') for n in new_workflow.get('nodes', []))

        added = new_node_ids - old_node_ids
        removed = old_node_ids - new_node_ids

        if added:
            changes.append(f"添加了 {len(added)} 个节点")
        if removed:
            changes.append(f"删除了 {len(removed)} 个节点")

        return changes

    def _generate_suggestions(self, workflow: Dict) -> List[str]:
        """Generate follow-up suggestions based on workflow using constants."""
        node_types = [n.get('type') for n in workflow.get('nodes', [])]

        suggestions = []
        if 'llm' not in node_types:
            suggestions.append('添加 AI 处理节点')
        if 'condition' not in node_types:
            suggestions.append('添加条件分支')
        if 'tool' not in node_types:
            suggestions.append('添加外部工具调用')

        # Email-specific suggestions
        if 'email' in node_types:
            suggestions.extend(SUGGESTION_TEMPLATES.get('email', [
                '配置 SMTP 服务器',
                '设置多个收件人',
                '添加 HTML 模板',
            ]))

        suggestions.extend(SUGGESTION_TEMPLATES['general'])
        return suggestions[:MAX_SUGGESTIONS]

    def _generate_suggestions_from_description(self, description: str) -> List[str]:
        """Generate initial suggestions from description using constants."""
        suggestions = list(SUGGESTION_TEMPLATES['initial'])

        desc_lower = description.lower()

        if any(k in desc_lower for k in ['ai', 'llm', 'gpt', 'chat', '模型']):
            suggestions.insert(0, '使用 AI 模型处理')
        if any(k in desc_lower for k in ['判断', '条件', 'if', 'branch', '分流']):
            suggestions.insert(0, '添加条件分支')
        if any(k in desc_lower for k in ['api', 'http', '请求', '调用']):
            suggestions.insert(0, '添加外部 API 调用')
        if any(k in desc_lower for k in ['输入', 'form', '表单', '用户']):
            suggestions.insert(0, '添加用户输入节点')
        if any(k in desc_lower for k in ['邮件', 'email', '发邮件', 'send email', 'smtp']):
            suggestions.insert(0, '配置 SMTP 服务器')
            suggestions.insert(0, '设置多个收件人')

        return suggestions[:MAX_SUGGESTIONS]

    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract follow-up suggestions from response using constants."""
        suggestions = []

        for pattern in SUGGESTION_EXTRACTION_PATTERNS:
            matches = re.findall(pattern, text)
            suggestions.extend(matches[:2])

        return suggestions[:MAX_SUGGESTIONS]


def get_nl_service(model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4096, user=None) -> NLToWorkflowService:
    """Factory function to create an NL service with specific configuration."""
    return NLToWorkflowService(model=model, temperature=temperature, max_tokens=max_tokens, user=user)


def generate_suggestions(description: str) -> List[str]:
    """
    Standalone function to generate workflow suggestions from description.
    Used by Celery tasks and external callers.
    """
    service = NLToWorkflowService()
    return service._generate_suggestions_from_description(description)


# ---------------------------------------------------------------------------
# Email Configuration Guidance
# ---------------------------------------------------------------------------

EMAIL_CONFIG_GUIDANCE: Dict[str, Any] = {
    "type": "email_config",
    "title": "邮件节点配置提醒",
    "description": "您的邮件工作流已生成，在保存和使用前请完成以下配置：",
    "items": [
        {
            "field": "收件人 (to)",
            "required": True,
            "tip": "请在邮件节点中填写实际收件人邮箱地址，支持多个收件人（逗号分隔）或变量插值如 {{{{input.email}}}}"
        },
        {
            "field": "SMTP 服务器配置",
            "required": False,
            "tip": "如果不配置则使用系统默认 SMTP。常见配置：\n- Gmail: smtp.gmail.com:587 (TLS)\n- QQ邮箱: smtp.qq.com:587 (TLS)\n- 163邮箱: smtp.163.com:465 (SSL)\n- 企业邮箱: smtp.company.com:465 (SSL)"
        },
        {
            "field": "发件人 (fromEmail)",
            "required": False,
            "tip": "默认使用系统配置的默认发件地址。如需自定义，请确保域名已通过 SMTP 服务商验证"
        },
        {
            "field": "主题和正文变量",
            "required": False,
            "tip": "使用 {{{{变量名}}}} 语法引用上游节点的输出或输入数据，实现动态邮件内容"
        }
    ],
    "quick_links": [
        {"label": "配置 SMTP", "path": "/settings/credentials", "description": "设置邮件发送服务器"},
        {"label": "邮件模板", "path": "/settings/branding", "description": "管理邮件模板和默认发件人"},
    ]
}


def get_email_config_guidance(workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Return email configuration guidance if the workflow contains email nodes.

    Args:
        workflow: The generated workflow dict

    Returns:
        Email config guidance dict or None if no email nodes present
    """
    nodes = workflow.get('nodes', [])
    email_nodes = [n for n in nodes if n.get('type') == 'email']

    if not email_nodes:
        return None

    # Check which email nodes are missing required config
    missing_config = []
    warnings = []
    for node in email_nodes:
        config = node.get('config', {})
        node_name = node.get('name', '邮件节点')
        if not config.get('to'):
            missing_config.append(f"「{node_name}」- 收件人为空")
        if not config.get('subject'):
            missing_config.append(f"「{node_name}」- 主题为空")
        if not config.get('body'):
            missing_config.append(f"「{node_name}」- 正文为空")
        has_smtp = config.get('smtpConfig') and any([
            config['smtpConfig'].get('server'),
            config['smtpConfig'].get('username')
        ])
        if not has_smtp:
            warnings.append(f"「{node_name}」未配置 SMTP，将使用系统默认邮件服务器发送")

    guidance = copy.deepcopy(EMAIL_CONFIG_GUIDANCE)
    guidance['missing_fields'] = missing_config
    guidance['warning'] = '\n'.join(warnings)
    guidance['configured_fields'] = {
        '收件人 (to)': all((node.get('config') or {}).get('to') for node in email_nodes),
        'SMTP 服务器配置': not warnings,
        '发件人 (fromEmail)': all((node.get('config') or {}).get('fromEmail') for node in email_nodes),
        '主题和正文变量': all((node.get('config') or {}).get('subject') and (node.get('config') or {}).get('body') for node in email_nodes),
    }
    guidance['description'] = f"工作流包含 {len(email_nodes)} 个邮件节点，请核对收件人、主题、正文和发送服务器。"
    return guidance


def get_node_config_guidance(workflow: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Return node configuration guidance for all nodes that need config in the workflow.

    Args:
        workflow: The generated workflow dict

    Returns:
        List of guidance dicts for nodes that need configuration, or None if all nodes are configured
    """
    nodes = workflow.get('nodes', [])
    guidance_list = []

    for node in nodes:
        node_type = node.get('type')
        node_name = node.get('name', f'{node_type} 节点')
        config = node.get('config', {}) or {}

        guidance = _get_guidance_for_node_type(node_type, node_name, config)
        if guidance:
            guidance_list.append(guidance)

    return guidance_list if guidance_list else None


def _get_guidance_for_node_type(node_type: str, node_name: str, config: Dict) -> Optional[Dict[str, Any]]:
    """Generate guidance for a specific node type."""
    node_type_map = {
        'llm': {
            'items': [
                {'field': '模型选择', 'required': True, 'tip': '选择要使用的 LLM 模型，如 qwen2.5-coder:7b', 'example': 'qwen2.5-coder:7b'},
                {'field': '系统提示词', 'required': False, 'tip': '设置 AI 的角色和行为规则', 'example': '你是一个专业的客服助手'},
                {'field': '温度参数', 'required': False, 'tip': '控制输出的随机性，0-1之间，较低更确定', 'example': '0.7'},
                {'field': '最大令牌数', 'required': False, 'tip': '限制输出的最大长度', 'example': '2000'},
            ],
            'quick_links': [
                {'label': '配置 API Keys', 'path': '/settings', 'description': '设置模型 API 密钥'},
            ],
        },
        'code': {
            'items': [
                {'field': '代码语言', 'required': True, 'tip': '选择代码执行的语言', 'example': 'python'},
                {'field': '代码内容', 'required': True, 'tip': '输入要执行的代码', 'example': 'print("Hello World")'},
                {'field': '超时时间', 'required': False, 'tip': '代码执行的最大等待时间（秒）', 'example': '30'},
            ],
        },
        'database': {
            'items': [
                {'field': '数据库类型', 'required': True, 'tip': '选择数据库类型：mysql, postgresql, mongodb', 'example': 'mysql'},
                {'field': '连接信息', 'required': True, 'tip': '填写主机、端口、数据库名', 'example': 'host: localhost, port: 3306'},
                {'field': '认证信息', 'required': True, 'tip': '用户名和密码', 'example': 'username: root'},
                {'field': 'SQL 语句', 'required': False, 'tip': '执行的查询语句', 'example': 'SELECT * FROM users LIMIT 10'},
            ],
            'quick_links': [
                {'label': '连接管理', 'path': '/settings', 'description': '管理数据库连接'},
            ],
        },
        'webhook': {
            'items': [
                {'field': '请求 URL', 'required': True, 'tip': 'Webhook 目标地址', 'example': 'https://api.example.com/webhook'},
                {'field': '请求方法', 'required': True, 'tip': 'HTTP 方法：GET, POST, PUT, DELETE', 'example': 'POST'},
                {'field': '请求头', 'required': False, 'tip': 'HTTP 请求头（JSON 格式）', 'example': '{"Content-Type": "application/json"}'},
                {'field': '认证方式', 'required': False, 'tip': 'Bearer Token, Basic Auth, API Key 等', 'example': 'Bearer eyJhbGc...'},
            ],
        },
        'trigger': {
            'items': [
                {'field': '触发类型', 'required': True, 'tip': '选择触发方式：webhook, schedule, manual', 'example': 'webhook'},
                {'field': '触发条件', 'required': True, 'tip': '设置触发条件或定时规则', 'example': 'cron: 0 9 * * * (每天9点)'},
            ],
        },
        'schedule': {
            'items': [
                {'field': 'Cron 表达式', 'required': True, 'tip': '定时任务表达式', 'example': '0 9 * * * (每天9点)'},
                {'field': '时区', 'required': False, 'tip': '定时任务的时区', 'example': 'Asia/Shanghai'},
                {'field': '最大执行次数', 'required': False, 'tip': '限制总执行次数，留空表示无限', 'example': '10'},
            ],
        },
        'tool': {
            'items': [
                {'field': '工具类型', 'required': True, 'tip': '选择工具类型：http_request, file_operation, data_transform', 'example': 'http_request'},
                {'field': '工具配置', 'required': True, 'tip': '根据工具类型填写相应配置', 'example': '见各工具详细文档'},
            ],
        },
        'input': {
            'items': [
                {'field': '输入类型', 'required': True, 'tip': '输入数据的类型：text, file, json', 'example': 'text'},
                {'field': '参数名称', 'required': True, 'tip': '定义输入参数的名称', 'example': 'user_query'},
                {'field': '默认值', 'required': False, 'tip': '设置默认输入值', 'example': '请输入您的问题'},
            ],
        },
        'output': {
            'items': [
                {'field': '输出类型', 'required': True, 'tip': '输出数据类型：text, json, file', 'example': 'text'},
                {'field': '输出格式', 'required': False, 'tip': '定义输出格式模板', 'example': '回答：{result}'},
            ],
        },
    }

    if node_type not in node_type_map:
        return None

    template = node_type_map[node_type]
    missing = []

    # Check for common missing fields
    if node_type == 'llm':
        if not config.get('model'):
            missing.append(f"「{node_name}」- 未选择模型")
    elif node_type == 'database':
        if not config.get('host') and not config.get('connection_string'):
            missing.append(f"「{node_name}」- 未配置数据库连接")
    elif node_type == 'webhook':
        if not config.get('url'):
            missing.append(f"「{node_name}」- 未配置请求 URL")
    elif node_type in ('trigger', 'schedule'):
        if not config.get('trigger_type') and not config.get('schedule'):
            missing.append(f"「{node_name}」- 未配置触发条件")
    elif node_type == 'code':
        if not config.get('code') and not config.get('language'):
            missing.append(f"「{node_name}」- 未配置代码")

    guidance = {
        'node_type': node_type,
        'node_name': node_name,
        'description': f"「{node_name}」节点需要以下配置：",
        'missing_fields': missing,
        'items': template['items'],
        'config': config,
        'quick_links': template.get('quick_links', []),
    }

    return guidance


nl_to_workflow_service = NLToWorkflowService()
