<template>
  <Teleport to="body">
    <!-- Floating Trigger Button -->
    <Transition name="trigger-pop">
      <button
        v-if="!visible"
        class="assistant-trigger"
        :class="themeClass"
        :style="triggerStyle"
        title="AI 工作流助手"
        @click="openAssistant"
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
                  <span class="session-time">{{ formatSessionTime(session.updated_at || session.created_at) }}</span>
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
                    <div
                      v-if="msg.isHtml"
                      class="msg-html"
                      v-html="msg.content"
                    />
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
              <span class="hint"><kbd>Enter</kbd> 发送</span>
              <span class="hint"><kbd>Shift+Enter</kbd> 换行</span>
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
  Sparkles, Trash2, Minus, X, Send, Loader2, Copy,
  Lightbulb, Wand2, Puzzle, FileText, Zap,
  Menu, Plus, Pencil, ChevronDown
} from 'lucide-vue-next'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'
import { ElMessageBox } from 'element-plus'
import { nlWorkflowApi } from '@/api/nl-workflow'

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
  }
})

const emit = defineEmits(['update:modelValue'])

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

// Drag state - panel
const panelPos = ref({ x: null, y: null })
const panelDragging = ref(false)
const panelDragOffset = ref({ x: 0, y: 0 })

// Drag state - trigger
const triggerPos = ref({ x: null, y: null })
const triggerDragging = ref(false)
const triggerDragOffset = ref({ x: 0, y: 0 })

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
const suggestions = [
  { text: '帮我设计一个翻译工作流', icon: Zap },
  { text: '添加一个LLM节点', icon: Puzzle },
  { text: '优化现有的工作流', icon: Wand2 },
  { text: '如何设置条件分支', icon: Lightbulb },
]

// Sync with parent
watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (val) {
    nextTick(() => {
      inputField.value?.focus()
      scrollToBottom()
    })
    nlStore.loadHistory()
    nlStore.loadModels()
  }
})

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
  if (e.target.closest('button') && !e.target.closest('.trigger-ring')) return
  triggerDragging.value = true
  const el = e.currentTarget
  const rect = el.getBoundingClientRect()
  triggerDragOffset.value = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
  document.addEventListener('mousemove', onTriggerDrag)
  document.addEventListener('mouseup', stopTriggerDrag)
}

function onTriggerDrag(e) {
  if (!triggerDragging.value) return
  let x = e.clientX - triggerDragOffset.value.x
  let y = e.clientY - triggerDragOffset.value.y
  const clamped = clampPosition(x, y, 48, 48)
  triggerPos.value = clamped
}

function stopTriggerDrag() {
  if (triggerDragging.value) {
    triggerDragging.value = false
    document.removeEventListener('mousemove', onTriggerDrag)
    document.removeEventListener('mouseup', stopTriggerDrag)
    const el = document.querySelector('.assistant-trigger')
    if (el) {
      const rect = el.getBoundingClientRect()
      const snapped = snapToEdge(rect.left, rect.top, 48, 48)
      triggerPos.value = snapped
    }
    saveTriggerPos()
  }
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
  } catch {}
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
  } catch {}
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
  } catch {}
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
  } catch {}
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
  } catch {}
}

// ==================== Message Handling ====================

async function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text || nlStore.isGenerating) return

  inputMessage.value = ''
  nextTick(() => {
    if (inputField.value) {
      inputField.value.style.height = 'auto'
    }
  })

  // Ensure model is loaded (no-op if already loaded)
  if (!nlStore.selectedModel && nlStore.models.length === 0) {
    nlStore.loadModels()
  }

  try {
    if (!nlStore.currentSessionId) {
      nlStore.clearMessages()
      nlStore.addUserMessage(text)
      await nlStore.streamWorkflow(text)
    } else {
      nlStore.addUserMessage(text)
      await nlStore.streamSendMessage(text)
    }
  } catch (err) {
    nlStore.updateLastAssistantMessage('抱歉，处理请求时遇到了问题。请稍后重试。', { error: true })
  }

  nextTick(() => scrollToBottom())
}

async function sendSuggestion(text) {
  inputMessage.value = text
  await sendMessage()
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
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

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
  background: var(--assistant-bg, #1a1a2e);
  border: 1px solid var(--assistant-border, rgba(255, 255, 255, 0.1));
  border-radius: 20px;
  box-shadow:
    0 25px 80px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(255, 255, 255, 0.05) inset;
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
  background: rgba(0, 0, 0, 0.2);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--assistant-text, #e2e8f0);
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
  color: rgba(255, 255, 255, 0.4);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
  }

  &.danger:hover {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }
}

.sidebar-search {
  padding: 8px 12px;
}

.search-input {
  width: 100%;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: var(--assistant-text, #e2e8f0);
  font-size: 11px;
  outline: none;
  box-sizing: border-box;

  &::placeholder { color: rgba(255, 255, 255, 0.3); }

  &:focus {
    border-color: rgba(59, 130, 246, 0.4);
    background: rgba(255, 255, 255, 0.07);
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
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  cursor: pointer;
  color: #60a5fa;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(59, 130, 246, 0.25);
    border-color: rgba(59, 130, 246, 0.5);
  }
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px;

  &::-webkit-scrollbar { width: 3px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

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
  transition: all 0.15s ease;
  gap: 4px;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    .session-actions { opacity: 1; }
  }

  &.active {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.25);
    .session-name { color: #60a5fa; }
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
  color: var(--assistant-text, #e2e8f0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.3);
}

.session-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s ease;
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
  color: rgba(255, 255, 255, 0.3);
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
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
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
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.8);
  }
}

.header-text {
  min-width: 0;

  .header-title {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
    color: var(--assistant-text, #e2e8f0);
    letter-spacing: 0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 140px;
  }

  .header-status {
    font-size: 10px;
    color: #10b981;

    &.thinking {
      color: #f59e0b;
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
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.4);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.8);
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
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
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
  transition: all 0.15s ease;

  &:hover {
  background: var(--assistant-accent-bg);
  border: 1px solid var(--assistant-accent-border);
  cursor: pointer;
  color: var(--assistant-accent-text);
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
    border: 2px solid rgba(255, 255, 255, 0.15);
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
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
    color: var(--assistant-text, #e2e8f0);
  }

  .welcome-desc {
    margin: 0 0 14px;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
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
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  cursor: pointer;
  color: var(--assistant-text, #e2e8f0);
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
  border: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;

.msg-user-avatar {
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

.avatar-icon {
  width: 14px;
  height: 14px;
  color: white;
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
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom-left-radius: 4px;
    color: var(--assistant-text, #e2e8f0);
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
    background: rgba(0, 0, 0, 0.2);
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
  background: #0d1117;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .code-lang {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.4);
  }
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  font-size: 10px;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.8);
  }

  .copy-icon { width: 10px; height: 10px; }
}

.code-content {
  margin: 0;
  padding: 10px 12px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: #a5d6ff;
  overflow-x: auto;
  line-height: 1.5;

  &::-webkit-scrollbar { height: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
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
  transition: all 0.15s ease;

  &:hover {
    background: var(--assistant-accent-bg);
    border-color: var(--assistant-accent-border);
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
    background: rgba(255, 255, 255, 0.4);
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
  color: rgba(255, 255, 255, 0.25);
  margin-top: 4px;
}

// ==================== Input ====================
.assistant-input {
  padding: 12px 14px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 6px 6px 6px 14px;
  transition: all 0.15s ease;

  &:focus-within {
    border-color: var(--assistant-accent-border);
    background: var(--assistant-bg-focus);
    box-shadow: 0 0 0 3px var(--assistant-accent-shadow);
  }
}

.input-field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--assistant-text, #e2e8f0);
  font-size: 12px;
  line-height: 1.5;
  resize: none;
  min-height: 24px;
  max-height: 120px;
  font-family: inherit;

  &::placeholder { color: rgba(255, 255, 255, 0.3); }
}

.send-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  cursor: pointer;
  color: white;
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
    color: rgba(255, 255, 255, 0.25);

    kbd {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
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
  cursor: pointer;
  box-shadow: var(--assistant-accent-shadow);
  transition: filter 0.2s ease;
  user-select: none;

  &:hover {
    filter: brightness(1.15);
    box-shadow: var(--assistant-accent-shadow-hover);
  }

  &:active {
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

  .trigger-avatar {
    width: 100%;
    height: 100%;
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
// ==================== Theme Variables ====================

// Base defaults (dark)
.workflow-assistant {
  --assistant-bg: #1a1a2e;
  --assistant-bg-subtle: #252542;
  --assistant-bg-focus: rgba(255, 255, 255, 0.07);
  --assistant-border: rgba(255, 255, 255, 0.1);
  --assistant-border-subtle: rgba(255, 255, 255, 0.06);
  --assistant-text: #e2e8f0;
  --assistant-text-secondary: rgba(255, 255, 255, 0.5);
  --assistant-text-tertiary: rgba(255, 255, 255, 0.25);
  --assistant-accent-bg: rgba(6, 182, 212, 0.12);
  --assistant-accent-border: rgba(6, 182, 212, 0.3);
  --assistant-accent-text: #06b6d4;
  --assistant-accent-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
  --assistant-accent-shadow-hover: 0 6px 20px rgba(6, 182, 212, 0.4);
  --assistant-user-bubble-bg: rgba(6, 182, 212, 0.15);
  --assistant-user-bubble-text: #22d3ee;
}

// Dark theme
[data-theme="dark"] {
  .workflow-assistant {
    --assistant-bg: #1a1a2e;
    --assistant-bg-subtle: #252542;
    --assistant-bg-focus: rgba(255, 255, 255, 0.07);
    --assistant-border: rgba(255, 255, 255, 0.1);
    --assistant-border-subtle: rgba(255, 255, 255, 0.06);
    --assistant-text: #e2e8f0;
    --assistant-text-secondary: rgba(255, 255, 255, 0.5);
    --assistant-text-tertiary: rgba(255, 255, 255, 0.25);
    --assistant-accent-bg: rgba(6, 182, 212, 0.12);
    --assistant-accent-border: rgba(6, 182, 212, 0.3);
    --assistant-accent-text: #06b6d4;
    --assistant-accent-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
    --assistant-accent-shadow-hover: 0 6px 20px rgba(6, 182, 212, 0.4);
    --assistant-user-bubble-bg: rgba(6, 182, 212, 0.15);
    --assistant-user-bubble-text: #22d3ee;
  }
  .assistant-trigger {
    background: linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%);
    box-shadow: 0 8px 32px rgba(6, 182, 212, 0.4);
  }
  .assistant-trigger:hover {
    box-shadow: 0 12px 40px rgba(6, 182, 212, 0.5);
  }
  .assistant-trigger .trigger-ring {
    border-color: rgba(6, 182, 212, 0.3);
  }
  .assistant-trigger .trigger-logo-wrap {
    background: #1a1a2e;
    border-radius: 50%;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .assistant-trigger .trigger-avatar {
    border-radius: 50%;
    width: 100%;
    height: 100%;
    object-fit: contain;
    max-width: 70%;
    max-height: 70%;
  }

  .workflow-assistant .assistant-header {
    background: rgba(6, 182, 212, 0.08);
    border-color: rgba(255, 255, 255, 0.06);
  }
  .workflow-assistant .suggestion-pill {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
  }
  .workflow-assistant .suggestion-pill:hover {
    background: rgba(6, 182, 212, 0.12);
    border-color: rgba(6, 182, 212, 0.3);
  }
  .workflow-assistant .suggestion-pill .pill-icon { color: #06b6d4; }
  .workflow-assistant .msg-bubble.ai-message {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.08);
  }
  .workflow-assistant .msg-user-avatar { background-color: rgba(6, 182, 212, 0.1); }
  .workflow-assistant .msg-user-avatar .avatar-initial { color: rgba(255, 255, 255, 0.5); }
  .workflow-assistant .session-item:hover { background: rgba(255, 255, 255, 0.05); }
  .workflow-assistant .session-item.active { background: rgba(6, 182, 212, 0.1); }
  .workflow-assistant .session-item.active .session-name { color: #06b6d4; }
  .workflow-assistant .conversation-sidebar { background: rgba(0, 0, 0, 0.15); }
  .workflow-assistant .msg-time { color: rgba(255, 255, 255, 0.25); }
  .workflow-assistant .welcome-title { color: #e2e8f0; }
  .workflow-assistant .welcome-desc { color: rgba(255, 255, 255, 0.5); }
  .workflow-assistant .welcome-avatar { border-color: rgba(255, 255, 255, 0.1); }
  .workflow-assistant .input-hints .hint { color: rgba(255, 255, 255, 0.25); }
  .workflow-assistant .input-field { color: #e2e8f0; }
  .workflow-assistant .assistant-input { background: rgba(0, 0, 0, 0.1); }
  .workflow-assistant .input-wrapper {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
  }
  .workflow-assistant .input-wrapper:focus-within {
    border-color: rgba(6, 182, 212, 0.3);
    background: rgba(255, 255, 255, 0.07);
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
  }
  .workflow-assistant .header-title { color: #e2e8f0; }
  .workflow-assistant .header-btn {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.4);
  }
  .workflow-assistant .header-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
  }
  .workflow-assistant .sidebar-toggle-btn {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.4);
  }
  .workflow-assistant .sidebar-toggle-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
  }
  .workflow-assistant .new-conv-btn {
    background: rgba(6, 182, 212, 0.1);
    border-color: rgba(6, 182, 212, 0.2);
    color: #06b6d4;
  }
  .workflow-assistant .new-conv-btn:hover { background: rgba(6, 182, 212, 0.18); }
  .workflow-assistant .sidebar-title { color: #e2e8f0; }
  .workflow-assistant .session-name { color: #e2e8f0; }
  .workflow-assistant .session-time { color: rgba(255, 255, 255, 0.25); }
  .workflow-assistant .search-input {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
  }
  .workflow-assistant .search-input::placeholder { color: rgba(255, 255, 255, 0.25); }
  .workflow-assistant .search-input:focus { background: rgba(255, 255, 255, 0.06); }
  .workflow-assistant .assistant-messages::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); }
  .workflow-assistant .session-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); }
  .workflow-assistant .sidebar-header { border-color: rgba(255, 255, 255, 0.05); }
  .workflow-assistant .sidebar-close-btn, .workflow-assistant .session-action-btn { color: rgba(255, 255, 255, 0.4); }
  .workflow-assistant .sidebar-close-btn:hover, .workflow-assistant .session-action-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
  }
  .workflow-assistant .code-block { background: #0d1117; }
  .workflow-assistant .code-header { background: rgba(255, 255, 255, 0.03); border-color: rgba(255, 255, 255, 0.05); }
  .workflow-assistant .code-header .code-lang { color: rgba(255, 255, 255, 0.35); }
  .workflow-assistant .copy-btn { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.4); }
  .workflow-assistant .copy-btn:hover { background: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.7); }
  .workflow-assistant .code-content { color: #a5d6ff; }
  .workflow-assistant .input-hints kbd { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.08); }
  .workflow-assistant .ai-status-dot { background: #10b981; border-color: #1a1a2e; }
  .workflow-assistant .header-status { color: #10b981; }
  .workflow-assistant .header-status.thinking { color: #f59e0b; }
  .workflow-assistant .empty-sessions { color: rgba(255, 255, 255, 0.3); }
  .workflow-assistant .welcome-avatar { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }
}

// Light theme
[data-theme="light"] {
  .workflow-assistant {
    --assistant-bg: #ffffff;
    --assistant-bg-subtle: #f1f5f9;
    --assistant-bg-focus: rgba(0, 0, 0, 0.04);
    --assistant-border: rgba(0, 0, 0, 0.1);
    --assistant-border-subtle: rgba(0, 0, 0, 0.06);
    --assistant-text: #1e293b;
    --assistant-text-secondary: rgba(0, 0, 0, 0.45);
    --assistant-text-tertiary: rgba(0, 0, 0, 0.25);
    --assistant-accent-bg: rgba(6, 182, 212, 0.08);
    --assistant-accent-border: rgba(6, 182, 212, 0.2);
    --assistant-accent-text: #0891b2;
    --assistant-accent-shadow: 0 4px 12px rgba(6, 182, 212, 0.2);
    --assistant-accent-shadow-hover: 0 6px 20px rgba(6, 182, 212, 0.3);
    --assistant-user-bubble-bg: rgba(6, 182, 212, 0.1);
    --assistant-user-bubble-text: #0e7490;
  }
  .assistant-trigger {
    background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
    box-shadow: 0 8px 32px rgba(6, 182, 212, 0.3);
  }
  .assistant-trigger:hover {
    box-shadow: 0 12px 40px rgba(6, 182, 212, 0.4);
  }
  .assistant-trigger .trigger-ring {
    border-color: rgba(6, 182, 212, 0.3);
  }
  .assistant-trigger .trigger-logo-wrap {
    background: #ffffff;
    border-radius: 50%;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .assistant-trigger .trigger-avatar {
    border-radius: 50%;
    width: 100%;
    height: 100%;
    object-fit: contain;
    max-width: 70%;
    max-height: 70%;
  }

  .workflow-assistant .assistant-header {
    background: rgba(6, 182, 212, 0.06);
    border-color: rgba(0, 0, 0, 0.06);
  }
  .workflow-assistant .msg-bubble.ai-message {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.08);
  }
  .workflow-assistant .msg-user-avatar { background-color: rgba(0, 0, 0, 0.06); }
  .workflow-assistant .msg-user-avatar .avatar-initial { color: rgba(0, 0, 0, 0.45); }
  .workflow-assistant .suggestion-pill {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.08);
    color: #1e293b;
  }
  .workflow-assistant .suggestion-pill:hover {
    background: rgba(6, 182, 212, 0.08);
    border-color: rgba(6, 182, 212, 0.2);
  }
  .workflow-assistant .suggestion-pill .pill-icon { color: #0891b2; }
  .workflow-assistant .session-item:hover { background: rgba(0, 0, 0, 0.04); }
  .workflow-assistant .session-item.active { background: rgba(6, 182, 212, 0.08); }
  .workflow-assistant .session-item.active .session-name { color: #0891b2; }
  .workflow-assistant .conversation-sidebar { background: rgba(0, 0, 0, 0.02); }
  .workflow-assistant .msg-time { color: rgba(0, 0, 0, 0.25); }
  .workflow-assistant .welcome-title { color: #1e293b; }
  .workflow-assistant .welcome-desc { color: rgba(0, 0, 0, 0.45); }
  .workflow-assistant .welcome-avatar { border-color: rgba(0, 0, 0, 0.1); }
  .workflow-assistant .input-hints .hint { color: rgba(0, 0, 0, 0.3); }
  .workflow-assistant .input-field { color: #1e293b; }
  .workflow-assistant .assistant-input { background: rgba(0, 0, 0, 0.03); }
  .workflow-assistant .input-wrapper {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.1);
  }
  .workflow-assistant .input-wrapper:focus-within {
    border-color: rgba(6, 182, 212, 0.2);
    background: rgba(0, 0, 0, 0.05);
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.08);
  }
  .workflow-assistant .header-title { color: #1e293b; }
  .workflow-assistant .header-btn {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.08);
    color: rgba(0, 0, 0, 0.45);
  }
  .workflow-assistant .header-btn:hover {
    background: rgba(0, 0, 0, 0.08);
    color: #1e293b;
  }
  .workflow-assistant .sidebar-toggle-btn {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.08);
    color: rgba(0, 0, 0, 0.45);
  }
  .workflow-assistant .sidebar-toggle-btn:hover {
    background: rgba(0, 0, 0, 0.08);
    color: #1e293b;
  }
  .workflow-assistant .new-conv-btn {
    background: rgba(6, 182, 212, 0.08);
    border-color: rgba(6, 182, 212, 0.2);
    color: #0891b2;
  }
  .workflow-assistant .new-conv-btn:hover { background: rgba(6, 182, 212, 0.15); }
  .workflow-assistant .sidebar-title { color: #1e293b; }
  .workflow-assistant .session-name { color: #1e293b; }
  .workflow-assistant .session-time { color: rgba(0, 0, 0, 0.25); }
  .workflow-assistant .search-input {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.1);
    color: #1e293b;
  }
  .workflow-assistant .search-input::placeholder { color: rgba(0, 0, 0, 0.25); }
  .workflow-assistant .search-input:focus { background: rgba(0, 0, 0, 0.06); }
  .workflow-assistant .assistant-messages::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.1); }
  .workflow-assistant .session-list::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.08); }
  .workflow-assistant .sidebar-header { border-color: rgba(0, 0, 0, 0.05); }
  .workflow-assistant .sidebar-close-btn, .workflow-assistant .session-action-btn { color: rgba(0, 0, 0, 0.45); }
  .workflow-assistant .sidebar-close-btn:hover, .workflow-assistant .session-action-btn:hover {
    background: rgba(0, 0, 0, 0.08);
    color: #1e293b;
  }
  .workflow-assistant .code-block { background: #0d1117; }
  .workflow-assistant .code-header { background: rgba(0, 0, 0, 0.03); border-color: rgba(0, 0, 0, 0.05); }
  .workflow-assistant .code-header .code-lang { color: rgba(0, 0, 0, 0.35); }
  .workflow-assistant .copy-btn { background: rgba(0, 0, 0, 0.04); border-color: rgba(0, 0, 0, 0.08); color: rgba(0, 0, 0, 0.45); }
  .workflow-assistant .copy-btn:hover { background: rgba(0, 0, 0, 0.08); color: #1e293b; }
  .workflow-assistant .code-content { color: #7dd3fc; }
  .workflow-assistant .input-hints kbd { background: rgba(0, 0, 0, 0.04); border-color: rgba(0, 0, 0, 0.08); }
  .workflow-assistant .ai-status-dot { background: #10b981; border-color: #ffffff; }
  .workflow-assistant .header-status { color: #10b981; }
  .workflow-assistant .header-status.thinking { color: #b45309; }
  .workflow-assistant .empty-sessions { color: rgba(0, 0, 0, 0.3); }
  .workflow-assistant .welcome-avatar { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); }
}

// Pure B&W theme
[data-theme="pure-bw"] {
  .workflow-assistant {
    --assistant-bg: #ffffff;
    --assistant-bg-subtle: #f5f5f5;
    --assistant-bg-focus: rgba(0, 0, 0, 0.05);
    --assistant-border: #111111;
    --assistant-border-subtle: #e5e5e5;
    --assistant-text: #111111;
    --assistant-text-secondary: #555555;
    --assistant-text-tertiary: #999999;
    --assistant-accent-bg: rgba(0, 0, 0, 0.06);
    --assistant-accent-border: rgba(0, 0, 0, 0.2);
    --assistant-accent-text: #111111;
    --assistant-accent-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    --assistant-accent-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.2);
    --assistant-user-bubble-bg: rgba(0, 0, 0, 0.1);
    --assistant-user-bubble-text: #111111;
  }
  .assistant-trigger {
    background: linear-gradient(135deg, #111111 0%, #333333 100%);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  }
  .assistant-trigger:hover {
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
  }
  .assistant-trigger .trigger-ring {
    border-color: rgba(0, 0, 0, 0.2);
  }
  .assistant-trigger .trigger-logo-wrap {
    background: #ffffff;
    border-radius: 50%;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .assistant-trigger .trigger-avatar {
    border-radius: 50%;
    width: 100%;
    height: 100%;
    object-fit: contain;
    max-width: 70%;
    max-height: 70%;
  }

  .workflow-assistant .assistant-header { background: #f5f5f5; border-color: #e5e5e5; }
  .workflow-assistant .msg-bubble.ai-message { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; }
  .workflow-assistant .msg-user-avatar { background-color: #f5f5f5; }
  .workflow-assistant .msg-user-avatar .avatar-initial { color: #555555; }
  .workflow-assistant .suggestion-pill { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; color: #111111; }
  .workflow-assistant .suggestion-pill:hover { background: rgba(0, 0, 0, 0.08); }
  .workflow-assistant .suggestion-pill .pill-icon { color: #111111; }
  .workflow-assistant .session-item:hover { background: rgba(0, 0, 0, 0.04); }
  .workflow-assistant .session-item.active { background: rgba(0, 0, 0, 0.08); }
  .workflow-assistant .conversation-sidebar { background: #fafafa; }
  .workflow-assistant .msg-time { color: #999999; }
  .workflow-assistant .welcome-title { color: #111111; }
  .workflow-assistant .welcome-desc { color: #555555; }
  .workflow-assistant .welcome-avatar { border-color: #e5e5e5; }
  .workflow-assistant .input-hints .hint { color: #999999; }
  .workflow-assistant .input-field { color: #111111; }
  .workflow-assistant .assistant-input { background: #f5f5f5; }
  .workflow-assistant .input-wrapper { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; }
  .workflow-assistant .input-wrapper:focus-within { border-color: rgba(0, 0, 0, 0.2); }
  .workflow-assistant .header-title { color: #111111; }
  .workflow-assistant .header-btn { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; color: #555555; }
  .workflow-assistant .header-btn:hover { background: rgba(0, 0, 0, 0.08); color: #111111; }
  .workflow-assistant .sidebar-toggle-btn { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; color: #555555; }
  .workflow-assistant .sidebar-toggle-btn:hover { background: rgba(0, 0, 0, 0.08); color: #111111; }
  .workflow-assistant .new-conv-btn { background: rgba(0, 0, 0, 0.06); border-color: rgba(0, 0, 0, 0.15); color: #111111; }
  .workflow-assistant .new-conv-btn:hover { background: rgba(0, 0, 0, 0.1); }
  .workflow-assistant .sidebar-title { color: #111111; }
  .workflow-assistant .session-name { color: #111111; }
  .workflow-assistant .session-time { color: #999999; }
  .workflow-assistant .search-input { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; color: #111111; }
  .workflow-assistant .search-input::placeholder { color: #999999; }
  .workflow-assistant .assistant-messages::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.1); }
  .workflow-assistant .session-list::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.08); }
  .workflow-assistant .sidebar-header { border-color: #e5e5e5; }
  .workflow-assistant .sidebar-close-btn, .workflow-assistant .session-action-btn { color: #555555; }
  .workflow-assistant .sidebar-close-btn:hover, .workflow-assistant .session-action-btn:hover { background: rgba(0, 0, 0, 0.08); color: #111111; }
  .workflow-assistant .code-block { background: #0d1117; }
  .workflow-assistant .code-header { background: rgba(0, 0, 0, 0.03); border-color: rgba(0, 0, 0, 0.05); }
  .workflow-assistant .code-header .code-lang { color: #555555; }
  .workflow-assistant .copy-btn { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; color: #555555; }
  .workflow-assistant .copy-btn:hover { background: rgba(0, 0, 0, 0.08); color: #111111; }
  .workflow-assistant .code-content { color: #888888; }
  .workflow-assistant .input-hints kbd { background: rgba(0, 0, 0, 0.04); border-color: #e5e5e5; }
  .workflow-assistant .ai-status-dot { background: #111111; border-color: #ffffff; }
  .workflow-assistant .header-status { color: #111111; }
  .workflow-assistant .header-status.thinking { color: #555555; }
  .workflow-assistant .empty-sessions { color: #999999; }
  .workflow-assistant .welcome-avatar { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); }
}

// High Contrast theme
[data-theme="high-contrast"] {
  .workflow-assistant {
    --assistant-bg: #000000;
    --assistant-bg-subtle: #111111;
    --assistant-bg-focus: rgba(255, 255, 0, 0.05);
    --assistant-border: #ffff00;
    --assistant-border-subtle: rgba(255, 255, 0, 0.3);
    --assistant-text: #ffffff;
    --assistant-text-secondary: #ffff00;
    --assistant-text-tertiary: rgba(255, 255, 255, 0.6);
    --assistant-accent-bg: rgba(255, 255, 0, 0.15);
    --assistant-accent-border: #ffff00;
    --assistant-accent-text: #ffff00;
    --assistant-accent-shadow: 0 0 8px rgba(255, 255, 0, 0.4);
    --assistant-accent-shadow-hover: 0 0 12px rgba(255, 255, 0, 0.6);
    --assistant-user-bubble-bg: rgba(255, 255, 0, 0.12);
    --assistant-user-bubble-text: #ffff00;
  }
  .assistant-trigger {
    background: linear-gradient(135deg, #000000 0%, #111111 100%);
    box-shadow: 0 0 12px rgba(255, 255, 0, 0.6);
    border: 2px solid #ffff00;
  }
  .assistant-trigger:hover {
    box-shadow: 0 0 20px rgba(255, 255, 0, 0.8);
  }
  .assistant-trigger .trigger-ring {
    border-color: rgba(255, 255, 0, 0.5);
  }
  .assistant-trigger .trigger-logo-wrap {
    background: #000000;
    border-radius: 50%;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .assistant-trigger .trigger-avatar {
    border-radius: 50%;
    width: 100%;
    height: 100%;
    object-fit: contain;
    max-width: 70%;
    max-height: 70%;
  }

  .workflow-assistant .assistant-header { background: #111111; border-color: #ffff00; }
  .workflow-assistant .msg-bubble.ai-message { background: #111111; border-color: rgba(255, 255, 0, 0.3); }
  .workflow-assistant .msg-user-avatar { background-color: #222222; }
  .workflow-assistant .msg-user-avatar .avatar-initial { color: #ffff00; }
  .workflow-assistant .suggestion-pill { background: rgba(255, 255, 0, 0.08); border-color: #ffff00; color: #ffffff; }
  .workflow-assistant .suggestion-pill:hover { background: rgba(255, 255, 0, 0.15); }
  .workflow-assistant .suggestion-pill .pill-icon { color: #ffff00; }
  .workflow-assistant .session-item:hover { background: rgba(255, 255, 0, 0.08); }
  .workflow-assistant .session-item.active { background: rgba(255, 255, 0, 0.15); }
  .workflow-assistant .conversation-sidebar { background: #0a0a0a; }
  .workflow-assistant .msg-time { color: rgba(255, 255, 255, 0.6); }
  .workflow-assistant .welcome-title { color: #ffffff; }
  .workflow-assistant .welcome-desc { color: #ffff00; }
  .workflow-assistant .welcome-avatar { border-color: #ffff00; }
  .workflow-assistant .input-hints .hint { color: rgba(255, 255, 255, 0.6); }
  .workflow-assistant .input-field { color: #ffffff; }
  .workflow-assistant .assistant-input { background: #0a0a0a; }
  .workflow-assistant .input-wrapper { background: rgba(255, 255, 0, 0.05); border-color: #ffff00; }
  .workflow-assistant .input-wrapper:focus-within { border-color: #ffff00; }
  .workflow-assistant .header-title { color: #ffffff; }
  .workflow-assistant .header-btn { background: rgba(255, 255, 0, 0.08); border-color: #ffff00; color: #ffffff; }
  .workflow-assistant .header-btn:hover { background: rgba(255, 255, 0, 0.15); }
  .workflow-assistant .sidebar-toggle-btn { background: rgba(255, 255, 0, 0.08); border-color: #ffff00; color: #ffffff; }
  .workflow-assistant .sidebar-toggle-btn:hover { background: rgba(255, 255, 0, 0.15); }
  .workflow-assistant .new-conv-btn { background: rgba(255, 255, 0, 0.08); border-color: #ffff00; color: #ffffff; }
  .workflow-assistant .new-conv-btn:hover { background: rgba(255, 255, 0, 0.15); }
  .workflow-assistant .sidebar-title { color: #ffffff; }
  .workflow-assistant .session-name { color: #ffffff; }
  .workflow-assistant .session-time { color: rgba(255, 255, 255, 0.6); }
  .workflow-assistant .search-input { background: rgba(255, 255, 0, 0.05); border-color: #ffff00; color: #ffffff; }
  .workflow-assistant .search-input::placeholder { color: rgba(255, 255, 255, 0.6); }
  .workflow-assistant .assistant-messages::-webkit-scrollbar-thumb { background: rgba(255, 255, 0, 0.3); }
  .workflow-assistant .session-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 0, 0.2); }
  .workflow-assistant .sidebar-header { border-color: rgba(255, 255, 0, 0.3); }
  .workflow-assistant .sidebar-close-btn, .workflow-assistant .session-action-btn { color: #ffffff; }
  .workflow-assistant .sidebar-close-btn:hover, .workflow-assistant .session-action-btn:hover { background: rgba(255, 255, 0, 0.15); }
  .workflow-assistant .code-block { background: #0a0a0a; }
  .workflow-assistant .code-header { background: rgba(255, 255, 0, 0.03); border-color: rgba(255, 255, 0, 0.2); }
  .workflow-assistant .code-header .code-lang { color: #ffff00; }
  .workflow-assistant .copy-btn { background: rgba(255, 255, 0, 0.05); border-color: #ffff00; color: #ffffff; }
  .workflow-assistant .copy-btn:hover { background: rgba(255, 255, 0, 0.1); }
  .workflow-assistant .code-content { color: #ffffff; }
  .workflow-assistant .input-hints kbd { background: rgba(255, 255, 0, 0.05); border-color: #ffff00; }
  .workflow-assistant .ai-status-dot { background: #ffff00; border-color: #000000; }
  .workflow-assistant .header-status { color: #ffff00; }
  .workflow-assistant .header-status.thinking { color: #ffffff; }
  .workflow-assistant .empty-sessions { color: rgba(255, 255, 255, 0.6); }
  .workflow-assistant .welcome-avatar { box-shadow: 0 0 8px rgba(255, 255, 0, 0.3); }
}

</style>

