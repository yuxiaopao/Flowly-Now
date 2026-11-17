import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DataExport from '@/views/settings/DataExport.vue'
import api from '@/api/index'
import { useAppStore } from '@/stores/app'

let wrapper
let get
let post
let patch
const policy = { enabled: true, frequency: 'weekly', keepCount: 5, schedulerConfigured: true,
  retentionMin: 3, retentionMax: 30, lastError: '', nextRunAt: '2026-11-01T01:00:00Z' }
const backup = { id: 7, exportType: 'full', format: 'json', status: 'completed', fileName: 'backup.json',
  fileSize: 1200, createdAt: '2026-10-31T01:00:00Z', restorable: true }
beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('flowly_backup_settings', JSON.stringify({ enabled: false, keepCount: 30 }))
  get = vi.spyOn(api, 'get').mockImplementation(async url => url.endsWith('/backup_settings/') ? { ...policy } : { results: [backup] })
  patch = vi.spyOn(api, 'patch').mockResolvedValue({ ...policy })
  post = vi.spyOn(api, 'post').mockResolvedValue({})
})
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ''; vi.restoreAllMocks() })

async function openPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  wrapper = mount(DataExport, { attachTo: document.body, global: { plugins: [pinia], stubs: { PageHeader: true } } })
  await flushPromises()
  return useAppStore(pinia)
}
function button(text) {
  const found = wrapper.findAll('button').find(item => item.text() === text)
  if (!found) throw new Error(`Missing button: ${text}`)
  return found
}
function dialogButton(text) {
  const found = [...document.body.querySelectorAll('.el-dialog button')].find(item => item.textContent.trim() === text)
  if (!found) throw new Error(`Missing dialog button: ${text}`)
  return found
}

describe('personal data settings', () => {
  it('loads the server policy and explicitly saves it instead of trusting a local switch', async () => {
    await openPage()
    expect(get.mock.calls.some(([url]) => url === '/data-export/backup_settings/')).toBe(true)
    expect(wrapper.get('input[role="spinbutton"]').element.value).toBe('5')
    await button('保存备份计划').trigger('click')
    await flushPromises()
    expect(patch).toHaveBeenCalledWith('/data-export/backup_settings/', expect.objectContaining({ enabled: true, keep_count: 5 }), expect.anything())
    expect(localStorage.getItem('flowly_backup_settings')).toContain('30')
  })

  it('requires a restore preview before explicitly confirming private copies', async () => {
    post.mockImplementation(async url => url.endsWith('/restore_preview/')
      ? { summary: { workflows: 1, nodes: 2, agents: 1 }, confirmationToken: 'preview-token', notice: '原数据保留，创建私有草稿副本。' }
      : { summary: { workflows: 1, agents: 1 }, mapping: { workflows: { old: 'new' } } })
    await openPage()
    await button('恢复为副本').trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('原数据保留')
    expect(post.mock.calls.filter(([url]) => url.endsWith('/restore/'))).toHaveLength(0)
    dialogButton('确认创建副本').click()
    await flushPromises()
    expect(post).toHaveBeenCalledWith('/data-export/7/restore/', { confirm: true, confirmation_token: 'preview-token' }, expect.anything())
  })

  it('requires both the current password and exact scope confirmation before clearing', async () => {
    get.mockImplementation(async url => {
      if (url.endsWith('/backup_settings/')) return { ...policy }
      if (url.endsWith('/delete_preview/')) return { summary: { workflows: 1, agents: 1 },
        confirmationToken: 'delete-token', confirmationText: '删除个人工作流和Agent', notice: '团队、账号、凭证和账单保留。' }
      return { results: [backup] }
    })
    post.mockRejectedValueOnce(new Error('Wrong password'))
    const app = await openPage()
    await button('清理个人工作区').trigger('click')
    await flushPromises()
    expect(dialogButton('确认删除').disabled).toBe(true)
    const password = document.querySelector('input[aria-label="当前密码"]')
    password.value = 'wrong-password'
    password.dispatchEvent(new Event('input', { bubbles: true }))
    const confirmation = document.querySelector('input[aria-label="清理确认文字"]')
    confirmation.value = '删除个人工作流和Agent'
    confirmation.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()
    expect(dialogButton('确认删除').disabled).toBe(false)
    dialogButton('确认删除').click()
    await flushPromises()
    expect(post).toHaveBeenCalledWith('/data-export/delete_personal_data/', {
      password: 'wrong-password', confirmation: '删除个人工作流和Agent', confirmation_token: 'delete-token',
    }, expect.anything())
    expect(app.toasts.some(item => item.message.includes('清理失败'))).toBe(true)
    expect(document.querySelector('input[aria-label="当前密码"]')).not.toBeNull()
  })

  it('keeps scheduling disabled after a server load failure and can retry', async () => {
    get.mockImplementation(async url => {
      if (url.endsWith('/backup_settings/')) throw new Error('service unavailable')
      return { results: [backup] }
    })
    await openPage()
    expect(button('保存备份计划').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('加载服务端备份计划失败')
    get.mockImplementation(async url => url.endsWith('/backup_settings/') ? { ...policy } : { results: [backup] })
    await button('重新加载计划').trigger('click')
    await flushPromises()
    expect(button('保存备份计划').attributes('disabled')).toBeUndefined()
  })

  it('reports a committed restore truthfully when refreshing another list fails', async () => {
    post.mockImplementation(async url => url.endsWith('/restore_preview/')
      ? { summary: { workflows: 1 }, confirmationToken: 'preview-token', notice: '原数据保留。' }
      : { mapping: { workflows: { old: 'new' } } })
    get.mockImplementation(async url => {
      if (url.startsWith('/workflows/')) throw new Error('list temporarily unavailable')
      return url.endsWith('/backup_settings/') ? { ...policy } : { results: [backup] }
    })
    const app = await openPage()
    await button('恢复为副本').trigger('click')
    await flushPromises()
    dialogButton('确认创建副本').click()
    await flushPromises()
    expect(app.toasts.some(item => item.message.includes('私有草稿副本已创建'))).toBe(true)
    expect(app.toasts.some(item => item.message.includes('部分列表刷新失败'))).toBe(true)
    expect(app.toasts.some(item => item.message.includes('恢复失败'))).toBe(false)
  })
})
