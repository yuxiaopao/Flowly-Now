<template>
  <el-form-item
    class="auth-field"
    :class="{
      'auth-field--focused': focused,
      'auth-field--floating': floating,
      'auth-field--password': password,
      'auth-field--has-prefix': hasPrefix,
    }"
    :prop="prop"
    :error="externalError"
  >
    <div class="auth-field__control">
      <el-input
        :id="inputId"
        ref="inputRef"
        class="auth-field__input"
        :model-value="modelValue"
        :type="resolvedType"
        :placeholder="resolvedPlaceholder"
        :aria-label="label || placeholder"
        :disabled="disabled"
        :clearable="clearable"
        :autocomplete="autocomplete"
        :size="size"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      >
        <template
          v-if="hasPrefix"
          #prefix
        >
          <slot name="prefix" />
        </template>
        <template #suffix>
          <slot name="suffix" />
          <button
            v-if="password"
            type="button"
            class="auth-field__toggle"
            :aria-label="visible ? '隐藏密码' : '显示密码'"
            :aria-pressed="visible"
            @click="toggleVisibility"
          >
            <EyeOff
              v-if="visible"
              class="auth-field__toggle-icon"
              aria-hidden="true"
            />
            <Eye
              v-else
              class="auth-field__toggle-icon"
              aria-hidden="true"
            />
          </button>
        </template>
      </el-input>

      <label
        v-if="label"
        :for="inputId"
        class="auth-field__label"
        :class="{ 'auth-field__label--float': floating }"
      >
        {{ label }}<span
          v-if="required"
          class="auth-field__star"
          aria-hidden="true"
        >*</span><span
          v-if="optional"
          class="auth-field__optional"
        >（选填）</span>
      </label>
    </div>

    <div
      v-if="strength"
      class="auth-field__strength"
      aria-hidden="true"
    >
      <div class="auth-field__strength-track">
        <div
          class="auth-field__strength-fill"
          :class="strengthInfo.level"
          :style="{ width: strengthInfo.percent }"
        />
      </div>
      <span
        v-if="strengthInfo.text"
        class="auth-field__strength-text"
        :class="strengthInfo.level"
      >{{ strengthInfo.text }}</span>
    </div>

    <div
      v-if="help"
      class="auth-field__help"
    >
      {{ help }}
    </div>
  </el-form-item>
</template>

<script setup>
import { computed, ref, useId, useSlots } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'

const props = defineProps({
  label: { type: String, default: '' },
  prop: { type: String, default: '' },
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  disabled: Boolean,
  clearable: Boolean,
  password: Boolean,
  strength: Boolean,
  trim: Boolean,
  help: { type: String, default: '' },
  minPasswordLength: { type: Number, default: 8 },
  externalError: { type: String, default: '' },
  required: Boolean,
  optional: Boolean,
  size: { type: String, default: 'large' },
})

const emit = defineEmits(['update:modelValue', 'focus', 'blur'])

const slots = useSlots()
const uid = useId()
const inputRef = ref(null)
const focused = ref(false)
const visible = ref(false)

const inputId = computed(() => `auth-field-${uid}`)
const hasPrefix = computed(() => Boolean(slots.prefix))
const floating = computed(() => focused.value || String(props.modelValue ?? '').length > 0)
const resolvedType = computed(() => {
  if (!props.password) return props.type
  return visible.value ? 'text' : 'password'
})
const resolvedPlaceholder = computed(() => (props.label ? ' ' : props.placeholder))

const strengthInfo = computed(() => {
  const value = String(props.modelValue ?? '')
  const minLength = Math.max(1, props.minPasswordLength)
  let score = 0
  if (value.length >= minLength) score++
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++
  if (/[0-9]/.test(value)) score++
  if (/[^A-Za-z0-9]/.test(value)) score++

  const percent = `${(score / 4) * 100}%`
  if (score <= 1) return { percent, level: 'weak', text: value ? '较弱' : '' }
  if (score <= 3) return { percent, level: 'medium', text: '中等' }
  return { percent, level: 'strong', text: '较强' }
})

function handleInput(value) {
  emit('update:modelValue', props.trim ? String(value ?? '').trim() : value)
}

function handleFocus(event) {
  focused.value = true
  emit('focus', event)
}

function handleBlur(event) {
  focused.value = false
  emit('blur', event)
}

function toggleVisibility() {
  visible.value = !visible.value
  inputRef.value?.focus()
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.auth-field {
  :deep(.el-form-item__content) {
    display: block;
    line-height: $line-height-normal;
  }

  :deep(.el-form-item__error) {
    position: static;
    padding-top: $spacing-1;
    font-size: $font-size-xs;
    line-height: $line-height-normal;
    color: var(--error);
  }

  &__control {
    position: relative;
  }

  &__input {
    :deep(.el-input__wrapper) {
      padding: 0 $spacing-4;
      background-color: var(--bg-tertiary);
      border-radius: $radius-lg;
      box-shadow: 0 0 0 1px var(--border-primary) inset;
      transition: box-shadow $transition-fast, background-color $transition-fast;

      &:hover {
        box-shadow: 0 0 0 1px var(--border-hover) inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1.5px var(--input-focus-border) inset;
      }
    }

    :deep(.el-input__inner) {
      height: 44px;
      color: var(--text-primary);
      font-size: $font-size-sm;

      &::placeholder {
        color: transparent;
      }
    }

    :deep(.el-input__prefix),
    :deep(.el-input__suffix) {
      color: var(--text-tertiary);
    }
  }

  &__label {
    position: absolute;
    left: $spacing-4;
    top: 50%;
    transform: translateY(-50%);
    max-width: calc(100% - #{$spacing-10});
    font-size: $font-size-sm;
    line-height: $line-height-tight;
    color: var(--text-tertiary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    pointer-events: none;
    transition: transform $transition-fast, top $transition-fast, font-size $transition-fast, color $transition-fast;

    &--float {
      top: 8px;
      transform: none;
      font-size: $font-size-xs;
      color: var(--text-secondary);
    }
  }

  &--has-prefix &__label {
    left: 44px;
    max-width: calc(100% - 60px);
  }

  &--focused &__label {
    color: var(--color-primary-light);
  }

  &__toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    margin-right: -12px;
    padding: 0;
    border: 0;
    border-radius: $radius-md;
    background: transparent;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: color $transition-fast;

    &:hover {
      color: var(--text-primary);
    }

    &:focus-visible {
      outline: 2px solid var(--color-primary);
      outline-offset: -2px;
    }
  }

  &__toggle-icon {
    width: 18px;
    height: 18px;
  }

  &__strength {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    margin-top: $spacing-2;
    padding: 0 4px;
  }

  &__strength-track {
    flex: 1;
    height: 4px;
    background: var(--toast-progress-track);
    border-radius: $radius-full;
    overflow: hidden;
  }

  &__strength-fill {
    height: 100%;
    border-radius: $radius-full;
    transition: width 0.3s ease, background-color 0.3s ease;

    &.weak {
      background: var(--error);
    }

    &.medium {
      background: var(--warning);
    }

    &.strong {
      background: var(--success);
    }
  }

  &__strength-text {
    font-size: $font-size-xs;
    font-weight: $font-weight-semibold;
    min-width: 32px;
    text-align: right;

    &.weak {
      color: var(--error);
    }

    &.medium {
      color: var(--warning);
    }

    &.strong {
      color: var(--success);
    }
  }

  &__help {
    margin-top: $spacing-2;
    padding: 0 4px;
    font-size: $font-size-xs;
    line-height: $line-height-normal;
    color: var(--text-tertiary);
  }

  &__star {
    margin-left: 2px;
    color: var(--error);
  }

  &__optional {
    margin-left: $spacing-1;
    color: var(--text-tertiary);
    font-size: $font-size-xs;
  }

  &.is-error {
    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px var(--error) inset;
    }

    .auth-field__label {
      color: var(--error);
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-field {
    &__label,
    &__toggle,
    &__strength-fill {
      transition: none !important;
    }

    &__input {
      :deep(.el-input__wrapper) {
        transition: none !important;
      }
    }
  }
}
</style>
