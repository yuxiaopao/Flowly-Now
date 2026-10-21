/**
 * 工作流节点统一注册表（n8n 风格分类）
 * 单一数据源：面板分类、默认配置、MiniMap 颜色、NL 支持标记
 */
import {
  PlayCircle, Circle, GitBranch, RefreshCw, Timer, SplitSquareHorizontal,
  GitMerge, Zap, MessageSquare, Bot, Brain, BookOpen, FileText, LogOut,
  Code, Variable as VariableIcon, Hammer, Webhook, Mail, Shuffle, Key,
  Filter, Calendar, Database, Globe, Sparkles, Search, Shield, Layers, Rss, Cloud, Server, Send, MessageCircle, Hash, Sheet, FileSpreadsheet,
  Braces, ShieldCheck, Monitor, ScanSearch, Upload, Tags, Target, Rocket,
  Video, Volume2, Subtitles, Image, Languages, FileInput, FileOutput, Cpu, BarChart3,
  Palette, Layout, Code2, ClipboardCheck,
  Slack, Github, Gitlab, Trello, HardDrive, Table2, Ticket, DatabaseBackup, LeafyGreen,
  Bell, BellRing, Phone, CreditCard, Users, FolderUp, Package, Plug, Smartphone,
} from 'lucide-vue-next'
import {
  INTEGRATIONS,
  INTEGRATION_TYPES,
  getIntegrationDefaultConfig,
  isIntegrationType,
} from './integrations'

const C = '#000'

function node(type, label, icon, description, color, opts = {}) {
  return {
    type,
    label,
    icon,
    description,
    color,
    bgColor: opts.bgColor ?? C,
    shortcut: opts.shortcut ?? '',
    nlSupported: opts.nlSupported ?? false,
    isTrigger: opts.isTrigger ?? false,
    isIntegration: opts.isIntegration ?? false,
  }
}

/** 集成节点图标（Lucide 语义化映射，避免全部使用同一占位图标） */
const INTEGRATION_ICON_MAP = {
  slack: Slack,
  discord: Hash,
  telegram: Send,
  feishu: MessageSquare,
  dingtalk: Bell,
  wechat_work: Smartphone,
  microsoft_teams: Users,
  notion: BookOpen,
  google_sheets: Sheet,
  google_drive: HardDrive,
  github: Github,
  gitlab: Gitlab,
  jira: Ticket,
  airtable: Table2,
  trello: Trello,
  mysql: Database,
  postgres: DatabaseBackup,
  mongodb: LeafyGreen,
  redis: Zap,
  elasticsearch: Search,
  aws_s3: Package,
  ftp: FolderUp,
  stripe: CreditCard,
  twilio: Phone,
  sendgrid: Mail,
  openai_api: Sparkles,
  huggingface: Brain,
  push_notification: BellRing,
  rss_feed: Rss,
}

export function getIntegrationIcon(type) {
  return INTEGRATION_ICON_MAP[type] || Plug
}

function integrationNode(type) {
  const meta = INTEGRATIONS[type]
  if (!meta) return null
  return node(
    type,
    meta.label,
    getIntegrationIcon(type),
    meta.description,
    meta.brandColor,
    { isIntegration: true, bgColor: '#fff' }
  )
}

/** n8n 风格分类 */
export const NODE_CATEGORIES = [
  {
    id: 'trigger',
    label: '触发器',
    icon: PlayCircle,
    nodes: [
      node('start', '开始', PlayCircle, '工作流入口点', '#10b981', { shortcut: 'S', nlSupported: true, isTrigger: true }),
      node('end', '结束', Circle, '工作流结束点', '#ef4444', { shortcut: 'E', nlSupported: true, isTrigger: true }),
      node('manual', '手动触发', PlayCircle, '手动点击执行一次', '#f59e0b', { isTrigger: true }),
      node('schedule', '定时触发', RefreshCw, 'Cron 表达式定时执行', '#06b6d4', { isTrigger: true }),
      node('webhook', 'Webhook', Webhook, '接收 HTTP 请求触发', '#3b82f6', { nlSupported: true, isTrigger: true }),
      node('form', '表单触发', FileText, '用户提交表单时触发', '#8b5cf6', { isTrigger: true }),
    ],
  },
  {
    id: 'flow',
    label: '控制流',
    icon: GitBranch,
    nodes: [
      node('condition', '条件判断', GitBranch, '根据条件分流执行', '#3b82f6', { shortcut: 'C', nlSupported: true }),
      node('switch', '分支选择', SplitSquareHorizontal, '多分支条件路由', '#3b82f6', { shortcut: 'W' }),
      node('loop', '循环', RefreshCw, '重复执行循环体', '#f59e0b', { shortcut: 'L' }),
      node('delay', '延时', Timer, '等待指定时间', '#14b8a6', { shortcut: 'D' }),
      node('merge', '合并', GitMerge, '合并多个分支数据', '#22c55e'),
      node('split', '批量拆分', Layers, '拆分数据并行处理', '#ec4899'),
      node('filter', '过滤器', Filter, '按条件过滤数据项', '#f97316'),
      node('subworkflow', '子工作流', GitMerge, '调用另一个工作流', '#8b5cf6', { shortcut: 'F' }),
    ],
  },
  {
    id: 'transform',
    label: '数据转换',
    icon: Shuffle,
    nodes: [
      node('input', '输入', FileText, '接收用户输入数据', '#06b6d4', { shortcut: 'I', nlSupported: true }),
      node('output', '输出', LogOut, '输出工作流结果', '#84cc16', { shortcut: 'O', nlSupported: true }),
      node('variable', '变量', VariableIcon, '变量赋值与读取', '#10b981', { shortcut: 'V' }),
      node('set', 'Set 赋值', Key, '快速设置字段值', '#14b8a6'),
      node('code', '代码执行', Code, '执行 JavaScript/Python', '#f97316', { shortcut: 'X', nlSupported: true }),
      node('transform', '数据转换', Shuffle, '映射/过滤/排序', '#8b5cf6', { shortcut: 'T' }),
      node('csv_transform', 'CSV 处理', FileSpreadsheet, 'CSV 解析与转换', '#22c55e'),
      node('json_transform', 'JSON 处理', Code, 'JSON 解析与构建', '#f59e0b'),
      node('json_parser', 'JSON 解析', Braces, '解析/序列化/校验 JSON', '#f59e0b'),
      node('text_template', '文本模板', FileText, 'Jinja 风格模板渲染', '#6366f1'),
      node('datetime', '日期时间', Calendar, '格式化与计算日期', '#6366f1'),
      node('rss_feed', 'RSS 订阅', Rss, '读取 RSS/Atom 源', '#f97316'),
    ],
  },
  {
    id: 'ai',
    label: 'AI 模型',
    icon: Zap,
    nodes: [
      node('llm', '大语言模型', Zap, '调用 LLM 生成内容', '#3b82f6', { shortcut: 'A', nlSupported: true }),
      node('prompt', '提示词', MessageSquare, '结构化提示词模板', '#f59e0b', { shortcut: 'P', nlSupported: true }),
      node('openai_api', 'OpenAI', Sparkles, 'OpenAI API 直接调用', '#10A37F', { isIntegration: true, bgColor: '#fff' }),
      node('huggingface', 'Hugging Face', Brain, 'HF Inference API', '#FFD21E', { isIntegration: true, bgColor: '#fff' }),
    ],
  },
  {
    id: 'agent',
    label: 'Agent 系统',
    icon: Bot,
    nodes: [
      node('agent', 'AI Agent', Bot, '自主规划执行 Agent', '#8b5cf6', { shortcut: 'G' }),
      node('planner', '任务规划', Brain, '分解复杂任务', '#8b5cf6', { shortcut: 'P' }),
      node('executor', '任务执行', Hammer, '执行规划子任务', '#8b5cf6', { shortcut: 'X' }),
      node('memory', '记忆存储', Database, 'Agent 上下文记忆', '#8b5cf6', { shortcut: 'M' }),
    ],
  },
  {
    id: 'communication',
    label: '通讯协作',
    icon: MessageCircle,
    nodes: [
      integrationNode('feishu'),
      integrationNode('dingtalk'),
      integrationNode('wechat_work'),
      integrationNode('slack'),
      integrationNode('discord'),
      integrationNode('telegram'),
      integrationNode('microsoft_teams'),
      node('email', '发送邮件', Mail, 'SMTP 邮件发送', '#dc2626', { shortcut: 'M', nlSupported: true }),
      integrationNode('twilio'),
      integrationNode('sendgrid'),
      integrationNode('push_notification'),
    ].filter(Boolean),
  },
  {
    id: 'productivity',
    label: '效率工具',
    icon: Sheet,
    nodes: [
      integrationNode('notion'),
      integrationNode('google_sheets'),
      integrationNode('google_drive'),
      integrationNode('jira'),
      integrationNode('airtable'),
      integrationNode('trello'),
      integrationNode('github'),
      integrationNode('gitlab'),
    ].filter(Boolean),
  },
  {
    id: 'database',
    label: '数据库',
    icon: Database,
    nodes: [
      integrationNode('mysql'),
      integrationNode('postgres'),
      integrationNode('mongodb'),
      integrationNode('redis'),
      integrationNode('elasticsearch'),
    ].filter(Boolean),
  },
  {
    id: 'cloud',
    label: '云服务',
    icon: Cloud,
    nodes: [
      integrationNode('aws_s3'),
      integrationNode('ftp'),
      integrationNode('stripe'),
    ].filter(Boolean),
  },
  {
    id: 'http',
    label: 'HTTP 与文件',
    icon: Webhook,
    nodes: [
      node('http', 'HTTP 请求', Webhook, 'REST API 请求', '#f97316', { shortcut: 'H', nlSupported: true }),
      node('web_scraper', '网页抓取', Globe, '抓取网页内容', '#10b981', { shortcut: 'S' }),
      node('file_reader', '文件读取', FileInput, '读取本地/云端文件', '#10b981', { shortcut: 'R' }),
      node('file_writer', '文件写入', FileOutput, '写入数据到文件', '#10b981', { shortcut: 'W' }),
      node('document_loader', '文档加载', BookOpen, 'PDF/Word/Excel 加载', '#06b6d4', { shortcut: 'L' }),
      node('tool', '内置工具', Hammer, '计算器/搜索等工具', '#ec4899', { shortcut: 'G', nlSupported: true }),
    ],
  },
  {
    id: 'rag',
    label: 'RAG 检索',
    icon: BookOpen,
    nodes: [
      node('embedding', '向量化', Cpu, '文本 Embedding', '#06b6d4', { shortcut: 'B' }),
      node('vector_store', '向量库', Database, '向量存储检索', '#06b6d4', { shortcut: 'K' }),
      node('retriever', '检索器', Search, '相似度检索', '#06b6d4', { shortcut: 'R' }),
      node('reranker', '重排序', Shield, '检索结果重排', '#06b6d4'),
    ],
  },
  {
    id: 'multimodal',
    label: '多模态生成',
    icon: Sparkles,
    nodes: [
      node('image_generation', '图像生成', Sparkles, 'AI 生成图像', '#ec4899', { shortcut: 'I' }),
      node('video_generation', '视频生成', Video, 'AI 生成视频', '#f97316', { shortcut: 'V' }),
      node('audio_generation', '音频生成', Volume2, 'AI 生成音频', '#d946ef', { shortcut: 'A' }),
      node('subtitle_generation', '字幕生成', Subtitles, '音视频字幕', '#a855f7', { shortcut: 'S' }),
      node('video_upload', '视频上传', Upload, '本地上传与实时预览', '#0284c7'),
      node('subtitle_translate', '字幕翻译', Languages, '分段翻译（单语言）', '#0ea5e9'),
      node('segment_dubbing', '分段配音', Volume2, 'CosyVoice 分段 TTS', '#06b6d4'),
      node('lip_sync', '口型同步', Video, 'VideoRetalk 口型对齐', '#8b5cf6'),
      node('subtitle_burn', '字幕烧录', Subtitles, 'FFmpeg 硬字幕烧录', '#f59e0b'),
      node('video_translation', '视频翻译(一体)', Languages, '一体化多语言流水线', '#64748b', { shortcut: 'T' }),
      node('image_editing', '图像编辑', Image, 'AI 编辑图像', '#f43f5e', { shortcut: 'E' }),
    ],
  },
  {
    id: 'mlops',
    label: '模型训练',
    icon: Brain,
    nodes: [
      node('dataset_upload', '数据集上传', Upload, '上传验证数据集', '#f59e0b', { shortcut: 'D' }),
      node('data_annotation', '数据标注', Tags, '数据集标注', '#f59e0b', { shortcut: 'N' }),
      node('data_augmentation', '数据增强', Layers, '数据增强变换', '#f59e0b', { shortcut: 'U' }),
      node('model_training', '模型训练', Brain, 'PyTorch / Transformers 通用训练', '#f59e0b', { shortcut: 'T' }),
      node('yolo_training', 'YOLO 训练', Target, '目标检测 YOLO 全流程（工作流内）', '#ef4444'),
      node('clip_classification', 'CLIP 分类', Layers, '零样本 / 微调分类', '#14b8a6'),
      node('clip_retrieval', 'CLIP 检索', Search, '图文索引与以图搜图', '#06b6d4'),
      node('project_profiler', '场景分析', ScanSearch, '分析类别与建站场景', '#a855f7'),
      node('model_evaluation', '模型评估', BarChart3, '评估模型性能', '#f59e0b', { shortcut: 'R' }),
      node('model_deployment', '模型部署', Rocket, '部署到生产', '#f59e0b', { shortcut: 'Y' }),
      node('website_generator', '网站生成', Globe, 'AI 生成识别/检索站脚手架', '#8b5cf6', { shortcut: 'W' }),
      node('backend_setup', '后端搭建', Code2, 'Agent 完善 Flask API 与错误处理', '#6366f1'),
      node('frontend_setup', '前端搭建', Layout, 'Agent 搭建现代化 Vue 布局', '#818cf8'),
      node('ui_beautify', 'UI 美化', Palette, 'Agent 优化视觉与主题', '#a855f7'),
      node('site_code_review', '代码复查', ClipboardCheck, 'Critic 复查并自动修复', '#10b981'),
      node('environment_provision', '环境配置', Server, 'Desktop 运行时与环境检测', '#06b6d4'),
      node('site_qa', '站点自查', ShieldCheck, 'L1–L4 全面 QA', '#10b981'),
      node('site_preview', '站点预览', Monitor, '节点内 iframe 预览', '#8b5cf6'),
      node('project_agent', '项目 Agent', Bot, '站点改码 + 强制 QA', '#ec4899'),
    ],
  },
]

/** 扁平节点列表 */
export function getAllNodes() {
  return NODE_CATEGORIES.flatMap((cat) => cat.nodes)
}

/** 按 type 索引 */
export function getNodeMeta(type) {
  return getAllNodes().find((n) => n.type === type) || null
}

/** 搜索过滤后的分类（保留非空分类） */
export function filterNodeCategories(query = '') {
  const q = query.trim().toLowerCase()
  if (!q) return NODE_CATEGORIES

  return NODE_CATEGORIES
    .map((cat) => ({
      ...cat,
      nodes: cat.nodes.filter(
        (n) =>
          n.label.toLowerCase().includes(q) ||
          n.description.toLowerCase().includes(q) ||
          n.type.toLowerCase().includes(q) ||
          (n.shortcut && n.shortcut.toLowerCase().includes(q))
      ),
    }))
    .filter((cat) => cat.nodes.length > 0)
}

/** MiniMap 节点颜色 */
const MINIMAP_COLORS = Object.fromEntries(
  getAllNodes().map((n) => [n.type, n.color])
)

export function getMinimapNodeColor(type) {
  if (isIntegrationType(type)) {
    return INTEGRATIONS[type]?.brandColor || '#6366f1'
  }
  return MINIMAP_COLORS[type] || '#6b7280'
}

/** 节点默认 config */
const BASE_DEFAULTS = {
  start: {},
  end: {},
  manual: { triggerType: 'manual' },
  schedule: { cron: '0 9 * * *', timezone: 'Asia/Shanghai' },
  webhook: { method: 'POST', path: '', authentication: 'none', responseMode: 'onReceived' },
  form: { fields: [], submitButtonText: '提交' },
  input: { placeholder: '请输入...' },
  output: {},
  llm: { model: '', temperature: 0.7, systemPrompt: '', userTemplate: '{input}' },
  prompt: { template: '', variables: [] },
  condition: { conditions: [], defaultBranch: 'false' },
  loop: { loopType: 'for', start: 0, end: 10, step: 1, whileCondition: 'i < 10', items: '', maxIterations: 100 },
  variable: { operation: 'set', variableName: '', variableValue: '', scope: 'local' },
  set: { mode: 'manual', fields: [{ name: '', value: '' }] },
  tool: { tool: 'calculator', parameters: {} },
  http: { method: 'GET', url: '', headers: '{}', body: '' },
  code: { code: 'input = input\noutput = {"result": input}' },
  subworkflow: { subworkflowId: '', subworkflowName: '', version: 'latest', inputMapping: [], outputMapping: [], executionMode: 'sync', timeout: 300, onError: 'stop', fallbackValue: null },
  switch: { label: '分支', branches: [{ id: 'branch_1', label: '条件 1', expression: '' }, { id: 'branch_2', label: '条件 2', expression: '' }], defaultBranch: '默认' },
  transform: { transformType: 'map', mappings: [], filterExpression: '', sortField: '', sortOrder: 'asc' },
  email: { to: '', cc: '', subject: '', isHtml: false, body: '', useGlobalSmtp: true, smtpConfig: { server: '', port: 587, useTls: true, username: '', password: '' } },
  delay: { delayType: 'fixed', duration: 1000, unit: 'ms' },
  merge: { mode: 'combine', joinMode: 'wait_all' },
  split: { batchSize: 10, field: '' },
  filter: { conditions: [{ field: '', operator: 'equals', value: '' }], combineMode: 'and' },
  json_transform: { operation: 'json_to_object' },
  json_parser: { action: 'parse', source_key: 'input' },
  text_template: { template: '你好，{{name}}' },
  datetime: { operation: 'format', format: 'YYYY-MM-DD HH:mm:ss', timezone: 'Asia/Shanghai' },
  rss_feed: { url: '', maxItems: 20 },
  website_generator: { websiteType: 'detection', waitForCompletion: true },
  backend_setup: { agentMode: 'auto', allowCoreEdit: true, autoQaAfterEdit: true },
  frontend_setup: { agentMode: 'auto', autoQaAfterEdit: true },
  ui_beautify: { agentMode: 'auto', autoQaAfterEdit: true },
  site_code_review: { agentMode: 'auto', maxRounds: 2 },
}

export function getDefaultNodeConfig(type) {
  if (isIntegrationType(type)) {
    return getIntegrationDefaultConfig(type)
  }
  return BASE_DEFAULTS[type] ? { ...BASE_DEFAULTS[type] } : {}
}

export { isIntegrationType, INTEGRATION_TYPES }
