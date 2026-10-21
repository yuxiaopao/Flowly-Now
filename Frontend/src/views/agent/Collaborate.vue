<template>
  <PageShell width="wide">
    <PageHeader
      title="多智能体协作"
      meta="Planner → Executor → Critic → Reporter 编排真实任务"
    >
      <template #actions>
        <AppButton
          variant="secondary"
          @click="showHistory = true"
        >
          <History class="btn-icon" />
          协作历史
        </AppButton>
      </template>
    </PageHeader>

    <div class="collab-layout">
      <!-- 左侧：任务与角色配置 -->
      <section class="config-panel">
        <div class="panel-block">
          <h4 class="block-title">
            任务描述
          </h4>
          <el-input
            v-model="task"
            type="textarea"
            :rows="4"
            placeholder="请描述需要多智能体协作完成的复杂任务，例如：调研并总结团队知识库中关于XX主题的资料，形成一份结构化报告"
            :disabled="isRunning"
          />
        </div>

        <div class="panel-block">
          <h4 class="block-title">
            所属团队（可选）
          </h4>
          <el-select
            v-model="tenantId"
            placeholder="不选则为个人协作"
            clearable
            class="full-width"
            :disabled="isRunning"
          >
            <el-option
              v-for="t in tenantStore.tenants"
              :key="t.id"
              :label="t.name"
              :value="String(t.id)"
            />
          </el-select>
          <p class="block-tip">
            选择团队后，可绑定该团队共享的 Agent（含其关联知识库），协作记录也将对团队成员可见。
          </p>
        </div>

        <div class="panel-block">
          <div class="block-title-row">
            <h4 class="block-title">
              角色配置
            </h4>
            <span class="role-count">{{ enabledRoles.length }} / 4 个角色</span>
          </div>

          <div
            v-for="roleDef in ROLE_DEFS"
            :key="roleDef.role"
            class="role-card"
            :class="{ 'role-card--disabled': !roleStates[roleDef.role].enabled }"
          >
            <div class="role-card-header">
              <el-checkbox
                v-model="roleStates[roleDef.role].enabled"
                :disabled="isRunning"
              />
              <component
                :is="roleDef.icon"
                class="role-icon"
                :style="{ color: roleDef.color }"
              />
              <span class="role-name">{{ roleDef.label }}</span>
            </div>

            <div
              v-if="roleStates[roleDef.role].enabled"
              class="role-card-body"
            >
              <el-select
                v-model="roleStates[roleDef.role].agentId"
                placeholder="使用默认角色设定（无需绑定 Agent）"
                clearable
                class="full-width"
                :disabled="isRunning"
              >
                <el-option
                  v-for="a in availableAgents"
                  :key="a.id"
                  :label="a.name"
                  :value="a.id"
                >
                  <span>{{ a.name }}</span>
                  <span
                    v-if="a.knowledge_collections?.length"
                    class="agent-option-kb"
                  > · 知识库x{{ a.knowledge_collections.length }}</span>
                </el-option>
              </el-select>
              <p class="role-hint">
                {{ roleStates[roleDef.role].agentId ? '将继承该 Agent 的系统提示词、模型与知识库' : roleDef.defaultHint }}
              </p>
            </div>
          </div>
        </div>

        <AppButton
          variant="primary"
          class="run-btn"
          :loading="isRunning"
          :disabled="!canRun"
          @click="handleRun"
        >
          <Play class="btn-icon" />
          {{ isRunning ? '协作执行中...' : '发起协作任务' }}
        </AppButton>
      </section>

      <!-- 右侧：执行轨迹与报告 -->
      <section class="trace-panel">
        <div
          v-if="!currentRun && !isRunning"
          class="trace-empty"
        >
          <Workflow class="empty-icon" />
          <p>配置任务与角色后，点击"发起协作任务"查看实时执行轨迹</p>
        </div>

        <template v-else>
          <div
            v-if="currentRun"
            class="trace-status"
          >
            <el-tag :type="statusTagType(currentRun.status)">
              {{ statusLabel(currentRun.status) }}
            </el-tag>
            <span class="trace-task">{{ currentRun.task }}</span>
          </div>

          <div
            v-if="isRunning"
            class="trace-running"
          >
            <el-skeleton
              :rows="4"
              animated
            />
            <p class="running-hint">
              正在依次调用 Planner → Executor → Critic → Reporter，可能需要数十秒（本地模型推理中）...
            </p>
          </div>

          <div
            v-else-if="currentRun"
            class="trace-steps"
          >
            <div
              v-for="(step, idx) in currentRun.trace"
              :key="idx"
              class="trace-step"
            >
              <div class="step-marker">
                <component
                  :is="phaseIcon(step.phase)"
                  class="step-icon"
                />
                <div
                  v-if="idx < currentRun.trace.length - 1"
                  class="step-line"
                />
              </div>
              <div class="step-content">
                <div class="step-header">
                  <span class="step-agent">{{ step.agent }}</span>
                  <span class="step-time">{{ formatTime(step.timestamp) }}</span>
                </div>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div
                  v-if="step.phase === 'report'"
                  class="step-markdown markdown-body"
                  v-html="renderStepMarkdown(step.content)"
                />
                <pre
                  v-else
                  class="step-text"
                >{{ step.content }}</pre>
              </div>
            </div>

            <div
              v-if="currentRun.error_message"
              class="trace-error"
            >
              <AlertTriangle class="error-icon" />
              {{ currentRun.error_message }}
            </div>

            <div
              v-if="resolveFinalReport(currentRun)"
              class="final-report"
            >
              <div class="report-header">
                <h4 class="block-title">
                  <FileCheck class="report-icon" />最终报告
                </h4>
                <el-button
                  text
                  size="small"
                  @click="copyFinalReport"
                >
                  <Copy class="btn-icon-sm" />
                  复制
                </el-button>
              </div>
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div
                class="report-markdown markdown-body"
                v-html="finalReportHtml"
              />
            </div>
          </div>
        </template>
      </section>
    </div>

    <!-- 历史记录抽屉 -->
    <el-drawer
      v-model="showHistory"
      title="协作历史记录"
      size="480px"
    >
      <div
        v-if="historyLoading"
        class="history-loading"
      >
        <el-skeleton
          :rows="4"
          animated
        />
      </div>
      <div
        v-else-if="historyList.length === 0"
        class="no-history"
      >
        暂无协作记录
      </div>
      <div
        v-else
        class="history-list"
      >
        <div
          v-for="run in historyList"
          :key="run.id"
          class="history-item"
          @click="viewHistoryRun(run)"
        >
          <div class="history-item-main">
            <span class="history-task">{{ run.task }}</span>
            <el-tag
              size="small"
              :type="statusTagType(run.status)"
            >
              {{ statusLabel(run.status) }}
            </el-tag>
          </div>
          <div class="history-item-meta">
            <span v-if="run.tenant_name">
              <Users class="meta-icon" />{{ run.tenant_name }}
            </span>
            <span>{{ formatDate(run.started_at) }}</span>
          </div>
          <p
            v-if="run.report_preview"
            class="history-preview"
          >
            {{ run.report_preview }}
          </p>
          <el-button
            text
            size="small"
            class="history-delete"
            @click.stop="handleDeleteRun(run)"
          >
            <Trash2 class="meta-icon" />
          </el-button>
        </div>
      </div>
    </el-drawer>
  </PageShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  History, Play, Workflow, ListTree, Hammer, ShieldCheck, FileText,
  AlertTriangle, FileCheck, Users, Trash2, Copy
} from 'lucide-vue-next'
import { agentApi } from '@/api/agent'
import { useTenantStore } from '@/stores/tenant'
import { useAppStore } from '@/stores/app'
import { renderMarkdown } from '@/utils/markdown'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import AppButton from '@/components/common/AppButton.vue'

const tenantStore = useTenantStore()
const appStore = useAppStore()

const ROLE_DEFS = [
  { role: 'planner', label: 'Planner（规划者）', icon: ListTree, color: '#6366f1', defaultHint: '将任务拆解为可执行步骤' },
  { role: 'executor', label: 'Executor（执行者）', icon: Hammer, color: '#f59e0b', defaultHint: '按计划执行并给出结果（可调用知识库检索）' },
  { role: 'critic', label: 'Critic（审查者）', icon: ShieldCheck, color: '#ef4444', defaultHint: '审查执行结果是否满足要求' },
  { role: 'reporter', label: 'Reporter（报告者）', icon: FileText, color: '#10b981', defaultHint: '整理各阶段结果为最终报告' },
]

const task = ref('')
const tenantId = ref('')
const isRunning = ref(false)
const currentRun = ref(null)
const allAgents = ref([])

const showHistory = ref(false)
const historyLoading = ref(false)
const historyList = ref([])

const roleStates = reactive({
  planner: { enabled: true, agentId: '' },
  executor: { enabled: true, agentId: '' },
  critic: { enabled: true, agentId: '' },
  reporter: { enabled: true, agentId: '' },
})

const enabledRoles = computed(() => ROLE_DEFS.filter(r => roleStates[r.role].enabled))

const availableAgents = computed(() => {
  if (!tenantId.value) {
    return allAgents.value.filter(a => !a.tenant)
  }
  return allAgents.value.filter(a => String(a.tenant || '') === tenantId.value || !a.tenant)
})

const canRun = computed(() => {
  return task.value.trim().length > 0 &&
    enabledRoles.value.length > 0 &&
    (roleStates.planner.enabled || roleStates.executor.enabled) &&
    !isRunning.value
})

const finalReportHtml = computed(() => renderMarkdown(resolveFinalReport(currentRun.value)))

function renderStepMarkdown(content) {
  return renderMarkdown(content)
}

onMounted(async () => {
  tenantStore.fetchTenants()
  try {
    const res = await agentApi.getList({ page_size: 200 })
    allAgents.value = res.results || res
  } catch {
    allAgents.value = []
  }
})

const TRACE_REPORT_PHASES = ['report', 'review', 'execution', 'planning']

function resolveFinalReport(run) {
  if (!run) return ''
  const direct = (run.final_report || '').trim()
  if (direct) return direct
  for (const phase of TRACE_REPORT_PHASES) {
    const step = (run.trace || []).find(s => s.phase === phase)
    const content = (step?.content || '').trim()
    if (content) return content
  }
  return ''
}

async function copyFinalReport() {
  const text = resolveFinalReport(currentRun.value)
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    appStore.success('报告已复制到剪贴板')
  } catch {
    appStore.error('复制失败')
  }
}

function phaseIcon(phase) {
  const map = {
    planning: ListTree,
    execution: Hammer,
    review: ShieldCheck,
    report: FileText,
    error: AlertTriangle,
  }
  return map[phase] || Workflow
}

function statusTagType(status) {
  const map = { completed: 'success', failed: 'danger', running: 'warning', pending: 'info' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { completed: '已完成', failed: '失败', running: '执行中', pending: '待处理' }
  return map[status] || status
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

async function handleRun() {
  if (!canRun.value) return

  const roles = enabledRoles.value.map(r => {
    const state = roleStates[r.role]
    const payload = { role: r.role }
    if (state.agentId) payload.agent_id = state.agentId
    return payload
  })

  isRunning.value = true
  currentRun.value = null

  try {
    const payload = { task: task.value.trim(), roles }
    if (tenantId.value) payload.tenant = tenantId.value

    const result = await agentApi.runCollaboration(payload)
    currentRun.value = result

    if (result.status === 'completed') {
      appStore.success('协作任务已完成')
    } else {
      appStore.error(result.error_message || '协作任务执行失败')
    }
  } catch (err) {
    appStore.error(err?.response?.data?.error || err.message || '发起协作任务失败')
  } finally {
    isRunning.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await agentApi.getCollaborationList(tenantId.value ? { tenant: tenantId.value } : {})
    historyList.value = res.results || res
  } catch {
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

async function viewHistoryRun(run) {
  try {
    const detail = await agentApi.getCollaborationDetail(run.id)
    currentRun.value = detail
    showHistory.value = false
  } catch {
    appStore.error('加载协作详情失败')
  }
}

async function handleDeleteRun(run) {
  try {
    await ElMessageBox.confirm('确定要删除此协作记录吗？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await agentApi.deleteCollaboration(run.id)
    historyList.value = historyList.value.filter(r => r.id !== run.id)
    appStore.success('已删除')
  } catch (err) {
    if (err !== 'cancel') {
      appStore.error('删除失败')
    }
  }
}

// 打开历史抽屉时刷新列表
watch(showHistory, (val) => {
  if (val) loadHistory()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.btn-icon {
  width: 16px;
  height: 16px;
}

.full-width {
  width: 100%;
}

.collab-layout {
  display: grid;
  grid-template-columns: minmax(0, 380px) minmax(0, 1fr);
  gap: $spacing-6;
  align-items: start;
  @media (max-width: $breakpoint-lg) { grid-template-columns: minmax(0, 1fr); }
}

.config-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: $spacing-5;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-5;
}

.panel-block {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.block-title {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0;
}

.block-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.role-count {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.block-tip,
.role-hint {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin: 0;
}

.role-card {
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-3;
  margin-bottom: $spacing-2;
  transition: opacity 0.2s ease;

  &--disabled {
    opacity: 0.55;
  }
}

.role-card-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.role-icon {
  width: 16px;
  height: 16px;
}

.role-name {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
}

.role-card-body {
  margin-top: $spacing-2;
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.agent-option-kb {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.run-btn {
  width: 100%;
  justify-content: center;
}

.trace-panel {
  min-width: 0;
  min-height: 400px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-5;
}

.trace-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  text-align: center;
  color: var(--text-tertiary);

  .empty-icon {
    width: 56px;
    height: 56px;
    margin-bottom: $spacing-4;
    opacity: 0.6;
  }

  p {
    max-width: 320px;
  }
}

.trace-status {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding-bottom: $spacing-4;
  margin-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);
}

.trace-task {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-running {
  .running-hint {
    margin-top: $spacing-3;
    font-size: $font-size-xs;
    color: var(--text-tertiary);
    text-align: center;
  }
}

.trace-step {
  display: flex;
  gap: $spacing-3;
}

.step-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.step-icon {
  width: 28px;
  height: 28px;
  padding: 6px;
  border-radius: $radius-full;
  background-color: var(--bg-tertiary);
  color: $color-primary;
}

.step-line {
  flex: 1;
  width: 2px;
  min-height: 24px;
  background-color: var(--border-primary);
  margin: $spacing-1 0;
}

.step-content {
  flex: 1;
  padding-bottom: $spacing-5;
  min-width: 0;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-1;
}

.step-agent {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
}

.step-time {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.step-text {
  font-family: inherit;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: $spacing-3;
  border-radius: $radius-md;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
}

.trace-error {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3;
  background-color: rgba($color-error, 0.1);
  color: $color-error;
  border-radius: $radius-md;
  font-size: $font-size-sm;

  .error-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }
}

.final-report {
  margin-top: $spacing-4;
  padding-top: $spacing-4;
  border-top: 1px solid var(--border-primary);

  .report-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-2;
  }

  .report-icon {
    width: 16px;
    height: 16px;
    color: $color-success;
  }
}

.report-text {
  font-family: inherit;
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  color: var(--text-primary);
  background: linear-gradient(135deg, rgba($color-success, 0.06), rgba($color-primary, 0.04));
  padding: $spacing-4;
  border-radius: $radius-md;
  white-space: pre-wrap;
  word-break: break-word;
  margin: $spacing-2 0 0;
}

.report-markdown,
.step-markdown {
  font-size: $font-size-sm;
  line-height: $line-height-relaxed;
  color: var(--text-primary);
  background: linear-gradient(135deg, rgba($color-success, 0.06), rgba($color-primary, 0.04));
  padding: $spacing-4;
  border-radius: $radius-md;
  margin: $spacing-2 0 0;
  word-break: break-word;

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    margin: $spacing-2 0 $spacing-1;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }

  :deep(p) {
    margin: 0 0 $spacing-2;
  }

  :deep(ul), :deep(ol) {
    margin: 0 0 $spacing-2;
    padding-left: $spacing-5;
  }

  :deep(code) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: var(--bg-tertiary);
    padding: 0.1em 0.35em;
    border-radius: $radius-sm;
    font-size: 0.92em;
  }

  :deep(pre) {
    background: var(--bg-tertiary);
    padding: $spacing-3;
    border-radius: $radius-md;
    overflow-x: auto;
    margin: 0 0 $spacing-2;
  }

  :deep(blockquote) {
    margin: 0 0 $spacing-2;
    padding-left: $spacing-3;
    border-left: 3px solid rgba($color-primary, 0.35);
    color: var(--text-secondary);
  }
}

.step-markdown {
  background: var(--bg-tertiary);
  margin: 0;
}

.history-loading {
  padding: $spacing-4;
}

.no-history {
  text-align: center;
  padding: $spacing-8;
  color: var(--text-tertiary);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.history-item {
  position: relative;
  padding: $spacing-3;
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: var(--bg-hover);

    .history-delete {
      opacity: 1;
    }
  }
}

.history-item-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
}

.history-task {
  font-size: $font-size-sm;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.history-item-meta {
  display: flex;
  gap: $spacing-3;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  span {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.history-preview {
  margin: $spacing-2 0 0;
  font-size: $font-size-xs;
  line-height: $line-height-relaxed;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-icon {
  width: 12px;
  height: 12px;
}

.history-delete {
  position: absolute;
  top: $spacing-2;
  right: $spacing-2;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: var(--text-tertiary);

  &:hover {
    color: $color-error;
  }
}
</style>
