<template>
  <PageShell width="wide">
    <PageHeader
      title="Agent 市场"
      :meta="`${totalCount} 个公开 Agent`"
    >
      <template #actions>
        <el-input
          v-model="searchQuery"
          placeholder="搜索 Agent 名称或描述..."
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
          @change="handleSearch"
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
        <router-link to="/agents">
          <AppButton variant="secondary">
            <Bot class="btn-icon" />
            我的 Agent
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
      v-else-if="agents.length === 0"
      :icon="Store"
      title="市场暂无公开 Agent"
      description="在「我的 Agent」列表中，通过卡片菜单将你的 Agent 发布到市场，供团队与其他用户克隆使用。"
    >
      <template #actions>
        <router-link to="/agents">
          <AppButton variant="primary">
            前往我的 Agent
          </AppButton>
        </router-link>
      </template>
    </PageEmptyState>

    <div
      v-else
      class="agent-grid"
    >
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
      >
        <div class="card-header">
          <div class="agent-avatar">
            <Bot />
          </div>
          <el-tag
            :type="getTypeTagType(agent.agent_type)"
            size="small"
          >
            {{ getTypeLabel(agent.agent_type) }}
          </el-tag>
        </div>

        <div class="card-body">
          <h3 class="agent-name">
            {{ agent.name }}
          </h3>
          <p class="agent-desc">
            {{ agent.description || '暂无描述' }}
          </p>
          <div class="agent-meta">
            <span class="meta-item">
              <User class="meta-icon" />{{ agent.owner_username }}
            </span>
            <span
              v-if="agent.tenant_name"
              class="meta-item"
            >
              <Users class="meta-icon" />{{ agent.tenant_name }}
            </span>
            <span class="meta-item">
              <Cpu class="meta-icon" />{{ agent.model || APP_CONFIG.llm.defaultModel }}
            </span>
          </div>
        </div>

        <div class="card-footer">
          <AppButton
            variant="secondary"
            size="small"
            @click="previewAgent(agent)"
          >
            <Eye class="btn-icon" />
            预览
          </AppButton>
          <AppButton
            variant="primary"
            size="small"
            :loading="cloningId === agent.id"
            @click="handleClone(agent)"
          >
            <Copy class="btn-icon" />
            克隆使用
          </AppButton>
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

    <!-- 预览对话框 -->
    <el-dialog
      v-model="showPreview"
      title="Agent 详情预览"
      width="600px"
    >
      <div
        v-if="previewTarget"
        class="preview-body"
      >
        <h4>{{ previewTarget.name }}</h4>
        <p class="preview-desc">
          {{ previewTarget.description || '暂无描述' }}
        </p>
        <div class="preview-section">
          <h5>系统提示词</h5>
          <pre class="preview-prompt">{{ previewTarget.system_prompt || '（无）' }}</pre>
        </div>
        <div class="preview-section">
          <h5>工具</h5>
          <div class="tools-list">
            <el-tag
              v-for="tool in previewTarget.tools"
              :key="tool"
              size="small"
            >
              {{ getToolLabel(tool) }}
            </el-tag>
            <span
              v-if="!previewTarget.tools?.length"
              class="no-tools"
            >无</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showPreview = false">
          关闭
        </el-button>
        <AppButton
          variant="primary"
          :loading="cloningId === previewTarget?.id"
          @click="handleClone(previewTarget)"
        >
          <Copy class="btn-icon" />
          克隆使用
        </AppButton>
      </template>
    </el-dialog>
  </PageShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { agentApi } from '@/api/agent'
import { useAppStore } from '@/stores/app'
import { APP_CONFIG } from '@/config'
import { getToolLabel } from '@/config/toolConfig'
import { Search, Bot, Cpu, Users, User, Store, Eye, Copy } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageEmptyState from '@/components/layout/PageEmptyState.vue'

const router = useRouter()
const appStore = useAppStore()

const agents = ref([])
const isLoading = ref(false)
const searchQuery = ref('')
const typeFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const totalCount = ref(0)

const cloningId = ref(null)
const showPreview = ref(false)
const previewTarget = ref(null)

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

onMounted(() => {
  fetchMarketplace()
})

async function fetchMarketplace() {
  isLoading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (searchQuery.value) params.search = searchQuery.value
    if (typeFilter.value) params.agent_type = typeFilter.value

    const res = await agentApi.getMarketplace(params)
    agents.value = res.results || res
    totalCount.value = res.count ?? agents.value.length
  } catch (err) {
    appStore.error('获取市场列表失败')
  } finally {
    isLoading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchMarketplace()
}

function handlePageChange(page) {
  currentPage.value = page
  fetchMarketplace()
}

function previewAgent(agent) {
  previewTarget.value = agent
  showPreview.value = true
}

async function handleClone(agent) {
  if (!agent) return
  cloningId.value = agent.id
  try {
    const cloned = await agentApi.cloneAgent(agent.id)
    appStore.success(`已克隆为「${cloned.name}」，可在「我的 Agent」中查看`)
    showPreview.value = false
    router.push(`/agents/${cloned.id}/edit`)
  } catch (err) {
    appStore.error('克隆失败')
  } finally {
    cloningId.value = null
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
  width: 16px;
  height: 16px;
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
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);

  &:hover {
    border-color: var(--accent-amber-soft);
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
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

  svg {
    width: 22px;
    height: 22px;
    color: #ffffff;
  }
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
  gap: $spacing-3;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.meta-icon {
  width: 12px;
  height: 12px;
}

.card-footer {
  display: flex;
  gap: $spacing-2;
  padding-top: $spacing-4;
  border-top: 1px solid var(--border-primary);

  :deep(.app-button) {
    flex: 1;
    justify-content: center;
  }
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: $spacing-8;
}

.preview-body {
  h4 {
    margin: 0 0 $spacing-2;
    font-size: $font-size-lg;
    color: var(--text-primary);
  }
}

.preview-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0 0 $spacing-4;
}

.preview-section {
  margin-bottom: $spacing-4;

  h5 {
    font-size: $font-size-xs;
    font-weight: $font-weight-medium;
    color: var(--text-tertiary);
    text-transform: uppercase;
    margin: 0 0 $spacing-2;
  }
}

.preview-prompt {
  font-family: inherit;
  font-size: $font-size-sm;
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: $spacing-3;
  border-radius: $radius-md;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}

.tools-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
}

.no-tools {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}
</style>
