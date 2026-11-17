<template>
  <section
    class="delivery-trace"
    aria-label="请求详情"
  >
    <div class="delivery-section-heading">
      <div>
        <span class="delivery-eyebrow">
          REQUEST TRACE
        </span>
        <h3>
          请求详情
        </h3>
      </div>
      <button
        type="button"
        class="delivery-button"
        @click="copy"
      >
        复制结果 JSON
      </button>
      <button
        v-if="canSaveCase"
        type="button"
        class="delivery-button"
        @click="$emit('save-case', request)"
      >
        存为测试用例
      </button>
    </div>
    <p
      v-if="copyFeedback"
      role="status"
      class="delivery-hint"
    >
      {{ copyFeedback }}
    </p>
    <dl class="delivery-facts">
      <div>
        <dt>
          请求 ID
        </dt>
        <dd class="delivery-mono">
          {{ request.id }}
        </dd>
      </div>
      <div>
        <dt>
          状态
        </dt>
        <dd>
          <span
            class="delivery-state"
            :data-status="request.status"
          >
            {{ APPLICATIONS.requestStatuses[request.status] || request.status }}
          </span>
        </dd>
      </div>
      <div>
        <dt>
          调用方式
        </dt>
        <dd>
          {{ APPLICATIONS.requestModes[request.mode] || request.mode }}
        </dd>
      </div>
      <div>
        <dt>
          耗时
        </dt>
        <dd>
          {{ applicationUsage(request.latencyMs, ' ms') }}
        </dd>
      </div>
      <div>
        <dt>
          Token 用量
        </dt>
        <dd>
          {{ applicationUsage(request.totalTokens) }}
        </dd>
      </div>
      <div>
        <dt>
          费用
        </dt>
        <dd>
          {{ request.cost === null || request.cost === undefined ? '未提供' : `${request.cost} ${request.currency || ''}` }}
        </dd>
      </div>
      <div>
        <dt>
          发布版本 ID
        </dt>
        <dd class="delivery-mono">
          {{ request.releaseId || '草稿' }}
        </dd>
      </div>
      <div>
        <dt>
          发起时间
        </dt>
        <dd>
          {{ applicationDate(request.createdAt) }}
        </dd>
      </div>
    </dl>
    <div
      v-if="request.errorMessage || request.errorCode"
      class="delivery-feedback delivery-feedback--error"
      role="alert"
    >
      <strong>
        {{ request.errorCode || '执行失败' }}
      </strong>
      <p>
        {{ request.errorMessage }}
      </p>
    </div>
    <ApplicationWorkflowTrace
      v-if="request.workflowExecutionId"
      :request="request"
    />
    <div class="delivery-trace-data">
      <div>
        <h4>
          输入
        </h4>
        <pre tabindex="0">{{ format(request.inputData) }}</pre>
      </div>
      <div>
        <h4>
          输出
        </h4>
        <pre tabindex="0">{{ format(request.outputData) }}</pre>
      </div>
    </div>
    <p class="delivery-hint">
      用量与费用仅展示服务返回的可归因数据；未提供时不计为 0。
    </p>
  </section>
</template>

<script setup>
import {
  ref
} from 'vue'
import ApplicationWorkflowTrace from './ApplicationWorkflowTrace.vue'
import {
  APPLICATIONS,
  applicationDate,
  applicationUsage
} from '@/config/applications'
const props = defineProps({
  request: {
    type: Object,
    required: true
  },
  canSaveCase: Boolean
})
defineEmits(['save-case'])
const copyFeedback = ref('')
const format = value => JSON.stringify(value ?? null, null, 2)
async function copy() {
  try {
    await navigator.clipboard.writeText(format(props.request.outputData));
    copyFeedback.value = '结果已复制。'
  } catch {
    copyFeedback.value = '无法访问剪贴板，请直接选择结果复制。'
  }
}
</script>

