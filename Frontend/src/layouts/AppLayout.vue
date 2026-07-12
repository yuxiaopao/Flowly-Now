<template>
  <div
    class="app-layout"
    :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed, 'mobile-open': mobileMenuOpen }"
  >
    <!-- 移动端菜单遮罩 -->
    <div
      v-show="mobileMenuOpen"
      class="mobile-overlay"
      @click="mobileMenuOpen = false"
    />

    <!-- 侧边栏 -->
    <aside
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
        </router-link>
        <button
          class="mobile-close"
          @click="mobileMenuOpen = false"
        >
          <X />
        </button>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div class="nav-section">
          <span class="nav-section-title">主导航</span>
          <router-link
            v-for="item in mainNavItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="[`nav-item--${item.accent}`, { active: isActiveRoute(item.path) }]"
            @click="mobileMenuOpen = false"
          >
            <span class="nav-icon-wrap">
              <component
                :is="item.icon"
                class="nav-icon"
              />
            </span>
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
        </div>

        <div class="nav-section">
          <span class="nav-section-title">工具</span>
          <router-link
            v-for="item in toolNavItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="[`nav-item--${item.accent}`, { active: isActiveRoute(item.path) }]"
            @click="mobileMenuOpen = false"
          >
            <span class="nav-icon-wrap">
              <component
                :is="item.icon"
                class="nav-icon"
              />
            </span>
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
        </div>

        <div
          v-if="generatedSiteNavItems.length"
          class="nav-section"
        >
          <span class="nav-section-title">识别项目</span>
          <router-link
            v-for="site in generatedSiteNavItems"
            :key="site.id"
            :to="siteNavPath(site)"
            class="nav-item nav-item--emerald"
            :class="{ active: isActiveRoute(siteNavPath(site)) }"
            @click="mobileMenuOpen = false"
          >
            <span class="nav-icon-wrap">
              <Globe class="nav-icon" />
            </span>
            <span class="nav-label">{{ site.name }}</span>
          </router-link>
        </div>

        <div class="nav-section">
          <span class="nav-section-title">工作流</span>
          <router-link
            :to="'/workflows/new'"
            class="nav-item nav-item--amber"
            :class="{ active: isActiveRoute('/workflows/new') }"
            @click="mobileMenuOpen = false"
          >
            <span class="nav-icon-wrap">
              <Plus class="nav-icon" />
            </span>
            <span class="nav-label">新建工作流</span>
          </router-link>
        </div>
      </nav>

      <!-- 侧边栏底部 -->
      <div class="sidebar-footer">
        <router-link
          to="/settings"
          class="nav-item nav-item--rose"
          :class="{ active: isActiveRoute('/settings') }"
          @click="mobileMenuOpen = false"
        >
          <span class="nav-icon-wrap">
            <Settings class="nav-icon" />
          </span>
          <span class="nav-label">个人中心</span>
        </router-link>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-container">
      <!-- 顶部栏 -->
      <header class="topbar">
        <!-- 移动端菜单按钮 -->
        <button
          class="mobile-menu-btn"
          @click="mobileMenuOpen = true"
        >
          <Menu />
        </button>
        <button
          class="sidebar-toggle"
          @click="appStore.toggleSidebar"
        >
          <Menu v-if="appStore.sidebarCollapsed" />
          <X v-else />
        </button>

        <!-- 面包屑 -->
        <div class="breadcrumb">
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
          <el-button
            :icon="Search"
            circle
          />
          <!-- 通知 -->
          <el-button
            :icon="BellIcon"
            circle
          />
          <!-- 用户菜单 -->
          <el-dropdown
            trigger="click"
            @command="handleUserCommand"
          >
            <div class="user-avatar">
              <el-avatar
                :size="36"
                :src="authStore.user?.avatar"
              >
                {{ authStore.user?.username?.[0]?.toUpperCase() }}
              </el-avatar>
            </div>
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
      <main class="main-content">
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import {
  Home,
  GitBranch,
  Bot,
  MessageSquare,
  Database,
  Users,
  BarChart2,
  Settings,
  Search,
  Bell as BellIcon,
  User,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Plus,
  FileText,
  BookOpen,
  Network,
  Cpu,
  HardDrive,
  Terminal,
  Store,
  History,
  Compass,
  Star,
  GitCompare,
  Globe,
  Workflow,
} from 'lucide-vue-next'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import ThemeLogo from '@/components/common/ThemeLogo.vue'
import { excludePersonalCenterModules } from '@/config/userNavigation'
import { websiteGeneratorApi } from '@/api/websiteGenerator'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()
const mobileMenuOpen = ref(false)
const isMobile = ref(false)
const generatedSiteNavItems = ref([])

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
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadGeneratedSiteNav()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const mainNavItems = [
  { path: '/home', label: '仪表盘', icon: Home, accent: 'blue' },
  { path: '/workflows', label: '工作流', icon: GitBranch, accent: 'emerald' },
  { path: '/agents', label: 'Agent', icon: Bot, accent: 'amber' },
  { path: '/knowledge', label: '知识库', icon: Database, accent: 'rose' },
  { path: '/team', label: '团队', icon: Users, accent: 'blue' },
]

const toolNavItems = excludePersonalCenterModules([
  { path: '/agents/collaborate', label: '多智能体协作', icon: Workflow, accent: 'rose' },
  { path: '/agents/marketplace', label: 'Agent 市场', icon: Store, accent: 'amber' },
  { path: '/nl-create', label: 'NL 创建', icon: MessageSquare, accent: 'blue' },
  { path: '/executions', label: '执行历史', icon: History, accent: 'emerald' },
  { path: '/datasets', label: '数据集', icon: BookOpen, accent: 'amber' },
  { path: '/dataset-recommend', label: '数据集推荐', icon: Compass, accent: 'rose' },
  { path: '/prompts', label: '模板', icon: FileText, accent: 'blue' },
  { path: '/marketplace', label: '模板市场', icon: Store, accent: 'emerald' },
  { path: '/my-templates', label: '我的模板', icon: Star, accent: 'amber' },
  { path: '/codegraph', label: '代码图谱', icon: Network, accent: 'rose' },
  { path: '/models', label: '模型管理', icon: Cpu, accent: 'blue' },
  { path: '/vector-stores', label: '向量存储', icon: HardDrive, accent: 'emerald' },
  { path: '/analytics', label: '数据分析', icon: BarChart2, accent: 'amber' },
  { path: '/api-explorer', label: 'API 测试', icon: Terminal, accent: 'rose' },
  { path: '/workflows/diff', label: '工作流对比', icon: GitCompare, accent: 'blue' },
])

function isActiveRoute(path) {
  if (path === '/home') {
    return route.path === '/home'
  }
  return route.path.startsWith(path)
}

function handleUserCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/settings/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      authStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.app-layout {
  display: flex;
  min-height: 100vh;
  background-color: var(--bg-primary);
}

// 侧边栏
.sidebar {
  width: $sidebar-width;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-right: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  display: flex;
  flex-direction: column;
  transition: width $transition-normal, background-color 0.3s ease, backdrop-filter 0.3s ease;
  z-index: $z-sticky;

  .sidebar-collapsed & {
    width: $sidebar-collapsed-width;
  }
}

.sidebar-header {
  height: $header-height;
  padding: 0 $spacing-4;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border-primary);
}

.logo-link {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  text-decoration: none;
}

.logo {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: $font-size-xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  transition: opacity $transition-normal;

  .sidebar-collapsed & {
    opacity: 0;
    width: 0;
    overflow: hidden;
  }
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-4 0;
}

.nav-section {
  margin-bottom: $spacing-6;
}

.nav-section:nth-child(1) .nav-section-title {
  color: var(--accent-blue);
  opacity: 0.85;
}

.nav-section:nth-child(2) .nav-section-title {
  color: var(--accent-emerald);
  opacity: 0.85;
}

.nav-section:nth-child(3) .nav-section-title {
  color: var(--accent-amber);
  opacity: 0.85;
}

.nav-section:nth-child(4) .nav-section-title {
  color: var(--accent-rose);
  opacity: 0.85;
}

.nav-section-title {
  display: block;
  padding: 0 $spacing-4;
  margin-bottom: $spacing-2;
  font-size: $font-size-xs;
  font-weight: $font-weight-semibold;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;

  .sidebar-collapsed & {
    opacity: 0;
    height: 0;
    margin: 0;
    overflow: hidden;
  }
}

.nav-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3 $spacing-4;
  margin: 0 $spacing-2;
  border: 1px solid transparent;
  border-radius: $radius-lg;
  color: var(--text-secondary);
  text-decoration: none;
  transition: background-color $transition-fast, color $transition-fast, border-color $transition-fast, transform $transition-fast;
  cursor: pointer;

  &:hover {
    background-color: var(--bg-hover);
    color: var(--text-primary);
    transform: translateX(2px);
  }

  &.active {
    color: var(--text-primary);
    box-shadow: inset 3px 0 0 var(--item-accent, var(--color-primary));
  }

  .sidebar-collapsed & {
    justify-content: center;
    padding: $spacing-3;

    .nav-label,
    .nav-icon-wrap {
      // icon wrap stays visible when collapsed
    }

    .nav-label {
      display: none;
    }
  }
}

// 无 accent 类的 nav-item 保持默认图标尺寸
.nav-item:not([class*='nav-item--']) {
  .nav-icon {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    transition: transform $transition-fast, color $transition-fast;
  }
}

.sidebar-footer {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .nav-item {
    flex: 1;
    width: auto;
  }

  :deep(.theme-switcher-container) {
    flex-shrink: 0;
  }
}

// 主容器
.main-container {
  flex: 1;
  margin-left: $sidebar-width;
  display: flex;
  flex-direction: column;
  transition: margin-left $transition-normal;

  .sidebar-collapsed & {
    margin-left: $sidebar-collapsed-width;
  }
}

// 顶部栏
.topbar {
  height: $header-height;
  padding: 0 $spacing-6;
  display: flex;
  align-items: center;
  gap: $spacing-4;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--glass-border);
  box-shadow: 0 1px 0 var(--glass-border), 0 4px 24px var(--topbar-edge-glow, transparent);
  position: sticky;
  top: 0;
  z-index: $z-sticky;
  transition: background-color 0.3s ease, backdrop-filter 0.3s ease;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: $radius-md;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
    color: var(--text-primary);
  }
}

.breadcrumb {
  flex: 1;
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-sm;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: $spacing-1;
  color: var(--text-secondary);

  a {
    color: inherit;
    text-decoration: none;

    &:hover {
      color: var(--accent-primary);
    }
  }
}

.breadcrumb-separator {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.user-avatar {
  cursor: pointer;
  border-radius: $radius-full;
  transition: transform $transition-fast;

  &:hover {
    transform: scale(1.05);
  }
}

.user-info-dropdown {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;

  .username {
    font-weight: $font-weight-medium;
  }

  .email {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.dropdown-icon {
  width: 16px;
  height: 16px;
  margin-right: $spacing-2;
}

// 主内容区
.main-content {
  flex: 1;
  padding: $spacing-6;
  overflow-x: hidden;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image:
      linear-gradient(var(--hero-grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 85% 60% at 50% 0%, black 15%, transparent 70%);
    opacity: 0.65;
  }

  &__page {
    min-height: 0;
    position: relative;
    z-index: 1;
  }
}

// 移动端响应式
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -280px;
    width: 280px;
    z-index: 1001;
    transition: left 0.3s ease;

    &.mobile-open {
      left: 0;
    }
  }

  .mobile-overlay {
    position: fixed;
    inset: 0;
    background: var(--bg-overlay);
    z-index: 1000;
    animation: fadeIn 0.2s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .mobile-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: $radius-md;
    color: var(--text-secondary);
    background: none;
    border: none;
    cursor: pointer;
    margin-left: auto;

    &:hover {
      background-color: var(--bg-hover);
    }
  }

  .mobile-menu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: $radius-md;
    color: var(--text-secondary);
    background: none;
    border: none;
    cursor: pointer;
    margin-right: $spacing-2;

    &:hover {
      background-color: var(--bg-hover);
    }
  }

  .main-container {
    margin-left: 0 !important;
  }

  .sidebar-collapsed .sidebar {
    width: 280px;
  }

  .topbar {
    padding: 0 $spacing-4;
  }

  .main-content {
    padding: $spacing-4;
  }

  .logo-text {
    display: block !important;
    opacity: 1 !important;
  }
}

// 平板适配
@media (min-width: 769px) and (max-width: 1024px) {
  .mobile-menu-btn {
    display: none;
  }

  .mobile-close {
    display: none;
  }
}

@media (min-width: 769px) {
  .mobile-menu-btn {
    display: none;
  }

  .mobile-close {
    display: none;
  }
}
</style>
