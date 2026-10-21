"""Tests for n8n Soft RAG training corpus used by 语创."""

from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from nl_to_workflow.n8n_corpus import (
    N8nCorpusEntry,
    _clean_workflow_name,
    compute_quality_score,
    format_corpus_reference,
    save_corpus,
    search_n8n_corpus,
)


def _entry(**kwargs) -> N8nCorpusEntry:
    base = dict(
        id='11111111-1111-1111-1111-111111111111',
        name='[n8n] Gmail to Slack alert',
        clean_name='Gmail to Slack alert',
        description='Forward important Gmail messages to Slack',
        category='gmail',
        tags=['n8n-import'],
        node_types=['start', 'email', 'slack', 'end'],
        node_type_sequence='start -> email -> slack -> end',
        node_count=4,
        edge_count=3,
        search_text='gmail to slack alert forward important gmail messages email slack',
        structure_summary='Gmail to Slack alert | flow: start -> email -> slack -> end',
        quality_score=0.8,
        source='n8n-import',
        n8n_source_path='/external/n8n-workflows/workflows/Gmail/demo.json',
        compact_example={
            'name': 'Gmail to Slack alert',
            'nodes': [
                {'type': 'email', 'name': 'Gmail'},
                {'type': 'slack', 'name': 'Slack'},
            ],
            'edges': [{'source_type': 'email', 'target_type': 'slack'}],
        },
    )
    base.update(kwargs)
    return N8nCorpusEntry(**base)


class N8nCorpusUnitTests(SimpleTestCase):
    def test_clean_name_strips_prefix_and_stem(self):
        self.assertEqual(
            _clean_workflow_name('[n8n] Sync Sheets (0057_Activecampaign_Create_Triggered)'),
            'Sync Sheets',
        )

    def test_quality_score_prefers_rich_graphs(self):
        rich = compute_quality_score(
            node_types=['start', 'http_request', 'filter', 'email', 'end'],
            edge_count=4,
            unmapped_nodes=0,
        )
        thin = compute_quality_score(
            node_types=['start', 'variable', 'end'],
            edge_count=1,
            unmapped_nodes=2,
        )
        self.assertGreater(rich, thin)

    def test_search_and_reference_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'corpus.json'
            save_corpus([
                _entry(),
                _entry(
                    id='22222222-2222-2222-2222-222222222222',
                    name='[n8n] HTTP webhook form',
                    clean_name='HTTP webhook form',
                    category='webhook',
                    description='Receive webhook and store to sheets',
                    node_types=['start', 'webhook', 'google_sheets', 'end'],
                    node_type_sequence='start -> webhook -> google_sheets -> end',
                    search_text='http webhook form receive webhook google sheets',
                    quality_score=0.75,
                ),
            ], path)

            hits = search_n8n_corpus('gmail slack notification', limit=3, path=path)
            self.assertGreaterEqual(len(hits), 1)
            self.assertIn('slack', hits[0][0].clean_name.lower())

            with override_settings(NL_WORKFLOW_USE_N8N_CORPUS=True, NL_WORKFLOW_N8N_CORPUS_LIMIT=2):
                text = format_corpus_reference('gmail slack', limit=2, path=path)
                self.assertIn('n8n 开源工作流训练语料', text)
                self.assertIn('拓扑:', text)

    def test_corpus_disabled(self):
        with override_settings(NL_WORKFLOW_USE_N8N_CORPUS=False):
            self.assertEqual(format_corpus_reference('anything'), '')
