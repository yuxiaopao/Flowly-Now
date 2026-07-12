<template>
  <SiteFactoryNodeShell
    :id="id"
    :data="data"
    :selected="selected"
    node-type="site_code_review"
  />
</template>

<script setup>
import SiteFactoryNodeShell from './SiteFactoryNodeShell.vue'

defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})
</script>
