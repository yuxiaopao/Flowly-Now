<template>
  <div class="yolo-progress-ring">
    <svg
      :width="size"
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
      class="ring-svg"
    >
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        class="ring-bg"
        fill="none"
        :stroke-width="strokeWidth"
      />
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        class="ring-progress"
        fill="none"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        :transform="`rotate(-90 ${center} ${center})`"
      />
    </svg>
    <div class="ring-content">
      <span class="ring-value">{{ displayValue }}</span>
      <span class="ring-label">{{ label }}</span>
    </div>
    <div
      v-if="showStatus && status"
      class="ring-status"
      :class="statusClass"
    >
      {{ statusLabel }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  percent: { type: Number, default: 0 },
  size: { type: Number, default: 140 },
  strokeWidth: { type: Number, default: 10 },
  label: { type: String, default: '进度' },
  status: { type: String, default: '' },
  showStatus: { type: Boolean, default: true },
})

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const dashOffset = computed(() => {
  const progress = Math.min(Math.max(props.percent, 0), 100)
  return circumference.value * (1 - progress / 100)
})
const displayValue = computed(() => `${Math.round(props.percent)}%`)

const statusClass = computed(() => {
  const map = {
    queued: 'status-queued',
    provisioning: 'status-running',
    preparing: 'status-running',
    running: 'status-running',
    validating: 'status-running',
    packaging: 'status-running',
    completed: 'status-completed',
    failed: 'status-failed',
    cancelled: 'status-failed',
    timeout: 'status-failed',
  }
  return map[props.status] || ''
})

const statusLabel = computed(() => {
  const map = {
    queued: '排队中',
    provisioning: '分配资源',
    preparing: '准备数据',
    running: '训练中',
    validating: '验证中',
    packaging: '打包中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    timeout: '超时',
  }
  return map[props.status] || props.status
})
</script>

<style scoped>
.yolo-progress-ring {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-svg {
  transform: none;
}

.ring-bg {
  stroke: var(--el-fill-color-light, #f0f2f5);
}

.ring-progress {
  stroke: var(--el-color-primary, #409eff);
  transition: stroke-dashoffset 0.5s ease;
}

.ring-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.ring-value {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--el-text-color-primary, #303133);
  line-height: 1;
}

.ring-label {
  font-size: 0.7rem;
  color: var(--el-text-color-secondary, #909399);
  line-height: 1;
}

.ring-status {
  margin-top: 8px;
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.status-running {
  background: #ecf5ff;
  color: #409eff;
}
.status-completed {
  background: #f0f9eb;
  color: #67c23a;
}
.status-failed {
  background: #fef0f0;
  color: #f56c6c;
}
.status-queued {
  background: #f4f4f5;
  color: #909399;
}
</style>
