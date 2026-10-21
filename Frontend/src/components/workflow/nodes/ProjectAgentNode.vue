<template>
  <SiteFactoryNodeShell
    :id="id"
    :data="data"
    :selected="selected"
    node-type="project_agent"
    :show-iframe="Boolean(previewUrl)"
  >
    <template #expanded>
      <div class="agent-panel">
        <div
          v-if="ragStatus === 'missing'"
          class="rag-banner"
        >
          <span>未配置向量库，对话记忆无法同步至知识库。</span>
          <router-link
            to="/knowledge"
            class="rag-link"
            @click.stop
          >
            去配置 →
          </router-link>
        </div>
        <div
          v-else-if="ragStatus === 'ready'"
          class="rag-banner ready"
        >
          <span>向量库已就绪，发送消息后将自动创建项目记忆集合。</span>
        </div>
        <div
          v-else-if="ragStatus === 'synced'"
          class="rag-banner synced"
        >
          <span>对话已同步至知识库</span>
          <router-link
            v-if="ragCollectionId"
            :to="`/knowledge?collection=${ragCollectionId}`"
            class="rag-link"
            @click.stop
          >
            查看 →
          </router-link>
        </div>
        <div
          ref="chatRef"
          class="chat-log"
        >
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="chat-line"
            :class="msg.role"
          >
            <span class="role">{{ msg.role === 'user' ? '你' : 'Agent' }}</span>
            <span class="text">{{ msg.content }}</span>
          </div>
          <p
            v-if="!messages.length"
            class="empty-hint"
          >
            输入修改需求，例如「把首页改成深色」
          </p>
        </div>
        <div
          v-if="lastReply.files_changed?.length"
          class="meta"
        >
          已修改：{{ lastReply.files_changed.join(', ') }}
        </div>
        <div class="composer">
          <input
            v-model="draft"
            class="chat-input"
            placeholder="描述要改的样式或文案…"
            :disabled="sending || !siteId"
            @keydown.enter.prevent="send"
            @click.stop
          >
          <button
            class="send-btn"
            type="button"
            :disabled="sending || !draft.trim() || !siteId"
            @click.stop="send"
          >
            {{ sending ? '…' : '发送' }}
          </button>
        </div>
        <p
          v-if="!siteId"
          class="warn"
        >
          等待上游网站生成完成后再对话
        </p>
        <a
          v-if="siteId"
          class="debugger-link"
          :href="`/projects/${siteId}`"
          @click.stop
        >打开完整 Debugger →</a>
      </div>
    </template>
  </SiteFactoryNodeShell>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import SiteFactoryNodeShell from './SiteFactoryNodeShell.vue'
import { websiteGeneratorApi } from '@/api/websiteGenerator'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const { updateNodeData } = useVueFlow()
const draft = ref('')
const sending = ref(false)
const chatRef = ref(null)
const localMessages = ref([])

const nodeOutput = computed(() => props.data.output || props.data.result || {})
const siteId = computed(() => {
  const cfg = props.data.config || {}
  return (
    cfg.generatedSiteId
    || nodeOutput.value.site_id
    || nodeOutput.value.siteId
    || null
  )
})
const lastReply = computed(() => nodeOutput.value.last_agent_reply || props.data.lastAgentReply || {})
const previewUrl = computed(() => nodeOutput.value.preview_url || nodeOutput.value.previewUrl || '')
const ragStatus = computed(() => (
  nodeOutput.value.rag_status
  || props.data.ragStatus
  || 'missing'
))
const ragCollectionId = computed(() => (
  nodeOutput.value.rag_collection_id
  || props.data.config?.ragCollectionId
  || ''
))

const messages = computed(() => {
  if (localMessages.value.length) return localMessages.value
  return props.data.messages || []
})

watch(
  () => nodeOutput.value.reply,
  (reply) => {
    if (reply && localMessages.value.length) {
      const last = localMessages.value[localMessages.value.length - 1]
      if (last?.role === 'assistant' && last.content === reply) return
      localMessages.value.push({ role: 'assistant', content: reply })
    }
  },
)

async function scrollChat() {
  await nextTick()
  if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight
}

async function send() {
  const text = draft.value.trim()
  if (!text || !siteId.value || sending.value) return

  localMessages.value = [...messages.value, { role: 'user', content: text }]
  draft.value = ''
  sending.value = true
  await scrollChat()

  try {
    const res = await websiteGeneratorApi.agentMessage(siteId.value, {
      content: text,
      qaProfile: props.data.config?.qaProfile || 'default',
      autoQaAfterEdit: props.data.config?.autoQaAfterEdit !== false,
      agentMode: props.data.config?.agentMode || 'auto',
    })
    localMessages.value.push({ role: 'assistant', content: res.reply || '已完成' })
    if (props.id) {
      updateNodeData(props.id, {
        output: {
          ...nodeOutput.value,
          reply: res.reply,
          qa_gate: res.qa_gate,
          gate: res.qa_gate,
          preview_url: res.preview_url,
          files_changed: res.files_changed,
          site_id: siteId.value,
          rag_status: res.rag_status,
          rag_collection_id: res.rag_collection_id,
        },
        messages: localMessages.value,
        ragStatus: res.rag_status,
        status: res.qa_gate === 'red' ? 'failed' : 'completed',
      })
    }
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || '发送失败'
    localMessages.value.push({ role: 'assistant', content: msg })
  } finally {
    sending.value = false
    await scrollChat()
  }
}
</script>

<style scoped lang="scss">
.agent-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chat-log {
  max-height: 140px;
  overflow-y: auto;
  padding: 6px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
  font-size: 11px;
}
.chat-line {
  margin-bottom: 6px;
  line-height: 1.4;
  &.user .role { color: #60a5fa; }
  &.assistant .role { color: #f472b6; }
  .role {
    font-weight: 600;
    margin-right: 4px;
  }
}
.empty-hint, .warn {
  margin: 0;
  font-size: 11px;
  color: var(--text-secondary, #a1a1aa);
}
.composer {
  display: flex;
  gap: 6px;
}
.chat-input {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.15);
  color: inherit;
  font-size: 11px;
}
.send-btn {
  padding: 4px 10px;
  border-radius: 6px;
  border: none;
  background: #ec4899;
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
.meta {
  font-size: 10px;
  color: #10b981;
}
.debugger-link {
  font-size: 10px;
  color: #ec4899;
  text-decoration: none;
  &:hover { text-decoration: underline; }
}
.rag-banner {
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 10px;
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  &.ready { background: rgba(59, 130, 246, 0.12); color: #93c5fd; }
  &.synced { background: rgba(16, 185, 129, 0.12); color: #6ee7b7; }
}
.rag-link {
  color: inherit;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  &:hover { text-decoration: underline; }
}
</style>
