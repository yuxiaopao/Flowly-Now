<template>
  <div class="agent-list">
    <div class="list-header">
      <div class="header-left">
        <h1 class="page-title">
          AI Agents
        </h1>
        <span class="agent-count">{{ agents.length }} 个 Agent</span>
      </div>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索 Agent..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
        <el-select
          v-model="typeFilter"
          placeholder="类型"
          clearable
          @change="fetchAgents"
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
        <router-link to="/agents/new">
          <AppButton variant="primary">
            <Plus class="btn-icon" />
            新建 Agent
          </AppButton>
        </router-link>
      </div>
    </div>

    <div
      v-if="isLoading"
      class="loading-container"
    >
      <el-skeleton
        :rows="6"
        animated
      />
    </div>

    <div
      v-else-if="agents.length === 0"
      class="empty-state"
    >
      <Bot class="empty-icon" />
      <h3>暂无 Agent</h3>
      <p>创建您的第一个 AI Agent</p>
      <router-link to="/agents/new">
        <AppButton variant="primary">
          创建 Agent
        </AppButton>
      </router-link>
    </div>

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
          </div>
        </div>

        <div class="card-footer">
          <span class="model-name">
            <Cpu class="model-icon" />
            {{ agent.model || APP_CONFIG.llm.defaultModel }}
          </span>
          <span class="updated-time">{{ formatDate(agent.updated_at) }}</span>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useAppStore } from '@/stores/app'
import { APP_CONFIG } from '@/config'
import { ElMessageBox } from 'element-plus'
import { Search, Plus, Bot, MoreVertical, Cpu } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'

const router = useRouter()
const agentStore = useAgentStore()
const appStore = useAppStore()

const searchQuery = ref('')
const typeFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const defaultModel = APP_CONFIG.llm.defaultModel

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

  return result
})

onMounted(() => {
  fetchAgents()
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
    case 'delete':
      await deleteAgent(agent.id)
      break
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

.agent-list {
  max-width: 1400px;
  margin: 0 auto;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;
  flex-wrap: wrap;
  gap: $spacing-4;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: $spacing-3;
}

.page-title {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0;
}

.agent-count {
  font-size: $font-size-sm;
  color: var(--text-primary);
  opacity: 0.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.search-input {
  width: 280px;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

.loading-container {
  padding: $spacing-6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-16;
  text-align: center;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--text-primary);
  opacity: 0.5;
    margin-bottom: $spacing-4;
  }

  h3 {
    font-size: $font-size-xl;
    color: var(--text-primary);
    margin: 0 0 $spacing-2;
  }

  p {
    color: var(--text-secondary);
    margin: 0 0 $spacing-6;
  }
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-5;
}

.agent-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-5;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: var(--accent-primary);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
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
  gap: $spacing-2;
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




