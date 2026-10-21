<template>
  <div
    class="workflow-card-preview"
    :class="{ 'is-empty': !hasScreenshot && !hasNodes }"
  >
    <img
      v-if="hasScreenshot"
      :src="canvasPreview"
      alt="工作流预览"
      class="preview-screenshot"
      loading="lazy"
    >
    <MiniWorkflowPreview
      v-else-if="hasNodes"
      :nodes="nodes"
      :edges="edges"
    />
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

const hasNodes = computed(() => Array.isArray(props.nodes) && props.nodes.length > 0)
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
  background: var(--canvas-bg);
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
  font-size: 12px;
}

.preview-empty-icon {
  width: 22px;
  height: 22px;
  opacity: 0.55;
}
</style>
