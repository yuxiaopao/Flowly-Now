<template>
  <section
    class="evaluation-run"
    aria-label="回归批次详情"
  >
    <div class="delivery-section-heading">
      <div>
        <span class="delivery-eyebrow">EVALUATION RUN</span>
        <h3>{{ run.suiteName }} · 修订 {{ run.suiteRevision }}</h3>
      </div>
      <div class="delivery-actions">
        <button
          type="button"
          class="delivery-button"
          :disabled="loading"
          @click="$emit('refresh')"
        >
          刷新批次
        </button>
        <button
          v-if="canEdit && active"
          type="button"
          class="delivery-button"
          data-testid="evaluation-cancel"
          :disabled="busy || run.status === 'cancelling'"
          @click="$emit('cancel')"
        >
          {{
            run.status === 'cancelling' ? '等待服务端确认取消…' : '请求取消批次'
          }}
        </button>
      </div>
    </div>
    <p class="delivery-mono evaluation-run-id">
      {{ run.id }}
    </p>
    <dl class="delivery-facts">
      <div>
        <dt>状态</dt>
        <dd
          role="status"
          data-testid="evaluation-run-status"
        >
          {{ CONFIG.runStatuses[run.status] || run.status }}
        </dd>
      </div>
      <div>
        <dt>目标</dt>
        <dd>
          {{
            run.target === 'release'
              ? `发布版本 v${run.releaseVersion ?? '—'}`
              : '草稿快照'
          }}
        </dd>
      </div>
      <div>
        <dt>通过 / 总用例</dt>
        <dd>{{ run.passed }} / {{ run.total }}</dd>
      </div>
      <div>
        <dt>通过率</dt>
        <dd>{{ evaluationPercent(run.passRate) }}</dd>
      </div>
      <div>
        <dt>未通过 / 执行错误 / 未执行</dt>
        <dd>{{ run.failed }} / {{ run.errors }} / {{ run.skipped }}</dd>
      </div>
      <div>
        <dt>创建时间</dt>
        <dd>{{ applicationDate(run.createdAt) }}</dd>
      </div>
      <div>
        <dt>开始时间</dt>
        <dd>{{ applicationDate(run.startedAt) }}</dd>
      </div>
      <div>
        <dt>完成时间</dt>
        <dd>{{ applicationDate(run.completedAt) }}</dd>
      </div>
    </dl>
    <p class="delivery-hint">
      {{
        run.runnerMode === 'eager'
          ? '本批次使用服务端同步测试模式；不表示生产 Worker 已配置。'
          : '本批次由服务端队列执行。排队状态不表示 Worker 已开始工作。'
      }}
    </p>
    <p
      v-if="active"
      class="delivery-hint"
    >
      取消需要服务端确认；在途第三方调用及已经发生的外部操作无法撤回。离开页面不会停止批次。
    </p>
    <p
      v-if="run.isStale"
      class="delivery-feedback"
    >
      该结果已过期：测试集、目标配置或知识内容已变化，不能作为当前发布回归依据。
    </p>
    <p
      v-if="run.corpusChanged"
      class="delivery-feedback"
    >
      运行期间知识内容发生变化，结果不能直接归因于版本差异。
    </p>
    <div
      v-if="run.errorMessage"
      role="alert"
      class="delivery-feedback delivery-feedback--error"
    >
      <strong>{{ run.errorCode }}</strong>
      <p>
        {{ run.errorMessage }}
      </p>
    </div>
    <div class="delivery-table-wrap">
      <table class="delivery-table">
        <thead>
          <tr>
            <th>用例</th>
            <th>真实状态</th>
            <th>耗时</th>
            <th>证据与断言</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in run.results || []"
            :key="row.id"
            :data-testid="`evaluation-result-${row.caseIdSnapshot}`"
          >
            <td>{{ row.caseName }}</td>
            <td>
              {{ CONFIG.caseStatuses[row.status] || row.status }}
              <small v-if="row.errorMessage">
                {{ row.errorCode }} · {{ row.errorMessage }}
              </small>
            </td>
            <td>{{ applicationUsage(row.latencyMs, ' ms') }}</td>
            <td>
              <button
                v-if="row.requestId"
                type="button"
                class="delivery-link"
                @click="$emit('request', row.requestId)"
              >
                查看真实请求
              </button>
              <span
                v-else
                class="delivery-hint"
              >
                尚无执行请求
              </span>
              <details v-if="row.assertionResults?.length">
                <summary>
                  查看 {{ row.assertionResults.length }} 条断言结果
                </summary>
                <ol class="evaluation-assertion-results">
                  <li
                    v-for="(result, index) in row.assertionResults"
                    :key="index"
                  >
                    <strong>
                      {{ result.passed ? '通过' : '未通过' }} ·
                      {{ assertionLabel(result.type) }}
                    </strong>
                    <span>
                      {{ result.path || '根对象 / 此检查不使用路径' }}
                    </span>
                    <span>{{ result.expectedTruncated ? '预期值过长，已截断（服务端摘要）' : '预期 JSON' }}</span>
                    <pre tabindex="0">{{
                      result.expectedDisplay ?? JSON.stringify(result.expected, null, 2)
                    }}</pre>
                    <span>实际值（服务端摘要）</span>
                    <pre tabindex="0">{{ result.actual }}</pre>
                  </li>
                </ol>
              </details>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p
      v-if="!run.results?.length"
      class="delivery-empty"
    >
      批次暂无用例结果，请刷新服务端状态。
    </p>
    <section
      class="evaluation-comparison"
      aria-label="批次比较"
    >
      <div class="delivery-section-heading">
        <h4>与历史批次比较</h4>
        <button
          type="button"
          class="delivery-button"
          data-testid="evaluation-compare"
          :disabled="!baseline || active || comparing || baseline.id === run.id || baseline.suiteId !== run.suiteId"
          @click="$emit('compare')"
        >
          {{ comparing ? '正在比较…' : '比较两个批次' }}
        </button>
      </div>
      <p class="delivery-hint">
        {{
          baseline
            ? `比较基线：${baseline.id} · ${baseline.suiteName}`
            : '在历史表中为同一测试集选择一个已结束的批次作为基线。'
        }}
      </p>
      <p
        v-if="compareError"
        role="alert"
        class="delivery-feedback delivery-feedback--error"
      >
        {{ compareError }}
      </p>
      <template v-if="comparison">
        <p
          v-if="comparison.warning"
          class="delivery-feedback"
        >
          {{ comparison.warning }}
        </p>
        <div class="delivery-table-wrap">
          <table class="delivery-table">
            <thead>
              <tr>
                <th>用例</th>
                <th>基线状态</th>
                <th>本次状态</th>
                <th>服务端比较结论</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in comparison.results"
                :key="row.caseId"
              >
                <td>{{ row.name }}</td>
                <td>
                  {{ CONFIG.caseStatuses[row.baselineStatus] || row.baselineStatus || '无此用例' }}
                </td>
                <td>
                  {{ CONFIG.caseStatuses[row.currentStatus] || row.currentStatus || '无此用例' }}
                </td>
                <td>{{ CONFIG.changes[row.change] || row.change }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="delivery-hint">
          新增、移除或修改的用例与不可归因结果不被包装成版本进步或退步。
        </p>
      </template>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import {
  APPLICATION_EVALUATIONS as CONFIG,
  evaluationPercent
} from '@/config/applicationEvaluations'
import { applicationDate, applicationUsage } from '@/config/applications'
const props = defineProps({
  run: { type: Object, required: true },
  baseline: { type: Object, default: null },
  comparison: { type: Object, default: null },
  compareError: { type: String, default: '' },
  canEdit: Boolean,
  busy: Boolean,
  loading: Boolean,
  comparing: Boolean
})
defineEmits(['refresh', 'cancel', 'compare', 'request'])
const active = computed(() => CONFIG.activeStatuses.includes(props.run.status))
const assertionLabel = (type) =>
  CONFIG.assertionTypes.find((item) => item.value === type)?.label || type
</script>

<style scoped>
.evaluation-run {
  margin-top: var(--delivery-space-2xl);
  border-top: 1px solid var(--delivery-border);
  padding-top: var(--delivery-space-xl);
}
.evaluation-run-id {
  color: var(--delivery-muted);
  overflow-wrap: anywhere;
  margin-bottom: var(--delivery-space-lg);
}
.evaluation-assertion-results {
  margin: var(--delivery-space-md) 0;
  padding-left: var(--delivery-space-lg);
}
.evaluation-assertion-results li {
  display: grid;
  gap: var(--delivery-space-sm);
  margin-bottom: var(--delivery-space-lg);
  font-size: 0.75rem;
}
.evaluation-assertion-results pre {
  max-height: var(--application-code-max-height);
  padding: var(--delivery-space-md);
  background: var(--delivery-surface);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  overflow: auto;
}
.evaluation-comparison {
  margin-top: var(--delivery-space-xl);
}
</style>
