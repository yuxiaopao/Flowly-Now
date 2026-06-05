<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div>
        <h1 class="dashboard-title">
          欢迎回来, {{ authStore.userName }}
        </h1>
        <p class="dashboard-subtitle">
          这里是您的工作概览
        </p>
      </div>
      <router-link to="/workflows/new">
        <AppButton variant="primary">
          <Plus class="button-icon" />
          新建工作流
        </AppButton>
      </router-link>
    </div>

    <div class="stats-grid">
      <div class="stat-card stat-card--workflows">
        <div class="stat-icon stat-icon--primary">
          <GitBranch />
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.workflows }}</span>
          <span class="stat-label">工作流</span>
        </div>
      </div>

      <div class="stat-card stat-card--executions">
        <div class="stat-icon stat-icon--success">
          <Play />
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.executions }}</span>
          <span class="stat-label">执行次数</span>
        </div>
      </div>

      <div class="stat-card stat-card--agents">
        <div class="stat-icon stat-icon--warning">
          <Bot />
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.agents }}</span>
          <span class="stat-label">Agent</span>
        </div>
      </div>

      <div class="stat-card stat-card--success">
        <div class="stat-icon stat-icon--info">
          <Clock />
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.successRate }}%</span>
          <span class="stat-label">成功率</span>
        </div>
      </div>
    </div>

    <div class="dashboard-grid">
      <AppCard
        title="最近工作流"
        icon="GitBranch"
      >
        <template #actions>
          <router-link to="/workflows">
            <el-button
              text
              size="small"
            >
              查看全部
            </el-button>
          </router-link>
        </template>
        <div class="workflow-list">
          <div
            v-if="recentWorkflows.length === 0"
            class="empty-state"
          >
            <GitBranch class="empty-icon" />
            <p>暂无工作流</p>
            <router-link to="/workflows/new">
              <AppButton size="small">
                创建第一个工作流
              </AppButton>
            </router-link>
          </div>
          <div
            v-for="workflow in recentWorkflows"
            :key="workflow.id"
            class="workflow-item"
          >
            <div class="workflow-info">
              <span class="workflow-name">{{ workflow.name }}</span>
              <span class="workflow-date">{{ formatDate(workflow.updated_at) }}</span>
            </div>
            <el-tag
              :type="getStatusType(workflow.status)"
              size="small"
            >
              {{ getStatusLabel(workflow.status) }}
            </el-tag>
          </div>
        </div>
      </AppCard>

      <AppCard
        title="快速操作"
        icon="Zap"
      >
        <div class="quick-actions">
          <router-link
            to="/workflows/new"
            class="quick-action"
          >
            <GitBranch class="quick-action-icon" />
            <span>新建工作流</span>
          </router-link>
          <router-link
            to="/agents/new"
            class="quick-action"
          >
            <Bot class="quick-action-icon" />
            <span>创建 Agent</span>
          </router-link>
          <router-link
            to="/nl-create"
            class="quick-action"
          >
            <MessageSquare class="quick-action-icon" />
            <span>自然语言创建</span>
          </router-link>
          <router-link
            to="/workflows"
            class="quick-action"
          >
            <Search class="quick-action-icon" />
            <span>浏览模板</span>
          </router-link>
        </div>
      </AppCard>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import { Plus, GitBranch, Play, Bot, Clock, Zap, MessageSquare, Search } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import AppCard from '@/components/common/AppCard.vue'
import dayjs from 'dayjs'

const authStore = useAuthStore()
const workflowStore = useWorkflowStore()
const appStore = useAppStore()

const stats = ref({
  workflows: 0,
  executions: 0,
  agents: 0,
  successRate: 0
})

const recentWorkflows = ref([])

onMounted(async () => {
  try {
    const response = await workflowStore.fetchWorkflows({ page_size: 5 })
    recentWorkflows.value = response.results || response
    stats.value.workflows = recentWorkflows.value.length
  } catch {
    // Silent failure - dashboard will show empty state
  }
})

function formatDate(date) {
  return dayjs(date).format('MM/DD HH:mm')
}

function getStatusType(status) {
  const typeMap = {
    draft: 'info',
    active: 'success',
    paused: 'warning',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

function getStatusLabel(status) {
  const labelMap = {
    draft: '草稿',
    active: '活跃',
    paused: '已暂停',
    archived: '已归档'
  }
  return labelMap[status] || status
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-8;
}

.dashboard-title {
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0 0 $spacing-2;
}

.dashboard-subtitle {
  font-size: $font-size-base;
  color: var(--text-secondary);
  margin: 0;
}

.button-icon {
  width: 18px;
  height: 18px;
  margin-right: $spacing-2;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-4;
  margin-bottom: $spacing-6;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-5;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;

  &:hover {
    border-color: var(--border-hover);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  &--workflows:hover { border-color: rgba($color-primary, 0.4); }
  &--executions:hover { border-color: rgba($color-success, 0.4); }
  &--agents:hover { border-color: rgba($color-warning, 0.4); }
  &--success:hover { border-color: rgba($color-info, 0.4); }
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: $radius-lg;

  svg {
    width: 24px;
    height: 24px;
  }

  &--primary {
    background-color: rgba($color-primary, 0.12);
    color: $color-primary;
  }

  &--success {
    background-color: rgba($color-success, 0.12);
    color: $color-success;
  }

  &--warning {
    background-color: rgba($color-warning, 0.12);
    color: $color-warning;
  }

  &--info {
    background-color: rgba($color-info, 0.12);
    color: $color-info;
  }
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: $font-size-2xl;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  line-height: 1.2;
}

.stat-label {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin-top: 2px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: $spacing-6;

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: 1fr;
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
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
  transition: background-color $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
  }
}

.workflow-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.workflow-name {
  font-weight: $font-weight-medium;
  color: var(--text-primary);
}

.workflow-date {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: $spacing-8;
  color: var(--text-secondary);

  .empty-icon {
    width: 48px;
    height: 48px;
    margin-bottom: $spacing-4;
    opacity: 0.5;
  }

  p {
    margin-bottom: $spacing-4;
  }
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
  padding: $spacing-4;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
    color: var(--accent-primary);

    .quick-action-icon {
      color: $color-primary;
    }
  }
}

.quick-action-icon {
  width: 24px;
  height: 24px;
  color: var(--text-tertiary);
  transition: color $transition-fast;
}
</style>
