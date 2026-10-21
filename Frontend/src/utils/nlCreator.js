import { NL_CREATOR, NL_GUIDANCE_FIELDS } from '@/config/nlCreator'

export function guidanceList(value) { return Array.isArray(value) ? value : value ? [value] : [] }

export function nlErrorMessage(error) {
  const message = error?.message || String(error || '')
  if (/429|rate.?limit|quota|额度|配额/i.test(message)) return '模型调用额度或频率受限，请稍后重试或切换模型。'
  if (/401|unauthorized/i.test(message)) return '登录状态或模型授权已失效，请重新登录并检查模型配置。'
  return message || '请求失败，请稍后重试'
}

export function guidanceFieldConfigured(config, field) {
  return (NL_GUIDANCE_FIELDS[field] || [field]).some(key => {
    const value = config?.[key]
    if (typeof value === 'string') return Boolean(value.trim())
    if (value && typeof value === 'object') return Object.keys(value).length > 0
    return value !== null && value !== undefined && value !== ''
  })
}

export function latestWorkflow(tab) {
  return [...(tab?.messages || [])].reverse().find(message => message.workflow?.nodes?.length)?.workflow || null
}

export function parseNodeConfig(value) {
  const parsed = JSON.parse(value)
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error(NL_CREATOR.configInvalid)
  return parsed
}

export function conversationMarkdown(tab) {
  return [`# ${tab.title}`, ...(tab.messages || []).map(message => {
    const workflow = message.workflow ? `\n\n\`\`\`json\n${JSON.stringify(message.workflow, null, 2)}\n\`\`\`` : ''
    return `## ${{ user: '我', assistant: '语创', system: '系统' }[message.role] || message.role}\n\n${message.content || ''}${workflow}`
  })].join('\n\n')
}

/** Parse complete SSE frames, including fragmented UTF-8 and the final unterminated frame. */
export async function consumeNlStream(response, onEvent) {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(payload.error || payload.message || payload.detail || `请求失败 (${response.status})`)
    error.fallbackAllowed = [404, 405, 501].includes(response.status)
    throw error
  }
  if (!response.body) throw new Error(NL_CREATOR.incomplete)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false
  const dispatch = frame => {
    const payload = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
    if (!payload) return
    if (payload === '[DONE]') { finished = true; return }
    const event = JSON.parse(payload)
    if (event.type === 'error') throw new Error(event.error || event.message || NL_CREATOR.incomplete)
    onEvent(event)
    if (event.type === 'done') finished = true
  }
  try {
    let reading = true
    while (reading) {
      const { done, value } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let separator
      while ((separator = /\r?\n\r?\n/.exec(buffer))) {
        dispatch(buffer.slice(0, separator.index))
        buffer = buffer.slice(separator.index + separator[0].length)
      }
      if (done) { if (buffer.trim()) dispatch(buffer); reading = false }
    }
    if (!finished) throw new Error(NL_CREATOR.incomplete)
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
