<template>
  <div
    :aria-busy="loading"
    class="stat-card"
    :class="`stat-card--${tone}`"
  >
    <div
      v-if="icon"
      class="stat-card__icon"
      aria-hidden="true"
    >
      <component :is="icon" />
    </div>
    <div class="stat-card__body">
      <span class="stat-card__label">{{ label }}</span>
      <el-skeleton
        v-if="loading"
        animated
        class="stat-card__loading"
      >
        <template #template>
          <el-skeleton-item variant="text" />
        </template>
      </el-skeleton>
      <span
        v-else
        class="stat-card__value"
      >{{ value }}</span>
      <div
        v-if="$slots.extra"
        class="stat-card__extra"
      >
        <slot name="extra" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  loading: Boolean,
  icon: { type: [Object, Function], default: null },
  tone: {
    type: String,
    default: 'primary',
    validator: value => ['primary', 'success', 'warning', 'danger', 'info', 'violet', 'neutral'].includes(value),
  },
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.stat-card {
  --stat-accent: var(--tech-blue);
  --stat-soft: var(--tech-blue-soft);
  position: relative; overflow: hidden;
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  padding: var(--content-card-padding);
  background: var(--card-bg); background-image: var(--tech-card-highlight);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-card);
  min-width: 0;
  &::before { content: ''; position: absolute; inset: 0; pointer-events: none; background: radial-gradient(ellipse at 100% 0%, var(--stat-soft), transparent 65%); }
  &--success { --stat-accent: var(--accent-emerald); --stat-soft: var(--accent-emerald-bg); }
  &--warning { --stat-accent: var(--warning); --stat-soft: var(--warning-bg); }
  &--danger { --stat-accent: var(--error); --stat-soft: var(--error-bg); }
  &--info { --stat-accent: var(--tech-cyan); --stat-soft: var(--tech-cyan-soft); }
  &--violet { --stat-accent: var(--tech-violet); --stat-soft: var(--tech-violet-soft); }
  &--neutral { --stat-accent: var(--text-secondary); --stat-soft: var(--surface-muted); }
  &__icon {
    position: relative; display: grid; place-items: center; width: var(--control-height); height: var(--control-height);
    color: var(--stat-accent); background: var(--stat-soft); border-radius: $radius-lg; flex-shrink: 0;
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--stat-accent) 20%, transparent);
    svg { width: $spacing-5; height: $spacing-5; }
  }
  &__body { position: relative; display: flex; flex-direction: column; min-width: 0; }
  &__label { color: var(--text-secondary); font-size: $font-size-xs; }
  &__value {
    margin-top: $spacing-1; color: var(--text-primary); font-size: $font-size-2xl; font-weight: $font-weight-semibold;
    font-variant-numeric: tabular-nums; font-family: var(--font-family-mono); line-height: $line-height-tight; overflow-wrap: anywhere;
  }
  &__extra { margin-top: $spacing-2; }
  &__loading { width: $spacing-16; margin-top: $spacing-1; height: $spacing-8; }
}
</style>
