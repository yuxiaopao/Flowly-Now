# -*- coding: utf-8 -*-
"""Tests for NL intelligence layer (AI-first generate / refine)."""

import copy

import pytest

from nl_to_workflow.intelligence import (
    extract_json_object,
    mark_llm_workflow,
    mark_offline_template,
    optimize_workflow_structure,
    validation_error_text,
)
from nl_to_workflow.services import NLToWorkflowService, analyze_intent


class TestIntelligenceHelpers:
    def test_extract_json_object_from_fence(self):
        raw = '```json\n{"intent":"optimize","confidence":0.9}\n```'
        parsed = extract_json_object(raw)
        assert parsed['intent'] == 'optimize'

    def test_mark_offline_template(self):
        wf = {'name': 't', 'nodes': [], 'edges': []}
        stamped = mark_offline_template(wf, 'offline')
        assert stamped['_generation_mode'] == 'offline_template'
        assert stamped['_is_intelligent'] is False
        assert 'offline' in stamped['_intelligence_note']

    def test_mark_llm_workflow(self):
        wf = mark_llm_workflow({'name': 'x', 'nodes': [{'id': '1'}]}, model='agnes-2.0-flash')
        assert wf['_is_intelligent'] is True
        assert wf['_generation_mode'] == 'llm'
        assert wf['_llm_model'] == 'agnes-2.0-flash'

    def test_optimize_removes_dangling_edges(self):
        wf = {
            'name': 'demo',
            'nodes': [
                {'id': 'a', 'type': 'start', 'name': '开始', 'position': {'x': 0, 'y': 0}, 'config': {}},
                {'id': 'b', 'type': 'end', 'name': '结束', 'position': {'x': 100, 'y': 0}, 'config': {}},
            ],
            'edges': [
                {'id': 'e1', 'source': 'a', 'target': 'b'},
                {'id': 'e2', 'source': 'a', 'target': 'missing'},
            ],
        }
        optimized, changes = optimize_workflow_structure(wf)
        targets = {e['target'] for e in optimized['edges']}
        assert 'missing' not in targets
        assert any('无效连线' in c for c in changes)

    def test_validation_error_text(self):
        assert validation_error_text({'validation': {'errors': ['缺节点']}}) == '缺节点'
        assert validation_error_text({'error': 'boom'}) == 'boom'


class TestKeywordIntentStillWorks:
    """Regression: keyword analyzer remains available for offline / tests."""

    def test_create_intent(self):
        assert analyze_intent('创建一个问答机器人')['intent'] == 'create'

    def test_modify_intent(self):
        assert analyze_intent('把LLM节点改成gpt-4')['intent'] == 'modify'


class TestGenerateNoSilentTemplate:
    def test_llm_failure_does_not_swap_video_template(self, monkeypatch, settings):
        settings.NL_WORKFLOW_TEMPLATE_FALLBACK = False
        settings.NL_WORKFLOW_USE_TEMPLATES = False
        svc = NLToWorkflowService(model='agnes-2.0-flash')
        monkeypatch.setattr(svc, '_prefer_llm_over_template', lambda: True)
        monkeypatch.setattr(svc, '_allow_offline_template', lambda: False)
        monkeypatch.setattr(
            svc,
            '_call_llm',
            lambda messages, mock_description=None: {'error': 'provider down'},
        )

        result = svc.generate_workflow('做个视频翻译工作流，翻译成英语日语韩语')
        assert result.get('error')
        assert not result.get('nodes')
        assert result.get('_generation_mode') == 'llm_failed'
        assert result.get('_is_intelligent') is False


class TestOptimizeIntentPath:
    def test_handle_optimize_intent_runs_structure_pass(self, monkeypatch):
        svc = NLToWorkflowService()
        monkeypatch.setattr(NLToWorkflowService, 'llm', property(lambda self: None))
        monkeypatch.setattr(svc, '_generate_suggestions', lambda workflow: ['ok'])
        monkeypatch.setattr(svc, '_validate_workflow', lambda workflow: workflow)
        wf = {
            'name': 'demo',
            'nodes': [
                {'id': 'a', 'type': 'start', 'name': '开始', 'position': {'x': 0, 'y': 0}, 'config': {}},
                {
                    'id': 'b',
                    'type': 'subtitle_generation',
                    'name': 'ASR',
                    'position': {'x': 0, 'y': 0},
                    'config': {},
                },
                {'id': 'c', 'type': 'end', 'name': '结束', 'position': {'x': 0, 'y': 0}, 'config': {}},
            ],
            'edges': [
                {'id': 'e1', 'source': 'a', 'target': 'b'},
                {'id': 'e2', 'source': 'b', 'target': 'c'},
                {'id': 'bad', 'source': 'b', 'target': 'ghost'},
            ],
        }
        result = svc._handle_optimize_intent(copy.deepcopy(wf), '/optimize')
        assert result['intent'] == 'optimize'
        assert result['workflow']
        assert all(e['target'] != 'ghost' for e in result['workflow']['edges'])
        assert result['workflow'].get('_optimized') is True
