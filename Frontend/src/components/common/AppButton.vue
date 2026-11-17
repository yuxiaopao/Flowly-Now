<template>
  <el-button
    :type="buttonType"
    :size="size"
    :disabled="disabled || loading"
    :loading="loading"
    :icon="iconComponent"
    :circle="circle"
    :round="round"
    :plain="plain"
    :text="text"
    :bg="bg"
    :native-type="nativeType"
    :class="['app-button', `app-button--${variant}`, { 'app-button--loading': loading }]"
    @click="handleClick"
  >
    <span
      v-if="$slots.default"
      class="app-button__content"
    >
      <slot />
    </span>
    <span
      ref="rippleLayer"
      aria-hidden="true"
      class="app-button__ripple-layer"
    />
  </el-button>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'success', 'warning', 'error', 'ghost'].includes(v)
  },
  size: {
    type: String,
    default: 'default',
    validator: (v) => ['small', 'default', 'large'].includes(v)
  },
  nativeType: {
    type: String,
    default: 'button',
    validator: (v) => ['button', 'submit', 'reset'].includes(v)
  },
  disabled: Boolean,
  loading: Boolean,
  icon: {
    type: [String, Object, Function],
    default: null
  },
  circle: Boolean,
  round: Boolean,
  plain: Boolean,
  text: Boolean,
  bg: Boolean
})

const emit = defineEmits(['click'])

const rippleLayer = ref(null)

function handleClick(event) {
  spawnRipple(event)
  emit('click', event)
}

function spawnRipple(event) {
  if (props.disabled || props.loading) return

  const layer = rippleLayer.value
  const button = event?.currentTarget
  if (!layer || !button) return

  const rect = button.getBoundingClientRect()
  if (!rect.width || !rect.height) return

  const size = Math.max(rect.width, rect.height) * 2
  const fromCenter = !event || event.detail === 0
  const originX = fromCenter ? rect.left + rect.width / 2 : event.clientX
  const originY = fromCenter ? rect.top + rect.height / 2 : event.clientY

  const ripple = document.createElement('span')
  ripple.className = 'app-button__ripple'
  ripple.style.width = `${size}px`
  ripple.style.height = `${size}px`
  ripple.style.left = `${originX - rect.left - size / 2}px`
  ripple.style.top = `${originY - rect.top - size / 2}px`

  const removeRipple = () => ripple.remove()
  ripple.addEventListener('animationend', removeRipple, { once: true })
  ripple.addEventListener('animationcancel', removeRipple, { once: true })
  window.setTimeout(removeRipple, 600)

  layer.appendChild(ripple)
}

const BUTTON_TYPE_MAP = {
  primary: 'primary',
  secondary: '',
  success: 'success',
  warning: 'warning',
  error: 'danger',
  ghost: ''
}

const buttonType = computed(() => BUTTON_TYPE_MAP[props.variant] ?? 'primary')

const iconComponent = computed(() => {
  if (!props.icon) return null
  if (typeof props.icon === 'function') return props.icon
  if (typeof props.icon === 'object') return props.icon
  return null
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.app-button {
  font-weight: 500;
  border-radius: $radius-lg;
  position: relative;
  overflow: hidden;
  transition: background-color $transition-fast, border-color $transition-fast, color $transition-fast;
  letter-spacing: 0;

  &--primary {
    background-color: var(--button-primary-bg);
    border: 1px solid var(--tech-button-border);
    color: var(--button-primary-text);
    box-shadow: var(--button-primary-shadow, 0 1px 3px rgba(0, 0, 0, 0.12));

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--button-primary-hover-bg);
      color: var(--button-primary-text);
      box-shadow: var(--button-primary-shadow, 0 4px 12px rgba(0, 0, 0, 0.2));
    }

    &:active:not(:disabled) {
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
  }

  &--secondary {
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);

    &:hover:not(:disabled) {
      background-color: var(--bg-hover);
      border-color: var(--border-hover);
      color: var(--text-primary);
    }

    &:active:not(:disabled) {
    }
  }

  &--success {
    background-color: var(--button-primary-bg);
    border: 1px solid var(--success);
    color: var(--button-primary-text);

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--success);
      box-shadow: var(--shadow-sm);
    }

    &:active:not(:disabled) {
    }
  }

  &--warning {
    background-color: var(--button-primary-bg);
    border: 1px solid var(--warning);
    color: var(--button-primary-text);

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--warning);
      box-shadow: var(--shadow-sm);
    }

    &:active:not(:disabled) {
    }
  }

  &--error {
    background-color: var(--button-primary-bg);
    border: 1px solid var(--error);
    color: var(--button-primary-text);

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--error);
      box-shadow: var(--shadow-sm);
    }

    &:active:not(:disabled) {
    }
  }

  &--ghost {
    background-color: transparent;
    border: 1px solid var(--border-primary);
    color: var(--text-secondary);

    &:hover:not(:disabled) {
      background-color: var(--bg-hover);
      border-color: var(--border-hover);
      color: var(--text-primary);
    }
  }

  &--loading {
    cursor: wait;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

:deep(.el-button__content) {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: $spacing-2 !important;
}

.app-button__content {
  display: inline-flex !important;
  align-items: center !important;
  gap: $spacing-2 !important;
}

// ============================================
// 按压回弹 + 波纹跟手（尊重减少动效偏好）
// ============================================

.app-button__ripple-layer {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  overflow: hidden;
  pointer-events: none;
}

.app-button__ripple {
  position: absolute;
  border-radius: 50%;
  background-color: currentColor;
  transform: scale(0);
  opacity: 0;
  pointer-events: none;
}

@media (prefers-reduced-motion: no-preference) {
  .app-button {
    transition: transform 0.35s $ease-spring,
                background-color $transition-fast,
                border-color $transition-fast,
                color $transition-fast;

    &:active:not(:disabled) {
      transform: scale(0.96);
      transition: transform 0.08s var(--flowly-ease-out),
                  background-color $transition-fast,
                  border-color $transition-fast,
                  color $transition-fast;
    }
  }

  .app-button__ripple {
    animation: flowly-ripple 0.5s var(--flowly-ease-out) forwards;
  }
}

@keyframes flowly-ripple {
  from { transform: scale(0); opacity: 0.35; }
  to   { transform: scale(1); opacity: 0; }
}
</style>
