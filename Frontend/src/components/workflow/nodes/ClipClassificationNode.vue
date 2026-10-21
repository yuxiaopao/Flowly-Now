<template>
  <SiteFactoryNodeShell
    :id="id"
    :data="data"
    :selected="selected"
    node-type="clip_classification"
  >
    <template #expanded>
      <div
        v-if="classNames.length"
        class="info"
      >
        <p>类别：{{ classNames.join(', ') }}</p>
        <p v-if="accuracy != null">
          Accuracy {{ pct(accuracy) }}
        </p>
      </div>
    </template>
  </SiteFactoryNodeShell>
</template>

<script setup>
import { computed } from 'vue'
import SiteFactoryNodeShell from './SiteFactoryNodeShell.vue'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const nodeOutput = computed(() => props.data.output || props.data.result || {})
const classNames = computed(() => nodeOutput.value.class_names || nodeOutput.value.classNames || [])
const accuracy = computed(() => nodeOutput.value.metrics?.accuracy)

function pct(v) {
  return `${(Number(v) * 100).toFixed(0)}%`
}
</script>

<style scoped lang="scss">
.info {
  font-size: 11px;
  color: var(--text-secondary, #a1a1aa);
  p { margin: 0 0 4px; }
}
</style>
