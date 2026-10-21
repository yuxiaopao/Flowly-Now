<template>
  <div
    class="codegraph-shell"
    @keydown.esc="closePanels"
  >
    <header class="codegraph-header cg-panel">
      <div class="header-left">
        <div class="brand-block">
          <div
            class="brand-orb"
            aria-hidden="true"
          />
          <div class="brand-text">
            <h1 class="page-title">
              <span class="cg-glow-text">代码图谱</span>
            </h1>
            <p class="page-sub">
              查看依赖关系与代码结构
            </p>
          </div>
        </div>

        <div class="project-selector">
          <el-select
            v-model="selectedProjectId"
            placeholder="选择项目"
            aria-label="选择代码图谱项目"
            :loading="store.loading"
            filterable
            @change="handleProjectChange"
          >
            <el-option
              v-for="project in store.projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            >
              <div class="project-option">
                <span>{{ project.name }}</span>
                <el-tag
                  v-if="!isProjectValid(project)"
                  type="warning"
                  size="small"
                >
                  路径无效
                </el-tag>
                <el-tag
                  v-else
                  type="success"
                  size="small"
                  effect="plain"
                >
                  就绪
                </el-tag>
              </div>
            </el-option>
          </el-select>
          <div
            v-if="currentProjectMeta"
            class="project-path"
            :class="{ invalid: !isProjectValid(currentProjectMeta) }"
            :title="currentProjectMeta.path"
          >
            {{ currentProjectMeta.path || '未配置路径' }}
          </div>
        </div>
      </div>

      <div class="header-right">
        <el-button
          class="explorer-toggle"
          :icon="PanelLeft"
          :aria-expanded="filesOpen"
          aria-controls="graph-explorer"
          @click="toggleFiles"
        >
          文件与筛选
        </el-button>
        <el-button
          class="insights-toggle"
          :icon="PanelRight"
          :aria-expanded="detailsOpen"
          aria-controls="graph-insights"
          @click="toggleDetails"
        >
          项目洞察
        </el-button>
        <span
          class="cg-chip"
          :class="store.wsConnected ? 'live' : 'offline'"
        >
          <span class="cg-dot" />
          {{ store.wsConnected ? '实时同步' : '手动刷新' }}
        </span>

        <el-button
          class="cg-btn-glow"
          :loading="store.analyzing"
          :disabled="!store.currentProject || store.loading || !isProjectValid(currentProjectMeta)"
          :icon="RotateCw"
          @click="handleRefresh"
        >
          {{ store.analyzing ? '分析中...' : '重新分析' }}
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      :closable="false"
      show-icon
    >
      <el-button
        size="small"
        :loading="store.loading"
        @click="handleRetry"
      >
        {{ CODE_GRAPH.messages.retry }}
      </el-button>
    </el-alert>

    <div class="codegraph-body">
      <button
        v-if="filesOpen || detailsOpen"
        class="panel-backdrop"
        aria-label="关闭侧栏"
        @click="closePanels"
      />
      <aside
        id="graph-explorer"
        ref="explorerRef"
        class="sidebar"
        :class="{ open: filesOpen }"
        aria-label="文件与筛选"
        :role="activePanel === explorerRef ? 'dialog' : undefined"
        :aria-modal="activePanel === explorerRef || undefined"
        @keydown="handlePanelKeydown"
      >
        <el-button
          class="panel-close files-close"
          :icon="X"
          @click="filesOpen = false"
        >
          关闭文件与筛选
        </el-button>
        <div class="cg-panel panel-block search-block">
          <SearchPanel @select="handleNodeSelect" />
          <div class="graph-filters">
            <el-select
              :model-value="store.filters.module"
              placeholder="全部模块"
              clearable
              filterable
              aria-label="按模块筛选"
              @change="value => store.setFilter('module', value)"
            >
              <el-option
                v-for="module in store.moduleOptions"
                :key="module"
                :label="module"
                :value="module"
              />
            </el-select>
            <el-select
              :model-value="store.filters.type"
              placeholder="全部类型"
              clearable
              aria-label="按文件类型筛选"
              @change="value => store.setFilter('type', value)"
            >
              <el-option
                v-for="type in store.typeOptions"
                :key="type"
                :label="`.${type}`"
                :value="type"
              />
            </el-select>
            <el-button
              v-if="store.hasFilters"
              text
              size="small"
              @click="store.resetFilters"
            >
              清除筛选
            </el-button>
          </div>
        </div>

        <div class="cg-panel panel-block tree-block">
          <FileTree
            :nodes="store.filteredNodes"
            :selected-node="store.selectedNode"
            @select="handleNodeSelect"
          />
        </div>

        <div class="cg-panel panel-block stats-block">
          <StatsPanel :stats="store.stats" />
        </div>
      </aside>

      <main class="canvas-container">
        <GraphCanvas
          ref="canvasRef"
          :nodes="store.filteredNodes"
          :edges="store.filteredEdges"
          :selected-node="store.selectedNode"
          :layout="store.layout"
          :loading="store.loading || store.analyzing"
          :empty-description="store.hasFilters ? CODE_GRAPH.messages.filteredEmpty : CODE_GRAPH.messages.empty"
          :empty-action="store.hasFilters ? '清除筛选' : '重新分析'"
          :can-refresh="Boolean(store.currentProject)"
          @node-click="handleNodeClick"
          @refresh="handleCanvasRefresh"
          @layout-change="handleLayoutChangeInStore"
        />
      </main>

      <aside
        id="graph-insights"
        ref="insightsRef"
        class="detail-sidebar"
        :class="{ open: detailsOpen }"
        aria-label="项目洞察"
        :role="activePanel === insightsRef ? 'dialog' : undefined"
        :aria-modal="activePanel === insightsRef || undefined"
        @keydown="handlePanelKeydown"
      >
        <el-button
          class="panel-close details-close"
          :icon="X"
          @click="detailsOpen = false"
        >
          关闭项目洞察
        </el-button>
        <Transition name="cg-slide">
          <div
            v-if="store.selectedNode"
            class="cg-panel panel-block detail-block"
          >
            <FileDetail
              :node="store.selectedNode"
              @close="store.clearSelection"
              @view-file="handleViewFile"
              @select="handleNodeSelect"
            />
          </div>
        </Transition>

        <div
          v-if="store.hotspots.length > 0"
          class="cg-panel panel-block"
        >
          <HotspotsPanel
            :hotspots="store.hotspots"
            @select="handleNodeSelect"
          />
        </div>

        <div
          v-if="store.hasCycles"
          class="cg-panel panel-block warning-block cycle-glow"
        >
          <CyclesWarning
            :cycles="store.cycles"
            @select="handleNodeSelect"
          />
        </div>

        <div
          v-if="!store.selectedNode && !store.hotspots.length && !store.hasCycles"
          class="cg-panel panel-block empty-hint"
        >
          <p>在图谱中点选节点</p>
          <span>查看依赖、热点与源码详情</span>
        </div>
      </aside>
    </div>

    <FilePreviewDialog
      v-model="showFilePreview"
      :file-path="previewFilePath"
      :project-id="selectedProjectId"
      :highlight-line="previewHighlightLine"
    />

    <GraphAssistant
      :project-id="selectedProjectId"
      :selected-node="store.selectedNode"
      @open-file="handleAssistantOpenFile"
      @select-node="handleNodeSelect"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCodeGraphStore } from '@/stores/codeGraph'
import SearchPanel from './SearchPanel.vue'
import FileTree from './FileTree.vue'
import StatsPanel from './StatsPanel.vue'
import GraphCanvas from './GraphCanvas.vue'
import FileDetail from './FileDetail.vue'
import HotspotsPanel from './HotspotsPanel.vue'
import CyclesWarning from './CyclesWarning.vue'
import FilePreviewDialog from './FilePreviewDialog.vue'
import GraphAssistant from './GraphAssistant.vue'
import { RotateCw, PanelLeft, PanelRight, X } from 'lucide-vue-next'
import { CODE_GRAPH } from '@/config/codeGraph'
import { useAppStore } from '@/stores/app'
import './codegraph-theme.scss'

const store = useCodeGraphStore()
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const selectedProjectId = ref(null)
const showFilePreview = ref(false)
const previewFilePath = ref('')
const previewHighlightLine = ref(null)
const canvasRef = ref(null)
const filesOpen = ref(false)
const detailsOpen = ref(false)
const explorerRef = ref(null)
const insightsRef = ref(null)
const viewportWidth = ref(window.innerWidth)
const activePanel = computed(() => {
  if (filesOpen.value && viewportWidth.value <= CODE_GRAPH.mobileBreakpoint) return explorerRef.value
  if (detailsOpen.value && viewportWidth.value <= CODE_GRAPH.detailBreakpoint) return insightsRef.value
  return null
})
let disposed = false
let panelReturnFocus = null

function updateViewport() { viewportWidth.value = window.innerWidth }
watch(activePanel, async (panel, previous) => {
  if (panel) {
    if (!previous) panelReturnFocus = document.activeElement
    await nextTick()
    panel.querySelector('button, input')?.focus()
  } else if (previous) {
    await nextTick()
    if (panelReturnFocus?.isConnected) panelReturnFocus.focus()
  }
})

function handlePanelKeydown(event) {
  const panel = activePanel.value
  if (!panel || event.key !== 'Tab') return
  const items = [...panel.querySelectorAll('button, input, [tabindex="0"]')]
    .filter(element => !element.disabled && element.getClientRects().length)
  const first = items[0]
  const last = items.at(-1)
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}

function closePanels() { filesOpen.value = detailsOpen.value = false }
function toggleFiles() { filesOpen.value = !filesOpen.value; detailsOpen.value = false }
function toggleDetails() { detailsOpen.value = !detailsOpen.value; filesOpen.value = false }

const currentProjectMeta = computed(() => {
  if (selectedProjectId.value == null) return null
  return store.projects.find(p => p.id === selectedProjectId.value) || null
})

/** API camelCase: isValid；兼容 snake_case is_valid */
function isProjectValid(project) {
  if (!project) return false
  if (typeof project.isValid === 'boolean') return project.isValid
  if (typeof project.is_valid === 'boolean') return project.is_valid
  return true
}

onMounted(async () => {
  window.addEventListener('resize', updateViewport)
  await store.fetchProjects()
  if (disposed) return

  const queryProject = route.query.project
  let target = null

  if (queryProject != null && queryProject !== '') {
    const qid = isNaN(Number(queryProject)) ? queryProject : Number(queryProject)
    target = store.projects.find(p => p.id === qid || String(p.id) === String(queryProject))
  }

  if (!target && store.projects.length > 0) {
    target = store.projects.find(p => isProjectValid(p)) || store.projects[0]
  }

  if (target) {
    selectedProjectId.value = target.id
    await store.selectProject(target.id)
    if (disposed) return
    syncProjectQuery(selectedProjectId.value)
  }

  startHeartbeat()
})

onUnmounted(() => {
  disposed = true
  window.removeEventListener('resize', updateViewport)
  store.reset()
  stopHeartbeat()
})

watch(
  () => route.query.project,
  async (project) => {
    if (project == null || project === '') return
    const qid = isNaN(Number(project)) ? project : Number(project)
    if (selectedProjectId.value === qid || String(selectedProjectId.value) === String(project)) return
    const found = store.projects.find(p => p.id === qid || String(p.id) === String(project))
    if (found) {
      selectedProjectId.value = found.id
      await store.selectProject(found.id)
    }
  }
)

let heartbeatTimer = null

function startHeartbeat() {
  heartbeatTimer = setInterval(() => {
    store.sendPing()
  }, CODE_GRAPH.heartbeatMs)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function syncProjectQuery(projectId) {
  if (String(route.query.project) === String(projectId)) return
  router.replace({
    query: {
      ...route.query,
      project: projectId,
    },
  })
}

async function handleProjectChange(projectId) {
  closePanels()
  showFilePreview.value = false
  syncProjectQuery(projectId)
  await store.selectProject(projectId)
}

async function handleRefresh() {
  if (!selectedProjectId.value) return
  if (await store.reanalyze()) appStore.success(CODE_GRAPH.messages.analysisComplete)
}

async function handleRetry() {
  if (store.currentProject) await store.selectProject(store.currentProject.id)
  else {
    await store.fetchProjects()
    const project = store.projects.find(isProjectValid)
    if (project && !disposed) {
      selectedProjectId.value = project.id
      await handleProjectChange(project.id)
    }
  }
}

function handleCanvasRefresh() {
  if (store.hasFilters) store.resetFilters()
  else handleRefresh()
}

function handleNodeClick(node) {
  if (node) handleNodeSelect(node)
  else store.clearSelection()
}

function handleNodeSelect(node) {
  if (!node) return
  node = store.nodes.find(item => item.id === node.id) || node
  // Selecting from global search must reveal the file even when filters exclude it.
  if (!store.filteredNodes.some(item => item.id === node.id)) store.resetFilters()
  store.selectNode(node)
  filesOpen.value = false
  detailsOpen.value = true
  nextTick(() => { if (store.layout !== '3d') canvasRef.value?.focusNode?.(node) })
}

function handleLayoutChangeInStore(newLayout) {
  store.setLayout(newLayout)
}

function handleViewFile(filePath) {
  previewFilePath.value = filePath
  previewHighlightLine.value = null
  showFilePreview.value = true
}

function handleAssistantOpenFile(payload) {
  const path = typeof payload === 'string' ? payload : payload?.path
  if (!path) return
  previewFilePath.value = path
  previewHighlightLine.value = typeof payload === 'object' ? (payload.startLine || null) : null
  showFilePreview.value = true
}
</script>

<style lang="scss" scoped>
.codegraph-shell {
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--header-height) - 2 * var(--cg-page-inset));
  min-height: 0;
  padding: 12px;
  gap: 12px;
  box-sizing: border-box;
  overflow: hidden;
}

.codegraph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  flex-shrink: 0;
  z-index: 2;
  animation-delay: 0.05s;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 22px;
  min-width: 0;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-orb {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.25);
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.1;
}

.page-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.project-selector {
  width: 260px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.project-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.project-path {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 2px;

  &.invalid {
    color: #fbbf24;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.codegraph-body {
  position: relative;
  display: flex;
  flex: 1;
  gap: 12px;
  min-height: 0;
  overflow: hidden;
  z-index: 1;
}

.graph-filters {
  display: grid;
  gap: var(--cg-control-gap);
  padding: var(--cg-control-padding);
  padding-top: 0;
}

.explorer-toggle, .insights-toggle, .panel-close, .panel-backdrop { display: none; }

.panel-backdrop {
  position: absolute;
  inset: 0;
  z-index: 20;
  border: 0;
  background: var(--cg-overlay-bg);
}

.sidebar,
.detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: hidden;
}

.sidebar {
  width: 288px;
  flex-shrink: 0;
}

.detail-sidebar {
  width: 320px;
  flex-shrink: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.panel-block {
  position: relative;
  z-index: 1;
  min-height: 0;
  animation-delay: 0.12s;

  &.tree-block {
    flex: 1;
    display: flex;
    flex-direction: column;
    animation-delay: 0.18s;
  }

  &.stats-block {
    max-height: 280px;
    overflow: auto;
    animation-delay: 0.24s;
  }

  &.search-block {
    flex-shrink: 0;
  }

  &.detail-block {
    flex-shrink: 0;
    max-height: min(72vh, 760px);
    overflow: hidden;
    display: flex;
    flex-direction: column;

    :deep(.file-detail) {
      flex: 1;
      min-height: 0;
    }
  }
}

.canvas-container {
  flex: 1;
  position: relative;
  min-width: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.empty-hint {
  padding: 28px 18px;
  text-align: center;
  color: var(--text-secondary);

  p {
    margin: 0 0 6px;
    font-size: 14px;
    color: var(--text-primary);
  }

  span {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.cycle-glow {
  border-color: rgba(251, 113, 133, 0.35);
}

.cg-slide-enter-active,
.cg-slide-leave-active {
  transition: opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1), transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.cg-slide-enter-from,
.cg-slide-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

@media (max-width: 1100px) {
  .insights-toggle { display: inline-flex; }
  .details-close { display: inline-flex; }
  .detail-sidebar {
    display: none;

    &.open {
      display: flex;
      position: absolute;
      inset: var(--cg-panel-inset) var(--cg-panel-inset) var(--cg-panel-inset) auto;
      width: var(--cg-mobile-panel-width);
      z-index: 21;
      background: var(--bg-secondary);
      padding: var(--cg-control-padding);
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-lg);
    }
  }

  .codegraph-body:has(.detail-sidebar.open) .panel-backdrop { display: block; }

  .sidebar {
    width: 260px;
  }
}

@media (max-width: 860px) {
  .codegraph-shell {
    --cg-page-inset: 16px;
    padding: 8px;
  }

  .sidebar {
    display: none;

    &.open {
      display: flex;
      position: absolute;
      inset: var(--cg-panel-inset) auto var(--cg-panel-inset) var(--cg-panel-inset);
      width: var(--cg-mobile-panel-width);
      z-index: 21;
      background: var(--bg-secondary);
      padding: var(--cg-control-padding);
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-lg);
      overflow-y: auto;
    }
  }

  .explorer-toggle, .files-close { display: inline-flex; }
  .codegraph-body:has(.sidebar.open) .panel-backdrop { display: block; }

  .page-sub {
    display: none;
  }
}

@media (max-width: 768px) {
  .codegraph-header { flex-direction: column; align-items: stretch; gap: 12px; padding: 12px; }
  .header-left { flex-wrap: wrap; gap: 12px; }
  .brand-block { flex: 1 0 100%; }
  .page-title { font-size: 18px; letter-spacing: normal; }
  .project-selector { width: 100%; min-width: 0; }
  .header-right { flex-wrap: wrap; justify-content: space-between; gap: 8px; }
}
</style>
