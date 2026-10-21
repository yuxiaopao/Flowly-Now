<template>
  <PageShell
    width="wide"
    class="model-list"
  >
    <PageHeader
      title="模型管理"
      subtitle="管理 AI 模型配置和 API 密钥"
    >
      <template #actions>
        <el-button @click="showAPIKeyDialog = true">
          <Key class="btn-icon" />
          添加 API Key
        </el-button>
      </template>
    </PageHeader>

    <!-- Tabs -->
    <el-tabs
      v-model="activeTab"
      class="model-tabs"
    >
      <!-- API Keys Tab -->
      <el-tab-pane
        label="API 密钥"
        name="api-keys"
      >
        <PageEmptyState
          v-if="apiKeys.length === 0 && !apiKeysLoading"
          :icon="Key"
          title="暂无 API 密钥"
          description="添加您的 API 密钥以使用 AI 模型"
        >
          <template #actions>
            <el-button
              type="primary"
              @click="showAPIKeyDialog = true"
            >
              添加密钥
            </el-button>
          </template>
        </PageEmptyState>

        <div
          v-else
          class="api-keys-list"
        >
          <div
            v-for="key in apiKeys"
            :key="key.id"
            class="api-key-card"
          >
            <div class="key-header">
              <div class="key-info">
                <el-tag
                  :type="getProviderType(key.provider)"
                  size="small"
                >
                  {{ getProviderLabel(key.provider) }}
                </el-tag>
                <span class="key-name">{{ key.name }}</span>
              </div>
              <div class="key-status">
                <el-tag
                  v-if="key.is_active"
                  type="success"
                  size="small"
                >
                  启用
                </el-tag>
                <el-tag
                  v-else
                  type="info"
                  size="small"
                >
                  禁用
                </el-tag>
              </div>
            </div>

            <div class="key-value">
              <code>{{ key.get_masked_key ? key.get_masked_key : maskKey(key.api_key) }}</code>
            </div>

            <div class="key-meta">
              <span class="meta-item">
                <Clock class="meta-icon" />
                创建于 {{ formatDate(key.created_at) }}
              </span>
              <span
                v-if="key.last_used_at"
                class="meta-item"
              >
                <Activity class="meta-icon" />
                最后使用 {{ formatDate(key.last_used_at) }}
              </span>
            </div>

            <div class="key-actions">
              <el-button
                size="small"
                @click="handleVerifyKey(key)"
              >
                <CheckCircle class="btn-icon" />
                验证
              </el-button>
              <el-button
                size="small"
                @click="editAPIKey(key)"
              >
                <Edit class="btn-icon" />
                编辑
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleDeleteKey(key)"
              >
                <Trash2 class="btn-icon" />
                删除
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Models Tab -->
      <el-tab-pane
        label="模型配置"
        name="models"
      >
        <div class="models-header">
          <div class="filter-bar">
            <el-select
              v-model="filterProvider"
              placeholder="提供商"
              clearable
              style="width: 150px"
            >
              <el-option
                v-for="p in providers"
                :key="p.id"
                :label="p.name"
                :value="p.slug"
              />
            </el-select>
            <el-select
              v-model="filterType"
              placeholder="类型"
              clearable
              style="width: 150px"
            >
              <el-option
                label="对话模型"
                value="chat"
              />
              <el-option
                label="嵌入模型"
                value="embedding"
              />
              <el-option
                label="图像模型"
                value="image"
              />
              <el-option
                label="音频模型"
                value="audio"
              />
            </el-select>
            <el-input
              v-model="searchQuery"
              placeholder="搜索模型..."
              clearable
              style="width: 200px"
            >
              <template #prefix>
                <Search class="input-icon" />
              </template>
            </el-input>
          </div>
        </div>

        <PageEmptyState
          v-if="filteredModels.length === 0 && !modelsLoading"
          :icon="Bot"
          title="暂无模型配置"
          description="系统中还没有配置 AI 模型"
        />

        <div
          v-else
          class="models-grid"
        >
          <div
            v-for="model in filteredModels"
            :key="model.id"
            class="model-card"
          >
            <div class="model-header">
              <div
                class="model-icon"
                :class="model.model_type"
              >
                <Bot
                  v-if="model.model_type === 'chat'"
                  class="icon"
                />
                <Layers
                  v-else-if="model.model_type === 'embedding'"
                  class="icon"
                />
                <Image
                  v-else-if="model.model_type === 'image'"
                  class="icon"
                />
                <Mic
                  v-else
                  class="icon"
                />
              </div>
              <el-dropdown
                trigger="click"
                @click.stop
              >
                <el-button
                  text
                  size="small"
                >
                  <MoreVertical />
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="testModel(model)">
                      <Play class="menu-icon" />
                      测试连接
                    </el-dropdown-item>
                    <el-dropdown-item @click="handleToggleDefault">
                      <Star class="menu-icon" />
                      {{ model.is_default ? '取消默认' : '设为默认' }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <h3 class="model-name">
              {{ model.name }}
            </h3>
            <p class="model-id">
              ID: {{ model.model_id }}
            </p>

            <div class="model-meta">
              <el-tag
                size="small"
                type="info"
              >
                {{ getProviderLabel(model.provider_slug) }}
              </el-tag>
              <el-tag
                v-if="model.is_default"
                size="small"
                type="warning"
              >
                默认
              </el-tag>
            </div>

            <div class="model-caps">
              <span
                v-if="model.supports_streaming"
                class="cap"
              >
                <Zap class="cap-icon" /> 流式
              </span>
              <span
                v-if="model.supports_function_calling"
                class="cap"
              >
                <Code class="cap-icon" /> 函数
              </span>
              <span
                v-if="model.supports_vision"
                class="cap"
              >
                <Eye class="cap-icon" /> 视觉
              </span>
            </div>

            <div class="model-pricing">
              <span class="price">
                <span class="price-label">输入</span>
                <span class="price-value">${{ model.input_price }}/1M</span>
              </span>
              <span class="price">
                <span class="price-label">输出</span>
                <span class="price-value">${{ model.output_price }}/1M</span>
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Usage Stats Tab -->
      <el-tab-pane
        label="使用统计"
        name="stats"
      >
        <div
          v-if="apiAggregate"
          class="stats-container"
        >
          <div class="stats-overview">
            <div class="stat-card">
              <div class="stat-icon">
                <Activity />
              </div>
              <div class="stat-content">
                <div class="stat-value">
                  {{ (apiAggregate.overall?.total_calls ?? 0).toLocaleString() }}
                </div>
                <div class="stat-label">
                  API 调用次数
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">
                <Cpu />
              </div>
              <div class="stat-content">
                <div class="stat-value">
                  {{ formatNumber(apiAggregate.overall?.total_tokens) }}
                </div>
                <div class="stat-label">
                  Token 使用量
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">
                <DollarSign />
              </div>
              <div class="stat-content">
                <div class="stat-value">
                  ${{ (apiAggregate.overall?.total_cost ?? 0).toFixed(4) }}
                </div>
                <div class="stat-label">
                  费用
                </div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">
                <Clock />
              </div>
              <div class="stat-content">
                <div class="stat-value">
                  {{ apiAggregate.overall?.avg_latency ?? 0 }}ms
                </div>
                <div class="stat-label">
                  平均延迟
                </div>
              </div>
            </div>
          </div>

          <div class="stats-detail">
            <div class="stats-section">
              <h3>按提供商</h3>
              <el-table
                :data="apiAggregate.by_provider"
                stripe
              >
                <el-table-column
                  prop="provider"
                  label="提供商"
                >
                  <template #default="{ row }">
                    {{ getProviderLabel(row.provider) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="calls"
                  label="调用次数"
                >
                  <template #default="{ row }">
                    {{ (row.calls ?? 0).toLocaleString() }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="tokens"
                  label="Token"
                >
                  <template #default="{ row }">
                    {{ formatNumber(row.tokens) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="cost"
                  label="费用"
                >
                  <template #default="{ row }">
                    ${{ (row.cost || 0).toFixed(4) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="stats-section">
              <h3>按模型</h3>
              <el-table
                :data="apiAggregate.by_model"
                stripe
              >
                <el-table-column
                  prop="model"
                  label="模型"
                />
                <el-table-column
                  prop="calls"
                  label="调用次数"
                >
                  <template #default="{ row }">
                    {{ (row.calls ?? 0).toLocaleString() }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="tokens"
                  label="Token"
                >
                  <template #default="{ row }">
                    {{ formatNumber(row.tokens) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="cost"
                  label="费用"
                >
                  <template #default="{ row }">
                    ${{ (row.cost || 0).toFixed(4) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Logs Tab -->
      <el-tab-pane
        label="调用日志"
        name="logs"
      >
        <div class="logs-header">
          <el-date-picker
            v-model="logDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="fetchLogs"
          />
          <el-button @click="fetchLogs">
            <RefreshCw class="btn-icon" />
            刷新
          </el-button>
        </div>

        <el-table
          v-loading="apiLogsLoading"
          :data="apiLogs"
          stripe
        >
          <el-table-column
            prop="timestamp"
            label="时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="provider"
            label="提供商"
            width="120"
          >
            <template #default="{ row }">
              {{ getProviderLabel(row.provider) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="model"
            label="模型"
          />
          <el-table-column
            prop="input_tokens"
            label="输入 Token"
            width="120"
          >
            <template #default="{ row }">
              {{ (row.input_tokens ?? 0).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column
            prop="output_tokens"
            label="输出 Token"
            width="120"
          >
            <template #default="{ row }">
              {{ (row.output_tokens ?? 0).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column
            prop="latency_ms"
            label="延迟"
            width="100"
          >
            <template #default="{ row }">
              {{ row.latency_ms }}ms
            </template>
          </el-table-column>
          <el-table-column
            prop="cost"
            label="费用"
            width="100"
          >
            <template #default="{ row }">
              ${{ row.cost.toFixed(6) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="status_code"
            label="状态"
            width="80"
          >
            <template #default="{ row }">
              <el-tag
                :type="row.status_code === 200 ? 'success' : 'danger'"
                size="small"
              >
                {{ row.status_code }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- API Key Dialog -->
    <el-dialog
      v-model="showAPIKeyDialog"
      :title="editingKey ? '编辑 API Key' : '添加 API Key'"
      width="500px"
    >
      <el-form
        ref="apiKeyFormRef"
        :model="apiKeyForm"
        :rules="apiKeyRules"
        label-position="top"
      >
        <el-form-item
          label="名称"
          prop="name"
        >
          <el-input
            v-model="apiKeyForm.name"
            placeholder="例如：我的 OpenAI 密钥"
          />
        </el-form-item>
        <el-form-item
          label="服务商"
          prop="provider"
        >
          <el-select
            v-model="apiKeyForm.provider"
            style="width: 100%"
          >
            <el-option
              label="OpenAI"
              value="openai"
            />
            <el-option
              label="Anthropic"
              value="anthropic"
            />
            <el-option
              label="Azure OpenAI"
              value="azure"
            />
            <el-option
              label="Google AI"
              value="google"
            />
            <el-option
              label="自定义"
              value="custom"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="API Key"
          prop="api_key"
        >
          <el-input
            v-model="apiKeyForm.api_key"
            type="password"
            show-password
            placeholder="sk-..."
          />
        </el-form-item>
        <el-form-item
          v-if="apiKeyForm.provider === 'azure'"
          label="API Endpoint"
        >
          <el-input
            v-model="apiKeyForm.endpoint"
            placeholder="https://xxx.openai.azure.com"
          />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="apiKeyForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAPIKeyDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSaveAPIKey"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Test Model Dialog -->
    <el-dialog
      v-model="showTestDialog"
      title="测试模型"
      width="500px"
    >
      <el-form label-position="top">
        <el-form-item label="测试提示">
          <el-input
            v-model="testPrompt"
            type="textarea"
            :rows="4"
            placeholder="输入测试提示..."
          />
        </el-form-item>
        <el-form-item label="模型">
          <el-input
            :value="testingModel?.name"
            disabled
          />
        </el-form-item>
      </el-form>
      <div
        v-if="testResult"
        class="test-result"
      >
        <h4>响应</h4>
        <div class="result-content">
          {{ testResult }}
        </div>
      </div>
      <template #footer>
        <el-button @click="showTestDialog = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          :loading="testing"
          @click="handleTest"
        >
          发送测试
        </el-button>
      </template>
    </el-dialog>
  </PageShell>
</template>

<script setup>
import PageEmptyState from '@/components/layout/PageEmptyState.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageShell from '@/components/layout/PageShell.vue'
import { ElMessageBox } from 'element-plus'
import { ref, reactive, computed, onMounted } from 'vue'
import { useGatewayStore } from '@/stores/gateway'
import { useAppStore } from '@/stores/app'
import {
  Key, Bot, Layers, Image, Mic, Search, MoreVertical,
  Edit, Trash2, CheckCircle, Play, Star, Zap, Code, Eye,
  Clock, Activity, Cpu, DollarSign, RefreshCw
} from 'lucide-vue-next'
import { formatNumber as formatCompactNumber } from '@/utils/formatters'

const gatewayStore = useGatewayStore()
const appStore = useAppStore()

const activeTab = ref('api-keys')
const showAPIKeyDialog = ref(false)
const showTestDialog = ref(false)
const editingKey = ref(null)
const testingModel = ref(null)
const testPrompt = ref('Hello, how are you?')
const testResult = ref('')
const testing = ref(false)
const saving = ref(false)

const filterProvider = ref('')
const filterType = ref('')
const searchQuery = ref('')
const logDateRange = ref([])

const apiKeyFormRef = ref(null)

const apiKeyForm = reactive({
  name: '',
  provider: 'openai',
  api_key: '',
  endpoint: '',
  is_active: true
})

const apiKeyRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择服务商', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }]
}

const apiKeys = computed(() => gatewayStore.apiKeys)
const apiKeysLoading = computed(() => gatewayStore.apiKeysLoading)
const providers = computed(() => gatewayStore.providers)
const models = computed(() => gatewayStore.models)
const modelsLoading = computed(() => gatewayStore.modelsLoading)
const apiLogs = computed(() => gatewayStore.apiLogs)
const apiLogsLoading = computed(() => gatewayStore.apiLogsLoading)
const apiAggregate = computed(() => gatewayStore.apiAggregate)

const filteredModels = computed(() => {
  let result = models.value

  if (filterProvider.value) {
    result = result.filter(m => m.provider_slug === filterProvider.value)
  }

  if (filterType.value) {
    result = result.filter(m => m.model_type === filterType.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(m =>
      m.name.toLowerCase().includes(query) ||
      m.model_id.toLowerCase().includes(query)
    )
  }

  return result
})

function getProviderType(provider) {
  const types = {
    openai: 'primary',
    anthropic: 'warning',
    azure: 'success',
    google: 'info',
    custom: 'info',
  }
  return types[provider] || undefined
}

function getProviderLabel(provider) {
  const labels = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    azure: 'Azure',
    google: 'Google',
    custom: '自定义'
  }
  return labels[provider] || provider
}

function maskKey(key) {
  if (!key || key.length < 8) return '***'
  return `${key.slice(0, 4)}...${key.slice(-4)}`
}

function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

function formatDateTime(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

function formatNumber(num) {
  return formatCompactNumber(num ?? 0)
}

function editAPIKey(key) {
  editingKey.value = key
  Object.assign(apiKeyForm, {
    name: key.name,
    provider: key.provider,
    api_key: key.api_key,
    endpoint: key.endpoint || '',
    is_active: key.is_active
  })
  showAPIKeyDialog.value = true
}

async function handleSaveAPIKey() {
  const valid = await apiKeyFormRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editingKey.value) {
      await gatewayStore.editAPIKey(editingKey.value.id, apiKeyForm)
      appStore.success('API Key 已更新')
    } else {
      await gatewayStore.addAPIKey(apiKeyForm)
      appStore.success('API Key 已添加')
    }
    showAPIKeyDialog.value = false
    resetForm()
    await gatewayStore.fetchAPIKeys()
  } catch (err) {
    appStore.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDeleteKey(key) {
  try {
    await ElMessageBox.confirm(`确定要删除 API Key "${key.name}" 吗？`, '删除确认', { type: 'warning' })
    await gatewayStore.removeAPIKey(key.id)
    appStore.success('已删除')
  } catch (err) {
    if (err !== 'cancel') appStore.error('删除失败')
  }
}

async function handleVerifyKey(key) {
  try {
    const result = await gatewayStore.verifyAPIKeyConnection(key.id)
    if (result.valid) {
      appStore.success('密钥验证成功')
    } else {
      appStore.error(`验证失败: ${result.error}`)
    }
  } catch (err) {
    appStore.error('验证失败')
  }
}

function testModel(model) {
  testingModel.value = model
  testPrompt.value = '请介绍一下你自己'
  testResult.value = ''
  showTestDialog.value = true
}

async function handleTest() {
  if (!testPrompt.value.trim()) return

  testing.value = true
  try {
    const result = await gatewayStore.testModelConnection(testingModel.value.id, {
      prompt: testPrompt.value
    })

    if (result.success) {
      testResult.value = result.response
    } else {
      testResult.value = `错误: ${result.error}`
    }
  } catch (err) {
    testResult.value = `错误: ${err.message}`
  } finally {
    testing.value = false
  }
}

async function handleToggleDefault() {
  try {
    appStore.info('该功能需要管理员权限')
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function fetchLogs() {
  const params = {}
  if (logDateRange.value?.length === 2) {
    params.start_date = logDateRange.value[0].toISOString()
    params.end_date = logDateRange.value[1].toISOString()
  }
  await gatewayStore.fetchAPILogs(params)
}

function resetForm() {
  Object.assign(apiKeyForm, {
    name: '',
    provider: 'openai',
    api_key: '',
    endpoint: '',
    is_active: true
  })
  editingKey.value = null
}

onMounted(async () => {
  await Promise.all([
    gatewayStore.fetchProviders(),
    gatewayStore.fetchModels(),
    gatewayStore.fetchAPIKeys(),
    gatewayStore.fetchAPIAggregate()
  ])
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.btn-icon {
  width: 16px;
  height: 16px;
}

.model-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: $spacing-6;
  }
}



.api-keys-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-4;
}

.api-key-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--content-card-radius);
  padding: var(--content-card-padding);
}

.key-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-3;
}

.key-info {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.key-name {
  font-weight: $font-weight-semibold;
}

.key-value {
  margin-bottom: $spacing-3;

  code {
    display: block;
    padding: $spacing-2 $spacing-3;
    background: var(--bg-tertiary);
    border-radius: $radius-md;
    font-family: monospace;
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.key-meta {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-3;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  .meta-item {
    display: flex;
    align-items: center;
    gap: $spacing-1;
  }

  .meta-icon {
    width: 14px;
    height: 14px;
  }
}

.key-actions {
  display: flex;
  gap: $spacing-2;
}

.models-header {
  margin-bottom: $spacing-4;
}

.filter-bar {
  display: flex;
  gap: $spacing-3;
}

.input-icon {
  width: 16px;
  height: 16px;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr));
  gap: $spacing-4;
}

.model-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--content-card-radius);
  padding: var(--content-card-padding);
  transition: all $transition-fast;

  &:hover {
    border-color: $color-primary;
    transform: translateY(-2px);
  }
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-3;
}

.model-icon {
  width: 40px;
  height: 40px;
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba($color-primary, 0.15);

  .icon {
    width: 20px;
    height: 20px;
    color: $color-primary;
  }

  &.chat {
    background: rgba($color-primary, 0.15);
    .icon { color: $color-primary; }
  }

  &.embedding {
    background: rgba($color-secondary, 0.15);
    .icon { color: $color-secondary; }
  }

  &.image {
    background: rgba($color-success, 0.15);
    .icon { color: $color-success; }
  }

  &.audio {
    background: rgba($color-warning, 0.15);
    .icon { color: $color-warning; }
  }
}

.model-name {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  margin: 0 0 $spacing-1;
}

.model-id {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin: 0 0 $spacing-3;
}

.model-meta {
  display: flex;
  gap: $spacing-2;
  margin-bottom: $spacing-3;
}

.model-caps {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  margin-bottom: $spacing-3;

  .cap {
    display: flex;
    align-items: center;
    gap: $spacing-1;
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }

  .cap-icon {
    width: 12px;
    height: 12px;
  }
}

.model-pricing {
  display: flex;
  gap: $spacing-4;
  padding-top: $spacing-3;
  border-top: 1px solid var(--border-primary);

  .price {
    display: flex;
    flex-direction: column;
    font-size: $font-size-xs;
  }

  .price-label {
    color: var(--text-tertiary);
  }

  .price-value {
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }
}

.menu-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-2;
}

.stats-container {
  display: flex;
  flex-direction: column;
  gap: $spacing-6;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: $spacing-4;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba($color-primary, 0.15);
    color: $color-primary;
  }

  .stat-content {
    flex: 1;
  }

  .stat-value {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.stats-detail {
  display: flex;
  flex-direction: column;
  gap: $spacing-6;
}

.stats-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;

  h3 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    margin: 0 0 $spacing-4;
  }
}

.logs-header {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-4;
}

.test-result {
  margin-top: $spacing-4;
  padding: $spacing-4;
  background: var(--bg-tertiary);
  border-radius: $radius-lg;

  h4 {
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    margin: 0 0 $spacing-2;
  }

  .result-content {
    font-size: $font-size-sm;
    line-height: 1.6;
    white-space: pre-wrap;
  }
}
</style>

