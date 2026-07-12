import { watch } from 'vue'
import APP_CONFIG from '@/config'
import {
  connectDesktopAgent,
  disconnectDesktopAgent,
  getDesktopAgentConfig,
  getDesktopAgentStatus,
  isElectron,
} from '@/utils/electron'

function normalizeCloudUrl(url) {
  return String(url || APP_CONFIG.apiBaseUrl).trim().replace(/\/+$/, '')
}

/**
 * 登录后自动将本地 GPU Agent 注册并连接至云端
 */
export async function bootstrapDesktopAgent(apiToken) {
  if (!isElectron() || !apiToken) return null

  const config = await getDesktopAgentConfig()
  const status = await getDesktopAgentStatus()
  if (status?.connected) {
    return status
  }

  return connectDesktopAgent({
    cloudUrl: normalizeCloudUrl(config?.cloudUrl),
    agentId: config?.agentId,
    apiToken,
  })
}

/**
 * 在 App 根组件挂载：监听登录态，自动连接/断开本地 Agent
 */
export function useDesktopAgentBridge(authStore) {
  if (!isElectron()) return

  const syncAgentConnection = async (token) => {
    if (token) {
      try {
        await bootstrapDesktopAgent(token)
      } catch (err) {
        console.warn('[desktop-agent] auto-connect failed:', err?.message || err)
      }
      return
    }

    try {
      await disconnectDesktopAgent()
    } catch {
      // ignore
    }
  }

  watch(
    () => authStore.token,
    (token) => {
      syncAgentConnection(token)
    },
    { immediate: true },
  )
}

export { isElectron, getDesktopAgentStatus, connectDesktopAgent, disconnectDesktopAgent }
