<template>
  <div class="desktop-agent-page">
    <PageHeader
      compact
      title="桌面端 Agent"
      subtitle="管理本地 GPU 训练代理，云端工作流可下发训练任务到桌面端执行"
    />

    <!-- Cloud Connection Card -->
    <div class="cloud-card">
      <div class="cloud-header">
        <div class="cloud-info">
          <div
            class="cloud-status-dot"
            :class="cloudConnected ? 'online' : 'offline'"
          />
          <span class="cloud-label">
            {{ cloudConnected ? '已连接 Flowly 云端' : '未连接云端' }}
          </span>
        </div>
        <el-button
          v-if="!cloudConnected"
          type="primary"
          size="small"
          :loading="connecting"
          @click="handleConnect"
        >
          连接云端
        </el-button>
        <el-button
          v-else
          type="danger"
          plain
          size="small"
          @click="handleDisconnect"
        >
          断开连接
        </el-button>
      </div>
      <div
        v-if="cloudConnected"
        class="cloud-stats"
      >
        <div class="stat-item">
          <span class="stat-label">云端地址</span>
          <span class="stat-value">{{ cloudUrl }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Agent ID</span>
          <span class="stat-value mono">{{ agentId || '—' }}</span>
        </div>
      </div>
    </div>

    <!-- Download Desktop App (browser only) -->
    <div
      v-if="!runningInDesktop"
      class="download-section"
    >
      <h3>下载桌面端应用</h3>
      <p>在您的电脑上安装 Flowly Agent，即可使用本地 GPU 进行 YOLO 模型训练</p>
      <div class="download-platforms">
        <button
          class="platform-btn"
          @click="handleDownload('win')"
        >
          <span class="platform-icon">W</span>
          Windows
        </button>
        <button
          class="platform-btn"
          @click="handleDownload('mac')"
        >
          <span class="platform-icon">M</span>
          macOS
        </button>
        <button
          class="platform-btn"
          @click="handleDownload('linux')"
        >
          <span class="platform-icon">L</span>
          Linux
        </button>
      </div>
      <div class="setup-hint">
        <InfoIcon :size="14" />
        <span>首次使用需要填写云端服务器地址和 Agent ID 进行连接</span>
      </div>
    </div>

    <!-- Local agent panel (Electron only) -->
    <SectionCard
      v-if="runningInDesktop"
      title="本机 GPU Agent"
      subtitle="当前桌面应用内置训练执行器，登录后会自动连接云端"
    >
      <div class="local-agent-grid">
        <div class="local-agent-stat">
          <span class="stat-label">连接状态</span>
          <span
            class="local-status"
            :class="localAgentConnected ? 'online' : 'offline'"
          >
            {{ localAgentConnected ? '已连接' : '未连接' }}
          </span>
        </div>
        <div class="local-agent-stat">
          <span class="stat-label">Agent ID</span>
          <span class="stat-value mono">{{ localAgentId || '—' }}</span>
        </div>
        <div class="local-agent-stat">
          <span class="stat-label">GPU</span>
          <span class="stat-value">{{ localGpuLabel }}</span>
        </div>
        <div class="local-agent-stat">
          <span class="stat-label">训练</span>
          <span class="stat-value">{{ localTrainingLabel }}</span>
        </div>
      </div>
      <div class="local-agent-actions">
        <el-button
          v-if="!localAgentConnected"
          type="primary"
          :loading="connecting"
          @click="handleConnect"
        >
          连接云端
        </el-button>
        <el-button
          v-else
          type="danger"
          plain
          @click="handleDisconnect"
        >
          断开连接
        </el-button>
        <el-button @click="refreshLocalAgentStatus">
          刷新本机状态
        </el-button>
      </div>
    </SectionCard>

    <!-- Connected Agents List -->
    <div class="agents-section">
      <h3>已连接的桌面端</h3>

      <div
        v-if="agentsLoading"
        class="loading-row"
      >
        <el-icon class="is-loading">
          <LoaderIcon />
        </el-icon>
        加载中...
      </div>

      <div
        v-else-if="onlineAgents.length === 0"
        class="empty-row"
      >
        <MonitorDotIcon :size="32" />
        <p>暂无在线桌面端</p>
        <p class="hint">
          启动桌面端应用并连接后即可看到此处列表
        </p>
      </div>

      <div
        v-else
        class="agents-list"
      >
        <div
          v-for="agent in onlineAgents"
          :key="agent.agent_id"
          class="agent-card"
        >
          <div class="agent-header">
            <div class="agent-info">
              <div class="agent-name">
                {{ agent.display_name || agent.hostname || '桌面端' }}
              </div>
              <div class="agent-id">
                {{ agent.agent_id }}
              </div>
            </div>
            <div
              class="agent-status"
              :class="agent.status"
            >
              {{ statusLabel(agent.status) }}
            </div>
          </div>

          <div class="agent-gpu">
            <div
              v-if="agent.gpu_available"
              class="gpu-badge"
            >
              <CpuIcon :size="12" />
              {{ agent.gpu_name || 'GPU' }}
            </div>
            <div
              v-else
              class="gpu-badge no-gpu"
            >
              <CpuIcon :size="12" />
              无 GPU
            </div>
          </div>

          <div class="agent-capabilities">
            <el-tag
              v-for="cap in (agent.capabilities || [])"
              :key="cap"
              size="small"
              type="info"
            >
              {{ cap }}
            </el-tag>
          </div>

          <div class="agent-actions">
            <el-button
              size="small"
              type="primary"
              :disabled="agent.status === 'training'"
              @click="handleDispatchTraining(agent)"
            >
              下发训练任务
            </el-button>
            <el-button
              size="small"
              @click="handleRefreshAgent"
            >
              刷新状态
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 训练任务下发对话框 -->
    <el-dialog
      v-model="showDispatchDialog"
      :title="dispatchDialogTitle"
      width="520px"
      destroy-on-close
      @closed="resetDispatchForm"
    >
      <el-form
        ref="dispatchFormRef"
        :model="dispatchForm"
        :rules="dispatchFormRules"
        label-width="120px"
      >
        <el-form-item
          label="任务名称"
          prop="name"
        >
          <el-input
            v-model="dispatchForm.name"
            placeholder="例如：零件缺陷检测 v2"
          />
        </el-form-item>

        <el-form-item
          label="YOLO 版本"
          prop="yolo_version"
        >
          <el-select
            v-model="dispatchForm.yolo_version"
            style="width: 100%"
          >
            <el-option
              label="YOLOv8"
              value="v8"
            />
            <el-option
              label="YOLOv11"
              value="v11"
            />
            <el-option
              label="YOLOv5"
              value="v5"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="模型规格"
          prop="model_variant"
        >
          <el-select
            v-model="dispatchForm.model_variant"
            style="width: 100%"
          >
            <el-option
              label="n (纳米)"
              value="n"
            />
            <el-option
              label="s (小)"
              value="s"
            />
            <el-option
              label="m (中)"
              value="m"
            />
            <el-option
              label="l (大)"
              value="l"
            />
            <el-option
              label="x (超大)"
              value="x"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="训练轮数"
          prop="total_epochs"
        >
          <el-input-number
            v-model="dispatchForm.total_epochs"
            :min="1"
            :max="1000"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item
          label="数据集 YAML"
          prop="dataset_yaml_path"
        >
          <el-input
            v-model="dispatchForm.dataset_yaml_path"
            placeholder="桌面端可访问的数据集 YAML 绝对路径"
          />
        </el-form-item>

        <el-form-item
          label="类别名称"
          prop="class_names"
        >
          <el-select
            v-model="dispatchForm.class_names"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入类别名后回车"
            style="width: 100%"
          >
            <el-option
              v-for="c in dispatchForm.class_names"
              :key="c"
              :label="c"
              :value="c"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="dispatchForm.description"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDispatchDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="dispatching"
          @click="submitDispatchTraining"
        >
          下发训练
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Info as InfoIcon,
  MonitorDot as MonitorDotIcon,
  Cpu as CpuIcon,
  Loader as LoaderIcon,
} from 'lucide-vue-next'
import agentApi from '@/api/agent'
import APP_CONFIG from '@/config'
import PageHeader from '@/components/layout/PageHeader.vue'
import SectionCard from '@/components/layout/SectionCard.vue'
import { useAuthStore } from '@/stores/auth'
import {
  connectDesktopAgent,
  disconnectDesktopAgent,
  getDesktopAgentConfig,
  getDesktopAgentStatus,
  isElectron,
} from '@/utils/electron'

const authStore = useAuthStore()
const runningInDesktop = isElectron()

const cloudConnected = ref(false)
const connecting = ref(false)
const cloudUrl = ref('')
const agentId = ref('')
const agentsLoading = ref(false)
const onlineAgents = ref([])

const localAgentConnected = ref(false)
const localAgentId = ref('')
const localGpuLabel = ref('检测中…')
const localTrainingLabel = ref('空闲')
let localStatusUnsubscribe = null

const showDispatchDialog = ref(false)
const dispatching = ref(false)
const dispatchTargetAgent = ref(null)
const dispatchFormRef = ref(null)

const dispatchForm = reactive({
  name: '',
  yolo_version: APP_CONFIG.desktopAgent.defaultYoloVersion,
  model_variant: APP_CONFIG.desktopAgent.defaultModelVariant,
  total_epochs: APP_CONFIG.desktopAgent.defaultEpochs,
  dataset_yaml_path: '',
  class_names: [],
  description: '',
})

const dispatchFormRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  yolo_version: [{ required: true, message: '请选择 YOLO 版本', trigger: 'change' }],
  model_variant: [{ required: true, message: '请选择模型规格', trigger: 'change' }],
  total_epochs: [{ required: true, type: 'number', min: 1, message: '请设置训练轮次', trigger: 'blur' }],
  dataset_yaml_path: [{ required: true, message: '请提供数据集 YAML 路径', trigger: 'blur' }],
}

const dispatchDialogTitle = computed(() => {
  const agent = dispatchTargetAgent.value
  if (!agent) return '下发训练任务'
  const label = agent.display_name || agent.hostname || agent.agent_id
  return `下发训练任务 — ${label}`
})

onMounted(async () => {
  if (runningInDesktop) {
    await refreshLocalAgentStatus()
    const api = window.agentAPI
    if (api?.onAgentStatus) {
      localStatusUnsubscribe = api.onAgentStatus((status) => {
        applyLocalAgentStatus(status)
      })
    }
  }
  await fetchAgents()
})

onUnmounted(() => {
  localStatusUnsubscribe?.()
})

function applyLocalAgentStatus(status) {
  if (!status) return
  localAgentConnected.value = Boolean(status.connected)
  localAgentId.value = status.agentId || ''
  cloudUrl.value = status.cloudUrl || APP_CONFIG.apiBaseUrl
  agentId.value = status.agentId || ''
  cloudConnected.value = Boolean(status.connected)

  const gpu = status.gpu
  if (gpu?.available) {
    localGpuLabel.value = gpu.name || 'GPU 可用'
  } else {
    localGpuLabel.value = '无 GPU / CPU 模式'
  }

  if (status.training?.running) {
    localTrainingLabel.value = `训练中 (${status.training.jobId?.slice(0, 8) || '…'})`
  } else {
    localTrainingLabel.value = '空闲'
  }
}

async function refreshLocalAgentStatus() {
  if (!runningInDesktop) return
  const status = await getDesktopAgentStatus()
  applyLocalAgentStatus(status)
  const config = await getDesktopAgentConfig()
  if (config?.agentId && !localAgentId.value) {
    localAgentId.value = config.agentId
  }
}

function syncCloudStatusFromAgents(agents) {
  if (agents.length === 0) {
    cloudConnected.value = false
    cloudUrl.value = ''
    agentId.value = ''
    return
  }
  cloudConnected.value = true
  const first = agents[0]
  cloudUrl.value = first.cloud_url || APP_CONFIG.apiBaseUrl
  agentId.value = first.agent_id || ''
}

function createJobId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `job-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function buildJobConfig() {
  const jobId = createJobId()
  return {
    jobId,
    name: dispatchForm.name.trim(),
    yolo_version: dispatchForm.yolo_version,
    model_variant: dispatchForm.model_variant,
    epochs: dispatchForm.total_epochs,
    dataset_yaml_path: dispatchForm.dataset_yaml_path.trim(),
    class_names: [...dispatchForm.class_names],
    training_kind: 'yolo',
    framework: 'ultralytics',
    description: dispatchForm.description.trim(),
  }
}

function resetDispatchForm() {
  dispatchTargetAgent.value = null
  dispatchForm.name = ''
  dispatchForm.yolo_version = APP_CONFIG.desktopAgent.defaultYoloVersion
  dispatchForm.model_variant = APP_CONFIG.desktopAgent.defaultModelVariant
  dispatchForm.total_epochs = APP_CONFIG.desktopAgent.defaultEpochs
  dispatchForm.dataset_yaml_path = ''
  dispatchForm.class_names = []
  dispatchForm.description = ''
  dispatchFormRef.value?.clearValidate()
}

async function fetchAgents() {
  agentsLoading.value = true
  try {
    const data = await agentApi.getAvailableDesktopAgents()
    onlineAgents.value = Array.isArray(data) ? data : (data?.results || [])
    syncCloudStatusFromAgents(onlineAgents.value)
  } catch (err) {
    console.error('Failed to fetch agents:', err)
    onlineAgents.value = []
    syncCloudStatusFromAgents([])
  } finally {
    agentsLoading.value = false
  }
}

async function handleConnect() {
  connecting.value = true
  try {
    if (runningInDesktop) {
      const config = await getDesktopAgentConfig()
      const status = await connectDesktopAgent({
        cloudUrl: APP_CONFIG.apiBaseUrl.replace(/\/+$/, ''),
        agentId: config?.agentId,
        apiToken: authStore.token || undefined,
      })
      applyLocalAgentStatus(status)
      ElMessage.success('本机 Agent 已连接云端')
      await fetchAgents()
      return
    }

    ElMessage.info('请在 Flowly 桌面端应用中连接云端')
  } catch (err) {
    ElMessage.error(err?.message || '连接失败')
  } finally {
    connecting.value = false
  }
}

async function handleDisconnect() {
  try {
    if (runningInDesktop) {
      const status = await disconnectDesktopAgent()
      applyLocalAgentStatus(status)
      ElMessage.success('本机 Agent 已断开')
      await fetchAgents()
      return
    }

    cloudConnected.value = false
    ElMessage.info('已在桌面端断开连接')
  } catch (err) {
    ElMessage.error(err?.message || '断开失败')
  }
}

function handleDownload(platform) {
  const url = APP_CONFIG.desktopAgent.downloads[platform]
  if (url) {
    ElMessage.info(`正在打开下载链接：${url}`)
    window.open(url, '_blank', 'noopener,noreferrer')
  } else {
    ElMessage.info('该平台下载即将推出')
  }
}

function handleDispatchTraining(agent) {
  if (!agent?.agent_id) {
    ElMessage.warning('无效的桌面端 Agent')
    return
  }
  if (agent.status === 'training') {
    ElMessage.warning('该桌面端正在训练中，请稍后再试')
    return
  }
  if (!agent.gpu_available) {
    ElMessage.warning('该桌面端未检测到可用 GPU')
    return
  }
  dispatchTargetAgent.value = agent
  dispatchForm.name = `${agent.display_name || agent.hostname || '桌面训练'}-${new Date().toISOString().slice(0, 10)}`
  showDispatchDialog.value = true
}

async function submitDispatchTraining() {
  const agent = dispatchTargetAgent.value
  if (!agent?.agent_id) {
    ElMessage.error('未选择目标桌面端')
    return
  }

  try {
    await dispatchFormRef.value?.validate()
  } catch {
    return
  }

  dispatching.value = true
  try {
    const jobConfig = buildJobConfig()
    const result = await agentApi.dispatchDesktopTraining({
      agent_id: agent.agent_id,
      job_config: jobConfig,
    })

    ElMessage.success(`训练任务已下发（Job ID: ${jobConfig.jobId.slice(0, 8)}…）`)
    showDispatchDialog.value = false

    if (result?.cloud_url) {
      cloudUrl.value = result.cloud_url
    }
    await fetchAgents()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || '下发失败'
    ElMessage.error(msg)
  } finally {
    dispatching.value = false
  }
}

async function handleRefreshAgent() {
  try {
    await fetchAgents()
    ElMessage.success('已刷新')
  } catch {
    ElMessage.error('刷新失败')
  }
}

function statusLabel(status) {
  const map = {
    online: '在线',
    offline: '离线',
    training: '训练中',
    error: '异常',
  }
  return map[status] || status
}
</script>

<style scoped>
.desktop-agent-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.cloud-card {
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 16px 20px;
}

.cloud-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.cloud-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cloud-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.cloud-status-dot.online { background: #67c23a; box-shadow: 0 0 4px #67c23a; }
.cloud-status-dot.offline { background: #c0c4cc; }

.cloud-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.cloud-stats {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-light);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 0.85rem;
  color: var(--el-text-color-primary);
}

.stat-value.mono {
  font-family: monospace;
  font-size: 0.8rem;
}

.download-section {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 20px;
}

.download-section h3 {
  font-size: 0.9rem;
  font-weight: 700;
  margin: 0 0 6px;
}

.download-section p {
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
  margin: 0 0 14px;
}

.download-platforms {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.platform-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-primary);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.15s;
  font-family: inherit;
}

.platform-btn:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.platform-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: var(--el-color-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.setup-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
  background: var(--el-color-primary-light-9);
  padding: 8px 12px;
  border-radius: 6px;
}

.agents-section h3 {
  font-size: 0.9rem;
  font-weight: 700;
  margin: 0 0 14px;
}

.loading-row,
.empty-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px;
  color: var(--el-text-color-secondary);
  font-size: 0.85rem;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
}

.empty-row .hint {
  font-size: 0.75rem;
  color: var(--el-text-color-placeholder);
}

.agents-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

.agent-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.agent-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.agent-id {
  font-size: 0.65rem;
  color: var(--el-text-color-placeholder);
  font-family: monospace;
  margin-top: 2px;
}

.agent-status {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.agent-status.online { background: #f0f9eb; color: #67c23a; }
.agent-status.training { background: #ecf5ff; color: #409eff; }
.agent-status.offline { background: #f4f4f5; color: #909399; }
.agent-status.error { background: #fef0f0; color: #f56c6c; }

.agent-gpu {
  display: flex;
}

.gpu-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 6px;
  background: #ecf5ff;
  color: #409eff;
}

.gpu-badge.no-gpu {
  background: #f4f4f5;
  color: #909399;
}

.agent-capabilities {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.agent-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.local-agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.local-agent-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.local-status {
  font-size: 0.85rem;
  font-weight: 600;
}

.local-status.online { color: #67c23a; }
.local-status.offline { color: #909399; }

.local-agent-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
