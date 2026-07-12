<template>
  <div
    class="nl-creator"
    :class="{ 'sidebar-open': showHistorySidebar }"
  >
    <!-- ============================================ -->
    <!-- 历史记录侧边栏 (Doubao style) -->
    <!-- ============================================ -->
    <Teleport to="body">
      <div
        v-if="showHistorySidebar"
        class="sidebar-overlay"
        aria-hidden="true"
        @click="showHistorySidebar = false"
      />
      <aside
        class="history-sidebar"
        :class="{ open: showHistorySidebar }"
        :style="historySidebarStyle"
        :aria-hidden="!showHistorySidebar"
      >
        <div class="sidebar-header">
          <div class="sidebar-title">
            <MessageSquare class="title-icon" />
            <span>对话历史</span>
          </div>
          <button
            class="sidebar-close-btn"
            @click="showHistorySidebar = false"
          >
            <X class="close-icon" />
          </button>
        </div>

        <div class="new-chat-btn-wrapper">
          <button
            class="new-chat-btn"
            @click="handleNewTab"
          >
            <Plus class="btn-icon" />
            <span>新建对话</span>
          </button>
        </div>

        <div class="sidebar-search">
          <label
            for="history-search"
            class="sr-only"
          >搜索对话</label>
          <el-input
            id="history-search"
            v-model="historySearchQuery"
            placeholder="搜索对话..."
            clearable
            size="small"
            @input="handleHistorySearch"
          >
            <template #prefix>
              <Search class="search-icon" />
            </template>
          </el-input>
        </div>

        <!-- 批量操作栏 -->
        <div
          v-if="batchMode"
          class="batch-actions-bar"
        >
          <div class="batch-info">
            <CheckSquare class="batch-icon" />
            <span>已选择 {{ selectedSessions.length }} 项</span>
          </div>
          <div class="batch-buttons">
            <button
              class="batch-btn danger"
              :disabled="selectedSessions.length === 0"
              @click="handleBatchDelete"
            >
              <Trash2 class="batch-btn-icon" />
              <span>删除</span>
            </button>
            <button
              class="batch-btn"
              @click="handleCancelBatch"
            >
              <X class="batch-btn-icon" />
              <span>取消</span>
            </button>
          </div>
        </div>

        <div
          v-if="!batchMode"
          class="filter-tags"
        >
          <button
            class="filter-tag"
            :class="{ active: !historyStatusFilter }"
            @click="historyStatusFilter = ''; handleHistorySearch()"
          >
            全部
          </button>
          <button
            class="filter-tag"
            :class="{ active: historyStatusFilter === 'completed' }"
            @click="historyStatusFilter = 'completed'; handleHistorySearch()"
          >
            已完成
          </button>
          <button
            class="filter-tag"
            :class="{ active: historyStatusFilter === 'generating' }"
            @click="historyStatusFilter = 'generating'; handleHistorySearch()"
          >
            生成中
          </button>
        </div>

        <div
          v-loading="historyLoading"
          class="session-list"
        >
          <div
            v-for="session in filteredHistorySessions"
            :key="session.sessionId || session.session_id || session.id"
            class="session-item"
            :data-sid="session.sessionId || session.session_id || session.id"
            :data-name="session.name"
            :class="{
              'is-active': activeSessionId === (session.sessionId || session.session_id || session.id),
              'is-selected': selectedSessions.includes(session.sessionId || session.session_id || session.id)
            }"
            @click="handleSessionItemClick($event)"
          >
            <div
              v-if="batchMode"
              class="session-checkbox"
              @click.stop
            >
              <el-checkbox
                :model-value="selectedSessions.includes(session.sessionId || session.session_id)"
                @update:model-value="toggleSessionSelection(session)"
              />
            </div>

            <div class="session-content">
              <div class="session-header">
                <span class="session-name">{{ session.name || '未命名会话' }}</span>
                <el-tag
                  v-if="session.status"
                  size="small"
                  :type="getStatusType(session.status)"
                  class="status-tag"
                >
                  {{ getStatusText(session.status) }}
                </el-tag>
                <el-tag
                  v-if="session.workflow_id || session.workflow"
                  size="small"
                  type="success"
                  class="workflow-tag"
                >
                  <GitBranch class="tag-icon" />
                </el-tag>
              </div>
              <div class="session-desc">
                {{ session.description || '暂无描述' }}
              </div>
              <div class="session-meta">
                <Clock class="meta-icon" />
                <span>{{ formatDate(session.createdAt || session.created_at) }}</span>
                <span
                  v-if="session.nodeCount ?? session.node_count"
                  class="meta-divider"
                >·</span>
                <span v-if="session.nodeCount ?? session.node_count">{{ session.nodeCount ?? session.node_count }} 节点</span>
              </div>
            </div>

            <div
              v-if="!batchMode"
              class="session-actions"
            >
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleSessionAction(cmd, session)"
              >
                <button class="action-btn">
                  <MoreVertical class="action-icon" />
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="open-tab">
                      <ExternalLink class="dropdown-icon" />
                      在新标签中打开
                    </el-dropdown-item>
                    <el-dropdown-item command="rename">
                      <Edit2 class="dropdown-icon" />
                      重命名
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="delete"
                      divided
                    >
                      <Trash2 class="dropdown-icon danger" />
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <div
            v-if="!historyLoading && filteredHistorySessions.length === 0"
            class="empty-state"
          >
            <History class="empty-icon" />
            <div class="empty-title">
              暂无对话记录
            </div>
            <div class="empty-hint">
              点击上方「新建对话」开始
            </div>
          </div>
        </div>

        <div
          v-if="!batchMode"
          class="sidebar-footer"
        >
          <button
            class="footer-btn"
            @click="handleSelectAll"
          >
            <CheckSquare class="footer-icon" />
            <span>全选</span>
          </button>
          <button
            class="footer-btn danger"
            :disabled="selectedSessions.length === 0"
            @click="handleBatchDelete"
          >
            <Trash2 class="footer-icon" />
            <span>批量删除</span>
          </button>
        </div>
      </aside>
    </Teleport>

    <!-- ============================================ -->
    <!-- 主内容区 -->
    <!-- ============================================ -->
    <div class="creator-main">
      <!-- 顶部工具栏 -->
      <div class="creator-toolbar">
        <button
          class="toolbar-btn"
          @click="showHistorySidebar = true"
        >
          <Menu class="toolbar-icon" />
          <span>历史对话</span>
          <span
            v-if="historyTotal > 0"
            class="toolbar-badge"
          >{{ historyTotal }}</span>
        </button>

        <div class="toolbar-right">
          <button
            class="toolbar-btn new-tab-btn"
            :disabled="currentTabLoading"
            @click="handleNewTab"
          >
            <Plus class="toolbar-icon" />
            <span>新标签</span>
          </button>
        </div>
      </div>

      <!-- ============================================ -->
      <!-- 浏览器风格标签页 -->
      <!-- ============================================ -->
      <div
        v-if="tabs.length > 0"
        class="tab-bar"
      >
        <div class="tab-scroll-container">
          <div class="tab-list">
            <div
              v-for="tab in tabs"
              :key="tab.id"
              class="tab-item"
              :class="{
                'is-active': activeTabId === tab.id,
                'is-loading': tab.isLoading
              }"
              @click="switchTab(tab.id)"
              @dblclick="handleRenameTab(tab)"
            >
              <!-- Tab Icon -->
              <img
                v-if="!tab.isLoading"
                :src="currentTabLogo"
                alt="Flowly"
                class="tab-icon"
              >
              <div
                v-else
                class="tab-loading"
              >
                <span /><span /><span />
              </div>

              <!-- Tab Title -->
              <span
                class="tab-title"
                :title="tab.title"
              >
                {{ tab.title || '新对话' }}
              </span>

              <!-- Has workflow indicator -->
              <span
                v-if="tab.hasWorkflow && !tab.isLoading"
                class="tab-workflow-dot"
                title="已生成工作流"
              />

              <!-- Close Button -->
              <button
                class="tab-close"
                :title="tab.isDirty ? '关闭并保存' : '关闭'"
                @click.stop="closeTab(tab.id)"
              >
                <X class="tab-close-icon" />
              </button>
            </div>
          </div>
        </div>

        <!-- Tab Actions -->
        <div class="tab-actions">
          <button
            class="tab-action-btn"
            title="新建标签"
            @click="handleNewTab"
          >
            <Plus class="tab-action-icon" />
          </button>
          <el-dropdown
            trigger="click"
            placement="bottom-end"
            @command="handleTabAction"
          >
            <button
              class="tab-action-btn"
              title="更多操作"
            >
              <ChevronDown class="tab-action-icon" />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="close-all">
                  <XCircle class="dropdown-icon" />
                  关闭所有标签
                </el-dropdown-item>
                <el-dropdown-item command="close-others">
                  <MinusCircle class="dropdown-icon" />
                  关闭其他标签
                </el-dropdown-item>
                <el-dropdown-item command="close-saved">
                  <CheckCircle class="dropdown-icon" />
                  关闭已保存的标签
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- 模型选择器 -->
      <div class="model-selector-bar">
        <div class="model-selector">
          <label class="model-label">选择模型</label>
          <el-select
            v-model="selectedModel"
            placeholder="选择 AI 模型"
            filterable
            size="large"
            class="model-select"
            :loading="modelsLoading"
            no-data-text="加载模型中..."
            data-testid="model-selector"
            @focus="loadModels"
          >
            <template v-if="Object.keys(modelOptions).length > 0">
              <el-option-group
                v-for="(modelList, provider) in modelOptions"
                :key="provider"
                :label="provider"
              >
                <el-option
                  v-for="opt in modelList"
                  :key="opt.modelId"
                  :label="opt.name"
                  :value="opt.modelId"
                >
                  <div class="model-option-content">
                    <span>{{ opt.name }}</span>
                    <span
                      v-if="opt.modelId === selectedModel"
                      class="model-selected-badge"
                    >使用中</span>
                  </div>
                </el-option>
              </el-option-group>
            </template>
            <template v-else>
              <el-option
                label="加载中..."
                value=""
                disabled
              />
            </template>
          </el-select>
        </div>
        <el-checkbox
          v-model="showAllModels"
          class="show-all-models"
          @change="loadModels(true)"
        >
          显示全部模型
        </el-checkbox>
        <div
          v-if="selectedModel"
          class="model-info"
        >
          <span class="model-name">{{ selectedModel }}</span>
          <el-tag
            v-if="selectedModelProvider"
            size="small"
            type="info"
          >
            {{ selectedModelProvider }}
          </el-tag>
        </div>
        <div
          v-else-if="!modelsLoading && availableModels.length === 0"
          class="model-info model-unavailable"
        >
          <el-icon><AlertTriangle /></el-icon>
          <span>无可用模型，请确保已配置 API Key 或启动 Ollama</span>
        </div>
      </div>

      <!-- 聊天容器 -->
      <div class="chat-container">
        <div
          ref="messagesContainer"
          :key="activeTabId"
          class="chat-messages"
        >
          <div
            v-for="(message, index) in currentTabMessages"
            :key="index"
            :class="['message', `message-${message.role}`]"
          >
            <div class="message-avatar">
              <NlAvatar
                :role="message.role"
                size="md"
              />
            </div>
            <div class="message-content">
              <div
                v-if="message.isStreaming || (!message.workflow && message.content)"
                class="message-text"
              >
                <template v-if="message.isStreaming">
                  {{ message.content }}<span class="cursor">|</span>
                </template>
                <template v-else>
                  {{ message.content }}
                </template>
              </div>
              <div
                v-else-if="message.workflow"
                class="message-text message-text--summary"
              >
                已生成工作流: {{ message.workflow.name || '未命名' }}
              </div>

              <div
                v-if="message.workflow"
                class="workflow-preview"
              >
                <div class="preview-header">
                  <GitBranch class="preview-icon" />
                  <span class="preview-name">{{ message.workflow.name }}</span>
                  <el-tag
                    size="small"
                    type="info"
                  >
                    {{ message.workflow.nodes?.length || 0 }} 节点
                  </el-tag>
                </div>

                <div
                  v-if="message.workflow.description"
                  class="preview-desc"
                >
                  {{ message.workflow.description }}
                </div>

                <div class="preview-nodes">
                  <div
                    v-for="(node, idx) in (message.workflow.nodes || []).slice(0, 8)"
                    :key="idx"
                    class="node-item"
                  >
                    <span class="node-name">{{ node.name || node.type }}</span>
                    <el-tag
                      size="small"
                      type="info"
                    >
                      {{ node.type }}
                    </el-tag>
                  </div>
                  <span
                    v-if="(message.workflow.nodes?.length || 0) > 8"
                    class="more-nodes"
                  >
                    +{{ message.workflow.nodes.length - 8 }} 更多
                  </span>
                </div>

                <div class="preview-actions">
                  <el-button
                    size="small"
                    @click="viewWorkflow(message.workflow)"
                  >
                    查看详情
                  </el-button>
                  <el-button
                    size="small"
                    type="primary"
                    @click="saveWorkflow(message.workflow)"
                  >
                    <Save class="btn-icon-sm" />
                    保存到我的工作流
                  </el-button>
                </div>
              </div>

              <div
                v-if="message.suggestions?.length && !message.isStreaming"
                class="suggestions"
              >
                <span class="suggestions-label">您可以：</span>
                <button
                  v-for="suggestion in message.suggestions"
                  :key="suggestion"
                  class="suggestion-btn"
                  @click="continueConversation(suggestion)"
                >
                  {{ suggestion }}
                </button>
              </div>

              <!-- Email Config Guidance -->
              <EmailConfigGuide
                v-if="message.emailGuidance && !message.isStreaming"
                :guidance="message.emailGuidance"
              />

              <!-- General Node Config Guidance -->
              <NodeConfigGuide
                v-if="message.nodeGuidance && !message.isStreaming"
                :guidance="message.nodeGuidance"
              />

              <!-- Intent Analysis Display -->
              <div
                v-if="message.intent && !message.isStreaming"
                class="intent-display"
              >
                <span class="intent-label">识别意图：</span>
                <el-tag
                  size="small"
                  :type="getIntentTagType(message.intent.type)"
                  class="intent-tag"
                >
                  {{ getIntentText(message.intent.type) }}
                </el-tag>
                <span
                  v-if="message.intent.detail"
                  class="intent-detail"
                >{{ message.intent.detail }}</span>
              </div>

              <div class="message-time">
                {{ formatTime(message.timestamp) }}
              </div>
            </div>
          </div>

          <div
            v-if="currentTabLoading"
            class="message message-assistant"
          >
            <div class="message-avatar">
              <NlAvatar
                role="assistant"
                size="md"
              />
            </div>
            <div class="message-content">
              <!-- Enhanced Streaming Progress Indicator -->
              <div
                v-if="isStreaming"
                class="streaming-progress"
              >
                <div class="progress-header">
                  <div class="progress-stage">
                    <span
                      class="stage-dot"
                      :class="{ 'is-active': isStreaming }"
                    />
                    <span class="stage-text">{{ streamStageLabel }}</span>
                  </div>
                  <div class="progress-stats">
                    <span
                      v-if="tokenCount > 0"
                      class="token-count"
                    >{{ tokenCount }} tokens</span>
                    <span
                      v-if="estimatedTimeRemaining"
                      class="time-remaining"
                    >{{ estimatedTimeRemaining }}</span>
                  </div>
                </div>
                <div class="progress-steps">
                  <div
                    v-for="(step, idx) in streamSteps"
                    :key="step"
                    class="progress-step"
                    :class="{
                      'is-active': idx <= currentStreamStepIndex,
                      'is-current': idx === currentStreamStepIndex
                    }"
                  >
                    <span class="step-dot" />
                    <span class="step-label">{{ step }}</span>
                  </div>
                </div>

                <!-- 深度思考内容实时展示 -->
                <div
                  v-if="streamThinking"
                  class="thinking-display"
                >
                  <div class="thinking-header">
                    <Brain class="thinking-icon" />
                    <span class="thinking-label">深度思考</span>
                  </div>
                  <div class="thinking-content">
                    {{ streamThinking }}
                  </div>
                </div>

                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :style="{ width: streamProgress + '%' }"
                  />
                </div>
                <div class="progress-percentage">
                  {{ Math.round(streamProgress) }}%
                </div>
              </div>
              <div
                v-else
                class="typing-indicator"
              >
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        </div>

        <!-- Mini Workflow Preview Panel (embedded) with Edge Visualization -->
        <div
          v-if="currentTab?.hasWorkflow && !currentTabLoading"
          class="mini-workflow-preview"
        >
          <div class="preview-panel-header">
            <GitBranch class="preview-panel-icon" />
            <span class="preview-panel-title">工作流预览</span>
            <div
              v-if="workflowValidation.nodeCount ?? workflowValidation.node_count"
              class="preview-stats"
            >
              <el-tag
                size="small"
                type="info"
              >
                {{ workflowValidation.nodeCount ?? workflowValidation.node_count }} 节点
              </el-tag>
              <el-tag
                size="small"
                type="info"
              >
                {{ workflowValidation.edge_count }} 连线
              </el-tag>
            </div>
            <el-button
              size="small"
              text
              @click="showMiniPreview = !showMiniPreview"
            >
              {{ showMiniPreview ? '收起' : '展开' }}
            </el-button>
          </div>
          <div
            v-if="showMiniPreview"
            class="preview-panel-body"
          >
            <!-- Workflow Validation Display -->
            <div
              v-if="workflowValidation.errors.length || workflowValidation.warnings.length"
              class="validation-display"
            >
              <div
                v-if="workflowValidation.errors.length"
                class="validation-errors"
              >
                <div
                  v-for="(error, idx) in workflowValidation.errors"
                  :key="'err-' + idx"
                  class="validation-error"
                >
                  <AlertCircle class="validation-icon error" />
                  <span>{{ error }}</span>
                </div>
              </div>
              <div
                v-if="workflowValidation.warnings.length"
                class="validation-warnings"
              >
                <div
                  v-for="(warning, idx) in workflowValidation.warnings"
                  :key="'warn-' + idx"
                  class="validation-warning"
                >
                  <AlertTriangle class="validation-icon warning" />
                  <span>{{ warning }}</span>
                </div>
              </div>
            </div>

            <!-- Cost Display -->
            <div
              v-if="workflowValidation.estimated_cost !== null"
              class="cost-display"
            >
              <span class="cost-label">预估成本:</span>
              <span class="cost-value">${{ workflowValidation.estimated_cost.toFixed(4) }}</span>
            </div>

            <!-- Email Config Guidance in Right Panel -->
            <EmailConfigGuide
              v-if="emailGuidance"
              :guidance="emailGuidance"
            />

            <!-- General Node Config Guidance in Right Panel -->
            <NodeConfigGuide
              v-if="nodeGuidance"
              :guidance="nodeGuidance"
            />

            <!-- Workflow Visualization with VueFlow -->
            <div class="workflow-visualization">
              <div
                v-if="nlNodes.length === 0"
                class="empty-workflow-hint"
              >
                <GitBranch class="empty-icon" />
                <span>{{ currentTabLoading ? '正在生成工作流...' : '暂无工作流预览，请发送描述生成' }}</span>
              </div>
              <VueFlow
                v-else
                v-model:nodes="nlNodes"
                v-model:edges="nlEdges"
                :node-types="nlNodeTypes"
                :default-viewport="{ ...WORKFLOW_CANVAS_VIEWPORT, zoom: 0.85 }"
                :min-zoom="WORKFLOW_CANVAS_ZOOM.min"
                :max-zoom="WORKFLOW_CANVAS_ZOOM.max"
                :snap-to-grid="true"
                :snap-grid="[16, 16]"
                :nodes-draggable="false"
                :nodes-connectable="false"
                :elements-selectable="true"
                fit-view-on-init
                @node-click="handleNlNodeClick"
              >
                <template #node-start="{ data }">
                  <StartNode :data="data" />
                </template>
                <template #node-end="{ data }">
                  <EndNode :data="data" />
                </template>
                <template #node-llm="{ data }">
                  <LLMNode :data="data" />
                </template>
                <template #node-input="{ data }">
                  <InputNode :data="data" />
                </template>
                <template #node-output="{ data }">
                  <OutputNode :data="data" />
                </template>
                <template #node-condition="{ data }">
                  <ConditionNode :data="data" />
                </template>
                <template #node-delay="{ data }">
                  <DelayNode :data="data" />
                </template>
                <template #node-http="{ data }">
                  <HttpNode :data="data" />
                </template>
                <template #node-code="{ data }">
                  <CodeNode :data="data" />
                </template>
                <template #node-variable="{ data }">
                  <VariableNode :data="data" />
                </template>
                <template #node-prompt="{ data }">
                  <PromptNode :data="data" />
                </template>
                <template #node-email="{ data }">
                  <EmailNode :data="data" />
                </template>
                <template #node-memory="{ data }">
                  <MemoryNode :data="data" />
                </template>
                <template #node-tool="{ data }">
                  <ToolNode :data="data" />
                </template>
                <template #node-retriever="{ data }">
                  <RetrieverNode :data="data" />
                </template>
                <template #node-vector_store="{ data }">
                  <VectorStoreNode :data="data" />
                </template>
                <template #node-embedding="{ data }">
                  <EmbeddingNode :data="data" />
                </template>
                <template #node-subworkflow="{ data }">
                  <SubworkflowNode :data="data" />
                </template>
                <template #node-executor="{ data }">
                  <ExecutorNode :data="data" />
                </template>
                <template #node-planner="{ data }">
                  <PlannerNode :data="data" />
                </template>
                <template #node-agent="{ data }">
                  <AgentNode :data="data" />
                </template>
                <template #node-loop="{ data }">
                  <LoopNode :data="data" />
                </template>
                <template #node-switch="{ data }">
                  <SwitchNode :data="data" />
                </template>
                <template #node-file_reader="{ data }">
                  <FileReaderNode :data="data" />
                </template>
                <template #node-file_writer="{ data }">
                  <FileWriterNode :data="data" />
                </template>
                <template #node-transform="{ data }">
                  <TransformNode :data="data" />
                </template>
                <template #node-json_transform="{ data }">
                  <JsonTransformNode :data="data" />
                </template>
                <template #node-csv_transform="{ data }">
                  <CsvTransformNode :data="data" />
                </template>
                <template #node-document_loader="{ data }">
                  <DocumentLoaderNode :data="data" />
                </template>
                <template #node-web_scraper="{ data }">
                  <WebScraperNode :data="data" />
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
                <template #node-yolo_training="{ data, id, selected }">
                  <YoloTrainingNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-project_profiler="{ data, id, selected }">
                  <ProjectProfilerNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-model_evaluation="{ data }">
                  <ModelEvaluationNode :data="data" />
                </template>
                <template #node-model_deployment="{ data }">
                  <ModelDeploymentNode :data="data" />
                </template>
                <template #node-image_generation="{ data }">
                  <ImageGenerationNode :data="data" />
                </template>
                <template #node-image_editing="{ data }">
                  <ImageEditingNode :data="data" />
                </template>
                <template #node-video_generation="{ data }">
                  <VideoGenerationNode :data="data" />
                </template>
                <template #node-audio_generation="{ data }">
                  <AudioGenerationNode :data="data" />
                </template>
                <template #node-subtitle_generation="{ data, id, selected }">
                  <SubtitleGenerationNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-video_upload="{ data, id, selected }">
                  <VideoUploadNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-subtitle_translate="{ data, id, selected }">
                  <SubtitleTranslateNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-segment_dubbing="{ data, id, selected }">
                  <SegmentDubbingNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-lip_sync="{ data, id, selected }">
                  <LipSyncNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-subtitle_burn="{ data, id, selected }">
                  <SubtitleBurnNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-video_translation="{ data, id, selected }">
                  <VideoTranslationNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-website_generator="{ data }">
                  <WebsiteGeneratorNode :data="data" />
                </template>
                <template #node-environment_provision="{ data, id, selected }">
                  <EnvironmentProvisionNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-site_qa="{ data, id, selected }">
                  <SiteQaNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-site_preview="{ data, id, selected }">
                  <SitePreviewNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-project_agent="{ data, id, selected }">
                  <ProjectAgentNode
                    :id="id"
                    :data="data"
                    :selected="selected"
                  />
                </template>
                <template #node-reranker="{ data }">
                  <RerankerNode :data="data" />
                </template>
                <Background :gap="16" />
              </VueFlow>
            </div>

            <!-- Node Configuration Preview -->
            <div
              v-if="selectedNode"
              class="node-config-panel"
            >
              <div class="config-header">
                <Settings class="config-icon" />
                <span class="config-title">{{ selectedNode.name || selectedNode.type }} 配置</span>
                <el-button
                  size="small"
                  link
                  @click="showNodeConfig = !showNodeConfig"
                >
                  {{ showNodeConfig ? '收起' : '编辑' }}
                </el-button>
              </div>
              <div
                v-if="showNodeConfig"
                class="config-body"
              >
                <div class="config-field">
                  <label for="node-name-input">节点名称</label>
                  <el-input
                    id="node-name-input"
                    v-model="editingNodeConfig.name"
                    size="small"
                    placeholder="节点名称"
                    aria-label="节点名称"
                    name="node-name-input"
                  />
                </div>
                <div class="config-field">
                  <label for="node-type-input">节点类型</label>
                  <el-input
                    id="node-type-input"
                    :model-value="selectedNode.type"
                    size="small"
                    disabled
                    aria-label="节点类型"
                  />
                </div>
                <div
                  v-if="selectedNode.config?.model || selectedNode.config?.prompt"
                  class="config-field"
                >
                  <label for="node-model-input">模型</label>
                  <el-input
                    id="node-model-input"
                    v-model="editingNodeConfig.model"
                    size="small"
                    placeholder="模型名称"
                    aria-label="模型名称"
                  />
                </div>
                <div
                  v-if="selectedNode.config?.prompt"
                  class="config-field"
                >
                  <label for="node-prompt-input">提示词</label>
                  <el-input
                    id="node-prompt-input"
                    v-model="editingNodeConfig.prompt"
                    type="textarea"
                    :rows="3"
                    size="small"
                    placeholder="提示词模板"
                    aria-label="提示词模板"
                  />
                </div>
                <div class="config-actions">
                  <el-button
                    size="small"
                    @click="cancelNodeEdit"
                  >
                    取消
                  </el-button>
                  <el-button
                    size="small"
                    type="primary"
                    @click="saveNodeConfig"
                  >
                    保存
                  </el-button>
                </div>
              </div>
            </div>

            <div class="preview-panel-footer">
              <el-button
                size="small"
                @click="viewWorkflow(getCurrentWorkflow())"
              >
                <ExternalLink class="btn-icon-sm" />
                查看详情
              </el-button>
              <el-button
                size="small"
                type="primary"
                @click="saveWorkflow(getCurrentWorkflow())"
              >
                <Save class="btn-icon-sm" />
                保存
              </el-button>
            </div>
          </div>
        </div>

        <div
          v-if="currentTabMessages.length <= 1"
          class="examples"
        >
          <p class="examples-title">
            快速开始：
          </p>
          <div class="examples-grid">
            <div
              class="example-card example-card--chat"
              @click="applyExample('我想做一个智能客服，能自动回答产品问题，复杂问题转人工')"
            >
              <MessageSquare class="example-icon" />
              <span>先聊聊 · 客服场景</span>
            </div>
            <div
              class="example-card"
              @click="applyExample('创建一个简单的问答机器人，可以回答用户关于产品的问题')"
            >
              <MessageSquare class="example-icon" />
              <span>直接生成 · 问答机器人</span>
            </div>
            <div
              class="example-card"
              @click="applyExample('创建一个数据处理工作流，读取CSV文件，进行清洗和转换')"
            >
              <FileSpreadsheet class="example-icon" />
              <span>直接生成 · 数据处理</span>
            </div>
            <div
              class="example-card example-card--chat"
              @click="applyExample('你好，我想了解一下工作流可以做什么')"
            >
              <Languages class="example-icon" />
              <span>先聊聊 · 了解能力</span>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <div class="input-mode-bar">
            <button
              type="button"
              class="mode-chip"
              :class="{ 'mode-chip--active': inputMode === 'thinking' }"
              :disabled="currentTabLoading"
              data-testid="mode-thinking"
              @click="inputMode = 'thinking'"
            >
              <Brain class="mode-chip-icon" />
              <span>深度思考</span>
            </button>
            <button
              type="button"
              class="mode-chip"
              :class="{ 'mode-chip--active': inputMode === 'generate' }"
              :disabled="currentTabLoading"
              data-testid="mode-generate"
              @click="inputMode = 'generate'"
            >
              <GitBranch class="mode-chip-icon" />
              <span>生成工作流</span>
            </button>
            <span class="mode-hint">{{ inputModeHint }}</span>
          </div>
          <el-input
            id="chat-message-input"
            ref="chatInputRef"
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            data-testid="chat-input"
            :placeholder="inputPlaceholder"
            :disabled="currentTabLoading"
            aria-label="输入工作流描述"
            @keydown.enter="handleInputKeydown"
          />
          <div class="input-actions">
            <div class="input-info">
              <span class="hint">Enter 发送, Shift+Enter 换行</span>
            </div>
            <AppButton
              variant="primary"
              :loading="currentTabLoading"
              :disabled="!inputMessage.trim() || _isSending"
              data-testid="send-button"
              @click="sendMessage"
            >
              <Send class="btn-icon" />
              {{ sendButtonLabel }}
            </AppButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 工作流详情对话框 -->
    <el-dialog
      v-model="showWorkflowDetail"
      title="工作流详情"
      width="700px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="true"
      @close="selectedWorkflow = null"
    >
      <div
        v-if="selectedWorkflow"
        class="workflow-detail"
      >
        <h3>{{ selectedWorkflow.name }}</h3>
        <p v-if="selectedWorkflow.description">
          {{ selectedWorkflow.description }}
        </p>

        <h4>节点</h4>
        <div class="detail-nodes">
          <div
            v-for="node in selectedWorkflow.nodes"
            :key="node.id || node.type"
            class="detail-node"
          >
            <span class="node-name">{{ node.name || node.type }}</span>
            <span class="node-type">{{ node.type }}</span>
            <pre
              v-if="node.config"
              class="node-config"
            >{{ JSON.stringify(node.config, null, 2) }}</pre>
          </div>
        </div>

        <h4>连线</h4>
        <div class="detail-edges">
          <div
            v-for="(edge, idx) in selectedWorkflow.edges"
            :key="idx"
            class="detail-edge"
          >
            {{ edge.source }} → {{ edge.target }}
            <span v-if="edge.label">({{ edge.label }})</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showWorkflowDetail = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="saveWorkflow(selectedWorkflow)"
        >
          保存工作流
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import {
  GitBranch, Send, Save,
  MessageSquare, FileSpreadsheet, Languages, AlertTriangle, History, Trash2,
  Search, Clock, MoreVertical, Edit2, AlertCircle, Plus,
  Menu, X, CheckSquare, ExternalLink, ChevronDown, XCircle, MinusCircle, CheckCircle,
  Settings, Brain
} from 'lucide-vue-next'
import { nlWorkflowApi } from '@/api/nl-workflow'
import { createWorkflow } from '@/api/workflow'
import { nlWorkflowToVueFlow, nlWorkflowToSavePayload } from '@/utils/workflowTransform'
import { WORKFLOW_CANVAS_VIEWPORT, WORKFLOW_CANVAS_ZOOM } from '@/config/workflowCanvas'
import AppButton from '@/components/common/AppButton.vue'
import NlAvatar from '@/components/nl-workflow/NlAvatar.vue'
import EmailConfigGuide from '@/components/nl-workflow/EmailConfigGuide.vue'
import NodeConfigGuide from '@/components/nl-workflow/NodeConfigGuide.vue'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
// VueFlow node components for NL workflow preview
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import StartNode from '@/components/workflow/nodes/StartNode.vue'
import EndNode from '@/components/workflow/nodes/EndNode.vue'
import LLMNode from '@/components/workflow/nodes/LLMNode.vue'
import InputNode from '@/components/workflow/nodes/InputNode.vue'
import OutputNode from '@/components/workflow/nodes/OutputNode.vue'
import ConditionNode from '@/components/workflow/nodes/ConditionNode.vue'
import DelayNode from '@/components/workflow/nodes/DelayNode.vue'
import HttpNode from '@/components/workflow/nodes/HttpNode.vue'
import CodeNode from '@/components/workflow/nodes/CodeNode.vue'
import VariableNode from '@/components/workflow/nodes/VariableNode.vue'
import PromptNode from '@/components/workflow/nodes/PromptNode.vue'
import EmailNode from '@/components/workflow/nodes/EmailNode.vue'
import MemoryNode from '@/components/workflow/nodes/MemoryNode.vue'
import ToolNode from '@/components/workflow/nodes/ToolNode.vue'
import RetrieverNode from '@/components/workflow/nodes/RetrieverNode.vue'
import VectorStoreNode from '@/components/workflow/nodes/VectorStoreNode.vue'
import EmbeddingNode from '@/components/workflow/nodes/EmbeddingNode.vue'
import SubworkflowNode from '@/components/workflow/nodes/SubworkflowNode.vue'
import ExecutorNode from '@/components/workflow/nodes/ExecutorNode.vue'
import PlannerNode from '@/components/workflow/nodes/PlannerNode.vue'
import AgentNode from '@/components/workflow/nodes/AgentNode.vue'
import LoopNode from '@/components/workflow/nodes/LoopNode.vue'
import SwitchNode from '@/components/workflow/nodes/SwitchNode.vue'
import FileReaderNode from '@/components/workflow/nodes/FileReaderNode.vue'
import FileWriterNode from '@/components/workflow/nodes/FileWriterNode.vue'
import TransformNode from '@/components/workflow/nodes/TransformNode.vue'
import JsonTransformNode from '@/components/workflow/nodes/JsonTransformNode.vue'
import CsvTransformNode from '@/components/workflow/nodes/CsvTransformNode.vue'
import DocumentLoaderNode from '@/components/workflow/nodes/DocumentLoaderNode.vue'
import WebScraperNode from '@/components/workflow/nodes/WebScraperNode.vue'
import DatasetUploadNode from '@/components/workflow/nodes/DatasetUploadNode.vue'
import DataAnnotationNode from '@/components/workflow/nodes/DataAnnotationNode.vue'
import DataAugmentationNode from '@/components/workflow/nodes/DataAugmentationNode.vue'
import ModelTrainingNode from '@/components/workflow/nodes/ModelTrainingNode.vue'
import ModelEvaluationNode from '@/components/workflow/nodes/ModelEvaluationNode.vue'
import ModelDeploymentNode from '@/components/workflow/nodes/ModelDeploymentNode.vue'
import ImageGenerationNode from '@/components/workflow/nodes/ImageGenerationNode.vue'
import ImageEditingNode from '@/components/workflow/nodes/ImageEditingNode.vue'
import VideoGenerationNode from '@/components/workflow/nodes/VideoGenerationNode.vue'
import AudioGenerationNode from '@/components/workflow/nodes/AudioGenerationNode.vue'
import SubtitleGenerationNode from '@/components/workflow/nodes/SubtitleGenerationNode.vue'
import VideoUploadNode from '@/components/workflow/nodes/VideoUploadNode.vue'
import SubtitleTranslateNode from '@/components/workflow/nodes/SubtitleTranslateNode.vue'
import SegmentDubbingNode from '@/components/workflow/nodes/SegmentDubbingNode.vue'
import LipSyncNode from '@/components/workflow/nodes/LipSyncNode.vue'
import SubtitleBurnNode from '@/components/workflow/nodes/SubtitleBurnNode.vue'
import VideoTranslationNode from '@/components/workflow/nodes/VideoTranslationNode.vue'
import WebsiteGeneratorNode from '@/components/workflow/nodes/WebsiteGeneratorNode.vue'
import EnvironmentProvisionNode from '@/components/workflow/nodes/EnvironmentProvisionNode.vue'
import SiteQaNode from '@/components/workflow/nodes/SiteQaNode.vue'
import SitePreviewNode from '@/components/workflow/nodes/SitePreviewNode.vue'
import ProjectAgentNode from '@/components/workflow/nodes/ProjectAgentNode.vue'
import RerankerNode from '@/components/workflow/nodes/RerankerNode.vue'
import YoloTrainingNode from '@/components/workflow/nodes/YoloTrainingNode.vue'
import ProjectProfilerNode from '@/components/workflow/nodes/ProjectProfilerNode.vue'

const router = useRouter()
const appStore = useAppStore()

const darkThemes = ['dark', 'pure-bw', 'high-contrast']
const currentTabLogo = computed(() =>
  darkThemes.includes(appStore.theme) ? logoWhite : logoBlack
)

const showWorkflowDetail = ref(false)
const selectedWorkflow = ref(null)
const selectedModel = ref('')
const selectedModelProvider = ref('')
const showAllModels = ref(false)
// Streaming state
const isStreaming = ref(false)
const streamProgress = ref(0)
const streamStage = ref('')
const streamMode = ref('idle') // idle | thinking | generating
const inputMode = ref('thinking') // thinking | generate — 用户手动选择
const streamThinking = ref('') // 深度思考内容（实时累积）
const tokenCount = ref(0)
const estimatedTimeRemaining = ref('')
const streamStartedAt = ref(0)

const streamSteps = computed(() => (
  streamMode.value === 'generating'
    ? ['分析需求', '设计结构', '生成节点', '连接边', '优化流程']
    : ['理解需求', '深度思考', '整理回复']
))

const streamStageLabel = computed(() => {
  if (streamMode.value === 'thinking') return '深度思考'
  if (streamMode.value === 'generating') return '工作流生成'
  return streamStage.value || '正在处理...'
})

const currentStreamStepIndex = computed(() => {
  const steps = streamSteps.value
  if (!steps.length) return 0
  const pct = Math.max(0, Math.min(1, streamProgress.value / 100))
  return Math.min(steps.length - 1, Math.floor(pct * steps.length))
})

// Workflow preview
const showMiniPreview = ref(true)

// Node configuration preview
const showNodeConfig = ref(false)
const selectedNode = ref(null)
const editingNodeConfig = ref({})

// Workflow validation display
const workflowValidation = ref({
  errors: [],
  warnings: [],
  estimated_cost: null,
  node_count: 0,
  edge_count: 0
})

// Email config guidance state
const emailGuidance = ref(null)

// General node config guidance state (for non-email nodes)
const nodeGuidance = ref(null)

// Context-aware suggestions state
const hasGenerationFailed = ref(false)

const modelOptions = ref({})
const modelsLoading = ref(false)
const availableModels = ref([])

const showHistorySidebar = ref(false)

const historySidebarStyle = computed(() => ({
  transform: showHistorySidebar.value ? 'translateX(0)' : 'translateX(-100%)',
  pointerEvents: showHistorySidebar.value ? 'auto' : 'none',
}))
const historySessions = ref([])
const historyLoading = ref(false)
const historySearchQuery = ref('')
const historyStatusFilter = ref('')
const historyTotal = ref(0)

const batchMode = ref(false)
const selectedSessions = ref([])

const STORAGE_KEY = 'flowly_nl_tabs'

// ============================================
// 标签页管理
// ============================================
const tabs = ref([])
const activeTabId = ref(null)

function generateTabId() {
  return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function saveTabsToStorage() {
  try {
    const tabData = tabs.value.map(t => ({
      id: t.id,
      title: t.title,
      sessionId: t.sessionId,
      hasWorkflow: t.hasWorkflow,
      messages: t.messages.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        workflow: m.workflow,
        suggestions: m.suggestions,
        emailGuidance: m.emailGuidance,
        nodeGuidance: m.nodeGuidance,
        intent: m.intent
      }))
    }))
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tabData))
    localStorage.setItem(STORAGE_KEY + '_active', activeTabId.value || '')
  } catch (e) {
    // Silently ignore storage errors
  }
}

function loadTabsFromStorage() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    const savedActiveId = localStorage.getItem(STORAGE_KEY + '_active')
    if (data) {
      const tabData = JSON.parse(data)
      tabs.value = tabData.map(t => ({
        ...t,
        isLoading: false,
        isDirty: false
      }))
      if (savedActiveId && tabs.value.find(t => t.id === savedActiveId)) {
        activeTabId.value = savedActiveId
      } else if (tabs.value.length > 0) {
        activeTabId.value = tabs.value[tabs.value.length - 1].id
      }
      // Restore guidance for the active tab
      restoreActiveTabGuidance()
    }
  } catch (e) {
    // Silently ignore storage errors
  }
}

function restoreActiveTabGuidance() {
  const activeTab = tabs.value.find(t => t.id === activeTabId.value)
  if (!activeTab) return
  const lastAssistant = [...(activeTab.messages || [])].reverse().find(m => m.role === 'assistant')
  if (lastAssistant) {
    if (lastAssistant.nodeGuidance) {
      nodeGuidance.value = lastAssistant.nodeGuidance
    } else if (lastAssistant.workflow?._node_guidance) {
      nodeGuidance.value = lastAssistant.workflow._node_guidance
    } else {
      nodeGuidance.value = null
    }
    if (lastAssistant.emailGuidance) {
      emailGuidance.value = lastAssistant.emailGuidance
    } else if (lastAssistant.workflow?._email_guidance) {
      emailGuidance.value = lastAssistant.workflow._email_guidance
    } else {
      emailGuidance.value = null
    }
  } else {
    nodeGuidance.value = null
    emailGuidance.value = null
  }
}

// 当前标签页数据
const currentTab = computed(() => {
  return tabs.value.find(t => t.id === activeTabId.value) || null
})

const currentTabMessages = computed(() => {
  return currentTab.value?.messages || []
})

const currentTabLoading = computed(() => {
  return currentTab.value?.isLoading || false
})

const sendButtonLabel = computed(() => {
  if (!currentTabLoading.value) return '发送'
  if (streamMode.value === 'generating') return '生成中...'
  if (streamMode.value === 'thinking') return '思考中...'
  return '处理中...'
})

// 当前标签对应的后端 sessionId（用于侧边栏高亮）
const activeSessionId = computed(() => {
  return currentTab.value?.sessionId || null
})

const inputPlaceholder = computed(() => (
  inputMode.value === 'generate'
    ? '描述要生成的工作流；若上方已聊清楚，可直接发送「生成工作流」或确认描述'
    : '和我聊聊您的工作流需求...\n\n例如：我想做 YOLO 目标检测，有标注数据集，训练完还要生成识别网站'
))

const inputModeHint = computed(() => (
  inputMode.value === 'generate'
    ? '将基于对话内容或当前描述生成工作流'
    : '与 AI 讨论需求，不会自动生成工作流'
))

const apiMode = computed(() => (inputMode.value === 'generate' ? 'generate' : 'chat'))

// 搜索过滤
const filteredHistorySessions = computed(() => {
  let sessions = [...historySessions.value]

  if (historySearchQuery.value) {
    const query = historySearchQuery.value.toLowerCase()
    sessions = sessions.filter(s =>
      (s.name || '').toLowerCase().includes(query) ||
      (s.description || '').toLowerCase().includes(query) ||
      (s.workflowName || s.workflow_name || '').toLowerCase().includes(query)
    )
  }

  if (historyStatusFilter.value) {
    sessions = sessions.filter(s => s.status === historyStatusFilter.value)
  }

  sessions.sort((a, b) => {
    const dateA = new Date(a.created_at || 0)
    const dateB = new Date(b.created_at || 0)
    return dateB.getTime() - dateA.getTime()
  })

  return sessions
})

// Input bound to current tab
const inputMessage = ref('')
const _isSending = ref(false)
const _isSaving = ref(false)
const chatInputRef = ref(null)
const messagesContainer = ref(null)

watch(currentTabMessages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

onMounted(async () => {
  loadTabsFromStorage()
  await loadModels()
  await loadHistory()

  if (tabs.value.length === 0) {
    createNewTab()
  }
})

onBeforeUnmount(() => {
  saveTabsToStorage()
})

function createNewTab(sessionOrData = null) {
  const tabId = generateTabId()
  const greetingMessages = [{
    role: 'assistant',
    content: '您好！我是 Flowly 的 AI 工作流助手。\n\n请先选择输入框上方的模式：\n· 深度思考 — 与我讨论需求，不会自动生成\n· 生成工作流 — 基于对话或描述生成工作流\n\n默认使用「深度思考」，聊清楚后切换到「生成工作流」再发送。',
    timestamp: new Date().toISOString(),
    suggestions: [
      '我想做一个智能客服系统',
      '需要定时发送报表邮件',
      '切换到生成工作流',
    ]
  }]

  // Support both reactive session object and raw { sid, name } data from DOM
  let sessionId = null
  let sessionName = '新对话'
  let sessionData = null

  if (sessionOrData) {
    // Vue 3 reactive proxy: try _rawValue first
    const raw = sessionOrData?._rawValue || sessionOrData
    sessionId = raw?.sessionId || raw?.session_id || raw?.id || raw?.sid || null
    sessionName = raw?.name || '新对话'
    sessionData = raw?.sessionId ? sessionOrData : null  // keep reactive only if has sessionId
  }

  const newTab = {
    id: tabId,
    title: sessionName,
    sessionId: sessionId,
    messages: greetingMessages,
    isLoading: false,
    isDirty: false,
    hasWorkflow: false
  }

  tabs.value.push(newTab)
  activeTabId.value = tabId
  inputMessage.value = ''
  saveTabsToStorage()

  if (sessionData) {
    loadSessionIntoTab(tabId, sessionData)
  } else if (sessionId) {
    // sessionId from DOM JSON but no reactive data - load directly
    loadSessionIntoTab(tabId, { sessionId: sessionId, name: sessionName })
  }

  nextTick(() => scrollToBottom())
  return tabId
}

function switchTab(tabId) {
  if (activeTabId.value === tabId) return
  activeTabId.value = tabId
  inputMessage.value = ''
  saveTabsToStorage()
  nextTick(() => {
    scrollToBottom()
    restoreActiveTabGuidance()
  })
}

function closeTab(tabId) {
  const tabIndex = tabs.value.findIndex(t => t.id === tabId)
  if (tabIndex === -1) return

  const tab = tabs.value[tabIndex]
  if (tab.isLoading) {
    appStore.error('对话生成中，无法关闭')
    return
  }

  tabs.value.splice(tabIndex, 1)

  if (tabs.value.length === 0) {
    createNewTab()
  } else if (activeTabId.value === tabId) {
    const newIndex = Math.min(tabIndex, tabs.value.length - 1)
    activeTabId.value = tabs.value[newIndex].id
  }

  saveTabsToStorage()
}

function handleNewTab() {
  createNewTab()
  emailGuidance.value = null
  nodeGuidance.value = null
  showHistorySidebar.value = false
  loadHistory()
}

function handleRenameTab(tab) {
  ElMessageBox.prompt('请输入新的标签名称', '重命名', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: tab.title || ''
  }).then(({ value }) => {
    if (value) {
      tab.title = value
      saveTabsToStorage()
    }
  }).catch(() => {})
}

function handleTabAction(command) {
  switch (command) {
    case 'close-all':
      while (tabs.value.length > 1) {
        const idx = tabs.value.findIndex(t => t.id !== activeTabId.value)
        if (idx > -1) tabs.value.splice(idx, 1)
      }
      saveTabsToStorage()
      break
    case 'close-others':
      tabs.value = tabs.value.filter(t => t.id === activeTabId.value)
      saveTabsToStorage()
      break
    case 'close-saved':
      tabs.value = tabs.value.filter(t => t.id === activeTabId.value || !t.hasWorkflow)
      if (tabs.value.length === 0) createNewTab()
      saveTabsToStorage()
      break
  }
}

async function loadSessionIntoTab(tabId, session) {
  const tab = tabs.value.find(t => t.id === tabId)
  if (!tab) return

  // Vue 3 reactive proxy: use _rawValue to access unwrapped data
  const rawSession = session?._rawValue || session
  const sessionId = rawSession?.sessionId || rawSession?.session_id || rawSession?.id

  // Guard: prevent duplicate loading
  if (tab._isLoadingSession) return
  tab._isLoadingSession = true

  // If no valid sessionId, just show welcome message
  if (!sessionId) {
    tab.messages = [{
      role: 'assistant',
      content: '您好！我是 Flowly 的 AI 工作流助手。\n\n请先选择输入框上方的模式：\n• **深度思考** — 与我讨论需求，不会自动生成\n• **生成工作流** — 基于对话或描述生成工作流',
      timestamp: new Date().toISOString(),
      suggestions: [
        '我想做一个智能客服系统',
        '需要定时发送报表邮件',
        '切换到生成工作流',
      ]
    }]
    tab.title = rawSession?.name || '新对话'
    tab.isLoading = false
    tab._isLoadingSession = false
    saveTabsToStorage()
    return
  }

  tab.isLoading = true
  tab.sessionId = sessionId

  try {
    const response = await nlWorkflowApi.getSession(sessionId)

    const loadedMessages = []

    if (session.description) {
      loadedMessages.push({
        role: 'user',
        content: session.description,
        timestamp: session.created_at
      })
    }

    if (response.messages && response.messages.length > 0) {
      response.messages.forEach(msg => {
        loadedMessages.push({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          emailGuidance: msg.emailGuidance,
          nodeGuidance: msg.nodeGuidance,
          workflow: msg.workflow,
          suggestions: msg.suggestions,
          intent: msg.intent
        })
      })
    } else if (session.description) {
      loadedMessages.push({
        role: 'assistant',
        content: '我已根据您的描述生成了工作流。请问还有什么需要调整的吗？',
        timestamp: new Date().toISOString()
      })
    } else {
      loadedMessages.push({
        role: 'assistant',
        content: '您好！我是 Flowly 的 AI 工作流助手。请描述您想要创建的工作流，我将根据您的描述自动生成。',
        timestamp: new Date().toISOString()
      })
    }

    tab.messages = loadedMessages
    tab.title = session.name || session.description?.substring(0, 20) || '未命名会话'

    const workflowData = response.workflow || response.workflowJson
    if (workflowData && Object.keys(workflowData).length > 0) {
      tab.hasWorkflow = true
      const lastAssistantMsg = tab.messages.filter(m => m.role === 'assistant').pop()
      if (lastAssistantMsg) {
        lastAssistantMsg.workflow = workflowData
        lastAssistantMsg.suggestions = [
          '添加更多节点',
          '调整工作流顺序',
          '修改某个节点的配置',
          '添加条件分支'
        ]
        // Restore guidance from embedded workflow data
        if (workflowData._node_guidance) {
          lastAssistantMsg.nodeGuidance = workflowData._node_guidance
          nodeGuidance.value = workflowData._node_guidance
        }
        if (workflowData._email_guidance) {
          lastAssistantMsg.emailGuidance = workflowData._email_guidance
          emailGuidance.value = workflowData._email_guidance
        }
      }
    }

    saveTabsToStorage()
  } catch (err) {
    tab.messages = [{
      role: 'assistant',
      content: '加载会话失败，请重试。',
      timestamp: new Date().toISOString()
    }]
    appStore.error('加载会话失败: ' + (err.message || '请重试'))
  } finally {
    tab.isLoading = false
    tab._isLoadingSession = false
  }
}

// ============================================
// 消息发送
// ============================================
function handleInputKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  event.preventDefault()
  sendMessage()
}

function stripReadyMarker(text) {
  if (!text) return ''
  return text.replace(/\[READY_TO_GENERATE\]/g, '').trim()
}

const GENERATION_STAGES = new Set(['starting', 'generating', 'parsing', 'validating', 'complete'])

function resetStreamState() {
  streamProgress.value = 0
  streamThinking.value = ''
  streamStage.value = ''
  streamMode.value = inputMode.value === 'generate' ? 'generating' : 'thinking'
  tokenCount.value = 0
  estimatedTimeRemaining.value = ''
  streamStartedAt.value = Date.now()
}

function finishStreamState() {
  streamMode.value = 'idle'
  streamThinking.value = ''
  streamStage.value = ''
}

function setStreamModeFromIntent(intent) {
  if (intent === 'chat') {
    streamMode.value = 'thinking'
    streamStage.value = '深度思考'
    return
  }
  if (['create', 'modify', 'delete'].includes(intent)) {
    streamMode.value = 'generating'
    streamStage.value = '工作流生成'
  }
}

function applyStreamProgressEvent(data, messageObj, fullContent, workflowData) {
  const stage = data.stage || ''
  const msg = data.message || ''

  if (GENERATION_STAGES.has(stage)) {
    streamMode.value = 'generating'
    streamStage.value = '工作流生成'
  } else if (stage !== 'thinking') {
    // Keep generate mode when already generating; only downgrade for explicit chat stages
    if (streamMode.value !== 'generating') {
      streamMode.value = 'thinking'
      streamStage.value = '深度思考'
    }
  }

  if (msg) {
    streamThinking.value += (streamThinking.value ? '\n' : '') + msg
  }

  bumpStreamProgress(data.progress, 6, 95)

  if (streamMode.value === 'generating' && !workflowData && !fullContent && msg) {
    messageObj.content = msg
  }
}

function bumpStreamProgress(explicitProgress, step = 4, cap = 95) {
  if (typeof explicitProgress === 'number' && !Number.isNaN(explicitProgress)) {
    streamProgress.value = Math.min(cap, Math.max(streamProgress.value, explicitProgress))
  } else {
    streamProgress.value = Math.min(cap, streamProgress.value + step)
  }
}

function applyTokenStreamEvent(data, messageObj, fullContent, mode = 'chat') {
  const isGenerate = mode === 'generate' || streamMode.value === 'generating'
  if (isGenerate) {
    streamMode.value = 'generating'
    streamStage.value = '工作流生成'
  } else {
    streamMode.value = 'thinking'
    streamStage.value = '深度思考'
  }

  const nextContent = fullContent + (data.content || '')
  messageObj.content = stripReadyMarker(nextContent)
  bumpStreamProgress(data.progress, isGenerate ? 2 : 4, isGenerate ? 95 : 92)
  return nextContent
}

function finalizeAssistantWorkflowMessage(messageObj, workflowData, fallbackMessage) {
  if (!workflowData || !Object.keys(workflowData).length) return
  messageObj.workflow = workflowData
  messageObj.content = fallbackMessage || `已生成工作流: ${workflowData.name || '未命名'}`
  messageObj.suggestions = generateContextSuggestions(workflowData)
  syncNlPreview()
}

async function sendMessage() {
  const tab = currentTab.value
  if (!tab || tab.isLoading) return

  // Read the actual textarea DOM value to handle all code paths
  const ta = chatInputRef.value?.$el?.querySelector?.('textarea')
    || chatInputRef.value?.$refs?.textarea
    || document.querySelector('textarea[data-testid="chat-input"]')
  const actualValue = ta?.value?.trim() || inputMessage.value?.trim() || ''

  if (!actualValue) return
  if (_isSending.value || tab._isCreatingSession) return

  _isSending.value = true
  const userMessage = actualValue
  inputMessage.value = ''
  if (ta) ta.value = ''

  tab.messages.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date().toISOString()
  })

  scrollToBottom()
  tab.isLoading = true
  tab.isDirty = true
  saveTabsToStorage()
  isStreaming.value = true
  resetStreamState()

  try {
    let response

    if (tab.sessionId) {
      // Use streaming for continue conversation
      const continueMessage = {
        role: 'assistant',
        content: '',
        isStreaming: true,
        timestamp: new Date().toISOString()
      }
      tab.messages.push(continueMessage)

      try {
        // Try streaming first
        response = await streamMessageWithUI(tab, userMessage, continueMessage, apiMode.value)

        const workflowData2 = response.workflow || response.workflowJson
        if (workflowData2 && Object.keys(workflowData2).length > 0) {
          finalizeAssistantWorkflowMessage(
            continueMessage,
            workflowData2,
            continueMessage.content || response.message
          )
          tab.hasWorkflow = true
          updateWorkflowValidation(workflowData2)
        } else {
          continueMessage.suggestions = generateContextSuggestions(workflowData2, {
            intent: continueMessage.intent,
            readyToGenerate: continueMessage.readyToGenerate
          })
        }
      } catch (sendErr) {
        // Fallback to non-streaming
        response = await nlWorkflowApi.sendMessage(tab.sessionId, userMessage, {
          model: selectedModel.value,
          mode: apiMode.value
        })

        continueMessage.content = response.message || '我理解了，您还有其他需要调整的地方吗？'
        continueMessage.suggestions = response.suggestions || generateContextSuggestions(response.workflow, {
          intent: response.intent,
          readyToGenerate: response.ready_to_generate
        })

        const workflowData2 = response.workflow || response.workflowJson
        if (workflowData2 && Object.keys(workflowData2).length > 0) {
          finalizeAssistantWorkflowMessage(
            continueMessage,
            workflowData2,
            response.message || continueMessage.content
          )
          tab.hasWorkflow = true
          updateWorkflowValidation(workflowData2)
        }
      } finally {
        continueMessage.isStreaming = false
      }
    } else {
      const assistantMessage = {
        role: 'assistant',
        content: '',
        isStreaming: true,
        timestamp: new Date().toISOString()
      }
      tab.messages.push(assistantMessage)

      try {
        tab._isCreatingSession = true
        
        // Try streaming workflow generation first
        response = await streamWorkflowWithUI(tab, userMessage, assistantMessage, apiMode.value)
        
        const workflowData = response.workflow || response.workflowJson
        if (workflowData && Object.keys(workflowData).length > 0) {
          finalizeAssistantWorkflowMessage(
            assistantMessage,
            workflowData,
            response.message || `已生成工作流: ${workflowData.name || '未命名'}`
          )
          tab.hasWorkflow = true
          updateWorkflowValidation(workflowData)
        } else {
          assistantMessage.content = stripReadyMarker(assistantMessage.content) || response.message || '正在处理您的请求...'
          assistantMessage.suggestions = generateContextSuggestions(null, {
            intent: response.intent,
            readyToGenerate: response.ready_to_generate
          })
        }

        hasGenerationFailed.value = false
      } catch (createErr) {
        // Fallback to non-streaming
        response = await nlWorkflowApi.createSession({
          description: userMessage,
          name: `NL Workflow ${Date.now()}`,
          model: selectedModel.value,
          mode: apiMode.value
        })

        tab.sessionId = response.sessionId || response.id
        tab.title = userMessage.substring(0, 20) + (userMessage.length > 20 ? '...' : '')

        if (response.error) {
          assistantMessage.content = `抱歉，生成工作流时遇到了问题：${response.error}`
          hasGenerationFailed.value = true
        } else {
          const workflowData = response.workflow || response.workflowJson
          if (workflowData && Object.keys(workflowData).length > 0) {
            finalizeAssistantWorkflowMessage(
              assistantMessage,
              workflowData,
              response.message || '我已根据您的描述生成了工作流'
            )
            tab.hasWorkflow = true
            updateWorkflowValidation(workflowData)
            if (response.email_guidance) {
              emailGuidance.value = response.email_guidance
              assistantMessage.emailGuidance = response.email_guidance
            }
            if (response.node_guidance) {
              nodeGuidance.value = response.node_guidance
              assistantMessage.nodeGuidance = response.node_guidance
            }
            if (workflowData?._email_guidance && !assistantMessage.emailGuidance) {
              emailGuidance.value = workflowData._email_guidance
              assistantMessage.emailGuidance = workflowData._email_guidance
            }
            if (workflowData?._node_guidance && !assistantMessage.nodeGuidance) {
              nodeGuidance.value = workflowData._node_guidance
              assistantMessage.nodeGuidance = workflowData._node_guidance
            }
          } else {
            assistantMessage.content = stripReadyMarker(response.message) || '正在处理您的请求...'
            assistantMessage.suggestions = generateContextSuggestions(null, {
              intent: response.intent,
              readyToGenerate: response.ready_to_generate
            })
          }
        }

        hasGenerationFailed.value = !!response.error
      } finally {
        assistantMessage.isStreaming = false
        tab._isCreatingSession = false
      }
    }
  } catch (err) {
    // Outer catch handles any unexpected errors — must show user feedback
    const msg = err?.message || '生成失败，请重试'
    // Determine which message object to update (assistantMessage in else branch, continueMessage in if branch)
    const lastMsg = tab.messages.length > 0 ? tab.messages[tab.messages.length - 1] : null
    if (lastMsg) {
      lastMsg.content = `生成工作流时遇到了问题：${msg}`
      lastMsg.isStreaming = false
    }
    hasGenerationFailed.value = true
    appStore.error(msg)
  } finally {
    if (tab) tab.isLoading = false
    isStreaming.value = false
    _isSending.value = false
    finishStreamState()
    saveTabsToStorage()
    scrollToBottom()
  }
}

/**
 * Stream message with real-time UI updates
 */
async function streamMessageWithUI(tab, userMessage, messageObj, mode = 'chat') {
  streamStage.value = mode === 'generate' ? '工作流生成' : '深度思考'
  streamMode.value = mode === 'generate' ? 'generating' : 'thinking'
  streamStartedAt.value = Date.now()
  streamProgress.value = 10
  
  try {
    const response = await nlWorkflowApi.streamMessage(tab.sessionId, userMessage, {
      model: selectedModel.value,
      mode
    })

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let buffer = ''
    let workflowData = null

    while (true) { // eslint-disable-line no-constant-condition
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk
      tokenCount.value += chunk.length

      // Update estimated time
      updateEstimatedTime()

      // Process complete SSE events
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))

            switch (data.type) {
              case 'thinking':
                streamMode.value = 'thinking'
                streamStage.value = '深度思考'
                streamThinking.value += data.content || ''
                streamProgress.value = Math.min(30, streamProgress.value)
                break

              case 'progress':
              case 'step':
                applyStreamProgressEvent(data, messageObj, fullContent, workflowData)
                break

              case 'token':
                fullContent = applyTokenStreamEvent(data, messageObj, fullContent, mode)
                break

              case 'intent':
                messageObj.intent = data.intent
                if (data.intent === 'generate' || data.mode === 'generate') {
                  streamMode.value = 'generating'
                  streamStage.value = '工作流生成'
                } else {
                  setStreamModeFromIntent(data.intent)
                }
                break

              case 'ready_to_generate':
                messageObj.readyToGenerate = true
                messageObj.suggestions = generateContextSuggestions(null, {
                  readyToGenerate: true,
                  intent: 'chat'
                })
                break

              case 'workflow':
                streamMode.value = 'generating'
                streamStage.value = '工作流生成'
                workflowData = data.workflow
                streamProgress.value = 90
                messageObj.content = data.message || fullContent || '工作流已更新'
                if (data.email_guidance) {
                  emailGuidance.value = data.email_guidance
                  messageObj.emailGuidance = data.email_guidance
                }
                if (data.node_guidance) {
                  nodeGuidance.value = data.node_guidance
                  messageObj.nodeGuidance = data.node_guidance
                }
                // Also check for guidance embedded in workflow data (_email_guidance, _node_guidance)
                if (workflowData?._email_guidance && !messageObj.emailGuidance) {
                  emailGuidance.value = workflowData._email_guidance
                  messageObj.emailGuidance = workflowData._email_guidance
                }
                if (workflowData?._node_guidance && !messageObj.nodeGuidance) {
                  nodeGuidance.value = workflowData._node_guidance
                  messageObj.nodeGuidance = workflowData._node_guidance
                }
                break

              case 'node_guidance':
                if (data.node_guidance) {
                  nodeGuidance.value = data.node_guidance
                  messageObj.nodeGuidance = data.node_guidance
                }
                break

              case 'done':
                if (data.workflow_json) {
                  try {
                    workflowData = JSON.parse(data.workflow_json)
                  } catch (parseErr) {
                    console.warn('Failed to parse workflow_json:', parseErr)
                  }
                }
                if (data.workflow) {
                  workflowData = data.workflow
                }
                streamProgress.value = 100
                messageObj.content = stripReadyMarker(data.message || fullContent) || '我理解了，您还有其他需要调整的地方吗？'
                messageObj.intent = data.intent || messageObj.intent
                messageObj.readyToGenerate = data.ready_to_generate || messageObj.readyToGenerate
                messageObj.suggestions = data.suggestions || generateContextSuggestions(workflowData, {
                  readyToGenerate: messageObj.readyToGenerate,
                  intent: messageObj.intent
                })
                if (data.email_guidance) {
                  emailGuidance.value = data.email_guidance
                  messageObj.emailGuidance = data.email_guidance
                }
                if (data.node_guidance) {
                  nodeGuidance.value = data.node_guidance
                  messageObj.nodeGuidance = data.node_guidance
                }
                // Also check for guidance embedded in workflow data
                if (workflowData?._email_guidance && !messageObj.emailGuidance) {
                  emailGuidance.value = workflowData._email_guidance
                  messageObj.emailGuidance = workflowData._email_guidance
                }
                if (workflowData?._node_guidance && !messageObj.nodeGuidance) {
                  nodeGuidance.value = workflowData._node_guidance
                  messageObj.nodeGuidance = workflowData._node_guidance
                }
                break

              case 'error':
                throw new Error(data.error)

              case 'suggestions':
                messageObj.suggestions = data.suggestions
                break

              case 'email_guidance':
                if (data.email_guidance) {
                  emailGuidance.value = data.email_guidance
                  messageObj.emailGuidance = data.email_guidance
                }
                break
            }
          } catch (e) {
            // eslint-disable-next-line no-undef
            const currentData = data
            if (e.message === currentData?.error) throw e
            // Skip malformed JSON
          }
        }
      }
    }

    return { workflow: workflowData, message: fullContent }

  } catch (error) {
    streamProgress.value = 0
    throw error
  }
}

/**
 * Stream workflow generation with real-time UI updates
 */
async function streamWorkflowWithUI(tab, userMessage, messageObj, mode = 'chat') {
  streamMode.value = mode === 'generate' ? 'generating' : 'thinking'
  streamStage.value = mode === 'generate' ? '工作流生成' : '深度思考'
  streamStartedAt.value = Date.now()
  streamProgress.value = 5
  
  try {
    const response = await nlWorkflowApi.streamWorkflow({
      description: userMessage,
      name: `NL Workflow ${Date.now()}`,
      model: selectedModel.value,
      mode
    })

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let buffer = ''
    let workflowData = null
    let streamIntent = 'chat'
    let readyToGenerate = false

    while (true) { // eslint-disable-line no-constant-condition
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk
      tokenCount.value += chunk.length
      updateEstimatedTime()

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))

            switch (data.type) {
              case 'thinking':
                streamMode.value = 'thinking'
                streamStage.value = '深度思考'
                streamThinking.value += data.content || ''
                streamProgress.value = Math.min(25, streamProgress.value)
                break

              case 'session':
                tab.sessionId = data.session_id || data.sessionId
                tab.title = userMessage.substring(0, 20) + (userMessage.length > 20 ? '...' : '')
                break

              case 'progress':
              case 'step':
                applyStreamProgressEvent(data, messageObj, fullContent, workflowData)
                if (data.stage === 'complete') {
                  streamProgress.value = 100
                  if (workflowData) {
                    messageObj.content = data.message || `已生成工作流: ${workflowData.name || '未命名'}`
                  }
                }
                break

              case 'token':
                fullContent = applyTokenStreamEvent(data, messageObj, fullContent, mode)
                if (workflowData) {
                  messageObj.content = stripReadyMarker(fullContent)
                }
                break

              case 'intent':
                streamIntent = data.intent || streamIntent
                messageObj.intent = streamIntent
                if (streamIntent === 'generate' || data.mode === 'generate') {
                  streamMode.value = 'generating'
                  streamStage.value = '工作流生成'
                } else {
                  setStreamModeFromIntent(streamIntent)
                }
                break

              case 'ready_to_generate':
                readyToGenerate = true
                messageObj.readyToGenerate = true
                messageObj.suggestions = generateContextSuggestions(null, {
                  readyToGenerate: true,
                  intent: 'chat'
                })
                break

              case 'workflow':
                streamMode.value = 'generating'
                streamStage.value = '工作流生成'
                workflowData = data.workflow
                streamProgress.value = 95
                if (workflowData) {
                  messageObj.workflow = workflowData
                  messageObj.content = data.message || `已生成工作流: ${workflowData.name || '未命名'}`
                  messageObj.suggestions = generateContextSuggestions(workflowData)
                  syncNlPreview()
                }
                break

              case 'suggestions':
                messageObj.suggestions = data.suggestions || generateContextSuggestions(workflowData)
                break

              case 'email_guidance':
                if (data.email_guidance) {
                  emailGuidance.value = data.email_guidance
                  messageObj.emailGuidance = data.email_guidance
                }
                break

              case 'node_guidance':
                if (data.node_guidance) {
                  nodeGuidance.value = data.node_guidance
                  messageObj.nodeGuidance = data.node_guidance
                }
                break

              case 'done':
                if (data.workflow_json) {
                  try {
                    workflowData = JSON.parse(data.workflow_json)
                  } catch (parseErr) {
                    console.warn('Failed to parse workflow_json:', parseErr)
                  }
                }
                if (data.workflow) {
                  workflowData = data.workflow
                }
                streamProgress.value = 100
                streamIntent = data.intent || streamIntent
                readyToGenerate = data.ready_to_generate || readyToGenerate
                messageObj.intent = streamIntent
                messageObj.readyToGenerate = readyToGenerate
                if (workflowData) {
                  messageObj.workflow = workflowData
                  messageObj.content = data.message || `已生成工作流: ${workflowData.name || '未命名'}`
                  messageObj.suggestions = data.suggestions || generateContextSuggestions(workflowData)
                  syncNlPreview()
                } else {
                  messageObj.content = stripReadyMarker(data.message || fullContent) || messageObj.content || '我理解了您的需求'
                  messageObj.suggestions = data.suggestions || generateContextSuggestions(null, {
                    readyToGenerate,
                    intent: streamIntent
                  })
                }
                if (data.email_guidance) {
                  emailGuidance.value = data.email_guidance
                  messageObj.emailGuidance = data.email_guidance
                }
                break

              case 'error':
                throw new Error(data.error)
            }
          } catch (e) {
            // eslint-disable-next-line no-undef
            if (e.message === data?.error) throw e
            // Skip malformed JSON (blank lines, partial data)
          }
        }
      }
    }

    if (workflowData) {
      finalizeAssistantWorkflowMessage(
        messageObj,
        workflowData,
        messageObj.content || `已生成工作流: ${workflowData.name || '未命名'}`
      )
    }

    return {
      workflow: workflowData,
      message: messageObj.content || stripReadyMarker(fullContent),
      intent: streamIntent,
      ready_to_generate: readyToGenerate
    }

  } catch (error) {
    streamProgress.value = 0
    throw error
  }
}

/**
 * Update estimated time remaining based on token count
 */
function updateEstimatedTime() {
  const tokensPerSecond = 50 // Rough estimate
  const remainingTokens = Math.max(0, 500 - tokenCount.value)
  const secondsRemaining = Math.ceil(remainingTokens / tokensPerSecond)

  // Smooth progress while waiting for first token (Ollama / cold start)
  if (isStreaming.value && streamProgress.value < 85 && streamStartedAt.value) {
    const elapsedSec = (Date.now() - streamStartedAt.value) / 1000
    const timeProgress = Math.min(84, 12 + elapsedSec * 3)
    streamProgress.value = Math.max(streamProgress.value, timeProgress)
  }
  
  if (secondsRemaining < 60) {
    estimatedTimeRemaining.value = `约 ${secondsRemaining} 秒`
  } else {
    estimatedTimeRemaining.value = `约 ${Math.ceil(secondsRemaining / 60)} 分钟`
  }
}

/**
 * Generate context-aware suggestions based on workflow state
 */
function generateContextSuggestions(workflow, options = {}) {
  const { readyToGenerate = false, intent = '' } = options
  const suggestions = []
  const nodeCount = workflow?.nodes?.length || 0
  const hasWorkflow = !!workflow?.nodes?.length

  const currentTab = tabs.value.find(t => t.id === activeTabId.value)

  if (!hasWorkflow) {
    if (readyToGenerate || intent === 'chat') {
      suggestions.push('切换到生成工作流', '我还需要补充一些细节')
    } else {
      suggestions.push(
        '我想做一个 YOLO 目标检测项目，训练完还要建站',
        '我想做一个客服机器人',
        '需要定时发送报表邮件',
        '帮我设计一个内容审核流程'
      )
    }
    return suggestions.slice(0, 5)
  }

  // Base suggestions when workflow exists
  if (hasWorkflow) {
    suggestions.push('添加更多节点')
    suggestions.push('调整工作流顺序')
    suggestions.push('修改某个节点的配置')
    suggestions.push('添加条件分支')
  }
  
  // Add "Undo last change" if workflow was modified
  if (currentTab?.isDirty && hasWorkflow) {
    suggestions.push('撤销上次更改')
  }
  
  // Add "Try different model" when generation failed
  if (hasGenerationFailed.value) {
    suggestions.push('尝试使用其他模型')
  }
  
  // Add "Simplify workflow" when too many nodes
  if (nodeCount > 15) {
    suggestions.push('简化工作流')
  }
  
  // Add "Optimize cost" if estimated cost is high
  if (workflowValidation.value?.estimated_cost && workflowValidation.value?.estimated_cost > 0.1) {
    suggestions.push('优化成本')
  }

  // Add email-specific suggestions
  const nodes = workflow?.nodes || []
  const hasEmailNode = nodes.some(n => n.type === 'email')
  if (hasEmailNode) {
    suggestions.push('配置 SMTP 服务器')
    suggestions.push('设置收件人')
    suggestions.push('添加 HTML 模板')
  }

  return suggestions.slice(0, 5) // Limit to 5 suggestions
}

/**
 * Update workflow validation display
 */
function updateWorkflowValidation(workflow) {
  if (!workflow) {
    workflowValidation.value = {
      errors: [],
      warnings: [],
      estimated_cost: null,
      node_count: 0,
      edge_count: 0
    }
    return
  }
  
  const errors = []
  const warnings = []
  let estimatedCost = 0
  
  // Check for nodes
  const nodes = workflow.nodes || []
  const edges = workflow.edges || []
  
  // Validate node connections
  const nodeIds = new Set(nodes.map(n => n.id))
  edges.forEach(edge => {
    if (!nodeIds.has(edge.source)) {
      errors.push(`节点 ${edge.source} 不存在`)
    }
    if (!nodeIds.has(edge.target)) {
      errors.push(`节点 ${edge.target} 不存在`)
    }
  })
  
  // Check for start/end nodes
  const hasStart = nodes.some(n => n.type === 'start' || n.type === 'input')
  const hasEnd = nodes.some(n => n.type === 'end' || n.type === 'output')
  
  if (!hasStart) {
    warnings.push('缺少开始节点')
  }
  if (!hasEnd) {
    warnings.push('缺少结束节点')
  }
  
  // Estimate cost based on node count and types
  nodes.forEach(node => {
    if (node.type === 'llm') {
      estimatedCost += 0.001 // Rough estimate per LLM call
    }
  })
  
  workflowValidation.value = {
    errors,
    warnings,
    estimated_cost: estimatedCost,
    node_count: nodes.length,
    edge_count: edges.length
  }
}

/**
 * Scroll to bottom of messages container
 */
function scrollToBottom(forceTop = false) {
  nextTick(() => {
    if (messagesContainer.value) {
      if (forceTop) {
        messagesContainer.value.scrollTop = 0
      }
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const GENERATE_MODE_KEYWORDS = ['生成工作流', '开始生成', '现在就生成', '切换到生成工作流']

function continueConversation(suggestion) {
  if (GENERATE_MODE_KEYWORDS.some(kw => suggestion.includes(kw))) {
    inputMode.value = 'generate'
    inputMessage.value = suggestion.includes('切换') ? '请根据上方对话生成工作流' : suggestion
  } else {
    inputMode.value = 'thinking'
    inputMessage.value = suggestion
  }
  nextTick(() => {
    const ta = chatInputRef.value?.$el?.querySelector?.('textarea')
      || chatInputRef.value?.$refs?.textarea
      || document.querySelector('textarea[data-testid="chat-input"]')
    if (ta) ta.value = inputMessage.value
    sendMessage()
  })
}

function applyExample(example) {
  const isGenerateExample = /创建|生成|读取CSV|数据处理工作流/.test(example)
  inputMode.value = isGenerateExample ? 'generate' : 'thinking'
  inputMessage.value = example
  nextTick(() => {
    const ta = chatInputRef.value?.$el?.querySelector?.('textarea')
      || chatInputRef.value?.$refs?.textarea
      || document.querySelector('textarea[data-testid="chat-input"]')
    if (ta) ta.value = example
    sendMessage()
  })
}

function viewWorkflow(workflow) {
  selectedWorkflow.value = workflow || null
  showWorkflowDetail.value = true
}

async function saveWorkflowDirect(workflow) {
  const payload = nlWorkflowToSavePayload(workflow)
  if (!payload) {
    throw new Error('empty workflow')
  }
  const response = await createWorkflow(payload)
  return response?.id || response?.data?.id
}

async function saveWorkflow(_workflow) { // eslint-disable-line no-unused-vars
  if (_isSaving.value) return

  _isSaving.value = true

  // If _workflow is provided (from message button), use it directly
  const activeTab = currentTab.value
  let targetWorkflow = _workflow || null
  let targetTab = activeTab

  // If no workflow passed in, search all tabs for one
  if (!targetWorkflow) {
    targetWorkflow = getCurrentWorkflow()
  }

  // Find the tab that owns the targetWorkflow
  if (targetWorkflow && targetTab) {
    const foundInCurrentTab = (targetTab.messages || []).some(m => m.workflow === targetWorkflow)
    if (!foundInCurrentTab) {
      // Search other tabs for the workflow
      for (const tab of tabs.value) {
        if (tab.sessionId && (tab.messages || []).some(m => m.workflow === targetWorkflow)) {
          targetTab = tab
          break
        }
      }
    }
  } else if (!targetWorkflow || !targetTab?.sessionId) {
    // Fallback: find any tab with sessionId and workflow
    for (const tab of tabs.value) {
      if (tab.sessionId) {
        for (let i = (tab.messages || []).length - 1; i >= 0; i--) {
          if (tab.messages[i].workflow) {
            targetTab = tab
            targetWorkflow = tab.messages[i].workflow
            break
          }
        }
        if (targetWorkflow) break
      }
    }
  }

  if (!targetWorkflow) {
    appStore.error('当前没有可保存的工作流')
    _isSaving.value = false
    return
  }

  const finishSave = async (workflowId) => {
    appStore.success('工作流已保存')
    showWorkflowDetail.value = false
    if (targetTab) {
      targetTab.isDirty = false
      targetTab.workflowId = workflowId
    }
    saveTabsToStorage()
    await router.push({ name: 'WorkflowEdit', params: { id: workflowId }, query: { fromNlSaved: '1' } })
  }

  try {
    if (targetTab?.sessionId) {
      try {
        const response = await nlWorkflowApi.confirmWorkflow(targetTab.sessionId)
        const workflowId = response.workflow_id || response.id || response.data?.workflow_id || response.workflowId
        if (workflowId) {
          await finishSave(workflowId)
          return
        }
      } catch (confirmErr) {
        // Session may be stale after backend restart — fall through to direct save
        console.warn('[NL Creator] confirmWorkflow failed, trying direct save', confirmErr)
      }
    }

    const workflowId = await saveWorkflowDirect(targetWorkflow)
    if (workflowId) {
      await finishSave(workflowId)
    } else {
      appStore.error('保存失败：未获取到工作流 ID')
    }
  } catch (err) {
    appStore.error('保存失败')
  } finally {
    _isSaving.value = false
  }
}

// ============================================
// 模型加载
// ============================================
async function loadModels(force = false) {
  if (!force && availableModels.value.length > 0 && !showAllModels.value) return
  modelsLoading.value = true
  try {
    const response = await nlWorkflowApi.getModels(showAllModels.value)
    availableModels.value = response.models || []
    const defaultModel = response.default ?? response.defaultModel
    if (defaultModel) {
      selectedModel.value = defaultModel
    } else if (availableModels.value.length > 0) {
      const first = availableModels.value[0]
      selectedModel.value = first.modelId ?? first.model_id ?? ''
    }

    const grouped = {}
    availableModels.value.forEach(m => {
      const provider = m.provider || 'Unknown'
      if (!grouped[provider]) grouped[provider] = []
      grouped[provider].push(m)
    })
    modelOptions.value = grouped

    const current = availableModels.value.find(m => m.modelId === selectedModel.value)
    selectedModelProvider.value = current?.provider || ''
  } catch (err) {
    appStore.error('加载模型列表失败')
  } finally {
    modelsLoading.value = false
  }
}

// ============================================
// 工具函数
// ============================================
function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDate(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffHours < 24) return `${diffHours} 小时前`
  if (diffDays < 7) return `${diffDays} 天前`

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const response = await nlWorkflowApi.getSessions()
    // toCamelCaseKeys already ran in Axios interceptor (session_id -> sessionId)
    const raw = response.data || response || []
    // Normalize: only set sessionId if it doesn't already exist after camelCase conversion
    const normalized = raw.map(s => {
      const obj = { ...s }
      if (!obj.sessionId) {
        obj.sessionId = s.sessionId || s.session_id || s.id || null
      }
      return obj
    })
    const seen = new Set()
    historySessions.value = normalized.filter(s => {
      if (!s.sessionId) return true
      if (seen.has(s.sessionId)) return false
      seen.add(s.sessionId)
      return true
    })
    historyTotal.value = historySessions.value.length
  } catch (err) {
    appStore.error('加载历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

function handleHistorySearch() {
  // Search is reactive via computed
}

function getStatusType(status) {
  const types = {
    'generating': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'pending': 'info'
  }
  return types[status] || 'info'
}

function getStatusText(status) {
  const texts = {
    'generating': '生成中',
    'completed': '已完成',
    'failed': '失败',
    'pending': '等待中'
  }
  return texts[status] || status
}

// ============================================
// Intent Analysis Display
// ============================================
function getIntentTagType(intentType) {
  const types = {
    'create': 'success',
    'modify': 'warning',
    'delete': 'danger',
    'chat': 'info'
  }
  return types[intentType] || 'info'
}

function getIntentText(intentType) {
  const texts = {
    'create': '创建新工作流',
    'modify': '修改现有工作流',
    'delete': '删除节点',
    'chat': '普通对话'
  }
  return texts[intentType] || intentType
}

// ============================================
// Workflow Preview Helpers
// ============================================
function getCurrentWorkflow() {
  const tab = currentTab.value
  if (!tab) return null
  
  // Find the latest message with workflow
  const messages = tab.messages || []
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].workflow) {
      return messages[i].workflow
    }
  }
  return null
}

// ============================================
// VueFlow 数据转换（NL → VueFlow 格式）
// ============================================
const nlNodeTypes = {
  start: StartNode,
  end: EndNode,
  llm: LLMNode,
  input: InputNode,
  output: OutputNode,
  condition: ConditionNode,
  delay: DelayNode,
  http: HttpNode,
  code: CodeNode,
  variable: VariableNode,
  prompt: PromptNode,
  email: EmailNode,
  memory: MemoryNode,
  tool: ToolNode,
  retriever: RetrieverNode,
  vector_store: VectorStoreNode,
  embedding: EmbeddingNode,
  subworkflow: SubworkflowNode,
  executor: ExecutorNode,
  planner: PlannerNode,
  agent: AgentNode,
  loop: LoopNode,
  switch: SwitchNode,
  file_reader: FileReaderNode,
  file_writer: FileWriterNode,
  transform: TransformNode,
  json_transform: JsonTransformNode,
  csv_transform: CsvTransformNode,
  document_loader: DocumentLoaderNode,
  web_scraper: WebScraperNode,
  dataset_upload: DatasetUploadNode,
  data_annotation: DataAnnotationNode,
  data_augmentation: DataAugmentationNode,
  model_training: ModelTrainingNode,
  yolo_training: YoloTrainingNode,
  project_profiler: ProjectProfilerNode,
  model_evaluation: ModelEvaluationNode,
  model_deployment: ModelDeploymentNode,
  image_generation: ImageGenerationNode,
  image_editing: ImageEditingNode,
  video_generation: VideoGenerationNode,
  audio_generation: AudioGenerationNode,
  subtitle_generation: SubtitleGenerationNode,
  video_upload: VideoUploadNode,
  subtitle_translate: SubtitleTranslateNode,
  segment_dubbing: SegmentDubbingNode,
  lip_sync: LipSyncNode,
  subtitle_burn: SubtitleBurnNode,
  video_translation: VideoTranslationNode,
  website_generator: WebsiteGeneratorNode,
  environment_provision: EnvironmentProvisionNode,
  site_qa: SiteQaNode,
  site_preview: SitePreviewNode,
  project_agent: ProjectAgentNode,
  reranker: RerankerNode
}

// nlNodes/nlEdges must be refs (not computed) because VueFlow v-model:nodes/edges writes to them
const nlNodes = ref([])
const nlEdges = ref([])

function syncNlPreview() {
  const workflow = getCurrentWorkflow()
  if (!workflow?.nodes?.length) {
    nlNodes.value = []
    nlEdges.value = []
    return
  }

  const converted = nlWorkflowToVueFlow(workflow, {
    preserveNodes: nlNodes.value
  })
  nlNodes.value = converted.nodes
  nlEdges.value = converted.edges.map((edge) => ({
    ...edge,
    style: { stroke: '#06b6d4', strokeWidth: 2 }
  }))
}

watch(
  [() => currentTab.value?.id, () => currentTab.value?.messages],
  () => {
    syncNlPreview()
  },
  { immediate: true, deep: true }
)

function handleNlNodeClick(event) {
  selectedNode.value = event.node
  showNodeConfig.value = true
  editingNodeConfig.value = { ...event.node.data }
}

function handleSessionAction(command, session) {
  const sessionId = session.sessionId || session.session_id

  if (!sessionId) return

  if (command === 'open-tab') {
    const existingTab = tabs.value.find(t => t.sessionId === sessionId)
    if (existingTab) {
      switchTab(existingTab.id)
    } else {
      createNewTab(session)
    }
    showHistorySidebar.value = false
  } else if (command === 'rename') {
    renameSession(session)
  } else if (command === 'delete') {
    deleteSession(session)
  }
}

async function renameSession(session) {
  const sessionId = session.sessionId || session.session_id
  if (!sessionId) return

  try {
    const { value: newName } = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: session.name || session.description || ''
    })

    if (newName) {
      let apiSuccess = false
      try {
        await nlWorkflowApi.updateSession(sessionId, { name: newName })
        apiSuccess = true
      } catch (err) {
        appStore.error('重命名失败，请重试')
      }

      if (apiSuccess) {
        const idx = historySessions.value.findIndex(s => (s.sessionId || s.session_id) === sessionId)
        if (idx !== -1) {
          historySessions.value[idx].name = newName
        }

        const tab = tabs.value.find(t => t.sessionId === sessionId)
        if (tab) {
          tab.title = newName
          saveTabsToStorage()
        }

        await loadHistory()
        appStore.success('会话已重命名')
      }
    }
  } catch (err) {
    // ElMessageBox cancelled or dismissed — no action needed
  }
}

function handleSessionItemClick(event) {
  // Handle click from DOM - extract sessionId from data-sid attribute
  if (batchMode.value) return

  const target = event.currentTarget || event.target
  const sessionId = target.dataset?.sid

  if (!sessionId) return

  const session = historySessions.value.find(s => (s.sessionId || s.session_id || s.id) === sessionId)
  if (!session) return

  // If this session is already open in a tab, switch to it
  const existingTab = tabs.value.find(t => t.sessionId === sessionId)
  if (existingTab) {
    switchTab(existingTab.id)
    showHistorySidebar.value = false
    return
  }

  // Otherwise create a new tab and load the session
  createNewTab(session)
  showHistorySidebar.value = false
}

async function deleteSession(session) {
  const sessionId = session.sessionId || session.session_id
  if (!sessionId) return

  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '删除对话', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await nlWorkflowApi.deleteSession(sessionId)
    historySessions.value = historySessions.value.filter(s => (s.sessionId || s.session_id) !== sessionId)
    historyTotal.value = historySessions.value.length

    // Close any tab with this session
    const tabIndex = tabs.value.findIndex(t => t.sessionId === sessionId)
    if (tabIndex > -1) {
      closeTab(tabs.value[tabIndex].id)
    } else if (tabs.value.length === 0) {
      createNewTab()
    }

    await loadHistory()
    appStore.success('会话已删除')
  } catch (err) {
    if (err !== 'cancel') {
      appStore.error('删除失败')
    }
  }
}

function toggleSessionSelection(session) {
  const sessionId = session.sessionId || session.session_id
  const idx = selectedSessions.value.indexOf(sessionId)
  if (idx > -1) {
    selectedSessions.value.splice(idx, 1)
  } else {
    selectedSessions.value.push(sessionId)
  }
}

function handleSelectAll() {
  if (selectedSessions.value.length === filteredHistorySessions.value.length) {
    selectedSessions.value = []
  } else {
    selectedSessions.value = filteredHistorySessions.value.map(s => s.sessionId || s.session_id)
  }
}

function handleCancelBatch() {
  batchMode.value = false
  selectedSessions.value = []
}

async function handleBatchDelete() {
  if (selectedSessions.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSessions.value.length} 个对话吗？此操作不可恢复。`,
      '批量删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const deletePromises = selectedSessions.value.map(sessionId =>
      nlWorkflowApi.deleteSession(sessionId).catch(() => {})
    )
    await Promise.all(deletePromises)

    historySessions.value = historySessions.value.filter(
      s => !selectedSessions.value.includes(s.sessionId || s.session_id)
    )
    historyTotal.value = historySessions.value.length

    // Close tabs with deleted sessions
    const tabsToRemove = tabs.value.filter(t =>
      t.sessionId && selectedSessions.value.includes(t.sessionId)
    )
    tabsToRemove.forEach(t => {
      const idx = tabs.value.findIndex(tab => tab.id === t.id)
      if (idx > -1) tabs.value.splice(idx, 1)
    })

    if (tabs.value.length === 0) createNewTab()

    await loadHistory()
    appStore.success(`已删除 ${selectedSessions.value.length} 个对话`)
  } catch (err) {
    if (err !== 'cancel') {
      appStore.error('批量删除失败')
    }
  } finally {
    handleCancelBatch()
    saveTabsToStorage()
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@import '@/styles/workflow-domain-node.scss';

.nl-creator {
  display: flex;
  min-height: calc(100vh - #{$header-height} - #{$spacing-12});
  padding: 0;
  position: relative;
}

// ============================================
// 历史记录侧边栏
// ============================================
.history-sidebar {
  position: fixed;
  left: 0;
  top: var(--header-height, #{$header-height});
  width: 320px;
  max-width: min(320px, 100vw);
  height: calc(100vh - var(--header-height, #{$header-height}));
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  z-index: $z-modal;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: $shadow-xl;
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  top: var(--header-height, #{$header-height});
  background-color: rgba(0, 0, 0, 0.45);
  z-index: $z-modal-backdrop;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);

  .title-icon {
    width: 18px;
    height: 18px;
    color: var(--color-primary);
  }
}

.sidebar-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: $radius-md;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
    color: var(--text-primary);
  }

  .close-icon {
    width: 18px;
    height: 18px;
  }
}

.new-chat-btn-wrapper {
  padding: $spacing-3 $spacing-4;
  flex-shrink: 0;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-2;
  width: 100%;
  padding: $spacing-3 $spacing-4;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  color: white;
  border: none;
  border-radius: $radius-lg;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--color-primary-shadow, rgba(6, 182, 212, 0.4));
  }

  .btn-icon {
    width: 16px;
    height: 16px;
  }
}

.sidebar-search {
  padding: 0 $spacing-4 $spacing-3;
  flex-shrink: 0;

  :deep(.el-input__wrapper) {
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-lg;
    box-shadow: none;

    &:focus-within {
      border-color: var(--color-primary);
    }
  }

  .search-icon {
    width: 14px;
    height: 14px;
    color: var(--text-tertiary);
  }
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.batch-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-3 $spacing-4;
  background-color: var(--color-primary-pale);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.batch-info {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-sm;
  color: var(--color-primary);
  font-weight: $font-weight-medium;

  .batch-icon {
    width: 16px;
    height: 16px;
  }
}

.batch-buttons {
  display: flex;
  gap: $spacing-2;
}

.batch-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: $spacing-1 $spacing-2;
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  background-color: var(--bg-secondary);
  font-size: $font-size-xs;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover:not(:disabled) {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.danger {
    color: var(--color-error);
    border-color: var(--color-error-light);

    &:hover:not(:disabled) {
      background-color: var(--color-error-light);
    }
  }

  .batch-btn-icon {
    width: 14px;
    height: 14px;
  }
}

.filter-tags {
  display: flex;
  gap: $spacing-2;
  padding: 0 $spacing-4 $spacing-3;
  flex-shrink: 0;
}

.filter-tag {
  padding: $spacing-1 $spacing-3;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-full;
  font-size: $font-size-xs;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &.active {
    background-color: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-2 $spacing-3;
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: $spacing-2;
  padding: $spacing-3;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-fast;
  margin-bottom: $spacing-1;

  &:hover {
    background-color: var(--bg-hover);

    .session-actions {
      opacity: 1;
    }
  }

  &.is-active {
    background-color: var(--color-primary-pale);

    &:hover {
      background-color: var(--color-primary-pale);
    }
  }

  &.is-selected {
    background-color: var(--color-primary-light);

    &:hover {
      background-color: var(--color-primary-light);
    }
  }
}

.session-checkbox {
  flex-shrink: 0;
  padding-top: 2px;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-1;
}

.session-name {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.status-tag {
  font-size: 10px;
  padding: 0 4px;
  height: 18px;
  line-height: 16px;
}

.workflow-tag {
  display: inline-flex;
  align-items: center;
  padding: 0 4px;
  height: 18px;
  font-size: 10px;

  .tag-icon {
    width: 10px;
    height: 10px;
  }
}

.session-desc {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: $spacing-1;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  .meta-icon {
    width: 12px;
    height: 12px;
  }

  .meta-divider {
    margin: 0 2px;
  }
}

.session-actions {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity $transition-fast;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: $radius-md;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all $transition-fast;

  &:hover {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .action-icon {
    width: 16px;
    height: 16px;
  }
}

.dropdown-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-2;

  &.danger {
    color: var(--color-error);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-10;
  text-align: center;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--text-tertiary);
    opacity: 0.5;
    margin-bottom: $spacing-3;
  }

  .empty-title {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    margin-bottom: $spacing-1;
  }

  .empty-hint {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.sidebar-footer {
  display: flex;
  gap: $spacing-2;
  padding: $spacing-3 $spacing-4;
  border-top: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.footer-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-2;
  padding: $spacing-2;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  font-size: $font-size-xs;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover:not(:disabled) {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.danger:hover:not(:disabled) {
    border-color: var(--color-error);
    color: var(--color-error);
    background-color: var(--color-error-light);
  }

  .footer-icon {
    width: 14px;
    height: 14px;
  }
}

// ============================================
// 主内容区
// ============================================
.creator-main {
  flex: 1;
  max-width: 1100px;
  margin: 0 auto;
  padding: $spacing-6;
  transition: all 0.3s ease;

  @media (max-width: 768px) {
    padding: $spacing-4;
  }
}

.creator-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-3;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  font-size: $font-size-sm;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover:not(:disabled) {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .toolbar-icon {
    width: 16px;
    height: 16px;
  }

  .toolbar-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    background-color: var(--color-primary);
    color: white;
    border-radius: $radius-full;
    font-size: 10px;
    font-weight: $font-weight-medium;
  }

  &.new-tab-btn {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
    color: white;
    border-color: transparent;

    &:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px var(--color-primary-shadow, rgba(6, 182, 212, 0.3));
    }
  }
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

// ============================================
// 浏览器风格标签页
// ============================================
.tab-bar {
  display: flex;
  align-items: center;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  margin-bottom: $spacing-3;
  overflow: hidden;
  height: 44px;
}

.tab-scroll-container {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.tab-list {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 $spacing-1;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  height: 36px;
  padding: 0 $spacing-3;
  border-radius: $radius-md;
  cursor: pointer;
  transition: all $transition-fast;
  min-width: 120px;
  max-width: 200px;
  flex-shrink: 0;
  margin: 0 2px;
  position: relative;
  background-color: var(--bg-tertiary);
  border: 1px solid transparent;

  &:hover {
    background-color: var(--bg-hover);

    .tab-close {
      opacity: 1;
    }
  }

  &.is-active {
    background-color: var(--bg-primary);
    border-color: var(--border-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

    &::before {
      content: '';
      position: absolute;
      top: -1px;
      left: 50%;
      transform: translateX(-50%);
      width: 40%;
      height: 2px;
      background-color: var(--color-primary);
      border-radius: 0 0 2px 2px;
    }
  }

  &.is-loading {
    .tab-icon {
      display: none;
    }
  }
}

.tab-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  border-radius: 4px;
}

.tab-loading {
  display: flex;
  gap: 2px;
  align-items: center;
  flex-shrink: 0;

  span {
    width: 5px;
    height: 5px;
    background-color: var(--color-primary);
    border-radius: 50%;
    animation: tab-typing 1.4s infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes tab-typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-3px); opacity: 1; }
}

.tab-title {
  flex: 1;
  font-size: $font-size-xs;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  .is-active & {
    color: var(--text-primary);
    font-weight: $font-weight-medium;
  }
}

.tab-workflow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--color-success);
  flex-shrink: 0;
}

.tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: $radius-sm;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  opacity: 0;
  transition: all $transition-fast;
  flex-shrink: 0;

  &:hover {
    background-color: var(--bg-tertiary);
    color: var(--color-error);
  }

  .tab-close-icon {
    width: 12px;
    height: 12px;
  }
}

.tab-actions {
  display: flex;
  align-items: center;
  padding: 0 $spacing-2;
  border-left: 1px solid var(--border-primary);
  flex-shrink: 0;
  height: 100%;
}

.tab-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: $radius-md;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
    color: var(--text-primary);
  }

  .tab-action-icon {
    width: 16px;
    height: 16px;
  }
}

// ============================================
// 模型选择器
// ============================================
.model-selector-bar {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-4 $spacing-6;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  margin-bottom: $spacing-4;
}

.model-selector {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.model-label {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-secondary);
  white-space: nowrap;
}

.model-select {
  min-width: 280px;
}

.model-option-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: $spacing-2;
}

.model-selected-badge {
  font-size: $font-size-xs;
  color: var(--color-primary);
  font-weight: $font-weight-medium;
}

.model-info {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-left: auto;

  .model-name {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    font-family: monospace;
  }

  &.model-unavailable {
    color: var(--color-warning, #e6a23c);

    svg {
      width: 16px;
      height: 16px;
    }

    span {
      font-size: $font-size-sm;
    }
  }
}

// ============================================
// 聊天容器
// ============================================
.chat-container {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-2xl;
  overflow: hidden;
}

.chat-messages {
  min-height: 400px;
  max-height: 500px;
  overflow-y: auto;
  padding: $spacing-6;
}

.message {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-6;

  &-user {
    flex-direction: row-reverse;

    .message-text {
      background: linear-gradient(135deg, var(--color-primary) 0%, $color-secondary 100%);
      color: white;
    }
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: $radius-full;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  // Avatar images / svgs are handled by NlAvatar component itself

  .message-assistant & {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
    box-shadow: 0 2px 8px var(--color-primary-shadow, rgba(6, 182, 212, 0.3));
    padding: 2px;
  }

  .message-user & {
    background-color: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .message-system & {
    background-color: var(--color-primary-10);
    color: var(--color-primary);
  }
}

.message-content {
  max-width: 80%;
}

.message-text {
  padding: $spacing-4;
  border-radius: $radius-xl;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  white-space: pre-wrap;

  .message-assistant & {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
    border-radius: $radius-xl $radius-xl $radius-xl 0;
  }

  .message-user & {
    border-radius: $radius-xl $radius-xl 0 $radius-xl;
  }

  .cursor {
    animation: blink 1s infinite;
    color: var(--color-primary);
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-time {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-top: $spacing-1;
  padding: 0 $spacing-2;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: $spacing-4;

  span {
    width: 8px;
    height: 8px;
    background-color: var(--text-tertiary);
    border-radius: $radius-full;
    animation: typing 1.4s infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

.workflow-preview {
  margin-top: $spacing-4;
  padding: $spacing-4;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-3;

  .preview-icon {
    width: 18px;
    height: 18px;
    color: var(--color-primary);
  }

  .preview-name {
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
    flex: 1;
  }
}

.preview-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin-bottom: $spacing-3;
}

.preview-nodes {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  margin-bottom: $spacing-4;
}

.node-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-1 $spacing-2;
  background-color: var(--color-primary-10);
  border-radius: $radius-md;
  font-size: $font-size-xs;

  .node-name {
    color: var(--text-primary);
  }
}

.more-nodes {
  padding: $spacing-1 $spacing-2;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.preview-actions {
  display: flex;
  gap: $spacing-2;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-icon-sm {
  width: 14px;
  height: 14px;
}

.suggestions {
  margin-top: $spacing-3;
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  align-items: center;
}

.suggestions-label {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.suggestion-btn {
  padding: $spacing-1 $spacing-3;
  background-color: var(--color-primary-10);
  border: 1px solid var(--color-primary-30);
  border-radius: $radius-full;
  font-size: $font-size-xs;
  color: var(--accent-primary);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background-color: var(--color-primary-20);
    border-color: var(--color-primary);
  }
}

.examples {
  padding: $spacing-4 $spacing-6;
  border-top: 1px solid var(--border-primary);
  background-color: var(--bg-active);
}

.examples-title {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
  margin: 0 0 $spacing-3;
}

.examples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: $spacing-3;
}

.example-card {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-fast;

  &--chat {
    border-style: dashed;
    background-color: var(--bg-secondary);
  }

  &:hover {
    border-color: var(--color-primary);
    background-color: var(--color-primary-05);
  }

  span {
    font-size: $font-size-sm;
    color: var(--text-primary);
  }

  .example-icon {
    width: 20px;
    height: 20px;
    color: var(--color-primary);
  }
}

.chat-input {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);
  background-color: var(--bg-secondary);

  :deep(.el-textarea__inner) {
    background-color: var(--bg-tertiary);
    border-color: var(--border-primary);
    border-radius: $radius-lg;
    padding: $spacing-3;
    resize: none;
    font-size: $font-size-sm;

    &:focus {
      border-color: var(--color-primary);
    }
  }
}

.input-mode-bar {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-3;
  flex-wrap: wrap;
}

.mode-chip {
  display: inline-flex;
  align-items: center;
  gap: $spacing-1;
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-lg;
  border: 1px solid var(--border-primary);
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all $transition-fast;

  .mode-chip-icon {
    width: 16px;
    height: 16px;
  }

  &:hover:not(:disabled) {
    border-color: var(--color-primary-40);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &--active {
    color: var(--text-primary);
    font-weight: $font-weight-medium;
  }

  &--active:first-of-type {
    color: var(--color-primary);
    background-color: var(--color-primary-10);
    border-color: var(--color-primary-30);
  }

  &--active:nth-of-type(2) {
    color: #059669;
    background-color: rgba(5, 150, 105, 0.1);
    border-color: rgba(5, 150, 105, 0.3);
  }
}

.mode-hint {
  margin-left: auto;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  line-height: 1.4;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: $spacing-3;
}

.input-info {
  display: flex;
  align-items: center;
  gap: $spacing-4;

  .hint {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.workflow-detail {
  h3 {
    margin: 0 0 $spacing-2;
    color: var(--text-primary);
  }

  h4 {
    margin: $spacing-4 0 $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
  }

  p {
    color: var(--text-secondary);
    margin: 0;
  }
}

.detail-nodes {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.detail-node {
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;

  .node-name {
    font-weight: $font-weight-medium;
    color: var(--text-primary);
    margin-right: $spacing-2;
  }

  .node-type {
    font-size: $font-size-xs;
    color: var(--color-primary);
  }

  .node-config {
    margin-top: $spacing-2;
    font-size: $font-size-xs;
    color: var(--text-secondary);
    white-space: pre-wrap;
  }
}

.detail-edges {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.detail-edge {
  font-size: $font-size-sm;
  color: var(--text-secondary);
}

// ============================================
// Streaming Progress Indicator
// ============================================
.streaming-progress {
  padding: $spacing-4;
  padding-bottom: $spacing-6;
  background-color: var(--bg-tertiary);
  border-radius: $radius-xl;
  position: relative;
}

.progress-steps {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-3;
  margin-bottom: $spacing-3;
}

.progress-step {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  transition: all $transition-fast;

  .step-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--text-tertiary);
    transition: all $transition-fast;
  }

  &.is-active {
    color: var(--text-secondary);

    .step-dot {
      background-color: var(--color-primary);
      opacity: 0.5;
    }
  }

  &.is-current {
    color: var(--color-primary);
    font-weight: $font-weight-medium;

    .step-dot {
      background-color: var(--color-primary);
      animation: pulse 1.5s infinite;
    }
  }
}

// ============================================
// 深度思考内容展示
// ============================================
.thinking-display {
  margin-bottom: $spacing-3;
  padding: $spacing-3;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  max-height: 200px;
  overflow-y: auto;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
}

.thinking-icon {
  width: 14px;
  height: 14px;
  color: var(--color-primary);
  animation: pulse 2s infinite;
}

.thinking-label {
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.thinking-content {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  animation: thinking-fade-in 0.3s ease;

  &::after {
    content: '▍';
    display: inline-block;
    color: var(--color-primary);
    animation: blink 0.8s step-end infinite;
    margin-left: 2px;
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
}

@keyframes thinking-fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.progress-bar {
  height: 4px;
  background-color: var(--bg-primary);
  border-radius: $radius-full;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  border-radius: $radius-full;
  transition: width 0.3s ease;
}

// ============================================
// Intent Display
// ============================================
.intent-display {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-top: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
  font-size: $font-size-xs;
}

.intent-label {
  color: var(--text-tertiary);
}

.intent-tag {
  font-weight: $font-weight-medium;
}

.intent-detail {
  color: var(--text-secondary);
}

// ============================================
// Mini Workflow Preview
// ============================================
.mini-workflow-preview {
  margin-top: $spacing-4;
  margin-bottom: $spacing-4;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  overflow: hidden;
}

.preview-panel-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3 $spacing-4;
  background-color: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-primary);

  .preview-panel-icon {
    width: 18px;
    height: 18px;
    color: var(--color-primary);
  }

  .preview-panel-title {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }
}

.preview-panel-body {
  padding: $spacing-4;
}

.preview-nodes-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: $spacing-3;
}

.preview-node-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
  transition: all $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
    
    .node-actions {
      opacity: 1;
    }
  }

  &.has-error {
    border-left: 3px solid var(--color-error);
  }

  .node-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--color-primary-10);
    border-radius: $radius-md;
    color: var(--color-primary);

    svg {
      width: 16px;
      height: 16px;
    }
  }

  .node-info {
    flex: 1;
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  .node-name {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }

  .node-type-tag {
    font-size: 10px;
  }

  .node-actions {
    opacity: 0;
    transition: opacity $transition-fast;

    .node-action-icon {
      width: 14px;
      height: 14px;
    }
  }
}

.preview-panel-footer {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-2;
  padding-top: $spacing-3;
  border-top: 1px solid var(--border-primary);
}

// ============================================
// Workflow Validation Display
// ============================================
.validation-display {
  margin-bottom: $spacing-3;
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
}

.validation-errors,
.validation-warnings {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.validation-error,
.validation-warning {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-xs;
}

.validation-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;

  &.error {
    color: var(--color-error);
  }

  &.warning {
    color: var(--color-warning, #e6a23c);
  }
}

.validation-error {
  color: var(--color-error);
}

.validation-warning {
  color: var(--color-warning, #e6a23c);
}

// ============================================
// Cost Display
// ============================================
.cost-display {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--color-primary-10);
  border-radius: $radius-md;
  font-size: $font-size-xs;
}

.cost-label {
  color: var(--text-secondary);
}

.cost-value {
  color: var(--color-primary);
  font-weight: $font-weight-medium;
  font-family: monospace;
}

// ============================================
// Workflow Visualization with Edges
// ============================================
.workflow-visualization {
  margin-bottom: $spacing-3;
  height: 320px;
  border-radius: $radius-xl;
  overflow: hidden;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
}

.empty-workflow-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-3;
  height: 200px;
  color: var(--text-tertiary);

  .empty-icon {
    width: 32px;
    height: 32px;
    opacity: 0.5;
  }
}

// VueFlow overrides for NL preview (dark theme)
:deep(.vue-flow) {
  background-color: var(--bg-secondary);
}

:deep(.vue-flow__background) {
  background-color: var(--bg-secondary);
}

:deep(.vue-flow__edge-path) {
  stroke: var(--color-primary);
  stroke-width: 2;
}

:deep(.vue-flow__handle) {
  background-color: var(--color-primary);
  width: 8px;
  height: 8px;
}

// Custom nodes — reset Vue Flow wrapper so inner domain-node renders correctly
:deep(.vue-flow__node) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  box-shadow: none !important;
  width: auto !important;
  min-width: unset !important;
}

// ============================================
// Node Configuration Panel
// ============================================
.node-config-panel {
  margin-bottom: $spacing-3;
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
}

.config-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-3;

  .config-icon {
    width: 16px;
    height: 16px;
    color: var(--color-primary);
  }

  .config-title {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;

  label {
    font-size: $font-size-xs;
    color: var(--text-secondary);
    font-weight: $font-weight-medium;
  }
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-2;
  margin-top: $spacing-2;
}

// ============================================
// Enhanced Streaming Progress
// ============================================
.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-3;
}

.progress-stage {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .stage-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--text-tertiary);
    transition: all $transition-fast;

    &.is-active {
      background-color: var(--color-primary);
      animation: pulse 1.5s infinite;
    }
  }

  .stage-text {
    font-size: $font-size-sm;
    color: var(--text-primary);
    font-weight: $font-weight-medium;
  }
}

.progress-stats {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.token-count,
.time-remaining {
  padding: 2px 8px;
  background-color: var(--bg-primary);
  border-radius: $radius-full;
}

.progress-percentage {
  position: absolute;
  right: $spacing-4;
  bottom: $spacing-4;
  font-size: $font-size-xs;
  color: var(--color-primary);
  font-weight: $font-weight-medium;
}

// ============================================
// Preview Stats
// ============================================
.preview-stats {
  display: flex;
  gap: $spacing-2;
  margin-right: auto;
  margin-left: $spacing-3;
}
</style>
