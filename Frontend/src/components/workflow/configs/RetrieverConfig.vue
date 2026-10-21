<template>
  <div class="config-form retriever-config-form">
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

      <el-form-item label="检索来源">
        <el-select
          v-model="localData.provider"
          @change="handleChange"
        >
          <el-option
            label="Flowly 知识库"
            value="knowledge_base"
          />
          <el-option
            label="Chroma 工作流索引"
            value="chroma"
          />
          <el-option
            label="Pinecone 工作流索引"
            value="pinecone"
          />
          <el-option
            label="Qdrant 工作流索引"
            value="qdrant"
          />
        </el-select>
      </el-form-item>
      <el-form-item
        v-if="localData.provider === 'knowledge_base'"
        label="知识库"
        required
      >
        <el-select
          v-model="localData.collectionId"
          filterable
          :loading="loadingCollections"
          @change="handleChange"
        >
          <el-option
            v-for="collection in collections"
            :key="collection.id"
            :value="collection.id"
            :label="collection.name"
          />
        </el-select>
        <p class="field-hint">
          使用知识库设置的检索方式，输出 context、documents 和 sources，可供后续大模型引用。
        </p>
      </el-form-item>
      <el-form-item
        v-else
        label="索引名称"
        required
      >
        <el-input
          v-model="localData.indexName"
          @change="handleChange"
        />
      </el-form-item>
      <!-- 检索配置 -->
      <div class="form-section">
        <h4 class="section-title">
          检索配置
        </h4>
        
        <el-form-item
          label="查询内容"
          required
        >
          <el-input
            v-model="localData.query"
            type="textarea"
            :rows="3"
            placeholder="输入要检索的查询内容..."
            class="query-input"
            @change="handleChange"
          />
          <div class="field-hint">
            支持使用 {变量名} 语法引用工作流变量
          </div>
        </el-form-item>

        <el-form-item label="返回数量 (Top-K)">
          <el-input-number
            v-model="localData.topK"
            :min="1"
            :max="100"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            返回最相关的 K 个结果
          </div>
        </el-form-item>

        <el-form-item label="启用重排序">
          <el-switch
            v-model="localData.enableRerank"
            @change="handleChange"
          />
          <span class="field-hint">使用重排序模型优化结果顺序</span>
        </el-form-item>
      </div>

      <!-- 过滤配置 -->
      <div class="form-section">
        <h4 class="section-title">
          过滤配置 (可选)
        </h4>
        
        <el-form-item label="过滤条件 (JSON)">
          <el-input
            v-model="localData.filter"
            type="textarea"
            :rows="3"
            placeholder="{&quot;category&quot;: &quot;news&quot;}"
            class="json-input"
            @change="handleChange"
          />
          <div class="field-hint">
            JSON格式的元数据过滤条件
          </div>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">Top-K:</span>
            <span class="preview-value">{{ localData.topK || 5 }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">重排序:</span>
            <el-tag
              size="small"
              :type="localData.enableRerank ? 'success' : 'info'"
            >
              {{ localData.enableRerank ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch, ref, onMounted } from 'vue'
import { ragApi } from '@/api/rag'
import { loadRagPages } from '@/utils/rag'
import { RAG_CONFIG } from '@/config/rag'
const collections = ref([])
const loadingCollections = ref(false)
onMounted(async () => {
  loadingCollections.value = true
  try { collections.value = await loadRagPages(ragApi.getCollections) }
  catch { /* API interceptor displays the error. */ }
  finally { loadingCollections.value = false }
})

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
  query: '',
  topK: RAG_CONFIG.topK,
  provider: 'knowledge_base',
  collectionId: '',
  indexName: '',
  enableRerank: false,
  filter: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      query: newVal.query || '',
      provider: newVal.provider || (newVal.indexName ? 'chroma' : 'knowledge_base'),
      collectionId: newVal.collectionId || newVal.collection_id || '',
      indexName: newVal.indexName || '',
      topK: newVal.topK ?? RAG_CONFIG.topK,
      enableRerank: newVal.enableRerank ?? false,
      filter: newVal.filter || ''
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

.query-input,
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
}
</style>
