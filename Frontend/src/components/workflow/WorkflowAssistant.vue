<template>
  <Teleport to="body">
    <!-- Floating Trigger Button -->
    <Transition name="trigger-pop">
      <button
        v-if="!visible"
        class="assistant-trigger"
        :class="[themeClass, { 'is-dragging': triggerDragging }]"
        :style="triggerStyle"
        title="AI 工作流助手（可拖动）"
        @click="handleTriggerClick"
        @mousedown="startTriggerDrag"
      >
        <div class="trigger-inner">
          <div class="trigger-logo-wrap">
            <img
              :src="currentLogo"
              alt="AI"
              class="trigger-avatar"
            >
          </div>
        </div>
        <div class="trigger-ring" />
      </button>
    </Transition>

    <!-- Main Panel -->
    <Transition name="assistant-slide">
      <div
        v-if="visible"
        class="workflow-assistant"
        :class="{ 'sidebar-open': sidebarOpen }"
        :style="panelStyle"
      >
        <!-- Left Sidebar -->
        <Transition name="sidebar-slide">
          <aside
            v-if="sidebarOpen"
            class="conversation-sidebar"
          >
            <div class="sidebar-header">
              <span class="sidebar-title">会话记录</span>
              <button
                class="sidebar-close-btn"
                @click="sidebarOpen = false"
              >
                <X class="btn-icon-sm" />
              </button>
            </div>
            <div class="sidebar-search">
              <input
                v-model="historySearch"
                placeholder="搜索会话..."
                class="search-input"
              >
            </div>
            <div class="sidebar-new-btn">
              <button
                class="new-conv-btn"
                @click="handleNewConversation"
              >
                <Plus class="btn-icon-sm" />
                <span>新对话</span>
              </button>
            </div>
            <div
              class="session-list"
              :class="{ loading: historyLoading }"
            >
              <div
                v-for="session in filteredSessions"
                :key="session.session_id || session.id"
                class="session-item"
                :class="{ active: session.session_id === nlStore.currentSessionId || session.id === nlStore.currentSessionId }"
                @click="handleSwitchSession(session)"
              >
                <div class="session-item-content">
                  <span class="session-name">{{ session.name || '新对话' }}</span>
                  <span class="session-time">{{ formatSessionTime(session.updatedAt || session.updated_at || session.createdAt || session.created_at) }}</span>
                </div>
                <div class="session-actions">
                  <button
                    class="session-action-btn"
                    title="重命名"
                    @click.stop="handleRenameSession(session)"
                  >
                    <Pencil class="btn-icon-xs" />
                  </button>
                  <button
                    class="session-action-btn danger"
                    title="删除"
                    @click.stop="handleDeleteSession(session)"
                  >
                    <Trash2 class="btn-icon-xs" />
                  </button>
                </div>
              </div>
              <div
                v-if="filteredSessions.length === 0 && !historyLoading"
                class="empty-sessions"
              >
                暂无会话记录
              </div>
            </div>
          </aside>
        </Transition>

        <!-- Main Chat Area -->
        <div class="assistant-main">
          <!-- Header -->
          <div
            class="assistant-header drag-handle"
            @mousedown="startPanelDrag"
          >
            <div class="header-left">
              <button
                class="header-btn sidebar-toggle-btn"
                title="会话记录"
                @click="sidebarOpen = !sidebarOpen"
              >
                <Menu class="btn-icon-sm" />
              </button>
              <div class="header-text">
                <h4 class="header-title">
                  {{ conversationTitle }}
                </h4>
                <span
                  class="header-status"
                  :class="{ thinking: nlStore.isGenerating }"
                >
                  {{ nlStore.isGenerating ? '思考中' : '在线' }}
                </span>
              </div>
            </div>
            <div class="header-actions">
              <button
                class="header-btn"
                title="规则引擎优化（不消耗 LLM）"
                :disabled="optimizing || !props.nodes.length"
                @click="runOptimizeWorkflow"
              >
                <Sparkles class="btn-icon-sm" />
              </button>
              <button
                class="header-btn"
                title="清除对话"
                @click="handleClearChat"
              >
                <Trash2 class="btn-icon-sm" />
              </button>
              <button
                class="header-btn"
                title="最小化"
                @click="minimizeAssistant"
              >
                <Minus class="btn-icon-sm" />
              </button>
              <button
                class="header-btn"
                title="关闭"
                @click="closeAssistant"
              >
                <X class="btn-icon-sm" />
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div
            ref="messagesContainer"
            class="assistant-messages"
          >
            <!-- Welcome message -->
            <div
              v-if="messages.length === 0"
              class="welcome-state"
            >
              <div class="welcome-avatar">
                <img
                  :src="currentLogo"
                  alt="AI"
                  class="welcome-img"
                >
              </div>
              <h4 class="welcome-title">
                你好，我是工作流助手
              </h4>
              <p class="welcome-desc">
                我可以帮助你：
              </p>
              <div class="suggestion-pills">
                <button
                  v-for="suggestion in suggestions"
                  :key="suggestion.text"
                  class="suggestion-pill"
                  @click="sendSuggestion(suggestion.text)"
                >
                  <component
                    :is="suggestion.icon"
                    class="pill-icon"
                  />
                  <span>{{ suggestion.text }}</span>
                </button>
              </div>
            </div>

            <!-- Message list -->
            <div
              v-else
              class="message-list"
            >
              <div
                v-for="(msg, index) in messages"
                :key="index"
                class="message-item"
                :class="{ 'ai-message': msg.role === 'assistant', 'user-message': msg.role === 'user' }"
              >
                <!-- Avatar -->
                <div
                  v-if="msg.role === 'assistant'"
                  class="msg-avatar"
                >
                  <img
                    :src="currentLogo"
                    alt="AI"
                    class="avatar-img"
                  >
                </div>
                <div
                  v-else
                  class="msg-avatar msg-user-avatar"
                >
                  <img
                    v-if="authStore.user?.avatar"
                    :src="authStore.user.avatar"
                    :alt="authStore.user?.username"
                    class="avatar-img"
                  >
                  <span
                    v-else
                    class="avatar-initial"
                  >
                    {{ authStore.user?.username?.[0]?.toUpperCase() || 'U' }}
                  </span>
                </div>

                <!-- Content -->
                <div class="msg-content">
                  <div
                    v-if="msg.content"
                    class="msg-bubble"
                  >
                    <!-- eslint-disable vue/no-v-html -->
                    <div
                      v-if="msg.isHtml"
                      class="msg-html"
                      v-html="msg.content"
                    />
                    <!-- eslint-enable vue/no-v-html -->
                    <pre
                      v-else
                      class="msg-text"
                    >{{ msg.content }}</pre>
                  </div>

                  <!-- Code blocks -->
                  <div
                    v-if="msg.codeBlocks?.length"
                    class="code-blocks"
                  >
                    <div
                      v-for="(block, bi) in msg.codeBlocks"
                      :key="bi"
                      class="code-block"
                    >
                      <div class="code-header">
                        <span class="code-lang">{{ block.language || 'code' }}</span>
                        <button
                          class="copy-btn"
                          @click="copyCode(block.code)"
                        >
                          <Copy class="copy-icon" />
                          复制
                        </button>
                      </div>
                      <pre class="code-content"><code>{{ block.code }}</code></pre>
                    </div>
                  </div>

                  <!-- Suggestions from AI -->
                  <div
                    v-if="msg.suggestions?.length"
                    class="msg-suggestions"
                  >
                    <button
                      v-for="(sug, si) in msg.suggestions"
                      :key="si"
                      class="msg-suggestion"
                      @click="sendSuggestion(sug)"
                    >
                      {{ sug }}
                    </button>
                  </div>

                  <!-- Ready to generate -->
                  <div
                    v-if="msg.readyToGenerate"
                    class="ready-generate-bar"
                  >
                    <button
                      class="ready-generate-btn"
                      @click="triggerGenerateFromChat"
                    >
                      <Wand2 class="btn-icon-xs" />
                      现在就生成工作流
                    </button>
                  </div>

                  <!-- Optimization results -->
                  <div
                    v-if="msg.optimizationResult"
                    class="optimization-result-card"
                  >
                    <div class="optimization-result-header">
                      <Sparkles class="card-icon" />
                      <div>
                        <strong>规则引擎优化分析</strong>
                        <span class="optimization-meta">不消耗 LLM 额度</span>
                      </div>
                    </div>
                    <div
                      v-if="msg.optimizationResult.suggestions?.length === 0"
                      class="optimization-empty"
                    >
                      <CheckCircle class="empty-icon success" />
                      <span>工作流状态良好，未发现需要优化的问题</span>
                    </div>
                    <div
                      v-else
                      class="optimization-suggestions"
                    >
                      <div
                        v-for="(suggestion, si) in msg.optimizationResult.suggestions"
                        :key="si"
                        class="optimization-suggestion"
                        :class="suggestion.severity"
                      >
                        <div class="suggestion-top">
                          <el-tag
                            size="small"
                            :type="getSeverityTagType(suggestion.severity)"
                          >
                            {{ getSeverityLabel(suggestion.severity) }}
                          </el-tag>
                          <el-tag
                            size="small"
                            :type="getTypeTagType(suggestion.type)"
                          >
                            {{ getTypeLabel(suggestion.type) }}
                          </el-tag>
                        </div>
                        <h5>{{ suggestion.title }}</h5>
                        <p>{{ suggestion.description }}</p>
                        <div
                          v-if="suggestion.expectedBenefit"
                          class="benefit-tag"
                        >
                          <TrendingUp class="benefit-icon" />
                          {{ suggestion.expectedBenefit }}
                        </div>
                        <div class="suggestion-actions">
                          <button
                            v-if="suggestion.affectedNodes?.length"
                            class="opt-action-btn"
                            @click="emitHighlightNodes(suggestion.affectedNodes)"
                          >
                            <MapPin class="btn-icon-xs" /> 定位节点
                          </button>
                          <button
                            v-if="suggestion.autoApplicable"
                            class="opt-action-btn primary"
                            @click="emitApplyFix(suggestion, msg)"
                          >
                            <Sparkles class="btn-icon-xs" /> 应用修复
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Workflow update card -->
                  <div
                    v-if="msg.workflow?.nodes?.length"
                    class="workflow-update-card"
                  >
                    <div class="workflow-update-header">
                      <GitBranch class="card-icon" />
                      <div>
                        <strong>{{ msg.workflow.name || '工作流更新' }}</strong>
                        <span class="workflow-update-meta">
                          {{ msg.workflow.nodes.length }} 节点 · {{ msg.workflow.edges?.length || 0 }} 连线
                        </span>
                      </div>
                    </div>
                    <p
                      v-if="msg.workflow.description"
                      class="workflow-update-desc"
                    >
                      {{ msg.workflow.description }}
                    </p>
                    <div
                      v-if="msg.changes?.length"
                      class="workflow-changes"
                    >
                      <span class="changes-label">变更：</span>
                      <span
                        v-for="(change, ci) in msg.changes.slice(0, 4)"
                        :key="ci"
                        class="change-tag"
                      >{{ change }}</span>
                    </div>
                    <button
                      class="apply-workflow-btn"
                      @click="applyWorkflowToEditor(msg.workflow)"
                    >
                      {{ msg.autoApplied ? '已应用到画布（点击重新应用）' : '应用到画布' }}
                    </button>
                  </div>

                  <!-- Config guidance -->
                  <div
                    v-if="msg.nodeGuidance?.length || msg.emailGuidance"
                    class="config-guidance"
                  >
                    <div class="guidance-title">
                      <AlertTriangle class="guidance-icon" />
                      配置提醒
                    </div>
                    <div
                      v-if="msg.emailGuidance"
                      class="guidance-block"
                    >
                      <strong>{{ msg.emailGuidance.title || '邮件节点' }}</strong>
                      <p>{{ msg.emailGuidance.description }}</p>
                      <ul v-if="msg.emailGuidance.missing_fields?.length">
                        <li
                          v-for="field in msg.emailGuidance.missing_fields"
                          :key="field"
                        >
                          {{ field }}
                        </li>
                      </ul>
                    </div>
                    <div
                      v-for="(guide, gi) in (msg.nodeGuidance || [])"
                      :key="gi"
                      class="guidance-block"
                    >
                      <strong>{{ guide.node_name || guide.node_type }}</strong>
                      <p>{{ guide.message || guide.description }}</p>
                      <ul v-if="guide.missing_fields?.length">
                        <li
                          v-for="field in guide.missing_fields"
                          :key="field"
                        >
                          {{ field }}
                        </li>
                      </ul>
                    </div>
                  </div>

                  <!-- Loading indicator -->
                  <div
                    v-if="msg.loading"
                    class="loading-indicator"
                  >
                    <div class="loading-dots">
                      <span /><span /><span />
                    </div>
                  </div>

                  <!-- Timestamp -->
                  <span
                    v-if="msg.timestamp"
                    class="msg-time"
                  >
                    {{ formatTime(msg.timestamp) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Scroll to bottom button -->
          <Transition name="fade">
            <button
              v-if="showScrollBtn"
              class="scroll-bottom-btn"
              @click="scrollToBottom"
            >
              <ChevronDown class="btn-icon-sm" />
            </button>
          </Transition>

          <!-- Input Area -->
          <div class="assistant-input">
            <div class="mode-chips">
              <button
                v-for="chip in modeChips"
                :key="chip.value"
                class="mode-chip"
                :class="{ active: nlStore.assistantMode === chip.value }"
                :title="chip.title"
                @click="setAssistantMode(chip.value)"
              >
                <component
                  :is="chip.icon"
                  class="chip-icon"
                />
                {{ chip.label }}
              </button>
            </div>
            <div class="input-wrapper">
              <textarea
                ref="inputField"
                v-model="inputMessage"
                class="input-field"
                placeholder="描述你的需求，或问我如何构建工作流..."
                rows="1"
                @keydown.enter.exact.prevent="sendMessage"
                @keydown.enter.shift.exact="inputMessage += '\n'"
                @input="autoResize"
                @scroll="handleScroll"
              />
              <button
                class="send-btn"
                :disabled="!inputMessage.trim() || nlStore.isGenerating"
                @click="sendMessage"
              >
                <Loader2
                  v-if="nlStore.isGenerating"
                  class="send-icon spinning"
                />
                <Send
                  v-else
                  class="send-icon"
                />
              </button>
            </div>
            <div class="input-hints">
              <span class="hint">{{ modeHint }}</span>
              <span class="hint"><kbd>/optimize</kbd> 规则优化</span>
              <span class="hint"><kbd>Enter</kbd> 发送</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useNLWorkflowStore } from '@/stores/nlWorkflow'
import {
  Trash2, Minus, X, Send, Loader2, Copy,
  Lightbulb, Wand2, Puzzle, Zap, GitBranch, AlertTriangle,
  Menu, Plus, Pencil, ChevronDown, Sparkles, MapPin, TrendingUp, CheckCircle,
  LayoutGrid, MessageSquare
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { optimizeWorkflow } from '@/api/workflow'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'
import { ElMessageBox } from 'element-plus'
import { nlWorkflowApi } from '@/api/nl-workflow'
import { vueFlowToNlWorkflow } from '@/utils/workflowTransform'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  },
  workflowName: {
    type: String,
    default: '未命名工作流'
  }
})

const emit = defineEmits(['update:modelValue', 'apply-workflow', 'highlight-nodes', 'apply-fix'])

const appStore = useAppStore()
const authStore = useAuthStore()
const nlStore = useNLWorkflowStore()

// State
const visible = ref(props.modelValue)
const inputMessage = ref('')
const messagesContainer = ref(null)
const inputField = ref(null)
const sidebarOpen = ref(false)
const historySearch = ref('')
const historyLoading = ref(false)
const showScrollBtn = ref(false)
const optimizing = ref(false)
const OPTIMIZE_DIMENSIONS = ['performance', 'error_handling', 'maintainability', 'cost', 'security']

// Drag state - panel
const panelPos = ref({ x: null, y: null })
const panelDragging = ref(false)
const panelDragOffset = ref({ x: 0, y: 0 })

// Drag state - trigger
const triggerPos = ref({ x: null, y: null })
const triggerDragging = ref(false)
const triggerDidDrag = ref(false)
const triggerDragOffset = ref({ x: 0, y: 0 })
const triggerDragStart = ref({ x: 0, y: 0 })

const TRIGGER_SIZE = 48
const TRIGGER_DRAG_THRESHOLD = 5

// Computed
const isDarkTheme = computed(() => {
  const darkThemes = ['dark', 'pure-bw', 'high-contrast']
  return darkThemes.includes(appStore.theme)
})

const currentLogo = computed(() =>
  isDarkTheme.value ? logoWhite : logoBlack
)

const messages = computed(() => nlStore.messages)

const conversationTitle = computed(() => {
  const userMsg = nlStore.lastUserMessage
  if (!userMsg) return '工作流助手'
  const text = userMsg.content || ''
  return text.length > 20 ? text.slice(0, 20) + '...' : text
})

const filteredSessions = computed(() => {
  if (!historySearch.value) return nlStore.history
  const q = historySearch.value.toLowerCase()
  return nlStore.history.filter(s =>
    (s.name || '').toLowerCase().includes(q)
  )
})

const panelStyle = computed(() => {
  if (panelPos.value.x !== null) {
    return {
      right: 'auto',
      left: panelPos.value.x + 'px',
      top: panelPos.value.y + 'px',
      bottom: 'auto'
    }
  }
  return {}
})

const triggerStyle = computed(() => {
  if (triggerPos.value.x !== null) {
    return {
      right: 'auto',
      left: triggerPos.value.x + 'px',
      top: triggerPos.value.y + 'px',
      bottom: 'auto'
    }
  }
  return {}
})

const themeClass = computed(() => 'trigger-theme-' + appStore.theme)

// Suggestions for welcome screen
const suggestions = computed(() => {
  const hasCanvasWorkflow = props.nodes.length > 0
  if (hasCanvasWorkflow) {
    const hasVideoPipeline = props.nodes.some(n =>
      ['video_upload', 'subtitle_generation', 'subtitle_translate'].includes(n.type)
    )
    if (hasVideoPipeline) {
      return [
        { text: '帮我自动排布节点', icon: LayoutGrid },
        { text: '添加日语翻译处理链', icon: Puzzle },
        { text: '检查哪些节点还需要配置', icon: AlertTriangle },
        { text: '/optimize', icon: Sparkles },
      ]
    }
    return [
      { text: '帮我自动排布节点', icon: LayoutGrid },
      { text: '帮我在当前工作流中添加一个 LLM 节点', icon: Puzzle },
      { text: '检查哪些节点还需要配置', icon: AlertTriangle },
      { text: '/optimize', icon: Sparkles },
    ]
  }
  return [
    { text: '帮我设计视频多语言翻译工作流（分节点）', icon: Zap },
    { text: '创建一个客服问答机器人', icon: Puzzle },
    { text: '设计数据处理流水线', icon: Wand2 },
    { text: '如何设置条件分支', icon: Lightbulb },
  ]
})

const modeChips = computed(() => {
  const hasCanvas = props.nodes.length > 0
  const chips = [
    { value: 'chat', label: '讨论', title: '只对话，不自动改动画布', icon: MessageSquare },
    { value: 'editor', label: '排布助手', title: '理解需求并直接修改/排布画布', icon: LayoutGrid },
    { value: 'generate', label: '生成', title: '根据对话生成全新工作流', icon: Wand2 },
  ]
  if (!hasCanvas) {
    return chips.filter(c => c.value !== 'editor')
  }
  return chips
})

const modeHint = computed(() => {
  const map = {
    chat: '讨论模式：仅对话建议，不改动画布',
    editor: '排布助手：修改/排布将自动应用到画布',
    generate: '生成模式：根据描述生成工作流',
  }
  return map[nlStore.assistantMode] || map.editor
})

function setAssistantMode(mode) {
  nlStore.setAssistantMode(mode)
}

function syncDefaultAssistantMode() {
  if (props.nodes.length > 0) {
    if (nlStore.assistantMode === 'chat' || nlStore.assistantMode === 'generate') return
    nlStore.setAssistantMode('editor')
  } else if (nlStore.assistantMode === 'editor') {
    nlStore.setAssistantMode('chat')
  }
}

function buildEditorWorkflowContext() {
  if (!props.nodes.length) return null
  return vueFlowToNlWorkflow(props.nodes, props.edges, {
    name: props.workflowName
  })
}

async function triggerGenerateFromChat() {
  nlStore.setAssistantMode('generate')
  inputMessage.value = '现在就生成工作流'
  await sendMessage()
}

function applyWorkflowToEditor(workflow) {
  if (!workflow?.nodes?.length) return
  emit('apply-workflow', workflow)
  nlStore.pendingAutoApply = false
}

// Sync with parent
watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (val) {
    syncDefaultAssistantMode()
    nextTick(() => {
      inputField.value?.focus()
      scrollToBottom()
    })
    nlStore.loadHistory()
    nlStore.loadModels()
  }
})

watch(
  () => props.nodes.length,
  (len) => {
    if (len > 0) {
      syncDefaultAssistantMode()
    }
  }
)

watch(
  () => nlStore.pendingAutoApply,
  (pending) => {
    if (!pending || !visible.value) return
    const workflow = nlStore.generatedWorkflow
    if (workflow?.nodes?.length) {
      applyWorkflowToEditor(workflow)
      appStore.success('排布助手已自动应用到画布')
    }
    nlStore.pendingAutoApply = false
  }
)

watch(
  () => nlStore.generatedWorkflow,
  (workflow) => {
    if (!visible.value || !workflow?.nodes?.length) return
    const lastAssistant = [...nlStore.messages].reverse().find(m => m.role === 'assistant')
    if (lastAssistant && !lastAssistant.workflow) {
      lastAssistant.workflow = workflow
    }
  }
)

// ==================== Drag Logic ====================

function startPanelDrag(e) {
  if (e.target.closest('.header-btn') || e.target.closest('.header-actions')) return
  panelDragging.value = true
  // Get absolute screen position of panel (resolves right/bottom defaults)
  const rect = getPanelScreenRect()
  panelDragOffset.value = {
    x: e.clientX - rect.x,
    y: e.clientY - rect.y
  }
  document.addEventListener('mousemove', onPanelDrag)
  document.addEventListener('mouseup', stopPanelDrag)
}

function onPanelDrag(e) {
  if (!panelDragging.value) return
  let x = e.clientX - panelDragOffset.value.x
  let y = e.clientY - panelDragOffset.value.y
  const clamped = clampPosition(x, y, 380, 560)
  panelPos.value = clamped
}

function stopPanelDrag() {
  if (panelDragging.value) {
    panelDragging.value = false
    document.removeEventListener('mousemove', onPanelDrag)
    document.removeEventListener('mouseup', stopPanelDrag)
    const rect = getPanelScreenRect()
    const snapped = snapToEdge(rect.x, rect.y, 380, 560)
    panelPos.value = snapped
    savePanelPos()
  }
}

function startTriggerDrag(e) {
  if (e.button !== 0) return

  triggerDidDrag.value = false
  triggerDragging.value = true
  triggerDragStart.value = { x: e.clientX, y: e.clientY }

  const el = e.currentTarget
  const rect = el.getBoundingClientRect()

  if (triggerPos.value.x === null || triggerPos.value.y === null) {
    triggerPos.value = { x: rect.left, y: rect.top }
  }

  triggerDragOffset.value = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
  }

  document.addEventListener('mousemove', onTriggerDrag)
  document.addEventListener('mouseup', stopTriggerDrag)
}

function onTriggerDrag(e) {
  if (!triggerDragging.value) return

  const dx = e.clientX - triggerDragStart.value.x
  const dy = e.clientY - triggerDragStart.value.y
  if (Math.abs(dx) > TRIGGER_DRAG_THRESHOLD || Math.abs(dy) > TRIGGER_DRAG_THRESHOLD) {
    triggerDidDrag.value = true
  }

  const x = e.clientX - triggerDragOffset.value.x
  const y = e.clientY - triggerDragOffset.value.y
  triggerPos.value = clampPosition(x, y, TRIGGER_SIZE, TRIGGER_SIZE)
}

function stopTriggerDrag() {
  if (!triggerDragging.value) return

  triggerDragging.value = false
  document.removeEventListener('mousemove', onTriggerDrag)
  document.removeEventListener('mouseup', stopTriggerDrag)
  saveTriggerPos()
}

function handleTriggerClick(e) {
  if (triggerDidDrag.value) {
    e.preventDefault()
    e.stopPropagation()
    triggerDidDrag.value = false
    return
  }
  openAssistant()
}

function getPanelScreenRect() {
  const el = document.querySelector('.workflow-assistant')
  if (!el) return { x: 0, y: 0, width: 380, height: 560 }
  const rect = el.getBoundingClientRect()
  return { x: rect.left, y: rect.top, width: rect.width, height: rect.height }
}

function clampPosition(x, y, width, height) {
  return {
    x: Math.max(0, Math.min(x, window.innerWidth - width)),
    y: Math.max(0, Math.min(y, window.innerHeight - height))
  }
}

function snapToEdge(x, y, width, height) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const edgeMargin = 24
  const snapZone = 80
  const centerZone = 120

  const centerX = x + width / 2
  const centerY = y + height / 2
  const distLeft = centerX
  const distRight = vw - centerX
  const distTop = centerY
  const distBottom = vh - centerY
  const minDistLR = Math.min(distLeft, distRight)
  const minDistTB = Math.min(distTop, distBottom)
  const minDistAll = Math.min(minDistLR, minDistTB)

  if (minDistAll < snapZone) {
    if (distLeft <= distRight && distLeft <= distTop && distLeft <= distBottom) {
      return { x: edgeMargin, y: Math.max(edgeMargin, Math.min(y, vh - height - edgeMargin)) }
    }
    if (distRight <= distTop && distRight <= distBottom) {
      return { x: vw - width - edgeMargin, y: Math.max(edgeMargin, Math.min(y, vh - height - edgeMargin)) }
    }
    if (distTop <= distBottom) {
      return { x: Math.max(edgeMargin, Math.min(x, vw - width - edgeMargin)), y: edgeMargin }
    }
    return { x: Math.max(edgeMargin, Math.min(x, vw - width - edgeMargin)), y: vh - height - edgeMargin }
  }

  if (minDistLR > centerZone && minDistTB > centerZone) {
    return { x: (vw - width) / 2, y: (vh - height) / 2 }
  }

  return { x, y }
}

function savePanelPos() {
  localStorage.setItem('assistant-panel-pos', JSON.stringify(panelPos.value))
}

function saveTriggerPos() {
  localStorage.setItem('assistant-trigger-pos', JSON.stringify(triggerPos.value))
}

function loadPositions() {
  try {
    const p = localStorage.getItem('assistant-panel-pos')
    if (p) panelPos.value = JSON.parse(p)
    const t = localStorage.getItem('assistant-trigger-pos')
    if (t) triggerPos.value = JSON.parse(t)
  } catch {
    // ignore invalid saved panel/trigger position JSON
  }
}

// ==================== Panel Controls ====================

function openAssistant() {
  visible.value = true
  nlStore.loadHistory()
  nlStore.loadModels()
}

function closeAssistant() {
  visible.value = false
}

function minimizeAssistant() {
  visible.value = false
}

async function handleClearChat() {
  try {
    await ElMessageBox.confirm('确定要清除当前对话吗？', '清除对话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    nlStore.resetSession()
  } catch {
    // user dismissed clear-chat confirm dialog
  }
}

// ==================== Conversation Management ====================

async function handleNewConversation() {
  nlStore.resetSession()
  sidebarOpen.value = false
}

async function handleSwitchSession(session) {
  const sid = session.session_id || session.id
  nlStore.currentSessionId = sid
  nlStore.messages = []
  nlStore.generatedWorkflow = null
  nlStore.generationError = null
  nlStore.isGenerating = false
  nlStore.isStreaming = false

  try {
    const response = await nlWorkflowApi.getSession(sid)
    if (response && response.messages) {
      nlStore.messages = response.messages.map(m => ({
        ...m,
        timestamp: m.timestamp || Date.now()
      }))
    }
  } catch {
    // session history unavailable; continue with empty messages
  }
  sidebarOpen.value = false
  nextTick(() => scrollToBottom())
}

async function handleRenameSession(session) {
  const sid = session.session_id || session.id
  try {
    const newName = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: session.name || ''
    })
    await nlWorkflowApi.updateSession(sid, { name: newName })
    await nlStore.loadHistory()
  } catch {
    // user dismissed rename prompt or rename failed
  }
}

async function handleDeleteSession(session) {
  const sid = session.session_id || session.id
  try {
    await ElMessageBox.confirm('确定要删除这个会话吗？此操作不可恢复。', '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await nlStore.deleteSession(sid)
    if (nlStore.currentSessionId === sid) {
      nlStore.resetSession()
    }
  } catch {
    // user dismissed delete confirm dialog
  }
}

// ==================== Message Handling ====================

async function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text || nlStore.isGenerating || optimizing.value) return

  if (text === '/optimize' || text.startsWith('/optimize ')) {
    inputMessage.value = ''
    nextTick(() => {
      if (inputField.value) inputField.value.style.height = 'auto'
    })
    await runOptimizeWorkflow()
    return
  }

  inputMessage.value = ''
  nextTick(() => {
    if (inputField.value) {
      inputField.value.style.height = 'auto'
    }
  })

  if (!nlStore.selectedModel && nlStore.models.length === 0) {
    nlStore.loadModels()
  }

  const currentWorkflow = buildEditorWorkflowContext()

  try {
    const mode = nlStore.assistantMode

    if (currentWorkflow && mode === 'editor') {
      nlStore.addUserMessage(text)
      await nlStore.applyEditorAction(text, { currentWorkflow, mode })
    } else if (!nlStore.currentSessionId) {
      nlStore.clearMessages()
      nlStore.addUserMessage(text)
      await nlStore.streamWorkflow(text, `Editor Assistant ${Date.now()}`, { currentWorkflow, mode })
    } else {
      nlStore.addUserMessage(text)
      await nlStore.streamSendMessage(text, { currentWorkflow, mode })
    }
  } catch (err) {
    nlStore.updateLastAssistantMessage('抱歉，处理请求时遇到了问题。请稍后重试。', { error: true })
  }

  nextTick(() => scrollToBottom())
}

async function sendSuggestion(text) {
  if (text === '/optimize') {
    await runOptimizeWorkflow()
    return
  }
  inputMessage.value = text
  await sendMessage()
}

function buildOptimizerPayload() {
  return {
    nodes: props.nodes.map(n => ({
      id: n.id,
      type: n.type,
      label: n.data?.label,
      config: n.data?.config
    })),
    edges: props.edges,
    dimensions: OPTIMIZE_DIMENSIONS
  }
}

async function runOptimizeWorkflow() {
  if (!props.nodes.length) {
    appStore.warning('画布为空，无法优化')
    return
  }
  if (optimizing.value) return

  optimizing.value = true
  nlStore.addUserMessage('/optimize')
  const loadingMsg = {
    role: 'assistant',
    content: '正在使用规则引擎分析当前工作流…',
    loading: true,
    timestamp: Date.now()
  }
  nlStore.messages.push(loadingMsg)

  try {
    const result = await optimizeWorkflow(buildOptimizerPayload())
    const suggestions = result?.suggestions || result?.data?.suggestions || []
    const idx = nlStore.messages.indexOf(loadingMsg)
    const assistantMsg = {
      role: 'assistant',
      content: suggestions.length
        ? `分析完成，发现 ${suggestions.length} 条优化建议（规则引擎，不消耗 LLM）。`
        : '分析完成，工作流状态良好。',
      optimizationResult: { suggestions },
      timestamp: Date.now()
    }
    if (idx >= 0) {
      nlStore.messages.splice(idx, 1, assistantMsg)
    } else {
      nlStore.messages.push(assistantMsg)
    }
  } catch (err) {
    const idx = nlStore.messages.indexOf(loadingMsg)
    const errorMsg = {
      role: 'assistant',
      content: `优化分析失败：${err.message || '未知错误'}`,
      timestamp: Date.now(),
      error: true
    }
    if (idx >= 0) nlStore.messages.splice(idx, 1, errorMsg)
    ElMessage.error(errorMsg.content)
  } finally {
    optimizing.value = false
    nextTick(() => scrollToBottom())
  }
}

function emitHighlightNodes(nodeIds) {
  emit('highlight-nodes', nodeIds)
}

function emitApplyFix(suggestion, msg) {
  emit('apply-fix', suggestion)
  if (msg?.optimizationResult?.suggestions) {
    msg.optimizationResult.suggestions = msg.optimizationResult.suggestions.filter(s => s !== suggestion)
  }
  appStore.success('已应用优化建议')
}

function getSeverityTagType(severity) {
  return { critical: 'danger', warning: 'warning', info: 'info' }[severity] || 'info'
}

function getSeverityLabel(severity) {
  return { critical: '严重', warning: '警告', info: '建议' }[severity] || severity
}

function getTypeTagType(type) {
  return { performance: 'warning', error_handling: 'danger', maintainability: '', cost: 'success', security: 'info' }[type] || ''
}

function getTypeLabel(type) {
  return {
    performance: '性能',
    error_handling: '错误处理',
    maintainability: '可维护性',
    cost: '成本',
    security: '安全'
  }[type] || type
}

// ==================== Scroll ====================

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function handleScroll() {
  if (!messagesContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value
  showScrollBtn.value = scrollHeight - scrollTop - clientHeight > 100
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function copyCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    appStore.success('代码已复制')
  }).catch(() => {
    appStore.error('复制失败')
  })
}

function formatTime(timestamp) {
  const d = new Date(timestamp)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function formatSessionTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  return d.toLocaleDateString('zh-CN')
}

// ==================== Keyboard ====================

function handleKeyDown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    openAssistant()
  }
}

onMounted(() => {
  loadPositions()
  syncDefaultAssistantMode()
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('mousemove', onTriggerDrag)
  document.removeEventListener('mouseup', stopTriggerDrag)
})
</script>

<style lang="scss" scoped>
// ==================== Layout ====================
.workflow-assistant {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  width: 380px;
  max-height: 560px;
  display: flex;
  flex-direction: row;
  background: var(--assistant-bg);
  border: 1px solid var(--assistant-border);
  border-radius: 20px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;

  &.sidebar-open {
    width: 600px;
  }
}

.assistant-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

// ==================== Sidebar ====================
.conversation-sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--assistant-bg-subtle);
  border-right: 1px solid var(--assistant-border-subtle);
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 8px;
  border-bottom: 1px solid var(--assistant-border-subtle);
}

.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--assistant-text);
  letter-spacing: 0.02em;
}

.sidebar-close-btn,
.session-action-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: var(--assistant-text-secondary);
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--assistant-text);
  }

  &.danger:hover {
    background: var(--error-bg);
    color: var(--error);
  }
}

.sidebar-search {
  padding: 8px 12px;
}

.search-input {
  width: 100%;
  padding: 6px 10px;
  background: var(--surface-muted);
  border: 1px solid var(--assistant-border-subtle);
  border-radius: 8px;
  color: var(--assistant-text);
  font-size: 11px;
  outline: none;
  box-sizing: border-box;
  transition: all 0.2s ease;

  &::placeholder { color: var(--assistant-text-tertiary); }

  &:focus {
    border-color: var(--assistant-accent-border);
    background: var(--assistant-bg-focus);
  }
}

.sidebar-new-btn {
  padding: 0 12px 8px;
}

.new-conv-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: var(--assistant-accent-bg);
  border: 1px solid var(--assistant-accent-border);
  border-radius: 8px;
  cursor: pointer;
  color: var(--assistant-accent-text);
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;

  &:hover {
    background: var(--color-primary-20);
    border-color: var(--color-primary-50);
  }
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px;

  &::-webkit-scrollbar { width: 3px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 2px; }

  &.loading {
    opacity: 0.5;
    pointer-events: none;
  }
}

.session-item {
  display: flex;
  align-items: center;
  padding: 8px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  gap: 4px;

  &:hover {
    background: var(--bg-hover);
    .session-actions { opacity: 1; }
  }

  &.active {
    background: var(--assistant-accent-bg);
    border: 1px solid var(--assistant-accent-border);
    .session-name { color: var(--assistant-accent-text); }
  }
}

.session-item-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-name {
  font-size: 11px;
  font-weight: 500;
  color: var(--assistant-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 9px;
  color: var(--assistant-text-tertiary);
}

.session-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.session-action-btn {
  width: 20px;
  height: 20px;

  .btn-icon-xs { width: 10px; height: 10px; }
}

.empty-sessions {
  text-align: center;
  padding: 20px 10px;
  font-size: 11px;
  color: var(--assistant-text-tertiary);
}

// Sidebar transitions
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  width: 0 !important;
  opacity: 0;
}

// ==================== Header ====================
.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: linear-gradient(135deg, var(--color-primary-10) 0%, var(--color-primary-05) 100%);
  border-bottom: 1px solid var(--assistant-border-subtle);
  flex-shrink: 0;
  cursor: grab;
  user-select: none;

  &:active { cursor: grabbing; }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar-toggle-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-muted);
  border: 1px solid var(--assistant-border-subtle);
  border-radius: 8px;
  cursor: pointer;
  color: var(--assistant-text-secondary);
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--assistant-text);
  }
}

.header-text {
  min-width: 0;

  .header-title {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
    color: var(--assistant-text);
    letter-spacing: 0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 140px;
  }

  .header-status {
    font-size: 10px;
    color: var(--success);

    &.thinking {
      color: var(--warning);
    }
  }
}

.header-actions {
  display: flex;
  gap: 4px;
}

.header-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-muted);
  border: 1px solid var(--assistant-border-subtle);
  border-radius: 8px;
  cursor: pointer;
  color: var(--assistant-text-secondary);
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--assistant-text);
  }
}

.btn-icon-sm { width: 14px; height: 14px; }
.btn-icon-xs { width: 10px; height: 10px; }

// ==================== Messages ====================
.assistant-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 4px; }
}

.scroll-bottom-btn {
  position: absolute;
  bottom: 80px;
  right: 16px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--assistant-accent-bg);
  border: 1px solid var(--assistant-accent-border);
  border-radius: 50%;
  cursor: pointer;
  color: var(--assistant-accent-text);
  box-shadow: var(--assistant-accent-shadow);
  z-index: 2;
  transition: all 0.2s ease;

  &:hover {
    transform: scale(1.1);
  }
}

// Welcome state
.welcome-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px 0;

  .welcome-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    overflow: hidden;
    border: 2px solid var(--assistant-border);
    margin-bottom: 14px;
    box-shadow: var(--shadow-md);
  }

  .welcome-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .welcome-title {
    margin: 0 0 8px;
    font-size: 15px;
    font-weight: 700;
    color: var(--assistant-text);
  }

  .welcome-desc {
    margin: 0 0 14px;
    font-size: 11px;
    color: var(--assistant-text-secondary);
  }
}

.suggestion-pills {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.suggestion-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--surface-muted);
  border: 1px solid var(--assistant-border-subtle);
  border-radius: 10px;
  cursor: pointer;
  color: var(--assistant-text);
  font-size: 12px;
  font-weight: 500;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);

  &:hover {
    background: var(--assistant-accent-bg);
    border-color: var(--assistant-accent-border);
    transform: translateX(4px);
  }

  .pill-icon {
    width: 14px;
    height: 14px;
    color: var(--assistant-accent-text);
    flex-shrink: 0;
  }
}

// Message items
.message-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.user-message {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  border: 1px solid var(--assistant-border-subtle);
  flex-shrink: 0;

  // 修复：原写法 .msg-avatar .msg-user-avatar 为后代选择器，永远不匹配同一元素
  &.msg-user-avatar {
    background-color: var(--assistant-bg-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;

    .avatar-img {
      border-radius: 50%;
      object-fit: contain;
      max-width: 70%;
      max-height: 70%;
    }

    .avatar-initial {
      font-size: 12px;
      font-weight: 700;
      color: var(--assistant-text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  max-width: 70%;
  max-height: 70%;
}

.msg-content {
  flex: 1;
  min-width: 0;
  max-width: 85%;
}

.user-message .msg-content {
  align-items: flex-end;
}

.msg-bubble {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-word;

  .ai-message & {
    background: var(--surface-muted);
    border: 1px solid var(--assistant-border-subtle);
    border-bottom-left-radius: 4px;
    color: var(--assistant-text);
  }

  .user-message & {
    background: var(--assistant-user-bubble-bg);
    border-bottom-right-radius: 4px;
    color: var(--assistant-user-bubble-text);
  }
}

.msg-text {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
}

.msg-html {
  :deep(p) { margin: 0 0 8px; &:last-child { margin: 0; } }
  :deep(code) {
    background: var(--surface-strong);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
  }
}

// Code blocks
.code-blocks {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.code-block {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 10px;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);

  .code-lang {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--code-muted);
  }
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--surface-muted);
  border: 1px solid var(--assistant-border-subtle);
  border-radius: 4px;
  cursor: pointer;
  color: var(--assistant-text-secondary);
  font-size: 10px;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--assistant-text);
  }

  .copy-icon { width: 10px; height: 10px; }
}

.code-content {
  margin: 0;
  padding: 10px 12px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--code-text);
  overflow-x: auto;
  line-height: 1.5;

  &::-webkit-scrollbar { height: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 2px; }
}

// Suggestions in messages
.msg-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.msg-suggestion {
  padding: 5px 10px;
  background: var(--assistant-accent-bg);
  border: 1px solid var(--assistant-accent-border);
  border-radius: 20px;
  cursor: pointer;
  color: var(--assistant-accent-text);
  font-size: 11px;
  font-weight: 500;
  transition: all 0.2s ease;

  &:hover {
    background: var(--color-primary-20);
    border-color: var(--color-primary-50);
  }
}

.optimization-result-card {
  margin-top: 10px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--assistant-border-subtle);
  background: var(--surface-muted);
}

.optimization-result-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;

  .card-icon {
    width: 16px;
    height: 16px;
    margin-top: 2px;
    color: var(--assistant-accent-text);
  }
}

.optimization-meta {
  display: block;
  font-size: 10px;
  color: var(--assistant-text-secondary);
  margin-top: 2px;
}

.optimization-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--success);

  .empty-icon {
    width: 16px;
    height: 16px;
  }
}

.optimization-suggestions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.optimization-suggestion {
  padding: 10px;
  border-radius: 10px;
  border-left: 3px solid var(--assistant-border);
  background: var(--assistant-bg);

  &.critical { border-left-color: var(--error); }
  &.warning { border-left-color: var(--warning); }
  &.info { border-left-color: var(--color-primary); }

  h5 {
    margin: 6px 0 4px;
    font-size: 12px;
  }

  p {
    margin: 0 0 8px;
    font-size: 11px;
    color: var(--assistant-text-secondary);
    line-height: 1.5;
  }
}

.suggestion-top {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.benefit-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-radius: 12px;
  font-size: 10px;
  margin-bottom: 8px;

  .benefit-icon {
    width: 10px;
    height: 10px;
  }
}

.suggestion-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.opt-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid var(--assistant-border-subtle);
  background: var(--surface-muted);
  color: var(--assistant-text);
  font-size: 10px;
  cursor: pointer;

  &.primary {
    background: var(--assistant-accent-bg);
    border-color: var(--assistant-accent-border);
    color: var(--assistant-accent-text);
  }
}

.workflow-update-card {
  margin-top: 10px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--assistant-accent-border);
  background: var(--assistant-accent-bg);
}

.workflow-update-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;

  .card-icon {
    width: 16px;
    height: 16px;
    margin-top: 2px;
    color: var(--assistant-accent-text);
  }
}

.workflow-update-meta {
  display: block;
  font-size: 11px;
  color: var(--assistant-text-secondary);
  margin-top: 2px;
}

.workflow-update-desc {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--assistant-text-secondary);
  line-height: 1.5;
}

.workflow-changes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  align-items: center;
}

.changes-label {
  font-size: 11px;
  color: var(--assistant-text-secondary);
}

.change-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--assistant-text-secondary);
}

.apply-workflow-btn {
  margin-top: 10px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;

  &:hover {
    opacity: 0.92;
  }
}

.config-guidance {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(245, 158, 11, 0.35);
  background: rgba(245, 158, 11, 0.08);
}

.guidance-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.guidance-icon {
  width: 14px;
  height: 14px;
  color: #f59e0b;
}

.guidance-block {
  font-size: 11px;
  line-height: 1.5;
  color: var(--assistant-text-secondary);

  & + & {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid rgba(245, 158, 11, 0.15);
  }

  ul {
    margin: 4px 0 0;
    padding-left: 16px;
  }
}

// Loading
.loading-indicator { padding: 8px 0; }

.loading-dots {
  display: flex;
  gap: 4px;
  align-items: center;

  span {
    width: 6px;
    height: 6px;
    background: var(--assistant-text-secondary);
    border-radius: 50%;
    animation: dot-bounce 1.4s infinite ease-in-out;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.msg-time {
  display: block;
  font-size: 9px;
  color: var(--assistant-text-tertiary);
  margin-top: 4px;
}

// ==================== Input ====================
.assistant-input {
  padding: 12px 14px 10px;
  border-top: 1px solid var(--assistant-border-subtle);
  background: var(--assistant-bg-subtle);
  flex-shrink: 0;
}

.mode-chips {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.mode-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--assistant-border-subtle);
  background: var(--surface-muted);
  color: var(--assistant-text-secondary);
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  .chip-icon {
    width: 11px;
    height: 11px;
  }

  &.active {
    background: var(--assistant-accent-bg);
    border-color: var(--assistant-accent-border);
    color: var(--assistant-accent-text);
  }
}

.ready-generate-bar {
  margin-top: 8px;
}

.ready-generate-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--surface-muted);
  border: 1px solid var(--assistant-border);
  border-radius: 14px;
  padding: 6px 6px 6px 14px;
  transition: all 0.2s ease;

  &:focus-within {
    border-color: var(--assistant-accent-border);
    background: var(--assistant-bg-focus);
    box-shadow: 0 0 0 3px var(--color-primary-10);
  }
}

.input-field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--assistant-text);
  font-size: 12px;
  line-height: 1.5;
  resize: none;
  min-height: 24px;
  max-height: 120px;
  font-family: inherit;

  &::placeholder { color: var(--assistant-text-tertiary); }
}

.send-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  color: var(--text-inverse);
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow: var(--assistant-accent-shadow);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .send-icon {
    width: 14px;
    height: 14px;

    &.spinning { animation: spin 1s linear infinite; }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.input-hints {
  display: flex;
  gap: 12px;
  padding: 4px 2px 0;

  .hint {
    font-size: 10px;
    color: var(--assistant-text-tertiary);

    kbd {
      background: var(--surface-muted);
      border: 1px solid var(--assistant-border-subtle);
      border-radius: 3px;
      padding: 0 4px;
      font-size: 9px;
      font-family: inherit;
    }
  }
}

// ==================== Floating Trigger ====================
.assistant-trigger {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9998;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  border: none;
  border-radius: 50%;
  cursor: grab;
  box-shadow: var(--assistant-accent-shadow);
  transition: filter 0.2s ease, box-shadow 0.2s ease;
  user-select: none;
  touch-action: none;

  &.is-dragging {
    cursor: grabbing;
    transition: none;
    box-shadow: var(--assistant-accent-shadow-hover);
  }

  &:hover:not(.is-dragging) {
    filter: brightness(1.15);
    box-shadow: var(--assistant-accent-shadow-hover);
  }

  &:active:not(.is-dragging) {
    filter: brightness(0.9);
  }

  .trigger-inner {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .trigger-logo-wrap {
    background: var(--assistant-bg);
    border-radius: 50%;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .trigger-avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: contain;
    max-width: 70%;
    max-height: 70%;
  }

  .trigger-ring {
    position: absolute;
    inset: -4px;
    border: 2px solid var(--assistant-accent-border);
    border-radius: 50%;
    animation: ring-pulse 2s infinite;
    pointer-events: none;
  }
}

@keyframes ring-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.1); }
}

// ==================== Transitions ====================
.assistant-slide-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.assistant-slide-leave-active {
  transition: all 0.25s ease-in;
}
.assistant-slide-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.assistant-slide-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.95);
}

.trigger-pop-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.trigger-pop-leave-active {
  transition: all 0.2s ease-in;
}
.trigger-pop-enter-from {
  opacity: 0;
  transform: scale(0) rotate(-180deg);
}
.trigger-pop-leave-to {
  opacity: 0;
  transform: scale(0);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

// ==================== Theme Variables ====================
// 组件局部变量统一引用全局主题变量（themes.scss），四个主题自动适配，
// 无需再按主题重复定义色块。面板与悬浮按钮是两个独立根节点，需同时声明。
.workflow-assistant,
.assistant-trigger {
  --assistant-bg: var(--bg-secondary);
  --assistant-bg-subtle: var(--bg-tertiary);
  --assistant-bg-focus: var(--surface-strong);
  --assistant-border: var(--border-secondary);
  --assistant-border-subtle: var(--border-primary);
  --assistant-text: var(--text-primary);
  --assistant-text-secondary: var(--text-secondary);
  --assistant-text-tertiary: var(--text-tertiary);
  --assistant-accent-bg: var(--color-primary-10);
  --assistant-accent-border: var(--color-primary-30);
  --assistant-accent-text: var(--color-primary);
  --assistant-accent-shadow: 0 4px 12px var(--color-primary-30);
  --assistant-accent-shadow-hover: 0 6px 20px var(--color-primary-50);
  --assistant-user-bubble-bg: var(--color-primary-10);
  --assistant-user-bubble-text: var(--color-primary);
}

</style>

