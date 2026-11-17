<template>
  <PageShell
    width="wide"
    class="generated-site-page"
  >
    <div class="page-header">
      <div>
        <h1>{{ site?.name || '识别项目' }}</h1>
        <p
          v-if="site?.description"
          class="page-desc"
        >
          {{ site.description }}
        </p>
      </div>
      <el-tag
        v-if="site"
        :type="statusTagType"
      >
        {{ site.statusDisplay || site.status }}
      </el-tag>
    </div>

    <el-skeleton
      v-if="loading"
      :rows="6"
      animated
    />

    <el-alert
      v-else-if="error"
      type="error"
      :title="error"
      show-icon
    />

    <template v-else-if="site">
      <div class="info-grid">
        <div class="info-card">
          <span class="label">网站类型</span>
          <span class="value">{{ site.websiteTypeDisplay || site.websiteType }}</span>
        </div>
        <div class="info-card">
          <span class="label">前端</span>
          <span class="value">{{ site.frontendDisplay || site.frontendFramework }}</span>
        </div>
        <div class="info-card">
          <span class="label">后端</span>
          <span class="value">{{ site.backendDisplay || site.backendFramework }}</span>
        </div>
        <div class="info-card">
          <span class="label">推理端点</span>
          <span class="value mono">{{ site.inferenceEndpoint || '—' }}</span>
        </div>
      </div>

      <div class="action-bar">
        <el-button
          type="primary"
          :loading="deploying"
          :disabled="site.status !== 'completed'"
          @click="handleDeploy"
        >
          本地部署
        </el-button>
        <el-button
          :loading="downloading"
          :disabled="site.status !== 'completed'"
          @click="handleDownload"
        >
          下载 ZIP
        </el-button>
        <el-button
          v-if="site.inferenceEndpoint"
          @click="openEndpoint"
        >
          打开推理服务
        </el-button>
        <el-button
          v-if="site.codegraphProjectId"
          @click="openCodeGraph"
        >
          查看 CodeGraph
        </el-button>
        <el-button
          v-if="site.source?.status === 'available'"
          data-testid="site-source-workflow"
          @click="openWorkflowEditor"
        >
          {{ site.source.canEdit ? '编辑源工作流' : '查看源工作流' }}
        </el-button>
        <el-button
          v-if="site.canRebuild"
          :loading="rebuilding"
          :disabled="rebuilding"
          data-testid="site-rebuild-workflow"
          @click="rebuildWorkflow"
        >
          基于项目创建工作流副本
        </el-button>
      </div>
      <p
        v-if="site.source?.message"
        class="page-desc"
      >
        {{ site.source.message }}
      </p>
      <p
        v-if="site.canRebuild"
        class="page-desc"
      >
        {{ site.rebuildNotice }}
      </p>
      <el-alert
        v-if="rebuildError"
        :title="rebuildError"
        type="error"
        show-icon
        :closable="false"
      />

      <div
        v-if="site.outputDir"
        class="path-block"
      >
        <span class="label">输出目录</span>
        <code>{{ site.outputDir }}</code>
        <el-button
          size="small"
          text
          @click="copyText(site.outputDir)"
        >
          复制
        </el-button>
      </div>

      <div
        v-if="site.lastAgentReply?.reply"
        class="agent-section"
      >
        <h3>最近 Agent 回复</h3>
        <p class="agent-reply">
          {{ site.lastAgentReply.reply }}
        </p>
        <p
          v-if="site.lastAgentReply.files_changed?.length"
          class="agent-meta"
        >
          已修改：{{ site.lastAgentReply.files_changed.join(', ') }}
        </p>
      </div>

      <div class="rag-section">
        <h3>项目记忆（RAG）</h3>
        <template v-if="site.ragCollectionId">
          <p class="rag-status synced">
            对话已同步至知识库集合
          </p>
          <el-button
            size="small"
            @click="openRagCollection"
          >
            在知识库中查看
          </el-button>
        </template>
        <template v-else>
          <p class="rag-status missing">
            尚未创建项目记忆集合
          </p>
          <el-button
            size="small"
            type="primary"
            plain
            @click="router.push('/knowledge')"
          >
            配置向量库
          </el-button>
        </template>
      </div>

      <div
        v-if="site.generatedFiles?.length"
        class="files-section"
      >
        <h3>生成文件（{{ site.generatedFiles.length }}）</h3>
        <ul>
          <li
            v-for="file in site.generatedFiles.slice(0, 20)"
            :key="file"
          >
            {{ file }}
          </li>
        </ul>
      </div>
    </template>
  </PageShell>
</template>

<script setup>
import PageShell from '@/components/layout/PageShell.vue'
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { websiteGeneratorApi } from '@/api/websiteGenerator'

const route = useRoute()
const router = useRouter()

const site = ref(null)
const loading = ref(true)
const error = ref('')
const deploying = ref(false)
const downloading = ref(false)
const rebuilding = ref(false)
const rebuildError = ref('')
let rebuildKey = ''
let siteRevision = 0
let navigatingToCopy = false
let pollTimer = null

const statusTagType = computed(() => {
  if (!site.value) return 'info'
  if (site.value.status === 'completed') return 'success'
  if (site.value.status === 'failed') return 'danger'
  return 'warning'
})

async function fetchSite() {
  const revision = siteRevision
  const id = route.params.id
  try {
    const result = await websiteGeneratorApi.get(id)
    if (revision !== siteRevision) return
    site.value = result
    error.value = ''
    if (site.value?.status === 'generating') {
      pollTimer = window.setTimeout(fetchSite, 3000)
    }
  } catch (e) {
    if (revision !== siteRevision) return
    error.value = e?.message || '加载识别项目失败'
  } finally {
    if (revision === siteRevision) loading.value = false
  }
}

async function handleDeploy() {
  deploying.value = true
  try {
    const res = await websiteGeneratorApi.deploy(route.params.id)
    ElMessage.success(res?.message || '部署已启动')
    if (res?.endpoint) {
      window.open(res.endpoint, '_blank')
    }
  } catch (e) {
    ElMessage.error(e?.message || '部署失败')
  } finally {
    deploying.value = false
  }
}

async function handleDownload() {
  downloading.value = true
  try {
    const blob = await websiteGeneratorApi.download(route.params.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${site.value?.name || 'site'}.zip`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch (e) {
    ElMessage.error(e?.message || '下载失败')
  } finally {
    downloading.value = false
  }
}

function openEndpoint() {
  if (site.value?.inferenceEndpoint) {
    window.open(site.value.inferenceEndpoint, '_blank')
  }
}

function openCodeGraph() {
  router.push({ path: '/codegraph', query: { project: site.value.codegraphProjectId } })
}

function openRagCollection() {
  if (site.value?.ragCollectionId) {
    router.push({ path: '/knowledge', query: { collection: site.value.ragCollectionId } })
  }
}

function openWorkflowEditor() {
  const source = site.value?.source
  if (source?.status !== 'available' || !source.workflowId) return
  router.push(`/workflows/${encodeURIComponent(source.workflowId)}${source.canEdit ? '/edit' : ''}`)
}

async function rebuildWorkflow() {
  if (rebuilding.value || !site.value?.canRebuild) return
  if (!rebuildKey) rebuildKey = Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, '0')).join('')
  rebuilding.value = true
  rebuildError.value = ''
  const revision = siteRevision
  try {
    const result = await websiteGeneratorApi.rebuildWorkflow(site.value.id, rebuildKey)
    if (revision !== siteRevision) return
    if (!result?.workflowId) throw new Error('服务未返回工作流编号，请重试以确认上次创建结果。')
    navigatingToCopy = true
    await router.push(`/workflows/${encodeURIComponent(result.workflowId)}/edit`)
  } catch (failure) {
    if (revision === siteRevision) {
      const payload = failure.response?.data
      const explanation = payload?.message || payload?.detail || payload?.error
      rebuildError.value = typeof explanation === 'string' ? explanation : Array.isArray(explanation) ? explanation.join('；') : failure.response ? '副本创建失败，请检查项目资源与权限后重试。' : '副本创建结果未确认，请重试；相同请求标识可避免重复创建。'
    }
  } finally {
    if (revision === siteRevision) { rebuilding.value = false; navigatingToCopy = false }
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function beforeUnload(event) { if (rebuilding.value) { event.preventDefault(); event.returnValue = '' } }
onBeforeRouteLeave(() => !rebuilding.value || navigatingToCopy)
onBeforeRouteUpdate(() => !rebuilding.value)
watch(() => route.params.id, () => {
  siteRevision++
  if (pollTimer) clearTimeout(pollTimer)
  site.value = null
  loading.value = true
  error.value = ''
  rebuildError.value = ''
  rebuildKey = ''
  fetchSite()
}, { immediate: true })
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onUnmounted(() => {
  siteRevision++
  if (pollTimer) clearTimeout(pollTimer)
  window.removeEventListener('beforeunload', beforeUnload)
})
</script>

<style lang="scss" scoped>

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;

  h1 {
    margin: 0 0 8px;
    font-size: 24px;
  }
}

.page-desc {
  margin: 0;
  color: var(--text-secondary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.info-card {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);

  .label {
    display: block;
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .value {
    font-size: 14px;
    font-weight: 600;

    &.mono {
      font-family: monospace;
      font-size: 12px;
      word-break: break-all;
    }
  }
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}

.path-block {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  border-radius: 8px;
  background: var(--bg-secondary);
  margin-bottom: 20px;

  code {
    font-size: 12px;
    word-break: break-all;
  }
}

.files-section {
  h3 {
    margin: 0 0 10px;
    font-size: 15px;
  }

  ul {
    margin: 0;
    padding-left: 18px;
    font-size: 13px;
    color: var(--text-secondary);
  }
}

.agent-section,
.rag-section {
  margin-bottom: 20px;
  padding: 14px;
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);

  h3 {
    margin: 0 0 8px;
    font-size: 15px;
  }
}

.agent-reply {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.agent-meta {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.rag-status {
  margin: 0 0 10px;
  font-size: 13px;

  &.synced { color: #10b981; }
  &.missing { color: #f59e0b; }
}
</style>
