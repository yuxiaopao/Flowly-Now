<template>
  <div
    class="node-type-badge"
    :class="{ compact }"
    :style="badgeStyle"
  >
    <component
      :is="nodeIcon"
      v-if="nodeIcon"
      class="badge-icon"
      :style="{ color: nodeColor }"
    />
    <span :style="{ color: nodeColor }">{{ displayLabel }}</span>
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { useNodePresentation } from '@/composables/useNodePresentation'

const props = defineProps({
  nodeType: {
    type: String,
    required: true,
  },
  /** 覆盖 registry 标签（极少使用） */
  label: {
    type: String,
    default: '',
  },
  compact: {
    type: Boolean,
    default: false,
  },
})

const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(toRef(props, 'nodeType'))

const displayLabel = computed(() => props.label || nodeLabel.value)

const badgeStyle = computed(() => ({
  backgroundColor: `${nodeColor.value}22`,
  borderColor: nodeColor.value,
}))
</script>

<style scoped lang="scss">
.node-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border: 1px solid;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;

  &.compact {
    padding: 2px 8px;
    font-size: 9px;
    border-radius: 12px;
  }

  .badge-icon {
    width: 11px;
    height: 11px;
    flex-shrink: 0;
  }
}
</style>
