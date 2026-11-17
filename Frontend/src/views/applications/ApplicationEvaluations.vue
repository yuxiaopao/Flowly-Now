<template>
  <div class="application-evaluations">
    <div class="delivery-section-heading">
      <div>
        <span class="delivery-eyebrow">REGRESSION</span>
        <h2>应用回归评测</h2>
        <p>
          保存真实输入与确定性断言，由服务端运行完整批次，保留可复查证据。
        </p>
      </div>
    </div>
    <p
      v-if="!evaluation.canEdit"
      class="delivery-feedback"
    >
      当前为只读权限，可以查看用例、历史与比较结果；编辑及运行需要应用编辑权限。
    </p>
    <p
      v-if="evaluation.feedback"
      :role="evaluation.failedFeedback ? 'alert' : 'status'"
      :class="[
        'delivery-feedback',
        { 'delivery-feedback--error': evaluation.failedFeedback }
      ]"
    >
      {{ evaluation.feedback }}
    </p>
    <button
      v-if="evaluation.writeUncertain"
      type="button"
      class="delivery-button"
      @click="evaluation.confirmUncertainWrite"
    >
      刷新列表并核对操作结果
    </button>

    <section
      class="evaluation-section"
      aria-label="测试集与用例"
    >
      <div class="delivery-section-heading">
        <h3>测试集与用例</h3>
        <div class="delivery-actions">
          <button
            v-if="evaluation.canEdit"
            type="button"
            class="delivery-button"
            data-testid="evaluation-new-suite"
            :disabled="evaluation.blocked || evaluation.recoverable"
            @click="openSuite()"
          >
            新建测试集
          </button>
          <button
            type="button"
            class="delivery-button"
            :disabled="evaluation.suiteLoading"
            @click="evaluation.loadSuites()"
          >
            刷新测试集
          </button>
        </div>
      </div>
      <div
        v-if="evaluation.suiteError"
        role="alert"
        class="delivery-feedback delivery-feedback--error"
      >
        {{ evaluation.suiteError }}
        <button
          type="button"
          class="delivery-link"
          @click="evaluation.loadSuites()"
        >
          重试测试集
        </button>
      </div>
      <p
        v-else-if="evaluation.suiteLoading"
        role="status"
        class="delivery-loading"
      >
        正在加载测试集…
      </p>
      <p
        v-else-if="!evaluation.suites.length"
        class="delivery-empty"
      >
        尚无测试集。先创建一个测试集，再保存需要持续验证的输入和断言。
      </p>
      <div
        v-if="evaluation.suites.length"
        class="evaluation-controls"
      >
        <div class="delivery-field">
          <label for="evaluation-suite">选择测试集</label>
          <select
            id="evaluation-suite"
            :value="evaluation.suiteId"
            aria-label="选择测试集"
            data-testid="evaluation-suite"
            :disabled="evaluation.blocked || evaluation.recoverable"
            @change="changeSuite"
          >
            <option
              v-for="suite in evaluation.suites"
              :key="suite.id"
              :value="suite.id"
            >
              {{ suite.name }} · 修订 {{ suite.revision }}
            </option>
          </select>
        </div>
        <div class="delivery-actions">
          <button
            v-if="evaluation.canEdit"
            type="button"
            class="delivery-button"
            :disabled="evaluation.blocked || evaluation.recoverable"
            @click="openSuite(evaluation.selectedSuite)"
          >
            编辑测试集
          </button>
          <button
            type="button"
            class="delivery-button"
            :disabled="!evaluation.suiteId || exporting"
            @click="exportSuite"
          >
            {{ exporting ? '正在准备下载…' : '导出 JSON' }}
          </button>
          <button
            v-if="evaluation.canEdit"
            type="button"
            class="delivery-button"
            :disabled="evaluation.blocked || evaluation.recoverable"
            @click="deleteSuite"
          >
            删除测试集
          </button>
        </div>
      </div>
      <p
        v-if="evaluation.selectedSuite"
        class="delivery-hint"
      >
        {{ evaluation.selectedSuite.description || '未填写说明' }} ·
        {{ evaluation.selectedSuite.caseCount }} 条用例，{{
          evaluation.selectedSuite.enabledCaseCount
        }}
        条启用。修改会增加修订号；在途批次保留启动时的快照。
      </p>

      <form
        v-if="suiteEditing"
        class="delivery-form"
        aria-label="编辑测试集"
        @submit.prevent="saveSuite"
      >
        <div class="delivery-form-grid">
          <div class="delivery-field">
            <label for="evaluation-suite-name">测试集名称</label>
            <input
              id="evaluation-suite-name"
              v-model="suiteForm.name"
              aria-label="测试集名称"
              data-testid="evaluation-suite-name"
              :maxlength="CONFIG.nameMaxLength"
              :disabled="evaluation.blocked"
              required
            >
          </div>
          <div class="delivery-field delivery-field--full">
            <label for="evaluation-suite-description">测试集说明</label>
            <textarea
              id="evaluation-suite-description"
              v-model="suiteForm.description"
              aria-label="测试集说明"
              :maxlength="CONFIG.descriptionMaxLength"
              :disabled="evaluation.blocked"
              rows="2"
            />
          </div>
        </div>
        <p
          v-if="suiteFormError"
          role="alert"
          class="delivery-field-error"
        >
          {{ suiteFormError }}
        </p>
        <div class="delivery-actions">
          <button
            type="submit"
            class="delivery-button delivery-button--primary"
            data-testid="evaluation-suite-save"
            :disabled="evaluation.blocked"
          >
            保存测试集
          </button>
          <button
            type="button"
            class="delivery-button"
            :disabled="evaluation.blocked"
            @click="closeSuite"
          >
            取消编辑
          </button>
        </div>
      </form>

      <div
        v-if="evaluation.canEdit"
        class="evaluation-import"
      >
        <button
          type="button"
          class="delivery-link"
          :disabled="evaluation.blocked || evaluation.recoverable"
          @click="toggleImport"
        >
          {{ importOpen ? '收起导入' : '导入测试集 JSON' }}
        </button>
        <form
          v-if="importOpen"
          aria-label="导入测试集"
          class="delivery-form"
          @submit.prevent="importSuite"
        >
          <div class="delivery-field">
            <label for="evaluation-import-file">选择导出的 JSON 文件</label>
            <input
              id="evaluation-import-file"
              type="file"
              accept=".json,application/json"
              aria-label="导入测试集文件"
              :disabled="evaluation.blocked"
              @change="readImportFile"
            >
          </div>
          <div class="delivery-field">
            <label for="evaluation-import-json">或粘贴完整测试集 JSON</label>
            <textarea
              id="evaluation-import-json"
              v-model="importText"
              aria-label="测试集导入 JSON"
              rows="6"
              spellcheck="false"
              :disabled="evaluation.blocked"
            />
          </div>
          <p class="delivery-hint">
            使用 Flowly
            导出格式。服务端会校验全部用例后在同一事务中导入，不覆盖已有测试集。
          </p>
          <p
            v-if="importError"
            role="alert"
            class="delivery-field-error"
          >
            {{ importError }}
          </p>
          <button
            type="submit"
            class="delivery-button"
            :disabled="evaluation.blocked || !importText.trim()"
          >
            导入为新测试集
          </button>
        </form>
      </div>

      <template v-if="evaluation.suiteId">
        <div class="delivery-section-heading">
          <h4>用例列表</h4>
          <div class="delivery-actions">
            <button
              v-if="evaluation.canEdit"
              type="button"
              class="delivery-button"
              data-testid="evaluation-new-case"
              :disabled="evaluation.blocked || evaluation.recoverable"
              @click="openCase()"
            >
              新增用例
            </button>
            <button
              type="button"
              class="delivery-button"
              :disabled="evaluation.casesLoading"
              @click="evaluation.loadCases"
            >
              刷新用例
            </button>
          </div>
        </div>
        <p
          v-if="seedRequest?.inputData && evaluation.canEdit"
          class="delivery-feedback"
        >
          当前请求输入可保存为长期回归用例。
          <button
            type="button"
            class="delivery-link"
            :disabled="evaluation.blocked || evaluation.recoverable"
            @click="openCase(null, true)"
          >
            将此输入保存为用例
          </button>
        </p>
        <p
          v-if="evaluation.casesError"
          role="alert"
          class="delivery-feedback delivery-feedback--error"
        >
          {{ evaluation.casesError }}
          <button
            type="button"
            class="delivery-link"
            @click="evaluation.loadCases"
          >
            重试用例
          </button>
        </p>
        <p
          v-else-if="evaluation.casesLoading"
          role="status"
          class="delivery-loading"
        >
          正在加载完整用例集…
        </p>
        <p
          v-else-if="!evaluation.cases.length"
          class="delivery-empty"
        >
          还没有用例。添加输入和至少一条断言后，可以运行完整测试集。
        </p>
        <div
          v-else
          class="delivery-table-wrap"
        >
          <table class="delivery-table">
            <thead>
              <tr>
                <th>用例 / 输入摘要</th>
                <th>状态</th>
                <th>断言数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in visibleCases"
                :key="row.id"
                :data-testid="`evaluation-case-${row.id}`"
              >
                <td>
                  {{ row.name }}
                  <small class="evaluation-input-preview">
                    {{ preview(row.inputData) }}
                  </small>
                </td>
                <td>{{ row.enabled ? '启用' : '停用' }}</td>
                <td>{{ row.assertions.length }}</td>
                <td>
                  <div class="delivery-actions">
                    <button
                      type="button"
                      class="delivery-link"
                      :disabled="evaluation.blocked"
                      @click="openCase(row)"
                    >
                      {{ evaluation.canEdit ? '查看 / 编辑' : '查看' }}
                    </button>
                    <button
                      v-if="evaluation.canEdit"
                      type="button"
                      class="delivery-link"
                      :disabled="evaluation.blocked || evaluation.recoverable"
                      @click="toggleCase(row)"
                    >
                      {{ row.enabled ? '停用' : '启用' }}
                    </button>
                    <button
                      v-if="evaluation.canEdit"
                      type="button"
                      class="delivery-link"
                      :disabled="evaluation.blocked || evaluation.recoverable"
                      @click="deleteCase(row)"
                    >
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <nav
          v-if="casePages > 1"
          class="delivery-pagination"
          aria-label="用例分页"
        >
          <span>
            共 {{ evaluation.cases.length }} 条 · 第 {{ casePage }} /
            {{ casePages }} 页
          </span>
          <button
            type="button"
            class="delivery-button"
            :disabled="casePage <= 1"
            @click="casePage--"
          >
            上一页用例
          </button>
          <button
            type="button"
            class="delivery-button"
            :disabled="casePage >= casePages"
            @click="casePage++"
          >
            下一页用例
          </button>
        </nav>
        <ApplicationCaseEditor
          v-if="caseEditing"
          :key="caseEditorKey"
          :value="editingCase"
          :seed-input="editorSeed"
          :disabled="!evaluation.canEdit || evaluation.writeUncertain || evaluation.recoverable"
          :busy="evaluation.mutation === 'case'"
          @dirty="caseDirty = $event"
          @save="saveCase"
          @cancel="closeCase"
        />
      </template>
    </section>

    <section
      class="evaluation-section"
      aria-label="运行回归评测"
    >
      <div class="delivery-section-heading">
        <h3>运行回归评测</h3>
      </div>
      <p class="delivery-hint">
        批次会真实执行启用用例，可能调用外部服务并产生副作用。它独立于单次草稿测试，不会替代单次成功证明。
      </p>
      <div class="evaluation-controls">
        <div class="delivery-field">
          <label for="evaluation-target">运行目标</label>
          <select
            id="evaluation-target"
            v-model="evaluation.target"
            aria-label="评测运行目标"
            :disabled="evaluation.blocked || evaluation.recoverable"
          >
            <option value="draft">
              当前已保存草稿
            </option>
            <option value="release">
              真实发布版本
            </option>
          </select>
        </div>
        <div
          v-if="evaluation.target === 'release'"
          class="delivery-field"
        >
          <label for="evaluation-release">发布版本</label>
          <select
            id="evaluation-release"
            v-model="evaluation.releaseId"
            aria-label="评测发布版本"
            :disabled="evaluation.blocked || evaluation.recoverable"
          >
            <option value="">
              选择版本
            </option>
            <option
              v-for="release in evaluation.releases"
              :key="release.id"
              :value="release.id"
            >
              v{{ release.version }} · {{ applicationDate(release.createdAt) }}
            </option>
          </select>
        </div>
      </div>
      <p
        v-if="dirty && evaluation.target === 'draft'"
        class="delivery-feedback"
      >
        应用草稿有未保存修改，请先保存再评测当前草稿。
      </p>
      <p
        v-if="evaluation.releasesError"
        role="alert"
        class="delivery-feedback delivery-feedback--error"
      >
        {{ evaluation.releasesError }}
        <button
          type="button"
          class="delivery-link"
          @click="evaluation.loadReleases"
        >
          重试版本
        </button>
      </p>
      <p
        v-if="evaluation.suiteLoading || evaluation.casesLoading"
        role="status"
        class="delivery-hint"
      >
        正在加载测试集与用例，请稍候再运行。
      </p>
      <p
        v-else-if="!evaluation.recoverable && evaluation.suiteId && !evaluation.suiteError && !evaluation.casesError && !evaluation.hasEnabledCases"
        class="delivery-hint"
      >
        当前测试集没有启用用例，请新增或启用至少一条用例后运行。
      </p>
      <button
        v-if="evaluation.canEdit"
        type="button"
        class="delivery-button delivery-button--primary"
        data-testid="evaluation-start"
        :disabled="evaluation.blocked || evaluation.suiteLoading || evaluation.casesLoading || (!evaluation.recoverable && (!evaluation.suiteId || evaluation.suiteError || evaluation.casesError || !evaluation.hasEnabledCases || caseDirty || suiteDirty || importDirty || (dirty && evaluation.target === 'draft')))"
        @click="evaluation.startRun"
      >
        {{
          evaluation.mutation === 'start'
            ? '正在提交…'
            : evaluation.recoverable
              ? '恢复同一启动请求'
              : '运行完整测试集'
        }}
      </button>
      <p
        v-if="evaluation.recoverable"
        class="delivery-hint"
      >
        启动参数已锁定。恢复复用原请求标识；也可以先查看批次历史，不能把网络超时当作未执行。
      </p>
    </section>

    <section
      class="evaluation-section"
      aria-label="发布回归门禁"
    >
      <div class="delivery-section-heading">
        <h3>发布回归门禁</h3>
      </div>
      <p class="delivery-hint">
        可选。启用后，发布除单次草稿测试成功外，还必须通过指定测试集当前修订的完整草稿回归；配置或知识内容变化后需重跑。
      </p>
      <form
        class="evaluation-controls"
        @submit.prevent="saveGate"
      >
        <div class="delivery-field">
          <label for="evaluation-gate-suite">发布要求的测试集</label>
          <select
            id="evaluation-gate-suite"
            v-model="gateValue"
            aria-label="发布要求的测试集"
            :disabled="!application.canPublish || evaluation.blocked || evaluation.recoverable || evaluation.suiteLoading"
          >
            <option value="">
              不额外要求批量回归
            </option>
            <option
              v-if="gateValue && !evaluation.suites.some((row) => row.id === gateValue)"
              :value="gateValue"
            >
              当前门禁 · {{ gateValue }}
            </option>
            <option
              v-for="suite in evaluation.suites"
              :key="suite.id"
              :value="suite.id"
            >
              {{ suite.name }}
            </option>
          </select>
        </div>
        <button
          v-if="application.canPublish"
          type="submit"
          class="delivery-button"
          data-testid="evaluation-save-gate"
          :disabled="!gateDirty || evaluation.blocked || evaluation.recoverable"
        >
          保存发布门禁
        </button>
      </form>
      <p
        v-if="!application.canPublish"
        class="delivery-hint"
      >
        仅应用所有者或团队管理员可修改发布门禁。
      </p>
      <p
        v-if="application.evaluationGate?.required"
        class="delivery-feedback"
      >
        {{
          application.evaluationGate.ready
            ? '服务端已确认当前回归门禁通过。'
            : application.evaluationGate.reason ||
              '当前完整回归尚未满足发布要求。'
        }}
      </p>
    </section>

    <section
      class="evaluation-section"
      aria-label="回归批次历史"
    >
      <div class="delivery-section-heading">
        <h3>批次历史</h3>
        <button
          type="button"
          class="delivery-button"
          :disabled="evaluation.historyLoading"
          @click="evaluation.loadHistory(evaluation.historyPage)"
        >
          刷新历史
        </button>
      </div>
      <div class="delivery-field evaluation-history-filter">
        <label for="evaluation-history-suite">按测试集筛选历史</label>
        <select
          id="evaluation-history-suite"
          v-model="evaluation.historySuiteId"
          aria-label="按测试集筛选批次"
        >
          <option value="">
            全部测试集
          </option>
          <option
            v-for="suite in evaluation.suites"
            :key="suite.id"
            :value="suite.id"
          >
            {{ suite.name }}
          </option>
        </select>
      </div>
      <p
        v-if="evaluation.historyError"
        role="alert"
        class="delivery-feedback delivery-feedback--error"
      >
        {{ evaluation.historyError }}
        <button
          type="button"
          class="delivery-link"
          @click="evaluation.loadHistory(evaluation.historyPage)"
        >
          重试批次历史
        </button>
      </p>
      <p
        v-else-if="evaluation.historyLoading"
        role="status"
        class="delivery-loading"
      >
        正在加载批次历史…
      </p>
      <p
        v-else-if="!evaluation.history.length"
        class="delivery-empty"
      >
        暂无匹配批次。运行测试集后会记录真实结果。
      </p>
      <div
        v-else
        class="delivery-table-wrap"
      >
        <table class="delivery-table">
          <thead>
            <tr>
              <th>测试集 / 时间</th>
              <th>目标</th>
              <th>状态</th>
              <th>通过</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in evaluation.history"
              :key="run.id"
              :data-testid="`evaluation-history-${run.id}`"
            >
              <td>
                {{ run.suiteName }} · 修订 {{ run.suiteRevision }}
                <small>{{ applicationDate(run.createdAt) }}</small>
              </td>
              <td>
                {{
                  run.target === 'release'
                    ? `v${run.releaseVersion ?? '—'}`
                    : '草稿快照'
                }}
              </td>
              <td>
                {{ CONFIG.runStatuses[run.status] || run.status }}
                <small v-if="run.isStale">结果已过期</small>
              </td>
              <td>{{ run.passed }} / {{ run.total }}</td>
              <td>
                <div class="delivery-actions">
                  <button
                    type="button"
                    class="delivery-link"
                    @click="evaluation.loadRun(run.id)"
                  >
                    查看批次
                  </button>
                  <button
                    type="button"
                    class="delivery-link"
                    :disabled="evaluation.active(run) || run.id === evaluation.selectedRun?.id"
                    @click="chooseBaseline(run)"
                  >
                    作为比较基线
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav
        v-if="evaluation.historyPages > 1"
        class="delivery-pagination"
        aria-label="批次历史分页"
      >
        <span>
          共 {{ evaluation.historyCount }} 次 · 第
          {{ evaluation.historyPage }} / {{ evaluation.historyPages }} 页
        </span>
        <button
          type="button"
          class="delivery-button"
          :disabled="evaluation.historyPage <= 1 || evaluation.historyLoading"
          @click="evaluation.loadHistory(evaluation.historyPage - 1)"
        >
          上一页批次
        </button>
        <button
          type="button"
          class="delivery-button"
          :disabled="evaluation.historyPage >= evaluation.historyPages || evaluation.historyLoading"
          @click="evaluation.loadHistory(evaluation.historyPage + 1)"
        >
          下一页批次
        </button>
      </nav>
    </section>
    <p
      v-if="evaluation.runLoading"
      role="status"
      class="delivery-loading"
    >
      正在读取批次详情…
    </p>
    <p
      v-if="evaluation.runError"
      role="alert"
      class="delivery-feedback delivery-feedback--error"
    >
      {{ evaluation.runError }}
      <button
        v-if="evaluation.requestedRunId"
        type="button"
        class="delivery-link"
        @click="evaluation.loadRun(evaluation.requestedRunId)"
      >
        重新读取批次
      </button>
    </p>
    <ApplicationEvaluationRun
      v-if="evaluation.selectedRun"
      :run="evaluation.selectedRun"
      :baseline="evaluation.baseline"
      :comparison="evaluation.comparison"
      :compare-error="evaluation.compareError"
      :can-edit="evaluation.canEdit"
      :busy="evaluation.blocked"
      :loading="evaluation.runLoading"
      :comparing="evaluation.comparing"
      @refresh="evaluation.loadRun(evaluation.selectedRun.id)"
      @cancel="evaluation.cancelRun"
      @compare="evaluation.compare"
      @request="$emit('request', $event)"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { applicationEvaluationsApi as api } from '@/api/applicationEvaluations'
import {
  APPLICATION_EVALUATIONS as CONFIG,
  parseEvaluationJson,
  sameEvaluationInput
} from '@/config/applicationEvaluations'
import { applicationDate } from '@/config/applications'
import ApplicationCaseEditor from './ApplicationCaseEditor.vue'
import ApplicationEvaluationRun from './ApplicationEvaluationRun.vue'
import { useApplicationEvaluation } from './useApplicationEvaluation'
const props = defineProps({
  application: { type: Object, required: true },
  dirty: Boolean,
  busy: { type: String, default: '' },
  seedRequest: { type: Object, default: null }
})
const emit = defineEmits(['updated', 'dirty', 'busy', 'request', 'case-saved'])
const app = useAppStore()
const evaluation = reactive(useApplicationEvaluation(props, emit))
const suiteEditing = ref(false),
  suiteEditingId = ref(''),
  suiteBaseline = ref(''),
  suiteFormError = ref('')
const suiteForm = reactive({ name: '', description: '' })
const caseEditing = ref(false),
  editingCase = ref(null),
  editorSeed = ref(null),
  seedSnapshot = ref(null),
  caseDirty = ref(false),
  caseEditorKey = ref(0),
  casePage = ref(1)
const importOpen = ref(false),
  importText = ref(''),
  importError = ref(''),
  exporting = ref(false)
const gateValue = ref(''),
  gateBaseline = ref('')
const suiteDirty = computed(
  () => suiteEditing.value && JSON.stringify(suiteForm) !== suiteBaseline.value
)
const importDirty = computed(
  () => importOpen.value && Boolean(importText.value.trim())
)
const gateDirty = computed(() => gateValue.value !== gateBaseline.value)
const editorDirty = computed(
  () =>
    suiteDirty.value || caseDirty.value || importDirty.value || gateDirty.value
)
const casePages = computed(() =>
  Math.max(1, Math.ceil(evaluation.cases.length / CONFIG.pageSize))
)
const visibleCases = computed(() =>
  evaluation.cases.slice(
    (casePage.value - 1) * CONFIG.pageSize,
    casePage.value * CONFIG.pageSize
  )
)
const preview = (value) => JSON.stringify(value ?? {}).slice(0, 120)
async function discard(message = '当前编辑尚未保存，是否放弃？') {
  if (!editorDirty.value) return true
  const confirmed = await app.confirm({
    title: '放弃未保存的评测编辑？',
    message,
    confirmText: '放弃编辑',
    cancelText: '继续编辑',
    confirmType: 'warning'
  })
  if (confirmed) {
    gateValue.value = gateBaseline.value
    suiteEditing.value = false
    caseEditing.value = false
    caseDirty.value = false
    importOpen.value = false
    importText.value = ''
  }
  return confirmed
}
async function openSuite(value) {
  if (!evaluation.canEdit || !(await discard())) return
  caseEditing.value = false
  caseDirty.value = false
  importOpen.value = false
  importText.value = ''
  suiteEditing.value = true
  suiteEditingId.value = value?.id || ''
  Object.assign(suiteForm, {
    name: value?.name || '',
    description: value?.description || ''
  })
  suiteBaseline.value = JSON.stringify(suiteForm)
  suiteFormError.value = ''
}
async function closeSuite() {
  if (await discard()) suiteEditing.value = false
}
async function saveSuite() {
  if (!suiteForm.name.trim()) {
    suiteFormError.value = '请输入测试集名称。'
    return
  }
  const appId = props.application.id
  const result = await (suiteEditingId.value
    ? evaluation.updateSuite({
        name: suiteForm.name.trim(),
        description: suiteForm.description
      })
    : evaluation.createSuite({
        name: suiteForm.name.trim(),
        description: suiteForm.description
      }))
  if (result && props.application.id === appId) {
    suiteEditing.value = false
    suiteBaseline.value = JSON.stringify(suiteForm)
  }
}
async function changeSuite(event) {
  if (!(await discard())) {
    event.target.value = evaluation.suiteId
    return
  }
  suiteEditing.value = false
  caseEditing.value = false
  caseDirty.value = false
  evaluation.suiteId = event.target.value
  casePage.value = 1
}
async function openCase(value = null, fromSeed = false) {
  if (!(await discard())) return
  suiteEditing.value = false
  importOpen.value = false
  importText.value = ''
  editingCase.value = value
  seedSnapshot.value = fromSeed
    ? JSON.parse(JSON.stringify(props.seedRequest))
    : null
  editorSeed.value = fromSeed
    ? JSON.parse(JSON.stringify(props.seedRequest.inputData))
    : null
  caseEditorKey.value++
  caseEditing.value = true
  caseDirty.value = false
}
async function closeCase() {
  if (await discard()) {
    caseEditing.value = false
    caseDirty.value = false
  }
}
async function saveCase(payload) {
  const appId = props.application.id,
    seed = seedSnapshot.value
  const data = { ...payload }
  if (seed?.id && sameEvaluationInput(seed.inputData, payload.input_data)) {
    delete data.input_data
    data.from_request_id = seed.id
  }
  const saved = await evaluation.saveCase(editingCase.value?.id, data)
  if (!saved || props.application.id !== appId) return
  if (seed && sameEvaluationInput(saved.inputData, seed.inputData))
    emit('case-saved', saved.inputData)
  caseEditing.value = false
  caseDirty.value = false
  seedSnapshot.value = null
}
async function toggleCase(row) {
  if (!(await discard())) return
  caseEditing.value = false
  caseDirty.value = false
  await evaluation.saveCase(row.id, { enabled: !row.enabled })
}
async function deleteCase(row) {
  if (!(await discard())) return
  if (
    await app.confirm({
      title: '删除此用例？',
      message: '历史批次保留原快照，当前测试集修订将变化。',
      confirmText: '删除用例',
      cancelText: '保留用例',
      confirmType: 'danger'
    })
  ) {
    caseEditing.value = false
    caseDirty.value = false
    await evaluation.removeCase(row.id)
  }
}
async function deleteSuite() {
  if (!(await discard())) return
  if (
    await app.confirm({
      title: '删除此测试集？',
      message:
        '历史批次保留；发布门禁或在途批次关联的测试集会由服务端拒绝删除。',
      confirmText: '删除测试集',
      cancelText: '保留测试集',
      confirmType: 'danger'
    })
  ) {
    suiteEditing.value = false
    caseEditing.value = false
    caseDirty.value = false
    await evaluation.removeSuite()
  }
}
async function toggleImport() {
  const open = !importOpen.value
  if (!(await discard())) return
  importOpen.value = open
  importText.value = ''
  importError.value = ''
  suiteEditing.value = false
  caseEditing.value = false
  caseDirty.value = false
}
async function readImportFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (file.size > CONFIG.maxImportBytes) {
    importError.value = '文件超过 2 MiB，请缩小测试集后导入。'
    return
  }
  const appId = props.application.id
  try {
    const text = await new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(new Error('无法读取文件。'))
      reader.readAsText(file)
    })
    if (props.application.id === appId) {
      importText.value = text
      importError.value = ''
    }
  } catch (error) {
    importError.value = error.message
  }
}
async function importSuite() {
  try {
    if (
      new TextEncoder().encode(importText.value).length > CONFIG.maxImportBytes
    )
      throw new Error('导入 JSON 超过 2 MiB。')
    const artifact = parseEvaluationJson(importText.value, '测试集')
    if (
      artifact?.type !== 'flowly_application_test_suite' ||
      artifact.schema_version !== 1 ||
      !Array.isArray(artifact.cases)
    )
      throw new Error('请使用支持的 Flowly 应用测试集导出格式。')
    importError.value = ''
    const result = await evaluation.importSuite(artifact)
    if (result) {
      importText.value = ''
      importOpen.value = false
    }
  } catch (error) {
    importError.value = error.message
  }
}
async function exportSuite() {
  if (!evaluation.suiteId || exporting.value) return
  const appId = props.application.id,
    suiteId = evaluation.suiteId
  exporting.value = true
  let url
  try {
    const blob = await api.exportSuite(appId, suiteId)
    if (!(blob instanceof Blob))
      throw new Error('服务端未返回可下载的测试集文件。')
    if (props.application.id !== appId) return
    url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `application-tests-${suiteId}.json`
    document.body.append(anchor)
    anchor.click()
    anchor.remove()
    evaluation.notice('已开始下载测试集 JSON，请在浏览器下载记录中查看。')
  } catch (error) {
    evaluation.notice(error.message || '导出失败，请重试。', true)
  } finally {
    if (url) URL.revokeObjectURL(url)
    exporting.value = false
  }
}
function chooseBaseline(run) {
  evaluation.baseline = run
  evaluation.comparison = null
  evaluation.compareError = ''
}
async function saveGate() {
  const selected = gateValue.value
  if (await evaluation.saveGate(selected)) gateBaseline.value = selected
}
watch(
  () => props.application.requiredEvaluationSuiteId,
  (value) => {
    if (!gateDirty.value) {
      gateValue.value = value || ''
      gateBaseline.value = value || ''
    }
  },
  { immediate: true }
)
watch(
  () => props.application.id,
  () => {
    suiteEditing.value = false
    caseEditing.value = false
    caseDirty.value = false
    importOpen.value = false
    importText.value = ''
    gateValue.value = props.application.requiredEvaluationSuiteId || ''
    gateBaseline.value = gateValue.value
    casePage.value = 1
  }
)
watch(
  () => evaluation.cases.length,
  () => {
    casePage.value = Math.min(casePage.value, casePages.value)
  }
)
watch(
  () =>
    editorDirty.value ||
    evaluation.recoverable ||
    evaluation.writeUncertain ||
    Boolean(evaluation.mutation),
  (value) => emit('dirty', value),
  { immediate: true }
)
watch(
  () => Boolean(evaluation.mutation),
  (value) => emit('busy', value),
  { immediate: true }
)
onBeforeUnmount(() => {
  emit('dirty', false)
  emit('busy', false)
})
</script>

<style scoped>
.application-evaluations {
  min-width: 0;
}
.evaluation-section + .evaluation-section {
  margin-top: var(--delivery-space-2xl);
  padding-top: var(--delivery-space-xl);
  border-top: 1px solid var(--delivery-border);
}
.evaluation-controls {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: var(--delivery-space-lg);
  margin-bottom: var(--delivery-space-lg);
}
.evaluation-controls > .delivery-field {
  flex: 1 1 var(--content-filter-width);
  min-width: min(100%, var(--content-filter-width));
}
.evaluation-import {
  margin-block: var(--delivery-space-xl);
}
.evaluation-input-preview {
  max-width: 40ch;
  white-space: normal;
  overflow-wrap: anywhere;
  font-family: var(--font-family-mono);
}
.evaluation-history-filter {
  max-width: var(--content-search-width);
}
.application-evaluations textarea {
  font-family: var(--font-family-mono);
}
</style>
