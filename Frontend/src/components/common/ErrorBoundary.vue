<template>
  <slot v-if="!hasError" />
  <div
    v-else
    class="error-fallback"
  >
    <div class="error-icon-wrapper">
      <svg
        class="error-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
        />
        <line
          x1="12"
          y1="8"
          x2="12"
          y2="12"
        />
        <line
          x1="12"
          y1="16"
          x2="12.01"
          y2="16"
        />
      </svg>
    </div>
    <h3 class="error-title">
      组件渲染出错
    </h3>
    <p class="error-message">
      {{ errorMessage }}
    </p>
    <div class="error-actions">
      <el-button
        type="primary"
        @click="handleRetry"
      >
        <el-icon><Refresh /></el-icon>
        重试
      </el-button>
      <el-button @click="handleReset">
        <el-icon><RefreshLeft /></el-icon>
        重置
      </el-button>
    </div>
    <details
      v-if="errorInfo"
      class="error-details"
    >
      <summary>查看详细信息</summary>
      <pre>{{ errorInfo }}</pre>
    </details>
  </div>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { Refresh, RefreshLeft } from '@element-plus/icons-vue'

const props = defineProps({
  fallback: {
    type: Function,
    default: null
  },
  onError: {
    type: Function,
    default: null
  }
})

const emit = defineEmits(['retry', 'reset', 'error'])

const hasError = ref(false)
const errorMessage = ref('')
const errorInfo = ref('')

onErrorCaptured((err, instance, info) => {
  hasError.value = true
  errorMessage.value = err?.message || 'Unknown error'

  if (import.meta.env.DEV) {
    errorInfo.value = [
      `Error: ${err?.message || 'Unknown'}`,
      `Info: ${info}`,
      `Component: ${instance?.$options?.name || 'Unknown'}`,
    ].join('\n')
  }

  // Report to monitoring service
  if (props.onError) {
    props.onError(err, instance, info)
  } else {
    _reportError(err, info)
  }

  emit('error', { err, instance, info })
  return false
})

function handleRetry() {
  hasError.value = false
  errorMessage.value = ''
  errorInfo.value = ''
  emit('retry')
}

function handleReset() {
  hasError.value = false
  errorMessage.value = ''
  errorInfo.value = ''
  window.location.reload()
  emit('reset')
}

function _reportError(err, info) {
  try {
    if (typeof window !== 'undefined' && window.__REPORT_ERROR__) {
      window.__REPORT_ERROR__({
        type: 'component_error',
        message: err?.message || 'Unknown',
        stack: err?.stack || '',
        componentInfo: info,
        url: window.location.href,
        userAgent: navigator.userAgent,
      })
    }
  } catch {
    // Silently fail if reporting fails
  }
}
</script>

<style scoped>
.error-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 32px;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  text-align: center;
}

.error-icon-wrapper {
  margin-bottom: 16px;
}

.error-icon {
  width: 48px;
  height: 48px;
  color: var(--el-color-danger);
}

.error-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.error-message {
  margin: 0 0 24px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  max-width: 400px;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.error-details {
  width: 100%;
  max-width: 500px;
  margin-top: 16px;
  text-align: left;
}

.error-details summary {
  cursor: pointer;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.error-details pre {
  margin-top: 8px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  color: var(--el-text-color-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
