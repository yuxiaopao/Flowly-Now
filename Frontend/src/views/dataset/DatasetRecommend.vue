<template>
  <PageShell
    width="wide"
    class="dataset-recommend"
  >
    <!-- Page Header -->
    <PageHeader
      title="数据集推荐"
      subtitle="浏览公开标注数据集，下载并上传用于模型训练"
    />

    <!-- Search and Filter Bar -->
    <div class="filter-bar">
      <div class="search-wrapper">
        <Search class="search-icon" />
        <el-input
          v-model="searchQuery"
          placeholder="搜索数据集名称、任务类型、领域..."
          clearable
          @input="handleSearch"
        />
      </div>
      <div class="category-tabs">
        <button
          v-for="category in categories"
          :key="category.id"
          class="category-tab"
          :class="{ active: activeCategory === category.id }"
          @click="handleCategoryChange(category.id)"
        >
          {{ category.name }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="isLoading"
      class="dataset-grid"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="dataset-card skeleton"
      >
        <div class="skeleton-icon" />
        <div class="skeleton-title" />
        <div class="skeleton-desc" />
        <div class="skeleton-tags" />
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredDatasets.length === 0"
      class="empty-state"
    >
      <Database class="empty-icon" />
      <h3>未找到匹配的数据集</h3>
      <p>尝试调整搜索关键词或切换分类标签</p>
      <el-button @click="resetFilters">
        重置筛选
      </el-button>
    </div>

    <!-- Dataset Cards Grid -->
    <div
      v-else
      class="dataset-grid"
    >
      <div
        v-for="dataset in filteredDatasets"
        :key="dataset.id"
        class="dataset-card"
        :class="{ expanded: expandedCards.has(dataset.id) }"
      >
        <!-- Card Header -->
        <div class="card-header">
          <div class="dataset-icon">
            <component :is="getCategoryIcon(dataset.category)" />
          </div>
          <div class="header-info">
            <h3 class="dataset-name">
              {{ dataset.name }}
            </h3>
            <span
              class="source-badge"
              :class="getSourceClass(dataset.source)"
            >
              {{ dataset.source }}
            </span>
          </div>
        </div>

        <!-- Description -->
        <p
          class="dataset-description"
          :class="{ 'line-clamp': !expandedCards.has(dataset.id) }"
        >
          {{ dataset.description }}
        </p>

        <!-- Expanded Details -->
        <div
          v-if="expandedCards.has(dataset.id)"
          class="expanded-content"
        >
          <div class="detail-item">
            <span class="detail-label">数据格式</span>
            <span class="detail-value">{{ dataset.format }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">应用领域</span>
            <span class="detail-value">{{ dataset.domain }}</span>
          </div>
          <div
            v-if="dataset.license"
            class="detail-item"
          >
            <span class="detail-label">许可证</span>
            <span class="detail-value">{{ dataset.license }}</span>
          </div>
        </div>

        <!-- Tags -->
        <div class="tags-row">
          <span class="tag category-tag">{{ getCategoryName(dataset.category) }}</span>
          <span class="tag domain-tag">{{ dataset.domain }}</span>
          <span class="tag format-tag">{{ dataset.format }}</span>
        </div>

        <!-- Stats -->
        <div class="stats-row">
          <span class="stat-item">
            <Database class="stat-icon" />
            {{ dataset.size }}
          </span>
          <span class="stat-item">
            <FileText class="stat-icon" />
            {{ dataset.samples }}
          </span>
        </div>

        <!-- Actions -->
        <div class="card-actions">
          <el-button
            type="primary"
            size="small"
            @click="openExternalLink(dataset.url)"
          >
            <ExternalLink class="btn-icon" />
            访问网站
          </el-button>
          <el-button
            size="small"
            @click="copyLink(dataset)"
          >
            <Copy class="btn-icon" />
            复制链接
          </el-button>
          <el-button
            size="small"
            text
            @click="toggleExpand(dataset.id)"
          >
            {{ expandedCards.has(dataset.id) ? '收起' : '查看详情' }}
            <ChevronDown
              class="btn-icon"
              :class="{ rotated: expandedCards.has(dataset.id) }"
            />
          </el-button>
        </div>
      </div>
    </div>
  </PageShell>
</template>

<script setup>
import PageHeader from '@/components/layout/PageHeader.vue'
import PageShell from '@/components/layout/PageShell.vue'
import { ref, computed, onMounted, markRaw } from 'vue'
import { datasetRecommendApi } from '@/api/datasetRecommend'
import { ElMessage } from 'element-plus'
import {
  Search,
  Database,
  ExternalLink,
  Copy,
  ChevronDown,
  Image,
  Target,
  MessageSquare,
  Mic,
  Table,
  Layers,
  FileText
} from 'lucide-vue-next'

const isLoading = ref(true)
const datasets = ref([])
const searchQuery = ref('')
const activeCategory = ref('all')
const expandedCards = ref(new Set())

const categories = [
  { id: 'all', name: '全部' },
  { id: 'image_classification', name: '图像分类' },
  { id: 'object_detection', name: '目标检测' },
  { id: 'nlp', name: '自然语言处理' },
  { id: 'speech', name: '语音识别' },
  { id: 'text_classification', name: '文本分类' },
  { id: 'tabular', name: '表格数据' },
  { id: 'recommendation', name: '推荐系统' }
]

const categoryIcons = {
  image_classification: markRaw(Image),
  object_detection: markRaw(Target),
  nlp: markRaw(MessageSquare),
  speech: markRaw(Mic),
  text_classification: markRaw(FileText),
  tabular: markRaw(Table),
  recommendation: markRaw(Layers),
  all: markRaw(Database)
}

const filteredDatasets = computed(() => {
  let result = datasets.value

  if (activeCategory.value !== 'all') {
    result = result.filter(d => d.category === activeCategory.value)
  }

  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(d =>
      d.name.toLowerCase().includes(query) ||
      d.description.toLowerCase().includes(query) ||
      d.domain.toLowerCase().includes(query) ||
      d.category.toLowerCase().includes(query)
    )
  }

  return result
})

function getCategoryIcon(categoryId) {
  return categoryIcons[categoryId] || Database
}

function getCategoryName(categoryId) {
  const category = categories.find(c => c.id === categoryId)
  return category?.name || categoryId
}

function getSourceClass(source) {
  const sourceMap = {
    'Kaggle': 'source-kaggle',
    'HuggingFace': 'source-huggingface',
    'Official': 'source-official',
    'ImageNet': 'source-official',
    'COCO': 'source-official'
  }
  return sourceMap[source] || 'source-default'
}

function handleSearch() {
  // Search is reactive via computed property
}

function handleCategoryChange(categoryId) {
  activeCategory.value = categoryId
}

function resetFilters() {
  searchQuery.value = ''
  activeCategory.value = 'all'
}

function toggleExpand(datasetId) {
  if (expandedCards.value.has(datasetId)) {
    expandedCards.value.delete(datasetId)
  } else {
    expandedCards.value.add(datasetId)
  }
  expandedCards.value = new Set(expandedCards.value)
}

function openExternalLink(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function copyLink(url) {
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function fetchDatasets() {
  try {
    isLoading.value = true
    const response = await datasetRecommendApi.getDatasets()
    datasets.value = Array.isArray(response)
      ? response
      : (response?.results || response?.datasets || [])
  } catch (error) {
    console.error('Failed to fetch datasets:', error)
    ElMessage.error('加载数据集失败')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchDatasets()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.filter-bar {
  margin-bottom: $spacing-6;
}

.search-wrapper {
  position: relative;
  margin-bottom: $spacing-4;

  .search-icon {
    position: absolute;
    left: $spacing-4;
    top: 50%;
    transform: translateY(-50%);
    width: 18px;
    height: 18px;
    color: var(--text-tertiary);
    z-index: 1;
    pointer-events: none;
  }

  :deep(.el-input__wrapper) {
    padding-left: $spacing-10;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-xl;
    box-shadow: none;
    transition: all $transition-fast;

    &:hover, &:focus-within {
      border-color: $color-primary;
      box-shadow: 0 0 0 3px rgba($color-primary, 0.1);
    }

    .el-input__inner {
      color: var(--text-primary);

      &::placeholder {
        color: var(--text-tertiary);
      }
    }
  }
}

.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  padding: $spacing-2;
  background: var(--bg-secondary);
  border-radius: $radius-xl;
  border: 1px solid var(--border-primary);
}

.category-tab {
  padding: $spacing-2 $spacing-4;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-fast;
  position: relative;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: $color-warning;
    background: rgba($color-warning, 0.1);

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 24px;
      height: 2px;
      background: $color-warning;
      border-radius: 1px;
    }
  }
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--content-card-min-width)), 1fr));
  gap: $spacing-4;
}

.dataset-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--content-card-radius);
  padding: var(--content-card-padding);
  transition: all $transition-normal;

  &:hover {
    border-color: rgba($color-primary, 0.3);
    transform: translateY(-4px);
    box-shadow:
      0 12px 24px rgba(0, 0, 0, 0.15),
      0 0 0 1px rgba($color-primary, 0.1),
      0 0 30px rgba($color-primary, 0.05);
  }

  &.expanded {
    grid-column: span 1;
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  margin-bottom: $spacing-4;
}

.dataset-icon {
  width: 44px;
  height: 44px;
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba($color-primary, 0.15), rgba($color-primary, 0.05));
  flex-shrink: 0;

  svg {
    width: 22px;
    height: 22px;
    color: $color-primary;
  }
}

.header-info {
  flex: 1;
  min-width: 0;
}

.dataset-name {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  margin: 0 0 $spacing-2;
  color: var(--text-primary);
  line-height: 1.4;
}

.source-badge {
  display: inline-block;
  padding: 2px $spacing-2;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;
  border-radius: $radius-sm;
  text-transform: uppercase;
  letter-spacing: 0.03em;

  &.source-kaggle {
    background: rgba(20, 132, 255, 0.15);
    color: #1484ff;
  }

  &.source-huggingface {
    background: rgba(252, 186, 3, 0.15);
    color: #fcba03;
  }

  &.source-official {
    background: rgba($color-info, 0.15);
    color: $color-info;
  }

  &.source-default {
    background: var(--bg-hover);
    color: var(--text-secondary);
  }
}

.dataset-description {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 $spacing-4;
  white-space: pre-wrap;

  &.line-clamp {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.expanded-content {
  padding: $spacing-4;
  background: var(--bg-tertiary);
  border-radius: $radius-lg;
  margin-bottom: $spacing-4;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: $spacing-2 0;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
  }
}

.detail-label {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.detail-value {
  font-size: $font-size-sm;
  color: var(--text-primary);
  font-weight: $font-weight-medium;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
  margin-bottom: $spacing-4;
}

.tag {
  padding: $spacing-1 $spacing-2;
  font-size: $font-size-xs;
  border-radius: $radius-full;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-primary);

  &.category-tag {
    background: rgba($color-primary, 0.1);
    color: $color-primary;
    border-color: rgba($color-primary, 0.2);
  }

  &.domain-tag {
    background: rgba($color-secondary, 0.1);
    color: $color-secondary;
    border-color: rgba($color-secondary, 0.2);
  }

  &.format-tag {
    background: rgba($color-info, 0.1);
    color: $color-info;
    border-color: rgba($color-info, 0.2);
  }
}

.stats-row {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-4;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-lg;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-sm;
  color: var(--text-secondary);

  .stat-icon {
    width: 14px;
    height: 14px;
    color: var(--text-tertiary);
  }
}

.card-actions {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  flex-wrap: wrap;

  :deep(.el-button) {
    border-radius: $radius-lg;
    font-weight: $font-weight-medium;
  }

  .btn-icon {
    width: 14px;
    height: 14px;
    margin-right: $spacing-1;

    &.rotated {
      transform: rotate(180deg);
    }
  }
}

.empty-state {
  text-align: center;
  padding: $spacing-16 $spacing-8;
  background: var(--bg-secondary);
  border: 1px dashed var(--border-primary);
  border-radius: $radius-xl;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--text-tertiary);
    margin-bottom: $spacing-4;
  }

  h3 {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    margin: 0 0 $spacing-2;
    color: var(--text-primary);
  }

  p {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    margin: 0 0 $spacing-4;
  }
}

.skeleton {
  pointer-events: none;

  .skeleton-icon {
    width: 44px;
    height: 44px;
    border-radius: $radius-lg;
    background: var(--bg-tertiary);
    animation: pulse 1.5s ease-in-out infinite;
  }

  .skeleton-title {
    width: 60%;
    height: 20px;
    border-radius: $radius-md;
    background: var(--bg-tertiary);
    margin-bottom: $spacing-3;
    animation: pulse 1.5s ease-in-out infinite;
  }

  .skeleton-desc {
    width: 100%;
    height: 40px;
    border-radius: $radius-md;
    background: var(--bg-tertiary);
    margin-bottom: $spacing-3;
    animation: pulse 1.5s ease-in-out infinite;
  }

  .skeleton-tags {
    width: 80%;
    height: 24px;
    border-radius: $radius-full;
    background: var(--bg-tertiary);
    animation: pulse 1.5s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 768px) {
  .dataset-grid {
    grid-template-columns: 1fr;
  }

  .category-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .category-tab {
    flex-shrink: 0;
  }

  .card-actions {
    flex-direction: column;

    :deep(.el-button) {
      width: 100%;
    }
  }
}
</style>
