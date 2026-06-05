<template>
  <img
    :src="currentLogo"
    :alt="alt"
    :class="$attrs.class"
  >
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import logoBlack from '@/assets/logos/logo.png'
import logoWhite from '@/assets/logos/logow.png'

defineOptions({
  inheritAttrs: false
})

const props = defineProps({
  alt: {
    type: String,
    default: ''
  }
})

const appStore = useAppStore()

// Light themes: logoBlack (dark logo on light background)
// Dark themes: logoWhite (white logo on dark background)
const currentLogo = computed(() => {
  const lightThemes = ['light']
  return lightThemes.includes(appStore.theme) ? logoBlack : logoWhite
})
</script>
