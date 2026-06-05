<template>
  <div class="streaming-output-panel">
    <div class="stream-header">
      <div class="header-left">
        <span class="stream-badge">
          <Zap class="stream-icon" />
          实时输出
        </span>
        <span
          v-if="currentNode"
          class="current-node"
        >
          当前节点: {{ currentNode }}
        </span>
      </div>
      <div class="header-actions">
        <el-button
          size="small"
          text
          @click="$emit('copy')"
        >
          <Copy class="btn-icon-small" />
          复制
        </el-button>
      </div>
    </div>

    <div
      ref="contentRef"
      class="stream-content"
    >
      <pre
        class="content-text"
        v-html="formattedContent"
      />
      <span
        v-if="isStreaming"
        class="streaming-cursor"
      >|</span>
    </div>

    <div class="stream-footer">
      <span class="char-count">{{ content.length }} 字符</span>
      <span
        v-if="isStreaming"
        class="streaming-status"
      >
        <Loader class="loading-icon" />
        生成中...
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Zap, Copy, Loader } from 'lucide-vue-next'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  isStreaming: {
    type: Boolean,
    default: false
  },
  currentNode: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['copy'])

const contentRef = ref(null)

const formattedContent = computed(() => {
  if (!props.content) return ''

  let formatted = props.content
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Format markdown
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Line breaks
    .replace(/\n/g, '<br>')

  return formatted
})

function scrollToBottom() {
  if (contentRef.value) {
    contentRef.value.scrollTop = contentRef.value.scrollHeight
  }
}

watch(() => props.content, () => {
  if (props.isStreaming) {
    nextTick(() => scrollToBottom())
  }
})
</script>

<style lang="scss" scoped>
.streaming-output-panel {
  background: #1e1e2e;
  border-radius: 8px;
  overflow: hidden;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d2d3d;
  border-bottom: 1px solid #3d3d4d;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .stream-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(59, 130, 246, 0.2);
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    color: #60a5fa;

    .stream-icon {
      width: 14px;
      height: 14px;
    }
  }

  .current-node {
    font-size: 12px;
    color: #9ca3af;
  }
}

.stream-content {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #e5e7eb;

  .content-text {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;

    :deep(strong) {
      font-weight: 600;
      color: #f9fafb;
    }

    :deep(em) {
      font-style: italic;
      color: #d1d5db;
    }

    :deep(code) {
      background: rgba(255, 255, 255, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }

    :deep(pre) {
      background: rgba(0, 0, 0, 0.3);
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;

      code {
        background: transparent;
        padding: 0;
      }
    }
  }

  .streaming-cursor {
    display: inline-block;
    color: #60a5fa;
    font-weight: 700;
    animation: blink 1s infinite;
  }
}

.stream-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2d2d3d;
  border-top: 1px solid #3d3d4d;

  .char-count {
    font-size: 11px;
    color: #6b7280;
    font-family: 'JetBrains Mono', monospace;
  }

  .streaming-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #60a5fa;

    .loading-icon {
      width: 12px;
      height: 12px;
      animation: spin 1s linear infinite;
    }
  }
}

.btn-icon-small {
  width: 14px;
  height: 14px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
