<template>
  <div class="data-export-page">
    <div class="page-header">
      <div class="header-left">
        <h1>数据管理</h1>
        <p class="subtitle">
          导出、备份和管理您的数据
        </p>
      </div>
    </div>

    <!-- Export Section -->
    <div class="section">
      <h2>数据导出</h2>
      <el-card shadow="never">
        <div class="export-options">
          <div
            v-for="exportType in exportTypes"
            :key="exportType.type"
            class="export-card"
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
      <el-card shadow="never">
        <div class="backup-settings">
          <div class="setting-row">
            <div class="setting-info">
              <h4>启用自动备份</h4>
              <p>定期自动备份您的工作流和配置</p>
            </div>
            <el-switch v-model="backupSettings.enabled" />
          </div>

          <div
            v-if="backupSettings.enabled"
            class="setting-row"
          >
            <div class="setting-info">
              <h4>备份频率</h4>
              <p>每天自动备份的次数</p>
            </div>
            <el-select
              v-model="backupSettings.frequency"
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
              :min="3"
              :max="30"
              style="width: 150px"
            />
          </div>

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
                    @click="restoreBackup(backup)"
                  >
                    恢复
                  </el-button>
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
            <h4>删除所有数据</h4>
            <p>永久删除您的所有工作流、执行记录和个人数据。此操作不可撤销。</p>
          </div>
          <el-button
            type="danger"
            @click="showDeleteDialog = true"
          >
            删除所有数据
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
              <el-radio label="json">
                JSON
              </el-radio>
              <el-radio label="csv">
                CSV
              </el-radio>
              <el-radio label="xlsx">
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
          @click="confirmExport"
        >
          开始导出
        </el-button>
      </template>
    </el-dialog>

    <!-- Delete Dialog -->
    <el-dialog
      v-model="showDeleteDialog"
      title="删除所有数据"
      width="500px"
    >
      <div class="delete-dialog">
        <div class="warning-icon-wrapper">
          <AlertTriangle class="warning-icon" />
        </div>
        <p class="warning-text">
          此操作将永久删除您的所有数据，包括：
        </p>
        <ul class="delete-list">
          <li>所有工作流和配置</li>
          <li>执行记录和日志</li>
          <li>Agent 和知识库</li>
          <li>API Keys 和设置</li>
        </ul>
        <p class="confirm-text">
          此操作不可撤销，请确认您已备份重要数据。
        </p>
        <el-input
          v-model="deleteConfirmText"
          placeholder="输入 &quot;删除所有数据&quot; 确认"
        />
      </div>
      <template #footer>
        <el-button @click="showDeleteDialog = false">
          取消
        </el-button>
        <el-button
          type="danger"
          :disabled="deleteConfirmText !== '删除所有数据'"
          @click="deleteAllData"
        >
          确认删除
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Download, Database, FileText, Activity, AlertTriangle } from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const showExportDialog = ref(false)
const showDeleteDialog = ref(false)
const currentExportType = ref(null)
const exportDateRange = ref([])
const exportFormat = ref('json')
const isExporting = ref(false)
const deleteConfirmText = ref('')

const exportTypes = ref([
  {
    type: 'workflows',
    name: '工作流',
    description: '导出所有工作流的定义和配置',
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
    name: '完整导出',
    description: '导出所有数据和配置的完整备份',
    icon: Download,
    color: '#f59e0b'
  }
])

const exportHistory = ref([
  {
    id: 1,
    type: 'workflows',
    fileName: 'workflows_2024-01-15.json',
    fileSize: '2.3 MB',
    status: 'completed',
    createdAt: '2024-01-15 14:30'
  },
  {
    id: 2,
    type: 'full',
    fileName: 'full_backup_2024-01-10.zip',
    fileSize: '15.7 MB',
    status: 'completed',
    createdAt: '2024-01-10 09:00'
  }
])

const backupSettings = ref({
  enabled: true,
  frequency: 'daily',
  keepCount: 7
})

const backupHistory = ref([
  { id: 1, createdAt: '2024-01-15 08:00', fileSize: '12.5 MB' },
  { id: 2, createdAt: '2024-01-14 08:00', fileSize: '12.4 MB' },
  { id: 3, createdAt: '2024-01-13 08:00', fileSize: '12.3 MB' }
])

const getTypeTag = (type) => {
  const types = {
    workflows: '',
    executions: 'success',
    agents: 'warning',
    full: 'info'
  }
  return types[type] || ''
}

const getTypeName = (type) => {
  const names = {
    workflows: '工作流',
    executions: '执行记录',
    agents: 'Agents',
    full: '完整'
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
  isExporting.value = true

  // Simulate export process
  setTimeout(() => {
    isExporting.value = false
    showExportDialog.value = false

    exportHistory.value.unshift({
      id: Date.now(),
      type: currentExportType.value.type,
      fileName: `${currentExportType.value.type}_${new Date().toISOString().split('T')[0]}.${exportFormat.value}`,
      fileSize: '0 KB',
      status: 'completed',
      createdAt: new Date().toLocaleString('zh-CN')
    })

    appStore.success('导出任务已创建')
    currentExportType.value = null
  }, 2000)
}

const downloadExport = (row) => {
  appStore.success(`正在下载 ${row.fileName}`)
}

const restoreBackup = (backup) => {
  ElMessageBox.confirm(
    '确定要恢复此备份吗？当前数据将被覆盖。',
    '恢复备份',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    appStore.success('备份已恢复')
  })
}

const downloadBackup = (backup) => {
  appStore.success(`正在下载 ${backup.createdAt} 的备份`)
}

const deleteAllData = async () => {
  ElMessageBox.confirm(
    '此操作不可撤销，请确保您已备份所有重要数据。',
    '确认删除',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'error'
    }
    ).then(() => {
    appStore.success('所有数据已删除')
    showDeleteDialog.value = false
    deleteConfirmText.value = ''
  })
}
</script>

<style lang="scss" scoped>
.data-export-page {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 8px 0 0;
    color: var(--el-text-color-secondary);
  }
}

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
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.export-card {
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
