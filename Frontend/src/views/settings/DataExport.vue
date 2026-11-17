<template>
  <div class="data-export-page">
    <PageHeader
      compact
      title="数据管理"
      subtitle="导出、备份和管理个人工作区；团队数据单独保留"
    />

    <!-- Export Section -->
    <div class="section">
      <h2>数据导出</h2>
      <el-card shadow="never">
        <div class="export-options">
          <div
            v-for="exportType in exportTypes"
            :key="exportType.type"
            class="export-card"
            :data-testid="`export-${exportType.type}`"
          >
            <div
              class="export-icon"
              :style="{ backgroundColor: exportType.color }"
            >
              <component
                :is="exportType.icon"
                class="icon"
              />
            </div>
            <div class="export-info">
              <h4>{{ exportType.name }}</h4>
              <p>{{ exportType.description }}</p>
            </div>
            <el-button @click="startExport(exportType)">
              导出
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Export History -->
    <div class="section">
      <h2>导出历史</h2>
      <el-table
        v-loading="loadingHistory"
        :data="exportHistory"
        stripe
      >
        <el-table-column
          label="类型"
          prop="type"
          width="150"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getTypeTag(row.type)"
            >
              {{ getTypeName(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="文件名"
          prop="fileName"
        />
        <el-table-column
          label="大小"
          prop="fileSize"
          width="100"
        />
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
            >
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="创建时间"
          prop="createdAt"
          width="180"
        />
        <el-table-column
          label="操作"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              text
              @click="downloadExport(row)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Backup Section -->
    <div class="section">
      <h2>自动备份</h2>
      <el-card
        v-loading="loadingPolicy"
        shadow="never"
      >
        <el-alert
          v-if="policyError"
          :title="policyError"
          type="error"
          :closable="false"
        />
        <el-button
          v-if="policyError && !policyReady"
          @click="loadBackupSettings"
        >
          重新加载计划
        </el-button>
        <p>计划保存在服务端，关闭浏览器后仍可运行；请确保管理员已启动备份服务。</p>
        <el-alert
          v-if="policyReady && !backupSchedulerConfigured"
          title="服务端尚未配置自动备份，请联系管理员。"
          type="warning"
          :closable="false"
        />
        <div class="backup-settings">
          <div class="setting-row">
            <div class="setting-info">
              <h4>启用自动备份</h4>
              <p>备份个人工作流、Agent 和配置；不包含团队、知识库文件及独立凭证库。</p>
            </div>
            <el-switch
              v-model="backupSettings.enabled"
              :disabled="!policyReady || savingPolicy || (!backupSchedulerConfigured && !backupSettings.enabled)"
              aria-label="启用自动备份"
            />
          </div>

          <div
            v-if="backupSettings.enabled"
            class="setting-row"
          >
            <div class="setting-info">
              <h4>备份频率</h4>
              <p>从保存计划时起计算下一次备份时间</p>
            </div>
            <el-select
              v-model="backupSettings.frequency"
              :disabled="!policyReady || savingPolicy"
              style="width: 150px"
            >
              <el-option
                label="每天"
                value="daily"
              />
              <el-option
                label="每周"
                value="weekly"
              />
              <el-option
                label="每月"
                value="monthly"
              />
            </el-select>
          </div>

          <div
            v-if="backupSettings.enabled"
            class="setting-row"
          >
            <div class="setting-info">
              <h4>保留备份数量</h4>
              <p>最近保留的备份版本数量</p>
            </div>
            <el-input-number
              v-model="backupSettings.keepCount"
              :min="retentionLimits.min"
              :max="retentionLimits.max"
              :disabled="!policyReady || savingPolicy"
              style="width: 150px"
            />
          </div>

          <el-alert
            v-if="backupSettings.lastError"
            :title="backupSettings.lastError"
            type="error"
            :closable="false"
          />
          <p v-if="backupSettings.nextRunAt">
            下次备份：{{ formatDateTime(backupSettings.nextRunAt) }}
          </p>
          <p v-if="backupSettings.lastRunAt">
            最近完成：{{ formatDateTime(backupSettings.lastRunAt) }}
          </p>
          <el-button
            type="primary"
            :loading="savingPolicy"
            :disabled="!policyReady"
            data-testid="backup-policy-save"
            @click="saveBackupPolicy"
          >
            保存备份计划
          </el-button>

          <div class="backup-history">
            <h4>最近的备份</h4>
            <div class="backup-list">
              <div
                v-for="backup in backupHistory"
                :key="backup.id"
                class="backup-item"
              >
                <div class="backup-info">
                  <span class="backup-date">{{ backup.createdAt }}</span>
                  <span class="backup-size">{{ backup.fileSize }}</span>
                </div>
                <div class="backup-actions">
                  <el-button
                    size="small"
                    text
                    :disabled="!backup.restorable || restoring"
                    :loading="previewingRestore === backup.id"
                    :data-testid="`restore-backup-${backup.id}`"
                    @click="restoreBackup(backup)"
                  >
                    恢复为副本
                  </el-button>
                  <span v-if="!backup.restorable">{{ backup.raw.format === 'json' ? '旧记录未保存历史快照' : '请使用 JSON 备份恢复' }}</span>
                  <el-button
                    size="small"
                    text
                    @click="downloadBackup(backup)"
                  >
                    下载
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Danger Zone -->
    <div class="section danger-zone">
      <h2>危险区域</h2>
      <el-card
        shadow="never"
        class="danger-card"
      >
        <div class="danger-content">
          <div class="danger-info">
            <h4>清理个人工作区</h4>
            <p>删除个人工作流、Agent 及关联执行和对话。团队、应用、账号、凭证、知识库和账单保留。</p>
          </div>
          <el-button
            type="danger"
            :loading="previewingDelete"
            data-testid="personal-data-delete-open"
            @click="openDeleteDialog"
          >
            清理个人工作区
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- Export Dialog -->
    <el-dialog
      v-model="showExportDialog"
      title="导出数据"
      width="500px"
    >
      <div
        v-if="currentExportType"
        class="export-dialog"
      >
        <p>导出类型：<strong>{{ currentExportType.name }}</strong></p>

        <el-form label-width="100px">
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="exportDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
            />
          </el-form-item>

          <el-form-item label="格式">
            <el-radio-group v-model="exportFormat">
              <el-radio value="json">
                JSON
              </el-radio>
              <el-radio value="csv">
                CSV
              </el-radio>
              <el-radio value="xlsx">
                Excel
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showExportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isExporting"
          data-testid="export-confirm"
          @click="confirmExport"
        >
          开始导出
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showRestoreDialog"
      title="恢复为私有副本"
      width="500px"
      :close-on-click-modal="!restoring"
      :show-close="!restoring"
    >
      <template v-if="restorePreview">
        <el-alert
          :title="restorePreview.notice"
          type="info"
          :closable="false"
        />
        <p
          v-for="(value, key) in restorePreview.summary"
          :key="key"
        >
          {{ summaryLabel(key) }}：{{ value }}
        </p>
        <p>不会覆盖或删除现有内容，也不会重放执行记录。</p>
      </template>
      <template #footer>
        <el-button
          :disabled="restoring"
          @click="showRestoreDialog = false"
        >
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="restoring"
          :disabled="!restorePreview"
          data-testid="backup-restore-confirm"
          @click="confirmRestore"
        >
          确认创建副本
        </el-button>
      </template>
    </el-dialog>

    <!-- Delete Dialog -->
    <el-dialog
      v-model="showDeleteDialog"
      title="确认清理个人工作区"
      width="500px"
      :close-on-click-modal="!deleting"
      :show-close="!deleting"
    >
      <div class="delete-dialog">
        <div class="warning-icon-wrapper">
          <AlertTriangle class="warning-icon" />
        </div>
        <p class="warning-text">
          此操作将永久删除预览范围内的个人数据：
        </p>
        <ul class="delete-list">
          <li
            v-for="(value, key) in deletionPreview?.summary"
            :key="key"
          >
            {{ summaryLabel(key) }}：{{ value }}
          </li>
        </ul>
        <p class="confirm-text">
          {{ deletionPreview?.notice }} 此操作不可撤销，请先备份。
        </p>
        <el-input
          v-model="deletePassword"
          type="password"
          show-password
          autocomplete="current-password"
          aria-label="当前密码"
          placeholder="输入当前登录密码"
          :disabled="deleting"
        />
        <el-input
          v-model="deleteConfirmText"
          :placeholder="`输入「${deletionPreview?.confirmationText || ''}」确认`"
          aria-label="清理确认文字"
          :disabled="deleting"
        />
      </div>
      <template #footer>
        <el-button
          :disabled="deleting"
          @click="showDeleteDialog = false"
        >
          取消
        </el-button>
        <el-button
          type="danger"
          :disabled="!deletePassword || deleteConfirmText !== deletionPreview?.confirmationText"
          :loading="deleting"
          data-testid="personal-data-delete-confirm"
          @click="deleteAllData"
        >
          确认删除
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { Download, Database, FileText, Activity, AlertTriangle } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { useWorkflowStore } from '@/stores/workflow'
import { useAgentStore } from '@/stores/agent'
import { dataExportApi } from '@/api/dataExport'
import { formatDateTime, formatFileSize } from '@/utils/formatters'
import PageHeader from '@/components/layout/PageHeader.vue'

const appStore = useAppStore()
const workflowStore = useWorkflowStore()
const agentStore = useAgentStore()

const showExportDialog = ref(false)
const showDeleteDialog = ref(false)
const currentExportType = ref(null)
const exportDateRange = ref([])
const exportFormat = ref('json')
const isExporting = ref(false)
const deleteConfirmText = ref('')
const loadingHistory = ref(false)
const loadingPolicy = ref(false)
const policyReady = ref(false)
const savingPolicy = ref(false)
const policyError = ref('')
const retentionLimits = ref({})
const backupSchedulerConfigured = ref(false)
const showRestoreDialog = ref(false)
const restoreTarget = ref(null)
const restorePreview = ref(null)
const previewingRestore = ref(null)
const restoring = ref(false)
const previewingDelete = ref(false)
const deletionPreview = ref(null)
const deleting = ref(false)
const deletePassword = ref('')

const exportTypes = ref([
  {
    type: 'workflows',
    name: '工作流',
    description: '导出个人工作流、节点、变量和触发器配置',
    icon: Database,
    color: '#3b82f6'
  },
  {
    type: 'executions',
    name: '执行记录',
    description: '导出工作流的执行历史和结果',
    icon: Activity,
    color: '#10b981'
  },
  {
    type: 'agents',
    name: 'Agents',
    description: '导出 Agent 的配置和工具定义',
    icon: FileText,
    color: '#3b82f6'
  },
  {
    type: 'full',
    name: '个人工作区备份',
    description: '备份个人工作流和 Agent，归档执行及审计记录',
    icon: Download,
    color: '#f59e0b'
  }
])

const exportHistory = ref([])

const backupSettings = ref({
  enabled: false,
  frequency: 'daily',
  keepCount: null,
  nextRunAt: null,
  lastRunAt: null,
  lastError: ''
})

const backupHistory = ref([])

async function loadBackupSettings() {
  loadingPolicy.value = true
  policyError.value = ''
  try {
    const data = await dataExportApi.getBackupSettings()
    applyPolicy(data)
    policyReady.value = true
  } catch (error) {
    policyReady.value = false
    policyError.value = '加载服务端备份计划失败，请重试。'
    appStore.error(policyError.value)
  } finally {
    loadingPolicy.value = false
  }
}

function applyPolicy(data) {
  backupSettings.value = {
    enabled: data.enabled, frequency: data.frequency,
    keepCount: data.keepCount ?? data.keep_count,
    nextRunAt: data.nextRunAt ?? data.next_run_at,
    lastRunAt: data.lastRunAt ?? data.last_run_at,
    lastError: data.lastError ?? data.last_error ?? '',
  }
  retentionLimits.value = { min: data.retentionMin ?? data.retention_min, max: data.retentionMax ?? data.retention_max }
  backupSchedulerConfigured.value = data.schedulerConfigured ?? data.scheduler_configured
}

async function saveBackupPolicy() {
  if (!policyReady.value || savingPolicy.value) return
  savingPolicy.value = true
  try {
    const data = await dataExportApi.saveBackupSettings({
      enabled: backupSettings.value.enabled, frequency: backupSettings.value.frequency,
      keep_count: backupSettings.value.keepCount,
    })
    applyPolicy(data)
    policyError.value = ''
    appStore.success('备份计划已保存，下次备份时间已更新。')
  } catch (error) {
    policyError.value = '保存备份计划失败，服务端计划未更改。'
    appStore.error(policyError.value)
  } finally {
    savingPolicy.value = false
  }
}

function mapExportRow(row) {
  return {
    id: row.id,
    type: row.exportType || row.export_type,
    fileName: row.fileName || row.file_name || '-',
    fileSize: formatFileSize(row.fileSize ?? row.file_size ?? 0),
    status: row.status,
    restorable: row.restorable === true,
    createdAt: formatDateTime(row.createdAt || row.created_at),
    raw: row,
  }
}

async function loadExportHistory() {
  loadingHistory.value = true
  try {
    const response = await dataExportApi.list()
    const data = response?.data ?? response
    const rows = Array.isArray(data) ? data : data.results || []
    exportHistory.value = rows.map(mapExportRow)
    backupHistory.value = exportHistory.value
      .filter(item => item.type === 'full' && item.status === 'completed')
  } catch (error) {
    console.error('Failed to load export history:', error)
    appStore.error('加载导出历史失败')
  } finally {
    loadingHistory.value = false
  }
}

onMounted(() => {
  loadBackupSettings()
  loadExportHistory()
})

function summaryLabel(key) {
  const labels = { workflows: '个人工作流', nodes: '节点', edges: '连线', agents: '个人 Agent',
    agent_tools: 'Agent 工具', agentTools: 'Agent 工具', workflow_executions: '工作流执行', workflowExecutions: '工作流执行',
    agent_executions: 'Agent 执行', agentExecutions: 'Agent 执行', conversations: 'Agent 对话',
    related_records: '关联记录合计', relatedRecords: '关联记录合计', variables: '工作流变量', triggers: '触发器', webhooks: 'Webhook' }
  return labels[key] || key
}

const getTypeTag = (type) => {
  const types = {
    workflows: 'primary',
    executions: 'success',
    agents: 'warning',
    full: 'info'
  }
  return types[type] || 'info'
}

const getTypeName = (type) => {
  const names = {
    workflows: '工作流',
    executions: '执行记录',
    agents: 'Agents',
      full: '个人工作区'
  }
  return names[type] || type
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusName = (status) => {
  const names = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return names[status] || status
}

const startExport = (exportType) => {
  currentExportType.value = exportType
  showExportDialog.value = true
}

const confirmExport = async () => {
  if (!currentExportType.value) return
  isExporting.value = true
  try {
    const extra = {}
    if (exportDateRange.value?.length === 2) {
      extra.date_from = dayjs(exportDateRange.value[0]).startOf('day').toISOString()
      extra.date_to = dayjs(exportDateRange.value[1]).endOf('day').toISOString()
    }
    const created = await dataExportApi.requestExport(
      currentExportType.value.type,
      exportFormat.value,
      extra
    )
    exportHistory.value.unshift(mapExportRow(created))
    appStore.success('导出任务已创建')
    showExportDialog.value = false
    currentExportType.value = null
    exportDateRange.value = []
    await loadExportHistory()
  } catch (error) {
    console.error('Export failed:', error)
    appStore.error('创建导出任务失败')
  } finally {
    isExporting.value = false
  }
}

const downloadExport = async (row) => {
  try {
    const blob = await dataExportApi.download(row.id)
    const filename = row.fileName || row.file_name || `export_${row.id}.json`
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    appStore.success(`正在下载 ${filename}`)
  } catch (error) {
    console.error('Download export failed:', error)
    appStore.error('下载失败')
  }
}

const restoreBackup = async (backup) => {
  if (!backup.restorable || previewingRestore.value !== null || restoring.value) return
  previewingRestore.value = backup.id
  try {
    const preview = await dataExportApi.previewRestore(backup.id)
    restoreTarget.value = backup
    restorePreview.value = { ...preview, confirmationToken: preview.confirmationToken ?? preview.confirmation_token }
    showRestoreDialog.value = true
  } catch (error) {
    appStore.error('无法预览此备份，请检查格式或重新导出。')
  } finally {
    previewingRestore.value = null
  }
}

async function confirmRestore() {
  if (!restorePreview.value || !restoreTarget.value || restoring.value) return
  restoring.value = true
  try {
    await dataExportApi.restore(restoreTarget.value.id, restorePreview.value.confirmationToken)
    showRestoreDialog.value = false
    restorePreview.value = null
    appStore.success('私有草稿副本已创建，原数据保持不变。')
    await refreshWorkspaceLists()
  } catch (error) {
    appStore.error('恢复失败，未创建部分副本；请重新预览后重试。')
    restorePreview.value = null
  } finally {
    restoring.value = false
  }
}

const downloadBackup = async (backup) => {
  await downloadExport(backup)
}

async function openDeleteDialog() {
  if (previewingDelete.value || deleting.value) return
  previewingDelete.value = true
  try {
    const preview = await dataExportApi.previewDelete()
    deletionPreview.value = { ...preview, confirmationText: preview.confirmationText ?? preview.confirmation_text,
      confirmationToken: preview.confirmationToken ?? preview.confirmation_token }
    deletePassword.value = ''
    deleteConfirmText.value = ''
    showDeleteDialog.value = true
  } catch (error) {
    appStore.error('无法预览清理范围，请先停止个人工作区中的运行任务。')
  } finally {
    previewingDelete.value = false
  }
}

const deleteAllData = async () => {
  if (!deletionPreview.value || !deletePassword.value || deleteConfirmText.value !== deletionPreview.value.confirmationText || deleting.value) return
  deleting.value = true
  try {
    const result = await dataExportApi.deletePersonalData({ password: deletePassword.value,
      confirmation: deleteConfirmText.value, confirmation_token: deletionPreview.value.confirmationToken })
    const ids = result.deletedIds ?? result.deleted_ids ?? {}
    if (ids.workflows?.includes(workflowStore.currentWorkflow?.id)) workflowStore.clearEditor()
    if (ids.agents?.includes(agentStore.currentAgent?.id)) agentStore.clearStore()
    showDeleteDialog.value = false
    deleteConfirmText.value = ''
    deletePassword.value = ''
    appStore.success('已清理预览中的个人工作区，团队及其余数据已保留。')
    await refreshWorkspaceLists()
  } catch (error) {
    appStore.error('清理失败，请核对密码；数据若已变化，请重新打开清理预览。')
  } finally {
    deleting.value = false
  }
}

async function refreshWorkspaceLists() {
  const results = await Promise.allSettled([workflowStore.fetchWorkflows(), agentStore.fetchAgents(), loadExportHistory()])
  if (results.some(result => result.status === 'rejected')) {
    appStore.warning('操作已完成，部分列表刷新失败，请重新加载列表。')
  }
}
</script>

<style lang="scss" scoped>

.section {
  margin-bottom: 32px;

  h2 {
    margin: 0 0 16px;
    font-size: 20px;
    font-weight: 600;
  }
}

.export-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr));
  gap: var(--content-gap);
}

.export-card {
  min-width: 0;
  overflow-wrap: anywhere;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
  }

  .export-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    .icon {
      width: 24px;
      height: 24px;
      color: white;
    }
  }

  .export-info {
    flex: 1;

    h4 {
      margin: 0;
      font-size: 16px;
    }

    p {
      margin: 4px 0 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}

.backup-settings {
  .setting-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);

    &:last-child {
      border-bottom: none;
    }

    .setting-info {
      h4 {
        margin: 0;
        font-size: 16px;
      }

      p {
        margin: 4px 0 0;
        font-size: 14px;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .backup-history {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid var(--el-border-color-lighter);

    h4 {
      margin: 0 0 16px;
      font-size: 16px;
    }
  }

  .backup-list {
    .backup-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      background: var(--el-fill-color-light);
      border-radius: 8px;
      margin-bottom: 8px;

      &:last-child {
        margin-bottom: 0;
      }

      .backup-info {
        .backup-date {
          font-weight: 500;
        }

        .backup-size {
          margin-left: 12px;
          color: var(--el-text-color-secondary);
          font-size: 14px;
        }
      }

      .backup-actions {
        display: flex;
        gap: 8px;
      }
    }
  }
}

.danger-zone {
  h2 {
    color: var(--el-color-danger);
  }
}

.danger-card {
  border-color: rgba(239, 68, 68, 0.3);

  .danger-content {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .danger-info {
      h4 {
        margin: 0;
        color: var(--el-color-danger);
      }

      p {
        margin: 4px 0 0;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.export-dialog {
  p {
    margin: 0 0 16px;

    strong {
      color: var(--el-color-primary);
    }
  }
}

.delete-dialog {
  text-align: center;

  .warning-icon-wrapper {
    margin-bottom: 16px;
  }

  .warning-icon {
    width: 64px;
    height: 64px;
    color: var(--el-color-danger);
  }

  .warning-text {
    font-size: 16px;
    margin-bottom: 16px;
  }

  .delete-list {
    text-align: left;
    margin: 0 0 16px;
    padding-left: 24px;
    color: var(--el-text-color-secondary);

    li {
      margin: 8px 0;
    }
  }

  .confirm-text {
    font-weight: 500;
    color: var(--el-color-danger);
    margin-bottom: 16px;
  }
}
</style>
