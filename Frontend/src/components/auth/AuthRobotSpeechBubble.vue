<template>
  <Transition name="robot-bubble">
    <div
      v-if="displayText"
      class="robot-speech-bubble"
      role="status"
      aria-live="polite"
    >
      <div class="robot-speech-bubble__avatar">
        <Bot class="robot-speech-bubble__icon" />
      </div>
      <div class="robot-speech-bubble__body">
        <span class="robot-speech-bubble__label">小流</span>
        <p
          v-if="loading"
          class="robot-speech-bubble__text robot-speech-bubble__text--loading"
        >
          <span /><span /><span />
        </p>
        <p
          v-else
          class="robot-speech-bubble__text"
        >
          {{ displayText }}
        </p>
      </div>
      <div class="robot-speech-bubble__tail" />
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import { Bot } from 'lucide-vue-next'

const props = defineProps({
  text: {
    type: String,
    default: '',
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const displayText = computed(() => props.text || (props.loading ? ' ' : ''))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.robot-speech-bubble {
  position: absolute;
  top: clamp(12%, 18vh, 22%);
  left: clamp(48%, 52vw, 58%);
  z-index: 4;
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  max-width: min(320px, 42vw);
  pointer-events: none;

  &__avatar {
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent-primary);
    color: var(--text-inverse);
    box-shadow: 0 4px 14px color-mix(in srgb, var(--accent-primary) 35%, transparent);
  }

  &__icon {
    width: 18px;
    height: 18px;
  }

  &__body {
    position: relative;
    flex: 1;
    min-width: 0;
    padding: $spacing-3 $spacing-4;
    background: color-mix(in srgb, var(--bg-secondary) 92%, transparent);
    border: 1px solid var(--border-primary);
    border-radius: $radius-xl;
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-md);
  }

  &__label {
    display: block;
    margin-bottom: $spacing-1;
    font-size: 11px;
    font-weight: $font-weight-semibold;
    color: var(--accent-primary);
    letter-spacing: 0.02em;
  }

  &__text {
    margin: 0;
    font-size: $font-size-sm;
    line-height: $line-height-relaxed;
    color: var(--text-primary);
    word-break: break-word;

    &--loading {
      display: flex;
      gap: 4px;
      align-items: center;
      min-height: 20px;

      span {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--accent-primary);
        animation: bubble-dot 1.2s ease-in-out infinite both;

        &:nth-child(1) { animation-delay: -0.24s; }
        &:nth-child(2) { animation-delay: -0.12s; }
      }
    }
  }

  &__tail {
    position: absolute;
    left: 42px;
    bottom: -8px;
    width: 14px;
    height: 14px;
    background: color-mix(in srgb, var(--bg-secondary) 92%, transparent);
    border-right: 1px solid var(--border-primary);
    border-bottom: 1px solid var(--border-primary);
    transform: rotate(45deg);
  }
}

@keyframes bubble-dot {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.robot-bubble-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.robot-bubble-leave-active {
  transition: all 0.2s ease;
}
.robot-bubble-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.94);
}
.robot-bubble-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}

@media (max-width: 1024px) {
  .robot-speech-bubble {
    top: 10%;
    left: auto;
    right: $spacing-4;
    max-width: min(280px, 75vw);
  }

  .robot-speech-bubble__tail {
    left: auto;
    right: 24px;
  }
}
</style>
