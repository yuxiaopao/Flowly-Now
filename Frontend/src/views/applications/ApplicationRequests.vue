<template>
  <section>
    <div class="delivery-section-heading">
      <div>
        <span class="delivery-eyebrow">
          OBSERVE
        </span>
        <h2>
          请求日志
        </h2>
        <p>
          草稿测试、发布 API 与回归评测都可追踪到具体请求。
        </p>
      </div>
      <button
        type="button"
        class="delivery-button"
        :disabled="history.loading.value"
        @click="history.load(history.page.value)"
      >
        刷新请求
      </button>
    </div>
    <form
      class="delivery-toolbar"
      aria-label="筛选请求"
      @submit.prevent="history.load(1)"
    >
      <select
        v-model="mode"
        aria-label="按调用方式筛选"
        @change="history.load(1)"
      >
        <option value="">
          全部调用方式
        </option>
        <option value="test">
          草稿测试
        </option>
        <option value="invoke">
          发布 API
        </option>
        <option value="evaluation">
          回归评测
        </option>
      </select>
      <select
        v-model="status"
        aria-label="按请求状态筛选"
        @change="history.load(1)"
      >
        <option value="">
          全部状态
        </option>
        <option
          v-for="(label, value) in APPLICATIONS.requestStatuses"
          :key="value"
          :value="value"
        >
          {{ label }}
        </option>
      </select>
    </form>
    <div
      v-if="history.error.value"
      class="delivery-feedback delivery-feedback--error"
      role="alert"
    >
      {{ history.error.value }}
      <button
        class="delivery-link"
        type="button"
        @click="history.load(history.page.value)"
      >
        重试请求列表
      </button>
    </div>
    <p
      v-else-if="history.loading.value"
      class="delivery-loading"
      role="status"
    >
      正在加载请求…
    </p>
    <p
      v-else-if="!history.rows.value.length"
      class="delivery-empty"
    >
      {{ mode || status ? '没有匹配的请求，请调整筛选条件。' : '尚无请求。运行一次草稿测试，或调用已发布的 API。' }}
    </p>
    <div
      v-else
      class="delivery-table-wrap"
    >
      <table class="delivery-table">
        <thead>
          <tr>
            <th>
              请求 / 时间
            </th>
            <th>
              方式
            </th>
            <th>
              状态
            </th>
            <th>
              耗时
            </th>
            <th>
              Token
            </th>
            <th>
              操作
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="request in history.rows.value"
            :key="request.id"
            :data-testid="`application-request-${request.id}`"
          >
            <td>
              <span class="delivery-mono">
                {{ request.id }}
              </span>
              <small>
                {{ applicationDate(request.createdAt) }}
              </small>
            </td>
            <td>
              {{ APPLICATIONS.requestModes[request.mode] || request.mode }}
            </td>
            <td>
              <span
                class="delivery-state"
                :data-status="request.status"
              >
                {{ APPLICATIONS.requestStatuses[request.status] || request.status }}
              </span>
            </td>
            <td>
              {{ applicationUsage(request.latencyMs, ' ms') }}
            </td>
            <td>
              {{ applicationUsage(request.totalTokens) }}
            </td>
            <td>
              <button
                class="delivery-button"
                type="button"
                :aria-label="`查看请求 ${request.id}`"
                @click="select(request)"
              >
                查看详情
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <nav
      v-if="history.pageCount.value > 1"
      class="delivery-pagination"
      aria-label="请求日志分页"
    >
      <span>
        共
        {{ history.count.value }}
        次 · 第
        {{ history.page.value }}
        /
        {{ history.pageCount.value }}
        页
      </span>
      <button
        type="button"
        class="delivery-button"
        :disabled="history.page.value <= 1 || history.loading.value"
        @click="history.load(history.page.value - 1)"
      >
        上一页
      </button>
      <button
        type="button"
        class="delivery-button"
        :disabled="history.page.value >= history.pageCount.value || history.loading.value"
        @click="history.load(history.page.value + 1)"
      >
        下一页
      </button>
    </nav>
    <p
      v-if="detailLoading"
      class="delivery-loading"
      role="status"
    >
      正在定位请求…
    </p>
    <div
      v-else-if="detailError"
      class="delivery-feedback delivery-feedback--error"
      role="alert"
    >
      {{ detailError }}
      <button
        type="button"
        class="delivery-link"
        @click="loadDetail(String(route.query.request || ''))"
      >
        重试请求详情
      </button>
    </div>
    <div
      v-else-if="selected"
      class="delivery-inline-details"
    >
      <div class="delivery-actions">
        <button
          type="button"
          class="delivery-button"
          @click="closeDetail"
        >
          收起请求详情
        </button>
      </div>
      <ApplicationRequestTrace
        :request="selected"
        :can-save-case="canEdit"
        @save-case="$emit('save-case', $event)"
      />
    </div>
  </section>
</template>

<script setup>
import {
  onBeforeUnmount,
  ref,
  watch
} from 'vue'
import {
  useRoute,
  useRouter
} from 'vue-router'
import {
  applicationsApi
} from '@/api/applications'
import {
  APPLICATIONS,
  applicationDate,
  applicationUsage
} from '@/config/applications'
import ApplicationRequestTrace from './ApplicationRequestTrace.vue'
import {
  useApplicationCollection
} from './useApplicationCollection'
const props = defineProps({
  applicationId: {
    type: String,
    required: true
  },
  revision: {
    type: Number,
    default: 0
  },
  canEdit: Boolean
})
defineEmits(['save-case'])
const route = useRoute()
const router = useRouter()
const mode = ref('')
const status = ref('')
const history = useApplicationCollection(params => applicationsApi.requests(props.applicationId, {
  ...params,
  mode: mode.value || undefined,
  status: status.value || undefined
}))
const selected = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
let detailRevision = 0
async function select(request) {
  selected.value = request
  await router.replace({
    query: {
      ...route.query,
      tab: 'requests',
      request: request.id
    }
  })
}
async function closeDetail() {
  const query = {
    ...route.query
  };
  delete query.request;
  await router.replace({
    query
  })
}
async function loadDetail(id) {
  const current = ++detailRevision
  selected.value = null
  detailError.value = ''
  detailLoading.value = Boolean(id)
  if (!id) return
  try {
    const result = await applicationsApi.request(props.applicationId, id)
    if (current === detailRevision) selected.value = result
  } catch (failure) {
    if (current === detailRevision) detailError.value = failure.message || '此请求不存在或无权读取。'
  } finally {
    if (current === detailRevision) detailLoading.value = false
  }
}
watch(() => [props.applicationId, props.revision], () => {
  history.reset();
  history.load()
}, {
  immediate: true
})
watch(() => [props.applicationId, route.query.request], () => loadDetail(String(route.query.request || '')), {
  immediate: true
})
onBeforeUnmount(() => {
  detailRevision++
})
</script>

