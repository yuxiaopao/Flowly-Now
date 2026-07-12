import api from './index'
import { APP_CONFIG } from '@/config'

export function getSiteConfig() {
  return api.get('/public/site-config/')
}

/**
 * 登录页机器人对话（无需登录）
 * @param {{ message: string, history?: Array<{role: string, content: string}> }} data
 */
export function sendAuthAssistantMessage(data) {
  return api.post('/public/auth-assistant/chat/', data, {
    timeout: APP_CONFIG.auth.assistantTimeoutMs,
  })
}
