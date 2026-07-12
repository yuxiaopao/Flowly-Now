<template>
  <div class="yolo-log-panel">
    <div class="log-header">
      <div class="header-left">
        <span class="header-title">训练日志</span>
        <span
          v-if="isLive"
          class="live-badge"
        >
          <span class="live-dot" />
          LIVE
        </span>
      </div>
      <div class="header-actions">
        <el-button
          size="small"
          text
          @click="$emit('clear')"
        >
          <Trash2 :size="12" />
          清空
        </el-button>
      </div>
    </div>
    <div
      ref="containerRef"
      class="log-content"
    >
      <div
        v-if="lines.length === 0"
        class="empty-logs"
      >
        等待训练开始...
      </div>
      <div
        v-for="(line, i) in lines"
        :key="i"
        class="log-line"
      >
        <span class="log-text">{{ line }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { Trash2 } from 'lucide-vue-next'

const props = defineProps({
  lines: { type: Array, default: () => [] },
  isLive: { type: Boolean, default: false },
})

defineEmits(['clear', 'download'])

const containerRef = ref(null)

watch(() => props.lines.length, async () => {
  await nextTick()
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight
  }
})
</script>

<style scoped>
.yolo-log-panel {
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color, #fff);
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 8px;
  overflow: hidden;
  height: 100%;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
  background: var(--el-fill-color-lighter, #f5f7fa);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--el-text-color-regular, #606266);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #67c23a;
  background: #f0f9eb;
  padding: 1px 6px;
  border-radius: 8px;
}

.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #67c23a;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.72rem;
  line-height: 1.6;
}

.empty-logs {
  color: var(--el-text-color-placeholder, #c0c4cc);
  font-style: italic;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-regular, #606266);
}

.log-line:last-child {
  color: var(--el-text-color-primary, #303133);
}
</style>
