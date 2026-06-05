<template>
  <div
    class="vectorstore-node"
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
        <Database
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">向量存储</span>
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
        v-if="localConfig.dbType || localConfig.provider"
        class="info-row"
      >
        <span class="info-label">类型</span>
        <span class="info-value">{{ localConfig.dbType || localConfig.provider || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description, 35) }}</span>
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
          <span>索引中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已就绪</span>
          <span
            v-if="docCount > 0"
            class="result-count"
          >{{ docCount }} 条</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>连接失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="store-zone"
    >
      <div class="store-header">
        <Database class="store-icon" />
        <span class="store-label">{{ localConfig.collectionName || 'collection' }}</span>
        <span class="db-type-badge">{{ localConfig.dbType || 'pinecone' }}</span>
      </div>
      <div class="store-stats">
        <div class="stat-item">
          <span class="stat-value">{{ docCount > 0 ? docCount : '—' }}</span>
          <span class="stat-label">文档</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ localConfig.dimensions || 1536 }}</span>
          <span class="stat-label">维度</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ localConfig.dbType === 'chroma' ? 'HNSW' : localConfig.dbType === 'pinecone' ? 's2' : localConfig.dbType === 'qdrant' ? 'HNSW' : 'ANN' }}</span>
          <span class="stat-label">索引</span>
        </div>
      </div>
      <div class="store-meter">
        <div class="meter-label">
          <span>容量使用</span>
          <span class="meter-value">{{ capacityPercent }}%</span>
        </div>
        <div class="meter-bar">
          <div
            class="meter-fill"
            :style="{ width: capacityPercent + '%' }"
          />
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
          <label class="config-label">向量数据库</label>
          <el-select
            v-model="localConfig.dbType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="pinecone"
              label="Pinecone"
            />
            <el-option
              value="weaviate"
              label="Weaviate"
            />
            <el-option
              value="milvus"
              label="Milvus"
            />
            <el-option
              value="chroma"
              label="Chroma"
            />
            <el-option
              value="qdrant"
              label="Qdrant"
            />
            <el-option
              value="pgvector"
              label="pgvector"
            />
            <el-option
              value="redis"
              label="Redis"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">服务商</label>
          <el-input
            v-model="localConfig.provider"
            size="small"
            placeholder="云服务商 (可选)"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">集合/索引名称</label>
          <el-input
            v-model="localConfig.collectionName"
            size="small"
            placeholder="集合名称"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">维度</label>
          <el-input-number
            v-model="localConfig.dimensions"
            :min="64"
            :max="4096"
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
            placeholder="向量存储描述..."
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
import { Database, ChevronDown, Loader } from 'lucide-vue-next'
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

const localName = ref(props.data.label || '向量存储')
const localConfig = ref({
  dbType: props.data.config?.dbType || 'pinecone',
  provider: props.data.config?.provider || '',
  collectionName: props.data.config?.collectionName || '',
  dimensions: props.data.config?.dimensions || 1536,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const docCount = computed(() => {
  if (!nodeOutput.value) return 0
  return nodeOutput.value.docCount || nodeOutput.value.count || nodeOutput.value.doc_count || nodeOutput.value.total || nodeOutput.value.n || 0
})

const capacityPercent = computed(() => {
  if (!nodeOutput.value) return 0
  const cap = nodeOutput.value.capacityPercent || nodeOutput.value.usage || 0
  return Math.min(100, Math.max(0, Number(cap)))
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '向量存储'
    localConfig.value = { dbType: d.config?.dbType || 'pinecone', provider: d.config?.provider || '', collectionName: d.config?.collectionName || '', dimensions: d.config?.dimensions || 1536, description: d.config?.description || '', ...d.config }
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
.vectorstore-node {
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, v-bind(nodeColor));
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent);
    transform: translateY(-1px);
  }

  &.is-running { animation: vs-pulse 1.8s ease-in-out infinite; }
  &.is-completed .store-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes vs-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(6, 182, 212, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(6, 182, 212, 0); }
}

.store-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(6, 182, 212, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.store-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(6, 182, 212, 0.15);
  background: rgba(6, 182, 212, 0.05);

  .store-icon { width: 11px; height: 11px; color: rgba(6, 182, 212, 0.6); }
  .store-label { font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.9); flex: 1; font-family: 'JetBrains Mono', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .db-type-badge { font-size: 9px; font-weight: 600; background: rgba(6, 182, 212, 0.15); color: #22d3ee; padding: 1px 6px; border-radius: 10px; border: 1px solid rgba(6, 182, 212, 0.3); text-transform: uppercase; }
}

.store-stats {
  display: flex;
  padding: 8px 10px;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  .stat-value { font-size: 14px; font-weight: 700; color: #22d3ee; font-family: 'JetBrains Mono', monospace; }
  .stat-label { font-size: 8px; color: rgba(255, 255, 255, 0.3); text-transform: uppercase; letter-spacing: 0.08em; }
}

.store-meter {
  padding: 6px 10px 8px;

  .meter-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(6, 182, 212, 0.5); }
  .meter-value { color: rgba(6, 182, 212, 0.8); font-family: 'JetBrains Mono', monospace; }
}

.meter-bar { width: 100%; height: 4px; background: rgba(6, 182, 212, 0.1); border-radius: 2px; overflow: hidden; }
.meter-fill { height: 100%; background: linear-gradient(90deg, #06b6d4, #22d3ee); border-radius: 2px; transition: width 0.5s ease; }

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
:global(.dark) { .vectorstore-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #06b6d4; --node-text: #e5e5e5; } }
:global(.light) { .vectorstore-node { --node-bg: #fff; --node-border: #06b6d4; --node-text: #1e1e2e; } }
</style>
