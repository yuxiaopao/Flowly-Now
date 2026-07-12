import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 可用的主题列表
export const THEMES = [
  { id: 'dark', name: '深色模式', icon: 'Moon', description: '默认深色主题' },
  { id: 'light', name: '浅色模式', icon: 'Sun', description: '明亮清爽的浅色主题' },
  { id: 'pure-bw', name: '纯黑白', icon: 'Contrast', description: '极简黑白设计' },
  { id: 'high-contrast', name: '高对比', icon: 'Eye', description: '高对比度无障碍设计' }
]

const DEFAULT_THEME = 'dark'

function normalizeTheme(themeId) {
  return THEMES.some(theme => theme.id === themeId) ? themeId : DEFAULT_THEME
}

export const useAppStore = defineStore('app', () => {
  // State
  const theme = ref(normalizeTheme(localStorage.getItem('theme')))
  const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')
  const sidebarWidth = computed(() => sidebarCollapsed.value ? 72 : 260)
  const isMobile = ref(false)
  const isTablet = ref(false)
  const isDesktop = ref(true)
  const isLoading = ref(false)
  const loadingText = ref('')
  const toasts = ref([])
  const modals = ref([])
  const breadcrumbs = ref([])

  // 当前主题信息
  const currentTheme = computed(() =>
    THEMES.find(t => t.id === theme.value) || THEMES[0]
  )

  // 设备检测
  function detectDevice() {
    const width = window.innerWidth
    isMobile.value = width < 768
    isTablet.value = width >= 768 && width < 1024
    isDesktop.value = width >= 1024

    // 移动端自动收起侧边栏
    if (isMobile.value) {
      sidebarCollapsed.value = true
    }
  }

  // 初始化设备检测
  function initDeviceDetection() {
    detectDevice()
    window.addEventListener('resize', detectDevice)
  }

  // 主题切换
  function toggleTheme() {
    const currentIndex = THEMES.findIndex(t => t.id === theme.value)
    const nextIndex = (currentIndex + 1) % THEMES.length
    theme.value = THEMES[nextIndex].id
    localStorage.setItem('theme', theme.value)
    applyTheme()
  }

  function setTheme(newTheme) {
    if (THEMES.find(t => t.id === newTheme)) {
      theme.value = newTheme
      localStorage.setItem('theme', newTheme)
      applyTheme()
    }
  }

  function applyTheme() {
    const nextTheme = normalizeTheme(theme.value)
    theme.value = nextTheme
    localStorage.setItem('theme', nextTheme)

    document.documentElement.classList.remove('dark', 'light', 'pure-bw', 'high-contrast')
    document.documentElement.classList.add(nextTheme)
    document.documentElement.setAttribute('data-theme', nextTheme)
    document.body.setAttribute('data-theme', nextTheme)
  }

  // 侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value)
  }

  function setSidebarCollapsed(collapsed) {
    sidebarCollapsed.value = collapsed
    localStorage.setItem('sidebarCollapsed', collapsed)
  }

  // 全屏加载
  function showLoading(text = '加载中...') {
    isLoading.value = true
    loadingText.value = text
  }

  function hideLoading() {
    isLoading.value = false
    loadingText.value = ''
  }

  // Toast 通知（自动消失由 ToastContainer 的 animationend 事件处理）
  let toastId = 0

  function showToast(toast) {
    const id = ++toastId
    const duration = toast.duration !== undefined ? toast.duration : 2000
    const newToast = {
      id,
      type: toast.type || 'info',
      message: toast.message,
      duration,
      closable: toast.closable !== false
    }
    toasts.value.push(newToast)
    return id
  }

  function removeToast(id) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function success(message, options = {}) {
    return showToast({ ...options, message, type: 'success' })
  }

  function error(message, options = {}) {
    return showToast({ ...options, message, type: 'error' })
  }

  function warning(message, options = {}) {
    return showToast({ ...options, message, type: 'warning' })
  }

  function info(message, options = {}) {
    return showToast({ ...options, message, type: 'info' })
  }

  // ============ Comprehensive Prompt Messages ============
  function prompt(action, detail = {}) {
    const prompts = {
      // ---- Team Management ----
      'team.create': {
        title: '创建团队',
        message: `确定要创建团队「${detail.name}」吗？团队创建后将成为所有者。`,
        confirmText: '创建',
        confirmType: 'primary'
      },
      'team.delete': {
        title: '删除团队',
        message: `确定要删除团队「${detail.name}」吗？此操作不可恢复，所有成员将被移除。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'team.edit': {
        title: '更新团队',
        message: `确定要更新团队「${detail.name}」的配置吗？`,
        confirmText: '保存',
        confirmType: 'primary'
      },

      // ---- Member Management ----
      'member.invite': {
        title: '邀请成员',
        message: `确定要向「${detail.email}」发送加入团队「${detail.tenantName}」的邀请吗？`,
        confirmText: '发送邀请',
        confirmType: 'primary'
      },
      'member.remove': {
        title: '移除成员',
        message: `确定要将「${detail.username}」从团队中移除吗？该成员将失去所有访问权限。`,
        confirmText: '移除',
        confirmType: 'danger'
      },
      'member.role_change': {
        title: '变更角色',
        message: `确定要将「${detail.username}」的角色从「${detail.fromRole}」变更为「${detail.toRole}」吗？`,
        confirmText: '确认变更',
        confirmType: 'warning'
      },

      // ---- Skill Management ----
      'skill.create': {
        title: '创建技能',
        message: `确定要创建技能「${detail.name}」吗？`,
        confirmText: '创建',
        confirmType: 'primary'
      },
      'skill.delete': {
        title: '删除技能',
        message: `确定要删除技能「${detail.name}」吗？此操作不可恢复，所有分配记录将被清除。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'skill.assign': {
        title: '分配技能',
        message: `确定要为「${detail.username}」分配技能「${detail.skillName}」吗？角色：${detail.role}，熟练度：${detail.level}/5`,
        confirmText: '确认分配',
        confirmType: 'primary'
      },
      'skill.unassign': {
        title: '取消技能分配',
        message: `确定要移除「${detail.username}」的技能「${detail.skillName}」分配吗？`,
        confirmText: '移除',
        confirmType: 'danger'
      },

      // ---- Task Management ----
      'task.create': {
        title: '创建任务',
        message: `确定要创建任务「${detail.title}」吗？优先级：${detail.priority || '中'}`,
        confirmText: '创建',
        confirmType: 'primary'
      },
      'task.delete': {
        title: '删除任务',
        message: `确定要删除任务「${detail.title}」吗？此操作不可恢复。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'task.assign': {
        title: '分配任务',
        message: `确定要将任务「${detail.title}」分配给「${detail.username}」吗？`,
        confirmText: '确认分配',
        confirmType: 'primary'
      },
      'task.status_change': {
        title: '变更任务状态',
        message: `确定要将任务「${detail.title}」状态变更为「${detail.toStatus}」吗？`,
        confirmText: '确认',
        confirmType: 'warning'
      },
      'task.complete': {
        title: '完成任务',
        message: `确定要标记任务「${detail.title}」为已完成吗？`,
        confirmText: '完成',
        confirmType: 'success'
      },

      // ---- Workflow Operations ----
      'workflow.delete': {
        title: '删除工作流',
        message: `确定要删除工作流「${detail.name}」吗？所有执行记录也将被删除。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'workflow.execute': {
        title: '执行工作流',
        message: `确定要立即执行工作流「${detail.name}」吗？`,
        confirmText: '执行',
        confirmType: 'primary'
      },
      'workflow.stop': {
        title: '停止执行',
        message: `确定要停止工作流「${detail.name}」的执行吗？`,
        confirmText: '停止',
        confirmType: 'danger'
      },
      'workflow.duplicate': {
        title: '复制工作流',
        message: `确定要复制工作流「${detail.name}」吗？`,
        confirmText: '复制',
        confirmType: 'primary'
      },
      'workflow.export': {
        title: '导出工作流',
        message: `确定要导出工作流「${detail.name}」的配置吗？`,
        confirmText: '导出',
        confirmType: 'primary'
      },
      'workflow.import': {
        title: '导入工作流',
        message: `确定要导入工作流配置吗？将覆盖现有工作流。`,
        confirmText: '导入',
        confirmType: 'warning'
      },

      // ---- Agent Operations ----
      'agent.delete': {
        title: '删除 Agent',
        message: `确定要删除 Agent「${detail.name}」吗？所有对话历史将被清除。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'agent.reset': {
        title: '重置对话',
        message: `确定要重置 Agent「${detail.name}」的对话历史吗？`,
        confirmText: '重置',
        confirmType: 'warning'
      },

      // ---- Variable Operations ----
      'variable.delete': {
        title: '删除变量',
        message: `确定要删除变量「${detail.name}」吗？引用此变量的工作流可能受影响。`,
        confirmText: '删除',
        confirmType: 'danger'
      },

      // ---- Credential Operations ----
      'credential.delete': {
        title: '删除凭证',
        message: `确定要删除凭证「${detail.name}」吗？使用此凭证的集成将中断。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'credential.rotate': {
        title: '轮换凭证',
        message: `确定要轮换凭证「${detail.name}」的密钥吗？旧密钥将立即失效。`,
        confirmText: '轮换',
        confirmType: 'warning'
      },

      // ---- Execution Operations ----
      'execution.delete': {
        title: '删除执行记录',
        message: `确定要删除执行记录 #${detail.id} 吗？此操作不可恢复。`,
        confirmText: '删除',
        confirmType: 'danger'
      },
      'execution.replay': {
        title: '重放执行',
        message: `确定要使用相同的输入重放工作流「${detail.workflowName}」的执行吗？`,
        confirmText: '重放',
        confirmType: 'primary'
      },
      'execution.cancel': {
        title: '取消执行',
        message: `确定要取消当前正在执行的工作流「${detail.workflowName}」吗？`,
        confirmText: '取消',
        confirmType: 'danger'
      },

      // ---- Data Operations ----
      'data.export': {
        title: '导出数据',
        message: `确定要导出数据吗？导出过程可能需要一些时间。`,
        confirmText: '导出',
        confirmType: 'primary'
      },
      'data.clear': {
        title: '清空数据',
        message: `确定要清空所有数据吗？此操作不可恢复，所有工作流、执行记录将被永久删除。`,
        confirmText: '清空',
        confirmType: 'danger'
      },

      // ---- Settings ----
      'settings.save': {
        title: '保存设置',
        message: `确定要保存当前设置吗？部分更改可能需要刷新页面后生效。`,
        confirmText: '保存',
        confirmType: 'primary'
      },
      'settings.reset': {
        title: '重置设置',
        message: `确定要将所有设置重置为默认值吗？`,
        confirmText: '重置',
        confirmType: 'warning'
      },

      // ---- Default ----
      'default': {
        title: detail.title || '确认操作',
        message: detail.message || '确定要执行此操作吗？',
        confirmText: '确定',
        cancelText: '取消',
        confirmType: 'primary'
      }
    }

    const p = prompts[action] || prompts['default']
    return confirm({
      title: p.title,
      message: p.message,
      confirmText: p.confirmText,
      cancelText: p.cancelText,
      confirmType: p.confirmType
    })
  }

  // Modal
  let modalId = 0

  function showModal(modal) {
    const id = ++modalId
    const newModal = {
      id,
      ...modal,
      visible: true
    }
    modals.value.push(newModal)
    return id
  }

  function closeModal(id) {
    const modal = modals.value.find(m => m.id === id)
    if (modal) {
      modal.visible = false
      setTimeout(() => {
        modals.value = modals.value.filter(m => m.id !== id)
      }, 300)
    }
  }

  function confirm(options) {
    return new Promise((resolve) => {
      showModal({
        title: options.title || '确认',
        message: options.message || '确定要执行此操作吗？',
        confirmText: options.confirmText || '确定',
        cancelText: options.cancelText || '取消',
        confirmType: options.confirmType || 'primary',
        closeOnOverlay: options.closeOnOverlay !== false,
        onConfirm: () => resolve(true),
        onCancel: () => resolve(false),
      })
    })
  }

  // 面包屑
  function setBreadcrumbs(items) {
    breadcrumbs.value = items
  }

  function clearBreadcrumbs() {
    breadcrumbs.value = []
  }

  // 初始化
  function init() {
    applyTheme()
    initDeviceDetection()
  }

  // 清理
  function cleanup() {
    window.removeEventListener('resize', detectDevice)
  }

  return {
    // State
    theme,
    sidebarCollapsed,
    sidebarWidth,
    isMobile,
    isTablet,
    isDesktop,
    isLoading,
    loadingText,
    toasts,
    modals,
    breadcrumbs,
    currentTheme,
    themes: THEMES,
    // Actions
    toggleTheme,
    setTheme,
    applyTheme,
    toggleSidebar,
    setSidebarCollapsed,
    showLoading,
    hideLoading,
    showToast,
    removeToast,
    success,
    error,
    warning,
    info,
    prompt,
    showModal,
    closeModal,
    confirm,
    setBreadcrumbs,
    clearBreadcrumbs,
    init,
    cleanup,
    openCommandPalette: null
  }
})
