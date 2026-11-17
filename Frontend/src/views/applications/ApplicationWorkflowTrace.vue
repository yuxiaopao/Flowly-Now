<template>
  <section
    class="application-workflow-trace"
    aria-label="应用工作流执行追踪"
  >
    <button
      type="button"
      class="delivery-link"
      data-testid="application-workflow-trace-toggle"
      :disabled="!hasScope"
      :aria-expanded="opened"
      :aria-controls="panelId"
      @click="toggle"
    >
      {{ opened ? '收起工作流执行详情' : '查看工作流执行详情' }}
    </button>
    <p
      v-if="!hasScope"
      class="delivery-hint"
    >
      请求标识不完整，请重新加载请求详情后查看执行概要。
    </p>
    <div
      v-if="opened"
      :id="panelId"
      :aria-busy="loading"
    >
      <p class="delivery-hint">
        此处展示主流程节点概要。主流程状态与应用请求状态分别记录；包含异步子流程时，最终结果以应用请求日志为准。
      </p>
      <p
        v-if="loading"
        role="status"
        class="delivery-hint"
      >
        正在加载工作流执行概要…
      </p>
      <div
        v-else-if="error"
        role="alert"
        class="delivery-feedback delivery-feedback--error"
      >
        <p>{{ error }}</p>
        <button
          type="button"
          class="delivery-link"
          data-testid="application-workflow-trace-retry"
          @click="load"
        >
          重试执行概要
        </button>
      </div>
      <template v-else-if="trace">
        <div class="delivery-section-heading">
          <h4>主流程执行状态</h4>
          <button
            type="button"
            class="delivery-button"
            data-testid="application-workflow-trace-refresh"
            @click="load"
          >
            刷新执行概要
          </button>
        </div>
        <dl class="delivery-facts">
          <div>
            <dt>主流程执行 ID</dt>
            <dd class="delivery-mono">
              {{ trace.id }}
            </dd>
          </div>
          <div>
            <dt>主流程状态</dt>
            <dd data-testid="application-workflow-trace-status">
              {{ statusLabel(trace.status) }}
            </dd>
          </div>
          <div>
            <dt>开始时间</dt>
            <dd>{{ applicationDate(trace.startedAt) }}</dd>
          </div>
          <div>
            <dt>完成时间</dt>
            <dd>{{ applicationDate(trace.completedAt) }}</dd>
          </div>
        </dl>
        <div class="delivery-table-wrap">
          <table
            class="delivery-table"
            aria-label="主流程节点状态"
          >
            <thead>
              <tr>
                <th>节点</th><th>类型</th><th>状态</th><th>开始 / 完成</th><th>错误</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="node in trace.nodes"
                :key="node.nodeId"
              >
                <td>
                  {{ node.nodeName || node.nodeId }}
                  <small class="delivery-mono">{{ node.nodeId }}</small>
                </td>
                <td>{{ node.nodeType || '未记录' }}</td>
                <td>{{ statusLabel(node.status) }}</td>
                <td>{{ applicationDate(node.startedAt) }} / {{ applicationDate(node.completedAt) }}</td>
                <td>{{ node.errorMessage || '无' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p
          v-if="!trace.nodes.length"
          class="delivery-empty"
        >
          尚未记录主流程节点执行状态，可刷新查看。
        </p>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
import { applicationsApi } from '@/api/applications'
import { applicationDate } from '@/config/applications'
import { APPLICATION_WORKFLOW_TRACE } from '@/config/applicationWorkflowTrace'

const props = defineProps({ request: { type: Object, required: true } })
const opened = ref(false), loading = ref(false), error = ref(''), trace = ref(null)
const panelId = useId()
const hasScope = computed(() => Boolean(props.request.applicationId && props.request.id && props.request.workflowExecutionId))
const statusLabel = status => APPLICATION_WORKFLOW_TRACE.statuses[status] || status
let revision = 0, controller, disposed = false
function reset() {
  revision++
  controller?.abort()
  controller = null
  loading.value = false
  error.value = ''
  trace.value = null
}
async function load() {
  if (!hasScope.value || !opened.value || loading.value || disposed) return
  const current = ++revision, applicationId = props.request.applicationId, requestId = props.request.id
  controller = new AbortController()
  loading.value = true
  error.value = ''
  trace.value = null
  try {
    const result = await applicationsApi.requestExecution(applicationId, requestId, { signal: controller.signal })
    if (!disposed && current === revision) trace.value = result
  } catch (failure) {
    if (!disposed && current === revision && failure.code !== 'ERR_CANCELED') {
      error.value = failure.response?.status === 403 ? '无权查看该应用请求的执行概要，请确认当前账号权限。'
        : failure.response?.status === 404 ? '该请求尚无可访问的工作流执行记录，请刷新请求详情后重试。'
          : failure.message || '工作流执行概要加载失败，请重试。'
    }
  } finally {
    if (!disposed && current === revision) loading.value = false
  }
}
function toggle() {
  opened.value = !opened.value
  if (opened.value) load()
  else reset()
}
watch(() => [props.request.applicationId, props.request.id, props.request.workflowExecutionId], () => {
  reset()
  opened.value = false
})
onBeforeUnmount(() => {
  disposed = true
  reset()
})
</script>

<style scoped>
.application-workflow-trace { min-width: 0; margin-block: var(--delivery-space-lg); }
.application-workflow-trace > div { margin-top: var(--delivery-space-lg); }
.application-workflow-trace td { overflow-wrap: anywhere; }
.application-workflow-trace small { display: block; color: var(--delivery-muted); }
</style>
