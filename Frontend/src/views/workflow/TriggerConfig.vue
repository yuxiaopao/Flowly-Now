<template>
  <el-drawer
    :model-value="visible"
    title="触发器配置"
    size="600px"
    direction="rtl"
    :before-close="handleClose"
  >
    <!-- 后端能力未启用提示 -->
    <el-alert
      v-if="!triggerFeatureAvailable"
      :title="triggerFeatureMessage || '当前环境未启用工作流触发器能力'"
      type="warning"
      :closable="false"
      show-icon
      class="trigger-feature-alert"
    />

    <!-- 触发器列表（已存在触发器时显示） -->
    <div
      v-if="triggers.length > 0 && !editingTrigger"
      class="trigger-list"
    >
      <div class="list-header">
        <span class="list-title">已配置的触发器</span>
        <el-tooltip
          content="为工作流添加新的触发器"
          placement="bottom"
        >
          <el-button
            type="primary"
            size="small"
            @click="createNew"
          >
            <Plus class="btn-icon" /> 添加触发器
          </el-button>
        </el-tooltip>
      </div>

      <el-table
        :data="triggers"
        stripe
        class="trigger-table"
      >
        <el-table-column
          prop="name"
          label="名称"
          min-width="120"
        />
        <el-table-column
          label="类型"
          width="100"
        >
          <template #default="{ row }">
            <el-tag size="small">
              {{ getTriggerTypeLabel(row.triggerType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="80"
          align="center"
        >
          <template #default="{ row }">
            <el-switch
              :model-value="row.isEnabled"
              @change="handleToggleTrigger(row.id, $event)"
            />
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            <el-button
              size="small"
              link
              @click="editTrigger(row)"
            >
              编辑
            </el-button>
            <el-popconfirm
              title="确定删除此触发器？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleRemoveTrigger(row.id)"
            >
              <template #reference>
                <el-button
                  size="small"
                  link
                  type="danger"
                >
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 触发器表单 -->
    <div
      v-if="editingTrigger || triggers.length === 0"
      class="trigger-form"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        class="trigger-form-content"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">
          基本信息
        </el-divider>
        <el-form-item
          label="名称"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="输入触发器名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item
          label="描述"
          prop="description"
        >
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="可选描述信息"
            maxlength="200"
          />
        </el-form-item>

        <!-- 触发类型 -->
        <el-divider content-position="left">
          触发类型
        </el-divider>
        <el-form-item
          label="类型"
          prop="triggerType"
        >
          <el-radio-group
            v-model="formData.triggerType"
            class="trigger-type-group"
          >
            <el-radio-button value="manual">
              手动触发
            </el-radio-button>
            <el-radio-button value="schedule">
              定时触发
            </el-radio-button>
            <el-radio-button value="cron">
              Cron 表达式
            </el-radio-button>
            <el-radio-button value="webhook">
              Webhook
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 定时触发配置 -->
        <template v-if="formData.triggerType === 'schedule'">
          <el-form-item label="执行方式">
            <el-radio-group v-model="formData.scheduleType">
              <el-radio value="once">
                单次执行
              </el-radio>
              <el-radio value="recurring">
                循环执行
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item
            v-if="formData.scheduleType === 'once'"
            label="执行时间"
            prop="scheduledAt"
          >
            <el-date-picker
              v-model="formData.scheduledAt"
              type="datetime"
              placeholder="选择执行时间"
              :disabled-date="disabledPastDate"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
          </el-form-item>

          <el-form-item
            v-if="formData.scheduleType === 'recurring'"
            label="执行间隔"
          >
            <el-input-number
              v-model="formData.intervalSeconds"
              :min="1"
              :max="86400"
            />
            <span class="interval-hint">秒（最小 1 秒，最大 86400 秒 = 24 小时）</span>
          </el-form-item>
        </template>

        <!-- Cron 表达式配置 -->
        <template v-if="formData.triggerType === 'cron'">
          <el-form-item
            label="Cron 表达式"
            prop="cronExpression"
          >
            <el-input
              v-model="formData.cronExpression"
              placeholder="* * * * *"
              @blur="fetchCronPreview"
            />
          </el-form-item>

          <el-form-item label="预设模板">
            <el-select
              v-model="selectedPreset"
              placeholder="选择预设模板"
              clearable
              @change="applyPreset"
            >
              <el-option
                v-for="preset in cronPresets"
                :key="preset.expression"
                :label="`${preset.label} (${preset.expression})`"
                :value="preset.expression"
              />
            </el-select>
          </el-form-item>

          <!-- 下次执行时间预览 -->
          <el-form-item label="下次执行">
            <div
              v-if="cronPreview.length > 0"
              class="cron-preview"
            >
              <el-tag
                v-for="(time, idx) in cronPreview"
                :key="idx"
                size="small"
                class="preview-tag"
              >
                {{ time }}
              </el-tag>
            </div>
            <span
              v-else-if="cronPreviewLoading"
              class="loading-text"
            >
              <el-icon class="is-loading"><Loader /></el-icon> 计算中...
            </span>
            <span
              v-else-if="formData.cronExpression"
              class="hint-text"
            >
              点击表达式输入框或离开后自动预览
            </span>
            <span
              v-else
              class="hint-text"
            >
              输入有效的 Cron 表达式后自动预览
            </span>
          </el-form-item>

          <el-form-item>
            <el-popover
              placement="right"
              :width="400"
              trigger="hover"
            >
              <template #reference>
                <el-link
                  type="primary"
                  :underline="false"
                >
                  <HelpCircle class="help-icon" /> Cron 帮助
                </el-link>
              </template>
              <div class="cron-help">
                <p class="help-title">
                  <strong>格式:</strong> 分 时 日 月 周
                </p>
                <div class="help-items">
                  <p><code>*</code> - 任意值</p>
                  <p><code>*/n</code> - 每 n 个单位</p>
                  <p><code>n-m</code> - 范围</p>
                  <p><code>n,m</code> - 列表</p>
                </div>
                <p class="help-title">
                  <strong>常用示例:</strong>
                </p>
                <div class="help-examples">
                  <code>* * * * *</code> - 每分钟<br>
                  <code>0 * * * *</code> - 每小时整点<br>
                  <code>0 9 * * 1-5</code> - 工作日 9:00<br>
                  <code>*/15 * * * *</code> - 每 15 分钟<br>
                  <code>0 0 1 * *</code> - 每月 1 号午夜
                </div>
              </div>
            </el-popover>
          </el-form-item>
        </template>

        <!-- Webhook 配置 -->
        <template v-if="formData.triggerType === 'webhook'">
          <el-form-item label="认证方式">
            <el-select v-model="formData.authType">
              <el-option
                label="无认证"
                value="none"
              />
              <el-option
                label="Header 认证"
                value="header"
              />
              <el-option
                label="签名认证"
                value="signature"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="formData.authType !== 'none'"
            label="密钥"
          >
            <el-input
              v-model="formData.webhookSecret"
              type="password"
              placeholder="输入认证密钥"
              show-password
            />
          </el-form-item>

          <el-form-item label="Webhook URL">
            <div class="webhook-url-display">
              <el-input
                :model-value="generatedWebhookUrl"
                readonly
                placeholder="保存后生成 Webhook URL"
                class="webhook-url-input"
              />
              <el-tooltip
                content="复制 URL"
                placement="top"
              >
                <el-button
                  :disabled="!triggerId"
                  @click="copyWebhookUrl"
                >
                  <Copy class="btn-icon" />
                </el-button>
              </el-tooltip>
            </div>
            <span class="url-hint">
              使用此 URL 触发工作流执行
            </span>
          </el-form-item>

          <el-form-item>
            <el-tooltip
              content="发送测试请求验证 Webhook 是否可用"
              placement="top"
            >
              <el-button
                :disabled="!triggerId"
                @click="testCurrentWebhook"
              >
                <Zap class="btn-icon" /> 测试 Webhook
              </el-button>
            </el-tooltip>
          </el-form-item>
        </template>

        <!-- 高级选项 -->
        <el-collapse>
          <el-collapse-item
            title="高级选项"
            name="advanced"
          >
            <el-form-item label="最大执行次数">
              <el-input-number
                v-model="formData.maxExecutions"
                :min="0"
                :max="10000"
                placeholder="0 表示无限制"
              />
              <span class="hint-text">0 表示无限制执行</span>
            </el-form-item>

            <el-form-item label="输入映射">
              <div class="mapping-table">
                <el-table
                  :data="inputMappings"
                  size="small"
                  class="mapping-inner-table"
                >
                  <el-table-column
                    label="外部变量"
                    prop="external"
                  />
                  <el-table-column
                    label=""
                    width="40"
                    align="center"
                  >
                    <template #default>
                      <span class="arrow-icon">→</span>
                    </template>
                  </el-table-column>
                  <el-table-column
                    label="工作流输入"
                    prop="internal"
                  >
                    <template #default="{ row }">
                      <el-input
                        v-model="row.internal"
                        size="small"
                        placeholder="工作流变量名"
                      />
                    </template>
                  </el-table-column>
                  <el-table-column
                    width="50"
                    align="center"
                  >
                    <template #default="{ $index }">
                      <el-button
                        size="small"
                        link
                        type="danger"
                        @click="removeMapping($index)"
                      >
                        <Minus class="btn-icon" />
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-button
                  size="small"
                  class="add-mapping-btn"
                  @click="addMapping"
                >
                  <Plus class="btn-icon" /> 添加映射
                </el-button>
              </div>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>

        <!-- 触发历史 -->
        <el-divider
          v-if="triggerId"
          content-position="left"
        >
          触发历史
        </el-divider>
        <div
          v-if="triggerId && !editingTrigger"
          class="trigger-history"
        >
          <el-table
            :data="triggerExecutions"
            size="small"
            max-height="200"
            class="executions-table"
          >
            <el-table-column
              label="状态"
              width="90"
            >
              <template #default="{ row }">
                <el-tag
                  size="small"
                  :type="getExecutionStatusType(row.status)"
                >
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="触发时间"
              prop="queuedAt"
              width="160"
            >
              <template #default="{ row }">
                {{ formatDate(row.queuedAt) }}
              </template>
            </el-table-column>
            <el-table-column
              label="执行时间"
              prop="durationMs"
              width="90"
            >
              <template #default="{ row }">
                {{ row.durationMs ? row.durationMs + 'ms' : '-' }}
              </template>
            </el-table-column>
            <el-table-column
              label="错误"
              prop="errorMessage"
              show-overflow-tooltip
            />
          </el-table>
          <div
            v-if="triggerExecutions.length === 0"
            class="no-executions"
          >
            暂无执行记录
          </div>
        </div>
      </el-form>

      <!-- 表单操作 -->
      <div class="form-actions">
        <el-button @click="cancelEdit">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSaveTrigger"
        >
          {{ triggerId ? '保存修改' : '创建触发器' }}
        </el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-if="triggers.length === 0 && !editingTrigger"
      class="empty-state"
    >
      <Clock class="empty-icon" />
      <h3>暂无触发器</h3>
      <p>为工作流配置定时或外部触发器</p>
      <el-tooltip
        content="为工作流添加新的触发器"
        placement="bottom"
      >
        <el-button
          type="primary"
          :disabled="!triggerFeatureAvailable"
          @click="createNew"
        >
          <Plus class="btn-icon" /> 添加触发器
        </el-button>
      </el-tooltip>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Plus, Minus, Copy, Zap, Clock, HelpCircle, Loader
} from 'lucide-vue-next'
import { getTriggerTypeLabel, getExecutionStatusType, formatTriggerDate, CRON_PRESETS } from '@/types/trigger'
import * as triggerApi from '@/api/trigger'
import { getPublicApiUrl } from '@/config'

// =============================================================================
// Props & Emits
// =============================================================================

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  workflowId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['update:visible'])

// =============================================================================
// 状态
// =============================================================================

const triggers = ref([])
const editingTrigger = ref(null)
const triggerId = ref(null)
const saving = ref(false)
const cronPreviewLoading = ref(false)
const cronPreview = ref([])
const selectedPreset = ref('')
const triggerExecutions = ref([])
const triggerFeatureAvailable = ref(true)
const triggerFeatureMessage = ref('')

const formRef = ref(null)

// 表单数据
const formData = reactive({
  name: '',
  description: '',
  triggerType: 'manual',
  scheduleType: 'recurring',
  scheduledAt: '',
  intervalSeconds: 60,
  cronExpression: '',
  authType: 'none',
  webhookSecret: '',
  maxExecutions: 0,
})

// 输入映射
const inputMappings = ref([])

// Cron 预设
const cronPresets = CRON_PRESETS

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入触发器名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  triggerType: [
    { required: true, message: '请选择触发类型', trigger: 'change' }
  ],
  scheduledAt: [
    { required: true, message: '请选择执行时间', trigger: 'change' }
  ],
  cronExpression: [
    { required: true, message: '请输入 Cron 表达式', trigger: 'blur' },
    { pattern: /^(\*|([0-5]?\d)) (\*|([01]?\d|2[0-3])) (\*|([12]?\d|3[01])) (\*|(1[0-2]|0?[1-9])) (\*|([0-6]))$/, message: '无效的 Cron 表达式', trigger: 'blur' }
  ]
}

// =============================================================================
// 计算属性
// =============================================================================

const generatedWebhookUrl = computed(() => {
  if (!triggerId.value) return ''
  return getPublicApiUrl(`/workflows/triggers/${triggerId.value}/webhook/`)
})

function getErrorMessage(error, fallback = '操作失败') {
  const responseData = error?.response?.data

  if (typeof responseData?.detail === 'string' && responseData.detail) return responseData.detail
  if (typeof responseData?.message === 'string' && responseData.message) return responseData.message
  if (typeof responseData?.error === 'string' && responseData.error) return responseData.error

  if (responseData && typeof responseData === 'object') {
    const fieldMessage = Object.values(responseData)
      .flat()
      .find(value => typeof value === 'string' && value)
    if (fieldMessage) return fieldMessage
  }

  if (typeof error?.message === 'string' && error.message) return error.message
  return fallback
}

function resetDrawerState() {
  editingTrigger.value = null
  triggerId.value = null
  triggers.value = []
  triggerExecutions.value = []
  triggerFeatureAvailable.value = true
  triggerFeatureMessage.value = ''
  saving.value = false
  cronPreviewLoading.value = false
  resetFormData()
  formRef.value?.clearValidate()
}

// =============================================================================
// 方法
// =============================================================================

/**
 * 加载触发器列表
 */
async function loadTriggers() {
  if (!props.workflowId) return

  try {
    triggerFeatureAvailable.value = true
    triggerFeatureMessage.value = ''
    const response = await triggerApi.getTriggers({ workflow_id: props.workflowId })
    triggers.value = response.results || response || []
  } catch (error) {
    triggers.value = []
    if (error?.response?.status === 404) {
      triggerFeatureAvailable.value = false
      triggerFeatureMessage.value = '当前后端尚未启用工作流触发器接口，暂不可创建或管理触发器。'
      return
    }
    triggerFeatureAvailable.value = true
    triggerFeatureMessage.value = '触发器列表加载失败，请稍后重试。'
  }
}

/**
 * 加载触发器执行历史
 */
async function loadTriggerExecutions() {
  if (!triggerId.value || !triggerFeatureAvailable.value) return

  try {
    const response = await triggerApi.getTriggerExecutions(triggerId.value, { page_size: 10 })
    triggerExecutions.value = response.results || response || []
  } catch (error) {
    triggerExecutions.value = []
    if (error?.response?.status === 404) {
      triggerFeatureAvailable.value = false
      triggerFeatureMessage.value = '当前后端尚未启用工作流触发器接口，暂不可创建或管理触发器。'
    }
  }
}

/**
 * 创建新触发器
 */
function createNew() {
  if (!triggerFeatureAvailable.value) {
    ElMessage.warning(triggerFeatureMessage.value || '当前环境未启用触发器后端能力')
    return
  }

  editingTrigger.value = {
    name: '',
    description: '',
    triggerType: 'manual',
    isEnabled: true
  }
  triggerId.value = null
  resetFormData()
}

/**
 * 编辑现有触发器
 */
function editTrigger(trigger) {
  editingTrigger.value = { ...trigger }
  triggerId.value = trigger.id

  // 填充表单数据
  formData.name = trigger.name || ''
  formData.description = trigger.description || ''
  formData.triggerType = trigger.triggerType || 'manual'
  formData.scheduleType = trigger.config?.scheduleType || 'recurring'
  formData.scheduledAt = trigger.config?.scheduledAt || ''
  formData.intervalSeconds = trigger.config?.intervalSeconds || 60
  formData.cronExpression = trigger.config?.cronExpression || ''
  formData.authType = trigger.config?.authType || 'none'
  formData.webhookSecret = trigger.config?.webhookSecret || ''
  formData.maxExecutions = trigger.config?.maxExecutions || 0

  // 填充输入映射
  inputMappings.value = trigger.config?.inputMappings?.length
    ? [...trigger.config.inputMappings]
    : []

  // 如果是 Cron 类型，预览下次执行时间
  if (formData.triggerType === 'cron' && formData.cronExpression) {
    fetchCronPreview()
  }

  // 加载执行历史
  loadTriggerExecutions()
}

/**
 * 重置表单数据
 */
function resetFormData() {
  formData.name = ''
  formData.description = ''
  formData.triggerType = 'manual'
  formData.scheduleType = 'recurring'
  formData.scheduledAt = ''
  formData.intervalSeconds = 60
  formData.cronExpression = ''
  formData.authType = 'none'
  formData.webhookSecret = ''
  formData.maxExecutions = 0
  inputMappings.value = []
  selectedPreset.value = ''
  cronPreview.value = []
}

/**
 * 取消编辑
 */
function cancelEdit() {
  editingTrigger.value = null
  triggerId.value = null
  triggerExecutions.value = []
  resetFormData()
  formRef.value?.clearValidate()
}

/**
 * 保存触发器
 */
async function handleSaveTrigger() {
  if (!triggerFeatureAvailable.value) {
    ElMessage.warning(triggerFeatureMessage.value || '当前环境未启用触发器后端能力')
    return
  }

  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true

  try {
    const payload = {
      name: formData.name,
      description: formData.description,
      trigger_type: formData.triggerType,
      is_enabled: true,
      config: {
        schedule_type: formData.scheduleType,
        scheduled_at: formData.scheduledAt,
        interval_seconds: formData.intervalSeconds,
        cron_expression: formData.cronExpression,
        auth_type: formData.authType,
        webhook_secret: formData.webhookSecret,
        max_executions: formData.maxExecutions,
        input_mappings: inputMappings.value.filter(m => m.external && m.internal)
      }
    }

    if (triggerId.value) {
      // 更新
      await triggerApi.updateTrigger(triggerId.value, payload)
      ElMessage.success('触发器已更新')
    } else {
      // 创建
      const result = await triggerApi.createTrigger(props.workflowId, payload)
      triggerId.value = result.id
      ElMessage.success('触发器已创建')
    }

    // 重新加载列表
    await loadTriggers()
    cancelEdit()
  } catch (error) {
    ElMessage.error(`保存失败：${getErrorMessage(error, '请检查触发器配置后重试')}`)
  } finally {
    saving.value = false
  }
}

/**
 * 切换触发器启用状态
 */
async function handleToggleTrigger(id, enabled) {
  try {
    await triggerApi.toggleTrigger(id, enabled)
    ElMessage.success(enabled ? '触发器已启用' : '触发器已禁用')
    await loadTriggers()
  } catch (error) {
    ElMessage.error(`切换状态失败：${getErrorMessage(error, '请稍后重试')}`)
    // 回滚 UI
    const trigger = triggers.value.find(t => t.id === id)
    if (trigger) {
      trigger.isEnabled = !enabled
    }
  }
}

/**
 * 删除触发器
 */
async function handleRemoveTrigger(id) {
  try {
    await triggerApi.deleteTrigger(id)
    ElMessage.success('触发器已删除')
    await loadTriggers()
  } catch (error) {
    ElMessage.error(`删除失败：${getErrorMessage(error, '请稍后重试')}`)
  }
}

/**
 * 禁用过去的时间
 */
function disabledPastDate(date) {
  return date.getTime() < Date.now() - 8.64e7 // 不允许选择今天之前的日期
}

/**
 * 应用 Cron 预设
 */
function applyPreset(expression) {
  formData.cronExpression = expression
  if (expression) {
    fetchCronPreview()
  }
}

/**
 * 获取 Cron 表达式预览
 */
async function fetchCronPreview() {
  if (!formData.cronExpression || !triggerFeatureAvailable.value) {
    cronPreview.value = []
    return
  }

  cronPreviewLoading.value = true

  try {
    const preview = await triggerApi.getCronPreview(formData.cronExpression, 5)
    cronPreview.value = preview || []
  } catch (error) {
    if (error?.response?.status === 404) {
      triggerFeatureAvailable.value = false
      triggerFeatureMessage.value = '当前后端尚未启用工作流触发器接口，暂不可创建或管理触发器。'
    }
    cronPreview.value = []
  } finally {
    cronPreviewLoading.value = false
  }
}

/**
 * 复制 Webhook URL
 */
async function copyWebhookUrl() {
  if (!generatedWebhookUrl.value) return

  try {
    await navigator.clipboard.writeText(generatedWebhookUrl.value)
    ElMessage.success('Webhook URL 已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

/**
 * 测试 Webhook
 */
async function testCurrentWebhook() {
  if (!triggerFeatureAvailable.value) {
    ElMessage.warning(triggerFeatureMessage.value || '当前环境未启用触发器后端能力')
    return
  }

  if (!triggerId.value) return

  try {
    const result = await triggerApi.testWebhook(triggerId.value, {
      test: true,
      timestamp: new Date().toISOString()
    })

    if (result.success) {
      ElMessage.success('Webhook 测试成功')
    } else {
      ElMessage.warning(result.message || 'Webhook 测试失败')
    }
  } catch (error) {
    ElMessage.error(`测试失败：${getErrorMessage(error, '请确认 Webhook 触发器配置是否正确')}`)
  }
}

/**
 * 格式化日期
 */
function formatDate(dateStr) {
  return formatTriggerDate(dateStr)
}

/**
 * 添加输入映射
 */
function addMapping() {
  inputMappings.value.push({ external: '', internal: '' })
}

/**
 * 删除输入映射
 */
function removeMapping(index) {
  inputMappings.value.splice(index, 1)
}

/**
 * 关闭抽屉
 */
function handleClose() {
  resetDrawerState()
  emit('update:visible', false)
}

// =============================================================================
// 监听器
// =============================================================================

watch(() => props.visible, (newVal) => {
  if (newVal) {
    loadTriggers()
    return
  }

  resetDrawerState()
})

watch(() => props.workflowId, () => {
  if (props.visible) {
    loadTriggers()
  }
})

// =============================================================================
// 生命周期
// =============================================================================

onMounted(() => {
  if (props.visible) {
    loadTriggers()
  }
})
</script>

<style lang="scss" scoped>
.trigger-list {
  padding: 0 16px;
}

.trigger-feature-alert {
  margin: 0 16px 16px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .list-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.trigger-table {
  :deep(.el-table__header th) {
    background-color: var(--bg-tertiary);
  }
}

.trigger-form {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
}

.trigger-form-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px;
}

.trigger-type-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.interval-hint {
  margin-left: 12px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.cron-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preview-tag {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
}

.loading-text {
  color: var(--text-tertiary);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.hint-text {
  color: var(--text-tertiary);
  font-size: 12px;
}

.help-icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.cron-help {
  font-size: 13px;
  line-height: 1.8;

  .help-title {
    margin: 8px 0 4px;
  }

  .help-items {
    padding-left: 8px;
  }

  .help-examples {
    padding-left: 8px;
    line-height: 2;
  }

  code {
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
    font-size: 12px;
    color: var(--color-primary);
  }
}

.webhook-url-display {
  display: flex;
  gap: 8px;
  align-items: center;

  .webhook-url-input {
    flex: 1;
  }
}

.url-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.mapping-table {
  width: 100%;
}

.mapping-inner-table {
  margin-bottom: 8px;
}

.arrow-icon {
  color: var(--text-tertiary);
  font-weight: bold;
}

.add-mapping-btn {
  width: 100%;
}

.trigger-history {
  margin-bottom: 16px;
}

.executions-table {
  :deep(.el-table__header th) {
    background-color: var(--bg-tertiary);
  }
}

.no-executions {
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--text-tertiary);
    margin-bottom: 16px;
    opacity: 0.5;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  p {
    margin: 0 0 20px;
    color: var(--text-tertiary);
    font-size: 14px;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.btn-icon {
  width: 16px;
  height: 16px;
}
</style>
