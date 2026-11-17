<template>
  <PageShell width="wide">
    <PageHeader
      title="数据分析"
      subtitle="监控平台使用情况和性能指标"
    >
      <template #actions>
        <el-button @click="fetchData">
          <RefreshCw class="btn-icon" />
          刷新
        </el-button>
      </template>
    </PageHeader>

    <PageToolbar>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="fetchData"
      />
    </PageToolbar>

    <div
      v-if="analyticsStore.error"
      class="analytics-feedback"
      role="alert"
    >
      <span>部分统计加载失败：{{ analyticsStore.error }}</span>
      <el-button
        :loading="isLoading"
        @click="fetchData"
      >
        重新加载
      </el-button>
    </div>
    <p class="analytics-scope">
      统计范围与明细使用相同筛选条件。费用为网关日志中的记录值，原日志未记录币种，不等同于完整账单。
    </p>

    <StatGrid
      :columns="6"
      class="overview-stat-grid"
    >
      <StatCard
        label="工作流总数"
        :value="formatNumber(stats.total_workflows)"
        :icon="GitBranch"
        :loading="analyticsStore.moduleLoading.overview"
        tone="primary"
      >
        <template
          v-if="stats.workflows_trend != null"
          #extra
        >
          <span
            class="stat-trend"
            :class="stats.workflows_trend > 0 ? 'up' : 'down'"
          >
            <TrendingUp
              v-if="stats.workflows_trend > 0"
              class="trend-icon"
            />
            <TrendingDown
              v-else
              class="trend-icon"
            />
            {{ Math.abs(stats.workflows_trend) }}%
          </span>
        </template>
      </StatCard>
      <StatCard
        label="执行次数"
        :value="formatNumber(stats.total_executions)"
        :icon="Play"
        :loading="analyticsStore.moduleLoading.overview"
        tone="success"
      >
        <template
          v-if="stats.executions_trend != null"
          #extra
        >
          <span
            class="stat-trend"
            :class="stats.executions_trend > 0 ? 'up' : 'down'"
          >
            <TrendingUp
              v-if="stats.executions_trend > 0"
              class="trend-icon"
            />
            <TrendingDown
              v-else
              class="trend-icon"
            />
            {{ Math.abs(stats.executions_trend) }}%
          </span>
        </template>
      </StatCard>
      <StatCard
        label="Token 使用量"
        :value="formatNumber(stats.total_tokens)"
        :icon="Cpu"
        :loading="analyticsStore.moduleLoading.overview"
        tone="info"
      />
      <StatCard
        label="网关记录费用"
        :value="stats.total_cost == null ? '—' : Number(stats.total_cost).toFixed(4)"
        :icon="DollarSign"
        :loading="analyticsStore.moduleLoading.overview"
        tone="warning"
      />
      <StatCard
        label="平均延迟"
        :value="stats.avg_latency == null ? '—' : `${Number(stats.avg_latency).toFixed(0)}ms`"
        :icon="Clock"
        :loading="analyticsStore.moduleLoading.overview"
        tone="neutral"
      />
      <StatCard
        label="成功率"
        :value="stats.success_rate == null ? '—' : `${Number(stats.success_rate).toFixed(1)}%`"
        :icon="CheckCircle"
        :loading="analyticsStore.moduleLoading.overview"
        tone="success"
      />
    </StatGrid>

    <!-- Charts Row -->
    <div class="charts-grid">
      <SectionCard
        title="执行趋势"
        class="analytics-section"
      >
        <template #actions>
          <el-radio-group
            v-model="chartPeriod"
            size="small"
            @change="fetchExecutionTrend"
          >
            <el-radio-button value="7d">
              7天
            </el-radio-button>
            <el-radio-button value="30d">
              30天
            </el-radio-button>
          </el-radio-group>
        </template>
        <div class="chart-container">
          <canvas ref="executionTrendChart" />
        </div>
      </SectionCard>

      <SectionCard
        title="模型使用分布"
        class="analytics-section"
      >
        <div class="chart-container">
          <canvas ref="modelUsageChart" />
        </div>
      </SectionCard>
    </div>

    <!-- Second Charts Row -->
    <div class="charts-grid">
      <SectionCard
        title="服务商使用分布"
        class="analytics-section"
      >
        <div class="chart-container">
          <canvas ref="providerChart" />
        </div>
      </SectionCard>

      <SectionCard
        title="费用趋势"
        class="analytics-section"
      >
        <div class="chart-container">
          <canvas ref="costChart" />
        </div>
      </SectionCard>
    </div>

    <!-- Detailed Tables -->
    <div class="tables-grid">
      <SectionCard title="热门工作流">
        <el-table
          :data="topWorkflows"
          stripe
        >
          <el-table-column
            prop="name"
            label="名称"
          />
          <el-table-column
            prop="executionCount"
            label="执行次数"
            width="120"
          >
            <template #default="{ row }">
              {{ row.executionCount?.toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column
            prop="successRate"
            label="成功率"
            width="100"
          >
            <template #default="{ row }">
              <span :class="row.successRate >= 90 ? 'text-success' : row.successRate >= 70 ? 'text-warning' : 'text-danger'">
                {{ row.successRate?.toFixed(1) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column
            prop="avgDuration"
            label="平均耗时"
            width="100"
          >
            <template #default="{ row }">
              {{ formatDuration(row.avgDuration) }}
            </template>
          </el-table-column>
        </el-table>
      </SectionCard>

      <SectionCard title="最近执行记录">
        <el-table
          :data="recentExecutions"
          stripe
        >
          <el-table-column
            label="工作流"
            prop="workflowName"
          />
          <el-table-column
            prop="status"
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                :type="getStatusType(row.status)"
                size="small"
              >
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="duration"
            label="耗时"
            width="100"
          >
            <template #default="{ row }">
              {{ formatDuration(row.duration) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="startedAt"
            label="时间"
            width="160"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.startedAt) }}
            </template>
          </el-table-column>
        </el-table>
      </SectionCard>
    </div>

    <SectionCard
      title="API 使用详情"
      class="analytics-section--full"
    >
      <el-table
        :data="apiUsageDetails"
        stripe
      >
        <el-table-column
          prop="model"
          label="模型"
        />
        <el-table-column
          prop="provider"
          label="服务商"
          width="120"
        >
          <template #default="{ row }">
            {{ getProviderLabel(row.provider) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="callCount"
          label="调用次数"
          width="120"
        >
          <template #default="{ row }">
            {{ row.callCount?.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column
          prop="inputTokens"
          label="输入 Token"
          width="140"
        >
          <template #default="{ row }">
            {{ formatNumber(row.inputTokens) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="outputTokens"
          label="输出 Token"
          width="140"
        >
          <template #default="{ row }">
            {{ formatNumber(row.outputTokens) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="totalTokens"
          label="总 Token"
          width="120"
        >
          <template #default="{ row }">
            {{ formatNumber(row.totalTokens) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="cost"
          label="费用"
          width="100"
        >
          <template #default="{ row }">
            {{ row.cost == null ? '—' : Number(row.cost).toFixed(4) }}
          </template>
        </el-table-column>
      </el-table>
    </SectionCard>
  </PageShell>
</template>

<script setup>
import PageToolbar from '@/components/layout/PageToolbar.vue'
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  GitBranch, Play, Cpu, DollarSign, Clock, CheckCircle,
  TrendingUp, TrendingDown, RefreshCw
} from 'lucide-vue-next'
import { Chart, registerables } from 'chart.js'
import { useAnalyticsStore } from '@/stores/analytics'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatGrid from '@/components/layout/StatGrid.vue'
import StatCard from '@/components/layout/StatCard.vue'
import SectionCard from '@/components/layout/SectionCard.vue'
import {
  getChartSeriesColors,
  getChartPrimaryColor,
  getChartPrimaryFill,
  getChartSuccessColor,
  getChartSuccessFill,
  getCssColor,
} from '@/utils/chartTheme'
import { useThemeChartRefresh } from '@/composables/useThemeChartRefresh'

Chart.register(...registerables)

const analyticsStore = useAnalyticsStore()

const dateRange = ref([])
const isLoading = ref(false)
const chartPeriod = ref('7d')

const stats = computed(() => {
  const overview = analyticsStore.overview || {}
  return {
    total_workflows: overview.totalWorkflows ?? null,
    workflows_trend: overview.workflowsTrend ?? null,
    total_executions: overview.totalExecutions ?? null,
    executions_trend: overview.executionsTrend ?? null,
    total_tokens: overview.totalTokens ?? null,
    total_cost: overview.totalCost ?? null,
    avg_latency: overview.avgLatency ?? null,
    success_rate: overview.successRate ?? null
  }
})

const topWorkflows = computed(() => analyticsStore.topWorkflows)
const recentExecutions = computed(() => analyticsStore.recentExecutions)
const apiUsageDetails = ref([])
const executionTrendData = computed(() => analyticsStore.executionTrend)

const executionTrendChart = ref(null)
const modelUsageChart = ref(null)
const providerChart = ref(null)
const costChart = ref(null)

const charts = {}

function formatNumber(num) {
  if (num == null) return '—'
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`
  return num.toString()
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function formatDateTime(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

function getStatusType(status) {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return types[status] || 'info'
}

function getStatusLabel(status) {
  const labels = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return labels[status] || status
}

function getProviderLabel(provider) {
  const labels = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    azure: 'Azure',
    google: 'Google'
  }
  return labels[provider] || provider
}

let dataRevision = 0
let disposed = false
function queryParams() {
  const params = { period: chartPeriod.value }
  if (dateRange.value?.length === 2) {
    params.start_date = new Date(dateRange.value[0]).toISOString()
    const end = new Date(dateRange.value[1])
    end.setHours(23, 59, 59, 999)
    params.end_date = end.toISOString()
  }
  return params
}
async function fetchData() {
  const revision = ++dataRevision
  isLoading.value = true
  try {
    await analyticsStore.fetchAll(queryParams())
    if (disposed || revision !== dataRevision) return
    const usage = analyticsStore.apiUsage
    apiUsageDetails.value = Array.isArray(usage) ? usage : (usage?.details || [])
    await nextTick()
    if (!disposed && revision === dataRevision) refreshAllCharts()
  } finally {
    if (!disposed && revision === dataRevision) isLoading.value = false
  }
}
async function fetchExecutionTrend() { await fetchData() }

function updateExecutionTrendChart() {
  if (charts.executionTrend) {
    charts.executionTrend.destroy()
    charts.executionTrend = null
  }

  const ctx = executionTrendChart.value?.getContext('2d')
  if (!ctx) return

  const trendData = executionTrendData.value
  if (trendData.length === 0) return

  charts.executionTrend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trendData.map(d => d.date.slice(5)),
      datasets: [
        {
          label: '执行次数',
          data: trendData.map(d => d.executions),
          borderColor: getChartPrimaryColor(),
          backgroundColor: getChartPrimaryFill(),
          fill: true,
          tension: 0.4
        },
        {
          label: '成功率',
          data: trendData.map(d => d.successRate),
          borderColor: getChartSuccessColor(),
          backgroundColor: getChartSuccessFill(),
          fill: true,
          tension: 0.4,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: { display: true, text: '执行次数' }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          min: 0,
          max: 100,
          title: { display: true, text: '成功率 (%)' },
          grid: { drawOnChartArea: false }
        }
      }
    }
  })
}

function updateModelUsageChart() {
  if (charts.modelUsage) {
    charts.modelUsage.destroy()
  }

  const ctx = modelUsageChart.value?.getContext('2d')
  if (!ctx) return

  const data = apiUsageDetails.value.map(d => ({
    model: d.model,
    tokens: d.totalTokens
  }))

  if (data.length === 0) return

  charts.modelUsage = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.model),
      datasets: [{
        data: data.map(d => d.tokens),
        backgroundColor: getChartSeriesColors(),
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right'
        }
      }
    }
  })
}

function updateProviderChart() {
  if (charts.provider) {
    charts.provider.destroy()
  }

  const ctx = providerChart.value?.getContext('2d')
  if (!ctx) return

  const providerTotals = {}
  apiUsageDetails.value.forEach(d => {
    if (!providerTotals[d.provider]) {
      providerTotals[d.provider] = 0
    }
    providerTotals[d.provider] += d.callCount
  })

  if (Object.keys(providerTotals).length === 0) return

  charts.provider = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: Object.keys(providerTotals).map(getProviderLabel),
      datasets: [{
        data: Object.values(providerTotals),
        backgroundColor: getChartSeriesColors().slice(0, 4),
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right'
        }
      }
    }
  })
}

function updateCostChart() {
  if (charts.cost) {
    charts.cost.destroy()
    charts.cost = null
  }

  const ctx = costChart.value?.getContext('2d')
  if (!ctx) return

  const trendData = executionTrendData.value
  if (!trendData.some(item => item.cost != null)) return

  charts.cost = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: trendData.map(d => d.date.slice(5)),
      datasets: [{
        label: '网关记录费用',
        data: trendData.map(d => d.cost),
        backgroundColor: getCssColor('--color-primary-50', 'rgba(6, 182, 212, 0.5)'),
        borderColor: getChartPrimaryColor(),
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: '网关记录费用' }
        }
      }
    }
  })
}

function refreshAllCharts() {
  updateExecutionTrendChart()
  updateModelUsageChart()
  updateProviderChart()
  updateCostChart()
}

onMounted(async () => {
  await fetchData()

})

useThemeChartRefresh(refreshAllCharts)

onUnmounted(() => {
  disposed = true
  dataRevision++
  Object.values(charts).forEach(chart => {
    if (chart) chart.destroy()
  })
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.analytics-feedback { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: $spacing-3; margin-bottom: $spacing-4; padding: $spacing-3 $spacing-4; background: var(--error-bg); border: 1px solid var(--border-primary); border-radius: var(--radius-lg); font-size: $font-size-sm; }
.analytics-scope { margin-bottom: $spacing-4; color: var(--text-tertiary); font-size: $font-size-xs; line-height: $line-height-normal; }


.overview-stat-grid {
  margin-bottom: $spacing-6;
}

.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;

  &.up {
    color: var(--color-success);
  }

  &.down {
    color: var(--color-danger);
  }

  .trend-icon {
    width: 14px;
    height: 14px;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-4;
  margin-bottom: $spacing-6;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.analytics-section--full {
  margin-bottom: $spacing-6;
}

.chart-container {
  height: 280px;
  position: relative;
}

.tables-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-4;
  margin-bottom: $spacing-6;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.text-success {
  color: var(--color-success);
}

.text-warning {
  color: var(--color-warning);
}

.text-danger {
  color: var(--color-danger);
}
</style>



