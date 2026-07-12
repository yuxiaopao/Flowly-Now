/**
 * Electron 桌面端平台检测与 Agent API 桥接
 */

export function isElectron() {
  return Boolean(
    typeof window !== 'undefined'
    && (window.flowlyDesktop?.isDesktop || window.agentAPI),
  )
}

export function getAgentAPI() {
  if (typeof window === 'undefined') return null
  return window.agentAPI || null
}

export async function getDesktopAgentStatus() {
  const api = getAgentAPI()
  if (!api) return null
  try {
    return await api.getStatus()
  } catch {
    return null
  }
}

export async function connectDesktopAgent({ cloudUrl, agentId, apiToken } = {}) {
  const api = getAgentAPI()
  if (!api) {
    throw new Error('当前环境不是 Flowly 桌面端')
  }
  return api.connect({ cloudUrl, agentId, apiToken })
}

export async function disconnectDesktopAgent() {
  const api = getAgentAPI()
  if (!api) return null
  return api.disconnect()
}

export async function getDesktopAgentConfig() {
  const api = getAgentAPI()
  if (!api) return null
  return api.getConfig()
}
