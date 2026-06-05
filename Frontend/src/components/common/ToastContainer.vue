<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast"
      tag="div"
      class="toast-container"
    >
      <div
        v-for="toast in appStore.toasts"
        :key="toast.id"
        :class="['toast', `toast--${toast.type}`]"
        role="alert"
        @mouseenter="pauseToast(toast.id)"
        @mouseleave="resumeToast(toast.id)"
      >
        <component
          :is="getIcon(toast.type)"
          class="toast__icon"
        />
        <div class="toast__content">
          <p class="toast__message">
            {{ toast.message }}
          </p>
        </div>
        <button
          v-if="toast.closable"
          class="toast__close"
          aria-label="关闭"
          @click="removeToast(toast.id)"
        >
          <X />
        </button>
        <div
          v-if="toast.duration > 0"
          class="toast__progress"
          :class="`toast__progress--${toast.type}`"
          :data-toast-id="toast.id"
          :style="{ animationDuration: `${toast.duration}ms` }"
        />
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { watch } from 'vue'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-vue-next'

const appStore = useAppStore()
const timers = new Map()

const getIcon = (type) => {
  const icons = { success: CheckCircle, error: AlertCircle, warning: AlertTriangle, info: Info }
  return icons[type] || Info
}

const removeToast = (id) => {
  const timer = timers.get(id)
  if (timer !== undefined) {
    clearTimeout(timer)
    timers.delete(id)
  }
  appStore.removeToast(id)
}

const pauseToast = (id) => {
  const timerId = timers.get(id)
  if (timerId) {
    clearTimeout(timerId)
    timers.set(id, null)
  }
}

const resumeToast = (id) => {
  const toast = appStore.toasts.find(t => t.id === id)
  if (toast && toast.duration > 0) {
    const timerId = setTimeout(() => removeToast(id), toast.duration)
    timers.set(id, timerId)
  }
}

const onProgressDone = (id) => {
  const timer = timers.get(id)
  if (timer !== undefined) {
    clearTimeout(timer)
    timers.delete(id)
  }
}

watch(
  () => appStore.toasts.length,
  () => {
    for (const toast of appStore.toasts) {
      if (toast.duration > 0 && !timers.has(toast.id)) {
        const timerId = setTimeout(() => removeToast(toast.id), toast.duration)
        timers.set(toast.id, timerId)
      }
    }
  }
)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.toast-container {
  position: fixed;
  top: $spacing-6;
  right: $spacing-6;
  z-index: $z-toast;
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
  pointer-events: none;
}

.toast {
  --toast-accent: var(--info);

  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  min-width: 320px;
  max-width: 480px;
  padding: $spacing-4;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  color: var(--text-primary);

  &--success { --toast-accent: var(--success); border-left: 3px solid var(--success); }
  &--error   { --toast-accent: var(--error);   border-left: 3px solid var(--error); }
  &--warning { --toast-accent: var(--warning); border-left: 3px solid var(--warning); }
  &--info    { --toast-accent: var(--info);    border-left: 3px solid var(--info); }
}

.toast__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--toast-accent);
  filter: drop-shadow(0 0 4px var(--toast-accent));
}

.toast__content {
  flex: 1;
  min-width: 0;
}

.toast__message {
  margin: 0;
  font-size: $font-size-sm;
  color: var(--text-primary);
  line-height: $line-height-normal;
}

.toast__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: none;
  border: none;
  border-radius: $radius-md;
  color: var(--text-tertiary);
  cursor: pointer;
  transition:
    background-color $transition-fast,
    color $transition-fast,
    transform $transition-fast;
  flex-shrink: 0;

  &:hover {
    background-color: var(--surface-muted);
    color: var(--text-primary);
    transform: scale(1.1);
  }

  &:active {
    transform: scale(0.95);
  }

  svg {
    width: 16px;
    height: 16px;
  }
}

.toast-enter-active {
  animation: toast-in 0.32s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.toast-leave-active {
  animation: toast-out 0.22s ease-in forwards;
}

@keyframes toast-in {
  0% {
    opacity: 0;
    transform: translateX(120%) scale(0.92);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes toast-out {
  0% {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translateX(120%) scale(0.92);
  }
}

.toast__progress {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 3px;
  border-radius: 0 0 $radius-xl $radius-xl;
  background: var(--toast-accent);
  animation: toast-progress linear forwards;
  animation-play-state: running;
  transform-origin: left center;
  opacity: 0.8;
}

@keyframes toast-progress {
  from { width: 100%; }
  to   { width: 0%; }
}
</style>
