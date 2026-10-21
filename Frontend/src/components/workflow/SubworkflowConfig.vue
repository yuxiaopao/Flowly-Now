<template>
  <div class="config-form subworkflow-config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <!-- 基本信息 -->
      <el-divider content-position="left">
        基本信息
      </el-divider>
      <el-form-item label="节点名称">
        <el-input
          v-model="localData.label"
          placeholder="输入节点名称"
          @input="markDirty"
        />
      </el-form-item>
      <el-form-item label="描述">
        <el-input 
          v-model="localData.description" 
          type="textarea" 
          :rows="2"
          placeholder="子工作流调用说明"
          @input="markDirty"
        />
      </el-form-item>

      <!-- 子工作流选择 -->
      <el-divider content-position="left">
        子工作流
      </el-divider>
      <el-form-item
        label="选择子工作流"
        required
      >
        <el-select
          v-model="localData.config.subworkflowId"
          placeholder="搜索或选择工作流"
          filterable
          remote
          :remote-method="searchSubworkflows"
          :loading="searching"
          @change="onWorkflowSelect"
        >
          <el-option
            v-for="wf in subworkflowOptions"
            :key="wf.id"
            :label="wf.name"
            :value="wf.id"
          >
            <div class="workflow-option-item">
              <Layers class="wf-icon" />
              <span>{{ wf.name }}</span>
              <el-tag
                size="small"
                type="info"
              >
                v{{ wf.version }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="版本">
        <el-select
          v-model="localData.config.version"
          placeholder="选择版本"
          @change="markDirty"
        >
          <el-option
            value="latest"
            label="最新版本"
          />
          <el-option 
            v-for="v in availableVersions" 
            :key="v" 
            :value="String(v)" 
            :label="`版本 ${v}`"
          />
        </el-select>
      </el-form-item>

      <!-- 子工作流信息预览 -->
      <div
        v-if="selectedSubworkflow"
        class="subworkflow-preview"
      >
        <el-descriptions
          :column="2"
          size="small"
          border
        >
          <el-descriptions-item label="名称">
            {{ selectedSubworkflow.name }}
          </el-descriptions-item>
          <el-descriptions-item label="版本">
            {{ selectedSubworkflow.version }}
          </el-descriptions-item>
          <el-descriptions-item label="节点数">
            {{ selectedSubworkflow.nodeCount || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small">
              {{ selectedSubworkflow.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 输入映射 -->
      <el-divider content-position="left">
        输入映射
        <el-tag
          size="small"
          type="info"
        >
          父 → 子
        </el-tag>
      </el-divider>
      <p class="section-hint">
        将父工作流的变量映射到子工作流的输入参数
      </p>
      
      <div class="mapping-list">
        <el-row 
          v-for="(mapping, idx) in localData.config.inputMapping" 
          :key="'in-' + idx"
          :gutter="8"
          class="mapping-row"
        >
          <el-col :span="10">
            <el-input 
              v-model="mapping.parentVar" 
              placeholder="父工作流变量"
              size="small"
              @input="markDirty"
            />
          </el-col>
          <el-col
            :span="2"
            class="arrow-col"
          >
            →
          </el-col>
          <el-col :span="10">
            <el-input 
              v-model="mapping.childParam" 
              placeholder="子工作流参数"
              size="small"
              @input="markDirty"
            />
          </el-col>
          <el-col :span="2">
            <el-button 
              link 
              type="danger" 
              size="small"
              @click="removeInputMapping(idx)"
            >
              <Minus class="icon-sm" />
            </el-button>
          </el-col>
        </el-row>
        <el-button 
          size="small" 
          @click="addInputMapping"
        >
          <Plus class="icon" /> 添加映射
        </el-button>
      </div>

      <!-- 输出映射 -->
      <el-divider content-position="left">
        输出映射
        <el-tag
          size="small"
          type="info"
        >
          子 → 父
        </el-tag>
      </el-divider>
      <p class="section-hint">
        将子工作流的输出传递到父工作流的变量
      </p>
      
      <div class="mapping-list">
        <el-row 
          v-for="(mapping, idx) in localData.config.outputMapping" 
          :key="'out-' + idx"
          :gutter="8"
          class="mapping-row"
        >
          <el-col :span="10">
            <el-input 
              v-model="mapping.childOutput" 
              placeholder="子工作流输出"
              size="small"
              @input="markDirty"
            />
          </el-col>
          <el-col
            :span="2"
            class="arrow-col"
          >
            →
          </el-col>
          <el-col :span="10">
            <el-input 
              v-model="mapping.parentVar" 
              placeholder="父工作流变量"
              size="small"
              @input="markDirty"
            />
          </el-col>
          <el-col :span="2">
            <el-button 
              link 
              type="danger" 
              size="small"
              @click="removeOutputMapping(idx)"
            >
              <Minus class="icon-sm" />
            </el-button>
          </el-col>
        </el-row>
        <el-button 
          size="small" 
          @click="addOutputMapping"
        >
          <Plus class="icon" /> 添加映射
        </el-button>
      </div>

      <!-- 执行策略 -->
      <el-divider content-position="left">
        执行策略
      </el-divider>
      <el-form-item label="执行模式">
        <el-radio-group
          v-model="localData.config.executionMode"
          @change="markDirty"
        >
          <el-radio value="sync">
            同步执行
            <div class="radio-desc">
              等待子工作流完成后继续
            </div>
          </el-radio>
          <el-radio value="async">
            异步执行
            <div class="radio-desc">
              立即继续，子工作流后台运行
            </div>
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="超时时间（秒）">
        <el-input-number 
          v-model="localData.config.timeout" 
          :min="10" 
          :max="3600"
          :step="10"
          @change="markDirty"
        />
        <span class="input-hint">超时后将终止子工作流执行</span>
      </el-form-item>

      <!-- 错误处理 -->
      <el-divider content-position="left">
        错误处理
      </el-divider>
      <el-form-item label="失败策略">
        <el-select
          v-model="localData.config.onError"
          @change="markDirty"
        >
          <el-option
            value="stop"
            label="停止 — 父工作流也停止"
          />
          <el-option
            value="skip"
            label="跳过 — 继续执行下一节点"
          />
          <el-option
            value="fallback"
            label="使用默认值 — 继续并使用预设值"
          />
        </el-select>
      </el-form-item>

      <el-form-item 
        v-if="localData.config.onError === 'fallback'" 
        label="默认值"
      >
        <el-input
          v-model="localData.config.fallbackValue"
          type="textarea"
          :rows="3"
          placeholder="JSON 格式，例如: { &quot;result&quot;: &quot;fallback&quot; }"
          @input="markDirty"
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getDefaultNodeConfig } from '@/config/nodeRegistry'
import { Plus, Minus, Layers } from 'lucide-vue-next'
import { getWorkflowList } from '@/api/workflow'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = ref({})
watch(() => props.modelValue, (value) => {
  const data = value || {}
  localData.value = {
    ...data,
    label: data.label ?? '子工作流',
    description: data.description ?? '',
    config: JSON.parse(JSON.stringify({
      ...getDefaultNodeConfig('subworkflow'),
      ...(data.config || {}),
    })),
  }
}, { immediate: true, deep: true })

const subworkflowOptions = ref([])
const searching = ref(false)
const selectedSubworkflow = ref(null)
const availableVersions = ref([])

async function searchSubworkflows(query = '') {
  searching.value = true
  try {
    const res = await getWorkflowList({ search: query, page_size: 20 })
    subworkflowOptions.value = res.results || res
  } catch (e) {
    console.error('Failed to search workflows:', e)
  } finally {
    searching.value = false
  }
}

function onWorkflowSelect(id) {
  const wf = subworkflowOptions.value.find(w => w.id === id)
  if (wf) {
    selectedSubworkflow.value = wf
    localData.value.config.subworkflowName = wf.name
    localData.value.config.version = 'latest'
    // 模拟版本数据
    availableVersions.value = Array.from({ length: wf.version || 1 }, (_, i) => i + 1)
    markDirty()
  }
}

function markDirty() {
  emit('update:modelValue', localData.value)
  emit('change')
}

function addInputMapping() {
  if (!localData.value.config.inputMapping) {
    localData.value.config.inputMapping = []
  }
  localData.value.config.inputMapping.push({ parentVar: '', childParam: '' })
  markDirty()
}

function removeInputMapping(idx) {
  localData.value.config.inputMapping.splice(idx, 1)
  markDirty()
}

function addOutputMapping() {
  if (!localData.value.config.outputMapping) {
    localData.value.config.outputMapping = []
  }
  localData.value.config.outputMapping.push({ childOutput: '', parentVar: '' })
  markDirty()
}

function removeOutputMapping(idx) {
  localData.value.config.outputMapping.splice(idx, 1)
  markDirty()
}
</script>

<style lang="scss" scoped>
.subworkflow-config-form {
  .section-hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin: -8px 0 12px;
  }

  .workflow-option-item {
    display: flex;
    align-items: center;
    gap: 8px;

    .wf-icon {
      width: 14px;
      height: 14px;
      color: var(--el-color-primary);
    }
  }

  .subworkflow-preview {
    margin-bottom: 16px;
  }

  .mapping-list {
    margin-bottom: 16px;

    .mapping-row {
      margin-bottom: 8px;
      align-items: center;

      .arrow-col {
        text-align: center;
        color: var(--el-color-primary);
        font-weight: 600;
      }
    }
  }

  .radio-desc {
    font-size: 11px;
    color: var(--el-text-color-secondary);
    margin-top: 2px;
  }

  .input-hint {
    margin-left: 8px;
    font-size: 11px;
    color: var(--el-text-color-secondary);
  }

  .icon {
    width: 14px;
    height: 14px;
  }

  .icon-sm {
    width: 12px;
    height: 12px;
  }
}
</style>
