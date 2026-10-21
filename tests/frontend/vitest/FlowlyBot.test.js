import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import FlowlyBot from '../../../Frontend/src/components/common/FlowlyBot.vue'
import { BotEngine } from '../../../Frontend/src/vendor/bloub/engine'

describe('FlowlyBot playback and accessibility', () => {
  let wrappers
  let frames
  let observers
  let motion
  let hidden
  let hiddenDescriptor
  let time

  beforeEach(() => {
    wrappers = []
    frames = new Map()
    observers = []
    hidden = false
    time = 0
    let nextFrameId = 0
    vi.stubGlobal('requestAnimationFrame', vi.fn(callback => {
      const id = ++nextFrameId
      frames.set(id, callback)
      return id
    }))
    vi.stubGlobal('cancelAnimationFrame', vi.fn(id => frames.delete(id)))
    vi.stubGlobal('IntersectionObserver', class {
      constructor(callback) {
        this.callback = callback
        this.observe = vi.fn()
        this.disconnect = vi.fn()
        observers.push(this)
      }
    })
    motion = { matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }
    vi.spyOn(window, 'matchMedia').mockReturnValue(motion)
    hiddenDescriptor = Object.getOwnPropertyDescriptor(document, 'hidden')
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden })
  })

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount())
    if (hiddenDescriptor) Object.defineProperty(document, 'hidden', hiddenDescriptor)
    else delete document.hidden
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  function create(props = {}) {
    const wrapper = mount(FlowlyBot, { props })
    wrappers.push(wrapper)
    return wrapper
  }

  async function advanceFrame() {
    time += 40
    const callbacks = [...frames.values()]
    frames.clear()
    callbacks.forEach(callback => callback(time))
    await nextTick()
  }

  it('keeps historical avatars static while preserving state feedback', async () => {
    const wrapper = create({ animated: false, state: 'success' })
    await nextTick()
    expect(frames.size).toBe(0)
    expect(wrapper.attributes('data-bot-state')).toBe('wink')
    expect(wrapper.attributes('aria-label')).toBe('小流 · 已完成')
    await wrapper.setProps({ state: 'error' })
    expect(wrapper.attributes('data-bot-state')).toBe('alert')
    expect(wrapper.html()).not.toMatch(/NaN|Infinity/)
    expect(frames.size).toBe(0)
  })

  it('applies a new shape to frozen geometry with contrasting eyes', async () => {
    const wrapper = create({ animated: false, shape: 'cercle', eyeColor: '#0a0a0c' })
    const before = wrapper.find('mask > path').attributes('d')
    await wrapper.setProps({ shape: 'nuage', expression: 'heureux', eyeColor: '#f9f9f9' })
    expect(wrapper.find('mask > path').attributes('d')).not.toBe(before)
    expect(wrapper.html()).toContain('#f9f9f9')
    expect(wrapper.html()).not.toMatch(/NaN|Infinity/)
    expect(frames.size).toBe(0)
  })

  it('plays saved animation blocks with the existing visibility controls', async () => {
    const wrapper = create({ blocks: [{ state: 'idle', duration: 0.1 }, { state: 'thinking', duration: 0.1 }] })
    await nextTick()
    for (let index = 0; index < 5; index++) await advanceFrame()
    expect(wrapper.attributes('data-bot-state')).toBe('thinking')
    for (let index = 0; index < 3; index++) await advanceFrame()
    expect(wrapper.attributes('data-bot-state')).toBe('idle')
    expect(wrapper.html()).not.toMatch(/NaN|Infinity/)
  })

  it('restarts repeated transient blocks instead of freezing a single-state loop', async () => {
    const reset = vi.spyOn(BotEngine.prototype, 'reset')
    const wrapper = create({ blocks: [{ state: 'wink', duration: 0.1 }] })
    await nextTick()
    const initialCount = reset.mock.calls.length
    for (let index = 0; index < 8; index++) await advanceFrame()
    expect(reset.mock.calls.length).toBeGreaterThan(initialCount)
    expect(reset.mock.calls.some(([state, time]) => state === 'wink' && time >= 0.1)).toBe(true)
    expect(wrapper.attributes('data-bot-state')).toBe('wink')
  })

  it('honors reduced motion initially and when the preference changes', async () => {
    motion.matches = true
    const wrapper = create({ state: 'generating' })
    await nextTick()
    expect(wrapper.attributes('data-bot-animated')).toBe('false')
    expect(frames.size).toBe(0)
    const change = motion.addEventListener.mock.calls.find(([event]) => event === 'change')[1]
    change({ matches: false })
    await nextTick()
    expect(wrapper.attributes('data-bot-animated')).toBe('true')
    await advanceFrame()
    await advanceFrame()
    change({ matches: true })
    await nextTick()
    expect(frames.size).toBe(0)
    expect(wrapper.attributes('data-bot-state')).toBe('orbit')
  })

  it('pauses offscreen and hidden avatars and resumes when visible', async () => {
    const wrapper = create()
    await nextTick()
    expect(frames.size).toBe(1)
    observers[0].callback([{ isIntersecting: false }])
    await nextTick()
    expect(frames.size).toBe(0)
    expect(wrapper.attributes('data-bot-animated')).toBe('false')
    observers[0].callback([{ isIntersecting: true }])
    await nextTick()
    expect(frames.size).toBe(1)
    hidden = true
    document.dispatchEvent(new Event('visibilitychange'))
    await nextTick()
    expect(frames.size).toBe(0)
    hidden = false
    document.dispatchEvent(new Event('visibilitychange'))
    await nextTick()
    await advanceFrame()
    expect(wrapper.attributes('data-bot-animated')).toBe('true')
    expect(wrapper.html()).not.toMatch(/NaN|Infinity/)
  })

  it('isolates SVG masks across instances and labels only informative avatars', async () => {
    const informative = create({ animated: false, label: '助手正在分析' })
    const decorative = create({ animated: false, decorative: true })
    expect(informative.find('mask').attributes('id')).not.toBe(decorative.find('mask').attributes('id'))
    expect(informative.attributes('role')).toBe('img')
    expect(informative.attributes('aria-label')).toBe('助手正在分析')
    expect(decorative.attributes('aria-hidden')).toBe('true')
    expect(decorative.attributes('aria-label')).toBeUndefined()
    await informative.setProps({ state: 'unsupported' })
    expect(informative.attributes('data-bot-state')).toBe('idle')
  })

  it('releases animation, observers and event listeners on unmount', async () => {
    const removeWindow = vi.spyOn(window, 'removeEventListener')
    const removeDocument = vi.spyOn(document, 'removeEventListener')
    const wrapper = create({ follow: true })
    await nextTick()
    await advanceFrame()
    wrapper.unmount()
    wrappers = []
    expect(frames.size).toBe(0)
    expect(observers[0].disconnect).toHaveBeenCalledOnce()
    expect(motion.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
    expect(removeWindow).toHaveBeenCalledWith('pointermove', expect.any(Function))
    expect(removeDocument).toHaveBeenCalledWith('pointerleave', expect.any(Function))
    expect(removeDocument).toHaveBeenCalledWith('visibilitychange', expect.any(Function))
  })
})
