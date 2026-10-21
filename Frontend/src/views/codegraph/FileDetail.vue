<template>
  <div class="file-detail">
    <div class="detail-header">
      <h3 class="detail-title">
        文件详情
      </h3>
      <el-button
        :icon="X"
        text
        size="small"
        aria-label="关闭文件详情"
        @click="$emit('close')"
      />
    </div>

    <div class="detail-content">
      <div class="info-section">
        <div class="file-icon-wrapper">
          <component
            :is="getFileIcon(node.type)"
            class="file-icon"
          />
        </div>
        <div class="file-name">
          {{ node.name }}
        </div>
        <div class="file-path">
          {{ node.path }}
        </div>
      </div>

      <!-- AI 解读 -->
      <div class="info-section ai-section">
        <div class="section-title">
          <Sparkles class="ai-icon" />
          <span>AI 解读</span>
          <el-button
            v-if="!store.fileExplainLoading"
            text
            size="small"
            class="ai-refresh"
            @click="rerunExplain"
          >
            重新分析
          </el-button>
        </div>

        <div
          v-if="store.fileExplainLoading"
          class="ai-loading"
        >
          <div class="ai-orb" />
          <span>正在分析该文件职责…</span>
        </div>

        <div
          v-else-if="store.fileExplainError"
          class="ai-error"
        >
          {{ store.fileExplainError }}
          <el-button
            size="small"
            text
            type="primary"
            @click="rerunExplain"
          >
            重试
          </el-button>
        </div>

        <div
          v-else-if="store.fileExplanation"
          class="ai-body"
        >
          <div class="ai-scroll">
            <p class="ai-summary">
              {{ aiFullText }}
            </p>
            <p
              v-if="showPurpose"
              class="ai-purpose"
            >
              <span>用途</span>{{ store.fileExplanation.purpose }}
            </p>
            <ul
              v-if="showKeyPoints"
              class="ai-points"
            >
              <li
                v-for="(point, idx) in explanationPoints"
                :key="idx"
              >
                {{ point }}
              </li>
            </ul>
          </div>
          <div
            v-if="store.fileExplanation.source"
            class="ai-source"
          >
            {{ store.fileExplanation.source === 'llm' ? 'LLM 分析' : '启发式分析' }}
            <template v-if="store.fileExplanation.cached">
              · 缓存
            </template>
            <span class="ai-scroll-hint">可滚动查看全文</span>
          </div>
        </div>

        <div
          v-else
          class="ai-empty"
        >
          选中文件后将自动分析用途
        </div>
      </div>

      <div class="info-section">
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">类型</span>
            <el-tag size="small">
              {{ node.type }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">模块</span>
            <span class="info-value">{{ node.module }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">大小</span>
            <span class="info-value">{{ formatSize(node.size) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">行数</span>
            <span class="info-value">{{ node.lines }}</span>
          </div>
        </div>
      </div>

      <div class="info-section">
        <div class="section-title">
          <span>依赖分析</span>
        </div>
        <div class="dependency-stats">
          <div class="dep-item">
            <span class="dep-label">导入</span>
            <span class="dep-value">{{ node.outdegree || 0 }}</span>
          </div>
          <div class="dep-item">
            <span class="dep-label">被依赖</span>
            <span class="dep-value">{{ node.indegree || 0 }}</span>
          </div>
          <div class="dep-item">
            <span class="dep-label">中心性</span>
            <span class="dep-value">{{ formatCentrality(node.centrality) }}</span>
          </div>
          <div class="dep-item">
            <span class="dep-label">深度</span>
            <span class="dep-value">{{ node.depth || 0 }}</span>
          </div>
        </div>
      </div>

      <div
        v-if="importedNodes.length > 0"
        class="info-section"
      >
        <div class="section-title">
          <span>导入 ({{ importedNodes.length }})</span>
        </div>
        <div class="import-list">
          <button
            v-for="item in importedNodes"
            :key="item.id"
            class="import-item"
            type="button"
            :title="item.path"
            @click="$emit('select', item)"
          >
            <span class="import-name">{{ item.name }}</span>
            <span class="import-path">{{ item.path }}</span>
          </button>
        </div>
      </div>

      <div
        v-if="importedByNodes.length > 0"
        class="info-section"
      >
        <div class="section-title">
          <span>被依赖 ({{ importedByNodes.length }})</span>
        </div>
        <div class="import-list">
          <button
            v-for="item in importedByNodes"
            :key="item.id"
            class="import-item"
            type="button"
            :title="item.path"
            @click="$emit('select', item)"
          >
            <span class="import-name">{{ item.name }}</span>
            <span class="import-path">{{ item.path }}</span>
          </button>
        </div>
      </div>

      <div class="action-buttons">
        <el-button
          type="primary"
          size="small"
          @click="handleViewFile"
        >
          查看源码
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { X, FileCode, Sparkles } from 'lucide-vue-next'

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'select', 'view-file'])

const store = useCodeGraphStore()

/** Prefer full LLM text so the panel can scroll instead of truncating mid-sentence */
const usingRawText = computed(() => {
  const exp = store.fileExplanation
  if (!exp) return false
  const raw = (exp.raw || '').trim()
  return Boolean(raw && raw.length > (exp.summary || '').length)
})

const aiFullText = computed(() => {
  const exp = store.fileExplanation
  if (!exp) return ''
  if (usingRawText.value) {
    return (exp.raw || '').trim().replace(/\\n/g, '\n')
  }
  return exp.summary || ''
})

const showPurpose = computed(() => {
  const exp = store.fileExplanation
  if (!exp?.purpose || usingRawText.value) return false
  return exp.purpose !== exp.summary
})

const showKeyPoints = computed(() => {
  return Boolean(explanationPoints.value.length && !usingRawText.value)
})
const explanationPoints = computed(() => store.fileExplanation?.keyPoints || store.fileExplanation?.key_points || [])

const importedNodes = computed(() => {
  const { byId, relationships } = store.relationships
  return [...(relationships.get(props.node.id)?.imports || [])].map(id => byId.get(id))
})

const importedByNodes = computed(() => {
  const { byId, relationships } = store.relationships
  return [...(relationships.get(props.node.id)?.importedBy || [])].map(id => byId.get(id))
})

watch(
  () => props.node,
  (node) => {
    if (node?.path) store.explainFile(node)
  },
  { immediate: true },
)

function getFileIcon(_type) {
  return FileCode
}

function formatSize(bytes) {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${bytes || 0} B`
}

function formatCentrality(value) {
  if (value === undefined || value === null) return '0.00'
  return `${(value * 100).toFixed(1)}%`
}

function handleViewFile() {
  emit('view-file', props.node.path)
}

function rerunExplain() {
  store.explainFile(props.node)
}
</script>

<style lang="scss" scoped>
.file-detail {
  display: flex;
  flex-direction: column;
  max-height: min(70vh, 720px);
  padding: 14px 16px 16px;
  min-height: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  flex-shrink: 0;
}

.detail-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-gutter: stable;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.35);
    border-radius: 999px;
  }
  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.04);
  }
}

.info-section {
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.file-icon-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;

  .file-icon {
    width: 40px;
    height: 40px;
    color: #22d3ee;
  }
}

.file-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 4px;
}

.file-path {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  word-break: break-all;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .info-label {
    font-size: 11px;
    color: var(--text-secondary);
  }

  .info-value {
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 500;
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.ai-section {
  min-width: 0;

  .ai-icon {
    width: 14px;
    height: 14px;
    color: #22d3ee;
  }

  .ai-refresh {
    margin-left: auto;
    color: #67e8f9;
  }
}

.ai-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  background: rgba(34, 211, 238, 0.06);
  border: 1px solid rgba(34, 211, 238, 0.18);
  color: #a5f3fc;
  font-size: 12px;
}

.ai-orb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(34, 211, 238, 0.25);
  border-top-color: #22d3ee;
  animation: ai-spin 0.7s linear infinite;
}

@keyframes ai-spin {
  to { transform: rotate(360deg); }
}

.ai-error {
  font-size: 12px;
  color: #fda4af;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.ai-scroll {
  max-height: 260px;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 10px 10px 10px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(34, 211, 238, 0.18);
  scrollbar-gutter: stable;

  &::-webkit-scrollbar {
    width: 8px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(34, 211, 238, 0.45);
    border-radius: 999px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(34, 211, 238, 0.65);
  }
  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.04);
    border-radius: 999px;
  }
}

.ai-summary {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.ai-purpose {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #94a3b8;

  span {
    display: inline-block;
    margin-right: 6px;
    color: #22d3ee;
    font-weight: 600;
  }
}

.ai-points {
  margin: 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  li {
    font-size: 12px;
    color: #cbd5e1;
    line-height: 1.45;
  }
}

.ai-source {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 10px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.75);
}

.ai-scroll-hint {
  margin-left: auto;
  text-transform: none;
  letter-spacing: 0;
  color: rgba(103, 232, 249, 0.75);
}

.ai-empty {
  font-size: 12px;
  color: var(--text-tertiary);
}

.dependency-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.dep-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;

  .dep-label {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .dep-value {
    font-size: 14px;
    font-weight: 700;
    color: #67e8f9;
  }
}

.import-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.import-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  text-align: left;
  font: inherit;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);

  &:hover,
  &:focus-visible {
    background: rgba(34, 211, 238, 0.08);
    color: #e0faff;
  }
}

.import-path {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--cg-caption-size);
  color: var(--text-tertiary);
}

.action-buttons {
  display: flex;
  gap: 8px;
}
</style>
