"""
Centralized Prompt Management for NL to Workflow.

This module provides versioned, reusable prompt templates with:
- Structured format instructions for LLM output
- Few-shot examples for different workflow types
- Context-aware prompts with dynamic placeholders
"""

from typing import Dict, Any, Optional, List, Literal
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
}"""

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
3. 使用 {{variable}} 语法引用变量
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
                        {"id": "node_3", "type": "llm", "name": "AI回答", "position": {"x": 460, "y": 100}, "config": {"model": "llama3", "prompt": "你是一个专业的AI助手，请简洁准确地回答用户的问题：{{input.user_question}}", "temperature": 0.7}},
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
                        {"id": "node_3", "type": "llm", "name": "情感分析", "position": {"x": 460, "y": 150}, "config": {"model": "llama3", "prompt": "分析以下评论的情感倾向，返回 positive 或 negative：{{input.comment}}", "temperature": 0.3}},
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
                few_shot_lines.append(f"输入：{example['input']}")
                few_shot_lines.append(f"输出：{example['output']}")
            few_shot_section = '\n'.join(few_shot_lines)

        # Format user message
        user_message = self.user_template.format(
            description=description,
            node_types=self._node_types_description(),
            format_instructions=self.format_instructions,
            context=json.dumps(context, ensure_ascii=False) if context else ""
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
1. 最小修改：只修改必要的部分
2. 保持一致：确保修改后工作流仍然有效
3. 明确意图：准确理解用户想要什么改变
4. 保持ID：如果节点ID没变化，保持不变""",
            "user": f"""## 当前工作流
```json
{json.dumps(current_workflow, ensure_ascii=False, indent=2)}
```

## 用户反馈
{user_feedback}

## 要求
根据用户反馈修改工作流。只输出修改后的完整JSON，不要有其他内容。"""
        }

    @staticmethod
    def delete(
        current_workflow: Dict[str, Any],
        user_feedback: str
    ) -> Dict[str, str]:
        """Generate prompt for deleting from workflow."""
        return {
            "system": """你是一个工作流修改专家。理解用户的删除意图，精确删除指定节点或连线。""",
            "user": f"""## 当前工作流
```json
{json.dumps(current_workflow, ensure_ascii=False, indent=2)}
```

## 用户要求删除
{user_feedback}

## 要求
删除指定的节点及其连线。只输出修改后的完整JSON。"""
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
