<template>

  <div

    class="stat-card"

    :class="[`stat-card--${tone}`]"

  >

    <div

      class="stat-card__icon"

      :class="`stat-card__icon--${tone}`"

    >

      <component

        :is="icon"

        v-if="icon"

      />

    </div>

    <div class="stat-card__body">

      <span class="stat-card__value">{{ value }}</span>

      <span class="stat-card__label">{{ label }}</span>

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

  label: {

    type: String,

    required: true,

  },

  value: {

    type: [String, Number],

    required: true,

  },

  icon: {

    type: [Object, Function],

    default: null,

  },

  tone: {

    type: String,

    default: 'primary',

    validator: (v) => ['primary', 'success', 'warning', 'info', 'neutral'].includes(v),

  },

})

</script>



<style lang="scss" scoped>

@use '@/assets/styles/variables.scss' as *;



.stat-card {

  position: relative;

  display: flex;

  align-items: flex-start;

  gap: $spacing-4;

  padding: $spacing-5;

  background: var(--card-bg);

  border: 1px solid var(--card-border);

  border-radius: var(--radius-card, $radius-xl);

  box-shadow: var(--shadow-sm);

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

  }



  &::after {

    content: '';

    position: absolute;

    top: 0;

    left: 0;

    right: 0;

    height: 2px;

    opacity: 0.85;

    transition: opacity 0.25s ease;

  }



  &--primary::after { background: linear-gradient(90deg, var(--accent-blue), var(--accent-amber)); }

  &--success::after { background: linear-gradient(90deg, var(--accent-emerald), var(--accent-blue)); }

  &--warning::after { background: linear-gradient(90deg, var(--accent-amber), var(--accent-rose)); }

  &--info::after { background: linear-gradient(90deg, var(--accent-blue), var(--accent-emerald)); }

  &--neutral::after { background: var(--border-primary); opacity: 0.5; }



  &:hover {

    transform: translateY(-3px);

    box-shadow: var(--shadow-md);



    &::after {

      opacity: 1;

    }

  }



  &--primary:hover { border-color: var(--accent-blue-soft); }

  &--success:hover { border-color: var(--accent-emerald-soft); }

  &--warning:hover { border-color: var(--accent-amber-soft); }

  &--info:hover { border-color: var(--accent-blue-soft); }

  &--neutral:hover { border-color: var(--border-hover); }



  &__icon {

    position: relative;

    z-index: 1;

    display: flex;

    align-items: center;

    justify-content: center;

    width: 48px;

    height: 48px;

    border-radius: $radius-lg;

    flex-shrink: 0;



    svg {

      width: 22px;

      height: 22px;

    }



    &--primary {

      background: var(--color-primary-10);

      color: var(--color-primary);

      box-shadow: inset 0 0 0 1px var(--color-primary-20);

    }



    &--success {

      background: var(--accent-emerald-soft);

      color: var(--accent-emerald);

    }



    &--warning {

      background: var(--accent-amber-soft);

      color: var(--accent-amber);

    }



    &--info {

      background: var(--accent-blue-soft);

      color: var(--accent-blue);

    }



    &--neutral {

      background: var(--bg-tertiary);

      color: var(--text-secondary);

    }

  }



  &__body {

    position: relative;

    z-index: 1;

    display: flex;

    flex-direction: column;

    min-width: 0;

  }



  &__value {

    font-size: $font-size-2xl;

    font-weight: $font-weight-bold;

    line-height: 1.2;

    color: var(--text-primary);

    font-variant-numeric: tabular-nums;

    letter-spacing: -0.02em;

  }



  &__label {

    margin-top: 2px;

    font-size: $font-size-sm;

    color: var(--text-secondary);

  }



  &__extra {

    margin-top: $spacing-2;

  }

}



@media (prefers-reduced-motion: reduce) {

  .stat-card:hover {

    transform: none;

  }

}

</style>

