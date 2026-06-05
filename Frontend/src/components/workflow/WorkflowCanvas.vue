<template>
  <div
    class="workflow-canvas-wrapper"
    :class="{ 'execution-mode': isExecutionMode }"
  >
    <!-- Execution Status Bar -->
    <div
      v-if="isExecutionMode"
      class="execution-status-bar"
    >
      <div class="execution-info">
        <div
          class="execution-indicator"
          :class="executionStatus"
        >
          <span class="indicator-dot" />
          <span class="indicator-text">{{ statusLabel }}</span>
        </div>
        <div class="execution-progress">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: progressPercentage + '%' }"
            />
          </div>
          <span class="progress-text">{{ progressPercentage }}%</span>
        </div>
      </div>
      <div class="execution-summary">
        <div class="summary-item completed">
          <Check class="summary-icon" />
          <span>{{ completedCount }} 完成</span>
        </div>
        <div class="summary-item running">
          <Loader class="summary-icon spinning" />
          <span>{{ runningCount }} 执行中</span>
        </div>
        <div
          v-if="failedCount > 0"
          class="summary-item failed"
        >
          <X class="summary-icon" />
          <span>{{ failedCount }} 失败</span>
        </div>
      </div>
      <div class="execution-actions">
        <el-button
          v-if="executionStatus === 'running'"
          size="small"
          @click="$emit('cancel')"
        >
          取消
        </el-button>
        <el-button
          v-if="executionStatus === 'running'"
          size="small"
          @click="$emit('pause')"
        >
          暂停
        </el-button>
        <el-button
          v-if="executionStatus === 'paused'"
          size="small"
          @click="$emit('resume')"
        >
          继续
        </el-button>
      </div>
    </div>

    <!-- Canvas Toolbar -->
    <div class="canvas-toolbar">
      <div class="toolbar-group">
        <el-button-group>
          <el-button
            size="small"
            title="放大"
            @click="zoomIn"
          >
            <ZoomIn class="btn-icon" />
          </el-button>
          <el-button
            size="small"
            title="缩小"
            @click="zoomOut"
          >
            <ZoomOut class="btn-icon" />
          </el-button>
          <el-button
            size="small"
            title="适应画布"
            @click="fitView"
          >
            <Maximize2 class="btn-icon" />
          </el-button>
          <el-button
            size="small"
            title="重置缩放"
            @click="resetZoom"
          >
            100%
          </el-button>
        </el-button-group>
        <span class="zoom-level">{{ Math.round(zoom * 100) }}%</span>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <el-tooltip
          content="对齐网格"
          placement="bottom"
        >
          <el-button
            size="small"
            :type="snapToGrid ? 'primary' : 'default'"
            @click="toggleSnapToGrid"
          >
            <Grid3x3 class="btn-icon" />
          </el-button>
        </el-tooltip>
        <el-tooltip
          content="显示小地图"
          placement="bottom"
        >
          <el-button
            size="small"
            :type="showMiniMap ? 'primary' : 'default'"
            @click="toggleMiniMap"
          >
            <Map class="btn-icon" />
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <el-button
          size="small"
          title="全选 (Ctrl+A)"
          @click="selectAll"
        >
          <CheckSquare class="btn-icon" />
        </el-button>
        <el-button
          size="small"
          :disabled="!hasSelection"
          title="删除选中 (Delete)"
          @click="deleteSelected"
        >
          <Trash2 class="btn-icon" />
        </el-button>
        <el-tooltip
          content="撤销 (Ctrl+Z)"
          placement="bottom"
        >
          <el-button
            size="small"
            :disabled="!canUndo"
            @click="undo"
          >
            <Undo2 class="btn-icon" />
          </el-button>
        </el-tooltip>
        <el-tooltip
          content="重做 (Ctrl+Y)"
          placement="bottom"
        >
          <el-button
            size="small"
            :disabled="!canRedo"
            @click="redo"
          >
            <Redo2 class="btn-icon" />
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- Vue Flow Canvas -->
    <VueFlow
      ref="vueFlowRef"
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :default-viewport="defaultViewport"
      :snap-to-grid="snapToGrid"
      :snap-grid="[16, 16]"
      :mini-map="miniMapConfig"
      :connections-line-type="connectionsLineType"
      :apply-d-e-f-a-u-l-t-edge-options="true"
      fit-view-on-init
      @node-click="$emit('node-click', $event)"
      @edge-click="$emit('edge-click', $event)"
      @pane-click="$emit('pane-click', $event)"
      @nodes-change="handleNodesChange"
      @edges-change="handleEdgesChange"
      @connect="$emit('connect', $event)"
      @node-drag-stop="$emit('node-drag-stop', $event)"
      @selection-change="handleSelectionChange"
      @move-end="handleMoveEnd"
    >
      <Background
        pattern-color="#1a1a2e"
        :gap="16"
      />

      <MiniMap
        v-if="showMiniMapEnabled"
        :node-color="getMiniMapNodeColor"
        :node-stroke-width="3"
        pannable
        zoomable
      />

      <template #node-start="{ data }">
        <StartNode :data="data" />
      </template>

      <template #node-end="{ data }">
        <EndNode :data="data" />
      </template>

      <template #node-llm="{ data }">
        <LLMNode :data="data" />
      </template>

      <template #node-prompt="{ data }">
        <PromptNode :data="data" />
      </template>

      <template #node-condition="{ data }">
        <ConditionNode :data="data" />
      </template>

      <template #node-tool="{ data }">
        <ToolNode :data="data" />
      </template>

      <template #node-input="{ data }">
        <InputNode :data="data" />
      </template>

      <template #node-output="{ data }">
        <OutputNode :data="data" />
      </template>

      <template #node-http="{ data }">
        <HttpNode :data="data" />
      </template>

      <template #node-code="{ data }">
        <CodeNode :data="data" />
      </template>

      <template #node-loop="{ data }">
        <LoopNode :data="data" />
      </template>

      <template #node-variable="{ data }">
        <VariableNode :data="data" />
      </template>

      <template #node-switch="{ data }">
        <SwitchNode :data="data" />
      </template>

      <template #node-delay="{ data }">
        <DelayNode :data="data" />
      </template>

      <template #node-transform="{ data }">
        <TransformNode :data="data" />
      </template>

      <template #node-image_generation="{ data }">
        <ImageGenerationNode :data="data" />
      </template>

      <template #node-video_generation="{ data }">
        <VideoGenerationNode :data="data" />
      </template>

      <template #node-audio_generation="{ data }">
        <AudioGenerationNode :data="data" />
      </template>

      <template #node-subtitle_generation="{ data }">
        <SubtitleGenerationNode :data="data" />
      </template>

      <template #node-image_editing="{ data }">
        <ImageEditingNode :data="data" />
      </template>

      <template #node-dataset_upload="{ data }">
        <DatasetUploadNode :data="data" />
      </template>

      <template #node-data_annotation="{ data }">
        <DataAnnotationNode :data="data" />
      </template>

      <template #node-data_augmentation="{ data }">
        <DataAugmentationNode :data="data" />
      </template>

      <template #node-model_training="{ data }">
        <ModelTrainingNode :data="data" />
      </template>

      <template #node-model_evaluation="{ data }">
        <ModelEvaluationNode :data="data" />
      </template>

      <template #node-model_deployment="{ data }">
        <ModelDeploymentNode :data="data" />
      </template>

      <template #node-website_generator="{ data }">
        <WebsiteGeneratorNode :data="data" />
      </template>

      <template #node-document_loader="{ data }">
        <DocumentLoaderNode :data="data" />
      </template>

      <template #node-embedding="{ data }">
        <EmbeddingNode :data="data" />
      </template>

      <template #node-vector_store="{ data }">
        <VectorStoreNode :data="data" />
      </template>

      <template #node-retriever="{ data }">
        <RetrieverNode :data="data" />
      </template>

      <template #node-reranker="{ data }">
        <RerankerNode :data="data" />
      </template>

      <template #node-agent="{ data }">
        <AgentNodeComponent :data="data" />
      </template>

      <template #node-planner="{ data }">
        <PlannerNode :data="data" />
      </template>

      <template #node-executor="{ data }">
        <ExecutorNode :data="data" />
      </template>

      <template #node-memory="{ data }">
        <MemoryNode :data="data" />
      </template>

      <template #node-file_reader="{ data }">
        <FileReaderNode :data="data" />
      </template>

      <template #node-file_writer="{ data }">
        <FileWriterNode :data="data" />
      </template>

      <template #node-web_scraper="{ data }">
        <WebScraperNode :data="data" />
      </template>

      <template #node-csv_transform="{ data }">
        <CsvTransformNode :data="data" />
      </template>

      <template #node-json_transform="{ data }">
        <JsonTransformNode :data="data" />
      </template>

      <template #node-email="{ data }">
        <EmailNode :data="data" />
      </template>

      <template #node-subworkflow="{ data }">
        <SubworkflowNode :data="data" />
      </template>

      <template #node-email_node="{ data }">
        <EmailNode :data="data" />
      </template>
    </VueFlow>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, h, watch } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/minimap/dist/style.css'

import StartNode from './nodes/StartNode.vue'
import EndNode from './nodes/EndNode.vue'
import LLMNode from './nodes/LLMNode.vue'
import PromptNode from './nodes/PromptNode.vue'
import ConditionNode from './nodes/ConditionNode.vue'
import ToolNode from './nodes/ToolNode.vue'
import InputNode from './nodes/InputNode.vue'
import OutputNode from './nodes/OutputNode.vue'
import HttpNode from './nodes/HttpNode.vue'
import CodeNode from './nodes/CodeNode.vue'
import LoopNode from './nodes/LoopNode.vue'
import VariableNode from './nodes/VariableNode.vue'
import SwitchNode from './nodes/SwitchNode.vue'
import DelayNode from './nodes/DelayNode.vue'
import TransformNode from './nodes/TransformNode.vue'
import ImageGenerationNode from './nodes/ImageGenerationNode.vue'
import VideoGenerationNode from './nodes/VideoGenerationNode.vue'
import AudioGenerationNode from './nodes/AudioGenerationNode.vue'
import SubtitleGenerationNode from './nodes/SubtitleGenerationNode.vue'
import ImageEditingNode from './nodes/ImageEditingNode.vue'
import DatasetUploadNode from './nodes/DatasetUploadNode.vue'
import DataAnnotationNode from './nodes/DataAnnotationNode.vue'
import DataAugmentationNode from './nodes/DataAugmentationNode.vue'
import ModelTrainingNode from './nodes/ModelTrainingNode.vue'
import ModelEvaluationNode from './nodes/ModelEvaluationNode.vue'
import ModelDeploymentNode from './nodes/ModelDeploymentNode.vue'
import WebsiteGeneratorNode from './nodes/WebsiteGeneratorNode.vue'
import DocumentLoaderNode from './nodes/DocumentLoaderNode.vue'
import EmbeddingNode from './nodes/EmbeddingNode.vue'
import VectorStoreNode from './nodes/VectorStoreNode.vue'
import RetrieverNode from './nodes/RetrieverNode.vue'
import RerankerNode from './nodes/RerankerNode.vue'
import AgentNodeComponent from './nodes/AgentNode.vue'
import PlannerNode from './nodes/PlannerNode.vue'
import ExecutorNode from './nodes/ExecutorNode.vue'
import MemoryNode from './nodes/MemoryNode.vue'
import FileReaderNode from './nodes/FileReaderNode.vue'
import FileWriterNode from './nodes/FileWriterNode.vue'
import WebScraperNode from './nodes/WebScraperNode.vue'
import CsvTransformNode from './nodes/CsvTransformNode.vue'
import JsonTransformNode from './nodes/JsonTransformNode.vue'
import EmailNode from './nodes/EmailNode.vue'
import SubworkflowNode from './nodes/SubworkflowNode.vue'

import {
  ZoomIn, ZoomOut, Maximize2, Grid3x3, Map, CheckSquare, Trash2,
  Undo2, Redo2, Check, Loader, X
} from 'lucide-vue-next'

import { useExecutionStore } from '@/stores/execution'
import { StatusColors, StatusLabels } from '@/composables/useExecutionProgress'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  },
  snapToGrid: {
    type: Boolean,
    default: true
  },
  showMiniMap: {
    type: Boolean,
    default: true
  },
  defaultViewport: {
    type: Object,
    default: () => ({ x: 0, y: 0, zoom: 1 })
  },
  executionId: {
    type: [String, Number],
    default: null
  },
  executionMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'node-click',
  'edge-click',
  'pane-click',
  'nodes-change',
  'edges-change',
  'connect',
  'node-drag-stop',
  'zoom-change',
  'history-change',
  'restore-history',
  'cancel',
  'pause',
  'resume'
])

const vueFlowRef = ref(null)
const snapToGridEnabled = ref(props.snapToGrid)
const showMiniMapEnabled = ref(props.showMiniMap)
const selectedNodes = ref([])
const zoom = ref(1)

// Execution store
const executionStore = useExecutionStore()

// Execution status computed
const isExecutionMode = computed(() => props.executionMode || executionStore.isRunning)
const executionStatus = computed(() => executionStore.executionStatus)
const progressPercentage = computed(() => executionStore.progressPercentage)
const completedCount = computed(() => executionStore.completedNodeCount)
const runningCount = computed(() => Object.values(executionStore.nodeStatusMap).filter(s => s === 'running').length)
const failedCount = computed(() => executionStore.failedNodeCount)

const statusLabel = computed(() => StatusLabels[executionStore.executionStatus] || '就绪')

// Get node execution status
function getNodeExecutionStatus(nodeId) {
  return executionStore.nodeStatusMap[nodeId] || 'pending'
}

// Get node status color for border/background
function getNodeStatusColor(nodeId) {
  const status = getNodeExecutionStatus(nodeId)
  return StatusColors[status] || StatusColors.pending
}

// Get node status class
function getNodeStatusClass(nodeId) {
  const status = getNodeExecutionStatus(nodeId)
  return `status-${status}`
}

// Check if node is in execution state
function isNodeRunning(nodeId) {
  return executionStore.nodeStatusMap[nodeId] === 'running'
}

function isNodeCompleted(nodeId) {
  return executionStore.nodeStatusMap[nodeId] === 'completed'
}

function isNodeFailed(nodeId) {
  return executionStore.nodeStatusMap[nodeId] === 'failed'
}

const nodeTypes = [
  'start', 'end', 'llm', 'prompt', 'condition',
  'tool', 'input', 'output', 'http', 'code',
  'loop', 'variable', 'switch', 'delay', 'transform',
  'image_generation', 'video_generation', 'audio_generation', 'subtitle_generation', 'image_editing',
  'dataset_upload', 'data_annotation', 'data_augmentation', 'model_training', 'model_evaluation', 'model_deployment',
  'website_generator', 'document_loader', 'embedding', 'vector_store', 'retriever', 'reranker',
  'agent', 'planner', 'executor', 'memory',
  'file_reader', 'file_writer', 'web_scraper',
  'csv_transform', 'json_transform', 'email', 'subworkflow'
]

const miniMapConfig = computed(() => ({
  show: showMiniMapEnabled.value
}))

// MiniMap node color based on execution status
function getMiniMapNodeColor(node) {
  // First check if node has execution status
  const executionStatus = executionStore.nodeStatusMap[node.id]
  if (executionStatus) {
    return StatusColors[executionStatus] || '#6b7280'
  }
  // Fallback to type-based colors
  const colors = {
    start: '#10b981',
    end: '#ef4444',
    llm: '#3b82f6',
    prompt: '#f59e0b',
    condition: '#3b82f6',
    tool: '#ec4899',
    input: '#06b6d4',
    output: '#84cc16',
    http: '#f97316',
    code: '#f97316',
    loop: '#f59e0b',
    variable: '#22c55e',
    switch: '#3b82f6',
    delay: '#14b8a6',
    transform: '#8b5cf6',
    // Multimodal & Generation
    image_generation: '#ec4899',
    video_generation: '#8b5cf6',
    audio_generation: '#06b6d4',
    subtitle_generation: '#f59e0b',
    image_editing: '#f97316',
    // ML & Training
    dataset_upload: '#22c55e',
    data_annotation: '#14b8a6',
    data_augmentation: '#f59e0b',
    model_training: '#ef4444',
    model_evaluation: '#3b82f6',
    model_deployment: '#10b981',
    website_generator: '#8b5cf6',
    // RAG & Retrieval
    document_loader: '#f59e0b',
    embedding: '#06b6d4',
    vector_store: '#3b82f6',
    retriever: '#22c55e',
    reranker: '#ec4899',
    // Agent System
    agent: '#8b5cf6',
    planner: '#3b82f6',
    executor: '#f97316',
    memory: '#06b6d4',
    // Data Pipeline
    file_reader: '#14b8a6',
    file_writer: '#14b8a6',
    web_scraper: '#f97316',
    csv_transform: '#22c55e',
    json_transform: '#22c55e',
    email: '#ec4899',
    subworkflow: '#8b5cf6'
  }
  return colors[node.type] || '#6b7280'
}

const hasSelection = computed(() => selectedNodes.value.length > 0)

// Undo/Redo state history
const undoStack = ref([])
const redoStack = ref([])
const maxHistorySize = 50

const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

function pushToHistory(nodesSnapshot, edgesSnapshot) {
  undoStack.value.push({ nodes: JSON.parse(JSON.stringify(nodesSnapshot)), edges: JSON.parse(JSON.stringify(edgesSnapshot)) })
  if (undoStack.value.length > maxHistorySize) {
    undoStack.value.shift()
  }
  redoStack.value = []
}

function undo() {
  if (undoStack.value.length === 0) return
  const current = { nodes: JSON.parse(JSON.stringify(props.nodes)), edges: JSON.parse(JSON.stringify(props.edges)) }
  redoStack.value.push(current)
  const previous = undoStack.value.pop()
  emit('restore-history', previous)
}

function redo() {
  if (redoStack.value.length === 0) return
  const current = { nodes: JSON.parse(JSON.stringify(props.nodes)), edges: JSON.parse(JSON.stringify(props.edges)) }
  undoStack.value.push(current)
  const next = redoStack.value.pop()
  emit('restore-history', next)
}

// Zoom controls
const zoomIn = () => {
  if (vueFlowRef.value) {
    vueFlowRef.value.zoomIn()
  }
}

const zoomOut = () => {
  if (vueFlowRef.value) {
    vueFlowRef.value.zoomOut()
  }
}

const fitView = () => {
  if (vueFlowRef.value) {
    vueFlowRef.value.fitView()
  }
}

const resetZoom = () => {
  if (vueFlowRef.value) {
    vueFlowRef.value.setViewport({ x: 0, y: 0, zoom: 1 })
  }
}

const toggleSnapToGrid = () => {
  snapToGridEnabled.value = !snapToGridEnabled.value
}

const toggleMiniMap = () => {
  showMiniMapEnabled.value = !showMiniMapEnabled.value
}

const selectAll = () => {
  if (vueFlowRef.value) {
    vueFlowRef.value.selectAll()
  }
}

const deleteSelected = () => {
  if (vueFlowRef.value) {
    vueFlowRef.value.removeSelectedNodes()
  }
}

// Event handlers
const handleNodesChange = (changes) => {
  emit('nodes-change', changes)
}

const handleEdgesChange = (changes) => {
  emit('edges-change', changes)
}

const handleSelectionChange = ({ nodes }) => {
  selectedNodes.value = nodes
}

const handleMoveEnd = ({ viewport }) => {
  zoom.value = viewport.zoom
  emit('zoom-change', viewport)
}

// Expose methods for parent component
defineExpose({
  pushToHistory,
  undo,
  redo,
  canUndo,
  canRedo,
  getNodeExecutionStatus,
  getNodeStatusColor,
  getNodeStatusClass
})

// Watch execution status changes
watch(() => executionStore.nodeStatusMap, () => {
  // Trigger reactivity for node status displays
}, { deep: true })

// Keyboard shortcuts
const handleKeyDown = (e) => {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'a') {
      e.preventDefault()
      selectAll()
    } else if (e.key === 'z') {
      e.preventDefault()
      undo()
    } else if (e.key === 'y') {
      e.preventDefault()
      redo()
    }
  }
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault()
      deleteSelected()
    }
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style lang="scss" scoped>
.workflow-canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  background-color: var(--color-bg-primary, #0f0f1a);
}

.canvas-toolbar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(15, 15, 26, 0.9);
  backdrop-filter: blur(12px);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.03) inset;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
}

.zoom-level {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  min-width: 40px;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

:deep(.vue-flow-controls) {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  background: rgba(15, 15, 26, 0.9);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

:deep(.vue-flow-controls-btn) {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  &:active {
    transform: scale(0.95);
  }
}

// ============================================================
// Execution Status Visualization Styles
// ============================================================

.execution-mode {
  .vue-flow__node {
    transition: all 0.3s ease;
  }
}

// Execution Status Bar
.execution-status-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: rgba(15, 15, 26, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.execution-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.execution-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;

  .indicator-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    animation: pulse-dot 1.5s ease-in-out infinite;
  }

  &.running {
    background: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
    border: 1px solid rgba(59, 130, 246, 0.3);

    .indicator-dot {
      background: #3b82f6;
      box-shadow: 0 0 8px rgba(59, 130, 246, 0.6);
    }
  }

  &.completed {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);

    .indicator-dot {
      background: #10b981;
      animation: none;
    }
  }

  &.failed {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);

    .indicator-dot {
      background: #ef4444;
      animation: none;
    }
  }

  &.paused {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);

    .indicator-dot {
      background: #f59e0b;
      animation: none;
    }
  }

  &.cancelled {
    background: rgba(156, 163, 175, 0.15);
    color: #9ca3af;
    border: 1px solid rgba(156, 163, 175, 0.3);

    .indicator-dot {
      background: #9ca3af;
      animation: none;
    }
  }

  &.idle,
  &.pending {
    background: rgba(156, 163, 175, 0.1);
    color: #9ca3af;
    border: 1px solid rgba(156, 163, 175, 0.2);

    .indicator-dot {
      background: #9ca3af;
      animation: none;
    }
  }
}

.execution-progress {
  display: flex;
  align-items: center;
  gap: 12px;

  .progress-bar {
    width: 120px;
    height: 6px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #10b981);
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    min-width: 36px;
  }
}

.execution-summary {
  display: flex;
  align-items: center;
  gap: 16px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;

  .summary-icon {
    width: 14px;
    height: 14px;

    &.spinning {
      animation: spin 1s linear infinite;
    }
  }

  &.completed {
    color: #10b981;
  }

  &.running {
    color: #3b82f6;
  }

  &.failed {
    color: #ef4444;
  }
}

.execution-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// Node Status Styles (applied via custom node classes)
:deep(.vue-flow__node) {
  // Running node pulse animation
  &.is-running {
    .node-card,
    .llm-node,
    .start-end-node,
    .node-wrapper {
      animation: node-pulse 1.8s ease-in-out infinite;
    }
  }

  // Completed node glow
  &.is-completed {
    .node-card,
    .llm-node,
    .start-end-node,
    .node-wrapper {
      box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.4), 0 4px 20px rgba(16, 185, 129, 0.2) !important;
    }
  }

  // Failed node error style
  &.is-failed {
    .node-card,
    .llm-node,
    .start-end-node,
    .node-wrapper {
      box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.4), 0 4px 20px rgba(239, 68, 68, 0.2) !important;
      animation: node-error-shake 0.5s ease-in-out;
    }
  }

  // Pending node dimmed
  &.is-pending {
    opacity: 0.6;
  }
}

@keyframes node-pulse {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 8px rgba(59, 130, 246, 0);
  }
}

@keyframes node-error-shake {
  0%, 100% {
    transform: translateX(0);
  }
  20%, 60% {
    transform: translateX(-3px);
  }
  40%, 80% {
    transform: translateX(3px);
  }
}

// Edge animation for running paths
:deep(.vue-flow__edge-path) {
  &.running-path {
    stroke: #3b82f6;
    stroke-width: 2;
    animation: edge-flow 1s linear infinite;
  }

  &.completed-path {
    stroke: #10b981;
    stroke-width: 2;
  }

  &.error-path {
    stroke: #ef4444;
    stroke-width: 2;
    stroke-dasharray: 5, 5;
  }
}

@keyframes edge-flow {
  0% {
    stroke-dashoffset: 20;
  }
  100% {
    stroke-dashoffset: 0;
  }
}
</style>
