import pytest
import sys

sys.path.insert(0, 'e:/Flowly-now/Backend')


class TestWorkflowsAPI:

    def test_workflow_list_endpoint_exists(self):
        """GET /api/v1/workflows/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'list')

    def test_workflow_create_endpoint_exists(self):
        """POST /api/v1/workflows/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'create')

    def test_workflow_execute_endpoint_exists(self):
        """POST /api/v1/workflows/{id}/execute/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'execute')

    def test_workflow_validate_endpoint_exists(self):
        """POST /api/v1/workflows/{id}/validate/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'validate')

    def test_workflow_duplicate_endpoint_exists(self):
        """POST /api/v1/workflows/{id}/duplicate/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'duplicate')

    def test_workflow_export_endpoint_exists(self):
        """POST /api/v1/workflows/{id}/export/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'export')

    def test_workflow_import_endpoint_exists(self):
        """Import workflow endpoint exists"""
        from workflows.views import WorkflowImportView
        assert WorkflowImportView is not None

    def test_workflow_stream_execute_endpoint_exists(self):
        """POST /api/v1/workflows/{id}/stream_execute/ 端点存在"""
        from workflows.views import WorkflowViewSet
        assert hasattr(WorkflowViewSet, 'stream_execute')

    def test_workflow_nodes_crud(self):
        """节点 CRUD 端点"""
        from workflows.views import NodeViewSet
        assert hasattr(NodeViewSet, 'list')
        assert hasattr(NodeViewSet, 'create')
        assert hasattr(NodeViewSet, 'retrieve')
        assert hasattr(NodeViewSet, 'update')
        assert hasattr(NodeViewSet, 'destroy')

    def test_workflow_nodes_batch_create(self):
        """节点批量创建"""
        from workflows.views import NodeViewSet
        assert hasattr(NodeViewSet, 'batch_create')

    def test_workflow_nodes_batch_update_positions(self):
        """节点位置批量更新"""
        from workflows.views import NodeViewSet
        assert hasattr(NodeViewSet, 'batch_update_positions')

    def test_workflow_available_node_types(self):
        """可用节点类型列表"""
        from workflows.views import NodeViewSet
        assert hasattr(NodeViewSet, 'available_types')

    def test_workflow_edges_crud(self):
        """边 CRUD 端点"""
        from workflows.views import EdgeViewSet
        assert hasattr(EdgeViewSet, 'list')
        assert hasattr(EdgeViewSet, 'create')
        assert hasattr(EdgeViewSet, 'batch_create')

    def test_workflow_executions_crud(self):
        """执行 CRUD 端点"""
        from workflows.views import WorkflowExecutionViewSet
        assert hasattr(WorkflowExecutionViewSet, 'list')
        assert hasattr(WorkflowExecutionViewSet, 'retrieve')
        assert hasattr(WorkflowExecutionViewSet, 'cancel')
        assert hasattr(WorkflowExecutionViewSet, 'retry')
        assert hasattr(WorkflowExecutionViewSet, 'pause')
        assert hasattr(WorkflowExecutionViewSet, 'resume')
        assert hasattr(WorkflowExecutionViewSet, 'logs')
        assert hasattr(WorkflowExecutionViewSet, 'output')
        assert hasattr(WorkflowExecutionViewSet, 'status')

    def test_workflow_templates_crud(self):
        """模板 CRUD 端点"""
        from workflows.views import WorkflowTemplateViewSet
        assert hasattr(WorkflowTemplateViewSet, 'list')
        assert hasattr(WorkflowTemplateViewSet, 'retrieve')
        assert hasattr(WorkflowTemplateViewSet, 'create_from_template')

    def test_workflow_import_view_exists(self):
        """WorkflowImportView 存在"""
        from workflows.views import WorkflowImportView
        assert WorkflowImportView is not None

    def test_node_execution_viewset_exists(self):
        """NodeExecutionViewSet 存在"""
        from workflows.views import NodeExecutionViewSet
        assert NodeExecutionViewSet is not None

    def test_variable_viewset_exists(self):
        """VariableViewSet 存在"""
        from workflows.views import VariableViewSet
        assert VariableViewSet is not None

    def test_tool_viewset_exists(self):
        """ToolViewSet 存在"""
        from workflows.views import ToolViewSet
        assert ToolViewSet is not None

    def test_audit_log_viewset_exists(self):
        """AuditLogViewSet 存在"""
        from workflows.views import AuditLogViewSet
        assert AuditLogViewSet is not None


class TestAgentsAPI:

    def test_agent_list_endpoint_exists(self):
        """GET /api/v1/agents/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'list')

    def test_agent_chat_endpoint_exists(self):
        """POST /api/v1/agents/{id}/chat/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'chat')

    def test_agent_stream_chat_endpoint_exists(self):
        """POST /api/v1/agents/{id}/stream_chat/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'stream_chat')

    def test_agent_debug_endpoint_exists(self):
        """POST /api/v1/agents/{id}/debug/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'debug')

    def test_agent_tools_endpoint_exists(self):
        """GET /api/v1/agents/{id}/tools/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'tools')

    def test_agent_skills_endpoint_exists(self):
        """GET /api/v1/agents/{id}/skills/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'skills')

    def test_agent_update_skills_endpoint_exists(self):
        """PATCH /api/v1/agents/{id}/update_skills/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'update_skills')

    def test_agent_reset_memory_endpoint_exists(self):
        """POST /api/v1/agents/{id}/reset_memory/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'reset_memory')

    def test_agent_duplicate_endpoint_exists(self):
        """POST /api/v1/agents/{id}/duplicate/ 端点存在"""
        from agents.views import AgentViewSet
        assert hasattr(AgentViewSet, 'duplicate')

    def test_conversation_endpoints_exist(self):
        """对话端点"""
        from agents.views import AgentConversationViewSet
        assert hasattr(AgentConversationViewSet, 'list')
        assert hasattr(AgentConversationViewSet, 'retrieve')
        assert hasattr(AgentConversationViewSet, 'messages')
        assert hasattr(AgentConversationViewSet, 'add_message')

    def test_agent_tool_viewset_exists(self):
        """AgentToolViewSet 存在"""
        from agents.views import AgentToolViewSet
        assert AgentToolViewSet is not None

    def test_agent_execution_viewset_exists(self):
        """AgentExecutionViewSet 存在"""
        from agents.views import AgentExecutionViewSet
        assert AgentExecutionViewSet is not None


class TestNLWorkflowAPI:

    def test_nl_session_list_endpoint_exists(self):
        """GET /api/v1/nl-workflow/sessions/"""
        from nl_to_workflow.views import NLSessionViewSet
        assert NLSessionViewSet is not None

    def test_nl_session_create_endpoint_exists(self):
        """POST /api/v1/nl-workflow/sessions/"""
        from nl_to_workflow.views import NLSessionViewSet
        assert NLSessionViewSet is not None

    def test_nl_session_detail_endpoint_exists(self):
        """NLSessionDetailView 存在"""
        from nl_to_workflow.views import NLSessionDetailView
        assert NLSessionDetailView is not None

    def test_nl_session_message_endpoint_exists(self):
        """POST /api/v1/nl-workflow/sessions/{id}/message/"""
        from nl_to_workflow.views import NLSessionMessageView
        assert NLSessionMessageView is not None

    def test_nl_confirm_endpoint_exists(self):
        """POST /api/v1/nl-workflow/sessions/{id}/confirm/"""
        from nl_to_workflow.views import NLSessionConfirmView
        assert NLSessionConfirmView is not None

    def test_nl_preview_endpoint_exists(self):
        """POST /api/v1/nl-workflow/preview/"""
        from nl_to_workflow.views import NLWorkflowPreviewView
        assert NLWorkflowPreviewView is not None

    def test_nl_stream_endpoint_exists(self):
        """POST /api/v1/nl-workflow/stream/"""
        from nl_to_workflow.views import NLWorkflowStreamView
        assert NLWorkflowStreamView is not None

    def test_nl_analyze_intent_endpoint_exists(self):
        """POST /api/v1/nl-workflow/analyze-intent/"""
        from nl_to_workflow.views import NLWorkflowAnalyzeIntentView
        assert NLWorkflowAnalyzeIntentView is not None

    def test_nl_suggest_endpoint_exists(self):
        """POST /api/v1/nl-workflow/suggest/"""
        from nl_to_workflow.views import NLWorkflowSuggestView
        assert NLWorkflowSuggestView is not None

    def test_nl_models_endpoint_exists(self):
        """GET /api/v1/nl-workflow/models/"""
        from nl_to_workflow.views import NLModelListView
        assert NLModelListView is not None


class TestGatewayAPI:

    def test_gateway_providers_endpoint_exists(self):
        """GET /api/v1/gateway/providers/"""
        from gateway.views import ModelProviderViewSet
        assert hasattr(ModelProviderViewSet, 'list')

    def test_gateway_models_endpoint_exists(self):
        """GET /api/v1/gateway/models/"""
        from gateway.views import AIModelViewSet
        assert hasattr(AIModelViewSet, 'list')
        assert hasattr(AIModelViewSet, 'available')

    def test_gateway_health_endpoint_exists(self):
        """GET /api/v1/gateway/health/"""
        from gateway.views import GatewayHealthView
        assert GatewayHealthView is not None

    def test_gateway_api_keys_endpoint_exists(self):
        """GET/POST /api/v1/gateway/api-keys/"""
        from gateway.views import UserAPIKeyViewSet
        assert hasattr(UserAPIKeyViewSet, 'list')
        assert hasattr(UserAPIKeyViewSet, 'create')

    def test_gateway_chat_endpoint_exists(self):
        """POST /api/v1/gateway/chat/"""
        from gateway.views import GatewayChatView
        assert GatewayChatView is not None

    def test_gateway_embeddings_endpoint_exists(self):
        """POST /api/v1/gateway/embeddings/"""
        from gateway.views import GatewayEmbeddingsView
        assert GatewayEmbeddingsView is not None

    def test_gateway_api_call_log_viewset_exists(self):
        """APICallLogViewSet 存在"""
        from gateway.views import APICallLogViewSet
        assert APICallLogViewSet is not None


class TestPromptsAPI:

    def test_prompt_template_viewset_exists(self):
        """PromptTemplateViewSet 存在"""
        from prompts.views import PromptTemplateViewSet
        assert PromptTemplateViewSet is not None

    def test_prompt_category_viewset_exists(self):
        """PromptCategoryViewSet 存在"""
        from prompts.views import PromptCategoryViewSet
        assert PromptCategoryViewSet is not None

    def test_my_prompt_viewset_exists(self):
        """MyPromptViewSet 存在"""
        from prompts.views import MyPromptViewSet
        assert MyPromptViewSet is not None


class TestMonitoringAPI:

    def test_monitoring_logs_endpoint_exists(self):
        """GET /api/v1/monitoring/logs/"""
        from monitoring.views import ExecutionLogViewSet
        assert hasattr(ExecutionLogViewSet, 'list')

    def test_monitoring_alerts_endpoint_exists(self):
        """GET/POST /api/v1/monitoring/alerts/"""
        from monitoring.views import AlertViewSet
        assert hasattr(AlertViewSet, 'list')
        assert hasattr(AlertViewSet, 'acknowledge')
        assert hasattr(AlertViewSet, 'resolve')
        assert hasattr(AlertViewSet, 'summary')

    def test_monitoring_rules_endpoint_exists(self):
        """GET/POST /api/v1/monitoring/rules/"""
        from monitoring.views import AlertRuleViewSet
        assert hasattr(AlertRuleViewSet, 'list')

    def test_monitoring_metrics_endpoint_exists(self):
        """GET /api/v1/monitoring/metrics/"""
        from monitoring.views import MetricViewSet
        assert hasattr(MetricViewSet, 'list')
        assert hasattr(MetricViewSet, 'aggregate')
        assert hasattr(MetricViewSet, 'dashboard')

    def test_monitoring_channels_endpoint_exists(self):
        """GET/POST /api/v1/monitoring/channels/"""
        from monitoring.views import NotificationChannelViewSet
        assert hasattr(NotificationChannelViewSet, 'list')

    def test_monitoring_notifications_endpoint_exists(self):
        """GET /api/v1/monitoring/notifications/"""
        from monitoring.views import NotificationViewSet
        assert hasattr(NotificationViewSet, 'list')

    def test_analytics_viewset_exists(self):
        """AnalyticsViewSet 存在"""
        from monitoring.views import AnalyticsViewSet
        assert AnalyticsViewSet is not None


class TestUnifiedResponseTool:

    def test_responses_module_imports(self):
        """统一响应工具可导入"""
        import sys
        sys.path.insert(0, 'e:/Flowly-now/Backend')
        from utils.responses import success_response, created_response, error_response, paginated_response
        assert callable(success_response)
        assert callable(created_response)
        assert callable(error_response)
        assert callable(paginated_response)

    def test_unified_response_mixin_exists(self):
        """UnifiedResponseMixin 存在"""
        import sys
        sys.path.insert(0, 'e:/Flowly-now/Backend')
        from utils.responses import UnifiedResponseMixin
        assert UnifiedResponseMixin is not None
