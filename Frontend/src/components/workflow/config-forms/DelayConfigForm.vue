<template>
  <div class="config-form delay-config-form">
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

      <!-- 延迟类型 -->
      <div class="form-section">
        <h4 class="section-title">
          延迟配置
        </h4>
        
        <el-form-item label="延迟类型">
          <el-radio-group
            v-model="localData.delayType"
            @change="handleChange"
          >
            <el-radio value="fixed">
              固定延迟
            </el-radio>
            <el-radio value="random">
              随机延迟
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 固定延迟 -->
        <template v-if="localData.delayType === 'fixed'">
          <el-form-item label="延迟时长">
            <el-input-number
              v-model="localData.duration"
              :min="1"
              :max="3600"
              controls-position="right"
              style="width: 100%"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="时间单位">
            <el-select
              v-model="localData.unit"
              @change="handleChange"
            >
              <el-option
                label="秒"
                value="seconds"
              />
              <el-option
                label="分钟"
                value="minutes"
              />
              <el-option
                label="小时"
                value="hours"
              />
            </el-select>
          </el-form-item>

          <div class="delay-preview">
            <span class="preview-text">将延迟 {{ formattedDuration }}</span>
          </div>
        </template>

        <!-- 随机延迟 -->
        <template v-else>
          <el-form-item label="最小延迟">
            <el-input-number
              v-model="localData.minDelay"
              :min="1"
              :max="3600"
              controls-position="right"
              style="width: 100%"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="最大延迟">
            <el-input-number
              v-model="localData.maxDelay"
              :min="1"
              :max="3600"
              controls-position="right"
              style="width: 100%"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="时间单位">
            <el-select
              v-model="localData.unit"
              @change="handleChange"
            >
              <el-option
                label="秒"
                value="seconds"
              />
              <el-option
                label="分钟"
                value="minutes"
              />
              <el-option
                label="小时"
                value="hours"
              />
            </el-select>
          </el-form-item>

          <div class="delay-preview">
            <span class="preview-text">将在 {{ formattedMinDelay }} 至 {{ formattedMaxDelay }} 之间随机延迟</span>
          </div>
        </template>
      </div>

      <!-- 时间范围 -->
      <div class="form-section">
        <h4 class="section-title">
          执行时间窗口（可选）
        </h4>
        
        <el-form-item label="限制时间范围">
          <el-switch
            v-model="localData.hasTimeWindow"
            @change="handleChange"
          />
          <span class="field-hint">启用后，仅在指定时间段内执行延迟</span>
        </el-form-item>

        <template v-if="localData.hasTimeWindow">
          <el-form-item label="开始时间">
            <el-time-select
              v-model="localData.windowStart"
              placeholder="开始时间"
              style="width: 100%"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="结束时间">
            <el-time-select
              v-model="localData.windowEnd"
              placeholder="结束时间"
              style="width: 100%"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="窗口外策略">
            <el-select
              v-model="localData.outsideWindowStrategy"
              @change="handleChange"
            >
              <el-option
                label="等待到窗口开始"
                value="wait"
              />
              <el-option
                label="跳过延迟"
                value="skip"
              />
              <el-option
                label="立即执行"
                value="execute"
              />
            </el-select>
          </el-form-item>
        </template>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          延迟预览
        </h4>
        <div class="delay-info">
          <div class="info-row">
            <el-tag
              size="small"
              type="primary"
            >
              {{ localData.delayType === 'fixed' ? '固定延迟' : '随机延迟' }}
            </el-tag>
            <span class="delay-value">{{ previewText }}</span>
          </div>
          <div
            v-if="localData.hasTimeWindow"
            class="info-row"
          >
            <el-tag
              size="small"
              type="info"
            >
              时间窗口
            </el-tag>
            <span class="window-text">{{ localData.windowStart || '00:00' }} - {{ localData.windowEnd || '23:59' }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'

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
  delayType: 'fixed',
  duration: 1,
  minDelay: 1,
  maxDelay: 10,
  unit: 'seconds',
  hasTimeWindow: false,
  windowStart: '',
  windowEnd: '',
  outsideWindowStrategy: 'wait'
})

const unitMultiplier = computed(() => {
  const multipliers = {
    seconds: 1,
    minutes: 60,
    hours: 3600
  }
  return multipliers[localData.unit] || 1
})

const unitLabel = computed(() => {
  const labels = {
    seconds: '秒',
    minutes: '分钟',
    hours: '小时'
  }
  return labels[localData.unit] || '秒'
})

const formattedDuration = computed(() => {
  const duration = localData.duration * unitMultiplier.value
  if (duration >= 3600) {
    return `${Math.floor(duration / 3600)} 小时 ${Math.floor((duration % 3600) / 60)} 分钟`
  } else if (duration >= 60) {
    return `${Math.floor(duration / 60)} 分钟 ${duration % 60} 秒`
  }
  return `${duration} 秒`
})

const formattedMinDelay = computed(() => {
  const delay = localData.minDelay * unitMultiplier.value
  if (delay >= 3600) {
    return `${Math.floor(delay / 3600)} 小时`
  } else if (delay >= 60) {
    return `${Math.floor(delay / 60)} 分钟`
  }
  return `${delay} 秒`
})

const formattedMaxDelay = computed(() => {
  const delay = localData.maxDelay * unitMultiplier.value
  if (delay >= 3600) {
    return `${Math.floor(delay / 3600)} 小时`
  } else if (delay >= 60) {
    return `${Math.floor(delay / 60)} 分钟`
  }
  return `${delay} 秒`
})

const previewText = computed(() => {
  if (localData.delayType === 'fixed') {
    return formattedDuration.value
  }
  return `${formattedMinDelay.value} ~ ${formattedMaxDelay.value}`
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      delayType: newVal.delayType || 'fixed',
      duration: newVal.duration || 1,
      minDelay: newVal.minDelay || 1,
      maxDelay: newVal.maxDelay || 10,
      unit: newVal.unit || 'seconds',
      hasTimeWindow: newVal.hasTimeWindow || false,
      windowStart: newVal.windowStart || '',
      windowEnd: newVal.windowEnd || '',
      outsideWindowStrategy: newVal.outsideWindowStrategy || 'wait'
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
  margin-left: $spacing-2;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.delay-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .preview-text {
    font-size: $font-size-sm;
    color: var(--text-primary);
  }
}

.delay-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .info-row {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  .delay-value {
    font-size: $font-size-sm;
    color: var(--text-primary);
    font-weight: $font-weight-medium;
  }

  .window-text {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}
</style>
