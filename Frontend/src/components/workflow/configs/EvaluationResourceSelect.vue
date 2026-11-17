<template>
  <div class="evaluation-resource">
    <el-select
      :model-value="modelValue"
      filterable
      remote
      clearable
      :remote-method="search"
      :loading="loading"
      :placeholder="`选择${definition.label}`"
      @update:model-value="$emit('update:modelValue', $event)"
    >
      <el-option
        v-if="modelValue && !rows.some(row => row.id === modelValue)"
        :value="modelValue"
        :label="`已保存 ID：${modelValue}（执行时校验权限）`"
      />
      <el-option
        v-for="row in rows"
        :key="row.id"
        :value="row.id"
        :label="row.name || row.id"
      />
    </el-select>
    <p
      v-if="error"
      role="alert"
    >
      {{ error }} <el-button
        link
        @click="load(false)"
      >
        重试
      </el-button>
    </p>
    <el-button
      v-if="hasMore"
      link
      :loading="loading"
      @click="load(true)"
    >
      加载更多{{ definition.label }}
    </el-button>
    <p v-if="!loading && !error && !rows.length">
      没有可选记录，可搜索名称或先创建资源。
    </p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import api from '@/api'
import { MODEL_EVALUATION } from '@/config/modelEvaluation'
import { authSession } from '@/utils/authSession'

const props = defineProps({ modelValue: { type: String, default: '' }, kind: { type: String, required: true } })
defineEmits(['update:modelValue'])
const definition = computed(() => MODEL_EVALUATION.resources[props.kind])
const rows = ref([]), loading = ref(false), error = ref(''), hasMore = ref(false)
let query = '', page = 1, revision = 0, controller
async function load(append) {
  controller?.abort()
  controller = new AbortController()
  const current = ++revision
  loading.value = true
  error.value = ''
  const requestedPage = append ? page + 1 : 1
  try {
    const result = await api.get(definition.value.endpoint, {
      params: { ...definition.value.params, search: query, page: requestedPage, page_size: MODEL_EVALUATION.pageSize },
      skipErrorToast: true, signal: controller.signal,
    })
    if (current !== revision) return
    const values = Array.isArray(result) ? result : result?.results
    if (!Array.isArray(values)) throw new Error('资源列表响应格式错误')
    rows.value = append ? [...new Map([...rows.value, ...values].map(row => [row.id, row])).values()] : values
    page = requestedPage
    hasMore.value = Boolean(result?.next)
  } catch (failure) {
    if (current === revision && failure.code !== 'ERR_CANCELED') error.value = failure.response?.data?.detail || failure.message || '资源加载失败'
  } finally { if (current === revision) loading.value = false }
}
function search(value) { query = value; load(false) }
watch(() => props.kind, () => { query = ''; rows.value = []; load(false) }, { immediate: true })
watch(() => authSession.user?.id, () => {
  ++revision
  controller?.abort()
  rows.value = []
  hasMore.value = false
  loading.value = false
  error.value = '登录身份已变化，请重新加载当前身份的资源。'
})
onBeforeUnmount(() => { ++revision; controller?.abort() })
</script>

<style scoped lang="scss">
.evaluation-resource { width: 100%; :deep(.el-select) { width: 100%; } p { color: var(--text-secondary); font-size: var(--font-size-xs, 12px); margin-block: var(--spacing-2, 8px); overflow-wrap: anywhere; } }
</style>
