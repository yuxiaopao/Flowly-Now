<template>
  <el-dialog
    v-model="visible"
    :title="filePath"
    width="80%"
    top="5vh"
    class="file-preview-dialog"
  >
    <div
      v-if="loading"
      class="loading-state"
    >
      <el-icon class="is-loading">
        <Loading />
      </el-icon>
      <span>加载中...</span>
    </div>

    <div
      v-else-if="error"
      class="error-state"
    >
      <el-empty :description="error" />
    </div>

    <div
      v-else
      class="file-content"
    >
      <div class="content-header">
        <el-tag size="small">
          {{ fileData?.extension }}
        </el-tag>
        <span class="file-info">
          {{ fileData?.lines }} 行 | {{ formatSize(fileData?.size || 0) }}
        </span>
      </div>

      <div class="code-container">
        <pre class="code-pre"><code class="code-block">{{ fileData?.content }}</code></pre>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">
        关闭
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Loading } from '@element-plus/icons-vue'

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
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const store = useCodeGraphStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const error = ref(null)
const fileData = ref(null)

watch(() => [props.modelValue, props.filePath], async ([newVisible, newPath]) => {
  if (newVisible && newPath) {
    await loadFileContent(newPath)
  }
}, { immediate: true })

async function loadFileContent(path) {
  loading.value = true
  error.value = null
  fileData.value = null

  try {
    const content = await store.fetchFileContent(path)
    if (content) {
      fileData.value = content
    } else {
      error.value = '无法加载文件内容'
    }
  } catch (err) {
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function formatSize(bytes) {
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }
  if (bytes >= 1024) {
    return (bytes / 1024).toFixed(1) + ' KB'
  }
  return bytes + ' B'
}
</script>

<style lang="scss" scoped>
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-secondary);
}

.file-content {
  display: flex;
  flex-direction: column;
  height: 70vh;
}

.content-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 12px;

  .file-info {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.code-container {
  flex: 1;
  overflow: auto;
  background: var(--bg-primary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.code-pre {
  margin: 0;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.code-block {
  color: var(--text-primary);
}
</style>
