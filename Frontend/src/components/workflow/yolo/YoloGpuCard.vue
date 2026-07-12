<template>
  <div class="yolo-gpu-card">
    <div class="gpu-header">
      <Cpu :size="14" />
      <span>GPU 状态</span>
      <span
        v-if="gpuInfo?.available"
        class="gpu-badge"
      >可用</span>
      <span
        v-else
        class="gpu-badge gpu-badge--off"
      >未检测到</span>
    </div>
    <div
      v-if="gpuInfo?.available"
      class="gpu-body"
    >
      <div class="gpu-name">
        {{ gpuInfo.name }}
      </div>
      <div class="gpu-bars">
        <div class="gpu-bar-item">
          <div class="bar-label">
            <span>显存</span>
            <span class="bar-values">
              {{ formatMB(gpuInfo.memory_free_mb) }} / {{ formatMB(gpuInfo.memory_total_mb) }}
            </span>
          </div>
          <el-progress
            :percentage="memoryPercent"
            :stroke-width="6"
            :show-text="false"
            :color="memoryColor"
          />
        </div>
        <div
          v-if="gpuInfo.utilization_percent != null"
          class="gpu-bar-item"
        >
          <div class="bar-label">
            <span>利用率</span>
            <span class="bar-values">{{ gpuInfo.utilization_percent }}%</span>
          </div>
          <el-progress
            :percentage="gpuInfo.utilization_percent"
            :stroke-width="6"
            :show-text="false"
            color="#409eff"
          />
        </div>
      </div>
    </div>
    <div
      v-else
      class="gpu-empty"
    >
      将在有 GPU 时自动使用加速
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Cpu } from 'lucide-vue-next'

const props = defineProps({
  gpuInfo: { type: Object, default: () => ({}) },
})

const formatMB = (v) => v != null ? `${Math.round(v)} MB` : '—'

const memoryPercent = computed(() => {
  const total = props.gpuInfo?.memory_total_mb
  const free = props.gpuInfo?.memory_free_mb
  if (!total || free == null) return 0
  return Math.round((1 - free / total) * 100)
})

const memoryColor = computed(() => {
  const p = memoryPercent.value
  if (p > 85) return '#f56c6c'
  if (p > 60) return '#e6a23c'
  return '#67c23a'
})
</script>

<style scoped>
.yolo-gpu-card {
  background: var(--el-fill-color-lighter, #f5f7fa);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gpu-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--el-text-color-regular, #606266);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.gpu-badge {
  margin-left: auto;
  background: #f0f9eb;
  color: #67c23a;
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 500;
  text-transform: none;
}

.gpu-badge--off {
  background: #f4f4f5;
  color: #909399;
}

.gpu-name {
  font-size: 0.75rem;
  color: var(--el-text-color-primary, #303133);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gpu-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gpu-bar-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.bar-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: var(--el-text-color-secondary, #909399);
}

.bar-values {
  font-variant-numeric: tabular-nums;
}

.gpu-empty {
  font-size: 0.75rem;
  color: var(--el-text-color-placeholder, #c0c4cc);
}
</style>
