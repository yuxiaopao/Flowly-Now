<template>
  <PageShell width="wide">
    <PageHeader
      title="工作流"
      :meta="`${totalCount} 个工作流`"
    >
      <template #actions>
        <el-input
          v-model="searchQuery"
          placeholder="搜索工作流..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          class="status-select"
          @change="fetchWorkflows"
        >
          <el-option
            label="草稿"
            value="draft"
          />
          <el-option
            label="活跃"
            value="active"
          />
          <el-option
            label="已暂停"
            value="paused"
          />
          <el-option
            label="已归档"
            value="archived"
          />
        </el-select>
        <router-link to="/workflows/new">
          <AppButton
            variant="primary"
            :icon="Plus"
          >
            新建工作流
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
      v-else-if="workflows.length === 0"
      :icon="GitBranch"
      title="暂无工作流"
      description="创建您的第一个 AI 工作流，开始编排自动化任务。"
    >
      <template #actions>
        <router-link to="/workflows/new">
          <AppButton variant="primary">
            创建工作流
          </AppButton>
        </router-link>
      </template>
    </PageEmptyState>

    <div
      v-else
      class="workflow-grid"
    >
      <div
        v-for="workflow in workflows"
        :key="workflow.id"
        class="workflow-card"
        @click="goToDetail(workflow.id)"
      >
        <div class="card-preview-wrap">
          <WorkflowCardPreview
            :canvas-preview="resolveCanvasPreview(workflow)"
            :nodes="resolvePreviewNodes(workflow)"
            :edges="resolvePreviewEdges(workflow)"
          />
          <el-dropdown
            trigger="click"
            class="card-menu"
            @command="(cmd) => handleCommand(cmd, workflow)"
          >
            <el-button
              text
              circle
              class="card-menu-btn"
              @click.stop
            >
              <MoreVertical />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  编辑
                </el-dropdown-item>
                <el-dropdown-item command="duplicate">
                  复制
                </el-dropdown-item>
                <el-dropdown-item command="execute">
                  执行
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
          <h3
            class="workflow-name"
            role="link"
            tabindex="0"
            @click.stop="goToDetail(workflow.id)"
            @keydown.enter.stop="goToDetail(workflow.id)"
          >
            {{ workflow.name }}
          </h3>
          <p class="workflow-desc">
            {{ workflow.description || '暂无描述' }}
          </p>
        </div>

        <div class="card-footer">
          <div class="card-stats">
            <span class="stat">
              <Layers class="stat-icon" />
              {{ workflow.nodeCount || workflow.node_count || 0 }}
            </span>
            <span class="stat">
              <Play class="stat-icon" />
              {{ workflow.executionCount || workflow.execution_count || 0 }}
            </span>
          </div>
          <el-tag
            :type="getStatusType(workflow.status)"
            size="small"
          >
            {{ getStatusLabel(workflow.status) }}
          </el-tag>
        </div>

        <div class="card-meta">
          <span class="meta-time">{{ formatDate(workflow.updatedAt || workflow.updated_at) }}</span>
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
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import { ElMessageBox } from 'element-plus'
import { Search, Plus, GitBranch, MoreVertical, Layers, Play } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageEmptyState from '@/components/layout/PageEmptyState.vue'
import WorkflowCardPreview from '@/components/workflow/WorkflowCardPreview.vue'
import {
  resolveWorkflowCanvasPreview,
  resolveWorkflowPreviewNodes,
  resolveWorkflowPreviewEdges,
} from '@/utils/workflowPreview'

const router = useRouter()
const workflowStore = useWorkflowStore()
const appStore = useAppStore()

const searchQuery = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(12)

const workflows = computed(() => workflowStore.workflows)
const isLoading = computed(() => workflowStore.isLoading)
const totalCount = computed(() => workflows.value.length)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

onMounted(() => {
  fetchWorkflows()
})

async function fetchWorkflows() {
  try {
    await workflowStore.fetchWorkflows({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value
    })
  } catch (err) {
    appStore.error('获取工作流列表失败')
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchWorkflows()
}

function handlePageChange(page) {
  currentPage.value = page
  fetchWorkflows()
}

function resolveCanvasPreview(workflow) {
  return resolveWorkflowCanvasPreview(workflow)
}

function resolvePreviewNodes(workflow) {
  return resolveWorkflowPreviewNodes(workflow)
}

function resolvePreviewEdges(workflow) {
  return resolveWorkflowPreviewEdges(workflow)
}

function goToDetail(id) {
  router.push(`/workflows/${id}`)
}

function goToEditor(id) {
  router.push(`/workflows/${id}/edit`)
}

async function handleCommand(command, workflow) {
  switch (command) {
    case 'edit':
      goToEditor(workflow.id)
      break
    case 'duplicate':
      await duplicateWorkflow(workflow.id)
      break
    case 'execute':
      router.push(`/workflows/${workflow.id}/execute`)
      break
    case 'delete':
      await deleteWorkflow(workflow.id)
      break
  }
}

async function duplicateWorkflow(id) {
  try {
    await workflowStore.duplicateWorkflow(id)
    appStore.success('工作流复制成功')
    fetchWorkflows()
  } catch (err) {
    appStore.error('复制失败')
  }
}

async function deleteWorkflow(id) {
  try {
    await ElMessageBox.confirm('确定要删除此工作流吗？此操作不可撤销。', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await workflowStore.deleteWorkflow(id)
    appStore.success('工作流已删除')
    fetchWorkflows()
  } catch (err) {
    if (err !== 'cancel') {
      appStore.error('删除失败')
    }
  }
}

function getStatusType(status) {
  const typeMap = {
    draft: 'info',
    active: 'success',
    paused: 'warning',
    archived: ''
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

.workflow-list {
  width: 100%;
}

.search-input {
  width: 220px;
}

.status-select {
  width: 120px;
}

.loading-container {
  padding: $spacing-6;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-5;
}

.workflow-card {
  position: relative;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  cursor: pointer;
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
  min-height: 180px;
  overflow: hidden;

  // 顶部全宽渐变描边，hover 时显现
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--border-gradient-brand);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    border-color: var(--accent-cyan-soft);
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);

    &::after {
      opacity: 1;
    }
  }
}

.card-preview-wrap {
  position: relative;
  width: 100%;
}

.card-menu {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 2;
}

.card-menu-btn {
  background: color-mix(in srgb, var(--bg-secondary) 82%, transparent);
  backdrop-filter: blur(6px);
  border: 1px solid var(--border-primary);
}

.card-body {
  flex: 1;
}

.workflow-name {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;

  &:hover {
    color: var(--el-color-primary);
    text-decoration: underline;
  }
}

.workflow-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 40px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: $spacing-4;
  border-top: 1px solid var(--border-primary);
}

.card-stats {
  display: flex;
  gap: $spacing-4;
}

.stat {
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-secondary);

  .stat-icon {
    width: 14px;
    height: 14px;
  }
}

.card-meta {
  margin-top: $spacing-3;
}

.meta-time {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: $spacing-8;
}

@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
    gap: $spacing-4;

    .header-actions {
      flex-wrap: wrap;
    }
  }

  .workflow-card {
    .card-content {
      flex-direction: column;
    }

    .card-description {
      -webkit-line-clamp: 1;
      line-clamp: 1;
    }

    .card-footer {
      flex-direction: column;
      align-items: flex-start;
      gap: $spacing-2;
    }
  }
}

@media (max-width: 480px) {
  .list-header {
    .search-input {
      width: 100%;
    }
  }

  .workflow-grid {
    grid-template-columns: 1fr;
  }
}
</style>
