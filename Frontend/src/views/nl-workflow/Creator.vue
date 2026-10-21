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
        ref="historyPanel"
        class="history-sidebar"
        :class="{ open: showHistorySidebar }"
        :style="historySidebarStyle"
        :aria-hidden="!showHistorySidebar"
        :inert="!showHistorySidebar"
        @keydown.esc="showHistorySidebar = false"
        @keydown.tab="trapHistoryFocus"
      >
        <div class="sidebar-header">
          <div class="sidebar-title">
            <MessageSquare class="title-icon" />
            <span>对话历史</span>
          </div>
          <button
            class="sidebar-close-btn"
            aria-label="关闭对话历史"
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
            :class="{ active: historyStatusFilter === 'processing' }"
            @click="historyStatusFilter = 'processing'; handleHistorySearch()"
          >
            处理中
          </button>
          <button
            v-for="state in ['active', 'failed']"
            :key="state"
            class="filter-tag"
            :class="{ active: historyStatusFilter === state }"
            @click="historyStatusFilter = state; handleHistorySearch()"
          >
            {{ getStatusText(state) }}
          </button>
        </div>

        <div
          v-if="historyError"
          class="workspace-notice"
          role="alert"
        >
          {{ historyError }} <el-button
            link
            @click="loadHistory()"
          >
            重试
          </el-button>
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
            role="button"
            tabindex="0"
            @keydown.enter="handleSessionItemClick($event)"
            @keydown.space.prevent="handleSessionItemClick($event)"
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
              @click.stop
            >
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleSessionAction(cmd, session)"
              >
                <button
                  class="action-btn"
                  :aria-label="`${session.name || '未命名会话'}的更多操作`"
                >
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
              {{ historySearchQuery || historyStatusFilter ? '没有匹配的对话' : '暂无对话记录' }}
            </div>
            <div class="empty-hint">
              {{ historySearchQuery || historyStatusFilter ? '调整搜索词或状态筛选' : '点击上方「新建对话」开始' }}
            </div>
          </div>
        </div>

        <el-button
          v-if="historyHasMore"
          :loading="historyLoading"
          class="history-more"
          @click="loadHistory(true)"
        >
          加载更多对话
        </el-button>
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
    <div
      class="creator-main"
      :inert="showHistorySidebar"
    >
      <header class="workspace-header">
        <div class="workspace-header-start">
          <button
            ref="historyTrigger"
            class="toolbar-btn icon-button"
            title="历史对话"
            aria-label="历史对话"
            :aria-expanded="showHistorySidebar"
            @click="showHistorySidebar = true"
          >
            <PanelLeft class="toolbar-icon" />
          </button>
          <h1>{{ NL_CREATOR.title }}</h1>
          <span
            class="header-divider"
            aria-hidden="true"
          >/</span>
          <button
            class="conversation-title"
            :title="NL_CREATOR.renameConversation"
            :disabled="!currentTab || _isSending"
            @click="handleRenameTab(currentTab)"
          >
            {{ currentTab?.title || NL_CREATOR.newConversation }}
          </button>
        </div>
        <div class="toolbar-right">
          <button
            v-if="currentTab?.hasWorkflow"
            ref="previewTrigger"
            class="toolbar-btn preview-toggle"
            :aria-expanded="showMiniPreview"
            @click="showMiniPreview = !showMiniPreview"
          >
            <PanelRight class="toolbar-icon" /><span>{{ NL_CREATOR.preview }}</span>
          </button>
          <el-dropdown
            trigger="click"
            placement="bottom-end"
          >
            <button
              class="toolbar-btn icon-button"
              :title="NL_CREATOR.conversationActions"
              :aria-label="NL_CREATOR.conversationActions"
            >
              <MoreVertical class="toolbar-icon" />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  :disabled="!currentTab?.sessionId || currentTabLoading || _isSending"
                  @click="refreshCurrentSession"
                >
                  <RefreshCw class="dropdown-icon" />同步会话
                </el-dropdown-item>
                <el-dropdown-item
                  :disabled="!currentTab || _isSending"
                  @click="exportConversation"
                >
                  <Download class="dropdown-icon" />导出对话
                </el-dropdown-item>
                <el-dropdown-item
                  :disabled="!currentTab || _isSending"
                  @click="handleRenameTab(currentTab)"
                >
                  <Edit2 class="dropdown-icon" />重命名对话
                </el-dropdown-item>
                <el-dropdown-item
                  :disabled="!currentTab || _isSending"
                  @click="closeTab(activeTabId)"
                >
                  <X class="dropdown-icon" />关闭当前对话
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <button
            class="toolbar-btn new-tab-btn"
            :disabled="currentTabLoading"
            @click="handleNewTab"
          >
            <Plus class="toolbar-icon" /><span>{{ NL_CREATOR.newConversation }}</span>
          </button>
        </div>
      </header>
      <div
        v-if="storageError"
        class="workspace-notice"
        role="alert"
      >
        {{ storageError }}
      </div>

      <!-- ============================================ -->
      <!-- 浏览器风格标签页 -->
      <!-- ============================================ -->
      <div
        v-if="tabs.length > 1"
        class="tab-bar"
      >
        <div class="tab-scroll-container">
          <div
            class="tab-list"
            role="tablist"
            aria-label="语创对话"
          >
            <div
              v-for="tab in tabs"
              :key="tab.id"
              class="tab-item"
              :class="{
                'is-active': activeTabId === tab.id,
                'is-loading': tab.isLoading
              }"
              role="tab"
              :aria-selected="activeTabId === tab.id"
              :aria-disabled="_isSending && activeTabId !== tab.id"
              :tabindex="activeTabId === tab.id ? 0 : -1"
              @keydown.enter="switchTab(tab.id)"
              @keydown.space.prevent="switchTab(tab.id)"
              @keydown.right.prevent="switchTab(tabs[(tabs.indexOf(tab) + 1) % tabs.length].id)"
              @keydown.left.prevent="switchTab(tabs[(tabs.indexOf(tab) + tabs.length - 1) % tabs.length].id)"
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
                :title="tab.draft ? '关闭标签会移除未发送草稿' : '关闭标签'"
                :aria-label="`关闭 ${tab.title}`"
                :disabled="_isSending"
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

      <div
        v-if="modelsError"
        class="workspace-notice"
        role="alert"
      >
        {{ modelsError }} <el-button
          link
          @click="loadModels(true)"
        >
          重试
        </el-button>
      </div>
      <!-- 聊天容器 -->
      <div
        v-if="currentTab?.taskId && ['processing', 'failed'].includes(currentTab.sessionStatus)"
        class="workspace-notice"
        role="status"
      >
        后台任务：{{ getStatusText(currentTab.sessionStatus) }}。可同步会话查看最新结果。
        <el-button
          v-if="currentTab.sessionStatus === 'failed'"
          link
          :loading="recoveringTask"
          @click="retryBackgroundTask"
        >
          重试后台任务
        </el-button>
      </div>
      <div
        class="chat-container"
        :class="{ 'has-preview': currentTab?.hasWorkflow && showMiniPreview, 'is-welcome': isWelcome }"
      >
        <div
          class="conversation-pane"
          :inert="compactPreview && currentTab?.hasWorkflow && showMiniPreview"
        >
          <div
            v-if="isWelcome"
            class="welcome-state"
          >
            <h2>{{ NL_CREATOR.welcomeTitle }}</h2>
            <p>{{ NL_CREATOR.welcomeDescription }}</p>
          </div>
          <div
            v-show="!isWelcome"
            ref="messagesContainer"
            :key="activeTabId"
            class="chat-messages"
            role="log"
            aria-label="对话消息"
            :aria-busy="currentTabLoading"
            @scroll="followMessages = $event.target.scrollHeight - $event.target.scrollTop - $event.target.clientHeight < NL_CREATOR.scrollThreshold"
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
                  :state="getAssistantAvatarState(message, streamMode)"
                  :animated="Boolean(message.isStreaming)"
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
                      :loading="_isSaving"
                      :disabled="_isSending"
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
                    :disabled="_isSending"
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
                  v-for="(guidance, guidanceIndex) in (!message.isStreaming ? guidanceList(message.nodeGuidance) : [])"
                  :key="guidanceIndex"
                  :guidance="guidance"
                />

                <!-- Intent Analysis Display -->
                <div
                  v-if="message.intent && !message.isStreaming"
                  class="intent-display"
                >
                  <span class="intent-label">识别意图：</span>
                  <el-tag
                    size="small"
                    :type="getIntentTagType(message.intent.type || message.intent)"
                    class="intent-tag"
                  >
                    {{ getIntentText(message.intent.type || message.intent) }}
                  </el-tag>
                  <span
                    v-if="message.intent.detail"
                    class="intent-detail"
                  >{{ message.intent.detail }}</span>
                </div>

                <div
                  v-if="!message.isStreaming"
                  class="message-tools"
                >
                  <button
                    class="toolbar-btn"
                    aria-label="复制消息"
                    @click="copyMessage(message)"
                  >
                    <Copy class="toolbar-icon" />复制
                  </button>
                  <button
                    v-if="message.error || message.interrupted"
                    class="toolbar-btn"
                    :disabled="_isSending"
                    @click="restoreLastRequest"
                  >
                    重新编辑需求
                  </button>
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
                  :state="streamMode === 'generating' ? 'generating' : 'thinking'"
                  animated
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
                      >{{ tokenCount }} 字符</span>
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

          <section
            v-if="isWelcome"
            class="examples"
            aria-label="需求模板"
          >
            <div class="starter-list">
              <button
                v-for="example in NL_STARTERS"
                :key="example.title"
                class="starter-item"
                @click="applyExample(example)"
              >
                <span class="starter-category">{{ example.category }}</span><strong>{{ example.title }}</strong><ArrowUpRight
                  class="starter-arrow"
                  aria-hidden="true"
                />
              </button>
            </div>
          </section>

          <div class="chat-input">
            <el-input
              id="chat-message-input"
              ref="chatInputRef"
              v-model="inputMessage"
              type="textarea"
              :autosize="NL_CREATOR.composerRows"
              :maxlength="NL_CREATOR.maxMessageLength"
              :title="`${inputModeHint} · ${NL_CREATOR.keyboardHint}`"
              data-testid="chat-input"
              :placeholder="inputPlaceholder"
              :disabled="currentTabLoading"
              aria-label="输入工作流描述"
              @keydown.enter="handleInputKeydown"
            />
            <div class="composer-controls">
              <div class="input-mode-bar">
                <button
                  type="button"
                  class="mode-chip"
                  :class="{ 'mode-chip--active': inputMode === 'thinking' }"
                  :disabled="currentTabLoading"
                  :aria-pressed="inputMode === 'thinking'"
                  :title="NL_CREATOR.thinkingHint"
                  aria-label="深度思考"
                  data-testid="mode-thinking"
                  @click="inputMode = 'thinking'"
                >
                  <Brain class="mode-chip-icon" />
                  <span class="mode-label">{{ NL_CREATOR.thinkingLabel }}</span>
                </button>
                <button
                  type="button"
                  class="mode-chip"
                  :class="{ 'mode-chip--active': inputMode === 'generate' }"
                  :disabled="currentTabLoading"
                  :aria-pressed="inputMode === 'generate'"
                  :title="NL_CREATOR.generateHint"
                  aria-label="生成工作流"
                  data-testid="mode-generate"
                  @click="inputMode = 'generate'"
                >
                  <GitBranch class="mode-chip-icon" />
                  <span class="mode-label">{{ NL_CREATOR.generateLabel }}</span>
                </button>
              </div>
              <div class="composer-model">
                <el-select
                  v-model="selectedModel"
                  placeholder="选择 AI 模型"
                  filterable
                  size="small"
                  class="model-select"
                  aria-label="选择 AI 模型"
                  :loading="modelsLoading"
                  :disabled="_isSending"
                  :no-data-text="modelsLoading ? '加载模型中...' : '暂无可用模型'"
                  data-testid="model-selector"
                  @focus="loadModels(false)"
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
                <el-popover
                  placement="top-start"
                  trigger="click"
                  :width="NL_CREATOR.modelSettingsWidth"
                >
                  <template #reference>
                    <button
                      class="toolbar-btn icon-button"
                      :title="NL_CREATOR.modelSettings"
                      :aria-label="NL_CREATOR.modelSettings"
                    >
                      <Settings class="toolbar-icon" />
                    </button>
                  </template>
                  <div class="model-settings">
                    <el-checkbox
                      v-model="showAllModels"
                      :disabled="_isSending"
                      @change="loadModels(true)"
                    >
                      显示全部模型
                    </el-checkbox>
                    <p v-if="selectedModelProvider">
                      {{ selectedModelProvider }} · {{ selectedModel }}
                    </p>
                    <el-button
                      text
                      :loading="modelsLoading"
                      :disabled="_isSending"
                      @click="loadModels(true)"
                    >
                      <RefreshCw class="toolbar-icon" />刷新模型
                    </el-button>
                  </div>
                </el-popover>
              </div>
              <VoiceRecorder
                :key="activeTabId"
                v-model="voiceClip"
                :disabled="currentTabLoading"
                @busy-change="voiceBusy = $event"
              />
              <el-button
                v-if="_isSending"
                type="danger"
                plain
                @click="activeController?.abort()"
              >
                <Square class="btn-icon-sm" />停止接收
              </el-button>
              <AppButton
                v-else
                variant="primary"
                class="send-button"
                :aria-label="sendButtonLabel"
                :title="sendButtonLabel"
                :loading="currentTabLoading"
                :disabled="!inputMessage.trim() || voiceBusy || _isSending || !selectedModel || modelsLoading || backgroundTaskPending"
                data-testid="send-button"
                @click="sendMessage"
              >
                <ArrowUp class="btn-icon" />
              </AppButton>
            </div>
            <div
              v-if="!modelsLoading && !selectedModel && availableModels.length === 0"
              class="composer-warning"
              role="status"
            >
              {{ NL_CREATOR.noModel }}
            </div>
          </div>
        </div>
        <!-- Mini Workflow Preview Panel (embedded) with Edge Visualization -->
        <div
          v-if="currentTab?.hasWorkflow && showMiniPreview"
          ref="previewPanel"
          class="mini-workflow-preview"
          role="region"
          aria-label="工作流预览"
          @keydown.esc.stop="showMiniPreview = false"
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
              :aria-label="NL_CREATOR.closePreview"
              @click="showMiniPreview = false"
            >
              <X class="btn-icon-sm" />
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
              v-for="(guidance, guidanceIndex) in guidanceList(nodeGuidance)"
              :key="guidanceIndex"
              :guidance="guidance"
            />

            <!-- Workflow Visualization with VueFlow -->
            <div
              ref="previewContainer"
              class="workflow-visualization"
            >
              <div
                v-if="nlNodes.length === 0"
                class="empty-workflow-hint"
              >
                <GitBranch class="empty-icon" />
                <span>{{ currentTabLoading ? '正在生成工作流...' : '暂无工作流预览，请发送描述生成' }}</span>
              </div>
              <VueFlow
                v-else-if="previewReady"
                :id="`nl-preview-${activeTabId}`"
                v-model:nodes="nlNodes"
                v-model:edges="nlEdges"
                :style="{ width: `${previewDimensions.width}px`, height: `${previewDimensions.height}px` }"
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
                <div class="config-field">
                  <label for="node-config-json">节点参数 (JSON)</label>
                  <el-input
                    id="node-config-json"
                    v-model="configJson"
                    type="textarea"
                    :rows="8"
                    aria-label="节点参数 JSON"
                    :disabled="configSaving"
                  />
                  <small>参数将保存到会话草稿；完整表单可在工作流编辑器中继续配置。</small>
                </div>
                <p
                  v-if="configError"
                  class="config-error"
                  role="alert"
                >
                  {{ configError }}
                </p>
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
                    :loading="configSaving"
                    :disabled="_isSending"
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
                :loading="_isSaving"
                :disabled="_isSending || configSaving"
                @click="saveWorkflow(getCurrentWorkflow())"
              >
                <Save class="btn-icon-sm" />
                保存并打开编辑器
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 工作流详情对话框 -->
    <el-dialog
      v-model="showWorkflowDetail"
      title="工作流详情"
      width="min(700px, 94vw)"
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
          :loading="_isSaving"
          :disabled="_isSending"
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
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { VOICE_RECORDER } from '@/config/voiceRecorder'
import VoiceRecorder from '@/components/nl-workflow/VoiceRecorder.vue'
import { NL_CREATOR, NL_SESSION_STATUS, NL_STARTERS } from '@/config/nlCreator'
import { latestWorkflow, parseNodeConfig, conversationMarkdown, consumeNlStream, guidanceList, nlErrorMessage } from '@/utils/nlCreator'
import {
  GitBranch, ArrowUp, ArrowUpRight, PanelLeft, PanelRight, Save,
  MessageSquare, Download, Copy, RefreshCw, Square, AlertTriangle, History, Trash2,
  Search, Clock, MoreVertical, Edit2, AlertCircle, Plus,
  X, CheckSquare, ExternalLink, ChevronDown, XCircle, MinusCircle, CheckCircle,
  Settings, Brain
} from 'lucide-vue-next'
import { nlWorkflowApi } from '@/api/nl-workflow'
import { nlPayloadWithCapabilities } from '@/utils/hardwareProfile'
import { createWorkflow } from '@/api/workflow'
import { nlWorkflowToVueFlow, nlWorkflowToSavePayload } from '@/utils/workflowTransform'
import { buildNodeTypesMap } from '@/config/nodeComponents'
import { WORKFLOW_CANVAS_VIEWPORT, WORKFLOW_CANVAS_ZOOM } from '@/config/workflowCanvas'
import AppButton from '@/components/common/AppButton.vue'
import NlAvatar from '@/components/nl-workflow/NlAvatar.vue'
import { getAssistantAvatarState } from '@/utils/botAvatar'
import EmailConfigGuide from '@/components/nl-workflow/EmailConfigGuide.vue'
import NodeConfigGuide from '@/components/nl-workflow/NodeConfigGuide.vue'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
// VueFlow node components for NL workflow preview
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'

const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const voiceBusy = ref(false)
const voiceClip = computed({
  get: () => currentTab.value?.voiceClip || null,
  set: value => { if (currentTab.value) currentTab.value.voiceClip = value },
})
function guardVoiceCapture() {
  if (!voiceBusy.value) return false
  appStore.warning(VOICE_RECORDER.labels.busy)
  return true
}
function protectUnsavedRecording(event) {
  if (voiceBusy.value || tabs.value.some(tab => tab.voiceClip && !tab.voiceClip.downloaded)) {
    event.preventDefault()
    event.returnValue = ''
  }
}
onBeforeRouteLeave(async () => {
  if (!voiceBusy.value && !tabs.value.some(tab => tab.voiceClip && !tab.voiceClip.downloaded)) return true
  try {
    await ElMessageBox.confirm(VOICE_RECORDER.labels.leave, VOICE_RECORDER.labels.title, { confirmButtonText: '离开页面', cancelButtonText: '保留录音', type: 'warning' })
    return true
  } catch { return false }
})
const storageError = ref('')
const historyError = ref('')
const modelsError = ref('')
const historyPage = ref(1)
const historyHasMore = ref(false)
const configJson = ref('{}')
const configError = ref('')
const configSaving = ref(false)
const recoveringTask = ref(false)
const followMessages = ref(true)
let historyRequestId = 0
let historySearchTimer
let activeController = null
let storageTimer

const darkThemes = ['dark', 'pure-bw', 'high-contrast']
const currentTabLogo = computed(() =>
  darkThemes.includes(appStore.theme) ? logoWhite : logoBlack
)

const showWorkflowDetail = ref(false)
const selectedWorkflow = ref(null)
const selectedModel = ref('')
const selectedModelProvider = computed(() => availableModels.value.find(model => model.modelId === selectedModel.value)?.provider || '')
const showAllModels = ref(false)
// Streaming state
const isStreaming = ref(false)
const streamProgress = ref(0)
const streamStage = ref('')
const streamMode = ref('idle') // idle | thinking | generating
const inputMode = computed({ get: () => currentTab.value?.mode || 'thinking', set: value => { if (currentTab.value) currentTab.value.mode = value } }) // thinking | generate — 用户手动选择
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
const previewTrigger = ref(null)
const previewPanel = ref(null)
const previewMedia = window.matchMedia(NL_CREATOR.compactPreviewQuery)
const compactPreview = ref(previewMedia.matches)
const updatePreviewLayout = event => { compactPreview.value = event.matches }
const previewContainer = ref(null)
const previewReady = ref(false)
const previewDimensions = ref({ width: 0, height: 0 })
watch(previewContainer, (element, previous, onCleanup) => {
  previewReady.value = false
  if (!element) return
  const observer = new ResizeObserver(([entry]) => {
    previewDimensions.value = { width: entry.contentRect.width, height: entry.contentRect.height }
    previewReady.value = entry.contentRect.width > 0 && entry.contentRect.height > 0
  })
  observer.observe(element)
  onCleanup(() => observer.disconnect())
})

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
const historyPanel = ref(null)
const historyTrigger = ref(null)

watch(showHistorySidebar, async open => {
  await nextTick()
  if (open) historyPanel.value?.querySelector('button')?.focus()
  else historyTrigger.value?.focus()
})

function trapHistoryFocus(event) {
  const controls = [...(historyPanel.value?.querySelectorAll('button:not(:disabled), input:not(:disabled), [tabindex="0"]') || [])].filter(element => element.getClientRects().length)
  const first = controls[0]
  const last = controls[controls.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}

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

const storageOwner = authStore.user?.id || authStore.user?.username || 'anonymous'
const storageKey = () => `${NL_CREATOR.storagePrefix}:${storageOwner}`

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
    const tabData = tabs.value.map(({ id, title, sessionId, hasWorkflow, workflowId, messages, draft, mode, isDirty, savedFingerprint, taskId, sessionStatus }) => ({
      id, title, sessionId, hasWorkflow, workflowId, draft, mode, isDirty, savedFingerprint, taskId, sessionStatus,
      messages: messages.map(message => ({ ...message, isStreaming: false }))
    }))
    localStorage.setItem(storageKey(), JSON.stringify({ tabs: tabData, activeId: activeTabId.value }))
    storageError.value = ''
  } catch {
    storageError.value = NL_CREATOR.storageError
  }
}

function loadTabsFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey()) || 'null')
    if (!Array.isArray(saved?.tabs)) return
    tabs.value = saved.tabs.filter(tab => tab.id && Array.isArray(tab.messages)).map(tab => ({ ...tab, isLoading: false }))
    activeTabId.value = tabs.value.find(tab => tab.id === saved.activeId)?.id || tabs.value[0]?.id || null
    restoreActiveTabGuidance()
  } catch {
    storageError.value = NL_CREATOR.storageError
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

watch(() => Boolean(currentTab.value?.hasWorkflow && showMiniPreview.value && compactPreview.value), async (open, previous) => {
  await nextTick()
  if (open) previewPanel.value?.querySelector('button')?.focus()
  else if (previous) previewTrigger.value?.focus()
})

const currentTabMessages = computed(() => {
  return currentTab.value?.messages || []
})

const isWelcome = computed(() => !currentTab.value?.isLoading && !currentTab.value?.hasWorkflow && currentTabMessages.value.every(message => message.role === 'assistant' && message.content === NL_CREATOR.greeting))

const currentTabLoading = computed(() => {
  return currentTab.value?.isLoading || false
})
const backgroundTaskPending = computed(() => Boolean(currentTab.value?.taskId && currentTab.value?.sessionStatus === 'processing'))

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

const inputPlaceholder = computed(() => inputMode.value === 'generate' ? NL_CREATOR.generatePlaceholder : NL_CREATOR.thinkingPlaceholder)

const inputModeHint = computed(() => inputMode.value === 'generate' ? NL_CREATOR.generateHint : NL_CREATOR.thinkingHint)

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
    const dateA = new Date(a.updatedAt || a.updated_at || a.createdAt || a.created_at || 0)
    const dateB = new Date(b.updatedAt || b.updated_at || b.createdAt || b.created_at || 0)
    return dateB.getTime() - dateA.getTime()
  })

  return sessions
})

// Input bound to current tab
const inputMessage = computed({ get: () => currentTab.value?.draft || '', set: value => { if (currentTab.value) currentTab.value.draft = value } })
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
  window.addEventListener('beforeunload', protectUnsavedRecording)
  previewMedia.addEventListener('change', updatePreviewLayout)
  loadTabsFromStorage()
  if (tabs.value.length === 0) {
    createNewTab()
  }
  await Promise.allSettled([loadModels(), loadHistory(), currentTab.value?.sessionId ? refreshCurrentSession() : Promise.resolve()])
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', protectUnsavedRecording)
  previewMedia.removeEventListener('change', updatePreviewLayout)
  activeController?.abort()
  clearTimeout(historySearchTimer)
  clearTimeout(storageTimer)
  saveTabsToStorage()
})

function createNewTab(sessionOrData = null) {
  if (guardVoiceCapture()) return
  if (_isSending.value) return
  const tabId = generateTabId()
  const greetingMessages = [{
    role: 'assistant',
    content: NL_CREATOR.greeting,
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
    draft: '',
    mode: 'thinking',
    sessionId: sessionId,
    messages: greetingMessages,
    isLoading: false,
    isDirty: false,
    hasWorkflow: false
  }

  tabs.value.push(newTab)
  activeTabId.value = tabId
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
  if (guardVoiceCapture()) return
  if (activeTabId.value === tabId || _isSending.value) return
  activeTabId.value = tabId
  saveTabsToStorage()
  nextTick(() => {
    scrollToBottom()
    restoreActiveTabGuidance()
  })
}

/**
 * Poll NL async task until completed/failed/timeout.
 * Used by createSession fallback when backend returns processing/async.
 */
async function pollNlTaskUntilReady(sessionId, options = {}) {
  const maxAttempts = options.maxAttempts || NL_CREATOR.pollAttempts
  const intervalMs = options.intervalMs || NL_CREATOR.pollInterval
  const taskId = options.taskId
  const onProgress = options.onProgress

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    activeController?.signal.throwIfAborted()
    const statusPayload = await nlWorkflowApi.getTaskStatus(
      sessionId,
      taskId ? { task_id: taskId } : {}
    )
    const status = statusPayload.status
    if (typeof onProgress === 'function') {
      onProgress(statusPayload)
    }

    if (status === 'completed' || status === 'failed') {
      return statusPayload
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }

  return {
    status: 'timeout',
    error: '生成超时，请稍后在历史会话中查看结果',
    sessionId
  }
}

async function closeTab(tabId, discardDraft = false) {
  if (guardVoiceCapture()) return
  const tabIndex = tabs.value.findIndex(t => t.id === tabId)
  if (tabIndex === -1) return

  const tab = tabs.value[tabIndex]
  if (tab.isLoading || _isSending.value) {
    appStore.error('对话生成中，无法关闭')
    return
  }

  if ((tab.draft?.trim() || (tab.voiceClip && !tab.voiceClip.downloaded)) && !discardDraft) {
    try {
      await ElMessageBox.confirm(tab.voiceClip && !tab.voiceClip.downloaded ? VOICE_RECORDER.labels.leave : '这个标签有未发送的草稿，关闭后将移除草稿。', '关闭标签', {
        confirmButtonText: '关闭标签', cancelButtonText: '继续编辑', type: 'warning'
      })
    } catch { return }
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
  if (guardVoiceCapture()) return
  createNewTab()
  emailGuidance.value = null
  nodeGuidance.value = null
  showHistorySidebar.value = false
  loadHistory()
}

async function handleRenameTab(tab) {
  if (tab.sessionId) return renameSession({ sessionId: tab.sessionId, name: tab.title })
  try {
    const { value } = await ElMessageBox.prompt('请输入标签名称', '重命名', {
      inputValue: tab.title, inputValidator: value => Boolean(value?.trim() && value.trim().length <= NL_CREATOR.maxNameLength) || '请输入 1 到 200 个字符'
    })
    tab.title = value.trim()
    saveTabsToStorage()
  } catch { /* User dismissed the prompt. */ }
}

async function handleTabAction(command) {
  if (guardVoiceCapture()) return
  if (_isSending.value) return
  const targets = tabs.value.filter(tab => !tab.isLoading && (
    command === 'close-all' ||
    (command === 'close-others' && tab.id !== activeTabId.value) ||
    (command === 'close-saved' && tab.workflowId && !tab.isDirty)
  ))
  if (targets.some(tab => tab.draft?.trim() || (tab.voiceClip && !tab.voiceClip.downloaded))) {
    try {
      await ElMessageBox.confirm('选中的标签含有未发送草稿或未下载录音，关闭后将移除。', '关闭标签', {
        confirmButtonText: '关闭标签', cancelButtonText: '继续编辑', type: 'warning'
      })
    } catch { return }
  }
  const targetIds = new Set(targets.map(tab => tab.id))
  tabs.value = tabs.value.filter(tab => !targetIds.has(tab.id))
  if (!tabs.value.length) createNewTab()
  if (!tabs.value.some(tab => tab.id === activeTabId.value)) activeTabId.value = tabs.value[0].id
  saveTabsToStorage()
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
      content: '您好！我是 Flowly「语创」助手。\n\n请先选择输入框上方的模式：\n• **深度思考** — 与我讨论需求，不会自动生成\n• **生成工作流** — 基于对话或描述生成工作流',
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

    if (!response.messages?.length && response.description) {
      loadedMessages.push({
        role: 'user',
        content: response.description,
        timestamp: response.createdAt
      })
    }

    if (response.messages && response.messages.length > 0) {
      response.messages.forEach(msg => {
        loadedMessages.push({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
          emailGuidance: msg.emailGuidance || msg.email_guidance,
          nodeGuidance: msg.nodeGuidance || msg.node_guidance,
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
        content: '您好！我是 Flowly「语创」助手。请描述您想要创建的工作流，我将根据您的描述自动生成。',
        timestamp: new Date().toISOString()
      })
    }

    if (response.status === 'failed' && response.errorMessage) {
      loadedMessages.push({ role: 'assistant', content: nlErrorMessage(new Error(response.errorMessage)), error: true, timestamp: response.updatedAt })
    }
    tab.messages = loadedMessages
    tab.title = response.name || session.name || '未命名会话'
    tab.workflowId = response.workflowId || null
    tab.taskId = response.celeryTaskId || null
    tab.sessionStatus = response.status
    tab.hasWorkflow = false
    tab.isDirty = false

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

    if (activeTabId.value === tab.id) { restoreActiveTabGuidance(); updateWorkflowValidation(getCurrentWorkflow()) }
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
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.keyCode === 229) return
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
  if (guardVoiceCapture()) return
  const tab = currentTab.value
  if (!tab || tab.isLoading || backgroundTaskPending.value) return

  // Read the actual textarea DOM value to handle all code paths
  const ta = chatInputRef.value?.$el?.querySelector?.('textarea')
    || chatInputRef.value?.$refs?.textarea
    || document.querySelector('textarea[data-testid="chat-input"]')
  const actualValue = ta?.value?.trim() || inputMessage.value?.trim() || ''

  if (!actualValue) return
  if (!selectedModel.value) { appStore.error(NL_CREATOR.noModel); return }
  if (actualValue.length > NL_CREATOR.maxMessageLength) return
  if (_isSending.value || tab._isCreatingSession) return

  _isSending.value = true
  activeController = new AbortController()
  const userMessage = actualValue
  inputMessage.value = ''
  if (ta) ta.value = ''

  tab.messages.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date().toISOString()
  })

  followMessages.value = true
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
        if (!sendErr.fallbackAllowed) throw sendErr
        // Fallback to non-streaming
        response = await nlWorkflowApi.sendMessage(tab.sessionId, userMessage, nlPayloadWithCapabilities({
          model: selectedModel.value,
          mode: apiMode.value
        }), { signal: activeController.signal })

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
        if (!createErr.fallbackAllowed || tab.sessionId) throw createErr
        // Fallback to non-streaming
        response = await nlWorkflowApi.createSession(nlPayloadWithCapabilities({
          description: userMessage,
          name: `语创 ${Date.now()}`,
          model: selectedModel.value,
          mode: apiMode.value
        }), { signal: activeController.signal })

        tab.sessionId = response.sessionId || response.id
        tab.taskId = response.taskId || response.task_id || null
        tab.sessionStatus = response.status
        tab.title = userMessage.substring(0, 20) + (userMessage.length > 20 ? '...' : '')

        // Async path: poll until completed / failed
        if (response.status === 'processing' || response.async) {
          assistantMessage.content = '正在后台生成工作流，请稍候...'
          const polled = await pollNlTaskUntilReady(tab.sessionId, {
            taskId: response.taskId || response.task_id,
            onProgress: (statusPayload) => {
              const state = statusPayload.celeryState || statusPayload.celery_state || statusPayload.status
              assistantMessage.content = `正在后台生成工作流（${state}）...`
            }
          })
          response = { ...response, ...polled }
          tab.sessionStatus = response.status
        }

        if (response.error || response.status === 'failed') {
          const errText = response.error || response.errorMessage || response.error_message || '生成失败'
          assistantMessage.content = `抱歉，生成工作流时遇到了问题：${errText}`
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

        hasGenerationFailed.value = !!(response.error || response.status === 'failed')
      } finally {
        assistantMessage.isStreaming = false
        tab._isCreatingSession = false
      }
    }
  } catch (err) {
    // Outer catch handles any unexpected errors — must show user feedback
    const cancelled = err?.name === 'AbortError' || err?.code === 'ERR_CANCELED'
    const msg = cancelled ? NL_CREATOR.interrupted : nlErrorMessage(err)
    // Determine which message object to update (assistantMessage in else branch, continueMessage in if branch)
    const lastMsg = tab.messages.length > 0 ? tab.messages[tab.messages.length - 1] : null
    if (lastMsg) {
      lastMsg.content = [lastMsg.content, msg].filter(Boolean).join('\n\n')
      lastMsg.error = !cancelled
      lastMsg.interrupted = cancelled
      lastMsg.isStreaming = false
    }
    hasGenerationFailed.value = true
    if (!cancelled) appStore.error(msg)
  } finally {
    if (tab) tab.isLoading = false
    isStreaming.value = false
    _isSending.value = false
    activeController = null
    loadHistory()
    finishStreamState()
    saveTabsToStorage()
    scrollToBottom()
  }
}

/**
 * Stream message with real-time UI updates
 */
async function streamMessageWithUI(tab, message, output, mode) {
  const response = await nlWorkflowApi.streamMessage(tab.sessionId, message, {
    ...nlPayloadWithCapabilities({ model: selectedModel.value, mode, workflow: latestWorkflow(tab) }),
    signal: activeController.signal
  })
  return readStreamWithUI(response, tab, message, output, mode)
}

async function streamWorkflowWithUI(tab, message, output, mode) {
  const response = await nlWorkflowApi.streamWorkflow(nlPayloadWithCapabilities({
    description: message, name: message.slice(0, NL_CREATOR.titleLength), model: selectedModel.value, mode
  }), { signal: activeController.signal })
  return readStreamWithUI(response, tab, message, output, mode)
}

async function readStreamWithUI(response, tab, message, output, mode) {
  let fullContent = ''
  let workflow = null
  await consumeNlStream(response, event => {
    if (event.type === 'session') {
      tab.sessionId = event.session_id || event.sessionId
      tab.title = message.slice(0, NL_CREATOR.titleLength)
      saveTabsToStorage()
    }
    if (event.type === 'thinking') streamThinking.value += event.content || ''
    if (['progress', 'step'].includes(event.type)) applyStreamProgressEvent(event, output, fullContent, workflow)
    if (event.type === 'token') {
      fullContent = applyTokenStreamEvent(event, output, fullContent, mode)
      tokenCount.value += (event.content || '').length
      updateEstimatedTime()
    }
    if (event.type === 'intent') {
      output.intent = event.intent
      setStreamModeFromIntent(event.intent)
    }
    if (event.type === 'ready_to_generate') output.readyToGenerate = true
    if (event.workflow || event.workflow_json) {
      workflow = event.workflow || (typeof event.workflow_json === 'string' ? JSON.parse(event.workflow_json) : event.workflow_json)
      output.workflow = workflow
      tab.hasWorkflow = true
      updateWorkflowValidation(workflow)
    }
    if (event.email_guidance || workflow?._email_guidance) {
      output.emailGuidance = event.email_guidance || workflow._email_guidance
      emailGuidance.value = output.emailGuidance
    }
    if (event.node_guidance || workflow?._node_guidance) {
      output.nodeGuidance = event.node_guidance || workflow._node_guidance
      nodeGuidance.value = output.nodeGuidance
    }
    if (event.suggestions) output.suggestions = event.suggestions
    if (event.type === 'done') {
      tab.sessionStatus = 'completed'
      output.content = stripReadyMarker(event.message || fullContent) || output.content
      output.intent = event.intent || output.intent
      output.readyToGenerate = event.ready_to_generate || output.readyToGenerate
      streamProgress.value = 100
    }
  })
  return { workflow, message: output.content || fullContent, intent: output.intent, ready_to_generate: output.readyToGenerate }
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
  if (currentTab.value?.isDirty && hasWorkflow) {
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
  const estimatedCost = workflow.estimated_cost ?? workflow.estimatedCost ?? null
  
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
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value && followMessages.value) {
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
  if (_isSending.value) return
  inputMode.value = example.mode
  inputMessage.value = example.prompt
  nextTick(() => chatInputRef.value?.focus())
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

async function saveWorkflow(workflow) {
  if (_isSaving.value || _isSending.value || configSaving.value) return
  const tab = currentTab.value
  const target = workflow || latestWorkflow(tab)
  if (!target) return appStore.error('当前没有可保存的工作流')
  _isSaving.value = true
  try {
    const fingerprint = JSON.stringify(target)
    let workflowId = tab.savedFingerprint === fingerprint ? tab.workflowId : null
    if (!workflowId && tab.sessionId) {
      await nlWorkflowApi.ensureWorkspaceVersion(tab.sessionId)
      const result = await nlWorkflowApi.confirmWorkflow(tab.sessionId, target)
      workflowId = result.workflowId || result.workflow_id || result.id
    } else if (!workflowId) {
      workflowId = await saveWorkflowDirect(target)
    }
    if (!workflowId) throw new Error('未获取到工作流 ID')
    tab.isDirty = false
    tab.workflowId = workflowId
    tab.savedFingerprint = fingerprint
    saveTabsToStorage()
    showWorkflowDetail.value = false
    appStore.success('工作流已保存，可在编辑器中配置和运行')
    await router.push({ name: 'WorkflowEdit', params: { id: workflowId }, query: { fromNlSaved: '1' } })
  } catch (error) {
    appStore.error(error.message || '保存失败，请重试')
  } finally { _isSaving.value = false }
}

// ============================================
// 模型加载
// ============================================
async function loadModels(force = false) {
  if (modelsLoading.value) return
  if (!force && availableModels.value.length > 0 && !showAllModels.value) return
  modelsLoading.value = true
  try {
    const response = await nlWorkflowApi.getModels(showAllModels.value)
    availableModels.value = response.models || []
    const defaultModel = response.default ?? response.defaultModel
    modelsError.value = ''
    availableModels.value = availableModels.value.map(model => ({ ...model, modelId: model.modelId || model.model_id }))
    if (availableModels.value.some(model => model.modelId === selectedModel.value)) {
      // Preserve the user's model selection across refreshes.
    } else if (defaultModel && availableModels.value.some(model => model.modelId === defaultModel)) {
      selectedModel.value = defaultModel
    } else if (availableModels.value.length > 0) {
      const first = availableModels.value[0]
      selectedModel.value = first.modelId ?? first.model_id ?? ''
    } else {
      selectedModel.value = ''
    }

    const grouped = {}
    availableModels.value.forEach(m => {
      const provider = m.provider || 'Unknown'
      if (!grouped[provider]) grouped[provider] = []
      grouped[provider].push(m)
    })
    modelOptions.value = grouped

  } catch (err) {
    modelsError.value = '加载模型列表失败，请刷新重试'
    availableModels.value = []
    modelOptions.value = {}
    selectedModel.value = ''
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

async function loadHistory(append = false) {
  const requestId = ++historyRequestId
  historyLoading.value = true
  historyError.value = ''
  const page = append ? historyPage.value + 1 : 1
  try {
    const response = await nlWorkflowApi.getSessions({ paginated: true, page, page_size: NL_CREATOR.pageSize, search: historySearchQuery.value.trim(), status: historyStatusFilter.value })
    if (requestId !== historyRequestId) return
    const rows = (response.results || response.data || response || []).map(session => ({ ...session, sessionId: session.sessionId || session.session_id || session.id }))
    const combined = append ? [...historySessions.value, ...rows] : rows
    historySessions.value = [...new Map(combined.map(row => [row.sessionId, row])).values()]
    historyTotal.value = response.count ?? rows.length
    historyPage.value = page
    historyHasMore.value = Boolean(response.hasMore ?? response.has_more)
  } catch (error) {
    if (requestId === historyRequestId) historyError.value = error.message || '历史记录加载失败'
  } finally { if (requestId === historyRequestId) historyLoading.value = false }
}

function handleHistorySearch() {
  clearTimeout(historySearchTimer)
  historySearchTimer = setTimeout(() => loadHistory(), NL_CREATOR.debounceMs)
}

function getStatusType(status) { return NL_SESSION_STATUS[status]?.type || 'info' }
function getStatusText(status) { return NL_SESSION_STATUS[status]?.label || status }

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
const nlNodeTypes = buildNodeTypesMap()

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
    style: { stroke: 'var(--color-primary)', strokeWidth: 2 }
  }))
}

watch(
  [() => currentTab.value?.id, () => latestWorkflow(currentTab.value)],
  () => {
    syncNlPreview()
  },
  { immediate: true, deep: true }
)

function handleNlNodeClick(event) {
  selectedNode.value = getCurrentWorkflow()?.nodes.find(node => node.id === event.node.id) || null
  cancelNodeEdit()
  showNodeConfig.value = true
}

function cancelNodeEdit() {
  editingNodeConfig.value = { name: selectedNode.value?.name || '' }
  configJson.value = JSON.stringify(selectedNode.value?.config || {}, null, 2)
  configError.value = ''
  showNodeConfig.value = false
}

async function saveNodeConfig() {
  if (configSaving.value || !selectedNode.value) return
  configError.value = ''
  const tab = currentTab.value
  try {
    const config = parseNodeConfig(configJson.value)
    const name = editingNodeConfig.value.name.trim()
    if (!name || name.length > NL_CREATOR.maxNameLength) throw new Error('节点名称须为 1 到 200 个字符')
    const workflow = JSON.parse(JSON.stringify(latestWorkflow(tab)))
    const node = workflow.nodes.find(node => node.id === selectedNode.value.id)
    if (!node) throw new Error('节点已变更，请重新选择')
    node.name = name
    node.config = config
    configSaving.value = true
    if (tab.sessionId) await nlWorkflowApi.ensureWorkspaceVersion(tab.sessionId)
    const response = tab.sessionId ? await nlWorkflowApi.updateSession(tab.sessionId, { workflow_json: JSON.stringify(workflow) }) : null
    const message = [...tab.messages].reverse().find(message => message.workflow)
    message.workflow = response?.workflow || response?.workflowJson || workflow
    message.nodeGuidance = message.workflow._node_guidance || null
    message.emailGuidance = message.workflow._email_guidance || null
    restoreActiveTabGuidance()
    tab.isDirty = true
    selectedNode.value = node
    updateWorkflowValidation(workflow)
    saveTabsToStorage()
    showNodeConfig.value = false
    appStore.success(NL_CREATOR.savedConfig)
  } catch (error) { configError.value = error instanceof SyntaxError ? NL_CREATOR.configInvalid : error.message }
  finally { configSaving.value = false }
}

async function copyMessage(message) {
  try { await navigator.clipboard.writeText(message.content || ''); appStore.success(NL_CREATOR.copySuccess) }
  catch { appStore.error(NL_CREATOR.copyError) }
}

function exportConversation() {
  const tab = currentTab.value
  if (!tab) return
  const url = URL.createObjectURL(new Blob([conversationMarkdown(tab)], { type: 'text/markdown;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${tab.title.replace(/[\\/:*?"<>|]/g, '_')}.md`
  link.click()
  URL.revokeObjectURL(url)
}

function restoreLastRequest() {
  const message = [...currentTabMessages.value].reverse().find(message => message.role === 'user')
  if (message) inputMessage.value = message.content
  nextTick(() => chatInputRef.value?.focus())
}

async function refreshCurrentSession() {
  const tab = currentTab.value
  if (!tab?.sessionId || tab.isLoading || _isSending.value) return
  try {
    if (tab.taskId) await nlWorkflowApi.getTaskStatus(tab.sessionId, { task_id: tab.taskId })
    await loadSessionIntoTab(tab.id, { sessionId: tab.sessionId, name: tab.title })
  } catch (error) { appStore.error(nlErrorMessage(error)) }
}

async function retryBackgroundTask() {
  const tab = currentTab.value
  if (!tab?.sessionId || recoveringTask.value || tab.sessionStatus !== 'failed') return
  recoveringTask.value = true
  try {
    const response = await nlWorkflowApi.retryTask(tab.sessionId, { model: selectedModel.value })
    tab.taskId = response.taskId || tab.taskId
    tab.sessionStatus = response.status
    await refreshCurrentSession()
  } catch (error) { appStore.error(nlErrorMessage(error)) }
  finally { recoveringTask.value = false }
}

watch([inputMessage, inputMode], () => {
  clearTimeout(storageTimer)
  storageTimer = setTimeout(saveTabsToStorage, NL_CREATOR.debounceMs)
})
watch(activeTabId, () => {
  selectedNode.value = null
  showNodeConfig.value = false
  restoreActiveTabGuidance()
  updateWorkflowValidation(getCurrentWorkflow())
})

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
      inputValue: session.name || session.description || '',
      inputValidator: value => Boolean(value?.trim() && value.trim().length <= NL_CREATOR.maxNameLength) || '请输入 1 到 200 个字符'
    })

    if (newName?.trim()) {
      let apiSuccess = false
      try {
        await nlWorkflowApi.updateSession(sessionId, { name: newName.trim() })
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
  if (guardVoiceCapture()) return
  const sessionId = session.sessionId || session.session_id
  if (!sessionId || _isSending.value) return

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
      await closeTab(tabs.value[tabIndex].id, true)
    } else if (tabs.value.length === 0) {
      createNewTab()
    }

    await loadHistory()
    appStore.success('会话已删除')
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
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
  batchMode.value = true
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
  if (guardVoiceCapture()) return
  if (selectedSessions.value.length === 0 || _isSending.value) return

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

    const ids = [...selectedSessions.value]
    const results = await Promise.allSettled(ids.map(id => nlWorkflowApi.deleteSession(id)))
    const deleted = ids.filter((_, index) => results[index].status === 'fulfilled')
    const failed = ids.filter((_, index) => results[index].status === 'rejected')
    tabs.value = tabs.value.filter(tab => !deleted.includes(tab.sessionId))
    if (!tabs.value.length) createNewTab()
    if (!tabs.value.some(tab => tab.id === activeTabId.value)) activeTabId.value = tabs.value[0].id
    await loadHistory()
    if (deleted.length) appStore.success(`已删除 ${deleted.length} 个对话`)
    if (failed.length) appStore.error(`${failed.length} 个对话删除失败，已保留，请重试`)
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
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
@use '@/styles/workflow-domain-node.scss';

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
  min-width: 0;
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

// ============================================
// 聊天容器
// ============================================
.message {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-6;

  &-user {
    flex-direction: row-reverse;

    .message-text {
      background: var(--button-primary-bg);
      color: var(--button-primary-text);
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
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
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
  min-width: 0;
  max-width: min(80%, 72ch);
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

<style lang="scss" scoped src="./workspace.scss"></style>
