<template>
  <div :class="['config-form', `${kind}-transform-config-form`]">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <div class="form-section">
        <h4 class="section-title">
          基本信息
        </h4>
        <el-form-item label="节点名称">
          <el-input
            v-model="localData.label"
            placeholder="输入节点名称"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="localData.description"
            type="textarea"
            :rows="2"
            placeholder="节点功能描述"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          转换配置
        </h4>
        <el-form-item label="操作类型">
          <el-select
            v-model="localData.operation"
            @change="handleChange"
          >
            <el-option
              v-for="item in operations"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="输入来源">
          <el-input
            v-model="localData.source"
            :placeholder="sourcePlaceholder"
            @change="handleChange"
          />
          <div class="field-hint">
            留空时使用上游输出；可通过变量表达式指定输入。
          </div>
        </el-form-item>
        <el-form-item
          label="操作参数（JSON 对象）"
          :error="parameterError"
        >
          <el-input
            v-model="localData[parameterField]"
            type="textarea"
            :rows="5"
            aria-label="操作参数"
            :placeholder="example"
            class="json-input"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item
          v-if="localData.operation === 'object_to_json'"
          label="序列化格式"
        >
          <el-select
            v-model="localData.formatting"
            @change="handleChange"
          >
            <el-option
              label="易读格式"
              value="pretty"
            />
            <el-option
              label="紧凑格式"
              value="compact"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="localData.operation === 'parse_array'"
          label="数组输出字段"
        >
          <el-input
            v-model="localData.target_field"
            placeholder="items"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item
          v-if="kind === 'csv'"
          label="CSV 分隔符"
        >
          <el-input
            v-model="localData.delimiter"
            placeholder=","
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item
          label="备用输入数据"
          :error="dataError"
        >
          <el-input
            v-model="localData.data"
            type="textarea"
            :rows="5"
            aria-label="备用输入数据"
            :placeholder="dataPlaceholder"
            class="json-input"
            @change="handleChange"
          />
          <div class="field-hint">
            上游未提供数据时使用。{{ dataHint }}
          </div>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          {{ operationLabel }} · 参数示例
        </h4>
        <div class="operation-guide">
          <code>{{ example }}</code>
          <p
            v-if="localData.operation === 'join'"
            class="field-hint"
          >
            rightData 是需要连接的第二张表，左右字段必须存在。
          </p>
          <p
            v-else-if="example === '{}'"
            class="field-hint"
          >
            此操作无需额外参数，可保留空对象。
          </p>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import {
  JSON_OPERATIONS, CSV_OPERATIONS, DATA_TRANSFORM_EXAMPLES,
  createDataTransformConfig, formatDataTransformField,
  getDataTransformJsonError, getDataTransformOperationLabel,
} from '@/config/dataTransformOperations'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  kind: { type: String, default: 'json' },
})
const emit = defineEmits(['update:modelValue', 'change'])
const localData = reactive({})
const parameterField = computed(() => props.kind === 'csv' ? 'params' : 'schema')
const operations = computed(() => props.kind === 'csv' ? CSV_OPERATIONS : JSON_OPERATIONS)
const sourcePlaceholder = '{{input_data.data}}'
const operationLabel = computed(() => getDataTransformOperationLabel(localData.operation, props.kind))
const example = computed(() => JSON.stringify(DATA_TRANSFORM_EXAMPLES[props.kind]?.[localData.operation] || {}, null, 2))
const parameterError = computed(() => getDataTransformJsonError(localData[parameterField.value], { objectOnly: true }))
const dataError = computed(() => getDataTransformJsonError(localData.data, { arrayOnly: props.kind === 'csv', allowXml: localData.operation === 'xml_to_json' }))
const dataPlaceholder = computed(() => localData.operation === 'xml_to_json' ? '<root><name>示例</name></root>' : props.kind === 'csv' ? '[{"类别":"示例","金额":100}]' : '{"id":1,"name":"示例"}')
const dataHint = computed(() => localData.operation === 'xml_to_json' ? '填写 XML 文本。' : props.kind === 'csv' ? '填写 JSON 数组，每一项代表一行。' : '填写有效的 JSON，支持对象、数组、数字及布尔值。')

watch(() => [props.modelValue, props.kind], () => {
  const config = createDataTransformConfig(props.modelValue, props.kind)
  for (const key of Object.keys(localData)) delete localData[key]
  Object.assign(localData, {
    label: '', description: '', source: '', formatting: 'pretty', target_field: 'items', delimiter: ',',
    ...config,
    [parameterField.value]: formatDataTransformField(config[parameterField.value], '{}'),
    data: formatDataTransformField(config.data),
  })
}, { immediate: true, deep: true })

function handleChange() {
  const updated = createDataTransformConfig({ ...localData }, props.kind)
  emit('update:modelValue', updated)
  emit('change', updated)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.form-section {
  margin-bottom: $spacing-5;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child { border-bottom: none; margin-bottom: 0; }
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
}

.json-input :deep(.el-textarea__inner), .operation-guide code {
  font-family: var(--font-family-mono, 'Fira Code', monospace);
  font-size: $font-size-xs;
}

.field-hint {
  margin: $spacing-1 0 0;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.operation-guide {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  padding: $spacing-3;
  line-height: 1.6;

  code { display: block; color: var(--text-secondary); white-space: pre-wrap; overflow-wrap: anywhere; }
}
</style>
