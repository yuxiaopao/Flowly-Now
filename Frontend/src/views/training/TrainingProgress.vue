<template>
  <div class="training-progress">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1>模型训练</h1>
        <p class="subtitle">
          监控和管理模型训练任务
        </p>
      </div>
    </div>

    <!-- GPU Info Banner -->
    <div
      v-if="gpuInfo"
      class="gpu-banner"
    >
      <div class="gpu-badge">
        <Cpu class="icon-sm" />
        <span>GPU 可用</span>
      </div>
      <span class="gpu-name">{{ gpuInfo.name }}</span>
      <span class="gpu-memory">{{ formatMemory(gpuInfo.memory_total) }}</span>
    </div>

    <!-- Job List -->
    <div class="job-list-section">
      <div
        v-if="jobs.length === 0 && !isLoading"
        class="empty-state"
      >
        <Brain class="empty-icon" />
        <h3>暂无训练任务</h3>
        <p>在工作流中添加模型训练节点来开始训练</p>
      </div>

      <div
        v-else
        class="job-grid"
      >
        <div
          v-for="job in jobs"
          :key="job.jobId"
          class="job-card"
          :class="job.status"
        >
          <div class="card-header">
            <div class="job-info">
              <h3>{{ job.name }}</h3>
              <span class="job-id">{{ job.jobId }}</span>
            </div>
            <el-tag
              :type="statusTagType(job.status)"
              size="small"
            >
              {{ statusText(job.status) }}
            </el-tag>
          </div>

          <div class="card-body">
            <div class="meta-row">
              <el-tag size="small">
                {{ job.framework }}
              </el-tag>
              <el-tag
                size="small"
                type="info"
              >
                {{ job.modelType }}
              </el-tag>
              <span
                v-if="job.gpuAvailable"
                class="gpu-tag"
              >
                <Cpu :size="12" /> GPU
              </span>
            </div>

            <div
              v-if="job.status === 'running' || job.status === 'completed'"
              class="progress-section"
            >
              <div class="progress-header">
                <span class="epoch-info">
                  Epoch {{ job.currentEpoch }} / {{ job.totalEpochs }}
                </span>
                <span class="progress-percent">{{ Math.round(job.progressPercent) }}%</span>
              </div>
              <el-progress
                :percentage="Math.round(job.progressPercent)"
                :stroke-width="6"
                :color="progressColor(job.status)"
                :show-text="false"
              />
              <div class="metrics-row">
                <span v-if="job.currentLoss !== null">
                  Loss: <strong>{{ job.currentLoss.toFixed(4) }}</strong>
                </span>
                <span v-if="job.currentMetric !== null">
                  Metric: <strong>{{ job.currentMetric.toFixed(4) }}</strong>
                </span>
              </div>
            </div>

            <div
              v-if="job.errorMessage"
              class="error-msg"
            >
              {{ job.errorMessage }}
            </div>
          </div>

          <div class="card-footer">
            <el-button
              v-if="job.status === 'running'"
              size="small"
              type="danger"
              @click="handleCancel(job)"
            >
              取消
            </el-button>
            <el-button
              v-if="job.status === 'failed'"
              size="small"
              type="warning"
              @click="handleRetry(job)"
            >
              重试
            </el-button>
            <el-button
              v-if="job.status === 'completed'"
              size="small"
              type="primary"
              @click="viewDetails(job)"
            >
              查看详情
            </el-button>
            <span class="job-time">{{ formatTime(job.createdAt) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Job Detail Drawer -->
    <el-drawer
      v-model="detailDrawer"
      title="训练详情"
      size="600px"
      direction="rtl"
    >
      <div
        v-if="selectedJob"
        class="detail-content"
      >
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">任务ID</span>
              <span class="value">{{ selectedJob.jobId }}</span>
            </div>
            <div class="detail-item">
              <span class="label">框架</span>
              <span class="value">{{ selectedJob.framework }}</span>
            </div>
            <div class="detail-item">
              <span class="label">模型类型</span>
              <span class="value">{{ selectedJob.modelType }}</span>
            </div>
            <div class="detail-item">
              <span class="label">GPU</span>
              <span class="value">{{ selectedJob.gpuAvailable ? selectedJob.gpuInfo?.name : '未使用' }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="selectedJob.metricsHistory?.length"
          class="detail-section"
        >
          <h4>训练曲线</h4>
          <div class="chart-container">
            <canvas ref="chartCanvas" />
          </div>
        </div>

        <div class="detail-section">
          <h4>输出文件</h4>
          <div
            v-if="selectedJob.modelPath"
            class="output-path"
          >
            <FileCode :size="14" />
            <span>{{ selectedJob.modelPath }}</span>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Brain, Cpu, FileCode } from 'lucide-vue-next'
import trainingApi from '@/api/training'

const jobs = ref([])
const gpuInfo = ref(null)
const isLoading = ref(true)
const detailDrawer = ref(false)
const selectedJob = ref(null)
const chartCanvas = ref(null)

async function loadJobs() {
  try {
    const res = await trainingApi.list()
    jobs.value = res.data.results || res.data || []
  } catch (e) {
    console.error('Failed to load jobs:', e)
  } finally {
    isLoading.value = false
  }
}

async function loadGpuInfo() {
  try {
    const res = await trainingApi.list({ page_size: 1 })
    const allJobs = res.data.results || res.data || []
    const latest = allJobs.find(j => j.gpuInfo)
    if (latest?.gpuInfo) gpuInfo.value = latest.gpuInfo
  } catch (e) {}
}

async function handleCancel(job) {
  try {
    await ElMessageBox.confirm('确定取消此训练任务？', '取消确认', { type: 'warning' })
    await trainingApi.cancel(job.jobId)
    ElMessage.success('训练已取消')
    await loadJobs()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('取消失败')
  }
}

async function handleRetry(job) {
  try {
    await trainingApi.retry(job.jobId)
    ElMessage.success('训练已重新开始')
    await loadJobs()
  } catch (e) {
    ElMessage.error('重试失败')
  }
}

function viewDetails(job) {
  selectedJob.value = job
  detailDrawer.value = true
  setTimeout(drawChart, 100)
}

function drawChart() {
  if (!chartCanvas.value || !selectedJob.value?.metricsHistory?.length) return
  const ctx = chartCanvas.value.getContext('2d')
  const history = selectedJob.value.metricsHistory
  const w = chartCanvas.value.offsetWidth
  const h = 200
  chartCanvas.value.width = w
  chartCanvas.value.height = h

  ctx.clearRect(0, 0, w, h)
  if (!history.length) return

  const losses = history.map(h => h.loss).filter(l => l !== undefined)
  const metrics = history.map(h => h.metric).filter(m => m !== undefined)

  const drawLine = (data, color) => {
    if (!data.length) return
    ctx.beginPath()
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    data.forEach((v, i) => {
      const x = (i / (data.length - 1 || 1)) * w
      const y = h - (v * h)
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
    })
    ctx.stroke()
  }

  drawLine(losses, '#f59e0b')
  drawLine(metrics, '#10b981')
}

function statusText(status) {
  const map = { pending: '等待中', preparing: '准备中', running: '运行中', completed: '已完成', failed: '失败', cancelled: '已取消' }
  return map[status] || status
}

function statusTagType(status) {
  const map = { pending: 'info', preparing: 'warning', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[status] || 'info'
}

function progressColor(status) {
  return status === 'completed' ? '#10b981' : '#06b6d4'
}

function formatMemory(bytes) {
  if (!bytes) return ''
  const gb = bytes / 1024 / 1024 / 1024
  return `${gb.toFixed(1)} GB`
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => { loadJobs(); loadGpuInfo() })
</script>

<style lang="scss" scoped>
.gpu-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 13px;

  .gpu-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #06b6d4;
    font-weight: 600;
  }
  .gpu-name { color: var(--text-primary); }
  .gpu-memory { color: var(--text-secondary); }
}

.job-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.job-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;

  &.running { border-color: rgba(6, 182, 212, 0.5); }
  &.completed { border-color: rgba(16, 185, 129, 0.5); }
  &.failed { border-color: rgba(239, 68, 68, 0.5); }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;

    h3 { font-size: 15px; font-weight: 600; margin: 0; color: var(--text-primary); }
    .job-id { font-size: 11px; color: var(--text-tertiary); font-family: monospace; }
  }

  .card-body {
    margin-bottom: 12px;
    .meta-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
    .gpu-tag { display: flex; align-items: center; gap: 3px; font-size: 11px; color: #06b6d4; }
  }

  .progress-section {
    margin-top: 12px;
    .progress-header { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px; }
    .epoch-info { color: var(--text-secondary); }
    .progress-percent { color: #06b6d4; font-weight: 600; }
    .metrics-row { display: flex; gap: 16px; margin-top: 6px; font-size: 12px; color: var(--text-secondary); strong { color: var(--text-primary); } }
  }

  .error-msg { margin-top: 8px; font-size: 12px; color: #ef4444; }

  .card-footer {
    display: flex;
    align-items: center;
    gap: 8px;
    border-top: 1px solid var(--border-primary);
    padding-top: 12px;
    .job-time { margin-left: auto; font-size: 11px; color: var(--text-tertiary); }
  }
}

.detail-content {
  .detail-section {
    margin-bottom: 24px;
    h4 { font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 12px; }
  }
  .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .detail-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    .label { font-size: 11px; color: var(--text-tertiary); }
    .value { font-size: 13px; color: var(--text-primary); }
  }
  .output-path { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary); font-family: monospace; background: var(--bg-tertiary); padding: 8px 12px; border-radius: 6px; }
}

.chart-container { background: var(--bg-tertiary); border-radius: 8px; padding: 8px; }
</style>
