<template>
  <section
    class="rag-question"
    :aria-label="RAG_TEXT.askTab"
  >
    <p class="rag-hint">
      {{ RAG_TEXT.askHint }}
    </p>
    <el-input
      v-model="query"
      type="textarea"
      :rows="3"
      :placeholder="RAG_TEXT.queryPlaceholder"
      aria-label="知识库问题"
      @keydown.ctrl.enter="ask"
    />
    <el-button
      type="primary"
      :loading="loading"
      :disabled="!query.trim()"
      @click="ask"
    >
      提问
    </el-button>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <div
      v-if="answer"
      aria-live="polite"
    >
      <el-tag :type="answer.grounded ? 'success' : 'info'">
        {{ answer.grounded ? RAG_TEXT.answered : RAG_TEXT.noEvidence }}
      </el-tag>
      <p class="rag-answer">
        {{ answer.response }}
      </p>
      <h3 v-if="answer.sources?.length">
        {{ RAG_TEXT.sources }}
      </h3>
      <article
        v-for="source in answer.sources"
        :key="source.id"
        class="rag-source"
      >
        <el-button
          link
          type="primary"
          @click="$emit('open-document', source.metadata.doc_id)"
        >
          [{{ source.citation }}] {{ source.metadata.title }} · 分块 {{ source.metadata.chunk_index + 1 }}
        </el-button>
        <p>{{ source.content }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ragApi } from '@/api/rag'
import { RAG_TEXT } from '@/config/rag'

const props = defineProps({ collectionId: { type: String, required: true } })
defineEmits(['open-document'])
const query = ref('')
const loading = ref(false)
const answer = ref(null)
const error = ref('')
watch(() => props.collectionId, () => { answer.value = null; query.value = ''; error.value = '' })

async function ask() {
  if (loading.value || !query.value.trim()) return
  const collectionId = props.collectionId
  loading.value = true
  error.value = ''
  answer.value = null
  try {
    const result = await ragApi.askCollection(collectionId, { query: query.value.trim() })
    if (collectionId === props.collectionId) answer.value = result
  } catch (err) {
    if (collectionId === props.collectionId) {
      const detail = err.response?.data?.error || err.response?.data?.message
      error.value = typeof detail === 'string' ? detail : '问答失败，请检查模型服务和网络后重试。'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.rag-question { display: grid; gap: var(--spacing-4, 16px); max-width: var(--content-reading-width, 900px); }
.rag-question > .el-button { justify-self: start; }
.rag-hint { color: var(--text-secondary); margin: 0; }
.rag-answer, .rag-source p { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.7; }
.rag-source { border-top: 1px solid var(--border-primary); padding-block: var(--spacing-3, 12px); }
.rag-source .el-button { height: auto; white-space: normal; text-align: start; }
.rag-source p { color: var(--text-secondary); }
</style>
