<template>
  <div class="vector-store-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button
          :icon="ArrowLeft"
          @click="goBack"
        >
          返回
        </el-button>
        <h1 class="page-title">
          {{ vectorStore?.name || '向量存储详情' }}
        </h1>
        <el-tag :type="getStatusType(vectorStore?.is_active)">
          {{ vectorStore?.is_active ? '活跃' : '已停用' }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-button @click="handleTest">
          <Wifi class="btn-icon" /> 测试连接
        </el-button>
        <el-button
          type="primary"
          @click="handleSave"
        >
          <Save class="btn-icon" /> 保存
        </el-button>
      </div>
    </div>

    <div
      v-if="vectorStore"
      class="detail-content"
    >
      <el-tabs
        v-model="activeTab"
        class="detail-tabs"
      >
        <el-tab-pane
          label="基本信息"
          name="basic"
        >
          <el-form
            :model="formData"
            label-width="120px"
            class="detail-form"
          >
            <el-form-item label="名称">
              <el-input
                v-model="formData.name"
                placeholder="向量存储名称"
              />
            </el-form-item>
            <el-form-item label="类型">
              <el-select
                v-model="formData.store_type"
                placeholder="选择类型"
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
            </el-form-item>
            <el-form-item label="主机">
              <el-input
                v-model="formData.host"
                :placeholder="APP_CONFIG.vectorStore.defaultHost"
              />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number
                v-model="formData.port"
                :min="1"
                :max="65535"
              />
            </el-form-item>
            <el-form-item label="集合名称">
              <el-input
                v-model="formData.collection"
                placeholder="默认"
              />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input
                v-model="formData.api_key"
                type="password"
                show-password
                placeholder="输入 API Key"
              />
            </el-form-item>
            <el-form-item label="向量维度">
              <el-input-number
                v-model="formData.dimension"
                :min="1"
                :max="4096"
              />
            </el-form-item>
            <el-form-item label="度量方式">
              <el-select v-model="formData.metric">
                <el-option
                  label="余弦相似度"
                  value="cosine"
                />
                <el-option
                  label="点积"
                  value="dot"
                />
                <el-option
                  label="欧氏距离"
                  value="euclidean"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-switch v-model="formData.is_active" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane
          label="集合管理"
          name="collections"
        >
          <div class="collections-header">
            <el-button
              type="primary"
              @click="showCreateCollection = true"
            >
              <Plus class="btn-icon" /> 新建集合
            </el-button>
          </div>
          <el-table
            :data="collections"
            stripe
            class="collections-table"
          >
            <el-table-column
              prop="name"
              label="名称"
            />
            <el-table-column
              prop="document_count"
              label="文档数"
              width="100"
            />
            <el-table-column
              prop="chunk_count"
              label="分块数"
              width="100"
            />
            <el-table-column
              prop="embedding_model"
              label="Embedding模型"
            />
            <el-table-column
              label="操作"
              width="200"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  @click="viewCollection(row)"
                >
                  查看
                </el-button>
                <el-button
                  type="danger"
                  link
                  @click="deleteCollection(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane
          label="使用统计"
          name="stats"
        >
          <el-row
            :gutter="20"
            class="stats-row"
          >
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-value">
                  {{ stats.totalCollections }}
                </div>
                <div class="stat-label">
                  总集合数
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-value">
                  {{ stats.totalDocuments }}
                </div>
                <div class="stat-label">
                  总文档数
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-value">
                  {{ stats.totalChunks }}
                </div>
                <div class="stat-label">
                  总分块数
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-value">
                  {{ stats.storageUsed }}
                </div>
                <div class="stat-label">
                  存储使用
                </div>
              </el-card>
            </el-col>
          </el-row>

          <div class="chart-container">
            <h3>使用趋势</h3>
            <div class="chart-placeholder">
              <LineChart class="chart" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane
          label="连接日志"
          name="logs"
        >
          <el-table
            :data="connectionLogs"
            stripe
          >
            <el-table-column
              prop="timestamp"
              label="时间"
              width="180"
            >
              <template #default="{ row }">
                {{ formatDate(row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column
              prop="status"
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="row.success ? 'success' : 'danger'"
                  size="small"
                >
                  {{ row.success ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="latency"
              label="延迟(ms)"
              width="100"
            />
            <el-table-column
              prop="message"
              label="消息"
            />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div
      v-else
      class="loading-state"
    >
      <el-skeleton
        :rows="10"
        animated
      />
    </div>

    <!-- 创建集合对话框 -->
    <el-dialog
      v-model="showCreateCollection"
      title="创建集合"
      width="500px"
    >
      <el-form
        :model="collectionForm"
        label-width="100px"
      >
        <el-form-item label="名称">
          <el-input
            v-model="collectionForm.name"
            placeholder="集合名称"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="collectionForm.description"
            type="textarea"
            :rows="3"
            placeholder="集合描述"
          />
        </el-form-item>
        <el-form-item label="Embedding模型">
          <el-select v-model="collectionForm.embedding_model">
            <el-option
              label="text-embedding-ada-002"
              value="text-embedding-ada-002"
            />
            <el-option
              label="text-embedding-3-small"
              value="text-embedding-3-small"
            />
            <el-option
              label="text-embedding-3-large"
              value="text-embedding-3-large"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="分块大小">
          <el-input-number
            v-model="collectionForm.chunk_size"
            :min="100"
            :max="4000"
            :step="100"
          />
        </el-form-item>
        <el-form-item label="分块重叠">
          <el-input-number
            v-model="collectionForm.chunk_overlap"
            :min="0"
            :max="500"
            :step="50"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateCollection = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="createCollection"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowLeft, Save, Plus, Wifi } from 'lucide-vue-next'
import { APP_CONFIG } from '@/config'
import { useAppStore } from '@/stores/app'
import ragApi from '@/api/rag'

const DEFAULT_EMBEDDING_MODEL = APP_CONFIG.embedding.defaultModel

const appStore = useAppStore()

const route = useRoute()
const router = useRouter()

const vectorStoreId = computed(() => route.params.id)
const vectorStore = ref(null)
const activeTab = ref('basic')
const showCreateCollection = ref(false)
const collections = ref([])
const connectionLogs = ref([])

const formData = ref({
  name: '',
  store_type: 'qdrant',
  host: APP_CONFIG.vectorStore.defaultHost,
  port: APP_CONFIG.vectorStore.defaultPort,
  collection: 'default',
  api_key: '',
  dimension: 1536,
  metric: 'cosine',
  is_active: true
})

const collectionForm = ref({
  name: '',
  description: '',
  embedding_model: DEFAULT_EMBEDDING_MODEL,
  chunk_size: 1000,
  chunk_overlap: 200
})

const stats = ref({
  totalCollections: 0,
  totalDocuments: 0,
  totalChunks: 0,
  storageUsed: '0 MB'
})

// Methods
const goBack = () => router.push('/vector-stores')

const fetchVectorStore = async () => {
  try {
    const data = await ragApi.getVectorStore(vectorStoreId.value)
    vectorStore.value = data
    formData.value = { ...data }
  } catch {
    appStore.error('获取向量存储失败')
  }
}

const fetchCollections = async () => {
  try {
    const data = await ragApi.getCollections({ vector_store: vectorStoreId.value })
    collections.value = data.results || data || []
    stats.value.totalCollections = collections.value.length
  } catch (err) {
    console.error('获取集合失败:', err)
    collections.value = []
  }
}

const handleSave = async () => {
  try {
    await ragApi.updateVectorStore(vectorStoreId.value, formData.value)
    appStore.success('保存成功')
    await fetchVectorStore()
  } catch {
    appStore.error('保存失败')
  }
}

const handleTest = async () => {
  appStore.info('正在测试连接...')
  try {
    const result = await ragApi.testVectorStoreConnection(vectorStoreId.value)
    if (result?.success || result?.ok) {
      appStore.success(result.message || '连接成功')
    } else {
      appStore.error(result?.message || result?.error || '连接失败')
    }
  } catch {
    appStore.error('连接测试失败')
  }
}

const createCollection = async () => {
  try {
    await ragApi.createCollection({
      ...collectionForm.value,
      vectorStore: vectorStoreId.value,
    })
    appStore.success('创建成功')
    showCreateCollection.value = false
    await fetchCollections()
  } catch {
    appStore.error('创建失败')
  }
}

const viewCollection = (collection) => {
  router.push(`/knowledge/${collection.id}`)
}

const deleteCollection = async (collection) => {
  try {
    await ElMessageBox.confirm('确定要删除这个集合吗？', '警告', {
      type: 'warning'
    })
    await ragApi.deleteCollection(collection.id)
    appStore.success('删除成功')
    await fetchCollections()
  } catch (err) {
    if (err !== 'cancel') appStore.error('删除失败')
  }
}

const getStatusType = (isActive) => isActive ? 'success' : 'info'
const formatDate = (date) => new Date(date).toLocaleString()

onMounted(() => {
  fetchVectorStore()
  fetchCollections()
})
</script>

<style scoped>
.vector-store-detail {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.detail-tabs {
  background: var(--card-bg);
  border: 1px solid var(--border-primary);
  padding: 24px;
  border-radius: 8px;
}

.detail-form {
  max-width: 600px;
}

.collections-header {
  margin-bottom: 16px;
}

.collections-table {
  margin-top: 16px;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--color-primary);
}

.stat-label {
  color: var(--text-secondary);
  margin-top: 8px;
}

.chart-container {
  background: var(--bg-tertiary);
  padding: 20px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.chart-container h3 {
  margin-bottom: 16px;
  color: var(--text-primary);
}

.chart-placeholder {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg);
  border: 1px dashed var(--border-secondary);
  border-radius: 8px;
  color: var(--text-tertiary);
  transition: border-color 0.2s ease;
}

.chart-placeholder:hover {
  border-color: var(--border-hover);
}

.loading-state {
  background: var(--card-bg);
  padding: 24px;
  border-radius: 8px;
}
</style>
