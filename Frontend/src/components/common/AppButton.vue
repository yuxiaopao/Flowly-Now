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
    @click="$emit('click', $event)"
  >
    <span
      v-if="$slots.default"
      class="app-button__content"
    >
      <slot />
    </span>
  </el-button>
</template>

<script setup>
import { computed } from 'vue'

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

defineEmits(['click'])

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
@use 'sass:color';
@use '@/assets/styles/variables.scss' as *;

.app-button {
  font-weight: 500;
  border-radius: $radius-lg;
  transition: all 0.15s ease;
  letter-spacing: 0.01em;

  &--primary {
    background-color: var(--button-primary-bg);
    border: 1.5px solid transparent;
    color: var(--button-primary-text);
    box-shadow: var(--button-primary-shadow, 0 1px 3px rgba(0, 0, 0, 0.12));

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--button-primary-hover-bg);
      color: var(--button-primary-text);
      transform: translateY(-1px);
      box-shadow: var(--button-primary-shadow, 0 4px 12px rgba(0, 0, 0, 0.2));
    }

    &:active:not(:disabled) {
      transform: translateY(0);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
  }

  &--secondary {
    background-color: var(--bg-tertiary);
    border: 1.5px solid var(--border-primary);
    color: var(--text-primary);

    &:hover:not(:disabled) {
      background-color: var(--bg-hover);
      border-color: var(--border-hover);
      color: var(--text-primary);
      transform: translateY(-1px);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
    }
  }

  &--success {
    background-color: var(--button-primary-bg);
    border: 1.5px solid var(--success);
    color: var(--button-primary-text);

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--success);
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
    }
  }

  &--warning {
    background-color: var(--button-primary-bg);
    border: 1.5px solid var(--warning);
    color: var(--button-primary-text);

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--warning);
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
    }
  }

  &--error {
    background-color: var(--button-primary-bg);
    border: 1.5px solid var(--error);
    color: var(--button-primary-text);

    &:hover:not(:disabled) {
      background-color: var(--button-primary-hover-bg);
      border-color: var(--error);
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
    }
  }

  &--ghost {
    background-color: transparent;
    border: 1.5px solid var(--border-primary);
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
  gap: 6px !important;
}

.app-button__content {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
}
</style>
