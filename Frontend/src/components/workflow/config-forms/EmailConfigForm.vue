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
            placeholder="noreply@example.com"
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
          SMTP 配置（可选）
        </h4>
        <div class="smtp-config">
          <el-form-item label="服务器">
            <el-input 
              v-model="localData.smtpConfig.server" 
              placeholder="smtp.example.com"
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
                  @change="handleChange"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="TLS">
                <el-switch
                  v-model="localData.smtpConfig.useTls"
                  @change="handleChange"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="用户名">
            <el-input 
              v-model="localData.smtpConfig.username" 
              placeholder="username"
              @change="handleChange"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input 
              v-model="localData.smtpConfig.password" 
              type="password" 
              show-password
              placeholder="密码"
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
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

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
  smtpConfig: {
    server: '',
    port: 587,
    useTls: true,
    username: '',
    password: ''
  }
})

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
      smtpConfig: {
        server: newVal.smtpConfig?.server || '',
        port: newVal.smtpConfig?.port || 587,
        useTls: newVal.smtpConfig?.useTls !== undefined ? newVal.smtpConfig.useTls : true,
        username: newVal.smtpConfig?.username || '',
        password: newVal.smtpConfig?.password || ''
      }
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
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
