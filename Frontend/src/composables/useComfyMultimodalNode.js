import { ref, watch, computed } from 'vue'
import { useVueFlow, useNodeId } from '@vue-flow/core'
import { useExecutionStore } from '@/stores/execution'

/**
 * ComfyUI 风格多模态节点共用逻辑：名称/配置同步、执行态、展开交互
 */
export function useComfyMultimodalNode(props, emit, options = {}) {
  const {
    defaultLabel = '节点',
    defaultConfig = () => ({}),
    mergeConfig = (config) => config || {},
  } = options

  const { updateNodeData } = useVueFlow()
  const flowNodeId = useNodeId()
  const executionStore = useExecutionStore()

  const isExpanded = ref(false)
  const nodeKey = computed(() => flowNodeId || props.id || '')

  const localName = ref(props.data.label || defaultLabel)
  const localConfig = ref({
    ...defaultConfig(),
    ...mergeConfig(props.data.config),
  })

  const nodeStatus = computed(() => {
    void executionStore.executionStatus
    return executionStore.nodeStatusMap[nodeKey.value]
  })
  const nodeOutput = computed(() => {
    void executionStore.executionStatus
    return executionStore.nodeOutputs[nodeKey.value]
  })

  const isRunning = computed(() => nodeStatus.value === 'running')
  const isCompleted = computed(() => nodeStatus.value === 'completed')
  const isFailed = computed(() => nodeStatus.value === 'failed')

  watch(
    () => props.data,
    (data) => {
      if (!data) return
      localName.value = data.label || defaultLabel
      localConfig.value = {
        ...defaultConfig(),
        ...mergeConfig(data.config),
      }
    },
    { deep: true },
  )

  function toggleExpand() {
    isExpanded.value = !isExpanded.value
  }

  function handleChange() {
    if (!props.id) return
    updateNodeData(props.id, {
      label: localName.value,
      config: { ...localConfig.value },
    })
  }

  function handleSelect() {
    emit('select')
    if (!isExpanded.value) isExpanded.value = true
  }

  function truncate(str, len = 40) {
    if (!str) return ''
    return str.length > len ? `${str.slice(0, len)}…` : str
  }

  return {
    isExpanded,
    localName,
    localConfig,
    nodeStatus,
    nodeOutput,
    isRunning,
    isCompleted,
    isFailed,
    toggleExpand,
    handleChange,
    handleSelect,
    truncate,
  }
}
