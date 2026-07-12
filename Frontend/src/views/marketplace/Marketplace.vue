<template>
  <PageShell
    width="wide"
    class="marketplace-page"
  >
    <PageHeader
      title="模板市场"
      subtitle="浏览社区和 Flowly 团队精心制作的模板，快速落地你的工作流"
    >
      <template #actions>
        <div class="search-bar">
          <Search
            :size="18"
            class="search-icon"
          />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="按名称、分类或功能搜索模板..."
            @input="debouncedSearch"
          >
          <button
            v-if="searchQuery"
            class="clear-btn"
            @click="clearSearch"
          >
            <X :size="16" />
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Categories -->
    <div class="categories-section">
      <div class="categories-header">
        <h2 class="section-label">
          按分类浏览
        </h2>
      </div>
      <div class="categories-scroll">
        <button
          v-for="cat in categoriesWithCount"
          :key="cat.slug || cat.id"
          class="category-chip"
          :class="{ active: activeCategory === getCategoryKey(cat) }"
          @click="selectCategory(getCategoryKey(cat))"
        >
          <component
            :is="getCategoryIcon(cat.icon)"
            :size="14"
          />
          <span>{{ cat.name }}</span>
          <span class="chip-count">{{ cat.count || 0 }}</span>
        </button>
      </div>
    </div>

    <!-- Featured Templates -->
    <div
      v-if="featuredTemplates.length > 0 && !searchQuery && activeCategory === 'all'"
      class="featured-section"
    >
      <div class="section-header">
        <div class="section-title-group">
          <Zap
            :size="20"
            class="section-icon featured-icon"
          />
          <h2 class="section-title">
            精选模板
          </h2>
        </div>
        <router-link
          to="/marketplace?tab=featured"
          class="view-all-link"
        >
          查看全部 <ArrowRight :size="14" />
        </router-link>
      </div>
      <div class="featured-grid">
        <div
          v-for="template in featuredTemplates"
          :key="template.id"
          class="featured-card"
          @click="openTemplate(template)"
        >
          <div class="card-preview">
            <div
              class="preview-gradient"
              :style="{ background: getTemplatePresentation(template).gradient }"
            >
              <component
                :is="getTemplatePresentation(template).icon"
                :size="40"
                class="preview-icon"
                :style="{ color: getTemplatePresentation(template).color }"
              />
            </div>
            <div class="preview-badge">
              精选
            </div>
          </div>
          <div class="card-info">
            <div
              class="card-category-tag"
              :style="{
                backgroundColor: getTemplatePresentation(template).color + '22',
                color: getTemplatePresentation(template).color,
              }"
            >
              {{ getTemplatePresentation(template).name }}
            </div>
            <h3 class="card-title">
              {{ template.name }}
            </h3>
            <p class="card-desc">
              {{ template.description }}
            </p>
            <div class="card-meta">
              <span class="meta-item">
                <GitBranch :size="12" /> 
                {{ getTemplateNodeCount(template) }} 个节点
              </span>
              <span class="meta-item">
                <Download :size="12" /> 
                {{ formatNumber(getTemplateUseCount(template)) }}
              </span>
              <span class="meta-item">
                <Star
                  :size="12"
                  :fill="'currentColor'"
                /> 
                {{ getTemplateRating(template) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- All Templates Grid -->
    <div class="templates-section">
      <div class="section-header">
        <div class="section-title-group">
          <Layers
            :size="20"
            class="section-icon"
          />
          <h2 class="section-title">
            {{ activeCategory === 'all' ? '全部模板' : activeCategoryName }}
          </h2>
          <span class="template-count">{{ filteredTemplates.length }} 个模板</span>
        </div>
        <div class="sort-controls">
          <select
            v-model="sortBy"
            class="sort-select"
            @change="onSortChange"
          >
            <option value="popular">
              最受欢迎
            </option>
            <option value="newest">
              最新发布
            </option>
            <option value="rating">
              评分最高
            </option>
            <option value="name">
              名称 A-Z
            </option>
          </select>
        </div>
      </div>

      <div
        v-if="loading"
        class="loading-grid"
      >
        <div
          v-for="i in 8"
          :key="i"
          class="skeleton-card"
        >
          <div class="skeleton-preview" />
          <div class="skeleton-content">
            <div class="skeleton-line short" />
            <div class="skeleton-line" />
            <div class="skeleton-line medium" />
          </div>
        </div>
      </div>

      <div
        v-else-if="filteredTemplates.length > 0"
        class="templates-grid"
      >
        <TemplateMarketCard
          v-for="template in filteredTemplates"
          :key="template.id"
          :template="template"
          :categories="categoriesWithCount"
          @open="openTemplate"
          @use="useTemplate"
        />
      </div>

      <div
        v-else
        class="empty-state"
      >
        <div class="empty-icon-wrapper">
          <Search :size="48" />
        </div>
        <h3>未找到模板</h3>
        <p>请尝试调整搜索条件或筛选条件</p>
        <button
          class="reset-btn"
          @click="resetFilters"
        >
          重置筛选
        </button>
      </div>

      <!-- Load More -->
      <div
        v-if="hasMore && !loading"
        class="load-more"
      >
        <button
          class="load-more-btn"
          :disabled="loadingMore"
          @click="loadMoreTemplates"
        >
          <Loader
            v-if="loadingMore"
            :size="16"
            class="spin"
          />
          <span v-else>加载更多</span>
        </button>
      </div>
    </div>
  </PageShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, X, Zap, ArrowRight, GitBranch,
  Download, Star, Layers, Loader,
} from 'lucide-vue-next'
import { useMarketplaceStore } from '@/stores/marketplace'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import TemplateMarketCard from '@/components/marketplace/TemplateMarketCard.vue'
import {
  getTemplateCategoryPresentation,
  getTemplateCategorySlug,
  resolveCategoryIcon,
} from '@/composables/useTemplateCategoryPresentation'
import {
  getTemplateCategory,
  getTemplateNodeCount,
  getTemplateUseCount,
  getTemplateRating,
} from '@/utils/workflowTransform'

const router = useRouter()
const store = useMarketplaceStore()

const searchQuery = ref('')
const activeCategory = ref('all')
const sortBy = ref('popular')
const loading = ref(false)
const loadingMore = ref(false)

const categoriesWithCount = computed(() => {
  return (store.categories || []).map(cat => {
    const key = cat.slug ?? cat.id
    return {
      ...cat,
      count: store.templates.filter(t => {
        const slug = getTemplateCategorySlug(t, store.categories || [])
        const categoryId = typeof t.category === 'object' ? t.category?.id : t.category
        return slug === key || categoryId === cat.id || categoryId === key
      }).length,
    }
  })
})

function getCategoryKey(cat) {
  return cat?.slug ?? cat?.id
}
const featuredTemplates = computed(() => store.featuredTemplates)

const filteredTemplates = computed(() => {
  let list = store.templates
  if (activeCategory.value !== 'all') {
    list = list.filter(t => getTemplateCategorySlug(t, store.categories || []) === activeCategory.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(t =>
      t.name?.toLowerCase().includes(q) ||
      t.description?.toLowerCase().includes(q) ||
      getTemplateCategory(t)?.toLowerCase().includes(q)
    )
  } else if (activeCategory.value === 'all' && featuredTemplates.value.length > 0) {
    const featuredIds = new Set(featuredTemplates.value.map(t => t.id))
    list = list.filter(t => !featuredIds.has(t.id))
  }
  return list
})

const hasMore = computed(() => store.hasMore)

const activeCategoryName = computed(() => {
  const cat = categoriesWithCount.value.find(c => getCategoryKey(c) === activeCategory.value)
  return cat?.name || '全部模板'
})

function getCategoryIcon(icon) {
  return resolveCategoryIcon(icon)
}

function getTemplatePresentation(template) {
  return getTemplateCategoryPresentation(template, categoriesWithCount.value)
}

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

let searchTimeout = null
function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    onSearch()
  }, 300)
}

function clearSearch() {
  searchQuery.value = ''
  onSearch()
}

async function onSearch() {
  loading.value = true
  store.setFilters({ search: searchQuery.value })
  await store.fetchTemplates({ search: searchQuery.value })
  loading.value = false
}

function selectCategory(catId) {
  activeCategory.value = catId
  loadTemplates()
}

async function loadTemplates() {
  loading.value = true
  try {
    const categoryParam = activeCategory.value === 'all' ? '' : activeCategory.value
    store.setFilters({ category: categoryParam, sort: sortBy.value })
    await store.fetchTemplates({ category: categoryParam, sort: sortBy.value })
  } catch (err) {
    console.error('Failed to load templates:', err)
  } finally {
    loading.value = false
  }
}

async function onSortChange() {
  store.setFilters({ sort: sortBy.value })
  await store.fetchTemplates({ sort: sortBy.value })
}

async function loadMoreTemplates() {
  loadingMore.value = true
  try {
    await store.loadMoreTemplates()
  } catch (err) {
    console.error('Failed to load more templates:', err)
  } finally {
    loadingMore.value = false
  }
}

function openTemplate(template) {
  router.push({ name: 'TemplateDetail', params: { id: template.id } })
}

async function useTemplate(template) {
  try {
    const workflow = await store.applyTemplate(template.id)
    if (workflow?.id) {
      router.push({ name: 'Editor', params: { id: workflow.id } })
    }
  } catch (error) {
    console.error('Failed to apply template:', error)
  }
}

function resetFilters() {
  searchQuery.value = ''
  activeCategory.value = 'all'
  loadTemplates()
}

onMounted(async () => {
  loading.value = true
  await Promise.all([
    store.fetchCategories(),
    store.fetchTemplates(),
  ])
  // fetchFeatured is non-critical — don't block loading on it
  store.fetchFeatured().catch(err => {
    console.warn('Failed to load featured templates:', err)
  })
  loading.value = false
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.marketplace-page {
  min-height: 100%;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface-muted);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: 10px 16px;
  min-width: 280px;
  max-width: 360px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;

  &:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px var(--accent-muted);
  }

  .search-icon {
    color: var(--text-tertiary);
    flex-shrink: 0;
  }

  input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-size: $font-size-sm;
    min-width: 0;

    &::placeholder {
      color: var(--text-tertiary);
    }
  }

  .clear-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: var(--surface-muted);
    border: none;
    border-radius: 50%;
    color: var(--text-secondary);
    cursor: pointer;
    transition: background-color 0.2s ease, color 0.2s ease;

    &:hover {
      background: var(--surface-strong);
      color: var(--text-primary);
    }
  }
}

// Categories Section
.categories-section {
  padding: 0 0 $spacing-6;

  .categories-header {
    max-width: 1280px;
    margin: 0 auto 16px;

    .section-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  }

  .categories-scroll {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding-bottom: 8px;
    max-width: 1280px;
    margin: 0 auto;

    &::-webkit-scrollbar {
      height: 4px;
    }

    &::-webkit-scrollbar-track {
      background: var(--surface-muted);
      border-radius: 2px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--border-secondary);
      border-radius: 2px;

      &:hover {
        background: var(--border-hover);
      }
    }

    .category-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      background: var(--surface-muted);
      border: 1px solid var(--border-primary);
      border-radius: 12px;
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;

      .chip-count {
        padding: 2px 8px;
        background: var(--surface-strong);
        border-radius: 10px;
        font-size: 11px;
        color: var(--text-tertiary);
      }

      &:hover {
        background: var(--bg-hover);
        border-color: var(--border-hover);
      }

      &.active {
        background: var(--accent-violet-soft);
        border-color: var(--accent-violet);
        color: var(--accent-violet);

        .chip-count {
          background: var(--accent-violet-soft);
          color: var(--accent-violet);
        }
      }
    }
  }
}

// Section Styling
.featured-section,
.templates-section {
  padding: 0 24px 48px;
  max-width: 1280px;
  margin: 0 auto;

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    .section-title-group {
      display: flex;
      align-items: center;
      gap: 12px;

      .section-icon {
        color: var(--accent-violet);

        &.featured-icon {
          color: var(--accent-amber);
        }
      }

      .section-title {
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
      }

      .template-count {
        font-size: 13px;
        color: var(--text-tertiary);
        padding: 4px 10px;
        background: var(--surface-muted);
        border-radius: 8px;
      }
    }

    .view-all-link {
      display: flex;
      align-items: center;
      gap: 4px;
      color: var(--accent-violet);
      font-size: 13px;
      text-decoration: none;
      transition: color 0.2s;

      &:hover {
        color: var(--text-primary);
      }
    }

    .sort-controls {
      .sort-select {
        padding: 8px 32px 8px 12px;
        background: var(--surface-muted);
        border: 1px solid var(--border-primary);
        border-radius: 8px;
        color: var(--text-secondary);
        font-size: 13px;
        cursor: pointer;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888888' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 10px center;

        &:focus {
          outline: none;
          border-color: var(--accent-violet);
        }
      }
    }
  }
}

// Featured Grid
.featured-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;

  .featured-card {
    position: relative;
    background: var(--card-bg);
    border: 1px solid var(--border-primary);
    border-radius: 20px;
    cursor: pointer;
    overflow: hidden;
    transition:
      transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
      box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1);

    &:hover {
      transform: translateY(-3px);
      box-shadow: var(--shadow-lg);
    }

    .card-preview {
      position: relative;
      height: 160px;
      border-radius: 20px 20px 0 0;
      overflow: hidden;

      .preview-gradient {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;

        .preview-icon {
          color: var(--text-primary);
          opacity: 0.75;
        }
      }

      .preview-badge {
        position: absolute;
        top: 12px;
        right: 12px;
        padding: 4px 10px;
        background: var(--accent-amber-soft);
        border: 1px solid var(--accent-amber-soft);
        border-radius: 6px;
        color: var(--accent-amber);
        font-size: 11px;
        font-weight: 600;
      }
    }

    .card-info {
      padding: 20px;

      .card-category-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: capitalize;
        margin-bottom: 10px;
      }

      .card-title {
        font-size: 17px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 6px;
      }

      .card-desc {
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 14px;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-clamp: 2;
        box-orient: vertical;
        overflow: hidden;
      }

      .card-meta {
        display: flex;
        gap: 16px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 12px;
          color: var(--text-tertiary);
        }
      }
    }
  }
}

// Templates Grid
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

// Loading State
.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;

  .skeleton-card {
    background: var(--card-bg);
    border: 1px solid var(--border-primary);
    border-radius: 18px;
    overflow: hidden;

    .skeleton-preview {
      height: 132px;
      background: linear-gradient(90deg, var(--surface-muted) 0%, var(--surface-strong) 50%, var(--surface-muted) 100%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
    }

    .skeleton-content {
      padding: 16px;

      .skeleton-line {
        height: 12px;
        background: linear-gradient(90deg, var(--surface-muted) 0%, var(--surface-strong) 50%, var(--surface-muted) 100%);
        background-size: 200% 100%;
        border-radius: 6px;
        margin-bottom: 10px;
        animation: shimmer 1.5s infinite;

        &.short { width: 40%; }
        &.medium { width: 70%; }
      }
    }
  }
}

// Empty State
.empty-state {
  text-align: center;
  padding: 80px 24px;
  
  .empty-icon-wrapper {
    width: 80px;
    height: 80px;
    margin: 0 auto 20px;
    background: var(--surface-muted);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-disabled);
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: var(--text-tertiary);
    margin-bottom: 24px;
  }

  .reset-btn {
    padding: 10px 24px;
    background: var(--accent-violet-soft);
    border: 1px solid var(--accent-violet-soft);
    border-radius: 10px;
    color: var(--accent-violet);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: var(--accent-violet);
    }
  }
}

// Load More
.load-more {
  text-align: center;
  padding-top: 32px;

  .load-more-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 32px;
    background: var(--surface-muted);
    border: 1px solid var(--border-primary);
    border-radius: 10px;
    color: var(--text-secondary);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: var(--bg-hover);
      border-color: var(--border-hover);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .spin {
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// Responsive
@media (max-width: 768px) {
  .search-bar {
    min-width: 100%;
    max-width: none;
  }

  .featured-grid,
  .templates-grid {
    grid-template-columns: 1fr;
  }
}
</style>
