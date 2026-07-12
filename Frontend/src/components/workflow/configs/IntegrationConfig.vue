<template>
  <div class="integration-config">
    <div class="form-group">
      <label>操作</label>
      <el-select
        :model-value="localConfig.operation"
        @update:model-value="updateField('operation', $event)"
      >
        <el-option
          v-for="op in operations"
          :key="op.value"
          :label="op.label"
          :value="op.value"
        />
      </el-select>
    </div>

    <div class="form-group">
      <label>服务凭证</label>
      <el-select
        :model-value="localConfig.credentialId || ''"
        clearable
        filterable
        :loading="credentialsLoading"
        placeholder="选择已保存的 API 凭证"
        @update:model-value="updateField('credentialId', $event)"
        @visible-change="onCredentialDropdown"
      >
        <el-option
          v-for="cred in credentialOptions"
          :key="cred.id"
          :label="credLabel(cred)"
          :value="cred.id"
        />
      </el-select>
      <p class="form-hint">
        在
        <router-link
          to="/settings/credentials"
          class="cred-link"
        >
          模型与服务凭证
        </router-link>
        中添加 {{ providerLabel }} 密钥；凭证 JSON 示例：
        <code v-if="credentialHint">{{ credentialHint }}</code>
      </p>
    </div>

    <template
      v-for="field in dynamicFields"
      :key="field.key"
    >
      <div class="form-group">
        <label>{{ field.label }}</label>
        <el-input
          v-if="field.type === 'text'"
          :model-value="localConfig[field.key]"
          :placeholder="field.placeholder"
          @update:model-value="updateField(field.key, $event)"
        />
        <el-input
          v-else-if="field.type === 'textarea'"
          type="textarea"
          :rows="field.rows || 3"
          :model-value="localConfig[field.key]"
          :placeholder="field.placeholder"
          @update:model-value="updateField(field.key, $event)"
        />
        <el-input-number
          v-else-if="field.type === 'number'"
          :model-value="Number(localConfig[field.key]) || 0"
          :min="field.min ?? 0"
          @update:model-value="updateField(field.key, $event)"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  getIntegrationMeta,
  getIntegrationCredentialProvider,
} from '@/config/integrations'
import { listMyCredentials } from '@/api/credentials'

const props = defineProps({
  integrationType: { type: String, required: true },
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change'])

const meta = computed(() => getIntegrationMeta(props.integrationType))
const operations = computed(() => meta.value?.operations || [])
const credentialProvider = computed(() => getIntegrationCredentialProvider(props.integrationType))
const providerLabel = computed(() => meta.value?.label || props.integrationType)

const localConfig = reactive({ ...props.modelValue })
const credentialsLoading = ref(false)
const credentialOptions = ref([])
const credentialsLoaded = ref(false)

watch(
  () => props.modelValue,
  (val) => Object.assign(localConfig, val || {}),
  { deep: true }
)

const credentialHint = computed(() => {
  const hints = {
    feishu: '{"webhookUrl":"https://..."} 或 {"appId":"...","appSecret":"..."}',
    dingtalk: '{"webhookUrl":"https://oapi.dingtalk.com/robot/send?access_token=...","secret":"..."}',
    wechat_work: '{"webhookUrl":"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."}',
    slack: 'Bot Token 纯文本或 {"token":"xoxb-..."}',
    github: 'Personal Access Token 纯文本',
    openai_api: 'API Key 纯文本',
  }
  return hints[props.integrationType] || 'API Key 纯文本，或 {"token":"..."} JSON'
})

async function loadCredentials() {
  if (credentialsLoaded.value) return
  credentialsLoading.value = true
  try {
    const res = await listMyCredentials({
      service_type: credentialProvider.value,
    })
    const list = res?.credentials || res?.results || res || []
    credentialOptions.value = Array.isArray(list) ? list : []
    credentialsLoaded.value = true
  } catch {
    credentialOptions.value = []
  } finally {
    credentialsLoading.value = false
  }
}

function onCredentialDropdown(visible) {
  if (visible) loadCredentials()
}

function credLabel(cred) {
  const name = cred.name || cred.id
  const masked = cred.maskedCredential || cred.masked_credential || '***'
  return `${name} (${masked})`
}

const dynamicFields = computed(() => {
  const type = props.integrationType

  const common = {
    feishu: [
      { key: 'webhookUrl', label: 'Webhook URL（可选）', type: 'text' },
      { key: 'receiveId', label: '接收方 ID', type: 'text', placeholder: 'chat_id / open_id' },
      { key: 'text', label: '消息内容', type: 'textarea', placeholder: '{{input.message}}' },
    ],
    dingtalk: [
      { key: 'webhookUrl', label: 'Webhook URL（无凭证时填写）', type: 'text' },
      { key: 'text', label: '消息内容', type: 'textarea', placeholder: '{{input.message}}' },
    ],
    wechat_work: [
      { key: 'webhookUrl', label: 'Webhook URL（无凭证时填写）', type: 'text' },
      { key: 'text', label: '消息内容', type: 'textarea', placeholder: '{{input.message}}' },
    ],
    slack: [
      { key: 'channel', label: '频道 ID', type: 'text', placeholder: 'C01234567' },
      { key: 'text', label: '消息内容', type: 'textarea', placeholder: '{{input.message}}' },
    ],
    discord: [
      { key: 'webhookUrl', label: 'Webhook URL', type: 'text' },
      { key: 'content', label: '消息内容', type: 'textarea', placeholder: '{{input.message}}' },
    ],
    telegram: [
      { key: 'chatId', label: 'Chat ID', type: 'text' },
      { key: 'text', label: '消息内容', type: 'textarea', placeholder: '{{input.message}}' },
    ],
    notion: [
      { key: 'databaseId', label: 'Database ID', type: 'text' },
      { key: 'title', label: '标题', type: 'text', placeholder: '{{input.title}}' },
      { key: 'properties', label: '属性 JSON', type: 'textarea', placeholder: '{}' },
    ],
    google_sheets: [
      { key: 'spreadsheetId', label: 'Spreadsheet ID', type: 'text' },
      { key: 'sheetName', label: 'Sheet 名称', type: 'text', placeholder: 'Sheet1' },
      { key: 'range', label: '范围', type: 'text', placeholder: 'A:Z' },
    ],
    mysql: [
      { key: 'query', label: 'SQL 查询', type: 'textarea', placeholder: 'SELECT * FROM users LIMIT 10' },
      { key: 'parameters', label: '参数 JSON', type: 'textarea', placeholder: '[]' },
    ],
    postgres: [
      { key: 'query', label: 'SQL 查询', type: 'textarea' },
    ],
    mongodb: [
      { key: 'database', label: '数据库', type: 'text' },
      { key: 'collection', label: '集合', type: 'text' },
      { key: 'filter', label: 'Filter JSON', type: 'textarea', placeholder: '{}' },
    ],
    redis: [
      { key: 'key', label: 'Key', type: 'text' },
      { key: 'value', label: 'Value', type: 'text' },
      { key: 'ttl', label: 'TTL (秒)', type: 'number', min: 0 },
    ],
    github: [
      { key: 'owner', label: 'Owner', type: 'text' },
      { key: 'repo', label: 'Repository', type: 'text' },
      { key: 'title', label: '标题', type: 'text', placeholder: '{{input.title}}' },
      { key: 'body', label: '内容', type: 'textarea' },
    ],
    rss_feed: [
      { key: 'url', label: 'Feed URL', type: 'text' },
      { key: 'maxItems', label: '最大条数', type: 'number', min: 1 },
    ],
  }

  return common[type] || [
    { key: 'payload', label: '请求参数 JSON', type: 'textarea', placeholder: '{{input}}' },
  ]
})

function updateField(key, value) {
  localConfig[key] = value
  emit('update:modelValue', { ...localConfig })
  emit('change', { ...localConfig })
}
</script>

<style scoped>
.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-muted, #6b7280);
  margin-bottom: 6px;
}

.form-hint {
  font-size: 11px;
  color: var(--flow-text-muted, #9ca3af);
  margin-top: 4px;
  line-height: 1.5;
}

.form-hint code {
  display: block;
  margin-top: 4px;
  padding: 4px 6px;
  background: var(--bg-tertiary, #f3f4f6);
  border-radius: 4px;
  font-size: 10px;
  word-break: break-all;
}

.cred-link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.cred-link:hover {
  text-decoration: underline;
}
</style>
