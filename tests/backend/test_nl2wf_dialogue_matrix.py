# -*- coding: utf-8 -*-
"""Pytest wrapper for NL2WF dialogue matrix (offline)."""

import pytest
from django.test import override_settings

from nl_to_workflow.bulk_subtype_generator import generate_bulk_subtype_samples
from nl_to_workflow.dialogue_fixtures import (
    BULK_SUBTYPE_SAMPLES,
    INTENT_SUBTYPE_CASES,
)
from nl_to_workflow.services import analyze_intent, detect_workflow_subtype


_BULK_EXTENDED = generate_bulk_subtype_samples(start_id=100, count=100)


@pytest.mark.parametrize(
    "case",
    INTENT_SUBTYPE_CASES + BULK_SUBTYPE_SAMPLES + _BULK_EXTENDED,
    ids=lambda c: c["id"],
)
def test_intent_subtype_matrix(case):
    msg = case["message"]
    if "subtype" in case:
        assert detect_workflow_subtype(msg) == case["subtype"], msg
    if "intent" in case:
        assert analyze_intent(msg).get("intent") == case["intent"], msg


@pytest.mark.django_db
@override_settings(DEBUG=True, NL_WORKFLOW_USE_MOCK=True)
def test_offline_dialogue_rules_and_template_routing():
    """离线规则及显式模板生成；不将模板冒充真实模型生成。"""
    import scripts.nl2wf_dialogue_e2e as runner

    report = runner.MatrixReport()
    runner.run_intent_subtype_cases(report)
    runner.run_utility_cases(report)
    runner.run_mock_routing_cases(report)
    failures = [r for r in report.results if not r.passed]
    assert not failures, failures[:5]


@pytest.mark.django_db
@pytest.mark.parametrize('case', __import__('nl_to_workflow.dialogue_fixtures', fromlist=['GENERATION_CASES']).GENERATION_CASES, ids=lambda case: case['id'])
def test_generation_without_provider_is_labelled_or_reports_failure(case):
    from unittest.mock import patch
    from nl_to_workflow.services import NLToWorkflowService
    service = NLToWorkflowService(model='__offline_test__')
    with patch.object(service, '_resolve_model', return_value=None):
        result = service.generate_workflow(case['description'])
    if result.get('nodes'):
        assert result.get('_generation_mode') == 'offline_template'
        assert result.get('_intelligence_note')
        node_types = {node['type'] for node in result['nodes']}
        assert set(case.get('must_have_types', [])) <= node_types
        assert not set(case.get('must_not_have_types', [])) & node_types
    else:
        assert result.get('error')
