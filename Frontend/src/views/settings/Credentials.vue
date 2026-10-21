<template>
  <div class="credentials-page">
    <PageHeader
      compact
      title="模型与服务凭证"
      subtitle="统一管理大模型服务商及第三方集成的访问密钥。所有凭证加密存储。"
    >
      <template #actions>
        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          添加凭证
        </el-button>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <el-skeleton
        :rows="5"
        animated
      />
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else-if="!credentials.length"
      description="暂无个人凭证，请添加第一个"
    >
      <el-button
        type="primary"
        @click="openCreateDialog"
      >
        添加第一个凭证
      </el-button>
    </el-empty>

    <!-- 凭证列表 -->
    <div
      v-else
      class="credentials-grid"
    >
      <el-card
        v-for="cred in credentials"
        :key="cred.id"
        class="credential-card"
        :class="{ inactive: !cred.isActive }"
      >
        <template #header>
          <div class="credential-header">
            <div class="credential-info">
              <el-tag
                size="small"
                :type="getProviderTagType(cred.serviceType)"
              >
                {{ cred.serviceTypeDisplay || cred.serviceType }}
              </el-tag>
              <span class="credential-name">{{ cred.name }}</span>
            </div>
            <el-switch
              v-model="cred.isActive"
              :disabled="togglingId === cred.id"
              @change="toggleStatus(cred)"
            />
          </div>
        </template>

        <div class="credential-body">
          <div class="credential-detail">
            <span class="detail-label">类型</span>
            <span class="detail-value">{{ cred.credentialTypeDisplay || cred.credentialType }}</span>
          </div>

          <div class="credential-detail">
            <span class="detail-label">密钥</span>
            <code class="credential-value">{{ cred.maskedCredential || '***' }}</code>
          </div>

          <div
            v-if="cred.isExpired"
            class="expired-warning"
          >
            <el-icon><Warning /></el-icon>
            <span>已过期</span>
          </div>

          <div class="credential-stats">
            <div class="stat-item">
              <span class="stat-label">使用次数</span>
              <span class="stat-value">{{ cred.usageCount || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">上次使用</span>
              <span class="stat-value">{{ formatDate(cred.lastUsedAt) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">创建时间</span>
              <span class="stat-value">{{ formatDate(cred.createdAt) }}</span>
            </div>
          </div>

          <div
            v-if="cred.description"
            class="credential-description"
          >
            {{ cred.description }}
          </div>

          <div
            v-if="cred.isEncrypted"
            class="credential-badge"
          >
            <el-icon><Lock /></el-icon>
            <span>已加密</span>
          </div>
        </div>

        <template #footer>
          <div class="credential-actions">
            <el-button
              size="small"
              :loading="verifyingId === cred.id"
              @click="testCredential(cred)"
            >
              测试
            </el-button>
            <el-button
              size="small"
              @click="openEditDialog(cred)"
            >
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              :disabled="deletingId === cred.id"
              @click="removeCredential(cred)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-card>
    </div>

    <!-- 创建 / 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingCredential ? '编辑凭证' : '添加凭证'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="110px"
      >
        <el-form-item
          label="服务商"
          prop="serviceType"
        >
          <el-select
            v-model="formData.serviceType"
            placeholder="请选择服务商"
            filterable
            class="full-width"
          >
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="凭证名称"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="例如：生产环境 OpenAI Key"
          />
        </el-form-item>

        <el-form-item
          label="凭证类型"
          prop="credentialType"
        >
          <el-select
            v-model="formData.credentialType"
            placeholder="请选择类型"
            class="full-width"
          >
            <el-option
              label="API 密钥"
              value="api_key"
            />
            <el-option
              label="OAuth2"
              value="oauth2"
            />
            <el-option
              label="Basic Auth"
              value="basic"
            />
            <el-option
              label="Bearer Token"
              value="bearer"
            />
            <el-option
              label="AWS"
              value="aws"
            />
            <el-option
              label="Azure"
              value="azure"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="密钥 / Token"
          prop="credentialData"
        >
          <el-input
            v-model="formData.credentialData"
            type="password"
            show-password
            placeholder="请输入密钥或 Token"
          />
          <div class="form-tip">
            编辑时留空则保留原值
          </div>
        </el-form-item>

        <el-form-item
          label="过期时间"
          prop="expiresAt"
        >
          <el-date-picker
            v-model="formData.expiresAt"
            type="datetime"
            placeholder="不设置则永不过期"
            class="full-width"
            :shortcuts="dateShortcuts"
          />
        </el-form-item>

        <el-form-item
          label="描述"
          prop="description"
        >
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="可选描述，标明用途或所属环境"
          />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="formData.isActive" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="submitting"
            @click="submitForm"
          >
            {{ editingCredential ? '更新' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Lock, Warning } from '@element-plus/icons-vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import {
  listCredentials,
  createCredential,
  updateCredential,
  patchCredential,
  deleteCredential,
  listProviders,
  testProviderCredential
} from '@/api/credentials'

const loading = ref(false)
const credentials = ref([])
const providers = ref([])
const dialogVisible = ref(false)
const editingCredential = ref(null)
const submitting = ref(false)
const verifyingId = ref(null)
const deletingId = ref(null)
const togglingId = ref(null)
const formRef = ref(null)

const formData = reactive({
  serviceType: '',
  name: '',
  credentialType: 'api_key',
  credentialData: '',
  description: '',
  expiresAt: null,
  isActive: true
})

const formRules = {
  serviceType: [{ required: true, message: '请选择服务商', trigger: 'change' }],
  name: [{ required: true, message: '请输入凭证名称', trigger: 'blur' }],
  credentialType: [{ required: true, message: '请选择凭证类型', trigger: 'change' }],
  credentialData: [
    {
      validator: (rule, value, callback) => {
        if (!editingCredential.value && !value) {
          callback(new Error('请输入密钥或 Token'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const dateShortcuts = [
  { text: '7 天后', value: () => new Date(Date.now() + 7 * 24 * 3600 * 1000) },
  { text: '30 天后', value: () => new Date(Date.now() + 30 * 24 * 3600 * 1000) },
  { text: '90 天后', value: () => new Date(Date.now() + 90 * 24 * 3600 * 1000) }
]

function getProviderTagType(provider) {
  if (!provider) return undefined
  const types = {
    openai: 'primary',
    anthropic: 'success',
    azure: 'warning',
    google: 'info',
    aws: 'danger',
    stability: 'warning',
    replicate: 'info',
    elevenlabs: 'success',
    pinecone: 'info',
    huggingface: 'info',
    cohere: 'info',
    slack: 'warning',
    discord: 'danger',
    github: 'info',
    deepseek: 'success',
    ollama: 'info',
    mistral: 'info',
    groq: 'warning',
    custom: 'info'
  }
  return types[provider] || 'info'
}

function formatDate(dateStr) {
  if (!dateStr) return '从未'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`
  if (days < 30) return `${Math.floor(days / 7)} 周前`
  return date.toLocaleDateString('zh-CN')
}

async function loadCredentials() {
  loading.value = true
  try {
    const response = await listCredentials({ scope: 'user' })
    credentials.value = response.results || response || []
  } catch (error) {
    console.error('加载凭证失败:', error)
    ElMessage.error('加载凭证失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function loadProviders() {
  try {
    const response = await listProviders()
    providers.value = response.providers || []
  } catch {
    providers.value = [
      { id: 'openai', name: 'OpenAI' },
      { id: 'anthropic', name: 'Anthropic' },
      { id: 'google', name: 'Google AI' },
      { id: 'azure', name: 'Azure' },
      { id: 'aws', name: 'AWS' },
      { id: 'deepseek', name: 'DeepSeek' },
      { id: 'ollama', name: 'Ollama' },
      { id: 'mistral', name: 'Mistral' },
      { id: 'groq', name: 'Groq' },
      { id: 'huggingface', name: 'HuggingFace' },
      { id: 'cohere', name: 'Cohere' },
      { id: 'stability', name: 'Stability AI' },
      { id: 'elevenlabs', name: 'ElevenLabs' },
      { id: 'pinecone', name: 'Pinecone' },
      { id: 'custom', name: '自定义' }
    ]
  }
}

function openCreateDialog() {
  editingCredential.value = null
  Object.assign(formData, {
    serviceType: '',
    name: '',
    credentialType: 'api_key',
    credentialData: '',
    description: '',
    expiresAt: null,
    isActive: true
  })
  formRef.value?.resetFields()
  dialogVisible.value = true
}

function openEditDialog(cred) {
  editingCredential.value = cred
  Object.assign(formData, {
    serviceType: cred.serviceType || '',
    name: cred.name,
    credentialType: cred.credentialType,
    credentialData: '',
    description: cred.description || '',
    expiresAt: cred.expiresAt ? new Date(cred.expiresAt) : null,
    isActive: cred.isActive
  })
  dialogVisible.value = true
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      service_type: formData.serviceType,
      name: formData.name,
      credential_type: formData.credentialType,
      description: formData.description,
      scope: 'user',
      is_active: formData.isActive
    }

    if (formData.credentialData) {
      payload.credential_data = formData.credentialData
    }

    if (formData.expiresAt) {
      payload.expires_at = new Date(formData.expiresAt).toISOString()
    } else {
      payload.expires_at = null
    }

    if (editingCredential.value) {
      await updateCredential(editingCredential.value.id, payload)
      ElMessage.success('凭证已更新')
    } else {
      await createCredential(payload)
      ElMessage.success('凭证已创建')
    }

    dialogVisible.value = false
    await loadCredentials()
  } catch (error) {
    console.error('保存凭证失败:', error)
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(cred) {
  togglingId.value = cred.id
  try {
    await patchCredential(cred.id, { is_active: cred.isActive })
    ElMessage.success(`凭证已${cred.isActive ? '启用' : '禁用'}`)
  } catch {
    cred.isActive = !cred.isActive
    ElMessage.error('更新状态失败')
  } finally {
    togglingId.value = null
  }
}

async function testCredential(cred) {
  verifyingId.value = cred.id
  try {
    const response = await testProviderCredential(cred.serviceType, null, cred.id)
    if (response.valid) {
      ElMessage.success(`连接测试成功：${response.message || '有效'}`)
    } else {
      ElMessage.warning(`连接测试失败：${response.error || response.message || '未知错误'}`)
    }
  } catch {
    ElMessage.error('测试连接失败')
  } finally {
    verifyingId.value = null
  }
}

async function removeCredential(cred) {
  try {
    await ElMessageBox.confirm(
      '确定要删除此凭证吗？此操作不可撤销。',
      '删除凭证',
      { type: 'warning' }
    )
    deletingId.value = cred.id
    await deleteCredential(cred.id)
    ElMessage.success('凭证已删除')
    await loadCredentials()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除凭证失败')
    }
  } finally {
    deletingId.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadCredentials(), loadProviders()])
})
</script>

<style scoped>

.loading-container {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--border-primary);
}

.credentials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px;
}

.credential-card {
  border-radius: 12px;
  transition: box-shadow 0.2s ease;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.credential-card:hover {
  box-shadow: var(--shadow-md);
}

.credential-card.inactive {
  opacity: 0.6;
}

.credential-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.credential-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.credential-name {
  font-weight: 600;
  font-size: 16px;
  color: var(--text-primary);
}

.credential-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.credential-detail {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-label {
  font-size: 13px;
  color: var(--text-tertiary);
  min-width: 70px;
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
}

.credential-value {
  background: var(--bg-tertiary);
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
  flex: 1;
}

.expired-warning {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--warning);
  font-size: 13px;
  padding: 4px 8px;
  background: var(--warning-bg);
  border-radius: 4px;
}

.credential-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--border-primary);
  border-bottom: 1px solid var(--border-primary);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.stat-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.credential-description {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.credential-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--color-primary-10);
  color: var(--color-primary);
  border-radius: 4px;
  font-size: 12px;
  width: fit-content;
}

.credential-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.full-width {
  width: 100%;
}

.form-tip {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .credentials-grid {
    grid-template-columns: 1fr;
  }

  .credential-stats {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .stat-item {
    flex-direction: row;
    justify-content: space-between;
    text-align: left;
  }
}
</style>
