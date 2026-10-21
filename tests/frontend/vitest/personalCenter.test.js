import { describe, it, expect } from 'vitest'
import { toProfileForm, normalizeProfile, getSettingsError, getSettingsFieldErrors } from '@/utils/personalCenter'
import { readPreferences } from '@/stores/preferences'
import { PERSONAL_CENTER, PROFILE_COPY } from '@/config/personalCenter'
import { PERSONAL_CENTER_NAV_ITEMS } from '@/config/userNavigation'

describe('personal center contracts', () => {
  it('restores camelCase and legacy names without losing saved data', () => {
    expect(toProfileForm({ firstName: '明', lastName: '陈', bio: '简介' })).toMatchObject({ firstName: '明', lastName: '陈', bio: '简介' })
    expect(toProfileForm({ first_name: '明', last_name: '陈' })).toMatchObject({ firstName: '明', lastName: '陈' })
    expect(toProfileForm()).toMatchObject({ firstName: '', phone: '' })
    expect(normalizeProfile({ username: ' 小流 ', bio: ' 简介 ' })).toEqual({ username: '小流', bio: '简介' })
  })
  it('keeps field errors actionable for the response envelope', () => {
    const error = { response: { data: { message: '数据验证失败', errors: { old_password: ['原密码错误'] } } } }
    expect(getSettingsFieldErrors(error)).toEqual({ oldPassword: '原密码错误' })
    expect(getSettingsError(error)).toBe('原密码错误')
    expect(getSettingsError(new Error('Network Error'))).toBe(PROFILE_COPY.profileError)
  })
  it.each(['null', '[]', 'broken', 'false'])('recovers corrupt preference storage %s', value => {
    expect(readPreferences({ getItem: () => value })).toEqual({})
  })
  it('keeps notification settings when loading editor preferences', () => {
    expect(readPreferences({ getItem: () => '{"notifyOnError":false,"snapToGrid":false}' })).toEqual({ notifyOnError: false, snapToGrid: false })
    expect(readPreferences({ getItem: () => { throw new Error('blocked') } })).toEqual({})
  })
  it('makes every existing destination available exactly once', () => {
    const keys = PERSONAL_CENTER.groups.flatMap(group => group.items)
    expect(new Set(keys).size).toBe(keys.length)
    expect([...keys].sort()).toEqual(PERSONAL_CENTER_NAV_ITEMS.map(item => item.key).sort())
  })
})
