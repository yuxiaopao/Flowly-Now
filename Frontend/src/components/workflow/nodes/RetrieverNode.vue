<template>
  <div
    class="domain-node retriever-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <div
        class="node-type-badge"
        :style="{ backgroundColor: nodeColor + '22', borderColor: nodeColor }"
      >
        <Search
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">检索器</span>
      </div>
      <button
        class="action-btn"
        @click.stop="toggleExpand"
      >
        <ChevronDown
          class="action-icon"
          :class="{ rotated: isExpanded }"
        />
      </button>
    </div>

    <div class="node-name-section">
      <input
        v-model="localName"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop
      >
    </div>

    <div class="compact-view">
      <div
        v-if="localConfig.retrieverType || localConfig.method"
        class="info-row"
      >
        <span class="info-label">类型</span>
        <span class="info-value">{{ localConfig.retrieverType || localConfig.method || '-' }}</span>
      </div>
      <div
        v-if="localConfig.query || localConfig.description"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.query || localConfig.description, 35) }}</span>
      </div>
      <div
        class="status-bar"
        :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
      >
        <div
          v-if="isRunning"
          class="status-running"
        >
          <Loader class="status-icon spinning" />
          <span>检索中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="resultCount > 0"
            class="result-count"
          >{{ resultCount }} 条</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>执行失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="results-zone"
    >
      <div class="results-header">
        <Search class="results-icon" />
        <span class="results-label">Top-{{ localConfig.topK || 5 }} 结果</span>
        <span
          v-if="resultCount > 0"
          class="results-count"
        >{{ resultCount }} 条</span>
      </div>
      <div class="results-list">
        <div
          v-for="(item, i) in topResults.slice(0, 3)"
          :key="i"
          class="result-item"
        >
          <div class="result-rank">
            #{{ i + 1 }}
          </div>
          <div class="result-content">
            <span class="result-text">{{ item.text || item.content || item.title || item.snippet || truncate(JSON.stringify(item), 40) }}</span>
          </div>
          <div class="result-score">
            <div class="score-bar">
              <div
                class="score-fill"
                :style="{ width: ((item.score || item.relevance || 0) * 100) + '%' }"
              />
            </div>
            <span class="score-value">{{ ((item.score || item.relevance || 0) * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div
          v-if="resultCount === 0"
          class="results-empty"
        >
          <span>无检索结果</span>
        </div>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">检索类型</label>
          <el-select
            v-model="localConfig.retrieverType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="similarity"
              label="相似度检索"
            />
            <el-option
              value="mmr"
              label="最大边际相关性 (MMR)"
            />
            <el-option
              value="hybrid"
              label="混合检索"
            />
            <el-option
              value="keyword"
              label="关键词检索"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">查询</label>
          <el-input
            v-model="localConfig.query"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="检索查询内容..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">返回数量</label>
          <el-input-number
            v-model="localConfig.topK"
            :min="1"
            :max="100"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">相似度阈值</label>
          <el-input-number
            v-model="localConfig.similarityThreshold"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="2"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">描述</label>
          <el-input
            v-model="localConfig.description"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="检索器描述..."
            @change="handleChange"
          />
        </div>
      </div>
    </Transition>

    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Search, ChevronDown, Loader } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const nodeColor = '#06b6d4'

const localName = ref(props.data.label || '检索器')
const localConfig = ref({
  retrieverType: props.data.config?.retrieverType || 'similarity',
  method: props.data.config?.method || '',
  query: props.data.config?.query || '',
  topK: props.data.config?.topK || 5,
  similarityThreshold: props.data.config?.similarityThreshold || 0.7,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const resultCount = computed(() => {
  if (!nodeOutput.value) return 0
  if (Array.isArray(nodeOutput.value)) return nodeOutput.value.length
  if (nodeOutput.value.results) return nodeOutput.value.results.length
  if (nodeOutput.value.items) return nodeOutput.value.items.length
  return 0
})

const topResults = computed(() => {
  if (!nodeOutput.value) return []
  if (Array.isArray(nodeOutput.value)) return nodeOutput.value
  if (nodeOutput.value.results) return nodeOutput.value.results
  if (nodeOutput.value.items) return nodeOutput.value.items
  return []
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '检索器'
    localConfig.value = { retrieverType: d.config?.retrieverType || 'similarity', method: d.config?.method || '', query: d.config?.query || '', topK: d.config?.topK || 5, similarityThreshold: d.config?.similarityThreshold || 0.7, description: d.config?.description || '', ...d.config }
  }
}, { deep: true })

function toggleExpand() { isExpanded.value = !isExpanded.value }

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.retriever-node {
  &.is-running { animation: retr-pulse 1.8s ease-in-out infinite; }
  &.is-completed .results-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes retr-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(6, 182, 212, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(6, 182, 212, 0); }
}

.results-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(6, 182, 212, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.results-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(6, 182, 212, 0.15);
  background: rgba(6, 182, 212, 0.05);

  .results-icon { width: 11px; height: 11px; color: rgba(6, 182, 212, 0.6); }
  .results-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(6, 182, 212, 0.7); flex: 1; }
  .results-count { font-size: 9px; font-weight: 600; background: rgba(6, 182, 212, 0.15); color: #22d3ee; padding: 1px 6px; border-radius: 10px; border: 1px solid rgba(6, 182, 212, 0.3); }
}

.results-list { padding: 6px 8px; display: flex; flex-direction: column; gap: 4px; }

.result-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  background: rgba(6, 182, 212, 0.04);
  border: 1px solid rgba(6, 182, 212, 0.1);
  border-radius: 5px;

  .result-rank { font-size: 9px; font-weight: 800; color: rgba(6, 182, 212, 0.6); font-family: 'JetBrains Mono', monospace; min-width: 20px; }
  .result-content { flex: 1; min-width: 0; }
  .result-text { font-size: 9px; color: rgba(255, 255, 255, 0.7); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
}

.result-score { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; min-width: 44px; }

.score-bar { width: 40px; height: 3px; background: rgba(6, 182, 212, 0.15); border-radius: 2px; overflow: hidden; }
.score-fill { height: 100%; background: linear-gradient(90deg, #06b6d4, #22d3ee); border-radius: 2px; transition: width 0.5s ease; }
.score-value { font-size: 8px; font-family: 'JetBrains Mono', monospace; color: rgba(6, 182, 212, 0.6); font-weight: 600; }

.results-empty { text-align: center; padding: 12px 0; font-size: 10px; color: rgba(6, 182, 212, 0.3); font-style: italic; }

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(6, 182, 212, 0.1); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.result-count { font-size: 9px; font-family: 'JetBrains Mono', monospace; color: rgba(6, 182, 212, 0.6); margin-left: auto; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.domain-node {
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, v-bind(nodeColor));
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected { box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent); transform: translateY(-2px); }
  &:hover:not(.selected) { box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent); transform: translateY(-1px); }
}

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: rgba(255, 255, 255, 0.02); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; border: 1px solid; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; .badge-icon { width: 11px; height: 11px; } }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 10px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e5e5e5); outline: none; transition: all 0.15s ease; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); } }
.compact-view { padding: 0 12px 10px; display: flex; flex-direction: column; gap: 4px; }
.info-row { display: flex; align-items: center; gap: 6px; .info-label { font-size: 10px; color: rgba(255, 255, 255, 0.4); } .info-value { font-size: 11px; color: rgba(255, 255, 255, 0.7); font-family: 'JetBrains Mono', monospace; } }
.preview-row .preview-text { font-size: 10px; color: rgba(255, 255, 255, 0.6); line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
:deep(.el-select), :deep(.el-input), :deep(.el-input-number) { width: 100%; .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; border-radius: 6px; } .el-input__inner { color: var(--node-text, #e5e5e5) !important; font-size: 12px !important; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: rgba(10, 10, 18, 0.95); border: 2px solid v-bind(nodeColor); border-radius: 50%; &:hover { background: v-bind(nodeColor); transform: scale(1.3); } }
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #06b6d4; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #06b6d4; --node-text: #1e1e2e; } }
</style>
