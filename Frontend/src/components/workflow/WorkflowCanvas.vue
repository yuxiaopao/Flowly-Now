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
      v-model:nodes="flowNodes"
      v-model:edges="flowEdges"
      :node-types="nodeTypes"
      :default-viewport="defaultViewport"
      :min-zoom="WORKFLOW_CANVAS_ZOOM.min"
      :max-zoom="WORKFLOW_CANVAS_ZOOM.max"
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
      <Background :gap="16" />

      <MiniMap
        v-if="showMiniMapEnabled"
        :node-color="getMiniMapNodeColor"
        :node-stroke-width="3"
        pannable
        zoomable
      />

      <template #node-start="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="StartNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-end="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="EndNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-llm="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="LLMNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-prompt="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="PromptNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-condition="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ConditionNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-tool="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ToolNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-input="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="InputNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-output="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="OutputNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-http="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="HttpNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-code="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="CodeNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-loop="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="LoopNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-variable="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="VariableNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-switch="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SwitchNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-delay="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="DelayNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-transform="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="TransformNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-image_generation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ImageGenerationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-video_generation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="VideoGenerationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-audio_generation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="AudioGenerationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-subtitle_generation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SubtitleGenerationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-video_translation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="VideoTranslationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-video_upload="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="VideoUploadNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-subtitle_translate="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SubtitleTranslateNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-segment_dubbing="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SegmentDubbingNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-lip_sync="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="LipSyncNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-subtitle_burn="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SubtitleBurnNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-image_editing="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ImageEditingNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-dataset_upload="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="DatasetUploadNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-data_annotation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="DataAnnotationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-data_augmentation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="DataAugmentationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-model_training="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ModelTrainingNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-yolo_training="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="YoloTrainingNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-clip_classification="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ClipClassificationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-clip_retrieval="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ClipRetrievalNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-project_profiler="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ProjectProfilerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-model_evaluation="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ModelEvaluationNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-model_deployment="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ModelDeploymentNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-website_generator="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="WebsiteGeneratorNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-environment_provision="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="EnvironmentProvisionNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-site_qa="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SiteQaNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-site_preview="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SitePreviewNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-project_agent="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ProjectAgentNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-backend_setup="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="BackendSetupNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-frontend_setup="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="FrontendSetupNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-ui_beautify="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="UiBeautifyNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-site_code_review="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SiteCodeReviewNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-document_loader="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="DocumentLoaderNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-embedding="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="EmbeddingNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-vector_store="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="VectorStoreNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-retriever="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="RetrieverNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-reranker="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="RerankerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-agent="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="AgentNodeComponent"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-planner="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="PlannerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-executor="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ExecutorNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-memory="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="MemoryNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-file_reader="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="FileReaderNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-file_writer="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="FileWriterNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-web_scraper="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="WebScraperNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-csv_transform="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="CsvTransformNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-json_transform="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="JsonTransformNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-email="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="EmailNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-subworkflow="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SubworkflowNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-manual="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ManualTriggerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-schedule="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="ScheduleTriggerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-form="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="FormTriggerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-webhook="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="WebhookTriggerNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-split="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SplitBatchesNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-merge="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="MergeNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-filter="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="FilterNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-datetime="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="DateTimeNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>

      <template #node-set="{ data, id, selected }">
        <WorkflowNodeHost
          :id="id"
          :node-component="SetNode"
          :data="data"
          :selected="selected"
          @select="handleCustomNodeSelect"
        />
      </template>
    </VueFlow>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/minimap/dist/style.css'
import { WORKFLOW_CANVAS_VIEWPORT, WORKFLOW_CANVAS_ZOOM } from '@/config/workflowCanvas'
import WorkflowNodeHost from './WorkflowNodeHost.vue'

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
import VideoTranslationNode from './nodes/VideoTranslationNode.vue'
import VideoUploadNode from './nodes/VideoUploadNode.vue'
import SubtitleTranslateNode from './nodes/SubtitleTranslateNode.vue'
import SegmentDubbingNode from './nodes/SegmentDubbingNode.vue'
import LipSyncNode from './nodes/LipSyncNode.vue'
import SubtitleBurnNode from './nodes/SubtitleBurnNode.vue'
import ImageEditingNode from './nodes/ImageEditingNode.vue'
import DatasetUploadNode from './nodes/DatasetUploadNode.vue'
import DataAnnotationNode from './nodes/DataAnnotationNode.vue'
import DataAugmentationNode from './nodes/DataAugmentationNode.vue'
import ModelTrainingNode from './nodes/ModelTrainingNode.vue'
import YoloTrainingNode from './nodes/YoloTrainingNode.vue'
import ProjectProfilerNode from './nodes/ProjectProfilerNode.vue'
import ModelEvaluationNode from './nodes/ModelEvaluationNode.vue'
import ModelDeploymentNode from './nodes/ModelDeploymentNode.vue'
import WebsiteGeneratorNode from './nodes/WebsiteGeneratorNode.vue'
import EnvironmentProvisionNode from './nodes/EnvironmentProvisionNode.vue'
import SiteQaNode from './nodes/SiteQaNode.vue'
import SitePreviewNode from './nodes/SitePreviewNode.vue'
import ProjectAgentNode from './nodes/ProjectAgentNode.vue'
import BackendSetupNode from './nodes/BackendSetupNode.vue'
import FrontendSetupNode from './nodes/FrontendSetupNode.vue'
import UiBeautifyNode from './nodes/UiBeautifyNode.vue'
import SiteCodeReviewNode from './nodes/SiteCodeReviewNode.vue'
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
import ManualTriggerNode from './nodes/ManualTriggerNode.vue'
import ScheduleTriggerNode from './nodes/ScheduleTriggerNode.vue'
import FormTriggerNode from './nodes/FormTriggerNode.vue'
import SplitBatchesNode from './nodes/SplitBatchesNode.vue'
import SetNode from './nodes/SetNode.vue'
import DateTimeNode from './nodes/DateTimeNode.vue'
import FilterNode from './nodes/FilterNode.vue'
import MergeNode from './nodes/MergeNode.vue'
import WebhookTriggerNode from './nodes/WebhookTriggerNode.vue'

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
    default: () => ({ ...WORKFLOW_CANVAS_VIEWPORT }),
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
  'resume',
  'update:nodes',
  'update:edges'
])

const flowNodes = computed({
  get: () => props.nodes,
  set: (value) => emit('update:nodes', value)
})

const flowEdges = computed({
  get: () => props.edges,
  set: (value) => emit('update:edges', value)
})

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

const nodeTypes = [
  'start', 'end', 'manual', 'schedule', 'webhook', 'form',
  'llm', 'prompt', 'condition', 'split', 'filter', 'merge',
  'tool', 'input', 'output', 'http', 'code', 'set', 'datetime',
  'loop', 'variable', 'switch', 'delay', 'transform',
  'image_generation', 'video_generation', 'audio_generation', 'subtitle_generation',
  'video_upload', 'subtitle_translate', 'segment_dubbing', 'lip_sync', 'subtitle_burn',
  'video_translation', 'image_editing',
  'dataset_upload', 'data_annotation', 'data_augmentation', 'model_training', 'yolo_training', 'clip_classification', 'clip_retrieval', 'project_profiler', 'model_evaluation', 'model_deployment',
  'yolo_training', 'clip_classification', 'clip_retrieval',
  'website_generator', 'backend_setup', 'frontend_setup', 'ui_beautify', 'site_code_review',
  'environment_provision', 'site_qa', 'site_preview', 'project_agent',
  'document_loader', 'embedding', 'vector_store', 'retriever', 'reranker',
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
    // Triggers
    manual: '#f59e0b',
    schedule: '#06b6d4',
    webhook: '#3b82f6',
    form: '#8b5cf6',
    // Control Flow
    split: '#ec4899',
    filter: '#f97316',
    merge: '#22c55e',
    // Utilities
    datetime: '#14b8a6',
    set: '#14b8a6',
    // Multimodal & Generation
    image_generation: '#ec4899',
    video_generation: '#8b5cf6',
    audio_generation: '#06b6d4',
    subtitle_generation: '#f59e0b',
    video_upload: '#0284c7',
    subtitle_translate: '#0ea5e9',
    segment_dubbing: '#06b6d4',
    lip_sync: '#8b5cf6',
    subtitle_burn: '#f59e0b',
    video_translation: '#64748b',
    image_editing: '#f97316',
    // ML & Training
    dataset_upload: '#22c55e',
    data_annotation: '#14b8a6',
    data_augmentation: '#f59e0b',
    model_training: '#ef4444',
    project_profiler: '#a855f7',
    model_evaluation: '#3b82f6',
    model_deployment: '#10b981',
    website_generator: '#8b5cf6',
    backend_setup: '#6366f1',
    frontend_setup: '#818cf8',
    ui_beautify: '#a855f7',
    site_code_review: '#10b981',
    environment_provision: '#06b6d4',
    site_qa: '#10b981',
    site_preview: '#8b5cf6',
    project_agent: '#ec4899',
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

/** 自定义节点 emit('select') → 同步 Editor PropertyPanel（根因：节点 @click.stop 阻止 VueFlow node-click） */
function handleCustomNodeSelect(nodeId) {
  if (!nodeId) return
  const node = props.nodes.find((n) => n.id === nodeId)
  if (node) {
    emit('node-click', { node })
  }
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
  background-color: var(--canvas-bg);
  transition: background-color 0.3s ease;
}

// 画布网格点 / 线颜色跟随主题（覆盖 Background 组件默认 pattern 色）
:deep(.vue-flow__background) {
  pattern circle,
  pattern path {
    fill: var(--canvas-pattern);
    stroke: var(--canvas-pattern);
  }
}

// 小地图背景跟随主题
:deep(.vue-flow__minimap) {
  background-color: var(--canvas-minimap-bg);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
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
  background: var(--bg-elevated);
  backdrop-filter: blur(12px);
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: var(--border-primary);
}

.zoom-level {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
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
  background: var(--bg-elevated);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
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
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
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
  background: var(--bg-elevated);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-primary);
  box-shadow: var(--shadow-md);
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
    background: var(--info-bg);
    color: var(--info);
    border: 1px solid var(--accent-blue-soft);

    .indicator-dot {
      background: var(--info);
      box-shadow: 0 0 8px var(--accent-blue-soft);
    }
  }

  &.completed {
    background: var(--success-bg);
    color: var(--success);
    border: 1px solid var(--accent-emerald-soft);

    .indicator-dot {
      background: var(--success);
      animation: none;
    }
  }

  &.failed {
    background: var(--error-bg);
    color: var(--error);
    border: 1px solid var(--accent-rose-soft);

    .indicator-dot {
      background: var(--error);
      animation: none;
    }
  }

  &.paused {
    background: var(--warning-bg);
    color: var(--warning);
    border: 1px solid var(--accent-amber-soft);

    .indicator-dot {
      background: var(--warning);
      animation: none;
    }
  }

  &.cancelled,
  &.idle,
  &.pending {
    background: var(--surface-muted);
    color: var(--text-tertiary);
    border: 1px solid var(--border-secondary);

    .indicator-dot {
      background: var(--text-tertiary);
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
    background: var(--surface-strong);
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--info), var(--success));
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
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
    color: var(--success);
  }

  &.running {
    color: var(--info);
  }

  &.failed {
    color: var(--error);
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
      box-shadow: 0 0 0 2px var(--accent-emerald-soft), 0 4px 20px var(--success-bg) !important;
    }
  }

  // Failed node error style
  &.is-failed {
    .node-card,
    .llm-node,
    .start-end-node,
    .node-wrapper {
      box-shadow: 0 0 0 2px var(--accent-rose-soft), 0 4px 20px var(--error-bg) !important;
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
    box-shadow: var(--shadow-md), 0 0 0 0 var(--accent-blue-soft);
  }
  50% {
    box-shadow: var(--shadow-md), 0 0 0 8px transparent;
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
    stroke: var(--info);
    stroke-width: 2;
    animation: edge-flow 1s linear infinite;
  }

  &.completed-path {
    stroke: var(--success);
    stroke-width: 2;
  }

  &.error-path {
    stroke: var(--error);
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
