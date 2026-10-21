<template>
  <PageShell width="wide">
    <PageHeader
      title="工作流"
      :meta="`${totalCount} 个工作流`"
      subtitle="编排自动化流程，跟踪状态与最近更新。"
    >
      <template #actions>
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

    <PageToolbar
      role="search"
      aria-label="筛选工作流"
    >
      <el-input
        v-model="searchQuery"
        placeholder="搜索工作流..."
        :prefix-icon="Search"
        clearable
        aria-label="搜索工作流"
        class="search-input"
        @input="handleSearch"
      />
      <el-select
        v-model="statusFilter"
        placeholder="状态"
        clearable
        aria-label="工作流状态"
        class="status-select"
        @change="handleFilterChange"
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
      <el-select
        v-model="ordering"
        aria-label="工作流排序"
        class="sort-select"
        @change="handleFilterChange"
      >
        <el-option
          label="最近更新"
          value="-updated_at"
        />
        <el-option
          label="最近创建"
          value="-created_at"
        />
        <el-option
          label="名称排序"
          value="name"
        />
      </el-select>
      
      <template #actions>
        <div
          class="view-switch"
          role="group"
          aria-label="工作流展示方式"
        >
          <button
            :class="{ active: viewMode === 'table' }"
            :aria-pressed="viewMode === 'table'"
            aria-label="列表视图"
            title="列表视图"
            @click="setViewMode('table')"
          >
            <ListIcon />
          </button>
          <button
            :class="{ active: viewMode === 'grid' }"
            :aria-pressed="viewMode === 'grid'"
            aria-label="画布卡片视图"
            title="画布卡片视图"
            @click="setViewMode('grid')"
          >
            <LayoutGrid />
          </button>
        </div>
      </template>
    </PageToolbar>

    <div
      v-if="loadError"
      class="list-feedback"
      role="alert"
    >
      <span>{{ loadError }}</span>
      <AppButton
        variant="secondary"
        size="small"
        :loading="isLoading"
        @click="fetchWorkflows"
      >
        重新加载
      </AppButton>
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

    <PageEmptyState
      v-else-if="workflows.length === 0 && !loadError"
      :icon="GitBranch"
      :title="hasFilters ? '没有匹配的工作流' : '暂无工作流'"
      :description="hasFilters ? '调整关键词或状态筛选后再试。' : '创建您的第一个 AI 工作流，开始编排自动化任务。'"
    >
      <template #actions>
        <AppButton
          v-if="hasFilters"
          variant="secondary"
          @click="clearFilters"
        >
          清除筛选
        </AppButton>
        <router-link
          v-else
          to="/workflows/new"
        >
          <AppButton variant="primary">
            创建工作流
          </AppButton>
        </router-link>
      </template>
    </PageEmptyState>

    <div
      v-else-if="viewMode === 'table' && workflows.length"
      class="workflow-table"
    >
      <el-table
        :data="workflows"
        row-key="id"
        aria-label="工作流列表"
      >
        <el-table-column
          label="工作流名称"
          min-width="300"
        >
          <template #default="{ row }">
            <div class="table-name">
              <GitBranch
                class="table-workflow-icon"
                aria-hidden="true"
              />
              <div class="table-name-copy">
                <router-link
                  :to="`/workflows/${row.id}`"
                  :title="row.name"
                >
                  {{ row.name }}
                </router-link>
                <span :title="row.description">{{ row.description || '暂无描述' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="90"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
            >
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="节点"
          width="70"
          align="right"
        >
          <template #default="{ row }">
            {{ resolveNodeCount(row) }}
          </template>
        </el-table-column>
        <el-table-column
          label="执行"
          width="70"
          align="right"
        >
          <template #default="{ row }">
            {{ resolveExecutionCount(row) }}
          </template>
        </el-table-column>
        <el-table-column
          label="最近更新"
          width="150"
        >
          <template #default="{ row }">
            <span class="table-date">{{ formatDate(row.updatedAt || row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="120"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              text
              size="small"
              @click="goToEditor(row.id)"
            >
              编辑
            </el-button>
            <el-dropdown
              trigger="click"
              @command="command => handleCommand(command, row)"
            >
              <el-button
                text
                size="small"
                :aria-label="`${row.name}的更多操作`"
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
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div
      v-else-if="workflows.length"
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
              :aria-label="`${workflow.name}的更多操作`"
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
            :title="workflow.name"
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
              {{ resolveNodeCount(workflow) }}
            </span>
            <span class="stat">
              <Play class="stat-icon" />
              {{ resolveExecutionCount(workflow) }}
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
      v-if="totalCount > pageSize"
      class="pagination"
    >
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalCount"
        :page-sizes="PRODUCT_UI.workflowPageSizes"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>
  </PageShell>
</template>

<script setup>
import PageToolbar from '@/components/layout/PageToolbar.vue'
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import { ElMessageBox } from 'element-plus'
import { Search, Plus, GitBranch, MoreVertical, Layers, Play, List as ListIcon, LayoutGrid } from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageEmptyState from '@/components/layout/PageEmptyState.vue'
import WorkflowCardPreview from '@/components/workflow/WorkflowCardPreview.vue'
import { APP_CONFIG } from '@/config'
import { PRODUCT_UI } from '@/config/productUi'
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
const pageSize = ref(APP_CONFIG.pagination.marketplace || APP_CONFIG.pagination.default || 24)
const ordering = ref('-updated_at')
const loadError = ref('')
const storedView = localStorage.getItem(PRODUCT_UI.workflowViewStorageKey)
const viewMode = ref(PRODUCT_UI.workflowViews.includes(storedView) ? storedView : PRODUCT_UI.workflowDefaultView)
const hasFilters = computed(() => Boolean(searchQuery.value || statusFilter.value))
let searchTimer
let listRequestId = 0

function setViewMode(mode) {
  if (!PRODUCT_UI.workflowViews.includes(mode)) return
  viewMode.value = mode
  localStorage.setItem(PRODUCT_UI.workflowViewStorageKey, mode)
}

onBeforeUnmount(() => clearTimeout(searchTimer))

const workflows = computed(() => workflowStore.workflows)
const isLoading = computed(() => workflowStore.isLoading)
const totalCount = computed(() => workflowStore.totalCount || 0)

onMounted(() => {
  fetchWorkflows()
})

async function fetchWorkflows() {
  const requestId = ++listRequestId
  clearTimeout(searchTimer)
  loadError.value = ''
  try {
    await workflowStore.fetchWorkflows({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value,
      ordering: ordering.value,
    })
  } catch (err) {
    if (requestId === listRequestId) loadError.value = '工作流加载失败，请检查连接后重试。'
  }
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(handleFilterChange, PRODUCT_UI.searchDebounceMs)
}

function handleFilterChange() {
  currentPage.value = 1
  fetchWorkflows()
}

function clearFilters() {
  searchQuery.value = ''
  statusFilter.value = ''
  handleFilterChange()
}

function handlePageChange(page) {
  currentPage.value = page
  fetchWorkflows()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
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

function resolveNodeCount(workflow) {
  const fromField = workflow?.nodeCount ?? workflow?.node_count
  if (fromField != null && fromField !== '') return Number(fromField) || 0
  const preview = resolvePreviewNodes(workflow)
  return Array.isArray(preview) ? preview.length : 0
}

function resolveExecutionCount(workflow) {
  const fromField = workflow?.executionCount ?? workflow?.execution_count
  return Number(fromField) || 0
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
      goToEditor(workflow.id)
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

.view-switch {
  display: flex; padding: $spacing-1; gap: $spacing-1; border: 1px solid var(--border-primary);
  border-radius: $radius-lg; background: var(--bg-secondary);
  button { display: grid; place-items: center; width: var(--control-height-small); height: var(--control-height-small); border-radius: $radius-md; color: var(--text-tertiary); svg { width: $spacing-4; height: $spacing-4; } &:hover, &.active { background: var(--bg-hover); color: var(--text-primary); } }
}
.list-feedback { display: flex; align-items: center; justify-content: space-between; gap: $spacing-3; padding: $spacing-3 $spacing-4; background: var(--error-bg); color: var(--text-secondary); border-radius: $radius-lg; margin-bottom: $spacing-4; font-size: $font-size-sm; }
.loading-container { padding: $spacing-6; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius-card); }
.workflow-table { border: 1px solid var(--border-primary); border-radius: var(--radius-card); overflow: hidden; }
.table-name { display: flex; align-items: center; gap: $spacing-3; min-width: 0; }
.table-workflow-icon { width: $spacing-8; height: $spacing-8; padding: $spacing-2; border: 1px solid var(--border-primary); border-radius: $radius-lg; color: var(--text-secondary); flex-shrink: 0; }
.table-name-copy { display: flex; flex-direction: column; min-width: 0; gap: $spacing-1;
  a { font-weight: $font-weight-medium; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; &:hover { text-decoration: underline; opacity: 1; } }
  span { color: var(--text-tertiary); font-size: $font-size-xs; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
}
.table-date { color: var(--text-secondary); font-size: $font-size-xs; }
.workflow-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr)); gap: $spacing-4; }
.workflow-card {
  position: relative; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--content-card-radius);
  padding: var(--content-card-padding); cursor: pointer; display: flex; flex-direction: column; gap: $spacing-3; overflow: hidden;
  transition: border-color $transition-fast; &:hover { border-color: var(--border-hover); }
}
.card-preview-wrap { position: relative; width: 100%; }
.card-menu { position: absolute; top: $spacing-1; right: $spacing-1; z-index: 2; }
.card-menu-btn { background: var(--bg-secondary); border: 1px solid var(--border-primary); }
.card-body { flex: 1; min-width: 0; }
.workflow-name { font-size: $font-size-sm; font-weight: $font-weight-semibold; color: var(--text-primary); margin: 0 0 $spacing-2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; &:hover { text-decoration: underline; } }
.workflow-desc { font-size: $font-size-xs; line-height: $line-height-normal; color: var(--text-secondary); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; min-height: $spacing-8; }
.card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: $spacing-3; border-top: 1px solid var(--border-primary); }
.card-stats { display: flex; gap: $spacing-4; }
.stat { display: flex; align-items: center; gap: $spacing-1; color: var(--text-secondary); font-size: $font-size-xs; .stat-icon { width: $spacing-3; height: $spacing-3; } }
.meta-time { font-size: $font-size-xs; color: var(--text-tertiary); }
.pagination { display: flex; justify-content: flex-end; margin-top: $spacing-5; }
@media (max-width: 768px) {

  .view-switch { button { width: var(--control-height-large); height: var(--control-height-large); } }
  .list-feedback { flex-direction: column; align-items: flex-start; }
  .pagination { justify-content: center; }
}
</style>
