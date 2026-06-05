<template>
  <div class="config-form model-deployment-config-form">
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

      <!-- 部署配置 -->
      <div class="form-section">
        <h4 class="section-title">
          部署配置
        </h4>
        
        <el-form-item label="部署平台">
          <el-select
            v-model="localData.platform"
            @change="handleChange"
          >
            <el-option
              label="本地部署 (Local)"
              value="local"
            />
            <el-option
              label="AWS SageMaker"
              value="sagemaker"
            />
            <el-option
              label="Lambda GPU"
              value="lambdagpu"
            />
            <el-option
              label="NVIDIA Triton"
              value="triton"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="端点类型">
          <el-select
            v-model="localData.endpointType"
            @change="handleChange"
          >
            <el-option
              label="实时推理 (Realtime)"
              value="realtime"
            />
            <el-option
              label="批量处理 (Batch)"
              value="batch"
            />
            <el-option
              label="异步处理 (Async)"
              value="async"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="模型路径"
          required
        >
          <el-input
            v-model="localData.modelPath"
            placeholder="/path/to/model"
            @change="handleChange"
          />
          <div class="field-hint">
            模型文件路径或S3路径
          </div>
        </el-form-item>
      </div>

      <!-- 自动扩缩容 -->
      <div class="form-section">
        <h4 class="section-title">
          自动扩缩容
        </h4>
        
        <el-form-item label="启用自动扩缩容">
          <el-switch
            v-model="localData.autoscaling"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.autoscaling"
          label="最小实例数"
        >
          <el-input-number
            v-model="localData.minInstances"
            :min="1"
            :max="100"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.autoscaling"
          label="最大实例数"
        >
          <el-input-number
            v-model="localData.maxInstances"
            :min="1"
            :max="1000"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">平台:</span>
            <span class="preview-value">{{ localData.platform || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">端点:</span>
            <span class="preview-value">{{ localData.endpointType || 'realtime' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">自动扩缩:</span>
            <el-tag
              size="small"
              :type="localData.autoscaling ? 'success' : 'info'"
            >
              {{ localData.autoscaling ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '',
  description: '',
  platform: 'local',
  endpointType: 'realtime',
  autoscaling: false,
  minInstances: 1,
  maxInstances: 5,
  modelPath: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      platform: newVal.platform || 'local',
      endpointType: newVal.endpointType || 'realtime',
      autoscaling: newVal.autoscaling ?? false,
      minInstances: newVal.minInstances ?? 1,
      maxInstances: newVal.maxInstances ?? 5,
      modelPath: newVal.modelPath || ''
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}
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
}
</style>
