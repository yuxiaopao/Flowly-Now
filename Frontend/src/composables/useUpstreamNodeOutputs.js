/**
 * Resolve upstream node execution outputs on the canvas (via edges + execution store).
 */
import { computed, unref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { storeToRefs } from 'pinia'
import { useExecutionStore } from '@/stores/execution'
import { unwrapNodeExecutionOutput } from '@/utils/workflowTransform'

function firstImageUrl(output) {
  if (!output || typeof output !== 'object') return null
  const images = output.images
  if (Array.isArray(images) && images.length) {
    const first = images[0]
    if (typeof first === 'string') return first
    if (first?.url) return first.url
  }
  return output.url || output.image_url || output.imageUrl || null
}

function firstVideoUrl(output) {
  if (!output || typeof output !== 'object') return null
  return output.video_url || output.videoUrl || output.url || null
}

export function useUpstreamNodeOutputs(nodeId, { sourceTypes = [] } = {}) {
  const { getEdges, getNodes } = useVueFlow()
  const executionStore = useExecutionStore()
  const { nodeOutputs } = storeToRefs(executionStore)

  const resolvedNodeId = computed(() => unref(nodeId))

  const upstreamSources = computed(() => {
    const id = resolvedNodeId.value
    if (!id) return []
    const edges = getEdges.value || []
    const nodes = getNodes.value || []
    return edges
      .filter((edge) => edge.target === id)
      .map((edge) => nodes.find((node) => node.id === edge.source))
      .filter(Boolean)
  })

  const upstreamImageUrl = computed(() => {
    for (const source of upstreamSources.value) {
      const type = source.type || source.data?.type
      if (sourceTypes.length && !sourceTypes.includes(type)) continue
      const output = unwrapNodeExecutionOutput(nodeOutputs.value[source.id])
      const url = firstImageUrl(output)
      if (url) return url
    }
    return null
  })

  const upstreamPrompt = computed(() => {
    for (const source of upstreamSources.value) {
      const type = source.type || source.data?.type
      if (type !== 'input') continue
      const output = unwrapNodeExecutionOutput(nodeOutputs.value[source.id])
      if (!output || typeof output !== 'object') continue
      const value = output.prompt || output.user_input || output.userInput || output.input
      if (value) return String(value)
    }
    return null
  })

  const upstreamVideoUrl = computed(() => {
    for (const source of upstreamSources.value) {
      const type = source.type || source.data?.type
      if (sourceTypes.length && !sourceTypes.includes(type)) continue
      const output = unwrapNodeExecutionOutput(nodeOutputs.value[source.id])
      const url = firstVideoUrl(output)
      if (url) return url
    }
    return null
  })

  return {
    upstreamSources,
    upstreamImageUrl,
    upstreamVideoUrl,
    upstreamPrompt,
  }
}

export function resolveDirectMediaUrl(value) {
  const raw = String(value || '').trim()
  if (!raw) return null
  if (/^https?:\/\//i.test(raw) || raw.startsWith('data:') || raw.startsWith('/media/')) {
    return raw
  }
  return null
}
