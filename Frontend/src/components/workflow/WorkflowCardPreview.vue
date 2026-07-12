<template>
  <div
    class="workflow-card-preview"
    :class="{ 'is-empty': !hasScreenshot && (!nodes || nodes.length === 0) }"
  >
    <img
      v-if="hasScreenshot"
      :src="canvasPreview"
      alt="工作流预览"
      class="preview-screenshot"
      loading="lazy"
    >
    <div
      v-else-if="nodes && nodes.length > 0"
      class="preview-fallback-wrap"
    >
      <MiniWorkflowPreview
        :nodes="nodes"
        :edges="edges"
        class="preview-fallback"
      />
      <span class="preview-fallback-hint">保存后将显示编辑界面截图</span>
    </div>
    <div
      v-else
      class="preview-empty"
    >
      <GitBranch class="preview-empty-icon" />
      <span>空工作流</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { GitBranch } from 'lucide-vue-next'
import MiniWorkflowPreview from '@/components/workflow/MiniWorkflowPreview.vue'

const props = defineProps({
  canvasPreview: {
    type: String,
    default: '',
  },
  nodes: {
    type: Array,
    default: () => [],
  },
  edges: {
    type: Array,
    default: () => [],
  },
})

const hasScreenshot = computed(() => (
  typeof props.canvasPreview === 'string'
  && props.canvasPreview.startsWith('data:image')
))
</script>

<style lang="scss" scoped>
.workflow-card-preview {
  width: 100%;
  height: 120px;
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--canvas-bg, var(--bg-tertiary));
  border: 1px solid var(--border-primary);
  position: relative;
}

.preview-screenshot {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  display: block;
  background: #0a0a14;
}

.preview-fallback-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}

.preview-fallback {
  width: 100%;
  height: 100%;
  opacity: 0.85;
}

.preview-fallback-hint {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  text-align: center;
  font-size: 10px;
  color: var(--text-tertiary);
  pointer-events: none;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 100%;
  color: var(--text-tertiary);
  font-size: 11px;
}

.preview-empty-icon {
  width: 20px;
  height: 20px;
  opacity: 0.5;
}
</style>
