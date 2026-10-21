<template>
  <div class="page-toolbar">
    <div class="page-toolbar__filters">
      <slot />
    </div>
    <div
      v-if="$slots.actions"
      class="page-toolbar__actions"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--content-control-gap);
  margin-bottom: var(--page-section-gap);
  min-width: 0;

  &__filters, &__actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--content-control-gap);
    min-width: 0;
    max-width: 100%;
  }

  &__filters { flex: 1; }

  // Slotted controls use one width scale without affecting dialog fields.
  &__filters :deep(.el-input) {
    width: var(--content-search-width);
    max-width: 100%;
  }
  &__filters :deep(.el-select) {
    width: var(--content-filter-width);
    max-width: 100%;
  }
  &__filters :deep(.el-date-editor) {
    width: var(--content-date-width);
    max-width: 100%;
    flex-grow: 0;
  }
  &__filters :deep(.el-radio-button__inner) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: var(--control-height);
  }
  :deep(.el-button + .el-button) { margin-left: 0; }

  @media (max-width: $breakpoint-md) {
    &__filters { flex-basis: 100%; }
    &__filters :deep(.el-input), &__filters :deep(.el-date-editor) {
      width: 100%;
    }
    &__filters :deep(.el-select) {
      flex: 1 1 var(--content-filter-width);
    }
    &__filters :deep(.el-radio-button__inner) {
      min-height: var(--control-height-large);
    }
  }
}
</style>
