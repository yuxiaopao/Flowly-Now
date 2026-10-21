import { describe, expect, it } from 'vitest'
import { AVATAR_STUDIO } from '@/config/avatarStudio'
import { getAvatarStudioUrl, isAvatarStudioMessage, makeAvatarStudioMessage } from '@/utils/avatarStudio'
import { resolvePersonalCenterActiveKey } from '@/config/userNavigation'
import { routes } from '@/router/routes'

// Route metadata can be inspected without initializing the auth/API/router cycle.
vi.mock('@/stores/auth', () => ({ useAuthStore: vi.fn() }))


describe('personal center avatar integration', () => {
  it('opens the authenticated avatar route and isolates its account query', () => {
    expect(resolvePersonalCenterActiveKey(AVATAR_STUDIO.route)).toBe('avatar')
    const settings = routes.find(route => route.path === '/settings')
    expect(settings.meta.requiresAuth).toBe(true)
    expect(settings.children.find(route => route.path === 'avatar')?.name).toBe('SettingsAvatar')
    expect(getAvatarStudioUrl('1036', '/')).toBe('/avatar-studio/index.html?account=1036&embedded=1')
    expect(getAvatarStudioUrl('a&account=b', './')).toBe('./avatar-studio/index.html?account=a%26account%3Db&embedded=1')
  })

  it('accepts only the expected frame, origin and protocol', () => {
    const frame = {}
    const origin = 'https://flowly.test'
    const message = { source: frame, origin, data: makeAvatarStudioMessage(AVATAR_STUDIO.response, 'request-one') }
    expect(isAvatarStudioMessage(message, frame, origin)).toBe(true)
    expect(isAvatarStudioMessage({ ...message, source: {} }, frame, origin)).toBe(false)
    expect(isAvatarStudioMessage({ ...message, origin: 'https://other.test' }, frame, origin)).toBe(false)
    expect(isAvatarStudioMessage({ ...message, data: { ...message.data, version: 999 } }, frame, origin)).toBe(false)
    expect(isAvatarStudioMessage({ ...message, data: null }, frame, origin)).toBe(false)
    expect(isAvatarStudioMessage(message, null, origin)).toBe(false)
  })

})
