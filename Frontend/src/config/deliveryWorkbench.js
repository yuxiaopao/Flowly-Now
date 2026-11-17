export const DELIVERY_WORKBENCH = Object.freeze({
  title: '交付工作台',
  subtitle: '从知识与流程，到团队真正用得上的应用。',
  periodLabel: '最近 7 天',
  avatarSize: 48,
  recentWorkflowLimit: 4,
  recentApplicationLimit: 6,
  recentRequestLimit: 8,
  failedOverview: '应用交付数据加载失败，请重试。已有构建资源仍可访问。',
  failedWorkflows: '工作流暂时无法加载。',
  numberFormat: Object.freeze({
    locale: 'zh-CN',
    decimal: Object.freeze({ maximumFractionDigits: 3 }),
    percent: Object.freeze({ style: 'percent', maximumFractionDigits: 1 }),
  }),
  steps: Object.freeze([
    Object.freeze({ number: '01', title: '接入知识', description: '导入文档，检查分块与检索结果', path: '/knowledge' }),
    Object.freeze({ number: '02', title: '构建应用', description: '绑定知识库，或接入已有工作流', path: '/applications?create=1' }),
    Object.freeze({ number: '03', title: '测试与发布', description: '验证真实输出，再激活固定版本', path: '/applications' }),
    Object.freeze({ number: '04', title: '接入与迭代', description: '管理调用密钥，追踪失败与回滚', path: '/applications' }),
  ]),
  resources: Object.freeze([
    Object.freeze({ title: '模型与连接', description: '配置应用实际使用的模型服务', path: '/models' }),
    Object.freeze({ title: '提示词', description: '维护可复用的指令与变量', path: '/prompts' }),
    Object.freeze({ title: '团队协作', description: '管理成员与共享资源的权限', path: '/team' }),
  ]),
})

export const DELIVERY_REQUEST_LABELS = Object.freeze({
  completed: '成功', failed: '失败', running: '运行中', rejected: '已拒绝',
})
export const DELIVERY_KIND_LABELS = Object.freeze({ knowledge: '知识助手', workflow: '工作流应用' })
