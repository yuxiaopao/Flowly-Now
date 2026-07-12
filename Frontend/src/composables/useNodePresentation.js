import { computed, unref } from 'vue'
import { getNodeMeta } from '@/config/nodeRegistry'
import { getIntegrationMeta } from '@/config/integrations'

/**
 * 从 nodeRegistry 读取节点图标、品牌色、标签（画布与侧栏单一数据源）
 * @param {import('vue').MaybeRef<string>} nodeType
 */
export function useNodePresentation(nodeType) {
  const meta = computed(() => {
    const type = unref(nodeType)
    if (!type) return null
    return getNodeMeta(type) || null
  })

  const integrationMeta = computed(() => {
    const type = unref(nodeType)
    if (!type) return null
    return getIntegrationMeta(type)
  })

  const nodeIcon = computed(() => meta.value?.icon || null)
  const nodeColor = computed(() => {
    if (integrationMeta.value?.brandColor) {
      return integrationMeta.value.brandColor
    }
    return meta.value?.color || '#6366f1'
  })
  const nodeLabel = computed(() => meta.value?.label || integrationMeta.value?.label || unref(nodeType) || '')
  const nodeDescription = computed(() => meta.value?.description || integrationMeta.value?.description || '')

  return {
    meta,
    integrationMeta,
    nodeIcon,
    nodeColor,
    nodeLabel,
    nodeDescription,
  }
}
