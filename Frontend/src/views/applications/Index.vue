<template>
  <PageShell
    width="wide"
    class="applications-page"
  >
    <PageHeader
      title="应用中心"
      subtitle="从草稿到发布，让知识与工作流成为可调用的应用。"
    >
      <template #actions>
        <button
          v-if="storedDraft && !createOpen"
          type="button"
          class="delivery-button"
          @click="restoreCreation(null)"
        >
          {{ HANDOFF.messages.resumeLabel }}
        </button>
        <button
          type="button"
          class="delivery-button delivery-button--primary"
          data-testid="application-create"
          :disabled="creating"
          @click="showCreate"
        >
          <Plus />
          创建应用
        </button>
      </template>
    </PageHeader>
    <form
      v-if="createOpen"
      class="delivery-form"
      aria-label="创建应用"
      @submit.prevent="createApplication"
    >
      <div class="delivery-create-heading">
        <div>
          <span class="delivery-eyebrow">
            NEW APPLICATION
          </span>
          <h2>
            创建应用草稿
          </h2>
          <p>
            绑定已有资源，测试通过后再发布 API。
          </p>
        </div>
        <button
          type="button"
          class="delivery-button"
          :disabled="creating"
          @click="closeCreate"
        >
          收起
        </button>
      </div>
      <div class="delivery-form-grid">
        <div class="delivery-field">
          <label for="new-application-name">
            应用名称
          </label>
          <input
            id="new-application-name"
            v-model="form.name"
            data-testid="application-name"
            aria-label="应用名称"
            :maxlength="APPLICATIONS.nameMaxLength"
            :disabled="creating"
            required
            autocomplete="off"
            placeholder="例如：客户支持助手"
          >
        </div>
        <div class="delivery-field">
          <label for="new-application-kind">
            应用类型
          </label>
          <select
            id="new-application-kind"
            v-model="form.kind"
            data-testid="application-kind"
            aria-label="应用类型"
            :disabled="creating"
            @change="changeDraftScope"
          >
            <option
              v-for="kind in APPLICATIONS.kinds"
              :key="kind.value"
              :value="kind.value"
            >
              {{ kind.label }}
            </option>
          </select>
          <p class="delivery-hint">
            {{ APPLICATIONS.kinds.find(item => item.value === form.kind)?.description }}
          </p>
        </div>
        <div class="delivery-field">
          <label for="new-application-tenant">
            所属空间
          </label>
          <select
            id="new-application-tenant"
            v-model="form.tenantId"
            aria-label="所属空间"
            :disabled="creating || tenantsLoading"
            @change="changeDraftScope"
          >
            <option value="">
              个人空间
            </option>
            <option
              v-if="tenantUnavailable"
              :value="form.tenantId"
              disabled
            >
              {{ HANDOFF.messages.unavailableTeam }}
            </option>
            <option
              v-for="tenant in tenants"
              :key="tenant.id"
              :value="tenant.id"
            >
              {{ tenant.name }}
            </option>
          </select>
          <p
            v-if="tenantError"
            role="alert"
            class="delivery-field-error"
          >
            {{ tenantError }}
            <button
              type="button"
              class="delivery-link"
              @click="loadTenants"
            >
              重新加载团队
            </button>
          </p>
          <p
            v-else
            class="delivery-hint"
          >
            创建后类型与空间保持固定；团队权限由后台实时检查。
          </p>
        </div>
        <ApplicationResourceField
          v-model="form.resourceId"
          :kind="form.kind"
          :tenant-id="form.tenantId"
          :disabled="creating"
          contextual-create
          @create-resource="createKnowledgeResource"
          @resources-loaded="resolveReturnedResource"
        />
        <div class="delivery-field delivery-field--full">
          <label for="new-application-description">
            用途说明
          </label>
          <textarea
            id="new-application-description"
            v-model="form.description"
            aria-label="用途说明"
            :maxlength="APPLICATIONS.descriptionMaxLength"
            :disabled="creating"
            rows="2"
            placeholder="说明它为谁解决什么问题（选填）"
          />
        </div>
      </div>
      <p
        v-if="createError"
        role="alert"
        class="delivery-field-error"
      >
        {{ createError }}
        <button
          v-if="storedDraft"
          type="button"
          class="delivery-link"
          @click="restoreCreation(null)"
        >
          {{ HANDOFF.messages.resumeLabel }}
        </button>
      </p>
      <div class="delivery-actions">
        <button
          data-testid="application-submit"
          type="submit"
          class="delivery-button delivery-button--primary"
          :disabled="creating"
        >
          {{ creating ? '正在创建…' : '创建草稿' }}
          <ArrowRight />
        </button>
        <button
          type="button"
          class="delivery-button"
          :disabled="creating"
          @click="closeCreate"
        >
          取消创建
        </button>
      </div>
    </form>
    <form
      class="delivery-toolbar"
      aria-label="筛选应用"
      @submit.prevent="applySearch"
    >
      <div class="delivery-search">
        <input
          v-model="searchText"
          aria-label="搜索应用"
          type="search"
          placeholder="搜索应用名称或用途"
        >
        <button
          type="submit"
          class="delivery-button"
        >
          <Search />
          搜索
        </button>
      </div>
      <select
        v-model="kindFilter"
        aria-label="按应用类型筛选"
        @change="load(1)"
      >
        <option value="">
          全部类型
        </option>
        <option
          v-for="kind in APPLICATIONS.kinds"
          :key="kind.value"
          :value="kind.value"
        >
          {{ kind.label }}
        </option>
      </select>
      <select
        v-model="statusFilter"
        aria-label="按应用状态筛选"
        @change="load(1)"
      >
        <option value="">
          全部状态
        </option>
        <option
          v-for="(label, status) in APPLICATIONS.statuses"
          :key="status"
          :value="status"
        >
          {{ label }}
        </option>
      </select>
      <button
        type="button"
        class="delivery-button"
        :disabled="loading"
        aria-label="刷新应用列表"
        @click="load(page)"
      >
        <RefreshCw />
        刷新
      </button>
    </form>
    <div
      v-if="error"
      class="delivery-feedback delivery-feedback--error"
      role="alert"
    >
      {{ error }}
      <button
        type="button"
        class="delivery-button"
        @click="load(page)"
      >
        重新加载
      </button>
    </div>
    <div
      v-else-if="loading"
      class="delivery-loading"
      role="status"
      aria-live="polite"
    >
      正在加载应用…
    </div>
    <section
      v-else-if="!applications.length"
      class="delivery-empty"
    >
      <Boxes
        :size="32"
        aria-hidden="true"
      />
      <h2>
        {{ hasFilters ? '没有匹配的应用' : '还没有应用' }}
      </h2>
      <p>
        {{ hasFilters ? '调整关键词、类型或状态，查看其他应用。' : '选择知识助手或自动化，绑定资源后运行一次测试，再发布给你的服务调用。' }}
      </p>
      <button
        v-if="hasFilters"
        type="button"
        class="delivery-button"
        @click="clearFilters"
      >
        清除筛选
      </button>
      <button
        v-else
        type="button"
        class="delivery-button delivery-button--primary"
        @click="showCreate"
      >
        创建第一个应用
        <ArrowRight />
      </button>
    </section>
    <template v-else>
      <div class="delivery-table-wrap">
        <table class="delivery-table">
          <thead>
            <tr>
              <th scope="col">
                应用
              </th>
              <th scope="col">
                类型
              </th>
              <th scope="col">
                状态
              </th>
              <th scope="col">
                线上版本
              </th>
              <th scope="col">
                最近更新
              </th>
              <th scope="col">
                <span class="sr-only">
                  操作
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="application in applications"
              :key="application.id"
            >
              <td>
                <router-link
                  class="delivery-application-name"
                  :to="`/applications/${application.id}`"
                >
                  {{ application.name }}
                </router-link>
                <small>
                  {{ application.description || '尚未填写用途说明' }}
                </small>
              </td>
              <td>
                {{ applicationKindLabel(application.kind) }}
              </td>
              <td>
                <span
                  class="delivery-state"
                  :data-status="applicationStatus(application)"
                >
                  {{ applicationStatusLabel(application) }}
                </span>
                <small v-if="application.activeRelease && application.activeRelease.fingerprint !== application.draftFingerprint">
                  草稿有新改动
                </small>
              </td>
              <td class="delivery-mono">
                {{ application.activeRelease ? `v${application.activeRelease.version}` : '尚未发布' }}
              </td>
              <td>
                {{ applicationDate(application.updatedAt) }}
              </td>
              <td>
                <router-link
                  class="delivery-button"
                  :to="`/applications/${application.id}`"
                  :aria-label="`打开${application.name}`"
                >
                  打开
                  <ArrowUpRight />
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav
        class="delivery-pagination"
        aria-label="应用分页"
      >
        <span>
          共
          {{ count }}
          个应用 · 第
          {{ page }}
          /
          {{ pageCount }}
          页
        </span>
        <button
          type="button"
          class="delivery-button"
          :disabled="page <= 1 || loading"
          @click="load(page - 1)"
        >
          上一页
        </button>
        <button
          type="button"
          class="delivery-button"
          :disabled="page >= pageCount || loading"
          @click="load(page + 1)"
        >
          下一页
        </button>
      </nav>
    </template>
  </PageShell>
</template>

<script setup>
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch
} from 'vue'
import {
  onBeforeRouteLeave,
  isNavigationFailure,
  useRoute,
  useRouter
} from 'vue-router'
import {
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Plus,
  RefreshCw,
  Search
} from 'lucide-vue-next'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import ApplicationResourceField from './ApplicationResourceField.vue'
import {
  applicationsApi
} from '@/api/applications'
import {
  APPLICATIONS,
  applicationDate,
  applicationKindLabel,
  applicationStatus,
  applicationStatusLabel,
  emptyApplicationDraft
} from '@/config/applications'
import {
  useAppStore
} from '@/stores/app'
import './applications.css'
import { APPLICATION_RESOURCE_HANDOFF as HANDOFF, applicationResourceHandoff as handoff, currentHandoffIdentity } from '@/utils/applicationResourceHandoff'

const route = useRoute()
const router = useRouter()
const app = useAppStore()
const applications = ref([])
const loading = ref(false)
const error = ref('')
const page = ref(1)
const count = ref(0)
const pageCount = computed(() => Math.max(1, Math.ceil(count.value / APPLICATIONS.pageSize)))
const searchText = ref('')
const search = ref('')
const kindFilter = ref('')
const statusFilter = ref('')
const hasFilters = computed(() => Boolean(search.value || kindFilter.value || statusFilter.value))
const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const form = reactive({
  name: '',
  description: '',
  kind: 'knowledge',
  tenantId: '',
  resourceId: ''
})
const formDirty = computed(() => Boolean(form.name || form.description || form.resourceId || form.tenantId || form.kind !== 'knowledge'))
const tenants = ref([])
const tenantsLoading = ref(false)
const tenantError = ref('')
const tenantUnavailable = computed(() => Boolean(form.tenantId && !tenantsLoading.value && !tenants.value.some(item => String(item.id) === String(form.tenantId))))
const identity = computed(currentHandoffIdentity)
const storedDraft = ref(null)
const currentDraftId = ref(null)
const pendingResource = ref(null)
let handoffLeaveTarget = null
let listRevision = 0
let tenantRevision = 0
let disposed = false
let created = false

async function load(nextPage = 1) {
  const revision = ++listRevision
  loading.value = true
  error.value = ''
  page.value = nextPage
  try {
    const result = await applicationsApi.list({
      page: nextPage,
      page_size: APPLICATIONS.pageSize,
      search: search.value || undefined,
      kind: kindFilter.value || undefined,
      status: statusFilter.value || undefined
    })
    if (revision !== listRevision || disposed) return
    applications.value = result.results || result || []
    count.value = result.count ?? applications.value.length
  } catch (failure) {
    if (revision === listRevision && !disposed) error.value = failure.message || '应用加载失败，请重试。'
  } finally {
    if (revision === listRevision && !disposed) loading.value = false
  }
}

function applySearch() {
  search.value = searchText.value.trim();
  load(1)
}

function clearFilters() {
  searchText.value = '';
  search.value = '';
  kindFilter.value = '';
  statusFilter.value = '';
  load(1)
}
async function loadTenants() {
  const revision = ++tenantRevision
  tenantsLoading.value = true
  tenantError.value = ''
  try {
    let result
    let nextPage = 1
    const rows = []
    do {
      result = await applicationsApi.tenants({
        page: nextPage,
        page_size: APPLICATIONS.pageSize
      })
      if (revision !== tenantRevision || disposed) return
      rows.push(...(result.results || result || []))
      nextPage++
    } while (result.next)
    tenants.value = rows
  } catch (failure) {
    if (revision === tenantRevision && !disposed) tenantError.value = failure.message || '团队列表加载失败，仍可在个人空间创建。'
  } finally {
    if (revision === tenantRevision && !disposed) tenantsLoading.value = false
  }
}

function showCreate() {
  if (!createOpen.value && handoff.read().status === 'draft') {
    restoreCreation(null)
    return
  }
  createOpen.value = true;
  createError.value = '';
  if (!tenants.value.length) loadTenants()
}
function changeDraftScope() {
  form.resourceId = ''
  pendingResource.value = null
  createError.value = ''
}
async function allowLeave(to) {
  if (handoffLeaveTarget && to?.fullPath === handoffLeaveTarget) {
    handoffLeaveTarget = null
    return true
  }
  if (created) return true
  if (creating.value) return false
  if (!createOpen.value || !formDirty.value) return true
  return app.confirm({
    title: '放弃未创建的应用？',
    message: '填写的应用信息尚未保存。',
    confirmText: '放弃并离开',
    cancelText: '继续填写',
    confirmType: 'warning'
  })
}
async function closeCreate() {
  if (!await allowLeave()) return
  if (currentDraftId.value) handoff.discard(currentDraftId.value)
  currentDraftId.value = null
  pendingResource.value = null
  storedDraft.value = null
  Object.assign(form, {
    name: '',
    description: '',
    kind: 'knowledge',
    tenantId: '',
    resourceId: ''
  })
  createOpen.value = false
  const query = {
    ...route.query
  };
  delete query.create
  delete query[HANDOFF.queryKey]
  await router.replace({
    query
  })
}
async function createApplication() {
  if (creating.value) return
  const actor = identity.value
  createError.value = ''
  if (tenantUnavailable.value) { createError.value = HANDOFF.messages.team; return }
  if (!form.name.trim()) {
    createError.value = '请输入应用名称。';
    return
  }
  if (!form.resourceId) {
    createError.value = `请选择${form.kind === 'knowledge' ? '知识库' : '工作流'}。`;
    return
  }
  creating.value = true
  try {
    const draft = emptyApplicationDraft(form.kind)
    draft[form.kind === 'knowledge' ? 'collection_id' : 'workflow_id'] = form.resourceId
    const result = await applicationsApi.create({
      name: form.name.trim(),
      description: form.description,
      kind: form.kind,
      tenant_id: form.tenantId || null,
      draft
    })
    if (disposed || actor !== identity.value) return
    if (currentDraftId.value) handoff.discard(currentDraftId.value)
    created = true
    await router.push(`/applications/${result.id}`)
  } catch (failure) {
    if (!disposed && actor === identity.value) createError.value = failure.message || '应用创建失败，请检查资源归属并重试。'
  } finally {
    if (!disposed) creating.value = false
  }
}

async function createKnowledgeResource() {
  if (creating.value || form.kind !== 'knowledge') return
  if (tenantUnavailable.value) { createError.value = HANDOFF.messages.team; return }
  createError.value = ''
  try {
    const context = handoff.begin(form, currentDraftId.value)
    currentDraftId.value = context.draftId
    storedDraft.value = handoff.read()
    handoffLeaveTarget = router.resolve(context.location).fullPath
    const failure = await router.push(context.location)
    if (isNavigationFailure(failure)) createError.value = HANDOFF.messages.navigation
  } catch (failure) { createError.value = failure.message || HANDOFF.messages.storage }
  finally { handoffLeaveTarget = null }
}

async function restoreCreation(nonce) {
  const actor = identity.value
  const context = handoff.read(nonce)
  const allowed = ['draft', 'creating', 'completed', 'cancelled', 'handoff_expired']
  if (!allowed.includes(context.status)) {
    createOpen.value = true
    createError.value = context.status === 'draft_expired' ? HANDOFF.messages.draftExpired : HANDOFF.messages.invalid
    const saved = handoff.read()
    storedDraft.value = saved.status === 'draft' ? saved : null
    return
  }
  if (createOpen.value && formDirty.value && currentDraftId.value !== context.draftId) {
    const confirmed = await app.confirm({ title: HANDOFF.messages.restoreTitle, message: HANDOFF.messages.restoreMessage, confirmText: HANDOFF.messages.restoreConfirm, cancelText: HANDOFF.messages.keepCurrent })
    if (!confirmed || actor !== identity.value || disposed) return
  }
  if (actor !== identity.value || disposed) return
  if (currentDraftId.value !== context.draftId) Object.assign(form, context.draft)
  currentDraftId.value = context.draftId
  createOpen.value = true
  createError.value = context.status === 'handoff_expired' ? HANDOFF.messages.expired : ''
  storedDraft.value = handoff.read()
  pendingResource.value = context.resource ? { ...context.resource, kind: context.draft.kind, identity: actor, draftId: context.draftId } : null
  loadTenants()
}

function resolveReturnedResource(result) {
  const pending = pendingResource.value
  if (!pending || pending.identity !== identity.value || pending.draftId !== currentDraftId.value
      || pending.kind !== form.kind || pending.tenantId !== String(form.tenantId || '')
      || result.kind !== form.kind || String(result.tenantId || '') !== String(form.tenantId || '')) return
  if (result.resources.some(resource => String(resource.id) === pending.id)) form.resourceId = pending.id
  else createError.value = HANDOFF.messages.unavailable
  pendingResource.value = null
}

function beforeUnload(event) {
  if ((createOpen.value && formDirty.value) || creating.value) {
    event.preventDefault();
    event.returnValue = ''
  }
}
watch(() => [route.query.create, route.query[HANDOFF.queryKey]], ([create, nonce]) => {
  if (nonce) restoreCreation(nonce)
  else if (create === '1') showCreate()
}, {
  immediate: true
})
watch(form, () => {
  if (!currentDraftId.value || !createOpen.value) return
  try { handoff.save(currentDraftId.value, form); storedDraft.value = handoff.read() }
  catch (failure) { createError.value = failure.message }
}, { flush: 'post' })
watch(identity, (next, previous) => {
  if (!previous || next === previous) return
  currentDraftId.value = null; pendingResource.value = null; storedDraft.value = null
  Object.assign(form, { name: '', description: '', kind: 'knowledge', tenantId: '', resourceId: '' })
  createOpen.value = false; createError.value = HANDOFF.messages.identity
  listRevision++; tenantRevision++; applications.value = []; tenants.value = []
  if (next) load()
}, { flush: 'sync' })
onBeforeRouteLeave(allowLeave)
onMounted(() => {
  load();
  const saved = handoff.read()
  storedDraft.value = saved.status === 'draft' ? saved : null
  window.addEventListener('beforeunload', beforeUnload)
})
onBeforeUnmount(() => {
  disposed = true;
  listRevision++;
  tenantRevision++;
  window.removeEventListener('beforeunload', beforeUnload)
})
</script>

