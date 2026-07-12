<template>
  <div class="yolo-action-bar">
    <div class="action-left">
      <el-button
        v-if="canCancel"
        type="danger"
        plain
        :loading="cancelling"
        @click="$emit('cancel')"
      >
        <StopCircle :size="14" />
        停止训练
      </el-button>

      <el-button
        v-if="canRetry"
        type="warning"
        plain
        :loading="retrying"
        @click="$emit('retry')"
      >
        <RotateCcw :size="14" />
        重新训练
      </el-button>

      <el-dropdown
        v-if="canDownload"
        trigger="click"
        @command="handleDownload"
      >
        <el-button
          type="success"
          :loading="downloading"
        >
          <Download :size="14" />
          下载权重
          <ChevronDown :size="12" />
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="pt">
              best.pt (PyTorch)
            </el-dropdown-item>
            <el-dropdown-item command="last_pt">
              last.pt (最终权重)
            </el-dropdown-item>
            <el-dropdown-item
              command="onnx"
              :disabled="!hasOnnx"
            >
              best.onnx
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="action-right">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { StopCircle, RotateCcw, Download, ChevronDown } from 'lucide-vue-next'

defineProps({
  canCancel: { type: Boolean, default: false },
  canRetry: { type: Boolean, default: false },
  canDownload: { type: Boolean, default: false },
  hasOnnx: { type: Boolean, default: false },
})

const emit = defineEmits(['cancel', 'retry', 'download'])

const cancelling = ref(false)
const retrying = ref(false)
const downloading = ref(false)

function handleDownload(artifact) {
  emit('download', artifact)
}

defineExpose({ cancelling, retrying, downloading })
</script>

<style scoped>
.yolo-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.action-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
