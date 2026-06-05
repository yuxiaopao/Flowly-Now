import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import { routes, setupRouterGuard } from './routes'

const router = createRouter({
  // history 模式 - 使用 URL path，不需要 #，但需要服务器配置
  // hash 模式 - 使用 #，不需要服务器配置，适合 SPA
  history: import.meta.env.VITE_USE_HASH_ROUTER === 'true'
    ? createWebHashHistory()
    : createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 如果有保存的位置（浏览器前进/后退）
    if (savedPosition) {
      return savedPosition
    }
    // 返回顶部
    return { top: 0 }
  }
})

// 设置路由守卫
setupRouterGuard(router)

export default router
