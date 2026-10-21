<template>
  <div class="search-panel">
    <div class="search-input-wrapper">
      <el-input
        v-model="searchQuery"
        placeholder="搜索文件..."
        aria-label="搜索图谱文件"
        :disabled="!store.currentProject"
        :prefix-icon="Search"
        clearable
        @input="handleSearch"
        @clear="handleClear"
        @keydown.enter.prevent="selectFirstResult"
      />
    </div>

    <!-- 搜索结果 -->
    <div
      v-if="searchResults.length > 0 && !loading"
      class="search-results"
    >
      <div class="results-header">
        <span class="results-count">{{ searchResults.length }} 个结果</span>
      </div>
      <div class="results-list">
        <button
          v-for="result in searchResults"
          :key="result.id"
          class="result-item"
          type="button"
          :title="result.path"
          @click="handleSelect(result)"
        >
          <component
            :is="getFileIcon(result.type)"
            class="file-icon"
          />
          <div class="result-info">
            <span class="result-name">{{ result.name }}</span>
            <span class="result-path">{{ result.path }}</span>
          </div>
          <el-tag
            size="small"
            :type="getTypeTagType(result.type)"
          >
            {{ result.type }}
          </el-tag>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div
      v-else-if="loading"
      class="search-loading"
    >
      <el-icon class="is-loading">
        <Loading />
      </el-icon>
      <span>搜索中...</span>
    </div>

    <!-- 无结果 -->
    <div
      v-else-if="store.searchError"
      class="search-loading"
      role="alert"
    >
      <span>{{ store.searchError }}</span>
      <el-button
        size="small"
        @click="handleSearch"
      >
        {{ CODE_GRAPH.messages.retry }}
      </el-button>
    </div>
    <div
      v-else-if="searchQuery.trim() && !loading"
      class="no-results"
    >
      <el-empty
        description="未找到匹配的文件"
        :image-size="60"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { CODE_GRAPH } from '@/config/codeGraph'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Search, File, FileCode, FileText } from 'lucide-vue-next'
import { Loading } from '@element-plus/icons-vue'

const emit = defineEmits(['select'])

const store = useCodeGraphStore()

const searchQuery = ref('')
const { searchResults } = storeToRefs(store)
const pending = ref(false)
const loading = computed(() => pending.value || store.searchLoading)

let searchTimer = null

function handleSearch() {
  clearTimeout(searchTimer)
  store.clearSearch()
  pending.value = Boolean(searchQuery.value.trim())
  if (!pending.value) return
  searchTimer = setTimeout(() => {
    pending.value = false
    store.search(searchQuery.value)
  }, CODE_GRAPH.searchDebounceMs)
}

function handleClear() {
  searchQuery.value = ''
  pending.value = false
  clearTimeout(searchTimer)
  store.clearSearch()
}

function selectFirstResult() {
  if (!loading.value && searchResults.value[0]) handleSelect(searchResults.value[0])
}

watch(() => store.currentProject?.id, handleClear)
onUnmounted(() => clearTimeout(searchTimer))

function handleSelect(result) {
  emit('select', result)
}

function getFileIcon(type) {
  switch (type) {
    case 'vue':
    case 'js':
    case 'ts':
    case 'jsx':
    case 'tsx':
      return FileCode
    case 'md':
    case 'txt':
      return FileText
    default:
      return File
  }
}

function getTypeTagType(type) {
  const typeMap = {
    vue: '',
    js: 'warning',
    ts: 'info',
    py: 'success',
    json: 'danger',
  }
  return typeMap[type] || 'info'
}
</script>

<style lang="scss" scoped>
.search-panel {
  padding: 12px 12px 8px;
}

.search-input-wrapper {
  margin-bottom: 8px;

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.04);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
    transition: box-shadow 0.25s ease;

    &:hover,
    &.is-focus {
      box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.4) inset;
    }
  }
}

.search-results {
  max-height: 240px;
  overflow-y: auto;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-item {
  width: 100%;
  text-align: left;
  font: inherit;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;

  &:hover,
  &:focus-visible {
    background: var(--bg-hover);
    border-color: var(--border-secondary);
  }

  .file-icon {
    width: 16px;
    height: 16px;
    color: #22d3ee;
    flex-shrink: 0;
  }

  .result-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;

    .result-name {
      font-size: 13px;
      color: var(--text-primary);
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .result-path {
      font-size: 11px;
      color: var(--text-secondary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.search-loading,
.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 13px;
  gap: 8px;
}
</style>
