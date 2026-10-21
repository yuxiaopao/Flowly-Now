const AUTH_SETTINGS = Object.freeze({
  cacheMs: 10000,
  timeoutMs: 5000,
  profilePath: '/api/v1/auth/user/',
  runPath: '/api/v1/training/yolo-runs/',
  requiredMessage: '请先登录 Flowly 后查看训练数据',
});

function createMonitorSession(getBackendUrl, request = fetch) {
  let session = null;
  let revision = 0;

  function clear() {
    revision++;
    session = null;
  }

  async function requireSession(token) {
    const base = String(getBackendUrl() || '').replace(/\/+$/, '');
    if (token !== undefined && (token !== session?.token || base !== session?.base)) {
      clear();
      if (typeof token !== 'string' || !token.trim()) throw new Error(AUTH_SETTINGS.requiredMessage);
      session = { token, base, verifiedAt: 0, user: null };
    }
    const current = session;
    const version = revision;
    if (!current || current.base !== base) {
      clear();
      throw new Error(AUTH_SETTINGS.requiredMessage);
    }
    if (current.user && Date.now() - current.verifiedAt < AUTH_SETTINGS.cacheMs) return current.user;
    try {
      const response = await request(`${base}${AUTH_SETTINGS.profilePath}`, {
        headers: { Authorization: `Bearer ${current.token}` },
        signal: AbortSignal.timeout(AUTH_SETTINGS.timeoutMs),
        redirect: 'error',
      });
      if (!response.ok) throw new Error(AUTH_SETTINGS.requiredMessage);
      const body = await response.json();
      const user = body.data || body;
      if (!user?.id || !user.username) throw new Error(AUTH_SETTINGS.requiredMessage);
      if (session !== current || revision !== version) throw new Error(AUTH_SETTINGS.requiredMessage);
      current.user = { id: user.id, username: user.username };
      current.verifiedAt = Date.now();
      return current.user;
    } catch (error) {
      if (session === current) clear();
      if (error.message === AUTH_SETTINGS.requiredMessage) throw error;
      throw new Error('无法验证登录状态，请检查 Flowly 服务后重新登录');
    }
  }

  async function getRun(binding) {
    await requireSession();
    const keys = ['jobId', 'nodeId', 'workflowId'];
    if (!binding || keys.some(key => !/^[a-f0-9-]{36}$/i.test(binding[key] || ''))) {
      throw new Error('请从工作流的 YOLO 训练节点打开监控');
    }
    const current = session;
    const key = keys.map(field => binding[field]).join(':');
    if (current.run?.key === key && Date.now() - current.run.at < AUTH_SETTINGS.cacheMs) return current.run.data;
    const response = await request(`${current.base}${AUTH_SETTINGS.runPath}${binding.jobId}/`, {
      headers: { Authorization: `Bearer ${current.token}` },
      signal: AbortSignal.timeout(AUTH_SETTINGS.timeoutMs),
      redirect: 'error',
    });
    if (!response.ok) throw new Error('当前账号无权访问此训练任务，或任务已不存在');
    const body = await response.json();
    const job = body.data || body;
    if (session !== current || String(job.node) !== binding.nodeId || String(job.workflow) !== binding.workflowId) {
      throw new Error('训练任务与当前工作流节点不匹配');
    }
    const local = job.config?.local_monitor || job.config?.localMonitor;
    const projectRoot = local?.project_root || local?.projectRoot;
    const runName = local?.run_name || local?.runName;
    if (!projectRoot || !runName) throw new Error('此任务尚未关联本地训练记录');
    const data = {
      ...binding, projectRoot, runName,
      nodeName: job.node_name || job.nodeName, workflowName: job.workflow_name || job.workflowName,
    };
    current.run = { key, at: Date.now(), data };
    return data;
  }

  return { requireSession, getRun, clear };
}

module.exports = { createMonitorSession, AUTH_SETTINGS };
