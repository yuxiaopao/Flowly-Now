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
def test_dialogue_matrix_script_exit_zero():
    """Ensure the matrix runner passes (invoked as subprocess-free in-process check)."""
    import scripts.nl2wf_dialogue_e2e as runner

    report = runner.MatrixReport()
    runner.run_intent_subtype_cases(report)
    runner.run_generation_cases(report)
    runner.run_dialogue_flows(report)
    runner.run_utility_cases(report)
    runner.run_mock_routing_cases(report)
    failures = [r for r in report.results if not r.passed]
    assert not failures, failures[:5]
