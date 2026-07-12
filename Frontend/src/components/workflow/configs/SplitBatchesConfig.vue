<template>
  <div class="config-form split-batches-config">
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
          批次配置
        </h4>
        
        <el-form-item label="每批数量">
          <el-input-number
            v-model="localData.batchSize"
            :min="1"
            :max="1000"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            每个批次包含的数据条数
          </div>
        </el-form-item>

        <el-form-item label="并发数">
          <el-slider
            v-model="localData.concurrency"
            :min="1"
            :max="10"
            :step="1"
            :marks="concurrencyMarks"
            @change="handleChange"
          />
          <div class="field-hint">
            同时处理的批次数量 (1-10)
          </div>
        </el-form-item>

        <el-form-item label="输出完成信号">
          <el-switch
            v-model="localData.doneOutput"
            @change="handleChange"
          />
          <span class="field-hint">处理完所有批次后输出完成信号到"完成"端口</span>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          处理流程
        </h4>
        <div class="flow-diagram">
          <div class="flow-step input">
            <div class="step-icon">
              1
            </div>
            <div class="step-content">
              <strong>输入数据</strong>
              <span>数组或可迭代对象</span>
            </div>
          </div>
          <div class="flow-arrow">
            <ArrowDown :size="16" />
          </div>
          <div class="flow-step split">
            <div class="step-icon">
              2
            </div>
            <div class="step-content">
              <strong>批量分割</strong>
              <span>拆分为多个批次</span>
            </div>
          </div>
          <div class="flow-arrow">
            <ArrowDown :size="16" />
          </div>
          <div class="flow-branches">
            <div class="flow-branch batch">
              <ArrowRight :size="16" />
              <div class="branch-content">
                <strong>批次</strong>
                <span>逐批处理后续节点</span>
              </div>
            </div>
            <div class="flow-branch done">
              <ArrowRight :size="16" />
              <div class="branch-content">
                <strong>完成</strong>
                <span>所有批次处理完毕</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">每批数量</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ localData.batchSize }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">并发数</span>
            <el-tag size="small">
              {{ localData.concurrency }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">完成信号</span>
            <el-tag
              size="small"
              :type="localData.doneOutput ? 'success' : 'info'"
            >
              {{ localData.doneOutput ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { ArrowDown, ArrowRight } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '批量分割',
  batchSize: 10,
  concurrency: 1,
  doneOutput: true
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '批量分割',
      batchSize: newVal.batchSize ?? 10,
      concurrency: newVal.concurrency ?? 1,
      doneOutput: newVal.doneOutput ?? true
    })
  }
}, { immediate: true, deep: true })

const concurrencyMarks = {
  1: '1',
  3: '3',
  5: '5',
  7: '7',
  10: '10'
}

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

.flow-diagram {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  padding: $spacing-4;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .step-icon {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #3b82f6;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-sm;
    font-weight: $font-weight-bold;
    flex-shrink: 0;
  }

  .step-content {
    display: flex;
    flex-direction: column;
    gap: 2px;

    strong {
      font-size: $font-size-sm;
      color: var(--text-primary);
    }

    span {
      font-size: $font-size-xs;
      color: var(--text-tertiary);
    }
  }
}

.flow-arrow {
  display: flex;
  justify-content: center;
  padding: $spacing-2;
  color: var(--text-tertiary);
}

.flow-branches {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-2;
}

.flow-branch {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2;
  border-radius: $radius-md;
  border: 1px solid;

  &.batch {
    background: rgba(132, 204, 22, 0.1);
    border-color: rgba(132, 204, 22, 0.3);
    color: #84cc16;
  }

  &.done {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
    color: #3b82f6;
  }

  .branch-content {
    display: flex;
    flex-direction: column;
    gap: 1px;

    strong {
      font-size: $font-size-xs;
    }

    span {
      font-size: 10px;
      opacity: 0.8;
    }
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
}
</style>
