<template>
  <div class="node-panel">
    <div class="panel-header">
      <h3>节点组件</h3>
    </div>

    <div class="panel-content">
      <!-- 搜索 -->
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索节点..."
          :prefix-icon="Search"
          clearable
          size="small"
        />
      </div>

      <!-- 节点分类 -->
      <div
        v-for="category in filteredCategories"
        :key="category.name"
        class="node-category"
      >
        <div
          class="category-header"
          @click="toggleCategory(category.name)"
        >
          <component
            :is="category.icon"
            class="category-icon"
          />
          <span class="category-name">{{ category.label }}</span>
          <el-icon
            class="toggle-icon"
            :class="{ expanded: expandedCategories.includes(category.name) }"
          >
            <ArrowDown />
          </el-icon>
        </div>

        <div
          v-show="expandedCategories.includes(category.name)"
          class="node-list"
        >
          <div
            v-for="node in category.nodes"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node)"
          >
            <component
              :is="node.icon"
              class="node-icon"
            />
            <div class="node-info">
              <span class="node-label">{{ node.label }}</span>
              <span class="node-desc">{{ node.description }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 收藏的节点 -->
      <div
        v-if="favoriteNodes.length > 0"
        class="node-category"
      >
        <div class="category-header favorite">
          <Star class="category-icon" />
          <span class="category-name">收藏</span>
        </div>
        <div class="node-list">
          <div
            v-for="node in favoriteNodes"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node)"
          >
            <component
              :is="node.icon"
              class="node-icon"
            />
            <div class="node-info">
              <span class="node-label">{{ node.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷键提示 -->
    <div class="panel-footer">
      <div class="shortcut-hint">
        <kbd>Ctrl</kbd> + <kbd>Z</kbd> 撤销
      </div>
      <div class="shortcut-hint">
        <kbd>Ctrl</kbd> + <kbd>Y</kbd> 重做
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Search, ArrowDown, Star,
  PlayCircle, Circle, Zap, MessageSquare,
  GitBranch, Hammer, FileText, User,
  Webhook, Code, Key
} from 'lucide-vue-next'

const emit = defineEmits(['drag-start'])

const searchQuery = ref('')
const expandedCategories = ref(['control', 'ai', 'data', 'tools'])
const favoriteNodes = ref([])

const categories = [
  {
    name: 'control',
    label: '控制流',
    icon: GitBranch,
    nodes: [
      { type: 'start', label: '开始', icon: PlayCircle, description: '工作流入口' },
      { type: 'end', label: '结束', icon: Circle, description: '工作流出口' },
      { type: 'condition', label: '条件判断', icon: GitBranch, description: '根据条件分流' },
    ]
  },
  {
    name: 'ai',
    label: 'AI 节点',
    icon: Zap,
    nodes: [
      { type: 'llm', label: '大语言模型', icon: Zap, description: '调用 AI 模型' },
      { type: 'prompt', label: '提示词', icon: MessageSquare, description: '格式化提示词' },
    ]
  },
  {
    name: 'data',
    label: '数据处理',
    icon: FileText,
    nodes: [
      { type: 'input', label: '输入', icon: FileText, description: '获取用户输入' },
      { type: 'output', label: '输出', icon: User, description: '返回结果' },
      { type: 'code', label: '代码执行', icon: Code, description: '运行 Python 代码' },
      { type: 'variable', label: '变量', icon: Key, description: '变量赋值/获取' },
    ]
  },
  {
    name: 'tools',
    label: '工具',
    icon: Hammer,
    nodes: [
      { type: 'tool', label: '工具', icon: Hammer, description: '调用内置工具' },
      { type: 'http', label: 'HTTP请求', icon: Webhook, description: '发送 HTTP 请求' },
    ]
  }
]

const filteredCategories = computed(() => {
  if (!searchQuery.value) return categories

  const query = searchQuery.value.toLowerCase()
  return categories
    .map(cat => ({
      ...cat,
      nodes: cat.nodes.filter(node =>
        node.label.toLowerCase().includes(query) ||
        node.description.toLowerCase().includes(query)
      )
    }))
    .filter(cat => cat.nodes.length > 0)
})

function toggleCategory(name) {
  const index = expandedCategories.value.indexOf(name)
  if (index === -1) {
    expandedCategories.value.push(name)
  } else {
    expandedCategories.value.splice(index, 1)
  }
}

function onDragStart(event, node) {
  event.dataTransfer.setData('application/flowly-node', JSON.stringify(node))
  event.dataTransfer.effectAllowed = 'move'
  emit('drag-start', node)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.node-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-primary)-secondary;
  border-right: 1px solid var(--border-primary);
}

.panel-header {
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  h3 {
    margin: 0;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-3;
}

.search-box {
  margin-bottom: $spacing-4;

  :deep(.el-input__wrapper) {
    background-color: var(--bg-primary)-tertiary;
    border: 1px solid var(--border-primary);
  }
}

.node-category {
  margin-bottom: $spacing-4;
}

.category-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2;
  cursor: pointer;
  border-radius: $radius-md;
  transition: background-color $transition-fast;

  &:hover {
    background-color: var(--bg-primary)-hover;
  }

  .category-icon {
    width: 16px;
    height: 16px;
    color: $color-primary;
  }

  .category-name {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary)-secondary;
  }

  .toggle-icon {
    width: 14px;
    height: 14px;
    color: var(--text-primary)-tertiary;
    transition: transform $transition-fast;

    &.expanded {
      transform: rotate(180deg);
    }
  }
}

.node-list {
  padding: $spacing-2 0;
}

.node-item {
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  padding: $spacing-3;
  margin: $spacing-1 0;
  background-color: var(--bg-primary)-tertiary;
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: grab;
  transition: all $transition-fast;

  &:hover {
    border-color: $color-primary;
    background-color: rgba($color-primary, 0.05);
    transform: translateX(2px);
  }

  &:active {
    cursor: grabbing;
  }

  .node-icon {
    width: 20px;
    height: 20px;
    color: $color-primary;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .node-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;

    .node-label {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: var(--text-primary);
    }

    .node-desc {
      font-size: $font-size-xs;
      color: var(--text-primary)-tertiary;
    }
  }
}

.panel-footer {
  padding: $spacing-3;
  border-top: 1px solid var(--border-primary);
}

.shortcut-hint {
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-primary)-tertiary;
  margin-bottom: $spacing-1;

  kbd {
    padding: 2px 6px;
    background-color: var(--bg-primary)-tertiary;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
    font-size: 10px;
  }
}
</style>



