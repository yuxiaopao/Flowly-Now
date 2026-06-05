<template>
  <div class="search-panel">
    <div class="search-input-wrapper">
      <el-input
        v-model="searchQuery"
        placeholder="搜索文件..."
        :prefix-icon="Search"
        clearable
        @input="handleSearch"
        @clear="handleClear"
      />
    </div>

    <!-- 搜索结果 -->
    <div
      v-if="searchResults.length > 0"
      class="search-results"
    >
      <div class="results-header">
        <span class="results-count">{{ searchResults.length }} 个结果</span>
      </div>
      <div class="results-list">
        <div
          v-for="result in searchResults"
          :key="result.id"
          class="result-item"
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
        </div>
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
      v-else-if="searchQuery && !loading"
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
import { ref } from 'vue'
import { useCodeGraphStore } from '@/stores/codeGraph'
import { Search, File, FileCode, FileText } from 'lucide-vue-next'
import { Loading } from '@element-plus/icons-vue'

const emit = defineEmits(['select'])

const store = useCodeGraphStore()

const searchQuery = ref('')
const searchResults = ref([])
const loading = ref(false)

let searchTimer = null

async function handleSearch() {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }

  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }

  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      await store.search(searchQuery.value)
      searchResults.value = store.searchResults
    } finally {
      loading.value = false
    }
  }, 300)
}

function handleClear() {
  searchQuery.value = ''
  searchResults.value = []
}

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
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.search-input-wrapper {
  margin-bottom: 8px;
}

.search-results {
  max-height: 300px;
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
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--bg-hover);
  }

  .file-icon {
    width: 16px;
    height: 16px;
    color: var(--text-secondary);
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
