"""Configuration shared by personal data APIs and scheduled backup workers."""

SNAPSHOT_TYPE = 'flowly_personal_backup'
SNAPSHOT_VERSION = 1
EXPORT_TYPES = ('full', 'workflows', 'agents', 'executions', 'usage', 'audit_logs')
EXPORT_FORMATS = ('json', 'csv', 'xlsx')
DEFAULT_MAX_SNAPSHOT_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_SNAPSHOT_RECORDS = 50000
DEFAULT_CONFIRMATION_MAX_AGE = 600
DEFAULT_BACKUP_RETENTION = 7
MIN_BACKUP_RETENTION = 3
MAX_BACKUP_RETENTION = 30
BACKUP_SCAN_INTERVAL_SECONDS = 300
BACKUP_TASK_NAME = 'core.tasks.run_due_personal_backups'
BACKUP_FREQUENCY_DAYS = {'daily': 1, 'weekly': 7}
EXCEL_MAX_CELL_CHARACTERS = 32767
BACKUP_FREQUENCIES = ('daily', 'weekly', 'monthly')
DELETE_CONFIRMATION_TEXT = '删除个人工作流和Agent'
RESTORE_SIGNING_SALT = 'flowly.personal-data.restore.v1'
DELETE_SIGNING_SALT = 'flowly.personal-data.delete.v1'
RESTORED_NAME_SUFFIX = '（恢复副本）'
RESTORED_NODE_ALIASES_KEY = '_restored_node_aliases'
PERSONAL_DELETE_MODELS = frozenset({
    'workflows.workflow', 'workflows.node', 'workflows.edge', 'workflows.variable',
    'workflows.workflowexecution', 'workflows.nodeexecution', 'workflows.executionlog',
    'workflows.webhookdeliverylog', 'workflows.workflowtrigger', 'workflows.triggerexecution',
    'workflows.webhook', 'agents.agent', 'agents.agenttool', 'agents.agentconversation',
    'agents.agentexecution', 'monitoring.executionlog', 'monitoring.metric',
})

WORKFLOW_FIELDS = ('id', 'name', 'description', 'category', 'tags', 'config', 'version')
NODE_FIELDS = (
    'id', 'node_type', 'name', 'description', 'parent_node_id', 'position_x',
    'position_y', 'width', 'height', 'sort_order', 'config', 'input_schema',
    'output_schema', 'style', 'error_handling', 'max_retries', 'retry_delay_seconds',
    'fallback_value', 'condition_expression', 'is_enabled', 'timeout_seconds', 'version',
)
EDGE_FIELDS = (
    'id', 'source_node_id', 'source_handle', 'target_node_id', 'target_handle',
    'label', 'style', 'condition_expression', 'condition_priority', 'animated',
)
AGENT_FIELDS = (
    'id', 'name', 'description', 'agent_type', 'system_prompt', 'model', 'temperature',
    'max_tokens', 'tools', 'skills', 'memory_enabled', 'context_window',
    'knowledge_collections', 'settings', 'is_active',
)
AGENT_TOOL_FIELDS = ('id', 'name', 'tool_type', 'config', 'is_enabled')
VARIABLE_FIELDS = ('id', 'name', 'display_name', 'description', 'var_type', 'default_value',
                   'validation_rules', 'source', 'secret_path', 'is_required', 'is_sensitive')
TRIGGER_FIELDS = ('id', 'name', 'description', 'trigger_type', 'schedule_type', 'scheduled_at',
                  'interval_seconds', 'cron_expression', 'webhook_path', 'webhook_secret',
                  'event_type', 'event_filter', 'input_mapping', 'max_executions')
WEBHOOK_FIELDS = ('id', 'name', 'path', 'auth_type', 'auth_secret', 'input_mapping')
