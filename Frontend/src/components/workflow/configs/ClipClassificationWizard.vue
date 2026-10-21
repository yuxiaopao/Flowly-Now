<template>
  <div class="clip-cls-wizard">
    <el-steps
      :active="step"
      finish-status="success"
      align-center
      class="wizard-steps"
    >
      <el-step title="数据" />
      <el-step title="模式" />
      <el-step title="类名" />
      <el-step title="环境" />
      <el-step title="输出" />
    </el-steps>

    <div class="wizard-body">
      <div
        v-show="step === 0"
        class="step-panel"
      >
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="数据来源"
        />
        <p class="hint">
          零样本：仅需类别名称，无需训练集。<br>
          微调：请连接上游 <code>dataset_upload</code>（format=classification_folders）。
        </p>
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="数据集路径（微调必填）">
            <el-input
              :model-value="local.datasetPath"
              placeholder="从上游 dataset_upload 继承或手动填写"
              @update:model-value="patch('datasetPath', $event)"
            />
          </el-form-item>
        </el-form>
      </div>

      <div
        v-show="step === 1"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="分类模式">
            <el-radio-group
              :model-value="local.mode"
              @update:model-value="patch('mode', $event)"
            >
              <el-radio-button value="zero_shot">
                零样本
              </el-radio-button>
              <el-radio-button value="finetune">
                微调
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>

      <div
        v-show="step === 2"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item
            label="类别名称"
            required
          >
            <el-select
              :model-value="classNames"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入后回车添加"
              style="width: 100%"
              @update:model-value="patch('classNames', $event)"
            />
          </el-form-item>
        </el-form>
      </div>

      <div
        v-show="step === 3"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="CLIP 基座">
            <el-select
              :model-value="local.baseModel || 'ViT-B/32'"
              @update:model-value="patch('baseModel', $event)"
            >
              <el-option
                label="ViT-B/32"
                value="ViT-B/32"
              />
              <el-option
                label="ViT-B/16"
                value="ViT-B/16"
              />
            </el-select>
          </el-form-item>
          <template v-if="local.mode === 'finetune'">
            <el-form-item label="训练轮次">
              <el-input-number
                :model-value="local.epochs || 10"
                :min="1"
                :max="200"
                @update:model-value="patch('epochs', $event)"
              />
            </el-form-item>
            <el-form-item label="训练方式">
              <el-radio-group
                :model-value="local.trainingMode || 'local'"
                @update:model-value="patch('trainingMode', $event)"
              >
                <el-radio-button value="local">
                  本地
                </el-radio-button>
                <el-radio-button value="cloud">
                  同步
                </el-radio-button>
              </el-radio-group>
            </el-form-item>
          </template>
        </el-form>
      </div>

      <div
        v-show="step === 4"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="输出目录">
            <el-input
              :model-value="local.outputDir || ''"
              placeholder="./outputs/clip_cls"
              @update:model-value="patch('outputDir', $event)"
            />
          </el-form-item>
          <div class="summary">
            <p><strong>模式</strong> {{ local.mode === 'finetune' ? '微调' : '零样本' }}</p>
            <p><strong>类别</strong> {{ classNames.join(', ') || '未设置' }}</p>
          </div>
        </el-form>
      </div>
    </div>

    <div class="wizard-footer">
      <el-button
        :disabled="step === 0"
        @click="prev"
      >
        上一步
      </el-button>
      <el-button
        v-if="step < 4"
        type="primary"
        :disabled="!canNext"
        @click="next"
      >
        下一步
      </el-button>
      <el-button
        v-else
        type="primary"
        :disabled="!canFinish"
        @click="finish"
      >
        完成向导
      </el-button>
    </div>
    <p
      v-if="validationError"
      class="validation-error"
    >
      {{ validationError }}
    </p>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change', 'finished'])

const local = reactive({
  mode: 'zero_shot',
  classNames: [],
  baseModel: 'ViT-B/32',
  epochs: 10,
  trainingMode: 'local',
  outputDir: '',
  datasetPath: '',
  wizardStep: 0,
  wizardCompleted: false,
})

const step = computed({
  get: () => local.wizardStep ?? 0,
  set: (v) => { local.wizardStep = v; emitAll() },
})

const classNames = computed(() => {
  const raw = local.classNames
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') return raw.split(',').map((s) => s.trim()).filter(Boolean)
  return []
})

watch(() => props.modelValue, (v) => {
  if (!v) return
  Object.assign(local, {
    mode: v.mode || 'zero_shot',
    classNames: v.classNames || [],
    baseModel: v.baseModel || 'ViT-B/32',
    epochs: v.epochs || 10,
    trainingMode: v.trainingMode || 'local',
    outputDir: v.outputDir || '',
    datasetPath: v.datasetPath || '',
    wizardStep: v.wizardStep ?? 0,
    wizardCompleted: v.wizardCompleted ?? false,
  })
}, { immediate: true, deep: true })

function emitAll(extra = {}) {
  const payload = {
    mode: local.mode,
    classNames: classNames.value,
    baseModel: local.baseModel,
    epochs: local.epochs,
    trainingMode: local.trainingMode,
    outputDir: local.outputDir,
    datasetPath: local.datasetPath,
    wizardStep: local.wizardStep,
    wizardCompleted: local.wizardCompleted,
    ...extra,
  }
  emit('update:modelValue', payload)
  emit('change', payload)
}

function patch(key, value) {
  local[key] = value
  emitAll()
}

const validationError = computed(() => {
  if (step.value === 0 && local.mode === 'finetune' && !local.datasetPath?.trim()) {
    return '微调模式需填写数据集路径'
  }
  if (step.value === 2 && !classNames.value.length) return '请至少添加一个类别'
  return ''
})

const canNext = computed(() => !validationError.value)
const canFinish = computed(() => classNames.value.length > 0 && (local.mode !== 'finetune' || local.datasetPath?.trim()))

function prev() {
  if (step.value > 0) emitAll({ wizardStep: step.value - 1 })
}

function next() {
  if (step.value < 4) emitAll({ wizardStep: step.value + 1 })
}

function finish() {
  emitAll({ wizardCompleted: true, wizardStep: 4 })
  emit('finished')
}
</script>

<style scoped>
.clip-cls-wizard { padding: 8px 0; }
.wizard-steps { margin-bottom: 16px; }
.step-panel { min-height: 160px; }
.hint { font-size: 12px; color: var(--text-secondary, #a1a1aa); line-height: 1.6; margin: 12px 0; }
.summary { font-size: 12px; color: var(--text-secondary, #a1a1aa); margin-top: 8px; }
.wizard-footer { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
.validation-error { color: #ef4444; font-size: 12px; margin-top: 8px; }
</style>
