"""
Prompt template service for rendering and management.
"""

import re
from typing import Dict, Any, List, Optional
from string import Template


class PromptTemplateService:
    """Service for handling prompt templates."""

    # Pattern to find template variables: {$var} or ${var}
    VARIABLE_PATTERN = re.compile(r'\$\{([^}]+)\}')

    @staticmethod
    def extract_variables(template: str) -> List[str]:
        """Extract all variables from a template string."""
        matches = PromptTemplateService.VARIABLE_PATTERN.findall(template)
        return list(set(matches))

    @staticmethod
    def render_string(template: str, context: Dict[str, Any]) -> str:
        """Render a template string with context.

        Supports:
        - ${variable} syntax
        - Default values: ${variable|default_value}
        """
        def replacer(match):
            var_expr = match.group(1)

            # Check for default value
            if '|' in var_expr:
                var_name, default_value = var_expr.split('|', 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                var_name = var_expr.strip()
                default_value = None

            # Get value from context
            value = context.get(var_name)

            if value is not None:
                return str(value)
            elif default_value is not None:
                return default_value
            else:
                return match.group(0)  # Return original if no value

        return PromptTemplateService.VARIABLE_PATTERN.sub(replacer, template)

    @staticmethod
    def validate_context(template: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that all required variables are present.

        Returns:
            Dict with 'valid', 'missing', and 'warnings' keys.
        """
        variables = PromptTemplateService.extract_variables(template)
        required_vars = [
            v.split('|')[0].strip()
            for v in variables
            if '|' not in v
        ]

        missing = [v for v in required_vars if v not in context]
        warnings = []

        # Check for unused variables
        unused = [k for k in context.keys() if k not in required_vars]
        if unused:
            warnings.append(f"未使用的变量: {', '.join(unused)}")

        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'warnings': warnings
        }

    @staticmethod
    def render_with_fallback(
        template: str,
        context: Dict[str, Any],
        fallback: Optional[Dict[str, str]] = None
    ) -> str:
        """Render template with fallback values for missing variables."""
        if fallback is None:
            fallback = {}

        # Build effective context with fallback
        effective_context = {**fallback, **context}

        return PromptTemplateService.render_string(template, effective_context)


class PromptBuilder:
    """Builder for constructing complex prompts."""

    def __init__(self, base_template: str = ''):
        self.template = base_template
        self.context: Dict[str, Any] = {}

    def add_section(self, title: str, content: str) -> 'PromptBuilder':
        """Add a titled section to the prompt."""
        section = f"\n## {title}\n{content}"
        self.template += section
        return self

    def add_instruction(self, instruction: str) -> 'PromptBuilder':
        """Add an instruction."""
        self.template += f"\n{instruction}"
        return self

    def add_variable(self, name: str, value: Any) -> 'PromptBuilder':
        """Add a variable to context."""
        self.context[name] = value
        return self

    def add_examples(self, examples: List[Dict[str, str]]) -> 'PromptBuilder':
        """Add few-shot examples.

        Args:
            examples: List of dicts with 'input' and 'output' keys
        """
        if not examples:
            return self

        example_section = "\n\n## 示例\n"
        for i, ex in enumerate(examples, 1):
            example_section += f"\n**示例 {i}:**\n"
            example_section += f"输入: {ex.get('input', '')}\n"
            example_section += f"输出: {ex.get('output', '')}\n"

        self.template += example_section
        return self

    def add_constraint(self, constraint: str) -> 'PromptBuilder':
        """Add a constraint/rule."""
        self.template += f"\n- {constraint}"
        return self

    def build(self) -> str:
        """Build and render the final prompt."""
        return PromptTemplateService.render_string(self.template, self.context)


class ChatPromptBuilder:
    """Builder for chat-style prompts."""

    def __init__(self, system_prompt: str = ''):
        self.messages = []

        if system_prompt:
            self.messages.append({
                'role': 'system',
                'content': system_prompt
            })

    def add_system(self, content: str) -> 'ChatPromptBuilder':
        """Add system message."""
        if self.messages and self.messages[0]['role'] == 'system':
            self.messages[0]['content'] += f"\n{content}"
        else:
            self.messages.insert(0, {
                'role': 'system',
                'content': content
            })
        return self

    def add_user(self, content: str) -> 'ChatPromptBuilder':
        """Add user message."""
        self.messages.append({
            'role': 'user',
            'content': content
        })
        return self

    def add_assistant(self, content: str) -> 'ChatPromptBuilder':
        """Add assistant message."""
        self.messages.append({
            'role': 'assistant',
            'content': content
        })
        return self

    def add_message(self, role: str, content: str) -> 'ChatPromptBuilder':
        """Add message with custom role."""
        if role not in ['system', 'user', 'assistant']:
            raise ValueError(f"Invalid role: {role}")

        self.messages.append({
            'role': role,
            'content': content
        })
        return self

    def build(self) -> List[Dict[str, str]]:
        """Build the final message list."""
        return self.messages

    def build_string(self) -> str:
        """Build as a single string (for non-chat models)."""
        return '\n\n'.join(
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in self.messages
        )


# Pre-built prompt templates
class PromptTemplates:
    """Collection of pre-built prompt templates."""

    SUMMARIZE = """请总结以下内容的要点：

${content}

请用简洁的语言概括主要内容，包括：
1. 核心主题
2. 关键信息
3. 重要结论"""

    TRANSLATE = """请将以下内容翻译成${target_language|英文}：

${content}"""

    EXPLAIN_CODE = """请解释以下代码的功能：

```{language|python}
${code}
```

请提供：
1. 代码整体功能概述
2. 关键部分的解释
3. 输入输出说明"""

    ANALYZE_SENTIMENT = """分析以下文本的情感倾向：

${text}

请判断：
1. 情感类型（正面/负面/中性）
2. 情感强度（1-10）
3. 简要说明"""

    GENERATE_QUESTIONS = """基于以下内容，生成${count|5}个问题：

${content}

请生成多样化的问题类型：
- 事实性问题
- 理解性问题
- 分析性问题"""

    WRITING_ASSISTANT = """你是一个专业的写作助手。请帮助改进以下文本：

原文：
${text}

请提供：
1. 改进建议
2. 改进后的版本
3. 修改说明"""
