import { watch } from 'vue'
import { authSession } from '@/utils/authSession'
import { APPLICATIONS, newApplicationRequestKey } from '@/config/applications'

export const APPLICATION_RESOURCE_HANDOFF = Object.freeze({
  storageKey: 'flowly.application-resource-draft.v1',
  queryKey: 'applicationDraft',
  applicationPath: '/applications',
  knowledgePath: '/knowledge',
  draftTtlMs: 2 * 60 * 60 * 1000,
  handoffTtlMs: 15 * 60 * 1000,
  maxBytes: 64 * 1024,
  messages: Object.freeze({
    identity: '登录身份尚未确认或已变化，请重新确认身份后继续。',
    storage: '无法安全暂存应用草稿，请检查浏览器存储后重试；当前填写内容仍保留。',
    invalid: '创建资源的上下文无效，未自动绑定任何资源。',
    expired: '创建资源的上下文已过期，应用草稿已恢复；请重新发起创建或选择已有知识库。',
    draftExpired: '暂存的应用草稿已到保留期限，未读取过期内容。',
    scope: '知识库与应用所属空间不一致，未自动绑定，请返回应用重新选择。',
    unavailable: '新知识库不在当前空间可绑定的资源中，请检查团队权限或重新选择。',
    navigation: '页面切换未完成；暂存草稿仍保留，可继续填写或重试。',
    team: '原团队不可用，未切换到个人空间；请返回应用重新选择空间。',
    returnLabel: '返回应用草稿',
    resumeLabel: '继续暂存的应用草稿',
    unavailableTeam: '原团队暂不可用，请重新选择',
    restoreTitle: '恢复暂存的应用草稿？',
    restoreMessage: '当前填写内容将替换为此前暂存的应用信息。',
    restoreConfirm: '恢复暂存草稿',
    keepCurrent: '继续当前填写',
    savedNotice: '正在为应用创建知识库，原应用草稿已暂存。',
    personalSpace: '个人空间',
    unnamed: '未命名应用',
    finishBeforeEditing: '请先返回应用草稿，再编辑其他知识库。',
    createdReturn: '集合已创建，正在返回应用草稿。',
    resourcesLoadFailed: '知识库资源加载失败，可重试或返回应用草稿。',
    leaveTitle: '离开知识库创建？',
    leaveMessage: '尚未创建的知识库内容会丢失；已暂存的应用草稿仍可继续。',
    leaveConfirm: '离开',
    keepCreating: '继续创建',
  }),
})
const CONFIG = APPLICATION_RESOURCE_HANDOFF
const noncePattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const scope = value => value === null || value === undefined ? '' : String(value)
export function handoffRetentionMessage() {
  return `资源创建上下文 ${CONFIG.handoffTtlMs / (60 * 1000)} 分钟有效；应用草稿保留 ${CONFIG.draftTtlMs / (60 * 60 * 1000)} 小时。`
}

// sid is stable across refreshes. Tokens and auth hashes are never persisted.
export function currentHandoffIdentity() {
  try {
    const userId = authSession.user?.id
    const token = authSession.access
    if (userId === null || userId === undefined || typeof token !== 'string' || token.length > 16384) return null
    const part = token.split('.')[1]?.replace(/-/g, '+').replace(/_/g, '/')
    if (!part) return null
    const payload = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(part), character => character.charCodeAt(0))))
    if (String(payload.user_id) !== String(userId) || !noncePattern.test(payload.sid || '')) return null
    return `${String(userId)}:${payload.sid}`
  } catch { return null }
}

function draftValue(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !['knowledge', 'workflow'].includes(value.kind)) return null
  const result = { name: value.name, description: value.description, kind: value.kind,
    tenantId: scope(value.tenantId), resourceId: scope(value.resourceId) }
  if (typeof result.name !== 'string' || result.name.length > APPLICATIONS.nameMaxLength
      || typeof result.description !== 'string' || result.description.length > APPLICATIONS.descriptionMaxLength
      || result.tenantId.length > 128 || result.resourceId.length > 128) return null
  return result
}

function remove() {
  try { sessionStorage.removeItem(CONFIG.storageKey) } catch { /* Current form stays in memory. */ }
}

function load() {
  const owner = currentHandoffIdentity()
  if (!owner) return { status: 'identity_unavailable' }
  let ledger
  try {
    const raw = sessionStorage.getItem(CONFIG.storageKey)
    if (!raw) return { status: 'missing' }
    if (new TextEncoder().encode(raw).length > CONFIG.maxBytes) throw new Error('oversized')
    ledger = JSON.parse(raw)
  } catch { return { status: 'invalid' } }
  if (ledger?.owner !== owner) { remove(); return { status: 'foreign' } }
  if (ledger?.status === 'draft_expired' && Number.isFinite(ledger.expiredAt)) {
    if (Date.now() - ledger.expiredAt <= CONFIG.handoffTtlMs) return { status: 'draft_expired' }
    remove(); return { status: 'missing' }
  }
  const draft = ledger?.draft
  if (ledger.version !== 1 || !draft || !noncePattern.test(draft.id || '') || !draftValue(draft.form)
      || !Number.isFinite(draft.createdAt) || draft.expiresAt - draft.createdAt !== CONFIG.draftTtlMs
      || !ledger.handoffs || typeof ledger.handoffs !== 'object' || Array.isArray(ledger.handoffs)) return { status: 'invalid' }
  if (Date.now() < draft.createdAt || Date.now() >= draft.expiresAt) {
    try { sessionStorage.setItem(CONFIG.storageKey, JSON.stringify({ version: 1, owner, status: 'draft_expired', expiredAt: Date.now() })) }
    catch { remove() }
    return { status: 'draft_expired' }
  }
  return { status: 'available', ledger }
}

function persist(ledger) {
  if (!ledger || ledger.owner !== currentHandoffIdentity()) throw new Error(CONFIG.messages.identity)
  try {
    const value = JSON.stringify(ledger)
    if (new TextEncoder().encode(value).length > CONFIG.maxBytes) throw new Error('oversized')
    sessionStorage.setItem(CONFIG.storageKey, value)
  } catch { throw new Error(CONFIG.messages.storage) }
}

function read(nonce) {
  const loaded = load()
  if (loaded.status !== 'available') return loaded
  const { ledger } = loaded
  const draft = { ...ledger.draft.form }
  if (!nonce) return { status: 'draft', draft, draftId: ledger.draft.id,
    nonce: Object.keys(ledger.handoffs).at(-1) || null }
  if (typeof nonce !== 'string' || !noncePattern.test(nonce)) return { status: 'invalid' }
  const handoff = ledger.handoffs[nonce]
  if (!handoff || handoff.draftId !== ledger.draft.id || handoff.kind !== 'knowledge'
      || handoff.tenantId !== draft.tenantId || draft.kind !== 'knowledge'
      || !['creating', 'completed', 'cancelled'].includes(handoff.status)
      || !Number.isFinite(handoff.createdAt) || handoff.expiresAt - handoff.createdAt !== CONFIG.handoffTtlMs) return { status: 'invalid' }
  if (Date.now() < handoff.createdAt || Date.now() >= handoff.expiresAt) return { status: 'handoff_expired', draft, draftId: ledger.draft.id, nonce }
  const resource = handoff.status === 'completed' ? handoff.resource : null
  if (resource && (typeof resource.id !== 'string' || !resource.id || resource.tenantId !== draft.tenantId)) return { status: 'invalid' }
  return { status: handoff.status, draft, draftId: ledger.draft.id, nonce, resource }
}

export const applicationResourceHandoff = Object.freeze({
  read,
  begin(form, draftId = null) {
    const value = draftValue(form)
    const owner = currentHandoffIdentity()
    if (!owner) throw new Error(CONFIG.messages.identity)
    if (!value || value.kind !== 'knowledge') throw new Error(CONFIG.messages.invalid)
    const loaded = load()
    const old = loaded.status === 'available' ? loaded.ledger : null
    const now = Date.now()
    const id = old?.draft.id === draftId ? draftId : newApplicationRequestKey()
    const nonce = newApplicationRequestKey()
    const ledger = { version: 1, owner, draft: { id, form: value, createdAt: now, expiresAt: now + CONFIG.draftTtlMs },
      handoffs: { [nonce]: { draftId: id, kind: value.kind, tenantId: value.tenantId, status: 'creating',
        createdAt: now, expiresAt: now + CONFIG.handoffTtlMs } } }
    persist(ledger)
    return { ...read(nonce), location: { path: CONFIG.knowledgePath, query: { [CONFIG.queryKey]: nonce } } }
  },
  save(draftId, form) {
    const loaded = load()
    const value = draftValue(form)
    if (loaded.status !== 'available' || loaded.ledger.draft.id !== draftId || !value) return false
    const { ledger } = loaded
    if (ledger.draft.form.kind !== value.kind || ledger.draft.form.tenantId !== value.tenantId) ledger.handoffs = {}
    ledger.draft.form = value
    persist(ledger)
    return true
  },
  complete(nonce, resource) {
    const context = read(nonce)
    if (!['creating', 'completed'].includes(context.status)) throw new Error(context.status === 'handoff_expired' ? CONFIG.messages.expired : CONFIG.messages.invalid)
    const id = scope(resource?.id)
    if (!id || id.length > 128 || scope(resource?.tenant) !== context.draft.tenantId) throw new Error(CONFIG.messages.scope)
    if (context.resource && context.resource.id !== id) throw new Error(CONFIG.messages.invalid)
    const { ledger } = load()
    ledger.handoffs[nonce].status = 'completed'
    ledger.handoffs[nonce].resource = { id, tenantId: scope(resource.tenant) }
    persist(ledger)
    return read(nonce)
  },
  cancel(nonce) {
    const context = read(nonce)
    if (context.status === 'creating') {
      const { ledger } = load()
      ledger.handoffs[nonce].status = 'cancelled'
      persist(ledger)
    }
    return read(nonce)
  },
  discard(draftId) {
    const loaded = load()
    if (loaded.status === 'available' && loaded.ledger.draft.id === draftId) remove()
  },
  returnLocation(nonce) {
    return { path: CONFIG.applicationPath, query: { create: '1', ...(noncePattern.test(nonce || '') ? { [CONFIG.queryKey]: nonce } : {}) } }
  },
})

watch(() => [currentHandoffIdentity(), Boolean(authSession.access)], ([next, authenticated], [previous] = []) => {
  if (!authenticated || previous && next !== previous) remove()
}, { flush: 'sync', immediate: true })
