<template>
  <div class="config-form video-generation-config-form">
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

      <!-- 服务商配置 -->
      <div class="form-section">
        <h4 class="section-title">
          服务商配置
        </h4>
        
        <el-form-item label="AI 提供商">
          <el-select
            v-model="localData.provider"
            placeholder="选择提供商"
            @change="handleProviderChange"
          >
            <el-option
              label="Replicate"
              value="replicate"
            />
            <el-option
              label="Runway"
              value="runway"
            />
            <el-option
              label="Pika"
              value="pika"
            />
            <el-option
              label="Agnes AI (agnes-video-v2.0)"
              value="agnes"
            />
            <el-option
              label="阿里云百炼 (通义万相 Wanx)"
              value="dashscope"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="模型">
          <el-input
            v-model="localData.model"
            placeholder="输入模型名称"
            @change="handleChange"
          />
          <div class="field-hint">
            例如: models/video-generation, wanx2.1-t2v-turbo
          </div>
        </el-form-item>
      </div>

      <!-- 视频生成配置 -->
      <div class="form-section">
        <h4 class="section-title">
          生成配置
        </h4>
        
        <el-form-item
          label="提示词"
          required
        >
          <el-input
            v-model="localData.prompt"
            type="textarea"
            :rows="4"
            placeholder="描述你想要生成的视频内容..."
            class="prompt-input"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="时长 (秒)">
          <el-input-number
            v-model="localData.duration"
            :min="1"
            :max="60"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div
            v-if="localData.provider === 'dashscope'"
            class="field-hint"
          >
            wanx2.1-t2v-turbo/plus 固定输出 5 秒视频，此设置将被忽略
          </div>
        </el-form-item>

        <el-form-item label="帧率 (FPS)">
          <el-input-number
            v-model="localData.fps"
            :min="1"
            :max="60"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="分辨率">
          <el-select
            v-model="localData.resolution"
            @change="handleChange"
          >
            <el-option
              label="720p"
              value="720p"
            />
            <el-option
              label="1080p"
              value="1080p"
            />
            <el-option
              label="4K"
              value="4k"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="localData.provider === 'agnes'"
          label="生成模式"
        >
          <el-select
            v-model="localData.mode"
            @change="handleGenerationModeChange"
          >
            <el-option
              label="自动 / 首帧控制"
              value=""
            />
            <el-option
              label="文字直接生成"
              value="text"
            />
            <el-option
              label="参考图片生成"
              value="reference"
            />
            <el-option
              label="首尾帧控制"
              value="keyframe"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="localData.mode === 'reference'"
          label="参考图片（每行一个URL）"
        >
          <el-input
            v-model="referenceImagesText"
            type="textarea"
            :rows="3"
            aria-label="视频参考图片"
            placeholder="可填写上游图片变量或公开图片URL"
            @change="handleChange"
          />
          <div class="field-hint">
            Flash 最多 5 张；参考模式将图像用于内容与风格控制。
          </div>
        </el-form-item>
        <el-form-item
          v-if="localData.mode !== 'reference'"
          label="输入图像 (图生视频)"
        >
          <el-input
            v-model="localData.inputImage"
            placeholder="{images.0.url} 或粘贴图片 URL"
            @change="handleChange"
          />
          <div class="field-hint">
            连接文生图节点后使用 <code>{images.0.url}</code> 自动引用上游生成图；留空时后端也会自动取上游 images
          </div>
        </el-form-item>
        <el-form-item
          v-if="localData.mode === 'keyframe'"
          label="尾帧图像（可选）"
        >
          <el-input
            v-model="localData.lastFrame"
            placeholder="尾帧图片URL或上游变量"
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
            <span class="preview-label">提供商:</span>
            <span class="preview-value">{{ localData.provider || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">模型:</span>
            <span class="preview-value">{{ localData.model || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">时长:</span>
            <span class="preview-value">{{ localData.duration || 4 }}秒</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">分辨率:</span>
            <span class="preview-value">{{ localData.resolution || '720p' }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'

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
  provider: 'replicate',
  model: '',
  prompt: '',
  duration: 4,
  fps: 24,
  resolution: '720p',
  inputImage: '{images.0.url}',
  mode: '',
  referenceImages: []
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    for (const key of Object.keys(localData)) delete localData[key]
    Object.assign(localData, {
      ...newVal,
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'replicate',
      model: newVal.model || '',
      prompt: newVal.prompt || '',
      duration: newVal.duration ?? 4,
      fps: newVal.fps ?? 24,
      resolution: newVal.resolution || '720p',
      inputImage: newVal.inputImage ?? '{images.0.url}',
      mode: newVal.mode || '',
      referenceImages: newVal.referenceImages || newVal.reference_images || [],
      lastFrame: newVal.lastFrame || newVal.last_frame || ''
    })
  }
}, { immediate: true, deep: true })

const referenceImagesText = computed({
  get: () => Array.isArray(localData.referenceImages) ? localData.referenceImages.join('\n') : String(localData.referenceImages || ''),
  set: (value) => { localData.referenceImages = value.split('\n').map(url => url.trim()).filter(Boolean) }
})

const defaultModels = {
  dashscope: 'wanx2.1-t2v-turbo',
  agnes: 'agnes-video-v2.0'
}

const handleProviderChange = () => {
  if (!localData.model || Object.values(defaultModels).includes(localData.model)) {
    localData.model = defaultModels[localData.provider] || ''
  }
  handleChange()
}

const handleGenerationModeChange = () => {
  if (localData.mode !== 'reference') localData.referenceImages = []
  handleChange()
}

const handleChange = () => {
  const config = { ...props.modelValue, ...localData }
  emit('update:modelValue', config)
  emit('change', config)
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

.prompt-input {
  :deep(.el-textarea__inner) {
    font-family: inherit;
    line-height: 1.6;
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
}
</style>
