<template>
  <div class="page-empty-state">
    <div
      v-if="icon"
      class="page-empty-state__icon-wrap"
    >
      <component
        :is="icon"
        class="page-empty-state__icon"
      />
    </div>
    <h3
      v-if="title"
      class="page-empty-state__title"
    >
      {{ title }}
    </h3>
    <p
      v-if="description"
      class="page-empty-state__description"
    >
      {{ description }}
    </p>
    <div
      v-if="$slots.actions"
      class="page-empty-state__actions"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: [Object, Function],
    default: null,
  },
  title: {
    type: String,
    default: '',
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.page-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: $spacing-10 $spacing-6;
  color: var(--text-secondary);

  &__icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    width: $spacing-12;
    height: $spacing-12;
    margin-bottom: $spacing-4;
    border-radius: $radius-xl;
    background: var(--surface-muted);
    color: var(--text-secondary);
    border: 1px solid var(--border-primary);
  }

  &__icon {
    width: 28px;
    height: 28px;
  }

  &__title {
    margin: 0 0 $spacing-2;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }

  &__description {
    margin: 0 0 $spacing-5;
    max-width: 36ch;
    font-size: $font-size-sm;
    line-height: $line-height-relaxed;
    color: var(--text-secondary);
  }

  &__actions {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-3;
    justify-content: center;
  }
}
</style>
