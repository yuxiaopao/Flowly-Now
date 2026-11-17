<template>
  <PageShell
    width="wide"
    class="delivery-workbench"
  >
    <PageHeader
      :title="WORKBENCH.title"
      :subtitle="WORKBENCH.subtitle"
    >
      <template #actions>
        <router-link to="/applications?create=1">
          <AppButton><Plus aria-hidden="true" />创建应用</AppButton>
        </router-link>
      </template>
    </PageHeader>
    <div
      v-if="overviewError"
      class="workbench-error"
      role="alert"
    >
      <AlertCircle aria-hidden="true" /><span>{{ overviewError }}</span><AppButton
        variant="secondary"
        size="small"
        :loading="loadingOverview"
        @click="loadOverview"
      >
        重新加载
      </AppButton>
    </div>
    <section
      class="delivery-pulse"
      aria-label="应用与最近七天请求概况"
      :aria-busy="loadingOverview"
    >
      <div class="pulse-label">
        <Activity aria-hidden="true" /><span>交付概况</span><small>{{ WORKBENCH.periodLabel }}</small>
      </div>
      <dl>
        <div
          v-for="metric in metrics"
          :key="metric.label"
          class="pulse-metric"
        >
          <dt>{{ metric.label }}</dt><dd :class="{ warning: metric.warning }">
            {{ loadingOverview ? '···' : metric.value }}
          </dd>
        </div>
      </dl>
    </section>
    <section
      class="delivery-path"
      aria-label="应用交付路径"
    >
      <router-link
        v-for="step in WORKBENCH.steps"
        :key="step.number"
        :to="step.path"
        class="delivery-step"
      >
        <span class="step-number">{{ step.number }}</span><span class="step-copy"><strong>{{ step.title }}</strong><span>{{ step.description }}</span></span><ArrowUpRight aria-hidden="true" />
      </router-link>
    </section>
    <div class="workbench-columns">
      <section
        class="workbench-section"
        aria-labelledby="recent-applications-title"
      >
        <div class="section-heading">
          <div>
            <span class="section-kicker">BUILD → SHIP</span><h2 id="recent-applications-title">
              继续交付
            </h2>
          </div><router-link
            to="/applications"
            class="text-link"
          >
            全部应用<ArrowRight aria-hidden="true" />
          </router-link>
        </div>
        <div
          v-if="loadingOverview"
          class="resource-skeleton"
          aria-label="正在加载应用"
        >
          <span
            v-for="n in 3"
            :key="n"
          />
        </div>
        <div
          v-else-if="!recentApplications.length"
          class="application-empty"
        >
          <Boxes aria-hidden="true" /><h3>{{ overviewError ? '应用数据暂不可用' : '把第一个原型变成可调用的应用' }}</h3><p>{{ overviewError ? '重新加载后可继续查看已有应用。' : '选择知识库或工作流，在工作区完成测试、发布和 API 接入。' }}</p><router-link
            v-if="!overviewError"
            to="/applications?create=1"
            class="text-link"
          >
            创建第一个应用<ArrowRight aria-hidden="true" />
          </router-link>
        </div>
        <div v-else>
          <router-link
            v-for="application in recentApplications"
            :key="application.id"
            :to="`/applications/${application.id}`"
            class="application-row"
          >
            <span class="application-glyph"><Database
              v-if="application.kind === 'knowledge'"
              aria-hidden="true"
            /><GitBranch
              v-else
              aria-hidden="true"
            /></span><span class="resource-copy"><strong>{{ application.name }}</strong><small>{{ KIND_LABELS[application.kind] || application.kind }} · {{ formatDate(application.updatedAt) }}</small></span><span
              class="release-label"
              :class="{ live: application.activeRelease }"
            ><span aria-hidden="true" />{{ application.activeRelease ? `已发布 v${application.activeRelease.version}` : '草稿' }}</span><ChevronRight
              class="row-arrow"
              aria-hidden="true"
            />
          </router-link>
        </div>
      </section>
      <section
        class="workbench-section"
        aria-labelledby="recent-requests-title"
      >
        <div class="section-heading">
          <div>
            <span class="section-kicker">OBSERVE → ITERATE</span><h2 id="recent-requests-title">
              最近请求
            </h2>
          </div><span class="section-note">含测试与回归评测</span>
        </div>
        <div
          v-if="loadingOverview"
          class="resource-skeleton"
          aria-label="正在加载请求"
        >
          <span
            v-for="n in 3"
            :key="n"
          />
        </div>
        <div
          v-else-if="!recentRequests.length"
          class="request-empty"
        >
          <Radio aria-hidden="true" /><p>{{ overviewError ? '请求记录暂不可用' : '应用测试或接入调用后，请求会记录在这里。' }}</p>
        </div>
        <div v-else>
          <router-link
            v-for="item in recentRequests"
            :key="item.id"
            :to="requestPath(item)"
            class="request-row"
          >
            <span
              class="request-status"
              :class="`request-status--${item.status}`"
            ><CheckCircle2
              v-if="item.status === 'completed'"
              aria-hidden="true"
            /><AlertCircle
              v-else-if="['failed', 'rejected'].includes(item.status)"
              aria-hidden="true"
            /><Clock3
              v-else
              aria-hidden="true"
            /></span><span class="resource-copy"><strong>{{ item.applicationName || applicationName(item.applicationId) }}</strong><small>{{ item.errorMessage || `${APPLICATIONS.requestModes[item.mode] || item.mode} · ${REQUEST_LABELS[item.status] || item.status}` }}</small></span><span class="request-timing"><span>{{ item.latencyMs == null ? '进行中' : `${item.latencyMs} ms` }}</span><small>{{ formatDate(item.createdAt) }}</small></span>
          </router-link>
        </div>
        <p
          v-if="overview && !overview.usageComplete"
          class="usage-note"
        >
          部分模型未提供可归因用量，费用以实际返回为准。
        </p>
      </section>
    </div>
    <div class="workbench-columns workbench-columns--resources">
      <section
        class="workbench-section"
        aria-labelledby="workflow-resources-title"
      >
        <div class="section-heading">
          <h2 id="workflow-resources-title">
            可复用工作流
          </h2><router-link
            to="/workflows"
            class="text-link"
          >
            管理工作流<ArrowRight aria-hidden="true" />
          </router-link>
        </div>
        <p
          v-if="workflowError"
          class="inline-error"
          role="status"
        >
          {{ workflowError }}<button
            type="button"
            class="text-link"
            @click="loadWorkflows"
          >
            重试
          </button>
        </p>
        <div
          v-else-if="loadingWorkflows"
          class="resource-skeleton"
          aria-label="正在加载工作流"
        >
          <span
            v-for="n in 2"
            :key="n"
          />
        </div>
        <div
          v-else-if="recentWorkflows.length"
          class="workflow-resources"
        >
          <router-link
            v-for="workflow in recentWorkflows"
            :key="workflow.id"
            :to="`/workflows/${workflow.id}/edit`"
            class="workflow-resource"
          >
            <GitBranch aria-hidden="true" /><span class="resource-copy"><strong>{{ workflow.name }}</strong><small>{{ workflow.nodeCount ?? '—' }} 个节点</small></span><ArrowUpRight aria-hidden="true" />
          </router-link>
        </div>
        <div
          v-else
          class="workflow-empty"
        >
          <span>还没有工作流，可以先用知识库创建助手。</span><router-link
            to="/workflows/new"
            class="text-link"
          >
            新建工作流<Plus aria-hidden="true" />
          </router-link>
        </div>
      </section>
      <aside
        class="workbench-section"
        aria-label="构建资源与小流助手"
      >
        <div class="assistant-identity">
          <button
            type="button"
            class="assistant-bot"
            aria-label="和小流打招呼"
            @click="greetBot"
          >
            <FlowlyBot
              :state="botState"
              :size="WORKBENCH.avatarSize"
              decorative
            />
          </button><div><strong>和小流一起构建</strong><p>描述你的流程，再带着真实结果迭代。</p></div><router-link
            to="/nl-create"
            class="text-link"
            aria-label="打开语创"
          >
            <ArrowUpRight aria-hidden="true" />
          </router-link>
        </div>
        <div class="resource-links">
          <router-link
            v-for="resource in WORKBENCH.resources"
            :key="resource.path"
            :to="resource.path"
            :title="resource.description"
          >
            {{ resource.title }}<ArrowUpRight aria-hidden="true" />
          </router-link>
        </div>
      </aside>
    </div>
  </PageShell>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { Activity, AlertCircle, ArrowRight, ArrowUpRight, Boxes, CheckCircle2, ChevronRight, Clock3, Database, GitBranch, Plus, Radio } from 'lucide-vue-next'
import { applicationsApi } from '@/api/applications'
import { APPLICATIONS } from '@/config/applications'
import { getWorkflowList } from '@/api/workflow'
import { DELIVERY_WORKBENCH as WORKBENCH, DELIVERY_REQUEST_LABELS as REQUEST_LABELS, DELIVERY_KIND_LABELS as KIND_LABELS } from '@/config/deliveryWorkbench'
import { BOT_AVATAR } from '@/config/botAvatar'
import AppButton from '@/components/common/AppButton.vue'
import FlowlyBot from '@/components/common/FlowlyBot.vue'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import dayjs from 'dayjs'

const overview = ref(null)
const overviewError = ref('')
const loadingOverview = ref(true)
const recentWorkflows = ref([])
const loadingWorkflows = ref(true)
const workflowError = ref('')
const botState = ref('idle')
let greetingTimer
let disposed = false
let overviewPending = false
let workflowsPending = false
const recentApplications = computed(() => (overview.value?.recentApplications || []).slice(0, WORKBENCH.recentApplicationLimit))
const recentRequests = computed(() => (overview.value?.recentRequests || []).slice(0, WORKBENCH.recentRequestLimit))
const numberFormatter = new Intl.NumberFormat(WORKBENCH.numberFormat.locale, WORKBENCH.numberFormat.decimal)
const percentFormatter = new Intl.NumberFormat(WORKBENCH.numberFormat.locale, WORKBENCH.numberFormat.percent)
const displayNumber = value => value == null ? '—' : numberFormatter.format(value)
const displayPercent = value => value == null ? '—' : percentFormatter.format(value)
const metrics = computed(() => [
  { label: '应用', value: displayNumber(overview.value?.applicationCount) },
  { label: '已发布', value: displayNumber(overview.value?.publishedCount) },
  { label: '请求', value: displayNumber(overview.value?.requestCount) },
  { label: '失败与拒绝', value: displayNumber(overview.value?.failedCount), warning: overview.value?.failedCount > 0 },
  { label: '成功率', value: displayPercent(overview.value?.successRate) },
  { label: '平均耗时', value: overview.value?.avgLatencyMs == null ? '—' : `${displayNumber(overview.value.avgLatencyMs)} ms` },
])
async function loadOverview() {
  if (overviewPending) return
  overviewPending = true
  loadingOverview.value = true
  overviewError.value = ''
  try {
    const result = await applicationsApi.overview()
    if (!disposed) overview.value = result
  } catch {
    if (!disposed) { overview.value = null; overviewError.value = WORKBENCH.failedOverview }
  } finally {
    overviewPending = false
    if (!disposed) loadingOverview.value = false
  }
}
async function loadWorkflows() {
  if (workflowsPending) return
  workflowsPending = true
  loadingWorkflows.value = true
  workflowError.value = ''
  try {
    const result = await getWorkflowList({ page_size: WORKBENCH.recentWorkflowLimit })
    if (!disposed) recentWorkflows.value = result.results || (Array.isArray(result) ? result : [])
  } catch {
    if (!disposed) { recentWorkflows.value = []; workflowError.value = WORKBENCH.failedWorkflows }
  } finally {
    workflowsPending = false
    if (!disposed) loadingWorkflows.value = false
  }
}
function greetBot() {
  clearTimeout(greetingTimer)
  botState.value = 'success'
  greetingTimer = setTimeout(() => { botState.value = 'idle' }, BOT_AVATAR.greetingDurationMs)
}
function formatDate(value) { return value && dayjs(value).isValid() ? dayjs(value).format('MM/DD HH:mm') : '—' }
function applicationName(id) { return recentApplications.value.find(item => item.id === id)?.name || '应用请求' }
function requestPath(item) { return `/applications/${item.applicationId}?tab=requests&request=${item.id}` }
onMounted(() => { loadOverview(); loadWorkflows() })
onBeforeUnmount(() => { disposed = true; clearTimeout(greetingTimer) })
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.delivery-workbench { container: delivery / inline-size; }
.delivery-workbench :deep(.app-button svg), .text-link svg { width: var(--delivery-icon); height: var(--delivery-icon); }
.text-link { display: inline-flex; align-items: center; gap: $spacing-2; color: var(--delivery-accent); font-size: $font-size-sm; white-space: nowrap; &:hover { opacity: 1; text-decoration: underline; } }
.workbench-error { display: flex; align-items: center; gap: $spacing-3; margin-bottom: $spacing-4; padding: $spacing-3 $spacing-4; border: 1px solid var(--border-secondary); border-radius: var(--radius-lg); background: var(--error-bg); font-size: $font-size-sm; > svg { width: var(--delivery-icon); flex-shrink: 0; } > span { flex: 1; } }
.delivery-pulse { display: grid; gap: $spacing-6; padding: $spacing-4 0 $spacing-6; border-bottom: 1px solid var(--delivery-border); }
.pulse-label { display: flex; flex-wrap: wrap; align-items: center; gap: $spacing-2; font-size: $font-size-sm; > svg { width: var(--delivery-icon); color: var(--delivery-accent); } small { margin-left: auto; color: var(--text-tertiary); font-size: $font-size-xs; } }
.delivery-pulse dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, #{$spacing-8 * 4}), 1fr)); min-width: 0; gap: $spacing-6; }
.pulse-metric { min-width: 0; dt { color: var(--text-secondary); font-size: $font-size-xs; } dd { margin-top: $spacing-2; font-family: var(--font-family-mono); font-weight: $font-weight-semibold; font-size: $font-size-xl; line-height: $line-height-normal; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; } .warning { color: var(--warning); } }
.delivery-path { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-block: $spacing-6 $spacing-8; border: 1px solid var(--delivery-border); border-radius: var(--delivery-radius); overflow: hidden; background: var(--delivery-panel); }
.delivery-step { display: flex; align-items: flex-start; gap: $spacing-3; padding: $spacing-4; min-width: 0; &:hover { background: var(--bg-hover); opacity: 1; } > svg { width: $spacing-4; height: $spacing-4; flex-shrink: 0; color: var(--text-tertiary); margin-left: auto; } }
.step-number { font-family: var(--font-family-mono); font-size: $font-size-xs; line-height: $line-height-normal; color: var(--delivery-accent); }
.step-copy { min-width: 0; display: flex; flex-direction: column; gap: $spacing-2; strong { color: var(--text-primary); font-size: $font-size-sm; font-weight: $font-weight-medium; } > span { color: var(--text-secondary); font-size: $font-size-xs; line-height: $line-height-normal; } }
.workbench-columns { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: $spacing-8; margin-bottom: $spacing-8; }
.workbench-section { min-width: 0; }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: $spacing-4; margin-bottom: $spacing-4; h2 { font-size: $font-size-lg; font-weight: $font-weight-semibold; line-height: $line-height-normal; } }
.section-kicker { display: block; color: var(--text-tertiary); font-family: var(--font-family-mono); font-size: $font-size-xs; line-height: $line-height-normal; margin-bottom: $spacing-2; }
.section-note { color: var(--text-tertiary); font-size: $font-size-xs; }
.application-row, .request-row { display: flex; align-items: center; gap: $spacing-3; min-height: $spacing-16; padding: $spacing-3 $spacing-2; border-bottom: 1px solid var(--delivery-border); &:hover { background: var(--bg-hover); opacity: 1; } }
.application-glyph { width: $spacing-10; height: $spacing-10; display: grid; place-items: center; flex-shrink: 0; border: 1px solid var(--delivery-border); border-radius: var(--radius-lg); color: var(--delivery-accent); background: var(--delivery-panel); svg { width: var(--delivery-icon); height: var(--delivery-icon); } }
.resource-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: $spacing-1; strong { color: var(--text-primary); font-size: $font-size-sm; font-weight: $font-weight-medium; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; } small { color: var(--text-secondary); font-size: $font-size-xs; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; } }
.release-label { display: inline-flex; align-items: center; gap: $spacing-2; color: var(--text-secondary); font-size: $font-size-xs; white-space: nowrap; > span { width: var(--delivery-status-dot); height: var(--delivery-status-dot); background: currentColor; border-radius: var(--radius-full); } &.live { color: var(--delivery-accent); } }
.row-arrow { width: $spacing-4; height: $spacing-4; color: var(--text-tertiary); flex-shrink: 0; }
.request-status { display: grid; place-items: center; color: var(--text-secondary); > svg { width: var(--delivery-icon); height: var(--delivery-icon); } &--completed { color: var(--delivery-accent); } &--failed, &--rejected { color: var(--error); } }
.request-timing { display: flex; flex-direction: column; align-items: flex-end; gap: $spacing-1; flex-shrink: 0; font-family: var(--font-family-mono); font-size: $font-size-xs; line-height: $line-height-normal; color: var(--text-secondary); small { color: var(--text-tertiary); } }
.application-empty, .request-empty { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; min-height: $spacing-16 * 3; gap: $spacing-3; padding: $spacing-6; border: 1px dashed var(--border-secondary); border-radius: var(--delivery-radius); > svg { width: $spacing-6; height: $spacing-6; color: var(--delivery-accent); } h3 { font-size: $font-size-base; font-weight: $font-weight-medium; } p { color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-relaxed; max-width: 60ch; } }
.request-empty { border: 0; padding-inline: $spacing-2; }
.resource-skeleton { display: flex; flex-direction: column; gap: $spacing-4; span { display: block; height: $spacing-12; background: var(--surface-muted); border-radius: var(--radius-lg); } }
.usage-note { color: var(--text-tertiary); font-size: $font-size-xs; line-height: $line-height-normal; margin-top: $spacing-3; }
.workbench-columns--resources { padding-top: $spacing-6; border-top: 1px solid var(--delivery-border); }
.workflow-resources { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: $spacing-2 $spacing-4; }
.workflow-resource { display: flex; align-items: center; gap: $spacing-3; padding: $spacing-3 $spacing-2; border-radius: var(--radius-lg); > svg { width: var(--delivery-icon); height: var(--delivery-icon); color: var(--text-tertiary); flex-shrink: 0; } &:hover { background: var(--bg-hover); opacity: 1; } }
.workflow-empty { display: flex; flex-direction: column; align-items: flex-start; gap: $spacing-3; color: var(--text-secondary); font-size: $font-size-sm; }
.inline-error { display: flex; gap: $spacing-3; color: var(--error); font-size: $font-size-sm; }
.assistant-identity { display: flex; align-items: center; gap: $spacing-3; > div { min-width: 0; flex: 1; } strong { font-size: $font-size-sm; font-weight: $font-weight-medium; } p { margin-top: $spacing-1; font-size: $font-size-xs; color: var(--text-secondary); line-height: $line-height-normal; } }
.resource-links { display: flex; flex-wrap: wrap; gap: $spacing-4; margin-top: $spacing-4; a { display: inline-flex; align-items: center; gap: $spacing-1; color: var(--text-secondary); font-size: $font-size-xs; &:hover { color: var(--delivery-accent); } svg { width: $spacing-3; height: $spacing-3; } } }
@container delivery (max-width: 1000px) { .delivery-pulse dl { gap: $spacing-3; } .delivery-path { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@container delivery (max-width: 720px) { .workbench-columns { grid-template-columns: minmax(0, 1fr); gap: $spacing-8; } .delivery-pulse dl { row-gap: $spacing-4; } .delivery-step { padding: $spacing-3; } .delivery-step > svg { display: none; } .workflow-resources { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 768px) { .workbench-error { flex-wrap: wrap; } .resource-links a, .text-link { min-height: var(--delivery-touch-target); } .row-arrow { display: none; } .pulse-metric dd { font-size: $font-size-lg; } }
</style>
