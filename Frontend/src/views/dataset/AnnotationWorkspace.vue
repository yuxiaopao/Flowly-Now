<template>
  <div class="annotation-workspace">
    <!-- Top Bar -->
    <div class="workspace-header">
      <div class="header-left">
        <el-button
          :icon="ArrowLeft"
          text
          @click="goBack"
        >
          返回
        </el-button>
        <div class="project-info">
          <h1 class="project-name">
            {{ project?.name || '标注工作台' }}
          </h1>
          <div class="project-meta">
            <el-tag
              size="small"
              :type="getAnnotationTypeTag(project?.annotationType)"
            >
              {{ getAnnotationTypeLabel(project?.annotationType) }}
            </el-tag>
            <el-tag
              size="small"
              :type="getStatusTag(project?.status)"
            >
              {{ getStatusLabel(project?.status) }}
            </el-tag>
          </div>
        </div>
      </div>

      <div class="header-center">
        <div class="progress-info">
          <span class="progress-text">
            {{ project?.annotatedItems || 0 }} / {{ project?.totalItems || 0 }}
          </span>
          <span class="progress-label">已标注</span>
          <el-progress
            :percentage="project?.progressPercentage || 0"
            :stroke-width="8"
            :show-text="false"
            style="width: 200px"
          />
          <span class="progress-percentage">{{ project?.progressPercentage || 0 }}%</span>
        </div>
      </div>

      <div class="header-right">
        <el-button
          v-if="project?.modelAssisted"
          type="warning"
          :loading="preLabeling"
          @click="handleAutoLabel"
        >
          <Cpu class="btn-icon" />
          AI 自动标注
        </el-button>

        <el-dropdown @command="handleExport">
          <el-button type="default">
            <Download class="btn-icon" />
            导出
            <ChevronDown class="btn-icon" />
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="json">
                JSON 格式
              </el-dropdown-item>
              <el-dropdown-item command="csv">
                CSV 格式
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button
          type="primary"
          :disabled="!canComplete"
          @click="handleComplete"
        >
          <CheckCircle class="btn-icon" />
          完成标注
        </el-button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="workspace-main">
      <!-- Left Sidebar: Item List -->
      <div class="item-sidebar">
        <div class="sidebar-header">
          <div class="filter-tabs">
            <button
              v-for="tab in filterTabs"
              :key="tab.value"
              class="filter-tab"
              :class="{ active: activeFilter === tab.value }"
              @click="activeFilter = tab.value"
            >
              {{ tab.label }}
              <span class="tab-count">{{ getFilterCount(tab.value) }}</span>
            </button>
          </div>
        </div>

        <div
          ref="itemListRef"
          class="item-list"
        >
          <div
            v-if="loadingItems"
            class="loading-state"
          >
            <el-icon class="is-loading">
              <Loader />
            </el-icon>
            <span>加载中...</span>
          </div>

          <div
            v-else-if="filteredItems.length === 0"
            class="empty-state"
          >
            <Inbox class="empty-icon" />
            <span>暂无数据</span>
          </div>

          <div
            v-for="(item, index) in filteredItems"
            v-else
            :key="item.id"
            class="item-card"
            :class="{
              active: currentItem?.id === item.id,
              annotated: item.status === 'annotated',
              skipped: item.status === 'skipped'
            }"
            @click="selectItem(item)"
          >
            <div class="item-index">
              {{ index + 1 + (currentPage - 1) * pageSize }}
            </div>
            <div class="item-content">
              <div class="item-preview">
                {{ getItemPreview(item) }}
              </div>
              <div class="item-badges">
                <span
                  v-if="item.preLabel"
                  class="pre-label-badge"
                  :style="{ backgroundColor: getLabelBgColor(item.preLabel), color: getLabelColor(item.preLabel) }"
                >
                  AI: {{ item.preLabel }}
                </span>
                <span
                  v-if="item.label"
                  class="label-badge"
                  :style="{ backgroundColor: getLabelBgColor(item.label), color: getLabelColor(item.label) }"
                >
                  {{ item.label }}
                </span>
              </div>
            </div>
            <div class="item-status">
              <el-tag
                v-if="item.status === 'annotated'"
                size="small"
                type="success"
              >
                已标
              </el-tag>
              <el-tag
                v-else-if="item.status === 'skipped'"
                size="small"
                type="info"
              >
                跳过
              </el-tag>
              <el-tag
                v-else
                size="small"
                type="warning"
              >
                待标
              </el-tag>
            </div>
          </div>
        </div>

        <div class="sidebar-footer">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="totalItems"
            layout="prev, pager, next"
            small
            @current-change="loadItems"
          />
        </div>
      </div>

      <!-- Center: Data Viewer -->
      <div class="data-viewer">
        <div
          v-if="!currentItem"
          class="viewer-empty"
        >
          <Tag class="empty-icon" />
          <span>选择左侧条目开始标注</span>
        </div>

        <div
          v-else
          class="viewer-content"
        >
          <div class="viewer-header">
            <span class="item-id">#{{ currentItem.dataId }}</span>
            <span class="item-index">第 {{ getCurrentItemIndex() }} / {{ totalItems }} 条</span>
          </div>

          <div class="data-content">
            <div class="content-section">
              <h4 class="section-title">
                数据内容
              </h4>
              <div class="text-content">
                <pre>{{ formatDataContent(currentItem.dataContent) }}</pre>
              </div>
            </div>

            <div
              v-if="currentItem.preLabel"
              class="content-section"
            >
              <h4 class="section-title">
                AI 预标注
                <el-tag
                  size="small"
                  type="warning"
                >
                  可修正
                </el-tag>
              </h4>
              <div
                class="pre-label-box"
                :style="{
                  borderColor: getLabelColor(currentItem.preLabel),
                  backgroundColor: getLabelBgColor(currentItem.preLabel)
                }"
              >
                {{ currentItem.preLabel }}
              </div>
            </div>
          </div>

          <div class="navigation-buttons">
            <el-button
              :disabled="!hasPrevious"
              @click="navigatePrevious"
            >
              <ArrowLeft class="btn-icon" />
              上一条
            </el-button>
            <el-button
              :disabled="!hasNext"
              @click="navigateNext"
            >
              下一条
              <ArrowRight class="btn-icon" />
            </el-button>
          </div>
        </div>
      </div>

      <!-- Right Sidebar: Label Panel -->
      <div class="label-panel">
        <div class="panel-section">
          <h4 class="panel-title">
            选择标签
          </h4>
          <div class="label-buttons">
            <button
              v-for="(label, index) in projectLabels"
              :key="label"
              class="label-button"
              :class="{ active: selectedLabel === label }"
              :style="{
                '--label-color': getLabelColor(label),
                '--label-bg': getLabelBgColor(label)
              }"
              @click="assignLabel(label)"
            >
              <span class="label-color-dot" />
              <span class="label-name">{{ label }}</span>
              <span class="label-shortcut">{{ index + 1 }}</span>
            </button>
          </div>
        </div>

        <div class="panel-section">
          <h4 class="panel-title">
            操作
          </h4>
          <div class="action-buttons">
            <el-button
              class="skip-button"
              :type="selectedLabel === '__skip__' ? 'warning' : 'default'"
              @click="skipItem"
            >
              <SkipForward class="btn-icon" />
              跳过此条
            </el-button>
            <el-button
              class="clear-button"
              type="danger"
              text
              @click="clearAnnotation"
            >
              <Trash2 class="btn-icon" />
              清除标注
            </el-button>
          </div>
        </div>

        <div class="panel-section">
          <h4 class="panel-title">
            快捷键
          </h4>
          <div class="shortcut-hints">
            <div class="shortcut-item">
              <kbd>1-9</kbd>
              <span>选择标签</span>
            </div>
            <div class="shortcut-item">
              <kbd>←</kbd>
              <kbd>→</kbd>
              <span>导航条目</span>
            </div>
            <div class="shortcut-item">
              <kbd>Enter</kbd>
              <span>确认标注</span>
            </div>
            <div class="shortcut-item">
              <kbd>S</kbd>
              <span>跳过</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pre-label Progress Dialog -->
    <el-dialog
      v-model="showPreLabelDialog"
      title="AI 自动标注"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="pre-label-dialog-content">
        <el-progress
          type="circle"
          :percentage="preLabelProgress"
          :status="preLabelProgress === 100 ? 'success' : undefined"
        />
        <p class="pre-label-status">
          {{ preLabelStatus }}
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, ArrowRight, Download, ChevronDown, CheckCircle,
  Cpu, Loader, Inbox, Tag, SkipForward, Trash2
} from 'lucide-vue-next'
import { annotationApi, getLabelColor, getLabelBgColor } from '@/api/annotation'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => route.params.id)

const project = ref(null)
const items = ref([])
const currentItem = ref(null)
const selectedLabel = ref(null)

const loadingProject = ref(false)
const loadingItems = ref(false)
const preLabeling = ref(false)
const showPreLabelDialog = ref(false)
const preLabelProgress = ref(0)
const preLabelStatus = ref('正在处理...')

const activeFilter = ref('all')
const currentPage = ref(1)
const pageSize = ref(20)
const totalItems = ref(0)

const filterTabs = [
  { label: '全部', value: 'all' },
  { label: '待标注', value: 'pending' },
  { label: '已标注', value: 'annotated' },
  { label: '已跳过', value: 'skipped' }
]

const itemListRef = ref(null)

const projectLabels = computed(() => {
  if (!project.value?.labels) return []
  if (Array.isArray(project.value.labels)) return project.value.labels
  try {
    return JSON.parse(project.value.labels)
  } catch {
    return []
  }
})

const filteredItems = computed(() => {
  if (activeFilter.value === 'all') return items.value
  return items.value.filter(item => item.status === activeFilter.value)
})

const hasPrevious = computed(() => {
  const currentIndex = items.value.findIndex(i => i.id === currentItem.value?.id)
  return currentIndex > 0 || currentPage.value > 1
})

const hasNext = computed(() => {
  const currentIndex = items.value.findIndex(i => i.id === currentItem.value?.id)
  return currentIndex < items.value.length - 1 || currentPage.value < Math.ceil(totalItems.value / pageSize.value)
})

const canComplete = computed(() => {
  return project.value?.status !== 'completed' && (project.value?.annotatedItems || 0) > 0
})

function getFilterCount(filter) {
  if (!project.value) return 0
  const stats = project.value.itemsStats || {}
  if (filter === 'all') {
    return stats.total || totalItems.value
  }
  return stats[filter] || 0
}

function getItemPreview(item) {
  if (!item.dataContent) return ''
  const content = item.dataContent
  if (typeof content === 'string') return content.slice(0, 50)
  if (content.text) return content.text.slice(0, 50)
  if (content.content) return content.content.slice(0, 50)

  const firstKey = Object.keys(content)[0]
  if (firstKey && content[firstKey]) {
    return String(content[firstKey]).slice(0, 50)
  }
  return JSON.stringify(content).slice(0, 50)
}

function getCurrentItemIndex() {
  const idx = items.value.findIndex(i => i.id === currentItem.value?.id)
  if (idx >= 0) {
    return (currentPage.value - 1) * pageSize.value + idx + 1
  }
  return 0
}

function formatDataContent(content) {
  if (!content) return ''
  if (typeof content === 'string') return content
  if (typeof content === 'object') {
    return JSON.stringify(content, null, 2)
  }
  return String(content)
}

function getAnnotationTypeLabel(type) {
  const labels = {
    classification: '分类',
    ner: '命名实体识别',
    sentiment: '情感分析',
    detection: '目标检测'
  }
  return labels[type] || type
}

function getAnnotationTypeTag(type) {
  const tags = {
    classification: '',
    ner: 'success',
    sentiment: 'warning',
    detection: 'danger'
  }
  return tags[type] || ''
}

function getStatusLabel(status) {
  const labels = {
    draft: '草稿',
    in_progress: '进行中',
    completed: '已完成'
  }
  return labels[status] || status
}

function getStatusTag(status) {
  const tags = {
    draft: 'info',
    in_progress: 'warning',
    completed: 'success'
  }
  return tags[status] || ''
}

function goBack() {
  router.push('/dataset-recommend')
}

async function loadProject() {
  if (!projectId.value) return

  loadingProject.value = true
  try {
    project.value = await annotationApi.get(projectId.value)
  } catch (error) {
    console.error('Failed to load project:', error)
    ElMessage.error('加载项目失败')
  } finally {
    loadingProject.value = false
  }
}

async function loadItems() {
  if (!projectId.value) return

  loadingItems.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (activeFilter.value !== 'all') {
      params.status = activeFilter.value
    }

    const response = await annotationApi.getItems(projectId.value, params)

    items.value = response.items || response.results || []
    totalItems.value = response.total || response.count || 0

    if (items.value.length > 0 && !currentItem.value) {
      selectItem(items.value[0])
    }
  } catch (error) {
    console.error('Failed to load items:', error)
    ElMessage.error('加载标注项失败')
  } finally {
    loadingItems.value = false
  }
}

function selectItem(item) {
  currentItem.value = item
  selectedLabel.value = item.label || null
}

async function assignLabel(label) {
  if (!currentItem.value) return

  selectedLabel.value = label

  try {
    await annotationApi.updateItem(currentItem.value.id, {
      label: label,
      status: 'annotated'
    })

    currentItem.value.label = label
    currentItem.value.status = 'annotated'

    if (project.value) {
      project.value.annotatedItems = (project.value.annotatedItems || 0) + 1
      project.value.itemsStats = {
        ...project.value.itemsStats,
        pending: (project.value.itemsStats?.pending || 1) - 1,
        annotated: (project.value.itemsStats?.annotated || 0) + 1
      }
    }

    ElMessage.success('标注成功')

    await nextTick()
    navigateNext()
  } catch (error) {
    console.error('Failed to assign label:', error)
    ElMessage.error('标注失败')
  }
}

async function skipItem() {
  if (!currentItem.value) return

  try {
    await annotationApi.updateItem(currentItem.value.id, {
      status: 'skipped'
    })

    currentItem.value.status = 'skipped'
    currentItem.value.label = ''

    if (project.value) {
      project.value.itemsStats = {
        ...project.value.itemsStats,
        pending: (project.value.itemsStats?.pending || 1) - 1,
        skipped: (project.value.itemsStats?.skipped || 0) + 1
      }
    }

    ElMessage.info('已跳过')

    await nextTick()
    navigateNext()
  } catch (error) {
    console.error('Failed to skip item:', error)
    ElMessage.error('操作失败')
  }
}

async function clearAnnotation() {
  if (!currentItem.value) return

  try {
    await ElMessageBox.confirm('确定要清除此标注吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await annotationApi.updateItem(currentItem.value.id, {
      label: '',
      status: 'pending'
    })

    currentItem.value.label = ''
    currentItem.value.status = 'pending'

    if (project.value && currentItem.value.status === 'annotated') {
      project.value.annotatedItems = Math.max(0, (project.value.annotatedItems || 1) - 1)
      project.value.itemsStats = {
        ...project.value.itemsStats,
        pending: (project.value.itemsStats?.pending || 0) + 1,
        annotated: Math.max(0, (project.value.itemsStats?.annotated || 1) - 1)
      }
    }

    selectedLabel.value = null
    ElMessage.success('已清除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to clear annotation:', error)
      ElMessage.error('操作失败')
    }
  }
}

function navigatePrevious() {
  const currentIndex = items.value.findIndex(i => i.id === currentItem.value?.id)
  if (currentIndex > 0) {
    selectItem(items.value[currentIndex - 1])
  } else if (currentPage.value > 1) {
    currentPage.value--
    loadItems().then(() => {
      selectItem(items.value[items.value.length - 1])
    })
  }
}

function navigateNext() {
  const currentIndex = items.value.findIndex(i => i.id === currentItem.value?.id)
  if (currentIndex < items.value.length - 1) {
    selectItem(items.value[currentIndex + 1])
  } else if (currentPage.value < Math.ceil(totalItems.value / pageSize.value)) {
    currentPage.value++
    loadItems().then(() => {
      selectItem(items.value[0])
    })
  }
}

async function handleAutoLabel() {
  try {
    await ElMessageBox.confirm(
      'AI 将自动为所有待标注项生成预标签。这可能需要一些时间。',
      '确认 AI 自动标注',
      {
        confirmButtonText: '开始',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    showPreLabelDialog.value = true
    preLabelProgress.value = 0
    preLabeling.value = true

    const result = await annotationApi.preLabel(projectId.value)

    if (result.processed !== undefined) {
      preLabelProgress.value = 100
      preLabelStatus.value = `已完成！处理了 ${result.processed} 条数据`

      setTimeout(() => {
        showPreLabelDialog.value = false
        ElMessage.success(`AI 自动标注完成，已处理 ${result.processed} 条数据`)
        loadItems()
      }, 1000)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Pre-labeling error:', error)
      ElMessage.error('AI 自动标注失败')
    }
    showPreLabelDialog.value = false
  } finally {
    preLabeling.value = false
  }
}

async function handleExport(format) {
  try {
    ElMessage.info(`正在导出 ${format.toUpperCase()} 格式...`)

    const response = await annotationApi.export(projectId.value, format)

    const blob = new Blob([response], {
      type: format === 'csv' ? 'text/csv' : 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `annotations_${projectId.value}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export error:', error)
    ElMessage.error('导出失败')
  }
}

async function handleComplete() {
  try {
    await ElMessageBox.confirm(
      '完成标注后将无法继续修改。确定要完成吗？',
      '确认完成标注',
      {
        confirmButtonText: '完成',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await annotationApi.complete(projectId.value)

    project.value.status = 'completed'
    ElMessage.success('标注项目已完成')

    router.push('/dataset-recommend')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Complete error:', error)
      ElMessage.error('完成标注失败')
    }
  }
}

function handleKeyboard(event) {
  if (!currentItem.value) return

  const key = event.key

  if (key >= '1' && key <= '9') {
    const index = parseInt(key) - 1
    if (index < projectLabels.value.length) {
      assignLabel(projectLabels.value[index])
    }
  } else if (key === 'ArrowLeft') {
    event.preventDefault()
    navigatePrevious()
  } else if (key === 'ArrowRight') {
    event.preventDefault()
    navigateNext()
  } else if (key === 's' || key === 'S') {
    event.preventDefault()
    skipItem()
  } else if (key === 'Enter' && selectedLabel.value) {
    event.preventDefault()
    assignLabel(selectedLabel.value)
  }
}

watch(activeFilter, () => {
  currentPage.value = 1
  loadItems()
})

onMounted(() => {
  loadProject()
  loadItems()
  document.addEventListener('keydown', handleKeyboard)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboard)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.annotation-workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-4 $spacing-6;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-4;
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.project-name {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  margin: 0;
  color: var(--text-primary);
}

.project-meta {
  display: flex;
  gap: $spacing-2;
}

.header-center {
  display: flex;
  align-items: center;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.progress-text {
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
}

.progress-label {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.progress-percentage {
  font-size: $font-size-sm;
  color: var(--color-primary);
  font-weight: $font-weight-medium;
  min-width: 40px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: $spacing-1;
}

.workspace-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.item-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.sidebar-header {
  padding: $spacing-3;
  border-bottom: 1px solid var(--border-primary);
}

.filter-tabs {
  display: flex;
  gap: $spacing-1;
}

.filter-tab {
  flex: 1;
  padding: $spacing-2;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: $font-size-xs;
  cursor: pointer;
  border-radius: $radius-md;
  transition: all $transition-fast;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: var(--color-primary-light-9);
    color: var(--color-primary);
  }

  .tab-count {
    font-size: 10px;
    opacity: 0.7;
  }
}

.item-list {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-2;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-8;
  color: var(--text-tertiary);
  gap: $spacing-2;
}

.empty-icon {
  width: 32px;
  height: 32px;
  opacity: 0.5;
}

.item-card {
  display: flex;
  align-items: flex-start;
  gap: $spacing-2;
  padding: $spacing-3;
  margin-bottom: $spacing-2;
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: $radius-md;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--border-primary);
  }

  &.active {
    background: var(--color-primary-light-9);
    border-color: var(--color-primary);
  }

  &.annotated {
    border-left: 3px solid var(--color-success);
  }

  &.skipped {
    opacity: 0.6;
  }
}

.item-index {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  min-width: 24px;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-preview {
  font-size: $font-size-sm;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: $spacing-1;
}

.item-badges {
  display: flex;
  gap: $spacing-1;
  flex-wrap: wrap;
}

.pre-label-badge,
.label-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: $radius-sm;
  font-weight: $font-weight-medium;
}

.item-status {
  flex-shrink: 0;
}

.sidebar-footer {
  padding: $spacing-3;
  border-top: 1px solid var(--border-primary);
  display: flex;
  justify-content: center;
}

.data-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-primary);
}

.viewer-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  gap: $spacing-3;

  .empty-icon {
    width: 48px;
    height: 48px;
    opacity: 0.3;
  }
}

.viewer-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: $spacing-6;
  overflow-y: auto;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-4;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);
}

.item-id {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
  font-family: 'Fira Code', monospace;
}

.item-index {
  font-size: $font-size-sm;
  color: var(--text-secondary);
}

.data-content {
  flex: 1;
}

.content-section {
  margin-bottom: $spacing-6;
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-secondary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.text-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-4;

  pre {
    margin: 0;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.pre-label-box {
  padding: $spacing-3 $spacing-4;
  border: 2px solid;
  border-radius: $radius-lg;
  font-weight: $font-weight-medium;
  text-align: center;
}

.navigation-buttons {
  display: flex;
  justify-content: center;
  gap: $spacing-4;
  padding-top: $spacing-6;
  border-top: 1px solid var(--border-primary);
  margin-top: auto;
}

.label-panel {
  width: 240px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  flex-shrink: 0;
  padding: $spacing-4;
}

.panel-section {
  margin-bottom: $spacing-6;
}

.panel-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-secondary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.label-buttons {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.label-button {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  cursor: pointer;
  transition: all $transition-fast;
  color: var(--text-primary);

  &:hover {
    background: var(--label-bg);
    border-color: var(--label-color);
  }

  &.active {
    background: var(--label-bg);
    border-color: var(--label-color);
    box-shadow: 0 0 0 2px var(--label-color);
  }

  .label-color-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--label-color);
    flex-shrink: 0;
  }

  .label-name {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    text-align: left;
  }

  .label-shortcut {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
    background: var(--bg-hover);
    padding: 2px 6px;
    border-radius: $radius-sm;
  }
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.shortcut-hints {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  kbd {
    display: inline-block;
    padding: 2px 6px;
    font-family: 'Fira Code', monospace;
    font-size: 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-sm;
  }
}

.pre-label-dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: $spacing-6;
  gap: $spacing-4;
}

.pre-label-status {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0;
}

@media (max-width: 1024px) {
  .label-panel {
    width: 200px;
  }

  .item-sidebar {
    width: 240px;
  }
}

@media (max-width: 768px) {
  .workspace-header {
    flex-wrap: wrap;
    gap: $spacing-3;
  }

  .header-center {
    order: 3;
    width: 100%;
    justify-content: center;
  }

  .workspace-main {
    flex-direction: column;
  }

  .item-sidebar,
  .label-panel {
    width: 100%;
    max-height: 200px;
  }

  .label-buttons {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .label-button {
    flex: 1;
    min-width: 80px;
  }
}
</style>
