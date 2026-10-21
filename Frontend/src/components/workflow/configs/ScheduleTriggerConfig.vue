<template>
  <div class="config-form schedule-trigger-config">
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
      </div>

      <div class="form-section">
        <h4 class="section-title">
          触发方式
        </h4>
        
        <el-form-item label="调度类型">
          <el-radio-group
            v-model="localData.scheduleType"
            @change="handleChange"
          >
            <el-radio value="cron">
              Cron 表达式
            </el-radio>
            <el-radio value="interval">
              间隔触发
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="localData.scheduleType === 'cron'"
          label="Cron 表达式"
        >
          <el-input
            v-model="localData.cron"
            placeholder="0 * * * *"
            @change="handleChange"
          />
          <div class="field-hint">
            格式: 分 时 日 月 周<br>
            例如: 0 9 * * * (每天9点) 或 */5 * * * * (每5分钟)
          </div>
          <div class="cron-helper">
            <el-button
              size="small"
              @click="setCron('*/5 * * * *')"
            >
              每5分钟
            </el-button>
            <el-button
              size="small"
              @click="setCron('0 * * * *')"
            >
              每小时
            </el-button>
            <el-button
              size="small"
              @click="setCron('0 9 * * *')"
            >
              每天9点
            </el-button>
            <el-button
              size="small"
              @click="setCron('0 9 * * 1-5')"
            >
              工作日9点
            </el-button>
          </div>
        </el-form-item>

        <el-form-item
          v-if="localData.scheduleType === 'interval'"
          label="间隔时间（秒）"
        >
          <el-input-number
            v-model="localData.interval"
            :min="1"
            :max="86400"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            最小间隔: 1 秒
          </div>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          时间配置
        </h4>
        
        <el-form-item label="时区">
          <el-select
            v-model="localData.timezone"
            filterable
            placeholder="选择时区"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="UTC"
              value="UTC"
            />
            <el-option
              label="Asia/Shanghai (北京时间)"
              value="Asia/Shanghai"
            />
            <el-option
              label="Asia/Tokyo (东京时间)"
              value="Asia/Tokyo"
            />
            <el-option
              label="America/New_York (纽约时间)"
              value="America/New_York"
            />
            <el-option
              label="Europe/London (伦敦时间)"
              value="Europe/London"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="开始日期（可选）">
          <el-date-picker
            v-model="localData.startDate"
            type="datetime"
            placeholder="选择开始日期"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="结束日期（可选）">
          <el-date-picker
            v-model="localData.endDate"
            type="datetime"
            placeholder="选择结束日期"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">触发方式</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ localData.scheduleType === 'cron' ? 'Cron' : '间隔' }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">时区</span>
            <span class="preview-value">{{ localData.timezone }}</span>
          </div>
          <div
            v-if="localData.scheduleType === 'cron'"
            class="preview-row"
          >
            <span class="preview-label">Cron</span>
            <span class="preview-value">{{ localData.cron }}</span>
          </div>
          <div
            v-else
            class="preview-row"
          >
            <span class="preview-label">间隔</span>
            <span class="preview-value">每 {{ localData.interval }} 秒</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '定时触发器',
  scheduleType: 'interval',
  cron: '',
  interval: 60,
  timezone: 'UTC',
  startDate: null,
  endDate: null
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '定时触发器',
      scheduleType: newVal.scheduleType || (newVal.cron ? 'cron' : 'interval'),
      cron: newVal.cron || '',
      interval: newVal.interval || 60,
      timezone: newVal.timezone || 'UTC',
      startDate: newVal.startDate || null,
      endDate: newVal.endDate || null
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

const setCron = (cron) => {
  localData.cron = cron
  handleChange()
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
  line-height: 1.5;
}

.cron-helper {
  margin-top: $spacing-2;
  display: flex;
  gap: $spacing-2;
  flex-wrap: wrap;
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
  justify-content: space-between;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .preview-label {
    color: var(--text-tertiary);
  }

  .preview-value {
    color: var(--text-primary);
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}
</style>
