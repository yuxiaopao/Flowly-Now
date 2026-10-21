import axios from 'axios'
import { AUTH } from '@/config/auth'
import { authSession, saveAuthSession, clearAuthSession } from '@/utils/authSession'
import router from '@/router'
import { APP_CONFIG, getApiBaseUrl } from '@/config'
import { reactive } from 'vue'
import { useAppStore } from '@/stores/app'

// =============================================================================
// 全局请求状态（loading 计数器）
// =============================================================================

export const requestState = reactive({
  pending: 0,
  get loading() { return this.pending > 0 }
})

// 创建 Axios 实例
const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: APP_CONFIG.requestTimeout,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const sessionClient = axios.create({ timeout: APP_CONFIG.requestTimeout })

// =============================================================================
// 字段转换函数 (snake_case <-> camelCase)
// =============================================================================

const toCamelCase = (str) => str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())

const toSnakeCase = (str) => str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)

const convertKeys = (obj, converter) => {
  if (obj === null || obj === undefined) return obj
  if (Array.isArray(obj)) return obj.map(item => convertKeys(item, converter))
  if (typeof obj !== 'object') return obj

  return Object.keys(obj).reduce((acc, key) => {
    const convertedKey = converter(key)
    let value = obj[key]

    if (value && typeof value === 'object') {
      value = convertKeys(value, converter)
    }

    acc[convertedKey] = value
    return acc
  }, {})
}

const toCamelCaseKeys = (obj) => convertKeys(obj, toCamelCase)
const toSnakeCaseKeys = (obj) => convertKeys(obj, toSnakeCase)

// =============================================================================
// 请求拦截器
// =============================================================================

api.interceptors.request.use(
  (config) => {
    requestState.pending++

    // 添加认证 Token
    const token = authSession.access
    if (token && !isAuthPublicRequest(config) && !config.url?.startsWith('/public/')) {
      config.headers.Authorization = `Bearer ${token}`
      config._authAccess = token
    } else {
      delete config.headers.Authorization
    }

    // FormData / Blob 不做字段转换，并移除默认 JSON Content-Type 以便浏览器设置 boundary
    if (config.data instanceof FormData || config.data instanceof Blob) {
      if (config.headers) {
        delete config.headers['Content-Type']
      }
    } else if (config.data && typeof config.data === 'object' && !config.preserveRequestKeys) {
      // 自动转换请求数据: camelCase -> snake_case
      config.data = toSnakeCaseKeys(config.data)
    }

    return config
  },
  (error) => {
    requestState.pending--
    return Promise.reject(error)
  }
)

// =============================================================================
// 统一错误消息提取
// =============================================================================

let _appStore = null
function getAppStore() {
  if (!_appStore) {
    try {
      _appStore = useAppStore()
    } catch {
      return null
    }
  }
  return _appStore
}

function isHtmlErrorPayload(data) {
  if (typeof data !== 'string') return false
  const trimmed = data.trimStart().toLowerCase()
  return trimmed.startsWith('<!doctype') || trimmed.startsWith('<html') || trimmed.includes('<title>page not found')
}

function extractErrorMessage(data) {
  if (!data) return null
  if (typeof data === 'string') {
    if (isHtmlErrorPayload(data)) return null
    return data.length > 500 ? `${data.slice(0, 500)}…` : data
  }

  if (typeof data === 'object') {
    // DRF ValidationError / 登录失败等
    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
      return data.non_field_errors.join('；')
    }

    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail.map((item) => (typeof item === 'string' ? item : item?.msg || String(item))).join('；')
    }

    // 处理 errors 对象中的具体错误信息
    if (data.errors && typeof data.errors === 'object') {
      const messages = []
      for (const [, value] of Object.entries(data.errors)) {
        if (Array.isArray(value)) {
          messages.push(...value)
        } else if (typeof value === 'string') {
          messages.push(value)
        }
      }
      if (messages.length > 0) return messages.join('；')
    }

    const direct = data.error_message || data.error || data.message || data.detail
    if (direct) return typeof direct === 'string' ? direct : JSON.stringify(direct)

    // 字段级校验错误，如 { username: ['该字段是必填项'] }
    const fieldMessages = []
    for (const [key, value] of Object.entries(data)) {
      if (['errors', 'code', 'data'].includes(key)) continue
      if (Array.isArray(value)) {
        fieldMessages.push(...value.map((item) => (typeof item === 'string' ? item : String(item))))
      } else if (typeof value === 'string') {
        fieldMessages.push(value)
      }
    }
    if (fieldMessages.length > 0) return fieldMessages.join('；')
  }

  return null
}

/** 无需登录态的认证接口（401 应展示业务错误，而非「请先登录」） */
const AUTH_PUBLIC_PATHS = Object.values(AUTH.endpoints)

function isAuthPublicRequest(config) {
  const url = config?.url || ''
  return AUTH_PUBLIC_PATHS.some((path) => url.split('?')[0].endsWith(path))
}

function isAuthPageRoute() {
  const path = router.currentRoute.value?.path || ''
  return ['/login', '/register', '/forgot-password', '/reset-password'].some(
    (authPath) => path === authPath || path.startsWith(`${authPath}/`)
  )
}

let refreshPromise = null
async function refreshSession() {
  if (!refreshPromise) {
    const revision = authSession.revision
    refreshPromise = sessionClient.post(AUTH.endpoints.refresh, { refresh: authSession.refresh }, {
      baseURL: api.defaults.baseURL, timeout: APP_CONFIG.requestTimeout,
    }).then(response => {
      const data = toCamelCaseKeys(response.data?.data ?? response.data)
      if (authSession.revision !== revision) throw new axios.CanceledError('登录状态已变化')
      saveAuthSession(data)
      return data.access
    }).finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

// =============================================================================
// 响应拦截器
// =============================================================================

api.interceptors.response.use(
  (response) => {
    requestState.pending--

    if (response.config?.responseType === 'blob') {
      return response.data
    }

    let responseData = response.data

    // 适配统一响应格式：如果后端返回 {code, message, data} 结构，提取 data 字段
    if (responseData && typeof responseData === 'object' && 'code' in responseData && 'data' in responseData) {
      responseData = responseData.data
    }

    // 自动转换响应数据: snake_case -> camelCase
    if (responseData && typeof responseData === 'object' && !response.config?.preserveResponseKeys) {
      const original = responseData
      responseData = toCamelCaseKeys(responseData)
      // Workflow configuration is user data: changing its keys changes executable semantics.
      if (response.config?.preserveWorkflowKeys) {
        for (const key of ['workflow', 'workflow_json', 'messages']) {
          if (original[key] !== undefined) responseData[toCamelCase(key)] = original[key]
        }
      }
    }
    return responseData
  },
  async (error) => {
    requestState.pending--

    const { response, config, code } = error

    // Canceled requests are expected when changing projects, searches, or files.
    if (code === 'ERR_CANCELED') return Promise.reject(error)

    // 超时重试（仅重试一次）
    if (code === 'ECONNABORTED' && config && ['get', 'head', 'options'].includes(config.method) && !config._timeoutRetry) {
      config._timeoutRetry = true
      return api(config)
    }

    if (!response) {
      const retryableMethod = (config?.method || 'get').toLowerCase()
      const canRetryNetwork = config && code !== 'ECONNABORTED' && !config._networkRetry && ['get', 'head', 'options'].includes(retryableMethod)

      if (canRetryNetwork) {
        config._networkRetry = true
        await new Promise(resolve => setTimeout(resolve, AUTH.safeRetryDelay))
        return api(config)
      }

      if (!config?.skipErrorToast) getAppStore()?.error(
        error.code === 'ERR_NETWORK' || `${error.message || ''}`.includes('Network Error')
          ? '暂时无法连接服务，请检查网络后重试'
          : '网络连接失败，请检查网络',
      )
      return Promise.reject(error)
    }

    const status = response.status
    const originalRequest = config
    const skipErrorToast = Boolean(originalRequest?.skipErrorToast)
    const errorMsg = extractErrorMessage(response.data)

    if (skipErrorToast && status !== 401) return Promise.reject(error)

    switch (status) {
      case 400: {
        getAppStore()?.error(errorMsg || '请求参数错误')
        break
      }
      case 401: {
        // 登录/注册等公开认证接口：直接展示后端返回的具体原因
        if (isAuthPublicRequest(originalRequest)) {
          if (!skipErrorToast) getAppStore()?.error(errorMsg || '认证失败，请检查输入')
          break
        }

        // 尝试刷新 Token
        const refreshToken = authSession.refresh
        if (refreshToken && !originalRequest._retry) {
          originalRequest._retry = true
          try {
            const access = authSession.access !== originalRequest._authAccess
              ? authSession.access : await refreshSession()
            originalRequest.headers.Authorization = `Bearer ${access}`
            return api(originalRequest)
          } catch (refreshError) {
            if (![400, 401].includes(refreshError.response?.status)) {
              if (refreshError.code !== 'ERR_CANCELED' && !skipErrorToast) getAppStore()?.error('暂时无法验证登录状态，请重试')
              return Promise.reject(refreshError)
            }
          }
        }
        clearAuthSession()
        if (!isAuthPageRoute() && !originalRequest.skipAuthRedirect) {
          router.replace({ path: AUTH.routes.login, query: { redirect: router.currentRoute.value.fullPath } })
          if (!skipErrorToast) getAppStore()?.error('登录已过期，请重新登录')
        }
        break
      }
      case 403:
        if (!skipErrorToast) {
          getAppStore()?.error(errorMsg || '没有权限访问此资源')
        }
        break
      case 404:
        if (!skipErrorToast) {
          getAppStore()?.error(errorMsg || '请求的资源不存在')
        }
        break
      case 422: {
        // 表单验证错误 - 转换字段名后显示
        const errors = response.data
        if (typeof errors === 'object' && errors !== null) {
          const camelCaseErrors = toCamelCaseKeys(errors)
          const messages = Object.values(camelCaseErrors).flat().join('; ')
          getAppStore()?.error(messages || '数据验证失败')
        }
        break
      }
      case 429:
        getAppStore()?.warning('请求过于频繁，请稍后再试')
        break
      case 500:
        getAppStore()?.error(errorMsg || '服务器内部错误')
        break
      case 502:
      case 503:
      case 504:
        getAppStore()?.error('服务暂时不可用，请稍后再试')
        break
      default:
        getAppStore()?.error(errorMsg || '请求失败')
    }

    return Promise.reject(error)
  }
)

// =============================================================================
// 导出字段转换工具函数
// =============================================================================

export { toCamelCase, toSnakeCase, toCamelCaseKeys, toSnakeCaseKeys }

// 封装通用请求方法
export const request = {
  get(url, params = {}, config = {}) {
    return api.get(url, { params, ...config })
  },

  post(url, data = {}, config = {}) {
    return api.post(url, data, config)
  },

  put(url, data = {}, config = {}) {
    return api.put(url, data, config)
  },

  patch(url, data = {}, config = {}) {
    return api.patch(url, data, config)
  },

  delete(url, config = {}) {
    return api.delete(url, config)
  },

  // 流式请求
  stream(url, data = {}, config = {}) {
    const token = authSession.access

    // 转换 camelCase -> snake_case
    const snakeData = toSnakeCaseKeys(data)

    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...config.headers
    }

    return fetch(`${api.defaults.baseURL}${url}`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(snakeData)
    })
  }
}

// 直接获取 axios 实例
export { api }

export default api
