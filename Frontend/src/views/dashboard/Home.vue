<template>
  <PageShell width="narrow">
    <PageHeader
      :title="`欢迎回来，${authStore.userName}`"
      subtitle="这里是您的工作概览"
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

    <StatGrid class="anim-stagger">
      <StatCard
        label="工作流"
        :value="stats.workflows"
        :icon="GitBranch"
        tone="primary"
      />
      <StatCard
        label="执行次数"
        :value="stats.executions"
        :icon="Play"
        tone="success"
      />
      <StatCard
        label="Agent"
        :value="stats.agents"
        :icon="Bot"
        tone="warning"
      />
      <StatCard
        label="成功率"
        :value="`${stats.successRate}%`"
        :icon="Clock"
        tone="info"
      />
    </StatGrid>

    <div class="page-shell__grid page-shell__grid--2-1">
      <SectionCard
        title="最近工作流"
        :icon="GitBranch"
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
            title="暂无工作流"
            description="创建您的第一个 AI 工作流，开始自动化任务。"
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
            <span>创建 Agent</span>
          </router-link>
          <router-link
            to="/nl-create"
            class="quick-action quick-action--rose"
          >
            <span class="quick-action-icon"><MessageSquare /></span>
            <span>自然语言创建</span>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowStore } from '@/stores/workflow'
import { getExecutionStatistics } from '@/api/workflow'
import { agentApi } from '@/api/agent'
import { Plus, GitBranch, Play, Bot, Clock, MessageSquare, Search, Zap } from 'lucide-vue-next'
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
  workflows: 0,
  executions: 0,
  agents: 0,
  successRate: 0,
})

const recentWorkflows = ref([])

onMounted(async () => {
  try {
    const [workflowRes, execStats, agentRes] = await Promise.all([
      workflowStore.fetchWorkflows({ page_size: 5 }),
      getExecutionStatistics(),
      agentApi.getList({ page_size: 1 }),
    ])

    recentWorkflows.value = workflowRes.results || workflowRes
    stats.value.workflows = workflowRes.count ?? recentWorkflows.value.length

    const totalExecutions = execStats.totalExecutions ?? execStats.total_executions ?? 0
    const completedCount = execStats.completedCount ?? execStats.completed_count ?? 0
    stats.value.executions = totalExecutions
    stats.value.successRate = totalExecutions > 0
      ? Math.round((completedCount / totalExecutions) * 1000) / 10
      : 0

    stats.value.agents = agentRes.count ?? (agentRes.results?.length ?? 0)
  } catch {
    // 仪表盘允许静默失败，展示空状态
  }
})

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
@use '@/assets/styles/page-layout.scss';

.button-icon {
  width: 18px;
  height: 18px;
}

.dashboard-empty {
  :deep(.page-empty-state) {
    padding: $spacing-6 $spacing-4;
  }
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.workflow-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-3 $spacing-4;
  background-color: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: background-color $transition-fast, border-color $transition-fast, transform $transition-fast, box-shadow $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
    border-color: var(--accent-blue-soft);
    transform: translateX(2px);
    box-shadow: var(--shadow-sm);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.workflow-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
  min-width: 0;
}

.workflow-name {
  font-weight: $font-weight-medium;
  color: var(--text-primary);
}

.workflow-date {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-3;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-5 $spacing-4;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  color: var(--text-secondary);
  text-decoration: none;
  transition: background-color 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              border-color 0.25s ease,
              color 0.25s ease,
              transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.25s ease;

  &:hover {
    background-color: var(--bg-hover);
    border-color: var(--color-primary-30);
    color: var(--text-primary);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);

    .quick-action-icon {
      transform: scale(1.08);
    }
  }
}

.quick-action-icon {
  :deep(svg) {
    width: 22px;
    height: 22px;
  }
}
</style>
