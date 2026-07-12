<template>
  <div class="editor-layout">
    <slot />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  // 编辑器布局下隐藏顶部栏等
  document.body.classList.add('editor-mode')
})

onUnmounted(() => {
  document.body.classList.remove('editor-mode')
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.editor-layout {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
  z-index: $z-fixed;
}
</style>
