<template>
  <div class="codegraph-container">
    <!-- 顶部导航 -->
    <div class="codegraph-header">
      <div class="header-left">
        <h1 class="page-title">
          <Network class="title-icon" />
          代码图谱
        </h1>
        <div class="project-selector">
          <el-select
            v-model="selectedProjectId"
            placeholder="选择项目"
            :loading="store.loading"
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
                  v-if="!project.is_valid"
                  type="warning"
                  size="small"
                >
                  路径无效
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </div>
      </div>
      <div class="header-right">
        <el-button
          :type="store.wsConnected ? 'success' : 'info'"
          size="small"
          circle
          :icon="store.wsConnected ? Wifi : WifiOff"
          :title="store.wsConnected ? '实时连接已建立' : '实时连接已断开'"
        />
        <el-button
          :loading="store.analyzing"
          :icon="RotateCw"
          @click="handleRefresh"
        >
          {{ store.analyzing ? '分析中...' : '重新分析' }}
        </el-button>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="codegraph-body">
      <!-- 左侧边栏 -->
      <div class="sidebar">
        <!-- 搜索面板 -->
        <SearchPanel @select="handleNodeSelect" />

        <!-- 文件树 -->
        <FileTree
          :nodes="store.nodes"
          :selected-node="store.selectedNode"
          @select="handleNodeSelect"
        />

        <!-- 统计面板 -->
        <StatsPanel :stats="store.stats" />
      </div>

      <!-- 中间画布 -->
      <div class="canvas-container">
        <GraphCanvas
          :nodes="store.filteredNodes"
          :edges="store.filteredEdges"
          :selected-node="store.selectedNode"
          :layout="store.layout"
          :loading="store.loading"
          @node-click="handleNodeClick"
          @node-hover="handleNodeHover"
          @zoom-change="handleZoomChange"
          @fit-view="handleFitView"
        />
      </div>

      <!-- 右侧边栏 -->
      <div class="detail-sidebar">
        <FileDetail
          v-if="store.selectedNode"
          :node="store.selectedNode"
          @close="store.clearSelection"
          @view-file="handleViewFile"
        />

        <!-- 热点文件 -->
        <HotspotsPanel
          v-if="store.hotspots.length > 0"
          :hotspots="store.hotspots"
          @select="handleNodeSelect"
        />

        <!-- 循环依赖警告 -->
        <CyclesWarning
          v-if="store.hasCycles"
          :cycles="store.cycles"
        />
      </div>
    </div>

    <!-- 文件预览弹窗 -->
    <FilePreviewDialog
      v-model="showFilePreview"
      :file-path="previewFilePath"
      :project-id="selectedProjectId"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import { useCodeGraphStore } from '@/stores/codeGraph'
import SearchPanel from './SearchPanel.vue'
import FileTree from './FileTree.vue'
import StatsPanel from './StatsPanel.vue'
import GraphCanvas from './GraphCanvas.vue'
import FileDetail from './FileDetail.vue'
import HotspotsPanel from './HotspotsPanel.vue'
import CyclesWarning from './CyclesWarning.vue'
import FilePreviewDialog from './FilePreviewDialog.vue'
import { Network, RotateCw, Wifi, WifiOff } from 'lucide-vue-next'

const store = useCodeGraphStore()

const selectedProjectId = ref(null)
const showFilePreview = ref(false)
const previewFilePath = ref('')

// 初始化
onMounted(async () => {
  await store.fetchProjects()

  // 默认选择第一个有效项目
  if (store.projects.length > 0) {
    const validProject = store.projects.find(p => p.is_valid) || store.projects[0]
    selectedProjectId.value = validProject.id
    await store.selectProject(validProject.id)
  }

  // 心跳保活
  startHeartbeat()
})

onUnmounted(() => {
  store.reset()
  stopHeartbeat()
})

let heartbeatTimer = null

function startHeartbeat() {
  heartbeatTimer = setInterval(() => {
    store.sendPing()
  }, 30000)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

// 事件处理
async function handleProjectChange(projectId) {
  await store.selectProject(projectId)
}

async function handleRefresh() {
  if (!selectedProjectId.value) return
  await store.reanalyze()
}

function handleNodeClick(node) {
  store.selectNode(node)
}

function handleNodeHover(node) {
  store.hoverNode(node)
}

function handleNodeSelect(node) {
  store.selectNode(node)
}

function handleZoomChange(zoom) {
  store.setZoom(zoom)
}

function handleFitView() {
  // GraphCanvas 内部处理
}

function handleViewFile(filePath) {
  previewFilePath.value = filePath
  showFilePreview.value = true
}
</script>

<style lang="scss" scoped>
.codegraph-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

.codegraph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);

  .title-icon {
    width: 24px;
    height: 24px;
    color: var(--color-primary);
  }
}

.project-selector {
  width: 200px;
}

.project-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.codegraph-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.canvas-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.detail-sidebar {
  width: 320px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
</style>
