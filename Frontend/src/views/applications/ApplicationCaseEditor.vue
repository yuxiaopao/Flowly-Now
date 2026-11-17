<template>
  <form
    class="delivery-form evaluation-case-editor"
    aria-label="编辑回归用例"
    @submit.prevent="submit"
  >
    <div class="delivery-section-heading">
      <h3>{{ disabled ? '查看用例' : value ? '编辑用例' : '新增用例' }}</h3>
      <button
        type="button"
        class="delivery-button"
        :disabled="busy"
        @click="$emit('cancel')"
      >
        取消编辑
      </button>
    </div>
    <p class="delivery-hint">
      断言检查真实结果，不使用模型猜测评分。输入和 expected 的自定义键保持原样。
    </p>
    <div class="delivery-form-grid">
      <div class="delivery-field">
        <label :for="`${identity}-name`">用例名称</label>
        <input
          :id="`${identity}-name`"
          v-model="form.name"
          data-testid="evaluation-case-name"
          aria-label="用例名称"
          :maxlength="CONFIG.nameMaxLength"
          :disabled="busy || disabled"
          required
        >
      </div>
      <div class="delivery-field">
        <label :for="`${identity}-position`">排列位置</label>
        <input
          :id="`${identity}-position`"
          v-model.number="form.position"
          aria-label="用例排列位置"
          type="number"
          min="0"
          max="10000"
          :disabled="busy || disabled"
        >
      </div>
      <div class="delivery-field delivery-field--full">
        <label :for="`${identity}-input`">输入 JSON</label>
        <textarea
          :id="`${identity}-input`"
          v-model="form.inputText"
          data-testid="evaluation-case-input"
          aria-label="用例输入 JSON"
          rows="6"
          spellcheck="false"
          :disabled="busy || disabled"
        />
      </div>
    </div>
    <label class="evaluation-check">
      <input
        v-model="form.enabled"
        type="checkbox"
        :disabled="busy || disabled"
      >
      启用此用例，参与完整测试集评测
    </label>
    <div class="delivery-section-heading">
      <h4>断言</h4>
      <button
        type="button"
        class="delivery-button"
        :disabled="busy || disabled || form.assertions.length >= CONFIG.maxAssertions"
        @click="addAssertion"
      >
        添加断言
      </button>
    </div>
    <fieldset
      v-for="(row, index) in form.assertions"
      :key="row.identity"
      :disabled="busy || disabled"
      class="evaluation-assertion"
    >
      <legend>断言 {{ index + 1 }}</legend>
      <div class="delivery-form-grid">
        <div class="delivery-field">
          <label :for="`${identity}-type-${row.identity}`">检查方式</label>
          <select
            :id="`${identity}-type-${row.identity}`"
            v-model="row.type"
            :aria-label="`断言 ${index + 1} 类型`"
            data-testid="evaluation-assertion-type"
          >
            <option
              v-for="definition in CONFIG.assertionTypes"
              :key="definition.value"
              :value="definition.value"
            >
              {{ definition.label }}
            </option>
          </select>
        </div>
        <div
          v-if="assertionDefinition(row.type)?.pointer"
          class="delivery-field"
        >
          <label :for="`${identity}-path-${row.identity}`">输出字段路径</label>
          <input
            :id="`${identity}-path-${row.identity}`"
            v-model="row.path"
            :aria-label="`断言 ${index + 1} JSON Pointer`"
            data-testid="evaluation-assertion-path"
            placeholder="例如 /variables/result；留空表示根对象"
          >
        </div>
        <div class="delivery-field delivery-field--full">
          <label :for="`${identity}-expected-${row.identity}`">
            预期值 expected（JSON）
          </label>
          <textarea
            :id="`${identity}-expected-${row.identity}`"
            v-model="row.expectedText"
            :aria-label="`断言 ${index + 1} 预期 JSON`"
            data-testid="evaluation-assertion-expected"
            rows="3"
            spellcheck="false"
          />
          <p class="delivery-hint">
            {{ assertionDefinition(row.type)?.hint }}
          </p>
        </div>
      </div>
      <button
        type="button"
        class="delivery-link"
        :disabled="form.assertions.length <= 1"
        @click="form.assertions.splice(index, 1)"
      >
        移除此断言
      </button>
    </fieldset>
    <p class="delivery-hint">
      字段路径采用 JSON Pointer：斜杠写为 ~1，波浪号写为 ~0；数组元素使用
      /0、/1。文本预期值需要双引号，例如 "退款"。
    </p>
    <p
      v-if="error"
      role="alert"
      class="delivery-feedback delivery-feedback--error"
    >
      {{ error }}
    </p>
    <div class="delivery-actions">
      <button
        type="submit"
        class="delivery-button delivery-button--primary"
        data-testid="evaluation-case-save"
        :disabled="busy || disabled"
      >
        {{ busy ? '正在保存…' : '保存用例' }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, useId, watch } from 'vue'
import {
  APPLICATION_EVALUATIONS as CONFIG,
  parseEvaluationCase
} from '@/config/applicationEvaluations'
const props = defineProps({
  value: { type: Object, default: null },
  seedInput: { type: Object, default: null },
  busy: Boolean,
  disabled: Boolean
})
const emit = defineEmits(['save', 'cancel', 'dirty'])
const identity = useId()
const form = reactive({
  name: '',
  inputText: '{}',
  enabled: true,
  position: 0,
  assertions: []
})
const baseline = ref(''),
  error = ref('')
let sequence = 0
const source = computed(() => JSON.stringify(form))
const assertionDefinition = (type) =>
  CONFIG.assertionTypes.find((item) => item.value === type)
function assertion(row = {}) {
  return {
    identity: ++sequence,
    type: row.type || 'json_equals',
    path: row.path || '',
    expectedText: JSON.stringify(
      row.expected === undefined ? null : row.expected,
      null,
      2
    )
  }
}
function addAssertion() {
  form.assertions.push(assertion())
}
watch(
  () => [props.value, props.seedInput],
  () => {
    const value = props.value
    Object.assign(form, {
      name: value?.name || '',
      inputText: JSON.stringify(
        value?.inputData ?? props.seedInput ?? {},
        null,
        2
      ),
      enabled: value?.enabled ?? true,
      position: value?.position ?? 0,
      assertions: value?.assertions?.length
        ? value.assertions.map(assertion)
        : [assertion()]
    })
    error.value = ''
    baseline.value = source.value
  },
  { immediate: true }
)
watch(source, (value) => emit('dirty', value !== baseline.value), {
  immediate: true
})
function submit() {
  try {
    error.value = ''
    emit('save', parseEvaluationCase(form))
  } catch (failure) {
    error.value = failure.message
  }
}
onBeforeUnmount(() => emit('dirty', false))
</script>

<style scoped>
.evaluation-assertion {
  min-width: 0;
  margin: var(--delivery-space-lg) 0;
  padding: var(--delivery-space-lg);
  border: 1px solid var(--delivery-border);
  border-radius: var(--radius-md);
}
.evaluation-assertion legend {
  padding-inline: var(--delivery-space-sm);
  font-size: 0.8125rem;
  color: var(--delivery-muted);
}
.evaluation-check {
  display: flex;
  align-items: center;
  gap: var(--delivery-space-sm);
  margin-bottom: var(--delivery-space-xl);
  font-size: 0.8125rem;
}
.evaluation-case-editor textarea {
  font-family: var(--font-family-mono);
  overflow-wrap: anywhere;
}
</style>
