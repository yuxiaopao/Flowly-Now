export const NL_CREATOR = Object.freeze({
  apiVersion: 1,
  outdatedBackend: '当前服务版本尚不支持保存编辑后的草稿，请更新或重启服务后重试。',
  storagePrefix: 'flowly_nl_workspace_v2',
  pageSize: 30,
  maxMessageLength: 20000,
  maxNameLength: 200,
  titleLength: 28,
  pollAttempts: 90,
  pollInterval: 2000,
  debounceMs: 250,
  scrollThreshold: 80,
  title: '语创',
  welcomeTitle: '今天，想让什么自动完成？',
  welcomeDescription: '从一个想法开始，一起把它变成工作流。',
  newConversation: '新对话',
  renameConversation: '重命名当前对话',
  conversationActions: '对话操作',
  preview: '工作流',
  closePreview: '收起工作流预览',
  modelSettings: '模型设置',
  modelSettingsWidth: 280,
  compactPreviewQuery: '(max-width: 1199px)',
  composerRows: { minRows: 1, maxRows: 4 },
  thinkingLabel: '讨论',
  generateLabel: '生成',
  thinkingPlaceholder: '描述你的想法，或一起梳理需求…',
  generatePlaceholder: '描述你想自动完成的任务…',
  thinkingHint: '讨论需求，不会自动生成',
  generateHint: '根据当前需求生成工作流',
  keyboardHint: 'Enter 发送 · Shift + Enter 换行',
  greeting: '从一个具体目标开始。告诉我输入是什么、希望如何处理，以及最终需要什么结果。你可以先讨论方案，也可以直接生成工作流。',
  interrupted: '已停止接收。后台可能仍在处理，可点击「同步会话」查看最终结果。',
  incomplete: '连接提前结束，结果尚未确认。请同步会话后再决定是否重试。',
  storageError: '草稿未能保存到此设备，请导出对话备份。',
  noModel: '请先选择可用模型；可刷新列表或前往模型配置。',
  configInvalid: '配置必须是有效的 JSON 对象。',
  copySuccess: '内容已复制',
  copyError: '复制失败，请手动选择文本复制',
  savedConfig: '节点配置已保存到会话草稿',
})

export const NL_SESSION_STATUS = Object.freeze({
  active: { label: '讨论中', type: 'info' },
  processing: { label: '处理中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
})

export const NL_GUIDANCE_FIELDS = Object.freeze({
  '模型选择': ['model'], '系统提示词': ['system_prompt'], '温度参数': ['temperature'], '最大令牌数': ['max_tokens'],
  '代码语言': ['language'], '代码内容': ['code'], '超时时间': ['timeout'],
  '数据库类型': ['database_type', 'db_type'], '连接信息': ['host', 'connection_string'], '认证信息': ['username', 'credential_id'], 'SQL 语句': ['query', 'sql'],
  '请求 URL': ['url'], '请求方法': ['method'], '请求头': ['headers'], '认证方式': ['auth_type', 'credential_id'],
  '触发类型': ['trigger_type'], '触发条件': ['schedule', 'cron'], 'Cron 表达式': ['cron', 'schedule', 'cron_expression'], '时区': ['timezone'], '最大执行次数': ['max_runs'],
  '工具类型': ['tool_name', 'tool_type'], '工具配置': ['parameters', 'tool_config'],
  '输入类型': ['input_type'], '参数名称': ['input_name', 'name'], '默认值': ['default_value'], '输出类型': ['output_type'], '输出格式': ['format', 'output_format'],
})

export const NL_SMTP_REFERENCE = Object.freeze([
  { name: 'Gmail', host: 'smtp.gmail.com', port: '587', encrypt: 'TLS' },
  { name: 'QQ邮箱', host: 'smtp.qq.com', port: '587', encrypt: 'TLS' },
  { name: '163邮箱', host: 'smtp.163.com', port: '465', encrypt: 'SSL' },
])

export const NL_STARTERS = Object.freeze([
  { title: '知识库客服', category: '问答与检索', mode: 'thinking', prompt: '我想搭建知识库客服：根据产品文档回答问题，引用信息来源，无法回答时转人工。请先帮我明确需要准备的资料和流程。' },
  { title: '数据清洗与汇总', category: '数据处理', mode: 'generate', prompt: '创建一个数据处理工作流：读取 CSV 文件，检查空值与重复记录，输出清洗后的 CSV 和处理汇总，异常数据单独记录。' },
  { title: '网页采集与邮件', category: '信息自动化', mode: 'thinking', prompt: '我需要采集网页内容、生成摘要并发送邮件。请先确认目标网址、采集范围、收件人和失败处理方式，再设计流程。' },
  { title: '训练与识别网站', category: '模型应用', mode: 'thinking', prompt: '我有标注好的目标检测数据集，希望训练 YOLO 模型并生成识别网站。请先确认数据格式、可用算力和网站功能。' },
  { title: '多语言内容', category: '内容创作', mode: 'generate', prompt: '创建一个多语言内容工作流：接收中文原文，生成英文译文，检查术语一致性，输出中英对照文本与修改说明。' },
  { title: '视频制作方案', category: '多模态', mode: 'thinking', prompt: '我想制作短视频，包含脚本、分镜、画面、配音和字幕。请先确认主题、时长、风格与可用模型，再给出工作流方案。' },
])
