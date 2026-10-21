"""
URL patterns for workflows app.
"""

from django.urls import path
from .views import (
    WorkflowViewSet, NodeViewSet, EdgeViewSet,
    WorkflowExecutionViewSet, PublicWorkflowTemplateViewSet, WorkflowTemplateViewSet,
    WorkflowImportView,
    NodeExecutionViewSet, VariableViewSet, ToolViewSet,
    APICredentialViewSet, AuditLogViewSet,
    TemplateCategoryViewSet,
    ExecutionCacheViewSet, ExecutionCacheConfigViewSet,
    CheckEnvView, WorkflowOptimizeView, EmailSmtpDefaultsView, MediaUploadView
)
from .trigger_views import WorkflowTriggerViewSet, WorkflowTriggerCreateView, CronPreviewView

urlpatterns = [
    # === 媒体上传（视频翻译等） ===
    path('media/upload/', MediaUploadView.as_view(), name='media-upload'),

    # === 触发器路由 ===
    path('workflows/triggers/cron-preview/', CronPreviewView.as_view(), name='trigger-cron-preview'),
    path('workflows/triggers/', WorkflowTriggerViewSet.as_view({
        'get': 'list',
    }), name='trigger-list'),
    path('workflows/triggers/<int:pk>/', WorkflowTriggerViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='trigger-detail'),
    path('workflows/triggers/<int:pk>/executions/', WorkflowTriggerViewSet.as_view({
        'get': 'executions',
    }), name='trigger-executions'),
    path('workflows/triggers/<int:pk>/test/', WorkflowTriggerViewSet.as_view({
        'post': 'test_trigger',
    }), name='trigger-test'),
    path('workflows/triggers/<int:pk>/webhook/', WorkflowTriggerViewSet.as_view({
        'post': 'webhook',
    }), name='trigger-webhook'),
    path('workflows/<uuid:workflow_pk>/triggers/', WorkflowTriggerCreateView.as_view(), name='workflow-trigger-create'),

    # === 必须在 workflows/ 之前定义的路由 ===
    
    # 节点路由
    path('workflows/nodes/', NodeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='node-list'),
    path('workflows/nodes/available_types/', NodeViewSet.as_view({
        'get': 'available_types'
    }), name='node-available-types'),
    path('workflows/nodes/batch_create/', NodeViewSet.as_view({
        'post': 'batch_create'
    }), name='node-batch-create'),
    path('workflows/nodes/batch_update_positions/', NodeViewSet.as_view({
        'post': 'batch_update_positions'
    }), name='node-batch-update-positions'),
    path('workflows/nodes/<uuid:pk>/', NodeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='node-detail'),
    
    # 连线路由
    path('workflows/edges/', EdgeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='edge-list'),
    path('workflows/edges/batch_create/', EdgeViewSet.as_view({
        'post': 'batch_create'
    }), name='edge-batch-create'),
    path('workflows/edges/<uuid:pk>/', EdgeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='edge-detail'),
    
    # 执行历史路由
    path('workflows/executions/', WorkflowExecutionViewSet.as_view({
        'get': 'list'
    }), name='execution-list'),
    path('workflows/executions/<uuid:pk>/', WorkflowExecutionViewSet.as_view({
        'get': 'retrieve',
        'delete': 'delete'
    }), name='execution-detail'),
    path('workflows/executions/<uuid:pk>/cancel/', WorkflowExecutionViewSet.as_view({
        'post': 'cancel'
    }), name='execution-cancel'),
    path('workflows/executions/<uuid:pk>/retry/', WorkflowExecutionViewSet.as_view({
        'post': 'retry'
    }), name='execution-retry'),
    path('workflows/executions/<uuid:pk>/retry_failed/', WorkflowExecutionViewSet.as_view({
        'post': 'retry_failed'
    }), name='execution-retry-failed'),
    path('workflows/executions/<uuid:pk>/continue/', WorkflowExecutionViewSet.as_view({
        'get': 'continue_execution',
        'post': 'continue_execution'
    }), name='execution-continue'),
    path('workflows/executions/<uuid:pk>/pause/', WorkflowExecutionViewSet.as_view({
        'post': 'pause'
    }), name='execution-pause'),
    path('workflows/executions/<uuid:pk>/resume/', WorkflowExecutionViewSet.as_view({
        'post': 'resume'
    }), name='execution-resume'),
    path('workflows/executions/<uuid:pk>/timeline/', WorkflowExecutionViewSet.as_view({
        'get': 'timeline'
    }), name='execution-timeline'),
    path('workflows/executions/<uuid:pk>/status/', WorkflowExecutionViewSet.as_view({
        'get': 'status'
    }), name='execution-status'),
    path('workflows/executions/<uuid:pk>/output/', WorkflowExecutionViewSet.as_view({
        'get': 'output'
    }), name='execution-output'),
    path('workflows/executions/<uuid:pk>/logs/', WorkflowExecutionViewSet.as_view({
        'get': 'logs'
    }), name='execution-logs'),
    path('workflows/executions/statistics/', WorkflowExecutionViewSet.as_view({
        'get': 'statistics'
    }), name='execution-statistics'),
    path('workflows/executions/analytics/', WorkflowExecutionViewSet.as_view({
        'get': 'analytics'
    }), name='execution-analytics'),

    # 模板路由 (legacy — public workflows as templates)
    path('workflows/templates/', PublicWorkflowTemplateViewSet.as_view({
        'get': 'list'
    }), name='template-list'),
    path('workflows/templates/<int:pk>/', PublicWorkflowTemplateViewSet.as_view({
        'get': 'retrieve'
    }), name='template-detail'),
    path('workflows/templates/<int:pk>/create_from_template/', PublicWorkflowTemplateViewSet.as_view({
        'post': 'create_from_template'
    }), name='template-create-from'),
    
    # === 新增的路由 ===
    
    # 节点执行记录路由
    path('node-executions/', NodeExecutionViewSet.as_view({
        'get': 'list'
    }), name='node-execution-list'),
    path('node-executions/statistics/', NodeExecutionViewSet.as_view({
        'get': 'statistics'
    }), name='node-execution-statistics'),
    path('node-executions/<uuid:pk>/', NodeExecutionViewSet.as_view({
        'get': 'retrieve'
    }), name='node-execution-detail'),
    
    # 变量路由
    path('variables/', VariableViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='variable-list'),
    path('variables/<uuid:pk>/', VariableViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='variable-detail'),
    
    # 工具路由
    path('tools/', ToolViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='tool-list'),
    path('tools/categories/', ToolViewSet.as_view({
        'get': 'categories'
    }), name='tool-categories'),
    path('tools/<int:pk>/', ToolViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tool-detail'),
    path('tools/<int:pk>/test/', ToolViewSet.as_view({
        'post': 'test'
    }), name='tool-test'),
    
    # API凭证路由
    path('credentials/', APICredentialViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='credential-list'),
    path('credentials/providers/', APICredentialViewSet.as_view({
        'get': 'providers'
    }), name='credential-providers'),
    path('credentials/<uuid:pk>/', APICredentialViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='credential-detail'),
    path('credentials/<uuid:pk>/verify/', APICredentialViewSet.as_view({
        'post': 'verify'
    }), name='credential-verify'),
    path('credentials/<uuid:pk>/rotate/', APICredentialViewSet.as_view({
        'post': 'rotate'
    }), name='credential-rotate'),
    
    # 审计日志路由
    path('audit-logs/', AuditLogViewSet.as_view({
        'get': 'list'
    }), name='audit-log-list'),
    path('audit-logs/summary/', AuditLogViewSet.as_view({
        'get': 'summary'
    }), name='audit-log-summary'),
    path('audit-logs/actions/', AuditLogViewSet.as_view({
        'get': 'actions'
    }), name='audit-log-actions'),
    path('audit-logs/resource-types/', AuditLogViewSet.as_view({
        'get': 'resource_types'
    }), name='audit-log-resource-types'),
    path('audit-logs/<int:pk>/', AuditLogViewSet.as_view({
        'get': 'retrieve'
    }), name='audit-log-detail'),

    # === 模板系统路由 ===

    # 模板分类路由
    path('template-categories/', TemplateCategoryViewSet.as_view({
        'get': 'list'
    }), name='template-category-list'),
    path('template-categories/<uuid:pk>/', TemplateCategoryViewSet.as_view({
        'get': 'retrieve'
    }), name='template-category-detail'),

    # === 执行缓存路由 ===
    path('execution-cache/', ExecutionCacheViewSet.as_view({
        'get': 'list',
        'delete': 'invalidate_all'
    }), name='execution-cache-list'),
    path('execution-cache/stats/', ExecutionCacheViewSet.as_view({
        'get': 'stats'
    }), name='execution-cache-stats'),
    path('execution-cache/cleanup/', ExecutionCacheViewSet.as_view({
        'post': 'cleanup'
    }), name='execution-cache-cleanup'),
    path('execution-cache/<uuid:pk>/', ExecutionCacheViewSet.as_view({
        'get': 'retrieve',
        'delete': 'invalidate'
    }), name='execution-cache-detail'),

    # 缓存配置路由
    path('cache-config/', ExecutionCacheConfigViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='cache-config-list'),
    path('cache-config/defaults/', ExecutionCacheConfigViewSet.as_view({
        'get': 'defaults'
    }), name='cache-config-defaults'),
    path('cache-config/bulk_update/', ExecutionCacheConfigViewSet.as_view({
        'post': 'bulk_update'
    }), name='cache-config-bulk-update'),
    path('cache-config/<str:node_type>/', ExecutionCacheConfigViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='cache-config-detail'),

    # 工作流模板路由
    path('templates/', WorkflowTemplateViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='workflow-template-list'),
    path('templates/featured/', WorkflowTemplateViewSet.as_view({
        'get': 'featured'
    }), name='workflow-template-featured'),
    path('templates/by_category/', WorkflowTemplateViewSet.as_view({
        'get': 'by_category'
    }), name='workflow-template-by-category'),
    path('templates/mine/', WorkflowTemplateViewSet.as_view({
        'get': 'mine'
    }), name='workflow-template-mine'),
    path('templates/installed/', WorkflowTemplateViewSet.as_view({
        'get': 'installed'
    }), name='workflow-template-installed'),
    path('templates/<uuid:pk>/', WorkflowTemplateViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='workflow-template-detail'),
    path('templates/<uuid:pk>/create_from_template/', WorkflowTemplateViewSet.as_view({
        'post': 'create_from_template'
    }), name='workflow-template-create-from'),
    path('templates/<uuid:pk>/install/', WorkflowTemplateViewSet.as_view({
        'post': 'install'
    }), name='workflow-template-install'),
    path('templates/<uuid:pk>/rate/', WorkflowTemplateViewSet.as_view({
        'post': 'rate'
    }), name='workflow-template-rate'),
    path('templates/<uuid:pk>/stats/', WorkflowTemplateViewSet.as_view({
        'get': 'stats'
    }), name='workflow-template-stats'),
    path('templates/<uuid:pk>/publish/', WorkflowTemplateViewSet.as_view({
        'patch': 'publish'
    }), name='workflow-template-publish'),
    path('templates/<uuid:pk>/unpublish/', WorkflowTemplateViewSet.as_view({
        'patch': 'unpublish'
    }), name='workflow-template-unpublish'),
    path('templates/<uuid:pk>/report/', WorkflowTemplateViewSet.as_view({
        'post': 'report'
    }), name='workflow-template-report'),

    
    # 工作流导入（列表级别，无需 ID）
    path('workflows/import/', WorkflowImportView.as_view(), name='workflow-import'),
    
    # 工作流列表 - 使用 workflows/ 前缀
    path('workflows/', WorkflowViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='workflow-list'),
    path('workflows/check-env/', CheckEnvView.as_view(), name='workflow-check-env'),
    path('workflows/email-smtp-defaults/', EmailSmtpDefaultsView.as_view(), name='workflow-email-smtp-defaults'),
    path('workflows/optimize/', WorkflowOptimizeView.as_view(), name='workflow-optimize'),
    path('workflows/<uuid:pk>/', WorkflowViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='workflow-detail'),
    path('workflows/<uuid:pk>/duplicate/', WorkflowViewSet.as_view({
        'post': 'duplicate'
    }), name='workflow-duplicate'),
    path('workflows/<uuid:pk>/execute/', WorkflowViewSet.as_view({
        'post': 'execute'
    }), name='workflow-execute'),
    path('workflows/<uuid:pk>/export/', WorkflowViewSet.as_view({
        'get': 'export'
    }), name='workflow-export'),
    path('workflows/<uuid:pk>/import_workflow/', WorkflowViewSet.as_view({
        'post': 'import_workflow'
    }), name='workflow-import'),
    path('workflows/<uuid:pk>/stream_execute/', WorkflowViewSet.as_view({
        'post': 'stream_execute'
    }), name='workflow-stream-execute'),
    path('workflows/<uuid:pk>/validate/', WorkflowViewSet.as_view({
        'post': 'validate'
    }), name='workflow-validate'),
]
