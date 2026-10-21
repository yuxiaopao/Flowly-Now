<template>
  <PageShell
    width="wide"
    class="settings-page"
    :style="{ '--personal-center-navigation-height': `${navigationHeight}px` }"
  >
    <div
      ref="stickyNavigation"
      class="settings-navigation"
    >
      <header class="settings-heading">
        <p class="settings-title">
          {{ center.title }}
        </p>
        <p class="settings-description">
          {{ center.subtitle }}
        </p>
      </header>
      <nav
        class="settings-nav"
        :aria-label="center.navigationLabel"
      >
        <div
          v-for="group in groups"
          :key="group.key"
          class="nav-group"
          :aria-labelledby="'settings-group-' + group.key"
        >
          <h2 :id="'settings-group-' + group.key">
            {{ group.label }}
          </h2>
          <div class="nav-group-items">
            <router-link
              v-for="item in group.items"
              :key="item.key"
              :to="item.to"
              class="nav-item"
              :class="{ active: activeTab === item.key }"
              :aria-current="activeTab === item.key ? 'page' : undefined"
              :title="item.description"
            >
              {{ item.label }}
            </router-link>
          </div>
        </div>
      </nav>
      <select
        v-model="navigationTarget"
        class="settings-mobile-nav"
        :aria-label="center.navigationLabel"
        @change="navigate"
      >
        <optgroup
          v-for="group in groups"
          :key="group.key"
          :label="group.label"
        >
          <option
            v-for="item in group.items"
            :key="item.key"
            :value="item.to"
          >
            {{ item.label }}
          </option>
        </optgroup>
      </select>
    </div>
    <div class="settings-content">
      <router-view />
    </div>
  </PageShell>
</template>

<script setup>
import PageShell from '@/components/layout/PageShell.vue'
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PERSONAL_CENTER_NAV_ITEMS, resolvePersonalCenterActiveKey } from '@/config/userNavigation'
import { PERSONAL_CENTER as center } from '@/config/personalCenter'

const route = useRoute()
const router = useRouter()
const stickyNavigation = ref(null)
const navigationHeight = ref(0)
let navigationObserver
const groups = center.groups.map(group => ({ ...group, items: group.items.map(key => PERSONAL_CENTER_NAV_ITEMS.find(item => item.key === key)) }))
const activeTab = computed(() => resolvePersonalCenterActiveKey(route.path))
const activeItem = computed(() => PERSONAL_CENTER_NAV_ITEMS.find(item => item.key === activeTab.value) || PERSONAL_CENTER_NAV_ITEMS[0])
const navigationTarget = ref(activeItem.value.to)
watch(activeItem, item => { navigationTarget.value = item.to })
onMounted(() => {
  const updateNavigationHeight = () => {
    navigationHeight.value = stickyNavigation.value?.getBoundingClientRect().height || 0
  }
  updateNavigationHeight()
  navigationObserver = new ResizeObserver(updateNavigationHeight)
  navigationObserver.observe(stickyNavigation.value)
})
onUnmounted(() => navigationObserver?.disconnect())
async function navigate() {
  try {
    await router.push(navigationTarget.value)
  } finally {
    navigationTarget.value = activeItem.value.to
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@use '@/assets/styles/personal-center.scss' as *;

.settings-page {
  container: personal-center / inline-size;
}
.settings-navigation {
  position: sticky;
  top: var(--header-height);
  z-index: $z-sticky - 1;
  padding-top: $spacing-6;
  padding-bottom: $spacing-4;
  margin-top: -$spacing-6;
  margin-bottom: $spacing-6;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-primary);
}
.settings-heading {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: $spacing-2 $spacing-4;
  margin-bottom: $spacing-4;
  p { margin: 0; }
}
.settings-title { color: var(--text-primary); font-size: $font-size-xl; font-weight: $font-weight-semibold; }
.settings-description { color: var(--text-secondary); font-size: $font-size-sm; line-height: $line-height-normal; }
.settings-nav { display: flex; gap: $spacing-6; }
.nav-group { min-width: 0; h2 { margin: 0 0 $spacing-2; padding-inline: $spacing-2; color: var(--text-secondary); font-size: $font-size-xs; font-weight: $font-weight-medium; } }
.nav-group-items { display: flex; gap: $spacing-1; }
.nav-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--control-height);
  padding: $spacing-2;
  border: 1px solid transparent;
  border-radius: $radius-md;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: $font-size-sm;
  line-height: $line-height-tight;
  white-space: nowrap;
  transition: background-color $transition-fast, color $transition-fast;
  &:hover { color: var(--text-primary); background: var(--surface-muted); }
  &.active { color: var(--tech-selection-text); background: var(--accent-muted); border-color: var(--tech-selection-border); font-weight: $font-weight-semibold; }
  &:focus-visible { outline: 2px solid var(--accent-primary); outline-offset: 2px; }
}
.settings-content { min-width: 0; }
.settings-content :deep(:is([id], input, textarea, button, select, a[href])) {
  scroll-margin-block-start: calc(var(--header-height) + var(--personal-center-navigation-height) + #{$spacing-4});
}
.settings-mobile-nav {
  display: none;
  width: 100%;
  min-height: var(--control-height-large);
  padding-inline: $spacing-3;
  border-radius: $radius-lg;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font: inherit;
  &:focus-visible { outline: 2px solid var(--accent-primary); outline-offset: 2px; }
}
@container personal-center (max-width: #{$personal-center-nav-breakpoint}) {
  .settings-nav { display: none; }
  .settings-mobile-nav { display: block; }
}
@media (max-width: $breakpoint-md) {
  .settings-navigation { padding-top: $spacing-4; margin-top: -$spacing-4; }
}
@media (max-width: $breakpoint-sm) {
  .settings-description { display: none; }
  .settings-heading { margin-bottom: $spacing-3; }
}
@media (prefers-reduced-motion: reduce) { .nav-item { transition: none; } }
</style>
