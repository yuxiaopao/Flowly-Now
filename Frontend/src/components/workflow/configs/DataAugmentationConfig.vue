<template>
  <div class="config-form data-augmentation-config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <!-- 基本信息 -->
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

      <!-- 数据集选择 -->
      <div class="form-section">
        <h4 class="section-title">
          数据集选择
        </h4>
        
        <el-form-item label="选择数据集">
          <div class="dataset-selector">
            <el-select 
              v-model="localData.datasetId" 
              placeholder="请选择数据集"
              filterable
              remote
              :remote-method="searchDatasets"
              :loading="loadingDatasets"
              style="width: 100%"
              @change="handleDatasetChange"
            >
              <el-option
                v-for="ds in datasets"
                :key="ds.id"
                :label="ds.name"
                :value="ds.id"
              >
                <div class="dataset-option">
                  <span class="dataset-name">{{ ds.name }}</span>
                  <span class="dataset-meta">
                    {{ ds.format_display || ds.format }} · 
                    {{ ds.row_count || 0 }} 行 · 
                    {{ ds.size_display || formatSize(ds.size_bytes) }}
                  </span>
                </div>
              </el-option>
            </el-select>
            <el-button 
              type="primary" 
              link 
              style="margin-left: 8px"
              @click="showDatasetDialog = true"
            >
              <Plus :size="14" />
              选择
            </el-button>
          </div>
          <div
            v-if="selectedDataset"
            class="field-hint"
          >
            已选择: <strong>{{ selectedDataset.name }}</strong>
            <span
              class="dataset-type-badge"
              :class="detectedType"
            >
              {{ detectedType === 'image' ? '图像' : detectedType === 'text' ? '文本' : '表格' }}
            </span>
          </div>
        </el-form-item>

        <el-form-item
          v-if="localData.datasetId"
          label="输出模式"
        >
          <el-radio-group
            v-model="localData.outputMode"
            @change="handleChange"
          >
            <el-radio value="create_new">
              创建新数据集
            </el-radio>
            <el-radio value="overwrite">
              覆盖原数据集
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="localData.outputMode === 'create_new'"
          label="输出数据集名称"
        >
          <el-input 
            v-model="localData.outputName" 
            :placeholder="`${selectedDataset?.name || '数据集'}_augmented`"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 增强策略 -->
      <div class="form-section">
        <h4 class="section-title">
          增强策略
        </h4>
        
        <!-- 预设按钮 -->
        <div class="preset-buttons">
          <el-button
            v-for="preset in presets"
            :key="preset.id"
            :type="activePreset === preset.id ? 'primary' : 'default'"
            size="small"
            @click="applyPreset(preset)"
          >
            {{ preset.name }}
          </el-button>
        </div>

        <el-form-item label="增强策略">
          <el-select
            v-model="localData.strategy"
            style="width: 100%"
            @change="handleStrategyChange"
          >
            <el-option
              label="几何变换 (Geometric)"
              value="geometric"
            />
            <el-option
              label="颜色变换 (Color)"
              value="color"
            />
            <el-option
              label="噪声注入 (Noise)"
              value="noise"
            />
            <el-option
              label="混合增强 (Mixup)"
              value="mixup"
            />
            <el-option
              label="全部策略"
              value="all"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="增强倍数">
          <div class="ratio-input-wrapper">
            <el-slider
              v-model="localData.ratio"
              :min="1"
              :max="10"
              :step="0.5"
              :marks="ratioMarks"
              @change="handleChange"
            />
            <el-input-number
              v-model="localData.ratio"
              :min="1"
              :max="20"
              :step="0.5"
              :precision="1"
              controls-position="right"
              @change="handleChange"
            />
          </div>
          <div class="field-hint">
            原始数据将被扩充为原来的 N 倍 (1.0x - 20.0x)
          </div>
        </el-form-item>
      </div>

      <!-- 变换配置 -->
      <div class="form-section">
        <div
          class="section-header"
          @click="showAdvanced = !showAdvanced"
        >
          <h4 class="section-title">
            高级选项
          </h4>
          <el-icon><ArrowDown v-if="!showAdvanced" /><ArrowUp v-else /></el-icon>
        </div>

        <div
          v-show="showAdvanced"
          class="advanced-options"
        >
          <el-form-item label="启用变换">
            <div class="transforms-grid">
              <el-checkbox
                v-for="t in availableTransforms"
                :key="t.value"
                v-model="t.enabled"
                :label="t.label"
                @change="handleTransformsChange"
              />
            </div>
          </el-form-item>

          <el-form-item label="变换配置 (JSON)">
            <el-input
              v-model="transformationsJson"
              type="textarea"
              :rows="4"
              placeholder="[&quot;rotate&quot;, &quot;flip&quot;, &quot;brightness&quot;]"
              class="json-input"
              @blur="handleTransformsJsonChange"
            />
            <div class="field-hint">
              JSON数组，指定具体的变换操作
            </div>
          </el-form-item>
        </div>
      </div>

      <!-- 预览 -->
      <div
        v-if="localData.datasetId"
        class="form-section"
      >
        <h4 class="section-title">
          增强预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">策略:</span>
            <span class="preview-value">{{ getStrategyLabel(localData.strategy) }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">倍数:</span>
            <span class="preview-value">{{ localData.ratio }}x</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">原始样本:</span>
            <span class="preview-value">{{ selectedDataset?.row_count || 0 }} 条</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">增强后:</span>
            <span class="preview-value preview-highlight">
              {{ Math.round((selectedDataset?.row_count || 0) * localData.ratio) }} 条
            </span>
          </div>
          <div class="preview-row">
            <span class="preview-label">数据类型:</span>
            <span class="preview-value">
              <span
                class="dataset-type-badge"
                :class="detectedType"
              >
                {{ detectedType === 'image' ? '图像' : detectedType === 'text' ? '文本' : '表格' }}
              </span>
            </span>
          </div>
          <div
            v-if="selectedDataset?.size_bytes"
            class="preview-row"
          >
            <span class="preview-label">预估大小:</span>
            <span class="preview-value">{{ formatSize((selectedDataset?.size_bytes || 0) * localData.ratio) }}</span>
          </div>
        </div>
      </div>
    </el-form>

    <!-- 数据集选择对话框 -->
    <el-dialog
      v-model="showDatasetDialog"
      title="选择数据集"
      width="700px"
      :close-on-click-modal="false"
    >
      <div class="dataset-dialog-content">
        <div class="dataset-search">
          <el-input
            v-model="datasetSearch"
            placeholder="搜索数据集..."
            prefix-icon="Search"
            clearable
            @input="handleDatasetSearch"
          />
        </div>

        <el-table
          v-loading="loadingDatasets"
          :data="datasets"
          style="width: 100%"
          height="400"
          :highlight-current-row="true"
          @row-click="handleDatasetRowClick"
        >
          <el-table-column
            prop="name"
            label="名称"
            min-width="150"
          />
          <el-table-column
            prop="format"
            label="格式"
            width="80"
          >
            <template #default="{ row }">
              <el-tag size="small">
                {{ row.format_display || row.format }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="row_count"
            label="行数"
            width="100"
          />
          <el-table-column
            prop="size_display"
            label="大小"
            width="100"
          />
          <el-table-column
            prop="status"
            label="状态"
            width="90"
          >
            <template #default="{ row }">
              <el-tag
                :type="row.is_ready ? 'success' : 'warning'"
                size="small"
              >
                {{ row.is_ready ? '就绪' : '处理中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="创建时间"
            width="160"
          >
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="showDatasetDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!localData.datasetId"
          @click="confirmDatasetSelection"
        >
          确认选择
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { Plus, ArrowDown, ArrowUp } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { augmentationApi } from '@/api/augmentation'
import { datasetApi } from '@/api/dataset'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

// State
const localData = reactive({
  label: '',
  description: '',
  datasetId: '',
  outputMode: 'create_new',
  outputName: '',
  strategy: 'all',
  transformations: [],
  ratio: 2.0,
})

const datasets = ref([])
const selectedDataset = ref(null)
const loadingDatasets = ref(false)
const showDatasetDialog = ref(false)
const datasetSearch = ref('')
const showAdvanced = ref(false)
const activePreset = ref(null)
const transformationsJson = ref('[]')

// Presets
const presets = ref([
  { id: 'image_classification', name: '图像分类', strategy: 'all', ratio: 3.0, transformations: ['rotate', 'flip_h', 'flip_v', 'brightness', 'contrast'] },
  { id: 'object_detection', name: '目标检测', strategy: 'geometric', ratio: 5.0, transformations: ['rotate', 'flip_h', 'flip_v', 'scale', 'crop'] },
  { id: 'text_classification', name: '文本分类', strategy: 'all', ratio: 2.0, transformations: ['synonym_replacement', 'random_swap', 'random_insertion'] },
  { id: 'tabular_balance', name: '表格平衡', strategy: 'all', ratio: 2.0, transformations: ['smote', 'noise', 'shuffle'] },
])

// Transforms by strategy
const transformOptions = {
  geometric: [
    { value: 'rotate', label: '旋转', enabled: true },
    { value: 'flip_h', label: '水平翻转', enabled: true },
    { value: 'flip_v', label: '垂直翻转', enabled: true },
    { value: 'scale', label: '缩放', enabled: false },
    { value: 'crop', label: '裁剪', enabled: false },
    { value: 'translate', label: '平移', enabled: false },
  ],
  color: [
    { value: 'brightness', label: '亮度', enabled: true },
    { value: 'contrast', label: '对比度', enabled: true },
    { value: 'saturation', label: '饱和度', enabled: false },
    { value: 'hue', label: '色调', enabled: false },
    { value: 'grayscale', label: '灰度', enabled: false },
  ],
  noise: [
    { value: 'gaussian_noise', label: '高斯噪声', enabled: true },
    { value: 'random_erasing', label: '随机擦除', enabled: false },
    { value: 'salt_pepper', label: '盐噪声', enabled: false },
  ],
  text: [
    { value: 'synonym_replacement', label: '同义词替换', enabled: true },
    { value: 'random_insertion', label: '随机插入', enabled: true },
    { value: 'random_swap', label: '随机交换', enabled: true },
    { value: 'back_translation', label: '回译', enabled: false },
  ],
  tabular: [
    { value: 'smote', label: 'SMOTE', enabled: false },
    { value: 'noise', label: '噪声注入', enabled: true },
    { value: 'shuffle', label: '行打乱', enabled: true },
  ],
  all: [
    { value: 'rotate', label: '旋转', enabled: true },
    { value: 'flip_h', label: '水平翻转', enabled: true },
    { value: 'flip_v', label: '垂直翻转', enabled: true },
    { value: 'brightness', label: '亮度', enabled: true },
    { value: 'contrast', label: '对比度', enabled: true },
    { value: 'gaussian_noise', label: '高斯噪声', enabled: true },
    { value: 'synonym_replacement', label: '同义词替换', enabled: true },
    { value: 'random_swap', label: '随机交换', enabled: true },
  ],
}

const availableTransforms = computed(() => {
  return transformOptions[localData.strategy] || transformOptions.all
})

const detectedType = computed(() => {
  if (!selectedDataset.value) return 'unknown'
  const format = selectedDataset.value.format
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(format?.toLowerCase())) {
    return 'image'
  }
  if (['csv', 'parquet'].includes(format?.toLowerCase())) {
    return 'tabular'
  }
  return 'text'
})

const ratioMarks = {
  1: '1x',
  2: '2x',
  5: '5x',
  10: '10x',
}

// Methods
const searchDatasets = async (query) => {
  if (!query && datasets.value.length > 0) return
  loadingDatasets.value = true
  try {
    const result = await datasetApi.list({ search: query, status: 'ready', page_size: 50 })
    datasets.value = result.results || result || []
  } catch (error) {
    console.error('Failed to load datasets:', error)
  } finally {
    loadingDatasets.value = false
  }
}

const loadDatasets = async () => {
  await searchDatasets('')
}

const handleDatasetSearch = () => {
  searchDatasets(datasetSearch.value)
}

const handleDatasetChange = (datasetId) => {
  selectedDataset.value = datasets.value.find(ds => ds.id === datasetId) || null
  if (selectedDataset.value && localData.outputMode === 'create_new' && !localData.outputName) {
    localData.outputName = `${selectedDataset.value.name}_augmented`
  }
  handleChange()
}

const handleDatasetRowClick = (row) => {
  localData.datasetId = row.id
  handleDatasetChange(row.id)
}

const confirmDatasetSelection = () => {
  showDatasetDialog.value = false
  ElMessage.success(`已选择数据集: ${selectedDataset.value?.name}`)
}

const applyPreset = (preset) => {
  activePreset.value = preset.id
  localData.strategy = preset.strategy
  localData.ratio = preset.ratio
  localData.transformations = [...preset.transformations]
  transformationsJson.value = JSON.stringify(preset.transformations)
  handleChange()
}

const handleStrategyChange = () => {
  const enabledTransforms = availableTransforms.value.filter(t => t.enabled).map(t => t.value)
  localData.transformations = enabledTransforms
  transformationsJson.value = JSON.stringify(enabledTransforms)
  activePreset.value = null
  handleChange()
}

const handleTransformsChange = () => {
  const enabledTransforms = availableTransforms.value.filter(t => t.enabled).map(t => t.value)
  localData.transformations = enabledTransforms
  transformationsJson.value = JSON.stringify(enabledTransforms)
  activePreset.value = null
  handleChange()
}

const handleTransformsJsonChange = () => {
  try {
    const parsed = JSON.parse(transformationsJson.value)
    if (Array.isArray(parsed)) {
      localData.transformations = parsed
      activePreset.value = null
    }
  } catch (e) {
    // Invalid JSON, ignore
  }
  handleChange()
}

const getStrategyLabel = (strategy) => {
  const labels = {
    geometric: '几何变换',
    color: '颜色变换',
    noise: '噪声注入',
    mixup: '混合增强',
    all: '全部策略',
  }
  return labels[strategy] || strategy
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

// Watch for prop changes
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      datasetId: newVal.datasetId || '',
      outputMode: newVal.outputMode || 'create_new',
      outputName: newVal.outputName || '',
      strategy: newVal.strategy || 'all',
      transformations: newVal.transformations || [],
      ratio: newVal.ratio ?? 2.0,
    })
    transformationsJson.value = JSON.stringify(newVal.transformations || [])
    
    if (newVal.datasetId && datasets.value.length === 0) {
      loadDatasets().then(() => {
        selectedDataset.value = datasets.value.find(ds => ds.id === newVal.datasetId) || null
      })
    }
  }
}, { immediate: true, deep: true })

// Load presets on mount
onMounted(async () => {
  try {
    const result = await augmentationApi.getPresets()
    if (result && result.length > 0) {
      presets.value = result.map(p => ({
        id: p.id,
        name: p.name,
        strategy: p.strategy,
        ratio: p.ratio,
        transformations: p.transformations || [],
      }))
    }
  } catch (error) {
    console.error('Failed to load presets:', error)
  }
  loadDatasets()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.config-form {
  padding: 0;
}

.form-section {
  margin-bottom: $spacing-5;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;

  .section-title {
    margin-bottom: 0;
  }

  .el-icon {
    color: var(--text-tertiary);
    transition: transform 0.2s;
  }
}

.dataset-selector {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.dataset-option {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .dataset-name {
    font-weight: 500;
  }

  .dataset-meta {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.dataset-type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: $radius-sm;
  font-size: $font-size-xs;
  font-weight: 500;
  margin-left: $spacing-2;

  &.image {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }

  &.text {
    background: rgba(139, 92, 246, 0.1);
    color: #8b5cf6;
  }

  &.tabular {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
  }

  &.unknown {
    background: var(--bg-tertiary);
    color: var(--text-tertiary);
  }
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  margin-bottom: $spacing-4;
}

.ratio-input-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-3;

  .el-slider {
    flex: 1;
  }

  .el-input-number {
    width: 100px;
  }
}

.transforms-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-2;
}

.advanced-options {
  margin-top: $spacing-4;
}

.json-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.config-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.preview-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .preview-label {
    color: var(--text-tertiary);
    min-width: 80px;
  }

  .preview-value {
    color: var(--text-primary);
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }

  .preview-highlight {
    color: var(--color-primary);
    font-weight: 600;
  }
}

.dataset-dialog-content {
  .dataset-search {
    margin-bottom: $spacing-4;
  }
}
</style>
