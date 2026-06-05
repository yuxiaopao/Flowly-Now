<template>
  <div class="workflow-detail">
    <div
      v-if="workflow"
      class="detail-container"
    >
      <!-- 顶部信息栏 -->
      <header class="detail-header">
        <div class="header-left">
          <el-button
            :icon="ArrowLeft"
            @click="handleBack"
          >
            返回
          </el-button>
          <div class="workflow-info">
            <h1 class="workflow-name">
              {{ workflow.name }}
            </h1>
            <div class="workflow-meta">
              <el-tag
                :type="getStatusType(workflow.status)"
                size="small"
              >
                {{ getStatusLabel(workflow.status) }}
              </el-tag>
              <span class="meta-text">v{{ workflow.version }}</span>
              <span class="meta-text">更新于 {{ formatDate(workflow.updated_at) }}</span>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="handleDuplicate">
            <Copy class="btn-icon" />
            复制
          </el-button>
          <el-button @click="goToEdit">
            <Edit class="btn-icon" />
            编辑
          </el-button>
          <el-button
            type="primary"
            @click="goToExecute"
          >
            <Play class="btn-icon" />
            执行
          </el-button>
        </div>
      </header>

      <div class="detail-content">
        <!-- 左侧：工作流可视化 -->
        <main class="workflow-canvas">
          <div class="canvas-header">
            <h3>工作流图</h3>
            <div class="canvas-controls">
              <el-button-group>
                <el-button
                  size="small"
                  @click="zoomIn"
                >
                  <ZoomIn />
                </el-button>
                <el-button
                  size="small"
                  @click="zoomOut"
                >
                  <ZoomOut />
                </el-button>
                <el-button
                  size="small"
                  @click="fitView"
                >
                  <Maximize2 />
                </el-button>
              </el-button-group>
            </div>
          </div>

          <div class="canvas-wrapper">
            <VueFlow
              v-if="canvasReady"
              v-model:nodes="nodes"
              v-model:edges="edges"
              :node-types="nodeTypesSnapshot"
              :default-viewport="viewport"
              :zoom="zoom"
              :nodes-draggable="false"
              :nodes-connectable="false"
              :elements-selectable="true"
              fit-view-on-init
              @node-click="onNodeClick"
            >
              <Background
                pattern-color="#1a1a2e"
                :gap="16"
              />
              <MiniMap />
            </VueFlow>
            <div
              v-else
              class="canvas-loading"
            >
              <span>加载中...</span>
            </div>
          </div>
        </main>

        <!-- 右侧：详情面板 -->
        <aside class="detail-sidebar">
          <!-- 基本信息 -->
          <section class="sidebar-section">
            <h3 class="section-title">
              基本信息
            </h3>
            <div class="info-list">
              <div class="info-item">
                <span class="info-label">名称</span>
                <span class="info-value">{{ workflow.name }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">状态</span>
                <el-tag
                  :type="getStatusType(workflow.status)"
                  size="small"
                >
                  {{ getStatusLabel(workflow.status) }}
                </el-tag>
              </div>
              <div class="info-item">
                <span class="info-label">版本</span>
                <span class="info-value">v{{ workflow.version }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">可见性</span>
                <span class="info-value">
                  {{ workflow.is_public ? '公开' : '私有' }}
                </span>
              </div>
            </div>
          </section>

          <!-- 描述 -->
          <section
            v-if="workflow.description"
            class="sidebar-section"
          >
            <h3 class="section-title">
              描述
            </h3>
            <p class="workflow-description">
              {{ workflow.description }}
            </p>
          </section>

          <!-- 统计 -->
          <section class="sidebar-section">
            <h3 class="section-title">
              统计
            </h3>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-value">
                  {{ workflow.node_count || 0 }}
                </div>
                <div class="stat-label">
                  节点
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-value">
                  {{ workflow.execution_count || 0 }}
                </div>
                <div class="stat-label">
                  执行次数
                </div>
              </div>
            </div>
          </section>

          <!-- 标签 -->
          <section
            v-if="workflow.tags?.length"
            class="sidebar-section"
          >
            <h3 class="section-title">
              标签
            </h3>
            <div class="tags-list">
              <el-tag
                v-for="tag in workflow.tags"
                :key="tag"
                size="small"
                type="info"
              >
                {{ tag }}
              </el-tag>
            </div>
          </section>

          <!-- 节点列表 -->
          <section class="sidebar-section">
            <h3 class="section-title">
              节点
            </h3>
            <div class="nodes-list">
              <div
                v-for="node in nodes"
                :key="node.id"
                :class="['node-item', { selected: selectedNodeId === node.id }]"
                @click="selectNode(node.id)"
              >
                <component
                  :is="getNodeIcon(node.type)"
                  class="node-icon"
                />
                <div class="node-info">
                  <span class="node-name">{{ node.data?.label || node.id }}</span>
                  <span class="node-type">{{ getNodeTypeLabel(node.type) }}</span>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <!-- 执行历史 -->
      <section class="execution-history">
        <div class="section-header">
          <h3>执行历史</h3>
          <el-button
            size="small"
            @click="refreshHistory"
          >
            <RefreshCw class="btn-icon" />
            刷新
          </el-button>
        </div>

        <el-table
          :data="executionHistory"
          stripe
          style="width: 100%"
          @row-click="viewExecution"
        >
          <el-table-column
            prop="id"
            label="ID"
            width="80"
          />
          <el-table-column
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                :type="getExecutionStatusType(row.status)"
                size="small"
              >
                {{ getExecutionStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="触发类型"
            width="100"
          >
            <template #default="{ row }">
              {{ getTriggerTypeLabel(row.trigger_type) }}
            </template>
          </el-table-column>
          <el-table-column
            label="开始时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.started_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="耗时"
            width="100"
          >
            <template #default="{ row }">
              {{ formatDuration(row.duration) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="120"
          >
            <template #default="{ row }">
              <el-button
                text
                size="small"
                @click.stop="viewExecution(row)"
              >
                查看
              </el-button>
              <el-button
                v-if="row.status === 'failed'"
                text
                size="small"
                type="danger"
                @click.stop="retryExecution(row)"
              >
                重试
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <div
      v-else
      class="loading-state"
    >
      <el-skeleton
        :rows="10"
        animated
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, shallowRef, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/minimap/dist/style.css'
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import {
  ArrowLeft, Copy, Edit, Play, ZoomIn, ZoomOut,
  Maximize2, RefreshCw, PlayCircle, MessageSquare,
  GitBranch, Hammer, User, FileText, Zap, Circle
} from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'

// 本地导入节点组件（避免 main.js 顶层 import 触发 Pinia）
import StartNode from '@/components/workflow/nodes/StartNode.vue'
import EndNode from '@/components/workflow/nodes/EndNode.vue'
import LLMNode from '@/components/workflow/nodes/LLMNode.vue'
import PromptNode from '@/components/workflow/nodes/PromptNode.vue'
import ConditionNode from '@/components/workflow/nodes/ConditionNode.vue'
import LoopNode from '@/components/workflow/nodes/LoopNode.vue'
import InputNode from '@/components/workflow/nodes/InputNode.vue'
import OutputNode from '@/components/workflow/nodes/OutputNode.vue'
import CodeNode from '@/components/workflow/nodes/CodeNode.vue'
import VariableNode from '@/components/workflow/nodes/VariableNode.vue'
import ToolNode from '@/components/workflow/nodes/ToolNode.vue'
import HttpNode from '@/components/workflow/nodes/HttpNode.vue'
import SwitchNode from '@/components/workflow/nodes/SwitchNode.vue'
import DelayNode from '@/components/workflow/nodes/DelayNode.vue'
import EmailNode from '@/components/workflow/nodes/EmailNode.vue'
import TransformNode from '@/components/workflow/nodes/TransformNode.vue'
import SubworkflowNode from '@/components/workflow/nodes/SubworkflowNode.vue'
import ImageGenerationNode from '@/components/workflow/nodes/ImageGenerationNode.vue'
import VideoGenerationNode from '@/components/workflow/nodes/VideoGenerationNode.vue'
import AudioGenerationNode from '@/components/workflow/nodes/AudioGenerationNode.vue'
import SubtitleGenerationNode from '@/components/workflow/nodes/SubtitleGenerationNode.vue'
import ImageEditingNode from '@/components/workflow/nodes/ImageEditingNode.vue'
import DatasetUploadNode from '@/components/workflow/nodes/DatasetUploadNode.vue'
import DataAnnotationNode from '@/components/workflow/nodes/DataAnnotationNode.vue'
import DataAugmentationNode from '@/components/workflow/nodes/DataAugmentationNode.vue'
import ModelTrainingNode from '@/components/workflow/nodes/ModelTrainingNode.vue'
import ModelEvaluationNode from '@/components/workflow/nodes/ModelEvaluationNode.vue'
import ModelDeploymentNode from '@/components/workflow/nodes/ModelDeploymentNode.vue'
import WebsiteGeneratorNode from '@/components/workflow/nodes/WebsiteGeneratorNode.vue'
import DocumentLoaderNode from '@/components/workflow/nodes/DocumentLoaderNode.vue'
import EmbeddingNode from '@/components/workflow/nodes/EmbeddingNode.vue'
import VectorStoreNode from '@/components/workflow/nodes/VectorStoreNode.vue'
import RetrieverNode from '@/components/workflow/nodes/RetrieverNode.vue'
import RerankerNode from '@/components/workflow/nodes/RerankerNode.vue'
import AgentNode from '@/components/workflow/nodes/AgentNode.vue'
import PlannerNode from '@/components/workflow/nodes/PlannerNode.vue'
import ExecutorNode from '@/components/workflow/nodes/ExecutorNode.vue'
import MemoryNode from '@/components/workflow/nodes/MemoryNode.vue'
import FileReaderNode from '@/components/workflow/nodes/FileReaderNode.vue'
import FileWriterNode from '@/components/workflow/nodes/FileWriterNode.vue'
import WebScraperNode from '@/components/workflow/nodes/WebScraperNode.vue'
import CsvTransformNode from '@/components/workflow/nodes/CsvTransformNode.vue'
import JsonTransformNode from '@/components/workflow/nodes/JsonTransformNode.vue'

// 注册节点类型（markRaw 防止 Vue 代理导致 VueFlow 读取失败）
const nodeTypes = markRaw({
  start: StartNode, end: EndNode, llm: LLMNode, prompt: PromptNode,
  condition: ConditionNode, loop: LoopNode, input: InputNode, output: OutputNode,
  code: CodeNode, variable: VariableNode, tool: ToolNode, http: HttpNode,
  switch: SwitchNode, delay: DelayNode, transform: TransformNode, email: EmailNode,
  subworkflow: SubworkflowNode, image_generation: ImageGenerationNode,
  video_generation: VideoGenerationNode, audio_generation: AudioGenerationNode,
  subtitle_generation: SubtitleGenerationNode, image_editing: ImageEditingNode,
  dataset_upload: DatasetUploadNode, data_annotation: DataAnnotationNode,
  data_augmentation: DataAugmentationNode, model_training: ModelTrainingNode,
  model_evaluation: ModelEvaluationNode, model_deployment: ModelDeploymentNode,
  website_generator: WebsiteGeneratorNode, document_loader: DocumentLoaderNode,
  embedding: EmbeddingNode, vector_store: VectorStoreNode, retriever: RetrieverNode,
  reranker: RerankerNode, agent: AgentNode, planner: PlannerNode,
  executor: ExecutorNode, memory: MemoryNode, file_reader: FileReaderNode,
  file_writer: FileWriterNode, web_scraper: WebScraperNode,
  csv_transform: CsvTransformNode, json_transform: JsonTransformNode,
})

// 确保 VueFlow 在组件完全注册后再渲染
const canvasReady = ref(false)

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const appStore = useAppStore()

const workflowId = computed(() => route.params.id)

const workflow = computed(() => workflowStore.currentWorkflow)
const nodes = ref([])
const edges = ref([])

function syncWorkflowToCanvas() {
  if (!workflow.value) return
  // workflow.value.nodes 已经由 store 的 fetchWorkflow 通过 backendWorkflowToFrontend 转换好了
  nodes.value = (workflow.value.nodes || []).map(n => ({
    id: String(n.id),
    type: n.type, // 已是转换后的 type（backendNodeToVueFlow 已处理）
    position: { x: Number(n.position?.x) || 0, y: Number(n.position?.y) || 0 },
    data: { ...n.data }
  }))
  edges.value = (workflow.value.edges || []).map(e => ({
    id: String(e.id),
    source: String(e.source),
    target: String(e.target),
    label: e.label
  }))
}

// 传递非响应式的 nodeTypes 快照给 VueFlow
const nodeTypesSnapshot = Object.assign({}, nodeTypes)

watch(workflow, syncWorkflowToCanvas, { immediate: false })
const executionHistory = computed(() => workflowStore.executionHistory)

const viewport = ref({ x: 50, y: 50, zoom: 1 })
const zoom = ref(1)
const selectedNodeId = ref(null)

onMounted(async () => {
  try {
    await workflowStore.fetchWorkflow(workflowId.value)
    await workflowStore.fetchExecutionHistory(workflowId.value)
    canvasReady.value = true
  } catch (err) {
    appStore.error('加载工作流失败')
  }
})

function handleBack() {
  router.push('/workflows')
}

function goToEdit() {
  router.push(`/workflows/${workflowId.value}/edit`)
}

function goToExecute() {
  router.push(`/workflows/${workflowId.value}/execute`)
}

async function handleDuplicate() {
  try {
    const newWorkflow = {
      name: `${workflow.value.name} (副本)`,
      description: workflow.value.description,
      nodes: workflow.value.nodes,
      edges: workflow.value.edges
    }
    await workflowStore.createWorkflow(newWorkflow)
    appStore.success('工作流复制成功')
  } catch (err) {
    appStore.error('复制失败')
  }
}

function selectNode(nodeId) {
  selectedNodeId.value = selectedNodeId.value === nodeId ? null : nodeId
}

function onNodeClick(event) {
  selectedNodeId.value = event.node.id
}

function zoomIn() {
  zoom.value = Math.min(2, zoom.value + 0.1)
}

function zoomOut() {
  zoom.value = Math.max(0.5, zoom.value - 0.1)
}

function fitView() {
  viewport.value = { x: 50, y: 50, zoom: 1 }
}

async function refreshHistory() {
  try {
    await workflowStore.fetchExecutionHistory(workflowId.value)
  } catch (err) {
    appStore.error('刷新失败')
  }
}

function viewExecution(execution) {
  router.push(`/workflows/${workflowId.value}/execute?execution=${execution.id}`)
}

async function retryExecution(execution) {
  try {
    await workflowStore.executeWorkflow({})
    appStore.success('执行已启动')
    await refreshHistory()
  } catch (err) {
    appStore.error('重试失败')
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

function getNodeTypeLabel(type) {
  const labelMap = {
    start: '开始',
    end: '结束',
    input: '输入',
    llm: '大语言模型',
    prompt: '提示词',
    condition: '条件判断',
    tool: '工具',
    output: '输出'
  }
  return labelMap[type] || type
}

function getNodeIcon(type) {
  const icons = {
    start: PlayCircle,
    end: Circle,
    input: FileText,
    llm: Zap,
    prompt: MessageSquare,
    condition: GitBranch,
    tool: Hammer,
    output: User
  }
  return icons[type] || Circle
}

function getExecutionStatusType(status) {
  const typeMap = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: ''
  }
  return typeMap[status] || 'info'
}

function getExecutionStatusLabel(status) {
  const labelMap = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return labelMap[status] || status
}

function getTriggerTypeLabel(type) {
  const labelMap = {
    manual: '手动',
    webhook: 'Webhook',
    scheduled: '定时',
    api: 'API'
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

function formatDateTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.workflow-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.detail-container {
  padding: $spacing-6;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-6;
  flex-wrap: wrap;
  gap: $spacing-4;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: $spacing-4;
}

.workflow-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.workflow-name {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0;
}

.workflow-meta {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.meta-text {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.header-actions {
  display: flex;
  gap: $spacing-3;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.detail-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: $spacing-6;
  margin-bottom: $spacing-6;
}

.workflow-canvas {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  overflow: hidden;
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  h3 {
    margin: 0;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }
}

.canvas-wrapper {
  height: 500px;
  flex: 1;
  background-color: var(--canvas-bg, var(--bg-secondary));
  border-radius: $radius-xl;
  border: 1px solid var(--border-primary);
  overflow: hidden;

  :deep(.vue-flow__background) {
    background-color: var(--canvas-bg, var(--bg-secondary));
  }

  :deep(.vue-flow__minimap) {
    background-color: var(--canvas-minimap-bg);
    border-radius: $radius-lg;
    border: 1px solid var(--border-primary);
  }
}

.detail-sidebar {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  overflow-y: auto;
  max-height: 500px;
}

.sidebar-section {
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
  }
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: $font-size-sm;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-primary);
  font-weight: $font-weight-medium;
}

.workflow-description {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0;
  line-height: $line-height-relaxed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-4;
}

.stat-item {
  text-align: center;
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
}

.stat-value {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: $color-primary;
}

.stat-label {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-top: $spacing-1;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
}

.nodes-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  max-height: 200px;
  overflow-y: auto;
}

.node-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: $radius-md;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: var(--border-hover);
  }

  &.selected {
    border-color: $color-primary;
    background-color: rgba($color-primary, 0.1);
  }
}

.node-icon {
  width: 18px;
  height: 18px;
  color: $color-primary;
}

.node-info {
  display: flex;
  flex-direction: column;
}

.node-name {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
}

.node-type {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.execution-history {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-4;

  h3 {
    margin: 0;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }
}

.loading-state {
  padding: $spacing-6;
}

@media (max-width: 1024px) {
  .detail-content {
    grid-template-columns: 1fr;
  }

  .detail-sidebar {
    max-height: none;
  }
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-4;
  }

  .detail-stats {
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .detail-stats {
    .stat-item {
      flex: 1 1 calc(50% - #{$spacing-3});
    }
  }
}

// ============================================================
// Detail 页画布样式 — 与 Editor 保持一致
// 节点类型边框色为设计常量保留，背景跟随主题
// ============================================================
.canvas-wrapper {
  height: 500px;
  flex: 1;
  background-color: var(--canvas-bg, var(--bg-secondary));
  border-radius: $radius-xl;
  border: 1px solid var(--border-primary);
  overflow: hidden;

  :deep(.vue-flow__background) {
    background-color: var(--canvas-bg, var(--bg-secondary));
  }

  :deep(.vue-flow__minimap) {
    background-color: var(--canvas-minimap-bg);
    border-radius: $radius-lg;
    border: 1px solid var(--border-primary);
  }

  // 节点边框跟随主题连线样式
  :deep(.vue-flow__node) {
    cursor: pointer;

    &.vue-flow__node-start .node-card,
    &.vue-flow__node-start .node-wrapper {
      border-left: 3px solid #10b981;
    }

    &.vue-flow__node-end .node-card,
    &.vue-flow__node-end .node-wrapper {
      border-left: 3px solid #ef4444;
    }

    &.vue-flow__node-llm .node-card,
    &.vue-flow__node-llm .node-wrapper {
      border-left: 3px solid #3b82f6;
    }

    &.vue-flow__node-prompt .node-card,
    &.vue-flow__node-prompt .node-wrapper {
      border-left: 3px solid #f59e0b;
    }

    &.vue-flow__node-input .node-card,
    &.vue-flow__node-input .node-wrapper {
      border-left: 3px solid #06b6d4;
    }

    &.vue-flow__node-output .node-card,
    &.vue-flow__node-output .node-wrapper {
      border-left: 3px solid #84cc16;
    }

    &.vue-flow__node-code .node-card,
    &.vue-flow__node-code .node-wrapper {
      border-left: 3px solid #f97316;
    }
  }

  :deep(.vue-flow__edge-path) {
    stroke: var(--border-primary);
    stroke-width: 2;

    &.animated {
      stroke: #3b82f6;
    }
  }

  :deep(.vue-flow__edge-text) {
    fill: var(--text-secondary);
    font-size: 11px;
  }
}

.canvas-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  font-size: $font-size-sm;
}
</style>
