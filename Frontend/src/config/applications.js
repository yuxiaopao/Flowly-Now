export const APPLICATIONS = Object.freeze({
  resource: '/applications/',
  pageSize: 20,
  nameMaxLength: 200,
  keyNameMaxLength: 100,
  descriptionMaxLength: 8000,
  promptMaxLength: 16000,
  maxInputBytes: 100 * 1024,
  executionTimeoutMs: 180000,
  requestPollMs: 1500,
  inputDraftDiscardTitle: '放弃尚未保存的测试输入？',
  inputDraftDiscardMessage: '测试输入尚未保存为用例。离开后该输入会丢失，可先在回归评测中保存。',
  defaultTopK: 5,
  maxTopK: 50,
  defaultPrompt: '请依据检索到的资料回答问题；资料不足时明确说明，不要编造。',
  kinds: Object.freeze([
    Object.freeze({ value: 'knowledge', label: '知识助手', description: '连接知识库，交付有来源的问答 API。' }),
    Object.freeze({ value: 'workflow', label: '自动化', description: '将工作流变成可调用、可追踪的应用。' }),
  ]),
  statuses: Object.freeze({ draft: '草稿', published: '已发布', unpublished: '已下线' }),
  requestStatuses: Object.freeze({ completed: '成功', failed: '失败', running: '运行中', rejected: '已拒绝' }),
  requestModes: Object.freeze({ test: '草稿测试', invoke: '发布 API', evaluation: '回归评测' }),
  tabs: Object.freeze([
    Object.freeze({ id: 'build', label: '配置' }),
    Object.freeze({ id: 'test', label: '测试' }),
    Object.freeze({ id: 'evaluations', label: '回归评测' }),
    Object.freeze({ id: 'publish', label: '发布与接入' }),
    Object.freeze({ id: 'requests', label: '请求日志' }),
  ]),
})

export function applicationKindLabel(kind) {
  return APPLICATIONS.kinds.find(item => item.value === kind)?.label || kind
}

export function applicationStatus(application) {
  return application?.status || (application?.activeRelease ? 'published' : 'draft')
}

export function applicationStatusLabel(application) {
  const status = applicationStatus(application)
  return APPLICATIONS.statuses[status] || status
}

export function emptyApplicationDraft(kind) {
  return kind === 'workflow'
    ? { workflow_id: '' }
    : { collection_id: '', system_prompt: APPLICATIONS.defaultPrompt, top_k: APPLICATIONS.defaultTopK, min_similarity: 0 }
}

export function parseApplicationInput(source) {
  let input
  try { input = JSON.parse(source) } catch { throw new Error('输入不是有效 JSON，请检查引号、逗号与括号。') }
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('输入必须是 JSON 对象，例如 {"query":"你的问题"}。')
  if (new TextEncoder().encode(JSON.stringify(input)).length > APPLICATIONS.maxInputBytes) throw new Error('输入超过 100 KiB，请缩小数据后重试。')
  return input
}

export function applicationDate(value) {
  if (!value) return '尚无记录'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '时间不可用' : date.toLocaleString('zh-CN', { hour12: false })
}

export function applicationUsage(value, suffix = '') {
  return value === null || value === undefined ? '未提供' : `${value.toLocaleString('zh-CN')}${suffix}`
}

export function newApplicationRequestKey() {
  if (globalThis.crypto.randomUUID) return globalThis.crypto.randomUUID()
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
