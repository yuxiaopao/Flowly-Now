<template>
  <div class="yolo-training-config">
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
          训练方式
        </h4>
        <el-form-item>
          <el-radio-group
            v-model="localData.trainingMode"
            size="small"
            @change="handleChange"
          >
            <el-radio-button value="local">
              本地训练（用户设备）
            </el-radio-button>
            <el-radio-button value="cloud">
              云端训练（服务器）
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <div
          v-if="localData.trainingMode === 'local'"
          class="local-hint"
        >
          <InfoIcon :size="12" />
          本地训练将在用户浏览器所在设备上运行训练脚本，支持 GPU 加速
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          模型配置
        </h4>
        <el-form-item label="YOLO 版本">
          <el-select
            v-model="localData.yoloVersion"
            style="width: 100%"
            @change="handleModelChange"
          >
            <el-option
              label="YOLOv8"
              value="v8"
            />
            <el-option
              label="YOLOv11"
              value="v11"
            />
            <el-option
              label="YOLOv5"
              value="v5"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型规格">
          <el-select
            v-model="localData.modelVariant"
            style="width: 100%"
            @change="handleModelChange"
          >
            <el-option
              label="n (Nano) — 轻量快速"
              value="n"
            />
            <el-option
              label="s (Small) — 平衡"
              value="s"
            />
            <el-option
              label="m (Medium) — 精度"
              value="m"
            />
            <el-option
              label="l (Large) — 高精度"
              value="l"
            />
            <el-option
              label="x (XLarge) — 最高精度"
              value="x"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="基础权重文件">
          <el-select
            v-model="localData.baseWeightUri"
            filterable
            allow-create
            style="width: 100%"
            @change="handleBaseWeightChange"
          >
            <el-option
              v-for="weight in yoloBaseWeights"
              :key="weight.value"
              :label="weight.label"
              :value="weight.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义权重路径（可选）">
          <el-input
            v-model="localData.baseWeightPath"
            placeholder="E:/models/custom.pt"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          训练参数
        </h4>
        <el-form-item label="Epochs（训练轮次）">
          <el-input-number
            v-model="localData.epochs"
            :min="1"
            :max="1000"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="Batch Size">
          <el-input-number
            v-model="localData.batchSize"
            :min="1"
            :max="256"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="图像尺寸">
          <el-input-number
            v-model="localData.imageSize"
            :min="320"
            :max="1280"
            :step="32"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="学习率">
          <el-input-number
            v-model="localData.learningRate"
            :min="0"
            :max="1"
            :precision="4"
            :step="0.0001"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          数据集
        </h4>
        <el-form-item label="数据集来源">
          <el-select
            v-model="localData.datasetSource"
            style="width: 100%"
            @change="handleDatasetSourceChange"
          >
            <el-option
              label="YAML 配置文件"
              value="yaml"
            />
            <el-option
              label="标注项目"
              value="annotation"
            />
            <el-option
              label="本地文件夹路径"
              value="local"
            />
          </el-select>
        </el-form-item>

        <template v-if="localData.datasetSource === 'yaml'">
          <el-form-item label="dataset.yaml 路径">
            <el-input
              v-model="localData.datasetYamlPath"
              placeholder="/data/my-project/dataset.yaml"
              @change="handleChange"
            />
          </el-form-item>
        </template>

        <template v-if="localData.datasetSource === 'annotation'">
          <el-form-item label="选择标注项目">
            <el-select
              v-model="localData.annotationProjectId"
              placeholder="选择标注项目"
              filterable
              style="width: 100%"
              @change="handleChange"
            >
              <el-option
                v-for="p in annotationProjects"
                :key="p.id"
                :label="p.name"
                :value="p.id"
              />
            </el-select>
          </el-form-item>
        </template>

        <template v-if="localData.datasetSource === 'local'">
          <el-form-item label="数据集根目录">
            <el-input
              v-model="localData.datasetPath"
              placeholder="/path/to/dataset"
              @change="handleChange"
            />
          </el-form-item>
        </template>

        <el-form-item label="类别名称（逗号分隔）">
          <el-input
            v-model="classNamesInput"
            placeholder="cat, dog, bird"
            @change="handleClassNamesChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          输出设置
        </h4>
        <el-form-item label="输出目录（本地训练时）">
          <el-input
            v-model="localData.outputDir"
            placeholder="./yolo_outputs"
            @change="handleChange"
          />
        </el-form-item>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Info as InfoIcon } from 'lucide-vue-next'
import trainingApi from '@/api/training'

const props = defineProps({
  nodeData: { type: Object, required: true },
})

const emit = defineEmits(['change'])

const localData = ref({
  label: '',
  description: '',
  trainingMode: 'local',
  yoloVersion: 'v8',
  modelVariant: 'n',
  baseWeightUri: 'yolov8n.pt',
  baseWeightPath: '',
  epochs: 100,
  batchSize: 16,
  imageSize: 640,
  learningRate: 0.01,
  datasetSource: 'yaml',
  datasetYamlPath: '',
  annotationProjectId: '',
  datasetPath: '',
  classNames: [],
  outputDir: './yolo_outputs',
})

const yoloBaseWeights = ref([])

async function loadYoloWeights() {
  try {
    const data = await trainingApi.getOptions()
    const yolo = (data.strategies || []).find((s) => s.id === 'yolo')
    yoloBaseWeights.value = (yolo?.baseWeights || yolo?.base_weights || []).map((w) => ({
      value: w.id,
      label: `${w.label} - ${w.id}`,
    }))
  } catch {
    yoloBaseWeights.value = [
      { value: 'yolov8n.pt', label: 'YOLOv8 Nano - yolov8n.pt' },
      { value: 'yolo11x.pt', label: 'YOLO11 XLarge - yolo11x.pt' },
    ]
  }
}

onMounted(loadYoloWeights)

const classNamesInput = ref('')
const annotationProjects = ref([])

watch(
  () => props.nodeData,
  (data) => {
    if (data?.config) {
      const cfg = data.config
      localData.value = {
        label: data.label || '',
        description: data.description || '',
        trainingMode: cfg.trainingMode || 'local',
        yoloVersion: cfg.yoloVersion || 'v8',
        modelVariant: cfg.modelVariant || 'n',
        baseWeightUri: cfg.baseWeightUri || buildDefaultBaseWeight(cfg.yoloVersion || 'v8', cfg.modelVariant || 'n'),
        baseWeightPath: cfg.baseWeightPath || '',
        epochs: cfg.epochs || 100,
        batchSize: cfg.batchSize || 16,
        imageSize: cfg.imageSize || 640,
        learningRate: cfg.learningRate || 0.01,
        datasetSource: cfg.datasetSource || 'yaml',
        datasetYamlPath: cfg.datasetYamlPath || '',
        annotationProjectId: cfg.annotationProjectId || '',
        datasetPath: cfg.datasetPath || '',
        classNames: cfg.classNames || [],
        outputDir: cfg.outputDir || './yolo_outputs',
      }
      classNamesInput.value = (cfg.classNames || []).join(', ')
    }
  },
  { immediate: true }
)

function handleChange() {
  emit('change', {
    label: localData.value.label,
    description: localData.value.description,
    config: {
      trainingMode: localData.value.trainingMode,
      yoloVersion: localData.value.yoloVersion,
      modelVariant: localData.value.modelVariant,
      baseWeightUri: localData.value.baseWeightUri,
      baseWeightPath: localData.value.baseWeightPath,
      epochs: localData.value.epochs,
      batchSize: localData.value.batchSize,
      imageSize: localData.value.imageSize,
      learningRate: localData.value.learningRate,
      datasetSource: localData.value.datasetSource,
      datasetYamlPath: localData.value.datasetYamlPath,
      annotationProjectId: localData.value.annotationProjectId,
      datasetPath: localData.value.datasetPath,
      classNames: localData.value.classNames,
      outputDir: localData.value.outputDir,
    },
  })
}

function handleDatasetSourceChange() {
  handleChange()
}

function handleModelChange() {
  localData.value.baseWeightUri = buildDefaultBaseWeight(localData.value.yoloVersion, localData.value.modelVariant)
  handleChange()
}

function handleBaseWeightChange(value) {
  const version = inferYoloVersion(value)
  const variant = inferModelVariant(value)
  if (version) localData.value.yoloVersion = version
  if (variant) localData.value.modelVariant = variant
  handleChange()
}

function buildDefaultBaseWeight(version, variant) {
  const prefix = version === 'v11' ? 'yolo11' : `yolov${String(version || 'v8').replace('v', '')}`
  return `${prefix}${variant || 'n'}.pt`
}

function inferYoloVersion(value = '') {
  const text = String(value).toLowerCase()
  if (text.includes('yolo11') || text.includes('yolov11')) return 'v11'
  if (text.includes('yolov8')) return 'v8'
  if (text.includes('yolov5')) return 'v5'
  return ''
}

function inferModelVariant(value = '') {
  const match = String(value).toLowerCase().match(/yolo(?:v?\d+|11)([nsmxl])/) || String(value).toLowerCase().match(/yolov11([nsmxl])/)
  return match?.[1] || ''
}

function handleClassNamesChange() {
  localData.value.classNames = classNamesInput.value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
  handleChange()
}
</script>

<style scoped>
.yolo-training-config {
  padding: 4px 0;
}

.form-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.local-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 6px 10px;
  border-radius: 6px;
  margin-top: -4px;
}
</style>
