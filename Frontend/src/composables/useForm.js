/**
 * 表单验证和提交处理
 */

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'

/**
 * useFormSubmit - 表单提交处理
 * @param {Function} submitFunc - 提交函数
 * @param {Object} options - 配置
 */
export function useFormSubmit(submitFunc, options = {}) {
  const {
    validate,
    successMessage = '保存成功',
    successRedirect,
    errorRedirect,
    onSuccess,
    onError
  } = options

  // Get appStore for toast notifications
  const appStore = useAppStore()

  // 状态
  const submitting = ref(false)
  const formData = ref({})
  const errors = ref({})

  // 是否有错误
  const hasErrors = computed(() => Object.keys(errors.value).length > 0)

  /**
   * 设置表单数据
   */
  const setFormData = (data) => {
    formData.value = { ...formData.value, ...data }
  }

  /**
   * 设置单个字段错误
   */
  const setFieldError = (field, message) => {
    errors.value = { ...errors.value, [field]: message }
  }

  /**
   * 清除单个字段错误
   */
  const clearFieldError = (field) => {
    const newErrors = { ...errors.value }
    delete newErrors[field]
    errors.value = newErrors
  }

  /**
   * 清除所有错误
   */
  const clearErrors = () => {
    errors.value = {}
  }

  /**
   * 从 API 错误响应中提取字段错误
   */
  const setErrorsFromResponse = (responseErrors) => {
    const fieldErrors = {}
    for (const [field, messages] of Object.entries(responseErrors)) {
      if (Array.isArray(messages) && messages.length > 0) {
        fieldErrors[field] = messages[0]
      } else if (typeof messages === 'string') {
        fieldErrors[field] = messages
      }
    }
    errors.value = fieldErrors
  }

  /**
   * 提交表单
   */
  const submit = async (data) => {
    const submitData = data || formData.value

    // 验证
    if (validate) {
      const result = validate(submitData)
      if (result === false) {
        return false
      }
      if (typeof result === 'string') {
        appStore.error(result)
        return false
      }
    }

    submitting.value = true
    clearErrors()

    try {
      await submitFunc(submitData)

      if (successMessage) {
        appStore.success(successMessage)
      }

      if (onSuccess) {
        onSuccess(submitData)
      }

      if (successRedirect) {
        // 延迟跳转，等待用户看到成功消息
        setTimeout(() => {
          window.location.href = successRedirect
        }, 1000)
      }

      return true

    } catch (error) {
      // 从 API 响应中提取字段错误
      if (error.response?.data?.errors) {
        setErrorsFromResponse(error.response.data.errors)
      }

      if (onError) {
        onError(error)
      }

      if (errorRedirect) {
        window.location.href = errorRedirect
      }

      return false

    } finally {
      submitting.value = false
    }
  }

  /**
   * 重置表单
   */
  const reset = () => {
    formData.value = {}
    errors.value = {}
  }

  return {
    // 状态
    submitting,
    formData,
    errors,
    hasErrors,

    // 方法
    setFormData,
    setFieldError,
    clearFieldError,
    clearErrors,
    setErrorsFromResponse,
    submit,
    reset
  }
}

/**
 * useFieldValidator - 字段级验证
 */
export function useFieldValidator() {
  const error = ref('')

  /**
   * 必填验证
   */
  const required = (value, message = '此字段必填') => {
    if (value === null || value === undefined || value === '') {
      error.value = message
      return false
    }
    error.value = ''
    return true
  }

  /**
   * 最小长度验证
   */
  const minLength = (value, min, message) => {
    if (!value || value.length < min) {
      error.value = message || `最少需要 ${min} 个字符`
      return false
    }
    error.value = ''
    return true
  }

  /**
   * 最大长度验证
   */
  const maxLength = (value, max, message) => {
    if (value && value.length > max) {
      error.value = message || `最多 ${max} 个字符`
      return false
    }
    error.value = ''
    return true
  }

  /**
   * 邮箱验证
   */
  const email = (value, message = '请输入有效的邮箱地址') => {
    if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      error.value = message
      return false
    }
    error.value = ''
    return true
  }

  /**
   * URL 验证
   */
  const url = (value, message = '请输入有效的 URL') => {
    if (value && !/^https?:\/\/.+/.test(value)) {
      error.value = message
      return false
    }
    error.value = ''
    return true
  }

  /**
   * 自定义验证
   */
  const custom = (value, validator, message) => {
    if (!validator(value)) {
      error.value = message
      return false
    }
    error.value = ''
    return true
  }

  return {
    error,
    required,
    minLength,
    maxLength,
    email,
    url,
    custom
  }
}

/**
 * 常用验证规则
 */
export const validators = {
  required: (message = '此字段必填') => ({
    validator: (rule, value, callback) => {
      if (value === null || value === undefined || value === '') {
        callback(new Error(message))
      } else {
        callback()
      }
    },
    trigger: ['blur', 'change']
  }),

  minLength: (min, message) => ({
    validator: (rule, value, callback) => {
      if (value && value.length < min) {
        callback(new Error(message || `最少需要 ${min} 个字符`))
      } else {
        callback()
      }
    },
    trigger: ['blur', 'change']
  }),

  maxLength: (max, message) => ({
    validator: (rule, value, callback) => {
      if (value && value.length > max) {
        callback(new Error(message || `最多 ${max} 个字符`))
      } else {
        callback()
      }
    },
    trigger: ['blur', 'change']
  }),

  email: (message = '请输入有效的邮箱地址') => ({
    validator: (rule, value, callback) => {
      if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        callback(new Error(message))
      } else {
        callback()
      }
    },
    trigger: ['blur', 'change']
  }),

  url: (message = '请输入有效的 URL') => ({
    validator: (rule, value, callback) => {
      if (value && !/^https?:\/\/.+/.test(value)) {
        callback(new Error(message))
      } else {
        callback()
      }
    },
    trigger: ['blur', 'change']
  }),

  pattern: (regex, message) => ({
    validator: (rule, value, callback) => {
      if (value && !regex.test(value)) {
        callback(new Error(message))
      } else {
        callback()
      }
    },
    trigger: ['blur', 'change']
  })
}
