<template>
  <figure class="analytics-figure">
    <figcaption>
      <span>{{ title }}</span><button
        type="button"
        :disabled="!chart"
        :aria-label="`下载${title}图片`"
        @click="download"
      >
        下载 PNG
      </button>
    </figcaption>
    <div
      ref="host"
      class="analytics-chart"
      role="img"
      :aria-label="`${title}，支持缩放、图例筛选和悬停查看数值`"
      :style="{ height: `${height}px` }"
    />
  </figure>
</template>

<script setup>
import { ref, shallowRef, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts/core'
import 'echarts/theme/v5.js'
import { LineChart, BarChart, HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useAppStore } from '@/stores/app'

echarts.use([LineChart, BarChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, VisualMapComponent, CanvasRenderer])
const props = defineProps({ title: { type: String, required: true }, option: { type: Object, required: true }, height: { type: Number, default: 310 } })
const host = ref(null)
const chart = shallowRef(null)
const appStore = useAppStore()
let observer
let resizeFrame
let lastSignature = ''
const colorCanvas = document.createElement('canvas')
colorCanvas.width = colorCanvas.height = 1
const colorContext = colorCanvas.getContext('2d', { willReadFrequently: true })
function chartColor(value) {
  // Theme tokens use OKLCH; zrender's gradient parser needs sRGB components.
  colorContext.clearRect(0, 0, 1, 1)
  colorContext.fillStyle = value
  colorContext.fillRect(0, 0, 1, 1)
  const [red, green, blue, alpha] = colorContext.getImageData(0, 0, 1, 1).data
  return `rgba(${red},${green},${blue},${alpha / 255})`
}
function draw() {
  if (!chart.value || !host.value) return
  const signature = JSON.stringify(props.option) + appStore.theme
  if (signature === lastSignature) return
  lastSignature = signature
  const previous = chart.value.getOption()
  const style = getComputedStyle(host.value)
  const color = name => chartColor(style.getPropertyValue(name).trim())
  const monochrome = ['pure-bw', 'high-contrast'].includes(appStore.theme)
  const text = color('--text-primary')
  const border = color('--border-color')
  chart.value.setOption({
    animation: false,
    color: monochrome ? [text, color('--text-secondary')] : [color('--primary-color'), color('--success'), color('--warning'), color('--info'), color('--error')],
    textStyle: { color: text },
    ...props.option,
    dataZoom: props.option.dataZoom?.map((zoom, index) => {
      const selected = previous?.dataZoom?.[index]
      return selected ? { ...zoom, start: selected.start, end: selected.end, startValue: selected.startValue, endValue: selected.endValue } : zoom
    }),
    legend: { ...props.option.legend, selected: previous?.legend?.[0]?.selected, textStyle: { color: text } },
    tooltip: { ...props.option.tooltip, backgroundColor: color('--bg-secondary'), borderColor: border, textStyle: { color: text }, confine: true },
    xAxis: { ...props.option.xAxis, axisLine: { lineStyle: { color: border } }, axisLabel: { ...props.option.xAxis?.axisLabel, color: text }, nameTextStyle: { color: text }, splitLine: { lineStyle: { color: border } } },
    yAxis: { ...props.option.yAxis, axisLine: { lineStyle: { color: border } }, axisLabel: { ...props.option.yAxis?.axisLabel, color: text }, nameTextStyle: { color: text }, splitLine: { lineStyle: { color: border } } },
    ...(props.option.visualMap ? { visualMap: { ...props.option.visualMap, textStyle: { color: text }, inRange: { color: [color('--bg-tertiary'), monochrome ? text : color('--primary-color')] } } } : {}),
  }, { notMerge: true, lazyUpdate: true })
}
function download() {
  const anchor = document.createElement('a')
  anchor.download = `${props.title}.png`
  anchor.href = chart.value.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: getComputedStyle(host.value).getPropertyValue('--bg-primary').trim() })
  anchor.click()
}
onMounted(() => {
  chart.value = echarts.init(host.value, 'v5')
  observer = new ResizeObserver(() => {
    cancelAnimationFrame(resizeFrame)
    resizeFrame = requestAnimationFrame(() => chart.value?.resize())
  })
  observer.observe(host.value)
  draw()
})
watch(() => props.option, draw, { deep: true })
watch(() => appStore.theme, draw, { flush: 'post' })
onBeforeUnmount(() => { observer?.disconnect(); cancelAnimationFrame(resizeFrame); chart.value?.dispose(); chart.value = null })
</script>

<style scoped>
.analytics-figure { margin: 0; min-width: 0; padding: 16px 0; border-top: 1px solid var(--border-color); }
figcaption { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-weight: 600; }
button { font: inherit; font-size: 12px; color: var(--text-secondary); border: 1px solid var(--border-color); background: var(--bg-secondary); padding: 5px 9px; border-radius: 6px; cursor: pointer; }
button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; }
.analytics-chart { width: 100%; min-width: 0; }
</style>
