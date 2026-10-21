<template>
  <Teleport to="body">
    <Transition name="cg-assist-trigger">
      <button
        v-if="!visible"
        class="cg-assist-trigger"
        title="CodeGraph 分析助手"
        @click="openAssistant"
      >
        <div class="trigger-inner">
          <div class="trigger-logo-wrap">
            <FlowlyBot
              :size="BOT_AVATAR.triggerSize"
              follow
              decorative
            />
          </div>
        </div>
        <div class="trigger-ring" />
      </button>
    </Transition>

    <Transition name="cg-assist-panel">
      <div
        v-if="visible"
        class="cg-assist-panel"
        :style="panelStyle"
      >
        <header
          class="cg-assist-header"
          @mousedown="startDrag"
        >
          <div class="header-left">
            <FlowlyBot
              :state="asking ? 'thinking' : 'idle'"
              :size="BOT_AVATAR.size"
            />
            <div>
              <h4>分析助手</h4>
              <span :class="{ thinking: asking }">
                {{ asking ? '分析中…' : '可问跳转 / 依赖 / 入口' }}
              </span>
            </div>
          </div>
          <div class="header-actions">
            <button
              title="清空对话"
              @click="clearChat"
            >
              <Trash2 />
            </button>
            <button
              title="最小化"
              @click="visible = false"
            >
              <Minus />
            </button>
            <button
              title="关闭"
              @click="closeAssistant"
            >
              <X />
            </button>
          </div>
        </header>

        <div
          ref="messagesEl"
          class="cg-assist-messages"
        >
          <div
            v-if="messages.length === 0"
            class="welcome"
          >
            <FlowlyBot
              :size="BOT_AVATAR.welcomeSize"
              class="welcome-bot"
              follow
            />
            <h4>你好，我是 CodeGraph 分析助手</h4>
            <p>结合依赖图谱与源码检索，回答页面跳转、路由入口、模块依赖等问题，并给出文件与行号。</p>
            <div class="pills">
              <button
                v-for="item in suggestions"
                :key="item"
                @click="sendSuggestion(item)"
              >
                {{ item }}
              </button>
            </div>
          </div>

          <div
            v-for="msg in messages"
            :key="msg.id"
            class="msg"
            :class="msg.role"
          >
            <div class="bubble">
              <pre class="text">{{ msg.content }}</pre>
              <div
                v-if="msg.references?.length"
                class="refs"
              >
                <button
                  v-for="(reference, idx) in msg.references"
                  :key="`${reference.path}-${reference.startLine}-${idx}`"
                  class="ref-chip"
                  :title="reference.reason || reference.path"
                  @click="emitOpenRef(reference)"
                >
                  <FileCode />
                  <span class="ref-path">{{ shortPath(reference.path) }}</span>
                  <span
                    v-if="reference.startLine"
                    class="ref-line"
                  >:{{ reference.startLine }}{{ reference.endLine && reference.endLine !== reference.startLine ? `-${reference.endLine}` : '' }}</span>
                </button>
              </div>
              <div
                v-if="msg.graphPaths?.length"
                class="paths"
              >
                <div
                  v-for="(gp, gidx) in msg.graphPaths"
                  :key="gidx"
                  class="path-row"
                >
                  <GitBranch />
                  <span>{{ (gp.paths || []).join(' → ') }}</span>
                </div>
              </div>
              <div
                v-if="msg.source"
                class="meta"
              >
                {{ msg.source === 'llm' ? 'LLM' : msg.source === 'heuristic' ? '规则检索' : msg.source }}
              </div>
            </div>
          </div>

          <div
            v-if="asking"
            class="msg assistant"
          >
            <div class="bubble loading">
              <span class="dot" /><span class="dot" /><span class="dot" />
            </div>
          </div>
        </div>

        <footer class="cg-assist-footer">
          <div
            v-if="selectedHint"
            class="context-chip"
          >
            上下文：{{ selectedHint }}
          </div>
          <div class="input-row">
            <textarea
              v-model="draft"
              rows="2"
              placeholder="例如：CodeGraph 页面是怎么跳转打开的？对应哪些文件？"
              :disabled="asking || !projectId"
              @keydown.enter.exact.prevent="sendMessage"
            />
            <button
              class="send-btn"
              :disabled="asking || !draft.trim() || !projectId"
              @click="sendMessage"
            >
              <Send />
            </button>
          </div>
        </footer>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { FileCode, GitBranch, Minus, Send, Trash2, X } from 'lucide-vue-next'
import { askAssistant } from '@/api/codegraph'
import { useCodeGraphStore } from '@/stores/codeGraph'
import FlowlyBot from '@/components/common/FlowlyBot.vue'
import { BOT_AVATAR } from '@/config/botAvatar'

const props = defineProps({
  projectId: {
    type: [Number, String],
    default: null,
  },
  selectedNode: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['open-file', 'select-node'])

const store = useCodeGraphStore()
const visible = ref(false)
const asking = ref(false)
const draft = ref('')
const messages = ref([])
const messagesEl = ref(null)

const panelPos = ref({ x: null, y: null })
let dragState = null
let requestSeq = 0
let requestController = null

const suggestions = [
  '当前选中页面是如何被路由打开的？',
  '这个模块的跳转入口在哪些文件？',
  '从路由到页面组件的依赖链路是什么？',
  '哪些文件调用了 router.push / navigate？',
]

const selectedHint = computed(() => {
  const n = props.selectedNode
  if (!n?.path) return ''
  return n.path.length > 42 ? `…${n.path.slice(-40)}` : n.path
})

const panelStyle = computed(() => {
  if (panelPos.value.x == null || panelPos.value.y == null) {
    return { right: '24px', bottom: '24px' }
  }
  return {
    left: `${panelPos.value.x}px`,
    top: `${panelPos.value.y}px`,
    right: 'auto',
    bottom: 'auto',
  }
})

function shortPath(path) {
  if (!path) return ''
  const parts = String(path).replace(/\\/g, '/').split('/')
  if (parts.length <= 3) return parts.join('/')
  return `${parts[0]}/…/${parts.slice(-2).join('/')}`
}

function stripJsonFence(text) {
  if (!text) return ''
  return String(text).replace(/\n*```json\s*\{[\s\S]*?\}\s*```\s*$/i, '').trim()
}

function openAssistant() {
  visible.value = true
  nextTick(scrollToBottom)
}

function closeAssistant() {
  visible.value = false
}

function clearChat() {
  ++requestSeq
  requestController?.abort()
  asking.value = false
  messages.value = []
}

function sendSuggestion(text) {
  draft.value = text
  sendMessage()
}

function emitOpenRef(ref) {
  if (!ref?.path) return
  const node = store.nodes.find(n => n.path === ref.path)
  if (node) emit('select-node', node)
  emit('open-file', {
    path: ref.path,
    startLine: ref.startLine || ref.start_line || ref.line || 1,
    endLine: ref.endLine || ref.end_line || ref.startLine || ref.start_line || ref.line || 1,
  })
}

async function scrollToBottom() {
  await nextTick()
  const el = messagesEl.value
  if (el) el.scrollTop = el.scrollHeight
}

async function sendMessage() {
  const text = draft.value.trim()
  if (!text || asking.value || !props.projectId) return
  const seq = ++requestSeq
  requestController = new AbortController()
  const projectId = props.projectId

  const userMsg = {
    id: `u-${Date.now()}`,
    role: 'user',
    content: text,
  }
  messages.value.push(userMsg)
  draft.value = ''
  asking.value = true
  await scrollToBottom()

  const history = messages.value
    .filter(m => m.role === 'user' || m.role === 'assistant')
    .slice(0, -1)
    .slice(-6)
    .map(m => ({ role: m.role, content: m.content }))

  try {
    const res = await askAssistant(projectId, {
      message: text,
      history,
      selected_path: props.selectedNode?.path || undefined,
      selected_node_id: props.selectedNode?.id || undefined,
    }, { signal: requestController.signal })
    if (seq !== requestSeq) return
    const data = res?.data ?? res
    messages.value.push({
      id: `a-${Date.now()}`,
      role: 'assistant',
      content: stripJsonFence(data?.answer || data?.error || '未返回有效回答'),
      references: data?.references || [],
      graphPaths: data?.graphPaths || data?.graph_paths || [],
      source: data?.source || '',
    })
  } catch (err) {
    if (seq !== requestSeq || err.code === 'ERR_CANCELED') return
    messages.value.push({
      id: `e-${Date.now()}`,
      role: 'assistant',
      content: err?.response?.data?.error || err?.message || '助手请求失败，请稍后重试',
      references: [],
      source: 'error',
    })
  } finally {
    if (seq === requestSeq) {
      asking.value = false
      await scrollToBottom()
    }
  }
}

function startDrag(e) {
  if (e.button !== 0) return
  const panel = e.currentTarget?.parentElement
  if (!panel) return
  const rect = panel.getBoundingClientRect()
  dragState = {
    ox: e.clientX - rect.left,
    oy: e.clientY - rect.top,
  }
  panelPos.value = { x: rect.left, y: rect.top }
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', endDrag)
}

function onDrag(e) {
  if (!dragState) return
  const x = Math.min(window.innerWidth - 80, Math.max(8, e.clientX - dragState.ox))
  const y = Math.min(window.innerHeight - 80, Math.max(8, e.clientY - dragState.oy))
  panelPos.value = { x, y }
}

function endDrag() {
  dragState = null
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
}

watch(() => props.projectId, () => {
  clearChat()
  draft.value = ''
})

onUnmounted(() => {
  clearChat()
  endDrag()
})

defineExpose({ openAssistant, closeAssistant })
</script>

<style scoped lang="scss">
.cg-assist-trigger {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1200;
  width: 48px;
  height: 48px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light, #22d3ee) 100%);
  box-shadow: 0 4px 12px var(--color-primary-30, rgba(34, 211, 238, 0.3));
  cursor: pointer;
  user-select: none;
  transition: filter 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    filter: brightness(1.12);
    box-shadow: 0 6px 20px var(--color-primary-50, rgba(34, 211, 238, 0.45));
  }

  &:active {
    filter: brightness(0.95);
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
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: var(--bg-secondary, #0f172a);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .trigger-ring {
    position: absolute;
    inset: -4px;
    border: 2px solid var(--color-primary-30, rgba(34, 211, 238, 0.35));
    border-radius: 50%;
    pointer-events: none;
    animation: cg-ring-pulse 2s infinite;
  }
}

@keyframes cg-ring-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.1); }
}

.cg-assist-panel {
  position: fixed;
  z-index: 1201;
  width: min(420px, calc(100vw - 24px));
  height: min(640px, calc(100vh - 48px));
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  border: 1px solid rgba(34, 211, 238, 0.28);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(2, 12, 27, 0.98));
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
  overflow: hidden;
  color: #e2e8f0;
}

.cg-assist-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  cursor: grab;
  user-select: none;

  h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 650;
  }

  span {
    font-size: 11px;
    color: #94a3b8;

    &.thinking {
      color: #67e8f9;
    }
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-actions {
    display: flex;
    gap: 4px;

    button {
      display: grid;
      place-items: center;
      width: 28px;
      height: 28px;
      border: none;
      border-radius: 8px;
      background: transparent;
      color: #94a3b8;
      cursor: pointer;

      &:hover {
        background: rgba(148, 163, 184, 0.12);
        color: #e2e8f0;
      }

      :deep(svg) {
        width: 14px;
        height: 14px;
      }
    }
  }
}

.cg-assist-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(34, 211, 238, 0.35);
    border-radius: 999px;
  }
}

.welcome {
  .welcome-bot {
    margin-inline: auto;
  }
  padding: 8px 4px 4px;

  h4 {
    margin: 0 0 8px;
    font-size: 15px;
  }

  p {
    margin: 0 0 14px;
    font-size: 12px;
    line-height: 1.55;
    color: #94a3b8;
  }

  .pills {
    display: flex;
    flex-direction: column;
    gap: 8px;

    button {
      text-align: left;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid rgba(34, 211, 238, 0.18);
      background: rgba(34, 211, 238, 0.06);
      color: #cffafe;
      font-size: 12px;
      cursor: pointer;

      &:hover {
        border-color: rgba(34, 211, 238, 0.4);
        background: rgba(34, 211, 238, 0.12);
      }
    }
  }
}

.msg {
  display: flex;

  &.user {
    justify-content: flex-end;

    .bubble {
      background: rgba(34, 211, 238, 0.14);
      border-color: rgba(34, 211, 238, 0.28);
    }
  }

  &.assistant {
    justify-content: flex-start;
  }
}

.bubble {
  max-width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(30, 41, 59, 0.75);

  &.loading {
    display: inline-flex;
    gap: 5px;
    padding: 12px 16px;

    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #22d3ee;
      animation: cg-bounce 1s infinite ease-in-out;

      &:nth-child(2) { animation-delay: 0.15s; }
      &:nth-child(3) { animation-delay: 0.3s; }
    }
  }
}

.text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  color: #e2e8f0;
}

.refs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid rgba(45, 212, 191, 0.28);
  background: rgba(45, 212, 191, 0.08);
  color: #99f6e4;
  font-size: 11px;
  cursor: pointer;

  &:hover {
    border-color: rgba(45, 212, 191, 0.5);
    background: rgba(45, 212, 191, 0.14);
  }

  :deep(svg) {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
  }

  .ref-path {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ref-line {
    color: #5eead4;
    flex-shrink: 0;
  }
}

.paths {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.path-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;

  :deep(svg) {
    width: 12px;
    height: 12px;
    margin-top: 2px;
    color: #67e8f9;
    flex-shrink: 0;
  }
}

.meta {
  margin-top: 8px;
  font-size: 10px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.7);
}

.cg-assist-footer {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  padding: 10px 12px 12px;
}

.context-chip {
  margin-bottom: 8px;
  font-size: 11px;
  color: #67e8f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;

  textarea {
    flex: 1;
    resize: none;
    min-height: 56px;
    max-height: 120px;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(15, 23, 42, 0.8);
    color: #e2e8f0;
    font-size: 13px;
    line-height: 1.45;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: rgba(34, 211, 238, 0.45);
    }

    &:disabled {
      opacity: 0.55;
    }
  }
}

.send-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #0891b2, #0d9488);
  color: white;
  display: grid;
  place-items: center;
  cursor: pointer;
  flex-shrink: 0;

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  :deep(svg) {
    width: 16px;
    height: 16px;
  }
}

@keyframes cg-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

.cg-assist-trigger-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.cg-assist-trigger-leave-active {
  transition: all 0.2s ease-in;
}
.cg-assist-trigger-enter-from {
  opacity: 0;
  transform: scale(0) rotate(-180deg);
}
.cg-assist-trigger-leave-to {
  opacity: 0;
  transform: scale(0);
}

.cg-assist-panel-enter-active,
.cg-assist-panel-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.cg-assist-panel-enter-from,
.cg-assist-panel-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
</style>
