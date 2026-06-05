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
            :class="{ active: isActiveRoute(item.path) }"
            @click="mobileMenuOpen = false"
          >
            <component
              :is="item.icon"
              class="nav-icon"
            />
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
            :class="{ active: isActiveRoute(item.path) }"
            @click="mobileMenuOpen = false"
          >
            <component
              :is="item.icon"
              class="nav-icon"
            />
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
        </div>

        <div class="nav-section">
          <span class="nav-section-title">工作流</span>
          <router-link
            :to="'/workflows/new'"
            class="nav-item"
            :class="{ active: isActiveRoute('/workflows/new') }"
            @click="mobileMenuOpen = false"
          >
            <Plus class="nav-icon" />
            <span class="nav-label">新建工作流</span>
          </router-link>
        </div>
      </nav>

      <!-- 侧边栏底部 -->
      <div class="sidebar-footer">
        <router-link
          to="/settings"
          class="nav-item"
          :class="{ active: isActiveRoute('/settings') }"
          @click="mobileMenuOpen = false"
        >
          <Settings class="nav-icon" />
          <span class="nav-label">设置</span>
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
                  <Settings class="dropdown-icon" /> 设置
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
        <router-view v-slot="{ Component }">
          <transition
            name="fade"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Toast 容器 -->
    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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
  Bell,
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
  Layers,
  Network
} from 'lucide-vue-next'
import ToastContainer from '@/components/common/ToastContainer.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import ThemeLogo from '@/components/common/ThemeLogo.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()
const mobileMenuOpen = ref(false)
const isMobile = ref(false)

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const mainNavItems = [
  { path: '/home', label: '仪表盘', icon: Home },
  { path: '/workflows', label: '工作流', icon: GitBranch },
  { path: '/agents', label: 'Agent', icon: Bot },
  { path: '/knowledge', label: '知识库', icon: Database },
  { path: '/team', label: '团队', icon: Users }
]

const toolNavItems = [
  { path: '/nl-create', label: 'NL 创建', icon: MessageSquare },
  { path: '/codegraph', label: '代码图谱', icon: Network },
  { path: '/monitoring', label: '监控中心', icon: BarChart2 },
  { path: '/prompts', label: '模板', icon: FileText },
  { path: '/dataset-recommend', label: '数据集推荐', icon: BookOpen },
  { path: '/augmentations', label: '数据增强', icon: Layers }
]

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
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  transition: width $transition-normal, background-color 0.3s ease;
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

.nav-section-title {
  display: block;
  padding: 0 $spacing-4;
  margin-bottom: $spacing-2;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;

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
  border-radius: $radius-lg;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all $transition-fast;
  cursor: pointer;

  &:hover {
    background-color: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background-color: var(--accent-muted);
    color: var(--accent-primary);

    .nav-icon {
      color: var(--accent-primary);
    }
  }

  .sidebar-collapsed & {
    justify-content: center;
    padding: $spacing-3;

    .nav-label {
      display: none;
    }
  }
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
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
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  position: sticky;
  top: 0;
  z-index: $z-sticky;
  transition: background-color 0.3s ease;
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
}

// 路由切换动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
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
