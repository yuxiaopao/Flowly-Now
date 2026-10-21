<template>
  <PageShell width="wide">
    <PageHeader
      title="智能体"
      :meta="`${filteredAgents.length} 个智能体`"
    >
      <template #actions>
        <router-link to="/agents/marketplace">
          <AppButton variant="secondary">
            <Store class="btn-icon" />
            智能体市场
          </AppButton>
        </router-link>
        <router-link to="/agents/new">
          <AppButton variant="primary">
            <Plus class="btn-icon" />
            新建智能体
          </AppButton>
        </router-link>
      </template>
    </PageHeader>

    <PageToolbar>
      <el-input
        v-model="searchQuery"
        placeholder="搜索 智能体名称..."
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
    </PageToolbar>

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
      title="暂无智能体"
      description="创建您的第一个 AI 智能体，用于对话、任务或自动化编排。"
    >
      <template #actions>
        <router-link to="/agents/new">
          <AppButton variant="primary">
            创建智能体
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
        tabindex="0"
        role="link"
        :aria-label="`编辑智能体：${agent.name}`"
        @keydown.enter.self="goToAgent(agent.id)"
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
              :aria-label="`${agent.name}的更多操作`"
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
import PageToolbar from '@/components/layout/PageToolbar.vue'
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

const agents = computed(() => agentStore.agents.map(agent => ({
  ...agent,
  agent_type: agent.agentType ?? agent.agent_type,
  is_active: agent.isActive ?? agent.is_active,
  is_public: agent.isPublic ?? agent.is_public,
  tenant_name: agent.tenantName ?? agent.tenant_name,
  knowledge_collections: agent.knowledgeCollections ?? agent.knowledge_collections,
  updated_at: agent.updatedAt ?? agent.updated_at,
  system_prompt: agent.systemPrompt ?? agent.system_prompt,
  max_tokens: agent.maxTokens ?? agent.max_tokens,
  memory_enabled: agent.memoryEnabled ?? agent.memory_enabled,
  context_window: agent.contextWindow ?? agent.context_window
})))
const isLoading = computed(() => agentStore.isLoading)
const totalCount = computed(() => agentStore.listPagination.count || agents.value.length)
const totalPages = computed(() => Math.max(1, agentStore.listPagination.totalPages || Math.ceil(totalCount.value / pageSize.value)))

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
    const response = await agentStore.fetchAgents({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const nextTotalPages = response.totalPages ?? response.total_pages ?? totalPages.value
    if (currentPage.value > nextTotalPages) {
      currentPage.value = Math.max(1, nextTotalPages)
      await agentStore.fetchAgents({
        page: currentPage.value,
        page_size: pageSize.value
      })
    }
  } catch (err) {
    if (err?.response?.status === 404 && currentPage.value > 1) {
      currentPage.value = 1
      await agentStore.fetchAgents({
        page: currentPage.value,
        page_size: pageSize.value
      })
      return
    }
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
      appStore.success('已发布到 智能体市场')
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

.btn-icon {
  width: 18px;
  height: 18px;
}

.loading-container {
  padding: $spacing-6;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr));
  gap: $spacing-4;
}

.agent-card {
  min-width: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--content-card-radius);
  padding: var(--content-card-padding);
  cursor: pointer;
  transition: border-color $transition-fast;
  &:hover { border-color: var(--border-hover); }
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-3;
}
.agent-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: $radius-md;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  color: var(--text-secondary);
  svg { width: 20px; height: 20px; }
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

