<template>
  <div class="credentials-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">
          API Credentials
        </h1>
        <p class="page-description">
          Manage your external API credentials for AI model providers and integrations
        </p>
      </div>
      <el-button
        type="primary"
        :icon="Plus"
        @click="openCreateDialog"
      >
        Add Credential
      </el-button>
    </div>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <el-skeleton
        :rows="5"
        animated
      />
    </div>

    <!-- Empty State -->
    <el-empty
      v-else-if="!credentials.length"
      description="No credentials configured"
    >
      <el-button
        type="primary"
        @click="openCreateDialog"
      >
        Add Your First Credential
      </el-button>
    </el-empty>

    <!-- Credentials List -->
    <div
      v-else
      class="credentials-grid"
    >
      <el-card
        v-for="cred in credentials"
        :key="cred.id"
        class="credential-card"
        :class="{ 'inactive': !cred.is_active }"
      >
        <template #header>
          <div class="credential-header">
            <div class="credential-info">
              <el-tag
                size="small"
                :type="getProviderTagType(cred.service_type)"
              >
                {{ cred.service_type_display || cred.service_type }}
              </el-tag>
              <span class="credential-name">{{ cred.name }}</span>
            </div>
            <el-switch
              v-model="cred.is_active"
              :disabled="togglingId === cred.id"
              @change="toggleStatus(cred)"
            />
          </div>
        </template>

        <div class="credential-body">
          <div class="credential-detail">
            <span class="detail-label">Type:</span>
            <span class="detail-value">{{ cred.credential_type_display || cred.credential_type }}</span>
          </div>

          <div class="credential-detail">
            <span class="detail-label">API Key:</span>
            <code class="credential-value">{{ cred.masked_credential || '***' }}</code>
          </div>

          <div class="credential-stats">
            <div class="stat-item">
              <span class="stat-label">Usage Count</span>
              <span class="stat-value">{{ cred.usage_count || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Last Used</span>
              <span class="stat-value">{{ formatDate(cred.last_used_at) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Created</span>
              <span class="stat-value">{{ formatDate(cred.created_at) }}</span>
            </div>
          </div>

          <div
            v-if="cred.description"
            class="credential-description"
          >
            {{ cred.description }}
          </div>

          <div
            v-if="cred.is_encrypted"
            class="credential-badge"
          >
            <el-icon><Lock /></el-icon>
            <span>Encrypted</span>
          </div>
        </div>

        <template #footer>
          <div class="credential-actions">
            <el-button
              size="small"
              @click="openEditDialog(cred)"
            >
              Edit
            </el-button>
            <el-button
              size="small"
              type="primary"
              :loading="verifyingId === cred.id"
              @click="verifyCredential(cred)"
            >
              Verify
            </el-button>
            <el-button
              size="small"
              type="danger"
              :disabled="deletingId === cred.id"
              @click="deleteCredential(cred)"
            >
              Delete
            </el-button>
          </div>
        </template>
      </el-card>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingCredential ? 'Edit Credential' : 'Add Credential'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item
          label="Provider"
          prop="service_type"
        >
          <el-select
            v-model="formData.service_type"
            placeholder="Select provider"
            class="full-width"
          >
            <el-option
              v-for="provider in providers"
              :key="provider.id"
              :label="provider.name"
              :value="provider.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="Name"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="e.g., Production Key"
          />
        </el-form-item>

        <el-form-item
          label="Credential Type"
          prop="credential_type"
        >
          <el-select
            v-model="formData.credential_type"
            placeholder="Select type"
            class="full-width"
          >
            <el-option
              label="API Key"
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
          label="API Key / Token"
          prop="credential_data"
        >
          <el-input
            v-model="formData.credential_data"
            type="password"
            placeholder="sk-... or your API token"
            show-password
          />
          <div class="form-tip">
            Leave empty to keep current value when editing
          </div>
        </el-form-item>

        <el-form-item
          label="Description"
          prop="description"
        >
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="Optional description for this credential"
          />
        </el-form-item>

        <el-form-item
          label="Expires At"
          prop="expires_at"
        >
          <el-date-picker
            v-model="formData.expires_at"
            type="datetime"
            placeholder="Optional expiration date"
            class="full-width"
            :shortcuts="dateShortcuts"
          />
        </el-form-item>

        <el-form-item label="Active">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">
            Cancel
          </el-button>
          <el-button
            type="primary"
            :loading="submitting"
            @click="submitForm"
          >
            {{ editingCredential ? 'Update' : 'Create' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Lock } from 'lucide-vue-next'
import api from '@/api'

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
  service_type: '',
  name: '',
  credential_type: 'api_key',
  credential_data: '',
  description: '',
  expires_at: null,
  is_active: true
})

const formRules = {
  service_type: [{ required: true, message: 'Please select a provider', trigger: 'change' }],
  name: [{ required: true, message: 'Please enter a name', trigger: 'blur' }],
  credential_type: [{ required: true, message: 'Please select a credential type', trigger: 'change' }],
  credential_data: [
    { required: true, message: 'Please enter the credential', trigger: 'blur' },
    { min: 4, message: 'Credential must be at least 4 characters', trigger: 'blur' }
  ]
}

const dateShortcuts = [
  { text: '7 days', value: () => new Date(Date.now() + 7 * 24 * 3600 * 1000) },
  { text: '30 days', value: () => new Date(Date.now() + 30 * 24 * 3600 * 1000) },
  { text: '90 days', value: () => new Date(Date.now() + 90 * 24 * 3600 * 1000) }
]

function getProviderTagType(provider) {
  const types = {
    openai: '',
    anthropic: 'success',
    azure: 'warning',
    google: 'info',
    aws: 'danger',
    stability: 'warning',
    replicate: 'info',
    elevenlabs: 'success',
    pinecone: '',
    huggingface: '',
    cohere: 'info',
    slack: 'warning',
    discord: 'danger',
    github: '',
    custom: 'info'
  }
  return types[provider] || ''
}

function formatDate(dateStr) {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`
  return date.toLocaleDateString()
}

async function loadCredentials() {
  loading.value = true
  try {
    const response = await api.get('/api/v1/credentials/')
    credentials.value = response.data || []
  } catch (error) {
    console.error('Failed to load credentials:', error)
    ElMessage.error('Failed to load credentials')
  } finally {
    loading.value = false
  }
}

async function loadProviders() {
  try {
    const response = await api.get('/api/v1/credentials/providers/')
    providers.value = response.data?.providers || []
  } catch (error) {
    console.error('Failed to load providers:', error)
    // Fallback to static list
    providers.value = [
      { id: 'openai', name: 'OpenAI' },
      { id: 'anthropic', name: 'Anthropic' },
      { id: 'google', name: 'Google AI' },
      { id: 'azure', name: 'Azure' },
      { id: 'aws', name: 'AWS' },
      { id: 'stability', name: 'Stability AI' },
      { id: 'replicate', name: 'Replicate' },
      { id: 'elevenlabs', name: 'ElevenLabs' },
      { id: 'pinecone', name: 'Pinecone' },
      { id: 'huggingface', name: 'HuggingFace' },
      { id: 'cohere', name: 'Cohere' },
      { id: 'slack', name: 'Slack' },
      { id: 'discord', name: 'Discord' },
      { id: 'github', name: 'GitHub' },
      { id: 'custom', name: 'Custom' }
    ]
  }
}

function openCreateDialog() {
  editingCredential.value = null
  Object.assign(formData, {
    service_type: '',
    name: '',
    credential_type: 'api_key',
    credential_data: '',
    description: '',
    expires_at: null,
    is_active: true
  })
  formRef.value?.resetFields()
  dialogVisible.value = true
}

function openEditDialog(cred) {
  editingCredential.value = cred
  Object.assign(formData, {
    service_type: cred.service_type || '',
    name: cred.name,
    credential_type: cred.credential_type,
    credential_data: '', // Don't pre-fill for security
    description: cred.description || '',
    expires_at: cred.expires_at ? new Date(cred.expires_at) : null,
    is_active: cred.is_active
  })
  dialogVisible.value = true
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = { ...formData }
    
    // Format expires_at
    if (payload.expires_at) {
      payload.expires_at = new Date(payload.expires_at).toISOString()
    } else {
      delete payload.expires_at
    }

    if (editingCredential.value) {
      // For update, only send credential_data if it was changed
      if (!payload.credential_data) {
        delete payload.credential_data
      }
      await api.put(`/api/v1/credentials/${editingCredential.value.id}/`, payload)
      ElMessage.success('Credential updated successfully')
    } else {
      await api.post('/api/v1/credentials/', payload)
      ElMessage.success('Credential created successfully')
    }
    
    dialogVisible.value = false
    await loadCredentials()
  } catch (error) {
    console.error('Failed to save credential:', error)
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || 'Failed to save credential')
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(cred) {
  togglingId.value = cred.id
  try {
    await api.patch(`/api/v1/credentials/${cred.id}/`, { is_active: cred.is_active })
    ElMessage.success(`Credential ${cred.is_active ? 'enabled' : 'disabled'}`)
  } catch (error) {
    console.error('Failed to toggle status:', error)
    cred.is_active = !cred.is_active // Revert
    ElMessage.error('Failed to update status')
  } finally {
    togglingId.value = null
  }
}

async function verifyCredential(cred) {
  verifyingId.value = cred.id
  try {
    const response = await api.post(`/api/v1/credentials/${cred.id}/verify/`)
    if (response.data.valid) {
      ElMessage.success('Credential is valid: ' + (response.data.message || 'Verified'))
    } else {
      ElMessage.warning('Credential verification failed: ' + (response.data.message || response.data.error || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to verify credential:', error)
    ElMessage.error('Verification failed: ' + (error.response?.data?.error || error.message))
  } finally {
    verifyingId.value = null
  }
}

async function deleteCredential(cred) {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to delete this credential? This action cannot be undone.',
      'Delete Credential',
      { type: 'warning' }
    )
    
    deletingId.value = cred.id
    await api.delete(`/api/v1/credentials/${cred.id}/`)
    ElMessage.success('Credential deleted')
    await loadCredentials()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete credential:', error)
      ElMessage.error('Failed to delete credential')
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
.credentials-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 4px 0;
}

.page-description {
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

.loading-container {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  padding: 24px;
}

.credentials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 16px;
}

.credential-card {
  border-radius: 12px;
  transition: box-shadow 0.2s ease;
}

.credential-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
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
}

.credential-name {
  font-weight: 600;
  font-size: 16px;
}

.credential-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.credential-detail {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-label {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  min-width: 70px;
}

.detail-value {
  font-size: 14px;
}

.credential-value {
  background: var(--bg-secondary, #f3f4f6);
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  flex: 1;
}

.credential-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--border-color, #e5e7eb);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
}

.stat-value {
  font-size: 13px;
  font-weight: 500;
}

.credential-description {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.5;
}

.credential-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--accent-muted, #f0f9ff);
  color: var(--primary-color, #3b82f6);
  border-radius: 4px;
  font-size: 12px;
  width: fit-content;
}

.credential-badge .el-icon {
  width: 14px;
  height: 14px;
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
  color: var(--text-secondary, #6b7280);
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
