<template>
  <section class="output-viewer">
    <div class="output-viewer__header">
      <h4>输出查看</h4>
      <div class="output-viewer__tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span class="tab-count">{{ tab.count }}</span>
        </button>
      </div>
    </div>

    <div
      v-if="currentList.length === 0"
      class="output-viewer__empty"
    >
      {{ emptyHint }}
    </div>

    <div
      v-else
      class="output-viewer__body"
    >
      <aside class="file-list">
        <button
          v-for="item in currentList"
          :key="item.key || item.id"
          type="button"
          class="file-item"
          :class="{ active: selectedId === (item.key || item.id) }"
          @click="selectItem(item)"
        >
          <span class="file-title">{{ item.title }}</span>
          <span
            v-if="item.nodeName"
            class="file-node"
          >{{ item.nodeName }}</span>
        </button>
      </aside>

      <div class="preview-pane">
        <div class="preview-toolbar">
          <span class="preview-name">{{ selected?.title }}</span>
          <div class="preview-actions">
            <button
              v-if="canCopy"
              type="button"
              class="tool-btn"
              @click="copySelected"
            >
              复制
            </button>
            <button
              v-if="canDownload"
              type="button"
              class="tool-btn"
              @click="downloadSelected"
            >
              下载
            </button>
          </div>
        </div>

        <div
          v-if="activeTab === 'documents' && selected?.kind === 'docx'"
          class="preview-docx"
        >
          <p>Word 已写入服务器路径：</p>
          <code>{{ selected.path }}</code>
          <p class="hint">
            这是可二次编辑的 .docx。当前浏览器无法内嵌预览 Office 文件，请从运行环境打开该路径。
          </p>
          <pre
            v-if="selected.content"
            class="preview-code"
          >{{ selected.content }}</pre>
        </div>

        <div
          v-else-if="activeTab === 'documents'"
          class="preview-markdown markdown-body"
          v-html="markdownHtml"
        />

        <pre
          v-else-if="activeTab === 'codes'"
          class="preview-code"
        >{{ selected?.content || '' }}</pre>

        <div
          v-else-if="activeTab === 'images'"
          class="preview-image-wrap"
        >
          <img
            v-if="selected?.url"
            :src="selected.url"
            :alt="selected.title"
            class="preview-image"
            @click="lightbox = selected.url"
          >
        </div>
      </div>
    </div>

    <div
      v-if="lightbox"
      class="lightbox"
      @click="lightbox = ''"
    >
      <img
        :src="lightbox"
        alt="预览大图"
      >
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { renderMarkdown } from '@/utils/markdown'
import { collectExecutionOutputs } from '@/utils/executionOutputViewer'

const props = defineProps({
  nodeStatus: { type: Object, default: () => ({}) },
  workflowNodes: { type: Array, default: () => [] },
  outputData: { type: [Object, String, null], default: null },
})

const appStore = useAppStore()
const activeTab = ref('documents')
const selectedId = ref('')
const lightbox = ref('')

const bundle = computed(() => collectExecutionOutputs({
  nodeStatus: props.nodeStatus,
  workflowNodes: props.workflowNodes,
  outputData: props.outputData,
}))

const tabs = computed(() => [
  { id: 'documents', label: '文档', count: bundle.value.totals.documents },
  { id: 'codes', label: '代码', count: bundle.value.totals.codes },
  { id: 'images', label: '图片', count: bundle.value.totals.images },
])

const currentList = computed(() => {
  if (activeTab.value === 'codes') return bundle.value.codes
  if (activeTab.value === 'images') return bundle.value.images
  return bundle.value.documents
})

const selected = computed(() =>
  currentList.value.find((item) => (item.key || item.id) === selectedId.value) || currentList.value[0] || null
)

const markdownHtml = computed(() => renderMarkdown(selected.value?.content || ''))
const canCopy = computed(() => Boolean(selected.value?.content || selected.value?.path || selected.value?.url))
const canDownload = computed(() => Boolean(selected.value?.content || selected.value?.url))

const emptyHint = computed(() => {
  if (activeTab.value === 'codes') return '暂无代码文件。工作流中的 code 节点源码会在加载后出现。'
  if (activeTab.value === 'images') return '暂无图片。图表节点执行完成后会显示在这里。'
  return '暂无输出文档。论文 Markdown / Word / 表格会在对应节点完成后出现。'
})

function preferredTab(b) {
  if (b.images.length && !b.documents.length) return 'images'
  if (b.documents.length) return 'documents'
  if (b.images.length) return 'images'
  if (b.codes.length) return 'codes'
  return 'documents'
}

watch(
  () => Object.keys(props.nodeStatus || {}).sort().join('|'),
  () => {
    activeTab.value = preferredTab(bundle.value)
  },
  { immediate: true },
)

watch(
  [currentList, activeTab],
  ([list]) => {
    if (!list.length) {
      selectedId.value = ''
      return
    }
    if (!list.some((item) => (item.key || item.id) === selectedId.value)) {
      selectedId.value = list[0].key || list[0].id
    }
  },
  { immediate: true },
)

function selectItem(item) {
  selectedId.value = item.key || item.id
}

function copySelected() {
  const text = selected.value?.content || selected.value?.path || selected.value?.url || ''
  navigator.clipboard.writeText(text).then(() => {
    appStore.success('已复制')
  }).catch(() => {
    appStore.error('复制失败')
  })
}

function downloadSelected() {
  const item = selected.value
  if (!item) return
  if (item.url && item.url.startsWith('data:')) {
    const a = document.createElement('a')
    a.href = item.url
    a.download = `${(item.title || 'figure').replace(/[\\/:*?"<>|]/g, '_')}.png`
    a.click()
    return
  }
  if (!item.content) {
    appStore.info(item.path ? `文件路径：${item.path}` : '没有可下载的文本内容')
    return
  }
  const ext = item.language === 'python' ? 'py' : item.language === 'json' ? 'json' : 'md'
  const blob = new Blob([item.content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = (item.title || `output.${ext}`).replace(/[\\/:*?"<>|]/g, '_')
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style lang="scss" scoped>
.output-viewer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  flex: 1;
}

.output-viewer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;

  h4 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.output-viewer__tabs {
  display: flex;
  gap: 6px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;

  &:hover {
    color: var(--text-primary);
  }

  &.active {
    color: var(--text-primary);
    border-color: color-mix(in srgb, var(--color-primary, #3b82f6) 55%, var(--border-primary));
    background: color-mix(in srgb, var(--color-primary, #3b82f6) 12%, transparent);
  }
}

.tab-count {
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  color: var(--text-tertiary);
}

.output-viewer__empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  border: 1px dashed var(--border-primary);
  border-radius: 12px;
}

.output-viewer__body {
  display: grid;
  grid-template-columns: minmax(180px, 240px) 1fr;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-tertiary);
}

.file-list {
  overflow: auto;
  border-right: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.file-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  padding: 9px 12px;
  border: 0;
  border-bottom: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;

  &:hover {
    background: var(--bg-hover, rgba(255, 255, 255, 0.04));
  }

  &.active {
    background: color-mix(in srgb, var(--color-primary, #3b82f6) 14%, transparent);
  }
}

.file-title {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  word-break: break-all;
}

.file-node {
  font-size: 10px;
  color: var(--text-tertiary);
}

.preview-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-primary);
}

.preview-name {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-actions {
  display: flex;
  gap: 6px;
}

.tool-btn {
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 11px;
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }
}

.preview-markdown,
.preview-code,
.preview-docx,
.preview-image-wrap {
  flex: 1;
  overflow: auto;
  padding: 14px 16px;
}

.preview-markdown {
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-primary);

  :deep(h1),
  :deep(h2),
  :deep(h3) {
    margin: 1.1em 0 0.4em;
    font-weight: 700;
  }

  :deep(p) {
    margin: 0.6em 0;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin: 12px 0;
  }

  :deep(th),
  :deep(td) {
    border: 1px solid var(--border-primary);
    padding: 6px 8px;
  }

  :deep(img) {
    max-width: 100%;
    border-radius: 8px;
  }

  :deep(code) {
    font-family: 'Fira Code', ui-monospace, monospace;
    font-size: 12px;
  }
}

.preview-code {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-primary);
}

.preview-docx {
  font-size: 13px;
  color: var(--text-secondary);

  code {
    display: block;
    margin: 8px 0 12px;
    padding: 8px 10px;
    border-radius: 8px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    word-break: break-all;
  }

  .hint {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.preview-image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(45deg, rgba(255, 255, 255, 0.03) 25%, transparent 25%) 0 0 / 16px 16px,
    linear-gradient(45deg, transparent 75%, rgba(255, 255, 255, 0.03) 75%) 8px 8px / 16px 16px;
}

.preview-image {
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
  cursor: zoom-in;
  border-radius: 8px;
  background: #fff;
}

.lightbox {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.78);
  cursor: zoom-out;

  img {
    max-width: 92vw;
    max-height: 92vh;
    object-fit: contain;
    background: #fff;
    border-radius: 8px;
  }
}

@media (max-width: 960px) {
  .output-viewer__body {
    grid-template-columns: 1fr;
    max-height: none;
  }

  .file-list {
    max-height: 160px;
    border-right: 0;
    border-bottom: 1px solid var(--border-primary);
  }
}
</style>
