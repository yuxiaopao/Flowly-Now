/**
 * 通用请求 Hook
 * 提供统一的请求状态管理（loading/error/data）
 */

import { ref, shallowRef } from 'vue'
import { ElLoading } from 'element-plus'
import { useAppStore } from '@/stores/app'
import api from '@/api/index'

/**
 * useRequest Hook
 * @param {Function} apiFunc - API 函数
 * @param {Object} options - 配置选项
 * @returns {Object} 请求状态和方法
 */
export function useRequest(apiFunc, options = {}) {
  const {
    immediate = false,
    defaultData = null,
    successMessage = '',
    errorMessage = '',
    showLoading = true,
    loadingText = '加载中...',
    formatter
  } = options

  // Get appStore for toast notifications
  const appStore = useAppStore()

  // 状态
  const loading = ref(false)
  const error = shallowRef(null)
  const data = shallowRef(defaultData)
  const status = ref('idle')

  // Loading 服务
  let loadingService = null

  /**
   * 执行请求
   */
  const execute = async (...args) => {
    // 开始加载
    loading.value = true
    error.value = null
    status.value = 'loading'

    // 显示 Loading
    if (showLoading) {
      loadingService = ElLoading.service({
        text: loadingText,
        fullscreen: false,
        lock: true
      })
    }

    try {
      const response = await apiFunc(...args)

      // 格式化数据
      const result = formatter ? formatter(response) : response

      data.value = result
      status.value = 'success'

      // 显示成功消息
      if (successMessage) {
        appStore.success(successMessage)
      }

      return result

    } catch (err) {
      const apiError = err.response?.data || {
        code: -1,
        message: err.message || '请求失败',
        errors: undefined
      }
      error.value = apiError
      status.value = 'error'

      // 显示错误消息
      if (errorMessage !== null) {
        const message = errorMessage || error.value?.message
        if (message) {
          appStore.error(message)
        }
      }

      return null

    } finally {
      loading.value = false
      if (loadingService) {
        loadingService.close()
        loadingService = null
      }
    }
  }

  /**
   * 重置状态
   */
  const reset = () => {
    loading.value = false
    error.value = null
    data.value = defaultData
    status.value = 'idle'
  }

  /**
   * 设置数据（手动）
   */
  const setData = (newData) => {
    data.value = newData
  }

  // 立即执行
  if (immediate) {
    execute()
  }

  return {
    // 状态
    loading,
    error,
    data,
    status,

    // 方法
    execute,
    reset,
    setData
  }
}

/**
 * useApiRequest - 简化版
 * 直接传入 URL 和方法
 */
export function useApiRequest() {
  return {
    /**
     * GET 请求
     */
    async get(url, params) {
      try {
        const response = await api.get(url, { params })
        return response
      } catch (err) {
        console.error('GET request failed:', err)
        return null
      }
    },

    /**
     * POST 请求
     */
    async post(url, data) {
      try {
        const response = await api.post(url, data)
        return response
      } catch (err) {
        console.error('POST request failed:', err)
        return null
      }
    },

    /**
     * PUT 请求
     */
    async put(url, data) {
      try {
        const response = await api.put(url, data)
        return response
      } catch (err) {
        console.error('PUT request failed:', err)
        return null
      }
    },

    /**
     * DELETE 请求
     */
    async delete(url) {
      try {
        const response = await api.delete(url)
        return response
      } catch (err) {
        console.error('DELETE request failed:', err)
        return null
      }
    }
  }
}
