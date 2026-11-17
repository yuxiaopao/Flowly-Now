<template>
  <div
    class="auth-code"
    :class="{ 'auth-code--disabled': disabled }"
  >
    <div
      class="auth-code__cells"
      @paste="handlePaste"
    >
      <input
        v-for="(digit, index) in cells"
        :id="`${baseId}-${index}`"
        :key="index"
        ref="cellRefs"
        :value="digit"
        type="text"
        inputmode="numeric"
        autocomplete="one-time-code"
        maxlength="1"
        class="auth-code__cell"
        :class="{ 'auth-code__cell--filled': digit }"
        :disabled="disabled"
        :aria-label="`验证码第 ${index + 1} 位`"
        @input="handleInput(index, $event)"
        @keydown="handleKeydown(index, $event)"
        @focus="handleFocus"
      >
    </div>

    <button
      type="button"
      class="auth-code__send"
      :disabled="disabled || counting"
      @click="handleSend"
    >
      {{ counting ? `${remaining} 秒后重发` : sendLabel }}
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  length: { type: Number, default: 6 },
  disabled: Boolean,
  countdown: { type: Number, default: 60 },
  sendLabel: { type: String, default: '获取验证码' },
})

const emit = defineEmits(['update:modelValue', 'send'])

const baseId = `auth-code-${useId()}`
const cellRefs = ref([])
const cellValues = ref(Array.from({ length: props.length }, () => ''))
const remaining = ref(0)
let countdownTimer = null

const cells = computed(() => cellValues.value)
const counting = computed(() => remaining.value > 0)

watch(
  () => props.modelValue,
  (value) => {
    const digits = String(value ?? '').replace(/\D/g, '').slice(0, props.length)
    cellValues.value = Array.from({ length: props.length }, (_, index) => digits[index] || '')
  },
)

watch(
  () => props.length,
  () => {
    cellValues.value = Array.from({ length: props.length }, (_, index) => cellValues.value[index] || '')
  },
)

function emitValue() {
  emit('update:modelValue', cellValues.value.join(''))
}

function focusCell(index) {
  const cell = cellRefs.value?.[index]
  if (cell) {
    cell.focus()
    cell.select()
  }
}

function handleInput(index, event) {
  const raw = event.target.value
  const digit = raw.replace(/\D/g, '').slice(-1)
  if (event.target.value !== digit) event.target.value = digit
  cellValues.value[index] = digit
  emitValue()
  if (digit && index < props.length - 1) {
    focusCell(index + 1)
  }
}

function handleKeydown(index, event) {
  if (event.key === 'Backspace') {
    if (cellValues.value[index]) {
      cellValues.value[index] = ''
      emitValue()
    } else if (index > 0) {
      cellValues.value[index - 1] = ''
      emitValue()
      focusCell(index - 1)
    }
    return
  }

  if (event.key === 'ArrowLeft' && index > 0) {
    event.preventDefault()
    focusCell(index - 1)
  } else if (event.key === 'ArrowRight' && index < props.length - 1) {
    event.preventDefault()
    focusCell(index + 1)
  }
}

function handlePaste(event) {
  event.preventDefault()
  const text = event.clipboardData?.getData('text') || ''
  const digits = text.replace(/\D/g, '').slice(0, props.length)
  if (!digits) return
  cellValues.value = Array.from({ length: props.length }, (_, index) => digits[index] || '')
  emitValue()
  focusCell(Math.min(digits.length, props.length - 1))
}

function handleFocus(event) {
  event.target.select()
}

function handleSend() {
  if (counting.value || props.disabled) return
  emit('send')
  startCountdown()
}

function startCountdown() {
  remaining.value = Math.max(1, props.countdown)
  countdownTimer = setInterval(() => {
    remaining.value -= 1
    if (remaining.value <= 0) {
      remaining.value = 0
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

onBeforeUnmount(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.auth-code {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
  width: 100%;
}

.auth-code__cells {
  display: flex;
  gap: $spacing-2;
  width: 100%;
}

.auth-code__cell {
  flex: 1;
  min-width: 0;
  height: 52px;
  padding: 0;
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  text-align: center;
  transition: border-color $transition-fast, box-shadow $transition-fast, background-color $transition-fast;

  &:hover:not(:disabled) {
    border-color: var(--border-hover);
  }

  &:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 1.5px var(--input-focus-border) inset;
  }

  &--filled {
    border-color: var(--border-hover);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.auth-code__send {
  height: 44px;
  padding: 0 $spacing-4;
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  cursor: pointer;
  transition: border-color $transition-fast, background-color $transition-fast, color $transition-fast;

  &:hover:not(:disabled) {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-code {
    &__cell,
    &__send {
      transition: none !important;
    }
  }
}
</style>
