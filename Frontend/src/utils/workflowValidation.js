/** 合并画布校验与真实后端执行器校验，保留节点定位信息。 */
export function mergeWorkflowValidation(local, remote) {
  const errors = [...local.errors]
  const warnings = [...local.warnings]
  const nodeErrors = Object.fromEntries(Object.entries(local.nodeErrors || {}).map(([id, messages]) => [id, [...messages]]))
  const issues = remote.nodeIssues || remote.node_issues || []
  for (const severity of ['error', 'warning']) {
    const target = severity === 'error' ? errors : warnings
    for (const message of remote[severity === 'error' ? 'errors' : 'warnings'] || []) {
      if (target.some(item => item.message === message)) continue
      const issue = issues.find(item => item.message === message)
      const nodeId = issue?.nodeId || issue?.node_id
      target.push({ type: issue?.code || 'backend_validation', message, severity, ...(nodeId ? { nodeId } : {}) })
      if (nodeId && severity === 'error') {
        nodeErrors[nodeId] ||= []
        if (!nodeErrors[nodeId].includes(message)) nodeErrors[nodeId].push(message)
      }
    }
  }
  return { valid: errors.length === 0, errors, warnings, nodeErrors }
}
