<template>
  <div
    :class="[
      'app-card',
      `app-card--${variant}`,
      `app-card--${size}`,
      { 'app-card--clickable': clickable || $attrs.onClick, 'app-card--bordered': bordered }
    ]"
    :tabindex="clickable ? 0 : undefined"
    :role="clickable ? 'button' : undefined"
    @keydown.enter.self="clickable && handleClick($event)"
    @keydown.space.self.prevent="clickable && handleClick($event)"
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

const emit = defineEmits(['click'])

function handleClick(e) {
  if (e?.target?.closest('.app-card__actions')) return
  emit('click', e)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.app-card {
  position: relative;
  background-color: var(--card-bg);
  background-image: var(--tech-card-highlight);
  border-radius: var(--radius-card, $radius-xl);
  overflow: hidden;
  transition: border-color 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);

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
      box-shadow: var(--shadow-lg);
    }

    &:active {
      background-color: var(--bg-hover);
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
      padding: var(--content-gap) var(--content-card-padding);
    }

    .app-card__body {
      padding: var(--content-card-padding);
    }

    .app-card__footer {
      padding: var(--content-gap) var(--content-card-padding);
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
  color: var(--tech-blue);
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
