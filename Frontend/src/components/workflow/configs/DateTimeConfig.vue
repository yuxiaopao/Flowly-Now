<template>
  <div class="config-form datetime-config">
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
          日期时间操作
        </h4>
        
        <el-form-item label="操作类型">
          <el-select
            v-model="localData.operation"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="当前时间"
              value="now"
            >
              <div class="option-content">
                <span class="option-label">当前时间</span>
                <span class="option-desc">获取当前时间戳</span>
              </div>
            </el-option>
            <el-option
              label="今日"
              value="today"
            >
              <div class="option-content">
                <span class="option-label">今日</span>
                <span class="option-desc">获取今天日期（00:00:00）</span>
              </div>
            </el-option>
            <el-option
              label="格式化"
              value="format"
            >
              <div class="option-content">
                <span class="option-label">格式化</span>
                <span class="option-desc">将日期格式化为指定格式</span>
              </div>
            </el-option>
            <el-option
              label="解析"
              value="parse"
            >
              <div class="option-content">
                <span class="option-label">解析</span>
                <span class="option-desc">将字符串解析为日期</span>
              </div>
            </el-option>
            <el-option
              label="增加时间"
              value="add"
            >
              <div class="option-content">
                <span class="option-label">增加时间</span>
                <span class="option-desc">在输入日期基础上增加时间</span>
              </div>
            </el-option>
            <el-option
              label="减少时间"
              value="subtract"
            >
              <div class="option-content">
                <span class="option-label">减少时间</span>
                <span class="option-desc">在输入日期基础上减少时间</span>
              </div>
            </el-option>
            <el-option
              label="计算差值"
              value="diff"
            >
              <div class="option-content">
                <span class="option-label">计算差值</span>
                <span class="option-desc">计算两个日期之间的差值</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="['format', 'parse'].includes(localData.operation)"
          label="输入格式"
        >
          <el-input
            v-model="localData.inputFormat"
            placeholder="%Y-%m-%d %H:%M:%S"
            @change="handleChange"
          >
            <template #append>
              <el-tooltip content="Python strftime 格式">
                <Info :size="14" />
              </el-tooltip>
            </template>
          </el-input>
          <div class="field-hint">
            常用: %Y-%m-%d, %H:%M:%S, %Y-%m-%d %H:%M:%S
          </div>
        </el-form-item>

        <el-form-item
          v-if="['format', 'parse'].includes(localData.operation)"
          label="输出格式"
        >
          <el-input
            v-model="localData.outputFormat"
            placeholder="%Y-%m-%d %H:%M:%S"
            @change="handleChange"
          >
            <template #append>
              <el-tooltip content="Python strftime 格式">
                <Info :size="14" />
              </el-tooltip>
            </template>
          </el-input>
        </el-form-item>

        <template v-if="['add', 'subtract'].includes(localData.operation)">
          <el-form-item label="时间数量">
            <el-input-number
              v-model="localData.addAmount"
              :min="0"
              :max="9999"
              style="width: 100%"
              @change="handleChange"
            />
          </el-form-item>
          <el-form-item label="时间单位">
            <el-select
              v-model="localData.addUnit"
              style="width: 100%"
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
              <el-option
                label="天"
                value="days"
              />
              <el-option
                label="周"
                value="weeks"
              />
              <el-option
                label="月"
                value="months"
              />
              <el-option
                label="年"
                value="years"
              />
            </el-select>
          </el-form-item>
        </template>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          时区配置
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
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">操作</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ operationLabel }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">时区</span>
            <span class="preview-value">{{ localData.timezone }}</span>
          </div>
          <div
            v-if="['add', 'subtract'].includes(localData.operation)"
            class="preview-row"
          >
            <span class="preview-label">调整</span>
            <span class="preview-value">{{ localData.addAmount }} {{ addUnitLabel }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { Info } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '日期时间',
  operation: 'now',
  inputFormat: '',
  outputFormat: '%Y-%m-%d %H:%M:%S',
  timezone: 'UTC',
  addAmount: 1,
  addUnit: 'days'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '日期时间',
      operation: newVal.operation || 'now',
      inputFormat: newVal.inputFormat || '',
      outputFormat: newVal.outputFormat || '%Y-%m-%d %H:%M:%S',
      timezone: newVal.timezone || 'UTC',
      addAmount: newVal.addAmount ?? 1,
      addUnit: newVal.addUnit || 'days'
    })
  }
}, { immediate: true, deep: true })

const operationLabel = computed(() => {
  const labels = {
    now: '当前时间',
    today: '今日',
    format: '格式化',
    parse: '解析',
    add: '增加时间',
    subtract: '减少时间',
    diff: '计算差值'
  }
  return labels[localData.operation] || localData.operation
})

const addUnitLabel = computed(() => {
  const labels = {
    seconds: '秒',
    minutes: '分钟',
    hours: '小时',
    days: '天',
    weeks: '周',
    months: '月',
    years: '年'
  }
  return labels[localData.addUnit] || localData.addUnit
})

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

.option-content {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .option-label {
    font-weight: $font-weight-medium;
  }

  .option-desc {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
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
