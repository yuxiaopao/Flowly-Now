/**
 * 格式化工具函数
 */

/**
 * 格式化日期
 * @param {string|Date} date - 日期
 * @param {string} locale - 区域设置
 * @returns {string}
 */
export function formatDate(date, locale = 'zh-CN') {
  if (!date) return ''
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  
  return d.toLocaleDateString(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

/**
 * 格式化日期时间
 * @param {string|Date} date - 日期
 * @param {string} locale - 区域设置
 * @returns {string}
 */
export function formatDateTime(date, locale = 'zh-CN') {
  if (!date) return ''
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  
  return d.toLocaleString(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 格式化相对时间
 * @param {string|Date} date - 日期
 * @returns {string}
 */
export function formatRelativeTime(date) {
  if (!date) return ''
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  
  const now = new Date()
  const diff = now - d
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `${days} 天前`
  if (hours > 0) return `${hours} 小时前`
  if (minutes > 0) return `${minutes} 分钟前`
  if (seconds > 10) return `${seconds} 秒前`
  return '刚刚'
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化数字
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数
 * @returns {string}
 */
export function formatNumber(num, decimals = 0) {
  if (num === null || num === undefined) return ''
  return Number(num).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

/**
 * 格式化百分比
 * @param {number} value - 值 (0-1)
 * @param {number} decimals - 小数位数
 * @returns {string}
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined) return ''
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * 格式化时长
 * @param {number} ms - 毫秒
 * @returns {string}
 */
export function formatDuration(ms) {
  if (!ms || ms < 0) return '0ms'
  
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `${days}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${minutes % 60}m`
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`
  if (seconds > 0) return `${seconds}s`
  return `${ms}ms`
}

/**
 * 截断文本
 * @param {string} text - 文本
 * @param {number} maxLength - 最大长度
 * @param {string} suffix - 后缀
 * @returns {string}
 */
export function truncateText(text, maxLength = 50, suffix = '...') {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength - suffix.length) + suffix
}

/**
 * 格式化货币
 * @param {number} amount - 金额
 * @param {string} currency - 货币代码
 * @returns {string}
 */
export function formatCurrency(amount, currency = 'CNY') {
  if (amount === null || amount === undefined) return ''
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency
  }).format(amount)
}

export default {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  formatFileSize,
  formatNumber,
  formatPercent,
  formatDuration,
  truncateText,
  formatCurrency
}
