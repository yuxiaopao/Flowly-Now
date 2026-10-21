<template>
  <PageShell
    width="wide"
    class="ai-workbench"
  >
    <PageHeader
      :title="`欢迎回来，${authStore.userName}`"
      subtitle="工作流、执行状态与常用资源，一处掌握。"
    >
      <template #actions>
        <router-link to="/workflows/new">
          <AppButton variant="primary">
            <Plus class="button-icon" />
            新建工作流
          </AppButton>
        </router-link>
      </template>
    </PageHeader>

    <section
      class="assistant-welcome"
      aria-labelledby="assistant-welcome-title"
    >
      <div class="assistant-welcome__copy">
        <span class="assistant-welcome__eyebrow"><Sparkles aria-hidden="true" />{{ BOT_AVATAR.home.eyebrow }}</span>
        <h2 id="assistant-welcome-title">
          {{ BOT_AVATAR.home.title }}
        </h2>
        <p>{{ BOT_AVATAR.home.description }}</p>
        <span class="assistant-welcome__capabilities">
          <template
            v-for="(capability, index) in AI_WORKBENCH.capabilities"
            :key="capability.id"
          >
            <span
              v-if="index"
              aria-hidden="true"
            >/</span>{{ capability.label }}
          </template>
        </span>
        <router-link
          :to="BOT_AVATAR.home.route"
          class="assistant-welcome__action"
        >
          <MessageSquare aria-hidden="true" />
          <span>{{ BOT_AVATAR.home.action }}</span>
          <ArrowUpRight aria-hidden="true" />
        </router-link>
      </div>
      <div class="assistant-welcome__companion">
        <AssistantCircuit
          :state="botState"
          @greet="greetBot"
        />
        <span
          class="assistant-welcome__hint"
          role="status"
          aria-live="polite"
        >
          {{ botState === 'success' ? BOT_AVATAR.home.greeting : BOT_AVATAR.home.hint }}
        </span>
      </div>
    </section>

    <div
      v-if="failedModules.length"
      class="dashboard-feedback"
      role="status"
    >
      <span>{{ failedModules.join('、') }}暂时无法加载，其余数据可正常查看。</span>
      <AppButton
        variant="secondary"
        size="small"
        :loading="isLoading"
        @click="loadDashboard"
      >
        重新加载
      </AppButton>
    </div>

    <StatGrid>
      <StatCard
        label="工作流"
        :value="stats.workflows ?? '—'"
        :loading="moduleLoading.workflows"
        :icon="GitBranch"
        tone="primary"
      />
      <StatCard
        label="执行次数"
        :value="stats.executions ?? '—'"
        :loading="moduleLoading.executions"
        :icon="Play"
        tone="success"
      />
      <StatCard
        label="智能体"
        :value="stats.agents ?? '—'"
        :loading="moduleLoading.agents"
        :icon="Bot"
        tone="violet"
      />
      <StatCard
        label="成功率"
        :value="stats.successRate == null ? '—' : `${stats.successRate}%`"
        :loading="moduleLoading.executions"
        :icon="Clock"
        tone="info"
      />
    </StatGrid>

    <div class="page-shell__grid page-shell__grid--2-1">
      <SectionCard
        title="最近工作流"
        :icon="GitBranch"
        :loading="moduleLoading.workflows"
      >
        <template #actions>
          <router-link to="/workflows">
            <AppButton
              variant="ghost"
              size="small"
              text
            >
              查看全部
            </AppButton>
          </router-link>
        </template>

        <div
          v-if="recentWorkflows.length === 0"
          class="dashboard-empty"
        >
          <PageEmptyState
            :icon="GitBranch"
            :title="failedModules.includes('工作流') ? '工作流加载失败' : '暂无工作流'"
            :description="failedModules.includes('工作流') ? '请检查网络连接后重新加载。' : '创建您的第一个 AI 工作流，开始自动化任务。'"
          >
            <template #actions>
              <router-link to="/workflows/new">
                <AppButton size="small">
                  创建第一个工作流
                </AppButton>
              </router-link>
            </template>
          </PageEmptyState>
        </div>
        <div
          v-else
          class="workflow-list"
        >
          <div
            v-for="workflow in recentWorkflows"
            :key="workflow.id"
            class="workflow-item"
            role="link"
            tabindex="0"
            @click="goToWorkflow(workflow.id)"
            @keydown.enter="goToWorkflow(workflow.id)"
          >
            <div class="workflow-info">
              <span class="workflow-name">{{ workflow.name }}</span>
              <span class="workflow-date">{{ formatDate(workflow.updatedAt || workflow.updated_at) }}</span>
            </div>
            <el-tag
              :type="getStatusType(workflow.status)"
              size="small"
            >
              {{ getStatusLabel(workflow.status) }}
            </el-tag>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="快速操作"
        :icon="Zap"
      >
        <div class="quick-actions">
          <router-link
            to="/workflows/new"
            class="quick-action quick-action--blue"
          >
            <span class="quick-action-icon"><GitBranch /></span>
            <span>新建工作流</span>
          </router-link>
          <router-link
            to="/agents/new"
            class="quick-action quick-action--amber"
          >
            <span class="quick-action-icon"><Bot /></span>
            <span>创建智能体</span>
          </router-link>
          <router-link
            to="/nl-create"
            class="quick-action quick-action--rose"
          >
            <span class="quick-action-icon"><MessageSquare /></span>
            <span>语创</span>
          </router-link>
          <router-link
            to="/marketplace"
            class="quick-action quick-action--emerald"
          >
            <span class="quick-action-icon"><Search /></span>
            <span>浏览模板</span>
          </router-link>
        </div>
      </SectionCard>
    </div>
  </PageShell>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowStore } from '@/stores/workflow'
import { getExecutionStatistics } from '@/api/workflow'
import { agentApi } from '@/api/agent'
import { Plus, GitBranch, Play, Bot, Clock, MessageSquare, Search, Zap, ArrowUpRight, Sparkles } from 'lucide-vue-next'
import AssistantCircuit from '@/components/dashboard/AssistantCircuit.vue'
import { BOT_AVATAR } from '@/config/botAvatar'
import { AI_WORKBENCH, PRODUCT_UI } from '@/config/productUi'
import AppButton from '@/components/common/AppButton.vue'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatGrid from '@/components/layout/StatGrid.vue'
import StatCard from '@/components/layout/StatCard.vue'
import SectionCard from '@/components/layout/SectionCard.vue'
import PageEmptyState from '@/components/layout/PageEmptyState.vue'
import dayjs from 'dayjs'

const router = useRouter()
const authStore = useAuthStore()
const workflowStore = useWorkflowStore()

const stats = ref({
  workflows: null,
  executions: null,
  agents: null,
  successRate: null,
})
const isLoading = ref(false)
const moduleLoading = ref({ workflows: true, executions: true, agents: true })
const failedModules = ref([])

const recentWorkflows = ref([])
const botState = ref('idle')
let greetingTimer

function greetBot() {
  clearTimeout(greetingTimer)
  botState.value = 'success'
  greetingTimer = setTimeout(() => { botState.value = 'idle' }, BOT_AVATAR.greetingDurationMs)
}

onBeforeUnmount(() => clearTimeout(greetingTimer))

async function loadDashboard() {
  if (isLoading.value) return
  isLoading.value = true
  failedModules.value = []
  moduleLoading.value = { workflows: true, executions: true, agents: true }
  await Promise.allSettled([
    workflowStore.fetchWorkflows({ page_size: PRODUCT_UI.recentWorkflowLimit })
      .then(response => {
        recentWorkflows.value = response.results || (Array.isArray(response) ? response : [])
        stats.value.workflows = response.count ?? recentWorkflows.value.length
      })
      .catch(() => { failedModules.value.push('工作流'); stats.value.workflows = null })
      .finally(() => { moduleLoading.value.workflows = false }),
    getExecutionStatistics()
      .then(response => {
        const total = response.totalExecutions ?? response.total_executions ?? 0
        const completed = response.completedCount ?? response.completed_count ?? 0
        stats.value.executions = total
        stats.value.successRate = total > 0 ? Math.round(completed / total * 1000) / 10 : 0
      })
      .catch(() => { failedModules.value.push('执行统计'); stats.value.executions = stats.value.successRate = null })
      .finally(() => { moduleLoading.value.executions = false }),
    agentApi.getList({ page_size: 1 })
      .then(response => { stats.value.agents = response.count ?? (response.results?.length ?? 0) })
      .catch(() => { failedModules.value.push('智能体'); stats.value.agents = null })
      .finally(() => { moduleLoading.value.agents = false }),
  ])
  isLoading.value = false
}

onMounted(loadDashboard)

function goToWorkflow(id) {
  router.push(`/workflows/${id}`)
}

function formatDate(date) {
  return dayjs(date).format('MM/DD HH:mm')
}

function getStatusType(status) {
  const typeMap = {
    draft: 'info',
    active: 'success',
    paused: 'warning',
    archived: 'info',
  }
  return typeMap[status] || 'info'
}

function getStatusLabel(status) {
  const labelMap = {
    draft: '草稿',
    active: '活跃',
    paused: '已暂停',
    archived: '已归档',
  }
  return labelMap[status] || status
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.ai-workbench { container: workbench / inline-size; }
.assistant-welcome {
  position: relative; isolation: isolate; overflow: hidden;
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 45%); align-items: center; gap: $spacing-5;
  margin-bottom: var(--page-section-gap); padding: $spacing-5 $spacing-8;
  border: 1px solid var(--tech-border); border-radius: var(--radius-card); background: var(--tech-hero-bg);
  &::before { content: ''; position: absolute; inset: 0; z-index: -1; pointer-events: none; background-image: linear-gradient(var(--tech-grid) 1px, transparent 1px), linear-gradient(90deg, var(--tech-grid) 1px, transparent 1px); background-size: var(--tech-grid-size) var(--tech-grid-size); }
  &__eyebrow { display: inline-flex; align-items: center; gap: $spacing-2; color: var(--tech-cyan); font-size: $font-size-xs; font-weight: $font-weight-medium; svg { width: $spacing-4; height: $spacing-4; } }
  h2 { margin: $spacing-3 0; color: var(--text-primary); font-size: $font-size-3xl; line-height: $line-height-tight; font-weight: $font-weight-semibold; }
  p { max-width: 65ch; margin: 0 0 $spacing-3; color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-normal; }
  &__capabilities { display: flex; align-items: center; gap: $spacing-2; margin-block: $spacing-4; color: var(--text-secondary); font-size: $font-size-xs; span { color: var(--tech-border); } }
  &__action { display: inline-flex; align-items: center; gap: $spacing-2; padding: $spacing-2 $spacing-3; border: 1px solid var(--tech-selection-border); border-radius: $radius-lg; background: var(--tech-blue-soft); color: var(--tech-blue); font-size: $font-size-sm; font-weight: $font-weight-medium; svg { width: $spacing-4; height: $spacing-4; } &:hover { opacity: 1; border-color: var(--tech-blue); } }
  &__companion { min-width: 0; display: flex; flex-direction: column; align-items: center; }
  &__hint { margin-top: $spacing-2; color: var(--text-secondary); font-size: $font-size-xs; }
}
.dashboard-feedback { display: flex; align-items: center; justify-content: space-between; gap: $spacing-3; padding: $spacing-3 $spacing-4; margin-bottom: $spacing-4; color: var(--text-secondary); background: var(--warning-bg); border-radius: $radius-lg; font-size: $font-size-sm; }
.button-icon { width: $spacing-4; height: $spacing-4; }
.dashboard-empty :deep(.page-empty-state) { padding: $spacing-6 $spacing-4; }
.workflow-list { display: flex; flex-direction: column; }
.workflow-item {
  display: flex; justify-content: space-between; align-items: center; gap: $spacing-4;
  padding: $spacing-3 0; border-bottom: 1px solid var(--border-primary); cursor: pointer;
  &:last-child { border-bottom: 0; }
  &:hover { background: var(--surface-muted); }
}
.workflow-info { display: flex; flex-direction: column; gap: $spacing-1; min-width: 0; }
.workflow-name { font-size: $font-size-sm; font-weight: $font-weight-medium; color: var(--text-primary); white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
.workflow-date { font-size: $font-size-xs; color: var(--text-tertiary); }
.quick-actions { display: flex; flex-direction: column; gap: $spacing-2; }
.quick-action {
  display: flex; align-items: center; gap: $spacing-3; padding: $spacing-2;
  border-radius: $radius-lg; color: var(--text-secondary); font-size: $font-size-sm;
  &:hover { background: var(--item-accent-bg); color: var(--text-primary); opacity: 1; }
}
.quick-action-icon :deep(svg) { width: 18px; height: 18px; }
@media (max-width: 1024px) {
  .assistant-welcome { padding: $spacing-5; grid-template-columns: minmax(0, 1fr) minmax(300px, 45%); }
}
@media (max-width: 720px) {
  .assistant-welcome { padding: $spacing-5 $spacing-4; gap: $spacing-2; grid-template-columns: 1fr; h2 { font-size: $font-size-2xl; } &__companion { width: 100%; } }
  .dashboard-feedback { flex-direction: column; align-items: flex-start; }
  .quick-action { min-height: var(--control-height-large); }
}
@container workbench (max-width: 680px) {
  .assistant-welcome { grid-template-columns: 1fr; h2 { font-size: $font-size-2xl; } }
  .assistant-welcome__capabilities { white-space: nowrap; }
}
</style>
