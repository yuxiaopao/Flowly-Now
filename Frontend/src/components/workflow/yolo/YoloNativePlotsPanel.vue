<template>
  <div
    v-if="plots.length"
    class="yolo-native-plots"
  >
    <div class="plots-header">
      <span class="plots-title">Ultralytics 原生训练图表</span>
      <span class="plots-count">{{ plots.length }} 张</span>
    </div>
    <div class="plots-grid">
      <button
        v-for="plot in plots"
        :key="plot.name"
        type="button"
        class="plot-thumb"
        :class="{ active: activePlot?.name === plot.name }"
        @click.stop="selectPlot(plot)"
      >
        <img
          v-if="plot.url"
          :src="plot.url"
          :alt="plot.label"
          loading="lazy"
        >
        <span
          v-else
          class="plot-loading"
        >加载中…</span>
        <span class="plot-label">{{ plot.label }}</span>
      </button>
    </div>
    <div
      v-if="activePlot?.url"
      class="plot-preview"
    >
      <img
        :src="activePlot.url"
        :alt="activePlot.label"
      >
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  plots: { type: Array, default: () => [] },
  jobId: { type: String, default: '' },
  fetchPlotBlob: { type: Function, required: true },
})

const activePlot = ref(null)
const loadedUrls = ref([])
const loadingNames = new Set()

async function selectPlot(plot) {
  activePlot.value = plot
  if (!plot.url && props.jobId) {
    try {
      const url = await props.fetchPlotBlob(props.jobId, plot.name)
      plot.url = url
      loadedUrls.value.push(url)
      activePlot.value = { ...plot }
    } catch {
      // parent handles logging
    }
  }
}

// Eagerly resolve thumbnails for every plot (not just the selected one) so new
// batch-preview images appear directly in the grid as soon as Ultralytics writes
// them — mirroring ComfyUI's "show images as they're produced" behaviour.
async function ensureThumbnails(items) {
  for (const plot of items) {
    if (plot.url || loadingNames.has(plot.name)) continue
    loadingNames.add(plot.name)
    try {
      const url = await props.fetchPlotBlob(props.jobId, plot.name)
      plot.url = url
      loadedUrls.value.push(url)
      if (activePlot.value?.name === plot.name) {
        activePlot.value = { ...plot }
      }
    } catch {
      // skip; will retry on next poll tick if still missing
    } finally {
      loadingNames.delete(plot.name)
    }
  }
}

watch(
  () => props.plots,
  async (items) => {
    if (!items?.length || !props.jobId) return
    if (!activePlot.value) {
      await selectPlot(items[0])
    }
    ensureThumbnails(items)
  },
  { immediate: true },
)

onUnmounted(() => {
  loadedUrls.value.forEach((url) => URL.revokeObjectURL(url))
})
</script>

<style scoped>
.yolo-native-plots {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plots-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.plots-title {
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
}

.plots-count {
  color: var(--text-secondary, #9ca3af);
}

.plots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 6px;
}

.plot-thumb {
  border: 1px solid var(--border-primary, #374151);
  border-radius: 6px;
  padding: 4px;
  background: var(--bg-secondary, #111827);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 72px;
}

.plot-thumb.active {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 1px #8b5cf6;
}

.plot-thumb img {
  width: 100%;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
}

.plot-loading {
  font-size: 10px;
  color: var(--text-secondary, #9ca3af);
  padding: 16px 0;
}

.plot-label {
  font-size: 10px;
  color: var(--text-secondary, #9ca3af);
  text-align: center;
  line-height: 1.2;
}

.plot-preview {
  border: 1px solid var(--border-primary, #374151);
  border-radius: 8px;
  overflow: hidden;
  background: #0f172a;
}

.plot-preview img {
  width: 100%;
  display: block;
}
</style>
