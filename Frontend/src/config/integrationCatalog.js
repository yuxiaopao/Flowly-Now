export const INTEGRATION_UI = Object.freeze({
  title: '第三方集成',
  subtitle: '连接常用服务，验证后再投入使用。',
  availabilityNote: '目录展示已接入的能力。您的连接是否可用，以最近一次测试结果为准。',
  search: '搜索服务、能力或关键词', category: '服务分类', statusFilter: '连接状态',
  all: '全部服务', allStatuses: '全部状态', refresh: '刷新', configure: '配置连接', manage: '管理连接',
  empty: '没有匹配的集成', clearFilters: '清除筛选', loadError: '集成加载失败，请检查网络后重试。',
  retry: '重新加载', count: '项服务', configured: '项已配置', verified: '项已验证',
  docs: '官方接入文档', capabilities: '当前支持', setup: '如何接入', scope: '能力范围',
  name: '连接名称', save: '保存配置', saveTest: '保存并测试', test: '测试连接',
  saved: '配置已保存，请测试连接。', saveError: '配置保存失败，请检查填写内容。',
  actionError: '操作失败，请稍后重试。', disconnect: '断开连接', disconnected: '连接已断开，自动投递已停止。',
  remove: '删除连接', removeConfirm: '删除此连接及其投递记录？此操作无法撤销。', removed: '连接已删除。',
  cancel: '取消', confirm: '确认', close: '关闭', discard: '放弃未保存的修改？',
  newConnection: '新建另一条连接', chooseConnection: '选择已保存的连接', newName: '的新连接',
  secretSaved: '已加密保存，留空保留原值', secretHelp: '敏感字段加密保存，不会回传到浏览器。',
  clearSecret: '清除已保存的值', optional: '选填', required: '请填写',
  events: '订阅执行事件', eventsHelp: '验证成功后由后台任务服务投递，只通知您拥有的工作流。留空则仅手动测试；发送结果见下方投递记录。',
  evidence: '最近验证', never: '尚未验证', stateHelp: '验证结果是当时的请求结果，不代表实时在线。修改配置后需重新验证。',
  unsaved: '配置有未保存的修改。请保存并测试后再使用。',
  data: '最近读取的数据', noData: '尚未读取数据', emptyData: '请求成功，但没有可访问的数据。请检查资源共享范围和权限。',
  limited: '显示本次读取的前 20 项；完整资源请在原服务查看。',
  history: '最近投递', noHistory: '尚无投递记录。测试连接后可在这里查看结果。',
  historyError: '投递记录加载失败。', latency: '耗时', http: 'HTTP',
  savedConnections: '已保存的连接',
})

export const INTEGRATION_CATEGORIES = Object.freeze({
  all: '全部', communication: '通信', automation: '自动化', development: '开发工具',
  productivity: '协作', data: '数据', storage: '存储',
})

export const INTEGRATION_STATES = Object.freeze({
  unconfigured: { label: '待配置', type: 'info' },
  untested: { label: '待验证', type: 'warning' },
  success: { label: '已验证', type: 'success' },
  failed: { label: '验证失败', type: 'danger' },
  disconnected: { label: '已断开', type: 'info' },
})

export const INTEGRATION_EVENTS = Object.freeze({
  'execution.started': '工作流开始执行', 'execution.completed': '工作流执行成功',
  'execution.failed': '工作流执行失败', 'connection.test': '连接测试',
})
export const INTEGRATION_DELIVERY_STATES = Object.freeze({
  pending: '等待投递', sending: '投递中', success: '投递成功', failed: '投递失败', cancelled: '已取消',
})
export const INTEGRATION_MODES = Object.freeze({ webhook: 'Webhook', telegram: 'Bot API', api: 'API · 只读' })
export const INTEGRATION_PAGE_SIZE = 100
export const INTEGRATION_NAME_LIMIT = 200
export const INTEGRATION_FIELD_LIMIT = 4096
export const INTEGRATION_DATE_LOCALE = 'zh-CN'
