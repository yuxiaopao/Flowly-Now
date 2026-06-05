<template>
  <Teleport to="body">
    <TransitionGroup
      name="modal-stack"
      tag="div"
      class="modal-stack"
    >
      <div
        v-for="modal in appStore.modals"
        :key="modal.id"
        class="modal-overlay"
        @click.self="handleOverlayClick(modal)"
      >
        <div
          class="modal-box"
          :style="{ width: modal.width || '480px' }"
        >
          <div
            v-if="modal.title"
            class="modal-header"
          >
            <h3 class="modal-title">
              {{ modal.title }}
            </h3>
            <button
              class="modal-close"
              @click="closeModal(modal)"
            >
              <X />
            </button>
          </div>

          <div class="modal-body">
            <slot :modal="modal">
              <p>{{ modal.message || modal.content }}</p>
            </slot>
          </div>

          <div
            v-if="modal.confirmText || modal.cancelText"
            class="modal-footer"
          >
            <el-button @click="handleCancel(modal)">
              {{ modal.cancelText || '取消' }}
            </el-button>
            <el-button
              v-if="modal.confirmText"
              :type="modal.confirmType || 'primary'"
              @click="handleConfirm(modal)"
            >
              {{ modal.confirmText }}
            </el-button>
          </div>
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { X } from 'lucide-vue-next'

const appStore = useAppStore()

const closeModal = (modal) => {
  appStore.closeModal(modal.id)
  modal.onCancel?.()
}

const handleConfirm = (modal) => {
  modal.onConfirm?.()
}

const handleCancel = (modal) => {
  modal.onCancel?.()
}

const handleOverlayClick = (modal) => {
  if (modal.closeOnOverlay !== false) {
    closeModal(modal)
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.modal-stack {
  position: fixed;
  inset: 0;
  z-index: 2500;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.modal-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  pointer-events: auto;
}

.modal-box {
  max-width: calc(100vw - 48px);
  max-height: calc(100vh - 48px);
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: $radius-2xl;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-4 $spacing-5;
  border-bottom: 1px solid var(--border-primary);
}

.modal-title {
  margin: 0;
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  border-radius: $radius-md;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: var(--surface-muted);
    color: var(--text-primary);
  }

  svg { width: 16px; height: 16px; }
}

.modal-body {
  flex: 1;
  padding: $spacing-5;
  overflow-y: auto;
  color: var(--text-secondary);
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-3;
  padding: $spacing-4 $spacing-5;
  border-top: 1px solid var(--border-primary);
  background: var(--bg-primary);
}

.modal-stack-enter-active {
  animation: modal-in 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-stack-leave-active {
  animation: modal-out 0.2s ease-in forwards;
}

.modal-stack-enter-active .modal-overlay {
  animation: overlay-in 0.28s ease;
}

.modal-stack-leave-active .modal-overlay {
  animation: overlay-out 0.2s ease forwards;
}

@keyframes modal-in {
  0% { opacity: 0; transform: scale(0.92) translateY(-12px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}

@keyframes modal-out {
  0% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(0.94) translateY(12px); }
}

@keyframes overlay-in {
  0% { opacity: 0; backdrop-filter: blur(0); }
  100% { opacity: 1; backdrop-filter: blur(4px); }
}

@keyframes overlay-out {
  0% { opacity: 1; }
  100% { opacity: 0; }
}
</style>
