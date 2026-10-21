import { afterEach, describe, expect, it, vi } from 'vitest'
import { normalizeAccountAvatar, persistAccountAvatar, readAccountAvatar, resolveAccountAvatarColors } from '@/utils/accountAvatar'
import { ACCOUNT_AVATAR } from '@/config/accountAvatar'
import { COLORS, SHAPES } from '@/vendor/bloub/skins'
import { EXPRESSIONS } from '@/vendor/bloub/expressions'

afterEach(() => vi.restoreAllMocks())

describe('animated account avatars', () => {
  it.each([undefined, null, [], 'image', {}])('defaults to the live robot without making an image selection: %j', value => {
    expect(normalizeAccountAvatar(value)).toEqual(ACCOUNT_AVATAR.defaults)
  })
  it('preserves explicit image choice and all supported customizations', () => {
    for (const shape of SHAPES) for (const color of COLORS) for (const expression of EXPRESSIONS) {
      const selected = { mode: 'image', shape: shape.id, color: color.id, expression: expression.id, blocks: [] }
      expect(normalizeAccountAvatar(selected)).toEqual(selected)
    }
  })
  it('retains valid animation blocks and discards unsafe or unbounded timing', () => {
    const blocks = [{ state: 'thinking', duration: 2.7 }, { state: 'idle', duration: 2.4 }]
    expect(normalizeAccountAvatar({ blocks }).blocks).toEqual(blocks)
    for (const block of [null, { state: 'bad', duration: 1 }, { state: 'idle', duration: Infinity },
      { state: 'idle', duration: NaN }, { state: 'idle', duration: -1 }, { state: 'idle', duration: 11 }]) {
      expect(normalizeAccountAvatar({ blocks: [block] }).blocks).toEqual([])
    }
    expect(normalizeAccountAvatar({ blocks: Array(ACCOUNT_AVATAR.maxBlocks + 1).fill(blocks[0]) }).blocks).toHaveLength(ACCOUNT_AVATAR.maxBlocks)
  })
  it.each(['encre', 'creme'])('keeps monochrome bodies and eyes visible in every theme: %s', color => {
    for (const theme of ['dark', 'high-contrast']) {
      expect(resolveAccountAvatarColors(color, theme)).toEqual({ body: ACCOUNT_AVATAR.lightBody, eyes: ACCOUNT_AVATAR.darkBody })
    }
    for (const theme of ['light', 'pure-bw']) {
      expect(resolveAccountAvatarColors(color, theme)).toEqual({ body: ACCOUNT_AVATAR.darkBody, eyes: ACCOUNT_AVATAR.lightBody })
    }
  })
  it('keeps white eyes on every colored body through all theme changes', () => {
    for (const color of COLORS.filter(color => !ACCOUNT_AVATAR.monochromeColors.includes(color.id))) {
      for (const theme of ['dark', 'light', 'pure-bw', 'high-contrast']) {
        expect(resolveAccountAvatarColors(color.id, theme)).toEqual({ body: color.hex, eyes: ACCOUNT_AVATAR.lightBody })
      }
    }
  })
  it('uses an image only after the user selects it, with isolated browser persistence', () => {
    const user = { id: 990001, avatar: 'https://example.test/image.png' }
    expect(readAccountAvatar(user).mode).toBe('robot')
    expect(persistAccountAvatar(user.id, { mode: 'image', shape: 'nuage' })).toBe(true)
    expect(readAccountAvatar(user).mode).toBe('image')
    expect(readAccountAvatar({ id: 990002 }).mode).toBe('robot')
    expect(readAccountAvatar({ ...user, avatarPreferences: { mode: 'robot', color: 'encre' } }).mode).toBe('robot')
  })
  it('recovers corrupt storage and reports a persistence failure without losing the current choice', () => {
    localStorage.setItem(`${ACCOUNT_AVATAR.storagePrefix}990003`, 'broken')
    expect(readAccountAvatar({ id: 990003 })).toEqual(ACCOUNT_AVATAR.defaults)
    vi.spyOn(localStorage, 'setItem').mockImplementation(() => { throw new Error('quota') })
    expect(persistAccountAvatar(990004, { mode: 'robot', color: 'encre' })).toBe(false)
    expect(readAccountAvatar({ id: 990004 }).color).toBe('encre')
  })
})
