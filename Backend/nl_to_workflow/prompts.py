"""
Centralized Prompt Management for NL to Workflow.

This module provides versioned, reusable prompt templates with:
- Structured format instructions for LLM output
- Few-shot examples for different workflow types
- Context-aware prompts with dynamic placeholders
"""

from typing import Dict, Any, Optional, List, Literal, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from .constants import SUPPORTED_NODE_TYPES


class WorkflowType(Enum):
    """Workflow subtype for targeted prompts."""
    QA_BOT = "qa_bot"
    DATA_PROCESSING = "data_processing"
    TRANSLATION = "translation"
    MODERATION = "moderation"
    ARTICLE_GENERATION = "article_generation"
    CUSTOMER_SERVICE = "customer_service"
    EMAIL_SENDING = "email_sending"
    MOBILE_PAGE_EMAIL = "mobile_page_email"
    WEB_SCRAPE_EMAIL = "web_scrape_email"
    YOLO_DETECTION = "yolo_detection"
    EMOTION_DETECTION = "emotion_detection"
    CUMCM = "cumcm"
    GENERIC = "generic"


@dataclass
class PromptVersion:
    """Versioned prompt with metadata."""
    version: str
    created_at: str
    description: str
    system_prompt: str
    user_template: str


@dataclass
class WorkflowGenerationPrompt:
    """Prompt for workflow generation with dynamic examples."""
    system_prompt: str = ""
    user_template: str = ""
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)
    format_instructions: str = ""

    @classmethod
    def create(cls, workflow_type: WorkflowType = WorkflowType.GENERIC) -> "WorkflowGenerationPrompt":
        """Create a prompt configured for the workflow type."""
        prompts = {
            WorkflowType.QA_BOT: cls._qa_bot_prompt(),
            WorkflowType.DATA_PROCESSING: cls._data_processing_prompt(),
            WorkflowType.TRANSLATION: cls._translation_prompt(),
            WorkflowType.MODERATION: cls._moderation_prompt(),
            WorkflowType.ARTICLE_GENERATION: cls._article_generation_prompt(),
            WorkflowType.CUSTOMER_SERVICE: cls._customer_service_prompt(),
            WorkflowType.EMAIL_SENDING: cls._email_sending_prompt(),
            WorkflowType.MOBILE_PAGE_EMAIL: cls._mobile_page_email_prompt(),
            WorkflowType.WEB_SCRAPE_EMAIL: cls._web_scrape_email_prompt(),
            WorkflowType.YOLO_DETECTION: cls._yolo_detection_prompt(),
            WorkflowType.EMOTION_DETECTION: cls._emotion_detection_prompt(),
            WorkflowType.CUMCM: cls._cumcm_prompt(),
            WorkflowType.GENERIC: cls._generic_prompt(),
        }
        return prompts.get(workflow_type, cls._generic_prompt())

    @classmethod
    def _format_instructions_raw(cls) -> str:
        """Get raw format instructions string (without brace escaping)."""
        return """请严格按照以下JSON格式输出，不要包含任何其他内容：

{
    "name": "工作流名称（简洁、有意义）",
    "description": "工作流功能描述（1-2句话）",
    "nodes": [
        {
            "id": "唯一ID（如 node_1, node_2...）",
            "type": "节点类型（start/end/input/llm/condition/tool/code/output）",
            "name": "节点显示名称",
            "position": {"x": 数字, "y": 数字},
            "config": { /* 节点配置 */ }
        }
    ],
    "edges": [
        {
            "id": "唯一ID（如 edge_1, edge_2...）",
            "source": "源节点ID",
            "target": "目标节点ID",
            "label": "连线标签（可为空字符串）"
        }
    ]
}

LLM节点config格式：
{"model": "模型名", "system_prompt": "系统提示词（角色设定）", "user_template": "用户消息模板，{input}会被替换为上游节点的输出", "temperature": 温度值}

Input节点config格式：
{"input_name": "变量名（英文）", "input_type": "text/number/object"}

Code节点config格式（必须可执行，运行时为 Python）：
{"language": "python", "code": "使用 input 读取上游数据，最终赋值给 output"}
CUMCM/科学计算 Code 节点可使用 numpy/scipy/pandas/matplotlib(Agg)；禁止 os/subprocess/eval。

Loop节点config格式：
{"loop_type": "for_each", "items_source": "input", "item_variable": "item", "max_iterations": 10}

Image/Video节点config格式：
图像：{"provider": "agnes", "model": "agnes-image-2.1-flash", "prompt": "{prompt}", "size": "1024x1024"}
视频：{"provider": "agnes", "model": "agnes-video-v2.0", "prompt": "{prompt}", "inputImage": "{images.0.url}", "duration": 5}
禁止编造系统不存在的字段（如 script 代替 code、item_var 代替 item_variable、任意 {{中间变量}} 假引用）。
"""

    @classmethod
    def _format_instructions(cls) -> str:
        """Get format instructions with braces escaped for .format()."""
        return cls._format_instructions_raw().replace('{', '{{').replace('}', '}}')

    @classmethod
    def _node_types_description(cls) -> str:
        """Format supported node types."""
        lines = []
        for node_type, desc in SUPPORTED_NODE_TYPES.items():
            lines.append(f"- **{node_type}**: {desc}")
        return '\n'.join(lines)

    @classmethod
    def _generic_prompt(cls) -> "WorkflowGenerationPrompt":
        """Generic workflow generation prompt."""
        return cls(
            system_prompt="""你是一个专业的 AI 工作流设计助手。你擅长理解用户需求，并生成清晰、高效的工作流结构。

工作流设计原则：
1. 保持简单：优先使用最少的节点完成需求
2. 清晰流程：确保每个节点都有明确的输入输出
3. 错误处理：考虑异常情况的处理路径
4. 可执行性：生成的节点配置必须实际可执行""",
            user_template="""## 用户需求
{description}

## 可用节点类型
{node_types}

## 输出格式要求
{format_instructions}

## 注意事项
1. 所有节点必须有唯一ID
2. 所有连线必须有唯一ID
3. LLM节点的user_template中使用 {{input}} 引用上游输入数据
4. 只输出JSON，不要有其他内容
5. 确保工作流可以实际执行""",
            few_shot_examples=cls._generic_examples(),
            format_instructions=cls._format_instructions()
        )

    @classmethod
    def _generic_examples(cls) -> List[Dict[str, str]]:
        """Few-shot examples for generic workflows."""
        return [
            {
                "input": "帮我做一个问答机器人，用户问问题，AI自动回答",
                "output": json.dumps({
                    "name": "智能问答机器人",
                    "description": "接收用户问题，AI自动生成回答并返回",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 100, "y": 100}, "config": {}},
                        {"id": "node_2", "type": "input", "name": "接收问题", "position": {"x": 280, "y": 100}, "config": {"input_name": "user_question", "input_type": "text"}},
                        {"id": "node_3", "type": "llm", "name": "AI回答", "position": {"x": 460, "y": 100}, "config": {"model": "llama3", "system_prompt": "你是一个专业的AI助手", "user_template": "请简洁准确地回答用户的问题：{input}", "temperature": 0.7}},
                        {"id": "node_4", "type": "output", "name": "返回结果", "position": {"x": 640, "y": 100}, "config": {"format": "text"}},
                        {"id": "node_5", "type": "end", "name": "结束", "position": {"x": 820, "y": 100}, "config": {}}
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""},
                        {"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}
                    ]
                })
            },
            {
                "input": "分析用户评论，如果是投诉就转人工，如果是表扬就回复感谢",
                "output": json.dumps({
                    "name": "评论智能分类处理",
                    "description": "分析评论情感，自动分流处理投诉和表扬",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 100, "y": 150}, "config": {}},
                        {"id": "node_2", "type": "input", "name": "接收评论", "position": {"x": 280, "y": 150}, "config": {"input_name": "comment", "input_type": "text"}},
                        {"id": "node_3", "type": "llm", "name": "情感分析", "position": {"x": 460, "y": 150}, "config": {"model": "llama3", "system_prompt": "你是一个情感分析专家", "user_template": "分析以下评论的情感倾向，返回 positive 或 negative：{input}", "temperature": 0.3}},
                        {"id": "node_4", "type": "condition", "name": "判断情感", "position": {"x": 640, "y": 150}, "config": {"conditions": [{"field": "sentiment", "operator": "equals", "value": "positive"}]}},
                        {"id": "node_5", "type": "tool", "name": "回复感谢", "position": {"x": 820, "y": 80}, "config": {"tool_name": "send_email", "parameters": {"template": "thanks"}}},
                        {"id": "node_6", "type": "tool", "name": "转人工", "position": {"x": 820, "y": 220}, "config": {"tool_name": "transfer_to_agent", "parameters": {}}},
                        {"id": "node_7", "type": "end", "name": "结束", "position": {"x": 1000, "y": 150}, "config": {}}
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""},
                        {"id": "edge_4", "source": "node_4", "target": "node_5", "label": "表扬"},
                        {"id": "edge_5", "source": "node_4", "target": "node_6", "label": "投诉"},
                        {"id": "edge_6", "source": "node_5", "target": "node_7", "label": ""},
                        {"id": "edge_7", "source": "node_6", "target": "node_7", "label": ""}
                    ]
                })
            }
        ]

    @classmethod
    def _qa_bot_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for QA bot workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个智能客服机器人设计专家。你擅长设计问答系统、FAQ机器人、智能客服等工作流。

设计要点：
1. 输入处理：设计友好的用户输入节点
2. 意图识别：使用LLM节点理解用户问题
3. 知识检索：考虑是否需要知识库检索
4. 回复生成：生成自然、准确的回答
5. 多轮对话：支持追问和澄清"""
        return base

    @classmethod
    def _data_processing_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for data processing workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个数据处理工作流设计专家。你擅长设计ETL、数据清洗、数据转换等工作流。

设计要点：
1. 数据输入：支持多种数据源（CSV、API、数据库）
2. 数据验证：添加数据质量检查节点
3. 转换逻辑：使用代码节点或工具节点处理数据
4. 错误处理：处理缺失值、格式错误等情况
5. 结果输出：支持多种格式输出"""
        return base

    @classmethod
    def _translation_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for translation workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个多语言翻译工作流设计专家。

设计要点：
1. 源语言检测：自动检测输入语言
2. 翻译引擎：使用高质量翻译模型
3. 后处理：处理术语一致性、格式保留
4. 多语言支持：设计可扩展的多语言架构"""
        return base

    @classmethod
    def _moderation_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for content moderation workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个内容审核工作流设计专家。

设计要点：
1. 内容输入：接收文本、图片或视频
2. 多维度检测：暴力、仇恨、色情、垃圾广告等
3. 分级处理：根据违规程度采取不同措施
4. 人工复核：复杂案例转人工审核
5. 申诉机制：支持用户申诉"""
        return base

    @classmethod
    def _article_generation_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for article generation workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个内容生成工作流设计专家。

设计要点：
1. 主题理解：分析用户输入的主题
2. 大纲生成：先规划文章结构
3. 分段生成：分步骤生成各段落
4. 质量审核：检查逻辑连贯性
5. 格式处理：Markdown或HTML输出"""
        return base

    @classmethod
    def _customer_service_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for customer service workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个客服工作流设计专家。

设计要点：
1. 智能分流：根据问题类型分配处理
2. FAQ匹配：快速匹配常见问题
3. 意图识别：理解用户真实需求
4. 工单创建：需要人工时创建工单
5. 满意度收集：闭环收集反馈"""
        return base

    @classmethod
    def _email_sending_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for email sending workflows."""
        base = cls._generic_prompt()
        base.system_prompt = """你是一个邮件自动化工作流设计专家。你擅长设计各种邮件发送场景，包括通知邮件、营销邮件、触发式邮件、工作流通知等。

邮件节点配置要点：
1. **收件人 (to)**：必填，支持多个收件人（逗号分隔），也支持 {{变量}} 插值
2. **抄送 (cc)**：可选，多个用逗号分隔
3. **密送 (bcc)**：可选，用于隐藏收件人
4. **发件人 (fromEmail)**：可选，默认使用系统配置的发件地址
5. **主题 (subject)**：必填，支持 {{变量}} 插值
6. **正文 (body)**：必填，支持纯文本或 HTML，支持 {{变量}} 插值
7. **SMTP 配置**：可选，如不配置则使用系统默认 SMTP
   - server: SMTP 服务器地址（如 smtp.gmail.com）
   - port: 端口（常用 587 for TLS, 465 for SSL, 25 for unencrypted）
   - username/password: 认证信息
   - useTls/useSsl: 加密方式

设计原则：
1. 工作流必须包含 email 类型节点
2. 邮件节点前通常需要 LLM 节点生成内容或格式化数据
3. 考虑添加条件分支处理发送失败的情况
4. 收件人、主题、正文应支持变量插值以实现动态内容
5. 可以结合 input 节点或 trigger 节点获取外部数据"""
        base.few_shot_examples = [
            {
                "input": "当有新用户注册时，自动发送一封欢迎邮件到用户的邮箱",
                "output": json.dumps({
                    "name": "新用户欢迎邮件",
                    "description": "新用户注册后自动发送欢迎邮件",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 100, "y": 150}, "config": {}},
                        {"id": "node_2", "type": "input", "name": "接收注册信息", "position": {"x": 280, "y": 150}, "config": {"input_name": "registration_data", "input_type": "object", "description": "包含 email, username 等字段"}},
                        {"id": "node_3", "type": "llm", "name": "生成欢迎内容", "position": {"x": 460, "y": 150}, "config": {"model": "llama3", "prompt": "为新用户生成一封欢迎邮件正文，用户名：{{{{input.registration_data.username}}}}。语气友好、专业。", "temperature": 0.7}},
                        {"id": "node_4", "type": "email", "name": "发送欢迎邮件", "position": {"x": 640, "y": 150}, "config": {"to": "{{{{input.registration_data.email}}}}", "subject": "欢迎加入！{{{{input.registration_data.username}}}}", "body": "{{{{nodes.node_3.output}}}}", "isHtml": False}},
                        {"id": "node_5", "type": "end", "name": "结束", "position": {"x": 820, "y": 150}, "config": {}}
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""},
                        {"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}
                    ]
                })
            },
            {
                "input": "每天早上9点查询数据库，把业绩报表发送给 manager@company.com",
                "output": json.dumps({
                    "name": "每日业绩报表发送",
                    "description": "定时查询数据并发送业绩报表邮件",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 100, "y": 200}, "config": {}},
                        {"id": "node_2", "type": "tool", "name": "查询业绩数据", "position": {"x": 280, "y": 200}, "config": {"tool_name": "db_query", "parameters": {"sql": "SELECT * FROM daily_sales WHERE date = CURDATE()"}}},
                        {"id": "node_3", "type": "llm", "name": "生成报表内容", "position": {"x": 460, "y": 200}, "config": {"model": "llama3", "prompt": "根据以下业绩数据生成一份简洁的日报摘要：{{{{input.sales_data}}}}", "temperature": 0.3}},
                        {"id": "node_4", "type": "email", "name": "发送报表邮件", "position": {"x": 640, "y": 200}, "config": {"to": "manager@company.com", "subject": "【每日业绩】{{{{workflow.date}}}} 业绩报告", "body": "{{{{nodes.node_3.output}}}}", "isHtml": True, "smtpConfig": {"server": "smtp.company.com", "port": 587, "useTls": True}}},
                        {"id": "node_5", "type": "end", "name": "结束", "position": {"x": 820, "y": 200}, "config": {}}
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""},
                        {"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}
                    ]
                })
            },
            {
                "input": "当网站出错时，发送告警邮件给运维团队，如果是严重错误还要同时通知技术负责人",
                "output": json.dumps({
                    "name": "网站错误告警通知",
                    "description": "根据错误严重程度发送不同级别的告警邮件",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 100, "y": 200}, "config": {}},
                        {"id": "node_2", "type": "input", "name": "接收错误信息", "position": {"x": 280, "y": 200}, "config": {"input_name": "error_event", "input_type": "object", "description": "包含 level, message, timestamp 等字段"}},
                        {"id": "node_3", "type": "condition", "name": "判断严重程度", "position": {"x": 460, "y": 200}, "config": {"conditions": [{"field": "error_event.level", "operator": "equals", "value": "critical"}]}},
                        {"id": "node_4", "type": "email", "name": "告警运维团队", "position": {"x": 640, "y": 100}, "config": {"to": "ops-team@company.com", "subject": "【告警】{{{{input.error_event.level}}}} - {{{{input.error_event.message}}}}", "body": "错误等级：{{{{input.error_event.level}}}}\n错误信息：{{{{input.error_event.message}}}}\n发生时间：{{{{input.error_event.timestamp}}}}", "isHtml": False}},
                        {"id": "node_5", "type": "email", "name": "通知技术负责人", "position": {"x": 640, "y": 300}, "config": {"to": "cto@company.com", "subject": "【紧急】严重错误 - {{{{input.error_event.message}}}}", "body": "检测到严重错误，请立即处理！\n\n错误信息：{{{{input.error_event.message}}}}\n发生时间：{{{{input.error_event.timestamp}}}}", "isHtml": False}},
                        {"id": "node_6", "type": "end", "name": "结束", "position": {"x": 820, "y": 200}, "config": {}}
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": "一般错误"},
                        {"id": "edge_4", "source": "node_3", "target": "node_5", "label": "严重错误"},
                        {"id": "edge_5", "source": "node_3", "target": "node_6", "label": ""},
                        {"id": "edge_6", "source": "node_4", "target": "node_6", "label": ""},
                        {"id": "edge_7", "source": "node_5", "target": "node_6", "label": ""}
                    ]
                })
            }
        ]
        return base

    @classmethod
    def _mobile_page_email_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt for mobile HTML page generation + email delivery."""
        base = cls._email_sending_prompt()
        base.system_prompt = """你是移动端网页与邮件自动化专家。设计「生成详细手机网页 HTML + 发送邮件」工作流。

必须包含：
1. **input** 节点：接收页面主题/内容要点（input_name: page_topic）
2. **llm** 节点：使用 agnes-2.0-flash，生成完整移动端 HTML（内联 CSS，max-width 480px，适配手机竖屏）
3. **email** 节点：isHtml=true，body 引用 LLM 输出（如 {text}），to 使用用户提供的邮箱
4. **output** 节点：展示 HTML 或发送结果

LLM prompt 应要求输出完整 HTML，禁止仅输出 Markdown。
邮件 SMTP 默认 smtp.qq.com:587（useTls=true），收件人若用户已给出则写入 to 字段。"""
        base.few_shot_examples = [
            {
                "input": "生成手机网页详细内容，发到 3488394996@qq.com",
                "output": json.dumps({
                    "name": "手机网页生成并发送邮件",
                    "description": "LLM 生成移动端 HTML 详情页并邮件发送",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 80, "y": 200}, "config": {}},
                        {"id": "node_2", "type": "input", "name": "页面主题", "position": {"x": 280, "y": 200}, "config": {"input_name": "page_topic", "input_type": "text"}},
                        {"id": "node_3", "type": "llm", "name": "生成手机网页", "position": {"x": 520, "y": 200}, "config": {"model": "agnes-2.0-flash", "provider": "agnes", "prompt": "生成移动端 HTML 详情页，主题：{page_topic}", "temperature": 0.6}},
                        {"id": "node_4", "type": "email", "name": "发送邮件", "position": {"x": 760, "y": 200}, "config": {"to": "3488394996@qq.com", "subject": "【手机网页】{page_topic}", "body": "{text}", "isHtml": True, "smtpConfig": {"server": "smtp.qq.com", "port": 587, "useTls": True}}},
                        {"id": "node_5", "type": "output", "name": "输出", "position": {"x": 980, "y": 200}, "config": {"template": "{text}", "format": "text"}},
                        {"id": "node_6", "type": "end", "name": "结束", "position": {"x": 1180, "y": 200}, "config": {}},
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""},
                        {"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""},
                        {"id": "edge_5", "source": "node_5", "target": "node_6", "label": ""},
                    ],
                }),
            },
        ]
        return base

    @classmethod
    def _web_scrape_email_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt for website scrape → format → email delivery."""
        base = cls._email_sending_prompt()
        base.system_prompt = """你是网站信息采集与邮件自动化专家。设计「从网站抓取信息 → LLM 排版 → 发送邮件」工作流。

必须包含（按顺序）：
1. **input** 节点：接收目标网站 URL（input_name: target_url）
2. **web_scraper** 节点：url 引用 {target_url}，selectors 抓取 title/headings/content
3. **llm** 节点：使用 agnes-2.0-flash，将抓取结果整理为 HTML 邮件正文（内联 CSS，结构清晰）
4. **email** 节点：isHtml=true，body 引用 LLM 输出（{text}），to 使用用户提供的邮箱
5. **output** 节点：展示排版结果或发送状态

LLM prompt 应引用上游变量 {url}、{data}。邮件 SMTP 默认 smtp.qq.com:587（useTls=true）。"""
        base.few_shot_examples = [
            {
                "input": "先去网站上收集信息，排版好之后，发到 3488394996@qq.com",
                "output": json.dumps({
                    "name": "网站信息采集排版并发送邮件",
                    "description": "抓取网站内容，LLM 排版后 HTML 邮件发送",
                    "nodes": [
                        {"id": "node_1", "type": "start", "name": "开始", "position": {"x": 80, "y": 200}, "config": {}},
                        {"id": "node_2", "type": "input", "name": "目标网站", "position": {"x": 260, "y": 200}, "config": {"input_name": "target_url", "input_type": "text"}},
                        {"id": "node_3", "type": "web_scraper", "name": "采集网站信息", "position": {"x": 480, "y": 200}, "config": {"url": "{target_url}", "selectors": [{"name": "title", "selector": "h1"}, {"name": "content", "selector": "article, main, body"}]}},
                        {"id": "node_4", "type": "llm", "name": "排版整理", "position": {"x": 700, "y": 200}, "config": {"model": "agnes-2.0-flash", "provider": "agnes", "prompt": "将抓取数据 {data} 排版为 HTML 邮件正文，来源 {url}", "temperature": 0.5}},
                        {"id": "node_5", "type": "email", "name": "发送邮件", "position": {"x": 920, "y": 200}, "config": {"to": "3488394996@qq.com", "subject": "【网站信息摘要】", "body": "{text}", "isHtml": True, "useGlobalSmtp": True}},
                        {"id": "node_6", "type": "output", "name": "输出", "position": {"x": 1120, "y": 200}, "config": {"template": "{text}", "format": "text"}},
                        {"id": "node_7", "type": "end", "name": "结束", "position": {"x": 1300, "y": 200}, "config": {}},
                    ],
                    "edges": [
                        {"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""},
                        {"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""},
                        {"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""},
                        {"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""},
                        {"id": "edge_5", "source": "node_5", "target": "node_6", "label": ""},
                        {"id": "edge_6", "source": "node_6", "target": "node_7", "label": ""},
                    ],
                }),
            },
        ]
        return base

    @classmethod
    def _yolo_detection_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt specialized for YOLO MLOps / detection website pipelines."""
        base = cls._generic_prompt()
        base.system_prompt = """你是 Flowly 平台的 MLOps / 计算机视觉工作流设计专家，擅长 YOLO 目标检测全链路。

## 必须使用的节点类型（按顺序串联，不可替换为 llm 问答链）
1. **dataset_upload** — 上传 YOLO 格式标注数据集
2. **yolo_training** — 本地 Ultralytics YOLOv8 训练（trainingMode: local, dataSourceType: upstream）
3. **project_profiler** — 场景分析（websiteType: detection）
4. **website_generator** — 生成识别网站脚手架（含 wizard.siteName、usageDescription、waitForCompletion: true）
5. **backend_setup** — Agent 完善 Flask 后端（agentMode: auto）
6. **frontend_setup** — Agent 搭建现代化前端（agentMode: auto）
7. **ui_beautify** — Agent UI 美化（agentMode: auto）
8. **environment_provision** — 运行环境配置
9. **site_qa** — 站点自查
10. **site_code_review** — 代码复查修复（maxRounds: 2）
11. **site_preview** — 站点预览
12. **project_agent** — 项目 Agent

## 设计原则
- 若用户明确要求「AI 分工」「现代化 UI」「精细建站」，使用上述完整 v2 链（含 backend_setup / frontend_setup / ui_beautify / site_code_review）
- 若用户仅要求快速建站，可省略 5–7、10，使用简化链（website_generator 后直接 environment_provision）
- 不要使用 start/end/input/llm 组成简单问答链
- yolo_training.config 应包含 yoloVersion(v8)、modelVariant(n/s/m)、epochs、batchSize、imageSize
- 若用户提到 epochs、站点名称，写入对应节点 config
- edges 按上述顺序线性连接"""
        base.few_shot_examples = [
            {
                "input": "我有 YOLO 标注数据集，想训练 YOLOv8 并自动生成识别网站，训练 30 epoch",
                "output": json.dumps({
                    "name": "YOLO 目标检测项目",
                    "description": "数据集上传 → YOLO 训练 → 建站 → QA → 预览",
                    "nodes": [
                        {"id": "dataset_upload_1", "type": "dataset_upload", "name": "上传标注数据集", "position": {"x": 80, "y": 200}, "config": {"format": "yolo", "sourceType": "upload"}},
                        {"id": "yolo_training_1", "type": "yolo_training", "name": "YOLO 训练", "position": {"x": 280, "y": 200}, "config": {"trainingMode": "local", "yoloVersion": "v8", "modelVariant": "n", "epochs": 30, "batchSize": 16, "imageSize": 640, "dataSourceType": "upstream"}},
                        {"id": "project_profiler_1", "type": "project_profiler", "name": "场景分析", "position": {"x": 480, "y": 200}, "config": {"websiteType": "detection", "useLlmEnrich": True}},
                        {"id": "website_generator_1", "type": "website_generator", "name": "生成识别网站", "position": {"x": 680, "y": 200}, "config": {"websiteType": "detection", "wizard": {"siteName": "YOLO 识别系统", "usageDescription": "上传图片进行目标检测", "wizardCompleted": True}}},
                        {"id": "environment_provision_1", "type": "environment_provision", "name": "环境配置", "position": {"x": 880, "y": 200}, "config": {"runtimeMode": "desktop"}},
                        {"id": "site_qa_1", "type": "site_qa", "name": "站点自查", "position": {"x": 1080, "y": 200}, "config": {"websiteType": "detection", "qaProfile": "default"}},
                        {"id": "site_preview_1", "type": "site_preview", "name": "站点预览", "position": {"x": 1280, "y": 200}, "config": {"qaProfile": "default"}},
                        {"id": "project_agent_1", "type": "project_agent", "name": "项目 Agent", "position": {"x": 1480, "y": 200}, "config": {"qaProfile": "default", "autoQaAfterEdit": True}},
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
                }),
            },
            {
                "input": "训练 YOLO 并分工完善现代化网站，后端前端 UI 都要 AI 优化",
                "output": json.dumps({
                    "name": "YOLO 识别项目 v2",
                    "description": "训练 → 脚手架 → 后端/前端/UI Agent → QA → 复查 → 预览",
                    "nodes": [
                        {"id": "dataset_upload_1", "type": "dataset_upload", "name": "上传数据集", "position": {"x": 80, "y": 200}, "config": {"format": "yolo", "sourceType": "upload"}},
                        {"id": "yolo_training_1", "type": "yolo_training", "name": "YOLO 训练", "position": {"x": 280, "y": 200}, "config": {"trainingMode": "local", "yoloVersion": "v8", "modelVariant": "n", "epochs": 30, "batchSize": 16, "imageSize": 640}},
                        {"id": "project_profiler_1", "type": "project_profiler", "name": "场景分析", "position": {"x": 480, "y": 200}, "config": {"websiteType": "detection"}},
                        {"id": "website_generator_1", "type": "website_generator", "name": "网站脚手架", "position": {"x": 680, "y": 200}, "config": {"websiteType": "detection", "waitForCompletion": True, "wizard": {"siteName": "智能检测站", "usageDescription": "上传图片检测", "wizardCompleted": True}}},
                        {"id": "backend_setup_1", "type": "backend_setup", "name": "后端搭建", "position": {"x": 880, "y": 200}, "config": {"agentMode": "auto"}},
                        {"id": "frontend_setup_1", "type": "frontend_setup", "name": "前端搭建", "position": {"x": 1080, "y": 200}, "config": {"agentMode": "auto"}},
                        {"id": "ui_beautify_1", "type": "ui_beautify", "name": "UI 美化", "position": {"x": 1280, "y": 200}, "config": {"agentMode": "auto"}},
                        {"id": "environment_provision_1", "type": "environment_provision", "name": "环境配置", "position": {"x": 1480, "y": 200}, "config": {"runtimeMode": "desktop"}},
                        {"id": "site_qa_1", "type": "site_qa", "name": "站点自查", "position": {"x": 1680, "y": 200}, "config": {"websiteType": "detection"}},
                        {"id": "site_code_review_1", "type": "site_code_review", "name": "代码复查", "position": {"x": 1880, "y": 200}, "config": {"maxRounds": 2}},
                        {"id": "site_preview_1", "type": "site_preview", "name": "站点预览", "position": {"x": 2080, "y": 200}, "config": {}},
                        {"id": "project_agent_1", "type": "project_agent", "name": "项目 Agent", "position": {"x": 2280, "y": 200}, "config": {"autoQaAfterEdit": True}},
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
                }),
            },
        ]
        return base

    @classmethod
    def _emotion_detection_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt for AI-autonomous facial-emotion MLOps pipelines."""
        base = cls._yolo_detection_prompt()
        base.system_prompt = """你是 Flowly 平台的 AI MLOps 架构师，专精 **人脸表情 / 情绪检测** 全链路。

## 任务
根据用户自然语言 **自主设计** 完整工作流 JSON（非固定模板拷贝）。必须体现用户提到的场景、情绪类别、训练参数、站点品牌。

## 必须使用的节点类型（按顺序线性串联）
1. **dataset_upload** — YOLO 格式人脸表情数据集（config.format: yolo）
2. **yolo_training** — Ultralytics YOLOv8 训练（trainingMode: local, dataSourceType: upstream）
3. **project_profiler** — AI 场景分析（websiteType: detection, **useLlmEnrich: true**）
4. **website_generator** — 生成情绪识别网站（wizard 含 siteName、usageDescription、primaryColor、wizardCompleted: true）
5. **environment_provision** — 运行环境
6. **site_qa** — 站点自查
7. **site_preview** — 预览
8. **project_agent** — 项目 Agent（autoQaAfterEdit: true，供用户后续 AI 改站）

## 自主设计原则
- 根据用户描述 **自行决定** 站点名称、主色调、epochs、模型规格（n/s/m）、情绪类别文案
- 常见类别：happy / sad / angry / neutral / surprise（用户指定时以用户为准）
- **禁止** 用 start/end/input/llm 拼简单问答链代替训练+建站
- website_generator.wizard 的 usageDescription 应面向终端用户，说明如何上传人脸照片识别情绪
- project_profiler 必须开启 useLlmEnrich 以让 AI 生成场景文案"""
        base.few_shot_examples = [
            {
                "input": "帮我做一个情绪检测系统，上传人脸图片训练 YOLO，实时看训练曲线，并生成情绪识别网站",
                "output": json.dumps({
                    "name": "情绪检测系统",
                    "description": "人脸表情 YOLO 训练 → AI 场景分析 → 情绪识别网站 → QA → Agent",
                    "nodes": [
                        {"id": "dataset_upload_1", "type": "dataset_upload", "name": "上传人脸表情数据集", "position": {"x": 80, "y": 200}, "config": {"format": "yolo", "sourceType": "upload"}},
                        {"id": "yolo_training_1", "type": "yolo_training", "name": "情绪模型训练", "position": {"x": 280, "y": 200}, "config": {"trainingMode": "local", "yoloVersion": "v8", "modelVariant": "n", "epochs": 30, "batchSize": 8, "imageSize": 640, "dataSourceType": "upstream"}},
                        {"id": "project_profiler_1", "type": "project_profiler", "name": "AI 场景分析", "position": {"x": 480, "y": 200}, "config": {"websiteType": "detection", "useLlmEnrich": True, "wizardScenario": "面部表情情绪识别"}},
                        {"id": "website_generator_1", "type": "website_generator", "name": "生成情绪识别网站", "position": {"x": 680, "y": 200}, "config": {"websiteType": "detection", "wizard": {"siteName": "情绪检测系统", "usageDescription": "上传人脸照片，识别 happy/sad/angry/neutral/surprise", "primaryColor": "#8b5cf6", "wizardCompleted": True}}},
                        {"id": "environment_provision_1", "type": "environment_provision", "name": "环境配置", "position": {"x": 880, "y": 200}, "config": {"runtimeMode": "desktop"}},
                        {"id": "site_qa_1", "type": "site_qa", "name": "站点自查", "position": {"x": 1080, "y": 200}, "config": {"websiteType": "detection", "qaProfile": "default"}},
                        {"id": "site_preview_1", "type": "site_preview", "name": "站点预览", "position": {"x": 1280, "y": 200}, "config": {"qaProfile": "default"}},
                        {"id": "project_agent_1", "type": "project_agent", "name": "项目 Agent", "position": {"x": 1480, "y": 200}, "config": {"qaProfile": "default", "autoQaAfterEdit": True, "agentMode": "auto"}},
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
                }),
            },
        ]
        return base

    @classmethod
    def _cumcm_prompt(cls) -> "WorkflowGenerationPrompt":
        """Prompt for CUMCM mathematical modeling full pipeline."""
        from .cumcm_prompts import CUMCM_WORKFLOW_GENERATION_SYSTEM, cumcm_few_shot_example

        base = cls._generic_prompt()
        base.system_prompt = CUMCM_WORKFLOW_GENERATION_SYSTEM
        base.few_shot_examples = [cumcm_few_shot_example()]
        base.user_template = """## 用户需求
{description}

## 可用节点类型
{node_types}

## 输出格式要求
{format_instructions}

## CUMCM 流水线要点
1. 必须含 input(赛题JSON) → llm(解析/分解) → code(预处理/求解/图表) → llm(论文各章) → file_writer
2. 子问题并行链路：每问 pick→model→solver→interpret 四节点
3. solver_type 写入 llm 模型建立节点的 JSON 输出，供 code 求解节点路由
4. 论文输出遵守 Markdown/docx 规范（## 章节标题、$$公式$$ (n)、中文图题≤15字）
5. 只输出 JSON，不要有其他内容"""
        return base

    def format(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Format the prompt with user input.

        Args:
            description: User's workflow description
            context: Additional context variables

        Returns:
            Dict with 'system' and 'user' messages
        """
        # Build few-shot section
        few_shot_section = ""
        if self.few_shot_examples:
            few_shot_lines = ["\n\n## 示例参考\n"]
            for i, example in enumerate(self.few_shot_examples, 1):
                few_shot_lines.append(f"### 示例{i}：")
                example_input = example.get('input') or example.get('description') or ''
                few_shot_lines.append(f"输入：{example_input}")
                few_shot_lines.append(f"输出：{example.get('output', '')}")
            few_shot_section = '\n'.join(few_shot_lines)

        safe_description = description.replace('{', '{{').replace('}', '}}')
        safe_context = json.dumps(context, ensure_ascii=False).replace('{', '{{').replace('}', '}}') if context else ""

        # Format user message
        user_message = self.user_template.format(
            description=safe_description,
            node_types=self._node_types_description(),
            format_instructions=self.format_instructions,
            context=safe_context
        ) + few_shot_section

        return {
            "system": self.system_prompt,
            "user": user_message
        }


# Modification prompt templates
class ModificationPrompt:
    """Prompt templates for workflow modifications."""

    @staticmethod
    def modify(
        current_workflow: Dict[str, Any],
        user_feedback: str
    ) -> Dict[str, str]:
        """Generate prompt for modifying existing workflow."""
        return {
            "system": """你是一个工作流修改专家。根据用户的反馈，精确修改工作流。

修改原则：
1. 最小修改：只修改必要的部分，保持其余节点和连线不变
2. 保持一致：确保修改后工作流仍然有效（有start/end节点）
3. 明确意图：准确理解用户想要什么改变
4. 保持ID：如果节点ID没变化，保持不变
5. 完整输出：必须返回完整的workflow JSON（name、description、nodes、edges四个字段全部保留）""",
            "user": f"""## 当前工作流
```json
{json.dumps(current_workflow, ensure_ascii=False, indent=2)}
```

## 用户反馈
{user_feedback}

## 要求
根据用户反馈修改工作流。必须返回完整的workflow JSON，四个字段都要有：name、description、nodes、edges。

只输出JSON，不要有其他内容。"""
        }

    @staticmethod
    def delete(
        current_workflow: Dict[str, Any],
        user_feedback: str
    ) -> Dict[str, str]:
        """Generate prompt for deleting from workflow."""
        return {
            "system": """你是一个工作流修改专家。理解用户的删除意图，精确删除指定节点或连线。

删除原则：
1. 最小删除：只删除用户指定的节点及其所有连线
2. 保持有效：删除后确保剩余节点仍然连通
3. 保持ID：未被删除的节点ID保持不变
4. 完整输出：必须返回完整的workflow JSON（name、description、nodes、edges四个字段全部保留）""",
            "user": f"""## 当前工作流
```json
{json.dumps(current_workflow, ensure_ascii=False, indent=2)}
```

## 用户要求删除
{user_feedback}

## 要求
删除指定的节点及其连线。必须返回完整的workflow JSON，四个字段都要有：name、description、nodes、edges。

只输出JSON，不要有其他内容。"""
        }


# Prompt registry for versioning
class PromptRegistry:
    """Registry for managing prompt versions."""

    _prompts: Dict[str, PromptVersion] = {}

    @classmethod
    def register(cls, name: str, prompt: PromptVersion):
        """Register a new prompt version."""
        cls._prompts[name] = prompt

    @classmethod
    def get(cls, name: str) -> Optional[PromptVersion]:
        """Get a prompt by name."""
        return cls._prompts.get(name)

    @classmethod
    def list_versions(cls, name: str) -> List[str]:
        """List all versions of a prompt."""
        # Simple implementation - just return the stored version
        prompt = cls._prompts.get(name)
        return [prompt.version] if prompt else []


# Convenience functions
def get_workflow_generation_prompt(
    workflow_type: WorkflowType = WorkflowType.GENERIC
) -> WorkflowGenerationPrompt:
    """Get a configured workflow generation prompt."""
    return WorkflowGenerationPrompt.create(workflow_type)


def format_workflow_prompt(
    description: str,
    workflow_type: WorkflowType = WorkflowType.GENERIC,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """Format a complete workflow generation prompt."""
    prompt = get_workflow_generation_prompt(workflow_type)
    return prompt.format(description, context)


def get_modification_prompt(
    current_workflow: Dict[str, Any],
    user_feedback: str,
    modification_type: str = "modify"
) -> Dict[str, str]:
    """Get a modification prompt."""
    if modification_type == "delete":
        return ModificationPrompt.delete(current_workflow, user_feedback)
    return ModificationPrompt.modify(current_workflow, user_feedback)


class ConversationPrompt:
    """Prompt for requirements gathering before workflow generation."""

    SYSTEM = """你是 Flowly 的 AI 工作流设计顾问。你的首要任务是通过自然对话理解用户真正想要的工作流，而不是立刻输出 JSON。

## 你的职责
1. **倾听与澄清**：当需求模糊时，用 1-3 个具体问题引导用户（触发方式、输入输出、是否需要 AI/分支/外部集成等）
2. **总结确认**：在信息较完整时，用简短条目复述理解，并询问是否可以开始生成
3. **专业建议**：基于场景推荐合适的节点类型（LLM、条件分支、HTTP、邮件、定时触发、MLOps 节点等）
4. **已有工作流**：若用户已有工作流草稿，结合上下文讨论优化方向，不要重复询问已知信息
5. **网站采集+排版+发邮件**：确认目标网站 URL、收件邮箱、是否 HTML 邮件
6. **手机网页+发邮件**：若用户要移动端 HTML 页面并发送邮件，确认页面主题、收件邮箱
7. **多模态/Agnes**：文生图/文生视频场景推荐使用 agnes-image / agnes-video 节点
8. **CUMCM/数学建模竞赛**：确认赛题、子问题数、数据附件、求解类型（LP/回归/时序/蒙特卡洛）、是否要图表与 Markdown 论文；就绪后生成完整多阶段流水线（非单 LLM 节点）

## 回复风格
- 使用中文，语气专业、简洁、友好
- 不要使用 markdown 代码块输出工作流 JSON
- 单次回复控制在 150-400 字，问题不超过 3 个
- 可在回复末尾用「您可以：」列出 2-4 个快捷回复建议（每行一条，以 - 开头）

## 何时认为可以生成
当已明确：业务目标、主要步骤（至少 2 步）、输入来源、期望输出，且用户未表示还有疑问时，在回复末尾单独一行输出：
[READY_TO_GENERATE]"""

    SYSTEM_FAST = """你是 Flowly 工作流顾问。尚未生成工作流时，用**简短**对话澄清需求（80-180 字，最多 2 个问题）。

- 不要输出 JSON 或代码块
- 信息足够时在末尾单独一行输出：[READY_TO_GENERATE]
- 网站采集+发邮件：确认目标 URL 与收件邮箱即可
- 手机网页+发邮件：确认主题与收件邮箱即可
- 多模态：确认文生图/文生视频与提示词来源
- CUMCM/数学建模：确认子问题数与数据即可，就绪后生成完整流水线"""

    SYSTEM_EDITOR = """你是 Flowly 画布排布助手。用户正在编辑器中调整**已有工作流**，你的职责是协助理解结构并给出可执行的排布/修改建议。

## 核心原则
1. **少说多做**：当用户要求添加、删除、连接、排布节点时，后端会自动执行并应用到画布；你只需用 1-2 句话说明做了什么或还需什么信息
2. **结合画布**：回复必须基于当前节点类型与连线结构，不要重复询问已知信息
3. **视频翻译分节点**：video_upload → subtitle_generation → 每种语言独立链路（subtitle_translate → segment_dubbing → lip_sync → subtitle_burn）→ output
4. **CUMCM 编辑器**：用户提到数学建模/CUMCM/国赛时，优先 enrich_cumcm 重建完整流水线（含求解/图表/论文节点）
5. **配置提醒**：指出未配置的必填项（如 SMTP、API Key、模型名），但不要输出完整 JSON

## 回复风格
- 中文，专业简洁，单次 80-220 字
- 不要输出 markdown 代码块或工作流 JSON
- 可在末尾用「您可以：」列出 2-4 条快捷操作建议（每行以 - 开头）
- 若用户描述已足够生成全新工作流，在末尾单独一行输出：[READY_TO_GENERATE]"""

    @classmethod
    def build_messages(
        cls,
        session_messages: List[Dict[str, str]],
        user_message: str,
        current_workflow: Optional[Dict[str, Any]] = None,
        mode: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build LLM messages for conversational requirements gathering."""
        from .constants import normalize_request_mode

        has_workflow = bool(current_workflow and current_workflow.get('nodes'))
        request_mode = normalize_request_mode(mode) or ('editor' if has_workflow else 'chat')

        if request_mode == 'editor' and has_workflow:
            system_content = cls.SYSTEM_EDITOR
        elif has_workflow:
            system_content = cls.SYSTEM
        else:
            system_content = cls.SYSTEM_FAST

        try:
            from nl_to_workflow.cumcm_enrichment import is_cumcm_intent
            from nl_to_workflow.cumcm_prompts import cumcm_conversation_hints

            combined_text = f'{user_message} ' + ' '.join(
                (m.get('content') or '') for m in session_messages if m.get('role') == 'user'
            )
            if is_cumcm_intent(combined_text):
                system_content += cumcm_conversation_hints()
        except Exception:
            pass

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

        if current_workflow and current_workflow.get('nodes'):
            nodes = current_workflow.get('nodes', [])
            edges = current_workflow.get('edges', [])
            wf_summary = json.dumps(
                {
                    'name': current_workflow.get('name'),
                    'description': current_workflow.get('description'),
                    'node_count': len(nodes),
                    'edge_count': len(edges),
                    'nodes': [
                        {
                            'id': n.get('id'),
                            'type': n.get('type'),
                            'name': n.get('name'),
                        }
                        for n in nodes[:40]
                    ],
                    'edges': [
                        {
                            'source': e.get('source'),
                            'target': e.get('target'),
                        }
                        for e in edges[:60]
                    ],
                },
                ensure_ascii=False,
            )
            messages.append({
                "role": "system",
                "content": f"当前画布工作流：{wf_summary}",
            })

        for msg in session_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role in ('user', 'assistant') and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    def strip_ready_marker(text: str) -> Tuple[str, bool]:
        """Remove [READY_TO_GENERATE] marker and return cleaned text + flag."""
        ready = '[READY_TO_GENERATE]' in text
        cleaned = text.replace('[READY_TO_GENERATE]', '').strip()
        return cleaned, ready
