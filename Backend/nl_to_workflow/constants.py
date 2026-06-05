"""
Constants and configuration for NL to Workflow module.
All magic strings, hardcoded values, and configuration are centralized here.
"""

from typing import Dict, List, Any, Tuple

# ---------------------------------------------------------------------------
# Default Configuration (imported from central config to avoid duplication)
# ---------------------------------------------------------------------------

from config.constants import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE

# Fallback model when none is configured (local Ollama model)
FALLBACK_MODEL: str = 'qwen2.5-coder:7b'

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
    if any(k in desc_lower for k in ['邮件', 'email']):
        suggestions.insert(0, '添加邮件发送节点')
    if any(k in desc_lower for k in ['数据', 'csv', 'excel', '文件']):
        suggestions.insert(0, '添加数据处理节点')

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
# Supported Node Types
# ---------------------------------------------------------------------------

SUPPORTED_NODE_TYPES: Dict[str, str] = {
    'start': '开始节点（每个工作流只能有一个开始节点）',
    'end': '结束节点（可以有多个结束节点）',
    'input': '输入节点（获取用户输入或外部数据）',
    'llm': '大语言模型节点（调用 AI 模型，需要配置 model 和 prompt）',
    'prompt': '提示词节点（处理和格式化文本）',
    'condition': '条件判断节点（根据条件分流，需要配置 conditions）',
    'tool': '工具节点（调用外部工具或 API，需要配置 tool_name 和 parameters）',
    'output': '输出节点（返回结果，需要配置 output_format）',
    'code': '代码执行节点（执行自定义代码，需要配置 code）',
    'email': '邮件节点（发送邮件，需要配置 smtp 和内容）',
    'webhook': 'Webhook 节点（发送 HTTP 请求）',
    'http': 'HTTP 请求节点（发送 HTTP 请求）',
}


# ---------------------------------------------------------------------------
# Cost Estimation Configuration
# ---------------------------------------------------------------------------

# Cost weights per node type (arbitrary units)
NODE_COST_WEIGHTS: Dict[str, float] = {
    'llm': 10.0,       # LLM calls are expensive
    'prompt': 5.0,     # Prompt processing
    'http': 3.0,       # HTTP requests
    'tool': 3.0,       # External tool calls
    'code': 2.0,       # Code execution
    'email': 2.0,      # Email sending
    'webhook': 2.0,    # Webhook calls
    'condition': 0.5, # Simple condition check
    'input': 0.5,      # Input processing
    'output': 0.5,     # Output processing
    'start': 0.1,      # Minimal cost
    'end': 0.1,        # Minimal cost
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
    'qa_bot',
    'data_processing',
    'translation',
    'moderation',
    'article_generation',
    'customer_service',
    'generic',
]

# Keywords for detecting workflow subtypes
SUBTYPE_KEYWORDS: Dict[str, List[str]] = {
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
}


def get_mock_workflow(description: str) -> Dict[str, Any]:
    """
    Get a mock workflow for development/testing when no LLM is available.
    Intelligently selects a workflow template based on description keywords.
    """
    desc_lower = description.lower()

    # Match based on keywords
    if any(k in desc_lower for k in ['问答', '问答机器人', '客服', 'faq', 'q&a', 'question', 'answer', '问题', '回答', '机器人']):
        return MOCK_WORKFLOW_RESPONSES['qa_bot']

    if any(k in desc_lower for k in ['数据', 'csv', 'excel', '处理', '清洗', '转换', 'etl', 'data', 'process']):
        return MOCK_WORKFLOW_RESPONSES['data_processing']

    if any(k in desc_lower for k in ['翻译', 'translation', '多语言', 'language']):
        return MOCK_WORKFLOW_RESPONSES['translation']

    if any(k in desc_lower for k in ['审核', 'moderation', '审核', '过滤', 'content', '内容', '敏感']):
        return MOCK_WORKFLOW_RESPONSES['moderation']

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
