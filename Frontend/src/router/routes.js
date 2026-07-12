import { useAuthStore } from '@/stores/auth'

// 路由配置
const routes = [
  // 公开路由
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/views/Landing.vue'),
    meta: { title: 'Flowly - AI Agent 工作流编排平台', requiresAuth: false, layout: 'blank' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/AuthPortal.vue'),
    meta: { title: '登录', requiresAuth: false, layout: 'blank' }
  },
  {
    path: '/register',
    name: 'Register',
    redirect: (to) => ({
      path: '/login',
      query: { ...to.query, tab: 'register' },
    }),
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPassword.vue'),
    meta: { title: '忘记密码', requiresAuth: false, layout: 'blank' }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/auth/ResetPassword.vue'),
    meta: { title: '重置密码', requiresAuth: false, layout: 'blank' }
  },

  // 认证后访问
  {
    path: '/home',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/Home.vue'),
    meta: { title: '仪表盘', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/workflows',
    name: 'WorkflowList',
    component: () => import('@/views/workflow/List.vue'),
    meta: { title: '工作流列表', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/workflows/new',
    name: 'WorkflowCreate',
    component: () => import('@/views/workflow/Editor.vue'),
    meta: { title: '创建工作流', requiresAuth: true, layout: 'editor' }
  },
  {
    path: '/workflows/:id/edit',
    name: 'WorkflowEdit',
    component: () => import('@/views/workflow/Editor.vue'),
    meta: { title: '编辑工作流', requiresAuth: true, layout: 'editor' }
  },
  {
    path: '/workflows/:id',
    name: 'WorkflowDetail',
    component: () => import('@/views/workflow/Detail.vue'),
    meta: { title: '工作流详情', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/workflows/:id/execute',
    name: 'WorkflowExecute',
    component: () => import('@/views/workflow/Execute.vue'),
    meta: { title: '执行工作流', requiresAuth: true, layout: 'default' }
  },

  // Agent 相关
  {
    path: '/agents',
    name: 'AgentList',
    component: () => import('@/views/agent/List.vue'),
    meta: { title: 'Agent 列表', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/agents/new',
    name: 'AgentCreate',
    component: () => import('@/views/agent/Create.vue'),
    meta: { title: '创建 Agent', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/agents/:id/edit',
    name: 'AgentEdit',
    component: () => import('@/views/agent/Create.vue'),
    meta: { title: '编辑 Agent', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/agents/:id/debug',
    name: 'AgentDebugger',
    component: () => import('@/views/agent/Debugger.vue'),
    meta: { title: 'Agent 调试器', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/agents/collaborate',
    name: 'AgentCollaborate',
    component: () => import('@/views/agent/Collaborate.vue'),
    meta: { title: '多智能体协作', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/agents/marketplace',
    name: 'AgentMarketplace',
    component: () => import('@/views/agent/Marketplace.vue'),
    meta: { title: 'Agent 市场', requiresAuth: true, layout: 'default' }
  },

  // NL 生成工作流
  {
    path: '/nl-create',
    name: 'NLCreator',
    component: () => import('@/views/nl-workflow/Creator.vue'),
    meta: { title: '自然语言创建', requiresAuth: true, layout: 'default' }
  },

  // 知识库 / RAG
  {
    path: '/knowledge',
    name: 'KnowledgeBase',
    component: () => import('@/views/knowledge/Index.vue'),
    meta: { title: '知识库', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/knowledge/:id',
    name: 'CollectionDetail',
    component: () => import('@/views/knowledge/CollectionDetail.vue'),
    meta: { title: '集合详情', requiresAuth: true, layout: 'default' }
  },

  // 数据集推荐
  {
    path: '/dataset-recommend',
    name: 'DatasetRecommend',
    component: () => import('@/views/dataset/DatasetRecommend.vue'),
    meta: { title: '数据集推荐', requiresAuth: true, layout: 'default' }
  },

  // 数据集管理
  {
    path: '/datasets',
    name: 'DatasetList',
    component: () => import('@/views/datasets/DatasetList.vue'),
    meta: { title: '数据集管理', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/datasets/:id',
    name: 'DatasetDetail',
    component: () => import('@/views/datasets/DatasetDetail.vue'),
    meta: { title: '数据集详情', requiresAuth: true, layout: 'default' }
  },

  // 数据增强
  {
    path: '/augmentations',
    name: 'AugmentationStatus',
    component: () => import('@/views/dataset/AugmentationStatus.vue'),
    meta: { title: '数据增强任务', requiresAuth: true, layout: 'default' }
  },

  // 标注工作台
  {
    path: '/annotations/:id',
    name: 'AnnotationWorkspace',
    component: () => import('@/views/dataset/AnnotationWorkspace.vue'),
    meta: { title: '标注工作台', requiresAuth: true, layout: 'blank' }
  },

  // 训练页已迁移至工作流节点（旧链接重定向提示）
  {
    path: '/training',
    name: 'TrainingRedirect',
    component: () => import('@/views/training/TrainingRedirect.vue'),
    meta: { title: '训练（工作流）', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/training/yolo/:pathMatch(.*)*',
    redirect: '/training'
  },

  // 识别项目（website_generator 生成站点）
  {
    path: '/projects/:id',
    name: 'GeneratedSiteProject',
    component: () => import('@/views/projects/GeneratedSiteDetail.vue'),
    meta: { title: '识别项目', requiresAuth: true, layout: 'default' }
  },

  // Prompt 模板
  {
    path: '/prompts',
    name: 'PromptList',
    component: () => import('@/views/prompt/List.vue'),
    meta: { title: 'Prompt 模板', requiresAuth: true, layout: 'default' }
  },

  // 模型管理
  {
    path: '/models',
    name: 'ModelList',
    component: () => import('@/views/model/Index.vue'),
    meta: { title: '模型管理', requiresAuth: true, layout: 'default' }
  },

  // 向量存储管理
  {
    path: '/vector-stores',
    name: 'VectorStoreList',
    component: () => import('@/views/vector-store/Index.vue'),
    meta: { title: '向量存储', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/vector-stores/:id',
    name: 'VectorStoreDetail',
    component: () => import('@/views/vector-store/Detail.vue'),
    meta: { title: '向量存储详情', requiresAuth: true, layout: 'default' }
  },

  // 团队/租户
  {
    path: '/team',
    name: 'Team',
    component: () => import('@/views/team/Index.vue'),
    meta: { title: '团队管理', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/team/join',
    name: 'TeamJoin',
    component: () => import('@/views/team/Join.vue'),
    meta: { title: '加入团队', requiresAuth: true, layout: 'default' }
  },

  // 集成（归入个人中心，旧路径重定向）
  {
    path: '/integrations',
    redirect: '/settings/integrations',
  },

  // 监控中心
  {
    path: '/monitoring',
    name: 'Monitoring',
    component: () => import('@/views/monitoring/Index.vue'),
    meta: { title: '监控中心', requiresAuth: true, layout: 'default' }
  },

  // 数据分析
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('@/views/analytics/Index.vue'),
    meta: { title: '数据分析', requiresAuth: true, layout: 'default' }
  },

  // 代码图谱
  {
    path: '/codegraph',
    name: 'CodeGraph',
    component: () => import('@/views/codegraph/Index.vue'),
    meta: { title: '代码图谱', requiresAuth: true, layout: 'default' }
  },

  // API 测试工具
  {
    path: '/api-explorer',
    name: 'ApiExplorer',
    component: () => import('@/views/api-explorer/Index.vue'),
    meta: { title: 'API 测试', requiresAuth: true, layout: 'default' }
  },

  // 模板市场
  {
    path: '/marketplace',
    name: 'Marketplace',
    component: () => import('@/views/marketplace/Marketplace.vue'),
    meta: { title: '模板市场', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/marketplace/:id',
    name: 'TemplateDetail',
    component: () => import('@/views/marketplace/TemplateDetail.vue'),
    meta: { title: '模板详情', requiresAuth: true, layout: 'default' }
  },
  {
    path: '/my-templates',
    name: 'MyTemplates',
    component: () => import('@/views/marketplace/MyTemplates.vue'),
    meta: { title: '我的模板', requiresAuth: true, layout: 'default' }
  },

  // 执行历史
  {
    path: '/executions',
    name: 'ExecutionHistory',
    component: () => import('@/views/execution/History.vue'),
    meta: { title: '执行历史', requiresAuth: true, layout: 'default' }
  },

  // 工作流对比
  {
    path: '/workflows/diff',
    name: 'WorkflowDiff',
    component: () => import('@/views/workflow/Diff.vue'),
    meta: { title: '工作流对比', requiresAuth: true, layout: 'default' }
  },

  // 设置页面
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/Settings.vue'),
    meta: { title: '个人中心', requiresAuth: true, layout: 'default' },
    children: [
      {
        path: '',
        name: 'SettingsIndex',
        redirect: { name: 'SettingsProfile' }
      },
      {
        path: 'profile',
        name: 'SettingsProfile',
        component: () => import('@/views/settings/Profile.vue'),
        meta: { title: '个人资料' }
      },
      {
        path: 'api-keys',
        redirect: '/settings/credentials',
        meta: { title: 'API 密钥' }
      },
      {
        path: 'api-doc',
        name: 'SettingsApiDoc',
        component: () => import('@/views/settings/ApiDoc.vue'),
        meta: { title: 'API 文档' }
      },
      {
        path: 'notifications',
        name: 'SettingsNotifications',
        component: () => import('@/views/settings/Notifications.vue'),
        meta: { title: '通知与邮件' }
      },
      {
        path: 'preferences',
        name: 'SettingsPreferences',
        component: () => import('@/views/settings/Preferences.vue'),
        meta: { title: '偏好设置' }
      },
      {
        path: 'billing',
        name: 'SettingsBilling',
        component: () => import('@/views/settings/Billing.vue'),
        meta: { title: '订阅管理' }
      },
{
                  path: 'data-export',
                  name: 'SettingsDataExport',
                  component: () => import('@/views/settings/DataExport.vue'),
                  meta: { title: '数据管理' }
                },
                {
                  path: 'branding',
                  name: 'SettingsBranding',
                  component: () => import('@/views/settings/Branding.vue'),
                  meta: { title: '品牌定制' }
                },
                {
                  path: 'credentials',
                  name: 'SettingsCredentials',
                  component: () => import('@/views/settings/Credentials.vue'),
                  meta: { title: '凭证管理' }
                },
                {
                  path: 'integrations',
                  name: 'SettingsIntegrations',
                  component: () => import('@/views/settings/Integrations.vue'),
                  meta: { title: '第三方集成' }
                },
                {
                  path: 'desktop-agent',
                  name: 'SettingsDesktopAgent',
                  component: () => import('@/views/settings/DesktopAgent.vue'),
                  meta: { title: '桌面端' }
                }
            ]
          },

  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在', requiresAuth: false, layout: 'blank' }
  }
]

// 路由守卫
function setupRouterGuard(router) {
  router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()
    
    // 设置页面标题（嵌套路由取最深匹配项的 title）
    const routeTitle = [...to.matched].reverse().find((record) => record.meta?.title)?.meta?.title
    document.title = routeTitle
      ? `${routeTitle} - Flowly`
      : 'Flowly - AI Agent 工作流编排平台'

    // 检查是否需要认证
    if (to.meta.requiresAuth) {
      // 如果没有 token，跳转到登录页
      if (!authStore.token) {
        // 保存跳转前的位置
        const redirectPath = to.fullPath
        next({ name: 'Login', query: { redirect: redirectPath } })
        return
      }

      // 如果有 token 但没有用户信息，获取用户信息
      if (!authStore.user) {
        try {
          await authStore.fetchUserInfo()
        } catch (err) {
          // 获取失败，清除 token 并跳转登录
          authStore.clearAuth()
          next({ name: 'Login', query: { redirect: to.fullPath } })
          return
        }
      }
    }

    // 已登录用户访问登录/注册页，重定向到首页
    if (
      !to.meta.requiresAuth &&
      to.meta.layout === 'blank' &&
      authStore.isAuthenticated
    ) {
      next({ name: 'Dashboard' })
      return
    }

    // 已登录用户访问首页，重定向到仪表盘
    if (to.path === '/' && authStore.isAuthenticated) {
      next({ name: 'Dashboard' })
      return
    }

    next()
  })

  // 页面切换时滚动到顶部
  router.afterEach(() => {
    window.scrollTo(0, 0)
  })
}

export { routes, setupRouterGuard }
