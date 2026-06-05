<template>
  <div
    class="theme-switcher-container"
    :class="`theme-switcher-container--${variant}`"
  >
    <el-dropdown
      trigger="click"
      popper-class="theme-popper"
      @command="handleCommand"
    >
      <button
        class="theme-trigger"
        :title="currentTheme?.description"
        :aria-label="`当前主题：${currentTheme?.name || '主题'}`"
      >
        <span
          class="icon-backing"
          :class="`icon-backing--${appStore.theme}`"
        >
          <!-- Dark: crescent moon with star -->
          <svg
            v-if="appStore.theme === 'dark'"
            class="theme-svg"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M21.5 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21.5 12.79z"
              fill="currentColor"
              opacity="0.9"
            />
            <path
              d="M15.5 4.5l1.2 1.2-1.2 1.2-1.2-1.2 1.2-1.2zM18 9l.8.8-.8.8-.8-.8.8-.8z"
              fill="currentColor"
            />
          </svg>
          <!-- Light: radiant sun with arcs -->
          <svg
            v-else-if="appStore.theme === 'light'"
            class="theme-svg"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <circle
              cx="12"
              cy="12"
              r="5"
              stroke="currentColor"
              stroke-width="1.8"
            />
            <path
              d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            />
          </svg>
          <!-- Pure B&W: elegant half-circle split -->
          <svg
            v-else-if="appStore.theme === 'pure-bw'"
            class="theme-svg"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M12 22A10 10 0 0 1 2 12h10v10z"
              fill="currentColor"
            />
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="1.8"
            />
          </svg>
          <!-- High contrast: eye icon for accessibility -->
          <svg
            v-else-if="appStore.theme === 'high-contrast'"
            class="theme-svg"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
              stroke="currentColor"
              stroke-width="1.8"
            />
            <circle
              cx="12"
              cy="12"
              r="4"
              stroke="currentColor"
              stroke-width="1.8"
            />
            <circle
              cx="12"
              cy="12"
              r="1.5"
              fill="currentColor"
            />
          </svg>
        </span>
      </button>
      <template #dropdown>
        <el-dropdown-menu class="theme-menu">
          <div class="theme-menu-header">
            <span>选择主题</span>
          </div>
          <el-dropdown-item
            v-for="t in themes"
            :key="t.id"
            :command="t.id"
            class="theme-item"
            :class="{ active: appStore.theme === t.id }"
          >
            <div class="theme-item-content">
              <span
                class="icon-backing icon-backing--menu"
                :class="`icon-backing--${t.id}`"
              >
                <!-- Dark -->
                <svg
                  v-if="t.id === 'dark'"
                  class="item-svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M21.5 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21.5 12.79z"
                    fill="currentColor"
                    opacity="0.9"
                  />
                  <path
                    d="M15.5 4.5l1.2 1.2-1.2 1.2-1.2-1.2 1.2-1.2zM18 9l.8.8-.8.8-.8-.8.8-.8z"
                    fill="currentColor"
                  />
                </svg>
                <!-- Light -->
                <svg
                  v-else-if="t.id === 'light'"
                  class="item-svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="5"
                    stroke="currentColor"
                    stroke-width="1.8"
                  />
                  <path
                    d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                  />
                </svg>
                <!-- Pure B&W -->
                <svg
                  v-else-if="t.id === 'pure-bw'"
                  class="item-svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M12 22A10 10 0 0 1 2 12h10v10z"
                    fill="currentColor"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="1.8"
                  />
                </svg>
                <!-- High Contrast -->
                <svg
                  v-else-if="t.id === 'high-contrast'"
                  class="item-svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
                    stroke="currentColor"
                    stroke-width="1.8"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="4"
                    stroke="currentColor"
                    stroke-width="1.8"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="1.5"
                    fill="currentColor"
                  />
                </svg>
              </span>
              <div class="theme-item-info">
                <span class="theme-item-name">{{ t.name }}</span>
                <span class="theme-item-desc">{{ t.description }}</span>
              </div>
            </div>
            <span
              v-if="appStore.theme === t.id"
              class="theme-check-wrap"
            >
              <svg
                class="theme-check-svg"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <polyline
                  points="20 6 9 17 4 12"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  variant: {
    type: String,
    default: 'default'
  }
})

const appStore = useAppStore()
const themes = computed(() => appStore.themes)
const currentTheme = computed(() => appStore.currentTheme)

function handleCommand(themeId) {
  appStore.setTheme(themeId)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.theme-switcher-container {
  display: inline-flex;

  &--pill {
    padding: $spacing-1;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-xl;
    box-shadow: var(--shadow-sm);
  }
}

.theme-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: background-color $transition-fast, transform $transition-fast;

  &:hover {
    background: var(--bg-hover);
  }

  &:active {
    transform: scale(0.94);
  }
}

.icon-backing {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  flex-shrink: 0;
  transition:
    background-color $transition-normal,
    color $transition-normal,
    box-shadow $transition-normal,
    transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);

  &--menu {
    width: 34px;
    height: 34px;
  }

  &--dark,
  &--pure-bw {
    background: #050505;
    color: #fafafa;
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
  }

  &--light,
  &--high-contrast {
    background: #fafafa;
    color: #050505;
    box-shadow: 0 0 0 1px rgba(5, 5, 5, 0.18) inset;
  }

  &--high-contrast {
    box-shadow: 0 0 0 2px #050505 inset;
  }
}

.theme-svg,
.item-svg {
  width: 18px;
  height: 18px;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.item-svg {
  width: 19px;
  height: 19px;
}

.theme-trigger:hover .icon-backing {
  transform: rotate(12deg) scale(1.06);
}

.theme-menu {
  min-width: 268px !important;
  padding: $spacing-2 !important;
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border-primary) !important;
  border-radius: $radius-xl !important;
  box-shadow: var(--shadow-xl) !important;
}

.theme-menu-header {
  padding: $spacing-2 $spacing-3;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--border-primary);
  margin-bottom: $spacing-1;
}

.theme-item {
  padding: $spacing-2 $spacing-3 !important;
  margin: 2px 0 !important;
  border-radius: $radius-lg !important;
  height: auto !important;
  line-height: normal !important;
  background: transparent !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  cursor: pointer;
  transition:
    background-color $transition-fast,
    transform $transition-fast;

  &:hover {
    background: var(--bg-hover) !important;
    transform: translateX(2px);
  }

  &.active {
    background: var(--surface-accent) !important;
  }
}

.theme-item-content {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.theme-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.theme-item-name {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  line-height: 1.4;
}

.theme-item-desc {
  font-size: $font-size-xs;
  color: var(--text-secondary);
  line-height: 1.35;
}

.theme-check-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: $spacing-2;
  color: var(--text-primary);
}

.theme-check-svg {
  width: 15px;
  height: 15px;
}
</style>
