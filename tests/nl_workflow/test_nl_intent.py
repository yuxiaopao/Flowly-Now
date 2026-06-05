# -*- coding: utf-8 -*-
"""
Tests for NL Intent Detection with subtypes and retry detection.

Tests the following functions from services.py:
- analyze_intent() - Main intent detection function
- detect_workflow_subtype() - Subtype detection
- is_retry_intent() - Retry detection
"""

import pytest
from nl_to_workflow.services import (
    analyze_intent,
    detect_workflow_subtype,
    is_retry_intent,
    NLToWorkflowService,
)


class TestIntentDetection:
    """Test enhanced intent detection with subtypes."""

    def test_create_intent_chinese(self):
        """Test create intent detection with Chinese keywords."""
        result = analyze_intent('创建一个问答机器人')
        assert result['intent'] == 'create'

    def test_create_intent_english(self):
        """Test create intent detection with English keywords."""
        result = analyze_intent('create a workflow')
        assert result['intent'] == 'create'
        
        result = analyze_intent('generate a new workflow')
        assert result['intent'] == 'create'
        
        result = analyze_intent('帮我做一个工作流')
        assert result['intent'] == 'create'

    def test_modify_intent(self):
        """Test modify intent detection."""
        result = analyze_intent('把LLM节点改成gpt-4')
        assert result['intent'] == 'modify'
        
        result = analyze_intent('添加一个邮件节点')
        assert result['intent'] == 'modify'
        
        result = analyze_intent('修改工作流配置')
        assert result['intent'] == 'modify'

    def test_delete_intent(self):
        """Test delete intent detection."""
        result = analyze_intent('删除第二个节点')
        assert result['intent'] == 'delete'
        
        result = analyze_intent('移除这个步骤')
        assert result['intent'] == 'delete'
        
        result = analyze_intent('不要这个节点')
        assert result['intent'] == 'delete'

    def test_chat_intent(self):
        """Test chat intent detection for general conversation."""
        result = analyze_intent('你好，这个工具怎么用')
        assert result['intent'] == 'chat'
        
        result = analyze_intent('What is this app about?')
        assert result['intent'] == 'chat'

    def test_subtype_qa_bot(self):
        """Test qa_bot subtype detection."""
        result = analyze_intent('创建一个问答机器人')
        assert result['subtype'] == 'qa_bot'
        
        result = analyze_intent('做一个客服系统')
        assert result['subtype'] == 'qa_bot'
        
        result = analyze_intent('create a Q&A bot')
        assert result['subtype'] == 'qa_bot'

    def test_subtype_data_processing(self):
        """Test data_processing subtype detection."""
        result = analyze_intent('创建一个数据处理工作流')
        assert result['subtype'] == 'data_processing'
        
        result = analyze_intent('处理CSV文件')
        assert result['subtype'] == 'data_processing'
        
        result = analyze_intent('清洗数据')
        assert result['subtype'] == 'data_processing'

    def test_subtype_translation(self):
        """Test translation subtype detection."""
        result = analyze_intent('创建一个翻译工作流')
        assert result['subtype'] == 'translation'
        
        result = analyze_intent('翻译成英文')
        assert result['subtype'] == 'translation'

    def test_subtype_moderation(self):
        """Test moderation subtype detection."""
        result = analyze_intent('创建一个内容审核工作流')
        assert result['subtype'] == 'moderation'
        
        result = analyze_intent('过滤敏感内容')
        assert result['subtype'] == 'moderation'

    def test_subtype_article_generation(self):
        """Test article_generation subtype detection."""
        result = analyze_intent('创建一个文章生成工作流')
        assert result['subtype'] == 'article_generation'
        
        result = analyze_intent('自动写文章')
        assert result['subtype'] == 'article_generation'

    def test_subtype_customer_service(self):
        """Test customer_service subtype detection."""
        result = analyze_intent('创建一个客服工作流')
        assert result['subtype'] == 'customer_service'

    def test_subtype_generic(self):
        """Test generic subtype when no specific type detected."""
        result = analyze_intent('创建一个简单的工作流')
        assert result['subtype'] == 'generic'
        
        result = analyze_intent('do something cool')
        assert result['subtype'] == 'generic'

    def test_retry_detection(self):
        """Test is_retry detection."""
        result = analyze_intent('重新生成工作流')
        assert result['is_retry'] is True
        
        result = analyze_intent('retry the workflow')
        assert result['is_retry'] is True
        
        result = analyze_intent('再试一次')
        assert result['is_retry'] is True

    def test_retry_detection_false(self):
        """Test is_retry returns False for non-retry messages."""
        result = analyze_intent('创建一个问答机器人')
        assert result['is_retry'] is False
        
        result = analyze_intent('修改这个节点')
        assert result['is_retry'] is False

    def test_retry_combined_with_intent(self):
        """Test retry detection combined with other intents."""
        result = analyze_intent('重新生成这个工作流')
        assert result['intent'] == 'create'
        assert result['is_retry'] is True

    def test_detect_workflow_subtype_direct(self):
        """Test detect_workflow_subtype function directly."""
        assert detect_workflow_subtype('问答机器人') == 'qa_bot'
        assert detect_workflow_subtype('数据处理') == 'data_processing'
        assert detect_workflow_subtype('翻译') == 'translation'
        assert detect_workflow_subtype('内容审核') == 'moderation'
        assert detect_workflow_subtype('文章生成') == 'article_generation'
        assert detect_workflow_subtype('客服') == 'customer_service'
        assert detect_workflow_subtype('一般工作流') == 'generic'

    def test_is_retry_intent_direct(self):
        """Test is_retry_intent function directly."""
        assert is_retry_intent('重试一下') is True
        assert is_retry_intent('retry') is True
        assert is_retry_intent('重新生成') is True
        assert is_retry_intent('再试') is True
        
        assert is_retry_intent('创建工作流') is False
        assert is_retry_intent('修改') is False

    def test_intent_order_delete_first(self):
        """Test that delete intent is detected before modify."""
        # Even though '修改' is in this message, '删除' should be detected first
        result = analyze_intent('删除并修改节点')
        assert result['intent'] == 'delete'

    def test_intent_order_modify_second(self):
        """Test that modify intent is detected before create."""
        # Even though '创建' is in this message, '修改' should be detected first
        result = analyze_intent('修改并创建节点')
        assert result['intent'] == 'modify'


class TestNLServiceIntent:
    """Test NLToWorkflowService intent analysis methods."""

    def test_service_analyze_intent(self):
        """Test service's _analyze_intent method."""
        service = NLToWorkflowService()
        assert service._analyze_intent('创建一个工作流') == 'create'
        assert service._analyze_intent('修改这个工作流') == 'modify'
        assert service._analyze_intent('删除这个节点') == 'delete'
        assert service._analyze_intent('你好') == 'chat'

    def test_service_get_intent_details(self):
        """Test service's _get_intent_details method."""
        service = NLToWorkflowService()
        
        result = service._get_intent_details('把LLM节点改成gpt-4')
        assert 'targets' in result
        assert 'intent' in result

    def test_intent_analysis_consistency(self):
        """Test that standalone and service methods return consistent results."""
        service = NLToWorkflowService()
        test_messages = [
            '创建一个问答机器人',
            '修改工作流配置',
            '删除这个节点',
            '你好',
        ]
        
        for msg in test_messages:
            standalone_result = analyze_intent(msg)
            service_result = {'intent': service._analyze_intent(msg)}
            assert standalone_result['intent'] == service_result['intent']
