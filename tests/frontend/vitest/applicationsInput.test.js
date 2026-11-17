import { describe, expect, it } from 'vitest'
import { APPLICATIONS, parseApplicationInput } from '@/config/applications'

describe('application JSON input validation', () => {
  it('preserves arbitrary nested field names', () => {
    expect(parseApplicationInput('{"Order_ID":{"user_data":[{"CamelCase":true}]}}')).toEqual({ Order_ID: { user_data: [{ CamelCase: true }] } })
  })
  it.each(['[]', 'null', 'true', '3', '"text"'])('rejects a non-object root: %s', value => {
    expect(() => parseApplicationInput(value)).toThrow('JSON 对象')
  })
  it('enforces the UTF-8 byte limit rather than JavaScript character count', () => {
    expect(() => parseApplicationInput(JSON.stringify({ query: '知'.repeat(Math.ceil(APPLICATIONS.maxInputBytes / 3)) }))).toThrow('100 KiB')
  })
})
