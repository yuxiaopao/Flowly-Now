<template>
  <div class="training-strategy-wizard">
    <el-steps
      :active="step"
      finish-status="success"
      align-center
      class="wizard-steps"
    >
      <el-step title="策略" />
      <el-step title="权重" />
      <el-step title="数据集" />
      <el-step title="超参" />
      <el-step title="输出" />
    </el-steps>

    <div
      v-loading="loadingOptions"
      class="wizard-body"
    >
      <!-- Step 0: Strategy -->
      <div
        v-show="step === 0"
        class="step-panel"
      >
        <el-alert
          v-if="optionsError"
          type="warning"
          :closable="false"
          show-icon
          class="options-alert"
          :title="optionsError"
        />
        <el-radio-group
          v-model="strategyId"
          class="strategy-grid"
          @change="onStrategyChange"
        >
          <el-radio
            v-for="s in strategies"
            :key="s.id"
            :value="s.id"
            border
            class="strategy-card"
          >
            <strong>{{ s.label }}</strong>
            <span class="strategy-desc">{{ strategyDesc(s) }}</span>
          </el-radio>
        </el-radio-group>
        <el-form
          v-if="strategyId === 'clip'"
          label-position="top"
          size="small"
          class="mt-3"
        >
          <el-form-item label="CLIP 任务类型">
            <el-radio-group
              v-model="clipTaskType"
              @change="emitChange"
            >
              <el-radio value="classification">
                分类 / 零样本
              </el-radio>
              <el-radio value="retrieval">
                图文检索
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 1: Base weights -->
      <div
        v-show="step === 1"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="基础权重 / 预训练模型">
            <el-select
              v-model="baseWeightUri"
              filterable
              @change="emitChange"
            >
              <el-option
                v-for="w in currentBaseWeights"
                :key="w.id"
                :label="w.label"
                :value="w.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 2: Dataset -->
      <div
        v-show="step === 2"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="dataset.yaml 路径（YOLO）或数据集路径">
            <el-input
              v-model="datasetYamlPath"
              placeholder="E:/datasets/xxx/dataset.yaml"
              @change="analyzeDataset"
            />
          </el-form-item>
          <el-button
            size="small"
            :loading="analyzing"
            :disabled="!datasetYamlPath.trim()"
            @click="analyzeDataset"
          >
            分析类别
          </el-button>
        </el-form>
        <div
          v-if="analysis"
          class="analysis-card"
        >
          <p><strong>类别数</strong> {{ analysis.classCount }}</p>
          <p><strong>建议任务</strong> {{ analysis.suggestedTaskType }}</p>
          <ul v-if="analysis.classes?.length">
            <li
              v-for="c in analysis.classes"
              :key="c.name"
            >
              {{ c.name }} — {{ c.count ?? '—' }} 样本
            </li>
          </ul>
          <ul
            v-if="analysis.warnings?.length"
            class="warnings"
          >
            <li
              v-for="(w, i) in analysis.warnings"
              :key="i"
            >
              {{ w }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Step 3: Hyperparams -->
      <div
        v-show="step === 3"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <template v-if="strategyId === 'yolo'">
            <el-form-item label="训练轮次">
              <el-input-number
                v-model="epochs"
                :min="1"
                :max="500"
                @change="emitChange"
              />
            </el-form-item>
            <el-form-item label="Batch Size">
              <el-input-number
                v-model="batchSize"
                :min="1"
                :max="128"
                @change="emitChange"
              />
            </el-form-item>
            <el-form-item label="图像尺寸">
              <el-input-number
                v-model="imageSize"
                :min="320"
                :max="1280"
                :step="32"
                @change="emitChange"
              />
            </el-form-item>
          </template>
          <template v-else-if="strategyId === 'clip' && clipTaskType === 'retrieval'">
            <el-form-item label="索引模式">
              <el-select
                v-model="indexMode"
                @change="emitChange"
              >
                <el-option
                  label="服务端"
                  value="server"
                />
                <el-option
                  label="Desktop GPU"
                  value="desktop"
                />
              </el-select>
            </el-form-item>
          </template>
          <template v-else>
            <el-form-item label="训练轮次">
              <el-input-number
                v-model="epochs"
                :min="1"
                :max="100"
                @change="emitChange"
              />
            </el-form-item>
            <el-form-item label="Learning Rate">
              <el-input-number
                v-model="learningRate"
                :min="0.00001"
                :max="1"
                :step="0.0001"
                @change="emitChange"
              />
            </el-form-item>
          </template>
        </el-form>
      </div>

      <!-- Step 4: Output -->
      <div
        v-show="step === 4"
        class="step-panel"
      >
        <el-form
          label-position="top"
          size="small"
        >
          <el-form-item label="权重输出目录">
            <el-input
              v-model="outputDir"
              placeholder="./training_outputs"
              @change="emitChange"
            />
          </el-form-item>
          <el-form-item label="目标节点类型">
            <el-tag>{{ targetNodeType }}</el-tag>
          </el-form-item>
          <el-form-item label="预期输出">
            <span class="output-hint">{{ expectedOutputs }}</span>
          </el-form-item>
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
        创建工作流
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
import { ref, computed, onMounted, watch } from 'vue'
import trainingApi from '@/api/training'

const FALLBACK_STRATEGIES = [
  {
    id: 'yolo',
    label: 'YOLO 目标检测',
    base_weights: [
      { id: 'yolov8n.pt', label: 'YOLOv8 Nano' },
      { id: 'yolo11x.pt', label: 'YOLO11 XLarge' },
    ],
    outputs: ['best.pt', 'last.pt', 'results.csv'],
  },
  {
    id: 'clip',
    label: 'CLIP 分类 / 检索',
    base_weights: [
      { id: 'ViT-B-32/openai', label: 'CLIP ViT-B/32 OpenAI' },
    ],
    outputs: ['clip.pt', 'manifest.json'],
  },
  {
    id: 'transformer',
    label: 'Transformer 微调',
    base_weights: [
      { id: 'bert-base-uncased', label: 'BERT Base' },
    ],
    outputs: ['pytorch_model.bin', 'config.json'],
  },
]

const emit = defineEmits(['finished'])

const step = ref(0)
const loadingOptions = ref(false)
const optionsError = ref('')
const analyzing = ref(false)
const strategies = ref([])
const strategyId = ref('yolo')
const clipTaskType = ref('classification')
const baseWeightUri = ref('yolov8n.pt')
const datasetYamlPath = ref('')
const analysis = ref(null)
const epochs = ref(50)
const batchSize = ref(16)
const imageSize = ref(640)
const learningRate = ref(0.00005)
const indexMode = ref('server')
const outputDir = ref('./training_outputs')

const currentStrategy = computed(() => strategies.value.find((s) => s.id === strategyId.value) || null)

const currentBaseWeights = computed(() => {
  const s = currentStrategy.value
  if (!s) return []
  return s.baseWeights || s.base_weights || []
})

const targetNodeType = computed(() => {
  if (strategyId.value === 'yolo') return 'yolo_training'
  if (strategyId.value === 'clip') return clipTaskType.value === 'retrieval' ? 'clip_retrieval' : 'clip_classification'
  return 'model_training'
})

const expectedOutputs = computed(() => {
  const s = currentStrategy.value
  return (s?.outputs || []).join(', ') || '—'
})

function strategyDesc(s) {
  if (s.id === 'yolo') return 'Ultralytics 目标检测'
  if (s.id === 'clip') return 'PyTorch CLIP 分类或检索'
  return 'HuggingFace Transformers 微调'
}

function onStrategyChange() {
  const weights = currentBaseWeights.value
  if (weights.length) baseWeightUri.value = weights[0].id
  emitChange()
}

async function loadOptions() {
  loadingOptions.value = true
  optionsError.value = ''
  try {
    const data = await trainingApi.getOptions()
    strategies.value = data.strategies?.length ? data.strategies : FALLBACK_STRATEGIES
    if (strategies.value.length && !strategies.value.find((s) => s.id === strategyId.value)) {
      strategyId.value = strategies.value[0].id
    }
    onStrategyChange()
  } catch (err) {
    optionsError.value = err?.message || '无法加载训练策略，已使用内置默认配置'
    strategies.value = FALLBACK_STRATEGIES
    onStrategyChange()
  } finally {
    loadingOptions.value = false
  }
}

async function analyzeDataset() {
  if (!datasetYamlPath.value.trim()) return
  analyzing.value = true
  try {
    const kind = strategyId.value === 'clip'
      ? (clipTaskType.value === 'retrieval' ? 'clip_ret' : 'clip_cls')
      : strategyId.value
    const res = await trainingApi.analyzeDataset({
      trainingKind: kind,
      datasetYamlPath: datasetYamlPath.value.trim(),
    })
    analysis.value = {
      classCount: res.classCount,
      suggestedTaskType: res.suggestedTaskType,
      classes: res.classes || [],
      warnings: res.warnings || [],
    }
  } catch (err) {
    analysis.value = { warnings: [err?.message || '分析失败'] }
  } finally {
    analyzing.value = false
  }
}

function buildConfig() {
  const classNames = (analysis.value?.classes || []).map((c) => c.name).filter(Boolean)
  const base = {
    strategyId: strategyId.value,
    baseWeightUri: baseWeightUri.value,
    datasetYamlPath: datasetYamlPath.value,
    classNames,
    epochs: epochs.value,
    outputDir: outputDir.value,
    targetNodeType: targetNodeType.value,
  }
  if (strategyId.value === 'yolo') {
    const variant = baseWeightUri.value.match(/([nsmxl])\.pt$/)?.[1] || 'n'
    const version = baseWeightUri.value.includes('11') ? 'v11' : 'v8'
    return {
      ...base,
      yoloVersion: version,
      modelVariant: variant,
      batchSize: batchSize.value,
      imageSize: imageSize.value,
      trainingMode: 'local',
    }
  }
  if (strategyId.value === 'clip') {
    return {
      ...base,
      clipTaskType: clipTaskType.value,
      indexMode: indexMode.value,
      baseModel: baseWeightUri.value,
    }
  }
  return {
    ...base,
    framework: 'transformers',
    modelType: 'classification',
    learningRate: learningRate.value,
  }
}

function emitChange() {
  // reserved for parent binding
}

const validationError = computed(() => {
  if (step.value === 0 && !strategyId.value) return '请选择训练策略'
  if (step.value === 1 && !baseWeightUri.value) return '请选择基础权重'
  return ''
})

const canNext = computed(() => !validationError.value)
const canFinish = computed(() => Boolean(baseWeightUri.value && outputDir.value.trim()))

function prev() {
  if (step.value > 0) step.value -= 1
}

function next() {
  if (!canNext.value) return
  if (step.value < 4) step.value += 1
}

function finish() {
  if (!canFinish.value) return
  emit('finished', buildConfig())
}

onMounted(loadOptions)
watch(strategyId, onStrategyChange)
</script>

<style scoped lang="scss">
.training-strategy-wizard {
  .wizard-steps { margin-bottom: 16px; }
  .options-alert { margin-bottom: 12px; }
  .step-panel { min-height: 180px; }
  .strategy-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .strategy-card {
    width: 100%;
    margin: 0;
    height: auto;
    padding: 10px 12px;
    :deep(.el-radio__label) {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      white-space: normal;
    }
  }
  .strategy-desc {
    font-size: 11px;
    color: var(--text-secondary, #a1a1aa);
    margin-top: 2px;
  }
  .analysis-card {
    margin-top: 12px;
    padding: 10px;
    border-radius: 8px;
    background: var(--bg-secondary, rgba(0,0,0,0.15));
    font-size: 12px;
    ul { margin: 6px 0 0; padding-left: 18px; }
    .warnings { color: #f59e0b; }
  }
  .output-hint { font-size: 12px; color: var(--text-secondary); }
  .wizard-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border-primary, #2e2e42);
  }
  .validation-error { color: #ef4444; font-size: 12px; margin-top: 8px; }
  .mt-3 { margin-top: 12px; }
}
</style>
