<template>
  <span class="integration-logo">
    <img
      v-if="source && !failed"
      :src="source"
      :alt="name"
      @error="failed = true"
    >
    <Webhook
      v-else-if="service === 'custom'"
      aria-hidden="true"
    />
    <ImageOff
      v-else
      :aria-label="name"
    />
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Webhook, ImageOff } from 'lucide-vue-next'

const props = defineProps({ service: { type: String, required: true }, name: { type: String, required: true } })
const assets = import.meta.glob('/src/assets/integrations/*.{svg,png,ico,jpg}', { eager: true, query: '?url', import: 'default' })
const failed = ref(false)
const source = computed(() => Object.entries(assets).find(([path]) => path.split('/').at(-1).split('.')[0] === props.service)?.[1])
watch(() => props.service, () => { failed.value = false })
</script>

<style scoped lang="scss">
@use '@/assets/styles/variables.scss' as *;
.integration-logo {
  display: inline-flex;
  width: $spacing-12;
  height: $spacing-12;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  padding: $spacing-2;
  background: $color-white;
  border: 1px solid var(--el-border-color-light);
  border-radius: $radius-lg;
  img, svg { display: block; width: 100%; height: 100%; object-fit: contain; }
  svg { color: $color-secondary; }
}
</style>
