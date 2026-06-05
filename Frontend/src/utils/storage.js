/**
 * 本地存储工具
 * 提供 localStorage 和 sessionStorage 的封装
 */

const PREFIX = 'flowly_'

/**
 * 存储工具类
 */
class Storage {
  constructor(type = 'local') {
    this.storage = type === 'session' ? sessionStorage : localStorage
    this.type = type
  }

  /**
   * 获取带前缀的 key
   */
  getKey(key) {
    return `${PREFIX}${key}`
  }

  /**
   * 设置值
   */
  set(key, value, options = {}) {
    const storageKey = this.getKey(key)
    
    try {
      const data = {
        value,
        timestamp: Date.now(),
        expire: options.expire || null
      }

      // 如果设置了过期时间
      if (options.expire) {
        data.expire = Date.now() + options.expire
      }

      this.storage.setItem(storageKey, JSON.stringify(data))
      return true
    } catch {
      return false
    }
  }

  /**
   * 获取值
   */
  get(key, defaultValue = null) {
    const storageKey = this.getKey(key)

    try {
      const data = this.storage.getItem(storageKey)
      if (!data) return defaultValue

      const parsed = JSON.parse(data)

      // 检查是否过期
      if (parsed.expire && Date.now() > parsed.expire) {
        this.remove(key)
        return defaultValue
      }

      return parsed.value ?? defaultValue
    } catch {
      return defaultValue
    }
  }

  /**
   * 获取字符串值（不移除过期检查）
   */
  getString(key, defaultValue = '') {
    const storageKey = this.getKey(key)
    return this.storage.getItem(storageKey) || defaultValue
  }

  /**
   * 获取数字值
   */
  getNumber(key, defaultValue = 0) {
    const value = this.get(key)
    const num = Number(value)
    return isNaN(num) ? defaultValue : num
  }

  /**
   * 获取布尔值
   */
  getBoolean(key, defaultValue = false) {
    const value = this.get(key)
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') {
      return value.toLowerCase() === 'true'
    }
    return defaultValue
  }

  /**
   * 获取对象值
   */
  getObject(key, defaultValue = {}) {
    const value = this.get(key)
    if (typeof value === 'object' && value !== null) return value
    return defaultValue
  }

  /**
   * 获取数组值
   */
  getArray(key, defaultValue = []) {
    const value = this.get(key)
    if (Array.isArray(value)) return value
    return defaultValue
  }

  /**
   * 检查 key 是否存在
   */
  has(key) {
    const storageKey = this.getKey(key)
    return this.storage.getItem(storageKey) !== null
  }

  /**
   * 移除值
   */
  remove(key) {
    const storageKey = this.getKey(key)
    try {
      this.storage.removeItem(storageKey)
      return true
    } catch {
      return false
    }
  }

  clear() {
    try {
      const keys = this.keys()
      keys.forEach(key => this.storage.removeItem(this.getKey(key)))
      return true
    } catch {
      return false
    }
  }

  /**
   * 获取所有 key
   */
  keys() {
    const result = []
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i)
      if (key && key.startsWith(PREFIX)) {
        result.push(key.substring(PREFIX.length))
      }
    }
    return result
  }

  /**
   * 获取所有 key（包括前缀）
   */
  keysWithPrefix() {
    const result = []
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i)
      if (key && key.startsWith(PREFIX)) {
        result.push(key)
      }
    }
    return result
  }
}

// 创建实例
const localStore = new Storage('local')
const sessionStore = new Storage('session')

// ==================== 快捷方法 ====================

/**
 * 设置认证 Token
 */
export function setToken(accessToken, refreshToken) {
  localStore.set('access_token', accessToken, { expire: 24 * 60 * 60 * 1000 }) // 1天
  if (refreshToken) {
    localStore.set('refresh_token', refreshToken, { expire: 7 * 24 * 60 * 60 * 1000 }) // 7天
  }
}

/**
 * 获取访问 Token
 */
export function getAccessToken() {
  return localStore.get('access_token')
}

/**
 * 获取刷新 Token
 */
export function getRefreshToken() {
  return localStore.get('refresh_token')
}

/**
 * 清除 Token
 */
export function clearTokens() {
  localStore.remove('access_token')
  localStore.remove('refresh_token')
}

/**
 * 设置用户信息
 */
export function setUserInfo(user) {
  localStore.set('user_info', user)
}

/**
 * 获取用户信息
 */
export function getUserInfo() {
  return localStore.getObject('user_info')
}

/**
 * 清除用户信息
 */
export function clearUserInfo() {
  localStore.remove('user_info')
}

/**
 * 设置主题
 */
export function setTheme(theme) {
  localStore.set('theme', theme)
}

/**
 * 获取主题
 */
export function getTheme() {
  return localStore.get('theme', 'dark')
}

/**
 * 设置工作流草稿
 */
export function setWorkflowDraft(workflowId, data) {
  localStore.set(`workflow_draft_${workflowId}`, data, { expire: 7 * 24 * 60 * 60 * 1000 })
}

/**
 * 获取工作流草稿
 */
export function getWorkflowDraft(workflowId) {
  return localStore.getObject(`workflow_draft_${workflowId}`)
}

/**
 * 清除工作流草稿
 */
export function clearWorkflowDraft(workflowId) {
  localStore.remove(`workflow_draft_${workflowId}`)
}

/**
 * 设置用户偏好设置
 */
export function setPreferences(preferences) {
  localStore.set('preferences', preferences)
}

/**
 * 获取用户偏好设置
 */
export function getPreferences() {
  return localStore.getObject('preferences', {
    language: 'zh-CN',
    timezone: 'Asia/Shanghai',
    dateFormat: 'YYYY-MM-DD',
    timeFormat: 'HH:mm',
    pageSize: 20
  })
}

/**
 * 设置侧边栏折叠状态
 */
export function setSidebarCollapsed(collapsed) {
  sessionStore.set('sidebar_collapsed', collapsed)
}

/**
 * 获取侧边栏折叠状态
 */
export function getSidebarCollapsed() {
  return sessionStore.getBoolean('sidebar_collapsed', false)
}

/**
 * 缓存 API 响应
 */
export function cacheResponse(key, data, expire = 5 * 60 * 1000) {
  localStore.set(`cache_${key}`, data, { expire })
}

/**
 * 获取缓存的响应
 */
export function getCachedResponse(key) {
  return localStore.getObject(`cache_${key}`)
}

/**
 * 清除缓存
 */
export function clearCache() {
  const keys = localStore.keys()
  keys.filter(k => k.startsWith('cache_')).forEach(k => localStore.remove(k))
}

// ==================== 导出 ====================

export { localStore, sessionStore }
export default {
  local: localStore,
  session: sessionStore,
  setToken,
  getAccessToken,
  getRefreshToken,
  clearTokens,
  setUserInfo,
  getUserInfo,
  clearUserInfo,
  setTheme,
  getTheme,
  setWorkflowDraft,
  getWorkflowDraft,
  clearWorkflowDraft,
  setPreferences,
  getPreferences,
  setSidebarCollapsed,
  getSidebarCollapsed,
  cacheResponse,
  getCachedResponse,
  clearCache
}
