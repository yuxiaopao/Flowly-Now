<template>
  <div class="analytics-dashboard">
    <div class="page-header">
      <div class="header-left">
        <h1>数据分析</h1>
        <p class="subtitle">
          监控平台使用情况和性能指标
        </p>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="fetchData"
        />
        <el-button @click="fetchData">
          <RefreshCw class="btn-icon" />
          刷新
        </el-button>
      </div>
    </div>

    <!-- Overview Cards -->
    <div class="overview-cards">
      <div class="overview-card">
        <div class="card-icon workflows">
          <GitBranch />
        </div>
        <div class="card-content">
          <div class="card-value">
            {{ formatNumber(stats.total_workflows) }}
          </div>
          <div class="card-label">
            工作流总数
          </div>
        </div>
        <div
          class="card-trend"
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
        </div>
      </div>

      <div class="overview-card">
        <div class="card-icon executions">
          <Play />
        </div>
        <div class="card-content">
          <div class="card-value">
            {{ formatNumber(stats.total_executions) }}
          </div>
          <div class="card-label">
            执行次数
          </div>
        </div>
        <div
          class="card-trend"
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
        </div>
      </div>

      <div class="overview-card">
        <div class="card-icon tokens">
          <Cpu />
        </div>
        <div class="card-content">
          <div class="card-value">
            {{ formatNumber(stats.total_tokens) }}
          </div>
          <div class="card-label">
            Token 使用量
          </div>
        </div>
      </div>

      <div class="overview-card">
        <div class="card-icon cost">
          <DollarSign />
        </div>
        <div class="card-content">
          <div class="card-value">
            ${{ stats.total_cost?.toFixed(4) || '0.00' }}
          </div>
          <div class="card-label">
            总费用
          </div>
        </div>
      </div>

      <div class="overview-card">
        <div class="card-icon latency">
          <Clock />
        </div>
        <div class="card-content">
          <div class="card-value">
            {{ stats.avg_latency?.toFixed(0) || 0 }}ms
          </div>
          <div class="card-label">
            平均延迟
          </div>
        </div>
      </div>

      <div class="overview-card">
        <div class="card-icon success">
          <CheckCircle />
        </div>
        <div class="card-content">
          <div class="card-value">
            {{ stats.success_rate?.toFixed(1) || 0 }}%
          </div>
          <div class="card-label">
            成功率
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-grid">
      <!-- Execution Trend Chart -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>执行趋势</h3>
          <el-radio-group
            v-model="chartPeriod"
            size="small"
            @change="fetchExecutionTrend"
          >
            <el-radio-button label="7d">
              7天
            </el-radio-button>
            <el-radio-button label="30d">
              30天
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="chart-container">
          <canvas ref="executionTrendChart" />
        </div>
      </div>

      <!-- Usage by Model Chart -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>模型使用分布</h3>
        </div>
        <div class="chart-container">
          <canvas ref="modelUsageChart" />
        </div>
      </div>
    </div>

    <!-- Second Charts Row -->
    <div class="charts-grid">
      <!-- Provider Distribution -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>服务商使用分布</h3>
        </div>
        <div class="chart-container">
          <canvas ref="providerChart" />
        </div>
      </div>

      <!-- Cost Over Time -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>费用趋势</h3>
        </div>
        <div class="chart-container">
          <canvas ref="costChart" />
        </div>
      </div>
    </div>

    <!-- Detailed Tables -->
    <div class="tables-grid">
      <!-- Top Workflows -->
      <div class="table-card">
        <div class="table-header">
          <h3>热门工作流</h3>
        </div>
        <el-table
          :data="topWorkflows"
          stripe
        >
          <el-table-column
            prop="name"
            label="名称"
          />
          <el-table-column
            prop="execution_count"
            label="执行次数"
            width="120"
          >
            <template #default="{ row }">
              {{ row.execution_count?.toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column
            prop="success_rate"
            label="成功率"
            width="100"
          >
            <template #default="{ row }">
              <span :class="row.success_rate >= 90 ? 'text-success' : row.success_rate >= 70 ? 'text-warning' : 'text-danger'">
                {{ row.success_rate?.toFixed(1) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column
            prop="avg_duration"
            label="平均耗时"
            width="100"
          >
            <template #default="{ row }">
              {{ formatDuration(row.avg_duration) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Recent Executions -->
      <div class="table-card">
        <div class="table-header">
          <h3>最近执行记录</h3>
        </div>
        <el-table
          :data="recentExecutions"
          stripe
        >
          <el-table-column
            label="工作流"
            prop="workflow_name"
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
            prop="created_at"
            label="时间"
            width="160"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- API Usage Details -->
    <div class="api-usage-section">
      <div class="section-header">
        <h2>API 使用详情</h2>
      </div>

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
          prop="call_count"
          label="调用次数"
          width="120"
        >
          <template #default="{ row }">
            {{ row.call_count?.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column
          prop="input_tokens"
          label="输入 Token"
          width="140"
        >
          <template #default="{ row }">
            {{ formatNumber(row.input_tokens) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="output_tokens"
          label="输出 Token"
          width="140"
        >
          <template #default="{ row }">
            {{ formatNumber(row.output_tokens) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="total_tokens"
          label="总 Token"
          width="120"
        >
          <template #default="{ row }">
            {{ formatNumber(row.total_tokens) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="cost"
          label="费用"
          width="100"
        >
          <template #default="{ row }">
            ${{ row.cost?.toFixed(4) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  GitBranch, Play, Cpu, DollarSign, Clock, CheckCircle,
  TrendingUp, TrendingDown, RefreshCw
} from 'lucide-vue-next'
import { Chart, registerables } from 'chart.js'
import { useAnalyticsStore } from '@/stores/analytics'

Chart.register(...registerables)

const analyticsStore = useAnalyticsStore()

const dateRange = ref([])
const isLoading = ref(false)
const chartPeriod = ref('7d')

const stats = computed(() => {
  const overview = analyticsStore.overview || {}
  return {
    total_workflows: overview.total_workflows || 0,
    workflows_trend: overview.workflows_trend || 0,
    total_executions: overview.total_executions || 0,
    executions_trend: overview.executions_trend || 0,
    total_tokens: overview.total_tokens || 0,
    total_cost: overview.total_cost || 0,
    avg_latency: overview.avg_latency || 0,
    success_rate: overview.success_rate || 0
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

let charts = {}

function formatNumber(num) {
  if (!num) return '0'
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

async function fetchData() {
  isLoading.value = true
  const params = {}
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0].toISOString()
    params.end_date = dateRange.value[1].toISOString()
  }

  try {
    await analyticsStore.fetchAll(params)
    apiUsageDetails.value = await fetchApiUsageDetails()
  } catch {
    // Error shown via appStore
  } finally {
    isLoading.value = false
  }
}

async function fetchApiUsageDetails() {
  try {
    const res = await analyticsStore.fetchApiUsage()
    return res?.details || res || []
  } catch {
    return []
  }
}

async function fetchExecutionTrend() {
  try {
    await analyticsStore.fetchExecutionTrend({
      period: chartPeriod.value
    })
    updateExecutionTrendChart()
  } catch {
    // Error shown via appStore
  }
}

function generateMockTrendData() {
  const days = chartPeriod.value === '7d' ? 7 : 30
  const data = []
  const now = new Date()

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    data.push({
      date: date.toISOString().split('T')[0],
      executions: Math.floor(Math.random() * 100) + 50,
      success_rate: Math.random() * 10 + 85,
      cost: Math.random() * 5 + 1
    })
  }

  return data
}

function updateExecutionTrendChart() {
  if (charts.executionTrend) {
    charts.executionTrend.destroy()
  }

  const ctx = executionTrendChart.value?.getContext('2d')
  if (!ctx) return

  const trendData = executionTrendData.value.length > 0 ? executionTrendData.value : generateMockTrendData()

  charts.executionTrend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trendData.map(d => d.date.slice(5)),
      datasets: [
        {
          label: '执行次数',
          data: trendData.map(d => d.executions),
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          fill: true,
          tension: 0.4
        },
        {
          label: '成功率',
          data: trendData.map(d => d.success_rate),
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
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
    tokens: d.total_tokens
  }))

  if (data.length === 0) return

  charts.modelUsage = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.model),
      datasets: [{
        data: data.map(d => d.tokens),
        backgroundColor: [
          '#6366f1',
          '#22c55e',
          '#f59e0b',
          '#ef4444',
          '#3b82f6',
          '#06b6d4'
        ]
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
    providerTotals[d.provider] += d.call_count
  })

  if (Object.keys(providerTotals).length === 0) return

  charts.provider = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: Object.keys(providerTotals).map(getProviderLabel),
      datasets: [{
        data: Object.values(providerTotals),
        backgroundColor: [
          '#6366f1',
          '#22c55e',
          '#f59e0b',
          '#ef4444'
        ]
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
  }

  const ctx = costChart.value?.getContext('2d')
  if (!ctx) return

  const trendData = executionTrendData.value.length > 0 ? executionTrendData.value : generateMockTrendData()

  charts.cost = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: trendData.map(d => d.date.slice(5)),
      datasets: [{
        label: '费用 ($)',
        data: trendData.map(d => d.cost),
        backgroundColor: 'rgba(99, 102, 241, 0.6)',
        borderColor: '#6366f1',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: '费用 ($)' }
        }
      }
    }
  })
}

onMounted(async () => {
  await fetchData()
  await fetchExecutionTrend()
  await nextTick()

  updateModelUsageChart()
  updateProviderChart()
  updateCostChart()
})

onUnmounted(() => {
  Object.values(charts).forEach(chart => {
    if (chart) chart.destroy()
  })
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.analytics-dashboard {
  padding: $spacing-6;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;
  flex-wrap: wrap;
  gap: $spacing-4;

  h1 {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    margin: 0;
  }

  .subtitle {
    font-size: $font-size-sm;
    color: var(--text-primary)-secondary;
    margin: $spacing-1 0 0;
  }
}

.header-actions {
  display: flex;
  gap: $spacing-3;
  align-items: center;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: $spacing-4;
  margin-bottom: $spacing-6;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  background: var(--bg-primary)-secondary;
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  position: relative;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 28px;
    height: 28px;
  }

  &.workflows {
    background: rgba($color-primary, 0.15);
    color: $color-primary;
  }

  &.executions {
    background: rgba($color-success, 0.15);
    color: $color-success;
  }

  &.tokens {
    background: rgba($color-secondary, 0.15);
    color: $color-secondary;
  }

  &.cost {
    background: rgba($color-warning, 0.15);
    color: $color-warning;
  }

  &.latency {
    background: rgba(#ef4444, 0.15);
    color: #ef4444;
  }

  &.success {
    background: rgba(#22c55e, 0.15);
    color: #22c55e;
  }
}

.card-content {
  flex: 1;
}

.card-value {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
}

.card-label {
  font-size: $font-size-sm;
  color: var(--text-primary)-secondary;
}

.card-trend {
  position: absolute;
  top: $spacing-3;
  right: $spacing-3;
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;

  .trend-icon {
    width: 14px;
    height: 14px;
  }

  &.up {
    color: $color-success;
  }

  &.down {
    color: $color-error;
  }
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

.chart-card {
  background: var(--bg-primary)-secondary;
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-4;

  h3 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    margin: 0;
  }
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

.table-card {
  background: var(--bg-primary)-secondary;
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
}

.table-header {
  margin-bottom: $spacing-4;

  h3 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    margin: 0;
  }
}

.text-success {
  color: $color-success;
}

.text-warning {
  color: $color-warning;
}

.text-danger {
  color: $color-error;
}

.api-usage-section {
  background: var(--bg-primary)-secondary;
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
}

.section-header {
  margin-bottom: $spacing-4;

  h2 {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    margin: 0;
  }
}
</style>



