<template>
  <div class="integrations-page">
    <PageHeader
      compact
      :title="COPY.title"
      :subtitle="COPY.subtitle"
    >
      <template #actions>
        <el-button
          :loading="store.isLoading"
          :disabled="busy"
          @click="load"
        >
          <RefreshCw
            :size="16"
            aria-hidden="true"
          />{{ COPY.refresh }}
        </el-button>
      </template>
    </PageHeader>

    <p class="catalog-note">
      <ShieldCheck
        :size="18"
        aria-hidden="true"
      />{{ COPY.availabilityNote }}
    </p>
    <PageToolbar>
      <el-input
        v-model="query"
        clearable
        :placeholder="COPY.search"
        :aria-label="COPY.search"
      >
        <template #prefix>
          <Search :size="16" />
        </template>
      </el-input>
      <el-select
        v-model="status"
        :aria-label="COPY.statusFilter"
      >
        <el-option
          value="all"
          :label="COPY.allStatuses"
        />
        <el-option
          v-for="(item, key) in STATES"
          :key="key"
          :value="key"
          :label="item.label"
        />
      </el-select>
      <template #actions>
        <span class="catalog-count">{{ store.availableIntegrations.length }} {{ COPY.count }} · {{ configuredCount }} {{ COPY.configured }} · {{ verifiedCount }} {{ COPY.verified }}</span>
      </template>
    </PageToolbar>
    <el-tabs
      v-model="category"
      class="category-tabs"
      :aria-label="COPY.category"
    >
      <el-tab-pane
        v-for="(label, key) in CATEGORIES"
        :key="key"
        :name="key"
        :label="`${label} ${categoryCount(key)}`"
      />
    </el-tabs>

    <div
      v-if="loadError"
      class="load-error"
      role="alert"
    >
      <el-alert
        :title="COPY.loadError"
        type="error"
        :closable="false"
        show-icon
      />
      <el-button @click="load">
        {{ COPY.retry }}
      </el-button>
    </div>
    <el-skeleton
      v-else-if="store.isLoading"
      :rows="8"
      animated
    />
    <el-empty
      v-else-if="!filtered.length"
      :description="COPY.empty"
    >
      <el-button @click="resetFilters">
        {{ COPY.clearFilters }}
      </el-button>
    </el-empty>
    <div
      v-else
      class="service-grid"
    >
      <article
        v-for="service in filtered"
        :key="service.id"
        class="service-card"
        :data-service="service.id"
      >
        <div class="service-heading">
          <IntegrationLogo
            :service="service.id"
            :name="service.name"
          />
          <div class="service-name">
            <h2>{{ service.name }}</h2><span>{{ CATEGORIES[service.category] }} · {{ MODES[service.mode] }}</span>
          </div>
          <el-tag
            :type="stateMeta(primary(service)).type"
            size="small"
          >
            {{ stateMeta(primary(service)).label }}
          </el-tag>
        </div>
        <p class="service-description">
          {{ service.description }}
        </p>
        <div class="service-footer">
          <span class="service-evidence">{{ primary(service)?.lastCheckedAt ? formatDate(primary(service).lastCheckedAt) : COPY.never }}</span>
          <el-button
            :type="primary(service) ? 'default' : 'primary'"
            :aria-label="`${primary(service) ? COPY.manage : COPY.configure} ${service.name}`"
            @click="open(service)"
          >
            {{ primary(service) ? COPY.manage : COPY.configure }}<ArrowUpRight
              :size="14"
              aria-hidden="true"
            />
          </el-button>
        </div>
      </article>
    </div>

    <el-drawer
      v-model="drawer"
      :title="selected?.name"
      size="min(640px, 100vw)"
      :before-close="beforeClose"
      destroy-on-close
      @closed="clearEditor"
    >
      <template v-if="selected">
        <div class="detail-heading">
          <IntegrationLogo
            :service="selected.id"
            :name="selected.name"
          /><div><h2>{{ selected.name }}</h2><p>{{ selected.description }}</p></div>
        </div>
        <div
          v-if="connections.length"
          class="connection-picker"
        >
          <el-select
            :model-value="connectionId || ''"
            :aria-label="COPY.chooseConnection"
            :placeholder="COPY.chooseConnection"
            :disabled="busy"
            @change="switchConnection"
          >
            <el-option
              v-for="item in connections"
              :key="item.id"
              :value="item.id"
              :label="`${item.name} · ${stateMeta(item).label}`"
            />
          </el-select>
          <el-button
            :disabled="busy"
            @click="switchConnection(null)"
          >
            {{ COPY.newConnection }}
          </el-button>
        </div>
        <section class="detail-section">
          <div class="section-title">
            <h3>{{ COPY.setup }}</h3><a
              :href="selected.documentationUrl"
              target="_blank"
              rel="noopener noreferrer"
            >{{ COPY.docs }}<ExternalLink :size="14" /></a>
          </div>
          <p>{{ selected.setupGuide }}</p>
          <p class="scope-note">
            {{ selected.scopeNote }}
          </p>
        </section>
        <el-form
          label-position="top"
          :disabled="busy"
          @submit.prevent="save(false)"
        >
          <el-form-item
            :label="COPY.name"
            :error="errors.name"
            for="integration-name"
            required
          >
            <el-input
              id="integration-name"
              v-model="form.name"
              :maxlength="NAME_LIMIT"
              autocomplete="off"
            />
          </el-form-item>
          <el-form-item
            v-for="field in selected.fields"
            :key="field.key"
            :label="`${field.label}${field.required ? '' : ` (${COPY.optional})`}`"
            :required="field.required"
            :error="errors[field.key]"
            :for="`integration-${field.key}`"
          >
            <el-input
              :id="`integration-${field.key}`"
              v-model="form.fields[field.key]"
              :type="field.secret ? 'password' : 'text'"
              :show-password="field.secret"
              :maxlength="FIELD_LIMIT"
              :placeholder="isSecretSaved(field) ? COPY.secretSaved : field.placeholder"
              autocomplete="off"
              :disabled="form.clearSecrets.includes(field.key)"
            />
            <el-checkbox
              v-if="field.secret && !field.required && isSecretSaved(field)"
              v-model="form.clearSecrets"
              :label="field.key"
            >
              {{ COPY.clearSecret }}
            </el-checkbox>
          </el-form-item>
          <p class="field-hint">
            <LockKeyhole :size="14" />{{ COPY.secretHelp }}
          </p>
          <el-form-item
            v-if="selected.events.length"
            :label="COPY.events"
          >
            <el-checkbox-group v-model="form.events">
              <el-checkbox
                v-for="event in selected.events"
                :key="event"
                :label="event"
              >
                {{ EVENTS[event] }}
              </el-checkbox>
            </el-checkbox-group>
            <p class="field-hint">
              {{ COPY.eventsHelp }}
            </p>
          </el-form-item>
        </el-form>
        <el-alert
          :title="selected.testNotice"
          :type="selected.mode === 'api' ? 'info' : 'warning'"
          :closable="false"
          show-icon
        />
        <div
          v-if="actionError"
          class="result-message"
          role="alert"
        >
          <el-alert
            :title="actionError"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
        <div
          v-if="result"
          class="result-message"
          role="status"
        >
          <el-alert
            :title="result.message"
            :type="result.success ? 'success' : 'error'"
            :closable="false"
            show-icon
          />
          <p class="field-hint">
            <span v-if="result.statusCode">{{ COPY.http }} {{ result.statusCode }} · </span>{{ COPY.latency }} {{ result.durationMs }} ms
          </p>
        </div>
        <section
          v-if="current"
          class="detail-section verification-section"
        >
          <div class="section-title">
            <h3>{{ COPY.evidence }}</h3><el-tag :type="stateMeta(current).type">
              {{ stateMeta(current).label }}
            </el-tag>
          </div>
          <p>{{ formatDate(current.lastCheckedAt) }}</p>
          <p
            v-if="current.lastError"
            class="error-text"
          >
            {{ current.lastError }}
          </p>
          <p class="field-hint">
            {{ dirty ? COPY.unsaved : COPY.stateHelp }}
          </p>
          <div class="connection-actions">
            <el-button
              v-if="selected.mode === 'api'"
              :disabled="busy || dirty || connectionState(current) !== 'success'"
              :loading="operation === 'sync'"
              @click="sync"
            >
              {{ selected.syncLabel }}
            </el-button>
            <el-button
              :disabled="busy || !current.isActive"
              @click="disconnect"
            >
              {{ COPY.disconnect }}
            </el-button>
            <el-button
              text
              type="danger"
              :disabled="busy"
              @click="remove"
            >
              {{ COPY.remove }}
            </el-button>
          </div>
        </section>
        <section
          v-if="current && selected.mode === 'api'"
          class="detail-section"
        >
          <h3>{{ COPY.data }}</h3>
          <template v-if="Object.keys(current.lastResult || {}).length">
            <p v-if="!current.lastResult.count">
              {{ COPY.emptyData }}
            </p>
            <ul
              v-else-if="current.lastResult.items"
              class="resource-list"
            >
              <li
                v-for="item in current.lastResult.items"
                :key="item.id"
              >
                <span>{{ item.name }}</span><code>{{ item.id }}</code>
              </li>
            </ul>
            <div
              v-else
              class="data-preview"
            >
              <table>
                <tbody>
                  <tr
                    v-for="(row, index) in current.lastResult.rows"
                    :key="index"
                  >
                    <td
                      v-for="(value, cell) in row"
                      :key="cell"
                    >
                      {{ value }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="field-hint">
              {{ COPY.limited }}
            </p>
          </template>
          <p
            v-else
            class="field-hint"
          >
            {{ COPY.noData }}
          </p>
        </section>
        <section
          v-if="current && selected.mode !== 'api'"
          class="detail-section"
        >
          <div class="section-title">
            <h3>{{ COPY.history }}</h3><el-button
              text
              :disabled="busy"
              @click="loadHistory"
            >
              {{ COPY.refresh }}
            </el-button>
          </div>
          <p
            v-if="historyError"
            role="alert"
            class="error-text"
          >
            {{ COPY.historyError }}
          </p>
          <el-skeleton
            v-else-if="historyLoading"
            :rows="3"
            animated
          />
          <p
            v-else-if="!history.length"
            class="field-hint"
          >
            {{ COPY.noHistory }}
          </p>
          <ol
            v-else
            class="delivery-list"
          >
            <li
              v-for="delivery in history"
              :key="delivery.id"
            >
              <div><strong>{{ EVENTS[delivery.event] || delivery.event }}</strong><span>{{ DELIVERY_STATES[delivery.status] }}</span></div><p>{{ delivery.message }}</p><small>{{ formatDate(delivery.createdAt) }}<template v-if="delivery.statusCode"> · HTTP {{ delivery.statusCode }}</template></small>
            </li>
          </ol>
        </section>
      </template>
      <template #footer>
        <div class="drawer-actions">
          <el-button
            :disabled="busy"
            @click="beforeClose(() => drawer = false)"
          >
            {{ COPY.close }}
          </el-button>
          <el-button
            :disabled="busy || !selected"
            :loading="operation === 'save'"
            @click="save(false)"
          >
            {{ COPY.save }}
          </el-button>
          <el-button
            type="primary"
            :disabled="busy || !selected"
            :loading="operation === 'test'"
            @click="save(true)"
          >
            {{ current && !dirty ? COPY.test : COPY.saveTest }}
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Search, RefreshCw, ShieldCheck, ArrowUpRight, ExternalLink, LockKeyhole } from 'lucide-vue-next'
import { useIntegrationsStore } from '@/stores/integrations'
import { useAppStore } from '@/stores/app'
import { integrationsApi } from '@/api/integrations'
import { getSettingsError } from '@/utils/personalCenter'
import { connectionState, stateMeta, serviceConnections, primaryConnection, filterCatalog, connectionForm, connectionPayload, validateConnectionForm, formatConnectionDate as formatDate } from '@/utils/integrationCatalog'
import { INTEGRATION_UI as COPY, INTEGRATION_CATEGORIES as CATEGORIES, INTEGRATION_STATES as STATES, INTEGRATION_EVENTS as EVENTS, INTEGRATION_DELIVERY_STATES as DELIVERY_STATES, INTEGRATION_MODES as MODES, INTEGRATION_NAME_LIMIT as NAME_LIMIT, INTEGRATION_FIELD_LIMIT as FIELD_LIMIT } from '@/config/integrationCatalog'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageToolbar from '@/components/layout/PageToolbar.vue'
import IntegrationLogo from '@/components/common/IntegrationLogo.vue'

const store = useIntegrationsStore(), app = useAppStore()
const query = ref(''), status = ref('all'), category = ref('all'), loadError = ref(false)
const drawer = ref(false), selected = ref(null), connectionId = ref(null)
const form = ref({ name: '', fields: {}, events: [], clearSecrets: [] }), baseline = ref('')
const errors = ref({}), actionError = ref(''), result = ref(null), operation = ref('')
const history = ref([]), historyError = ref(false), historyLoading = ref(false)
let historyRequest = 0
const busy = computed(() => !!operation.value)
const dirty = computed(() => !!selected.value && JSON.stringify(form.value) !== baseline.value)
const current = computed(() => store.integrations.find(item => item.id === connectionId.value))
const connections = computed(() => selected.value ? serviceConnections(selected.value, store.integrations) : [])
const filtered = computed(() => filterCatalog(store.availableIntegrations, store.integrations, { category: category.value, status: status.value, query: query.value }))
const configuredCount = computed(() => store.availableIntegrations.filter(item => primary(item)).length)
const verifiedCount = computed(() => store.availableIntegrations.filter(item => connectionState(primary(item)) === 'success').length)
const primary = service => primaryConnection(service, store.integrations)
const categoryCount = key => store.availableIntegrations.filter(item => key === 'all' || item.category === key).length
const isSecretSaved = field => current.value?.configuredFields?.includes(field.key)

async function load() {
  loadError.value = false
  try { await store.loadCatalog() } catch { loadError.value = true }
}
function resetFilters() { query.value = ''; status.value = 'all'; category.value = 'all' }
function setForm(connection) {
  connectionId.value = connection?.id || null
  form.value = connectionForm(selected.value, connection)
  baseline.value = JSON.stringify(form.value)
  errors.value = {}; actionError.value = ''; result.value = null
  loadHistory()
}
function open(service) { selected.value = service; setForm(primary(service)); drawer.value = true }
async function confirmDiscard() {
  if (!dirty.value) return true
  try { await ElMessageBox.confirm(COPY.discard, COPY.confirm, { confirmButtonText: COPY.confirm, cancelButtonText: COPY.cancel }); return true } catch { return false }
}
async function switchConnection(id) {
  if (await confirmDiscard()) setForm(store.integrations.find(item => item.id === id))
}
async function beforeClose(done) {
  if (!busy.value && await confirmDiscard()) done()
}
function clearEditor() {
  selected.value = null; connectionId.value = null; form.value = { name: '', fields: {}, events: [], clearSecrets: [] }
  result.value = null; history.value = []; historyRequest++
}
async function loadHistory() {
  const requestId = ++historyRequest, id = connectionId.value
  history.value = []; historyError.value = false; historyLoading.value = false
  if (!id || selected.value?.mode === 'api') return
  historyLoading.value = true
  try { const records = await integrationsApi.getIntegrationDeliveries(id); if (requestId === historyRequest) history.value = records }
  catch { if (requestId === historyRequest) historyError.value = true }
  finally { if (requestId === historyRequest) historyLoading.value = false }
}
async function save(test) {
  if (busy.value || !selected.value) return
  errors.value = validateConnectionForm(selected.value, form.value, current.value)
  if (Object.keys(errors.value).length) return
  operation.value = test ? 'test' : 'save'; actionError.value = ''; result.value = null
  try {
    if (!current.value || dirty.value) {
      const saved = await store.saveIntegration(connectionPayload(selected.value, form.value, current.value), connectionId.value)
      setForm(saved)
    }
    if (test) {
      const response = await store.testIntegration(connectionId.value)
      result.value = response.result
      await loadHistory()
    } else app.success(COPY.saved)
  } catch (error) { actionError.value = getSettingsError(error, COPY.saveError) }
  finally { operation.value = '' }
}
async function sync() {
  if (busy.value || !current.value || dirty.value) return
  operation.value = 'sync'; actionError.value = ''; result.value = null
  try { result.value = (await store.syncIntegration(connectionId.value)).result }
  catch (error) { actionError.value = getSettingsError(error, COPY.actionError) }
  finally { operation.value = '' }
}
async function disconnect() {
  operation.value = 'disconnect'; actionError.value = ''
  try { await store.disconnectIntegration(connectionId.value); result.value = null; app.success(COPY.disconnected) }
  catch (error) { actionError.value = getSettingsError(error, COPY.actionError) }
  finally { operation.value = '' }
}
async function remove() {
  try { await ElMessageBox.confirm(COPY.removeConfirm, COPY.confirm, { type: 'warning', confirmButtonText: COPY.remove, cancelButtonText: COPY.cancel }) } catch { return }
  operation.value = 'delete'
  try { await store.deleteIntegration(connectionId.value); setForm(connections.value[0]); app.success(COPY.removed) }
  catch (error) { actionError.value = getSettingsError(error, COPY.actionError) }
  finally { operation.value = '' }
}
onMounted(load)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.integrations-page { min-width: 0; }
.catalog-note { display: flex; gap: $spacing-2; align-items: flex-start; color: var(--el-text-color-secondary); font-size: $font-size-sm; margin: 0 0 var(--page-section-gap); svg { flex-shrink: 0; color: var(--el-color-primary); } }
.catalog-count { color: var(--el-text-color-secondary); font-size: $font-size-xs; }
.category-tabs { margin-bottom: $spacing-4; }
.load-error { display: grid; justify-items: start; gap: $spacing-4; }
.service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr)); gap: var(--content-gap); }
.service-card { min-width: 0; padding: var(--content-card-padding, #{$spacing-5}); border: 1px solid var(--el-border-color); border-radius: $radius-xl; background: var(--el-bg-color); display: flex; flex-direction: column; }
.service-heading { display: flex; align-items: center; gap: $spacing-3; .el-tag { align-self: flex-start; flex-shrink: 0; } }
.service-name { flex: 1; min-width: 0; h2 { font-size: $font-size-base; margin: 0 0 $spacing-1; overflow-wrap: anywhere; } span { font-size: $font-size-xs; color: var(--el-text-color-secondary); } }
.service-description { font-size: $font-size-sm; line-height: 1.6; color: var(--el-text-color-regular); margin: $spacing-4 0 $spacing-5; flex: 1; }
.service-footer { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: $spacing-2; }
.service-evidence { font-size: $font-size-xs; color: var(--el-text-color-secondary); }
.el-button svg { margin-inline: $spacing-1; }
.detail-heading { display: flex; align-items: center; gap: $spacing-4; h2 { margin: 0; font-size: $font-size-lg; } p { margin: $spacing-1 0 0; } }
.detail-section { margin-block: $spacing-6; h3 { font-size: $font-size-base; margin: 0 0 $spacing-3; } p { line-height: 1.65; font-size: $font-size-sm; } }
.section-title { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: $spacing-2; margin-bottom: $spacing-3; h3 { margin: 0; } a { color: var(--el-color-primary); display: inline-flex; align-items: center; gap: $spacing-1; font-size: $font-size-sm; } }
.scope-note { padding: $spacing-3; border-radius: $radius-md; background: var(--el-fill-color-light); color: var(--el-text-color-secondary); }
.field-hint { font-size: $font-size-xs !important; color: var(--el-text-color-secondary); margin: $spacing-2 0 $spacing-4; line-height: 1.6; svg { vertical-align: middle; margin-inline-end: $spacing-1; } }
.connection-picker { display: flex; flex-wrap: wrap; gap: $spacing-2; margin-top: $spacing-5; .el-select { flex: 1; min-width: 0; } }
.connection-actions, .drawer-actions { display: flex; flex-wrap: wrap; gap: $spacing-2; .el-button { margin-left: 0; } }
.drawer-actions { justify-content: flex-end; }
.result-message { margin-top: $spacing-4; }
.error-text { color: var(--el-color-danger); overflow-wrap: anywhere; }
.resource-list, .delivery-list { list-style: none; padding: 0; margin: 0; li { padding: $spacing-3 0; border-bottom: 1px solid var(--el-border-color-lighter); } code { display: block; color: var(--el-text-color-secondary); font-size: $font-size-xs; overflow-wrap: anywhere; } }
.delivery-list { div { display: flex; justify-content: space-between; gap: $spacing-2; font-size: $font-size-sm; } p { margin: $spacing-1 0; } small { color: var(--el-text-color-secondary); } }
.data-preview { max-width: 100%; overflow: auto; td { border: 1px solid var(--el-border-color); padding: $spacing-2; white-space: nowrap; font-size: $font-size-sm; } table { border-collapse: collapse; } }
:deep(.el-checkbox-group) { display: flex; flex-wrap: wrap; }
:deep(.el-form-item__content) > .field-hint { flex-basis: 100%; }
:deep(.el-drawer__body) { min-width: 0; }
:deep(.el-drawer__footer) { border-top: 1px solid var(--el-border-color-light); }
@media (max-width: $breakpoint-sm) { .service-heading { flex-wrap: wrap; } .service-name { flex-basis: 50%; } .drawer-actions .el-button { flex: 1; } }
</style>
