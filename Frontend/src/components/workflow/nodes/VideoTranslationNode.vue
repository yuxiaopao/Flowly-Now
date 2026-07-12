<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    class="domain-node video-translation-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle type="target" :position="Position.Left" />

    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" />
      <button class="action-btn" @click.stop="toggleExpand">
        <ChevronDown class="action-icon" :class="{ rotated: isExpanded }" />
      </button>
    </div>

    <div class="node-name-section">
      <input
        :id="id ? `node-label-${id}` : undefined"
        name="node-label"
        v-model="localName"
        class="node-name-input"
        placeholder="视频翻译..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div class="info-row">
        <span class="info-label">语言</span>
        <span class="info-value">{{ localConfig.source_language || 'zh' }} → {{ targetLabel }}</span>
      </div>
      <div v-if="stepLabel" class="info-row">
        <span class="info-label">进度</span>
        <span class="info-value">{{ stepLabel }}</span>
      </div>
      <div class="status-bar" :class="{ running: isRunning, completed: isCompleted, failed: isFailed }">
        <div v-if="isRunning" class="status-running">
          <Loader class="status-icon spinning" />
          <span>{{ stepLabel || '处理中...' }}</span>
        </div>
        <div v-else-if="isCompleted" class="status-done">
          <span class="status-dot" />
          <span>{{ lipSyncLabel }}</span>
        </div>
        <div v-else-if="isFailed" class="status-error">
          <span class="status-dot" />
          <span>{{ outputError || '失败' }}</span>
        </div>
      </div>
    </div>

    <div v-if="videoUrl && (isCompleted || showPreview)" class="preview-zone">
      <NodeMediaPreview kind="video" :src="videoUrl" />
    </div>

    <Handle type="source" :position="Position.Right" />

    <div
      class="resize-handle"
      title="拖动调整节点大小"
      @pointerdown.stop="(e) => resize.startResize(e, rootEl?.offsetWidth, rootEl?.offsetHeight)"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { ChevronDown, Loader } from 'lucide-vue-next'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import NodeMediaPreview from '@/components/workflow/nodes/NodeMediaPreview.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'
import { useExecutionStore } from '@/stores/execution'
import { extractVideoUrl } from '@/utils/nodeMediaOutput'

const NODE_TYPE = 'video_translation'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'update'])

const { nodeColor } = useNodePresentation(NODE_TYPE)
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 240,
  minHeight: 160,
  maxWidth: 720,
  maxHeight: 900,
})

const isExpanded = ref(false)
const showPreview = ref(true)

const defaultConfig = () => ({
  source_language: 'zh',
  target_languages: ['en'],
  lip_sync: true,
  burn_subtitles: true,
  subtitle_format: 'srt',
  video_input: '{video_url}',
  inputMode: 'upstream',
  provider: 'dashscope',
})

const localName = ref(props.data.label || '视频翻译')
const localConfig = ref({
  ...defaultConfig(),
  ...(props.data.config || {}),
})

watch(
  () => props.data,
  (data) => {
    if (!data) return
    localName.value = data.label || '视频翻译'
    localConfig.value = {
      ...defaultConfig(),
      ...(data.config || {}),
    }
  },
  { deep: true },
)

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const outputError = computed(() => {
  const state = executionStore.nodeStatusDetails?.[props.id]
  return state?.error || state?.error_message || state?.message || ''
})

const videoUrl = computed(() => extractVideoUrl(nodeOutput.value))

const targetLabel = computed(() => {
  const langs = localConfig.value.target_languages || localConfig.value.targetLanguages || ['en']
  return Array.isArray(langs) ? langs.join(', ') : langs
})

const stepLabel = computed(() => {
  const step = nodeOutput.value?.video_translation_step
  const map = {
    resolve_input: '解析输入',
    transcribe: '语音识别',
    translate: '翻译字幕',
    synthesize: '合成配音',
    lip_sync: '口型同步',
    burn_subtitles: '烧录字幕',
    finalize: '完成',
  }
  return map[step] || step || ''
})

const lipSyncLabel = computed(() => {
  if (nodeOutput.value?.lip_sync_applied === false) return '已完成（无口型同步）'
  if (nodeOutput.value?.lip_sync_applied) return '已完成（口型已同步）'
  return '已完成'
})

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
</script>

<style scoped>
.video-translation-node {
  min-width: 220px;
  background: var(--node-bg, #fff);
  border: 1.5px solid color-mix(in srgb, var(--node-accent) 35%, #e2e8f0);
  border-radius: 12px;
  padding: 10px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}
.info-row { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; margin-bottom: 6px; }
.info-label { color: #64748b; }
.info-value { color: #0f172a; font-weight: 600; text-align: right; }
.status-bar { margin-top: 8px; font-size: 12px; }
.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 6px; }
.status-icon { width: 14px; height: 14px; }
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.preview-zone { margin-top: 8px; border-radius: 8px; overflow: hidden; }
</style>
