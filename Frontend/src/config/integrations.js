/**
 * 第三方集成节点定义（n8n 风格）
 * 每个集成包含：品牌色、操作列表、默认配置、后端执行模板
 */

export const INTEGRATIONS = {
  slack: {
    label: 'Slack',
    brandColor: '#4A154B',
    category: 'communication',
    credentialProvider: 'slack',
    description: '发送消息、管理频道与文件',
    operations: [
      { value: 'post_message', label: '发送消息' },
      { value: 'update_message', label: '更新消息' },
      { value: 'list_channels', label: '列出频道' },
      { value: 'upload_file', label: '上传文件' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'post_message',
      channel: '',
      text: '{{input.message}}',
      blocks: '',
    },
  },
  discord: {
    label: 'Discord',
    brandColor: '#5865F2',
    category: 'communication',
    credentialProvider: 'discord',
    description: 'Webhook 与 Bot 消息推送',
    operations: [
      { value: 'send_webhook', label: 'Webhook 推送' },
      { value: 'send_message', label: 'Bot 发消息' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'send_webhook',
      webhookUrl: '',
      content: '{{input.message}}',
      username: 'Flowly Bot',
    },
  },
  telegram: {
    label: 'Telegram',
    brandColor: '#26A5E4',
    category: 'communication',
    credentialProvider: 'telegram',
    description: 'Bot 消息与媒体推送',
    operations: [
      { value: 'send_message', label: '发送文本' },
      { value: 'send_photo', label: '发送图片' },
      { value: 'send_document', label: '发送文件' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'send_message',
      chatId: '',
      text: '{{input.message}}',
      parseMode: 'Markdown',
    },
  },
  feishu: {
    label: '飞书',
    brandColor: '#3370FF',
    category: 'communication',
    credentialProvider: 'feishu',
    description: '飞书群消息、Webhook 与开放平台 API',
    operations: [
      { value: 'post_message', label: '发送消息' },
      { value: 'post_webhook', label: 'Webhook 推送' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'post_message',
      text: '{{input.message}}',
      receiveId: '',
      receiveIdType: 'chat_id',
      webhookUrl: '',
    },
  },
  dingtalk: {
    label: '钉钉',
    brandColor: '#0089FF',
    category: 'communication',
    credentialProvider: 'dingtalk',
    description: '钉钉群机器人消息推送',
    operations: [
      { value: 'post_message', label: '发送文本' },
      { value: 'post_markdown', label: '发送 Markdown' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'post_message',
      text: '{{input.message}}',
      webhookUrl: '',
      secret: '',
    },
  },
  wechat_work: {
    label: '企业微信',
    brandColor: '#07C160',
    category: 'communication',
    credentialProvider: 'wechat_work',
    description: '企业微信群机器人 Webhook',
    operations: [
      { value: 'post_message', label: '发送文本' },
      { value: 'post_markdown', label: '发送 Markdown' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'post_message',
      text: '{{input.message}}',
      webhookUrl: '',
    },
  },
  microsoft_teams: {
    label: 'Microsoft Teams',
    brandColor: '#6264A7',
    category: 'communication',
    description: 'Teams 频道消息与卡片',
    operations: [
      { value: 'post_message', label: '发送消息' },
      { value: 'post_adaptive_card', label: '发送卡片' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'post_message',
      webhookUrl: '',
      message: '{{input.message}}',
    },
  },
  notion: {
    label: 'Notion',
    brandColor: '#000000',
    category: 'productivity',
    description: '页面、数据库与块操作',
    operations: [
      { value: 'create_page', label: '创建页面' },
      { value: 'query_database', label: '查询数据库' },
      { value: 'update_page', label: '更新页面' },
      { value: 'append_block', label: '追加内容块' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'create_page',
      databaseId: '',
      title: '{{input.title}}',
      properties: '{}',
    },
  },
  google_sheets: {
    label: 'Google Sheets',
    brandColor: '#0F9D58',
    category: 'productivity',
    description: '读写电子表格',
    operations: [
      { value: 'read_rows', label: '读取行' },
      { value: 'append_row', label: '追加行' },
      { value: 'update_row', label: '更新行' },
      { value: 'clear_sheet', label: '清空表' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'read_rows',
      spreadsheetId: '',
      sheetName: 'Sheet1',
      range: 'A:Z',
    },
  },
  google_drive: {
    label: 'Google Drive',
    brandColor: '#4285F4',
    category: 'cloud',
    description: '文件上传下载与管理',
    operations: [
      { value: 'upload_file', label: '上传文件' },
      { value: 'download_file', label: '下载文件' },
      { value: 'list_files', label: '列出文件' },
      { value: 'delete_file', label: '删除文件' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'list_files',
      folderId: '',
      fileName: '',
    },
  },
  github: {
    label: 'GitHub',
    brandColor: '#24292F',
    category: 'dev',
    description: '仓库、Issue、PR 操作',
    operations: [
      { value: 'create_issue', label: '创建 Issue' },
      { value: 'list_issues', label: '列出 Issue' },
      { value: 'create_comment', label: '添加评论' },
      { value: 'trigger_workflow', label: '触发 Actions' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'create_issue',
      owner: '',
      repo: '',
      title: '{{input.title}}',
      body: '{{input.body}}',
    },
  },
  gitlab: {
    label: 'GitLab',
    brandColor: '#FC6D26',
    category: 'dev',
    description: '项目、Issue、MR 管理',
    operations: [
      { value: 'create_issue', label: '创建 Issue' },
      { value: 'list_pipelines', label: '列出流水线' },
      { value: 'trigger_pipeline', label: '触发流水线' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'create_issue',
      projectId: '',
      title: '{{input.title}}',
    },
  },
  jira: {
    label: 'Jira',
    brandColor: '#0052CC',
    category: 'productivity',
    description: 'Issue 创建与状态流转',
    operations: [
      { value: 'create_issue', label: '创建 Issue' },
      { value: 'update_issue', label: '更新 Issue' },
      { value: 'search_jql', label: 'JQL 搜索' },
      { value: 'add_comment', label: '添加评论' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'create_issue',
      projectKey: '',
      summary: '{{input.summary}}',
      issueType: 'Task',
    },
  },
  airtable: {
    label: 'Airtable',
    brandColor: '#18BFFF',
    category: 'productivity',
    description: 'Base 记录 CRUD',
    operations: [
      { value: 'list_records', label: '列出记录' },
      { value: 'create_record', label: '创建记录' },
      { value: 'update_record', label: '更新记录' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'list_records',
      baseId: '',
      tableName: '',
      fields: '{}',
    },
  },
  trello: {
    label: 'Trello',
    brandColor: '#0079BF',
    category: 'productivity',
    description: '看板卡片管理',
    operations: [
      { value: 'create_card', label: '创建卡片' },
      { value: 'move_card', label: '移动卡片' },
      { value: 'add_comment', label: '添加评论' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'create_card',
      listId: '',
      name: '{{input.title}}',
      desc: '',
    },
  },
  mysql: {
    label: 'MySQL',
    brandColor: '#00758F',
    category: 'database',
    description: 'SQL 查询与写入',
    operations: [
      { value: 'execute_query', label: '执行查询' },
      { value: 'insert', label: '插入数据' },
      { value: 'update', label: '更新数据' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'execute_query',
      query: 'SELECT * FROM table LIMIT 10',
      parameters: '[]',
    },
  },
  postgres: {
    label: 'PostgreSQL',
    brandColor: '#336791',
    category: 'database',
    description: 'PostgreSQL 数据库操作',
    operations: [
      { value: 'execute_query', label: '执行查询' },
      { value: 'insert', label: '插入数据' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'execute_query',
      query: 'SELECT * FROM table LIMIT 10',
    },
  },
  mongodb: {
    label: 'MongoDB',
    brandColor: '#47A248',
    category: 'database',
    description: '文档集合 CRUD',
    operations: [
      { value: 'find', label: '查询文档' },
      { value: 'insert', label: '插入文档' },
      { value: 'update', label: '更新文档' },
      { value: 'aggregate', label: '聚合管道' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'find',
      database: '',
      collection: '',
      filter: '{}',
    },
  },
  redis: {
    label: 'Redis',
    brandColor: '#DC382D',
    category: 'database',
    description: '键值缓存操作',
    operations: [
      { value: 'get', label: 'GET' },
      { value: 'set', label: 'SET' },
      { value: 'delete', label: 'DEL' },
      { value: 'publish', label: 'PUBLISH' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'get',
      key: '',
      value: '',
      ttl: 3600,
    },
  },
  elasticsearch: {
    label: 'Elasticsearch',
    brandColor: '#005571',
    category: 'database',
    description: '全文检索与索引',
    operations: [
      { value: 'search', label: '搜索文档' },
      { value: 'index', label: '索引文档' },
      { value: 'delete', label: '删除文档' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'search',
      index: '',
      query: '{}',
    },
  },
  aws_s3: {
    label: 'AWS S3',
    brandColor: '#FF9900',
    category: 'cloud',
    description: '对象存储读写',
    operations: [
      { value: 'upload', label: '上传对象' },
      { value: 'download', label: '下载对象' },
      { value: 'list_objects', label: '列出对象' },
      { value: 'delete_object', label: '删除对象' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'list_objects',
      bucket: '',
      key: '',
      region: 'us-east-1',
    },
  },
  ftp: {
    label: 'FTP/SFTP',
    brandColor: '#607D8B',
    category: 'cloud',
    description: '远程文件传输',
    operations: [
      { value: 'upload', label: '上传文件' },
      { value: 'download', label: '下载文件' },
      { value: 'list', label: '列出目录' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'list',
      protocol: 'sftp',
      remotePath: '/',
    },
  },
  stripe: {
    label: 'Stripe',
    brandColor: '#635BFF',
    category: 'finance',
    description: '支付与客户管理',
    operations: [
      { value: 'create_payment', label: '创建支付' },
      { value: 'list_customers', label: '列出客户' },
      { value: 'create_invoice', label: '创建发票' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'list_customers',
      amount: '',
      currency: 'usd',
    },
  },
  twilio: {
    label: 'Twilio',
    brandColor: '#F22F46',
    category: 'communication',
    description: '短信与语音通知',
    operations: [
      { value: 'send_sms', label: '发送短信' },
      { value: 'make_call', label: '拨打电话' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'send_sms',
      to: '',
      body: '{{input.message}}',
    },
  },
  sendgrid: {
    label: 'SendGrid',
    brandColor: '#1A82E2',
    category: 'communication',
    description: '事务邮件 API',
    operations: [
      { value: 'send_email', label: '发送邮件' },
      { value: 'list_contacts', label: '列出联系人' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'send_email',
      to: '',
      subject: '',
      htmlContent: '{{input.body}}',
    },
  },
  openai_api: {
    label: 'OpenAI',
    brandColor: '#10A37F',
    category: 'ai',
    description: 'OpenAI API 直接调用',
    operations: [
      { value: 'chat_completion', label: 'Chat 补全' },
      { value: 'embeddings', label: 'Embeddings' },
      { value: 'image_generation', label: '图像生成' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'chat_completion',
      model: 'gpt-4o',
      messages: '[{"role":"user","content":"{{input.prompt}}"}]',
    },
  },
  huggingface: {
    label: 'Hugging Face',
    brandColor: '#FFD21E',
    category: 'ai',
    description: 'Inference API 调用',
    operations: [
      { value: 'inference', label: '模型推理' },
      { value: 'text_classification', label: '文本分类' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'inference',
      modelId: '',
      inputs: '{{input.text}}',
    },
  },
  push_notification: {
    label: '推送通知',
    brandColor: '#6366F1',
    category: 'communication',
    description: 'App/Web 推送通知',
    operations: [
      { value: 'send', label: '发送通知' },
      { value: 'broadcast', label: '广播通知' },
    ],
    defaultConfig: {
      credentialId: '',
      operation: 'send',
      title: '{{input.title}}',
      body: '{{input.body}}',
      targetUserId: '',
    },
  },
  rss_feed: {
    label: 'RSS 订阅',
    brandColor: '#F97316',
    category: 'data',
    description: '读取 RSS/Atom 源',
    operations: [
      { value: 'read_feed', label: '读取 Feed' },
    ],
    defaultConfig: {
      operation: 'read_feed',
      url: '',
      maxItems: 20,
    },
  },
}

export const INTEGRATION_TYPES = Object.keys(INTEGRATIONS)

export function isIntegrationType(type) {
  return INTEGRATION_TYPES.includes(type)
}

export function getIntegrationMeta(type) {
  return INTEGRATIONS[type] || null
}

export function getIntegrationCredentialProvider(type) {
  return INTEGRATIONS[type]?.credentialProvider || type
}

export function getIntegrationDefaultConfig(type) {
  const meta = getIntegrationMeta(type)
  if (!meta) return {}
  return { ...meta.defaultConfig, integrationType: type }
}
