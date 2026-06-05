<template>
  <div class="vector-store-page">
    <div class="page-header">
      <div class="header-left">
        <h1>向量存储</h1>
        <p class="subtitle">
          管理向量数据库连接和配置
        </p>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          @click="showCreateDialog = true"
        >
          <Plus class="btn-icon" />
          创建向量存储
        </el-button>
      </div>
    </div>

    <!-- Filter -->
    <div class="filter-bar">
      <el-select
        v-model="filterType"
        placeholder="存储类型"
        clearable
        style="width: 150px"
      >
        <el-option
          label="Qdrant"
          value="qdrant"
        />
        <el-option
          label="Milvus"
          value="milvus"
        />
        <el-option
          label="Chroma"
          value="chroma"
        />
        <el-option
          label="Pinecone"
          value="pinecone"
        />
        <el-option
          label="Weaviate"
          value="weaviate"
        />
      </el-select>
    </div>

    <!-- Empty State -->
    <div
      v-if="vectorStores.length === 0 && !isLoading"
      class="empty-state"
    >
      <Database class="empty-icon" />
      <h3>暂无向量存储</h3>
      <p>创建您的第一个向量存储来管理文档嵌入</p>
      <el-button
        type="primary"
        @click="showCreateDialog = true"
      >
        创建向量存储
      </el-button>
    </div>

    <!-- Vector Stores Grid -->
    <div
      v-else
      class="stores-grid"
    >
      <div
        v-for="store in filteredStores"
        :key="store.id"
        class="store-card"
      >
        <div class="card-header">
          <div
            class="store-icon"
            :class="store.store_type"
          >
            <Database
              v-if="store.store_type === 'qdrant'"
              class="icon"
            />
            <Box
              v-else-if="store.store_type === 'milvus'"
              class="icon"
            />
            <Layers
              v-else-if="store.store_type === 'chroma'"
              class="icon"
            />
            <TreePine
              v-else-if="store.store_type === 'pinecone'"
              class="icon"
            />
            <Globe
              v-else
              class="icon"
            />
          </div>
          <el-dropdown
            trigger="click"
            @click.stop
          >
            <el-button
              text
              size="small"
            >
              <MoreVertical />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click.stop="handleTestConnection(store)">
                  <Wifi class="menu-icon" />
                  测试连接
                </el-dropdown-item>
                <el-dropdown-item @click.stop="editStore(store)">
                  <Edit class="menu-icon" />
                  编辑
                </el-dropdown-item>
                <el-dropdown-item @click.stop="createCollection(store)">
                  <FolderPlus class="menu-icon" />
                  创建集合
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="!store.is_default"
                  divided
                  @click.stop="handleSetDefault(store)"
                >
                  <Star class="menu-icon" />
                  设为默认
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="store.is_default"
                  divided
                  @click.stop="handleUnsetDefault(store)"
                >
                  <StarOff class="menu-icon" />
                  取消默认
                </el-dropdown-item>
                <el-dropdown-item
                  divided
                  class="danger"
                  @click.stop="handleDelete(store)"
                >
                  <Trash2 class="menu-icon" />
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <h3 class="store-name">
          {{ store.name }}
        </h3>
        <p class="store-type">
          {{ getStoreTypeLabel(store.store_type) }}
        </p>

        <div class="store-meta">
          <span
            v-if="store.is_default"
            class="meta-badge default"
          >
            <Star class="badge-icon" />
            默认
          </span>
          <span class="meta-badge">
            <Layers class="badge-icon" />
            {{ store.dimension }} 维
          </span>
          <span class="meta-badge">
            <Scale class="badge-icon" />
            {{ getMetricLabel(store.metric) }}
          </span>
        </div>

        <div class="store-connection">
          <div class="connection-info">
            <span class="connection-label">连接</span>
            <span class="connection-value">{{ store.host }}:{{ store.port }}</span>
          </div>
          <el-tag
            v-if="storeConnections[store.id] !== undefined"
            :type="storeConnections[store.id] ? 'success' : 'danger'"
            size="small"
          >
            {{ storeConnections[store.id] ? '已连接' : '未连接' }}
          </el-tag>
        </div>

        <div class="store-actions">
          <el-button
            size="small"
            @click="handleTestConnection(store)"
          >
            测试连接
          </el-button>
          <el-button
            size="small"
            type="primary"
            @click="goToCollections(store)"
          >
            查看集合
          </el-button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingStore ? '编辑向量存储' : '创建向量存储'"
      width="600px"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-position="top"
      >
        <el-form-item
          label="名称"
          prop="name"
        >
          <el-input
            v-model="form.name"
            placeholder="例如：生产环境 Qdrant"
          />
        </el-form-item>

        <el-form-item
          label="存储类型"
          prop="store_type"
        >
          <el-select
            v-model="form.store_type"
            style="width: 100%"
          >
            <el-option
              label="Qdrant"
              value="qdrant"
            >
              <div class="store-option">
                <Database class="option-icon" />
                <span>Qdrant - 高性能向量数据库</span>
              </div>
            </el-option>
            <el-option
              label="Milvus"
              value="milvus"
            >
              <div class="store-option">
                <Box class="option-icon" />
                <span>Milvus - 开源向量数据库</span>
              </div>
            </el-option>
            <el-option
              label="Chroma"
              value="chroma"
            >
              <div class="store-option">
                <Layers class="option-icon" />
                <span>Chroma - 轻量级向量库</span>
              </div>
            </el-option>
            <el-option
              label="Pinecone"
              value="pinecone"
            >
              <div class="store-option">
                <TreePine class="option-icon" />
                <span>Pinecone - 云端向量数据库</span>
              </div>
            </el-option>
            <el-option
              label="Weaviate"
              value="weaviate"
            >
              <div class="store-option">
                <Globe class="option-icon" />
                <span>Weaviate - 语义向量搜索引擎</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item
          label="主机地址"
          prop="host"
        >
          <el-input
            v-model="form.host"
            placeholder="localhost 或 IP 地址"
          />
        </el-form-item>

        <el-form-item
          label="端口"
          prop="port"
        >
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
          />
        </el-form-item>

        <el-form-item
          v-if="form.store_type === 'qdrant' || form.store_type === 'pinecone'"
          label="API Key"
        >
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="API Key（可选）"
          />
        </el-form-item>

        <el-form-item
          v-if="form.store_type === 'chroma'"
          label="本地路径"
        >
          <el-input
            v-model="form.path"
            placeholder="./chroma_data"
          />
        </el-form-item>

        <el-form-item
          label="向量维度"
          prop="dimension"
        >
          <el-select
            v-model="form.dimension"
            style="width: 100%"
          >
            <el-option
              label="1536 (OpenAI Ada)"
              :value="1536"
            />
            <el-option
              label="3072 (OpenAI 3 Large)"
              :value="3072"
            />
            <el-option
              label="1536 (Cohere)"
              :value="1024"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="度量方式"
          prop="metric"
        >
          <el-radio-group v-model="form.metric">
            <el-radio label="cosine">
              余弦相似度
            </el-radio>
            <el-radio label="euclidean">
              欧几里得距离
            </el-radio>
            <el-radio label="dotproduct">
              点积
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSave"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Create Collection Dialog -->
    <el-dialog
      v-model="showCollectionDialog"
      title="创建集合"
      width="500px"
    >
      <el-form
        ref="collectionFormRef"
        :model="collectionForm"
        label-position="top"
      >
        <el-form-item label="集合名称">
          <el-input
            v-model="collectionForm.name"
            placeholder="my_collection"
          />
        </el-form-item>
        <el-form-item label="维度">
          <el-input-number
            v-model="collectionForm.dimension"
            :min="1"
          />
        </el-form-item>
        <el-form-item label="度量方式">
          <el-select
            v-model="collectionForm.metric"
            style="width: 100%"
          >
            <el-option
              label="余弦相似度"
              value="cosine"
            />
            <el-option
              label="欧几里得距离"
              value="euclidean"
            />
            <el-option
              label="点积"
              value="dotproduct"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCollectionDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="creatingCollection"
          @click="handleCreateCollection"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRAGStore } from '@/stores/rag'
import { useAppStore } from '@/stores/app'
import {
  Plus, Database, Box, Layers, Globe, MoreVertical,
  Edit, Trash2, Star, StarOff, Wifi, FolderPlus,
  Scale, TreePine
} from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { APP_CONFIG } from '@/config'

const router = useRouter()
const ragStore = useRAGStore()
const appStore = useAppStore()

const showCreateDialog = ref(false)
const showCollectionDialog = ref(false)
const editingStore = ref(null)
const selectedStore = ref(null)
const saving = ref(false)
const creatingCollection = ref(false)
const filterType = ref('')
const formRef = ref(null)
const collectionFormRef = ref(null)

const storeConnections = ref({})

const form = reactive({
  name: '',
  store_type: 'qdrant',
  host: APP_CONFIG.vectorStore.defaultHost,
  port: APP_CONFIG.vectorStore.defaultPort,
  api_key: '',
  path: '',
  dimension: 1536,
  metric: 'cosine',
  is_default: false
})

const collectionForm = reactive({
  name: '',
  dimension: 1536,
  metric: 'cosine'
})

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  store_type: [{ required: true, message: '请选择存储类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  dimension: [{ required: true, message: '请输入向量维度', trigger: 'blur' }]
}

const vectorStores = computed(() => ragStore.vectorStores)
const isLoading = computed(() => ragStore.isLoading)

const filteredStores = computed(() => {
  if (!filterType.value) return vectorStores.value
  return vectorStores.value.filter(s => s.store_type === filterType.value)
})

function getStoreTypeLabel(type) {
  const labels = {
    qdrant: 'Qdrant',
    milvus: 'Milvus',
    chroma: 'Chroma',
    pinecone: 'Pinecone',
    weaviate: 'Weaviate'
  }
  return labels[type] || type
}

function getMetricLabel(metric) {
  const labels = {
    cosine: '余弦',
    euclidean: '欧氏',
    dotproduct: '点积'
  }
  return labels[metric] || metric
}

function editStore(store) {
  editingStore.value = store
  Object.assign(form, {
    name: store.name,
    store_type: store.store_type,
    host: store.host,
    port: store.port,
    api_key: store.api_key || '',
    path: store.path || '',
    dimension: store.dimension,
    metric: store.metric,
    is_default: store.is_default
  })
  showCreateDialog.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editingStore.value) {
      await ragStore.updateVectorStore(editingStore.value.id, form)
      appStore.success('向量存储已更新')
    } else {
      await ragStore.createVectorStore(form)
      appStore.success('向量存储已创建')
    }
    showCreateDialog.value = false
    resetForm()
    await ragStore.fetchVectorStores()
  } catch (err) {
    appStore.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(store) {
  try {
    await ElMessageBox.confirm(
      `确定要删除向量存储 "${store.name}" 吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    await ragStore.deleteVectorStore(store.id)
    appStore.success('已删除')
    await ragStore.fetchVectorStores()
  } catch (err) {
    if (err !== 'cancel') appStore.error('删除失败')
  }
}

async function handleTestConnection(store) {
  try {
    const result = await ragStore.testConnection(store.id)
    storeConnections.value[store.id] = true
    appStore.success('连接成功')
  } catch (err) {
    storeConnections.value[store.id] = false
    appStore.error('连接失败: ' + (err.message || '未知错误'))
  }
}

async function handleSetDefault(store) {
  try {
    await ragStore.updateVectorStore(store.id, { is_default: true })
    appStore.success('已设为默认')
    await ragStore.fetchVectorStores()
  } catch (err) {
    appStore.error('设置失败')
  }
}

async function handleUnsetDefault(store) {
  try {
    await ragStore.updateVectorStore(store.id, { is_default: false })
    appStore.success('已取消默认')
    await ragStore.fetchVectorStores()
  } catch (err) {
    appStore.error('操作失败')
  }
}

function createCollection(store) {
  selectedStore.value = store
  Object.assign(collectionForm, {
    name: '',
    dimension: store.dimension,
    metric: store.metric
  })
  showCollectionDialog.value = true
}

async function handleCreateCollection() {
  if (!collectionForm.name) {
    appStore.error('请输入集合名称')
    return
  }

  creatingCollection.value = true
  try {
    await ragStore.api.createVectorStoreCollection(selectedStore.value.id, {
      name: collectionForm.name,
      dimension: collectionForm.dimension,
      metric: collectionForm.metric
    })
    appStore.success('集合已创建')
    showCollectionDialog.value = false
  } catch (err) {
    appStore.error('创建失败')
  } finally {
    creatingCollection.value = false
  }
}

function goToCollections(store) {
  router.push(`/vector-store/${store.id}`)
}

function resetForm() {
  Object.assign(form, {
    name: '',
    store_type: 'qdrant',
    host: APP_CONFIG.vectorStore.defaultHost,
    port: APP_CONFIG.vectorStore.defaultPort,
    api_key: '',
    path: '',
    dimension: 1536,
    metric: 'cosine',
    is_default: false
  })
  editingStore.value = null
}

onMounted(async () => {
  await ragStore.fetchVectorStores()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.vector-store-page {
  padding: $spacing-6;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;

  h1 {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    margin: 0;
  }

  .subtitle {
    font-size: $font-size-sm;
    color: var(--text-primary)-secondary;
    margin: $spacing-1 0 0;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.filter-bar {
  margin-bottom: $spacing-4;
}

.empty-state {
  text-align: center;
  padding: $spacing-12;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--text-primary)-tertiary;
    margin-bottom: $spacing-4;
  }

  h3 {
    font-size: $font-size-lg;
    margin: 0 0 $spacing-2;
  }

  p {
    color: var(--text-primary)-secondary;
    margin: 0 0 $spacing-4;
  }
}

.stores-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: $spacing-4;
}

.store-card {
  background: var(--bg-primary)-secondary;
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  transition: all $transition-fast;

  &:hover {
    border-color: $color-primary;
    transform: translateY(-2px);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-3;
}

.store-icon {
  width: 40px;
  height: 40px;
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;

  .icon {
    width: 20px;
    height: 20px;
  }

  &.qdrant {
    background: rgba(#46A3FF, 0.15);
    .icon { color: #46A3FF; }
  }

  &.milvus {
    background: rgba(#FF6B6B, 0.15);
    .icon { color: #FF6B6B; }
  }

  &.chroma {
    background: rgba(#A855F7, 0.15);
    .icon { color: #A855F7; }
  }

  &.pinecone {
    background: rgba(#22C55E, 0.15);
    .icon { color: #22C55E; }
  }

  &.weaviate {
    background: rgba(#F59E0B, 0.15);
    .icon { color: #F59E0B; }
  }
}

.store-name {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  margin: 0 0 $spacing-1;
}

.store-type {
  font-size: $font-size-sm;
  color: var(--text-primary)-secondary;
  margin: 0 0 $spacing-3;
}

.store-meta {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  margin-bottom: $spacing-3;

  .meta-badge {
    display: inline-flex;
    align-items: center;
    gap: $spacing-1;
    padding: 2px 8px;
    background: var(--bg-primary)-tertiary;
    border-radius: $radius-md;
    font-size: $font-size-xs;
    color: var(--text-primary)-tertiary;

    &.default {
      background: rgba($color-warning, 0.15);
      color: $color-warning;
    }
  }

  .badge-icon {
    width: 12px;
    height: 12px;
  }
}

.store-connection {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-3;
  background: var(--bg-primary)-tertiary;
  border-radius: $radius-md;
  margin-bottom: $spacing-3;

  .connection-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .connection-label {
    font-size: $font-size-xs;
    color: var(--text-primary)-tertiary;
  }

  .connection-value {
    font-size: $font-size-sm;
    font-family: monospace;
    color: var(--text-primary);
  }
}

.store-actions {
  display: flex;
  gap: $spacing-2;
}

.menu-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-2;
}

.store-option {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .option-icon {
    width: 16px;
    height: 16px;
  }
}

.danger {
  color: $color-error;
}
</style>



