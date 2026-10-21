<template>
  <div class="stats-panel">
    <div class="panel-header">
      <span class="panel-title">统计信息</span>
    </div>

    <div class="stats-content">
      <!-- 概览统计 -->
      <div class="stats-overview">
        <div class="stat-item">
          <span class="stat-value">{{ stats.totalFiles || stats.total_files || 0 }}</span>
          <span class="stat-label">文件数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ stats.totalEdges || stats.total_edges || 0 }}</span>
          <span class="stat-label">依赖关系</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ formatNumber(stats.totalLines || stats.total_lines || 0) }}</span>
          <span class="stat-label">代码行数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ formatSize(stats.totalSize || stats.total_size || 0) }}</span>
          <span class="stat-label">总大小</span>
        </div>
      </div>

      <!-- 文件类型分布 -->
      <div
        v-if="byType && Object.keys(byType).length > 0"
        class="stats-section"
      >
        <div class="section-title">
          文件类型
        </div>
        <div class="type-list">
          <div
            v-for="(count, type) in byType"
            :key="type"
            class="type-item"
          >
            <div class="type-info">
              <span
                class="type-dot"
                :style="{ background: getTypeColor(type) }"
              />
              <span class="type-name">.{{ type }}</span>
            </div>
            <div class="type-stats">
              <span class="type-count">{{ count }}</span>
              <div class="type-bar">
                <div
                  class="type-bar-fill"
                  :style="{
                    width: `${(count / maxTypeCount) * 100}%`,
                    background: getTypeColor(type)
                  }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模块分布 -->
      <div
        v-if="byModule && Object.keys(byModule).length > 0"
        class="stats-section"
      >
        <div class="section-title">
          模块分布
        </div>
        <div class="module-list">
          <div
            v-for="(count, module) in topModules"
            :key="module"
            class="module-item"
          >
            <span class="module-name">{{ module }}</span>
            <span class="module-count">{{ count }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getTypeColor } from './graphColors'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({})
  }
})

const byType = computed(() => props.stats.byType || props.stats.by_type || {})
const byModule = computed(() => props.stats.byModule || props.stats.by_module || {})

const maxTypeCount = computed(() => {
  const counts = Object.values(byType.value)
  return counts.length > 0 ? Math.max(...counts) : 1
})

const topModules = computed(() => {
  const entries = Object.entries(byModule.value)
  return Object.fromEntries(
    entries.sort((a, b) => b[1] - a[1]).slice(0, 5)
  )
})

function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

function formatSize(bytes) {
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
  }
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
.stats-panel {
  padding: 12px 14px 14px;
}

.panel-header {
  margin-bottom: 12px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  transition: border-color 0.15s ease;

  &:hover {
    border-color: var(--border-secondary);
  }

  .stat-value {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 4px;
  }
}

.stats-section {
  .section-title {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
}

.type-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.type-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 60px;

  .type-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    box-shadow: 0 0 8px currentColor;
  }

  .type-name {
    font-size: 12px;
    color: var(--text-primary);
  }
}

.type-stats {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;

  .type-count {
    font-size: 12px;
    color: var(--text-secondary);
    min-width: 30px;
    text-align: right;
  }

  .type-bar {
    flex: 1;
    height: 5px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
    overflow: hidden;

    .type-bar-fill {
      height: 100%;
      border-radius: 999px;
      transition: width 0.25s ease;
    }
  }
}

.module-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.module-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  font-size: 12px;
  transition: border-color 0.2s ease;

  &:hover {
    border-color: rgba(34, 211, 238, 0.25);
  }

  .module-name {
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .module-count {
    color: #67e8f9;
    font-weight: 600;
  }
}
</style>
