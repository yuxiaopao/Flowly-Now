<template>
  <PageShell width="wide">
    <PageHeader
      title="AI Agents"
      :meta="`${filteredAgents.length} 个 Agent`"
    >
      <template #actions>
        <el-input
          v-model="searchQuery"
          placeholder="搜索 Agent 名称..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
        <el-select
          v-model="typeFilter"
          placeholder="类型"
          clearable
          class="type-select"
        >
          <el-option
            label="对话型"
            value="conversational"
          />
          <el-option
            label="任务型"
            value="task"
          />
          <el-option
            label="研究型"
            value="research"
          />
          <el-option
            label="编程型"
            value="coding"
          />
        </el-select>
        <el-select
          v-model="teamFilter"
          placeholder="按团队筛选"
          clearable
          class="type-select"
        >
          <el-option
            label="仅我个人"
            value="mine"
          />
          <el-option
            v-for="t in tenantStore.tenants"
            :key="t.id"
            :label="t.name"
            :value="String(t.id)"
          />
        </el-select>
        <router-link to="/agents/marketplace">
          <AppButton variant="secondary">
            <Store class="btn-icon" />
            Agent 市场
          </AppButton>
        </router-link>
        <router-link to="/agents/new">
          <AppButton variant="primary">
            <Plus class="btn-icon" />
            新建 Agent
          </AppButton>
        </router-link>
      </template>
    </PageHeader>

    <div
      v-if="isLoading"
      class="loading-container"
    >
      <el-skeleton
        :rows="6"
        animated
      />
    </div>

    <PageEmptyState
      v-else-if="filteredAgents.length === 0"
      :icon="Bot"
      title="暂无 Agent"
      description="创建您的第一个 AI Agent，用于对话、任务或自动化编排。"
    >
      <template #actions>
        <router-link to="/agents/new">
          <AppButton variant="primary">
            创建 Agent
          </AppButton>
        </router-link>
      </template>
    </PageEmptyState>

    <div
      v-else
      class="agent-grid"
    >
      <div
        v-for="agent in filteredAgents"
        :key="agent.id"
        class="agent-card"
        @click="goToAgent(agent.id)"
      >
        <div class="card-header">
          <div class="agent-avatar">
            <Bot />
          </div>
          <el-dropdown
            trigger="click"
            @command="(cmd) => handleCommand(cmd, agent)"
            @click.stop
          >
            <el-button
              text
              circle
              @click.stop
            >
              <MoreVertical />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  编辑
                </el-dropdown-item>
                <el-dropdown-item command="debug">
                  调试
                </el-dropdown-item>
                <el-dropdown-item command="duplicate">
                  复制
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="agent.owner === authStore.user?.id"
                  :command="agent.is_public ? 'unpublish' : 'publish'"
                >
                  {{ agent.is_public ? '从市场下架' : '发布到市场' }}
                </el-dropdown-item>
                <el-dropdown-item
                  command="delete"
                  divided
                >
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="card-body">
          <h3 class="agent-name">
            {{ agent.name }}
          </h3>
          <p class="agent-desc">
            {{ agent.description || '暂无描述' }}
          </p>
          <div class="agent-meta">
            <el-tag
              :type="getTypeTagType(agent.agent_type)"
              size="small"
            >
              {{ getTypeLabel(agent.agent_type) }}
            </el-tag>
            <el-tag
              :type="agent.is_active ? 'success' : 'info'"
              size="small"
            >
              {{ agent.is_active ? '已启用' : '已禁用' }}
            </el-tag>
            <el-tag
              v-if="agent.tenant_name"
              type="success"
              size="small"
            >
              <Users class="tag-icon" />{{ agent.tenant_name }}
            </el-tag>
            <el-tag
              v-if="agent.knowledge_collections?.length"
              type="warning"
              size="small"
            >
              <BookOpen class="tag-icon" />知识库 x{{ agent.knowledge_collections.length }}
            </el-tag>
            <el-tag
              v-if="agent.is_public"
              type="danger"
              size="small"
            >
              <Store class="tag-icon" />已发布市场
            </el-tag>
          </div>
        </div>

        <div class="card-footer">
          <span class="model-name">
            <Cpu class="model-icon" />
            {{ agent.model || APP_CONFIG.llm.defaultModel }}
          </span>
          <span class="updated-time">{{ formatDate(agent.updatedAt || agent.updated_at) }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="totalPages > 1"
      class="pagination"
    >
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalCount"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </PageShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useAppStore } from '@/stores/app'
import { useTenantStore } from '@/stores/tenant'
import { useAuthStore } from '@/stores/auth'
import { APP_CONFIG } from '@/config'
import { agentApi } from '@/api/agent'
import { ElMessageBox } from 'element-plus'
import { Search, Plus, Bot, MoreVertical, Cpu, Users, BookOpen, Store } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageEmptyState from '@/components/layout/PageEmptyState.vue'

const router = useRouter()
const agentStore = useAgentStore()
const appStore = useAppStore()
const tenantStore = useTenantStore()
const authStore = useAuthStore()

const searchQuery = ref('')
const typeFilter = ref('')
const teamFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(12)

const agents = computed(() => agentStore.agents)
const isLoading = computed(() => agentStore.isLoading)
const totalCount = computed(() => agents.value.length)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

const filteredAgents = computed(() => {
  let result = agents.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(a =>
      a.name.toLowerCase().includes(query) ||
      a.description?.toLowerCase().includes(query)
    )
  }

  if (typeFilter.value) {
    result = result.filter(a => a.agent_type === typeFilter.value)
  }

  if (teamFilter.value === 'mine') {
    result = result.filter(a => !a.tenant)
  } else if (teamFilter.value) {
    result = result.filter(a => String(a.tenant || '') === teamFilter.value)
  }

  return result
})

onMounted(() => {
  fetchAgents()
  tenantStore.fetchTenants()
})

async function fetchAgents() {
  try {
    await agentStore.fetchAgents({
      page: currentPage.value,
      page_size: pageSize.value
    })
  } catch (err) {
    appStore.error('获取 Agent 列表失败')
  }
}

function handleSearch() {
  currentPage.value = 1
}

function handlePageChange(page) {
  currentPage.value = page
  fetchAgents()
}

function goToAgent(id) {
  router.push(`/agents/${id}/edit`)
}

async function handleCommand(command, agent) {
  switch (command) {
    case 'edit':
      goToAgent(agent.id)
      break
    case 'debug':
      router.push(`/agents/${agent.id}/debug`)
      break
    case 'duplicate':
      await duplicateAgent(agent)
      break
    case 'publish':
      await togglePublish(agent, true)
      break
    case 'unpublish':
      await togglePublish(agent, false)
      break
    case 'delete':
      await deleteAgent(agent.id)
      break
  }
}

async function togglePublish(agent, publish) {
  try {
    if (publish) {
      await agentApi.publishAgent(agent.id)
      appStore.success('已发布到 Agent 市场')
    } else {
      await agentApi.unpublishAgent(agent.id)
      appStore.success('已从市场下架')
    }
    fetchAgents()
  } catch (err) {
    appStore.error(publish ? '发布失败' : '下架失败')
  }
}

async function duplicateAgent(agent) {
  try {
    const newAgent = {
      name: `${agent.name} (副本)`,
      description: agent.description,
      agent_type: agent.agent_type,
      system_prompt: agent.system_prompt,
      model: agent.model,
      temperature: agent.temperature,
      max_tokens: agent.max_tokens,
      tools: agent.tools,
      skills: agent.skills,
      memory_enabled: agent.memory_enabled,
      context_window: agent.context_window
    }
    await agentStore.createAgent(newAgent)
    appStore.success('Agent 复制成功')
    fetchAgents()
  } catch (err) {
    appStore.error('复制失败')
  }
}

async function deleteAgent(id) {
  try {
    await ElMessageBox.confirm('确定要删除此 Agent 吗？此操作不可撤销。', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await agentStore.deleteAgent(id)
    appStore.success('Agent 已删除')
    fetchAgents()
  } catch (err) {
    if (err !== 'cancel') {
      appStore.error('删除失败')
    }
  }
}

function getTypeTagType(type) {
  const typeMap = {
    conversational: 'primary',
    task: 'success',
    research: 'warning',
    coding: 'info'
  }
  return typeMap[type] || 'info'
}

function getTypeLabel(type) {
  const labelMap = {
    conversational: '对话型',
    task: '任务型',
    research: '研究型',
    coding: '编程型'
  }
  return labelMap[type] || type
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.search-input {
  width: 280px;
}

.type-select {
  width: 120px;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

.loading-container {
  padding: $spacing-6;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-5;
}

.agent-card {
  position: relative;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-5;
  cursor: pointer;
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;

  // 顶部全宽暖色渐变描边，hover 时显现（Agent 主题色为琥珀橙）
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--border-gradient-warm);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    border-color: var(--accent-amber-soft);
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);

    &::after {
      opacity: 1;
    }
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-4;
}

.agent-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: linear-gradient(145deg, var(--agent-icon-from), var(--agent-icon-to));
  border-radius: $radius-xl;
  box-shadow:
    0 0 0 1px var(--agent-icon-shadow),
    0 4px 14px var(--agent-icon-shadow);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.22) 0%, transparent 55%);
    border-radius: inherit;
    pointer-events: none;
  }

  svg {
    width: 22px;
    height: 22px;
    color: #ffffff;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.25));
    position: relative;
    z-index: 1;
  }
}

.agent-card:hover .agent-avatar {
  transform: scale(1.06) rotate(3deg);
  box-shadow:
    0 0 0 1px var(--agent-icon-shadow),
    0 8px 24px var(--agent-icon-shadow);
}

.card-body {
  margin-bottom: $spacing-4;
}

.agent-name {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0 0 $spacing-3;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 40px;
}

.agent-meta {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
}

.tag-icon {
  width: 12px;
  height: 12px;
  margin-right: 4px;
  vertical-align: -1px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: $spacing-4;
  border-top: 1px solid var(--border-primary);
}

.model-name {
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-secondary);

  .model-icon {
    width: 14px;
    height: 14px;
  }
}

.updated-time {
  font-size: $font-size-xs;
  color: var(--text-primary);
  opacity: 0.5;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: $spacing-8;
}
</style>




