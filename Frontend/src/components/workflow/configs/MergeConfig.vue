<template>
  <div class="config-form merge-config">
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
          合并配置
        </h4>
        
        <el-form-item label="合并模式">
          <el-select
            v-model="localData.mode"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="合并 (combine)"
              value="combine"
            >
              <div class="option-content">
                <span class="option-label">合并</span>
                <span class="option-desc">将所有输入合并为一个数组或对象</span>
              </div>
            </el-option>
            <el-option
              label="覆盖 (override)"
              value="override"
            >
              <div class="option-content">
                <span class="option-label">覆盖</span>
                <span class="option-desc">后面的输入覆盖前面的相同字段</span>
              </div>
            </el-option>
            <el-option
              label="配对 (zip)"
              value="zip"
            >
              <div class="option-content">
                <span class="option-label">配对</span>
                <span class="option-desc">按索引将数组元素一一配对</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="冲突解决策略">
          <el-select
            v-model="localData.conflictResolution"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="使用左侧数据"
              value="left"
            />
            <el-option
              label="使用右侧数据"
              value="right"
            />
            <el-option
              label="使用默认值"
              value="override"
            />
          </el-select>
          <div class="field-hint">
            当多个输入有相同字段时的处理策略
          </div>
        </el-form-item>

        <el-form-item label="去重">
          <el-switch
            v-model="localData.deduplicate"
            @change="handleChange"
          />
          <span class="field-hint">移除合并结果中的重复项</span>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          输入连接
        </h4>
        <div class="input-hints">
          <div class="hint-item">
            <div class="hint-icon input1">
              1
            </div>
            <span>输入 1 - 连接到前一个节点的输出</span>
          </div>
          <div class="hint-item">
            <div class="hint-icon input2">
              2
            </div>
            <span>输入 2 - 连接到另一个节点的输出</span>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">模式</span>
            <el-tag size="small">
              {{ modeLabel }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">冲突策略</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ conflictLabel }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">去重</span>
            <el-tag
              size="small"
              :type="localData.deduplicate ? 'success' : 'info'"
            >
              {{ localData.deduplicate ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '合并数据',
  mode: 'combine',
  conflictResolution: 'right',
  deduplicate: false
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '合并数据',
      mode: newVal.mode || 'combine',
      conflictResolution: newVal.conflictResolution || 'right',
      deduplicate: newVal.deduplicate ?? false
    })
  }
}, { immediate: true, deep: true })

const modeLabel = computed(() => {
  const modes = { combine: '合并', override: '覆盖', zip: '配对' }
  return modes[localData.mode] || localData.mode
})

const conflictLabel = computed(() => {
  const strategies = { left: '左侧优先', right: '右侧优先', override: '默认覆盖' }
  return strategies[localData.conflictResolution] || localData.conflictResolution
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
  margin-left: $spacing-2;
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

.input-hints {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2;
  background: var(--bg-secondary);
  border-radius: $radius-sm;
  font-size: $font-size-sm;
  color: var(--text-secondary);
}

.hint-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-size-xs;
  font-weight: $font-weight-bold;
  color: white;

  &.input1 { background: #3b82f6; }
  &.input2 { background: #10b981; }
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
}
</style>
