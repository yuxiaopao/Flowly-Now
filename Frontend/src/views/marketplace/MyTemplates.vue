<template>
  <PageShell width="wide">
    <PageHeader
      title="我的模板"
      subtitle="管理你保存和创建的工作流模板"
    >
      <template #actions>
        <button
          class="create-btn"
          @click="createNewTemplate"
        >
          <Plus :size="18" />
          <span>新建模板</span>
        </button>
      </template>
    </PageHeader>

    <!-- Tabs -->
    <div class="templates-tabs">
      <div class="tabs-container">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >
          <component
            :is="tab.icon"
            :size="16"
          />
          <span>{{ tab.label }}</span>
          <span class="tab-count">{{ getTabCount(tab.id) }}</span>
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="templates-content">
      <!-- Loading State -->
      <div
        v-if="loading"
        class="loading-state"
      >
        <div
          v-for="i in 4"
          :key="i"
          class="skeleton-row"
        />
      </div>

      <!-- Templates List -->
      <div
        v-else-if="filteredItems.length > 0"
        class="templates-list anim-stagger"
      >
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="template-row hover-lift"
          :class="getCategoryAccentClass(getTemplateCategory(item))"
          @click="openTemplate(item)"
        >
          <div
            class="row-icon"
            :style="{ background: getCategoryGradient(getTemplateCategory(item)) }"
          >
            <component
              :is="getCategoryIcon(getTemplateCategory(item))"
              :size="20"
            />
          </div>
          <div class="row-info">
            <h3>{{ item.name }}</h3>
            <p>{{ item.description || 'No description' }}</p>
          </div>
          <div class="row-meta">
            <span class="meta-item">
              <GitBranch :size="14" />
              {{ getTemplateNodeCount(item) }} 个节点
            </span>
            <span class="meta-item">
              <Calendar :size="14" />
              {{ formatDate(item.createdAt ?? item.created_at) }}
            </span>
            <span
              v-if="item.isFeatured ?? item.is_featured"
              class="meta-badge featured"
            >
              <Star
                :size="12"
                fill="currentColor"
              />
              Featured
            </span>
            <span
              v-if="isTemplatePublic(item)"
              class="meta-badge published"
            >
              <Globe :size="12" />
              Published
            </span>
          </div>
          <div class="row-actions">
            <button
              class="action-btn"
              title="Edit"
              @click.stop="editTemplate(item)"
            >
              <Pencil :size="16" />
            </button>
            <button
              class="action-btn"
              title="Duplicate"
              @click.stop="duplicateTemplate(item)"
            >
              <Copy :size="16" />
            </button>
            <button
              class="action-btn"
              title="Share"
              @click.stop="shareTemplate(item)"
            >
              <Share2 :size="16" />
            </button>
            <button
              class="action-btn danger"
              title="Delete"
              @click.stop="deleteTemplate(item)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-else
        class="empty-state anim-fade-in"
      >
        <div class="empty-icon-wrapper">
          <component
            :is="getEmptyIcon()"
            :size="48"
          />
        </div>
        <h3>{{ getEmptyTitle() }}</h3>
        <p>{{ getEmptyDescription() }}</p>
        <button
          v-if="activeTab === 'created'"
          class="create-first-btn"
          @click="createNewTemplate"
        >
          <Plus :size="16" />
          创建你的第一个模板
        </button>
        <router-link
          v-else-if="activeTab === 'saved'"
          to="/marketplace"
          class="browse-btn"
        >
          <Compass :size="16" />
          Browse Marketplace
        </router-link>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="showDeleteModal"
        class="modal-overlay"
        @click.self="closeDeleteModal"
      >
        <div class="delete-modal anim-scale-in">
          <div class="modal-icon">
            <AlertTriangle :size="32" />
          </div>
          <h3>删除模板</h3>
          <p>Are you sure you want to delete "{{ templateToDelete?.name }}"? This action cannot be undone.</p>
          <div class="modal-actions">
            <button
              class="cancel-btn"
              @click="closeDeleteModal"
            >
              Cancel
            </button>
            <button
              class="delete-btn"
              :disabled="isDeleting"
              @click="confirmDelete"
            >
              {{ isDeleting ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </PageShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageShell from '@/components/layout/PageShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import {
  Plus, Sparkles, GitBranch, Calendar, Pencil, Trash2, Copy, Share2,
  Star, Globe, FolderOpen, Bookmark, FileCode, Compass, AlertTriangle
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useMarketplaceStore } from '@/stores/marketplace'
import { useAppStore } from '@/stores/app'
import {
  getTemplateCategory,
  getTemplateNodeCount,
  isTemplatePublic,
} from '@/utils/workflowTransform'

const router = useRouter()
const store = useMarketplaceStore()
const appStore = useAppStore()

const loading = ref(false)
const activeTab = ref('created')
const myTemplates = ref([])
const showDeleteModal = ref(false)
const templateToDelete = ref(null)
const isDeleting = ref(false)

const tabs = computed(() => [
  { id: 'created', label: '已创建', icon: FileCode },
  { id: 'saved', label: '已收藏', icon: Bookmark },
  { id: 'shared', label: '已分享', icon: Share2 },
])

const filteredItems = computed(() => {
  switch (activeTab.value) {
    case 'created':
      return myTemplates.value
    case 'saved':
      return myTemplates.value.filter(t => t.isSaved ?? t.is_saved ?? t.isBookmarked ?? t.is_bookmarked)
    case 'shared':
      return myTemplates.value.filter(t => isTemplatePublic(t))
    default:
      return myTemplates.value
  }
})

function getTabCount(tabId) {
  switch (tabId) {
    case 'created':
      return myTemplates.value.length
    case 'saved':
      return myTemplates.value.filter(t => t.isSaved ?? t.is_saved ?? t.isBookmarked ?? t.is_bookmarked).length
    case 'shared':
      return myTemplates.value.filter(t => isTemplatePublic(t)).length
    default:
      return 0
  }
}

function getCategoryIcon(category) {
  const iconMap = {
    sparkles: Sparkles, bot: 'Bot', 'file-text': 'FileText',
    database: 'Database', brain: 'Brain', zap: 'Zap',
    ai: Sparkles, automation: 'Settings', data: 'Database'
  }
  return iconMap[category] || Sparkles
}

function getCategoryGradient(category) {
  const colors = {
    multimodal: 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)',
    data: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
    mlops: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
    rag: 'linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%)',
    agent: 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)',
    utility: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
    ai: 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)',
    automation: 'linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%)',
  }
  return colors[category] || 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)'
}

// 纯展示用：分类 → 主题彩色边框工具类（motion.scss）
const categoryAccentClassMap = {
  multimodal: 'border-accent-rose',
  data: 'border-accent-amber',
  mlops: 'border-accent-amber',
  rag: 'border-accent-cyan',
  agent: 'border-accent-violet',
  utility: 'border-accent-emerald',
  ai: 'border-accent-violet',
  automation: 'border-accent-cyan',
  default: 'border-accent-blue'
}

function getCategoryAccentClass(category) {
  return categoryAccentClassMap[category?.toLowerCase()] || categoryAccentClassMap.default
}

function formatDate(d) {
  if (!d) return '—'
  const date = new Date(d)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getEmptyIcon() {
  switch (activeTab.value) {
    case 'created': return FileCode
    case 'saved': return Bookmark
    case 'shared': return Share2
    default: return FolderOpen
  }
}

function getEmptyTitle() {
  switch (activeTab.value) {
    case 'created': return '还没有创建的模板'
    case 'saved': return '暂无收藏的模板'
    case 'shared': return '暂无已分享的模板'
    default: return '暂无模板'
  }
}

function getEmptyDescription() {
  switch (activeTab.value) {
    case 'created': return '创建你的第一个工作流模板，分享给社区'
    case 'saved': return '从模板市场收藏的模板将在此显示'
    case 'shared': return '你分享的模板将出现在这里'
    default: return ''
  }
}

function switchTab(tabId) {
  activeTab.value = tabId
}

function openTemplate(item) {
  router.push({ name: 'TemplateDetail', params: { id: item.id } })
}

function editTemplate(item) {
  router.push({ name: 'WorkflowEdit', params: { id: item.workflow_id || item.id } })
}

function buildDuplicateSlug(name) {
  const base = String(name || 'template')
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .slice(0, 40) || 'template'
  return `${base}-copy-${Date.now()}`
}

async function duplicateTemplate(item) {
  try {
    const source = item.workflowData || item.workflow_data
      ? item
      : await store.fetchTemplate(item.id)
    const duplicated = await store.createTemplate({
      name: `${source.name || item.name} (副本)`,
      slug: buildDuplicateSlug(source.name || item.name),
      description: source.description || item.description || '',
      category: source.category || item.category || null,
      tags: source.tags || item.tags || [],
      workflowData: source.workflowData || source.workflow_data || {},
      nodes: source.nodes || [],
      edges: source.edges || [],
      isPublished: false,
    })
    myTemplates.value.unshift(duplicated)
    appStore.success('模板已复制')
  } catch (error) {
    console.error('Failed to duplicate template:', error)
    appStore.error('复制模板失败')
  }
}

async function shareTemplate(item) {
  const url = `${window.location.origin}/marketplace/${item.id}`
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('分享链接已复制到剪贴板')
  } catch {
    ElMessage.info(url)
  }
}

function deleteTemplate(item) {
  templateToDelete.value = item
  showDeleteModal.value = true
}

function closeDeleteModal() {
  showDeleteModal.value = false
  templateToDelete.value = null
}

async function confirmDelete() {
  if (!templateToDelete.value) return
  isDeleting.value = true
  try {
    await store.deleteTemplate(templateToDelete.value.id)
    myTemplates.value = myTemplates.value.filter(t => t.id !== templateToDelete.value.id)
    closeDeleteModal()
  } catch (error) {
    console.error('Failed to delete template:', error)
  } finally {
    isDeleting.value = false
  }
}

function createNewTemplate() {
  router.push({ name: 'WorkflowCreate' })
}

async function loadTemplates() {
  loading.value = true
  try {
    await store.fetchMyTemplates()
    myTemplates.value = store.myTemplates
  } catch (error) {
    console.error('Failed to load templates:', error)
    myTemplates.value = []
  }
  loading.value = false
}

onMounted(() => {
  loadTemplates()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.create-btn {
  display: inline-flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3 $spacing-5;
  background: var(--accent-primary);
  border: none;
  border-radius: $radius-lg;
  color: var(--text-inverse);
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }
}

// Tabs
.templates-tabs {
  padding: 0;
  margin-bottom: $spacing-6;
  border-bottom: 1px solid var(--border-primary);

  .tabs-container {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    gap: 4px;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 20px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-tertiary);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: -1px;

    .tab-count {
      padding: 3px 10px;
      background: var(--surface-muted);
      border-radius: 10px;
      font-size: 12px;
      color: var(--text-tertiary);
    }

    &:hover {
      color: var(--text-primary);
    }

    &.active {
      color: var(--accent-violet);
      border-bottom-color: var(--accent-violet);

      .tab-count {
        background: var(--accent-violet-soft);
        color: var(--accent-violet);
      }
    }
  }
}

// Content
.templates-content {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

// Templates List
.templates-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .template-row {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 20px 24px;
    background: var(--card-bg);
    border: 1px solid var(--border-primary);
    border-radius: 16px;
    cursor: pointer;

    &:hover {
      background: var(--bg-hover);
      transform: translateX(4px);
    }

    // hover 时分类彩边加深（覆盖全局 .border-accent-* 的 soft 色）
    &.border-accent-cyan:hover    { border-color: var(--accent-cyan) !important; }
    &.border-accent-violet:hover  { border-color: var(--accent-violet) !important; }
    &.border-accent-amber:hover   { border-color: var(--accent-amber) !important; }
    &.border-accent-emerald:hover { border-color: var(--accent-emerald) !important; }
    &.border-accent-rose:hover    { border-color: var(--accent-rose) !important; }
    &.border-accent-blue:hover    { border-color: var(--accent-blue) !important; }

    .row-icon {
      width: 52px;
      height: 52px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      flex-shrink: 0;
    }

    .row-info {
      flex: 1;
      min-width: 0;

      h3 {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 4px;
      }

      p {
        font-size: 13px;
        color: var(--text-tertiary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .row-meta {
      display: flex;
      align-items: center;
      gap: 16px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--text-tertiary);
        white-space: nowrap;
      }

      .meta-badge {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;

        &.featured {
          background: var(--accent-amber-soft);
          color: var(--accent-amber);
        }

        &.published {
          background: var(--success-bg);
          color: var(--success);
        }
      }
    }

    .row-actions {
      display: flex;
      gap: 8px;

      .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: var(--surface-muted);
        border: 1px solid var(--border-primary);
        border-radius: 10px;
        color: var(--text-tertiary);
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: var(--bg-hover);
          color: var(--text-primary);
        }

        &.danger:hover {
          background: var(--error-bg);
          border-color: var(--error-bg);
          color: var(--error);
        }
      }
    }
  }
}

// Loading State
.loading-state {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .skeleton-row {
    height: 92px;
    background: linear-gradient(90deg, var(--surface-muted) 0%, var(--surface-strong) 50%, var(--surface-muted) 100%);
    background-size: 200% 100%;
    border-radius: 16px;
    animation: shimmer 1.5s infinite;
  }
}

// Empty State
.empty-state {
  text-align: center;
  padding: 80px 24px;

  .empty-icon-wrapper {
    width: 96px;
    height: 96px;
    margin: 0 auto 24px;
    background: var(--surface-muted);
    border: 1px solid var(--border-primary);
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
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
  }

  .create-first-btn,
  .browse-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: var(--accent-violet-soft);
    border: 1px solid var(--accent-violet-soft);
    border-radius: 10px;
    color: var(--accent-violet);
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: var(--accent-violet);
    }
  }
}

// Delete Modal
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;

  .delete-modal {
    background: var(--bg-elevated);
    border: 1px solid var(--border-primary);
    border-radius: 20px;
    padding: 32px;
    max-width: 420px;
    width: 100%;
    text-align: center;

    .modal-icon {
      width: 64px;
      height: 64px;
      margin: 0 auto 20px;
      background: var(--error-bg);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--error);
    }

    h3 {
      font-size: 20px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 10px;
    }

    p {
      font-size: 14px;
      color: var(--text-secondary);
      margin-bottom: 28px;
      line-height: 1.5;
    }

    .modal-actions {
      display: flex;
      gap: 12px;

      .cancel-btn {
        flex: 1;
        padding: 12px 20px;
        background: var(--surface-muted);
        border: 1px solid var(--border-primary);
        border-radius: 10px;
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: var(--bg-hover);
        }
      }

      .delete-btn {
        flex: 1;
        padding: 12px 20px;
        background: var(--error);
        border: none;
        border-radius: 10px;
        color: var(--text-inverse);
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;

        &:hover:not(:disabled) {
          filter: brightness(0.92);
        }

        &:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
      }
    }
  }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

// Responsive
@media (max-width: 768px) {
  .create-btn {
    width: 100%;
    justify-content: center;
  }

  .templates-tabs {
    padding: 0 16px;
    overflow-x: auto;

    .tabs-container {
      min-width: max-content;
    }
  }

  .templates-content {
    padding: 16px;
  }

  .templates-list .template-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;

    .row-meta {
      flex-wrap: wrap;
      gap: 10px;
    }

    .row-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }
}
</style>
