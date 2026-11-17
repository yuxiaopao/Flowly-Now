<template>
  <section
    class="yolo-analytics"
    data-testid="yolo-run-analytics"
    aria-label="YOLO 训练图表分析"
  >
    <header class="analysis-header">
      <div>
        <p class="analysis-kicker">
          YOLO · 训练分析
        </p><h2>{{ run?.name || '正在读取训练图表' }}</h2><p
          v-if="run"
          class="muted"
        >
          {{ run.model.label }} · {{ TASK_LABELS[run.task] }} · {{ STATUS_LABELS[run.status] || run.status }} · {{ run.current_epoch }} / {{ run.total_epochs }} 轮
        </p>
      </div>
      <div class="analysis-actions">
        <span
          class="muted"
          role="status"
        >{{ loading ? '同步中…' : updatedAt ? `同步于 ${updatedAt}` : '' }}</span><button
          type="button"
          :disabled="loading"
          @click="refresh"
        >
          刷新图表
        </button>
      </div>
    </header>
    <p
      v-if="error"
      class="analysis-notice error"
      role="alert"
    >
      {{ error }}<button
        type="button"
        :disabled="loading"
        @click="refresh"
      >
        重试
      </button>
    </p>
    <p
      v-for="warning in run?.warnings || []"
      :key="warning"
      class="analysis-notice"
    >
      {{ warning }}
    </p>
    <div
      v-if="!run && !error"
      class="analysis-empty"
      role="status"
    >
      正在读取当前节点的训练记录…
    </div>
    <template v-if="run">
      <div class="analysis-stats">
        <div><span>{{ primary ? `最近验证 ${metricLabel(primary)}` : '最近验证指标' }}</span><strong>{{ formatMetric(latest?.[primary]) }}</strong><small>第 {{ latest?.epoch || '—' }} 轮</small></div>
        <div><span>最高验证指标</span><strong>{{ formatMetric(best?.value) }}</strong><small>第 {{ best?.epoch || '—' }} 轮，来自训练期间验证</small></div>
        <div><span>最终验证集 {{ run.task === 'classify' ? 'Top-1' : '评估' }}</span><strong>{{ formatMetric(run.reports.validation?.top1) }}</strong><small>{{ run.reports.validation ? `${run.reports.validation.images} 个样本，最佳检查点` : '完整评估尚未生成' }}</small></div>
        <div><span>独立测试集 {{ run.task === 'classify' ? 'Top-1' : '评估' }}</span><strong>{{ formatMetric(run.reports.test?.top1) }}</strong><small>{{ run.reports.test ? `${run.reports.test.images} 个样本，未参与模型选择` : '独立测试尚未生成' }}</small></div>
      </div>
      <div
        class="analysis-tabs"
        role="tablist"
        aria-label="分析图表类型"
        @keydown="moveTab"
      >
        <button
          v-for="tab in tabs"
          :id="`analysis-tab-${instanceId}-${tab.id}`"
          :key="tab.id"
          role="tab"
          type="button"
          :aria-selected="activeTab === tab.id"
          :tabindex="activeTab === tab.id ? 0 : -1"
          :aria-controls="`analysis-panel-${instanceId}`"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
      <div
        :id="`analysis-panel-${instanceId}`"
        role="tabpanel"
        :aria-labelledby="`analysis-tab-${instanceId}-${activeTab}`"
      >
        <template v-if="activeTab === 'curves'">
          <p class="muted">
            图表按实际任务和 CSV 字段生成；悬停查看数值，滚轮或拖动滑块缩放，点击图例筛选曲线。
          </p>
          <div
            v-if="!run.history.length"
            class="analysis-empty"
          >
            等待首轮训练与验证完成，指标写入后会自动出现。
          </div>
          <YoloAnalyticsChart
            v-if="groups.losses.length"
            title="训练与验证损失"
            :option="lineOptions(run.history, groups.losses)"
          />
          <YoloAnalyticsChart
            v-for="group in groups.quality"
            :key="group.label"
            :title="group.label"
            :option="lineOptions(run.history, group.series, true)"
          />
          <div class="analysis-chart-grid">
            <YoloAnalyticsChart
              v-if="groups.learningRates.length"
              title="学习率"
              :option="lineOptions(run.history, groups.learningRates)"
            />
            <YoloAnalyticsChart
              v-if="epochTimes.length"
              title="每轮耗时（秒）"
              :option="lineOptions(epochTimes, ['epoch_seconds'])"
            />
          </div>
          <details class="analysis-data">
            <summary>查看本轮图表的原始数值</summary><div class="analysis-table">
              <table>
                <thead>
                  <tr>
                    <th>轮次</th><th
                      v-for="key in historyKeys"
                      :key="key"
                    >
                      {{ key }}
                    </th>
                  </tr>
                </thead><tbody>
                  <tr
                    v-for="row in run.history"
                    :key="row.epoch"
                  >
                    <td>{{ row.epoch }}</td><td
                      v-for="key in historyKeys"
                      :key="key"
                    >
                      {{ row[key] ?? '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>
        </template>
        <template v-else-if="activeTab === 'confusion' || activeTab === 'classes'">
          <div class="analysis-controls">
            <label>评估集合 <select v-model="split"><option value="test">独立测试集</option><option value="validation">完整验证集</option></select></label>
            <label v-if="activeTab === 'confusion'">矩阵数值 <select v-model="matrixMode"><option value="count">样本数量</option><option value="normalized">按真实类别归一化</option></select></label>
            <label v-else>逐类指标 <select v-model="classMetric"><option value="f1">F1</option><option value="precision">Precision</option><option value="recall">Recall</option></select></label>
            <span class="muted">{{ report ? `${report.images} 个样本 · Macro-F1 ${formatMetric(report.macro_f1)}` : '该评估报告尚未生成' }}</span>
          </div>
          <template v-if="activeTab === 'confusion'">
            <p class="muted">
              纵轴是真实类别，横轴是预测类别。归一化按每个真实类别的样本总数计算；空类别记为 0。
            </p>
            <YoloAnalyticsChart
              v-if="matrixOption"
              :title="`${splitLabel}混淆矩阵`"
              :option="matrixOption"
              :height="680"
            />
            <div
              v-else
              class="analysis-empty"
            >
              {{ report ? '本次评估未保存数值混淆矩阵，可在“原生图表”查看已生成的矩阵图片。' : '等待完整评估报告；训练期间不会使用虚构的混淆矩阵。' }}
            </div>
            <template v-if="matrixData">
              <h3>最常见的误分类</h3><div class="analysis-table">
                <table>
                  <thead><tr><th>真实类别</th><th>预测类别</th><th>错误样本</th><th>占真实类别比例</th></tr></thead><tbody>
                    <tr
                      v-for="item in matrixData.errors"
                      :key="`${item.actual}-${item.predicted}`"
                    >
                      <td>{{ labelMap.get(item.actual) || item.actual }}</td><td>{{ labelMap.get(item.predicted) || item.predicted }}</td><td>{{ item.count }}</td><td>{{ formatMetric(item.ratio) }}</td>
                    </tr><tr v-if="!matrixData.errors.length">
                      <td colspan="4">
                        此评估集合未出现误分类。
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </template>
          <template v-else>
            <YoloAnalyticsChart
              v-if="perClass.length"
              :title="`${splitLabel}逐类${classMetric.toUpperCase()}`"
              :option="classOptions(perClass, classMetric)"
              :height="560"
            />
            <div
              v-else
              class="analysis-empty"
            >
              本次尚未生成逐类评估报告；可查看“原生图表”中对应任务的 PR、F1 和验证预测图。
            </div>
            <div
              v-if="perClass.length"
              class="analysis-table"
            >
              <table>
                <thead><tr><th>类别</th><th>Precision</th><th>Recall</th><th>F1</th><th>样本数</th></tr></thead><tbody>
                  <tr
                    v-for="item in perClass"
                    :key="item.key"
                  >
                    <td>{{ item.label }}<small>{{ item.key }}</small></td><td>{{ formatMetric(item.precision) }}</td><td>{{ formatMetric(item.recall) }}</td><td>{{ formatMetric(item.f1) }}</td><td>{{ item.support }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </template>
        <template v-else-if="activeTab === 'native'">
          <p class="muted">
            直接读取本次训练生成的图表与批次预览。检测、分割、姿态和分类任务会生成不同类型的图片；文件更新后自动刷新。
          </p>
          <p
            v-if="plotsError"
            class="analysis-notice error"
            role="alert"
          >
            {{ plotsError }}
          </p>
          <YoloNativePlotsPanel
            :job-id="jobId"
            :plots="plots"
            :fetch-plot-blob="fetchPlot"
          />
        </template>
        <template v-else-if="activeTab === 'compare'">
          <div class="analysis-controls">
            <label>添加训练记录 <select v-model="candidateId"><option value="">选择已有 YOLO 训练记录</option><option
              v-for="item in candidates"
              :key="item.id"
              :value="item.id"
              :disabled="selectedIds.includes(item.id)"
            >{{ item.name }} · {{ item.yoloVersion || item.yolo_version }}{{ item.modelVariant || item.model_variant }}</option></select></label><button
              type="button"
              :disabled="!candidateId || comparing || selectedIds.length >= ANALYTICS.maxCompare"
              @click="addComparison"
            >
              加入对比
            </button>
          </div>
          <p class="muted">
            最多比较 {{ ANALYTICS.maxCompare }} 条真实训练记录；候选列表展示最近 {{ ANALYTICS.pageSize }} 条可访问记录。同一任务、同一数据划分才适合直接比较。
          </p>
          <p
            v-if="comparisonError"
            class="analysis-notice error"
            role="alert"
          >
            {{ comparisonError }}
          </p>
          <p
            v-if="comparisonNotice"
            class="analysis-notice"
          >
            {{ comparisonNotice }}
          </p>
          <p
            v-if="comparisonRuns.length === 1"
            class="analysis-empty"
          >
            当前只选择了 {{ run.model.label }} 的真实结果。其他 YOLO 模型需有训练记录后加入对比。
          </p>
          <div class="analysis-table">
            <table>
              <thead><tr><th>模型 / 训练记录</th><th>任务</th><th>轮次</th><th>最佳验证指标</th><th>独立测试 Top-1</th><th>操作</th></tr></thead><tbody>
                <tr
                  v-for="item in comparisonRuns"
                  :key="item.id"
                >
                  <td>{{ item.model.label }}<small>{{ item.name }}</small></td><td>{{ TASK_LABELS[item.task] }}</td><td>{{ item.current_epoch }} / {{ item.total_epochs }}</td><td>{{ formatMetric(bestValue(item)?.value) }}<small>{{ primaryMetric(item) ? metricLabel(primaryMetric(item)) : '尚无验证指标' }}</small></td><td>{{ item.task === 'classify' ? formatMetric(item.reports.test?.top1) : '不适用' }}</td><td>
                    <button
                      v-if="item.id !== jobId"
                      type="button"
                      @click="removeComparison(item.id)"
                    >
                      移除
                    </button><span v-else>当前节点</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <YoloAnalyticsChart
            v-if="comparisonOption"
            title="模型验证指标对比"
            :option="comparisonOption"
          />
        </template>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch, getCurrentInstance } from 'vue'
import trainingApi from '@/api/training'
import YoloAnalyticsChart from './YoloAnalyticsChart.vue'
import YoloNativePlotsPanel from './YoloNativePlotsPanel.vue'
import { ANALYTICS, TASK_LABELS, STATUS_LABELS, formatMetric, metricLabel, metricGroups, primaryMetric, bestValue, lineOptions, confusionData, confusionOptions, classRows, classOptions, comparisonWarning } from './analyticsMetrics'

const props = defineProps({ jobId: { type: String, required: true } })
const instanceId = getCurrentInstance().uid
const tabs = [{ id: 'curves', label: '训练曲线' }, { id: 'confusion', label: '混淆矩阵' }, { id: 'classes', label: '逐类表现' }, { id: 'native', label: '原生图表' }, { id: 'compare', label: '模型对比' }]
const activeTab = ref('curves')
const run = ref(null)
const loading = ref(false)
const error = ref('')
const plots = ref([])
const plotsError = ref('')
const updatedAt = ref('')
const split = ref('test')
const matrixMode = ref('count')
const classMetric = ref('f1')
const candidates = ref([])
const candidateId = ref('')
const selectedIds = ref([])
const comparisons = ref([])
const comparing = ref(false)
const comparisonError = ref('')
let alive = true
let generation = 0
let timer
const inFlight = new Set()
const groups = computed(() => metricGroups(run.value?.history || []))
const primary = computed(() => run.value ? primaryMetric(run.value) : null)
const latest = computed(() => run.value?.history.at(-1))
const best = computed(() => run.value ? bestValue(run.value) : null)
const report = computed(() => run.value?.reports[split.value])
const splitLabel = computed(() => split.value === 'test' ? '独立测试集' : '完整验证集')
const labelMap = computed(() => new Map((run.value?.classes || []).map(item => [item.key, item.label])))
const matrixOption = computed(() => confusionOptions(report.value, labelMap.value, matrixMode.value))
const matrixData = computed(() => confusionData(report.value))
const perClass = computed(() => classRows(report.value, run.value?.classes || []))
const historyKeys = computed(() => [...groups.value.losses, ...groups.value.quality.flatMap(group => group.series), ...groups.value.learningRates])
const epochTimes = computed(() => (run.value?.history || []).flatMap((row, index, rows) => {
  const previous = index ? rows[index - 1].time : 0
  return Number.isFinite(row.time) && Number.isFinite(previous) && row.time >= previous ? [{ epoch: row.epoch, epoch_seconds: row.time - previous }] : []
}))
const comparisonRuns = computed(() => run.value ? [run.value, ...comparisons.value] : [])
const comparisonNotice = computed(() => comparisonWarning(comparisonRuns.value))
const comparisonOption = computed(() => {
  if (!run.value || comparisonRuns.value.some(item => item.task !== run.value.task)) return null
  const key = primary.value
  if (!key || comparisonRuns.value.some(item => !item.history.some(row => Number.isFinite(row[key])))) return null
  const option = lineOptions([], [], true)
  option.series = comparisonRuns.value.map(item => ({ name: `${item.model.label} · ${item.name}`, type: 'line', connectNulls: false, data: item.history.map(row => [row.epoch, row[key] ?? null]) }))
  return option
})

async function refresh() {
  if (inFlight.has(generation) || !props.jobId || document.hidden) return
  const version = generation
  const id = props.jobId
  inFlight.add(version)
  loading.value = true
  try {
    const comparisonIds = comparisons.value.map(item => item.id)
    const [analytics, images, ...updates] = await Promise.allSettled([
      trainingApi.getYoloAnalytics(id), trainingApi.getYoloTrainingPlots(id),
      ...comparisonIds.map(otherId => trainingApi.getYoloAnalytics(otherId)),
    ])
    if (!alive || generation !== version) return
    if (analytics.status === 'fulfilled') {
      run.value = analytics.value
      error.value = ''
      updatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    } else error.value = analytics.reason?.message || '训练图表读取失败，请重试。'
    if (images.status === 'fulfilled') { plots.value = images.value.plots || []; plotsError.value = '' }
    else plotsError.value = images.reason?.message || '原生图表目录暂时不可读。'
    comparisons.value = comparisons.value.map(item => {
      const update = updates[comparisonIds.indexOf(item.id)]
      return update?.status === 'fulfilled' ? update.value : item
    })
  } finally {
    inFlight.delete(version)
    if (alive && generation === version) loading.value = false
  }
}
async function fetchPlot(id, name) { return URL.createObjectURL(await trainingApi.getYoloPlotImage(id, name)) }
async function loadCandidates() {
  const version = generation
  try {
    const response = await trainingApi.listYoloRuns({ page_size: ANALYTICS.pageSize })
    if (alive && version === generation) candidates.value = response.results || response || []
  } catch (failure) { if (alive && version === generation) comparisonError.value = failure.message || '训练记录列表加载失败。' }
}
async function addComparison() {
  if (!candidateId.value || comparing.value || selectedIds.value.length >= ANALYTICS.maxCompare) return
  const version = generation
  const id = candidateId.value
  comparing.value = true
  comparisonError.value = ''
  try {
    const item = await trainingApi.getYoloAnalytics(id)
    if (!alive || version !== generation) return
    if (item.task !== run.value.task) throw new Error('该记录的任务类型不同，请选择相同任务进行对比。')
    if (selectedIds.value.includes(id)) return
    comparisons.value.push(item)
    selectedIds.value.push(id)
    candidateId.value = ''
  } catch (failure) { if (alive && version === generation) comparisonError.value = failure.message || '对比记录加载失败。' }
  finally { if (alive && version === generation) comparing.value = false }
}
function removeComparison(id) { comparisons.value = comparisons.value.filter(item => item.id !== id); selectedIds.value = selectedIds.value.filter(value => value !== id) }
function moveTab(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const index = tabs.findIndex(tab => tab.id === activeTab.value)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
  activeTab.value = tabs[next].id
  event.currentTarget.querySelectorAll('[role=tab]')[next]?.focus()
}
watch(() => props.jobId, () => {
  generation++
  run.value = null; error.value = ''; plots.value = []; comparisons.value = []; candidateId.value = ''; candidates.value = []; comparisonError.value = ''
  selectedIds.value = [props.jobId]
  comparing.value = false
  refresh()
}, { immediate: true })
watch(activeTab, tab => { if (tab === 'compare') loadCandidates() })
function onVisibility() { if (!document.hidden) refresh() }
onMounted(() => { timer = setInterval(refresh, ANALYTICS.pollMs); document.addEventListener('visibilitychange', onVisibility) })
onBeforeUnmount(() => { alive = false; generation++; clearInterval(timer); document.removeEventListener('visibilitychange', onVisibility) })
</script>

<style scoped>
.yolo-analytics { color: var(--text-primary); background: var(--bg-primary); padding: 20px; min-width: 0; }
.analysis-header { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.analysis-header h2 { font-size: 21px; margin: 0 0 8px; line-height: 1.5; overflow-wrap: anywhere; }
.analysis-kicker { font-size: 12px; color: var(--primary-color); margin: 0 0 6px; }
.muted, small { color: var(--text-secondary); font-size: 12px; line-height: 1.7; }
.analysis-actions, .analysis-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
button, select { color: var(--text-primary); background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 6px; padding: 7px 10px; font: inherit; cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
button:focus-visible, select:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; }
.analysis-controls { margin: 16px 0; }
.analysis-controls label { display: flex; align-items: center; gap: 8px; min-width: 0; font-size: 13px; }
select { max-width: min(420px, 65vw); }
.analysis-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); padding: 20px 0; gap: 18px; }
.analysis-stats span, .analysis-stats strong, small { display: block; }
.analysis-stats span { font-size: 12px; color: var(--text-secondary); }
.analysis-stats strong { font-size: 24px; font-variant-numeric: tabular-nums; line-height: 1.8; }
.analysis-tabs { display: flex; overflow-x: auto; gap: 24px; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); }
.analysis-tabs button { white-space: nowrap; border: none; border-bottom: 2px solid transparent; border-radius: 0; background: none; padding: 10px 0; color: var(--text-secondary); }
.analysis-tabs button[aria-selected=true] { border-color: var(--primary-color); color: var(--text-primary); }
.analysis-chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.analysis-empty { padding: 24px; margin: 16px 0; background: var(--bg-secondary); color: var(--text-secondary); font-size: 13px; }
.analysis-notice { padding: 10px 12px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; font-size: 13px; }
.analysis-notice.error { color: var(--error); }
.analysis-notice button { margin-left: 12px; }
.analysis-table { max-width: 100%; overflow: auto; margin-top: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { text-align: left; padding: 10px; border-bottom: 1px solid var(--border-color); white-space: nowrap; font-variant-numeric: tabular-nums; }
th { background: var(--bg-secondary); color: var(--text-secondary); font-weight: 500; }
.analysis-data { margin: 16px 0; }
summary { cursor: pointer; font-size: 13px; }
@media (max-width: 800px) { .analysis-header { flex-direction: column; } .analysis-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } .analysis-chart-grid { grid-template-columns: minmax(0, 1fr); } .yolo-analytics { padding: 12px; } }
</style>
