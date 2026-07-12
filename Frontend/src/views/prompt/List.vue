<template>
  <div class="prompt-list">
    <div class="page-header">
      <div class="header-left">
        <h1>Prompt 模板</h1>
        <p class="subtitle">
          管理和使用 Prompt 模板
        </p>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          @click="showCreateDialog = true"
        >
          <Plus class="btn-icon" />
          创建模板
        </el-button>
      </div>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filters-bar">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模板..."
          :prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
      </div>
      <div class="category-filter">
        <el-select
          v-model="selectedCategory"
          placeholder="全部分类"
          clearable
          @change="handleFilter"
        >
          <el-option
            v-for="cat in categories"
            :key="cat.value"
            :label="cat.label"
            :value="cat.value"
          />
        </el-select>
      </div>
      <div class="filter-tabs">
        <el-radio-group
          v-model="viewFilter"
          @change="handleFilter"
        >
          <el-radio-button label="all">
            全部
          </el-radio-button>
          <el-radio-button label="public">
            公开
          </el-radio-button>
          <el-radio-button label="me">
            我的
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 热门模板 -->
    <div
      v-if="!searchQuery && viewFilter === 'all'"
      class="featured-section"
    >
      <h2 class="section-title">
        推荐模板
      </h2>
      <div class="featured-grid">
        <div
          v-for="template in featuredTemplates"
          :key="template.id"
          class="template-card featured"
          @click="selectTemplate(template)"
        >
          <div class="card-header">
            <div class="card-icon featured">
              <Star class="icon" />
            </div>
            <el-tag
              size="small"
              type="warning"
            >
              推荐
            </el-tag>
          </div>
          <h3 class="card-title">
            {{ template.name }}
          </h3>
          <p class="card-desc">
            {{ template.description || '暂无描述' }}
          </p>
          <div class="card-meta">
            <span class="usage">
              <TrendingUp class="meta-icon" />
              {{ template.useCount ?? template.use_count ?? template.usage_count ?? 0 }} 使用
            </span>
            <span class="category">{{ promptStore.getCategoryLabelForTemplate(template) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 模板列表 -->
    <div class="templates-section">
      <h2 class="section-title">
        {{ searchQuery ? '搜索结果' : (viewFilter === 'me' ? '我的模板' : '所有模板') }}
        <span class="count">({{ filteredTemplates.length }})</span>
      </h2>

      <div
        v-if="isLoading"
        class="loading-state"
      >
        <el-skeleton
          :rows="5"
          animated
        />
      </div>

      <div
        v-else-if="filteredTemplates.length === 0"
        class="empty-state"
      >
        <FileText class="empty-icon" />
        <p>暂无模板</p>
        <el-button
          type="primary"
          @click="showCreateDialog = true"
        >
          创建第一个模板
        </el-button>
      </div>

      <div
        v-else
        class="templates-grid"
      >
        <div
          v-for="template in filteredTemplates"
          :key="template.id"
          class="template-card"
          @click="selectTemplate(template)"
        >
          <div class="card-header">
            <div
              class="card-icon"
              :style="{ background: getCategoryColor(template.category) }"
            >
              {{ template.name?.charAt(0)?.toUpperCase() ?? '?' }}
            </div>
            <el-dropdown
              trigger="click"
              @click.stop
            >
              <el-button
                text
                size="small"
                @click.stop
              >
                <MoreVertical />
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click.stop="handleDuplicate(template)">
                    <Copy class="menu-icon" />
                    复制
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="template.isPublic ?? template.is_public"
                    @click.stop="handleUnshare(template)"
                  >
                    <Lock class="menu-icon" />
                    设为私有
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-else
                    @click.stop="handleShare(template)"
                  >
                    <Globe class="menu-icon" />
                    设为公开
                  </el-dropdown-item>
                  <el-dropdown-item
                    divided
                    class="danger"
                    @click.stop="handleDelete(template)"
                  >
                    <Trash2 class="menu-icon" />
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <h3 class="card-title">
            {{ template.name }}
          </h3>
          <p class="card-desc">
            {{ template.description || '暂无描述' }}
          </p>
          <div class="card-preview">
            <pre>{{ truncate(template.template, 100) }}</pre>
          </div>
          <div class="card-meta">
            <span class="usage">
              <TrendingUp class="meta-icon" />
              {{ template.useCount ?? template.use_count ?? template.usage_count ?? 0 }}
            </span>
            <span
              v-if="template.owner"
              class="owner"
            >
              <User class="meta-icon" />
              {{ template.owner.username }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTemplate ? '编辑模板' : '创建模板'"
      width="700px"
      class="create-dialog"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-position="top"
      >
        <el-form-item
          label="模板名称"
          prop="name"
        >
          <el-input
            v-model="formData.name"
            placeholder="输入模板名称"
          />
        </el-form-item>

        <el-form-item
          label="描述"
          prop="description"
        >
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="模板描述（可选）"
          />
        </el-form-item>

        <el-form-item
          label="分类"
          prop="category"
        >
          <el-select
            v-model="formData.category"
            placeholder="选择分类"
          >
            <el-option
              v-for="cat in categories"
              :key="cat.value"
              :label="cat.label"
              :value="cat.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="Prompt 模板"
          prop="template"
        >
          <el-input
            v-model="formData.template"
            type="textarea"
            :rows="8"
            placeholder="输入 Prompt 模板，使用 ${变量名} 占位..."
            class="template-input"
          />
          <p class="form-hint">
            使用 <code>${变量名}</code> 定义变量，如 <code>${content}</code>
          </p>
        </el-form-item>

        <el-form-item label="标签">
          <el-select
            v-model="formData.tags"
            multiple
            filterable
            allow-create
            placeholder="添加标签"
            style="width: 100%"
          >
            <el-option
              v-for="tag in suggestedTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="formData.is_public">
            设为公开模板
          </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isSaving"
          @click="handleSave"
        >
          {{ editingTemplate ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 模板详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="selectedTemplate?.name"
      width="800px"
      class="detail-dialog"
    >
      <div
        v-if="selectedTemplate"
        class="template-detail"
      >
        <div class="detail-header">
          <div class="detail-info">
            <p class="detail-desc">
              {{ selectedTemplate.description || '暂无描述' }}
            </p>
            <div class="detail-meta">
              <el-tag size="small">
                {{ getCategoryLabel(selectedTemplate.category) }}
              </el-tag>
              <span class="usage-count">
                <TrendingUp class="meta-icon" />
                {{ selectedTemplate.useCount ?? selectedTemplate.use_count ?? selectedTemplate.usage_count ?? 0 }} 次使用
              </span>
              <span
                v-if="selectedTemplate.owner"
                class="owner"
              >
                <User class="meta-icon" />
                {{ selectedTemplate.owner.username }}
              </span>
            </div>
          </div>
          <div class="detail-actions">
            <el-button @click="handleUseInEditor(selectedTemplate)">
              <Play class="btn-icon" />
              在编辑器中使用
            </el-button>
            <el-button
              type="primary"
              @click="handleCopyTemplate(selectedTemplate)"
            >
              <Copy class="btn-icon" />
              复制模板
            </el-button>
          </div>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane
            label="模板内容"
            name="content"
          >
            <div class="template-content">
              <pre>{{ selectedTemplate.template }}</pre>
            </div>
          </el-tab-pane>

          <el-tab-pane
            v-if="selectedTemplate.variables?.length"
            label="变量"
            name="variables"
          >
            <div class="variables-list">
              <div
                v-for="variable in selectedTemplate.variables"
                :key="variable.name"
                class="variable-item"
              >
                <span class="var-name">{{ variable.name }}</span>
                <el-tag size="small">
                  {{ variable.type }}
                </el-tag>
                <span
                  v-if="variable.default"
                  class="var-default"
                >
                  默认: {{ variable.default }}
                </span>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane
            label="预览渲染"
            name="preview"
          >
            <div class="render-form">
              <el-form label-position="top">
                <el-form-item
                  v-for="variable in selectedTemplate.variables"
                  :key="variable.name"
                  :label="variable.label || variable.name"
                >
                  <el-input
                    v-model="previewContext[variable.name]"
                    :type="variable.type === 'textarea' ? 'textarea' : 'text'"
                    :placeholder="variable.description || `输入 ${variable.label || variable.name}`"
                  />
                </el-form-item>
              </el-form>
              <el-button
                type="primary"
                :loading="isRendering"
                @click="handleRender"
              >
                渲染预览
              </el-button>
            </div>
            <div
              v-if="renderedResult"
              class="render-result"
            >
              <h4>渲染结果</h4>
              <pre>{{ renderedResult }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePromptStore } from '@/stores/prompt'
import { useAppStore } from '@/stores/app'
import {
  Plus, Search, Star, TrendingUp, User, FileText,
  MoreVertical, Copy, Trash2, Lock, Globe, Play
} from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const promptStore = usePromptStore()
const appStore = useAppStore()

const searchQuery = ref('')
const selectedCategory = ref('')
const viewFilter = ref('all')
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const editingTemplate = ref(null)
const selectedTemplate = ref(null)
const activeTab = ref('content')
const isRendering = ref(false)
const renderedResult = ref('')
const previewContext = reactive({})

const formRef = ref(null)
const formData = reactive({
  name: '',
  description: '',
  category: 'general',
  template: '',
  tags: [],
  is_public: false
})

const formRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template: [{ required: true, message: '请输入模板内容', trigger: 'blur' }]
}

const suggestedTags = ['AI', '写作', '翻译', '代码', '分析', '创意', '助手']

const categories = computed(() => promptStore.categories)

const isLoading = computed(() => promptStore.isLoading)
const isSaving = computed(() => promptStore.isSaving)

const featuredTemplates = computed(() => promptStore.featuredTemplates)

const filteredTemplates = computed(() => {
  let templates = promptStore.templates

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    templates = templates.filter(t =>
      t.name.toLowerCase().includes(query) ||
      t.description?.toLowerCase().includes(query)
    )
  }

  if (selectedCategory.value) {
    templates = templates.filter(
      t => promptStore.resolveCategoryId(t.category) === selectedCategory.value
    )
  }

  if (viewFilter.value === 'public') {
    templates = templates.filter(t => t.isPublic ?? t.is_public)
  } else if (viewFilter.value === 'me') {
    templates = templates.filter(t => t.owner?.id === appStore.user?.id)
  }

  return templates
})

function getCategoryLabel(category) {
  const cat = categories.value.find(c => c.value === category)
  return cat ? cat.label : category
}

function getCategoryColor(category) {
  const colors = {
    general: '#6366f1',
    writing: '#ec4899',
    coding: '#3b82f6',
    analysis: '#f59e0b',
    creative: '#10b981',
    business: '#3b82f6'
  }
  return colors[category] || '#6b7280'
}

function truncate(text, length) {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}

function handleSearch() {
  // Debounced search
}

function handleFilter() {
  // Filter handled by computed
}

function selectTemplate(template) {
  selectedTemplate.value = template
  previewContext.value = {}

  if (template.variables?.length) {
    template.variables.forEach(v => {
      previewContext.value[v.name] = v.default || ''
    })
  }

  showDetailDialog.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    if (editingTemplate.value) {
      await promptStore.updateTemplate(editingTemplate.value.id, formData)
      appStore.success('模板已更新')
    } else {
      await promptStore.createTemplate(formData)
      appStore.success('模板已创建')
    }
    showCreateDialog.value = false
    resetForm()
  } catch (err) {
    appStore.error('保存失败')
  }
}

function resetForm() {
  editingTemplate.value = null
  Object.assign(formData, {
    name: '',
    description: '',
    category: 'general',
    template: '',
    tags: [],
    is_public: false
  })
}

async function handleDuplicate(template) {
  try {
    await promptStore.duplicateTemplate(template.id)
    appStore.success('模板已复制')
  } catch (err) {
    appStore.error('复制失败')
  }
}

async function handleShare(template) {
  try {
    await promptStore.shareTemplate(template.id)
    template.isPublic = true
    template.is_public = true
    appStore.success('模板已设为公开')
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleUnshare(template) {
  try {
    await promptStore.unshareTemplate(template.id)
    template.isPublic = false
    template.is_public = false
    appStore.success('模板已设为私有')
  } catch (err) {
    appStore.error('操作失败')
  }
}

async function handleDelete(template) {
  try {
    await ElMessageBox.confirm(
      `确定要删除模板 "${template.name}" 吗？`,
      '删除确认',
      { type: 'warning' }
    )
    await promptStore.deleteTemplate(template.id)
    appStore.success('模板已删除')
  } catch (err) {
    if (err !== 'cancel') {
      appStore.error('删除失败')
    }
  }
}

async function handleRender() {
  if (!selectedTemplate.value) return

  try {
    isRendering.value = true
    const response = await promptStore.renderTemplate(
      selectedTemplate.value.id,
      previewContext.value
    )
    renderedResult.value = response.rendered
  } catch (err) {
    appStore.error('渲染失败')
  } finally {
    isRendering.value = false
  }
}

function handleUseInEditor(template) {
  // Navigate to editor with template
  router.push({
    path: '/workflows/new',
    query: { template_id: template.id }
  })
}

function handleCopyTemplate(template) {
  navigator.clipboard.writeText(template.template)
  appStore.success('模板已复制到剪贴板')
}

onMounted(async () => {
  await Promise.all([
    promptStore.fetchCategories().catch(() => null),
    promptStore.fetchTemplates(),
  ])
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.prompt-list {
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
    color: var(--text-primary);
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

.filters-bar {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-6;
  padding: $spacing-4;
  background-color: var(--bg-secondary);
  border-radius: $radius-lg;

  .search-box {
    width: 300px;
  }
}

.featured-section {
  margin-bottom: $spacing-8;
}

.section-title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-4;

  .count {
    font-weight: $font-weight-normal;
    color: var(--text-tertiary);
    font-size: $font-size-sm;
  }
}

.featured-grid,
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: $spacing-4;
}

.template-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: $color-primary;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba($color-primary, 0.15);
  }

  &.featured {
    border-color: rgba($color-warning, 0.3);
    background: linear-gradient(135deg, rgba($color-warning, 0.05) 0%, transparent 100%);
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
  font-size: $font-size-lg;
  font-weight: $font-weight-bold;
  color: white;

  &.featured {
    background: linear-gradient(135deg, $color-warning 0%, $color-primary 100%);
  }
}

.card-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
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

.card-preview {
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;
  padding: $spacing-3;
  margin-bottom: $spacing-3;
  max-height: 80px;
  overflow: hidden;

  pre {
    margin: 0;
    font-size: $font-size-xs;
    font-family: 'Fira Code', monospace;
    color: var(--text-secondary);
    white-space: pre-wrap;
  }
}

.card-meta {
  display: flex;
  gap: $spacing-4;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  .meta-icon {
    width: 14px;
    height: 14px;
    margin-right: $spacing-1;
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

  p {
    color: var(--text-secondary);
    margin-bottom: $spacing-4;
  }
}

.loading-state {
  padding: $spacing-6;
}

.menu-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-2;
}

.danger {
  color: $color-error;
}

.template-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
  }
}

.form-hint {
  margin: $spacing-2 0 0;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  code {
    background-color: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
  }
}

.template-detail {
  .detail-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: $spacing-6;
  }

  .detail-desc {
    color: var(--text-secondary);
    margin: 0 0 $spacing-3;
  }

  .detail-meta {
    display: flex;
    gap: $spacing-4;
    font-size: $font-size-sm;
    color: var(--text-tertiary);

    .meta-icon {
      width: 14px;
      height: 14px;
      margin-right: $spacing-1;
    }
  }

  .detail-actions {
    display: flex;
    gap: $spacing-2;
  }
}

.template-content {
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;
  padding: $spacing-4;

  pre {
    margin: 0;
    font-size: $font-size-sm;
    font-family: 'Fira Code', monospace;
    color: var(--text-primary);
    white-space: pre-wrap;
  }
}

.variables-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;

  .var-name {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
    color: $color-primary;
  }

  .var-default {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
    margin-left: auto;
  }
}

.render-result {
  margin-top: $spacing-4;
  padding: $spacing-4;
  background-color: rgba($color-success, 0.1);
  border-radius: $radius-md;

  h4 {
    margin: 0 0 $spacing-2;
    font-size: $font-size-sm;
    color: $color-success;
  }

  pre {
    margin: 0;
    font-size: $font-size-sm;
    font-family: 'Fira Code', monospace;
    color: var(--text-primary);
    white-space: pre-wrap;
  }
}
</style>



