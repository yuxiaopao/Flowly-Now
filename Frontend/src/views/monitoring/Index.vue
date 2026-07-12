<template>
  <PageShell width="wide">
    <PageHeader
      title="执行监控"
      subtitle="实时监控工作流执行状态和系统健康度"
    />

    <StatGrid>
      <StatCard
        label="总执行次数"
        :value="stats.totalExecutions"
        :icon="Activity"
        tone="neutral"
      />
      <StatCard
        label="成功率"
        :value="`${stats.successRate}%`"
        :icon="CheckCircle"
        tone="success"
      >
        <template #extra>
          <el-tag
            size="small"
            type="success"
          >
            <TrendingUp class="trend-icon" /> +{{ stats.successTrend }}%
          </el-tag>
        </template>
      </StatCard>
      <StatCard
        label="平均执行时间"
        :value="`${stats.avgDuration}ms`"
        :icon="Clock"
        tone="info"
      />
      <StatCard
        label="活跃工作流"
        :value="stats.activeWorkflows"
        :icon="Zap"
        tone="warning"
      />
    </StatGrid>

    <!-- Main Content Grid -->
    <div class="dashboard-grid">
      <!-- Real-time Execution Monitor -->
      <SectionCard
        title="实时执行"
        class="monitor-section monitor-section--full"
      >
        <template #actions>
          <el-tag
            size="small"
            type="danger"
            class="live-indicator"
          >
            <span class="pulse-dot" /> LIVE
          </el-tag>
        </template>

        <el-table 
          v-loading="isLoadingActive" 
          :data="activeExecutions" 
          size="small"
          max-height="200"
        >
          <el-table-column
            label="工作流"
            prop="workflowName"
            min-width="120"
          />
          <el-table-column
            label="当前节点"
            prop="currentNodeId"
            min-width="100"
          />
          <el-table-column
            label="进度"
            width="140"
          >
            <template #default="{ row }">
              <el-progress 
                :percentage="row.progress || 0" 
                :stroke-width="8"
                :color="getProgressColor(row.progress)"
              />
            </template>
          </el-table-column>
          <el-table-column
            label="耗时"
            width="90"
          >
            <template #default="{ row }">
              {{ row.duration ? row.duration + 'ms' : '-' }}
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="90"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="getStatusType(row.status)"
              >
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="80"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button 
                v-if="row.status === 'running'" 
                size="small" 
                link
                @click="pauseExecution(row.id)"
              >
                暂停
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="!isLoadingActive && activeExecutions.length === 0"
          class="empty-table"
        >
          <span>暂无正在执行的流程</span>
        </div>
      </SectionCard>

      <!-- Execution Trend Chart -->
      <SectionCard
        title="执行趋势"
        class="monitor-section monitor-section--chart"
      >
        <template #actions>
          <el-radio-group
            v-model="trendPeriod"
            size="small"
            @change="loadTrendData"
          >
            <el-radio-button value="day">
              今天
            </el-radio-button>
            <el-radio-button value="week">
              7天
            </el-radio-button>
            <el-radio-button value="month">
              30天
            </el-radio-button>
          </el-radio-group>
        </template>
        
        <div
          ref="trendChartRef"
          v-loading="isLoadingTrend"
          class="trend-chart"
          style="height: 280px;"
        />
      </SectionCard>

      <!-- Workflow Health -->
      <SectionCard
        title="工作流健康度"
        class="monitor-section monitor-section--health"
      >
        <div
          v-loading="isLoadingHealth"
          class="health-grid"
        >
          <div 
            v-for="workflow in workflowHealth" 
            :key="workflow.id" 
            class="health-item"
          >
            <div class="health-header">
              <span class="workflow-name">{{ workflow.name }}</span>
              <el-tag 
                size="small" 
                :type="getHealthType(workflow.healthScore)"
              >
                {{ workflow.healthScore }}分
              </el-tag>
            </div>
            <el-progress 
              :percentage="workflow.healthScore" 
              :stroke-width="6"
              :color="getHealthColor(workflow.healthScore)"
              :show-text="false"
            />
            <div class="health-stats">
              <span>成功率: {{ workflow.successRate }}%</span>
              <span>平均耗时: {{ workflow.avgDuration }}ms</span>
            </div>
          </div>

          <div
            v-if="!isLoadingHealth && workflowHealth.length === 0"
            class="empty-health"
          >
            <span>暂无工作流数据</span>
          </div>
        </div>
      </SectionCard>

      <!-- Alert Rules -->
      <SectionCard
        title="告警规则"
        class="monitor-section monitor-section--full"
      >
        <template #actions>
          <el-button
            type="primary"
            size="small"
            @click="showAlertDialog = true"
          >
            <Plus class="icon" /> 添加规则
          </el-button>
        </template>

        <el-table
          v-loading="isLoadingRules"
          :data="alertRules"
          size="small"
        >
          <el-table-column
            label="规则名称"
            prop="name"
            min-width="120"
          />
          <el-table-column
            label="类型"
            width="120"
          >
            <template #default="{ row }">
              <el-tag size="small">
                {{ getAlertTypeLabel(row.condition || row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="阈值"
            prop="threshold"
            width="80"
          />
          <el-table-column
            label="严重程度"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="getSeverityType(row.severity)"
              >
                {{ getSeverityLabel(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="80"
          >
            <template #default="{ row }">
              <el-switch
                v-model="row.enabled"
                @change="toggleAlert(row)"
              />
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="120"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                size="small"
                link
                @click="editAlert(row)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                link
                type="danger"
                @click="deleteAlert(row.id)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="!isLoadingRules && alertRules.length === 0"
          class="empty-table"
        >
          <span>暂无告警规则</span>
        </div>
      </SectionCard>
    </div>

    <!-- Alert Rule Dialog -->
    <el-dialog 
      v-model="showAlertDialog" 
      :title="editingAlert ? '编辑告警规则' : '添加告警规则'" 
      width="500px"
    >
      <el-form
        ref="alertFormRef"
        :model="alertForm"
        :rules="alertRules2"
        label-position="top"
      >
        <el-form-item
          label="规则名称"
          prop="name"
        >
          <el-input
            v-model="alertForm.name"
            placeholder="输入规则名称"
          />
        </el-form-item>
        <el-form-item
          label="规则类型"
          prop="type"
        >
          <el-select
            v-model="alertForm.type"
            style="width: 100%"
          >
            <el-option
              label="执行失败"
              value="execution_failed"
            />
            <el-option
              label="执行超时"
              value="execution_timeout"
            />
            <el-option
              label="错误率高"
              value="error_rate_high"
            />
            <el-option
              label="执行时间过长"
              value="execution_duration_high"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="严重程度"
          prop="severity"
        >
          <el-select
            v-model="alertForm.severity"
            style="width: 100%"
          >
            <el-option
              label="低"
              value="low"
            />
            <el-option
              label="中"
              value="medium"
            />
            <el-option
              label="高"
              value="high"
            />
            <el-option
              label="严重"
              value="critical"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="阈值"
          prop="threshold"
        >
          <el-input-number
            v-model="alertForm.threshold"
            :min="1"
            :max="1000"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="alertForm.description"
            type="textarea"
            :rows="2"
            placeholder="描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAlertDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleSaveAlert"
        >
          {{ editingAlert ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </PageShell>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useMonitoringStore } from '@/stores/monitoring'
import { useAppStore } from '@/stores/app'
import { monitoringApi } from '@/api/monitoring'
import { pauseExecution as pauseWorkflowExecution } from '@/api/workflow'
import { useWebSocket } from '@/composables/useWebSocket'
import { getWebSocketUrl } from '@/config'
import * as echarts from 'echarts'
import {
  Plus, Activity, CheckCircle, Clock, Zap, TrendingUp
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatGrid from '@/components/layout/StatGrid.vue'
import StatCard from '@/components/layout/StatCard.vue'
import SectionCard from '@/components/layout/SectionCard.vue'
import { getEchartsTheme } from '@/utils/chartTheme'
import { useThemeChartRefresh } from '@/composables/useThemeChartRefresh'

const monitoringStore = useMonitoringStore()
const appStore = useAppStore()

// Refs
const trendChartRef = ref(null)
const trendPeriod = ref('week')
const showAlertDialog = ref(false)
const editingAlert = ref(null)
const alertFormRef = ref(null)

// Loading states
const isLoadingActive = ref(false)
const isLoadingTrend = ref(false)
const isLoadingHealth = ref(false)
const isLoadingRules = ref(false)
const isSaving = ref(false)

// Stats data
const stats = ref({
  totalExecutions: 0,
  successRate: 0,
  successTrend: 0,
  avgDuration: 0,
  activeWorkflows: 0
})

// Active executions
const activeExecutions = ref([])

// Trend data
const trendData = ref({
  dates: [],
  counts: [],
  successRates: [],
  durations: []
})

// Workflow health
const workflowHealth = ref([])

// Alert rules
const alertRules = ref([])

// Alert form
const alertForm = reactive({
  name: '',
  type: 'execution_failed',
  severity: 'medium',
  threshold: 1,
  description: ''
})

const alertRules2 = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
  severity: [{ required: true, message: '请选择严重程度', trigger: 'change' }],
  threshold: [{ required: true, message: '请输入阈值', trigger: 'blur' }]
}

// Chart instance
let trendChart = null

// WebSocket connection
const { connect, disconnect } = useWebSocket()

// Load stats
function emptyStats() {
  return {
    totalExecutions: 0,
    successRate: 0,
    successTrend: 0,
    avgDuration: 0,
    activeWorkflows: 0
  }
}

function mapTrendPeriod(period) {
  const mapping = {
    week: '7d',
    month: '30d',
    day: '1d',
  }
  return mapping[period] || period
}

async function loadStats() {
  try {
    const response = await monitoringApi.getExecutionStats()
    stats.value = {
      totalExecutions: response.totalExecutions ?? response.total_executions ?? 0,
      successRate: response.successRate ?? response.success_rate ?? 0,
      successTrend: response.successTrend ?? response.success_trend ?? 0,
      avgDuration: response.avgDurationMs ?? response.avg_duration_ms ?? response.avgDuration ?? response.avg_duration ?? 0,
      activeWorkflows: response.activeWorkflows ?? response.active_workflows ?? 0
    }
  } catch (err) {
    stats.value = emptyStats()
    appStore.error('加载执行统计失败')
    console.error('loadStats failed:', err)
  }
}

// Load active executions
async function loadActiveExecutions() {
  isLoadingActive.value = true
  try {
    const response = await monitoringApi.getActiveExecutions()
    activeExecutions.value = response.results || response || []
  } catch (err) {
    activeExecutions.value = []
    appStore.error('加载活跃执行失败')
    console.error('loadActiveExecutions failed:', err)
  } finally {
    isLoadingActive.value = false
  }
}

// Load trend data
async function loadTrendData() {
  isLoadingTrend.value = true
  try {
    const response = await monitoringApi.getExecutionTrend({ period: mapTrendPeriod(trendPeriod.value) })
    trendData.value = {
      dates: response.dates || [],
      counts: response.counts || [],
      successRates: response.successRates || [],
      durations: response.durations || []
    }
  } catch (err) {
    trendData.value = { dates: [], counts: [], successRates: [], durations: [] }
    appStore.error('加载执行趋势失败')
    console.error('loadTrendData failed:', err)
  } finally {
    isLoadingTrend.value = false
    await nextTick()
    initTrendChart()
  }
}

// Load workflow health
async function loadWorkflowHealth() {
  isLoadingHealth.value = true
  try {
    const response = await monitoringApi.getResourceUsage()
    workflowHealth.value = (response.workflows || []).map(w => ({
      ...w,
      healthScore: w.healthScore ?? w.health_score ?? 0,
      successRate: w.successRate ?? w.success_rate ?? 0,
      avgDuration: w.avgDurationMs ?? w.avg_duration_ms ?? w.avgDuration ?? w.avg_duration ?? 0,
    }))
  } catch (err) {
    workflowHealth.value = []
    appStore.error('加载工作流健康度失败')
    console.error('loadWorkflowHealth failed:', err)
  } finally {
    isLoadingHealth.value = false
  }
}

function normalizeAlertRule(rule) {
  if (!rule || typeof rule !== 'object') return rule
  return {
    ...rule,
    type: rule.type || rule.condition,
    condition: rule.condition || rule.type,
    enabled: rule.enabled ?? rule.isActive ?? rule.is_active ?? true,
  }
}

function buildAlertRulePayload(form) {
  return {
    name: form.name,
    description: form.description || '',
    condition: form.type || form.condition,
    severity: form.severity,
    threshold: form.threshold,
    enabled: form.enabled ?? true,
  }
}

// Load alert rules
async function loadAlertRules() {
  isLoadingRules.value = true
  try {
    const response = await monitoringApi.getAlertRules()
    const rows = response.results || response || []
    alertRules.value = rows.map(normalizeAlertRule)
  } catch (err) {
    alertRules.value = (monitoringStore.alertRules || []).map(normalizeAlertRule)
  } finally {
    isLoadingRules.value = false
  }
}

// Initialize trend chart
function buildTrendChartOption() {
  const theme = getEchartsTheme()

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: theme.surface,
      borderColor: theme.axis,
      textStyle: { color: theme.foreground },
    },
    legend: {
      data: ['执行次数', '成功率', '平均耗时'],
      bottom: 0,
      textStyle: { color: theme.text },
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true, top: '10%' },
    xAxis: {
      type: 'category',
      data: trendData.value.dates,
      boundaryGap: false,
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.axis } },
    },
    yAxis: [
      {
        type: 'value',
        name: '执行次数',
        position: 'left',
        nameTextStyle: { color: theme.text },
        axisLabel: { color: theme.text },
        axisLine: { lineStyle: { color: theme.axis } },
        splitLine: { lineStyle: { color: theme.splitLine } },
      },
      {
        type: 'value',
        name: '成功率 %',
        position: 'right',
        min: 0,
        max: 100,
        nameTextStyle: { color: theme.text },
        axisLabel: { color: theme.text },
        axisLine: { lineStyle: { color: theme.axis } },
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: '耗时 ms',
        position: 'right',
        offset: 60,
        nameTextStyle: { color: theme.text },
        axisLabel: { color: theme.text },
        axisLine: { lineStyle: { color: theme.axis } },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '执行次数',
        type: 'bar',
        data: trendData.value.counts,
        itemStyle: { color: theme.primary },
      },
      {
        name: '成功率',
        type: 'line',
        yAxisIndex: 1,
        data: trendData.value.successRates,
        itemStyle: { color: theme.success },
        lineStyle: { color: theme.success },
        smooth: true,
      },
      {
        name: '平均耗时',
        type: 'line',
        yAxisIndex: 2,
        data: trendData.value.durations,
        itemStyle: { color: theme.warning },
        lineStyle: { color: theme.warning },
        smooth: true,
      },
    ],
  }
}

function initTrendChart() {
  if (!trendChartRef.value) return

  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  trendChart.setOption(buildTrendChartOption(), true)
}

function refreshTrendChartTheme() {
  if (!trendChart) return
  initTrendChart()
}

// Handle execution event from WebSocket
function handleExecutionEvent(event) {
  switch (event.type) {
    case 'execution_start':
      activeExecutions.value.unshift({
        id: event.data.execution_id,
        workflowName: event.data.workflow_name || '未知工作流',
        currentNodeId: event.data.node_id || '-',
        progress: 0,
        duration: 0,
        status: 'running'
      })
      stats.value.totalExecutions++
      stats.value.activeWorkflows++
      break

    case 'execution_complete':
      activeExecutions.value = activeExecutions.value.filter(
        e => e.id !== event.data.execution_id
      )
      if (event.data.status === 'completed') {
        stats.value.successRate = calculateSuccessRate()
      }
      stats.value.activeWorkflows = Math.max(0, stats.value.activeWorkflows - 1)
      break

    case 'execution_error': {
      const errorExecution = activeExecutions.value.find(
        e => e.id === event.data.execution_id
      )
      if (errorExecution) {
        errorExecution.status = 'failed'
        errorExecution.progress = 100
      }
      stats.value.activeWorkflows = Math.max(0, stats.value.activeWorkflows - 1)
      break
    }

    case 'execution_progress': {
      const progressExecution = activeExecutions.value.find(
        e => e.id === event.data.execution_id
      )
      if (progressExecution) {
        progressExecution.progress = event.data.progress
        progressExecution.currentNodeId = event.data.node_id || progressExecution.currentNodeId
        progressExecution.duration = event.data.duration
      }
      break
    }
  }
}

function calculateSuccessRate() {
  const total = stats.value.totalExecutions
  if (total === 0) return 0
  return Math.round((stats.value.successRate * (total - 1) + 100) / total * 100) / 100
}

// Pause execution
async function pauseExecution(executionId) {
  try {
    await pauseWorkflowExecution(executionId)
    ElMessage.success('执行已暂停')
    await loadActiveExecutions()
  } catch (err) {
    appStore.error('暂停失败')
    console.error('pauseExecution failed:', err)
  }
}

// Toggle alert rule
async function toggleAlert(rule) {
  try {
    await monitoringApi.updateAlertRule(rule.id, { enabled: rule.enabled })
    ElMessage.success('规则状态已更新')
  } catch (err) {
    rule.enabled = !rule.enabled
    appStore.error('更新失败')
  }
}

// Edit alert
function editAlert(rule) {
  const normalized = normalizeAlertRule(rule)
  editingAlert.value = normalized
  Object.assign(alertForm, {
    name: normalized.name,
    type: normalized.type,
    severity: normalized.severity,
    threshold: normalized.threshold,
    description: normalized.description || ''
  })
  showAlertDialog.value = true
}

// Delete alert
async function deleteAlert(id) {
  try {
    await monitoringStore.deleteAlertRule(id)
    alertRules.value = alertRules.value.filter(r => r.id !== id)
    ElMessage.success('规则已删除')
  } catch (err) {
    appStore.error('删除失败')
  }
}

// Save alert
async function handleSaveAlert() {
  const valid = await alertFormRef.value?.validate().catch(() => false)
  if (!valid) return

  isSaving.value = true
  try {
    const payload = buildAlertRulePayload(alertForm)
    if (editingAlert.value) {
      const response = await monitoringApi.updateAlertRule(editingAlert.value.id, payload)
      const normalized = normalizeAlertRule(response)
      const index = alertRules.value.findIndex(r => r.id === editingAlert.value.id)
      if (index !== -1) {
        alertRules.value[index] = { ...alertRules.value[index], ...normalized }
      }
      ElMessage.success('规则已更新')
    } else {
      const response = await monitoringApi.createAlertRule(payload)
      alertRules.value.unshift(normalizeAlertRule(response))
      ElMessage.success('规则已创建')
    }
    showAlertDialog.value = false
    resetAlertForm()
  } catch (err) {
    appStore.error(editingAlert.value ? '更新失败' : '创建失败')
  } finally {
    isSaving.value = false
  }
}

function resetAlertForm() {
  editingAlert.value = null
  Object.assign(alertForm, {
    name: '',
    type: 'execution_failed',
    severity: 'medium',
    threshold: 1,
    description: ''
  })
}

// Helper functions
function getStatusType(status) {
  const types = {
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    paused: 'warning',
    pending: 'info'
  }
  return types[status] || 'info'
}

function getStatusLabel(status) {
  const labels = {
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    paused: '已暂停',
    pending: '等待中'
  }
  return labels[status] || status
}

function getProgressColor(progress) {
  if (progress >= 80) return '#10b981'
  if (progress >= 50) return '#6366f1'
  if (progress >= 20) return '#f59e0b'
  return '#ef4444'
}

function getHealthType(score) {
  if (score >= 90) return 'success'
  if (score >= 70) return 'primary'
  if (score >= 50) return 'warning'
  return 'danger'
}

function getHealthColor(score) {
  if (score >= 90) return '#10b981'
  if (score >= 70) return '#6366f1'
  if (score >= 50) return '#f59e0b'
  return '#ef4444'
}

function getAlertTypeLabel(type) {
  const labels = {
    execution_failed: '执行失败',
    execution_timeout: '执行超时',
    error_rate_high: '错误率高',
    execution_duration_high: '执行时间过长'
  }
  return labels[type] || type
}

function getSeverityType(severity) {
  const types = { low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }
  return types[severity] || 'info'
}

function getSeverityLabel(severity) {
  const labels = { low: '低', medium: '中', high: '高', critical: '严重' }
  return labels[severity] || severity
}

// Lifecycle
onMounted(async () => {
  // Load all data in parallel
  await Promise.all([
    loadStats(),
    loadActiveExecutions(),
    loadTrendData(),
    loadWorkflowHealth(),
    loadAlertRules()
  ])

  // Connect WebSocket for real-time updates
  connect(getWebSocketUrl('/ws/monitoring/'), {
    onMessage: (data) => {
      handleExecutionEvent(data)
    },
    onOpen: () => {
      console.log('WebSocket connected')
    },
    onError: (err) => {
      console.warn('WebSocket connection failed:', err)
    }
  })

  // Handle window resize for chart
  window.addEventListener('resize', handleResize)
})

useThemeChartRefresh(refreshTrendChartTheme)

onUnmounted(() => {
  disconnect()
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
  window.removeEventListener('resize', handleResize)
})

// Watch for period change
watch(trendPeriod, () => {
  loadTrendData()
})

function handleResize() {
  if (trendChart) {
    trendChart.resize()
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.trend-icon {
  width: 12px;
  height: 12px;
  margin-right: 2px;
  vertical-align: -2px;
}

// Dashboard Grid
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-4;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: 1fr;
  }
}

.monitor-section {
  &.monitor-section--full {
    grid-column: 1 / -1;
  }

  &.monitor-section--chart,
  &.monitor-section--health {
    min-height: 360px;
  }

  .live-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: $font-weight-semibold;

    .pulse-dot {
      width: 8px;
      height: 8px;
      background: var(--color-danger);
      border-radius: 50%;
      animation: pulse 1.5s infinite;
    }
  }

  .icon {
    width: 14px;
    height: 14px;
    margin-right: 4px;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

// Empty states
.empty-table,
.empty-health {
  text-align: center;
  padding: $spacing-8;
  color: var(--text-tertiary);
}

// Health Grid
.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: $spacing-4;
}

.health-item {
  padding: $spacing-4;
  background: var(--bg-secondary);
  border-radius: $radius-lg;
  border: 1px solid var(--border-primary);

  .health-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-3;

    .workflow-name {
      font-weight: $font-weight-semibold;
      font-size: $font-size-sm;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
      margin-right: $spacing-2;
    }
  }

  .health-stats {
    display: flex;
    justify-content: space-between;
    margin-top: $spacing-3;
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

// Trend Chart
.trend-chart {
  width: 100%;
}

// Scrollbar styling
:deep(.el-table) {
  .el-table__body-wrapper {
    &::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--border-primary);
      border-radius: 3px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }
  }
}
</style>
