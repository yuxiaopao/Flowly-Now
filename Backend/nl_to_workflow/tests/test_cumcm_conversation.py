# -*- coding: utf-8 -*-
"""Tests for CUMCM conversation prompt injection."""

from django.test import SimpleTestCase

from nl_to_workflow.prompts import ConversationPrompt


class CumcmConversationTests(SimpleTestCase):
    def test_cumcm_hints_injected_for_modeling_intent(self):
        msgs = ConversationPrompt.build_messages(
            [],
            '帮我搭建 CUMCM 全国大学生数学建模完整工作流',
        )
        system = msgs[0]['content']
        self.assertIn('CUMCM', system)
        self.assertIn('子问题数量', system)

    def test_no_cumcm_hints_for_unrelated_intent(self):
        msgs = ConversationPrompt.build_messages(
            [],
            '做一个客服问答机器人',
        )
        system = msgs[0]['content']
        self.assertNotIn('子问题数量', system)
