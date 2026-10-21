import { describe, expect, it } from 'vitest'
import { ReadableStream } from 'node:stream/web'
import { TextEncoder } from 'node:util'
import { latestWorkflow, parseNodeConfig, conversationMarkdown, consumeNlStream, guidanceList, guidanceFieldConfigured, nlErrorMessage } from '../../../Frontend/src/utils/nlCreator'

function response(chunks) {
  return { ok: true, body: new ReadableStream({ start(controller) {
    for (const chunk of chunks) controller.enqueue(chunk)
    controller.close()
  } }) }
}
const bytes = value => new TextEncoder().encode(value)

describe('NL workspace behavior', () => {
  it('explains provider limits and retains actionable validation errors', () => {
    expect(nlErrorMessage(new Error('Error code: 429 rate limit'))).toContain('额度或频率受限')
    expect(nlErrorMessage(new Error('HTTP 401'))).toContain('重新登录')
    expect(nlErrorMessage(new Error('节点不存在'))).toBe('节点不存在')
  })
  it('normalizes multi-node guidance and checks actual parameter keys including zero values', () => {
    expect(guidanceList(null)).toEqual([])
    expect(guidanceList({ node_type: 'code' })).toHaveLength(1)
    expect(guidanceList([{ node_type: 'code' }, { node_type: 'llm' }])).toHaveLength(2)
    expect(guidanceFieldConfigured({ language: 'python' }, '代码语言')).toBe(true)
    expect(guidanceFieldConfigured({ temperature: 0 }, '温度参数')).toBe(true)
    expect(guidanceFieldConfigured({ code: ' ' }, '代码内容')).toBe(false)
    expect(guidanceFieldConfigured({ parameters: {} }, '工具配置')).toBe(false)
  })
  it('finds the last actual workflow after conversational replies', () => {
    const workflow = { nodes: [{ id: 'n' }] }
    expect(latestWorkflow({ messages: [{ workflow }, { content: 'hello' }] })).toBe(workflow)
    expect(latestWorkflow({ messages: [{ workflow: {} }] })).toBeNull()
  })
  it('accepts nested configuration without changing user keys', () => {
    expect(parseNodeConfig('{"apiKey":"x","some_field":{"KeepCASE":true}}')).toEqual({ apiKey: 'x', some_field: { KeepCASE: true } })
    for (const value of ['null', '[]', '2', '"text"', '{oops}']) expect(() => parseNodeConfig(value)).toThrow()
  })
  it('exports the full conversation including executable workflow', () => {
    const markdown = conversationMarkdown({ title: '测试', messages: [{ role: 'user', content: '需求' }, { role: 'assistant', content: '完成', workflow: { nodes: [] } }] })
    expect(markdown).toContain('## 我\n\n需求')
    expect(markdown).toContain('```json')
    expect(markdown).toContain('"nodes": []')
  })
  it('decodes fragmented UTF-8, CRLF frames and a final event without newline', async () => {
    const encoded = bytes(': heartbeat\r\n\r\ndata:{"type":"token","content":"你好"}\r\n\r\ndata: {"type":"done"}')
    const events = []
    await consumeNlStream(response([...encoded].map(byte => Uint8Array.of(byte))), event => events.push(event))
    expect(events).toEqual([{ type: 'token', content: '你好' }, { type: 'done' }])
  })
  it('propagates server errors instead of swallowing them or permitting duplicate retry', async () => {
    await expect(consumeNlStream(response([bytes('data: {"type":"error","error":"模型不可用"}\n\n')]), () => {})).rejects.toThrow('模型不可用')
  })
  it('rejects truncated and malformed streams', async () => {
    await expect(consumeNlStream(response([bytes('data: {"type":"token","content":"半段"}\n\n')]), () => {})).rejects.toThrow('连接提前结束')
    await expect(consumeNlStream(response([bytes('data: not-json\n\n')]), () => {})).rejects.toThrow()
  })
  it('permits fallback only when a streaming endpoint does not exist', async () => {
    for (const status of [401, 429, 500, 404, 405, 501]) {
      let error
      try { await consumeNlStream({ ok: false, status, json: async () => ({ error: '失败' }) }, () => {}) } catch (caught) { error = caught }
      expect(error.fallbackAllowed).toBe([404, 405, 501].includes(status))
    }
  })
})
