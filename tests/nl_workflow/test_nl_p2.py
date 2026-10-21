# -*- coding: utf-8 -*-
"""Tests for NL intelligence P2: agent context, memory, async task wiring."""

from unittest.mock import MagicMock, patch

import pytest

from nl_to_workflow.agent_context import gather_generation_context, validate_generated_workflow_payload
from nl_to_workflow.conversation_memory import (
    compress_messages_for_generation,
    should_summarize,
    summarize_messages,
)
from nl_to_workflow.services import NLToWorkflowService


class TestConversationMemory:
    def test_should_summarize_respects_threshold(self, settings):
        settings.NL_CHAT_SUMMARY_THRESHOLD = 5
        assert should_summarize([{'role': 'user', 'content': 'x'}] * 4) is False
        assert should_summarize([{'role': 'user', 'content': 'x'}] * 5) is True

    def test_summarize_heuristic_without_llm(self, settings):
        settings.NL_CHAT_USE_SUMMARY = True
        messages = [
            {'role': 'user', 'content': '我想做一个翻译工作流'},
            {'role': 'assistant', 'content': '目标语言是？'},
            {'role': 'user', 'content': '英文和日文'},
        ]
        summary = summarize_messages(messages, call_llm=None)
        assert '翻译' in summary or '初始需求' in summary

    def test_compress_includes_summary_and_recent(self, settings):
        settings.NL_CHAT_SUMMARY_THRESHOLD = 2
        settings.NL_CHAT_USE_SUMMARY = True
        messages = [
            {'role': 'user', 'content': '需求A'},
            {'role': 'assistant', 'content': '追问'},
            {'role': 'user', 'content': '补充B'},
        ]
        description, summary = compress_messages_for_generation(
            messages, '生成工作流', call_llm=None, existing_summary=''
        )
        assert '【当前用户】' in description
        assert '生成工作流' in description
        assert summary


class TestAgentContext:
    def test_gather_disabled(self, settings):
        settings.NL_WORKFLOW_USE_AGENT_CONTEXT = False
        result = gather_generation_context('做一个问答机器人')
        assert result['source'] == 'disabled'
        assert result['text'] == ''

    def test_gather_enabled_best_effort(self, settings):
        settings.NL_WORKFLOW_USE_AGENT_CONTEXT = True
        with patch('nl_to_workflow.agent_context._safe_tool_call', return_value='[]'):
            result = gather_generation_context('做一个问答机器人', user_id=1)
        assert result['source'] == 'agent_tools'

    def test_validate_payload(self):
        wf = {
            'nodes': [
                {'id': 's', 'type': 'start'},
                {'id': 'e', 'type': 'end'},
            ],
            'edges': [{'source': 's', 'target': 'e'}],
        }
        with patch(
            'nl_to_workflow.agent_context._safe_tool_call',
            return_value='{"valid": true, "errors": [], "warnings": []}',
        ):
            result = validate_generated_workflow_payload(wf)
        assert result['valid'] is True


class TestGenerateUsesAgentContext:
    def test_enrich_merges_agent_text(self, settings, monkeypatch):
        settings.NL_WORKFLOW_USE_AGENT_CONTEXT = True
        svc = NLToWorkflowService(model='agnes-2.0-flash')
        monkeypatch.setattr(
            'nl_to_workflow.services.gather_generation_context',
            lambda *a, **k: {'text': '【Agent】参考模板X', 'source': 'agent_tools'},
        )
        ctx = svc._enrich_context_with_agent_tools('测试', {}, user_id=1)
        assert '参考模板X' in ctx.get('reference_context', '')
        assert ctx.get('agent_context_text')

    def test_build_description_returns_tuple(self, settings, monkeypatch):
        settings.NL_CHAT_USE_SUMMARY = True
        settings.NL_CHAT_SUMMARY_THRESHOLD = 100
        svc = NLToWorkflowService(model='agnes-2.0-flash')
        desc, summary = svc._build_generation_description_from_messages(
            [{'role': 'user', 'content': '做个翻译'}, {'role': 'assistant', 'content': '好'}],
            '生成工作流',
        )
        assert isinstance(desc, str)
        assert '生成工作流' in desc or '翻译' in desc
        assert isinstance(summary, str)


class TestAsyncTaskHelpers:
    def test_generate_workflow_async_task_imports(self):
        from nl_to_workflow.tasks import generate_workflow_async, continue_conversation_async
        assert generate_workflow_async.name.endswith('generate_workflow_async')
        assert continue_conversation_async.name.endswith('continue_conversation_async')

    def test_agent_builder_uses_local_prompt(self):
        from nl_to_workflow.agent import WorkflowAgentBuilder, _LOCAL_REACT_PROMPT
        assert 'Final Answer' in _LOCAL_REACT_PROMPT.template
        llm = MagicMock()
        builder = WorkflowAgentBuilder(llm=llm, max_iterations=1, verbose=False)
        with patch('nl_to_workflow.agent.create_react_agent') as create_agent, \
             patch('nl_to_workflow.agent.AgentExecutor') as executor_cls:
            create_agent.return_value = MagicMock()
            executor_cls.from_agent_and_tools.return_value = MagicMock()
            builder.build()
            prompt_arg = create_agent.call_args.kwargs.get('prompt') or create_agent.call_args[1].get('prompt')
            if prompt_arg is None:
                # positional
                prompt_arg = create_agent.call_args[0][2] if len(create_agent.call_args[0]) > 2 else create_agent.call_args.kwargs['prompt']
            assert prompt_arg is _LOCAL_REACT_PROMPT
