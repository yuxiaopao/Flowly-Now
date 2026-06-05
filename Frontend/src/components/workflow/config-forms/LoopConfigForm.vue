<template>
  <div class="config-form loop-config-form">
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

      <!-- 循环类型 -->
      <div class="form-section">
        <h4 class="section-title">
          循环类型
        </h4>
        
        <div class="loop-type-grid">
          <div 
            class="loop-type-option"
            :class="{ active: localData.loopType === 'for' }"
            @click="selectLoopType('for')"
          >
            <Repeat class="type-icon" />
            <span class="type-label">For 循环</span>
            <span class="type-desc">指定次数循环</span>
          </div>
          <div 
            class="loop-type-option"
            :class="{ active: localData.loopType === 'while' }"
            @click="selectLoopType('while')"
          >
            <RefreshCw class="type-icon" />
            <span class="type-label">While 循环</span>
            <span class="type-desc">条件满足时循环</span>
          </div>
          <div 
            class="loop-type-option"
            :class="{ active: localData.loopType === 'foreach' }"
            @click="selectLoopType('foreach')"
          >
            <List class="type-icon" />
            <span class="type-label">ForEach 循环</span>
            <span class="type-desc">遍历数组/对象</span>
          </div>
        </div>
      </div>

      <!-- For 循环配置 -->
      <div
        v-if="localData.loopType === 'for'"
        class="form-section"
      >
        <h4 class="section-title">
          循环参数
        </h4>
        
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="起始值">
              <el-input-number
                v-model="localData.start"
                :min="0"
                controls-position="right"
                style="width: 100%"
                @change="handleChange"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="结束值">
              <el-input-number
                v-model="localData.end"
                :min="1"
                controls-position="right"
                style="width: 100%"
                @change="handleChange"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="步长">
              <el-input-number
                v-model="localData.step"
                :min="1"
                :max="100"
                controls-position="right"
                style="width: 100%"
                @change="handleChange"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="loop-preview">
          <code>for (i = {{ localData.start }}; i &lt; {{ localData.end }}; i += {{ localData.step }}) &#123; ... &#125;</code>
        </div>
      </div>

      <!-- While 循环配置 -->
      <div
        v-if="localData.loopType === 'while'"
        class="form-section"
      >
        <h4 class="section-title">
          循环条件
        </h4>
        
        <el-form-item label="循环条件 (JavaScript 表达式)">
          <el-input
            v-model="localData.whileCondition"
            type="textarea"
            :rows="3"
            placeholder="i < 10"
            class="condition-input"
            @change="handleChange"
          />
          <div class="field-hint">
            当表达式结果为 true 时继续循环，为 false 时退出
          </div>
        </el-form-item>

        <div class="loop-preview">
          <code>while ({{ localData.whileCondition || 'condition' }}) &#123; ... &#125;</code>
        </div>
      </div>

      <!-- ForEach 循环配置 -->
      <div
        v-if="localData.loopType === 'foreach'"
        class="form-section"
      >
        <h4 class="section-title">
          遍历配置
        </h4>
        
        <el-form-item label="数据源">
          <el-select
            v-model="localData.itemsSource"
            @change="handleChange"
          >
            <el-option
              label="输入变量"
              value="input"
            />
            <el-option
              label="静态数组"
              value="static"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="迭代变量名称">
          <el-input
            v-model="localData.loopVariable"
            placeholder="例如: item"
            @change="handleChange"
          />
          <div class="field-hint">
            在循环体中可以使用此变量名访问当前元素
          </div>
        </el-form-item>

        <el-form-item
          v-if="localData.itemsSource === 'input'"
          label="输入变量"
        >
          <el-input
            v-model="localData.items"
            placeholder="数组变量名"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.itemsSource === 'static'"
          label="静态数组"
        >
          <el-input
            v-model="localData.staticItems"
            type="textarea"
            :rows="3"
            placeholder="每行一个值，或 JSON 数组 [1, 2, 3]"
            @change="handleChange"
          />
        </el-form-item>

        <div class="loop-preview">
          <code>for ({{ localData.loopVariable || 'item' }} of {{ localData.items || 'items' }}) &#123; ... &#125;</code>
        </div>
      </div>

      <!-- 循环限制 -->
      <div class="form-section">
        <h4 class="section-title">
          循环限制
        </h4>
        
        <el-form-item label="最大迭代次数">
          <el-input-number
            v-model="localData.maxIterations"
            :min="1"
            :max="10000"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            防止无限循环，超过此次数将自动退出循环
          </div>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          循环预览
        </h4>
        <div class="loop-info">
          <el-tag
            size="small"
            type="primary"
          >
            {{ loopTypeLabel }}
          </el-tag>
          <span class="loop-count">最大 {{ localData.maxIterations }} 次迭代</span>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Repeat, RefreshCw, List } from 'lucide-vue-next'

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
  loopType: 'for',
  // For loop
  start: 0,
  end: 10,
  step: 1,
  // While loop
  whileCondition: 'i < 10',
  // ForEach loop
  itemsSource: 'input',
  items: '',
  staticItems: '',
  loopVariable: 'item',
  // Common
  maxIterations: 100
})

const loopTypeLabel = computed(() => {
  const labels = {
    for: 'For 循环',
    while: 'While 循环',
    foreach: 'ForEach 循环'
  }
  return labels[localData.loopType] || '循环'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      loopType: newVal.loopType || newVal.mode || 'for',
      start: newVal.start ?? 0,
      end: newVal.end ?? 10,
      step: newVal.step ?? 1,
      whileCondition: newVal.whileCondition || 'i < 10',
      itemsSource: newVal.itemsSource || 'input',
      items: newVal.items || '',
      staticItems: newVal.staticItems || '',
      loopVariable: newVal.loopVariable || 'item',
      maxIterations: newVal.maxIterations || 100
    })
  }
}, { immediate: true, deep: true })

const selectLoopType = (type) => {
  localData.loopType = type
  handleChange()
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

.loop-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-2;
}

.loop-type-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-1;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-primary);
  border-radius: $radius-md;
  cursor: pointer;
  transition: all $transition-fast;
  text-align: center;

  .type-icon {
    width: 24px;
    height: 24px;
    color: var(--text-tertiary);
  }

  .type-label {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }

  .type-desc {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }

  &:hover {
    border-color: var(--accent-primary);
  }

  &.active {
    border-color: var(--accent-primary);
    background: rgba(59, 130, 246, 0.08);

    .type-icon {
      color: var(--accent-primary);
    }
  }
}

.condition-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
  }
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.loop-preview {
  margin-top: $spacing-3;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  code {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    color: var(--accent-primary);
  }
}

.loop-info {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .loop-count {
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}
</style>
