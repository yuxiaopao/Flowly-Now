/**
 * 执行缓存 Composable
 * 提供执行缓存相关的功能，包括缓存统计、缓存清除等
 */

import { ref, computed } from 'vue'
import { request } from '@/utils/request'

// 缓存状态
export const cacheStats = ref({
  total: 0,
  valid: 0,
  expired: 0,
  invalid: 0,
  hit_rate: 0,
  by_node_type: []
})

// 加载状态
export const isLoading = ref(false)

// ==================== 缓存统计 ====================

/**
 * 加载缓存统计
 */
export async function loadCacheStats() {
  isLoading.value = true
  try {
    const res = await request.get('/execution-cache/stats/')
    cacheStats.value = {
      total: res.data.total,
      valid: res.data.valid,
      expired: res.data.expired,
      invalid: res.data.invalid,
      hit_rate: res.data.hit_rate,
      by_node_type: res.data.by_node_type || []
    }
    return cacheStats.value
  } catch (error) {
    console.error('Failed to load cache stats:', error)
    throw error
  } finally {
    isLoading.value = false
  }
}

// ==================== 缓存操作 ====================

/**
 * 清除所有缓存
 * @param {string} [nodeType] - 可选，按节点类型清除
 */
export async function clearCache(nodeType = null) {
  isLoading.value = true
  try {
    const params = nodeType ? { node_type: nodeType } : {}
    await request.delete('/execution-cache/', { params })
    await loadCacheStats()
    return true
  } catch (error) {
    console.error('Failed to clear cache:', error)
    throw error
  } finally {
    isLoading.value = false
  }
}

/**
 * 清理过期缓存
 */
export async function cleanupExpiredCache() {
  isLoading.value = true
  try {
    const res = await request.post('/execution-cache/cleanup/')
    await loadCacheStats()
    return res.data.cleaned
  } catch (error) {
    console.error('Failed to cleanup expired cache:', error)
    throw error
  } finally {
    isLoading.value = false
  }
}

// ==================== 缓存配置 ====================

/**
 * 获取缓存配置列表
 */
export async function getCacheConfig() {
  try {
    const res = await request.get('/cache-config/')
    return res.data
  } catch (error) {
    console.error('Failed to get cache config:', error)
    throw error
  }
}

/**
 * 更新缓存配置
 * @param {string} nodeType - 节点类型
 * @param {object} config - 配置对象 { enabled, ttl_hours, max_size_mb }
 */
export async function updateCacheConfig(nodeType, config) {
  try {
    const res = await request.patch(`/cache-config/${nodeType}/`, config)
    return res.data
  } catch (error) {
    console.error('Failed to update cache config:', error)
    throw error
  }
}

/**
 * 批量更新缓存配置
 * @param {Array} configs - 配置数组 [{ node_type, enabled, ttl_hours, max_size_mb }]
 */
export async function bulkUpdateCacheConfig(configs) {
  try {
    const res = await request.post('/cache-config/bulk_update/', { configs })
    return res.data
  } catch (error) {
    console.error('Failed to bulk update cache config:', error)
    throw error
  }
}

// ==================== Composable 函数 ====================

export function useExecutionCache() {
  // 计算属性
  const hitRatePercent = computed(() => {
    return `${cacheStats.value.hit_rate}%`
  })

  const totalEntries = computed(() => cacheStats.value.total)
  const validEntries = computed(() => cacheStats.value.valid)
  const expiredEntries = computed(() => cacheStats.value.expired)

  const entriesByType = computed(() => {
    return cacheStats.value.by_node_type || []
  })

  /**
   * 刷新缓存统计
   */
  async function refreshStats() {
    return loadCacheStats()
  }

  /**
   * 清除指定类型的缓存
   */
  async function clearCacheByType(nodeType) {
    return clearCache(nodeType)
  }

  /**
   * 清除所有缓存
   */
  async function clearAllCache() {
    return clearCache()
  }

  /**
   * 显示缓存命中指示器
   * @param {string} nodeId - 节点 ID
   * @param {boolean} isCached - 是否来自缓存
   */
  function showCachedIndicator(nodeId, isCached) {
    if (isCached) {
      console.log(`[Cache HIT] Node: ${nodeId}`)
    }
    return isCached
  }

  /**
   * 获取节点缓存状态文本
   */
  function getCacheStatusText(isCached) {
    return isCached ? '缓存命中' : '新执行'
  }

  return {
    // 状态
    cacheStats,
    isLoading,

    // 计算属性
    hitRatePercent,
    totalEntries,
    validEntries,
    expiredEntries,
    entriesByType,

    // 方法
    refreshStats,
    loadCacheStats,
    clearCache,
    clearCacheByType,
    clearAllCache,
    cleanupExpiredCache,
    getCacheConfig,
    updateCacheConfig,
    bulkUpdateCacheConfig,
    showCachedIndicator,
    getCacheStatusText
  }
}

export default useExecutionCache
