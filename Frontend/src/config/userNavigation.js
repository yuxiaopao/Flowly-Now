/**
 * 个人中心（/settings）导航 — 单一数据源。
 * 此处登记的模块不应再出现在主导航侧边栏或仪表盘入口中。
 */
/** @type {Array<{ key: string, to: string, label: string, description: string }>} */
export const PERSONAL_CENTER_NAV_ITEMS = [
  {
    key: 'profile',
    to: '/settings/profile',
    label: '个人资料',
    description: '账号信息与基础资料',
  },
  {
    key: 'avatar',
    to: '/settings/avatar',
    label: 'AI 头像',
    description: 'Bloub 定制、动画编辑与导出',
  },
  {
    key: 'credentials',
    to: '/settings/credentials',
    label: '模型与服务凭证',
    description: '统一管理大模型、邮箱等密钥',
  },
  {
    key: 'integrations',
    to: '/settings/integrations',
    label: '第三方集成',
    description: '连接外部平台与服务',
  },
  {
    key: 'api-doc',
    to: '/settings/api-doc',
    label: 'API 文档',
    description: '查看接口说明与接入方式',
  },
  {
    key: 'notifications',
    to: '/settings/notifications',
    label: '通知与邮件',
    description: '通知偏好、默认发件人与 SMTP',
  },
  {
    key: 'preferences',
    to: '/settings/preferences',
    label: '偏好设置',
    description: '外观主题与编辑器习惯',
  },
  {
    key: 'billing',
    to: '/settings/billing',
    label: '订阅管理',
    description: '套餐、账单与配额',
  },
  {
    key: 'data-export',
    to: '/settings/data-export',
    label: '数据管理',
    description: '导出、备份与数据控制',
  },
  {
    key: 'branding',
    to: '/settings/branding',
    label: '品牌定制',
    description: 'Logo、名称与视觉配置',
  },
  {
    key: 'desktop-agent',
    to: '/settings/desktop-agent',
    label: '桌面端 Agent',
    description: '本地执行节点与桌面代理',
  },
]

const PERSONAL_CENTER_EXTERNAL_PATHS = PERSONAL_CENTER_NAV_ITEMS
  .map((item) => item.to)
  .filter((to) => !to.startsWith('/settings'))

/**
 * 判断路径是否属于个人中心模块。
 * @param {string} path
 */
export function isPersonalCenterPath(path) {
  if (!path) return false
  if (path === '/settings' || path.startsWith('/settings/')) return true
  return PERSONAL_CENTER_EXTERNAL_PATHS.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`)
  )
}

/**
 * 从主导航项中过滤掉已在个人中心出现的模块。
 * @template {{ path: string }} T
 * @param {T[]} items
 * @returns {T[]}
 */
export function excludePersonalCenterModules(items) {
  return items.filter((item) => !isPersonalCenterPath(item.path))
}

/**
 * 根据当前路由解析个人中心侧栏激活项 key。
 * @param {string} path
 */
export function resolvePersonalCenterActiveKey(path) {
  if (path.includes('api-keys') || path.includes('credentials')) return 'credentials'
  if (path.includes('integrations')) return 'integrations'
  if (path.includes('api-doc')) return 'api-doc'
  if (path.includes('notifications')) return 'notifications'
  if (path.includes('preferences')) return 'preferences'
  if (path.includes('billing')) return 'billing'
  if (path.includes('data-export')) return 'data-export'
  if (path.includes('branding')) return 'branding'
  if (path.includes('desktop-agent')) return 'desktop-agent'
  if (path.includes('/settings/avatar')) return 'avatar'
  if (path.includes('profile')) return 'profile'
  return 'profile'
}
