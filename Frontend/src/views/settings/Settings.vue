<template>
  <div class="settings-page">
    <div class="settings-container">
      <div class="settings-sidebar">
        <nav class="settings-nav">
          <template
            v-for="item in navItems"
            :key="item.key"
          >
            <router-link
              :to="item.to"
              class="nav-item"
              :class="{ active: activeTab === item.key }"
              :title="item.description"
            >
              <component
                :is="item.icon"
                class="nav-icon"
              />
              <div class="nav-text">
                <span class="nav-label">{{ item.label }}</span>
                <span class="nav-desc">{{ item.description }}</span>
              </div>
            </router-link>
          </template>
        </nav>
      </div>

      <div class="settings-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  PERSONAL_CENTER_NAV_ITEMS,
  resolvePersonalCenterActiveKey,
} from '@/config/userNavigation'

const route = useRoute()

const navItems = PERSONAL_CENTER_NAV_ITEMS

const activeTab = computed(() => resolvePersonalCenterActiveKey(route.path))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.settings-page {
  max-width: 1200px;
  margin: 0 auto;
}

.settings-container {
  display: flex;
  gap: $spacing-6;
}

.settings-sidebar {
  width: 240px;
  flex-shrink: 0;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.nav-item {
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  padding: $spacing-3 $spacing-4;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: $radius-lg;
  transition: background-color $transition-fast, color $transition-fast, border-color $transition-fast;
  border: 1px solid transparent;

  &:hover {
    background-color: var(--surface-muted);
    color: var(--text-primary);
  }

  &.active {
    background-color: var(--accent-muted);
    color: var(--text-primary);
    border-color: var(--border-primary);
  }
}

.nav-icon {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  flex-shrink: 0;
}

.nav-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nav-label {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: inherit;
}

.nav-desc {
  font-size: $font-size-xs;
  line-height: 1.4;
  color: var(--text-tertiary);
}

.settings-content {
  flex: 1;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-6;
  box-shadow: var(--shadow-sm);
}
</style>
