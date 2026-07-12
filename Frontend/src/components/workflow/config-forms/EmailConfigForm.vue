<template>
  <div class="config-form email-config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <!-- 基本信息 -->
      <div class="form-section">
        <h4 class="section-title">
          基本信息
        </h4>
        <el-form-item label="节点名称">
          <el-input
            v-model="localData.label"
            placeholder="输入节点名称"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="localData.description" 
            type="textarea" 
            :rows="2"
            placeholder="节点功能描述"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 收件人配置 -->
      <div class="form-section">
        <h4 class="section-title">
          收件人
        </h4>
        <el-form-item
          label="收件人"
          required
        >
          <el-input 
            v-model="localData.to" 
            placeholder="user@example.com，支持 {{变量}} 插值"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="抄送 (CC)">
          <el-input 
            v-model="localData.cc" 
            placeholder="cc@example.com，多个用逗号分隔"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="密送 (BCC)">
          <el-input 
            v-model="localData.bcc" 
            placeholder="bcc@example.com，多个用逗号分隔"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 邮件内容 -->
      <div class="form-section">
        <h4 class="section-title">
          邮件内容
        </h4>
        <el-form-item label="发件人">
          <el-input 
            v-model="localData.fromEmail" 
            placeholder="留空则使用系统默认发件人"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item
          label="主题"
          required
        >
          <el-input 
            v-model="localData.subject" 
            placeholder="邮件主题，支持 {{变量}} 插值"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="内容类型">
          <el-radio-group
            v-model="localData.isHtml"
            @change="handleChange"
          >
            <el-radio :value="false">
              纯文本
            </el-radio>
            <el-radio :value="true">
              HTML
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item
          label="正文"
          required
        >
          <el-input 
            v-model="localData.body"
            type="textarea"
            :rows="6"
            :placeholder="localData.isHtml ? '<p>HTML 内容</p>' : '纯文本内容'"
            class="body-input"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- SMTP 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          SMTP 配置
        </h4>
        <el-form-item label="使用全局 SMTP">
          <div class="switch-row">
            <el-switch
              v-model="localData.useGlobalSmtp"
              @change="handleGlobalSmtpToggle"
            />
            <span class="switch-label">
              {{ localData.useGlobalSmtp ? '使用系统默认（设置 → 通知与邮件 / .env）' : '使用节点自定义 SMTP' }}
            </span>
          </div>
        </el-form-item>
        <div class="section-hint">
          开启后将自动使用平台全局 SMTP 发送；关闭后可在此节点单独填写并覆盖。
        </div>
        <div
          v-if="localData.useGlobalSmtp && globalSmtp.configured"
          class="global-smtp-badge"
        >
          已检测到全局 SMTP：{{ globalSmtp.server }}:{{ globalSmtp.port }}（{{ globalSmtp.username }}）
        </div>
        <div
          v-else-if="localData.useGlobalSmtp && !globalSmtpLoaded"
          class="section-hint"
        >
          正在加载全局 SMTP…
        </div>
        <div
          v-else-if="localData.useGlobalSmtp && !globalSmtp.configured"
          class="global-smtp-warning"
        >
          全局 SMTP 尚未配置，请先在「设置 → 通知与邮件」或 Backend `.env` 中配置。
        </div>
        <div
          class="smtp-config"
          :class="{ readonly: localData.useGlobalSmtp }"
        >
          <el-form-item label="服务器">
            <el-input 
              v-model="localData.smtpConfig.server" 
              placeholder="smtp.example.com"
              :disabled="localData.useGlobalSmtp"
              @change="handleChange"
            />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="端口">
                <el-input-number
                  v-model="localData.smtpConfig.port" 
                  :min="1" 
                  :max="65535"
                  placeholder="587"
                  controls-position="right"
                  style="width: 100%"
                  :disabled="localData.useGlobalSmtp"
                  @change="handleChange"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="TLS">
                <el-switch
                  v-model="localData.smtpConfig.useTls"
                  :disabled="localData.useGlobalSmtp"
                  @change="handleChange"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="用户名">
            <el-input 
              v-model="localData.smtpConfig.username" 
              placeholder="username"
              :disabled="localData.useGlobalSmtp"
              @change="handleChange"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input 
              v-model="localData.smtpConfig.password" 
              type="password" 
              show-password
              :placeholder="smtpPasswordPlaceholder"
              :disabled="localData.useGlobalSmtp"
              @change="handleChange"
            />
          </el-form-item>
        </div>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="email-preview">
          <div class="preview-row">
            <span class="preview-label">收件人:</span>
            <span class="preview-value">{{ localData.to || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">主题:</span>
            <span class="preview-value">{{ localData.subject || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">类型:</span>
            <el-tag
              size="small"
              :type="localData.isHtml ? 'success' : 'info'"
            >
              {{ localData.isHtml ? 'HTML' : '纯文本' }}
            </el-tag>
          </div>
          <div
            v-if="localData.cc"
            class="preview-row"
          >
            <span class="preview-label">抄送:</span>
            <span class="preview-value">{{ localData.cc }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch, ref, onMounted, computed } from 'vue'
import { getEmailSmtpDefaults } from '@/api/workflow'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const globalSmtpLoaded = ref(false)
const globalSmtp = reactive({
  server: '',
  port: 587,
  useTls: true,
  username: '',
  fromEmail: '',
  hasPassword: false,
  configured: false,
})

const localData = reactive({
  label: '',
  description: '',
  to: '',
  cc: '',
  bcc: '',
  fromEmail: '',
  subject: '',
  isHtml: false,
  body: '',
  useGlobalSmtp: true,
  smtpConfig: {
    server: '',
    port: 587,
    useTls: true,
    username: '',
    password: ''
  }
})

const smtpPasswordPlaceholder = computed(() => {
  if (!localData.useGlobalSmtp) return '密码'
  return globalSmtp.hasPassword ? '使用全局授权码' : '密码'
})

async function loadGlobalSmtp() {
  try {
    const resp = await getEmailSmtpDefaults()
    const smtp = resp?.smtp || resp?.data?.smtp || {}
    Object.assign(globalSmtp, {
      server: smtp.server || '',
      port: smtp.port || 587,
      useTls: smtp.useTls !== false,
      username: smtp.username || '',
      fromEmail: smtp.fromEmail || '',
      hasPassword: Boolean(smtp.hasPassword),
      configured: Boolean(smtp.configured),
    })
  } catch {
    // ignore — user can still configure node-level SMTP
  } finally {
    globalSmtpLoaded.value = true
    applyGlobalSmtpToForm()
  }
}

function applyGlobalSmtpToForm() {
  if (!localData.useGlobalSmtp) return
  localData.smtpConfig.server = globalSmtp.server
  localData.smtpConfig.port = globalSmtp.port
  localData.smtpConfig.useTls = globalSmtp.useTls
  localData.smtpConfig.username = globalSmtp.username
  localData.smtpConfig.password = globalSmtp.hasPassword ? '********' : ''
  if (!localData.fromEmail && globalSmtp.fromEmail) {
    localData.fromEmail = globalSmtp.fromEmail
  }
}

function handleGlobalSmtpToggle() {
  if (localData.useGlobalSmtp) {
    applyGlobalSmtpToForm()
  }
  handleChange()
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      to: newVal.to || '',
      cc: newVal.cc || '',
      bcc: newVal.bcc || '',
      fromEmail: newVal.fromEmail || '',
      subject: newVal.subject || '',
      isHtml: newVal.isHtml || false,
      body: newVal.body || '',
      useGlobalSmtp: newVal.useGlobalSmtp !== false,
      smtpConfig: {
        server: newVal.smtpConfig?.server || '',
        port: newVal.smtpConfig?.port || 587,
        useTls: newVal.smtpConfig?.useTls !== undefined ? newVal.smtpConfig.useTls : true,
        username: newVal.smtpConfig?.username || '',
        password: newVal.smtpConfig?.password || ''
      }
    })
    if (localData.useGlobalSmtp && globalSmtpLoaded.value) {
      applyGlobalSmtpToForm()
    }
  }
}, { immediate: true, deep: true })

onMounted(() => {
  loadGlobalSmtp()
})

const handleChange = () => {
  const payload = { ...localData }
  if (payload.useGlobalSmtp) {
    payload.smtpConfig = {
      server: '',
      port: payload.smtpConfig.port || 587,
      useTls: payload.smtpConfig.useTls !== false,
      username: '',
      password: '',
    }
  }
  emit('update:modelValue', payload)
  emit('change', payload)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.config-form {
  padding: 0;
}

.form-section {
  margin-bottom: $spacing-5;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-hint {
  margin: -$spacing-1 0 $spacing-3;
  font-size: $font-size-xs;
  line-height: 1.5;
  color: var(--text-secondary);
}

.switch-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.switch-label {
  font-size: $font-size-xs;
  color: var(--text-secondary);
}

.global-smtp-badge {
  margin-bottom: $spacing-3;
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-md;
  background: color-mix(in srgb, var(--color-success, #22c55e) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-success, #22c55e) 35%, transparent);
  font-size: $font-size-xs;
  color: var(--text-primary);
}

.global-smtp-warning {
  margin-bottom: $spacing-3;
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-md;
  background: color-mix(in srgb, var(--color-warning, #f59e0b) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-warning, #f59e0b) 35%, transparent);
  font-size: $font-size-xs;
  color: var(--text-primary);
}

.smtp-config.readonly {
  opacity: 0.92;
}

.body-input {
  :deep(.el-textarea__inner) {
    font-family: inherit;
    resize: vertical;
    min-height: 100px;
  }
}

.smtp-config {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  :deep(.el-form-item) {
    margin-bottom: $spacing-3;

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(.el-form-item__label) {
    font-size: $font-size-xs;
  }
}

.email-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.preview-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .preview-label {
    color: var(--text-tertiary);
    min-width: 50px;
  }

  .preview-value {
    color: var(--text-primary);
    flex: 1;
    word-break: break-all;
  }
}
</style>
