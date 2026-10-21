<template>
  <div class="auth-robot-chat">
    <div class="auth-robot-chat__header">
      <FlowlyBot
        :state="loading ? 'thinking' : 'idle'"
        :size="BOT_AVATAR.sizes.md"
      />
      <span>与小流对话</span>
    </div>

    <form
      class="auth-robot-chat__form"
      @submit.prevent="handleSubmit"
    >
      <textarea
        ref="inputRef"
        v-model="draft"
        class="auth-robot-chat__input"
        :placeholder="placeholder"
        rows="2"
        :maxlength="maxLength"
        :disabled="loading"
        @keydown.enter.exact.prevent="handleSubmit"
      />
      <button
        type="submit"
        class="auth-robot-chat__send"
        :disabled="loading || !draft.trim()"
        title="发送 (Enter)"
      >
        <Loader2
          v-if="loading"
          class="auth-robot-chat__send-icon spin"
        />
        <Send
          v-else
          class="auth-robot-chat__send-icon"
        />
      </button>
    </form>

    <p class="auth-robot-chat__hint">
      按 Enter 发送，Shift+Enter 换行
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Send, Loader2 } from 'lucide-vue-next'
import FlowlyBot from '@/components/common/FlowlyBot.vue'
import { BOT_AVATAR } from '@/config/botAvatar'

defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
  placeholder: {
    type: String,
    default: '问我关于 Flowly 或登录注册的问题…',
  },
  maxLength: {
    type: Number,
    default: 500,
  },
})

const emit = defineEmits(['send'])

const draft = ref('')
const inputRef = ref(null)

function handleSubmit() {
  const text = draft.value.trim()
  if (!text) return
  emit('send', text)
  draft.value = ''
}

defineExpose({
  focus: () => inputRef.value?.focus(),
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.auth-robot-chat {
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    margin-bottom: $spacing-3;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
  }

  &__form {
    display: flex;
    gap: $spacing-2;
    align-items: flex-end;
  }

  &__input {
    flex: 1;
    min-height: 44px;
    max-height: 120px;
    padding: $spacing-3 $spacing-4;
    resize: vertical;
    border: 1px solid var(--border-primary);
    border-radius: $radius-lg;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: $font-size-sm;
    font-family: inherit;
    line-height: $line-height-normal;
    transition: border-color $transition-fast, box-shadow $transition-fast;

    &::placeholder {
      color: var(--text-tertiary);
    }

    &:focus {
      outline: none;
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-primary) 18%, transparent);
    }

    &:disabled {
      opacity: 0.65;
      cursor: not-allowed;
    }
  }

  &__send {
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: $radius-lg;
    background: var(--accent-primary);
    color: var(--text-inverse);
    cursor: pointer;
    transition: all $transition-fast;

    &:hover:not(:disabled) {
      filter: brightness(1.08);
      transform: translateY(-1px);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  &__send-icon {
    width: 18px;
    height: 18px;

    &.spin {
      animation: spin 0.8s linear infinite;
    }
  }

  &__hint {
    margin: $spacing-2 0 0;
    font-size: 11px;
    color: var(--text-tertiary);
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
