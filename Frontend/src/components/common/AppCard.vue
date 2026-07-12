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
  title: {
    type: String,
    default: ''
  },
  icon: {
    type: [String, Object, Function],
    default: null
  },
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
  position: relative;
  background-color: var(--card-bg);
  border-radius: var(--radius-card, $radius-xl);
  overflow: hidden;
  transition: border-color 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: var(--card-inner-highlight);
    border-radius: inherit;
  }

  &--default {
    border: 1px solid var(--card-border);
    box-shadow: var(--shadow-sm);
  }

  &--bordered {
    border: 1px solid var(--card-border);
    box-shadow: var(--shadow-sm);
  }

  &--elevated {
    border: 1px solid var(--card-border);
    box-shadow: var(--shadow-md);
  }

  &--outlined {
    border: 1px solid var(--border-primary);
    background-color: transparent;
    box-shadow: none;
  }

  &--clickable {
    cursor: pointer;

    &:hover {
      border-color: var(--accent-blue-soft);
      transform: translateY(-3px);
      box-shadow: var(--shadow-lg);
    }

    &:active {
      transform: translateY(-1px);
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
  position: relative;
  z-index: 1;
}

.app-card__header-content {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.app-card__icon {
  width: 20px;
  height: 20px;
  color: var(--accent-blue);
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
  position: relative;
  z-index: 1;

  &--no-padding {
    padding: 0;
  }
}

.app-card__footer {
  border-top: 1px solid var(--border-primary);
  background-color: var(--bg-tertiary);
  position: relative;
  z-index: 1;
}
</style>
