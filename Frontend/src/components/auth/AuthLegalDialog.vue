<template>
  <el-dialog
    v-model="visible"
    :title="document?.title || title"
    width="min(680px, 92vw)"
    append-to-body
  >
    <template v-if="document">
      <p class="legal-version">
        版本：{{ document.version }}
      </p>
      <!-- HTML and Markdown both pass through DOMPurify before rendering. -->
      <!-- eslint-disable vue/no-v-html -->
      <div
        class="legal-content"
        v-html="content"
      />
      <!-- eslint-enable vue/no-v-html -->
    </template>
    <el-empty
      v-else
      description="管理员尚未发布此文档，请联系管理员了解相关条款。"
    />
    <template #footer>
      <el-button @click="visible = false">
        关闭
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

const visible = defineModel({ type: Boolean, default: false })
const props = defineProps({ document: { type: Object, default: null }, title: { type: String, default: '' } })
const content = computed(() => DOMPurify.sanitize(props.document?.content_html || marked.parse(props.document?.content_markdown || '')))
</script>

<style scoped>
.legal-version { color: var(--text-secondary); }
.legal-content { max-height: 55vh; overflow: auto; overflow-wrap: anywhere; line-height: 1.8; }
.legal-content :deep(img) { max-width: 100%; }
</style>
