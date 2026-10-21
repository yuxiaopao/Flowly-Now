<template>
  <header
    class="page-header"
    :class="{
      'page-header--bordered': bordered,
      'page-header--compact': compact,
    }"
  >
    <div class="page-header__main">
      <p
        v-if="eyebrow"
        class="page-header__eyebrow"
      >
        {{ eyebrow }}
      </p>
      <h1 class="page-header__title">
        <slot name="title">
          {{ title }}
        </slot>
      </h1>
      <p
        v-if="subtitle || $slots.subtitle"
        class="page-header__subtitle"
      >
        <slot name="subtitle">
          {{ subtitle }}
        </slot>
      </p>
      <p
        v-if="meta || $slots.meta"
        class="page-header__meta"
      >
        <slot name="meta">
          {{ meta }}
        </slot>
      </p>
    </div>
    <div
      v-if="$slots.actions || $slots.default"
      class="page-header__actions"
    >
      <slot name="actions" />
      <slot />
    </div>
  </header>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
  subtitle: {
    type: String,
    default: '',
  },
  eyebrow: {
    type: String,
    default: '',
  },
  meta: {
    type: String,
    default: '',
  },
  bordered: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: $spacing-4;
  margin-bottom: var(--page-header-gap, #{$spacing-8});
  flex-wrap: wrap;

  &--bordered {
    padding-bottom: $spacing-5;
    border-bottom: 1px solid var(--border-primary);
  }

  &--compact {
    margin-bottom: var(--page-header-gap);

    .page-header__title {
      font-size: $font-size-xl;
    }
  }

  &__main {
    min-width: 0;
    flex: 1 1 16rem;
    overflow-wrap: anywhere;
  }

  &__eyebrow {
    margin: 0 0 $spacing-1;
    font-size: $font-size-xs;
    font-weight: $font-weight-semibold;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-secondary);
  }

  &__title {
    margin: 0;
    font-size: var(--page-title-size);
    font-weight: $font-weight-semibold;
    line-height: var(--page-title-line-height);
    color: var(--text-primary);
    letter-spacing: -0.015em;
  }

  &__subtitle {
    margin: var(--page-description-gap) 0 0;
    font-size: $font-size-sm;
    line-height: $line-height-relaxed;
    color: var(--text-secondary);
    max-width: 68ch;
  }

  &__meta {
    margin: $spacing-2 0 0;
    font-size: $font-size-sm;
    color: var(--text-tertiary);
  }

  &__actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: $spacing-3;
    min-width: 0;
    max-width: 100%;
    margin-left: auto;

    :deep(.el-button + .el-button) { margin-left: 0; }
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;

    &__main { flex-basis: auto; }

    &__actions {
      margin-left: 0;
      width: 100%;
    }
  }
}
</style>
