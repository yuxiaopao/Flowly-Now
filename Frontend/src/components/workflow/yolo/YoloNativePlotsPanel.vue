<template>
  <section
    class="yolo-native-plots"
    aria-label="Ultralytics 原生训练图表"
  >
    <div class="plots-header">
      <strong>原生图表与训练预览</strong><span>{{ plots.length }} 张</span><label>类型 <select v-model="group"><option value="all">全部</option><option value="evaluation">评估曲线与矩阵</option><option value="batch">训练 / 验证批次</option><option value="dataset">标签分布</option></select></label>
    </div>
    <p
      v-if="!plots.length"
      class="plot-empty"
    >
      本次训练尚未生成图表。启用 plots 后，训练与验证产生的图片会自动同步。
    </p>
    <p
      v-else-if="!visiblePlots.length"
      class="plot-empty"
    >
      本次记录没有生成该类型的图片。
    </p>
    <div class="plots-grid">
      <button
        v-for="plot in visiblePlots"
        :key="plot.name"
        type="button"
        class="plot-thumb"
        :class="{ active: activeName === plot.name }"
        :aria-pressed="activeName === plot.name"
        @click.stop="selectPlot(plot)"
      >
        <img
          v-if="cache.get(plot.name)?.url"
          :src="cache.get(plot.name).url"
          :alt="plot.label"
          loading="lazy"
        >
        <span
          v-else
          class="plot-loading"
        >{{ cache.get(plot.name)?.error ? '读取失败，点击重试' : '图片加载中…' }}</span>
        <span class="plot-label">{{ plot.label }}</span>
      </button>
    </div>
    <template v-if="activePlot">
      <div class="plots-header">
        <span>{{ activePlot.label }}<small>{{ activePlot.name }}</small></span><a
          v-if="activeUrl"
          :href="activeUrl"
          :download="activePlot.name"
        >下载原图</a><button
          v-if="activeUrl"
          type="button"
          @click="expanded = !expanded"
        >
          {{ expanded ? '适应窗口' : '展开原图' }}
        </button>
      </div>
      <p
        v-if="cache.get(activeName)?.error"
        class="plot-error"
        role="alert"
      >
        {{ cache.get(activeName).error }}<button
          type="button"
          @click="loadPlot(activePlot, true)"
        >
          重新加载图片
        </button>
      </p>
      <div
        v-if="activeUrl"
        class="plot-preview"
        :class="{ expanded }"
      >
        <img
          :src="activeUrl"
          :alt="activePlot.label"
        >
      </div>
      <p
        v-else-if="!cache.get(activeName)?.error"
        class="plot-empty"
        role="status"
      >
        正在读取原图…
      </p>
    </template>
  </section>
</template>

<script setup>
import { computed, ref, shallowReactive, watch, onBeforeUnmount } from 'vue'
const props = defineProps({ plots: { type: Array, default: () => [] }, jobId: { type: String, default: '' }, fetchPlotBlob: { type: Function, required: true } })
const cache = shallowReactive(new Map())
const pending = new Map()
const activeName = ref('')
const group = ref('all')
const expanded = ref(false)
let generation = 0
let disposed = false
const activePlot = computed(() => props.plots.find(plot => plot.name === activeName.value))
const activeUrl = computed(() => cache.get(activeName.value)?.url)
const category = name => /(?:train|val)_batch/.test(name) ? 'batch' : name.startsWith('labels') ? 'dataset' : 'evaluation'
const visiblePlots = computed(() => props.plots.filter(plot => group.value === 'all' || category(plot.name) === group.value))
const signature = plot => `${plot.modified_at ?? plot.modifiedAt ?? ''}:${plot.size_bytes ?? plot.sizeBytes ?? ''}`

function clear() {
  generation++
  for (const value of cache.values()) if (value.url) URL.revokeObjectURL(value.url)
  cache.clear(); pending.clear(); activeName.value = ''
}
async function loadPlot(plot, retry = false) {
  if (!props.jobId || !plot || disposed) return
  const id = props.jobId
  const version = generation
  const stamp = signature(plot)
  const cached = cache.get(plot.name)
  if (pending.has(plot.name) || (!retry && cached?.url && cached.stamp === stamp)) return
  pending.set(plot.name, stamp)
  try {
    const url = await props.fetchPlotBlob(id, plot.name)
    if (disposed || version !== generation || props.jobId !== id || !props.plots.some(item => item.name === plot.name && signature(item) === stamp)) { URL.revokeObjectURL(url); return }
    if (cached?.url) URL.revokeObjectURL(cached.url)
    cache.set(plot.name, { url, stamp, error: '' })
  } catch (failure) {
    if (!disposed && version === generation) cache.set(plot.name, { ...cached, error: failure.message || '图片读取失败，请重试。' })
  } finally { if (version === generation) pending.delete(plot.name) }
}
function selectPlot(plot) { activeName.value = plot.name; loadPlot(plot, Boolean(cache.get(plot.name)?.error)) }
async function synchronize() {
  const items = props.plots
  const names = new Set(items.map(plot => plot.name))
  for (const [name, value] of cache) {
    if (!names.has(name)) { if (value.url) URL.revokeObjectURL(value.url); cache.delete(name) }
  }
  if (!names.has(activeName.value)) activeName.value = items[0]?.name || ''
  const version = generation
  const queue = [...items]
  await Promise.all(Array.from({ length: Math.min(3, queue.length) }, async () => {
    while (queue.length && !disposed && version === generation) await loadPlot(queue.shift())
  }))
}
watch(() => props.jobId, () => { clear(); synchronize() }, { immediate: true })
watch(() => props.plots, synchronize)
watch(group, () => { if (!visiblePlots.value.some(plot => plot.name === activeName.value)) activeName.value = visiblePlots.value[0]?.name || '' })
onBeforeUnmount(() => { disposed = true; clear() })
</script>

<style scoped>
.yolo-native-plots { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.plots-header { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; color: var(--text-secondary); font-size: 12px; }
.plots-header strong { color: var(--text-primary); }
button, select { font: inherit; padding: 6px 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; }
.plots-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(135px, 1fr)); gap: 10px; }
.plot-thumb { min-width: 0; padding: 6px; display: flex; flex-direction: column; gap: 7px; align-items: stretch; }
.plot-thumb.active { border-color: var(--primary-color); }
.plot-thumb img { width: 100%; height: 88px; object-fit: contain; }
.plot-label { font-size: 11px; line-height: 1.5; }
.plot-loading { display: grid; place-content: center; min-height: 88px; color: var(--text-secondary); font-size: 11px; }
.plot-preview { border: 1px solid var(--border-color); background: var(--bg-secondary); border-radius: 8px; overflow: auto; max-height: 650px; }
.plot-preview img { display: block; width: 100%; height: auto; object-fit: contain; }
.plot-preview.expanded { max-height: none; }
.plot-preview.expanded img { width: auto; max-width: none; }
.plot-empty { margin: 0; padding: 20px; background: var(--bg-secondary); color: var(--text-secondary); font-size: 12px; }
.plot-error { color: var(--error); font-size: 12px; }
.plot-error button { margin-left: 12px; }
small { display: block; margin-top: 4px; }
a { color: var(--primary-color); }
button:focus-visible, select:focus-visible, a:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; }
</style>
