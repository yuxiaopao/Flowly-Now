<template>
  <div
    class="stat-grid"
    :class="[`stat-grid--cols-${columns}`]"
  >
    <slot />
  </div>
</template>

<script setup>
defineProps({
  columns: {
    type: Number,
    default: 4,
    validator: (v) => [1, 2, 3, 4, 6].includes(v),
  },
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.stat-grid {
  display: grid;
  gap: $spacing-4;
  margin-bottom: var(--page-section-gap, #{$spacing-6});

  &--cols-4 {
    grid-template-columns: repeat(4, minmax(0, 1fr));

    @media (max-width: $breakpoint-lg) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    @media (max-width: $breakpoint-sm) {
      grid-template-columns: 1fr;
    }
  }

  &--cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));

    @media (max-width: $breakpoint-lg) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    @media (max-width: $breakpoint-sm) {
      grid-template-columns: 1fr;
    }
  }

  &--cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));

    @media (max-width: $breakpoint-sm) {
      grid-template-columns: 1fr;
    }
  }

  &--cols-6 {
    grid-template-columns: repeat(6, minmax(0, 1fr));

    @media (max-width: $breakpoint-xl) {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    @media (max-width: $breakpoint-md) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    @media (max-width: $breakpoint-sm) {
      grid-template-columns: 1fr;
    }
  }

  &--cols-1 {
    grid-template-columns: 1fr;
  }
}
</style>
