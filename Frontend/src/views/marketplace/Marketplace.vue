<template>
  <div class="marketplace-page">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-bg">
        <div class="gradient-orb orb-1" />
        <div class="gradient-orb orb-2" />
      </div>
      <div class="hero-content">
        <div class="hero-badge">
          <Sparkles :size="14" />
          <span>Template Gallery</span>
        </div>
        <h1 class="hero-title">
          Jump-start your workflows
        </h1>
        <p class="hero-subtitle">
          Discover pre-built templates crafted by the community and the Flowly team
        </p>
        <div class="search-container">
          <div class="search-bar">
            <Search
              :size="18"
              class="search-icon"
            />
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search templates by name, category, or feature..." 
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
        </div>
      </div>
    </div>

    <!-- Categories -->
    <div class="categories-section">
      <div class="categories-header">
        <h2 class="section-label">
          Browse by Category
        </h2>
      </div>
      <div class="categories-scroll">
        <button
          v-for="cat in categories"
          :key="cat.id"
          class="category-chip"
          :class="{ active: activeCategory === cat.id }"
          @click="selectCategory(cat.id)"
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
            Featured Templates
          </h2>
        </div>
        <router-link
          to="/marketplace?tab=featured"
          class="view-all-link"
        >
          View all <ArrowRight :size="14" />
        </router-link>
      </div>
      <div class="featured-grid">
        <div
          v-for="template in featuredTemplates"
          :key="template.id"
          class="featured-card"
          @click="openTemplate(template)"
        >
          <div class="featured-card-glow" />
          <div class="card-preview">
            <div
              class="preview-gradient"
              :style="{ background: getCategoryGradient(getTemplateCategory(template)) }"
            >
              <component
                :is="getCategoryIcon(getTemplateCategory(template))"
                :size="40"
                class="preview-icon"
              />
            </div>
            <div class="preview-badge">
              Featured
            </div>
          </div>
          <div class="card-info">
            <div
              class="card-category-tag"
              :style="{ backgroundColor: getCategoryColor(getTemplateCategory(template)) + '20', color: getCategoryColor(getTemplateCategory(template)) }"
            >
              {{ getTemplateCategory(template) }}
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
                {{ getTemplateNodeCount(template) }} nodes
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
            {{ activeCategory === 'all' ? 'All Templates' : activeCategoryName }}
          </h2>
          <span class="template-count">{{ filteredTemplates.length }} templates</span>
        </div>
        <div class="sort-controls">
          <select
            v-model="sortBy"
            class="sort-select"
            @change="onSortChange"
          >
            <option value="popular">
              Most Popular
            </option>
            <option value="newest">
              Newest
            </option>
            <option value="rating">
              Highest Rated
            </option>
            <option value="name">
              A to Z
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
        <div
          v-for="template in filteredTemplates"
          :key="template.id"
          class="template-card"
          @click="openTemplate(template)"
        >
          <div class="card-header">
            <div
              class="card-icon"
              :style="{ background: getCategoryGradient(getTemplateCategory(template)) }"
            >
              <component
                :is="getCategoryIcon(getTemplateCategory(template))"
                :size="16"
              />
            </div>
            <span class="card-category">{{ getTemplateCategory(template) }}</span>
          </div>
          <h3 class="card-title">
            {{ template.name }}
          </h3>
          <p class="card-desc">
            {{ template.description }}
          </p>
          <div class="card-footer">
            <div class="card-stats">
              <span><GitBranch :size="12" /> {{ getTemplateNodeCount(template) }}</span>
              <span><Download :size="12" /> {{ formatNumber(getTemplateUseCount(template)) }}</span>
            </div>
            <button
              class="use-btn"
              @click.stop="useTemplate(template)"
            >
              Use <ArrowRight :size="12" />
            </button>
          </div>
        </div>
      </div>

      <div
        v-else
        class="empty-state"
      >
        <div class="empty-icon-wrapper">
          <Search :size="48" />
        </div>
        <h3>No templates found</h3>
        <p>Try adjusting your search or filters</p>
        <button
          class="reset-btn"
          @click="resetFilters"
        >
          Reset Filters
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
          <span v-else>Load More Templates</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, X, Sparkles, Zap, ArrowRight, GitBranch, 
  Download, Star, Layers, Loader, Bot, FileText, Database, Brain, 
  Settings, MessageSquare, Code, Globe, Clock
} from 'lucide-vue-next'
import { useMarketplaceStore } from '@/stores/marketplace'
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

const categories = computed(() => store.categories)
const featuredTemplates = computed(() => store.featuredTemplates)

const filteredTemplates = computed(() => {
  let list = store.templates
  if (activeCategory.value !== 'all') {
    list = list.filter(t => getTemplateCategory(t) === activeCategory.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(t =>
      t.name?.toLowerCase().includes(q) ||
      t.description?.toLowerCase().includes(q) ||
      getTemplateCategory(t)?.toLowerCase().includes(q)
    )
  }
  return list
})

const hasMore = computed(() => store.hasMore)

const activeCategoryName = computed(() => {
  const cat = categories.value.find(c => c.id === activeCategory.value)
  return cat?.name || 'Templates'
})

const categoryIconMap = {
  sparkles: Sparkles, bot: Bot, 'file-text': FileText, 
  database: Database, brain: Brain, zap: Zap,
  settings: Settings, message: MessageSquare, code: Code,
  globe: Globe, clock: Clock
}

function getCategoryIcon(icon) {
  return categoryIconMap[icon] || Sparkles
}

const categoryColors = {
  multimodal: '#ec4899',
  data: '#f59e0b',
  mlops: '#f59e0b',
  rag: '#06b6d4',
  agent: '#8b5cf6',
  utility: '#10b981',
  ai: '#8b5cf6',
  automation: '#06b6d4',
  default: '#6366f1'
}

function getCategoryColor(category) {
  return categoryColors[category?.toLowerCase()] || categoryColors.default
}

function getCategoryGradient(category) {
  const color = getCategoryColor(category)
  return `linear-gradient(135deg, ${color}40 0%, ${color}20 100%)`
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
  const categoryParam = activeCategory.value === 'all' ? '' : activeCategory.value
  store.setFilters({ category: categoryParam, sort: sortBy.value })
  await store.fetchTemplates({ category: categoryParam, sort: sortBy.value })
  loading.value = false
}

async function onSortChange() {
  store.setFilters({ sort: sortBy.value })
  await store.fetchTemplates({ sort: sortBy.value })
}

async function loadMoreTemplates() {
  loadingMore.value = true
  await store.loadMoreTemplates()
  loadingMore.value = false
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
    store.fetchFeatured()
  ])
  loading.value = false
})
</script>

<style lang="scss" scoped>
.marketplace-page {
  min-height: 100vh;
  background: #09090b;
  position: relative;
  overflow-x: hidden;
}

// Hero Section
.hero-section {
  position: relative;
  padding: 64px 24px 48px;
  text-align: center;
  overflow: hidden;

  .hero-bg {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
  }

  .gradient-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(100px);
    opacity: 0.4;

    &.orb-1 {
      width: 600px;
      height: 600px;
      background: radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%);
      top: -200px;
      left: 50%;
      transform: translateX(-50%);
    }

    &.orb-2 {
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(6, 182, 212, 0.2) 0%, transparent 70%);
      bottom: -100px;
      right: 10%;
    }
  }

  .hero-content {
    position: relative;
    max-width: 640px;
    margin: 0 auto;

    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      background: rgba(139, 92, 246, 0.15);
      border: 1px solid rgba(139, 92, 246, 0.3);
      border-radius: 20px;
      color: #a78bfa;
      font-size: 12px;
      font-weight: 500;
      margin-bottom: 20px;
    }

    .hero-title {
      font-size: 48px;
      font-weight: 700;
      background: linear-gradient(135deg, #fff 0%, #a78bfa 50%, #06b6d4 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 12px;
      line-height: 1.1;
      letter-spacing: -0.02em;
    }

    .hero-subtitle {
      font-size: 18px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 32px;
      line-height: 1.5;
    }

    .search-container {
      .search-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 16px 20px;
        max-width: 560px;
        margin: 0 auto;
        transition: all 0.2s;

        &:focus-within {
          border-color: rgba(139, 92, 246, 0.5);
          box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1);
        }

        .search-icon {
          color: rgba(255, 255, 255, 0.4);
          flex-shrink: 0;
        }

        input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: rgba(255, 255, 255, 0.9);
          font-size: 15px;

          &::placeholder {
            color: rgba(255, 255, 255, 0.35);
          }
        }

        .clear-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          background: rgba(255, 255, 255, 0.1);
          border: none;
          border-radius: 50%;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          transition: all 0.2s;

          &:hover {
            background: rgba(255, 255, 255, 0.15);
            color: rgba(255, 255, 255, 0.9);
          }
        }
      }
    }
  }
}

// Categories Section
.categories-section {
  padding: 0 24px 32px;

  .categories-header {
    max-width: 1280px;
    margin: 0 auto 16px;

    .section-label {
      font-size: 14px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.5);
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
      background: rgba(255, 255, 255, 0.05);
      border-radius: 2px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 2px;

      &:hover {
        background: rgba(255, 255, 255, 0.25);
      }
    }

    .category-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      color: rgba(255, 255, 255, 0.7);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;

      .chip-count {
        padding: 2px 8px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
      }

      &:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.15);
      }

      &.active {
        background: rgba(139, 92, 246, 0.15);
        border-color: rgba(139, 92, 246, 0.4);
        color: #a78bfa;

        .chip-count {
          background: rgba(139, 92, 246, 0.2);
          color: #a78bfa;
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
        color: #a78bfa;

        &.featured-icon {
          color: #f59e0b;
        }
      }

      .section-title {
        font-size: 20px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9);
        margin: 0;
      }

      .template-count {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.4);
        padding: 4px 10px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
      }
    }

    .view-all-link {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #a78bfa;
      font-size: 13px;
      text-decoration: none;
      transition: color 0.2s;

      &:hover {
        color: #c4b5fd;
      }
    }

    .sort-controls {
      .sort-select {
        padding: 8px 32px 8px 12px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: rgba(255, 255, 255, 0.8);
        font-size: 13px;
        cursor: pointer;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.5)' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 10px center;

        &:focus {
          outline: none;
          border-color: rgba(139, 92, 246, 0.5);
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
    background: linear-gradient(145deg, rgba(139, 92, 246, 0.08) 0%, rgba(6, 182, 212, 0.04) 100%);
    border: 1px solid rgba(139, 92, 246, 0.15);
    border-radius: 20px;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      border-color: rgba(139, 92, 246, 0.35);
      transform: translateY(-6px);
      box-shadow: 0 20px 50px rgba(139, 92, 246, 0.15);

      .card-preview .preview-gradient {
        transform: scale(1.05);
      }
    }

    .featured-card-glow {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 100px;
      background: linear-gradient(180deg, rgba(139, 92, 246, 0.1) 0%, transparent 100%);
      pointer-events: none;
    }

    .card-preview {
      position: relative;
      height: 160px;
      overflow: hidden;

      .preview-gradient {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.3s;

        .preview-icon {
          color: rgba(255, 255, 255, 0.7);
        }
      }

      .preview-badge {
        position: absolute;
        top: 12px;
        right: 12px;
        padding: 4px 10px;
        background: rgba(245, 158, 11, 0.2);
        border: 1px solid rgba(245, 158, 11, 0.4);
        border-radius: 6px;
        color: #fbbf24;
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
        color: rgba(255, 255, 255, 0.95);
        margin-bottom: 6px;
      }

      .card-desc {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.5);
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
          color: rgba(255, 255, 255, 0.45);
        }
      }
    }
  }
}

// Templates Grid
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;

  .template-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.25s;

    &:hover {
      background: rgba(255, 255, 255, 0.04);
      border-color: rgba(255, 255, 255, 0.12);
      transform: translateY(-3px);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
    }

    .card-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;

      .card-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
      }

      .card-category {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.45);
        text-transform: capitalize;
      }
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 8px;
    }

    .card-desc {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.45);
      margin-bottom: 16px;
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      line-clamp: 2;
      box-orient: vertical;
      overflow: hidden;
    }

    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .card-stats {
        display: flex;
        gap: 14px;

        span {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.4);
        }
      }

      .use-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        background: rgba(139, 92, 246, 0.15);
        border: 1px solid rgba(139, 92, 246, 0.25);
        border-radius: 8px;
        color: #a78bfa;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: rgba(139, 92, 246, 0.25);
          border-color: rgba(139, 92, 246, 0.4);
        }
      }
    }
  }
}

// Loading State
.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;

  .skeleton-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    overflow: hidden;

    .skeleton-preview {
      height: 120px;
      background: linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 100%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
    }

    .skeleton-content {
      padding: 16px;

      .skeleton-line {
        height: 12px;
        background: linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 100%);
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
    background: rgba(255, 255, 255, 0.03);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.2);
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 24px;
  }

  .reset-btn {
    padding: 10px 24px;
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.25);
    border-radius: 10px;
    color: #a78bfa;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(139, 92, 246, 0.25);
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
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.15);
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
  .hero-section {
    padding: 48px 16px 32px;

    .hero-content {
      .hero-title {
        font-size: 32px;
      }

      .hero-subtitle {
        font-size: 15px;
      }
    }
  }

  .featured-grid,
  .templates-grid {
    grid-template-columns: 1fr;
  }
}
</style>
