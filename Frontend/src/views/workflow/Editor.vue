<template>
  <div class="workflow-editor">
    <el-alert
      v-if="!canEditWorkflow && !isNewWorkflow"
      class="editor-readonly-alert"
      type="warning"
      :closable="false"
      show-icon
      title="当前为只读模式：您不是此工作流的所有者，无法保存修改。请使用「复制」创建副本后再编辑。"
    />
    <!-- 顶部工具栏 -->
    <header class="editor-toolbar">
      <!-- 左侧：返回 + 工作流名称 -->
      <div class="toolbar-section toolbar-section--left">
        <el-tooltip
          content="返回工作流列表"
          placement="bottom"
        >
          <el-button
            :icon="ArrowLeft"
            class="toolbar-back-btn"
            @click="handleBack"
          />
        </el-tooltip>
        <div class="workflow-name-wrapper">
          <input
            v-model="workflowName"
            class="workflow-name-input"
            placeholder="输入工作流名称..."
            @blur="handleNameBlur"
          >
          <span
            v-if="isDirty"
            class="unsaved-indicator"
          >未保存</span>
        </div>
      </div>

      <!-- 中间：画布操作（缩放/撤销重做/连线/添加） -->
      <div class="toolbar-section toolbar-section--center">
        <div class="toolbar-btn-group">
          <el-tooltip
            content="放大画布"
            placement="bottom"
          >
            <el-button
              :icon="ZoomIn"
              @click="handleZoomIn"
            />
          </el-tooltip>
          <el-tooltip
            content="缩小画布"
            placement="bottom"
          >
            <el-button
              :icon="ZoomOut"
              @click="handleZoomOut"
            />
          </el-tooltip>
          <el-tooltip
            content="适应窗口"
            placement="bottom"
          >
            <el-button
              :icon="Maximize2"
              @click="handleFitView"
            />
          </el-tooltip>
        </div>
        <div class="toolbar-btn-group">
          <el-tooltip
            content="撤销 (Ctrl+Z)"
            placement="bottom"
          >
            <el-button
              :icon="Undo"
              :disabled="!canUndo"
              @click="handleUndo"
            />
          </el-tooltip>
          <el-tooltip
            content="重做 (Ctrl+Y)"
            placement="bottom"
          >
            <el-button
              :icon="Redo"
              :disabled="!canRedo"
              @click="handleRedo"
            />
          </el-tooltip>
        </div>
        <div class="toolbar-btn-group toolbar-btn-group--single">
          <el-tooltip
            :content="autoConnectMode ? '退出连线模式' : '连线模式'"
            placement="bottom"
          >
            <el-button
              :type="autoConnectMode ? 'primary' : 'default'"
              :icon="Link2"
              size="small"
              @click="autoConnectMode ? cancelAutoConnect() : enableAutoConnectMode()"
            >
              连线
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="右键画布快速添加节点"
            placement="bottom"
          >
            <el-button
              :icon="Plus"
              size="small"
              @click="openQuickAddMenuFromToolbar"
            >
              添加
            </el-button>
          </el-tooltip>
          <el-dropdown
            trigger="click"
            @command="handleAutoLayout"
          >
            <template #default>
              <el-button
                :icon="Layout"
                size="small"
                title="自动排列节点"
              >
                布局
                <ChevronDown
                  :size="12"
                  class="toolbar-btn-icon-right"
                />
              </el-button>
            </template>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="horizontal">
                  <ArrowRight :size="14" />
                  水平排列（从左到右）
                </el-dropdown-item>
                <el-dropdown-item command="vertical">
                  <ArrowDown :size="14" />
                  垂直排列（从上到下）
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-tooltip
            content="触发器配置"
            placement="bottom"
          >
            <el-button
              :icon="Clock"
              size="small"
              @click="openTriggerConfig"
            >
              触发器
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <!-- 右侧：操作按钮 -->
      <div class="toolbar-section toolbar-section--right">
        <!-- 核心操作：验证 + 保存 + 执行 — 始终显示 -->
        <el-tooltip
          content="验证工作流配置"
          placement="bottom"
        >
          <el-button
            :icon="AlertCircle"
            class="toolbar-core-btn"
            @click="handleValidate"
          >
            <span class="btn-label">验证</span>
          </el-button>
        </el-tooltip>
        <el-tooltip
          content="保存工作流 (Ctrl+S)"
          placement="bottom"
        >
          <el-button
            :icon="Save"
            :loading="isSaving"
            :disabled="!canEditWorkflow"
            class="toolbar-core-btn"
            @click="handleSave"
          >
            <span class="btn-label">保存</span>
          </el-button>
        </el-tooltip>
        <el-tooltip
          :content="isExecuting ? '工作流执行中' : (hasExecutionHistory ? '再次运行工作流' : '立即运行工作流')"
          placement="bottom"
        >
          <el-button
            type="primary"
            :icon="Play"
            :loading="isExecuting"
            :disabled="isExecuting"
            class="toolbar-core-btn toolbar-core-btn--primary"
            @click="handleExecute"
          >
            <span class="btn-label">{{ executeButtonLabel }}</span>
          </el-button>
        </el-tooltip>
        <el-tooltip
          v-if="showExecutionResumeEntry"
          content="查看最近一次执行结果"
          placement="bottom"
        >
          <el-button
            :icon="PanelBottomOpen"
            class="toolbar-core-btn"
            @click="reopenExecutionPanel"
          >
            <span class="btn-label">查看执行</span>
          </el-button>
        </el-tooltip>

        <!-- 折叠按钮：小屏幕时显示展开菜单 -->
        <el-dropdown
          trigger="click"
          class="toolbar-more-dropdown"
          @command="(cmd) => handleToolbarCommand(cmd)"
        >
          <template #default>
            <el-button
              :icon="MoreHorizontal"
              class="toolbar-more-btn"
              title="更多操作"
            />
          </template>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="variable">
                <VariableIcon
                  :size="15"
                  style="margin-right: 8px;"
                />
                变量管理
              </el-dropdown-item>
              <el-dropdown-item command="assistant">
                <MessageSquare
                  :size="15"
                  style="margin-right: 8px;"
                />
                AI 助手
              </el-dropdown-item>
              <el-dropdown-item command="theme">
                <PanelRightClose
                  :size="15"
                  style="margin-right: 8px;"
                />
                切换主题
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="editor-container">
      <!-- 左侧节点面板 -->
      <aside class="node-panel">
        <div class="panel-section">
          <h3 class="panel-title">
            流程节点
          </h3>

          <!-- 搜索框 -->
          <div class="node-search">
            <el-input
              v-model="nodeSearchQuery"
              placeholder="搜索节点..."
              :prefix-icon="Search"
              clearable
              size="small"
            />
          </div>

          <!-- n8n 风格动态分类节点面板 -->
          <div
            v-for="category in filteredNodeCategories"
            :key="category.id"
            class="node-category"
          >
            <div class="category-header">
              <component
                :is="category.icon"
                class="category-icon"
              />
              <span>{{ category.label }}</span>
              <span class="category-count">{{ category.nodes.length }}</span>
            </div>
            <div
              v-for="node in category.nodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                v-if="node.shortcut"
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 空状态 -->
          <div
            v-if="!hasAnyNodes"
            class="node-empty"
          >
            <Search class="empty-icon" />
            <span>未找到匹配的节点</span>
          </div>
        </div>
      </aside>

      <!-- 中间画布 -->
      <main
        class="canvas-wrapper"
        :class="{ 'connect-mode-active': autoConnectMode }"
        @drop="onDrop"
        @dragover.prevent
        @contextmenu="onPaneContextMenu"
        @dblclick="onPaneDoubleClick"
      >
        <VueFlow
          ref="vueFlowRef"
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :default-viewport="viewport"
          :min-zoom="WORKFLOW_CANVAS_ZOOM.min"
          :max-zoom="WORKFLOW_CANVAS_ZOOM.max"
          :snap-to-grid="snapToGrid"
          :snap-grid="[16, 16]"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @pane-click="onPaneClick"
          @nodes-change="handleNodesChange"
          @edges-change="handleEdgesChange"
          @node-drag="onNodeDrag"
          @node-drag-stop="onNodeDragStop"
          @connect="onConnect"
          @node-context-menu="onNodeContextMenu"
          @nodes-initialized="onNodesInitialized"
          @node-mouse-enter="onNodeMouseEnter"
          @node-mouse-leave="onNodeMouseLeave"
          @viewport-change="onViewportChange"
        >
          <!-- Custom node type templates（其余类型由 nodeTypes 自动渲染） -->
          <template #node-llm="{ id, data, selected }">
            <WorkflowNodeHost
              :id="id"
              :node-component="LLMNode"
              :data="data"
              :selected="selected"
              :extra-props="{ runtimeState: executionNodeStateMap[id] }"
            />
          </template>
          <Background
            pattern-color="#1a1a2e"
            :gap="16"
          />
          <Controls />
          <MiniMap
            v-show="showMiniMap"
            :node-types="nodeTypes"
            :node-color="minimapNodeColor"
            :node-stroke-width="3"
            mask-color="rgba(15, 15, 30, 0.7)"
            class="editor-minimap"
          />
        </VueFlow>

        <!-- 空状态提示 -->
        <div
          v-if="nodes.length === 0"
          class="empty-canvas"
        >
          <div class="empty-content">
            <div class="empty-icon-wrapper">
              <GitBranch class="empty-icon" />
            </div>
            <h3>开始创建工作流</h3>
            <p>从左侧面板拖拽节点到画布，或右键/双击画布快速添加</p>
            <div class="quick-hint-row">
              <kbd>S</kbd><span>开始</span>
              <kbd>E</kbd><span>结束</span>
              <kbd>A</kbd><span>LLM</span>
              <kbd>I</kbd><span>输入</span>
              <kbd>O</kbd><span>输出</span>
            </div>
          </div>
        </div>

        <!-- 快速添加菜单 (右键菜单) -->
        <div
          v-if="showQuickAddMenu"
          class="quick-add-menu"
          :style="{ left: quickAddMenuPos.x + 'px', top: quickAddMenuPos.y + 'px' }"
          @contextmenu.prevent
        >
          <div class="quick-add-header">
            <Plus class="menu-icon" />
            <span>快速添加节点</span>
            <button
              class="close-btn"
              @click="closeQuickAddMenu"
            >
              <X class="btn-icon" />
            </button>
          </div>
          <div class="quick-add-body">
            <div
              v-for="category in quickAddCategories"
              :key="category.id"
              class="quick-add-section"
            >
              <div class="section-label">
                {{ category.label }}
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in category.nodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 自动连线模式指示器 -->
        <div
          v-if="autoConnectMode"
          class="auto-connect-indicator"
        >
          <Link2 class="indicator-icon" />
          <span>连线模式: 点击目标节点完成连线</span>
          <el-button
            size="small"
            @click="cancelAutoConnect"
          >
            取消 (ESC)
          </el-button>
        </div>

        <!-- 节点数量统计 -->
        <div class="canvas-status-bar">
          <span class="status-item">
            <span
              class="status-dot"
              style="background: #3b82f6;"
            />
            {{ nodes.length }} 个节点
          </span>
          <span class="status-item">
            <span
              class="status-dot"
              style="background: #10b981;"
            />
            {{ edges.length }} 条连线
          </span>
          <span
            v-if="autoConnectMode"
            class="status-item connect-mode"
          >
            <Link2 class="status-icon" />
            连线模式
          </span>
        </div>
      </main>

      <!-- 右侧属性面板 -->
      <PropertyPanel
        :selected-node="selectedNode"
        @change="handleNodePropertyChange"
        @delete="handleDeleteNodeById"
      />
    </div>

    <!-- 验证结果对话框 -->
    <el-dialog
      v-model="showValidateDialog"
      title="工作流验证"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="true"
    >
      <div
        v-if="validationResult.valid"
        class="validate-success"
      >
        <CheckCircle class="success-icon" />
        <p>工作流结构验证通过</p>
      </div>
      <div
        v-else
        class="validate-errors"
      >
        <div
          v-if="validationResult.errors?.length"
          class="error-list"
        >
          <h4>错误</h4>
          <ul>
            <li
              v-for="(error, index) in validationResult.errors"
              :key="index"
            >
              {{ error }}
            </li>
          </ul>
        </div>
        <div
          v-if="validationResult.warnings?.length"
          class="warning-list"
        >
          <h4>警告</h4>
          <ul>
            <li
              v-for="(warning, index) in validationResult.warnings"
              :key="index"
            >
              {{ warning }}
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="showValidateDialog = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <!-- 触发器配置抽屉 -->
    <TriggerConfig
      v-model:visible="triggerConfigVisible"
      :workflow-id="workflowId"
    />

    <!-- 变量管理面板 -->
    <VariablePanel
      v-model="variablePanelVisible"
      :workflow-id="workflowId"
      :nodes="nodes"
    />

    <!-- AI 工作流助手 -->
    <WorkflowAssistant
      v-model="showAssistant"
      :nodes="nodes"
      :edges="edges"
      :workflow-name="workflowName"
      @apply-workflow="handleAssistantApplyWorkflow"
      @highlight-nodes="handleOptimizerHighlight"
      @apply-fix="handleOptimizerApplyFix"
    />

    <!-- 底部执行面板 -->
    <Transition name="slide-up">
      <div
        v-if="showExecutionPanel"
        class="execution-bottom-panel"
        :class="{ 'is-dragging': isDraggingPanel }"
        :style="{ height: executionPanelHeight + 'px' }"
      >
        <!-- 拖拽把手（双击折叠，拖拽调整高度） -->
        <div
          class="exec-panel-handle"
          title="拖拽调整高度 / 双击折叠"
          @mousedown.prevent="onPanelDragStart"
          @touchstart.prevent="onPanelDragStart"
          @dblclick="closeExecutionPanel"
        />

        <!-- 面板头部 -->
        <div class="exec-panel-header">
          <div class="exec-header-left">
            <Zap class="exec-icon" />
            <span class="exec-title">执行状态</span>
            <el-tag
              :type="executionStatus === 'completed' ? 'success' : executionStatus === 'failed' ? 'danger' : executionStatus === 'running' ? 'warning' : 'info'"
              size="small"
            >
              {{ executionStatus === 'idle' ? '就绪' : executionStatus === 'running' ? '执行中' : executionStatus === 'completed' ? '已完成' : executionStatus === 'cancelled' ? '已取消' : '失败' }}
            </el-tag>
            <span class="exec-node-count">
              {{ completedNodeCount }}/{{ nodes.length }} 节点
            </span>
          </div>
          <div class="exec-header-right">
            <span
              v-if="executionElapsed"
              class="exec-elapsed"
            >{{ executionElapsed }}</span>
            <el-button
              v-if="executionStatus === 'running'"
              type="danger"
              size="small"
              @click="cancelExecution"
            >
              取消
            </el-button>
            <el-button
              v-if="executionStatus === 'completed' || executionStatus === 'failed'"
              size="small"
              @click="startExecution"
            >
              重试
            </el-button>
            <el-button
              size="small"
              @click="closeExecutionPanel"
            >
              <X class="btn-icon" />
            </el-button>
          </div>
        </div>

        <!-- 三栏主体 -->
        <div class="exec-panel-body">
          <!-- 左栏：节点执行时间线 -->
          <div class="exec-timeline">
            <div class="timeline-header">
              节点状态
            </div>
            <div
              ref="executionTimelineListRef"
              class="timeline-list"
            >
              <div
                v-for="node in executionNodeList"
                :key="node.id"
                :ref="(el) => setExecutionTimelineNodeRef(el, node.id)"
                class="timeline-item"
                :class="[
                  `node-${node.status}`,
                  { 'is-selected': selectedExecNode?.id === node.id }
                ]"
                @click="selectedExecNode = node"
              >
                <div class="timeline-status">
                  <Loader
                    v-if="node.status === 'running'"
                    class="tl-icon spinning"
                  />
                  <Check
                    v-else-if="node.status === 'completed'"
                    class="tl-icon success"
                  />
                  <X
                    v-else-if="node.status === 'failed'"
                    class="tl-icon error"
                  />
                  <Circle
                    v-else
                    class="tl-icon pending"
                  />
                </div>
                <div class="timeline-info">
                  <span class="tl-name">{{ node.name }}</span>
                  <span class="tl-type">{{ node.type }}</span>
                </div>
              </div>
              <div
                v-if="!executionNodeList.length"
                class="timeline-empty"
              >
                暂无执行数据
              </div>
            </div>
          </div>

          <!-- 中栏：节点输出卡片 -->
          <div class="exec-output">
            <div class="output-header">
              <span>输出详情</span>
              <span
                v-if="selectedExecNode"
                class="output-node-name"
              >{{ selectedExecNode.name }}</span>
            </div>
            <div class="output-content">
              <template v-if="selectedExecNode">
                <div
                  v-if="selectedExecNode.status === 'running'"
                  class="output-running"
                >
                  <Loader class="output-spinner spinning" />
                  <span>执行中...</span>
                </div>
                <div
                  v-else-if="selectedExecNode.status === 'completed'"
                  class="output-success"
                >
                  <Check class="output-check success" />
                  <span>执行完成</span>
                  <pre class="output-data">{{ formatNodeOutput(selectedExecNode.output) }}</pre>
                </div>
                <div
                  v-else-if="selectedExecNode.status === 'failed'"
                  class="output-error"
                >
                  <X class="output-check error" />
                  <span>执行失败</span>
                  <div class="output-err-detail">
                    {{ selectedExecNode.error || '未知错误' }}
                  </div>
                </div>
                <div
                  v-else
                  class="output-pending"
                >
                  <span>等待执行</span>
                </div>
              </template>
              <div
                v-else
                class="output-placeholder"
              >
                <span>点击左侧节点查看详情</span>
              </div>
            </div>
          </div>

          <!-- 右栏：执行进度摘要 -->
          <div class="exec-summary">
            <div class="summary-header">
              执行摘要
            </div>
            <div class="summary-stats">
              <div class="stat-item">
                <span class="stat-label">总节点</span>
                <span class="stat-value">{{ nodes.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已完成</span>
                <span class="stat-value success">{{ completedNodeCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">进行中</span>
                <span class="stat-value running">{{ runningNodeCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">失败</span>
                <span class="stat-value error">{{ failedNodeCount }}</span>
              </div>
            </div>

            <!-- 进度条 -->
            <div class="summary-progress">
              <div class="progress-track">
                <div
                  class="progress-fill"
                  :style="{ width: executionProgressPct + '%' }"
                />
              </div>
              <span class="progress-pct">{{ executionProgressPct }}%</span>
            </div>

            <!-- 日志流 -->
            <div class="summary-logs">
              <div class="logs-header">
                执行日志
              </div>
              <div
                ref="execPanelBodyRef"
                class="logs-scroll"
              >
                <div
                  v-for="(log, idx) in executionLogs"
                  :key="idx"
                  class="exec-log-item"
                  :class="`log-${log.type}`"
                >
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-text">{{ log.text }}</span>
                </div>
                <div
                  v-if="executionStatus === 'running'"
                  class="exec-loading"
                >
                  <span class="exec-spinner" />
                  <span>执行中...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
defineOptions({ name: 'WorkflowEditor' })

import { ref, computed, onMounted, onUnmounted, onActivated, watch, shallowRef, nextTick, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkflowStore } from '@/stores/workflow'
import { useExecutionStore } from '@/stores/execution'
import { autoLayoutWorkflow, applyWorkflowLayout, needsAutoLayout, resolveNodeCollision } from '@/utils/workflowLayout'
import { captureWorkflowCanvas, buildVueFlowCaptureApi } from '@/utils/workflowCanvasCapture'
import { resolveWorkflowCanvasPreview } from '@/utils/workflowPreview'
import { nlWorkflowToVueFlow, normalizeNodeConfig, syncCanvasAfterSave, ensureMultimodalWorkflowGraph } from '@/utils/workflowTransform'
import {
  migrateNodeRuntimeCache,
  remapExecutionStoreNodeIds,
  remapRecordByIdMap,
} from '@/utils/nodeRuntimePersistence'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import {
  ArrowLeft, Save, Play, ZoomIn, ZoomOut,
  Maximize2, Undo, Redo, CheckCircle,
  AlertCircle, GitBranch,
  Circle, Zap, MessageSquare,
  Variable as VariableIcon,
  Search,
  Plus, Link2, Clock, X,
  MoreHorizontal, ChevronDown, PanelRightClose, PanelBottomOpen,
  Loader, Check, Layout, ArrowDown, ArrowRight
} from 'lucide-vue-next'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import {
  filterNodeCategories,
  getDefaultNodeConfig,
  getMinimapNodeColor,
  getNodeMeta,
  NODE_CATEGORIES,
} from '@/config/nodeRegistry'
import { buildNodeTypesMap } from '@/config/nodeComponents'
import LLMNode from '@/components/workflow/nodes/LLMNode.vue'
import WorkflowNodeHost from '@/components/workflow/WorkflowNodeHost.vue'
import VariablePanel from '@/views/workflow/VariablePanel.vue'
import PropertyPanel from '@/components/workflow/PropertyPanel.vue'
import TriggerConfig from './TriggerConfig.vue'
import WorkflowAssistant from '@/components/workflow/WorkflowAssistant.vue'
import { YOLO_WORKFLOW_TEMPLATE } from '@/config/yoloWorkflowTemplate'
import { CLIP_RETRIEVAL_WORKFLOW_TEMPLATE } from '@/config/clipRetrievalWorkflowTemplate'
import { WORKFLOW_CANVAS_VIEWPORT, WORKFLOW_CANVAS_ZOOM, WORKFLOW_SELECT_NODE_KEY } from '@/config/workflowCanvas'
import workflowApi from '@/api/workflow'
import { prepareDesktopClipIndexes } from '@/composables/useClipIndexDesktop'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const appStore = useAppStore()
const authStore = useAuthStore()
const executionStore = useExecutionStore()

const workflowId = computed(() => route.params.id)
const isNewWorkflow = computed(() => workflowId.value === 'new' || !workflowId.value)

const canEditWorkflow = computed(() => {
  if (isNewWorkflow.value) return true
  const wf = workflowStore.currentWorkflow
  if (!wf) return true
  if (typeof wf.canEdit === 'boolean') return wf.canEdit
  const ownerId = wf.owner?.id ?? wf.ownerId
  const userId = authStore.user?.id
  if (authStore.user?.isSuperuser) return true
  if (ownerId != null && userId != null) return Number(ownerId) === Number(userId)
  return true
})

const workflowName = ref('未命名工作流')
const isDirty = ref(false)
const isSaving = computed(() => workflowStore.isSaving)
const showValidateDialog = ref(false)
const validationResult = ref({ valid: true, errors: [], warnings: [] })
const triggerConfigVisible = ref(false)
const variablePanelVisible = ref(false)
const showAssistant = ref(false)

// 执行面板状态
const showExecutionPanel = ref(false)
const executionPanelHeight = ref(320) // 可拖拽调整高度
const isDraggingPanel = ref(false)
const executionId = ref(null)
const executionStatus = ref('idle') // idle | running | completed | failed | cancelled
const executionLogs = ref([]) // { type: 'info'|'success'|'error', time: string, text: string }
const executionNodeStateMap = ref({})
const executionSessionId = ref(0)
const seenExecutionLogKeys = ref(new Set())
const executionDurationMs = ref(null)
const executionStartTime = ref(null)
const selectedExecNode = ref(null)
const elapsedTick = ref(0) // 触发 executionElapsed 重新计算

const executionNodeList = computed(() => {
  return nodes.value.map((n) => {
    const runtimeState = executionNodeStateMap.value[n.id] || {}
    return {
      id: n.id,
      name: n.data?.label || n.label || n.id,
      type: n.type,
      status: runtimeState.status || 'pending',
      output: runtimeState.output ?? null,
      error: runtimeState.error ?? null
    }
  })
})

const completedNodeCount = computed(() => executionNodeList.value.filter(n => n.status === 'completed').length)
const runningNodeCount = computed(() => executionNodeList.value.filter(n => n.status === 'running').length)
const failedNodeCount = computed(() => executionNodeList.value.filter(n => n.status === 'failed').length)

const executionProgressPct = computed(() => {
  if (!nodes.value.length) return 0
  return Math.round((completedNodeCount.value / nodes.value.length) * 100)
})

const executionElapsed = computed(() => {
  if (!executionStartTime.value) return null

  const durationMs = executionStatus.value === 'running'
    ? null
    : executionDurationMs.value

  const ms = durationMs ?? (Date.now() - executionStartTime.value)
  elapsedTick.value // 依赖响应式，触发更新
  return formatExecutionDuration(Math.max(0, ms))
})

const hasExecutionHistory = computed(() => {
  return executionLogs.value.length > 0 || Object.keys(executionNodeStateMap.value).length > 0 || executionStatus.value !== 'idle'
})

const showExecutionResumeEntry = computed(() => {
  return !showExecutionPanel.value && hasExecutionHistory.value
})

const isExecuting = computed(() => ['running', 'pending', 'paused', 'queued'].includes(executionStatus.value))

const executeButtonLabel = computed(() => {
  if (isExecuting.value) return '执行中'
  if (hasExecutionHistory.value && executionStatus.value !== 'idle') return '再次执行'
  return '执行'
})

function formatNodeOutput(output) {
  if (!output) return ''
  if (typeof output === 'string') return output
  try { return JSON.stringify(output, null, 2) } catch { return String(output) }
}

function formatExecutionDuration(durationMs) {
  if (durationMs == null || Number.isNaN(durationMs)) return ''

  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function createExecutionLog(type, text) {
  return {
    type,
    time: new Date().toLocaleTimeString(),
    text
  }
}

function getErrorMessage(error, fallback = '操作失败') {
  const responseData = error?.response?.data
  if (typeof responseData?.detail === 'string' && responseData.detail) return responseData.detail
  if (typeof responseData?.message === 'string' && responseData.message) return responseData.message
  if (typeof responseData?.error === 'string' && responseData.error) return responseData.error
  if (typeof error?.message === 'string' && error.message) return error.message
  return fallback
}

function resetExecutionState() {
  executionSessionId.value += 1
  executionId.value = null
  executionStatus.value = 'idle'
  executionLogs.value = []
  executionNodeStateMap.value = {}
  executionDurationMs.value = null
  executionStartTime.value = null
  selectedExecNode.value = null
  elapsedTick.value = 0
  seenExecutionLogKeys.value = new Set()
  if (elapsedTimer.value) {
    clearInterval(elapsedTimer.value)
    elapsedTimer.value = null
  }
  executionStore.reset()
}

function startExecutionElapsedTimer(sessionId = executionSessionId.value) {
  if (elapsedTimer.value) {
    clearInterval(elapsedTimer.value)
    elapsedTimer.value = null
  }
  executionStartTime.value = executionStartTime.value || Date.now()
  elapsedTimer.value = setInterval(() => {
    if (executionSessionId.value !== sessionId) return
    elapsedTick.value += 1
  }, 1000)
}

function stopExecutionElapsedTimer() {
  if (elapsedTimer.value) {
    clearInterval(elapsedTimer.value)
    elapsedTimer.value = null
  }
}

function appendExecutionLogsFromSnapshot(execution) {
  const nodeExecutions = execution?.node_executions || execution?.nodeExecutions || []
  nodeExecutions.forEach((nodeExecution) => {
    const nodeId = nodeExecution.node_id || nodeExecution.nodeId || nodeExecution.node || 'unknown'
    const status = nodeExecution.status || 'pending'
    const nodeName = nodeExecution.node_name || nodeExecution.nodeName || nodeId
    const detail = nodeExecution.error_message || nodeExecution.errorMessage || ''
    const outputData = nodeExecution.output_data ?? nodeExecution.outputData ?? nodeExecution.output ?? null
    const normalizedOutput = outputData == null
      ? ''
      : typeof outputData === 'string'
        ? outputData
        : JSON.stringify(outputData)
    const logKey = `${nodeId}:${status}:${detail}:${normalizedOutput}`
    if (seenExecutionLogKeys.value.has(logKey)) return
    seenExecutionLogKeys.value.add(logKey)

    executionLogs.value.push(createExecutionLog(
      status === 'failed' ? 'error' : status === 'completed' ? 'success' : 'info',
      `${nodeName}: ${status}${detail ? ` — ${detail}` : ''}`
    ))
  })
}

function applyExecutionSnapshotLocal(execution, nodeStateMap) {
  if (execution?.durationMs != null) {
    executionDurationMs.value = Number(execution.durationMs) || 0
  } else if (execution?.duration_ms != null) {
    executionDurationMs.value = Number(execution.duration_ms) || 0
  } else if (execution?.duration_seconds != null) {
    executionDurationMs.value = Number(execution.duration_seconds) * 1000 || 0
  } else if (execution?.durationSeconds != null) {
    executionDurationMs.value = Number(execution.durationSeconds) * 1000 || 0
  } else if (execution?.duration != null) {
    executionDurationMs.value = Number(execution.duration) * 1000 || 0
  }

  executionNodeStateMap.value = nodeStateMap || {}
  ensureExecutionFocusNode()
}

function handleEditorExecutionSnapshot(execution, nodeStateMap) {
  if (!execution) return
  const sessionId = executionSessionId.value
  const prevStatus = executionStatus.value
  applyExecutionSnapshotLocal(execution, nodeStateMap)
  executionStatus.value = execution.status || executionStatus.value
  appendExecutionLogsFromSnapshot(execution)

  if (execution.status === 'completed' && prevStatus !== 'completed') {
    stopExecutionElapsedTimer()
    const durationText = formatExecutionDuration(executionDurationMs.value)
    executionLogs.value.push(createExecutionLog('success', `执行完成${durationText ? ` (耗时 ${durationText})` : ''}`))
    return
  }
  if (execution.status === 'failed' && prevStatus !== 'failed') {
    stopExecutionElapsedTimer()
    executionLogs.value.push(createExecutionLog('error', execution.error_message || execution.errorMessage || '执行失败'))
    return
  }
  if (execution.status === 'cancelled' && prevStatus !== 'cancelled') {
    stopExecutionElapsedTimer()
    executionLogs.value.push(createExecutionLog('info', '执行已取消'))
    return
  }

  if (['running', 'pending', 'paused', 'queued'].includes(execution.status)) {
    startExecutionElapsedTimer(sessionId)
  }
}

async function resumeWorkflowExecution() {
  if (isNewWorkflow.value || !workflowId.value) return

  executionStore.registerEditorSnapshotListener(workflowId.value, handleEditorExecutionSnapshot)

  try {
    const resumed = await executionStore.resumeEditorExecution(workflowId.value)
    if (!resumed) {
      if (Object.keys(executionStore.nodeStatusMap || {}).length > 0) {
        executionNodeStateMap.value = { ...executionStore.canvasNodeRuntime }
        executionStatus.value = executionStore.executionStatus
        showExecutionPanel.value = executionStatus.value !== 'idle'
      }
      return
    }

    executionId.value = resumed.executionId
    executionStatus.value = resumed.status || resumed.execution?.status || executionStore.executionStatus
    applyExecutionSnapshotLocal(resumed.execution, executionStore.canvasNodeRuntime)
    appendExecutionLogsFromSnapshot(resumed.execution)
    showExecutionPanel.value = true

    if (['running', 'pending', 'paused', 'queued'].includes(executionStatus.value)) {
      executionLogs.value.unshift(createExecutionLog('info', `已恢复执行监控，ID: ${resumed.executionId}`))
      startExecutionElapsedTimer()
    } else if (executionStatus.value === 'completed') {
      executionLogs.value.unshift(createExecutionLog('info', `已加载最近执行结果，ID: ${resumed.executionId}`))
    }
  } catch (error) {
    console.warn('[Editor] resume workflow execution failed:', error)
  }
}

function syncSelectedExecNode() {
  if (!selectedExecNode.value?.id) return
  const updatedNode = executionNodeList.value.find(node => node.id === selectedExecNode.value.id)
  if (!updatedNode) {
    selectedExecNode.value = null
    return
  }
  const current = selectedExecNode.value
  if (
    current.status === updatedNode.status
    && current.error === updatedNode.error
    && JSON.stringify(current.output) === JSON.stringify(updatedNode.output)
  ) {
    return
  }
  selectedExecNode.value = updatedNode
}

const executionTimelineListRef = ref(null)
const executionTimelineNodeRefs = ref({})

function setExecutionTimelineNodeRef(el, nodeId) {
  if (!nodeId) return

  if (el) {
    executionTimelineNodeRefs.value[nodeId] = el
    return
  }

  delete executionTimelineNodeRefs.value[nodeId]
}

async function scrollSelectedExecNodeIntoView() {
  await nextTick()

  const selectedId = selectedExecNode.value?.id
  if (!selectedId) return

  const container = executionTimelineListRef.value
  const nodeElement = executionTimelineNodeRefs.value[selectedId]
  if (!container || !nodeElement || typeof nodeElement.scrollIntoView !== 'function') return

  nodeElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}

function pickExecutionFocusNode() {
  const preferredNode = executionNodeList.value.find(node => node.status === 'failed')
    || executionNodeList.value.find(node => node.status === 'running')
    || executionNodeList.value.find(node => node.status === 'completed')
    || null

  if (preferredNode) {
    selectedExecNode.value = preferredNode
  }
}

function ensureExecutionFocusNode() {
  const previousSelectedId = selectedExecNode.value?.id || null

  if (selectedExecNode.value?.id) {
    syncSelectedExecNode()
  }

  if (!selectedExecNode.value?.id) {
    pickExecutionFocusNode()
  }

  if (selectedExecNode.value?.id && selectedExecNode.value.id !== previousSelectedId) {
    scrollSelectedExecNodeIntoView()
  }
}

function closeExecutionPanel() {
  showExecutionPanel.value = false
}

// ============================================
// 执行面板拖拽调整高度
// ============================================
let panelDragStartY = 0
let panelDragStartHeight = 0

function onPanelDragStart(e) {
  isDraggingPanel.value = true
  panelDragStartY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY
  panelDragStartHeight = executionPanelHeight.value
  document.addEventListener('mousemove', onPanelDragMove)
  document.addEventListener('mouseup', onPanelDragEnd)
  document.addEventListener('touchmove', onPanelDragMove, { passive: false })
  document.addEventListener('touchend', onPanelDragEnd)
  e.preventDefault()
}

function onPanelDragMove(e) {
  if (!isDraggingPanel.value) return
  const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY
  const delta = panelDragStartY - clientY
  const newHeight = Math.max(160, Math.min(window.innerHeight - 200, panelDragStartHeight + delta))
  executionPanelHeight.value = Math.round(newHeight)
  e.preventDefault()
}

function onPanelDragEnd() {
  isDraggingPanel.value = false
  document.removeEventListener('mousemove', onPanelDragMove)
  document.removeEventListener('mouseup', onPanelDragEnd)
  document.removeEventListener('touchmove', onPanelDragMove)
  document.removeEventListener('touchend', onPanelDragEnd)
}

function reopenExecutionPanel() {
  if (!hasExecutionHistory.value) return
  ensureExecutionFocusNode()
  showExecutionPanel.value = true
}


const viewport = ref({ ...WORKFLOW_CANVAS_VIEWPORT })
const showMiniMap = ref(false)
let minimapHideTimer = null
const MINIMAP_BASE_ZOOM = 1
const MINIMAP_HIDE_DELAY_MS = 1800
const snapToGrid = ref(true)
const vueFlowRef = ref(null)
const previewSyncInFlight = ref(false)
let previewSyncTimer = null

function getVueFlowCaptureApi() {
  return buildVueFlowCaptureApi({
    fitView,
    getViewport,
    setViewport,
    vueFlowRef,
  })
}

const selectedNode = ref(null)
const selectedEdge = ref(null)
const execPanelBodyRef = ref(null)
const elapsedTimer = ref(null)

const nodes = shallowRef([])
const edges = shallowRef([])

// 可用的模型和工具列表（从 API 获取）
const availableModels = ref([])
const availableTools = ref([])

// 历史记录（用于撤销/重做）
const history = ref([])
const historyIndex = ref(-1)

// ============================================================
// 核心新增功能：点击添加节点 + 自动连线
// ============================================================

// 快速添加菜单
const showQuickAddMenu = ref(false)
const quickAddMenuPos = ref({ x: 0, y: 0 })
const quickAddTargetPos = ref({ x: 0, y: 0 })

// 自动连线模式
const autoConnectMode = ref(false)
const autoConnectSourceNode = ref(null)
const autoConnectSourceHandle = ref(null)
const connectHoverTargetId = ref(null)

const CONNECT_VISUAL_CLASSES = [
  'connect-source',
  'connect-target-hover',
  'connect-target-valid',
  'connect-candidate',
]

function stripConnectVisualClass(className) {
  if (!className) return ''
  return className
    .split(/\s+/)
    .filter(c => c && !CONNECT_VISUAL_CLASSES.includes(c))
    .join(' ')
}

function syncConnectVisualClasses() {
  if (!autoConnectMode.value) {
    clearConnectVisuals()
    return
  }
  const sourceId = autoConnectSourceNode.value
  const hoverId = connectHoverTargetId.value
  nodes.value = nodes.value.map((n) => {
    const baseClass = stripConnectVisualClass(n.class)
    const classes = baseClass ? [baseClass] : []
    if (n.id === sourceId) {
      classes.push('connect-source')
    } else if (sourceId && n.id === hoverId) {
      classes.push('connect-target-hover')
    } else if (sourceId) {
      classes.push('connect-target-valid')
    } else {
      classes.push('connect-candidate')
    }
    const nextClass = classes.join(' ').trim()
    return { ...n, class: nextClass || undefined }
  })
}

function clearConnectVisuals() {
  connectHoverTargetId.value = null
  nodes.value = nodes.value.map((n) => {
    const nextClass = stripConnectVisualClass(n.class)
    return { ...n, class: nextClass || undefined }
  })
}

function onNodeMouseEnter({ node }) {
  if (!autoConnectMode.value || !node?.id) return
  if (autoConnectSourceNode.value && autoConnectSourceNode.value === node.id) return
  connectHoverTargetId.value = node.id
  syncConnectVisualClasses()
}

function onNodeMouseLeave({ node }) {
  if (!autoConnectMode.value || !node?.id) return
  if (connectHoverTargetId.value === node.id) {
    connectHoverTargetId.value = null
    syncConnectVisualClasses()
  }
}

function readInputNodeValue(node) {
  const cfg = node.data?.config || {}
  const el = document.getElementById(`user-input-${node.id}`)
  const domValue = el && 'value' in el ? String(el.value ?? '') : null
  const stored = cfg.userInput ?? cfg.user_input ?? cfg.default ?? cfg.value ?? ''
  const raw = domValue != null && domValue !== String(stored ?? '') ? domValue : stored
  return raw != null ? String(raw).trim() : ''
}

function flushCanvasInputValues() {
  nodes.value = nodes.value.map((node) => {
    const type = node.data?.type || node.type
    if (type !== 'input') return node
    const cfg = node.data?.config || {}
    const el = document.getElementById(`user-input-${node.id}`)
    if (!el || !('value' in el)) return node
    const value = String(el.value ?? '')
    const stored = cfg.userInput ?? cfg.user_input ?? cfg.default ?? ''
    if (value === String(stored ?? '')) return node
    return {
      ...node,
      data: {
        ...node.data,
        config: {
          ...cfg,
          userInput: value,
          user_input: value,
          default: value,
        },
      },
    }
  })
}

function collectEmptyInputNodes() {
  return nodes.value.filter((n) => {
    const type = n.data?.type || n.type
    if (type !== 'input') return false
    return !readInputNodeValue(n)
  })
}

function clearInputNeedsFlags() {
  nodes.value = nodes.value.map((n) => {
    if (!n.data?._needsInput) return n
    const nextData = { ...n.data }
    delete nextData._needsInput
    return { ...n, data: nextData }
  })
}

function markEmptyInputNodes(emptyNodes) {
  const emptyIds = new Set(emptyNodes.map(n => n.id))
  nodes.value = nodes.value.map((n) => ({
    ...n,
    data: {
      ...n.data,
      _needsInput: emptyIds.has(n.id),
    },
  }))
}

function focusEmptyInputNode(node) {
  if (!node) return
  selectedNode.value = node
  nextTick(() => {
    fitView({ nodes: [node.id], padding: WORKFLOW_CANVAS_ZOOM.fitViewPadding, duration: 450, maxZoom: WORKFLOW_CANVAS_ZOOM.fitViewMax })
    const textarea = document.getElementById(`user-input-${node.id}`)
    textarea?.focus()
  })
}

// 自动连线辅助：将节点按从上到下、从左到右排序
function getAutoConnectSuggestion(newNodeId) {
  const newNode = nodes.value.find(n => n.id === newNodeId)
  if (!newNode) return null

  const nodeAbove = nodes.value.find(n =>
    n.id !== newNodeId &&
    Math.abs(n.position.x - newNode.position.x) < 200 &&
    n.position.y < newNode.position.y
  )
  const nodeRight = nodes.value.find(n =>
    n.id !== newNodeId &&
    Math.abs(n.position.y - newNode.position.y) < 100 &&
    n.position.x > newNode.position.x
  )

  // 如果上面有节点，优先自动连接到上面的节点
  if (nodeAbove) {
    return { source: nodeAbove.id, target: newNodeId, label: '自动连线' }
  }
  // 如果右边有节点，自动连接
  if (nodeRight) {
    return { source: nodeRight.id, target: newNodeId, label: '自动连线' }
  }
  return null
}

// 检查两节点间是否已有连线
function hasEdgeBetween(source, target) {
  return edges.value.some((e) => e.source === source && e.target === target)
}

// 自动创建连线
function createAutoConnect(source, target, label = '自动连线') {
  if (hasEdgeBetween(source, target)) {
    appStore.warning('这两个节点之间已存在连线')
    return false
  }

  const newEdge = {
    id: `edge_auto_${Date.now()}`,
    source,
    target,
    label,
    type: 'default',
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    style: 'stroke: #3b82f6; stroke-dasharray: 5,5;'
  }
  edges.value = [...edges.value, newEdge]
  markDirty()
  saveHistory()
  return true
}

// 在画布指定位置添加节点（带自动连线）
function addNodeAtPosition(type, position) {
  const nodeType = getNodeMeta(type)
  if (!nodeType) return

  const snappedPos = resolveNodeCollision(
    { id: '__new__', position: {
      x: Math.round(position.x / 16) * 16,
      y: Math.round(position.y / 16) * 16,
    } },
    nodes.value
  )

  const newNode = {
    id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
    type,
    position: snappedPos,
    data: {
      label: nodeType.label,
      type,
      config: getDefaultConfig(type),
      description: ''
    }
  }

  nodes.value = [...nodes.value, newNode]
  saveHistory()

  // 自动连线逻辑
  const suggestion = getAutoConnectSuggestion(newNode.id)
  if (suggestion) {
    createAutoConnect(suggestion.source, suggestion.target, suggestion.label)
  }

  // 选中刚添加的节点
  selectedNode.value = newNode
  selectedEdge.value = null

  markDirty()
  return newNode
}

// 打开快速添加菜单
function openQuickAddMenu(clientX, clientY) {
  // 计算相对于画布的位置
  const canvasEl = document.querySelector('.canvas-wrapper')
  if (!canvasEl) return
  const rect = canvasEl.getBoundingClientRect()

  quickAddTargetPos.value = {
    x: Math.round((clientX - rect.left) / 16) * 16,
    y: Math.round((clientY - rect.top) / 16) * 16
  }
  quickAddMenuPos.value = {
    x: clientX - rect.left,
    y: clientY - rect.top
  }
  showQuickAddMenu.value = true
}

// 工具栏「添加」按钮入口（模板中无法访问 window，需在 script 中计算位置）
function openQuickAddMenuFromToolbar() {
  openQuickAddMenu(window.innerWidth / 2, 180)
}

// 关闭快速添加菜单
function closeQuickAddMenu() {
  showQuickAddMenu.value = false
}

// 处理快速添加菜单选择
function handleQuickAddSelect(type) {
  closeQuickAddMenu()
  addNodeAtPosition(type, quickAddTargetPos.value)
}

// 取消连线模式
function cancelAutoConnect() {
  autoConnectMode.value = false
  autoConnectSourceNode.value = null
  autoConnectSourceHandle.value = null
  clearConnectVisuals()
  document.body.style.cursor = 'default'
}

function enableAutoConnectMode() {
  autoConnectMode.value = true
  autoConnectSourceNode.value = null
  autoConnectSourceHandle.value = null
  connectHoverTargetId.value = null
  selectedNode.value = null
  selectedEdge.value = null
  document.body.style.cursor = 'crosshair'
  syncConnectVisualClasses()
  appStore.info('连线模式：先点击源节点，再点击目标节点')
}

// ESC 取消操作
function handleGlobalKeyDown(e) {
  if (e.key === 'Escape') {
    if (showQuickAddMenu.value) {
      closeQuickAddMenu()
    }
    if (autoConnectMode.value) {
      cancelAutoConnect()
    }
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    handleSave()
    return
  }

  // 快捷键添加节点 — 输入框/可编辑区域内不拦截
  const target = e.target
  if (target instanceof HTMLElement) {
    const tag = target.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable) return
    if (target.closest('.nodrag textarea, .nodrag input, [contenteditable="true"]')) return
  }

  // Delete / Backspace 删除选中节点
  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNode.value) {
    e.preventDefault()
    handleDeleteNode()
    return
  }

  const shortcuts = {
    's': 'start', 'S': 'start',
    'e': 'end', 'E': 'end',
    'a': 'llm', 'A': 'llm',
    'p': 'prompt', 'P': 'prompt',
    'i': 'input', 'I': 'input',
    'o': 'output', 'O': 'output',
    'c': 'code', 'C': 'code',
    'v': 'variable', 'V': 'variable',
    'h': 'http', 'H': 'http',
    'g': 'tool', 'G': 'tool',
    'l': 'loop', 'L': 'loop',
    'd': 'delay', 'D': 'delay',
    'w': 'switch', 'W': 'switch',
    'r': 'condition', 'R': 'condition',
    'f': 'subworkflow', 'F': 'subworkflow',
    't': 'transform', 'T': 'transform',
    'm': 'email', 'M': 'email',
  }

  if (shortcuts[e.key]) {
    e.preventDefault()
    const pos = {
      x: 400 + Math.random() * 100,
      y: 300 + Math.random() * 100
    }
    addNodeAtPosition(shortcuts[e.key], pos)
    appStore.success(`已添加节点: ${getNodeMeta(shortcuts[e.key])?.label}`)
  }
}

// 画布右键菜单
function onPaneContextMenu(event) {
  event.preventDefault()
  openQuickAddMenu(event.clientX, event.clientY)
}

// 双击画布添加节点
function onPaneDoubleClick(event) {
  const canvasEl = document.querySelector('.canvas-wrapper')
  if (!canvasEl) return
  const rect = canvasEl.getBoundingClientRect()
  const pos = {
    x: Math.round((event.clientX - rect.left) / 16) * 16,
    y: Math.round((event.clientY - rect.top) / 16) * 16
  }
  // 双击添加 LLM 节点作为默认
  addNodeAtPosition('llm', pos)
}

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKeyDown)
})

onActivated(async () => {
  if (!isNewWorkflow.value && workflowId.value) {
    await resumeWorkflowExecution()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeyDown)
  document.body.style.cursor = 'default'
  stopExecutionElapsedTimer()
  if (previewSyncTimer) {
    clearTimeout(previewSyncTimer)
    previewSyncTimer = null
  }
  if (workflowId.value) {
    executionStore.unregisterEditorSnapshotListener(workflowId.value)
  }
})

// 节点注册表（n8n 风格统一数据源）
const nodeSearchQuery = ref('')

const filteredNodeCategories = computed(() => filterNodeCategories(nodeSearchQuery.value))

const hasAnyNodes = computed(() => filteredNodeCategories.value.length > 0)

const quickAddCategories = computed(() =>
  NODE_CATEGORIES.filter((cat) =>
    ['trigger', 'flow', 'ai', 'transform', 'http', 'communication'].includes(cat.id)
  )
)

const nodeTypes = buildNodeTypesMap()
const minimapNodeColor = (node) => getMinimapNodeColor(node.type)

function scheduleMiniMapHide() {
  clearTimeout(minimapHideTimer)
  minimapHideTimer = setTimeout(() => {
    showMiniMap.value = false
  }, MINIMAP_HIDE_DELAY_MS)
}

function onViewportChange(nextViewport) {
  const prevZoom = viewport.value?.zoom ?? MINIMAP_BASE_ZOOM
  viewport.value = nextViewport
  const zoom = nextViewport?.zoom ?? MINIMAP_BASE_ZOOM
  if (Math.abs(zoom - prevZoom) > 0.001) {
    showMiniMap.value = true
  }
  scheduleMiniMapHide()
}

// Vue Flow composable
const {
  applyNodeChanges,
  applyEdgeChanges,
  zoomIn,
  zoomOut,
  fitView,
  getViewport,
  setViewport,
  project,
} = useVueFlow()

function handleNodeClick({ node }) {
  if (autoConnectMode.value) {
    if (!autoConnectSourceNode.value) {
      autoConnectSourceNode.value = node.id
      connectHoverTargetId.value = null
      syncConnectVisualClasses()
      appStore.info(`已选源节点「${node.data?.label || node.type}」，请点击目标节点`)
      return
    }
    if (autoConnectSourceNode.value === node.id) {
      return
    }
    if (createAutoConnect(autoConnectSourceNode.value, node.id, '')) {
      appStore.success('连线已创建')
    }
    autoConnectSourceNode.value = null
    connectHoverTargetId.value = null
    syncConnectVisualClasses()
    return
  }

  selectedNode.value = node
  selectedEdge.value = null
}

provide(WORKFLOW_SELECT_NODE_KEY, (nodeId) => {
  if (!nodeId) return
  const node = nodes.value.find((n) => n.id === nodeId)
  if (node) {
    handleNodeClick({ node })
  }
})

// 撤销/重做
const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.value.length - 1)

// 选中节点数据

// 保存历史状态
function saveHistory() {
  const state = JSON.stringify({ nodes: nodes.value, edges: edges.value })
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(state)
  historyIndex.value = history.value.length - 1
  isDirty.value = true
}

function handleUndo() {
  if (canUndo.value) {
    historyIndex.value--
    const state = JSON.parse(history.value[historyIndex.value])
    nodes.value = state.nodes
    edges.value = state.edges
    isDirty.value = true
  }
}

function handleRedo() {
  if (canRedo.value) {
    historyIndex.value++
    const state = JSON.parse(history.value[historyIndex.value])
    nodes.value = state.nodes
    edges.value = state.edges
    isDirty.value = true
  }
}

// 拖拽开始
function onDragStart(event, nodeType) {
  event.dataTransfer.setData('application/flowly-node', JSON.stringify(nodeType))
  event.dataTransfer.effectAllowed = 'move'
}

// 拖放
function onDrop(event) {
  const nodeDataStr = event.dataTransfer.getData('application/flowly-node')
  if (!nodeDataStr) return

  const nodeType = JSON.parse(nodeDataStr)
  const { left, top } = event.currentTarget.getBoundingClientRect()
  const position = project({
    x: event.clientX - left,
    y: event.clientY - top
  })

  const snappedPos = resolveNodeCollision(
    {
      id: '__new__',
      position: {
        x: Math.round(position.x / 16) * 16,
        y: Math.round(position.y / 16) * 16,
      },
    },
    nodes.value
  )

  const newNode = {
    id: `node_${Date.now()}`,
    type: nodeType.type,
    position: snappedPos,
    data: {
      label: nodeType.label,
      type: nodeType.type,
      config: getDefaultConfig(nodeType.type),
      description: ''
    }
  }

  nodes.value = [...nodes.value, newNode]
  saveHistory()
  markDirty()
}

// 获取节点默认配置
function getDefaultConfig(type) {
  return getDefaultNodeConfig(type)
}

// 连线
function onConnect(params) {
  if (hasEdgeBetween(params.source, params.target)) {
    appStore.warning('这两个节点之间已存在连线')
    return
  }

  const newEdge = {
    id: `edge_${Date.now()}`,
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle,
    label: '',
    type: 'default',
    animated: false,
    markerEnd: MarkerType.ArrowClosed
  }
  edges.value = [...edges.value, newEdge]
  markDirty()
  saveHistory()
}

// 节点点击（使用 useVueFlow composable 的 onNodeClick 替代 @node-click）
function handleEdgeClick(event) {
  selectedEdge.value = event.edge
  selectedNode.value = null
}

// 画布点击
function onPaneClick() {
  if (autoConnectMode.value && autoConnectSourceNode.value) {
    autoConnectSourceNode.value = null
    connectHoverTargetId.value = null
    syncConnectVisualClasses()
    appStore.info('已取消当前源节点选择')
    return
  }
  selectedNode.value = null
  selectedEdge.value = null
}

// VueFlow 节点尺寸计算完成后执行 fitView
// nodes-initialized 事件在 ResizeObserver 测量完所有节点尺寸后触发
// 这确保 fitView 能获取正确的节点边界，从而正确计算缩放比例
function onNodesInitialized() {
  if (!isNewWorkflow.value && nodes.value.length > 0) {
    nextTick(() => {
      nextTick(() => {
        if (vueFlowRef.value) {
          vueFlowRef.value.fitView({ padding: 0.2, duration: 400 })
        }
        scheduleCanvasPreviewSync()
      })
    })
  }
}

function scheduleCanvasPreviewSync() {
  if (previewSyncTimer) {
    clearTimeout(previewSyncTimer)
  }
  previewSyncTimer = setTimeout(() => {
    syncCanvasPreviewIfMissing()
  }, 900)
}

function applyCanvasPreviewLocally(canvasPreview, targetWorkflowId = workflowId.value) {
  if (!canvasPreview) return
  const existingConfig = workflowStore.currentWorkflow?.config || {}
  if (workflowStore.currentWorkflow) {
    workflowStore.currentWorkflow = {
      ...workflowStore.currentWorkflow,
      canvasPreview,
      config: { ...existingConfig, canvasPreview },
    }
  }
  const listItem = workflowStore.workflows.find((item) => item.id === targetWorkflowId)
  if (listItem) {
    listItem.canvasPreview = canvasPreview
    listItem.config = { ...(listItem.config || {}), canvasPreview }
  }
}

async function syncCanvasPreviewIfMissing() {
  if (
    previewSyncInFlight.value
    || isNewWorkflow.value
    || !canEditWorkflow.value
    || nodes.value.length === 0
  ) {
    return
  }

  const existingPreview = resolveWorkflowCanvasPreview(workflowStore.currentWorkflow)
  if (existingPreview) return

  previewSyncInFlight.value = true
  try {
    const canvasPreview = await captureWorkflowCanvas(getVueFlowCaptureApi())
    if (!canvasPreview) return

    const existingConfig = workflowStore.currentWorkflow?.config || {}
    await workflowApi.update(workflowId.value, {
      config: { ...existingConfig, canvas_preview: canvasPreview },
    })
    applyCanvasPreviewLocally(canvasPreview)
  } catch (captureErr) {
    console.warn('[syncCanvasPreviewIfMissing] failed:', captureErr)
  } finally {
    previewSyncInFlight.value = false
  }
}

// 节点变化（先交给 Vue Flow 应用变更，再标记脏状态）
function handleNodesChange(changes) {
  applyNodeChanges(changes)
  changes.forEach(change => {
    if (change.type !== 'select' && change.type !== 'dimensions') {
      markDirty()
    }
  })
}

// 连线变化
function handleEdgesChange(changes) {
  applyEdgeChanges(changes)
}

// 节点拖拽停止 — 防碰撞：若与其他节点重叠则自动偏移
function onNodeDragStop({ node }) {
  const idx = nodes.value.findIndex(n => n.id === node.id)
  if (idx === -1) return

  const resolved = resolveNodeCollision(
    { id: node.id, position: node.position },
    nodes.value
  )

  const updated = [...nodes.value]
  updated[idx] = {
    ...updated[idx],
    position: {
      x: Math.round(resolved.x),
      y: Math.round(resolved.y),
    },
  }
  nodes.value = updated
  markDirty()
}

// 节点拖拽中 - 实时同步位置到响应式数组
function onNodeDrag({ node }) {
  const idx = nodes.value.findIndex(n => n.id === node.id)
  if (idx !== -1) {
    const updated = [...nodes.value]
    updated[idx] = { ...updated[idx], position: { x: node.position.x, y: node.position.y } }
    nodes.value = updated
  }
}

// 节点右键菜单
function onNodeContextMenu() {
  // 可以添加右键菜单
}

// 标记为已修改
function markDirty() {
  isDirty.value = true
}

// 属性面板更新节点
function handleNodePropertyChange({ id, data }) {
  if (!id || !data) return
  const idx = nodes.value.findIndex(n => n.id === id)
  if (idx === -1) return
  const updated = [...nodes.value]
  updated[idx] = {
    ...updated[idx],
    data: {
      ...updated[idx].data,
      ...data
    }
  }
  nodes.value = updated
  markDirty()
}

// 删除节点
function handleDeleteNodeById(nodeId) {
  const targetId = nodeId || selectedNode.value?.id
  if (!targetId) return
  nodes.value = nodes.value.filter(n => n.id !== targetId)
  edges.value = edges.value.filter(
    e => e.source !== targetId && e.target !== targetId
  )
  if (selectedNode.value?.id === targetId) {
    selectedNode.value = null
  }
  saveHistory()
}

function handleDeleteNode() {
  handleDeleteNodeById(selectedNode.value?.id)
}

function handleAssistantApplyWorkflow(workflow) {
  if (!workflow?.nodes?.length) return

  const converted = nlWorkflowToVueFlow(workflow, {
    preserveNodes: nodes.value
  })
  nodes.value = converted.nodes
  edges.value = converted.edges.map(e => ({
    ...e,
    markerEnd: MarkerType.ArrowClosed
  }))

  if (workflow.name) {
    workflowName.value = workflow.name
  }

  selectedNode.value = null
  selectedEdge.value = null
  saveHistory()
  markDirty()

  nextTick(() => {
    vueFlowRef.value?.fitView({ padding: 0.2, duration: 400 })
  })

  appStore.success('AI 建议的工作流已应用到画布')
}

// 缩放控制
function handleZoomIn() {
  zoomIn()
}

function handleZoomOut() {
  zoomOut()
}

function handleFitView() {
  fitView()
}

function handleAutoLayout(direction = 'horizontal') {
  const layouted = autoLayoutWorkflow(nodes.value, edges.value, {
    nodeWidth: 220,
    nodeHeight: 140,
    gapX: 180,
    gapY: 80,
    startX: 80,
    startY: 80,
    direction
  })
  nodes.value = layouted
  markDirty()
  saveHistory()
  nextTick(() => {
    fitView({ padding: 0.1, duration: 300 })
  })
  appStore.success(
    direction === 'vertical' ? '已自动排列为垂直布局' : '已自动排列为水平布局'
  )
}

function handleToolbarCommand(cmd) {
  switch (cmd) {
    case 'variable':
      variablePanelVisible.value = true
      break
    case 'assistant':
      showAssistant.value = true
      break
    case 'theme': {
      const themeBtn = document.querySelector('[data-theme-switcher]')
      if (themeBtn) themeBtn.click()
      break
    }
  }
}

function handleOptimizerHighlight(nodeIds) {
  if (!Array.isArray(nodeIds) || nodeIds.length === 0) return
  const target = nodes.value.find((node) => nodeIds.includes(node.id))
  if (!target) return
  selectedNode.value = target
  nextTick(() => {
    fitView({ nodes: nodeIds, padding: WORKFLOW_CANVAS_ZOOM.fitViewPadding, duration: 450, maxZoom: WORKFLOW_CANVAS_ZOOM.fitViewMax })
  })
}

function handleOptimizerApplyFix(suggestion) {
  const nodeIds = suggestion?.affectedNodes || []
  if (!nodeIds.length || !suggestion?.autoApplicable) return

  let patch = {}
  if (suggestion.fix) {
    try {
      patch = JSON.parse(suggestion.fix)
    } catch {
      appStore.warning('该建议需要手动应用')
      return
    }
  }

  const targetId = nodeIds[0]
  nodes.value = nodes.value.map((node) => {
    if (node.id !== targetId) return node
    const currentConfig = node.data?.config || {}
    return {
      ...node,
      data: {
        ...node.data,
        config: { ...currentConfig, ...patch },
      },
    }
  })
  markDirty()
  appStore.success('已应用优化建议')
}

// 名称修改
function handleNameBlur() {
  if (workflowName.value.trim()) {
    markDirty()
  }
}

// 验证工作流
async function handleValidate() {
  try {
    const { validateWorkflowSchema, highlightErrorNodes, showValidationResult } = await import('@/utils/workflow-schema')

    // 先清除之前的高亮
    clearErrorHighlights()

    // 执行验证
    const result = validateWorkflowSchema(nodes.value, edges.value)

    // 高亮错误节点
    highlightErrorNodes(nodes.value, result.nodeErrors)

    // 显示验证结果
    showValidationResult(result)

    // 更新验证对话框数据（兼容现有对话框）
    validationResult.value = {
      valid: result.valid,
      errors: result.errors.map(e => e.message),
      warnings: result.warnings.map(w => w.message)
    }
    showValidateDialog.value = true
  } catch (err) {
    console.error('验证失败:', err)
    appStore.error('验证失败')
  }
}

// 清除错误高亮
function clearErrorHighlights() {
  for (const node of nodes.value) {
    if (node.data?.hasError) {
      node.data = {
        ...node.data,
        hasError: false,
        errorMessages: []
      }
    }
  }
}

// 打开触发器配置
function openTriggerConfig() {
  if (isNewWorkflow.value) {
    appStore.warning('请先保存工作流后再配置触发器')
    return
  }
  triggerConfigVisible.value = true
}

// 保存
async function handleSave() {
  if (!canEditWorkflow.value) {
    appStore.warning('您没有此工作流的编辑权限，请先复制工作流后再编辑')
    return false
  }
  try {
    const graphPatch = ensureMultimodalWorkflowGraph(nodes.value, edges.value)
    if (graphPatch.patched) {
      nodes.value = graphPatch.nodes
      edges.value = graphPatch.edges
    }
    const saveNodes = nodes.value.map((n, index) => ({
      id: n.id,
      node_type: n.type,
      name: n.data.label,
      description: n.data.description || '',
      position_x: Math.round(Number(n.position?.x) || 0),
      position_y: Math.round(Number(n.position?.y) || 0),
      sort_order: index,
      config: normalizeNodeConfig(n.data.config || {}, n.type),
      style: {
        ...(n.data?.style || n.style || {}),
        ...(n.data?.uiSize ? { uiSize: n.data.uiSize } : {}),
        ...(n.data?._runtime ? { _runtime: n.data._runtime } : {}),
      },
    }))
    const saveEdges = edges.value.map(e => ({
      source_node: e.source,
      target_node: e.target,
      label: e.label || '',
      animated: e.animated || false
    }))

    let canvasPreview = null
    try {
      canvasPreview = await captureWorkflowCanvas(getVueFlowCaptureApi())
    } catch (captureErr) {
      console.warn('[handleSave] workflow preview capture failed:', captureErr)
    }

    const existingConfig = workflowStore.currentWorkflow?.config || {}
    const savePayload = {
      name: workflowName.value,
      nodes: saveNodes,
      edges: saveEdges,
    }
    if (canvasPreview) {
      savePayload.config = { ...existingConfig, canvas_preview: canvasPreview }
    }

    if (isNewWorkflow.value) {
      const result = await workflowStore.createWorkflow(savePayload)
      if (canvasPreview && result?.id) {
        applyCanvasPreviewLocally(canvasPreview, result.id)
      }
      appStore.success('工作流创建成功')
      router.replace(`/workflows/${result.id}/edit`)
    } else {
      const response = await workflowStore.updateWorkflow(workflowId.value, savePayload)
      if (response?.nodes?.length) {
        const synced = syncCanvasAfterSave(nodes.value, edges.value, response)
        if (synced.idMap && Object.keys(synced.idMap).length > 0) {
          try {
            migrateNodeRuntimeCache(workflowId.value, synced.idMap)
            remapExecutionStoreNodeIds(executionStore, synced.idMap)
            executionNodeStateMap.value = remapRecordByIdMap(executionNodeStateMap.value, synced.idMap)
          } catch (migrateErr) {
            console.warn('[handleSave] node runtime migration failed:', migrateErr)
          }
        }
        nodes.value = synced.nodes
        edges.value = synced.edges.map((e) => ({
          ...e,
          markerEnd: MarkerType.ArrowClosed,
        }))
        saveHistory()
      }
      if (canvasPreview) {
        applyCanvasPreviewLocally(canvasPreview)
      }
      appStore.success('工作流已保存')
    }

    isDirty.value = false
    return true
  } catch (err) {
    const resp = err?.response?.data
    let errorMsg = resp?.detail || err?.message

    // Extract validation errors for nodes/edges
    if (resp && typeof resp === 'object') {
      const msgs = []
      if (resp.nodes) msgs.push(`节点: ${Array.isArray(resp.nodes) ? resp.nodes[0] : resp.nodes}`)
      if (resp.edges) msgs.push(`连线: ${Array.isArray(resp.edges) ? resp.edges[0] : resp.edges}`)
      if (resp.node_type) msgs.push(`节点类型: ${Array.isArray(resp.node_type) ? resp.node_type[0] : resp.node_type}`)
      if (resp.non_field_errors) msgs.push(Array.isArray(resp.non_field_errors) ? resp.non_field_errors[0] : resp.non_field_errors)
      if (msgs.length > 0) {
        errorMsg = msgs.join('; ')
      }
    }

    console.error('[handleSave] Failed to save workflow:', err, { responseData: resp })
    if (errorMsg) {
      appStore.error(`保存失败: ${errorMsg}`)
    }
    return false
  }
}

// 执行
async function handleExecute() {
  if (isNewWorkflow.value) {
    appStore.warning('请先保存工作流后再执行')
    return
  }

  if (isDirty.value) {
    const confirmed = await appStore.confirm({
      title: '有未保存的更改',
      message: '执行前需要先保存工作流，是否保存并继续执行？',
      confirmText: '保存并执行',
      cancelText: '取消',
      confirmType: 'primary',
    })
    if (!confirmed) return
    const saved = await handleSave()
    if (!saved) return
  }

  clearInputNeedsFlags()
  flushCanvasInputValues()
  const emptyInputNodes = collectEmptyInputNodes()
  if (emptyInputNodes.length > 0) {
    markEmptyInputNodes(emptyInputNodes)
    const labels = emptyInputNodes.map(n => n.data?.label || '输入').join('、')
    appStore.warning(`请先在 ${emptyInputNodes.length} 个输入节点中填写内容（${labels}）`)
    focusEmptyInputNode(emptyInputNodes[0])
    return
  }

  // 收集 input 节点所需的输入参数；优先使用画布节点内已填写的值
  const inputNodes = nodes.value.filter(n => (n.data?.type || n.type) === 'input')
  const inputData = {}
  for (const node of inputNodes) {
    const config = node.data?.config || {}
    const varName = config.variable_name || config.input_name || config.variableName || config.inputName || 'user_input'
    const value = readInputNodeValue(node)

    inputData[varName] = value
    inputData.prompt = value
    inputData.text = value
    inputData.user_input = value
    if (varName === 'user_input' || varName === 'input') {
      inputData.input = value
    }
  }

  showExecutionPanel.value = true
  startExecution(inputData)
}

// 执行引擎
async function startExecution(inputData = {}) {
  resetExecutionState()
  const sessionId = executionSessionId.value
  showExecutionPanel.value = true
  executionStatus.value = 'running'
  executionStartTime.value = Date.now()
  startExecutionElapsedTimer(sessionId)
  executionLogs.value.push(createExecutionLog('info', '开始执行工作流...'))

  executionStore.registerEditorSnapshotListener(workflowId.value, handleEditorExecutionSnapshot)

  try {
    const prep = await prepareDesktopClipIndexes(nodes.value, edges.value, {
      onProgress: ({ nodeId, progress, phase }) => {
        if (executionSessionId.value !== sessionId) return
        executionLogs.value.push(createExecutionLog('info', `Desktop 索引 ${nodeId}: ${phase} ${progress}%`))
      },
    })
    if (executionSessionId.value !== sessionId) return
    if (prep.patched) {
      executionLogs.value.push(createExecutionLog('info', 'Desktop 本地 GPU 索引已构建，正在保存节点配置…'))
      await handleSave()
    }
  } catch (prepErr) {
    if (executionSessionId.value !== sessionId) return
    executionStatus.value = 'failed'
    executionLogs.value.push(createExecutionLog('error', prepErr.message || 'Desktop 索引预构建失败'))
    appStore.error(prepErr.message || 'Desktop 索引预构建失败')
    return
  }

  try {
    const data = await workflowApi.executeAsync(workflowId.value, inputData)
    if (executionSessionId.value !== sessionId) return

    if (data.execution_id || data.executionId) {
      executionId.value = data.execution_id || data.executionId
      executionLogs.value.push(createExecutionLog('info', `执行已启动，ID: ${executionId.value}`))
      await executionStore.startEditorPolling(workflowId.value, executionId.value)
      return
    }

    executionStatus.value = 'completed'
    stopExecutionElapsedTimer()
    executionLogs.value.push(createExecutionLog('success', data.message || '执行完成'))
  } catch (err) {
    if (executionSessionId.value !== sessionId) return
    executionStatus.value = 'failed'
    stopExecutionElapsedTimer()
    executionLogs.value.push(createExecutionLog('error', getErrorMessage(err, '执行失败')))
  }
}

async function cancelExecution() {
  const sessionId = executionSessionId.value

  if (!executionId.value) {
    executionStatus.value = 'cancelled'
    stopExecutionElapsedTimer()
    executionStore.stopEditorPolling({ resetSession: true, clearActive: true })
    executionLogs.value.push(createExecutionLog('info', '已取消'))
    return
  }

  try {
    await workflowApi.cancelExecution(executionId.value)
    if (executionSessionId.value !== sessionId) return
    executionStatus.value = 'cancelled'
    stopExecutionElapsedTimer()
    executionStore.stopEditorPolling({ resetSession: true, clearActive: true })
    executionLogs.value.push(createExecutionLog('info', '已发送取消请求'))
  } catch (error) {
    if (executionSessionId.value !== sessionId) return
    executionLogs.value.push(createExecutionLog('error', getErrorMessage(error, '取消执行失败')))
  }
}

// 返回
async function handleBack() {
  if (isDirty.value) {
    const confirmed = await appStore.confirm({
      title: '未保存的更改',
      message: '您有未保存的更改，确定要离开吗？未保存的内容将丢失。',
      confirmText: '离开',
      cancelText: '取消',
      confirmType: 'danger',
    })
    if (!confirmed) return
  }
  window.history.back()
}

// 加载模型和工具列表
async function loadModelsAndTools() {
  try {
    const [modelsRes, toolsRes] = await Promise.allSettled([
      workflowStore.fetchAvailableModels({ type: 'chat' }),
      workflowStore.fetchAvailableTools()
    ])

    if (modelsRes.status === 'fulfilled' && modelsRes.value) {
      availableModels.value = modelsRes.value.map(m => ({
        value: m.model_id || m.id,
        label: `${m.name} (${m.provider?.name || m.provider_name || 'Unknown'})`
      }))
    }

    if (toolsRes.status === 'fulfilled' && toolsRes.value) {
      availableTools.value = toolsRes.value.map(t => ({
        value: t.name,
        label: t.name
      }))
    }
  } catch {
    // Error shown via appStore
  }
}

function applyWorkflowTemplate(template) {
  if (!template?.nodes?.length) return
  workflowName.value = template.name || '未命名工作流'
  nodes.value = template.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    position: n.position || { x: 0, y: 0 },
    data: {
      label: n.data?.label || n.data?.name || n.type,
      config: normalizeNodeConfig(n.type, n.data?.config || {}),
      ...n.data,
    },
  }))
  edges.value = (template.edges || []).map((e) => ({
    ...e,
    id: e.id || `e-${e.source}-${e.target}`,
    markerEnd: MarkerType.ArrowClosed,
  }))
  saveHistory()
  isDirty.value = true
  nextTick(() => {
    vueFlowRef.value?.fitView({ padding: 0.2, duration: 400 })
  })
}

onMounted(async () => {
  // 初始化历史
  saveHistory()

  // 加载模型和工具列表
  loadModelsAndTools()

  if (isNewWorkflow.value) {
    const pendingRaw = sessionStorage.getItem('flowly_pending_workflow_template')
    if (pendingRaw) {
      try {
        applyWorkflowTemplate(JSON.parse(pendingRaw))
        sessionStorage.removeItem('flowly_pending_workflow_template')
      } catch {
        sessionStorage.removeItem('flowly_pending_workflow_template')
      }
    } else if (route.query.template === 'yolo-detection' || route.query.template === 'yolo') {
      applyWorkflowTemplate(YOLO_WORKFLOW_TEMPLATE)
    } else if (route.query.template === 'clip-retrieval') {
      applyWorkflowTemplate(CLIP_RETRIEVAL_WORKFLOW_TEMPLATE)
    }
  } else if (!isNewWorkflow.value) {
    try {
      await workflowStore.fetchWorkflow(workflowId.value)
      workflowName.value = workflowStore.currentWorkflow?.name || '未命名工作流'

      // Store already has Vue Flow format data from backendWorkflowToFrontend
      nodes.value = [...(workflowStore.nodes || [])]

      // 仅对未定位节点做布局，已保存坐标原样保留
      const layoutEdges = workflowStore.edges || []
      const positionsBefore = JSON.stringify(nodes.value.map(n => n.position))
      if (needsAutoLayout(nodes.value) && nodes.value.length > 0) {
        nodes.value = applyWorkflowLayout(nodes.value, layoutEdges, nodes.value)
      }
      const autoLayoutApplied = positionsBefore !== JSON.stringify(nodes.value.map(n => n.position))

      edges.value = (workflowStore.edges || [])
        .map(e => ({
          ...e,
          // source_node_id is the integer ID from backend; source is the string ID
          source: String(e.source || e.source_node_id || ''),
          target: String(e.target || e.target_node_id || ''),
          markerEnd: MarkerType.ArrowClosed
        }))
        .filter(e => e.source && e.source !== 'undefined' && e.target && e.target !== 'undefined')

      const graphPatch = ensureMultimodalWorkflowGraph(nodes.value, edges.value)
      if (graphPatch.patched) {
        nodes.value = graphPatch.nodes
        edges.value = graphPatch.edges.map((e) => ({
          ...e,
          markerEnd: MarkerType.ArrowClosed,
        }))
        isDirty.value = true
        appStore.info('已自动修复输入→文生图→图生视频链路连线与配置，请保存')
      }

      // 更新历史
      saveHistory()
      isDirty.value = autoLayoutApplied
      if (autoLayoutApplied) {
        appStore.info('节点已自动排列，请保存以固定布局')
      } else {
        isDirty.value = false
      }

      // 自动适应画布，让所有节点可见
      // 使用 vueFlowRef.value.fitView() 调用实例方法
      // nodes-initialized 事件会再次触发 fitView，双重保障
      await nextTick()
      await nextTick()
      if (vueFlowRef.value) {
        vueFlowRef.value.fitView({ padding: 0.2, duration: 600 })
      }

      await resumeWorkflowExecution()
    } catch (err) {
      appStore.error('加载工作流失败')
    }
  }
})

// 监听节点和连线变化
watch([nodes, edges], () => {
  if (!isDirty.value) return
}, { deep: true })

// 执行日志自动滚动到底部
watch(executionLogs, async () => {
  await nextTick()
  if (execPanelBodyRef.value) {
    execPanelBodyRef.value.scrollTop = execPanelBodyRef.value.scrollHeight
  }
})

watch(selectedExecNode, (newNode) => {
  if (newNode?.id) {
    scrollSelectedExecNodeIntoView()
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

@import '@/styles/workflow-domain-node.scss';

.workflow-editor {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
}

.editor-readonly-alert {
  margin: 0;
  border-radius: 0;
  flex-shrink: 0;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 $spacing-4;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  z-index: 10;
  gap: $spacing-3;
  flex-shrink: 0;
}

// 工具栏三段式布局
.toolbar-section {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  &--left {
    flex-shrink: 0;
    max-width: 100%;
  }

  &--center {
    flex: 1;
    justify-content: center;
    flex-wrap: wrap;
    gap: $spacing-2;
    overflow: hidden;
  }

  &--right {
    flex-shrink: 0;
    flex-wrap: nowrap;
    justify-content: flex-end;
  }
}

.toolbar-back-btn {
  flex-shrink: 0;
}

.toolbar-btn-group {
  display: inline-flex;
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;

  .toolbar-btn-icon-right {
    margin-left: 4px;
    opacity: 0.7;
  }

  .el-button {
    border: none;
    border-radius: 0;
    padding: 6px 10px;

    &:not(:last-child) {
      border-right: 1px solid var(--border-primary);
    }
  }

  &--single {
    border: none;
    gap: 2px;

    .el-button {
      border: 1px solid var(--border-primary);
      border-radius: $radius-md;
      padding: 6px 10px;
    }
  }
}

.workflow-name-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  overflow: hidden;
  min-width: 0;
}

.workflow-name-input {
  background: transparent;
  border: none;
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-md;
  min-width: 200px;
  max-width: 360px;

  &:hover,
  &:focus {
    background-color: var(--bg-hover);
    outline: none;
  }
}

.unsaved-indicator {
  font-size: $font-size-xs;
  color: $color-warning;
  flex-shrink: 0;
}

// 核心按钮：小屏幕时隐藏文字
.toolbar-core-btn {
  .btn-label {
    transition: opacity 0.2s;
  }
}

.toolbar-more-dropdown {
  flex-shrink: 0;
}

.toolbar-more-btn {
  padding: 6px 8px !important;
}

// 响应式断点
// 1. 1200px 以下：隐藏核心按钮文字
@media (max-width: 1200px) {
  .toolbar-core-btn {
    .btn-label {
      display: none;
    }

    padding: 6px 10px !important;
    min-width: auto;
  }
}

// 2. 1000px 以下：隐藏中心区域的触发器文字
@media (max-width: 1000px) {
  .toolbar-section--center {
    .toolbar-btn-group--single .el-button {
      padding: 6px 8px;

      span:not(.el-icon) {
        display: none;
      }
    }
  }
}

// 3. 850px 以下：隐藏验证/保存/执行的文字，折叠到图标
@media (max-width: 850px) {
  .toolbar-core-btn {
    .btn-label {
      display: none;
    }
  }

  .workflow-name-input {
    min-width: 150px;
    max-width: 250px;
  }
}

// 4. 700px 以下：隐藏中心区域所有文字，仅保留图标按钮
@media (max-width: 700px) {
  .toolbar-section--center {
    .el-button {
      span:not(.el-icon) {
        display: none;
      }
    }
  }

  .workflow-name-input {
    min-width: 100px;
    max-width: 160px;
  }
}

// 5. 500px 以下：隐藏连线文字，仅图标
@media (max-width: 500px) {
  .toolbar-section--center {
    .toolbar-btn-group--single .el-button span {
      display: none;
    }
  }

  .workflow-name-input {
    min-width: 80px;
    max-width: 120px;
  }
}

// 超小屏幕完全隐藏中间区域（保留画布操作）
@media (max-width: 380px) {
  .toolbar-section--center {
    display: none;
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
  width: 100%;
  position: relative;
}

.node-panel {
  width: 260px;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  overflow-y: auto;
}

.panel-section {
  padding: $spacing-4;
}

.panel-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  letter-spacing: 0.02em;
}

.node-search {
  margin-bottom: $spacing-4;

  .el-input__wrapper {
    background: var(--bg-tertiary) !important;
    box-shadow: 0 0 0 1px var(--border-primary) inset !important;
  }

  .el-input__inner {
    color: var(--text-primary) !important;
  }

  .el-input__prefix {
    color: var(--text-tertiary) !important;
  }
}

.node-category {
  margin-bottom: $spacing-4;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-bottom: $spacing-2;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: $font-weight-medium;

  .category-icon {
    width: 14px;
    height: 14px;
    opacity: 0.75;
    flex-shrink: 0;
  }

  .category-count {
    margin-left: auto;
    background: var(--bg-tertiary);
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 10px;
  }
}

.node-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: grab;
  transition: all $transition-fast;
  margin-bottom: $spacing-2;

  &:hover {
    border-color: var(--node-color, var(--accent-primary));
    background-color: var(--bg-hover);
    transform: translateX(2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  &:active {
    cursor: grabbing;
    transform: scale(0.98);
  }
}

.node-item-preview {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1.5px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-label {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  line-height: 1.2;
}

.node-desc {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-shortcut {
  font-size: 10px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 5px;
  border-radius: 4px;
  border: 1.5px solid;
  flex-shrink: 0;
  letter-spacing: 0;
  opacity: 0.8;
  line-height: 1;
}

.node-icon {
  width: 16px;
  height: 16px;
}

.node-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-2;
  padding: $spacing-6;
  color: var(--text-tertiary);
  font-size: $font-size-sm;
  text-align: center;

  .empty-icon {
    width: 24px;
    height: 24px;
    opacity: 0.5;
  }
}

.canvas-wrapper {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  width: 100%;
  position: relative;
  background-color: var(--bg-primary);

  :deep(.vue-flow) {
    width: 100%;
    height: 100%;
  }

  :deep(.vue-flow__minimap.editor-minimap) {
    margin: 12px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    transition: opacity 0.2s ease, transform 0.2s ease;
  }

  :deep(.vue-flow__minimap.editor-minimap:not([style*="display: none"])) {
    opacity: 1;
  }

  &.connect-mode-active {
    &::before {
      content: '';
      position: absolute;
      inset: 0;
      z-index: 2;
      pointer-events: none;
      background:
        radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.08), transparent 45%),
        radial-gradient(circle at 80% 80%, rgba(34, 211, 238, 0.06), transparent 40%);
      animation: connect-ambient 4s ease-in-out infinite alternate;
    }

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      z-index: 2;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(59, 130, 246, 0.03) 2px,
        rgba(59, 130, 246, 0.03) 4px
      );
      mask-image: linear-gradient(to bottom, transparent, black 15%, black 85%, transparent);
      animation: connect-scan 6s linear infinite;
    }

    :deep(.vue-flow__node.connect-candidate) {
      filter: saturate(0.85);
      opacity: 0.92;
      transition: filter 0.25s ease, opacity 0.25s ease, transform 0.25s ease;
    }

    :deep(.vue-flow__node.connect-source) {
      z-index: 12 !important;
      filter: drop-shadow(0 0 18px rgba(59, 130, 246, 0.75));

      > div {
        outline: 2px solid rgba(96, 165, 250, 0.95);
        outline-offset: 3px;
        border-radius: 14px;
        animation: connect-source-glow 1.4s ease-in-out infinite;
      }
    }

    :deep(.vue-flow__node.connect-target-valid) {
      cursor: crosshair;

      > div {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }

      &:hover > div {
        transform: translateY(-2px) scale(1.01);
      }
    }

    :deep(.vue-flow__node.connect-target-hover) {
      z-index: 11 !important;

      > div {
        outline: 2px dashed rgba(34, 211, 238, 0.95);
        outline-offset: 4px;
        border-radius: 14px;
        box-shadow:
          0 0 0 1px rgba(34, 211, 238, 0.35),
          0 0 28px rgba(34, 211, 238, 0.35);
        animation: connect-target-pulse 0.9s ease-in-out infinite;
      }
    }

    :deep(.vue-flow__edge-path) {
      stroke: rgba(96, 165, 250, 0.55);
    }
  }
}

@keyframes connect-ambient {
  from { opacity: 0.55; }
  to { opacity: 1; }
}

@keyframes connect-scan {
  from { transform: translateY(-8%); }
  to { transform: translateY(8%); }
}

@keyframes connect-source-glow {
  0%, 100% {
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.45), 0 0 24px rgba(59, 130, 246, 0.2);
  }
  50% {
    box-shadow: 0 0 22px rgba(96, 165, 250, 0.75), 0 0 36px rgba(34, 211, 238, 0.35);
  }
}

@keyframes connect-target-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.015); }
}

.empty-canvas {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;

  .empty-content {
    text-align: center;

    .empty-icon-wrapper {
      width: 80px;
      height: 80px;
      margin: 0 auto $spacing-4;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(59, 130, 246, 0.08);
      border: 1px solid rgba(59, 130, 246, 0.2);
      border-radius: 24px;
    }

    .empty-icon {
      width: 40px;
      height: 40px;
      color: rgba(59, 130, 246, 0.6);
    }

    h3 {
      color: var(--text-primary);
      margin: 0 0 $spacing-2;
      font-size: $font-size-xl;
      font-weight: $font-weight-semibold;
    }

    p {
      color: var(--text-tertiary);
      margin: 0;
      font-size: $font-size-sm;
    }

    .quick-hint-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $spacing-2;
      margin-top: $spacing-4;
      flex-wrap: wrap;

      kbd {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 26px;
        height: 26px;
        padding: 0 6px;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        color: var(--text-secondary);
        box-shadow: 0 2px 0 var(--border-primary);
      }

      span {
        font-size: $font-size-xs;
        color: var(--text-tertiary);
      }
    }
  }
}

.property-form {
  padding: $spacing-4;
}

.form-group {
  margin-bottom: $spacing-4;

  label {
    display: block;
    margin-bottom: $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
  }

  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
  }
}

.variable-list,
.condition-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.variable-item,
.condition-item {
  display: flex;
  gap: $spacing-2;
  align-items: center;

  .el-input {
    flex: 1;
  }

  .el-select {
    width: 100px;
  }
}

.code-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
  }
}

.property-actions {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);

  .el-button {
    width: 100%;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.empty-properties {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;

  .empty-content {
    text-align: center;

    .empty-icon {
      width: 48px;
      height: 48px;
      color: var(--text-tertiary);
      margin-bottom: $spacing-3;
    }

    p {
      color: var(--text-tertiary);
      margin: 0;
    }
  }
}

.validate-success {
  text-align: center;
  padding: $spacing-6;

  .success-icon {
    width: 48px;
    height: 48px;
    color: $color-success;
    margin-bottom: $spacing-4;
  }
}

.validate-errors,
.warning-list {
  h4 {
    margin: 0 0 $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
  }

  ul {
    margin: 0;
    padding-left: $spacing-5;
  }

  li {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    margin-bottom: $spacing-1;
  }
}

.error-list {
  margin-bottom: $spacing-4;

  li {
    color: $color-error;
  }
}

// ============================================================
// 错误节点高亮样式
// ============================================================
:deep(.vue-flow__node) {
  &.has-error {
    .node-card,
    .node-wrapper {
      background: rgba(239, 68, 68, 0.15) !important;
      border: 2px solid var(--el-color-danger, #ef4444) !important;
      animation: error-shake 0.3s ease-in-out;
      box-shadow: 0 0 12px rgba(239, 68, 68, 0.4) !important;
    }
  }

  &.has-warning {
    .node-card,
    .node-wrapper {
      background: rgba(245, 158, 11, 0.15) !important;
      border: 2px solid var(--el-color-warning, #f59e0b) !important;
      box-shadow: 0 0 8px rgba(245, 158, 11, 0.3) !important;
    }
  }
}

@keyframes error-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

// ============================================================
// 快速添加菜单样式
// ============================================================
.quick-add-menu {
  position: absolute;
  z-index: 100;
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-primary, rgba(255,255,255,0.1));
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255,255,255,0.05) inset;
  width: 320px;
  max-height: 480px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(20px);
}

.quick-add-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3 $spacing-4;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-tertiary, #0f0f1a);

  .menu-icon {
    width: 16px;
    height: 16px;
    color: $color-primary;
  }

  span {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }

  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-tertiary);
    padding: 2px;
    border-radius: 4px;
    display: flex;
    align-items: center;

    &:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
    }
  }
}

.quick-add-body {
  padding: $spacing-3;
  overflow-y: auto;
  max-height: 400px;
}

.quick-add-section {
  margin-bottom: $spacing-3;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: $spacing-2;
  padding-left: $spacing-1;
}

.quick-add-items {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-2;
}

.quick-add-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: $spacing-3 $spacing-2;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 500;

  &:hover {
    background: var(--bg-hover);
    border-color: $color-primary;
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(59, 130, 246, 0.2);
  }

  &:active {
    transform: translateY(0) scale(0.98);
  }

  .item-icon {
    width: 20px;
    height: 20px;
  }
}

// ============================================================
// 自动连线模式指示器
// ============================================================
.auto-connect-indicator {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3 $spacing-4;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 58, 138, 0.88));
  backdrop-filter: blur(12px);
  border-radius: 14px;
  border: 1px solid rgba(96, 165, 250, 0.45);
  box-shadow:
    0 8px 32px rgba(37, 99, 235, 0.35),
    0 0 0 1px rgba(34, 211, 238, 0.15) inset;
  color: #e0f2fe;
  font-size: $font-size-sm;
  font-weight: 500;
  white-space: nowrap;

  .indicator-icon {
    width: 16px;
    height: 16px;
    color: #67e8f9;
    animation: connect-indicator-pulse 1.5s infinite;
  }
}

@keyframes connect-indicator-pulse {
  0%, 100% { opacity: 1; filter: drop-shadow(0 0 4px rgba(34, 211, 238, 0.8)); }
  50% { opacity: 0.55; filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.9)); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

// ============================================================
// 画布状态栏
// ============================================================
.canvas-status-bar {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-2 $spacing-4;
  background: rgba(15, 15, 26, 0.85);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: var(--text-secondary);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255,255,255,0.03) inset;

  .status-item {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-icon {
    width: 12px;
    height: 12px;
  }

  .connect-mode {
    color: #3b82f6;
    font-weight: 500;
  }
}

// ============================================================
// 空状态提示增强
// ============================================================
.empty-canvas {
  .empty-content {
    .quick-hint {
      margin-top: $spacing-3;
      font-size: 11px;
      color: var(--text-tertiary);
      background: var(--bg-tertiary);
      padding: 4px 8px;
      border-radius: 4px;
    }
  }
}

// ============================================
// 响应式设计 - Responsive Design
// ============================================

@media (max-width: 1024px) {
  .node-panel {
    width: 220px;
  }
}

@media (max-width: 768px) {
  .editor-header {
    padding: $spacing-3 $spacing-4;

    .header-left,
    .header-right {
      gap: $spacing-2;
    }
  }

  .toolbar-center {
    display: none;
  }

  .node-panel {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 10;
    width: 260px;
    transform: translateX(-100%);
    transition: transform $transition-normal;
    box-shadow: $shadow-lg;

    &.open {
      transform: translateX(0);
    }
  }

  .canvas-wrapper {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .editor-header {
    padding: $spacing-2 $spacing-3;
  }

  .header-title {
    font-size: $font-size-base;
  }

  .el-button {
    padding: $spacing-2 $spacing-3;
    font-size: $font-size-sm;
  }
}

// =============================================================================
// 底部执行面板
// =============================================================================

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}

.execution-bottom-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 320px;
  min-height: 160px;
  max-height: calc(100vh - 100px);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  z-index: 200;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.3);
  transition: box-shadow 0.2s;
  overflow: hidden;

  &.is-dragging {
    box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.5);
    cursor: ns-resize;
    user-select: none;
  }
}

.exec-panel-handle {
  height: 6px;
  cursor: ns-resize;
  background: transparent;
  border-radius: 3px 3px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  flex-shrink: 0;
  transition: background 0.2s;

  &::after {
    content: '';
    display: block;
    width: 36px;
    height: 3px;
    border-radius: 2px;
    background: var(--border-primary);
    transition: background 0.2s, width 0.2s;
  }

  &:hover::after {
    background: var(--text-tertiary);
    width: 60px;
  }
}

.exec-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;

  .exec-header-left {
    display: flex;
    align-items: center;
    gap: 8px;

    .exec-icon {
      color: var(--color-primary, #6366f1);
      width: 16px;
      height: 16px;
    }

    .exec-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .exec-node-count {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }
  }

  .exec-header-right {
    display: flex;
    align-items: center;
    gap: 8px;

    .exec-elapsed {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }
  }
}

.exec-panel-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  gap: 0;
  min-height: 0;
}

// 三栏布局
.exec-timeline {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .timeline-header {
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;
  }

  .timeline-list {
    flex: 1;
    overflow-y: auto;
    padding: 6px 0;

    &::-webkit-scrollbar { width: 4px; }
    &::-webkit-scrollbar-track { background: transparent; }
    &::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 2px; }
  }

  .timeline-empty {
    padding: 16px 12px;
    color: var(--text-muted);
    font-size: 12px;
    text-align: center;
  }
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;

  &:hover { background: rgba(255,255,255,0.04); }
  &.node-running { background: rgba(59,130,246,0.08); }
  &.node-completed { background: rgba(16,185,129,0.06); }
  &.node-failed { background: rgba(239,68,68,0.08); }
  &.is-selected {
    background: rgba(59,130,246,0.16);
    box-shadow: inset 2px 0 0 #3b82f6;
  }
  &.node-failed.is-selected {
    background: rgba(239,68,68,0.16);
    box-shadow: inset 2px 0 0 #ef4444;
  }

  .timeline-status {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .tl-icon {
    width: 14px;
    height: 14px;
    &.success { color: #10b981; }
    &.error { color: #ef4444; }
    &.pending { color: var(--text-muted); }
    &.spinning { color: #3b82f6; }
  }

  .timeline-info {
    display: flex;
    flex-direction: column;
    min-width: 0;

    .tl-name {
      font-size: 12px;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tl-type {
      font-size: 10px;
      color: var(--text-muted);
    }
  }
}

.exec-output {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border-primary);

  .output-header {
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;

    .output-node-name {
      color: var(--text-primary);
      font-size: 12px;
      text-transform: none;
      letter-spacing: 0;
    }
  }

  .output-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;

    &::-webkit-scrollbar { width: 6px; }
    &::-webkit-scrollbar-track { background: transparent; }
    &::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 3px; }
  }

  .output-placeholder {
    color: var(--text-muted);
    font-size: 12px;
    text-align: center;
    padding: 32px 0;
  }

  .output-running, .output-pending {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-muted);
    font-size: 12px;
    padding: 16px 0;
  }

  .output-success, .output-error {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 12px;
  }

  .output-check { width: 16px; height: 16px; &.success { color: #10b981; } &.error { color: #ef4444; } }
  .output-spinner { color: #3b82f6; }
  .output-data {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    padding: 10px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
    margin-top: 8px;
  }

  .output-err-detail {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11px;
    color: #ef4444;
    font-family: 'JetBrains Mono', monospace;
  }
}

.exec-summary {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .summary-header {
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;
  }

  .summary-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: var(--border-primary);
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 8px;
      background: var(--bg-secondary);
      gap: 2px;

      .stat-label {
        font-size: 10px;
        color: var(--text-muted);
      }

      .stat-value {
        font-size: 18px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: var(--text-primary);

        &.success { color: #10b981; }
        &.running { color: #3b82f6; }
        &.error { color: #ef4444; }
      }
    }
  }

  .summary-progress {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;

    .progress-track {
      flex: 1;
      height: 4px;
      background: rgba(255,255,255,0.08);
      border-radius: 2px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      border-radius: 2px;
      transition: width 0.3s ease;
    }

    .progress-pct {
      font-size: 11px;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-secondary);
      min-width: 32px;
      text-align: right;
    }
  }

  .summary-logs {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .logs-header {
      padding: 6px 12px;
      font-size: 10px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-primary);
      flex-shrink: 0;
    }

    .logs-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 6px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      line-height: 1.5;

      &::-webkit-scrollbar { width: 4px; }
      &::-webkit-scrollbar-track { background: transparent; }
      &::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 2px; }
    }
  }
}

.exec-empty {
  color: var(--text-muted);
  padding: 16px 0;
}

.exec-log-item {
  display: flex;
  gap: 12px;
  padding: 3px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);

  .log-time {
    color: var(--text-muted);
    flex-shrink: 0;
    font-size: 11px;
  }

  .log-text {
    color: var(--text-secondary);
    word-break: break-all;
  }

  &.log-success .log-text {
    color: #22c55e;
  }

  &.log-error .log-text {
    color: #ef4444;
  }

  &.log-warning .log-text {
    color: #f59e0b;
  }
}

.exec-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: var(--text-muted);

  .exec-spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid var(--border-primary);
    border-top-color: var(--color-primary, #6366f1);
    border-radius: 50%;
    animation: exec-spin 0.8s linear infinite;
  }
}

@keyframes exec-spin {
  to { transform: rotate(360deg); }
}
</style>
