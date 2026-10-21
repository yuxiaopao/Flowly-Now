// 产品界面参数集中管理，保持页面与交互的一致性。
export const PRODUCT_UI = Object.freeze({
  mobileBreakpoint: 768,
  searchDebounceMs: 300,
  recentWorkflowLimit: 6,
  workflowPageSizes: Object.freeze([12, 24, 48, 96]),
  workflowViewStorageKey: 'flowly.workflow-view',
  workflowDefaultView: 'table',
  workflowViews: Object.freeze(['table', 'grid']),
})

export const TEMPLATE_CATEGORY_LABELS = Object.freeze({
  'ai-agent': 'AI 智能体', agent: 'AI 智能体', ai: 'AI 智能体',
  'rag-knowledge': '知识检索', rag: '知识检索',
  'data-pipeline': '数据管道', data: '数据处理',
  'office-automation': '办公自动化', automation: '自动化',
  'video-generation': '视频生成', multimodal: '多模态生成',
  'model-training': '模型训练', mlops: '机器学习与运维', utility: '实用工具',
})

export const AI_WORKBENCH = Object.freeze({
  label: 'AI 能力工作台',
  coreLabel: '小流',
  subtitle: '连接能力，编排智能',
  capabilities: Object.freeze([
    Object.freeze({ id: 'models', label: '模型推理', detail: '模型与接口', route: '/models', icon: 'Cpu', tone: 'violet' }),
    Object.freeze({ id: 'knowledge', label: '知识检索', detail: '知识库与 RAG', route: '/knowledge', icon: 'Database', tone: 'cyan' }),
    Object.freeze({ id: 'workflows', label: '工作流编排', detail: '节点与执行', route: '/workflows', icon: 'GitBranch', tone: 'blue' }),
  ]),
})
