<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="visible"
        class="confirm-overlay"
        @click.self="handleCancel"
      >
        <div
          class="confirm-dialog"
          :class="`confirm-dialog--${confirmType}`"
        >
          <div class="confirm-header">
            <component
              :is="headerIcon"
              class="confirm-icon"
            />
            <h3 class="confirm-title">
              {{ title }}
            </h3>
          </div>

          <div class="confirm-body">
            <p class="confirm-message">
              {{ message }}
            </p>
          </div>

          <div class="confirm-footer">
            <el-button
              size="large"
              @click="handleCancel"
            >
              {{ cancelText }}
            </el-button>
            <el-button
              size="large"
              :type="buttonType"
              @click="handleConfirm"
            >
              {{ confirmText }}
            </el-button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  AlertCircle, CheckCircle, AlertTriangle, Info,
  Trash2, Edit3, ShieldAlert, Settings
} from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '确定要执行此操作吗？' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  confirmType: { type: String, default: 'primary' }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const buttonType = computed(() => {
  const map = {
    danger: 'danger',
    warning: 'warning',
    success: 'success',
    primary: 'primary'
  }
  return map[props.confirmType] || 'primary'
})

const headerIcon = computed(() => {
  const map = {
    danger: Trash2,
    warning: AlertTriangle,
    success: CheckCircle,
    primary: Info
  }
  return map[props.confirmType] || Info
})

const handleConfirm = () => {
  emit('confirm')
  visible.value = false
}

const handleCancel = () => {
  emit('cancel')
  visible.value = false
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.confirm-dialog {
  width: 440px;
  max-width: calc(100vw - 48px);
  background: var(--bg-elevated);
  border-radius: $radius-2xl;
  border: 1px solid var(--border-primary);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  overflow: hidden;

  &--danger {
    border-top: 3px solid var(--error);
    .confirm-icon { color: var(--error); }
  }
  &--warning {
    border-top: 3px solid var(--warning);
    .confirm-icon { color: var(--warning); }
  }
  &--success {
    border-top: 3px solid var(--success);
    .confirm-icon { color: var(--success); }
  }
  &--primary {
    border-top: 3px solid var(--primary);
    .confirm-icon { color: var(--primary); }
  }
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-5 $spacing-5 $spacing-4;
}

.confirm-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.confirm-title {
  margin: 0;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
}

.confirm-body {
  padding: 0 $spacing-5 $spacing-5;
}

.confirm-message {
  margin: 0;
  font-size: $font-size-sm;
  color: var(--text-secondary);
  line-height: $line-height-relaxed;
}

.confirm-footer {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-3;
  padding: $spacing-4 $spacing-5;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-primary);
}

.modal-fade-enter-active {
  animation: modal-in 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-fade-leave-active {
  animation: modal-out 0.2s ease-in forwards;
}

@keyframes modal-in {
  0% { opacity: 0; transform: scale(0.92) translateY(-8px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}

@keyframes modal-out {
  0% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(0.95) translateY(8px); }
}
</style>
