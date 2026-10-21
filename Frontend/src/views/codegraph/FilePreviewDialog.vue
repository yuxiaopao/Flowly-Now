<template>
  <el-dialog
    v-model="visible"
    title="文件预览"
    :width="CODE_GRAPH.previewWidth"
    :before-close="handleClose"
    @opened="scrollToHighlight"
  >
    <div
      v-if="filePath"
      class="file-preview-content"
    >
      <div class="preview-header">
        <span class="file-name">{{ filePath }}</span>
        <span
          v-if="highlightLine"
          class="line-hint"
        >定位第 {{ highlightLine }} 行</span>
      </div>
      <div
        ref="bodyEl"
        class="preview-body"
      >
        <div
          v-if="loading"
          class="no-file"
        >
          加载中...
        </div>
        <div
          v-else-if="error"
          class="no-file"
          role="alert"
        >
          <p>{{ error }}</p>
          <el-button @click="loadPreview(filePath)">
            {{ CODE_GRAPH.messages.retry }}
          </el-button>
        </div>
        <div
          v-else
          class="code-preview"
        >
          <div
            v-for="(line, idx) in lines"
            :id="`cg-line-${idx + 1}`"
            :key="idx"
            class="code-line"
            :class="{ highlight: highlightLine === idx + 1 }"
          >
            <span class="ln">{{ idx + 1 }}</span>
            <span class="lc">{{ line || ' ' }}</span>
          </div>
        </div>
      </div>
    </div>
    <div
      v-else
      class="no-file"
    >
      暂无预览内容
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { getFileContent } from '@/api/codegraph'
import { CODE_GRAPH } from '@/config/codeGraph'
import { graphError } from '@/utils/codeGraph'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  filePath: {
    type: String,
    default: ''
  },
  projectId: {
    type: [String, Number],
    default: null
  },
  highlightLine: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const previewContent = ref('')
const loading = ref(false)
const error = ref('')
const bodyEl = ref(null)
let requestSeq = 0
let controller = null

const lines = computed(() => (previewContent.value || '').split('\n'))

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (val) scrollToHighlight()
})

async function loadPreview(path) {
  const seq = ++requestSeq
  controller?.abort()
  previewContent.value = ''
  error.value = ''
  loading.value = false
  if (!path || !props.projectId) {
    return
  }

  controller = new AbortController()
  loading.value = true
  try {
    const data = await getFileContent(props.projectId, path, { signal: controller.signal })
    if (seq !== requestSeq) return
    previewContent.value = data?.content ?? data?.source ?? data?.text ?? ''
  } catch (err) {
    if (seq === requestSeq && err.code !== 'ERR_CANCELED') error.value = graphError(err, CODE_GRAPH.messages.previewFailed)
  } finally {
    if (seq === requestSeq) {
      loading.value = false
      await scrollToHighlight()
    }
  }
}

async function scrollToHighlight() {
  await nextTick()
  const line = Number(props.highlightLine)
  if (!line || !visible.value) return
  const el = bodyEl.value?.querySelector(`#cg-line-${line}`)
  el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

watch(
  () => [props.filePath, props.projectId, props.modelValue],
  ([path, , open]) => {
    if (open) loadPreview(path)
    else {
      ++requestSeq
      controller?.abort()
      loading.value = false
    }
  },
  { immediate: true }
)

watch(() => props.highlightLine, () => {
  scrollToHighlight()
})

function handleClose() {
  visible.value = false
}

onUnmounted(() => {
  ++requestSeq
  controller?.abort()
})
</script>

<style scoped>
.file-preview-content {
  height: 60vh;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  margin-bottom: 12px;
}

.file-name {
  min-width: 0;
  overflow-wrap: anywhere;
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.line-hint {
  font-size: 12px;
  color: #22d3ee;
  flex-shrink: 0;
}

.preview-body {
  flex: 1;
  overflow: auto;
}

.code-preview {
  padding: 8px 0;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.55;
  overflow: auto;
  max-height: 50vh;
}

.code-line {
  display: flex;
  gap: 12px;
  padding: 0 12px;
  min-height: 1.55em;
}

.code-line.highlight {
  background: rgba(34, 211, 238, 0.14);
  outline: 1px solid rgba(34, 211, 238, 0.28);
}

.ln {
  width: 42px;
  flex-shrink: 0;
  text-align: right;
  color: var(--text-tertiary);
  user-select: none;
}

.lc {
  white-space: pre;
  color: var(--text-primary);
}

.no-file {
  text-align: center;
  color: var(--text-tertiary);
  padding: 40px;
}
</style>
