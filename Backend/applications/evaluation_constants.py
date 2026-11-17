"""Limits, states and user-facing copy for deterministic application regressions."""
MAX_SUITES = 20
MAX_CASES = 100
MAX_ASSERTIONS = 20
MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_RUN_SECONDS = 900
QUEUE_LEASE_SECONDS = 120
LEASE_GRACE_SECONDS = 30
POLL_SECONDS = .2
MAX_ACTIVE_RUNS = 1
MAX_ASSERTION_DISPLAY_CHARS = 500
MAX_ASSERTION_VALUE_BYTES = 64 * 1024
EXPORT_SCHEMA_VERSION = 1
ACTIVE_RUN_STATUSES = ('queued', 'running', 'cancelling')
TERMINAL_RUN_STATUSES = ('completed', 'failed', 'cancelled')
ASSERTION_TYPES = ('json_equals', 'json_contains', 'json_exists', 'json_type',
                   'response_contains', 'grounded', 'sources_min', 'latency_max', 'error_code')
JSON_TYPES = ('object', 'array', 'string', 'number', 'boolean', 'null')
MESSAGES = {
    'suite_missing': '测试集不存在或已删除。',
    'case_missing': '用例不存在，或不属于当前测试集。',
    'suite_limit': '测试集数量已达到服务端上限。',
    'case_limit': '用例数量已达到服务端上限。',
    'empty_suite': '请先保存并启用至少一条测试用例。',
    'target': '目标必须是当前草稿，或本应用的真实发布版本。',
    'busy': '本应用已有评测在排队或运行，请等待结束或明确取消。',
    'queue_failed': '无法提交评测任务，请检查消息队列；本批次没有开始执行。',
    'queue_expired': '评测排队超时，未启动用例。请检查 Worker 后重新发起。',
    'expired': '评测执行租约已过期；不会自动重复可能产生副作用的调用。',
    'cancelled': '评测已取消，后续用例不会启动；外部已经发生的操作无法撤回。',
    'permission': '评测发起者或应用资源的权限已失效，已停止后续用例。',
    'execution': '用例执行失败，请查看关联请求的真实错误。',
    'unexpected_error': '请求未成功，且用例未声明期望的错误代码。',
    'gate': '发布需要当前草稿通过指定测试集的完整回归；用例、配置或知识内容变化后需重跑。',
    'required_suite': '该测试集是当前发布门禁，请先明确解除门禁后再删除。',
    'suite_running': '测试集仍有在途评测，请先取消或等待结束。',
    'import': '导入必须是受支持版本的 Flowly 应用测试集 JSON。',
    'idempotency': '相同请求标识已用于不同评测参数，请为新运行生成新标识。',
    'compare': '只能比较同一应用、同一测试集的两个已结束批次。',
    'corpus_changed': '知识内容在运行期间或两个批次间发生变化，结果不能直接归因于版本差异。',
}
