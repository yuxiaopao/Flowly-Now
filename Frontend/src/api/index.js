import axios from 'axios'
import Cookies from 'js-cookie'
import { ElMessageBox } from 'element-plus'
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

    // 自动转换请求数据: camelCase -> snake_case
    if (config.data && typeof config.data === 'object') {
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

function extractErrorMessage(data) {
  if (!data || typeof data !== 'object') return null

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

  return data.error_message || data.error || data.message || data.detail || null
}

// =============================================================================
// 响应拦截器
// =============================================================================

api.interceptors.response.use(
  (response) => {
    requestState.pending--

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
      getAppStore()?.error('网络连接失败，请检查网络')
      return Promise.reject(error)
    }

    const status = response.status
    const originalRequest = config
    const errorMsg = extractErrorMessage(response.data)

    switch (status) {
      case 400:
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
      case 401:
        // 尝试刷新 Token
        const refreshToken = Cookies.get('refresh_token') || localStorage.getItem('refresh_token')
        if (refreshToken && !originalRequest._retry) {
          originalRequest._retry = true
          try {
            const res = await axios.post(
              `${APP_CONFIG.apiBaseUrl}${APP_CONFIG.apiPrefix}/auth/refresh/`,
              { refresh: refreshToken }
            )
            const { access } = res.data
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
            router.push('/login')
            getAppStore()?.error('登录已过期，请重新登录')
          }
        } else {
          Cookies.remove('access_token')
          Cookies.remove('refresh_token')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          router.push('/login')
          getAppStore()?.error('请先登录')
        }
        break
      case 403:
        getAppStore()?.error(errorMsg || '没有权限访问此资源')
        break
      case 404:
        getAppStore()?.error(errorMsg || '请求的资源不存在')
        break
      case 422:
        // 表单验证错误 - 转换字段名后显示
        const errors = response.data
        if (typeof errors === 'object' && errors !== null) {
          const camelCaseErrors = toCamelCaseKeys(errors)
          const messages = Object.values(camelCaseErrors).flat().join('; ')
          getAppStore()?.error(messages || '数据验证失败')
        }
        break
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
