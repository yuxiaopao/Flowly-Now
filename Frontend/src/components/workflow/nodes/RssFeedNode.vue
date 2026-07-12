<template>
  <div
    class="core-node rss-feed-node"
    :class="{ selected }"
    @click.stop="$emit('select')"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />
    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" compact />
    </div>
    <div class="node-body">
      <div
        class="node-icon-wrapper"
        :style="{ backgroundColor: nodeColor + '15' }"
      >
        <component
          :is="nodeIcon"
          :size="18"
          :style="{ color: nodeColor }"
        />
      </div>
      <div class="node-info">
        <div class="node-label">
          {{ data.label || nodeLabel }}
        </div>
        <div class="node-url">
          {{ urlPreview }}
        </div>
      </div>
    </div>
    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Rss } from 'lucide-vue-next'
import { truncateText } from '@/composables/useNodeResultDisplay'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const NODE_TYPE = 'rss_feed'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)
defineEmits(['select'])


const urlPreview = computed(() => truncateText(props.data?.config?.url || '未配置 URL', 36))
</script>

<style lang="scss" scoped>
.core-node {
  background: linear-gradient(145deg, #431407 0%, #0f172a 100%);
  border: 2px solid v-bind(nodeColor);
  border-radius: 12px;
  min-width: 170px;
  max-width: 240px;
  box-shadow: 0 0 16px rgba(249, 115, 22, 0.12);
  cursor: pointer;
}
.node-header { padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.node-type-badge {
  display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px;
  border: 1px solid; border-radius: 12px; font-size: 9px; font-weight: 700;
}
.node-body { display: flex; gap: 8px; padding: 8px 10px; align-items: center; }
.node-icon-wrapper { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
.node-label { font-size: 12px; font-weight: 600; color: #e2e8f0; }
.node-url { font-size: 10px; color: #94a3b8; margin-top: 2px; }
</style>
