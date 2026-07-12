<template>
  <div class="agent-debugger">
    <div class="debugger-container">
      <!-- 左侧：Agent 信息 -->
      <aside class="agent-sidebar">
        <div class="sidebar-header">
          <h3>Agent 信息</h3>
          <el-button
            text
            circle
            @click="handleBack"
          >
            <X />
          </el-button>
        </div>

        <div
          v-if="agent"
          class="agent-info"
        >
          <div class="agent-avatar">
            <Bot />
          </div>
          <h2 class="agent-name">
            {{ agent.name }}
          </h2>
          <p class="agent-desc">
            {{ agent.description || '暂无描述' }}
          </p>

          <div class="info-section">
            <h4>配置</h4>
            <div class="info-item">
              <span class="info-label">模型</span>
              <span class="info-value">{{ agent.model }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">温度</span>
              <span class="info-value">{{ agent.temperature }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">上下文</span>
              <span class="info-value">{{ agent.context_window }} 轮</span>
            </div>
            <div class="info-item">
              <span class="info-label">最大Token</span>
              <span class="info-value">{{ agent.max_tokens }}</span>
            </div>
          </div>

          <div
            v-if="agent.system_prompt"
            class="info-section"
          >
            <h4>系统提示词</h4>
            <div class="system-prompt">
              {{ truncatedPrompt }}
              <el-button
                v-if="agent.system_prompt.length > 200"
                text
                size="small"
                @click="showFullPrompt = true"
              >
                展开
              </el-button>
            </div>
          </div>

          <div class="info-section">
            <h4>可用工具</h4>
            <div class="tools-list">
              <el-tag
                v-for="tool in agent.tools"
                :key="tool"
                size="small"
                type="info"
              >
                {{ getToolLabel(tool) }}
              </el-tag>
              <span
                v-if="!agent.tools?.length"
                class="no-tools"
              >无</span>
            </div>
          </div>
        </div>

        <div class="sidebar-footer">
          <el-button @click="goToEdit">
            <Edit class="btn-icon" />
            编辑 Agent
          </el-button>
          <el-button @click="clearSession">
            <RefreshCw class="btn-icon" />
            清除对话
          </el-button>
          <el-button @click="handleResetMemory">
            <Trash2 class="btn-icon" />
            重置记忆
          </el-button>
        </div>
      </aside>

      <!-- 中间：对话区域 -->
      <main class="chat-area">
        <div class="chat-header">
          <h3>调试会话</h3>
          <div class="chat-actions">
            <el-switch
              v-model="useStreaming"
              active-text="流式输出"
              inactive-text=""
            />
            <el-button
              v-if="debugSessions.length > 0"
              text
              @click="showHistory = true"
            >
              <History class="btn-icon" />
              历史记录
            </el-button>
          </div>
        </div>

        <div
          ref="messagesContainer"
          class="messages-container"
        >
          <div
            v-if="messages.length === 0"
            class="empty-chat"
          >
            <Bot class="empty-icon" />
            <p>开始与 Agent 对话</p>
            <p class="hint">
              输入消息来测试 Agent 的响应
            </p>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message', `message-${msg.role}`, { 'message-streaming': msg.isStreaming }]"
          >
            <div class="message-avatar">
              <Bot v-if="msg.role === 'assistant'" />
              <User v-else />
            </div>
            <div class="message-content">
              <div class="message-text">
                <template v-if="msg.isStreaming">
                  {{ msg.content }}<span class="cursor">|</span>
                </template>
                <template v-else>
                  {{ msg.content }}
                </template>
              </div>
              <div class="message-time">
                {{ formatTime(msg.timestamp) }}
              </div>

              <!-- 工具调用展示 -->
              <div
                v-if="msg.toolCalls?.length"
                class="tool-calls"
              >
                <div
                  v-for="(call, i) in msg.toolCalls"
                  :key="i"
                  class="tool-call"
                >
                  <template v-if="call.name === 'knowledge_base'">
                    <div class="kb-call">
                      <div class="kb-call-header">
                        <BookOpen class="tool-icon" />
                        <span class="tool-name">知识库检索</span>
                        <span
                          v-if="call.result?.success"
                          class="kb-count"
                        >命中 {{ call.result.count || 0 }} 条</span>
                        <span
                          v-else
                          class="kb-count kb-error"
                        >{{ call.result?.error || '检索失败' }}</span>
                      </div>
                      <div
                        v-if="call.result?.results?.length"
                        class="kb-sources"
                      >
                        <div
                          v-for="(src, si) in call.result.results"
                          :key="si"
                          class="kb-source"
                        >
                          <span class="kb-source-collection">{{ src.collection }}</span>
                          <span class="kb-source-content">{{ src.content }}</span>
                        </div>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <Hammer class="tool-icon" />
                    <span class="tool-name">{{ getToolLabel(call.name) }}</span>
                    <span class="tool-result">{{ formatToolResult(call.result) }}</span>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="isLoading && !isStreaming"
            class="message message-assistant"
          >
            <div class="message-avatar">
              <Bot />
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            :placeholder="inputPlaceholder"
            :disabled="isLoading"
            @keydown.enter.ctrl="sendMessage"
            @keydown.enter.meta="sendMessage"
            @keydown.shift.enter="inputMessage += '\n'"
          />
          <div class="input-actions">
            <div class="input-hints">
              <span class="hint">Enter 发送, Shift+Enter 换行</span>
              <span
                v-if="inputMessage.length > 0"
                class="char-count"
              >
                {{ inputMessage.length }}
              </span>
            </div>
            <AppButton
              variant="primary"
              :loading="isLoading"
              :disabled="!inputMessage.trim()"
              @click="sendMessage"
            >
              <Send class="btn-icon" />
              {{ isLoading ? '处理中...' : '发送' }}
            </AppButton>
          </div>
        </div>
      </main>

      <!-- 右侧：上下文/变量 -->
      <aside class="context-sidebar">
        <div class="sidebar-header">
          <h3>调试信息</h3>
        </div>

        <div class="context-section">
          <h4>当前会话</h4>
          <div class="context-item">
            <span class="context-label">会话 ID</span>
            <span class="context-value">{{ currentSessionId || '-' }}</span>
          </div>
          <div class="context-item">
            <span class="context-label">消息数</span>
            <span class="context-value">{{ messages.length }}</span>
          </div>
          <div class="context-item">
            <span class="context-label">模式</span>
            <span class="context-value">{{ useStreaming ? '流式' : '普通' }}</span>
          </div>
        </div>

        <div class="context-section">
          <h4>Token 使用</h4>
          <el-progress
            :percentage="tokenUsagePercent"
            :color="tokenUsageColor"
            :stroke-width="8"
          />
          <div class="token-stats">
            <span>已使用: {{ tokenUsage }}</span>
            <span>限制: {{ maxTokens }}</span>
          </div>
        </div>

        <div class="context-section">
          <h4>模型信息</h4>
          <div class="model-info">
            <div class="context-item">
              <span class="context-label">模型</span>
              <span class="context-value">{{ agent?.model || '-' }}</span>
            </div>
            <div class="context-item">
              <span class="context-label">温度</span>
              <span class="context-value">{{ agent?.temperature }}</span>
            </div>
          </div>
        </div>

        <div class="context-section">
          <h4>快捷操作</h4>
          <div class="quick-actions">
            <el-button
              size="small"
              @click="insertTemplate('总结')"
            >
              总结这段文字
            </el-button>
            <el-button
              size="small"
              @click="insertTemplate('翻译')"
            >
              翻译成英文
            </el-button>
            <el-button
              size="small"
              @click="insertTemplate('代码')"
            >
              解释这段代码
            </el-button>
          </div>
        </div>
      </aside>
    </div>

    <!-- 历史记录对话框 -->
    <el-dialog
      v-model="showHistory"
      title="调试历史"
      width="600px"
    >
      <div class="history-list">
        <div
          v-for="session in debugSessions"
          :key="session.id"
          class="history-item"
          @click="loadSession(session)"
        >
          <div class="history-info">
            <span class="history-date">{{ formatDate(session.created_at) }}</span>
            <span class="history-messages">{{ session.message_count || 0 }} 条消息</span>
          </div>
          <el-button
            text
            size="small"
          >
            <ArrowRight />
          </el-button>
        </div>
        <div
          v-if="debugSessions.length === 0"
          class="no-history"
        >
          暂无历史记录
        </div>
      </div>
      <template #footer>
        <el-button @click="showHistory = false">
          关闭
        </el-button>
        <el-button
          type="danger"
          @click="clearAllHistory"
        >
          清空历史
        </el-button>
      </template>
    </el-dialog>

    <!-- 完整提示词对话框 -->
    <el-dialog
      v-model="showFullPrompt"
      title="系统提示词"
      width="700px"
    >
      <pre class="full-prompt">{{ agent?.system_prompt }}</pre>
      <template #footer>
        <el-button @click="showFullPrompt = false">
          关闭
        </el-button>
        <el-button @click="copyPrompt">
          复制
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useAppStore } from '@/stores/app'
import { getToolLabel } from '@/config/toolConfig'
import {
  Bot, User, X, Edit, RefreshCw, Send, History,
  ArrowRight, Hammer, Trash2, BookOpen
} from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()
const appStore = useAppStore()

const agentId = computed(() => route.params.id)

const agent = computed(() => agentStore.currentAgent)
const messages = computed(() => agentStore.debugMessages)
const isLoading = computed(() => agentStore.isLoading)
const isStreaming = computed(() => agentStore.isStreaming)
const debugSessions = computed(() => agentStore.debugSessions)
const currentDebugSession = computed(() => agentStore.currentDebugSession)

const inputMessage = ref('')
const showHistory = ref(false)
const showFullPrompt = ref(false)
const useStreaming = ref(true)
const messagesContainer = ref(null)

const tokenUsage = ref(0)
const maxTokens = computed(() => agent.value?.max_tokens || 2000)
const tokenUsagePercent = computed(() => Math.min(100, (tokenUsage.value / maxTokens.value) * 100))
const tokenUsageColor = computed(() => {
  if (tokenUsagePercent.value > 90) return '#F56C6C'
  if (tokenUsagePercent.value > 70) return '#E6A23C'
  return '#67C23A'
})

const currentSessionId = computed(() => currentDebugSession.value?.conversation_id)

const truncatedPrompt = computed(() => {
  const prompt = agent.value?.system_prompt || ''
  return prompt.length > 200 ? prompt.slice(0, 200) + '...' : prompt
})

const inputPlaceholder = computed(() => {
  return useStreaming.value
    ? '输入消息 (流式响应)...'
    : '输入消息...'
})

onMounted(async () => {
  if (agentId.value) {
    try {
      await agentStore.fetchAgent(agentId.value)
      await agentStore.fetchDebugHistory(agentId.value)
    } catch (err) {
      appStore.error('加载 Agent 失败')
    }
  }
})

watch(messages, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}, { deep: true })

async function sendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  try {
    if (useStreaming.value) {
      await agentStore.streamChatMessage(agentId.value, message)
    } else {
      await agentStore.sendDebugMessage(agentId.value, message)
    }
  } catch (err) {
    appStore.error('发送消息失败')
  }
}

function handleBack() {
  agentStore.clearDebugSession()
  router.push('/agents')
}

function goToEdit() {
  router.push(`/agents/${agentId.value}/edit`)
}

function clearSession() {
  agentStore.clearDebugSession()
  appStore.success('对话已清除')
}

async function handleResetMemory() {
  try {
    await agentStore.resetMemory(agentId.value)
    appStore.success('记忆已重置')
  } catch (err) {
    appStore.error('重置失败')
  }
}

function loadSession(session) {
  // Load a previous debug session
  showHistory.value = false

  if (!session || !session.id) {
    appStore.error('无效的会话')
    return
  }

  // Get agent ID from route
  const agentIdValue = route.params.id
  if (!agentIdValue) {
    appStore.error('无法加载会话')
    return
  }

  agentStore.loadDebugSession(agentIdValue, session.id)
    .then(() => {
      appStore.success('会话已加载')
    })
    .catch((_err) => {
      appStore.error('加载会话失败')
    })
}

async function clearAllHistory() {
  try {
    await agentStore.clearDebugHistory(agentId.value)
    showHistory.value = false
    appStore.success('历史已清空')
  } catch (err) {
    appStore.error('清空失败')
  }
}

function insertTemplate(type) {
  const templates = {
    '总结': '请总结以下内容的要点：\n',
    '翻译': '请将以下内容翻译成英文：\n',
    '代码': '请解释以下代码的功能：\n```\n\n```'
  }
  inputMessage.value = templates[type] || ''
}

function copyPrompt() {
  if (agent.value?.system_prompt) {
    navigator.clipboard.writeText(agent.value.system_prompt)
    appStore.success('已复制')
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatToolResult(result) {
  if (result == null) return ''
  if (typeof result === 'string') return result
  try {
    return JSON.stringify(result)
  } catch {
    return String(result)
  }
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.agent-debugger {
  position: fixed;
  inset: 0;
  background-color: var(--bg-primary);
}

.debugger-container {
  display: flex;
  height: 100%;
}

.agent-sidebar {
  width: 280px;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  h3 {
    margin: 0;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
    text-transform: uppercase;
  }
}

.agent-info {
  flex: 1;
  padding: $spacing-4;
  overflow-y: auto;
}

.agent-avatar {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, $color-secondary 0%, $color-primary 100%);
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: $spacing-4;

  svg {
    width: 24px;
    height: 24px;
    color: white;
  }
}

.agent-name {
  font-size: $font-size-lg;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0 0 $spacing-2;
}

.agent-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0 0 $spacing-4;
}

.info-section {
  margin-bottom: $spacing-4;

  h4 {
    font-size: $font-size-xs;
    font-weight: $font-weight-medium;
    color: var(--text-tertiary);
    margin: 0 0 $spacing-2;
    text-transform: uppercase;
  }
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: $spacing-2 0;
  font-size: $font-size-sm;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-primary);
  font-weight: $font-weight-medium;
}

.system-prompt {
  font-size: $font-size-xs;
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: $spacing-3;
  border-radius: $radius-md;
  max-height: 100px;
  overflow: hidden;
  position: relative;

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 30px;
    background: linear-gradient(transparent, var(--bg-tertiary));
  }
}

.tools-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
}

.no-tools {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.sidebar-footer {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
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

.chat-actions {
  display: flex;
  align-items: center;
  gap: $spacing-4;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-4;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--text-tertiary);
    margin-bottom: $spacing-4;
  }

  p {
    margin: 0;
    color: var(--text-secondary);

    &.hint {
      font-size: $font-size-sm;
      color: var(--text-tertiary);
      margin-top: $spacing-2;
    }
  }
}

.message {
  display: flex;
  gap: $spacing-3;
  margin-bottom: $spacing-4;

  &-user {
    flex-direction: row-reverse;
  }

  &-streaming {
    .message-text {
      background: linear-gradient(135deg, rgba($color-primary, 0.1) 0%, rgba($color-secondary, 0.1) 100%);
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

  svg {
    width: 20px;
    height: 20px;
  }

  .message-assistant & {
    background: linear-gradient(135deg, $color-primary 0%, $color-secondary 100%);
    color: white;
  }

  .message-user & {
    background-color: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .message-error & {
    background-color: rgba($color-error, 0.2);
    color: $color-error;
  }
}

.message-content {
  max-width: 70%;
}

.message-text {
  padding: $spacing-3 $spacing-4;
  border-radius: $radius-xl;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  white-space: pre-wrap;

  .message-assistant & {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border-radius: $radius-xl $radius-xl $radius-xl 0;
  }

  .message-user & {
    background: linear-gradient(135deg, $color-primary 0%, $color-secondary 100%);
    color: white;
    border-radius: $radius-xl $radius-xl 0 $radius-xl;
  }

  .message-error & {
    background-color: rgba($color-error, 0.1);
    color: $color-error;
  }

  .cursor {
    animation: blink 1s infinite;
    color: $color-primary;
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

.tool-calls {
  margin-top: $spacing-2;
  padding: $spacing-2;
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;
}

.tool-call {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-xs;
  padding: $spacing-1 0;

  .tool-icon {
    width: 14px;
    height: 14px;
    color: $color-primary;
    flex-shrink: 0;
  }

  .tool-name {
    font-weight: $font-weight-medium;
    color: $color-primary;
  }

  .tool-result {
    color: var(--text-secondary);
    overflow-wrap: anywhere;
  }
}

.kb-call {
  width: 100%;
}

.kb-call-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.kb-count {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-left: auto;

  &.kb-error {
    color: $color-error;
  }
}

.kb-sources {
  margin-top: $spacing-2;
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.kb-source {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: $spacing-2;
  background-color: var(--bg-primary);
  border-radius: $radius-sm;
  border-left: 2px solid $color-primary;
}

.kb-source-collection {
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  color: $color-primary;
}

.kb-source-content {
  font-size: $font-size-xs;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: $spacing-3 $spacing-4;

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

.chat-input-area {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);

  :deep(.el-textarea__inner) {
    background-color: var(--bg-tertiary);
    border-color: var(--border-primary);
    border-radius: $radius-lg;
    resize: none;
    font-size: $font-size-sm;

    &:focus {
      border-color: $color-primary;
    }
  }
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: $spacing-3;
}

.input-hints {
  display: flex;
  align-items: center;
  gap: $spacing-4;

  .hint {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }

  .char-count {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.context-sidebar {
  width: 260px;
  background-color: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  overflow-y: auto;
}

.context-section {
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  h4 {
    font-size: $font-size-xs;
    font-weight: $font-weight-medium;
    color: var(--text-tertiary);
    margin: 0 0 $spacing-3;
    text-transform: uppercase;
  }
}

.context-item {
  display: flex;
  justify-content: space-between;
  font-size: $font-size-sm;
  margin-bottom: $spacing-2;
}

.context-label {
  color: var(--text-secondary);
}

.context-value {
  color: var(--text-primary);
}

.token-stats {
  display: flex;
  justify-content: space-between;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-top: $spacing-2;
}

.model-info {
  .context-item:last-child {
    margin-bottom: 0;
  }
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;

  .el-button {
    justify-content: flex-start;
  }
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-3;
  border-radius: $radius-md;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
  }
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.history-date {
  font-size: $font-size-sm;
  color: var(--text-primary);
}

.history-messages {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.no-history {
  text-align: center;
  padding: $spacing-8;
  color: var(--text-tertiary);
}

.full-prompt {
  max-height: 400px;
  overflow: auto;
  font-family: 'Fira Code', monospace;
  font-size: $font-size-sm;
  background-color: var(--bg-tertiary);
  padding: $spacing-4;
  border-radius: $radius-md;
  white-space: pre-wrap;
}
</style>



