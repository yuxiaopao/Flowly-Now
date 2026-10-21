<template>
  <div
    class="app-layout"
    :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed && !isMobile, 'mobile-open': mobileMenuOpen }"
  >
    <a
      class="skip-link"
      href="#main-content"
    >跳至页面内容</a>
    <!-- 移动端菜单遮罩 -->
    <div
      v-show="mobileMenuOpen"
      class="mobile-overlay"
      @click="mobileMenuOpen = false"
    />

    <!-- 侧边栏 -->
    <aside
      id="app-sidebar"
      ref="sidebarRef"
      :inert="(isMobile && !mobileMenuOpen) || undefined"
      :role="isMobile && mobileMenuOpen ? 'dialog' : undefined"
      :aria-modal="isMobile && mobileMenuOpen ? true : undefined"
      aria-label="应用导航"
      class="sidebar"
      :class="{ 'mobile-open': mobileMenuOpen }"
    >
      <!-- Logo 区域 -->
      <div class="sidebar-header">
        <router-link
          to="/home"
          class="logo-link"
        >
          <ThemeLogo
            class="logo"
            alt="Flowly"
          />
          <span class="logo-text">Flowly</span>
          <span class="logo-badge">AI</span>
        </router-link>
        <button
          class="mobile-close"
          aria-label="关闭导航"
          @click="mobileMenuOpen = false"
        >
          <X />
        </button>
      </div>

      <router-link
        :to="NAVIGATION_UI.newWorkflow.path"
        class="sidebar-create"
        :aria-label="NAVIGATION_UI.newWorkflow.label"
        :title="NAVIGATION_UI.newWorkflow.label"
        @click="mobileMenuOpen = false"
      >
        <Plus aria-hidden="true" />
        <span>{{ NAVIGATION_UI.newWorkflow.label }}</span>
      </router-link>

      <!-- 导航菜单 -->
      <nav
        class="sidebar-nav"
        aria-label="主导航"
      >
        <div
          v-for="section in APP_NAV_SECTIONS"
          :key="section.id"
          class="nav-section"
          :class="`nav-section--${section.accent}`"
        >
          <button
            type="button"
            class="nav-section-title"
            :aria-label="NAVIGATION_UI.sectionLabel(section.label)"
            :aria-expanded="isSectionOpen(section.id)"
            :aria-controls="NAVIGATION_UI.sectionId(section.id)"
            @click="toggleSection(section.id)"
          >
            <span>{{ section.label }}</span>
            <span
              class="nav-section-count"
              aria-hidden="true"
            >{{ section.items.length }}</span>
            <ChevronRight
              class="nav-section-chevron"
              :class="{ expanded: isSectionOpen(section.id) }"
              aria-hidden="true"
            />
          </button>
          <div
            v-show="isSectionOpen(section.id)"
            :id="NAVIGATION_UI.sectionId(section.id)"
            class="nav-section-items"
          >
            <router-link
              v-for="item in section.items"
              :key="item.path"
              :to="item.path"
              class="nav-item"
              :class="[`nav-item--${item.accent}`, { active: isActiveRoute(item.path) }]"
              :aria-current="isActiveRoute(item.path) ? 'page' : undefined"
              :aria-label="item.label"
              :title="item.label"
              @click="mobileMenuOpen = false"
            >
              <span class="nav-icon-wrap"><component
                :is="item.icon"
                class="nav-icon"
                aria-hidden="true"
              /></span>
              <span class="nav-label">{{ item.label }}</span>
              <ChevronRight
                v-if="isActiveRoute(item.path)"
                class="nav-active-arrow"
                aria-hidden="true"
              />
            </router-link>
          </div>
        </div>

        <div
          v-if="generatedSiteNavItems.length"
          class="nav-section"
        >
          <span class="nav-section-title nav-section-title--static">{{ NAVIGATION_UI.generatedProjects.label }}</span>
          <router-link
            v-for="site in generatedSiteNavItems"
            :key="site.id"
            :to="siteNavPath(site)"
            class="nav-item nav-item--emerald"
            :class="{ active: isActiveRoute(siteNavPath(site)) }"
            :aria-label="site.name"
            :title="site.name"
            :aria-current="isActiveRoute(siteNavPath(site)) ? 'page' : undefined"
            @click="mobileMenuOpen = false"
          >
            <span class="nav-icon-wrap">
              <Globe
                class="nav-icon"
                aria-hidden="true"
              />
            </span>
            <span class="nav-label">{{ site.name }}</span>
          </router-link>
        </div>
      </nav>

      <!-- 侧边栏底部 -->
      <div class="sidebar-footer">
        <router-link
          :to="NAVIGATION_UI.personalCenter.path"
          class="nav-item"
          :class="[`nav-item--${NAVIGATION_UI.personalCenter.accent}`, { active: isActiveRoute(NAVIGATION_UI.personalCenter.path) }]"
          :aria-label="NAVIGATION_UI.personalCenter.label"
          :title="NAVIGATION_UI.personalCenter.label"
          :aria-current="isActiveRoute(NAVIGATION_UI.personalCenter.path) ? 'page' : undefined"
          @click="mobileMenuOpen = false"
        >
          <span class="nav-icon-wrap">
            <Settings
              class="nav-icon"
              aria-hidden="true"
            />
          </span>
          <span class="nav-label">{{ NAVIGATION_UI.personalCenter.label }}</span>
        </router-link>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div
      class="main-container"
      :inert="(isMobile && mobileMenuOpen) || undefined"
    >
      <!-- 顶部栏 -->
      <header class="topbar">
        <!-- 移动端菜单按钮 -->
        <button
          class="mobile-menu-btn"
          aria-label="打开导航"
          aria-controls="app-sidebar"
          :aria-expanded="mobileMenuOpen"
          @click="mobileMenuOpen = true"
        >
          <Menu />
        </button>
        <button
          class="sidebar-toggle"
          :aria-label="appStore.sidebarCollapsed ? '展开导航' : '收起导航'"
          :aria-expanded="!appStore.sidebarCollapsed"
          @click="appStore.toggleSidebar"
        >
          <PanelLeftOpen v-if="appStore.sidebarCollapsed" />
          <PanelLeftClose v-else />
        </button>

        <!-- 面包屑 -->
        <div
          class="breadcrumb"
          aria-label="当前位置"
        >
          <span
            v-if="appStore.breadcrumbs.length === 0"
            class="breadcrumb-current"
          >{{ route.meta.title }}</span>
          <span
            v-for="(item, index) in appStore.breadcrumbs"
            :key="index"
            class="breadcrumb-item"
          >
            <router-link
              v-if="item.path"
              :to="item.path"
            >{{ item.label }}</router-link>
            <span v-else>{{ item.label }}</span>
            <ChevronRight
              v-if="index < appStore.breadcrumbs.length - 1"
              class="breadcrumb-separator"
            />
          </span>
        </div>

        <div class="topbar-actions">
          <!-- 主题切换 -->
          <ThemeSwitcher />
          <!-- 搜索 -->
          <button
            class="global-search"
            aria-label="搜索命令与页面"
            @click="appStore.openCommandPalette?.()"
          >
            <Search
              class="icon"
              aria-hidden="true"
            />
            <span>快速跳转</span>
            <kbd>Ctrl K</kbd>
          </button>
          <!-- 通知 -->
          <el-button
            :icon="BellIcon"
            aria-label="通知与邮件"
            title="通知与邮件"
            circle
            @click="router.push('/settings/notifications')"
          />
          <!-- 用户菜单 -->
          <el-dropdown
            trigger="click"
            @command="handleUserCommand"
          >
            <button
              class="user-menu-trigger"
              aria-label="打开账户菜单"
            >
              <AccountAvatar />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <div class="user-info-dropdown">
                    <span class="username">{{ authStore.userName }}</span>
                    <span class="email">{{ authStore.userEmail }}</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item
                  divided
                  command="profile"
                >
                  <User class="dropdown-icon" /> 个人资料
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <Settings class="dropdown-icon" /> 个人中心
                </el-dropdown-item>
                <el-dropdown-item
                  divided
                  command="logout"
                >
                  <LogOut class="dropdown-icon" /> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main
        id="main-content"
        class="main-content"
        tabindex="-1"
      >
        <transition
          name="page"
          mode="out-in"
        >
          <div
            :key="route.path"
            class="main-content__page"
          >
            <slot />
          </div>
        </transition>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import {
  Settings,
  Search,
  Bell as BellIcon,
  User,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  ChevronRight,
  Plus,
  Globe,
} from 'lucide-vue-next'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import AccountAvatar from '@/components/common/AccountAvatar.vue'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import { APP_NAV_SECTIONS, APP_NAV_ITEMS, NAVIGATION_UI } from '@/config/appNavigation'
import { PRODUCT_UI } from '@/config/productUi'
import { websiteGeneratorApi } from '@/api/websiteGenerator'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()
const mobileMenuOpen = ref(false)
const isMobile = ref(false)
const generatedSiteNavItems = ref([])
const sidebarRef = ref(null)
let menuReturnFocus

watch(mobileMenuOpen, async (open) => {
  if (open) {
    menuReturnFocus = document.activeElement
    await nextTick()
    sidebarRef.value?.querySelector('.mobile-close')?.focus()
  } else {
    await nextTick()
    menuReturnFocus?.focus()
  }
})

function handleNavigationKeydown(event) {
  if (!mobileMenuOpen.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    mobileMenuOpen.value = false
  } else if (event.key === 'Tab') {
    const focusable = [...sidebarRef.value.querySelectorAll('a[href], button')].filter(el => el.getClientRects().length)
    const first = focusable[0]
    const last = focusable.at(-1)
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }
}

function siteNavPath(site) {
  return `/projects/${site.id}`
}

async function loadGeneratedSiteNav() {
  if (!authStore.isAuthenticated) {
    generatedSiteNavItems.value = []
    return
  }
  try {
    const res = await websiteGeneratorApi.list({ show_in_nav: true, status: 'completed' })
    const items = Array.isArray(res) ? res : (res?.results || [])
    generatedSiteNavItems.value = items.filter((s) => s.showInNav !== false)
  } catch {
    generatedSiteNavItems.value = []
  }
}

const checkMobile = () => {
  isMobile.value = window.innerWidth <= PRODUCT_UI.mobileBreakpoint
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadGeneratedSiteNav()
  window.addEventListener('flowly:assets-updated', loadGeneratedSiteNav)
  document.addEventListener('keydown', handleNavigationKeydown)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('flowly:assets-updated', loadGeneratedSiteNav)
  document.removeEventListener('keydown', handleNavigationKeydown)
})

const collapsedSections = ref([])

watch(() => route.path, () => {
  const activeSection = APP_NAV_SECTIONS.find(section => section.items.some(item => isActiveRoute(item.path)))
  if (activeSection) collapsedSections.value = collapsedSections.value.filter(id => id !== activeSection.id)
})

function isSectionOpen(id) {
  return (appStore.sidebarCollapsed && !isMobile.value) || !collapsedSections.value.includes(id)
}

function toggleSection(id) {
  collapsedSections.value = collapsedSections.value.includes(id)
    ? collapsedSections.value.filter(sectionId => sectionId !== id)
    : [...collapsedSections.value, id]
}

function isActiveRoute(path) {
  if (!(route.path === path || route.path.startsWith(`${path}/`))) return false
  const paths = APP_NAV_ITEMS.map(item => item.path)
  return !paths.some(candidate => candidate !== path && candidate.startsWith(`${path}/`) &&
    (route.path === candidate || route.path.startsWith(`${candidate}/`)))
}

async function handleUserCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/settings/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      await authStore.logout()
      await router.replace('/login')
      break
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.app-layout { display: flex; min-height: 100dvh; background: var(--tech-app-bg); }
.skip-link {
  position: fixed; top: $spacing-2; left: $spacing-2; z-index: $z-tooltip;
  padding: $spacing-3; background: var(--bg-elevated); color: var(--text-primary);
  border-radius: $radius-lg; transform: translateY(-200%);
  &:focus { transform: none; }
}
.sidebar {
  width: $sidebar-width; height: 100dvh; position: fixed; inset: 0 auto 0 0;
  display: flex; flex-direction: column; background: var(--tech-shell-bg);
  border-right: 1px solid var(--border-primary); z-index: $z-fixed;
  .sidebar-collapsed & { width: $sidebar-collapsed-width; }
}
.sidebar-header { height: $header-height; min-height: $header-height; padding-inline: $spacing-4; display: flex; align-items: center; }
.logo-link { display: flex; align-items: center; gap: $spacing-2; }
.logo { width: 28px; height: 28px; }
.logo-text { font-size: $font-size-lg; font-weight: $font-weight-semibold; color: var(--text-primary); .sidebar-collapsed & { display: none; } }
.logo-badge { margin-left: $spacing-1; padding: 2px $spacing-1; border: 1px solid var(--tech-selection-border); border-radius: $radius-sm; color: var(--tech-cyan); background: var(--tech-cyan-soft); font-family: var(--font-family-mono); font-size: $font-size-xs; .sidebar-collapsed & { display: none; } }
.sidebar-nav { flex: 1; overflow-y: auto; padding: $spacing-3 $spacing-2; overscroll-behavior: contain; }
.nav-section { margin-bottom: $spacing-3; min-width: 0; }
.nav-section-title {
  display: flex; align-items: center; gap: $spacing-2; width: 100%; padding: $spacing-1 $spacing-3; margin-bottom: $spacing-1;
  border-radius: $radius-md; text-align: left; font-size: $font-size-xs; color: var(--text-tertiary); font-weight: $font-weight-medium;
  &:hover { background: var(--surface-muted); color: var(--text-primary); }
  > span:first-child { color: var(--section-accent, var(--text-secondary)); }
  .sidebar-collapsed & { display: none; }
  &--static { color: var(--text-secondary); }
}
.nav-section-count { margin-left: auto; font-variant-numeric: tabular-nums; font-family: var(--font-family-mono); }
.nav-section-chevron { width: $spacing-3; height: $spacing-3; transition: transform $transition-fast; &.expanded { transform: rotate(90deg); } }
.nav-active-arrow { width: $spacing-3; height: $spacing-3; flex-shrink: 0; margin-left: auto; color: var(--navigation-accent); .sidebar-collapsed & { display: none; } }
.sidebar-create {
  display: flex; align-items: center; justify-content: center; gap: $spacing-2;
  min-height: var(--control-height); margin: $spacing-2 $spacing-3 0;
  border: 1px solid var(--tech-selection-border); border-radius: $radius-lg;
  background: var(--tech-blue-soft); color: var(--tech-blue); font-size: $font-size-sm; font-weight: $font-weight-medium;
  svg { width: $spacing-4; height: $spacing-4; }
  &:hover { opacity: 1; border-color: var(--tech-blue); }
  .sidebar-collapsed & { margin-inline: $spacing-2; span { display: none; } }
}
.nav-item {
  display: flex; align-items: center; gap: $spacing-3; padding: $spacing-1 $spacing-3;
  min-height: var(--control-height); margin-bottom: var(--navigation-item-gap); border: 1px solid transparent;
  border-radius: $radius-lg; color: var(--text-secondary); font-size: $font-size-sm;
  transition: background-color $transition-fast, color $transition-fast;
  &:hover { background: var(--surface-muted); color: var(--text-primary); opacity: 1; }
  &.active { background: var(--tech-selection-bg); border-color: var(--tech-selection-border); color: var(--tech-selection-text); font-weight: $font-weight-medium; }
  .sidebar-collapsed & { justify-content: center; padding-inline: $spacing-1; .nav-label { display: none; } }
}
.sidebar-footer { padding: $spacing-3 $spacing-2; border-top: 1px solid var(--border-primary); }
.main-container {
  position: relative; isolation: isolate; flex: 1; min-width: 0; margin-left: $sidebar-width;
  .sidebar-collapsed & { margin-left: $sidebar-collapsed-width; }
  &::before {
    content: ''; position: absolute; inset: $header-height 0 0; z-index: -1; pointer-events: none;
    background-image: linear-gradient(var(--tech-grid) 1px, transparent 1px), linear-gradient(90deg, var(--tech-grid) 1px, transparent 1px);
    background-size: var(--tech-grid-size) var(--tech-grid-size);
    mask-image: var(--tech-grid-mask);
  }
}
.topbar {
  height: $header-height; padding-inline: $spacing-6; display: flex; align-items: center; gap: $spacing-3;
  position: sticky; top: 0; z-index: $z-sticky; background: var(--tech-shell-bg); border-bottom: 1px solid var(--border-primary); box-shadow: 0 1px 0 var(--tech-edge);
}
.sidebar-toggle, .mobile-menu-btn, .mobile-close, .user-menu-trigger {
  display: grid; place-items: center; width: var(--control-height); height: var(--control-height);
  flex-shrink: 0; border-radius: $radius-lg; color: var(--text-secondary);
  &:hover { color: var(--text-primary); background: var(--bg-hover); }
  svg { width: 18px; height: 18px; }
}
.mobile-menu-btn, .mobile-close { display: none; }
.breadcrumb { flex: 1; min-width: 0; display: flex; align-items: center; font-size: $font-size-sm; }
.breadcrumb-current { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.breadcrumb-item { display: flex; align-items: center; gap: $spacing-1; color: var(--text-secondary); }
.breadcrumb-separator { width: $spacing-4; height: $spacing-4; color: var(--text-tertiary); }
.topbar-actions { display: flex; align-items: center; gap: $spacing-2; }
.global-search {
  display: flex; align-items: center; gap: $spacing-2; padding: $spacing-2 $spacing-3;
  border: 1px solid var(--border-primary); border-radius: $radius-lg; color: var(--text-secondary); font-size: $font-size-xs;
  &:hover { border-color: var(--border-hover); background: var(--bg-hover); }
  .icon { width: $spacing-4; height: $spacing-4; }
  kbd { margin-left: $spacing-4; font-family: inherit; color: var(--text-tertiary); }
}
.user-info-dropdown { display: flex; flex-direction: column; gap: $spacing-1; .username { font-weight: $font-weight-medium; } .email { font-size: $font-size-xs; color: var(--text-tertiary); } }
.dropdown-icon { width: $spacing-4; height: $spacing-4; margin-right: $spacing-2; }
.main-content { min-width: 0; padding: var(--page-gutter); &__page { min-width: 0; } &:focus { outline: none; } }
@media (max-width: 768px) {
  .sidebar { width: min(280px, 85vw); transform: translateX(-100%); transition: transform $transition-normal; &.mobile-open { transform: none; box-shadow: var(--shadow-xl); } }
  .mobile-overlay { position: fixed; inset: 0; background: var(--bg-overlay); z-index: $z-sticky + 5; }
  .main-container { margin-left: 0; }
  .mobile-menu-btn, .mobile-close { display: grid; width: var(--control-height-large); height: var(--control-height-large); }
  .mobile-close { margin-left: auto; }
  .sidebar-toggle { display: none; }
  .topbar { padding-inline: $spacing-3; gap: $spacing-2; }
  .nav-item, .nav-section-title, .sidebar-create { min-height: var(--control-height-large); }
  .global-search { width: var(--control-height-large); height: var(--control-height-large); padding: $spacing-3; border: 0; justify-content: center; span, kbd { display: none; } }
  .breadcrumb { font-size: $font-size-xs; }
}
</style>

<style scoped>
.user-menu-trigger { width: 44px; height: 44px; padding: 0; border: 0; border-radius: 0; background: transparent; }
.user-menu-trigger:hover, .user-menu-trigger:active { background: transparent; }
.user-menu-trigger :deep(svg) { width: 100%; height: 100%; }
</style>
