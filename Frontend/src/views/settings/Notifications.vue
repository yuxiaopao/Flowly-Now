<template>
  <div class="notifications-settings-page">
    <PageHeader
      compact
      title="通知与邮件"
      subtitle="配置系统通知方式、默认发件人和系统级 SMTP，供邮件节点在未单独填写时复用。"
    />

    <div class="section">
      <h2>通知偏好</h2>
      <el-card shadow="never">
        <div class="setting-list">
          <div class="setting-row">
            <div class="setting-info">
              <h4>执行完成通知</h4>
              <p>工作流执行完成后显示应用内通知</p>
            </div>
            <el-switch v-model="settings.notifyOnComplete" />
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h4>执行失败通知</h4>
              <p>工作流执行失败时优先提醒，避免错误被忽略</p>
            </div>
            <el-switch v-model="settings.notifyOnError" />
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h4>邮件发送失败提醒</h4>
              <p>邮件节点发送失败时给出额外提醒</p>
            </div>
            <el-switch v-model="settings.notifyOnEmailFailure" />
          </div>
        </div>
      </el-card>
    </div>

    <div class="section">
      <h2>系统默认发件设置</h2>
      <el-card shadow="never">
        <el-form
          :model="settings"
          label-position="top"
          class="mail-form"
        >
          <el-form-item label="默认发件人邮箱">
            <el-input
              v-model="settings.defaultFromEmail"
              placeholder="noreply@example.com"
            />
            <div class="field-hint">
              邮件节点未填写“发件人”时，将优先使用这里的邮箱地址。
            </div>
          </el-form-item>

          <el-form-item label="默认发件人名称">
            <el-input
              v-model="settings.defaultFromName"
              placeholder="Flowly 通知中心"
            />
            <div class="field-hint">
              用于统一邮件品牌形象，例如“Flowly 通知中心”。
            </div>
          </el-form-item>

          <el-form-item label="默认回复邮箱">
            <el-input
              v-model="settings.defaultReplyTo"
              placeholder="support@example.com"
            />
            <div class="field-hint">
              需要用户直接回复邮件时建议设置。
            </div>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <div class="section">
      <h2>系统默认 SMTP</h2>
      <el-card shadow="never">
        <div class="smtp-intro">
          <el-alert
            title="邮件节点可以覆盖这里的默认 SMTP"
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              如果邮件节点填写了自己的 SMTP 配置，则优先使用节点内配置；如果留空，则自动回退到这里的系统默认 SMTP。
            </template>
          </el-alert>
        </div>

        <el-form
          :model="settings.smtp"
          label-position="top"
          class="mail-form"
        >
          <el-form-item label="SMTP 服务器">
            <el-input
              v-model="settings.smtp.server"
              placeholder="smtp.qq.com"
            />
          </el-form-item>

          <div class="grid-row">
            <el-form-item label="端口">
              <el-input-number
                v-model="settings.smtp.port"
                :min="1"
                :max="65535"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="TLS / STARTTLS">
              <div class="switch-row">
                <el-switch v-model="settings.smtp.useTls" />
                <span class="switch-label">{{ settings.smtp.useTls ? '已启用' : '未启用' }}</span>
              </div>
            </el-form-item>
          </div>

          <el-form-item label="用户名">
            <el-input
              v-model="settings.smtp.username"
              placeholder="邮箱账号或 SMTP 用户名"
            />
          </el-form-item>

          <el-form-item label="密码 / 授权码">
            <el-input
              v-model="settings.smtp.password"
              type="password"
              show-password
              placeholder="请输入 SMTP 密码或授权码"
            />
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <div class="section">
      <h2>常用 SMTP 参考</h2>
      <el-card shadow="never">
        <div class="provider-grid">
          <div
            v-for="provider in smtpProviders"
            :key="provider.name"
            class="provider-card"
          >
            <div class="provider-title-row">
              <h4>{{ provider.name }}</h4>
              <el-button
                size="small"
                text
                @click="applyProvider(provider)"
              >
                套用
              </el-button>
            </div>
            <div class="provider-detail">
              服务器：{{ provider.host }}
            </div>
            <div class="provider-detail">
              端口：{{ provider.port }}
            </div>
            <div class="provider-detail">
              加密：{{ provider.encrypt }}
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <div class="page-actions">
      <el-button @click="resetSettings">
        恢复默认
      </el-button>
      <el-button
        type="primary"
        @click="saveSettings"
      >
        保存设置
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import PageHeader from '@/components/layout/PageHeader.vue'
import { readPreferences } from '@/stores/preferences'
import { PREFERENCE_CONFIG } from '@/config/personalCenter'

const STORAGE_KEY = 'system_notification_settings'
const USER_PREFERENCES_KEY = PREFERENCE_CONFIG.storageKey

const appStore = useAppStore()

const defaultSettings = () => ({
  notifyOnComplete: true,
  notifyOnError: true,
  notifyOnEmailFailure: true,
  defaultFromEmail: '',
  defaultFromName: 'Flowly 通知中心',
  defaultReplyTo: '',
  smtp: {
    server: '',
    port: 587,
    useTls: true,
    username: '',
    password: ''
  }
})

const settings = reactive(defaultSettings())

const smtpProviders = [
  { name: 'QQ 邮箱', host: 'smtp.qq.com', port: 587, encrypt: 'TLS' },
  { name: 'Gmail', host: 'smtp.gmail.com', port: 587, encrypt: 'TLS' },
  { name: '163 邮箱', host: 'smtp.163.com', port: 465, encrypt: 'SSL/TLS' },
  { name: 'Outlook', host: 'smtp.office365.com', port: 587, encrypt: 'STARTTLS' }
]

onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      Object.assign(settings, {
        ...settings,
        ...parsed,
        smtp: {
          ...settings.smtp,
          ...(parsed.smtp || {})
        }
      })
    } catch {
      // ignore malformed local data
    }
  }
})

function applyProvider(provider) {
  settings.smtp.server = provider.host
  settings.smtp.port = provider.port
  settings.smtp.useTls = true
}

function saveSettings() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    localStorage.setItem(USER_PREFERENCES_KEY, JSON.stringify({
      ...readPreferences(),
      notifyOnComplete: settings.notifyOnComplete,
      notifyOnError: settings.notifyOnError
    }))
    appStore.success('通知与邮件设置已保存')
  } catch {
    appStore.error(PREFERENCE_CONFIG.error)
  }
}

function resetSettings() {
  Object.assign(settings, defaultSettings())
  saveSettings()
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.notifications-settings-page {
  display: flex;
  flex-direction: column;
  gap: $spacing-6;
}

.section {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.section h2 {
  margin: 0;
  font-size: $font-size-lg;
  color: var(--text-primary);
}

.setting-list {
  display: flex;
  flex-direction: column;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-4 0;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  &:first-child {
    padding-top: 0;
  }
}

.setting-info h4,
.provider-title-row h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: $font-size-base;
}

.setting-info p,
.provider-detail,
.field-hint,
.switch-label {
  color: var(--text-secondary);
  font-size: $font-size-sm;
  line-height: 1.5;
}

.setting-info p,
.field-hint {
  margin: $spacing-1 0 0;
}

.mail-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.smtp-intro {
  margin-bottom: $spacing-4;
}

.grid-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: $spacing-4;
}

.switch-row {
  display: inline-flex;
  align-items: center;
  gap: $spacing-3;
  min-height: 32px;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: $spacing-4;
}

.provider-card {
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-4;
  background: var(--bg-tertiary);
}

.provider-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-3;
  margin-bottom: $spacing-2;
}

.page-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-3;
}

@media (max-width: 768px) {
  .grid-row {
    grid-template-columns: 1fr;
  }

  .setting-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-actions {
    flex-direction: column;

    .el-button {
      width: 100%;
    }
  }
}
</style>
