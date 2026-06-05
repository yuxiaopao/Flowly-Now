<template>
  <div
    class="nl-creator"
    :class="{ 'sidebar-open': showHistorySidebar }"
  >
    <!-- ============================================ -->
    <!-- 历史记录侧边栏 (Doubao style) -->
    <!-- ============================================ -->
    <aside
      class="history-sidebar"
      :class="{ open: showHistorySidebar }"
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
        <el-input
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
          :key="session.session_id"
          class="session-item"
          :class="{
            'is-active': activeSessionId === (session.session_id),
            'is-selected': selectedSessions.includes(session.session_id)
          }"
          @click="handleSessionClick(session)"
        >
          <div
            v-if="batchMode"
            class="session-checkbox"
            @click.stop
          >
            <el-checkbox
              :model-value="selectedSessions.includes(session.session_id)"
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
              <span>{{ formatDate(session.created_at) }}</span>
              <span
                v-if="session.node_count"
                class="meta-divider"
              >·</span>
              <span v-if="session.node_count">{{ session.node_count }} 节点</span>
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

    <div
      v-if="showHistorySidebar"
      class="sidebar-overlay"
      @click="showHistorySidebar = false"
    />

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
                  关闭以保存的标签
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
          v-else
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
              <div class="message-text">
                <template v-if="message.isStreaming">
                  {{ message.content }}<span class="cursor">|</span>
                </template>
                <template v-else>
                  {{ message.content }}
                </template>
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
                    <span class="stage-text">{{ streamStage || '正在生成...' }}</span>
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
                      'is-active': idx <= streamSteps.indexOf(streamStage),
                      'is-current': streamStage === step
                    }"
                  >
                    <span class="step-dot" />
                    <span class="step-label">{{ step }}</span>
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
              v-if="workflowValidation.node_count"
              class="preview-stats"
            >
              <el-tag
                size="small"
                type="info"
              >
                {{ workflowValidation.node_count }} 节点
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

            <!-- Workflow Visualization with Edges -->
            <div class="workflow-visualization">
              <div class="nodes-container">
                <div
                  v-for="(node, idx) in getCurrentWorkflowNodes()"
                  :key="node.id || node.type + '-' + idx"
                  class="workflow-node"
                  :class="{
                    'has-error': node.error,
                    'is-selected': selectedNode?.id === node.id
                  }"
                  @click="selectNode(node)"
                >
                  <div class="node-icon">
                    <component :is="getNodeIcon(node.type)" />
                  </div>
                  <div class="node-info">
                    <span class="node-name">{{ node.name || node.type }}</span>
                    <el-tag
                      size="small"
                      type="info"
                      class="node-type-tag"
                    >
                      {{ node.type }}
                    </el-tag>
                  </div>
                  <div class="node-actions">
                    <el-button
                      size="small"
                      link
                      @click.stop="selectNode(node)"
                    >
                      <Settings class="node-action-icon" />
                    </el-button>
                  </div>
                </div>

                <!-- Edge Connections (CSS-based) -->
                <svg
                  v-if="getCurrentWorkflowEdges().length > 0"
                  class="edges-svg"
                >
                  <defs>
                    <marker
                      id="arrowhead-green"
                      markerWidth="10"
                      markerHeight="7"
                      refX="9"
                      refY="3.5"
                      orient="auto"
                    >
                      <polygon
                        points="0 0, 10 3.5, 0 7"
                        fill="#22c55e"
                      />
                    </marker>
                    <marker
                      id="arrowhead-red"
                      markerWidth="10"
                      markerHeight="7"
                      refX="9"
                      refY="3.5"
                      orient="auto"
                    >
                      <polygon
                        points="0 0, 10 3.5, 0 7"
                        fill="#ef4444"
                      />
                    </marker>
                    <marker
                      id="arrowhead-default"
                      markerWidth="10"
                      markerHeight="7"
                      refX="9"
                      refY="3.5"
                      orient="auto"
                    >
                      <polygon
                        points="0 0, 10 3.5, 0 7"
                        fill="#06b6d4"
                      />
                    </marker>
                  </defs>
                  <g
                    v-for="(edge, idx) in getEdgePositions(idx)"
                    :key="'edge-' + idx"
                  >
                    <path
                      :d="edge.path"
                      :stroke="getEdgeColor(edge.label)"
                      stroke-width="2"
                      fill="none"
                      :marker-end="getEdgeMarker(edge.label)"
                    />
                    <text
                      v-if="edge.label"
                      :x="edge.labelX"
                      :y="edge.labelY"
                      class="edge-label"
                      :fill="getEdgeColor(edge.label)"
                    >
                      {{ edge.label }}
                    </text>
                  </g>
                </svg>
              </div>
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
                  <label>节点名称</label>
                  <el-input
                    v-model="editingNodeConfig.name"
                    size="small"
                    placeholder="节点名称"
                  />
                </div>
                <div class="config-field">
                  <label>节点类型</label>
                  <el-input
                    :model-value="selectedNode.type"
                    size="small"
                    disabled
                  />
                </div>
                <div
                  v-if="selectedNode.config?.model || selectedNode.config?.prompt"
                  class="config-field"
                >
                  <label>模型</label>
                  <el-input
                    v-model="editingNodeConfig.model"
                    size="small"
                    placeholder="模型名称"
                  />
                </div>
                <div
                  v-if="selectedNode.config?.prompt"
                  class="config-field"
                >
                  <label>提示词</label>
                  <el-input
                    v-model="editingNodeConfig.prompt"
                    type="textarea"
                    :rows="3"
                    size="small"
                    placeholder="提示词模板"
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
            试试这些示例：
          </p>
          <div class="examples-grid">
            <div
              class="example-card"
              @click="applyExample('创建一个简单的问答机器人，可以回答用户关于产品的问题')"
            >
              <MessageSquare class="example-icon" />
              <span>问答机器人</span>
            </div>
            <div
              class="example-card"
              @click="applyExample('创建一个数据处理工作流，读取CSV文件，进行清洗和转换')"
            >
              <FileSpreadsheet class="example-icon" />
              <span>数据处理</span>
            </div>
            <div
              class="example-card"
              @click="applyExample('创建一个自动翻译工作流，输入文本自动翻译成多语言')"
            >
              <Languages class="example-icon" />
              <span>多语言翻译</span>
            </div>
            <div
              class="example-card"
              @click="applyExample('创建一个内容审核工作流，自动审核用户提交的内容')"
            >
              <ShieldCheck class="example-icon" />
              <span>内容审核</span>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            :placeholder="inputPlaceholder"
            :disabled="currentTabLoading"
            data-testid="chat-input"
            @keydown.enter.ctrl="sendMessage"
            @keydown.enter.meta="sendMessage"
            @keydown.shift.enter="inputMessage += '\n'"
          />
          <div class="input-actions">
            <div class="input-info">
              <span class="hint">Enter 发送, Shift+Enter 换行</span>
              <span
                v-if="activeTabId"
                class="session-id"
              >
                会话: {{ activeTabId }}
              </span>
            </div>
            <AppButton
              variant="primary"
              :loading="currentTabLoading"
              :disabled="!inputMessage.trim()"
              data-testid="send-button"
              @click="sendMessage"
            >
              <Send class="btn-icon" />
              {{ currentTabLoading ? '生成中...' : '发送' }}
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
import { useNLWorkflowStore } from '@/stores/nlWorkflow'
import {
  GitBranch, Send, Save,
  MessageSquare, FileSpreadsheet, Languages, ShieldCheck, AlertTriangle, History, Trash2,
  Search, Clock, MoreVertical, Edit2, AlertCircle, Plus,
  Menu, X, CheckSquare, ExternalLink, ChevronDown, XCircle, MinusCircle, CheckCircle,
  Settings, ArrowRight, Undo
} from 'lucide-vue-next'
import { nlWorkflowApi } from '@/api/nl-workflow'
import AppButton from '@/components/common/AppButton.vue'
import NlAvatar from '@/components/nl-workflow/NlAvatar.vue'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'

const router = useRouter()
const appStore = useAppStore()
const nlWorkflowStore = useNLWorkflowStore()

const darkThemes = ['dark', 'pure-bw', 'high-contrast']
const currentTabLogo = computed(() =>
  darkThemes.includes(appStore.theme) ? logoWhite : logoBlack
)

const showWorkflowDetail = ref(false)
const selectedWorkflow = ref(null)
const selectedModel = ref('')
const selectedModelProvider = ref('')
// Intent analysis display
const lastIntent = ref(null)

// Streaming state
const isStreaming = ref(false)
const streamProgress = ref(0)
const streamStage = ref('')
const streamSteps = ['分析需求', '设计结构', '生成节点', '连接边', '优化流程']
const tokenCount = ref(0)
const estimatedTimeRemaining = ref('')

// Workflow preview
const showMiniPreview = ref(true)
const miniPreviewNodes = ref([])
const miniPreviewEdges = ref([])

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

// Context-aware suggestions state
const hasGenerationFailed = ref(false)

const modelOptions = ref({})
const modelsLoading = ref(false)
const availableModels = ref([])

const showHistorySidebar = ref(false)
const historySessions = ref([])
const historyLoading = ref(false)
const historySearchQuery = ref('')
const historyStatusFilter = ref('')
const historyTotal = ref(0)

const batchMode = ref(false)
const selectedSessions = ref([])

const STORAGE_KEY = 'flowly_nl_tabs'
const STORAGE_TAB_KEY = 'flowly_nl_active_tab'

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
        suggestions: m.suggestions
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
    }
  } catch (e) {
    // Silently ignore storage errors
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

// 当前标签对应的后端 sessionId（用于侧边栏高亮）
const activeSessionId = computed(() => {
  return currentTab.value?.sessionId || null
})

const inputPlaceholder = '描述您想要的工作流...\n\n例如：创建一个自动回复用户问题的客服工作流，包含输入、LLM处理和输出'

// 搜索过滤
const filteredHistorySessions = computed(() => {
  let sessions = [...historySessions.value]

  if (historySearchQuery.value) {
    const query = historySearchQuery.value.toLowerCase()
    sessions = sessions.filter(s =>
      (s.name || '').toLowerCase().includes(query) ||
      (s.description || '').toLowerCase().includes(query) ||
      (s.workflow_name || '').toLowerCase().includes(query)
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

function createNewTab(session = null) {
  const tabId = generateTabId()
  const greetingMessages = [{
    role: 'assistant',
    content: '您好！我是 Flowly 的 AI 工作流助手。\n\n请描述您想要创建的工作流，例如：\n• "创建一个客服机器人，自动回复用户问题"\n• "数据处理流程：读取CSV、分析、输出结果"\n• "翻译工作流：输入文本自动翻译成英文"\n\n我将根据您的描述自动生成工作流。',
    timestamp: new Date().toISOString()
  }]

  const newTab = {
    id: tabId,
    title: '新对话',
    sessionId: session ? (session.session_id) : null,
    messages: greetingMessages,
    isLoading: false,
    isDirty: false,
    hasWorkflow: false
  }

  tabs.value.push(newTab)
  activeTabId.value = tabId
  inputMessage.value = ''
  saveTabsToStorage()

  if (session) {
    loadSessionIntoTab(tabId, session)
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

  const sessionId = session.session_id

  // Guard: prevent duplicate loading
  if (tab._isLoadingSession) return
  tab._isLoadingSession = true

  // If no valid sessionId, just show welcome message
  if (!sessionId) {
    tab.messages = [{
      role: 'assistant',
      content: '您好！我是 Flowly 的 AI 工作流助手。请描述您想要创建的工作流，我将根据您的描述自动生成。',
      timestamp: new Date().toISOString()
    }]
    tab.title = session.name || '新对话'
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
          timestamp: msg.timestamp || new Date().toISOString()
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
async function sendMessage() {
  const tab = currentTab.value
  if (!tab || !inputMessage.value.trim() || tab.isLoading) return

  // Prevent duplicate session creation: if already creating a session, wait
  if (tab._isCreatingSession) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

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
  streamProgress.value = 0
  tokenCount.value = 0

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
        response = await streamMessageWithUI(tab, userMessage, continueMessage)
        
        const workflowData2 = response.workflow || response.workflowJson
        if (workflowData2 && Object.keys(workflowData2).length > 0) {
          continueMessage.workflow = workflowData2
          tab.hasWorkflow = true
          updateWorkflowValidation(workflowData2)
        }
        
        // Update suggestions based on context
        continueMessage.suggestions = generateContextSuggestions(workflowData2)
      } catch (sendErr) {
        // Fallback to non-streaming
        response = await nlWorkflowApi.sendMessage(tab.sessionId, userMessage, {
          model: selectedModel.value
        })

        continueMessage.content = response.message || '我理解了，您还有其他需要调整的地方吗？'
        continueMessage.suggestions = response.suggestions || generateContextSuggestions(response.workflow)

        const workflowData2 = response.workflow || response.workflowJson
        if (workflowData2 && Object.keys(workflowData2).length > 0) {
          continueMessage.workflow = workflowData2
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
        response = await streamWorkflowWithUI(tab, userMessage, assistantMessage)
        
        const workflowData = response.workflow || response.workflowJson
        if (workflowData && Object.keys(workflowData).length > 0) {
          assistantMessage.workflow = workflowData
          assistantMessage.suggestions = generateContextSuggestions(workflowData)
          tab.hasWorkflow = true
          updateWorkflowValidation(workflowData)
        } else {
          assistantMessage.suggestions = generateContextSuggestions(null)
        }
        
        hasGenerationFailed.value = false
      } catch (createErr) {
        // Fallback to non-streaming
        response = await nlWorkflowApi.createSession({
          description: userMessage,
          name: `NL Workflow ${Date.now()}`,
          model: selectedModel.value
        })

        tab.sessionId = response.sessionId || response.id
        tab.title = userMessage.substring(0, 20) + (userMessage.length > 20 ? '...' : '')

        if (response.error) {
          assistantMessage.content = `抱歉，生成工作流时遇到了问题：${response.error}`
          hasGenerationFailed.value = true
        } else {
          const workflowData = response.workflow || response.workflowJson
          if (workflowData && Object.keys(workflowData).length > 0) {
            assistantMessage.content = response.message || '我已根据您的描述生成了工作流'
            assistantMessage.workflow = workflowData
            assistantMessage.suggestions = generateContextSuggestions(workflowData)
            tab.hasWorkflow = true
            updateWorkflowValidation(workflowData)
          } else {
            assistantMessage.content = response.message || '正在处理您的请求...'
            assistantMessage.suggestions = generateContextSuggestions(null)
          }
        }
        
        hasGenerationFailed.value = !!response.error
      } finally {
        assistantMessage.isStreaming = false
        tab._isCreatingSession = false
      }
    }
  } catch (err) {
    // Outer catch handles any unexpected errors
  } finally {
    if (tab) tab.isLoading = false
    isStreaming.value = false
    saveTabsToStorage()
    scrollToBottom()
  }
}

/**
 * Stream message with real-time UI updates
 */
async function streamMessageWithUI(tab, userMessage, messageObj) {
  streamStage.value = '正在处理...'
  streamProgress.value = 10
  
  try {
    const response = await nlWorkflowApi.streamMessage(tab.sessionId, userMessage, {
      model: selectedModel.value
    })

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let buffer = ''
    let workflowData = null

    while (true) {
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
              case 'progress':
              case 'step':
                streamProgress.value = Math.min(50, (data.progress || 30) + 20)
                streamStage.value = data.stage || '正在处理...'
                messageObj.content = data.message || fullContent
                break

              case 'token':
                fullContent += data.content
                messageObj.content = fullContent
                streamProgress.value = Math.min(70, streamProgress.value + 5)
                break

              case 'workflow':
                workflowData = data.workflow
                streamProgress.value = 90
                messageObj.content = data.message || fullContent || '工作流已更新'
                break

              case 'done':
                if (data.workflow_json) {
                  workflowData = JSON.parse(data.workflow_json)
                }
                streamProgress.value = 100
                messageObj.content = data.message || fullContent || '我理解了，您还有其他需要调整的地方吗？'
                messageObj.suggestions = data.suggestions || generateContextSuggestions(workflowData)
                break

              case 'error':
                throw new Error(data.error)

              case 'suggestions':
                messageObj.suggestions = data.suggestions
                break
            }
          } catch (e) {
            if (e.message === data?.error) throw e
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
async function streamWorkflowWithUI(tab, userMessage, messageObj) {
  streamStage.value = streamSteps[0]
  streamProgress.value = 5
  
  try {
    const response = await nlWorkflowApi.streamWorkflow({
      description: userMessage,
      name: `NL Workflow ${Date.now()}`,
      model: selectedModel.value
    })

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let buffer = ''
    let workflowData = null
    let stepIndex = 0

    while (true) {
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
              case 'session':
                tab.sessionId = data.session_id || data.sessionId
                tab.title = userMessage.substring(0, 20) + (userMessage.length > 20 ? '...' : '')
                break

              case 'progress':
              case 'step':
                if (data.stage) {
                  const idx = streamSteps.indexOf(data.stage)
                  if (idx !== -1) stepIndex = idx
                  streamStage.value = data.stage
                }
                streamProgress.value = Math.min(80, (stepIndex / streamSteps.length) * 100)
                messageObj.content = data.message || fullContent
                break

              case 'token':
                fullContent += data.content
                messageObj.content = fullContent
                streamProgress.value = Math.min(90, streamProgress.value + 2)
                break

              case 'workflow':
                workflowData = data.workflow
                streamProgress.value = 95
                messageObj.content = data.message || '工作流生成中...'
                break

              case 'done':
                if (data.workflow_json) {
                  workflowData = JSON.parse(data.workflow_json)
                }
                streamProgress.value = 100
                messageObj.content = data.message || response.message || '我已根据您的描述生成了工作流'
                messageObj.workflow = workflowData
                break

              case 'error':
                throw new Error(data.error)
            }
          } catch (e) {
            if (e.message === data?.error) throw e
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
 * Update estimated time remaining based on token count
 */
function updateEstimatedTime() {
  const tokensPerSecond = 50 // Rough estimate
  const remainingTokens = Math.max(0, 500 - tokenCount.value)
  const secondsRemaining = Math.ceil(remainingTokens / tokensPerSecond)
  
  if (secondsRemaining < 60) {
    estimatedTimeRemaining.value = `约 ${secondsRemaining} 秒`
  } else {
    estimatedTimeRemaining.value = `约 ${Math.ceil(secondsRemaining / 60)} 分钟`
  }
}

/**
 * Generate context-aware suggestions based on workflow state
 */
function generateContextSuggestions(workflow) {
  const suggestions = []
  const nodeCount = workflow?.nodes?.length || 0
  const hasWorkflow = !!workflow
  
  // Get current tab for isDirty check
  const currentTab = tabs.value.find(t => t.id === activeTabId.value)
  
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
 * Get edge positions for SVG rendering
 */
function getEdgePositions(nodeIndex) {
  const edges = getCurrentWorkflowEdges()
  const positions = []
  
  edges.forEach((edge, idx) => {
    const sourceNode = getCurrentWorkflowNodes().find(n => n.id === edge.source)
    const targetNode = getCurrentWorkflowNodes().find(n => n.id === edge.target)
    
    if (sourceNode && targetNode) {
      // Calculate approximate positions based on node index
      const sourceY = (idx * 60) + 30
      const targetY = (idx * 60) + 30
      
      positions.push({
        path: `M 150 ${sourceY} C 180 ${sourceY}, 20 ${targetY}, 50 ${targetY}`,
        labelX: 100,
        labelY: (sourceY + targetY) / 2,
        label: edge.label || ''
      })
    }
  })
  
  return positions
}

/**
 * Get edge color based on label
 */
function getEdgeColor(label) {
  if (!label) return '#06b6d4' // Default cyan
  const lowerLabel = label.toLowerCase()
  if (lowerLabel.includes('yes') || lowerLabel.includes('true') || lowerLabel.includes('通过') || lowerLabel.includes('成功')) {
    return '#22c55e' // Green
  }
  if (lowerLabel.includes('no') || lowerLabel.includes('false') || lowerLabel.includes('失败') || lowerLabel.includes('拒绝')) {
    return '#ef4444' // Red
  }
  return '#06b6d4' // Default cyan
}

/**
 * Get edge marker based on label
 */
function getEdgeMarker(label) {
  if (!label) return 'url(#arrowhead-default)'
  const lowerLabel = label.toLowerCase()
  if (lowerLabel.includes('yes') || lowerLabel.includes('true') || lowerLabel.includes('通过') || lowerLabel.includes('成功')) {
    return 'url(#arrowhead-green)'
  }
  if (lowerLabel.includes('no') || lowerLabel.includes('false') || lowerLabel.includes('失败') || lowerLabel.includes('拒绝')) {
    return 'url(#arrowhead-red)'
  }
  return 'url(#arrowhead-default)'
}

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

function continueConversation(suggestion) {
  inputMessage.value = suggestion
  sendMessage()
}

function applyExample(example) {
  inputMessage.value = example
}

function viewWorkflow(workflow) {
  selectedWorkflow.value = workflow || null
  showWorkflowDetail.value = true
}

async function saveWorkflow(workflow) {
  const tab = currentTab.value
  if (!tab?.sessionId) {
    appStore.error('请先生成工作流')
    return
  }

  try {
    const response = await nlWorkflowApi.confirmWorkflow(tab.sessionId)

    const workflowId = response.workflow_id || response.id
    if (workflowId) {
      appStore.success('工作流已保存')
      showWorkflowDetail.value = false
      tab.isDirty = false
      saveTabsToStorage()
      router.push(`/workflows/${workflowId}/edit`)
    }
  } catch (err) {
    appStore.error('保存失败')
  }
}

// ============================================
// 模型加载
// ============================================
async function loadModels() {
  if (availableModels.value.length > 0) return
  modelsLoading.value = true
  try {
    const response = await nlWorkflowApi.getModels()
    availableModels.value = response.models || []

    if (response.default) {
      selectedModel.value = response.default
    } else if (availableModels.value.length > 0) {
      selectedModel.value = availableModels.value[0].modelId
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
    historySessions.value = response.data || response || []
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

function getCurrentWorkflowNodes() {
  const workflow = getCurrentWorkflow()
  if (!workflow) return []
  return workflow.nodes || []
}

function getCurrentWorkflowEdges() {
  const workflow = getCurrentWorkflow()
  if (!workflow) return []
  return workflow.edges || []
}

function getNodeIcon(nodeType) {
  // Return appropriate icon based on node type
  const icons = {
    'start': MessageSquare,
    'input': MessageSquare,
    'llm': MessageSquare,
    'output': Send,
    'condition': ShieldCheck,
    'http': FileSpreadsheet,
    'code': Languages,
    'delay': Clock,
    'end': ShieldCheck,
    'default': GitBranch
  }
  return icons[nodeType] || icons.default
}

function viewWorkflowNode(node) {
  // Open node configuration modal
  selectedWorkflow.value = node
  showWorkflowDetail.value = true
}

function handleSessionAction(command, session) {
  const sessionId = session.session_id

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
  const sessionId = session.session_id
  if (!sessionId) return

  try {
    const { value: newName } = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: session.name || session.description || ''
    })

      if (newName) {
        try {
          await nlWorkflowApi.updateSession(sessionId, { name: newName })
        } catch (err) {}

        const idx = historySessions.value.findIndex(s => s.sessionId === sessionId)
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
  } catch (err) {}
}

function handleSessionClick(session) {
  if (batchMode.value) return
  const sessionId = session.session_id

  // Defensive: don't create tabs for invalid sessions
  if (!sessionId) return

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
  const sessionId = session.session_id
  if (!sessionId) return

  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '删除对话', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await nlWorkflowApi.deleteSession(sessionId)
    historySessions.value = historySessions.value.filter(s => s.sessionId !== sessionId)
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
  const sessionId = session.session_id
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
    selectedSessions.value = filteredHistorySessions.value.map(s => s.sessionId)
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
      s => !selectedSessions.value.includes(s.sessionId)
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
  left: -320px;
  top: $header-height;
  width: 320px;
  height: calc(100vh - #{$header-height});
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  z-index: $z-fixed;
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: $shadow-xl;

  &.open {
    left: 0;
  }
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

.sidebar-overlay {
  display: none;

  @media (max-width: 768px) {
    display: block;
    position: fixed;
    inset: 0;
    top: $header-height;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: $z-fixed - 1;
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

  .session-id {
    font-size: $font-size-xs;
    color: var(--color-primary);
    padding: $spacing-1 $spacing-2;
    background-color: var(--color-primary-10);
    border-radius: $radius-md;
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

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
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
}

.nodes-container {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  position: relative;
  padding-left: 20px;
}

.workflow-node {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-lg;
  border: 2px solid transparent;
  transition: all $transition-fast;
  cursor: pointer;
  position: relative;

  &:hover {
    background-color: var(--bg-hover);

    .node-actions {
      opacity: 1;
    }
  }

  &.has-error {
    border-left: 3px solid var(--color-error);
  }

  &.is-selected {
    border-color: var(--color-primary);
    background-color: var(--color-primary-05);
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

// ============================================
// Edge SVG
// ============================================
.edges-svg {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.edge-label {
  font-size: 10px;
  font-weight: $font-weight-medium;
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
