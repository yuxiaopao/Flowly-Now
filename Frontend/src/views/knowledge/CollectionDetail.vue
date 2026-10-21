<template>
  <PageShell
    width="wide"
    class="collection-detail"
  >
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
        <el-button
          :loading="importingGuides"
          @click="importGuides"
        >
          导入 Flowly 使用指南
        </el-button>
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

    <el-alert
      :title="RAG_TEXT.modeHint"
      type="info"
      :closable="false"
      show-icon
    />

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
              value="completed"
            />
            <el-option
              label="待处理"
              value="pending"
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
              <el-tooltip
                v-if="row.error_message"
                :content="row.error_message"
              >
                <el-text type="danger">
                  查看原因
                </el-text>
              </el-tooltip>
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
            prop="char_count"
            label="字符数"
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

      <el-tab-pane
        :label="RAG_TEXT.askTab"
        name="ask"
      >
        <RAGQuestionPanel
          :collection-id="String(route.params.id)"
          @open-document="viewDocumentById"
        />
      </el-tab-pane>

      <!-- Search Tab -->
      <el-tab-pane
        label="搜索测试"
        name="search"
      >
        <div class="search-test-container">
          <el-card shadow="hover">
            <template #header>
              <span>{{ RAG_TEXT.searchTitle }}</span>
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
                <el-form label-width="100px">
                  <el-form-item label="返回数量">
                    <el-input-number
                      v-model="searchTopK"
                      :min="1"
                      :max="50"
                    />
                  </el-form-item>
                  <el-form-item label="最低相关度">
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
                    相关度: {{ (result.score * 100).toFixed(1) }}%
                  </span>
                  <el-tag size="small">
                    <el-button
                      link
                      @click="viewDocumentById(result.document_id)"
                    >
                      {{ result.document_title }}
                    </el-button>
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
            <el-form-item label="检索方式">
              <el-select v-model="settingsForm.retrieval_mode">
                <el-option
                  v-for="mode in RETRIEVAL_MODES"
                  :key="mode.value"
                  :value="mode.value"
                  :label="mode.label"
                />
              </el-select>
            </el-form-item>
            <el-form-item
              v-if="settingsForm.retrieval_mode !== 'keyword'"
              label="Embedding 模型"
            >
              <el-input
                v-model="settingsForm.embedding_model"
                placeholder="例如 ollama:nomic-embed-text"
              />
            </el-form-item>
            <el-form-item label="分块策略">
              <el-select v-model="settingsForm.chunk_strategy">
                <el-option
                  v-for="strategy in CHUNK_STRATEGIES"
                  :key="strategy.value"
                  :value="strategy.value"
                  :label="strategy.label"
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
            <el-form-item label="向量存储">
              <el-text>{{ collection.vector_store_name }}</el-text>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="savingSettings"
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
                :loading="reindexing"
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
      width="min(600px, calc(100vw - 32px))"
    >
      <el-tabs v-model="uploadTab">
        <el-tab-pane
          label="文件上传"
          name="file"
        >
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :accept="fileAccept"
            :limit="RAG_CONFIG.maxUploadFiles"
            :file-list="fileList"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            drag
          >
            <el-icon class="el-icon--upload">
              <upload-filled />
            </el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 {{ fileAccept }}，单个文件不超过 {{ formatSize(maxFileBytes) }}
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
      width="min(800px, calc(100vw - 32px))"
    >
      <div
        v-if="selectedDocument"
        class="document-detail"
      >
        <div class="detail-meta">
          <el-tag :type="getStatusType(selectedDocument.status)">
            {{ getStatusLabel(selectedDocument.status) }}
          </el-tag>
          <span>{{ selectedDocument.chunk_count }} 分块</span>
          <span>{{ formatDateTime(selectedDocument.created_at) }}</span>
        </div>
        <el-alert
          v-if="selectedDocument.error_message"
          :title="selectedDocument.error_message"
          type="error"
          :closable="false"
        />
        <el-link
          v-if="selectedDocument.source_url"
          :href="selectedDocument.source_url"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ selectedDocument.source_url }}
        </el-link>
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
            v-for="(chunk, index) in selectedDocument.chunks"
            :key="index"
            class="chunk-preview"
          >
            <div class="chunk-header">
              <span>分块 {{ index + 1 }}</span>
              <span class="chunk-tokens">{{ chunk.content.length }} 字符</span>
            </div>
            <div class="chunk-text">
              {{ chunk.content }}
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- Edit Collection Dialog -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑集合"
      width="min(500px, calc(100vw - 32px))"
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
      width="min(600px, calc(100vw - 32px))"
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
  </PageShell>
</template>

<script setup>
import PageShell from '@/components/layout/PageShell.vue'
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
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
import { FileText, Layers, Database } from 'lucide-vue-next'
import RAGQuestionPanel from '@/components/common/RAGQuestionPanel.vue'
import { RAG_CONFIG, RAG_TEXT, DOCUMENT_STATUSES, RETRIEVAL_MODES, CHUNK_STRATEGIES } from '@/config/rag'
import { loadRagPages, chunkDistribution as computeChunkDistribution, validateRagFile } from '@/utils/rag'

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
const savingSettings = ref(false)
const importingGuides = ref(false)
const reindexing = ref(false)
const fileAccept = ref(RAG_CONFIG.fileAccept)
const maxFileBytes = ref(RAG_CONFIG.maxFileBytes)
let pollingTimer
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
  chunk_size: RAG_CONFIG.chunkSize,
  chunk_overlap: RAG_CONFIG.chunkOverlap,
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
const chunkPageSize = ref(RAG_CONFIG.chunkPageSize)
const statusFilter = ref('')
const searchTopK = ref(RAG_CONFIG.topK)
const searchMinSimilarity = ref(RAG_CONFIG.minSimilarity)
const searchResults = ref([])

const textForm = reactive({ title: '', content: '' })
const urlForm = reactive({ url: '', title: '' })

const settingsForm = reactive({
  embedding_model: DEFAULT_EMBEDDING_MODEL,
  chunk_size: RAG_CONFIG.chunkSize,
  chunk_overlap: RAG_CONFIG.chunkOverlap,
  retrieval_mode: 'keyword',
  chunk_strategy: 'recursive'
})

const editForm = reactive({
  name: '',
  description: ''
})

const chunkDistribution = computed(() => computeChunkDistribution(chunks.value))

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
      chunk_overlap: response.chunk_overlap ?? settingsForm.chunk_overlap,
      retrieval_mode: response.retrieval_mode,
      chunk_strategy: response.chunk_strategy,
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
    stats.value.storage = data.storage_bytes ?? 0
    stats.value.totalTokens = data.token_count ?? 0
    stats.value.avgTokens = stats.value.chunks ? Math.round(stats.value.totalTokens / stats.value.chunks) : 0
  } catch {
    // Error shown via API interceptor
  }
}

async function fetchDocuments() {
  loadingDocuments.value = true
  try {
    documents.value = await loadRagPages(ragApi.getDocuments, { collection: route.params.id })
  } catch {
    // Error shown via API interceptor
  } finally {
    loadingDocuments.value = false
  }
}

async function fetchChunks() {
  loadingChunks.value = true
  try {
    chunks.value = (await loadRagPages(ragApi.getChunks, { collection: route.params.id }))
      .map(chunk => ({ ...chunk, char_count: chunk.content.length }))
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
  try {
    const capabilities = await ragApi.getCapabilities()
    fileAccept.value = capabilities.file_extensions.join(',')
    maxFileBytes.value = capabilities.max_file_bytes
  } catch { /* API interceptor displays the error. */ }
  pollingTimer = setInterval(() => {
    if (!loadingDocuments.value && documents.value.some(doc => doc.status === 'processing')) refreshCollectionData()
  }, RAG_CONFIG.pollInterval)
})
onUnmounted(() => clearInterval(pollingTimer))
watch(() => route.params.id, () => { selectedDocuments.value = []; searchResults.value = []; refreshCollectionData() })

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const getStatusType = status => DOCUMENT_STATUSES[status]?.type || 'info'
const getStatusLabel = status => DOCUMENT_STATUSES[status]?.label || status

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
  if (uploading.value) return
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
        const error = validateRagFile(rawFile, maxFileBytes.value, fileAccept.value)
        if (error) { appStore.error(error); return }
        const formData = new FormData()
        formData.append('file', rawFile)
        await ragApi.uploadFile(collectionId, formData)
        fileList.value = fileList.value.filter(item => item !== file)
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
  } catch {
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

const viewDocumentById = id => viewDocument({ id })

const reprocessDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(`重新处理文档「${doc.title}」？`, '确认', { type: 'info' })
    await ragApi.reprocessDocument(doc.id)
    appStore.success('文档重新处理完成')
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
    const results = await Promise.allSettled(selectedDocuments.value.map(doc => ragApi.reprocessDocument(doc.id)))
    const failed = results.filter(result => result.status === 'rejected').length
    if (failed) appStore.error(`${failed} 个文档处理失败，请查看文档状态`)
    else appStore.success('批量重新处理完成')
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const deleteDocuments = async () => {
  try {
    await ElMessageBox.confirm(`删除选中的 ${selectedDocuments.value.length} 个文档？`, '确认', { type: 'warning' })
    const results = await Promise.allSettled(selectedDocuments.value.map(doc => ragApi.deleteDocument(doc.id)))
    const failed = results.filter(result => result.status === 'rejected').length
    if (failed) appStore.error(`${failed} 个文档删除失败，请重试`)
    else appStore.success('批量删除成功')
    selectedDocuments.value = []
    await refreshCollectionData()
  } catch (_e) { /* noop */ }
}

const performSearch = async () => {
  if (!semanticSearchQuery.value.trim()) return
  searching.value = true
  hasSearched.value = true
  searchResults.value = []
  try {
    const response = await ragApi.searchCollection(route.params.id, {
      query: semanticSearchQuery.value.trim(),
      top_k: searchTopK.value,
      min_similarity: searchMinSimilarity.value,
    })
    const results = response.results || []
    searchResults.value = results
      .filter(r => (r.score ?? 0) >= searchMinSimilarity.value)
      .map(r => ({
        score: r.score ?? 0,
        content: r.content || '',
        document_title: r.metadata?.title || r.documentTitle || '未知文档',
        document_id: r.metadata?.doc_id,
      }))
  } catch { /* API interceptor displays the error. */ } finally {
    searching.value = false
  }
}

const importGuides = async () => {
  if (importingGuides.value) return
  importingGuides.value = true
  try {
    const result = await ragApi.importGuides(route.params.id)
    if (result.failed) appStore.error(`${result.completed} 份成功，${result.failed} 份失败：${result.results.filter(item => !item.success).map(item => item.error).join('；')}`)
    else appStore.success('Flowly 使用指南已导入，可在知识问答中提问')
  } catch { /* API interceptor displays the error. */ }
  finally { importingGuides.value = false; await refreshCollectionData() }
}

const saveSettings = async () => {
  if (savingSettings.value) return
  if (settingsForm.chunk_overlap >= settingsForm.chunk_size) { appStore.error('分块重叠必须小于分块大小'); return }
  savingSettings.value = true
  try {
    if (documents.value.length) await ElMessageBox.confirm('修改索引配置后，旧索引将暂停检索，需要重新处理全部文档。继续保存？', '修改索引配置', { type: 'warning' })
    await ragApi.updateCollection(route.params.id, {
      embedding_model: settingsForm.embedding_model,
      chunk_size: settingsForm.chunk_size,
      chunk_overlap: settingsForm.chunk_overlap,
      retrieval_mode: settingsForm.retrieval_mode,
      chunk_strategy: settingsForm.chunk_strategy,
    })
    appStore.success('设置已保存；索引参数变化后请重新处理全部文档')
    await refreshCollectionData()
  } catch { /* Cancellation or API error. */ } finally { savingSettings.value = false }
}

const reprocessAll = async () => {
  if (reindexing.value) return
  try {
    await ElMessageBox.confirm('重新处理集合中的所有文档？这可能需要较长时间。', '确认', { type: 'warning' })
    reindexing.value = true
    const result = await ragApi.reindexCollection(route.params.id)
    if (result.failed) appStore.error(`${result.completed} 个完成，${result.failed} 个失败，请查看文档错误原因`)
    else appStore.success(`${result.completed} 个文档重新处理完成`)
    await refreshCollectionData()
  } catch { /* Cancellation or API error. */ } finally { reindexing.value = false }
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
  flex-wrap: wrap;
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
  flex-wrap: wrap;
  gap: var(--spacing-3, 12px);
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
.collection-detail :deep(.el-alert--info) {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-3, 12px);
}

@media (max-width: 768px) {
  .page-header { flex-wrap: wrap; gap: var(--spacing-4, 16px); }
  .stats-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat-content { gap: var(--spacing-2, 8px); }
  .stat-icon { width: 24px; height: 24px; }
  .stat-value { font-size: 16px; overflow-wrap: anywhere; }
  .tab-toolbar, .danger-item, .bulk-actions { flex-wrap: wrap; }
  .tab-toolbar > * { max-width: 100%; }
  .search-options { padding: var(--spacing-2, 8px); }
}
</style>
