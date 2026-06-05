<template>
  <div class="my-templates-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-bg">
        <div class="gradient-orb orb-1" />
        <div class="gradient-orb orb-2" />
      </div>
      <div class="header-content">
        <div class="header-text">
          <h1>My Templates</h1>
          <p>Manage your saved and created workflow templates</p>
        </div>
        <button
          class="create-btn"
          @click="createNewTemplate"
        >
          <Plus :size="18" />
          <span>New Template</span>
        </button>
      </div>
    </div>

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
        class="templates-list"
      >
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="template-row"
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
              {{ getTemplateNodeCount(item) }} nodes
            </span>
            <span class="meta-item">
              <Calendar :size="14" />
              {{ formatDate(item.created_at) }}
            </span>
            <span
              v-if="item.is_featured"
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
        class="empty-state"
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
          Create Your First Template
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
        <div class="delete-modal">
          <div class="modal-icon">
            <AlertTriangle :size="32" />
          </div>
          <h3>Delete Template</h3>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Plus, Sparkles, GitBranch, Calendar, Pencil, Trash2, Copy, Share2,
  Star, Globe, FolderOpen, Bookmark, FileCode, Compass, AlertTriangle
} from 'lucide-vue-next'
import { useMarketplaceStore } from '@/stores/marketplace'
import {
  getTemplateCategory,
  getTemplateNodeCount,
  isTemplatePublic,
} from '@/utils/workflowTransform'

const router = useRouter()
const store = useMarketplaceStore()

const loading = ref(false)
const activeTab = ref('created')
const myTemplates = ref([])
const showDeleteModal = ref(false)
const templateToDelete = ref(null)
const isDeleting = ref(false)

const tabs = [
  { id: 'created', label: 'Created', icon: FileCode },
  { id: 'saved', label: 'Saved', icon: Bookmark },
  { id: 'shared', label: 'Shared', icon: Share2 },
]

const filteredItems = computed(() => {
  switch (activeTab.value) {
    case 'created':
      return myTemplates.value.filter(t => t.is_own || t.author_is_current_user)
    case 'saved':
      return myTemplates.value.filter(t => t.is_saved || t.is_bookmarked)
    case 'shared':
      return myTemplates.value.filter(t => t.is_shared)
    default:
      return myTemplates.value
  }
})

function getTabCount(tabId) {
  switch (tabId) {
    case 'created':
      return myTemplates.value.filter(t => t.is_own || t.author_is_current_user).length
    case 'saved':
      return myTemplates.value.filter(t => t.is_saved || t.is_bookmarked).length
    case 'shared':
      return myTemplates.value.filter(t => t.is_shared).length
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
    case 'created': return 'No templates created yet'
    case 'saved': return 'No saved templates'
    case 'shared': return 'No shared templates'
    default: return 'No templates'
  }
}

function getEmptyDescription() {
  switch (activeTab.value) {
    case 'created': return 'Create your first workflow template and share it with the community'
    case 'saved': return 'Save templates from the marketplace to access them here'
    case 'shared': return 'Templates you share will appear here'
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

function duplicateTemplate(item) {
  // TODO: Implement duplicate functionality
  console.log('Duplicate template:', item.id)
}

function shareTemplate(item) {
  // TODO: Implement share functionality
  const url = `${window.location.origin}/marketplace/${item.id}`
  navigator.clipboard.writeText(url)
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
    // TODO: Call API to delete template
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
    const result = await store.fetchMyTemplates()
    myTemplates.value = result?.results || result || []
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
.my-templates-page {
  min-height: 100vh;
  background: #09090b;
  position: relative;
}

// Page Header
.page-header {
  position: relative;
  padding: 48px 24px 32px;
  overflow: hidden;

  .header-bg {
    position: absolute;
    inset: 0;
    pointer-events: none;

    .gradient-orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(100px);
      opacity: 0.25;

      &.orb-1 {
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%);
        top: -150px;
        right: 10%;
      }

      &.orb-2 {
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(6, 182, 212, 0.2) 0%, transparent 70%);
        bottom: -100px;
        left: 5%;
      }
    }
  }

  .header-content {
    position: relative;
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;

    .header-text {
      h1 {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #fff 0%, #a78bfa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 6px;
      }

      p {
        font-size: 15px;
        color: rgba(255, 255, 255, 0.5);
      }
    }

    .create-btn {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 24px;
      background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
      border: none;
      border-radius: 12px;
      color: white;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.25s;
      box-shadow: 0 4px 20px rgba(139, 92, 246, 0.35);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(139, 92, 246, 0.45);
      }
    }
  }
}

// Tabs
.templates-tabs {
  padding: 0 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

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
    color: rgba(255, 255, 255, 0.5);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: -1px;

    .tab-count {
      padding: 3px 10px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 10px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }

    &:hover {
      color: rgba(255, 255, 255, 0.8);
    }

    &.active {
      color: #a78bfa;
      border-bottom-color: #a78bfa;

      .tab-count {
        background: rgba(139, 92, 246, 0.15);
        color: #a78bfa;
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
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.25s;

    &:hover {
      background: rgba(255, 255, 255, 0.04);
      border-color: rgba(255, 255, 255, 0.1);
      transform: translateX(4px);
    }

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
        color: rgba(255, 255, 255, 0.9);
        margin-bottom: 4px;
      }

      p {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.45);
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
        color: rgba(255, 255, 255, 0.45);
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
          background: rgba(245, 158, 11, 0.15);
          color: #fbbf24;
        }

        &.published {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
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
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        color: rgba(255, 255, 255, 0.6);
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.9);
        }

        &.danger:hover {
          background: rgba(239, 68, 68, 0.1);
          border-color: rgba(239, 68, 68, 0.2);
          color: #ef4444;
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
    background: linear-gradient(90deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.04) 50%, rgba(255,255,255,0.02) 100%);
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
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.2);
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.4);
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
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 10px;
    color: #a78bfa;
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(139, 92, 246, 0.25);
    }
  }
}

// Delete Modal
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;

  .delete-modal {
    background: #18181b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 32px;
    max-width: 420px;
    width: 100%;
    text-align: center;

    .modal-icon {
      width: 64px;
      height: 64px;
      margin: 0 auto 20px;
      background: rgba(239, 68, 68, 0.1);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ef4444;
    }

    h3 {
      font-size: 20px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.95);
      margin-bottom: 10px;
    }

    p {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 28px;
      line-height: 1.5;
    }

    .modal-actions {
      display: flex;
      gap: 12px;

      .cancel-btn {
        flex: 1;
        padding: 12px 20px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: rgba(255, 255, 255, 0.8);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: rgba(255, 255, 255, 0.08);
        }
      }

      .delete-btn {
        flex: 1;
        padding: 12px 20px;
        background: #ef4444;
        border: none;
        border-radius: 10px;
        color: white;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;

        &:hover:not(:disabled) {
          background: #dc2626;
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
  .page-header {
    padding: 32px 16px 24px;

    .header-content {
      flex-direction: column;

      .create-btn {
        width: 100%;
        justify-content: center;
      }
    }
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
