<template>
  <el-input
    :model-value="modelValue"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    :clearable="clearable"
    :show-password="showPassword"
    :prefix-icon="prefixIconComponent"
    :suffix-icon="suffixIconComponent"
    :size="size"
    :class="['app-input', { 'app-input--error': hasError }]"
    @input="$emit('update:modelValue', $event)"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
  >
    <template
      v-if="$slots.prefix"
      #prefix
    >
      <slot name="prefix" />
    </template>
    <template
      v-if="$slots.suffix"
      #suffix
    >
      <slot name="suffix" />
    </template>
  </el-input>
</template>

<script setup>
import { computed } from 'vue'

defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: Boolean,
  readonly: Boolean,
  clearable: Boolean,
  showPassword: Boolean,
  prefixIcon: [String, Object],
  suffixIcon: [String, Object],
  size: {
    type: String,
    default: 'default'
  },
  hasError: Boolean
})

defineEmits(['update:modelValue', 'focus', 'blur'])

const prefixIconComponent = computed(() => null)
const suffixIconComponent = computed(() => null)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.app-input {
  border-radius: $radius-lg;

  :deep(.el-input__wrapper) {
    background-color: var(--input-bg);
    border-radius: $radius-lg;
    box-shadow: 0 0 0 1px var(--input-border) inset;
    transition: box-shadow $transition-fast;

    &:hover {
      box-shadow: 0 0 0 1px var(--border-hover) inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1.5px var(--input-focus-border) inset;
    }
  }

  :deep(.el-input__inner) {
    color: var(--text-primary);
    font-size: $font-size-sm;

    &::placeholder {
      color: var(--text-tertiary);
    }
  }

  :deep(.el-input__prefix),
  :deep(.el-input__suffix) {
    color: var(--text-tertiary);
  }

  &--error {
    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px var(--error) inset;
    }
  }
}
</style>
