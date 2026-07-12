<template>
  <div class="branding-settings-page">
    <PageHeader
      compact
      title="品牌定制"
      subtitle="自定义您的平台外观和品牌标识"
    />

    <el-tabs
      v-model="activeTab"
      class="branding-tabs"
    >
      <!-- Brand Identity -->
      <el-tab-pane
        label="品牌标识"
        name="identity"
      >
        <el-card shadow="never">
          <template #header>
            <span>公司信息</span>
          </template>
          <el-form
            :model="branding"
            label-width="120px"
          >
            <el-form-item label="公司名称">
              <el-input
                v-model="branding.company_name"
                placeholder="输入公司名称"
              />
            </el-form-item>
            <el-form-item label="公司Logo">
              <div class="logo-upload">
                <el-image
                  v-if="branding.company_logo"
                  :src="branding.company_logo"
                  class="logo-preview"
                  fit="contain"
                />
                <el-upload
                  action="#"
                  :show-file-list="false"
                  :before-upload="handleLogoUpload"
                >
                  <el-button>
                    <Upload class="btn-icon" />
                    {{ branding.company_logo ? '更换Logo' : '上传Logo' }}
                  </el-button>
                </el-upload>
              </div>
            </el-form-item>
            <el-form-item label="网站图标">
              <el-input
                v-model="branding.company_favicon"
                placeholder="输入网站图标URL"
              >
                <template #append>
                  <el-button @click="previewFavicon">
                    预览
                  </el-button>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="公司网站">
              <el-input
                v-model="branding.company_website"
                placeholder="https://example.com"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Colors -->
      <el-tab-pane
        label="主题颜色"
        name="colors"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <span>主要颜色</span>
              </template>
              <el-form label-width="100px">
                <el-form-item label="主题色">
                  <div class="color-input-group">
                    <el-color-picker v-model="branding.primary_color" />
                    <el-input
                      v-model="branding.primary_color"
                      class="color-text"
                    />
                  </div>
                </el-form-item>
                <el-form-item label="强调色">
                  <div class="color-input-group">
                    <el-color-picker v-model="branding.accent_color" />
                    <el-input
                      v-model="branding.accent_color"
                      class="color-text"
                    />
                  </div>
                </el-form-item>
                <el-form-item label="成功色">
                  <div class="color-input-group">
                    <el-color-picker v-model="branding.success_color" />
                    <el-input
                      v-model="branding.success_color"
                      class="color-text"
                    />
                  </div>
                </el-form-item>
                <el-form-item label="警告色">
                  <div class="color-input-group">
                    <el-color-picker v-model="branding.warning_color" />
                    <el-input
                      v-model="branding.warning_color"
                      class="color-text"
                    />
                  </div>
                </el-form-item>
                <el-form-item label="危险色">
                  <div class="color-input-group">
                    <el-color-picker v-model="branding.danger_color" />
                    <el-input
                      v-model="branding.danger_color"
                      class="color-text"
                    />
                  </div>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <span>主题预设</span>
              </template>
              <div class="theme-presets">
                <div
                  v-for="preset in themePresets"
                  :key="preset.id"
                  :class="['preset-card', { active: selectedPreset === preset.id }]"
                  @click="applyPreset(preset)"
                >
                  <div
                    class="preset-preview"
                    :style="{
                      background: preset.bg_color,
                      color: preset.text_color
                    }"
                  >
                    <div
                      class="preset-accent"
                      :style="{ background: preset.primary_color }"
                    />
                    <span>标题</span>
                    <span class="preset-small">正文</span>
                  </div>
                  <div class="preset-name">
                    {{ preset.name }}
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- Background & Text -->
        <el-card
          shadow="never"
          style="margin-top: 20px;"
        >
          <template #header>
            <span>背景与文字</span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="背景色">
              <div class="color-input-group">
                <el-color-picker v-model="branding.bg_color" />
                <el-input
                  v-model="branding.bg_color"
                  class="color-text"
                />
              </div>
            </el-form-item>
            <el-form-item label="次要背景">
              <div class="color-input-group">
                <el-color-picker v-model="branding.bg_color_secondary" />
                <el-input
                  v-model="branding.bg_color_secondary"
                  class="color-text"
                />
              </div>
            </el-form-item>
            <el-form-item label="主要文字">
              <div class="color-input-group">
                <el-color-picker v-model="branding.text_color_primary" />
                <el-input
                  v-model="branding.text_color_primary"
                  class="color-text"
                />
              </div>
            </el-form-item>
            <el-form-item label="次要文字">
              <div class="color-input-group">
                <el-color-picker v-model="branding.text_color_secondary" />
                <el-input
                  v-model="branding.text_color_secondary"
                  class="color-text"
                />
              </div>
            </el-form-item>
            <el-form-item label="边框色">
              <div class="color-input-group">
                <el-color-picker v-model="branding.border_color" />
                <el-input
                  v-model="branding.border_color"
                  class="color-text"
                />
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Login Page -->
      <el-tab-pane
        label="登录页面"
        name="login"
      >
        <el-card shadow="never">
          <template #header>
            <span>登录页设置</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="背景图片">
              <el-input
                v-model="branding.login_background"
                placeholder="输入背景图片URL"
              >
                <template #append>
                  <el-button @click="previewBackground">
                    预览
                  </el-button>
                </template>
              </el-input>
              <div
                v-if="branding.login_background"
                class="background-preview"
              >
                <img
                  :src="branding.login_background"
                  alt="背景预览"
                >
              </div>
            </el-form-item>
            <el-form-item label="显示Logo">
              <el-switch v-model="branding.login_show_logo" />
            </el-form-item>
            <el-form-item label="欢迎消息">
              <el-input
                v-model="branding.login_message"
                type="textarea"
                :rows="3"
                placeholder="输入显示在登录框下方的自定义消息"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Custom Code -->
      <el-tab-pane
        label="自定义代码"
        name="code"
      >
        <el-card shadow="never">
          <template #header>
            <span>自定义CSS/JS</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="自定义CSS">
              <el-input
                v-model="branding.custom_css"
                type="textarea"
                :rows="10"
                placeholder="输入自定义CSS样式"
                class="code-textarea"
              />
            </el-form-item>
            <el-form-item label="自定义JavaScript">
              <el-input
                v-model="branding.custom_js"
                type="textarea"
                :rows="10"
                placeholder="输入自定义JavaScript代码"
                class="code-textarea"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Email Templates -->
      <el-tab-pane
        label="邮件模板"
        name="email"
      >
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>邮件模板</span>
              <el-button
                size="small"
                type="primary"
                @click="showEmailTemplateDialog = true"
              >
                <Plus class="btn-icon" />
                新建模板
              </el-button>
            </div>
          </template>
          <el-table
            :data="emailTemplates"
            stripe
          >
            <el-table-column
              prop="template_type"
              label="类型"
              width="150"
            >
              <template #default="{ row }">
                {{ getTemplateTypeLabel(row.template_type) }}
              </template>
            </el-table-column>
            <el-table-column
              prop="name"
              label="名称"
              min-width="150"
            />
            <el-table-column
              prop="subject"
              label="主题"
              min-width="200"
            />
            <el-table-column
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="row.is_active ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="150"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  size="small"
                  text
                  @click="editEmailTemplate(row)"
                >
                  编辑
                </el-button>
                <el-button
                  size="small"
                  text
                  @click="resetToDefault(row)"
                >
                  重置
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Custom Domain -->
      <el-tab-pane
        label="自定义域名"
        name="domain"
      >
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>自定义域名</span>
              <el-button
                size="small"
                type="primary"
                @click="showDomainDialog = true"
              >
                <Plus class="btn-icon" />
                添加域名
              </el-button>
            </div>
          </template>
          <div
            v-if="customDomains.length === 0"
            class="empty-domains"
          >
            <Globe class="empty-icon" />
            <h4>暂无自定义域名</h4>
            <p>添加自定义域名，让您的用户通过您自己的域名访问平台</p>
          </div>
          <el-table
            v-else
            :data="customDomains"
            stripe
          >
            <el-table-column
              prop="domain"
              label="域名"
              min-width="200"
            />
            <el-table-column
              label="状态"
              width="120"
            >
              <template #default="{ row }">
                <el-tag
                  :type="getDomainStatusType(row.status)"
                  size="small"
                >
                  {{ getDomainStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="cname_target"
              label="CNAME目标"
              min-width="200"
            />
            <el-table-column
              label="SSL"
              width="80"
            >
              <template #default="{ row }">
                <el-tag
                  :type="row.ssl_enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.ssl_enabled ? '已启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="200"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'pending'"
                  size="small"
                  text
                  type="primary"
                  @click="verifyDomain(row)"
                >
                  验证
                </el-button>
                <el-button
                  size="small"
                  text
                  @click="editDomain(row)"
                >
                  设置
                </el-button>
                <el-button
                  size="small"
                  text
                  type="danger"
                  @click="deleteDomain(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- DNS Instructions -->
        <el-card
          shadow="never"
          style="margin-top: 20px;"
        >
          <template #header>
            <span>DNS配置说明</span>
          </template>
          <div class="dns-instructions">
            <p>要添加自定义域名，请按以下步骤配置DNS记录：</p>
            <ol>
              <li>在您的域名注册商处，添加一条CNAME记录：</li>
            </ol>
            <div class="dns-code">
              <pre>主机记录: @ (或您想要的子域名)
记录类型: CNAME
记录值: {TENANT_SUBDOMAIN}.{{ MAIN_DOMAIN }}
TTL: 3600</pre>
            </div>
            <p class="dns-note">
              <strong>提示：</strong>将 <code>{{ MAIN_DOMAIN }}</code> 替换为您实际的域名。
            </p>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- Save Actions -->
    <div class="page-actions">
      <el-button @click="previewBranding">
        <Eye class="btn-icon" />
        预览
      </el-button>
      <el-button @click="resetChanges">
        重置
      </el-button>
      <el-button
        type="primary"
        :loading="saving"
        @click="saveBranding"
      >
        <Save class="btn-icon" />
        保存更改
      </el-button>
    </div>

    <!-- Email Template Dialog -->
    <el-dialog
      v-model="showEmailTemplateDialog"
      title="邮件模板"
      width="700px"
    >
      <el-form
        :model="emailTemplateForm"
        label-width="100px"
      >
        <el-form-item label="模板类型">
          <el-select v-model="emailTemplateForm.template_type">
            <el-option
              v-for="(label, value) in TEMPLATE_TYPE_LABELS"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模板名称">
          <el-input v-model="emailTemplateForm.name" />
        </el-form-item>
        <el-form-item label="邮件主题">
          <el-input v-model="emailTemplateForm.subject" />
        </el-form-item>
        <el-form-item label="模板内容">
          <el-input
            v-model="emailTemplateForm.body_html"
            type="textarea"
            :rows="10"
            placeholder="支持HTML，可使用变量: {username}, {email}, {app_name}"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEmailTemplateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="saveEmailTemplate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Custom Domain Dialog -->
    <el-dialog
      v-model="showDomainDialog"
      title="添加自定义域名"
      width="500px"
    >
      <el-form
        :model="domainForm"
        label-width="100px"
      >
        <el-form-item label="域名">
          <el-input
            v-model="domainForm.domain"
            placeholder="example.com"
          />
        </el-form-item>
        <el-form-item label="子域名">
          <el-input
            v-model="domainForm.subdomain"
            placeholder="app (可选)"
          />
        </el-form-item>
        <el-form-item label="启用SSL">
          <el-switch v-model="domainForm.ssl_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDomainDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="addDomain"
        >
          添加
        </el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog
      v-model="showPreview"
      title="品牌预览"
      width="800px"
    >
      <div
        class="branding-preview"
        :style="previewStyles"
      >
        <div class="preview-header">
          <img
            v-if="branding.company_logo"
            :src="branding.company_logo"
            class="preview-logo"
          >
          <span class="preview-company">{{ branding.company_name }}</span>
        </div>
        <div class="preview-content">
          <h2>欢迎使用 {{ branding.company_name || 'Flowly' }}</h2>
          <p>这是品牌定制预览，展示您设置的颜色和样式。</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Upload, Plus, Eye, Save, Globe
} from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { useBrandingStore } from '@/stores/branding'
import { APP_CONFIG } from '@/config'
import PageHeader from '@/components/layout/PageHeader.vue'

const appStore = useAppStore()

// Lookup maps
const TEMPLATE_TYPE_LABELS = Object.freeze({
  welcome: '欢迎邮件', password_reset: '密码重置', email_verification: '邮箱验证',
  workflow_notification: '工作流通知', execution_complete: '执行完成',
  execution_failed: '执行失败', subscription_alert: '订阅提醒',
  usage_alert: '用量提醒', team_invitation: '团队邀请'
})
const DOMAIN_STATUS_TYPES = Object.freeze({
  pending: 'warning', verified: 'success', active: 'success', failed: 'danger'
})
const DOMAIN_STATUS_LABELS = Object.freeze({
  pending: '待验证', verified: '已验证', active: '已激活', failed: '失败'
})

const DEFAULT_BRANDING = {
  company_name: 'My Company',
  company_logo: '',
  company_favicon: '',
  company_website: '',
  primary_color: '#3b82f6',
  accent_color: '#3b82f6',
  success_color: '#10b981',
  warning_color: '#f59e0b',
  danger_color: '#ef4444',
  bg_color: '#ffffff',
  bg_color_secondary: '#f3f4f6',
  text_color_primary: '#1f2937',
  text_color_secondary: '#6b7280',
  border_color: '#e5e7eb',
  login_background: '',
  login_show_logo: true,
  login_message: '',
  custom_css: '',
  custom_js: ''
}

const brandingStore = useBrandingStore()

// 域名配置常量
const MAIN_DOMAIN = computed(() => APP_CONFIG.domains.tenantSubdomain || 'flowly.com')

const activeTab = ref('identity')
const saving = ref(false)
const selectedPreset = ref(null)
const showEmailTemplateDialog = ref(false)
const showDomainDialog = ref(false)
const showPreview = ref(false)

const branding = computed(() => brandingStore.currentBranding || DEFAULT_BRANDING)

const emailTemplateForm = ref({
  template_type: 'welcome',
  name: '',
  subject: '',
  body_html: ''
})

const domainForm = ref({
  domain: '',
  subdomain: '',
  ssl_enabled: true
})

const emailTemplates = computed(() => brandingStore.emailTemplates)

const customDomains = computed(() => brandingStore.customDomains)

const themePresets = computed(() => brandingStore.presets)

const previewStyles = computed(() => ({
  '--primary-color': branding.value.primary_color,
  '--accent-color': branding.value.accent_color,
  '--bg-color': branding.value.bg_color,
  '--text-color': branding.value.text_color_primary,
  '--border-color': branding.value.border_color
}))

const handleLogoUpload = (file) => {
  const url = URL.createObjectURL(file.raw)
  branding.value.company_logo = url
  return false
}

const previewFavicon = () => {
  appStore.info(`预览图标: ${branding.value.company_favicon}`)
}

const previewBackground = () => {
  if (branding.value.login_background) {
    appStore.info(`背景预览: ${branding.value.login_background}`)
  }
}

const getTemplateTypeLabel = (type) => TEMPLATE_TYPE_LABELS[type] ?? type
const getDomainStatusType = (status) => DOMAIN_STATUS_TYPES[status] ?? 'info'
const getDomainStatusLabel = (status) => DOMAIN_STATUS_LABELS[status] ?? status

const editEmailTemplate = (template) => {
  emailTemplateForm.value = { ...template }
  showEmailTemplateDialog.value = true
}

const saveEmailTemplate = async () => {
  try {
    if (emailTemplateForm.value.id) {
      await brandingStore.updateEmailTemplate(emailTemplateForm.value.id, emailTemplateForm.value)
    } else {
      await brandingStore.createEmailTemplate(emailTemplateForm.value)
    }
    appStore.success('邮件模板已保存')
    showEmailTemplateDialog.value = false
    await brandingStore.fetchEmailTemplates()
  } catch (error) {
    console.error('保存邮件模板失败:', error)
    appStore.error('保存失败')
  }
}

const resetToDefault = async (template) => {
  try {
    await brandingStore.resetEmailTemplate(template.id)
    appStore.success('已重置为默认模板')
    await brandingStore.fetchEmailTemplates()
  } catch (error) {
    console.error('重置邮件模板失败:', error)
    appStore.error('重置失败')
  }
}

const verifyDomain = async (domain) => {
  try {
    await brandingStore.verifyDomain(domain.id)
    appStore.success('域名验证成功')
    await brandingStore.fetchCustomDomains()
  } catch (error) {
    console.error('验证域名失败:', error)
    appStore.error('验证失败')
  }
}

const editDomain = (domain) => {
  domainForm.value = { ...domain }
  showDomainDialog.value = true
}

const addDomain = async () => {
  try {
    await brandingStore.createCustomDomain(domainForm.value)
    appStore.success('域名添加成功')
    showDomainDialog.value = false
    domainForm.value = { domain: '', subdomain: '', ssl_enabled: true }
    await brandingStore.fetchCustomDomains()
  } catch (error) {
    console.error('添加域名失败:', error)
    appStore.error('添加失败')
  }
}

const deleteDomain = async (domain) => {
  try {
    await brandingStore.deleteCustomDomain(domain.id)
    appStore.success('域名已删除')
    await brandingStore.fetchCustomDomains()
  } catch (error) {
    console.error('删除域名失败:', error)
    appStore.error('删除失败')
  }
}

const previewBranding = () => {
  showPreview.value = true
}

const saveBranding = async () => {
  saving.value = true
  try {
    await brandingStore.updateBranding(branding.value)
    appStore.success('品牌设置已保存')
  } catch (error) {
    console.error('保存品牌设置失败:', error)
    appStore.error('保存失败')
  } finally {
    saving.value = false
  }
}

const applyPreset = async (preset) => {
  try {
    await brandingStore.applyPreset(preset.id)
    selectedPreset.value = preset.id
    appStore.success(`已应用预设: ${preset.name}`)
  } catch (error) {
    console.error('应用预设失败:', error)
    appStore.error('应用预设失败')
  }
}

const resetChanges = () => {
  Object.assign(branding.value, { ...DEFAULT_BRANDING })
  selectedPreset.value = null
  appStore.info('已重置所有更改')
}

onMounted(async () => {
  await Promise.all([
    brandingStore.fetchCurrentBranding(),
    brandingStore.fetchPresets(),
    brandingStore.fetchEmailTemplates(),
    brandingStore.fetchCustomDomains()
  ])
})
</script>

<style lang="scss" scoped>
.branding-settings-page {
  padding: 24px;
  max-width: 1200px;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.logo-upload {
  display: flex;
  align-items: center;
  gap: 16px;

  .logo-preview {
    width: 100px;
    height: 100px;
    border: 1px solid var(--el-border-color);
    border-radius: 8px;
  }
}

.color-input-group {
  display: flex;
  align-items: center;
  gap: 12px;

  .color-text {
    width: 120px;
  }
}

.theme-presets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;

  .preset-card {
    cursor: pointer;
    border: 2px solid transparent;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    &.active {
      border-color: var(--el-color-primary);
    }

    .preset-preview {
      height: 80px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;

      .preset-accent {
        width: 40px;
        height: 8px;
        border-radius: 4px;
      }

      span {
        font-size: 14px;
        font-weight: 600;
      }

      .preset-small {
        font-size: 11px;
        opacity: 0.7;
      }
    }

    .preset-name {
      padding: 8px;
      text-align: center;
      font-size: 13px;
      font-weight: 500;
      background: var(--el-fill-color-light);
    }
  }
}

.background-preview {
  margin-top: 12px;

  img {
    width: 300px;
    height: 150px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid var(--el-border-color);
  }
}

.code-textarea {
  :deep(textarea) {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }
}

.empty-domains {
  text-align: center;
  padding: 48px;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--el-text-color-secondary);
    opacity: 0.5;
    margin-bottom: 16px;
  }

  h4 {
    margin: 0 0 8px;
  }

  p {
    margin: 0;
    color: var(--el-text-color-secondary);
  }
}

.dns-instructions {
  p {
    margin: 0 0 12px;
  }

  ol {
    margin: 0 0 12px;
  }

  .dns-code {
    background: #1e1e2e;
    border-radius: 8px;
    padding: 16px;

    pre {
      margin: 0;
      color: #cdd6f4;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
    }
  }
}

.page-actions {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--el-border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.branding-preview {
  background: var(--bg-color, #ffffff);
  color: var(--text-color, #1f2937);
  border-radius: 12px;
  overflow: hidden;

  .preview-header {
    background: var(--primary-color, #3b82f6);
    padding: 24px;
    display: flex;
    align-items: center;
    gap: 12px;

    .preview-logo {
      height: 32px;
    }

    .preview-company {
      font-size: 18px;
      font-weight: 600;
      color: white;
    }
  }

  .preview-content {
    padding: 32px;

    h2 {
      margin: 0 0 12px;
      color: var(--primary-color, #3b82f6);
    }

    p {
      margin: 0;
      color: var(--text-color, #6b7280);
    }
  }
}
</style>
