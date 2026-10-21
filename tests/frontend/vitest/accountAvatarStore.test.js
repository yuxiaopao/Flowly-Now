import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import authApi from '@/api/auth'
import { ACCOUNT_AVATAR } from '@/config/accountAvatar'

vi.mock('@/api/auth', () => ({ default: { updateProfile: vi.fn() } }))

describe('account avatar persistence feedback', () => {
  const design = { mode: 'robot', shape: 'nuage', color: 'encre', expression: 'heureux', blocks: [{ state: 'wink', duration: 1.6 }] }
  let store

  beforeEach(() => {
    vi.resetAllMocks()
    localStorage.clear()
    setActivePinia(createPinia())
    store = useAuthStore()
    store.user = { id: 990101, avatar: '/media/example.png', avatarPreferences: { ...design } }
  })

  it('preserves the robot design when explicitly choosing an uploaded image', async () => {
    authApi.updateProfile.mockResolvedValue({ avatarPreferences: { ...design, mode: 'image' } })
    const response = await store.updateProfile({ avatarPreferences: { mode: 'image' } })
    expect(authApi.updateProfile).toHaveBeenCalledWith({ avatarPreferences: { ...design, mode: 'image' } })
    expect(store.user.avatarPreferences).toEqual({ ...design, mode: 'image' })
    expect(response.avatarPreferencesSynced).toBe(true)
  })

  it('reports browser-only persistence honestly when a legacy server omits preferences', async () => {
    authApi.updateProfile.mockResolvedValue({ id: 990101, avatar: '/media/example.png' })
    const response = await store.updateProfile({ avatarPreferences: { color: 'creme' } })
    expect(response.avatarPreferencesSynced).toBe(false)
    expect(response.avatarPreferencesPersisted).toBe(true)
    expect(JSON.parse(localStorage.getItem(`${ACCOUNT_AVATAR.storagePrefix}990101`))).toEqual({ ...design, color: 'creme' })
    expect(store.user.avatar).toBe('/media/example.png')
  })

  it('keeps the active avatar unchanged when saving fails', async () => {
    authApi.updateProfile.mockRejectedValue(new Error('Network Error'))
    await expect(store.updateProfile({ avatarPreferences: { color: 'creme' } })).rejects.toThrow('Network Error')
    expect(store.user.avatarPreferences).toEqual(design)
    expect(localStorage.getItem(`${ACCOUNT_AVATAR.storagePrefix}990101`)).toBeNull()
    expect(store.isLoading).toBe(false)
  })
})
