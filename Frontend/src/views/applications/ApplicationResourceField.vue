<template>
  <div class="delivery-field">
    <label :for="fieldId">
      {{ label }}
    </label>
    <select
      :id="fieldId"
      data-testid="application-source"
      :value="modelValue"
      :aria-label="label"
      :disabled="disabled || loading"
      :aria-describedby="`${fieldId}-help`"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option value="">
        {{ loading ? '正在加载可用资源…' : `选择${label}` }}
      </option>
      <option
        v-if="modelValue && !resources.some(item => String(item.id) === String(modelValue))"
        :value="modelValue"
      >
        已绑定资源 ·
        {{ modelValue }}
      </option>
      <option
        v-for="resource in resources"
        :key="resource.id"
        :value="resource.id"
      >
        {{ resource.name }}
      </option>
    </select>
    <p
      v-if="error"
      :id="`${fieldId}-help`"
      role="alert"
      class="delivery-field-error"
    >
      {{ error }}
      <button
        type="button"
        class="delivery-link"
        @click="load"
      >
        重试资源列表
      </button>
    </p>
    <p
      v-else-if="!loading && !disabled && !resources.length"
      :id="`${fieldId}-help`"
      class="delivery-hint"
    >
      当前空间没有可绑定的
      {{ label }}
      。
      <button
        v-if="contextualCreate && kind === 'knowledge'"
        type="button"
        class="delivery-link"
        @click="$emit('create-resource')"
      >
        先创建{{ label }}
      </button>
      <router-link
        v-else
        :to="kind === 'knowledge' ? '/knowledge' : '/workflows'"
      >
        先创建
        {{ label }}
      </router-link>
    </p>
    <p
      v-else
      :id="`${fieldId}-help`"
      class="delivery-hint"
    >
      仅列出当前空间内可绑定的资源。
      {{ kind === 'knowledge' ? '发布后知识内容持续更新。' : '发布时冻结流程，草稿修改不会改变线上版本。' }}
    </p>
  </div>
</template>

<script setup>
import {
  computed,
  onBeforeUnmount,
  ref,
  useId,
  watch
} from 'vue'
import {
  applicationsApi
} from '@/api/applications'
import {
  APPLICATIONS
} from '@/config/applications'

const props = defineProps({
  kind: {
    type: String,
    required: true
  },
  tenantId: {
    type: [String, Number],
    default: ''
  },
  modelValue: {
    type: [String, Number],
    default: ''
  },
  disabled: Boolean,
  contextualCreate: Boolean
})
const emit = defineEmits(['update:modelValue', 'create-resource', 'resources-loaded'])
const fieldId = useId()
const label = computed(() => props.kind === 'knowledge' ? '知识库' : '工作流')
const resources = ref([])
const loading = ref(false)
const error = ref('')
let revision = 0
async function load() {
  const current = ++revision
  if (props.disabled) {
    loading.value = false;
    error.value = '';
    return
  }
  loading.value = true
  error.value = ''
  resources.value = []
  const items = []
  try {
    let page = 1
    let result
    do {
      result = await applicationsApi.resources({
        kind: props.kind,
        tenant_id: props.tenantId || undefined,
        page,
        page_size: APPLICATIONS.pageSize
      })
      if (current !== revision) return
      items.push(...(result.results || result || []))
      page++
    } while (result.next)
    resources.value = items
    emit('resources-loaded', { kind: props.kind, tenantId: props.tenantId || '', resources: items })
  } catch (failure) {
    if (current === revision) error.value = failure.message || '无法加载可用资源，请重试。'
  } finally {
    if (current === revision) loading.value = false
  }
}
watch(() => [props.kind, props.tenantId, props.disabled], load, {
  immediate: true
})
onBeforeUnmount(() => {
  revision++
})
</script>

