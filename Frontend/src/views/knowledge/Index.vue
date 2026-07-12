<template>
  <div class="knowledge-base">
    <div class="page-header">
      <div class="header-left">
        <h1>知识库</h1>
        <p class="subtitle">
          管理文档集合和 RAG 流水线
        </p>
      </div>
      <div class="header-actions">
        <el-button @click="showPipelineDialog = true">
          <Plus class="btn-icon" />
          新建流水线
        </el-button>
        <el-button
          type="primary"
          @click="showCollectionDialog = true"
        >
          <Plus class="btn-icon" />
          新建集合
        </el-button>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs
      v-model="activeTab"
      class="knowledge-tabs"
    >
      <el-tab-pane
        label="文档集合"
        name="collections"
      >
        <div class="collection-toolbar">
          <el-checkbox v-model="showProjectOnly">
            仅显示项目 Agent 记忆（project-*）
          </el-checkbox>
          <el-select
            v-model="teamFilter"
            placeholder="按团队筛选"
            clearable
            style="width: 200px"
          >
            <el-option
              label="全部（含个人）"
              value=""
            />
            <el-option
              label="仅我个人"
              value="mine"
            />
            <el-option
              v-for="t in tenantStore.tenants"
              :key="t.id"
              :label="t.name"
              :value="String(t.id)"
            />
          </el-select>
        </div>
        <div
          v-if="collections.length === 0 && !isLoading"
          class="empty-state"
        >
          <Database class="empty-icon" />
          <h3>暂无文档集合</h3>
          <p>创建您的第一个文档集合，上传文档构建知识库</p>
          <el-button
            type="primary"
            @click="showCollectionDialog = true"
          >
            创建集合
          </el-button>
        </div>

        <div
          v-else
          class="collections-grid"
        >
          <div
            v-for="collection in collections"
            :key="collection.id"
            class="collection-card"
            @click="selectCollection(collection)"
          >
            <div class="card-header">
              <div class="card-icon">
                <FolderOpen class="icon" />
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
                    <el-dropdown-item @click.stop="editCollection(collection)">
                      <Edit class="menu-icon" />
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item @click.stop="showAddDocumentDialog(collection)">
                      <Upload class="menu-icon" />
                      添加文档
                    </el-dropdown-item>
                    <el-dropdown-item @click.stop="handleClearCollection(collection)">
                      <Trash2 class="menu-icon" />
                      清空
                    </el-dropdown-item>
                    <el-dropdown-item
                      divided
                      class="danger"
                      @click.stop="handleDeleteCollection(collection)"
                    >
                      <Trash2 class="menu-icon" />
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <h3 class="card-title">
              {{ collection.name }}
              <el-tag
                v-if="collection.tenant_name"
                size="small"
                type="success"
                class="team-tag"
              >
                <Users class="tag-icon" />{{ collection.tenant_name }}
              </el-tag>
              <el-tag
                v-else
                size="small"
                type="info"
                class="team-tag"
              >
                个人
              </el-tag>
            </h3>
            <p class="card-desc">
              {{ collection.description || '暂无描述' }}
            </p>
            <div class="card-stats">
              <span class="stat">
                <FileText class="stat-icon" />
                {{ collection.document_count }} 文档
              </span>
              <span class="stat">
                <Layers class="stat-icon" />
                {{ collection.chunk_count }} 分块
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane
        label="RAG 流水线"
        name="pipelines"
      >
        <div
          v-if="pipelines.length === 0 && !isLoading"
          class="empty-state"
        >
          <GitBranch class="empty-icon" />
          <h3>暂无 RAG 流水线</h3>
          <p>创建 RAG 流水线，让 AI 能够基于知识库回答问题</p>
          <el-button
            type="primary"
            @click="showPipelineDialog = true"
          >
            创建流水线
          </el-button>
        </div>

        <div
          v-else
          class="pipelines-grid"
        >
          <div
            v-for="pipeline in pipelines"
            :key="pipeline.id"
            class="pipeline-card"
          >
            <div class="card-header">
              <div class="card-icon pipeline">
                <Bot class="icon" />
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
                    <el-dropdown-item @click.stop="testPipeline(pipeline)">
                      <Play class="menu-icon" />
                      测试
                    </el-dropdown-item>
                    <el-dropdown-item
                      divided
                      class="danger"
                      @click.stop="handleDeletePipeline(pipeline)"
                    >
                      <Trash2 class="menu-icon" />
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <h3 class="card-title">
              {{ pipeline.name }}
            </h3>
            <p class="card-desc">
              {{ pipeline.description || '暂无描述' }}
            </p>
            <div class="card-meta">
              <el-tag size="small">
                {{ pipeline.collection_name }}
              </el-tag>
              <span class="usage">{{ pipeline.usage_count }} 次查询</span>
            </div>
            <div class="card-actions">
              <el-button
                type="primary"
                size="small"
                @click="showQueryDialog(pipeline)"
              >
                查询
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Create Collection Dialog -->
    <el-dialog
      v-model="showCollectionDialog"
      title="创建文档集合"
      width="500px"
      destroy-on-close
      @closed="resetCollectionForm"
    >
      <el-form
        ref="collectionFormRef"
        :model="collectionForm"
        :rules="collectionRules"
        label-position="top"
      >
        <el-form-item
          label="名称"
          prop="name"
        >
          <el-input
            v-model="collectionForm.name"
            placeholder="输入集合名称"
          />
        </el-form-item>
        <el-form-item
          label="描述"
          prop="description"
        >
          <el-input
            v-model="collectionForm.description"
            type="textarea"
            :rows="3"
            placeholder="集合描述（可选）"
          />
        </el-form-item>
        <el-form-item label="向量存储">
          <el-select
            v-model="collectionForm.vector_store"
            placeholder="选择向量存储（可选）"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="store in ragStore.vectorStores"
              :key="store.id"
              :label="store.name"
              :value="store.id"
            />
          </el-select>
          <div
            v-if="!ragStore.vectorStores.length"
            class="form-item-tip"
          >
            暂无可用向量存储，将使用默认存储
          </div>
        </el-form-item>
        <el-form-item label="所属团队">
          <el-select
            v-model="collectionForm.tenant"
            placeholder="仅个人可见（不选择团队）"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="t in tenantStore.tenants"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
          <div class="form-item-tip">
            选择团队后，该团队所有成员均可查看和使用此知识库
          </div>
        </el-form-item>
        <el-form-item label="Embedding 模型">
          <el-select
            v-model="collectionForm.embedding_model"
            style="width: 100%"
          >
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
            <el-option
              label="nomic-embed-text（本地 Ollama）"
              value="nomic-embed-text"
            />
          </el-select>
          <div class="form-item-tip">
            未配置 OpenAI Key 时，选择 nomic-embed-text 可使用本机 Ollama 生成真实向量（需先执行 ollama pull nomic-embed-text）
          </div>
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
        <el-button @click="showCollectionDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleCreateCollection"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- Add Document Dialog -->
    <el-dialog
      v-model="showAddDocDialog"
      title="添加文档"
      width="600px"
    >
      <el-tabs v-model="addDocTab">
        <el-tab-pane
          label="文本输入"
          name="text"
        >
          <el-form
            ref="docFormRef"
            :model="docForm"
            label-position="top"
          >
            <el-form-item
              label="标题"
              prop="title"
            >
              <el-input
                v-model="docForm.title"
                placeholder="文档标题"
              />
            </el-form-item>
            <el-form-item
              label="内容"
              prop="content"
            >
              <el-input
                v-model="docForm.content"
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
          <el-form
            ref="urlFormRef"
            :model="urlForm"
            label-position="top"
          >
            <el-form-item
              label="URL"
              prop="url"
            >
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
        <el-button @click="showAddDocDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleAddDocument"
        >
          添加
        </el-button>
      </template>
    </el-dialog>

    <!-- Create Pipeline Dialog -->
    <el-dialog
      v-model="showPipelineDialog"
      title="创建 RAG 流水线"
      width="500px"
    >
      <el-form
        ref="pipelineFormRef"
        :model="pipelineForm"
        :rules="pipelineRules"
        label-position="top"
      >
        <el-form-item
          label="名称"
          prop="name"
        >
          <el-input
            v-model="pipelineForm.name"
            placeholder="输入流水线名称"
          />
        </el-form-item>
        <el-form-item
          label="描述"
          prop="description"
        >
          <el-input
            v-model="pipelineForm.description"
            type="textarea"
            :rows="2"
            placeholder="描述（可选）"
          />
        </el-form-item>
        <el-form-item
          label="文档集合"
          prop="collection"
        >
          <el-select
            v-model="pipelineForm.collection"
            style="width: 100%"
          >
            <el-option
              v-for="c in collections"
              :key="c.id"
              :label="c.name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="返回数量">
          <el-input-number
            v-model="pipelineForm.top_k"
            :min="1"
            :max="20"
          />
        </el-form-item>
        <el-form-item label="最低相似度">
          <el-slider
            v-model="pipelineForm.min_similarity"
            :min="0"
            :max="1"
            :step="0.05"
            show-input
          />
        </el-form-item>
        <el-form-item label="系统提示词">
          <el-input
            v-model="pipelineForm.system_prompt"
            type="textarea"
            :rows="3"
            placeholder="自定义系统提示词"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="pipelineForm.include_sources">
            包含来源信息
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPipelineDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleCreatePipeline"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- Query Dialog -->
    <el-dialog
      v-model="showQueryDialogVisible"
      title="RAG 查询"
      width="700px"
    >
      <div class="query-container">
        <el-form @submit.prevent="handleQuery">
          <el-form-item>
            <el-input
              v-model="queryText"
              type="textarea"
              :rows="3"
              placeholder="输入您的问题..."
              @keydown.enter.ctrl="handleQuery"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="isQuerying"
              @click="handleQuery"
            >
              查询
            </el-button>
          </el-form-item>
        </el-form>

        <div
          v-if="queryResult"
          class="query-result"
        >
          <div class="response-section">
            <h4>回答</h4>
            <div class="response-content">
              {{ queryResult.response }}
            </div>
          </div>

          <div
            v-if="queryResult.sources?.length"
            class="sources-section"
          >
            <h4>来源</h4>
            <div
              v-for="(source, idx) in queryResult.sources"
              :key="idx"
              class="source-item"
            >
              <div class="source-content">
                {{ source.content }}
              </div>
              <div class="source-score">
                相似度: {{ (source.score * 100).toFixed(1) }}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRAGStore } from '@/stores/rag'
import { useAppStore } from '@/stores/app'
import { useTenantStore } from '@/stores/tenant'
import {
  Plus, Database, FolderOpen, FileText, Layers, GitBranch, Bot,
  MoreVertical, Edit, Trash2, Upload, Play, Users
} from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { APP_CONFIG } from '@/config'

const DEFAULT_EMBEDDING_MODEL = APP_CONFIG.embedding.defaultModel
const ragStore = useRAGStore()
const appStore = useAppStore()
const tenantStore = useTenantStore()
const router = useRouter()
const route = useRoute()

const projectFilter = computed(() => String(route.query.collection || route.query.project || ''))
const showProjectOnly = ref(false)
const teamFilter = ref('')

const activeTab = ref('collections')
const showCollectionDialog = ref(false)
const showAddDocDialog = ref(false)
const showPipelineDialog = ref(false)
const showQueryDialogVisible = ref(false)
const addDocTab = ref('text')
const selectedCollection = ref(null)
const selectedPipeline = ref(null)
const queryText = ref('')
const queryResult = ref(null)

const collectionFormRef = ref(null)
const docFormRef = ref(null)
const urlFormRef = ref(null)
const pipelineFormRef = ref(null)

const collectionForm = reactive({
  name: '',
  description: '',
  vector_store: null,
  tenant: null,
  embedding_model: DEFAULT_EMBEDDING_MODEL,
  chunk_size: 1000,
  chunk_overlap: 200
})

const docForm = reactive({
  title: '',
  content: ''
})

const urlForm = reactive({
  url: '',
  title: ''
})

const pipelineForm = reactive({
  name: '',
  description: '',
  collection: null,
  top_k: 5,
  min_similarity: 0.7,
  system_prompt: '你是一个有帮助的助手。使用以下上下文信息回答用户问题。',
  include_sources: true
})

const collectionRules = {
  name: [{ required: true, message: '请输入集合名称', trigger: 'blur' }]
}

const pipelineRules = {
  name: [{ required: true, message: '请输入流水线名称', trigger: 'blur' }],
  collection: [{ required: true, message: '请选择文档集合', trigger: 'change' }]
}

const collections = computed(() => {
  let list = ragStore.collections
  if (showProjectOnly.value) {
    list = list.filter((c) => String(c.name || '').startsWith('project-'))
  }
  if (projectFilter.value) {
    list = list.filter((c) => String(c.id) === projectFilter.value || String(c.name) === projectFilter.value)
  }
  if (teamFilter.value === 'mine') {
    list = list.filter((c) => !c.tenant)
  } else if (teamFilter.value) {
    list = list.filter((c) => String(c.tenant || '') === teamFilter.value)
  }
  return list
})
const pipelines = computed(() => ragStore.pipelines)
const isLoading = computed(() => ragStore.isLoading)
const isSaving = computed(() => ragStore.isSaving)
const isQuerying = computed(() => ragStore.isQuerying)

function selectCollection(collection) {
  router.push(`/knowledge/${collection.id}`)
}

function editCollection(collection) {
  selectedCollection.value = collection
  Object.assign(collectionForm, {
    name: collection.name,
    description: collection.description,
    tenant: collection.tenant || null,
    embedding_model: collection.embedding_model,
    chunk_size: collection.chunk_size,
    chunk_overlap: collection.chunk_overlap
  })
  showCollectionDialog.value = true
}

function showAddDocumentDialog(collection) {
  selectedCollection.value = collection
  addDocTab.value = 'text'
  Object.assign(docForm, { title: '', content: '' })
  Object.assign(urlForm, { url: '', title: '' })
  showAddDocDialog.value = true
}

async function handleCreateCollection() {
  const valid = await collectionFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    if (selectedCollection.value) {
      await ragStore.updateCollection(selectedCollection.value.id, collectionForm)
      appStore.success('集合已更新')
    } else {
      await ragStore.createCollection(collectionForm)
      appStore.success('集合已创建')
    }
    showCollectionDialog.value = false
    resetCollectionForm()
    await ragStore.fetchCollections()
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleAddDocument() {
  if (!selectedCollection.value) return

  try {
    if (addDocTab.value === 'text') {
      if (!docForm.content) {
        appStore.error('请输入文档内容')
        return
      }
      await ragStore.addDocument(selectedCollection.value.id, {
        title: docForm.title || 'Untitled',
        content: docForm.content
      })
    } else {
      if (!urlForm.url) {
        appStore.error('请输入 URL')
        return
      }
      await ragStore.addUrl(selectedCollection.value.id, {
        url: urlForm.url,
        title: urlForm.title
      })
    }
    appStore.success('文档已添加')
    showAddDocDialog.value = false
    await ragStore.fetchCollections()
  } catch (err) {
    appStore.error('添加失败')
  }
}

async function handleClearCollection(collection) {
  try {
    await ElMessageBox.confirm('确定要清空此集合的所有文档吗？', '清空确认', { type: 'warning' })
    await ragStore.clearCollection(collection.id)
    appStore.success('集合已清空')
    await ragStore.fetchCollections()
  } catch (err) {
    if (err !== 'cancel') appStore.error('操作失败')
  }
}

async function handleDeleteCollection(collection) {
  try {
    await ElMessageBox.confirm(`确定要删除集合 "${collection.name}" 吗？`, '删除确认', { type: 'warning' })
    await ragStore.deleteCollection(collection.id)
    appStore.success('集合已删除')
  } catch (err) {
    if (err !== 'cancel') appStore.error('删除失败')
  }
}

async function handleCreatePipeline() {
  const valid = await pipelineFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await ragStore.createPipeline(pipelineForm)
    appStore.success('流水线已创建')
    showPipelineDialog.value = false
    resetPipelineForm()
    await ragStore.fetchPipelines()
  } catch (err) {
    appStore.error('创建失败')
  }
}

async function handleDeletePipeline(pipeline) {
  try {
    await ElMessageBox.confirm(`确定要删除流水线 "${pipeline.name}" 吗？`, '删除确认', { type: 'warning' })
    await ragStore.deletePipeline(pipeline.id)
    appStore.success('流水线已删除')
  } catch (err) {
    if (err !== 'cancel') appStore.error('删除失败')
  }
}

function showQueryDialog(pipeline) {
  selectedPipeline.value = pipeline
  queryText.value = ''
  queryResult.value = null
  showQueryDialogVisible.value = true
}

async function handleQuery() {
  if (!queryText.value.trim() || !selectedPipeline.value) return

  try {
    queryResult.value = await ragStore.queryPipeline(selectedPipeline.value.id, queryText.value)
  } catch (err) {
    appStore.error('查询失败')
  }
}

function testPipeline(pipeline) {
  showQueryDialog(pipeline)
}

function resetCollectionForm() {
  Object.assign(collectionForm, {
    name: '',
    description: '',
    tenant: null,
    embedding_model: DEFAULT_EMBEDDING_MODEL,
    chunk_size: 1000,
    chunk_overlap: 200
  })
  selectedCollection.value = null
}

function resetPipelineForm() {
  Object.assign(pipelineForm, {
    name: '',
    description: '',
    collection: null,
    top_k: 5,
    min_similarity: 0.7,
    system_prompt: '你是一个有帮助的助手。使用以下上下文信息回答用户问题。',
    include_sources: true
  })
}

onMounted(async () => {
  if (route.query.collection) {
    showProjectOnly.value = true
  }
  await Promise.all([
    ragStore.fetchCollections(),
    ragStore.fetchPipelines(),
    ragStore.fetchVectorStores(),
    tenantStore.fetchTenants()
  ])
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.knowledge-base {
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
    color: var(--text-secondary);
    margin: $spacing-1 0 0;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.knowledge-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: $spacing-6;
  }
}

.empty-state {
  text-align: center;
  padding: $spacing-12;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--text-tertiary);
    margin-bottom: $spacing-4;
  }

  h3 {
    font-size: $font-size-lg;
    margin: 0 0 $spacing-2;
  }

  p {
    color: var(--text-secondary);
    margin: 0 0 $spacing-4;
  }
}

.collections-grid {
  margin-bottom: 12px;
}

.collection-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-4;
  margin-bottom: 12px;
}

.team-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: $spacing-2;
  font-weight: $font-weight-normal;
  vertical-align: middle;
}

.tag-icon {
  width: 12px;
  height: 12px;
}
.pipelines-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: $spacing-4;
}

.collection-card,
.pipeline-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: $color-primary;
    transform: translateY(-2px);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-3;
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba($color-primary, 0.15);

  .icon {
    width: 20px;
    height: 20px;
    color: $color-primary;
  }

  &.pipeline {
    background: linear-gradient(135deg, rgba($color-primary, 0.15), rgba($color-secondary, 0.15));
  }
}

.card-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  margin: 0 0 $spacing-2;
}

.card-desc {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0 0 $spacing-3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-stats {
  display: flex;
  gap: $spacing-4;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  .stat {
    display: flex;
    align-items: center;
    gap: $spacing-1;
  }

  .stat-icon {
    width: 14px;
    height: 14px;
  }
}

.card-meta {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  margin-bottom: $spacing-3;

  .usage {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.card-actions {
  display: flex;
  gap: $spacing-2;
}

.menu-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-2;
}

.danger {
  color: $color-error;
}

.query-container {
  .query-result {
    margin-top: $spacing-6;
  }

  .response-section,
  .sources-section {
    margin-bottom: $spacing-4;

    h4 {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      margin: 0 0 $spacing-2;
      color: var(--text-secondary);
    }
  }

  .response-content {
    background: var(--bg-tertiary);
    padding: $spacing-4;
    border-radius: $radius-lg;
    font-size: $font-size-sm;
    line-height: 1.7;
    white-space: pre-wrap;
  }

  .source-item {
    background: var(--bg-tertiary);
    padding: $spacing-3;
    border-radius: $radius-md;
    margin-bottom: $spacing-2;

    .source-content {
      font-size: $font-size-sm;
      margin-bottom: $spacing-2;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .source-score {
      font-size: $font-size-xs;
      color: var(--text-tertiary);
    }
  }
}

.form-item-tip {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-top: $spacing-1;
}
</style>


