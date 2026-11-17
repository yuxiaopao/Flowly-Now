import { AGENT_DEBUG } from '@/config/agentDebug'

export async function* readJsonSse(response) {
  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try { const payload = await response.json(); message = payload.message || payload.error || message } catch { /* Non-JSON upstream error. */ }
    throw new Error(message)
  }
  if (!response.body) throw new Error('响应没有可读取的数据流')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''
  let ended = false
  function parse(frame) {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n')
    if (!data) return null
    if (data === '[DONE]') return { type: 'done' }
    try { return JSON.parse(data) } catch { throw new Error('响应数据流格式无效，请重试') }
  }
  try {
    for (;;) {
      const { value, done } = await reader.read()
      pending += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let boundary
      while ((boundary = /\r?\n\r?\n/.exec(pending))) {
        const frame = pending.slice(0, boundary.index)
        pending = pending.slice(boundary.index + boundary[0].length)
        if (frame.length > AGENT_DEBUG.maxSseFrameChars) throw new Error('响应数据帧超过限制')
        const parsed = parse(frame)
        if (parsed) yield parsed
      }
      if (pending.length > AGENT_DEBUG.maxSseFrameChars) throw new Error('响应数据帧超过限制')
      if (done) {
        ended = true
        if (pending.trim()) { const parsed = parse(pending); if (parsed) yield parsed }
        break
      }
    }
  } finally {
    if (!ended) await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
