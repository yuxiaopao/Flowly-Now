<template>
  <div class="collection-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button
          text
          @click="goBack"
        >
          <ArrowLeft class="btn-icon" />
          返回
        </el-button>
        <div class="header-info">
          <h1>{{ collection.name }}</h1>
          <p class="subtitle">
            {{ collection.description || '暂无描述' }}
          </p>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="showEditDialog = true">
          <Edit class="btn-icon" />
          编辑
        </el-button>
        <el-button
          type="primary"
          @click="showUploadDialog = true"
        >
          <Upload class="btn-icon" />
          上传文档
        </el-button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row">
      <el-card
        shadow="hover"
        class="stat-card"
      >
        <div class="stat-content">
          <FileText class="stat-icon" />
          <div class="stat-info">
            <span class="stat-value">{{ stats.documents }}</span>
            <span class="stat-label">文档</span>
          </div>
        </div>
      </el-card>
      <el-card
        shadow="hover"
        class="stat-card"
      >
        <div class="stat-content">
          <Layers class="stat-icon" />
          <div class="stat-info">
            <span class="stat-value">{{ stats.chunks }}</span>
            <span class="stat-label">分块</span>
          </div>
        </div>
      </el-card>
      <el-card
        shadow="hover"
        class="stat-card"
      >
        <div class="stat-content">
          <Database class="stat-icon" />
          <div class="stat-info">
            <span class="stat-value">{{ formatSize(stats.storage) }}</span>
            <span class="stat-label">存储</span>
          </div>
        </div>
      </el-card>
      <el-card
        shadow="hover"
        class="stat-card"
      >
        <div class="stat-content">
          <Clock class="stat-icon" />
          <div class="stat-info">
            <span class="stat-value">{{ formatDate(collection.updatedAt || collection.updated_at) }}</span>
            <span class="stat-label">最后更新</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Tabs -->
    <el-tabs
      v-model="activeTab"
      class="detail-tabs"
    >
      <!-- Documents Tab -->
      <el-tab-pane
        label="文档"
        name="documents"
      >
        <div class="tab-toolbar">
          <el-input
            v-model="documentFilterQuery"
            placeholder="搜索文档..."
            :prefix-icon="Search"
            clearable
            style="width: 300px"
          />
          <el-select
            v-model="statusFilter"
            placeholder="状态"
            clearable
            style="width: 150px"
          >
            <el-option
              label="全部"
              value=""
            />
            <el-option
              label="已处理"
              value="processed"
            />
            <el-option
              label="处理中"
              value="processing"
            />
            <el-option
              label="失败"
              value="failed"
            />
          </el-select>
        </div>

        <el-table
          v-loading="loadingDocuments"
          :data="filteredDocuments"
          stripe
          @selection-change="handleSelectionChange"
        >
          <el-table-column
            type="selection"
            width="55"
          />
          <el-table-column
            prop="title"
            label="标题"
            min-width="200"
          >
            <template #default="{ row }">
              <div class="doc-title-cell">
                <el-icon><Document /></el-icon>
                <span>{{ row.title }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="status"
            label="状态"
            width="120"
          >
            <template #default="{ row }">
              <el-tag
                :type="getStatusType(row.status)"
                size="small"
              >
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="chunk_count"
            label="分块数"
            width="100"
            align="center"
          />
          <el-table-column
            prop="source_type"
            label="来源"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                type="info"
              >
                {{ row.source_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="上传时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="200"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                text
                type="primary"
                size="small"
                @click="viewDocument(row)"
              >
                查看
              </el-button>
              <el-button
                text
                type="primary"
                size="small"
                @click="reprocessDocument(row)"
              >
                重新处理
              </el-button>
              <el-button
                text
                type="danger"
                size="small"
                @click="deleteDocument(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="selectedDocuments.length > 0"
          class="bulk-actions"
        >
          <span>已选择 {{ selectedDocuments.length }} 项</span>
          <el-button
            size="small"
            @click="reprocessDocuments"
          >
            批量重新处理
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="deleteDocuments"
          >
            批量删除
          </el-button>
        </div>
      </el-tab-pane>

      <!-- Chunks Tab -->
      <el-tab-pane
        label="分块"
        name="chunks"
      >
        <div class="tab-toolbar">
          <el-input
            v-model="chunkSearchQuery"
            placeholder="搜索分块内容..."
            :prefix-icon="Search"
            clearable
            style="width: 300px"
          />
          <el-button @click="showChunkStatsDialog = true">
            <TrendCharts class="btn-icon" />
            统计
          </el-button>
        </div>

        <el-table
          v-loading="loadingChunks"
          :data="paginatedChunks"
          stripe
        >
          <el-table-column
            prop="id"
            label="ID"
            width="80"
          />
          <el-table-column
            prop="content"
            label="内容"
            min-width="400"
          >
            <template #default="{ row }">
              <div class="chunk-content">
                {{ row.content }}
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="document_title"
            label="来源文档"
            width="180"
          >
            <template #default="{ row }">
              <el-link
                type="primary"
                @click="viewDocumentById(row.document_id)"
              >
                {{ row.document_title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column
            prop="token_count"
            label="Token 数"
            width="100"
            align="center"
          />
          <el-table-column
            prop="created_at"
            label="创建时间"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="chunkPage"
            v-model:page-size="chunkPageSize"
            :total="totalChunks"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </el-tab-pane>

      <!-- Search Tab -->
      <el-tab-pane
        label="搜索测试"
        name="search"
      >
        <div class="search-test-container">
          <el-card shadow="hover">
            <template #header>
              <span>语义搜索测试</span>
            </template>
            <div class="search-form">
              <el-input
                v-model="semanticSearchQuery"
                type="textarea"
                :rows="3"
                placeholder="输入搜索查询..."
                @keydown.enter.ctrl="performSearch"
              />
              <div class="search-options">
                <el-form label-width="80px">
                  <el-form-item label="返回数量">
                    <el-input-number
                      v-model="searchTopK"
                      :min="1"
                      :max="50"
                    />
                  </el-form-item>
                  <el-form-item label="最小相似度">
                    <el-slider
                      v-model="searchMinSimilarity"
                      :min="0"
                      :max="1"
                      :step="0.05"
                      show-input
                    />
                  </el-form-item>
                </el-form>
              </div>
              <el-button
                type="primary"
                :loading="searching"
                @click="performSearch"
              >
                搜索
              </el-button>
            </div>

            <div
              v-if="searchResults.length > 0"
              class="search-results"
            >
              <h4>搜索结果 ({{ searchResults.length }})</h4>
              <div
                v-for="(result, index) in searchResults"
                :key="index"
                class="result-item"
              >
                <div class="result-header">
                  <span class="result-score">
                    相似度: {{ (result.score * 100).toFixed(1) }}%
                  </span>
                  <el-tag size="small">
                    {{ result.document_title }}
                  </el-tag>
                </div>
                <div class="result-content">
                  {{ result.content }}
                </div>
              </div>
            </div>

            <el-empty
              v-else-if="!searching && hasSearched"
              description="暂无结果"
            />
          </el-card>
        </div>
      </el-tab-pane>

      <!-- Settings Tab -->
      <el-tab-pane
        label="设置"
        name="settings"
      >
        <el-card
          shadow="hover"
          class="settings-card"
        >
          <template #header>
            <span>集合配置</span>
          </template>
          <el-form
            :model="settingsForm"
            label-width="150px"
          >
            <el-form-item label="Embedding 模型">
              <el-select v-model="settingsForm.embedding_model">
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
                v-model="settingsForm.chunk_size"
                :min="100"
                :max="4000"
                :step="100"
              />
            </el-form-item>
            <el-form-item label="分块重叠">
              <el-input-number
                v-model="settingsForm.chunk_overlap"
                :min="0"
                :max="500"
                :step="50"
              />
            </el-form-item>
            <el-form-item label="向量维度">
              <el-input-number
                v-model="settingsForm.dimension"
                :min="128"
                :max="4096"
                :step="128"
              />
            </el-form-item>
            <el-form-item label="向量存储">
              <el-select v-model="settingsForm.vector_store">
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
            <el-form-item>
              <el-button
                type="primary"
                @click="saveSettings"
              >
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card
          shadow="hover"
          class="settings-card danger-zone"
        >
          <template #header>
            <span>危险区域</span>
          </template>
          <div class="danger-actions">
            <div class="danger-item">
              <div class="danger-info">
                <h4>重新处理所有文档</h4>
                <p>使用新的分块配置重新处理集合中的所有文档</p>
              </div>
              <el-button
                type="warning"
                @click="reprocessAll"
              >
                重新处理
              </el-button>
            </div>
            <div class="danger-item">
              <div class="danger-info">
                <h4>清空集合</h4>
                <p>删除集合中的所有文档和分块</p>
              </div>
              <el-button
                type="danger"
                @click="clearCollectionAction"
              >
                清空
              </el-button>
            </div>
            <div class="danger-item">
              <div class="danger-info">
                <h4>删除集合</h4>
                <p>永久删除此集合，所有数据将无法恢复</p>
              </div>
              <el-button
                type="danger"
                @click="deleteCollectionAction"
              >
                删除
              </el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="600px"
    >
      <el-tabs v-model="uploadTab">
        <el-tab-pane
          label="文件上传"
          name="file"
        >
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="10"
            :file-list="fileList"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            drag
            accept=".pdf,.doc,.docx,.txt,.md,.csv,.json"
          >
            <el-icon class="el-icon--upload">
              <upload-filled />
            </el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF, DOC, DOCX, TXT, MD, CSV, JSON 格式，单个文件不超过 50MB
              </div>
            </template>
          </el-upload>
        </el-tab-pane>
        <el-tab-pane
          label="文本输入"
          name="text"
        >
          <el-form label-position="top">
            <el-form-item label="标题">
              <el-input
                v-model="textForm.title"
                placeholder="文档标题"
              />
            </el-form-item>
            <el-form-item label="内容">
              <el-input
                v-model="textForm.content"
                type="textarea"
                :rows="10"
                placeholder="输入文档内容..."
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane
          label="URL"
          name="url"
        >
          <el-form label-position="top">
            <el-form-item label="URL">
              <el-input
                v-model="urlForm.url"
                placeholder="https://..."
              />
            </el-form-item>
            <el-form-item label="标题（可选）">
              <el-input
                v-model="urlForm.title"
                placeholder="文档标题"
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showUploadDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="uploading"
          @click="handleUpload"
        >
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- Document Detail Dialog -->
    <el-dialog
      v-model="showDocumentDialog"
      :title="selectedDocument?.title"
      width="800px"
    >
      <div
        v-if="selectedDocument"
        class="document-detail"
      >
        <div class="detail-meta">
          <el-tag>{{ selectedDocument.status }}</el-tag>
          <span>{{ selectedDocument.chunk_count }} 分块</span>
          <span>{{ formatDateTime(selectedDocument.created_at) }}</span>
        </div>
        <el-divider />
        <div class="detail-content">
          <h4>原始内容</h4>
          <div class="content-box">
            {{ selectedDocument.content || '暂无内容' }}
          </div>
        </div>
        <div class="detail-chunks">
          <h4>分块预览</h4>
          <div
            v-for="(chunk, index) in selectedDocument.chunks?.slice(0, 5)"
            :key="index"
            class="chunk-preview"
          >
            <div class="chunk-header">
              <span>分块 {{ index + 1 }}</span>
              <span class="chunk-tokens">{{ chunk.token_count }} tokens</span>
            </div>
            <div class="chunk-text">
              {{ chunk.content }}
            </div>
          </div>
          <el-link
            v-if="selectedDocument.chunks?.length > 5"
            type="primary"
          >
            查看全部 {{ selectedDocument.chunks.length }} 个分块
          </el-link>
        </div>
      </div>
    </el-dialog>

    <!-- Edit Collection Dialog -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑集合"
      width="500px"
    >
      <el-form
        :model="editForm"
        label-width="80px"
      >
        <el-form-item label="名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="saveEdit"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Chunk Stats Dialog -->
    <el-dialog
      v-model="showChunkStatsDialog"
      title="分块统计"
      width="600px"
    >
      <div class="stats-content">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="mini-stat">
              <span class="mini-value">{{ stats.chunks }}</span>
              <span class="mini-label">总分块数</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="mini-stat">
              <span class="mini-value">{{ stats.avgTokens }}</span>
              <span class="mini-label">平均 Token</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="mini-stat">
              <span class="mini-value">{{ (stats.totalTokens ?? 0).toLocaleString() }}</span>
              <span class="mini-label">总 Token</span>
            </div>
          </el-col>
        </el-row>
        <div class="chunk-distribution">
          <h4>分块大小分布</h4>
          <div class="distribution-bars">
            <div
              v-for="(count, size) in chunkDistribution"
              :key="size"
              class="bar-item"
            >
              <span class="bar-label">{{ size }}</span>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ width: (stats.chunks ? (count / stats.chunks * 100) : 0) + '%' }"
                />
              </div>
              <span class="bar-value">{{ count }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import {
  ArrowLeft, Edit, Upload, Document, Clock, Search,
  TrendCharts, UploadFilled
} from '@element-plus/icons-vue'
import { formatDate, formatDateTime } from '@/utils/formatters'
import { ragApi } from '@/api/rag'
import { APP_CONFIG } from '@/config'

const DEFAULT_EMBEDDING_MODEL = APP_CONFIG.embedding.defaultModel

const appStore = useAppStore()
const route = useRoute()
const router = useRouter()

// State
const activeTab = ref('documents')
const loadingDocuments = ref(false)
const loadingChunks = ref(false)
const searching = ref(false)
const uploading = ref(false)
const hasSearched = ref(false)
const showUploadDialog = ref(false)
const showDocumentDialog = ref(false)
const showEditDialog = ref(false)
const showChunkStatsDialog = ref(false)
const selectedDocuments = ref([])
const selectedDocument = ref(null)
const uploadTab = ref('file')
const fileList = ref([])

// Real data (fetched from API via fetchCollection)
const collection = ref({
  id: route.params.id,
  name: '',
  description: '',
  embedding_model: '',
  chunk_size: 1000,
  chunk_overlap: 200,
  created_at: null,
  updated_at: null
})

const stats = ref({
  documents: 0,
  chunks: 0,
  storage: 0,
  avgTokens: 0,
  totalTokens: 0
})

const documents = ref([])
const chunks = ref([])

const documentFilterQuery = ref('')
const semanticSearchQuery = ref('')
const chunkSearchQuery = ref('')
const chunkPage = ref(1)
const chunkPageSize = ref(20)
const statusFilter = ref('')
const searchTopK = ref(5)
const searchMinSimilarity = ref(0.7)
const searchResults = ref([])

const textForm = reactive({ title: '', content: '' })
const urlForm = reactive({ url: '', title: '' })

const settingsForm = reactive({
  embedding_model: DEFAULT_EMBEDDING_MODEL,
  chunk_size: 1000,
  chunk_overlap: 200,
  dimension: 1536,
  vector_store: 'qdrant'
})

const editForm = reactive({
  name: '',
  description: ''
})

const chunkDistribution = ref({
  '0-100': 45,
  '100-500': 234,
  '500-1000': 567,
  '1000-2000': 345,
  '2000+': 43
})

// Computed
const filteredDocuments = computed(() => {
  let result = [...documents.value]

  if (documentFilterQuery.value) {
    const query = documentFilterQuery.value.toLowerCase()
    result = result.filter(d => d.title.toLowerCase().includes(query))
  }

  if (statusFilter.value) {
    result = result.filter(d => d.status === statusFilter.value)
  }

  return result
})

const filteredChunks = computed(() => {
  if (!chunkSearchQuery.value) return chunks.value
  const query = chunkSearchQuery.value.toLowerCase()
  return chunks.value.filter(c => c.content.toLowerCase().includes(query))
})

const paginatedChunks = computed(() => {
  const start = (chunkPage.value - 1) * chunkPageSize.value
  return filteredChunks.value.slice(start, start + chunkPageSize.value)
})

const totalChunks = computed(() => filteredChunks.value.length)

// Methods
const goBack = () => {
  router.push('/knowledge')
}

// ==================== API Integration ====================

async function fetchCollection() {
  const collectionId = route.params.id
  try {
    const response = await ragApi.getCollection(collectionId)
    collection.value = { ...collection.value, ...response }
    Object.assign(settingsForm, {
      embedding_model: response.embeddingModel || response.embedding_model || settingsForm.embedding_model,
      chunk_size: response.chunkSize || response.chunk_size || settingsForm.chunk_size,
      chunk_overlap: response.chunkOverlap || response.chunk_overlap || settingsForm.chunk_overlap,
    })
    Object.assign(editForm, {
      name: response.name || collection.value.name,
      description: response.description || collection.value.description || '',
    })
  } catch {
    // Error shown via API interceptor
  }
}

async function fetchStats() {
  try {
    const data = await ragApi.getCollectionStats(route.params.id)
    stats.value.documents = data.documentCount ?? data.document_count ?? 0
    stats.value.chunks = data.chunkCount ?? data.chunk_count ?? 0
  } catch {
    // Error shown via API interceptor
  }
}

async function fetchDocuments() {
  loadingDocuments.value = true
  try {
    const response = await ragApi.getDocuments({ collection: route.params.id })
    documents.value = response.results || response || []
  } catch {
    // Error shown via API interceptor
  } finally {
    loadingDocuments.value = false
  }
}

async function fetchChunks() {
  loadingChunks.value = true
  try {
    const docs = documents.value.length
      ? documents.value
      : ((await ragApi.getDocuments({ collection: route.params.id })).results || [])
    const allChunks = []
    for (const doc of docs) {
      const chunksRes = await ragApi.getDocumentChunks(doc.id)
      const list = chunksRes.results || chunksRes || []
      for (const chunk of list) {
        allChunks.push({
          ...chunk,
          document_id: doc.id,
          document_title: doc.title,
        })
      }
    }
    chunks.value = allChunks
    const tokenCounts = allChunks.map(c => c.tokenCount ?? c.token_count ?? 0).filter(Boolean)
    if (tokenCounts.length) {
      stats.value.avgTokens = Math.round(tokenCounts.reduce((a, b) => a + b, 0) / tokenCounts.length)
      stats.value.totalTokens = tokenCounts.reduce((a, b) => a + b, 0)
    }
  } catch {
    // Error shown via API interceptor
  } finally {
    loadingChunks.value = false
  }
}

async function refreshCollectionData() {
  await Promise.all([fetchCollection(), fetchDocuments(), fetchStats()])
  await fetchChunks()
}

// Initial data fetch
onMounted(async () => {
  await refreshCollectionData()
})

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const getStatusType = (status) => {
  const types = { processed: 'success', processing: 'warning', failed: 'danger' }
  return types[status] || ''
}

const getStatusLabel = (status) => {
  const labels = { processed: '已处理', processing: '处理中', failed: '失败' }
  return labels[status] || status
}

const handleFileChange = (file, files) => {
  fileList.value = files
}

const handleFileRemove = (file, files) => {
  fileList.value = files
}

const handleSelectionChange = (selection) => {
  selectedDocuments.value = selection
}

const handleUpload = async () => {
  uploading.value = true
  const collectionId = route.params.id
  try {
    if (uploadTab.value === 'file') {
      if (!fileList.value.length) {
        appStore.error('请选择要上传的文件')
        return
      }
      for (const file of fileList.value) {
        const rawFile = file.raw || file.originFileObj || (file instanceof File ? file : null)
        if (!rawFile) {
          appStore.error('无法读取文件内容，请重新选择')
          return
        }
        const formData = new FormData()
        formData.append('file', rawFile)
        await ragApi.uploadFile(collectionId, formData)
      }
    } else if (uploadTab.value === 'text') {
      if (!textForm.title.trim() || !textForm.content.trim()) {
        appStore.error('请填写标题和内容')
        return
      }
      await ragApi.addDocument(collectionId, {
        title: textForm.title,
        content: textForm.content,
      })
    } else {
      if (!urlForm.url.trim()) {
        appStore.error('请填写 URL')
        return
      }
      await ragApi.addUrl(collectionId, {
        url: urlForm.url,
        title: urlForm.title || undefined,
      })
    }
    appStore.success('文档上传成功')
    showUploadDialog.value = false
    fileList.value = []
    Object.assign(textForm, { title: '', content: '' })
    Object.assign(urlForm, { url: '', title: '' })
    await refreshCollectionData()
  } finally {
    uploading.value = false
  }
}

const viewDocument = async (doc) => {
  try {
    const detail = await ragApi.getDocument(doc.id)
    const chunksRes = await ragApi.getDocumentChunks(doc.id)
    selectedDocument.value = {
      ...detail,
      chunks: chunksRes.results || chunksRes || [],
    }
    showDocumentDialog.value = true
  } catch {
    // Error shown via API interceptor
  }
}

const viewDocumentById = (id) => {
  const doc = documents.value.find(d => d.id === id)
  if (doc) viewDocument(doc)
}

const reprocessDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(`重新处理文档「${doc.title}」？`, '确认', { type: 'info' })
    await ragApi.reprocessDocument(doc.id)
    appStore.success('文档重新处理已启动')
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const deleteDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(`删除文档「${doc.title}」？`, '确认', { type: 'warning' })
    await ragApi.deleteDocument(doc.id)
    appStore.success('文档已删除')
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const reprocessDocuments = async () => {
  try {
    await ElMessageBox.confirm(`重新处理选中的 ${selectedDocuments.value.length} 个文档？`, '确认', { type: 'info' })
    await Promise.all(selectedDocuments.value.map(doc => ragApi.reprocessDocument(doc.id)))
    appStore.success('批量重新处理已启动')
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const deleteDocuments = async () => {
  try {
    await ElMessageBox.confirm(`删除选中的 ${selectedDocuments.value.length} 个文档？`, '确认', { type: 'warning' })
    await Promise.all(selectedDocuments.value.map(doc => ragApi.deleteDocument(doc.id)))
    appStore.success('批量删除成功')
    selectedDocuments.value = []
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const performSearch = async () => {
  if (!semanticSearchQuery.value.trim()) return
  searching.value = true
  hasSearched.value = true
  try {
    const response = await ragApi.searchCollection(route.params.id, {
      query: semanticSearchQuery.value.trim(),
      top_k: searchTopK.value,
    })
    const results = response.results || []
    searchResults.value = results
      .filter(r => (r.score ?? 0) >= searchMinSimilarity.value)
      .map(r => ({
        score: r.score ?? 0,
        content: r.content || '',
        document_title: r.metadata?.title || r.documentTitle || '未知文档',
      }))
  } finally {
    searching.value = false
  }
}

const saveSettings = async () => {
  try {
    await ragApi.updateCollection(route.params.id, {
      embedding_model: settingsForm.embedding_model,
      chunk_size: settingsForm.chunk_size,
      chunk_overlap: settingsForm.chunk_overlap,
    })
    appStore.success('设置保存成功')
    await fetchCollection()
  } catch (_e) { /* noop */ }
}

const reprocessAll = async () => {
  try {
    await ElMessageBox.confirm('重新处理集合中的所有文档？这可能需要较长时间。', '确认', { type: 'warning' })
    await Promise.all(documents.value.map(doc => ragApi.reprocessDocument(doc.id)))
    appStore.success('重新处理任务已启动')
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const clearCollectionAction = async () => {
  try {
    await ElMessageBox.confirm('清空集合中的所有文档和分块？此操作不可撤销。', '警告', { type: 'warning' })
    await ragApi.clearCollection(route.params.id)
    appStore.success('集合已清空')
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const deleteCollectionAction = async () => {
  try {
    await ElMessageBox.confirm('永久删除此集合？所有数据将无法恢复。', '危险操作', { type: 'error' })
    await ragApi.deleteCollection(route.params.id)
    appStore.success('集合已删除')
    router.push('/knowledge')
  } catch (_e) { /* noop */ }
}

const saveEdit = async () => {
  try {
    await ragApi.updateCollection(route.params.id, {
      name: editForm.name,
      description: editForm.description,
    })
    collection.value.name = editForm.name
    collection.value.description = editForm.description
    appStore.success('保存成功')
    showEditDialog.value = false
  } catch (_e) { /* noop */ }
}
</script>

<style scoped>
.collection-detail {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.header-info h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0 0;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 40px;
  height: 40px;
  color: var(--primary-color);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.detail-tabs {
  background: transparent;
}

.tab-toolbar {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.doc-title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-content {
  font-size: 13px;
  line-height: 1.5;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.bulk-actions {
  margin-top: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-test-container {
  max-width: 800px;
}

.search-form {
  margin-bottom: 24px;
}

.search-options {
  margin: 16px 0;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.search-results h4 {
  margin: 0 0 16px 0;
}

.result-item {
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-score {
  font-weight: 500;
  color: var(--primary-color);
}

.result-content {
  font-size: 14px;
  line-height: 1.6;
}

.settings-card {
  margin-bottom: 16px;
  max-width: 600px;
}

.danger-zone {
  border-color: var(--danger-color);
}

.danger-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.danger-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.danger-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
}

.danger-info p {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.document-detail {
  padding: 0 8px;
}

.detail-meta {
  display: flex;
  gap: 16px;
  align-items: center;
  color: var(--text-secondary);
  font-size: 14px;
}

.detail-content,
.detail-chunks {
  margin-top: 24px;
}

.detail-content h4,
.detail-chunks h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
}

.content-box {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.chunk-preview {
  margin-bottom: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.chunk-tokens {
  font-family: monospace;
}

.chunk-text {
  font-size: 13px;
  line-height: 1.5;
}

.stats-content {
  padding: 0 8px;
}

.mini-stat {
  text-align: center;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.mini-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
}

.mini-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.chunk-distribution {
  margin-top: 24px;
}

.chunk-distribution h4 {
  margin: 0 0 16px 0;
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar-label {
  width: 70px;
  font-size: 13px;
}

.bar-track {
  flex: 1;
  height: 20px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s;
}

.bar-value {
  width: 50px;
  text-align: right;
  font-size: 13px;
  font-weight: 500;
}
</style>
