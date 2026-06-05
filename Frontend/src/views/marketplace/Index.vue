<template>
  <div class="marketplace-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">
          模板市场
        </h1>
        <p class="page-description">
          发现、安装和分享工作流模板
        </p>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          @click="showSubmitDialog = true"
        >
          <el-icon><Upload /></el-icon> 提交模板
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-section">
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模板..."
          :prefix-icon="Search"
          clearable
          size="large"
          class="search-input"
        />
      </div>
      <div class="filter-bar">
        <el-select
          v-model="categoryFilter"
          placeholder="分类"
          clearable
          style="width: 150px"
        >
          <el-option
            label="全部"
            value=""
          />
          <el-option
            label="AI 助手"
            value="ai-assistant"
          />
          <el-option
            label="内容生成"
            value="content"
          />
          <el-option
            label="数据处理"
            value="data"
          />
          <el-option
            label="自动化"
            value="automation"
          />
          <el-option
            label="聊天机器人"
            value="chatbot"
          />
          <el-option
            label="分析报告"
            value="analytics"
          />
        </el-select>
        <el-select
          v-model="sortBy"
          style="width: 150px"
        >
          <el-option
            label="最受欢迎"
            value="popular"
          />
          <el-option
            label="最新发布"
            value="newest"
          />
          <el-option
            label="评分最高"
            value="rating"
          />
          <el-option
            label="名称 A-Z"
            value="name"
          />
        </el-select>
        <div class="view-toggle">
          <el-button
            :type="viewMode === 'grid' ? 'primary' : 'default'"
            @click="viewMode = 'grid'"
          >
            <el-icon><Grid /></el-icon>
          </el-button>
          <el-button
            :type="viewMode === 'list' ? 'primary' : 'default'"
            @click="viewMode = 'list'"
          >
            <el-icon><List /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 模板统计 -->
    <div class="stats-bar">
      <span class="stats-item">共 {{ filteredTemplates.length }} 个模板</span>
      <el-divider direction="vertical" />
      <span class="stats-item">本周新增 {{ weeklyNewCount }} 个</span>
    </div>

    <!-- 模板列表 - 网格视图 -->
    <div
      v-if="viewMode === 'grid'"
      class="templates-grid"
    >
      <div
        v-for="template in filteredTemplates"
        :key="template.id"
        class="template-card"
        @click="showTemplateDetail(template)"
      >
        <div class="card-preview">
          <div class="preview-placeholder">
            <el-icon :size="48">
              <component :is="getCategoryIcon(getTemplateCategory(template))" />
            </el-icon>
          </div>
          <div class="preview-overlay">
            <el-button
              type="primary"
              size="large"
              @click.stop="installTemplate(template)"
            >
              安装
            </el-button>
            <el-button
              size="large"
              @click.stop="previewTemplate(template)"
            >
              预览
            </el-button>
          </div>
        </div>
        <div class="card-content">
          <div class="card-header">
            <h3 class="card-title">
              {{ template.name }}
            </h3>
            <el-tag
              size="small"
              :type="getCategoryType(getTemplateCategory(template))"
            >
              {{ getCategoryLabel(getTemplateCategory(template)) }}
            </el-tag>
          </div>
          <p class="card-description">
            {{ template.description }}
          </p>
          <div class="card-meta">
            <div class="meta-item">
              <el-icon><User /></el-icon>
              <span>{{ getTemplateAuthor(template) }}</span>
            </div>
            <div class="meta-item">
              <el-icon><Download /></el-icon>
              <span>{{ getTemplateInstallCount(template) }}</span>
            </div>
            <div class="meta-item">
              <el-icon><Star /></el-icon>
              <span>{{ getTemplateRating(template) }}</span>
            </div>
          </div>
          <div class="card-tags">
            <el-tag
              v-for="tag in template.tags.slice(0, 3)"
              :key="tag"
              size="small"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 模板列表 - 列表视图 -->
    <div
      v-else
      class="templates-list"
    >
      <el-card
        v-for="template in filteredTemplates"
        :key="template.id"
        shadow="hover"
        class="template-list-item"
        @click="showTemplateDetail(template)"
      >
        <div class="list-item-content">
          <div class="list-item-icon">
            <el-icon :size="32">
              <component :is="getCategoryIcon(getTemplateCategory(template))" />
            </el-icon>
          </div>
          <div class="list-item-info">
            <div class="list-item-header">
              <h3 class="list-item-title">
                {{ template.name }}
              </h3>
              <el-tag
                size="small"
                :type="getCategoryType(getTemplateCategory(template))"
              >
                {{ getCategoryLabel(getTemplateCategory(template)) }}
              </el-tag>
            </div>
            <p class="list-item-description">
              {{ template.description }}
            </p>
            <div class="list-item-meta">
              <span><el-icon><User /></el-icon> {{ getTemplateAuthor(template) }}</span>
              <span><el-icon><Download /></el-icon> {{ getTemplateInstallCount(template) }} 安装</span>
              <span><el-icon><Star /></el-icon> {{ getTemplateRating(template) }} 评分</span>
              <span><el-icon><Clock /></el-icon> {{ formatDate(template.created_at) }}</span>
            </div>
          </div>
          <div class="list-item-actions">
            <el-button
              type="primary"
              @click.stop="installTemplate(template)"
            >
              安装
            </el-button>
            <el-button @click.stop="previewTemplate(template)">
              预览
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="totalTemplates"
        :page-sizes="[12, 24, 48]"
        layout="total, sizes, prev, pager, next"
      />
    </div>

    <!-- 模板详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="selectedTemplate?.name"
      width="800px"
      class="template-detail-dialog"
    >
      <div
        v-if="selectedTemplate"
        class="template-detail"
      >
        <div class="detail-preview">
          <div class="preview-placeholder large">
            <el-icon :size="80">
              <component :is="getCategoryIcon(getTemplateCategory(selectedTemplate))" />
            </el-icon>
          </div>
        </div>

        <div class="detail-info">
          <div class="detail-header">
            <h2>{{ selectedTemplate.name }}</h2>
            <el-tag
              :type="getCategoryType(getTemplateCategory(selectedTemplate))"
              size="large"
            >
              {{ getCategoryLabel(getTemplateCategory(selectedTemplate)) }}
            </el-tag>
          </div>

          <p class="detail-description">
            {{ selectedTemplate.description }}
          </p>

          <div class="detail-stats">
            <div class="stat-item">
              <el-icon><Download /></el-icon>
              <span>{{ getTemplateInstallCount(selectedTemplate) }} 次安装</span>
            </div>
            <div class="stat-item">
              <el-icon><Star /></el-icon>
              <span>{{ getTemplateRating(selectedTemplate) }} 评分</span>
            </div>
            <div class="stat-item">
              <el-icon><User /></el-icon>
              <span>{{ getTemplateAuthor(selectedTemplate) }}</span>
            </div>
            <div class="stat-item">
              <el-icon><Clock /></el-icon>
              <span>{{ formatDate(selectedTemplate.created_at) }}</span>
            </div>
          </div>

          <el-divider />

          <div class="detail-section">
            <h4>标签</h4>
            <div class="detail-tags">
              <el-tag
                v-for="tag in getTemplateTags(selectedTemplate)"
                :key="tag"
                size="small"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>

          <div class="detail-section">
            <h4>功能特点</h4>
            <ul class="feature-list">
              <li
                v-for="feature in getTemplateFeatures(selectedTemplate)"
                :key="feature"
              >
                <el-icon><Check /></el-icon>
                {{ feature }}
              </li>
            </ul>
          </div>

          <div class="detail-section">
            <h4>节点组成</h4>
            <div class="node-list">
              <div
                v-for="node in getTemplateNodes(selectedTemplate)"
                :key="node.id"
                class="node-item"
              >
                <el-icon><component :is="getNodeIcon(node.type)" /></el-icon>
                <span>{{ node.name }}</span>
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ node.type }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">
          关闭
        </el-button>
        <el-button @click="previewTemplate(selectedTemplate)">
          预览工作流
        </el-button>
        <el-button
          type="primary"
          @click="installTemplate(selectedTemplate)"
        >
          <el-icon><Download /></el-icon> 安装模板
        </el-button>
      </template>
    </el-dialog>

    <!-- 提交模板对话框 -->
    <el-dialog
      v-model="showSubmitDialog"
      title="提交模板"
      width="600px"
    >
      <el-form
        ref="submitFormRef"
        :model="submitForm"
        :rules="submitRules"
        label-width="100px"
      >
        <el-form-item
          label="模板名称"
          prop="name"
        >
          <el-input
            v-model="submitForm.name"
            placeholder="给你的模板起个名字"
          />
        </el-form-item>
        <el-form-item
          label="描述"
          prop="description"
        >
          <el-input
            v-model="submitForm.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述模板的功能"
          />
        </el-form-item>
        <el-form-item
          label="分类"
          prop="category"
        >
          <el-select
            v-model="submitForm.category"
            placeholder="选择分类"
          >
            <el-option
              label="AI 助手"
              value="ai-assistant"
            />
            <el-option
              label="内容生成"
              value="content"
            />
            <el-option
              label="数据处理"
              value="data"
            />
            <el-option
              label="自动化"
              value="automation"
            />
            <el-option
              label="聊天机器人"
              value="chatbot"
            />
            <el-option
              label="分析报告"
              value="analytics"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="submitForm.tags"
            multiple
            filterable
            allow-create
            placeholder="添加标签"
          >
            <el-option
              label="GPT"
              value="gpt"
            />
            <el-option
              label="Claude"
              value="claude"
            />
            <el-option
              label="LangChain"
              value="langchain"
            />
            <el-option
              label="RAG"
              value="rag"
            />
            <el-option
              label="API"
              value="api"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="工作流JSON"
          prop="workflow"
        >
          <el-input
            v-model="submitForm.workflow"
            type="textarea"
            :rows="10"
            placeholder="粘贴工作流 JSON 数据"
            style="font-family: monospace"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="submitForm.isPublic">
            公开模板（其他用户可以发现和使用）
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSubmitDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitTemplate"
        >
          提交审核
        </el-button>
      </template>
    </el-dialog>

    <!-- 工作流预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      title="模板预览"
      width="90%"
      fullscreen
    >
      <div class="workflow-preview-container">
        <div class="preview-toolbar">
          <el-button @click="zoomIn">
            放大
          </el-button>
          <el-button @click="zoomOut">
            缩小
          </el-button>
          <el-button @click="resetZoom">
            重置
          </el-button>
          <span class="zoom-level">{{ Math.round(previewZoom * 100) }}%</span>
        </div>
        <div
          class="preview-canvas"
          :style="{ transform: `scale(${previewZoom})` }"
        >
          <div class="workflow-nodes">
            <div
              v-for="node in previewNodes"
              :key="node.id"
              class="preview-node"
              :class="node.type"
              :style="{ left: node.x + 'px', top: node.y + 'px' }"
            >
              <div class="node-header">
                <el-icon><component :is="getNodeIcon(node.type)" /></el-icon>
                <span>{{ node.name }}</span>
              </div>
              <div class="node-content">
                {{ node.description || node.type }}
              </div>
            </div>
          </div>
          <svg class="workflow-edges">
            <line
              v-for="(edge, index) in previewEdges"
              :key="index"
              :x1="edge.sourceX"
              :y1="edge.sourceY"
              :x2="edge.targetX"
              :y2="edge.targetY"
              stroke="#409EFF"
              stroke-width="2"
              marker-end="url(#arrow)"
            />
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path
                  d="M 0 0 L 10 5 L 0 10 z"
                  fill="#409EFF"
                />
              </marker>
            </defs>
          </svg>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import {
  Search, Upload, Grid, List, Download, Star, User, Clock, Check,
  Document, ChatLineSquare, DataAnalysis, Setting, Message, TrendCharts
} from '@element-plus/icons-vue'
import { useMarketplaceStore } from '@/stores/marketplace'
import {
  getTemplateAuthor,
  getTemplateCategory,
  getTemplateFeatures,
  getTemplateInstallCount,
  getTemplateNodes,
  getTemplateRating,
  getTemplateTags,
} from '@/utils/workflowTransform'

const marketplaceStore = useMarketplaceStore()
const appStore = useAppStore()

// State
const searchQuery = ref('')
const categoryFilter = ref('')
const sortBy = ref('popular')
const viewMode = ref('grid')
const currentPage = ref(1)
const pageSize = ref(24)
const weeklyNewCount = computed(() => {
  const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
  return marketplaceStore.templates.filter(template => new Date(template.created_at).getTime() >= oneWeekAgo).length
})
const showDetailDialog = ref(false)
const showSubmitDialog = ref(false)
const showPreviewDialog = ref(false)
const selectedTemplate = ref(null)
const submitting = ref(false)
const submitFormRef = ref(null)
const previewZoom = ref(1)

// Submit form
const submitForm = ref({
  name: '',
  description: '',
  category: '',
  tags: [],
  workflow: '',
  isPublic: true
})

const submitRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  workflow: [{ required: true, message: '请输入工作流 JSON', trigger: 'blur' }]
}

// Computed
const templates = computed(() => marketplaceStore.templates)

const filteredTemplates = computed(() => {
  let result = [...templates.value]

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.name?.toLowerCase().includes(query) ||
      t.description?.toLowerCase().includes(query) ||
      t.tags?.some(tag => tag.toLowerCase().includes(query))
    )
  }

  // Category filter
  if (categoryFilter.value) {
    result = result.filter(t => getTemplateCategory(t) === categoryFilter.value)
  }

  // Sort
  switch (sortBy.value) {
    case 'popular':
      result.sort((a, b) => getTemplateInstallCount(b) - getTemplateInstallCount(a))
      break
    case 'newest':
      result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      break
    case 'rating':
      result.sort((a, b) => getTemplateRating(b) - getTemplateRating(a))
      break
    case 'name':
      result.sort((a, b) => a.name.localeCompare(b.name))
      break
  }

  return result
})

const totalTemplates = computed(() => filteredTemplates.value.length)

// Preview
const previewNodes = computed(() => getTemplateNodes(selectedTemplate.value))
const previewEdges = computed(() => {
  const edges = []
  const nodes = previewNodes.value

  // Generate edges based on node order
  for (let i = 0; i < nodes.length - 1; i++) {
    const source = nodes[i]
    const target = nodes[i + 1]
    edges.push({
      sourceX: (source.position?.x || source.x || 0) + 120,
      sourceY: (source.position?.y || source.y || 0) + 40,
      targetX: target.position?.x || target.x || 0,
      targetY: (target.position?.y || target.y || 0) + 40
    })
  }
  return edges
})

// Methods
const getCategoryIcon = (category) => {
  const icons = {
    'ai-assistant': ChatLineSquare,
    'content': Document,
    'data': DataAnalysis,
    'automation': Setting,
    'chatbot': Message,
    'analytics': TrendCharts
  }
  return icons[category] || Document
}

const getCategoryLabel = (category) => {
  const labels = {
    'ai-assistant': 'AI 助手',
    'content': '内容生成',
    'data': '数据处理',
    'automation': '自动化',
    'chatbot': '聊天机器人',
    'analytics': '分析报告'
  }
  return labels[category] || category
}

const getCategoryType = (category) => {
  const types = {
    'ai-assistant': 'primary',
    'content': 'success',
    'data': 'warning',
    'automation': 'info',
    'chatbot': 'danger',
    'analytics': ''
  }
  return types[category] || ''
}

const getNodeIcon = (type) => {
  const icons = {
    'input': Document,
    'output': Document,
    'llm': ChatLineSquare,
    'code': Setting,
    'http': Setting,
    'rag': DataAnalysis
  }
  return icons[type] || Document
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

const showTemplateDetail = async (template) => {
  selectedTemplate.value = template
  showDetailDialog.value = true
}

const installTemplate = async (template) => {
  try {
    await ElMessageBox.confirm(
      `确定要安装模板「${template.name}」吗？`,
      '安装模板',
      { type: 'info', confirmButtonText: '安装', cancelButtonText: '取消' }
    )
    await marketplaceStore.installTemplate(template.id)
    appStore.success(`模板「${template.name}」安装成功！`)
    showDetailDialog.value = false
  } catch (error) {
    if (error !== 'cancel') {
      appStore.error('安装失败，请稍后重试')
    }
  }
}

const previewTemplate = (template) => {
  selectedTemplate.value = template
  showDetailDialog.value = false
  showPreviewDialog.value = true
}

const zoomIn = () => {
  previewZoom.value = Math.min(previewZoom.value + 0.1, 2)
}

const zoomOut = () => {
  previewZoom.value = Math.max(previewZoom.value - 0.1, 0.5)
}

const resetZoom = () => {
  previewZoom.value = 1
}

const submitTemplate = async () => {
  try {
    await submitFormRef.value.validate()
    submitting.value = true

    // Validate workflow JSON
    let workflowData
    try {
      workflowData = JSON.parse(submitForm.value.workflow)
    } catch (e) {
      appStore.error('工作流 JSON 格式不正确')
      return
    }

    await marketplaceStore.createTemplate({
      name: submitForm.value.name,
      description: submitForm.value.description,
      category: submitForm.value.category,
      tags: submitForm.value.tags,
      workflow_data: workflowData,
      is_public: submitForm.value.isPublic
    })

    appStore.success('模板提交成功')
    showSubmitDialog.value = false
    submitForm.value = {
      name: '',
      description: '',
      category: '',
      tags: [],
      workflow: '',
      isPublic: true
    }
  } catch (e) {
    console.error('Validation failed:', e)
  } finally {
    submitting.value = false
  }
}

const fetchTemplates = async () => {
  marketplaceStore.setFilters({
    search: searchQuery.value,
    category: categoryFilter.value,
    sort: sortBy.value
  })
  await marketplaceStore.fetchTemplates()
}

// Watchers
watch([searchQuery, categoryFilter, sortBy], () => {
  fetchTemplates()
})

// Lifecycle
onMounted(async () => {
  await fetchTemplates()
})
</script>

<style scoped>
.marketplace-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.page-description {
  color: var(--text-secondary);
  margin: 0;
}

.search-section {
  margin-bottom: 16px;
}

.search-bar {
  margin-bottom: 16px;
}

.search-input {
  max-width: 500px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
}

.view-toggle {
  margin-left: auto;
}

.stats-bar {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* Grid View */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.template-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.card-preview {
  position: relative;
  height: 160px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-placeholder {
  color: white;
  opacity: 0.8;
}

.preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}

.template-card:hover .preview-overlay {
  opacity: 1;
}

.card-content {
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  margin-right: 8px;
}

.card-description {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* List View */
.templates-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.template-list-item {
  cursor: pointer;
}

.list-item-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.list-item-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.list-item-info {
  flex: 1;
  min-width: 0;
}

.list-item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.list-item-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.list-item-description {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.list-item-meta {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: var(--text-secondary);
}

.list-item-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.list-item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
}

/* Template Detail */
.template-detail {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-preview {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-placeholder.large {
  color: white;
  opacity: 0.8;
}

.detail-info {
  padding: 0 8px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.detail-header h2 {
  margin: 0;
  font-size: 24px;
}

.detail-description {
  font-size: 16px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 24px;
}

.detail-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.detail-section {
  margin-top: 24px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
}

.detail-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.feature-list .el-icon {
  color: var(--success-color);
}

.node-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.node-item span {
  flex: 1;
}

/* Preview */
.workflow-preview-container {
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 16px;
}

.zoom-level {
  color: var(--text-secondary);
  font-size: 14px;
}

.preview-canvas {
  flex: 1;
  position: relative;
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: auto;
  transform-origin: top left;
}

.workflow-nodes {
  position: relative;
  min-width: 100%;
  min-height: 100%;
}

.preview-node {
  position: absolute;
  width: 120px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.preview-node.input {
  border-left: 3px solid var(--primary-color);
}

.preview-node.output {
  border-left: 3px solid var(--success-color);
}

.preview-node.llm {
  border-left: 3px solid #e6a23c;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: var(--bg-secondary);
  font-size: 12px;
  font-weight: 500;
}

.node-content {
  padding: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}

.workflow-edges {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

:deep(.el-dialog__body) {
  padding-top: 16px;
}
</style>
