<template>
  <PageShell
    width="wide"
    class="applications-page"
  >
    <router-link
      class="delivery-link"
      to="/applications"
    >
      返回应用中心
    </router-link>
    <PageHeader
      :title="application?.name || '应用工作区'"
      :subtitle="application?.description || '配置、测试、发布和追踪应用请求。'"
    >
      <template
        v-if="application"
        #actions
      >
        <button
          type="button"
          class="delivery-button"
          data-testid="application-refresh"
          :disabled="Boolean(busy) || evaluationBusy"
          @click="reload"
        >
          刷新状态
        </button>
        <span
          class="delivery-hint"
          role="status"
        >
          {{ dirty ? '有未保存的修改' : '草稿已保存' }}
        </span>
        <button
          v-if="canEdit"
          type="button"
          class="delivery-button delivery-button--primary"
          :disabled="!dirty || Boolean(busy) || testRecoverable"
          data-testid="application-save"
          @click="save"
        >
          {{ busy === 'save' ? '正在保存…' : '保存草稿' }}
        </button>
      </template>
    </PageHeader>
    <div
      v-if="loadError"
      class="delivery-feedback delivery-feedback--error"
      role="alert"
    >
      {{ loadError }}
      <button
        type="button"
        class="delivery-button"
        @click="load"
      >
        重新加载
      </button>
    </div>
    <div
      v-else-if="loading"
      class="delivery-loading"
      role="status"
    >
      正在加载应用配置…
    </div>
    <template v-else-if="application">
      <div class="delivery-context">
        <span>
          {{ applicationKindLabel(application.kind) }}
        </span>
        <span>
          {{ application.tenantId ? '团队空间' : '个人空间' }}
        </span>
        <span
          class="delivery-state"
          :data-status="applicationStatus(application)"
        >
          {{ applicationStatusLabel(application) }}
        </span>
        <span
          v-if="application.activeRelease"
          class="delivery-mono"
        >
          线上 v
          {{ application.activeRelease.version }}
        </span>
        <span class="delivery-mono">
          {{ application.id }}
        </span>
      </div>
      <ol
        class="delivery-timeline"
        aria-label="交付状态"
      >
        <li :data-ready="!dirty">
          <span>
            01
          </span>
          {{ dirty ? '有未保存修改' : '已保存配置' }}
        </li>
        <li :data-ready="testIsCurrent">
          <span>
            02
          </span>
          {{ testIsCurrent ? '当前草稿已测试' : application.testedFingerprint ? '测试需要更新' : '等待测试' }}
        </li>
        <li :data-ready="Boolean(application.activeRelease)">
          <span>
            03
          </span>
          {{ application.activeRelease ? `v${application.activeRelease.version} 正在服务` : '等待发布' }}
        </li>
      </ol>
      <p
        v-if="!canEdit"
        class="delivery-feedback"
      >
        你可以查看应用配置与请求记录。修改和测试需要应用编辑权限。
      </p>
      <div
        v-if="feedback"
        :class="['delivery-feedback', { 'delivery-feedback--error': feedbackIsError }]"
        :role="feedbackIsError ? 'alert' : 'status'"
      >
        {{ feedback }}
      </div>
      <nav
        class="delivery-tabs"
        role="tablist"
        aria-label="应用任务"
      >
        <button
          v-for="tab in APPLICATIONS.tabs"
          :id="`application-tab-${tab.id}`"
          :key="tab.id"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.id"
          :aria-controls="`application-panel-${tab.id}`"
          :disabled="evaluationBusy"
          :tabindex="activeTab === tab.id ? 0 : -1"
          @click="selectTab(tab.id)"
          @keydown="handleTabKey($event, tab.id)"
        >
          {{ tab.label }}
        </button>
      </nav>
      <section
        v-show="activeTab === 'build'"
        id="application-panel-build"
        role="tabpanel"
        aria-labelledby="application-tab-build"
      >
        <form
          class="delivery-form"
          aria-label="应用配置"
          @submit.prevent="save"
        >
          <div class="delivery-section-heading">
            <div>
              <span class="delivery-eyebrow">
                BUILD
              </span>
              <h2>
                草稿配置
              </h2>
              <p>
                保存只更新草稿，线上版本保持不变。
              </p>
            </div>
          </div>
          <div class="delivery-form-grid">
            <div class="delivery-field">
              <label for="application-name">
                应用名称
              </label>
              <input
                id="application-name"
                v-model="form.name"
                aria-label="应用名称"
                :maxlength="APPLICATIONS.nameMaxLength"
                :disabled="!canEdit || Boolean(busy) || testRecoverable"
                required
              >
            </div>
            <ApplicationResourceField
              v-model="form.draft[application.kind === 'knowledge' ? 'collection_id' : 'workflow_id']"
              :kind="application.kind"
              :tenant-id="application.tenantId || ''"
              :disabled="!canEdit || Boolean(busy) || testRecoverable"
            />
            <div class="delivery-field delivery-field--full">
              <label for="application-description">
                用途说明
              </label>
              <textarea
                id="application-description"
                v-model="form.description"
                aria-label="用途说明"
                :maxlength="APPLICATIONS.descriptionMaxLength"
                rows="2"
                :disabled="!canEdit || Boolean(busy) || testRecoverable"
              />
            </div>
            <template v-if="application.kind === 'knowledge'">
              <div class="delivery-field delivery-field--full">
                <label for="application-system-prompt">
                  系统提示词
                </label>
                <textarea
                  id="application-system-prompt"
                  v-model="form.draft.system_prompt"
                  aria-label="系统提示词"
                  :maxlength="APPLICATIONS.promptMaxLength"
                  rows="5"
                  :disabled="!canEdit || Boolean(busy) || testRecoverable"
                />
                <p class="delivery-hint">
                  回答基于当前知识库检索结果。内容实时更新，发布时保留提示词与检索配置。
                </p>
              </div>
              <div class="delivery-field">
                <label for="application-top-k">
                  检索片段数
                </label>
                <input
                  id="application-top-k"
                  v-model.number="form.draft.top_k"
                  aria-label="检索片段数"
                  type="number"
                  min="1"
                  :max="APPLICATIONS.maxTopK"
                  step="1"
                  :disabled="!canEdit || Boolean(busy) || testRecoverable"
                >
              </div>
              <div class="delivery-field">
                <label for="application-min-similarity">
                  最低相似度
                </label>
                <input
                  id="application-min-similarity"
                  v-model.number="form.draft.min_similarity"
                  aria-label="最低相似度"
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  :disabled="!canEdit || Boolean(busy) || testRecoverable"
                >
              </div>
            </template>
          </div>
          <div class="delivery-actions">
            <router-link
              v-if="sourcePath"
              class="delivery-button"
              :to="sourcePath"
            >
              {{ application.kind === 'knowledge' ? '打开知识库' : '在画布中编辑工作流' }}
              <ArrowUpRight />
            </router-link>
            <button
              type="button"
              class="delivery-button"
              @click="selectTab('test')"
            >
              前往测试
              <ArrowRight />
            </button>
          </div>
        </form>
        <ApplicationReadiness
          :application-id="String(application.id)"
          :revision="refreshRevision"
          :dirty="dirty"
        />
        <div
          v-if="canPublish"
          class="delivery-danger-zone"
        >
          <div>
            <strong>
              删除应用
            </strong>
            <p class="delivery-hint">
              停用调用能力并保留后台审计记录。
            </p>
          </div>
          <button
            type="button"
            class="delivery-button delivery-button--danger"
            :disabled="Boolean(busy)"
            @click="remove"
          >
            删除应用
          </button>
        </div>
      </section>
      <section
        v-if="activeTab === 'test'"
        id="application-panel-test"
        role="tabpanel"
        aria-labelledby="application-tab-test"
      >
        <div class="delivery-section-heading">
          <div>
            <span class="delivery-eyebrow">
              PLAYGROUND
            </span>
            <h2>
              测试当前草稿
            </h2>
            <p>
              执行真实检索或工作流，成功后才能发布此配置。
            </p>
          </div>
        </div>
        <p
          v-if="dirty"
          class="delivery-feedback"
        >
          配置有未保存的修改，请先保存草稿。
        </p>
        <p
          v-if="testRecoverable"
          class="delivery-feedback"
        >
          上次请求的结果尚未确认。恢复会使用相同请求标识与原输入，不会主动启动第二次执行；也可到请求日志检查。
        </p>
        <div class="delivery-workbench">
          <form
            aria-label="测试应用"
            @submit.prevent="runTest"
          >
            <div class="delivery-field">
              <label for="application-test-json">
                测试输入 JSON
              </label>
              <textarea
                id="application-test-json"
                v-model="testInput"
                data-testid="application-test-input"
                aria-label="测试输入 JSON"
                spellcheck="false"
                :disabled="Boolean(busy) || !canEdit || testRecoverable"
              />
              <p class="delivery-hint">
                {{ application.kind === 'knowledge' ? 'query 为问题，filters 为可选简单键值过滤条件。' : '输入会保留原始字段名称，交给工作流的输入节点处理。' }}
              </p>
            </div>
            <p
              v-if="testError"
              class="delivery-feedback delivery-feedback--error"
              role="alert"
            >
              {{ testError }}
            </p>
            <div class="delivery-actions">
              <button
                data-testid="application-test"
                type="submit"
                class="delivery-button delivery-button--primary"
                :disabled="dirty || Boolean(busy) || !canEdit"
              >
                {{ busy === 'test' ? '执行中，请稍候…' : testRecoverable ? '恢复测试请求' : '运行草稿测试' }}
                <Play />
              </button>
              <button
                type="button"
                class="delivery-button"
                :disabled="Boolean(busy) || !canEdit"
                data-testid="application-save-case"
                @click="openEvaluation()"
              >
                保存输入为用例
              </button>
            </div>
            <p
              v-if="testInputDirty"
              class="delivery-hint"
            >
              输入尚未保存为回归用例，离开应用前会提示确认；刷新状态会保留当前输入。
            </p>
            <p
              v-if="busy === 'test'"
              class="delivery-hint"
              role="status"
            >
              请求正在服务端执行。完成后会显示结果与请求记录。
            </p>
          </form>
          <ApplicationRequestTrace
            v-if="testResult"
            :request="testResult"
            :can-save-case="canEdit"
            @save-case="openEvaluation($event)"
          />
          <div
            v-else
            class="delivery-empty"
          >
            <Activity
              :size="28"
              aria-hidden="true"
            />
            <h2>
              等待测试结果
            </h2>
            <p>
              发送一份 JSON 输入，查看实际输出、耗时与错误。未提供的模型用量会保持未知。
            </p>
          </div>
        </div>
      </section>
      <section
        v-if="activeTab === 'evaluations'"
        id="application-panel-evaluations"
        role="tabpanel"
        aria-labelledby="application-tab-evaluations"
      >
        <ApplicationEvaluations
          :key="application.id"
          :application="application"
          :dirty="dirty"
          :busy="busy"
          :seed-request="evaluationSeed"
          @updated="updateMetadata"
          @dirty="evaluationDirty = $event"
          @busy="evaluationBusy = $event"
          @case-saved="savedCaseInput"
          @request="openRequest"
        />
      </section>
      <section
        v-if="activeTab === 'publish'"
        id="application-panel-publish"
        role="tabpanel"
        aria-labelledby="application-tab-publish"
      >
        <ApplicationPublish
          :key="application.id"
          :application="application"
          :ready="readyToPublish"
          :dirty="dirty"
          :busy="busy"
          :secret="secret"
          :revision="refreshRevision"
          @publish="changePublication('publish')"
          @rollback="changePublication('rollback', $event)"
          @unpublish="changePublication('unpublish')"
          @secret="secret = $event"
          @busy="busy = $event"
        />
      </section>
      <section
        v-if="activeTab === 'requests'"
        id="application-panel-requests"
        role="tabpanel"
        aria-labelledby="application-tab-requests"
      >
        <ApplicationRequests
          :key="application.id"
          :application-id="String(application.id)"
          :revision="refreshRevision"
          :can-edit="canEdit"
          @save-case="openEvaluation($event)"
        />
      </section>
    </template>
  </PageShell>
</template>

<script setup>
import {
  computed,
  nextTick,
  ref,
  watch
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Play
} from 'lucide-vue-next'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import ApplicationResourceField from './ApplicationResourceField.vue'
import ApplicationRequestTrace from './ApplicationRequestTrace.vue'
import ApplicationPublish from './ApplicationPublish.vue'
import ApplicationRequests from './ApplicationRequests.vue'
import ApplicationReadiness from './ApplicationReadiness.vue'
import ApplicationEvaluations from './ApplicationEvaluations.vue'
import {
  APPLICATIONS,
  applicationKindLabel,
  applicationStatus,
  applicationStatusLabel,
  parseApplicationInput
} from '@/config/applications'
import {
  useApplicationWorkspace
} from './useApplicationWorkspace'
import './applications.css'

const {
  application,
  form,
  loading,
  loadError,
  busy,
  feedback,
  feedbackIsError,
  testInput,
  testInputDirty,
  evaluationDirty,
  evaluationBusy,
  testResult,
  testError,
  testRecoverable,
  secret,
  refreshRevision,
  activeTab,
  dirty,
  canEdit,
  canPublish,
  readyToPublish,
  load,
  reload,
  save,
  runTest,
  changePublication,
  remove,
  selectTab,
  showFeedback,
  acknowledgeTestInput,
  updateMetadata
} = useApplicationWorkspace()
const router = useRouter()
const route = useRoute()
const evaluationSeed = ref(null)
async function openEvaluation(record) {
  try {
    const input = record?.inputData ?? parseApplicationInput(testInput.value)
    evaluationSeed.value = { ...(record?.id ? { id: record.id } : {}), inputData: JSON.parse(JSON.stringify(input)) }
    await selectTab('evaluations')
  } catch (failure) { showFeedback(failure.message, true) }
}
function savedCaseInput(input) { acknowledgeTestInput(input); evaluationSeed.value = null }
function openRequest(id) { return router.replace({ query: { ...route.query, tab: 'requests', request: id } }) }
watch(() => [route.params.id, activeTab.value], ([id, tab], previous) => {
  if (previous && (id !== previous[0] || previous[1] === 'evaluations' && tab !== 'evaluations')) evaluationSeed.value = null
})
const testIsCurrent = computed(() => !dirty.value && Boolean(application.value?.testedFingerprint) && application.value.testedFingerprint === application.value.draftFingerprint && application.value.lastTestStatus === 'completed')
const sourcePath = computed(() => {
  const id = form.value.draft[application.value?.kind === 'knowledge' ? 'collection_id' : 'workflow_id']
  return id ? application.value?.kind === 'knowledge' ? `/knowledge/${encodeURIComponent(id)}` : `/workflows/${encodeURIComponent(id)}/edit` : ''
})
async function handleTabKey(event, id) {
  const current = APPLICATIONS.tabs.findIndex(tab => tab.id === id)
  const index = event.key === 'ArrowRight' ? (current + 1) % APPLICATIONS.tabs.length : event.key === 'ArrowLeft' ? (current - 1 + APPLICATIONS.tabs.length) % APPLICATIONS.tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? APPLICATIONS.tabs.length - 1 : null
  if (index === null) return
  event.preventDefault()
  const parent = event.currentTarget.parentElement
  await selectTab(APPLICATIONS.tabs[index].id)
  await nextTick()
  parent.querySelectorAll('[role="tab"]')[index]?.focus()
}
</script>

