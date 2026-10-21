<template>
  <div
    class="page-shell"
    :class="[`page-shell--${width}`]"
  >
    <slot />
  </div>
</template>

<script setup>
defineProps({
  width: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'wide', 'narrow', 'full'].includes(v),
  },
})
</script>
