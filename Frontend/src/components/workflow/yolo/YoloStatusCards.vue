<template>
  <div class="yolo-status-cards">
    <div
      v-for="card in cards"
      :key="card.key"
      class="status-card"
      :class="card.statusClass"
    >
      <div class="card-label">
        <component
          :is="card.icon"
          :size="14"
        />
        {{ card.label }}
      </div>
      <div class="card-value">
        {{ card.value }}
      </div>
      <div
        v-if="card.sub"
        class="card-sub"
      >
        {{ card.sub }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Clock, Zap, Target } from 'lucide-vue-next'

const props = defineProps({
  epoch: { type: Number, default: 0 },
  totalEpochs: { type: Number, default: 0 },
  eta: { type: Number, default: 0 },
  etaFormatted: { type: String, default: '' },
  elapsedSeconds: { type: Number, default: 0 },
  bestFitness: { type: Number, default: 0 },
  learningRate: { type: Number, default: 0 },
})

const formatElapsed = (s) => {
  const seconds = Number(s)
  if (!Number.isFinite(seconds) || seconds <= 0) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const sec = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${sec}s`
  return `${sec}s`
}

const cards = computed(() => [
  {
    key: 'epoch',
    icon: Target,
    label: '当前轮次',
    value: props.totalEpochs > 0 ? `${props.epoch} / ${props.totalEpochs}` : `${props.epoch}`,
    statusClass: '',
  },
  {
    key: 'eta',
    icon: Clock,
    label: '剩余时间',
    value: props.etaFormatted || formatElapsed(props.eta),
    statusClass: '',
  },
  {
    key: 'elapsed',
    icon: Zap,
    label: '已用时间',
    value: formatElapsed(props.elapsedSeconds),
    statusClass: '',
  },
  {
    key: 'fitness',
    icon: Target,
    label: '最佳适应度',
    value: props.bestFitness > 0 ? props.bestFitness.toFixed(4) : '—',
    statusClass: props.bestFitness > 0.5 ? 'card-highlight' : '',
  },
  {
    key: 'lr',
    icon: Zap,
    label: '学习率',
    value: props.learningRate > 0 ? props.learningRate.toExponential(2) : '—',
    statusClass: '',
  },
])
</script>

<style scoped>
.yolo-status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.status-card {
  background: var(--el-fill-color-lighter, #f5f7fa);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: background 0.2s;
}

.card-label {
  font-size: 0.7rem;
  color: var(--el-text-color-secondary, #909399);
  display: flex;
  align-items: center;
  gap: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.card-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--el-text-color-primary, #303133);
  font-variant-numeric: tabular-nums;
}

.card-sub {
  font-size: 0.7rem;
  color: var(--el-text-color-placeholder, #c0c4cc);
}

.card-highlight .card-value {
  color: var(--el-color-success, #67c23a);
}
</style>
