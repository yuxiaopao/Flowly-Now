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
      <pre class="content-text">{{ content }}</pre>
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
import { ref, watch, nextTick } from 'vue'
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

defineEmits(['copy'])

const contentRef = ref(null)

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
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  overflow: hidden;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);

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
    background: var(--info-bg);
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    color: var(--info);
    transition: background-color 0.2s ease;

    .stream-icon {
      width: 14px;
      height: 14px;
    }
  }

  .current-node {
    font-size: 12px;
    color: var(--code-muted);
  }
}

.stream-content {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--code-text);

  .content-text {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .streaming-cursor {
    display: inline-block;
    color: var(--color-primary);
    font-weight: 700;
    animation: blink 1s infinite;
  }
}

.stream-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--code-surface);
  border-top: 1px solid var(--code-border);

  .char-count {
    font-size: 11px;
    color: var(--code-muted);
    font-family: 'JetBrains Mono', monospace;
  }

  .streaming-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--color-primary);

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
