<template>
  <div class="workflow-list">
    <div class="list-header">
      <div class="header-left">
        <h1 class="page-title">
          工作流
        </h1>
        <span class="workflow-count">{{ totalCount }} 个工作流</span>
      </div>
      <div class="header-actions">
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
      v-else-if="workflows.length === 0"
      class="empty-state"
    >
      <GitBranch class="empty-icon" />
      <h3>暂无工作流</h3>
      <p>创建您的第一个 AI 工作流</p>
      <router-link to="/workflows/new">
        <AppButton variant="primary">
          创建工作流
        </AppButton>
      </router-link>
    </div>

    <div
      v-else
      class="workflow-grid"
    >
      <div
        v-for="workflow in workflows"
        :key="workflow.id"
        class="workflow-card"
        @click="goToEditor(workflow.id)"
      >
        <div class="card-header">
          <MiniWorkflowPreview
            :nodes="workflow.nodesPreview"
            class="card-preview"
          />
          <el-dropdown
            trigger="click"
            @command="(cmd) => handleCommand(cmd, workflow)"
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
          <h3 class="workflow-name">
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
              {{ workflow.node_count || 0 }}
            </span>
            <span class="stat">
              <Play class="stat-icon" />
              {{ workflow.execution_count || 0 }}
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
          <span class="meta-time">{{ formatDate(workflow.updated_at) }}</span>
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
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Search, Plus, GitBranch, MoreVertical, Layers, Play } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import MiniWorkflowPreview from '@/components/workflow/MiniWorkflowPreview.vue'

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

.workflow-count {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
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
    color: var(--text-tertiary);
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

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-5;
}

.workflow-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  cursor: pointer;
  transition: all $transition-fast;
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
  min-height: 180px;

  &:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: $spacing-3;
}

.card-preview {
  width: 220px;
  height: 100px;
  flex-shrink: 0;
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
