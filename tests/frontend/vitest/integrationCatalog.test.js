import { describe, it, expect } from 'vitest'
import { connectionState, filterCatalog, connectionForm, connectionPayload, validateConnectionForm } from '@/utils/integrationCatalog'

const service = { id: 'slack', name: 'Slack', category: 'communication', description: '频道通知', fields: [{ key: 'webhook_url', secret: true, required: true, label: 'Webhook 地址' }, { key: 'keyword', secret: false, required: false }] }
const saved = { id: 7, name: '团队通知', integrationType: 'slack', configuredFields: ['webhook_url'], config: { keyword: '消息', events: ['execution.failed'] } }

describe('integration connection behavior', () => {
  it('never treats a legacy connected flag as verified', () => {
    expect(connectionState()).toBe('unconfigured')
    expect(connectionState({ isConnected: true })).toBe('untested')
    expect(connectionState({ isConnected: true, verificationStatus: 'success', lastCheckedAt: '2026-10-19' })).toBe('success')
    expect(connectionState({ isConnected: true, isActive: false, verificationStatus: 'success', lastCheckedAt: '2026-10-19' })).toBe('disconnected')
  })
  it('preserves an existing secret when the edit field is blank', () => {
    const form = connectionForm(service, saved)
    expect(form.fields.webhook_url).toBe('')
    expect(validateConnectionForm(service, form, saved)).toEqual({})
    expect(connectionPayload(service, form, saved).credentials).toEqual({})
    form.fields.webhook_url = 'https://hooks.slack.com/new'
    expect(connectionPayload(service, form, saved).credentials.webhook_url).toBe('https://hooks.slack.com/new')
  })
  it('requires credentials for new connections and does not mutate saved events', () => {
    const form = connectionForm(service)
    expect(validateConnectionForm(service, form).webhook_url).toBeTruthy()
    const edit = connectionForm(service, saved)
    edit.events.push('execution.completed')
    expect(saved.config.events).toEqual(['execution.failed'])
  })
  it('filters combined search, category and actual verification state', () => {
    expect(filterCatalog([service], [saved], { query: 'SLACK', category: 'communication', status: 'untested' })).toEqual([service])
    expect(filterCatalog([service], [saved], { status: 'success' })).toEqual([])
    expect(filterCatalog([service], [], { query: '频道', status: 'unconfigured' })).toEqual([service])
  })
})
