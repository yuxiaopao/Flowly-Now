<template>
  <div class="template-detail-page">
    <!-- Loading State -->
    <div
      v-if="loading"
      class="loading-state"
    >
      <div class="skeleton-hero" />
      <div class="skeleton-content">
        <div class="skeleton-line" />
        <div class="skeleton-line short" />
        <div class="skeleton-block" />
      </div>
    </div>

    <!-- Template Content -->
    <template v-else-if="template">
      <!-- Hero Section -->
      <div class="detail-hero">
        <div class="hero-bg">
          <div class="gradient-orb orb-1" />
          <div class="gradient-orb orb-2" />
        </div>
        <div class="hero-content anim-fade-up">
          <button
            class="back-btn"
            @click="goBack"
          >
            <ArrowLeft :size="16" />
            <span>返回市场</span>
          </button>
          
          <div
            class="template-badge"
            :style="{ backgroundColor: getCategoryColor(normalizedTemplate?.displayCategory) + '25', borderColor: getCategoryColor(normalizedTemplate?.displayCategory) + '50' }"
          >
            <component
              :is="getCategoryIcon(normalizedTemplate?.displayCategory)"
              :size="14"
            />
            {{ normalizedTemplate?.displayCategory }}
          </div>
          
          <h1 class="template-title">
            {{ template.name }}
          </h1>
          <p class="template-desc">
            {{ template.description }}
          </p>
          
          <div class="template-meta">
            <div class="meta-item">
              <GitBranch :size="16" />
              <span>{{ normalizedTemplate?.displayNodeCount }} 个节点</span>
            </div>
            <div class="meta-item">
              <Download :size="16" />
              <span>{{ formatNumber(normalizedTemplate?.displayUseCount) }} 次使用</span>
            </div>
            <div class="meta-item">
              <Star
                :size="16"
                :fill="'currentColor'"
              />
              <span>{{ normalizedTemplate?.displayRating }}</span>
            </div>
            <div class="meta-item">
              <User :size="16" />
              <span>{{ normalizedTemplate?.displayAuthor }}</span>
            </div>
          </div>

          <div class="hero-actions">
            <button
              class="use-template-btn"
              :disabled="isApplying"
              @click="useTemplate"
            >
              <Play :size="18" />
              {{ isApplying ? '创建中...' : '使用此模板' }}
            </button>
            <button
              class="secondary-btn"
              @click="previewWorkflow"
            >
              <Eye :size="16" />
              预览
            </button>
            <button
              class="icon-btn"
              @click="toggleFavorite"
            >
              <Heart
                :size="18"
                :fill="isFavorite ? 'currentColor' : 'none'"
              />
            </button>
          </div>
        </div>
      </div>

      <!-- Detail Content -->
      <div class="detail-content">
        <!-- Main Content -->
        <div class="content-main">
          <!-- Workflow Preview -->
          <div class="workflow-preview-card anim-fade-up">
            <div class="card-header">
              <h3>
                <Layers :size="18" />
                工作流结构
              </h3>
              <span class="node-count">{{ previewNodes.length }} 个节点</span>
            </div>
            <div class="preview-canvas">
              <div class="preview-nodes">
                <div 
                  v-for="(node, i) in previewNodes" 
                  :key="i" 
                  class="preview-node"
                  :class="{ 'start-node': i === 0, 'end-node': i === previewNodes.length - 1 }"
                >
                  <div
                    v-if="i < previewNodes.length - 1"
                    class="node-connector"
                  />
                  <div class="node-number">
                    {{ i + 1 }}
                  </div>
                  <div class="node-info">
                    <component
                      :is="getNodeIcon(node.type)"
                      :size="16"
                      class="node-icon"
                    />
                    <span class="node-name">{{ node.name || node.type || '节点' }}</span>
                  </div>
                  <span class="node-type">{{ node.type || 'process' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Tags -->
          <div
            v-if="template.tags && template.tags.length > 0"
            class="tags-section anim-fade-up anim-delay-1"
          >
            <h3>
              <Tag :size="18" />
              Tags
            </h3>
            <div class="tags-list">
              <span
                v-for="tag in template.tags"
                :key="tag"
                class="tag"
              >{{ tag }}</span>
            </div>
          </div>

          <!-- Features -->
          <div
            v-if="template.features && template.features.length > 0"
            class="features-section anim-fade-up anim-delay-2"
          >
            <h3>
              <Zap :size="18" />
              Features
            </h3>
            <ul class="features-list">
              <li
                v-for="(feature, i) in template.features"
                :key="i"
              >
                <CheckCircle :size="16" />
                {{ feature }}
              </li>
            </ul>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="content-sidebar anim-stagger">
          <!-- Template Info -->
          <div class="info-card hover-lift border-top-accent">
            <h4>模板信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">作者</span>
                <span class="info-value">{{ normalizedTemplate?.displayAuthor }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">创建时间</span>
                <span class="info-value">{{ formatDate(template.createdAt || template.created_at) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">更新时间</span>
                <span class="info-value">{{ formatDate(template.updatedAt || template.updated_at) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">难度</span>
                <span
                  class="info-value difficulty-badge"
                  :class="getDifficultyClass(template.difficulty)"
                >
                  {{ template.difficulty || 'Beginner' }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">Est. Time</span>
                <span class="info-value">{{ template.estimated_time || '5 min' }}</span>
              </div>
            </div>
          </div>

          <!-- Stats Card -->
          <div class="stats-card hover-lift border-top-accent">
            <h4>热度统计</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-icon">
                  <Download :size="18" />
                </div>
                <div class="stat-info">
                  <span class="stat-value">{{ formatNumber(normalizedTemplate?.displayUseCount) }}</span>
                  <span class="stat-label">使用次数</span>
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-icon">
                  <Star :size="18" />
                </div>
                <div class="stat-info">
                  <span class="stat-value">{{ normalizedTemplate?.displayRating }}</span>
                  <span class="stat-label">评分</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Share Card -->
          <div class="share-card hover-lift border-top-accent">
            <h4>分享模板</h4>
            <div class="share-actions">
              <button
                class="share-btn"
                @click="copyLink"
              >
                <Link :size="16" />
                Copy Link
              </button>
              <button
                class="share-btn"
                @click="shareToTwitter"
              >
                <Twitter :size="16" />
                Twitter
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Not Found -->
    <div
      v-else
      class="not-found anim-fade-in"
    >
      <div class="not-found-icon">
        <FileX :size="64" />
      </div>
      <h2>模板未找到</h2>
      <p>The template you're looking for doesn't exist or has been removed.</p>
      <button
        class="back-to-gallery"
        @click="goToGallery"
      >
        <ArrowRight :size="16" />
        Go to Gallery
      </button>
    </div>

    <!-- Preview Modal -->
    <Teleport to="body">
      <div
        v-if="showPreview"
        class="preview-modal"
        @click.self="closePreview"
      >
        <div class="preview-modal-content anim-scale-in">
          <div class="preview-modal-header">
            <h3>工作流预览</h3>
            <button
              class="close-btn"
              @click="closePreview"
            >
              <X :size="20" />
            </button>
          </div>
          <div class="preview-modal-body">
            <div class="workflow-diagram">
              <div
                v-for="(node, i) in previewNodes"
                :key="i"
                class="diagram-node"
              >
                <div class="node-box">
                  <component
                    :is="getNodeIcon(node.type)"
                    :size="20"
                  />
                  <span>{{ node.name || node.type }}</span>
                </div>
                <div
                  v-if="i < previewNodes.length - 1"
                  class="node-arrow"
                >
                  <ArrowRight :size="16" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  ArrowLeft, ArrowRight, GitBranch, Download, Star, User, Play, 
  Eye, Heart, Layers, Tag, Zap, CheckCircle, FileX, X, Link, Twitter
} from 'lucide-vue-next'
import { useMarketplaceStore } from '@/stores/marketplace'
import { getTemplateNodes } from '@/utils/workflowTransform'

const route = useRoute()
const router = useRouter()
const store = useMarketplaceStore()

const template = ref(null)
const loading = ref(false)
const isApplying = ref(false)
const isFavorite = ref(false)
const showPreview = ref(false)

const normalizedTemplate = computed(() => template.value)

const categoryIconMap = {
  sparkles: 'Sparkles', bot: 'Bot', 'file-text': 'FileText', 
  database: 'Database', brain: 'Brain', zap: 'Zap',
  settings: 'Settings', message: 'MessageSquare', code: 'Code',
  globe: 'Globe', clock: 'Clock'
}

function getCategoryIcon(icon) {
  return categoryIconMap[icon] || 'Sparkles'
}

function getCategoryColor(category) {
  const colors = {
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
  return colors[category?.toLowerCase()] || colors.default
}

function getNodeIcon() {
  return 'Layers'
}

function getDifficultyClass(difficulty) {
  const map = {
    beginner: 'easy',
    intermediate: 'medium',
    advanced: 'hard'
  }
  return map[difficulty?.toLowerCase()] || 'easy'
}

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

function formatDate(d) {
  if (!d) return 'Recently'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const previewNodes = computed(() => {
  if (!template.value) return []
  const nodes = getTemplateNodes(template.value)
  if (nodes.length > 0) {
    return nodes
  }
  return [
    { type: 'input', name: 'Input' },
    { type: 'process', name: 'Processing' },
    { type: 'output', name: 'Output' }
  ]
})

function goBack() {
  router.back()
}

function goToGallery() {
  router.push({ name: 'Marketplace' })
}

async function useTemplate() {
  if (!template.value) return
  isApplying.value = true
  try {
    const workflow = await store.applyTemplate(template.value.id)
    if (workflow?.id) {
      router.push({ name: 'Editor', params: { id: workflow.id } })
    }
  } catch (error) {
    console.error('Failed to apply template:', error)
  } finally {
    isApplying.value = false
  }
}

function previewWorkflow() {
  showPreview.value = true
}

function closePreview() {
  showPreview.value = false
}

function toggleFavorite() {
  isFavorite.value = !isFavorite.value
}

function copyLink() {
  const url = window.location.href
  navigator.clipboard.writeText(url)
}

function shareToTwitter() {
  const text = `Check out this workflow template: ${template.value?.name}`
  const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`
  window.open(url, '_blank')
}

onMounted(async () => {
  loading.value = true
  try {
    const result = await store.fetchTemplate(route.params.id)
    template.value = result || store.currentTemplate
  } catch (error) {
    console.error('Failed to fetch template:', error)
    template.value = null
  }
  loading.value = false
})
</script>

<style lang="scss" scoped>
.template-detail-page {
  min-height: 100vh;
  background: var(--bg-primary);
  position: relative;
}

// Hero Section
.detail-hero {
  position: relative;
  padding: 40px 24px 60px;
  overflow: hidden;

  .hero-bg {
    position: absolute;
    inset: 0;
    pointer-events: none;

    .gradient-orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(120px);
      opacity: 0.3;

      &.orb-1 {
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, var(--accent-violet-soft) 0%, transparent 70%);
        top: -150px;
        right: 10%;
      }

      &.orb-2 {
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, var(--accent-cyan-soft) 0%, transparent 70%);
        bottom: -100px;
        left: 5%;
      }
    }
  }

  .hero-content {
    position: relative;
    max-width: 900px;
    margin: 0 auto;

    .back-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: var(--surface-muted);
      border: 1px solid var(--border-primary);
      border-radius: 10px;
      color: var(--text-secondary);
      font-size: 14px;
      cursor: pointer;
      margin-bottom: 24px;
      transition: all 0.2s;

      &:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
      }
    }

    .template-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border: 1px solid;
      border-radius: 20px;
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 600;
      text-transform: capitalize;
      margin-bottom: 16px;
    }

    .template-title {
      font-size: 40px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 12px;
      line-height: 1.2;
    }

    .template-desc {
      font-size: 18px;
      color: var(--text-secondary);
      margin-bottom: 24px;
      max-width: 700px;
      line-height: 1.6;
    }

    .template-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      margin-bottom: 28px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: var(--text-secondary);

        svg {
          color: var(--text-tertiary);
        }
      }
    }

    .hero-actions {
      display: flex;
      align-items: center;
      gap: 12px;

      .use-template-btn {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 28px;
        background: linear-gradient(135deg, var(--accent-violet) 0%, var(--accent-blue) 100%);
        border: none;
        border-radius: 12px;
        color: var(--text-inverse);
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s;
        box-shadow: 0 4px 20px var(--accent-violet-soft);

        &:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 30px var(--accent-violet-soft);
        }

        &:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
      }

      .secondary-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 14px 24px;
        background: var(--surface-muted);
        border: 1px solid var(--border-secondary);
        border-radius: 12px;
        color: var(--text-primary);
        font-size: 15px;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: var(--bg-hover);
          border-color: var(--border-hover);
        }
      }

      .icon-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        background: var(--surface-muted);
        border: 1px solid var(--border-primary);
        border-radius: 12px;
        color: var(--text-tertiary);
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          color: var(--error);
          background: var(--error-bg);
          border-color: var(--error-bg);
        }
      }
    }
  }
}

// Detail Content
.detail-content {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  padding: 0 24px 60px;
  max-width: 1200px;
  margin: 0 auto;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }

  .content-main {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .content-sidebar {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
}

// Workflow Preview Card
.workflow-preview-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  overflow: hidden;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
    border-bottom: 1px solid var(--border-primary);

    h3 {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;

      svg {
        color: var(--accent-violet);
      }
    }

    .node-count {
      font-size: 12px;
      color: var(--text-tertiary);
      padding: 4px 10px;
      background: var(--surface-muted);
      border-radius: 6px;
    }
  }

  .preview-canvas {
    padding: 24px;
    background: var(--bg-secondary);

    .preview-nodes {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .preview-node {
        position: relative;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        background: var(--surface-muted);
        border: 1px solid var(--border-primary);
        border-radius: 12px;
        transition: all 0.2s;

        &:hover {
          background: var(--bg-hover);
        }

        // 起止节点用语义色全边框标识（避免 border-left 粗彩条）
        &.start-node {
          border-color: var(--success);
        }

        &.end-node {
          border-color: var(--error);
        }

        .node-connector {
          position: absolute;
          left: 30px;
          bottom: -12px;
          width: 2px;
          height: 12px;
          background: var(--border-secondary);
        }

        .node-number {
          width: 28px;
          height: 28px;
          background: var(--accent-violet-soft);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 600;
          color: var(--accent-violet);
          flex-shrink: 0;
        }

        .node-info {
          display: flex;
          align-items: center;
          gap: 10px;
          flex: 1;

          .node-icon {
            color: var(--text-tertiary);
          }

          .node-name {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
          }
        }

        .node-type {
          font-size: 11px;
          color: var(--text-tertiary);
          text-transform: capitalize;
          padding: 3px 8px;
          background: var(--surface-muted);
          border-radius: 4px;
        }
      }
    }
  }
}

// Tags Section
.tags-section {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 20px;

  h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 16px;

    svg {
      color: var(--accent-violet);
    }
  }

  .tags-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    .tag {
      padding: 6px 14px;
      background: var(--accent-violet-soft);
      border: 1px solid var(--accent-violet-soft);
      border-radius: 8px;
      font-size: 13px;
      color: var(--accent-violet);
    }
  }
}

// Features Section
.features-section {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 20px;

  h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 16px;

    svg {
      color: var(--success);
    }
  }

  .features-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;

    li {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      color: var(--text-secondary);

      svg {
        color: var(--success);
        flex-shrink: 0;
      }
    }
  }
}

// Info Card
.info-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 20px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
    margin: 0 0 16px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .info-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .info-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid var(--border-primary);

      &:last-child {
        border-bottom: none;
      }

      .info-label {
        font-size: 13px;
        color: var(--text-tertiary);
      }

      .info-value {
        font-size: 13px;
        color: var(--text-primary);
        font-weight: 500;

        &.difficulty-badge {
          padding: 3px 10px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 600;

          &.easy {
            background: var(--success-bg);
            color: var(--success);
          }
          &.medium {
            background: var(--warning-bg);
            color: var(--warning);
          }
          &.hard {
            background: var(--error-bg);
            color: var(--error);
          }
        }
      }
    }
  }
}

// Stats Card
.stats-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 20px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
    margin: 0 0 16px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;

    .stat-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px;
      background: var(--surface-muted);
      border-radius: 10px;

      .stat-icon {
        width: 40px;
        height: 40px;
        background: var(--accent-violet-soft);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--accent-violet);
      }

      .stat-info {
        display: flex;
        flex-direction: column;

        .stat-value {
          font-size: 18px;
          font-weight: 700;
          color: var(--text-primary);
        }

        .stat-label {
          font-size: 11px;
          color: var(--text-tertiary);
        }
      }
    }
  }
}

// Share Card
.share-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 20px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
    margin: 0 0 16px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .share-actions {
    display: flex;
    gap: 10px;

    .share-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 14px;
      background: var(--surface-muted);
      border: 1px solid var(--border-primary);
      border-radius: 10px;
      color: var(--text-secondary);
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: var(--bg-hover);
      }
    }
  }
}

// Not Found
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  padding: 48px 24px;

  .not-found-icon {
    width: 120px;
    height: 120px;
    background: var(--surface-muted);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-disabled);
    margin-bottom: 24px;
  }

  h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  p {
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 24px;
  }

  .back-to-gallery {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
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

// Loading State
.loading-state {
  padding: 40px 24px;

  .skeleton-hero {
    max-width: 900px;
    margin: 0 auto;
    height: 200px;
    background: var(--surface-muted);
    border-radius: 20px;
    margin-bottom: 32px;
    animation: pulse 1.5s infinite;
  }

  .skeleton-content {
    max-width: 800px;
    margin: 0 auto;

    .skeleton-line {
      height: 16px;
      background: var(--surface-muted);
      border-radius: 8px;
      margin-bottom: 12px;
      animation: pulse 1.5s infinite;

      &.short { width: 40%; }
    }

    .skeleton-block {
      height: 150px;
      background: var(--surface-muted);
      border-radius: 16px;
      margin-top: 24px;
      animation: pulse 1.5s infinite;
    }
  }
}

// Preview Modal
.preview-modal {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;

  .preview-modal-content {
    background: var(--bg-elevated);
    border: 1px solid var(--border-primary);
    border-radius: 20px;
    width: 100%;
    max-width: 800px;
    max-height: 80vh;
    overflow: hidden;

    .preview-modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-primary);

      h3 {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
      }

      .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: var(--surface-muted);
        border: none;
        border-radius: 8px;
        color: var(--text-tertiary);
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: var(--bg-hover);
          color: var(--text-primary);
        }
      }
    }

    .preview-modal-body {
      padding: 32px 24px;
      overflow-y: auto;
      max-height: calc(80vh - 80px);

      .workflow-diagram {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
        gap: 16px;

        .diagram-node {
          display: flex;
          align-items: center;
          gap: 16px;

          .node-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            padding: 20px 24px;
            background: var(--surface-muted);
            border: 1px solid var(--border-primary);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 13px;

            svg {
              color: var(--accent-violet);
            }
          }

          .node-arrow {
            color: var(--text-tertiary);
          }
        }
      }
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
