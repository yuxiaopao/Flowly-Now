<template>
  <div class="public-layout">
    <div class="public-container">
      <slot />
    </div>
    <ToastContainer />
  </div>
</template>

<script setup>
import ToastContainer from '@/components/common/ToastContainer.vue'
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.public-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: $spacing-4;
  position: relative;
  overflow: hidden;

  &::before,
  &::after {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  &::before {
    background: radial-gradient(
      ellipse 78% 52% at 50% -12%,
      var(--hero-glow) 0%,
      transparent 58%
    );
  }

  &::after {
    background-image:
      linear-gradient(var(--hero-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(circle at center, black 35%, transparent 80%);
  }
}

.public-container {
  width: 100%;
  max-width: 440px;
  position: relative;
  z-index: 1;
}
</style>
