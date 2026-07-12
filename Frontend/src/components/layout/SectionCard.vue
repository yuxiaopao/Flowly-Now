<template>
  <AppCard
    :title="title"
    :icon="icon"
    :variant="variant"
    :size="size"
    class="section-card"
    :class="{ 'section-card--loading': loading }"
  >
    <template
      v-if="$slots.actions"
      #actions
    >
      <slot name="actions" />
    </template>

    <div
      v-if="loading"
      class="section-card__skeleton"
    >
      <el-skeleton
        :rows="skeletonRows"
        animated
      />
    </div>
    <slot v-else />
  </AppCard>
</template>

<script setup>
import AppCard from '@/components/common/AppCard.vue'

defineProps({
  title: {
    type: String,
    default: '',
  },
  icon: {
    type: [String, Object, Function],
    default: null,
  },
  variant: {
    type: String,
    default: 'default',
  },
  size: {
    type: String,
    default: 'default',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  skeletonRows: {
    type: Number,
    default: 4,
  },
})
</script>

<style lang="scss" scoped>
.section-card {
  &--loading {
    pointer-events: none;
  }

  &__skeleton {
    padding: 0.25rem 0;
  }
}
</style>
