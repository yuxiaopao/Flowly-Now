<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    :fullscreen="fullscreen"
    :close-on-click-modal="closeOnClickModal"
    :close-on-press-escape="closeOnPressEscape"
    :show-close="showClose"
    :class="['app-modal', `app-modal--${size}`]"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="handleOpen"
    @opened="$emit('opened', $event)"
    @close="$emit('close', $event)"
    @closed="handleClosed"
  >
    <!-- Top accent bar -->
    <template
      v-if="accentType && accentType !== 'default'"
      #header
    >
      <div class="app-modal__header">
        <component
          :is="icon"
          v-if="icon"
          class="app-modal__icon"
          :class="`app-modal__icon--${accentType}`"
        />
        <span class="app-modal__title">{{ title }}</span>
      </div>
    </template>
    <template
      v-else
      #header
    >
      <div class="app-modal__header">
        <component
          :is="icon"
          v-if="icon"
          class="app-modal__icon"
        />
        <span class="app-modal__title">{{ title }}</span>
      </div>
    </template>

    <div class="app-modal__body">
      <slot />
    </div>

    <template
      v-if="$slots.footer"
      #footer
    >
      <div class="app-modal__footer">
        <slot name="footer" />
      </div>
    </template>

    <!-- Top color accent bar -->
    <div
      v-if="accentType && accentType !== 'default'"
      class="app-modal__accent-bar"
      :class="`app-modal__accent-bar--${accentType}`"
    />

    <!-- Bottom progress bar for auto-close -->
    <div
      v-if="showProgress && autoClose > 0"
      ref="progressBar"
      class="app-modal__progress"
      :class="`app-modal__progress--${accentType || 'default'}`"
      :style="{ animationDuration: `${autoClose}ms` }"
    />
  </el-dialog>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: {
    type: String,
    default: ''
  },
  icon: [String, Object],
  width: {
    type: String,
    default: '500px'
  },
  size: {
    type: String,
    default: 'default',
    validator: (v) => ['small', 'default', 'large', 'full'].includes(v)
  },
  fullscreen: Boolean,
  closeOnClickModal: {
    type: Boolean,
    default: false
  },
  closeOnPressEscape: {
    type: Boolean,
    default: true
  },
  showClose: {
    type: Boolean,
    default: true
  },
  accentType: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'success', 'warning', 'error', 'info'].includes(v)
  },
  autoClose: {
    type: Number,
    default: 0
  },
  showProgress: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:modelValue',
  'open',
  'opened',
  'close',
  'closed'
])

const progressBar = ref(null)
let autoCloseTimer = null
let progressRaf = null

function handleOpen() {
  emit('open')
  if (props.showProgress && props.autoClose > 0) {
    startProgress()
  }
}

function handleClosed() {
  stopProgress()
  emit('closed')
}

function startProgress() {
  stopProgress()
  if (!progressBar.value) return

  progressBar.value.style.animationPlayState = 'running'

  autoCloseTimer = setTimeout(() => {
    emit('update:modelValue', false)
  }, props.autoClose)
}

function stopProgress() {
  if (autoCloseTimer) {
    clearTimeout(autoCloseTimer)
    autoCloseTimer = null
  }
  if (progressRaf) {
    cancelAnimationFrame(progressRaf)
    progressRaf = null
  }
}

watch(() => props.modelValue, (val) => {
  if (!val) {
    stopProgress()
  }
})

onBeforeUnmount(() => {
  stopProgress()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

// Accent bar colors per theme type
$accent-colors: (
  'success': var(--success),
  'warning': var(--warning),
  'error': var(--error),
  'info': var(--info),
  'default': var(--text-primary),
);

.app-modal {
  --el-dialog-bg-color: var(--bg-secondary);
  --el-dialog-title-font-size: #{$font-size-lg};

  border-radius: $radius-xl;
  overflow: hidden;

  &:hover {
    .app-modal__progress {
      animation-play-state: paused;
    }
  }

  :deep(.el-dialog) {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-xl;
    box-shadow: var(--shadow-xl);
    transition: box-shadow $transition-normal, transform $transition-normal;
  }

  :deep(.el-dialog__header) {
    padding: $spacing-5;
    margin: 0;
    border-bottom: 1px solid var(--border-primary);
  }

  :deep(.el-dialog__body) {
    padding: $spacing-5;
    color: var(--text-primary);
  }

  :deep(.el-dialog__footer) {
    padding: $spacing-4 $spacing-5;
    border-top: 1px solid var(--border-primary);
    background-color: var(--bg-tertiary);
  }

  :deep(.el-dialog__headerbtn) {
    top: $spacing-4;
    right: $spacing-4;
    width: 32px;
    height: 32px;

    .el-dialog__close {
      color: var(--text-secondary);
      transition: color $transition-fast;

      &:hover {
        color: var(--text-primary);
      }
    }
  }

  &--small {
    :deep(.el-dialog) {
      max-width: 400px;
    }
  }

  &--default {
    :deep(.el-dialog) {
      max-width: 600px;
    }
  }

  &--large {
    :deep(.el-dialog) {
      max-width: 900px;
    }
  }

  &--full {
    :deep(.el-dialog) {
      width: 95vw;
      max-width: 1400px;
      height: 90vh;
    }
  }
}

.app-modal__header {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.app-modal__icon {
  width: 22px;
  height: 22px;
  color: var(--accent-primary);

  &--success { color: var(--success); }
  &--warning { color: var(--warning); }
  &--error { color: var(--error); }
  &--info { color: var(--info); }
}

.app-modal__title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
}

.app-modal__body {
  max-height: 60vh;
  overflow-y: auto;
}

.app-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: $spacing-3;
}

// Top accent bar — colored strip at the top of the modal
.app-modal__accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: $radius-xl $radius-xl 0 0;

  &--success {
    background: linear-gradient(90deg, var(--success) 0%, color-mix(in srgb, var(--success) 60%, white 40%) 100%);
    box-shadow: 0 0 12px 0 var(--success);
  }

  &--warning {
    background: linear-gradient(90deg, var(--warning) 0%, color-mix(in srgb, var(--warning) 60%, white 40%) 100%);
    box-shadow: 0 0 12px 0 var(--warning);
  }

  &--error {
    background: linear-gradient(90deg, var(--error) 0%, color-mix(in srgb, var(--error) 60%, white 40%) 100%);
    box-shadow: 0 0 12px 0 var(--error);
  }

  &--info {
    background: linear-gradient(90deg, var(--info) 0%, color-mix(in srgb, var(--info) 60%, white 40%) 100%);
    box-shadow: 0 0 12px 0 var(--info);
  }
}

// Bottom progress bar — countdown timer
.app-modal__progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 0 0 $radius-xl $radius-xl;
  animation: modal-progress linear forwards;
  animation-play-state: running;
  transform-origin: left center;

  &--success {
    background: linear-gradient(90deg, var(--success) 0%, color-mix(in srgb, var(--success) 60%, white 40%) 100%);
    box-shadow: 0 0 8px 0 var(--success);
  }

  &--warning {
    background: linear-gradient(90deg, var(--warning) 0%, color-mix(in srgb, var(--warning) 60%, white 40%) 100%);
    box-shadow: 0 0 8px 0 var(--warning);
  }

  &--error {
    background: linear-gradient(90deg, var(--error) 0%, color-mix(in srgb, var(--error) 60%, white 40%) 100%);
    box-shadow: 0 0 8px 0 var(--error);
  }

  &--info {
    background: linear-gradient(90deg, var(--info) 0%, color-mix(in srgb, var(--info) 60%, white 40%) 100%);
    box-shadow: 0 0 8px 0 var(--info);
  }

  &--default {
    background: linear-gradient(90deg, var(--text-primary) 0%, var(--text-secondary) 100%);
  }
}

@keyframes modal-progress {
  from { width: 100%; opacity: 1; }
  to   { width: 0%;   opacity: 0.6; }
}
</style>
