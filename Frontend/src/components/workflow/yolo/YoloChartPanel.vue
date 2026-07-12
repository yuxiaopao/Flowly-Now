<template>
  <div class="yolo-chart-panel">
    <div class="chart-header">
      <span class="chart-title">{{ title }}</span>
      <span
        v-if="latestValue !== null"
        class="chart-latest"
      >{{ formatValue(latestValue) }}</span>
    </div>
    <canvas
      ref="canvasRef"
      class="chart-canvas"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  data: { type: Array, default: () => [] },
  color: { type: String, default: '#409eff' },
  formatValue: {
    type: Function,
    default: (v) => v?.toFixed(4) ?? '—',
  },
  latestValue: { type: Number, default: null },
})

const canvasRef = ref(null)
let animationFrame = null
let ctx = null

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return

  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.scale(dpr, dpr)

  const w = rect.width
  const h = rect.height
  const data = props.data
  const len = data.length

  ctx.clearRect(0, 0, w, h)

  if (len < 2) return

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pad = 4
  const drawH = h - pad * 2
  const stepX = w / Math.max(len - 1, 1)

  // Grid lines
  ctx.strokeStyle = 'rgba(0,0,0,0.05)'
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const y = pad + (drawH * i) / 4
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()
  }

  // Gradient fill
  const gradient = ctx.createLinearGradient(0, pad, 0, h - pad)
  gradient.addColorStop(0, props.color + '44')
  gradient.addColorStop(1, props.color + '00')

  ctx.beginPath()
  data.forEach((v, i) => {
    const x = i * stepX
    const y = pad + drawH - ((v - min) / range) * drawH
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.lineTo(w, h - pad)
  ctx.lineTo(0, h - pad)
  ctx.closePath()
  ctx.fillStyle = gradient
  ctx.fill()

  // Line
  ctx.beginPath()
  data.forEach((v, i) => {
    const x = i * stepX
    const y = pad + drawH - ((v - min) / range) * drawH
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  })
  ctx.strokeStyle = props.color
  ctx.lineWidth = 2
  ctx.stroke()

  // Dot on last point
  const lastX = w
  const lastY = pad + drawH - ((data[len - 1] - min) / range) * drawH
  ctx.beginPath()
  ctx.arc(lastX, lastY, 3, 0, Math.PI * 2)
  ctx.fillStyle = props.color
  ctx.fill()
}

function scheduleRedraw() {
  if (animationFrame) cancelAnimationFrame(animationFrame)
  animationFrame = requestAnimationFrame(draw)
}

watch(() => props.data, scheduleRedraw, { deep: true })

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  const ro = new ResizeObserver(scheduleRedraw)
  ro.observe(canvas)
  scheduleRedraw()
})

onUnmounted(() => {
  if (animationFrame) cancelAnimationFrame(animationFrame)
})
</script>

<style scoped>
.yolo-chart-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  height: 100%;
}

.chart-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.chart-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--el-text-color-secondary, #909399);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.chart-latest {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--el-text-color-primary, #303133);
  font-variant-numeric: tabular-nums;
}

.chart-canvas {
  display: block;
  flex: 1;
  min-height: 60px;
  width: 100%;
}
</style>
