<template>
  <div class="config-form model-evaluation-config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <section
        v-if="showIdentity"
        class="form-section"
      >
        <el-form-item label="节点名称">
          <el-input
            v-model="localData.label"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="localData.description"
            type="textarea"
            :rows="2"
            @change="handleChange"
          />
        </el-form-item>
      </section>
      <section class="form-section">
        <h4 class="section-title">
          模型与测试数据
        </h4>
        <el-form-item label="模型来源">
          <el-select
            v-model="modelSource"
            @change="changeModelSource"
          >
            <el-option
              label="上游训练节点"
              value="upstream"
            />
            <el-option
              label="已完成的训练记录"
              value="registered"
            />
            <el-option
              label="历史配置（已登记 ID / 路径）"
              value="legacy"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="modelSource === 'registered'"
          label="训练记录"
          required
        >
          <EvaluationResourceSelect
            v-model="localData.trainingJobId"
            kind="model"
            @update:model-value="handleChange"
          />
        </el-form-item>
        <el-form-item
          v-else-if="modelSource === 'legacy'"
          label="已登记模型 ID 或路径"
          required
        >
          <el-input
            v-model="localData.modelPath"
            @change="handleChange"
          />
        </el-form-item>
        <p class="field-hint">
          只评测有权限访问的已完成训练产物。上游模式读取当前执行的训练记录，不接受任意服务器文件。
        </p>
        <el-form-item label="测试数据来源">
          <el-select
            v-model="datasetSource"
            @change="changeDatasetSource"
          >
            <el-option
              label="训练数据集"
              value="training"
            />
            <el-option
              label="通用数据集"
              value="generic"
            />
            <el-option
              label="历史配置（已登记 ID / 路径）"
              value="legacy"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="datasetSource === 'training'"
          label="测试数据集"
          required
        >
          <EvaluationResourceSelect
            v-model="localData.trainingDatasetId"
            kind="training"
            @update:model-value="handleChange"
          />
        </el-form-item>
        <el-form-item
          v-else-if="datasetSource === 'generic'"
          label="测试数据集"
          required
        >
          <EvaluationResourceSelect
            v-model="localData.datasetId"
            kind="generic"
            @update:model-value="handleChange"
          />
        </el-form-item>
        <el-form-item
          v-else
          label="已登记测试集 ID 或路径"
          required
        >
          <el-input
            v-model="localData.testDataset"
            @change="handleChange"
          />
        </el-form-item>
      </section>
      <section class="form-section">
        <h4 class="section-title">
          真实评测指标
        </h4>
        <el-form-item
          label="指标"
          required
        >
          <el-select
            v-model="localData.metrics"
            multiple
            @change="handleChange"
          >
            <el-option
              v-for="metric in MODEL_EVALUATION.metrics"
              :key="metric.value"
              :value="metric.value"
              :label="metric.label"
            />
            <el-option
              v-for="metric in unsupportedMetrics"
              :key="metric"
              :value="metric"
              :label="metric + '（不支持，请移除）'"
              disabled
            />
          </el-select>
        </el-form-item>
        <p
          v-if="unsupportedMetrics.length"
          class="field-hint"
          role="alert"
        >
          历史指标尚未实现，执行会明确失败。请选择当前模型支持的指标。
        </p>
        <p class="field-hint">
          分类模型支持准确率、精确率、召回率、F1、AUC；YOLO 支持精确率、召回率与 mAP。类别不足时 AUC 显示无法计算。
        </p>
        <details>
          <summary>数据列与图像选项</summary>
          <el-form-item label="CSV 标签列（留空自动匹配）">
            <el-input
              v-model="localData.labelColumn"
              clearable
              @change="handleChange"
            />
          </el-form-item>
          <el-form-item label="CSV 特征列（留空使用训练列顺序）">
            <el-select
              v-model="localData.features"
              multiple
              filterable
              allow-create
              default-first-option
              @change="handleChange"
            />
          </el-form-item>
          <p class="field-hint">
            按训练时的列名与归一化参数评测；旧模型会校验原训练数据。JSON 使用 features 二维数组与 labels 数组。
          </p>
          <el-form-item label="YOLO 数据划分">
            <el-select
              v-model="localData.split"
              @change="handleChange"
            >
              <el-option
                label="测试集 test"
                value="test"
              /><el-option
                label="验证集 val"
                value="val"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="图像尺寸">
            <el-input-number
              v-model="localData.imageSize"
              v-bind="MODEL_EVALUATION.imageSize"
              @change="handleChange"
            />
          </el-form-item>
        </details>
      </section>
    </el-form>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import EvaluationResourceSelect from './EvaluationResourceSelect.vue'
import { evaluationConfig, MODEL_EVALUATION } from '@/config/modelEvaluation'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  showIdentity: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'change'])
const localData = reactive(evaluationConfig())
const modelSource = ref('upstream'), datasetSource = ref('training')
const unsupportedMetrics = computed(() => localData.metrics.filter(value => !MODEL_EVALUATION.metrics.some(metric => metric.value === value)))
watch(() => props.modelValue, value => {
  for (const key of Object.keys(localData)) delete localData[key]
  Object.assign(localData, evaluationConfig(value))
  modelSource.value = localData.evaluationModelSource || (localData.trainingJobId ? 'registered' : localData.modelPath ? 'legacy' : 'upstream')
  datasetSource.value = localData.evaluationDatasetSource || (localData.datasetId ? 'generic' : localData.testDataset && !localData.trainingDatasetId ? 'legacy' : 'training')
}, { immediate: true, deep: true })
function handleChange() {
  const value = { ...localData, evaluationModelSource: modelSource.value, evaluationDatasetSource: datasetSource.value,
    metrics: [...localData.metrics], features: [...localData.features] }
  emit('update:modelValue', value)
  emit('change', value)
}
function changeModelSource() {
  localData.trainingJobId = ''
  delete localData.trainingRunId
  localData.modelPath = ''
  handleChange()
}
function changeDatasetSource() {
  localData.datasetId = ''
  localData.trainingDatasetId = ''
  localData.testDataset = ''
  handleChange()
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
.form-section { margin-bottom: $spacing-5; padding-bottom: $spacing-4; border-bottom: 1px solid var(--border-primary); &:last-child { border-bottom: none; } }
.section-title { font-size: $font-size-sm; color: var(--text-primary); margin: 0 0 $spacing-3; }
.field-hint { margin-block: $spacing-2; font-size: $font-size-xs; color: var(--text-secondary); line-height: 1.6; }
:deep(.el-select) { width: 100%; }
details { summary { cursor: pointer; color: var(--text-primary); margin-bottom: $spacing-3; } }
</style>
