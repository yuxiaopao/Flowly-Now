# -*- coding: utf-8 -*-
"""Tests for CUMCM centralized prompts."""

from django.test import SimpleTestCase

from nl_to_workflow.cumcm_prompts import (
    CUMCM_WORKFLOW_GENERATION_SYSTEM,
    PAPER_WRITING_RULES,
    get_decompose_system,
    get_paper_section_prompt,
    load_prompt_file,
)


class CumcmPromptsTests(SimpleTestCase):
    def test_load_academic_prompt_files(self):
        docx = load_prompt_file('docx_write_markdown.md')
        traps = load_prompt_file('academic_docx_traps.md')
        self.assertIn('Markdown', docx)
        self.assertIn('公式', traps)

    def test_paper_writing_rules_composed(self):
        self.assertIn('docx', PAPER_WRITING_RULES.lower() or 'Markdown')
        self.assertTrue(len(PAPER_WRITING_RULES) > 500)

    def test_decompose_system_count(self):
        sys_prompt = get_decompose_system(4)
        self.assertIn('4', sys_prompt)
        self.assertIn('solver_type', sys_prompt)

    def test_paper_section_includes_docx_rules(self):
        prompt = get_paper_section_prompt('模型建立', '写模型建立章节')
        self.assertIn('模型建立', prompt)
        self.assertIn('$$', prompt)

    def test_workflow_generation_system(self):
        self.assertIn('integer_programming', CUMCM_WORKFLOW_GENERATION_SYSTEM)
        self.assertIn('matplotlib', CUMCM_WORKFLOW_GENERATION_SYSTEM)
