<template>
  <el-dialog
    v-model="visible"
    title="文件预览"
    width="80%"
    :before-close="handleClose"
  >
    <div
      v-if="filePath"
      class="file-preview-content"
    >
      <div class="preview-header">
        <span class="file-name">{{ filePath }}</span>
      </div>
      <div class="preview-body">
        <div
          v-if="loading"
          class="no-file"
        >
          加载中...
        </div>
        <pre
          v-else
          class="code-preview"
        >{{ previewContent }}</pre>
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
import { ref, watch } from 'vue'
import { getFileContent } from '@/api/codegraph'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

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
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const previewContent = ref('')
const loading = ref(false)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

async function loadPreview(path) {
  if (!path || !props.projectId) {
    previewContent.value = path ? `// 未选择项目，无法加载: ${path}` : ''
    return
  }

  loading.value = true
  try {
    const data = await getFileContent(props.projectId, path)
    previewContent.value = data?.content || data?.source || data?.text || String(data || '')
  } catch (err) {
    console.error('Failed to load file preview:', err)
    previewContent.value = `// 加载失败: ${path}`
    appStore.error('文件预览加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.filePath, props.projectId],
  ([path]) => {
    if (path) loadPreview(path)
  },
  { immediate: true }
)

function handleClose() {
  visible.value = false
}
</script>

<style scoped>
.file-preview-content {
  height: 60vh;
  display: flex;
  flex-direction: column;
}

.preview-header {
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  margin-bottom: 12px;
}

.file-name {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.preview-body {
  flex: 1;
  overflow: auto;
}

.code-preview {
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow: auto;
  max-height: 50vh;
}

.no-file {
  text-align: center;
  color: var(--text-tertiary);
  padding: 40px;
}
</style>
