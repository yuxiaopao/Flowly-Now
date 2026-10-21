import { describe, expect, it } from 'vitest'
import { getAssistantAvatarState, resolveBotState } from '../../../Frontend/src/utils/botAvatar'
import { BotEngine } from '../../../Frontend/src/vendor/bloub/engine'
import { POSES, STATES } from '../../../Frontend/src/vendor/bloub/states'

describe('assistant avatar feedback', () => {
  it('reflects errors, pending requests, streaming stages and completed workflows', () => {
    expect(getAssistantAvatarState({ error: true, isStreaming: true })).toBe('error')
    expect(getAssistantAvatarState({ metadata: { error: true } })).toBe('error')
    expect(getAssistantAvatarState({ loading: true })).toBe('thinking')
    expect(getAssistantAvatarState({ isStreaming: true }, 'thinking')).toBe('thinking')
    expect(getAssistantAvatarState({ isStreaming: true }, 'generating')).toBe('generating')
    expect(getAssistantAvatarState({ isStreaming: true })).toBe('replying')
    expect(getAssistantAvatarState({ workflow: { name: 'Example' } })).toBe('success')
    expect(getAssistantAvatarState(null)).toBe('idle')
  })

  it('maps application feedback and falls back safely for unsupported input', () => {
    expect(resolveBotState('generating')).toBe('orbit')
    expect(resolveBotState('success')).toBe('wink')
    expect(resolveBotState('error')).toBe('alert')
    expect(resolveBotState('offline')).toBe('sleep')
    expect(resolveBotState('burst')).toBe('burst')
    expect(resolveBotState('invalid')).toBe('idle')
    expect(resolveBotState(undefined)).toBe('idle')
  })
})

describe('vendored Bloub animation regression', () => {
  for (const state of STATES) {
    it(`renders ${state.id} deterministically at rest and throughout the animation`, () => {
      const engine = new BotEngine(undefined, state.id)
      for (const time of [0, POSES[state.id], state.duration, state.duration * 2]) {
        const frame = engine.sample(time)
        expect(frame.bodyPath).toMatch(/^M/)
        expect(JSON.stringify(frame)).not.toMatch(/NaN|Infinity|null(?=\s*,\s*null)/)
        expect(new BotEngine(undefined, state.id).sample(time)).toEqual(frame)
      }
    })
  }

  it('keeps geometry finite through rapid state changes and rejects invalid gaze coordinates', () => {
    const engine = new BotEngine()
    STATES.forEach((state, index) => {
      const time = index / 10
      engine.setState(state.id, time)
      engine.setLook({ yaw: NaN, pitch: 0, mix: 1, spin: 0, wander: 0 }, time)
      const frame = engine.sample(time + 0.05)
      expect(JSON.stringify(frame)).not.toMatch(/NaN|Infinity/)
      expect(frame.bodyAlpha).toBeGreaterThanOrEqual(0)
      expect(frame.bodyAlpha).toBeLessThanOrEqual(1)
    })
  })
})
