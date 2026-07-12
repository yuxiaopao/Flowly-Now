/**
 * 表单验证工具
 * 提供常用的验证函数和验证规则
 */

/**
 * 验证规则集合
 */
export const rules = {
  /**
   * 必填验证
   */
  required: (message = '此字段为必填项') => ({
    required: true,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 邮箱验证
   */
  email: (message = '请输入正确的邮箱格式') => ({
    type: 'email',
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * URL 验证
   */
  url: (message = '请输入正确的 URL 格式') => ({
    pattern: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 手机号验证（中国大陆）
   */
  phone: (message = '请输入正确的手机号') => ({
    pattern: /^1[3-9]\d{9}$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 身份证验证（中国大陆）
   */
  idCard: (message = '请输入正确的身份证号') => ({
    pattern: /^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 最小长度验证
   */
  minLength: (min, message) => ({
    min,
    message: message || `长度不能少于 ${min} 个字符`,
    trigger: ['blur', 'change']
  }),

  /**
   * 最大长度验证
   */
  maxLength: (max, message) => ({
    max,
    message: message || `长度不能超过 ${max} 个字符`,
    trigger: ['blur', 'change']
  }),

  /**
   * 长度范围验证
   */
  lengthRange: (min, max, message) => ({
    min,
    max,
    message: message || `长度应在 ${min} 到 ${max} 个字符之间`,
    trigger: ['blur', 'change']
  }),

  /**
   * 最小值验证
   */
  min: (value, message) => ({
    min: value,
    message: message || `值不能小于 ${value}`,
    trigger: ['blur', 'change']
  }),

  /**
   * 最大值验证
   */
  max: (value, message) => ({
    max: value,
    message: message || `值不能大于 ${value}`,
    trigger: ['blur', 'change']
  }),

  /**
   * 数字验证
   */
  number: (message = '请输入数字') => ({
    pattern: /^\d+$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 正整数验证
   */
  positiveInteger: (message = '请输入正整数') => ({
    pattern: /^[1-9]\d*$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 整数验证
   */
  integer: (message = '请输入整数') => ({
    pattern: /^-?\d+$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 浮点数验证
   */
  float: (message = '请输入小数') => ({
    pattern: /^-?\d+(\.\d+)?$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 密码强度验证
   * 至少包含数字、字母、特殊字符，长度 8-32
   */
  password: (message = '密码需包含数字、字母和特殊字符，长度 8-32 位') => ({
    pattern: /^(?=.*[0-9])(?=.*[a-zA-Z])(?=.*[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]).{8,32}$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 简单密码验证（至少 6 位）
   */
  simplePassword: (message = '密码长度至少 6 位') => ({
    min: 6,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 用户名验证（字母、数字、下划线，3-20 位）
   */
  username: (message = '用户名只能包含字母、数字和下划线，长度 3-20 位') => ({
    pattern: /^[a-zA-Z0-9_]{3,20}$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 中文验证
   */
  chinese: (message = '只能输入中文') => ({
    pattern: /^[\u4e00-\u9fa5]+$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 英文验证
   */
  english: (message = '只能输入英文') => ({
    pattern: /^[a-zA-Z]+$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * IP 地址验证
   */
  ip: (message = '请输入正确的 IP 地址') => ({
    pattern: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 端口号验证
   */
  port: (message = '请输入正确的端口号 (1-65535)') => ({
    pattern: /^([1-9]\d{0,3}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5])$/,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * JSON 格式验证
   */
  json: (message = '请输入有效的 JSON 格式') => ({
    validator: (rule, value, callback) => {
      if (!value) {
        callback()
        return
      }
      try {
        JSON.parse(value)
        callback()
      } catch (e) {
        callback(new Error(message))
      }
    },
    trigger: ['blur', 'change']
  }),

  /**
   * 自定义正则验证
   */
  pattern: (regex, message = '格式不正确') => ({
    pattern: regex,
    message,
    trigger: ['blur', 'change']
  }),

  /**
   * 自定义函数验证
   */
  validator: (validatorFn, message = '验证失败') => ({
    validator: (rule, value, callback) => {
      const result = validatorFn(value)
      if (result === true) {
        callback()
      } else {
        callback(new Error(typeof result === 'string' ? result : message))
      }
    },
    trigger: ['blur', 'change']
  })
}

/**
 * 验证器类
 */
class Validator {
  constructor() {
    this.errors = {}
  }

  /**
   * 验证单个字段
   */
  validate(field, value, fieldRules) {
    this.errors[field] = []

    for (const rule of fieldRules) {
      // 必填验证
      if (rule.required && (value === undefined || value === null || value === '')) {
        this.errors[field].push(rule.message || '此字段为必填项')
        continue
      }

      // 如果值为空且不是必填，跳过其他验证
      if (value === undefined || value === null || value === '') {
        continue
      }

      // 最小长度
      if (rule.min !== undefined && String(value).length < rule.min) {
        this.errors[field].push(rule.message || `长度不能少于 ${rule.min} 个字符`)
      }

      // 最大长度
      if (rule.max !== undefined && String(value).length > rule.max) {
        this.errors[field].push(rule.message || `长度不能超过 ${rule.max} 个字符`)
      }

      // 正则验证
      if (rule.pattern && !rule.pattern.test(String(value))) {
        this.errors[field].push(rule.message || '格式不正确')
      }

      // 自定义验证器
      if (rule.validator) {
        const result = rule.validator(value)
        if (result !== true) {
          this.errors[field].push(typeof result === 'string' ? result : (rule.message || '验证失败'))
        }
      }

      // 邮箱验证
      if (rule.type === 'email') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(value)) {
          this.errors[field].push(rule.message || '请输入正确的邮箱格式')
        }
      }
    }

    return this.errors[field].length === 0
  }

  /**
   * 验证多个字段
   */
  validateAll(data, schema) {
    let isValid = true

    for (const [field, fieldRules] of Object.entries(schema)) {
      const value = data[field]
      if (!this.validate(field, value, fieldRules)) {
        isValid = false
      }
    }

    return isValid
  }

  /**
   * 获取错误信息
   */
  getErrors() {
    return this.errors
  }

  /**
   * 获取第一个错误
   */
  getFirstError() {
    for (const errors of Object.values(this.errors)) {
      if (errors.length > 0) {
        return errors[0]
      }
    }
    return null
  }

  /**
   * 是否有错误
   */
  hasErrors() {
    return Object.values(this.errors).some(errors => errors.length > 0)
  }

  /**
   * 清除错误
   */
  clear() {
    this.errors = {}
  }
}

/**
 * 创建验证器实例
 */
export function createValidator() {
  return new Validator()
}

/**
 * 常用验证函数
 */
export const validators = {
  /**
   * 验证邮箱
   */
  isEmail(value) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(value)
  },

  /**
   * 验证手机号
   */
  isPhone(value) {
    const phoneRegex = /^1[3-9]\d{9}$/
    return phoneRegex.test(value)
  },

  /**
   * 验证 URL
   */
  isUrl(value) {
    const urlRegex = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$/
    return urlRegex.test(value)
  },

  /**
   * 验证是否为空
   */
  isEmpty(value) {
    return value === undefined || value === null || value === ''
  },

  /**
   * 验证是否为数字
   */
  isNumber(value) {
    return !isNaN(parseFloat(value)) && isFinite(value)
  },

  /**
   * 验证整数
   */
  isInteger(value) {
    return /^-?\d+$/.test(value)
  },

  /**
   * 验证 JSON
   */
  isJson(value) {
    try {
      JSON.parse(value)
      return true
    } catch {
      return false
    }
  },

  /**
   * 验证工作流节点名称
   */
  isValidNodeName(value) {
    if (!value || value.trim().length === 0) return '节点名称不能为空'
    if (value.length > 50) return '节点名称不能超过 50 个字符'
    return true
  },

  /**
   * 验证工作流名称
   */
  isValidWorkflowName(value) {
    if (!value || value.trim().length === 0) return '工作流名称不能为空'
    if (value.length > 100) return '工作流名称不能超过 100 个字符'
    return true
  },

  /**
   * 验证 API Key
   */
  isValidApiKey(value) {
    if (!value || value.trim().length === 0) return 'API Key 不能为空'
    if (value.length < 10) return 'API Key 格式不正确'
    return true
  }
}

/**
 * 验证工作流
 */
export function validateWorkflow(workflow) {
  const errors = []

  // 验证工作流名称
  const nameResult = validators.isValidWorkflowName(workflow.name)
  if (nameResult !== true) {
    errors.push({ field: 'name', message: nameResult })
  }

  // 验证节点
  if (!workflow.nodes || workflow.nodes.length === 0) {
    errors.push({ field: 'nodes', message: '工作流必须包含至少一个节点' })
  }

  // 检查开始和结束节点
  const nodeTypes = workflow.nodes?.map(n => n.type) || []
  if (!nodeTypes.includes('start')) {
    errors.push({ field: 'nodes', message: '工作流必须包含开始节点' })
  }
  if (!nodeTypes.includes('end')) {
    errors.push({ field: 'nodes', message: '工作流必须包含结束节点' })
  }

  // 验证连线
  if (!workflow.edges || workflow.edges.length === 0) {
    errors.push({ field: 'edges', message: '工作流必须包含至少一条连线' })
  }

  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * 验证节点配置
 */
export function validateNodeConfig(node) {
  const errors = []

  // 验证节点名称
  const nameResult = validators.isValidNodeName(node.data?.label)
  if (nameResult !== true) {
    errors.push({ field: 'label', message: nameResult })
  }

  // 根据节点类型验证配置
  switch (node.type) {
    case 'llm':
      if (!node.data?.config?.model) {
        errors.push({ field: 'model', message: '请选择模型' })
      }
      break

    case 'http':
      if (!node.data?.config?.url) {
        errors.push({ field: 'url', message: '请输入请求地址' })
      }
      if (node.data?.config?.url && !validators.isUrl(node.data.config.url)) {
        errors.push({ field: 'url', message: '请输入正确的 URL' })
      }
      break

    case 'code':
      if (!node.data?.config?.code) {
        errors.push({ field: 'code', message: '请输入代码' })
      }
      break

    case 'prompt':
      if (!node.data?.config?.template) {
        errors.push({ field: 'template', message: '请输入提示词模板' })
      }
      break
  }

  return {
    valid: errors.length === 0,
    errors
  }
}

export default {
  rules,
  Validator,
  createValidator,
  validators,
  validateWorkflow,
  validateNodeConfig
}
