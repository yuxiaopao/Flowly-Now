"""
Constants and configuration for NL to Workflow module.
All magic strings, hardcoded values, and configuration are centralized here.
"""

from typing import Dict, List, Any, Tuple, Optional

# ---------------------------------------------------------------------------
# Default Configuration (imported from central config to avoid duplication)
# ---------------------------------------------------------------------------

from config.constants import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
from .node_catalog import SUPPORTED_NODE_TYPES, NL_PRIMARY_NODE_TYPES

FALLBACK_GRID_START_X = 100
FALLBACK_GRID_START_Y = 150
FALLBACK_GRID_SPACING_X = 180
FALLBACK_GRID_SPACING_Y = 120
FALLBACK_GRID_COLUMNS = 4

# Fallback model when none is configured (prefer Agnes when API key present)
FALLBACK_MODEL: str = 'agnes-2.0-flash'

# Volcengine Ark endpoint models (OpenAI-compatible chat/completions)
VOLCENGINE_ARK_CHAT_MODELS: List[Dict[str, Any]] = [
    {
        'model_id': 'ep-20260412153558-stg4j',
        'name': 'Doubao-1.5-pro-32k',
        'provider': 'openai',
        'max_tokens': 32768,
        'supports_streaming': True,
        'context_window': 32768,
    },
    {
        'model_id': 'ep-20260428094034-wsw42',
        'name': 'Doubao-Seed-1.6-flash',
        'provider': 'openai',
        'max_tokens': 32768,
        'supports_streaming': True,
        'context_window': 32768,
    },
    {
        'model_id': 'ep-20260428093650-qg4gm',
        'name': 'Doubao-Seed-1.6',
        'provider': 'openai',
        'max_tokens': 32768,
        'supports_streaming': True,
        'context_window': 32768,
    },
    {
        'model_id': 'ep-20260428094223-mtpg5',
        'name': 'Doubao-Seed-Code',
        'provider': 'openai',
        'max_tokens': 32768,
        'supports_streaming': True,
        'context_window': 32768,
    },
]

# Maximum number of suggestions to return
MAX_SUGGESTIONS: int = 4

# ---------------------------------------------------------------------------
# Intent Analysis - Keywords for Intent Detection
# ---------------------------------------------------------------------------

CREATE_KEYWORDS: List[str] = [
    '创建', '生成', '做一个', '帮我', '设计', 'build', 'create', 'generate', 'make',
    '给我一个', '做一个', 'new workflow', '新工作流', '新建'
]

MODIFY_KEYWORDS: List[str] = [
    # Chinese
    '修改', '调整', '改变', '添加', '增加', '改变', '替换', '更新', '编辑', 
    '重命名', '移动', '重新排序', '改一下', '把', '改成', '加上', '再加',
    '再加一个', '再加个', '再添', '再添加', '添加一个',
    # English
    'change', 'modify', 'add', 'update', 'edit', 'replace', 'rename', 'move', 
    'reorder', 'insert', 'adjust', 'alter', 'fix', 'correct',
]

DELETE_KEYWORDS: List[str] = [
    # Chinese
    '删除', '移除', '不要', '去掉', '删掉', '去掉',
    # English
    'delete', 'remove', 'drop', 'discard', 'cancel',
]

# Explicit command to generate workflow after discussion
GENERATE_KEYWORDS: List[str] = [
    '生成工作流', '开始生成', '可以生成了', '现在就生成', '帮我生成',
    '生成吧', '开始创建', '创建吧', '可以创建了', '就按这个生成',
    'generate workflow', 'generate now', 'start generating', 'go ahead',
    'create workflow', 'build workflow',
]

# Greeting / small-talk — prefer chat over immediate generation
CHAT_GREETING_KEYWORDS: List[str] = [
    '你好', '您好', 'hi', 'hello', 'hey', '在吗', '谢谢', '感谢',
]

# Workflow detail signals — enough context to generate directly
WORKFLOW_DETAIL_KEYWORDS: List[str] = [
    '输入', '输出', '节点', '分支', '条件', '触发', '定时', 'webhook',
    'llm', 'api', 'http', '邮件', 'email', 'csv', '数据库', '包含',
    '步骤', '流程', '自动', '处理', '发送', '接收', '审核', '翻译',
]

# Business scenario keywords — indicate a concrete workflow topic
WORKFLOW_SCENE_KEYWORDS: List[str] = [
    '问答', '机器人', '客服', '翻译', '审核', '报表', '邮件', '通知',
    '数据', 'csv', 'excel', 'webhook', '定时', 'slack', '飞书', '钉钉',
    '企业微信', 'api', 'http', '表单', '工单', '投诉', '评论',
    'yolo', '目标检测', '物体检测', 'ultralytics', '识别项目', 'mlops',
    '数据集', '模型训练', '建站', '识别网站',
]

# Combined modification keywords for backward compatibility
MODIFICATION_KEYWORDS: List[str] = MODIFY_KEYWORDS + [
    'change', 'modify', 'add', 'remove', 'update', 'edit',
    'replace', 'rename', 'move', 'reorder', 'delete', 'insert',
    'adjust', 'alter', 'fix', 'correct',
]


def is_modification_intent(message: str) -> bool:
    """Check if a message indicates a workflow modification intent."""
    message_lower = message.lower()
    return any(kw in message_lower for kw in MODIFICATION_KEYWORDS)


def detect_intent(message: str) -> str:
    """
    Detect user intent from message.
    
    Args:
        message: User's message
        
    Returns:
        Intent type: 'create', 'modify', 'delete', or 'chat'
    """
    message_lower = message.lower()
    
    # Check delete first (most specific)
    if any(kw in message_lower for kw in DELETE_KEYWORDS):
        return 'delete'
    
    # Check modify
    if any(kw in message_lower for kw in MODIFY_KEYWORDS):
        return 'modify'
    
    # Check create
    if any(kw in message_lower for kw in CREATE_KEYWORDS):
        return 'create'
    
    return 'chat'


def is_generate_command(message: str) -> bool:
    """True when user explicitly asks to generate the workflow."""
    message_lower = message.lower().strip()
    return any(kw in message_lower for kw in GENERATE_KEYWORDS)


def is_greeting_only(message: str) -> bool:
    """True for short greetings without workflow requirements."""
    text = message.strip()
    if len(text) > 20:
        return False
    lower = text.lower()
    return any(kw in lower for kw in CHAT_GREETING_KEYWORDS)


def has_sufficient_workflow_detail(message: str) -> bool:
    """
    Heuristic: message contains enough detail to generate a workflow directly.
    """
    text = message.strip()
    if len(text) < 15:
        return False
    lower = text.lower()
    detail_hits = sum(1 for kw in WORKFLOW_DETAIL_KEYWORDS if kw in lower)
    scene_hits = sum(1 for kw in WORKFLOW_SCENE_KEYWORDS if kw in lower)

    if detail_hits >= 2:
        return True
    if len(text) >= 30 and (detail_hits >= 1 or scene_hits >= 1):
        return True
    if any(kw in lower for kw in CREATE_KEYWORDS) and len(text) >= 20 and scene_hits >= 1:
        return True
    try:
        from .yolo_workflow import has_sufficient_yolo_detail
        if has_sufficient_yolo_detail(text):
            return True
    except ImportError:
        pass
    return False


def normalize_request_mode(mode: Optional[str]) -> Optional[str]:
    """
    Normalize frontend mode to 'chat', 'generate', or 'editor'.

    Frontend sends: thinking/chat | generate/workflow | editor/assist
    """
    if mode is None or mode == '':
        return None
    lower = str(mode).lower().strip()
    if lower in ('generate', 'workflow', '生成', '生成工作流'):
        return 'generate'
    if lower in ('editor', 'assist', 'assistant', '排布', '排布助手', '画布助手'):
        return 'editor'
    if lower in ('chat', 'thinking', '思考', '深度思考', '讨论'):
        return 'chat'
    return None


def resolve_initial_stream_mode(
    message: str,
    has_workflow: bool = False,
    prior_messages: Optional[List[Dict]] = None,
    explicit_mode: Optional[str] = None,
) -> str:
    """
    Decide whether the first stream action should be 'chat' or 'generate'.

    When explicit_mode is provided, it takes priority.
    Otherwise defaults to chat — workflow is only generated when user selects generate mode.
    """
    normalized = normalize_request_mode(explicit_mode)
    if normalized == 'generate':
        return 'generate'
    if normalized == 'editor':
        return 'editor'
    if normalized == 'chat':
        return 'chat'

    if has_workflow:
        return 'editor'

    return 'chat'


# ---------------------------------------------------------------------------
# Follow-up Suggestions
# ---------------------------------------------------------------------------

SUGGESTION_TEMPLATES: Dict[str, List[str]] = {
    'general': [
        '添加更多处理步骤',
        '调整节点顺序',
        '修改某个节点的配置',
        '添加错误处理',
    ],
    'no_llm': ['添加 AI 处理节点'],
    'no_condition': ['添加条件分支'],
    'no_tool': ['添加外部工具调用'],
    'initial': [
        '添加更多处理步骤',
        '添加条件分支',
        '添加错误处理',
        '优化工作流顺序',
    ],
    'chat_no_workflow': [
        '我想做一个 YOLO 目标检测项目，训练完还要建站',
        '我想做一个客服机器人',
        '需要定时发送报表邮件',
        '帮我设计一个内容审核流程',
        '现在就生成工作流',
    ],
    'chat_yolo': [
        '我有 YOLO 数据集，需要训练并生成识别网站',
        '训练 50 个 epoch，网站名叫现场检测系统',
        '只需要训练，不需要建站',
        '现在就生成工作流',
    ],
    'chat_emotion': [
        '我有表情数据集，需要训练并生成情绪识别网站',
        '训练 30 个 epoch，网站名叫情绪检测系统',
        '只需要训练，不需要建站',
        '现在就生成工作流',
    ],
    'chat_ready': [
        '现在就生成工作流',
        '开始生成',
        '我还需要补充一些细节',
    ],
    'chat_cumcm': [
        '帮我搭建 CUMCM 数学建模完整工作流',
        '赛题有 3 个子问题，需要建模求解和论文输出',
        '增加灵敏度分析和模型检验节点',
        '现在就生成工作流',
    ],
    'modify': [
        '把 LLM 节点改成使用 gpt-4',
        '添加一个条件分支',
        '再添加一个处理步骤',
        '添加重试机制',
    ],
    'delete': [
        '删除某个节点',
        '简化工作流',
        '去掉某个处理步骤',
    ],
    'email': [
        '配置 SMTP 服务器',
        '添加多个收件人',
        '设置 HTML 邮件模板',
        '添加附件支持',
        '配置抄送/密送',
        '设置邮件发送失败重试',
    ],
}


def get_contextual_suggestions(node_types: List[str]) -> List[str]:
    """Generate suggestions based on current workflow node types."""
    suggestions = []

    if 'llm' not in node_types:
        suggestions.append('添加 AI 处理节点')
    if 'condition' not in node_types:
        suggestions.append('添加条件分支')
    if 'tool' not in node_types:
        suggestions.append('添加外部工具调用')

    suggestions.extend(SUGGESTION_TEMPLATES['general'])
    return suggestions[:MAX_SUGGESTIONS]


def get_initial_suggestions(description: str = '') -> List[str]:
    """Generate initial suggestions based on description keywords."""
    suggestions = list(SUGGESTION_TEMPLATES['initial'])

    desc_lower = description.lower()

    # Keyword-based suggestions
    if any(k in desc_lower for k in ['ai', 'llm', 'gpt', 'chat', '模型']):
        suggestions.insert(0, '使用 AI 模型处理')
    if any(k in desc_lower for k in ['判断', '条件', 'if', 'branch', '分流']):
        suggestions.insert(0, '添加条件分支')
    if any(k in desc_lower for k in ['api', 'http', '请求', '调用']):
        suggestions.insert(0, '添加外部 API 调用')
    if any(k in desc_lower for k in ['输入', 'form', '表单', '用户']):
        suggestions.insert(0, '添加用户输入节点')
    if any(k in desc_lower for k in ['邮件', 'email', '发邮件', 'send email', 'smtp']):
        suggestions.insert(0, '添加邮件发送节点')
        suggestions.insert(1, '配置 SMTP 服务器')
        suggestions.insert(2, '设置多个收件人')
    if any(k in desc_lower for k in ['数据', 'csv', 'excel', '文件']):
        suggestions.insert(0, '添加数据处理节点')
    if any(k in desc_lower for k in ['cumcm', '数学建模', '建模竞赛', '国赛', '建模论文']):
        suggestions = list(SUGGESTION_TEMPLATES['chat_cumcm']) + suggestions

    return suggestions[:MAX_SUGGESTIONS]


# ---------------------------------------------------------------------------
# Suggestion Extraction Patterns
# ---------------------------------------------------------------------------

SUGGESTION_EXTRACTION_PATTERNS: List[str] = [
    r'建议[\s:：](.+?)(?:\n|$)',
    r'你可以(.+?)(?:\n|$)',
    r'是否(.+?)(?:\n|$)',
    r'想(.+?)(?:\n|$)',
    r'尝试(.+?)(?:\n|$)',
]


# ---------------------------------------------------------------------------
# Validation Error Messages
# ---------------------------------------------------------------------------

VALIDATION_MESSAGES = {
    'missing_name': '工作流缺少名称',
    'missing_nodes': '工作流没有节点',
    'missing_start': '工作流没有开始节点',
    'missing_end': '工作流没有结束节点',
    'multiple_starts': '工作流有 {count} 个开始节点，只能有一个',
    'disconnected_nodes': '以下节点未连接到任何其他节点: {nodes}',
    'cycle_detected': '工作流存在循环依赖: {cycle_path}。这会导致执行时无限循环，请修改工作流结构。',
}


# ---------------------------------------------------------------------------
# Supported Node Types (see node_catalog.py)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Cost Estimation Configuration
# ---------------------------------------------------------------------------

# Cost weights per node type (arbitrary units)
NODE_COST_WEIGHTS: Dict[str, float] = {
    'llm': 10.0,
    'prompt': 5.0,
    'agent': 12.0,
    'openai_api': 10.0,
    'http': 3.0,
    'tool': 3.0,
    'code': 2.0,
    'email': 2.0,
    'webhook': 2.0,
    'slack': 2.5,
    'feishu': 2.5,
    'dingtalk': 2.5,
    'wechat_work': 2.5,
    'mysql': 3.0,
    'postgres': 3.0,
    'mongodb': 3.0,
    'redis': 2.0,
    'condition': 0.5,
    'switch': 0.5,
    'merge': 0.5,
    'filter': 0.5,
    'split': 1.0,
    'set': 0.3,
    'input': 0.5,
    'output': 0.5,
    'start': 0.1,
    'end': 0.1,
}

# Premium models with higher cost multiplier
PREMIUM_MODELS = ['gpt-4', 'claude-3', 'claude-3.5', 'gemini-pro']
# Budget-friendly models including local Ollama options
BUDGET_MODELS = ['qwen2.5-coder:7b', 'llama3', 'mistral', 'phi3', 'qwen2.5:7b']

# Complexity multipliers based on node count
COMPLEXITY_MULTIPLIERS: Dict[str, float] = {
    'simple': (1, 5, 1.0),      # (min_nodes, max_nodes, multiplier)
    'moderate': (6, 15, 1.2),
    'complex': (16, 30, 1.5),
    'very_complex': (31, float('inf'), 2.0),
}


def get_cost_multiplier(node_count: int) -> float:
    """Get complexity multiplier based on node count."""
    for level, (min_n, max_n, mult) in COMPLEXITY_MULTIPLIERS.items():
        if min_n <= node_count <= max_n:
            return mult
    return 2.0


# ---------------------------------------------------------------------------
# Workflow Subtypes for Intent Detection
# ---------------------------------------------------------------------------

WORKFLOW_SUBTYPES: List[str] = [
    'yolo_detection',
    'qa_bot',
    'data_processing',
    'translation',
    'moderation',
    'article_generation',
    'customer_service',
    'email_sending',
    'generic',
]

# Keywords for detecting workflow subtypes
SUBTYPE_KEYWORDS: Dict[str, List[str]] = {
    'yolo_detection': [
        'yolo', 'ultralytics', '目标检测', '物体检测', '识别项目',
        'yolo训练', 'yolo 训练', 'yolo检测', 'yolo 检测', 'bounding box',
        '计算机视觉', 'mlops', '识别网站', '检测模型',
    ],
    'qa_bot': [
        '问答', '问答机器人', '客服', 'faq', 'q&a', 'question', 'answer', 
        '问题', '回答', '机器人', 'qa bot', '智能问答'
    ],
    'data_processing': [
        '数据', 'csv', 'excel', '处理', '清洗', '转换', 'etl', 'data', 
        'process', '文件处理', '批量处理', '数据清洗', '数据转换'
    ],
    'translation': [
        '翻译', 'translation', '多语言', 'language', '语言转换', 
        '翻译成', '翻译为', '语言处理'
    ],
    'moderation': [
        '审核', 'moderation', '过滤', 'content', '内容', '敏感', 
        '检查', '合规', '内容审核', '违规检测'
    ],
    'article_generation': [
        '文章', 'article', '生成文章', '写作', '写文章', '内容生成', 
        '创作', '文案', '博客', '内容创作'
    ],
    'customer_service': [
        '客服', 'customer service', 'support', '售后', '服务',
        '客户', '工单', '服务请求', '客户支持'
    ],
    'email_sending': [
        '发邮件', '发送邮件', '发送email', '发email', '寄邮件',
        'send email', 'send a mail', 'email sending', '邮件发送',
        '发一封邮件', '发送一封邮件', '给我发邮件', 'send me',
        '邮件通知', '邮件提醒', '发送通知邮件', '自动发邮件',
        'smtp', '发件人', '收件人', '邮件模板', 'email template',
        'notification email', 'alert email', 'welcome email',
        'activation email', 'verification email', '邮件',
    ],
    'generic': [],
}

# Retry/regenerate keywords
RETRY_KEYWORDS: List[str] = [
    '重试', 'retry', '重新', 'regenerate', '再试', '再来', 
    '重新生成', '再生成', 'try again', 'try another'
]


# ---------------------------------------------------------------------------
# Mock Response for Development/Testing
# ---------------------------------------------------------------------------

MOCK_WORKFLOW_RESPONSES = {
    'qa_bot': {
        'name': '智能问答机器人',
        'description': '基于 AI 的自动问答工作流，能够理解用户问题并给出准确回答',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': '开始', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': '接收问题', 'position': {'x': 280, 'y': 150}, 'config': {'input_name': 'user_question', 'input_type': 'text', 'placeholder': '请输入您的问题'}},
            {'id': 'node_3', 'type': 'llm', 'name': 'AI 回答', 'position': {'x': 460, 'y': 150}, 'config': {'model': 'llama3', 'prompt': '你是一个专业的 AI 助手，请简洁准确地回答用户的问题: {{input.user_question}}', 'temperature': 0.7}},
            {'id': 'node_4', 'type': 'output', 'name': '返回结果', 'position': {'x': 640, 'y': 150}, 'config': {'format': 'text'}},
            {'id': 'node_5', 'type': 'end', 'name': '结束', 'position': {'x': 820, 'y': 150}, 'config': {}},
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''},
        ]
    },
    'data_processing': {
        'name': '数据处理工作流',
        'description': '自动化数据处理流程，包括读取、清洗、转换和输出',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': '开始', 'position': {'x': 100, 'y': 200}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': '读取数据', 'position': {'x': 280, 'y': 200}, 'config': {'input_name': 'source', 'input_type': 'file', 'format': 'csv'}},
            {'id': 'node_3', 'type': 'tool', 'name': '数据清洗', 'position': {'x': 460, 'y': 200}, 'config': {'tool_name': 'data_cleaner', 'operations': ['remove_nulls', 'trim_whitespace', 'validate_types']}},
            {'id': 'node_4', 'type': 'tool', 'name': '数据转换', 'position': {'x': 640, 'y': 200}, 'config': {'tool_name': 'data_transformer', 'operations': ['normalize', 'aggregate']}},
            {'id': 'node_5', 'type': 'output', 'name': '输出结果', 'position': {'x': 820, 'y': 200}, 'config': {'format': 'json', 'destination': 'file'}},
            {'id': 'node_6', 'type': 'end', 'name': '结束', 'position': {'x': 1000, 'y': 200}, 'config': {}},
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''},
            {'id': 'edge_5', 'source': 'node_5', 'target': 'node_6', 'label': ''},
        ]
    },
    'translation': {
        'name': '多语言翻译工作流',
        'description': '自动将文本翻译成多种目标语言',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': '开始', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': '输入文本', 'position': {'x': 280, 'y': 150}, 'config': {'input_name': 'source_text', 'input_type': 'text'}},
            {'id': 'node_3', 'type': 'llm', 'name': '翻译引擎', 'position': {'x': 460, 'y': 150}, 'config': {'model': 'llama3', 'prompt': 'Translate to English: {{input.source_text}}', 'temperature': 0.3}},
            {'id': 'node_4', 'type': 'output', 'name': '输出翻译', 'position': {'x': 640, 'y': 150}, 'config': {'format': 'text'}},
            {'id': 'node_5', 'type': 'end', 'name': '结束', 'position': {'x': 820, 'y': 150}, 'config': {}},
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''},
        ]
    },
    'moderation': {
        'name': '内容审核工作流',
        'description': '自动审核用户提交的内容，过滤违规信息',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': '开始', 'position': {'x': 100, 'y': 200}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': '接收内容', 'position': {'x': 280, 'y': 200}, 'config': {'input_name': 'content', 'input_type': 'text'}},
            {'id': 'node_3', 'type': 'llm', 'name': '内容分析', 'position': {'x': 460, 'y': 200}, 'config': {'model': 'llama3', 'prompt': '分析以下内容是否违规: {{input.content}}，返回 pass 或 fail', 'temperature': 0.1}},
            {'id': 'node_4', 'type': 'condition', 'name': '判断审核', 'position': {'x': 640, 'y': 200}, 'config': {'conditions': [{'field': 'result', 'operator': 'equals', 'value': 'pass'}]}},
            {'id': 'node_5', 'type': 'output', 'name': '通过输出', 'position': {'x': 820, 'y': 100}, 'config': {'format': 'json', 'message': '内容审核通过'}},
            {'id': 'node_6', 'type': 'output', 'name': '拒绝输出', 'position': {'x': 820, 'y': 300}, 'config': {'format': 'json', 'message': '内容违规，已拒绝'}},
            {'id': 'node_7', 'type': 'end', 'name': '结束', 'position': {'x': 1000, 'y': 200}, 'config': {}},
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': '通过'},
            {'id': 'edge_5', 'source': 'node_4', 'target': 'node_6', 'label': '拒绝'},
            {'id': 'edge_6', 'source': 'node_5', 'target': 'node_7', 'label': ''},
            {'id': 'edge_7', 'source': 'node_6', 'target': 'node_7', 'label': ''},
        ]
    },
    'default': {
        'name': '通用工作流',
        'description': '基于 AI 的通用自动化处理流程',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': '开始', 'position': {'x': 100, 'y': 150}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': '接收输入', 'position': {'x': 280, 'y': 150}, 'config': {'input_name': 'user_input', 'input_type': 'text'}},
            {'id': 'node_3', 'type': 'llm', 'name': 'AI 处理', 'position': {'x': 460, 'y': 150}, 'config': {'model': 'llama3', 'prompt': '处理以下输入: {{input.user_input}}', 'temperature': 0.7}},
            {'id': 'node_4', 'type': 'output', 'name': '输出结果', 'position': {'x': 640, 'y': 150}, 'config': {'format': 'text'}},
            {'id': 'node_5', 'type': 'end', 'name': '结束', 'position': {'x': 820, 'y': 150}, 'config': {}},
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''},
        ]
    },
    'email_sending': {
        'name': '邮件自动发送',
        'description': '接收触发事件，自动发送定制化邮件给指定收件人',
        'nodes': [
            {'id': 'node_1', 'type': 'start', 'name': '开始', 'position': {'x': 100, 'y': 200}, 'config': {}},
            {'id': 'node_2', 'type': 'input', 'name': '接收触发', 'position': {'x': 280, 'y': 200}, 'config': {'input_name': 'trigger_event', 'input_type': 'text', 'placeholder': '触发事件描述'}},
            {'id': 'node_3', 'type': 'llm', 'name': '生成内容', 'position': {'x': 460, 'y': 200}, 'config': {'model': 'llama3', 'prompt': '根据以下触发事件生成邮件内容：{{{{input.trigger_event}}}}', 'temperature': 0.7}},
            {'id': 'node_4', 'type': 'email', 'name': '发送邮件', 'position': {'x': 640, 'y': 200}, 'config': {'to': '', 'subject': '自动化通知', 'body': '{{{{nodes.node_3.output}}}}', 'smtpConfig': {}}},
            {'id': 'node_5', 'type': 'end', 'name': '结束', 'position': {'x': 820, 'y': 200}, 'config': {}},
        ],
        'edges': [
            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            {'id': 'edge_3', 'source': 'node_3', 'target': 'node_4', 'label': ''},
            {'id': 'edge_4', 'source': 'node_4', 'target': 'node_5', 'label': ''},
        ]
    },
}


def get_mock_workflow(description: str) -> Dict[str, Any]:
    """
    Get a mock workflow for development/testing when no LLM is available.
    Intelligently selects a workflow template based on description keywords.
    """
    desc_lower = description.lower()

    try:
        from .emotion_workflow import is_emotion_detection_intent, build_emotion_detection_workflow
        if is_emotion_detection_intent(description):
            return build_emotion_detection_workflow(description)
    except ImportError:
        pass

    try:
        from .yolo_workflow import is_yolo_detection_intent, build_yolo_detection_workflow
        if is_yolo_detection_intent(description):
            return build_yolo_detection_workflow(description)
    except ImportError:
        pass

    try:
        from .web_scrape_email_workflow import (
            is_web_scrape_email_intent,
            build_web_scrape_email_workflow,
        )
        if is_web_scrape_email_intent(description):
            return build_web_scrape_email_workflow(description)
    except ImportError:
        pass

    try:
        from .mobile_page_email_workflow import (
            is_mobile_page_email_intent,
            build_mobile_page_email_workflow,
        )
        if is_mobile_page_email_intent(description):
            return build_mobile_page_email_workflow(description)
    except ImportError:
        pass

    # Match based on keywords
    if any(k in desc_lower for k in ['问答', '问答机器人', '客服', 'faq', 'q&a', 'question', 'answer', '问题', '回答', '机器人']):
        return MOCK_WORKFLOW_RESPONSES['qa_bot']

    if any(k in desc_lower for k in ['数据', 'csv', 'excel', '处理', '清洗', '转换', 'etl', 'data', 'process']):
        return MOCK_WORKFLOW_RESPONSES['data_processing']

    if any(k in desc_lower for k in ['翻译', 'translation', '多语言', 'language']):
        return MOCK_WORKFLOW_RESPONSES['translation']

    if any(k in desc_lower for k in ['审核', 'moderation', '审核', '过滤', 'content', '内容', '敏感']):
        return MOCK_WORKFLOW_RESPONSES['moderation']

    if any(k in desc_lower for k in ['发邮件', '发送邮件', '发email', 'send email', 'send a mail',
            '邮件通知', '邮件提醒', '发送通知邮件', '自动发邮件', 'smtp', '发件人',
            '收件人', '邮件模板', 'email template', 'notification email', 'alert email',
            'welcome email', 'activation email', 'verification email', '寄邮件', '邮件发送', '邮件', 'email alert']):
        return MOCK_WORKFLOW_RESPONSES['email_sending']

    return MOCK_WORKFLOW_RESPONSES['default']


# ---------------------------------------------------------------------------
# Error Messages
# ---------------------------------------------------------------------------

ERROR_MESSAGES = {
    'no_provider': '没有可用的 LLM provider。请检查 API Key 配置或确保 Ollama 已启动。',
    'llm_call_failed': 'LLM 调用失败: {error}',
    'parse_failed': '无法解析工作流描述',
    'generation_failed': '生成工作流时遇到了问题',
    'continuation_failed': '处理失败: {error}',
    'modification_failed': '修改失败: {error}',
}


# ---------------------------------------------------------------------------
# Workflow Name Generation
# ---------------------------------------------------------------------------

WORKFLOW_NAME_PREFIXES: List[str] = [
    '自动化', '智能', '高效', '快捷', 'AI', '智能',
    '批量', '实时', '简易', '快速'
]

# Action verbs for name generation
WORKFLOW_ACTION_VERBS: Dict[str, str] = {
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
    '查询': '查询',
    '校验': '校验',
    '清洗': '清洗',
    '汇总': '汇总',
    '匹配': '匹配',
}

# Subject words for name generation
WORKFLOW_SUBJECT_WORDS: Dict[str, str] = {
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
    '产品': '产品',
    '新闻': '新闻',
    '报告': '报告',
    '日志': '日志',
    'API': 'API',
    '网页': '网页',
}


# ---------------------------------------------------------------------------
# API Response Messages
# ---------------------------------------------------------------------------

RESPONSE_MESSAGES = {
    'generation_success': '工作流生成成功',
    'workflow_saved': '工作流已保存',
    'preview_success': '预览生成成功',
    'session_deleted': '会话已删除',
    'workflow_modified': '已根据您的要求修改工作流',
}
