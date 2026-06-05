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
        @click="$emit('close')"
      />
    </div>

    <div class="detail-content">
      <!-- 基本信息 -->
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

      <!-- 元数据 -->
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

      <!-- 依赖分析 -->
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

      <!-- 导入列表 -->
      <div
        v-if="importedNodes.length > 0"
        class="info-section"
      >
        <div class="section-title">
          <span>导入 ({{ importedNodes.length }})</span>
        </div>
        <div class="import-list">
          <div
            v-for="item in importedNodes.slice(0, 10)"
            :key="item.id"
            class="import-item"
            @click="$emit('select', item)"
          >
            <span class="import-name">{{ item.name }}</span>
          </div>
          <div
            v-if="importedNodes.length > 10"
            class="import-more"
          >
            还有 {{ importedNodes.length - 10 }} 个...
          </div>
        </div>
      </div>

      <!-- 被导入列表 -->
      <div
        v-if="importedByNodes.length > 0"
        class="info-section"
      >
        <div class="section-title">
          <span>被依赖 ({{ importedByNodes.length }})</span>
        </div>
        <div class="import-list">
          <div
            v-for="item in importedByNodes.slice(0, 10)"
            :key="item.id"
            class="import-item"
            @click="$emit('select', item)"
          >
            <span class="import-name">{{ item.name }}</span>
          </div>
          <div
            v-if="importedByNodes.length > 10"
            class="import-more"
          >
            还有 {{ importedByNodes.length - 10 }} 个...
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
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
import { computed } from 'vue'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { X } from 'lucide-vue-next'

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'select', 'view-file'])

const store = useCodeGraphStore()

const importedNodes = computed(() => {
  if (!props.node.imports || props.node.imports.length === 0) return []
  return store.nodes.filter(n => props.node.imports.includes(n.path))
})

const importedByNodes = computed(() => {
  if (!props.node.imported_by || props.node.imported_by.length === 0) return []
  return store.nodes.filter(n => props.node.imported_by.includes(n.id))
})

function getFileIcon(type) {
  return 'FileCodeIcon'
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

function formatCentrality(value) {
  if (value === undefined || value === null) return '0.00'
  return (value * 100).toFixed(1) + '%'
}

function handleViewFile() {
  emit('view-file', props.node.path)
}
</script>

<style lang="scss" scoped>
.file-detail {
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
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
  gap: 16px;
}

.info-section {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);

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
    width: 48px;
    height: 48px;
    color: var(--color-primary);
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
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
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
  background: var(--bg-hover);
  border-radius: 6px;

  .dep-label {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .dep-value {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.import-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.import-item {
  padding: 6px 10px;
  background: var(--bg-hover);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--color-primary-light-9);
  }

  .import-name {
    font-size: 12px;
    color: var(--text-primary);
  }
}

.import-more {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 4px 10px;
}

.action-buttons {
  display: flex;
  gap: 8px;

  .el-button {
    flex: 1;
  }
}
</style>
