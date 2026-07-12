<template>
  <div class="training-site-wizard">
    <el-steps :active="step" finish-status="success" align-center class="wizard-steps">
      <el-step title="场景" />
      <el-step title="品牌" />
      <el-step title="合规" />
      <el-step title="输出" />
    </el-steps>

    <div class="wizard-body">
      <!-- Step 1 -->
      <div v-show="step === 0" class="step-panel">
        <el-alert
          v-if="!hasProfile"
          type="info"
          :closable="false"
          show-icon
          title="未检测到上游 Profiler，可手动填写场景信息"
          class="mb-3"
        />
        <el-form label-position="top" size="small">
          <el-form-item label="领域">
            <el-input v-model="local.domain" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="应用场景" required>
            <el-input v-model="local.scenario" type="textarea" :rows="2" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="UI 风格">
            <el-select v-model="local.uiTone" @change="emitWizard">
              <el-option label="工业警示" value="industrial_warning" />
              <el-option label="告警红" value="alert_red" />
              <el-option label="质检蓝" value="quality_inspect" />
              <el-option label="友好" value="friendly" />
              <el-option label="检索图库" value="search_gallery" />
              <el-option label="中性" value="neutral" />
            </el-select>
          </el-form-item>
          <div v-if="copyHints.length" class="hint-list">
            <p class="hint-title">文案建议</p>
            <ul>
              <li v-for="(h, i) in copyHints" :key="i">{{ h }}</li>
            </ul>
          </div>
          <div v-if="riskNotes.length" class="risk-list">
            <p class="hint-title">风险提示</p>
            <ul>
              <li v-for="(r, i) in riskNotes" :key="i">{{ r }}</li>
            </ul>
          </div>
        </el-form>
      </div>

      <!-- Step 2 -->
      <div v-show="step === 1" class="step-panel">
        <el-form label-position="top" size="small">
          <el-form-item label="站点名称" required>
            <el-input v-model="local.siteName" placeholder="如：安全帽识别系统" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="Logo URL">
            <el-input v-model="local.logoUrl" placeholder="https://..." @change="emitWizard" />
          </el-form-item>
          <el-form-item label="主色">
            <el-color-picker v-model="local.primaryColor" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="联系邮箱">
            <el-input v-model="local.contactEmail" placeholder="support@example.com" @change="emitWizard" />
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 3 -->
      <div v-show="step === 2" class="step-panel">
        <el-form label-position="top" size="small">
          <el-form-item label="使用场景描述" required>
            <el-input v-model="local.usageDescription" type="textarea" :rows="3" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="免责声明">
            <el-input v-model="local.disclaimer" type="textarea" :rows="2" placeholder="本系统仅供参考，不构成安全合规承诺…" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="隐私说明">
            <el-input v-model="local.privacy" type="textarea" :rows="2" @change="emitWizard" />
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 4 -->
      <div v-show="step === 3" class="step-panel">
        <el-form label-position="top" size="small">
          <el-form-item label="数据库引擎">
            <el-select v-model="local.dbEngine" @change="emitWizard">
              <el-option label="SQLite（默认）" value="sqlite" />
              <el-option label="MySQL（高级）" value="mysql" />
            </el-select>
          </el-form-item>
          <template v-if="local.dbEngine === 'mysql'">
            <el-form-item label="MySQL Host">
              <el-input v-model="local.mysqlHost" placeholder="127.0.0.1" @change="emitWizard" />
            </el-form-item>
            <el-form-item label="MySQL Port">
              <el-input-number v-model="local.mysqlPort" :min="1" :max="65535" @change="emitWizard" />
            </el-form-item>
            <el-form-item label="MySQL User">
              <el-input v-model="local.mysqlUser" @change="emitWizard" />
            </el-form-item>
            <el-form-item label="MySQL Database">
              <el-input v-model="local.mysqlDatabase" @change="emitWizard" />
            </el-form-item>
            <p class="field-hint">MySQL 密码通过 Desktop 运行时环境变量 MYSQL_PASSWORD 注入，不会写入工作流配置。</p>
          </template>
          <el-form-item label="输出目录">
            <el-input v-model="local.outputDir" placeholder="留空则使用 {训练目录}/generated_site" @change="emitWizard">
              <template v-if="isDesktop" #append>
                <el-button @click="pickOutputDir">
                  <FolderOpen class="btn-icon-inline" />
                  选择本地文件夹
                </el-button>
              </template>
            </el-input>
            <p v-if="isDesktop" class="field-hint">
              网站代码将直接生成到你选择的本地文件夹，不会写入应用安装目录
            </p>
            <p v-else class="field-hint hint-warning">
              浏览器模式无法调用系统文件夹选择器，请在 Flowly Desktop 中运行以生成到本地目录
            </p>
          </el-form-item>
          <el-form-item label="后端端口">
            <el-input-number v-model="local.port" :min="1024" :max="65535" @change="emitWizard" />
          </el-form-item>
          <el-form-item label="QA Profile">
            <el-select v-model="local.qaProfile" @change="emitWizard">
              <el-option label="默认（严格）" value="default" />
              <el-option label="研究" value="research" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型路径">
            <el-input v-model="local.modelPath" @change="emitWizard">
              <template #append>
                <el-button @click="$emit('pick-training')">从训练节点</el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="类别标签">
            <el-input v-model="local.labels" type="textarea" :rows="2" @change="emitWizard" />
          </el-form-item>
          <div v-if="isClipRetrieval" class="clip-wizard-block">
            <el-alert type="info" :closable="false" show-icon title="CLIP 检索站专用配置" class="mb-3" />
            <el-form-item label="检索索引目录">
              <el-input
                v-model="local.indexDir"
                placeholder="clip_retrieval 节点输出的 index_dir"
                @change="emitWizard"
              />
            </el-form-item>
            <el-form-item label="示例搜索词（逗号分隔）">
              <el-input
                v-model="local.exampleQueries"
                type="textarea"
                :rows="2"
                placeholder="一只橘猫, 工业现场, 商品展示"
                @change="onClipQueriesChange"
              />
              <p class="field-hint">将显示在检索站 Tab1 空态与占位符中</p>
            </el-form-item>
            <el-form-item label="默认 Top-K">
              <el-input-number v-model="local.topK" :min="1" :max="48" @change="emitWizard" />
            </el-form-item>
          </div>
          <el-form-item label="网站类型">
            <el-select v-model="local.websiteType" @change="emitWizard">
              <el-option label="目标检测" value="detection" />
              <el-option label="图像分类" value="classification" />
              <el-option label="CLIP 图文检索" value="clip_retrieval" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="wizard-footer">
      <el-button :disabled="step === 0" @click="prev">上一步</el-button>
      <el-button v-if="step < 3" type="primary" :disabled="!canNext" @click="next">下一步</el-button>
      <el-button v-else type="primary" :disabled="!canFinish" @click="finish">完成向导</el-button>
    </div>
    <p v-if="validationError" class="validation-error">{{ validationError }}</p>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { FolderOpen } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useDesktopRuntime } from '@/composables/useDesktopRuntime'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  profile: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change', 'pick-training', 'finished'])

const { isDesktop, selectDirectory } = useDesktopRuntime()

async function pickOutputDir() {
  const dir = await selectDirectory({ title: '选择网站生成的本地文件夹' })
  if (dir) {
    local.outputDir = dir
    emitWizard()
  } else if (dir === null) {
    // user cancelled the dialog; no-op
  } else {
    ElMessage.warning('无法打开系统文件夹选择器')
  }
}

const step = computed({
  get: () => props.modelValue.wizardStep ?? 0,
  set: (v) => emitWizard({ wizardStep: v }),
})

const local = reactive({
  domain: '',
  scenario: '',
  uiTone: 'neutral',
  siteName: '',
  logoUrl: '',
  primaryColor: '#f59e0b',
  contactEmail: '',
  usageDescription: '',
  disclaimer: '',
  privacy: '',
  outputDir: '',
  port: 5000,
  qaProfile: 'default',
  modelPath: '',
  labels: '',
  websiteType: 'detection',
  indexDir: '',
  exampleQueries: '',
  topK: 12,
  dbEngine: 'sqlite',
  mysqlHost: '127.0.0.1',
  mysqlPort: 3306,
  mysqlUser: 'root',
  mysqlDatabase: 'flowly_site',
})

const isClipRetrieval = computed(() => local.websiteType === 'clip_retrieval')

const hasProfile = computed(() => Boolean(props.profile?.scenario || props.profile?.domain))
const copyHints = computed(() => props.profile?.copy_hints || [])
const riskNotes = computed(() => props.profile?.risk_notes || [])

function syncFromProps() {
  const w = props.modelValue || {}
  const p = props.profile || {}
  local.domain = w.domain ?? p.domain ?? local.domain
  local.scenario = w.scenario ?? p.scenario ?? local.scenario
  local.uiTone = w.uiTone ?? p.ui_tone ?? local.uiTone
  local.siteName = w.siteName ?? local.siteName
  local.logoUrl = w.logoUrl ?? local.logoUrl
  local.primaryColor = w.primaryColor ?? local.primaryColor
  local.contactEmail = w.contactEmail ?? local.contactEmail
  local.usageDescription = w.usageDescription ?? p.scenario ?? local.usageDescription
  local.disclaimer = w.disclaimer ?? local.disclaimer
  local.privacy = w.privacy ?? local.privacy
  local.outputDir = w.outputDir ?? local.outputDir
  local.port = w.port ?? local.port
  local.qaProfile = w.qaProfile ?? local.qaProfile
  local.modelPath = w.modelPath ?? local.modelPath
  local.labels = w.labels ?? local.labels
  local.websiteType = w.websiteType ?? p.recommended_template ?? local.websiteType
  local.indexDir = w.indexDir ?? w.index_dir ?? local.indexDir
  local.exampleQueries = w.exampleQueries ?? w.example_queries ?? local.exampleQueries
  local.topK = w.topK ?? w.top_k ?? local.topK
  local.dbEngine = w.dbEngine ?? w.db_engine ?? local.dbEngine
  local.mysqlHost = w.mysqlHost ?? w.mysql_host ?? local.mysqlHost
  local.mysqlPort = w.mysqlPort ?? w.mysql_port ?? local.mysqlPort
  local.mysqlUser = w.mysqlUser ?? w.mysql_user ?? local.mysqlUser
  local.mysqlDatabase = w.mysqlDatabase ?? w.mysql_database ?? local.mysqlDatabase
}

watch(() => local.websiteType, (t) => {
  if (t === 'clip_retrieval' && local.uiTone === 'neutral') {
    local.uiTone = 'search_gallery'
    emitWizard()
  }
})

watch(() => [props.modelValue, props.profile], syncFromProps, { immediate: true, deep: true })

function buildWizard(extra = {}) {
  return {
    domain: local.domain,
    scenario: local.scenario,
    uiTone: local.uiTone,
    siteName: local.siteName,
    logoUrl: local.logoUrl,
    primaryColor: local.primaryColor,
    contactEmail: local.contactEmail,
    usageDescription: local.usageDescription,
    disclaimer: local.disclaimer,
    privacy: local.privacy,
    outputDir: local.outputDir,
    port: local.port,
    qaProfile: local.qaProfile,
    modelPath: local.modelPath,
    labels: local.labels,
    websiteType: local.websiteType,
    indexDir: local.indexDir,
    exampleQueries: local.exampleQueries,
    topK: local.topK,
    dbEngine: local.dbEngine,
    mysqlHost: local.mysqlHost,
    mysqlPort: local.mysqlPort,
    mysqlUser: local.mysqlUser,
    mysqlDatabase: local.mysqlDatabase,
    wizardStep: step.value,
    wizardCompleted: extra.wizardCompleted ?? props.modelValue.wizardCompleted ?? false,
    ...extra,
  }
}

function onClipQueriesChange() {
  if (isClipRetrieval.value && !local.scenario.trim() && local.exampleQueries.trim()) {
    local.scenario = `图文检索演示：支持「${local.exampleQueries.split(/[,，]/)[0].trim()}」等语义搜索`
  }
  emitWizard()
}

function emitWizard(extra = {}) {
  const payload = buildWizard(extra)
  emit('update:modelValue', payload)
  emit('change', payload)
}

const validationError = computed(() => {
  if (step.value === 0 && !local.scenario.trim()) return '请填写应用场景'
  if (step.value === 1 && !local.siteName.trim()) return '请填写站点名称'
  if (step.value === 2 && !local.usageDescription.trim()) return '请填写使用场景描述'
  if (step.value === 3) {
    if (isClipRetrieval.value && !local.indexDir.trim()) return 'CLIP 检索站请填写索引目录'
    if (!local.labels.trim() && !(props.profile?.class_names?.length)) {
      return '请填写类别标签，或确保上游训练/Profiler 已输出 class_names'
    }
  }
  return ''
})

const canNext = computed(() => !validationError.value)
const canFinish = computed(() => {
  if (!local.siteName.trim() || !local.usageDescription.trim() || !local.scenario.trim()) return false
  if (isClipRetrieval.value && !local.indexDir.trim()) return false
  if (!local.labels.trim() && !(props.profile?.class_names?.length)) return false
  return true
})

function prev() {
  if (step.value > 0) emitWizard({ wizardStep: step.value - 1 })
}

function next() {
  if (!canNext.value) return
  emitWizard({ wizardStep: step.value + 1 })
}

function finish() {
  if (!canFinish.value) return
  emitWizard({ wizardStep: 3, wizardCompleted: true })
  emit('finished', buildWizard({ wizardCompleted: true }))
}
</script>

<style scoped lang="scss">
.training-site-wizard {
  .wizard-steps { margin-bottom: 16px; }
  .step-panel { min-height: 200px; }
  .wizard-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border-primary, #2e2e42);
  }
  .hint-list, .risk-list {
    margin-top: 8px;
    font-size: 12px;
    color: var(--text-secondary, #a1a1aa);
    ul { margin: 4px 0 0; padding-left: 18px; }
  }
  .hint-title { font-weight: 600; margin: 0; }
  .validation-error { color: #ef4444; font-size: 12px; margin-top: 8px; }
  .mb-3 { margin-bottom: 12px; }
  .field-hint { margin: 4px 0 0; font-size: 11px; color: var(--text-secondary, #a1a1aa); }
  .field-hint.hint-warning { color: #f59e0b; }
  .btn-icon-inline { width: 14px; height: 14px; margin-right: 4px; vertical-align: -2px; }
  .clip-wizard-block { margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-primary, #2e2e42); }
}
</style>
