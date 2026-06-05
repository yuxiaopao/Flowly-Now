<template>
  <div class="settings-page">
    <div class="settings-container">
      <div class="settings-sidebar">
        <nav class="settings-nav">
          <router-link
            to="/settings/profile"
            class="nav-item"
            :class="{ active: activeTab === 'profile' }"
          >
            <User class="nav-icon" />
            个人资料
          </router-link>
          <router-link
            to="/settings/credentials"
            class="nav-item"
            :class="{ active: activeTab === 'credentials' }"
          >
            <Key class="nav-icon" />
            统一凭证管理
          </router-link>
          <router-link
            to="/settings/preferences"
            class="nav-item"
            :class="{ active: activeTab === 'preferences' }"
          >
            <Settings class="nav-icon" />
            偏好设置
          </router-link>
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
import { User, Key, Settings } from 'lucide-vue-next'

const route = useRoute()
const activeTab = computed(() => {
  const path = route.path
  if (path.includes('api-keys') || path.includes('credentials')) return 'credentials'
  if (path.includes('preferences')) return 'preferences'
  return 'profile'
})
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
  gap: $spacing-1;
}

.nav-item {
  display: flex;
  align-items: center;
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
