<template>
  <div
    :class="[
      'app-card',
      `app-card--${variant}`,
      `app-card--${size}`,
      { 'app-card--clickable': clickable || $attrs.onClick, 'app-card--bordered': bordered }
    ]"
    @click="handleClick"
  >
    <div
      v-if="$slots.header || title"
      class="app-card__header"
    >
      <slot name="header">
        <div class="app-card__header-content">
          <component
            :is="icon"
            v-if="icon"
            class="app-card__icon"
          />
          <h3 class="app-card__title">
            {{ title }}
          </h3>
        </div>
        <div
          v-if="$slots.actions"
          class="app-card__actions"
        >
          <slot name="actions" />
        </div>
      </slot>
    </div>

    <div
      class="app-card__body"
      :class="{ 'app-card__body--no-padding': noPadding }"
    >
      <slot />
    </div>

    <div
      v-if="$slots.footer"
      class="app-card__footer"
    >
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  icon: [String, Object],
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'bordered', 'elevated', 'outlined'].includes(v)
  },
  size: {
    type: String,
    default: 'default',
    validator: (v) => ['small', 'default', 'large'].includes(v)
  },
  clickable: Boolean,
  bordered: {
    type: Boolean,
    default: true
  },
  noPadding: Boolean
})

defineEmits(['click'])

function handleClick(e) {
  if (e?.target?.closest('.app-card__actions')) return
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.app-card {
  background-color: var(--bg-secondary);
  border-radius: $radius-xl;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;

  &--default {
    border: 1px solid var(--border-primary);
  }

  &--bordered {
    border: 1px solid var(--border-primary);
  }

  &--elevated {
    border: none;
    box-shadow: var(--shadow-md);
  }

  &--outlined {
    border: none;
    background-color: transparent;
  }

  &--clickable {
    cursor: pointer;

    &:hover {
      border-color: var(--border-hover);
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    &:active {
      transform: translateY(0);
    }
  }

  &--small {
    .app-card__header {
      padding: $spacing-3 $spacing-4;
    }

    .app-card__body {
      padding: $spacing-3 $spacing-4;
    }

    .app-card__footer {
      padding: $spacing-3 $spacing-4;
    }
  }

  &--default {
    .app-card__header {
      padding: $spacing-4 $spacing-5;
    }

    .app-card__body {
      padding: $spacing-5;
    }

    .app-card__footer {
      padding: $spacing-4 $spacing-5;
    }
  }

  &--large {
    .app-card__header {
      padding: $spacing-5 $spacing-6;
    }

    .app-card__body {
      padding: $spacing-6;
    }

    .app-card__footer {
      padding: $spacing-5 $spacing-6;
    }
  }
}

.app-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-primary);
}

.app-card__header-content {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.app-card__icon {
  width: 20px;
  height: 20px;
  color: $color-primary;
}

.app-card__title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0;
}

.app-card__actions {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.app-card__body {
  &--no-padding {
    padding: 0;
  }
}

.app-card__footer {
  border-top: 1px solid var(--border-primary);
  background-color: var(--bg-tertiary);
}
</style>
