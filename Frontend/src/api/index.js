import axios from 'axios'
import Cookies from 'js-cookie'
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
    const token = Cookies.get('access_token') || localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // FormData / Blob 不做字段转换，并移除默认 JSON Content-Type 以便浏览器设置 boundary
    if (config.data instanceof FormData || config.data instanceof Blob) {
      if (config.headers) {
        delete config.headers['Content-Type']
      }
    } else if (config.data && typeof config.data === 'object') {
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
const AUTH_PUBLIC_PATHS = [
  '/auth/login/',
  '/auth/register/',
  '/auth/refresh/',
  '/auth/password-reset/',
  '/auth/password-reset/confirm/',
  '/auth/verify-email/',
  '/auth/verify-email/resend/',
]

function isAuthPublicRequest(config) {
  const url = config?.url || ''
  return AUTH_PUBLIC_PATHS.some((path) => url.includes(path))
}

function isAuthPageRoute() {
  const path = router.currentRoute.value?.path || ''
  return ['/login', '/register', '/forgot-password', '/reset-password'].some(
    (authPath) => path === authPath || path.startsWith(`${authPath}/`)
  )
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
    if (responseData && typeof responseData === 'object') {
      responseData = toCamelCaseKeys(responseData)
    }
    return responseData
  },
  async (error) => {
    requestState.pending--

    const { response, config, code } = error

    // 超时重试（仅重试一次）
    if (code === 'ECONNABORTED' && !config._timeoutRetry) {
      config._timeoutRetry = true
      requestState.pending++
      return api(config)
    }

    if (!response) {
      const retryableMethod = (config?.method || 'get').toLowerCase()
      const canRetryNetwork = !config?._networkRetry && ['get', 'head', 'options'].includes(retryableMethod)

      if (canRetryNetwork) {
        config._networkRetry = true
        await new Promise(resolve => setTimeout(resolve, 800))
        requestState.pending++
        return api(config)
      }

      getAppStore()?.error(
        error.code === 'ERR_NETWORK' || `${error.message || ''}`.includes('Network Error')
          ? '无法连接后端服务，请确认 Django 已在 127.0.0.1:8000 启动'
          : '网络连接失败，请检查网络',
      )
      return Promise.reject(error)
    }

    const status = response.status
    const originalRequest = config
    const skipErrorToast = Boolean(originalRequest?.skipErrorToast)
    const errorMsg = extractErrorMessage(response.data)

    switch (status) {
      case 400: {
        const detail = response.data?.detail || response.data?.error || response.data?.message
        if (detail) {
          getAppStore()?.error(`请求参数错误: ${detail}`)
        } else {
          const errorValues = Object.values(response.data).flat()
          if (errorValues.length > 0) {
            getAppStore()?.error(`请求参数错误: ${errorValues.join('; ')}`)
          } else {
            getAppStore()?.error('请求参数错误')
          }
        }
        break
      }
      case 401: {
        // 登录/注册等公开认证接口：直接展示后端返回的具体原因
        if (isAuthPublicRequest(originalRequest)) {
          getAppStore()?.error(extractErrorMessage(response.data) || '认证失败，请检查输入')
          break
        }

        // 尝试刷新 Token
        const refreshToken = Cookies.get('refresh_token') || localStorage.getItem('refresh_token')
        if (refreshToken && !originalRequest._retry) {
          originalRequest._retry = true
          try {
            const res = await axios.post(
              `${APP_CONFIG.apiBaseUrl}${APP_CONFIG.apiPrefix}/auth/refresh/`,
              { refresh: refreshToken }
            )
            let refreshData = res.data
            if (refreshData && typeof refreshData === 'object' && 'code' in refreshData && 'data' in refreshData) {
              refreshData = refreshData.data
            }
            const access = refreshData?.access
            if (!access) {
              throw new Error('refresh response missing access token')
            }
            Cookies.set('access_token', access, { expires: 1 })
            localStorage.setItem('access_token', access)
            originalRequest.headers.Authorization = `Bearer ${access}`
            requestState.pending++
            return api(originalRequest)
          } catch (refreshError) {
            Cookies.remove('access_token')
            Cookies.remove('refresh_token')
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            if (!isAuthPageRoute()) {
              router.push('/login')
            }
            getAppStore()?.error('登录已过期，请重新登录')
          }
        } else {
          Cookies.remove('access_token')
          Cookies.remove('refresh_token')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          if (!isAuthPageRoute()) {
            router.push('/login')
            getAppStore()?.error(extractErrorMessage(response.data) || '请先登录')
          }
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
    const token = Cookies.get('access_token') || localStorage.getItem('access_token')

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
