# 任务 2：工作流编辑器增强功能

## 任务概述

| 属性 | 值 |
|------|-----|
| **任务名称** | 工作流编辑器增强功能 |
| **优先级** | P0 - 核心功能 |
| **预估工时** | 4-6 天 |
| **前置依赖** | 基础编辑器组件已完成 |

## 任务目标

增强工作流编辑器，提供更丰富的编辑功能和更好的用户体验。

## 详细需求

### 1.1 多人协作编辑

#### 1.1.1 WebSocket 实时同步

```javascript
// Frontend/src/composables/useCollaboration.js
import { ref, onMounted, onUnmounted } from 'vue'

export function useCollaboration(workflowId) {
  const collaborators = ref([])
  const cursors = ref({})
  const ws = ref(null)
  
  // 连接 WebSocket
  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws.value = new WebSocket(`${protocol}//.../ws/workflow/${workflowId}/collaborate/`)
    
    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleMessage(data)
    }
  }
  
  // 处理消息
  function handleMessage(data) {
    switch (data.type) {
      case 'user_join':
        collaborators.value.push(data.user)
        break
      case 'user_leave':
        collaborators.value = collaborators.value.filter(u => u.id !== data.userId)
        break
      case 'cursor_move':
        cursors.value[data.userId] = data.position
        break
      case 'node_update':
        // 更新其他用户的画布
        store.updateRemoteNode(data.node)
        break
      case 'edge_update':
        store.updateRemoteEdge(data.edge)
        break
    }
  }
  
  // 广播更新
  function broadcastUpdate(type, data) {
    ws.value.send(JSON.stringify({ type, ...data }))
  }
  
  // 广播光标位置
  function broadcastCursor(position) {
    broadcastUpdate('cursor_move', { position })
  }
  
  return {
    collaborators,
    cursors,
    broadcastUpdate,
    broadcastCursor
  }
}
```

#### 1.1.2 协作光标显示

```vue
<!-- Frontend/src/components/workflow/CollaboratorCursors.vue -->
<template>
  <div class="collaborator-cursors">
    <div
      v-for="(cursor, userId) in cursors"
      :key="userId"
      class="cursor"
      :style="{ left: `${cursor.x}px`, top: `${cursor.y}px` }"
    >
      <svg width="24" height="24" viewBox="0 0 24 24">
        <path
          d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87c.48 0 .72-.58.38-.92L6.35 2.85a.5.5 0 0 0-.85.36z"
          :fill="getUserColor(userId)"
        />
      </svg>
      <span class="cursor-label" :style="{ background: getUserColor(userId) }">
        {{ getUserName(userId) }}
      </span>
    </div>
  </div>
</template>
```

### 1.2 节点搜索与定位

```javascript
// Frontend/src/components/workflow/NodeSearch.vue
<template>
  <div class="node-search">
    <el-input
      v-model="searchQuery"
      placeholder="搜索节点..."
      prefix-icon="Search"
      @input="handleSearch"
    />
    
    <div v-if="searchResults.length > 0" class="search-results">
      <div
        v-for="result in searchResults"
        :key="result.node.id"
        class="search-result-item"
        @click="focusNode(result.node)"
      >
        <span class="node-type-icon">{{ getNodeIcon(result.node.type) }}</span>
        <span class="node-name">{{ result.node.name }}</span>
        <span class="match-text">{{ result.match }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const searchQuery = ref('')
const searchResults = computed(() => {
  if (!searchQuery.value) return []
  
  const query = searchQuery.value.toLowerCase()
  return nodes.value
    .filter(node => 
      node.name.toLowerCase().includes(query) ||
      node.description?.toLowerCase().includes(query)
    )
    .map(node => ({
      node,
      match: node.name
    }))
    .slice(0, 10)
})

function focusNode(node) {
  // 平移到节点位置
  panTo(node.position_x, node.position_y)
  // 选中节点
  selectNode(node.id)
}
</script>
```

### 1.3 节点分组与注释

#### 1.3.1 节点分组

```javascript
// 添加分组功能
const groups = ref([
  {
    id: 'group-1',
    name: '输入处理',
    color: '#409EFF',
    nodeIds: ['node-1', 'node-2', 'node-3'],
    collapsed: false
  }
])

function createGroup(name, selectedNodeIds) {
  const group = {
    id: `group-${Date.now()}`,
    name,
    color: getRandomColor(),
    nodeIds: [...selectedNodeIds],
    collapsed: false
  }
  groups.value.push(group)
}

function collapseGroup(groupId) {
  const group = groups.value.find(g => g.id === groupId)
  if (group) {
    group.collapsed = !group.collapsed
  }
}
```

#### 1.3.2 节点注释

```javascript
// 节点评论功能
const comments = ref([
  {
    id: 'comment-1',
    nodeId: 'node-1',
    userId: 1,
    content: '这个节点的 prompt 需要优化',
    position: { x: 0, y: 0 },
    replies: [
      {
        id: 'reply-1',
        userId: 2,
        content: '好的，我来处理',
        createdAt: '2026-05-09T10:00:00Z'
      }
    ],
    resolved: false,
    createdAt: '2026-05-09T09:00:00Z'
  }
])

function addComment(nodeId, content) {
  comments.value.push({
    id: `comment-${Date.now()}`,
    nodeId,
    userId: currentUser.value.id,
    content,
    replies: [],
    resolved: false,
    createdAt: new Date().toISOString()
  })
}
```

### 1.4 撤销/重做功能

```javascript
// Frontend/src/stores/history.js
import { defineStore } from 'pinia'

export const useHistoryStore = defineStore('history', () => {
  const undoStack = ref([])
  const redoStack = ref([])
  const maxHistorySize = 50
  
  // 保存状态快照
  function saveSnapshot(nodes, edges) {
    const snapshot = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      timestamp: Date.now()
    }
    
    undoStack.value.push(snapshot)
    if (undoStack.value.length > maxHistorySize) {
      undoStack.value.shift()
    }
    
    // 清空重做栈
    redoStack.value = []
  }
  
  // 撤销
  function undo(nodes, edges) {
    if (undoStack.value.length === 0) return null
    
    // 保存当前状态到重做栈
    redoStack.value.push({
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      timestamp: Date.now()
    })
    
    // 弹出上一个状态
    return undoStack.value.pop()
  }
  
  // 重做
  function redo(nodes, edges) {
    if (redoStack.value.length === 0) return null
    
    // 保存当前状态到撤销栈
    undoStack.value.push({
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      timestamp: Date.now()
    })
    
    // 弹出重做状态
    return redoStack.value.pop()
  }
  
  return { undoStack, redoStack, saveSnapshot, undo, redo }
})
```

### 1.5 快捷键支持

```javascript
// Frontend/src/composables/useKeyboardShortcuts.js
import { onMounted, onUnmounted } from 'vue'

const shortcuts = {
  // 文件操作
  'Ctrl+S': 'save',
  'Ctrl+Z': 'undo',
  'Ctrl+Shift+Z': 'redo',
  'Ctrl+Y': 'redo',
  
  // 编辑操作
  'Ctrl+C': 'copy',
  'Ctrl+V': 'paste',
  'Ctrl+X': 'cut',
  'Delete': 'delete',
  'Backspace': 'delete',
  'Escape': 'deselect',
  
  // 选择
  'Ctrl+A': 'selectAll',
  'Ctrl+D': 'duplicate',
  
  // 视图
  'Ctrl+0': 'zoomReset',
  'Ctrl+Plus': 'zoomIn',
  'Ctrl+Minus': 'zoomOut',
  
  // 节点操作
  'Ctrl+Shift+L': 'addLLMNode',
  'Ctrl+Shift+P': 'addPromptNode',
  'Ctrl+Shift+T': 'addToolNode',
}

export function useKeyboardShortcuts(store) {
  function handleKeyDown(event) {
    const key = buildKeyString(event)
    const action = shortcuts[key]
    
    if (action) {
      event.preventDefault()
      executeAction(action)
    }
  }
  
  function buildKeyString(event) {
    const parts = []
    if (event.ctrlKey) parts.push('Ctrl')
    if (event.shiftKey) parts.push('Shift')
    if (event.altKey) parts.push('Alt')
    parts.push(event.key)
    return parts.join('+')
  }
  
  function executeAction(action) {
    const actions = {
      save: () => store.saveWorkflow(),
      undo: () => store.undo(),
      redo: () => store.redo(),
      delete: () => store.deleteSelected(),
      selectAll: () => store.selectAllNodes(),
      duplicate: () => store.duplicateSelected(),
      // ...
    }
    
    if (actions[action]) {
      actions[action]()
    }
  }
  
  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
  })
  
  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
  })
}
```

### 1.6 节点模板市场

```javascript
// Frontend/src/components/workflow/NodeTemplateGallery.vue
<template>
  <el-drawer
    v-model="visible"
    title="节点模板"
    size="400px"
  >
    <div class="template-categories">
      <el-tabs v-model="activeCategory">
        <el-tab-pane
          v-for="category in categories"
          :key="category.id"
          :label="category.name"
          :name="category.id"
        >
          <div class="template-grid">
            <div
              v-for="template in category.templates"
              :key="template.id"
              class="template-card"
              @click="applyTemplate(template)"
            >
              <div class="template-icon">{{ template.icon }}</div>
              <div class="template-name">{{ template.name }}</div>
              <div class="template-desc">{{ template.description }}</div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<script setup>
const categories = ref([
  {
    id: 'llm',
    name: 'LLM 节点',
    templates: [
      {
        id: 'chat-completion',
        name: '对话补全',
        icon: '💬',
        description: '简单的对话补全模板',
        config: { model: 'gpt-4', temperature: 0.7 }
      },
      // ...
    ]
  },
  {
    id: 'logic',
    name: '逻辑节点',
    templates: [
      {
        id: 'if-else',
        name: '条件分支',
        icon: '🔀',
        description: 'if-else 条件分支模板',
        config: { conditions: [] }
      },
      // ...
    ]
  }
])

function applyTemplate(template) {
  // 在画布中心创建节点
  const position = getCanvasCenter()
  store.addNode({
    ...template,
    position_x: position.x,
    position_y: position.y
  })
  visible.value = false
}
</script>
```

### 1.7 自动保存

```javascript
// Frontend/src/stores/autoSave.js
import { defineStore } from 'pinia'
import { watch, ref } from 'vue'

export const useAutoSaveStore = defineStore('autoSave', () => {
  const lastSaved = ref(null)
  const isAutoSaving = ref(false)
  const autoSaveInterval = ref(30000) // 30秒
  
  let saveTimer = null
  
  function startAutoSave(store) {
    saveTimer = setInterval(async () => {
      if (store.isDirty && !store.isSaving) {
        await saveWithNotification(store)
      }
    }, autoSaveInterval.value)
  }
  
  function stopAutoSave() {
    if (saveTimer) {
      clearInterval(saveTimer)
      saveTimer = null
    }
  }
  
  async function saveWithNotification(store) {
    isAutoSaving.value = true
    try {
      await store.saveWorkflow()
      lastSaved.value = new Date()
      showNotification('success', '自动保存成功')
    } catch (error) {
      showNotification('error', '自动保存失败')
    } finally {
      isAutoSaving.value = false
    }
  }
  
  // 监听变化启动自动保存
  watch(() => store.isDirty, (isDirty) => {
    if (isDirty) {
      startAutoSave(store)
    } else {
      stopAutoSave()
    }
  })
  
  return { lastSaved, isAutoSaving }
})
```

## 验收标准

- [ ] 支持多人实时协作编辑
- [ ] 协作者光标实时显示
- [ ] 节点搜索和快速定位
- [ ] 节点分组功能
- [ ] 节点评论和讨论
- [ ] 完整的撤销/重做功能
- [ ] 快捷键支持
- [ ] 节点模板库
- [ ] 自动保存功能

## 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `Frontend/src/composables/useCollaboration.js` | 协作功能 |
| `Frontend/src/composables/useKeyboardShortcuts.js` | 快捷键 |
| `Frontend/src/components/workflow/CollaboratorCursors.vue` | 协作光标 |
| `Frontend/src/components/workflow/NodeSearch.vue` | 节点搜索 |
| `Frontend/src/components/workflow/NodeGroups.vue` | 节点分组 |
| `Frontend/src/components/workflow/NodeComments.vue` | 节点评论 |
| `Frontend/src/components/workflow/NodeTemplateGallery.vue` | 模板库 |
| `Frontend/src/stores/history.js` | 历史记录 |

## 测试用例

```javascript
// tests/unit/workflow-editor.spec.js

describe('Workflow Editor', () => {
  describe('Undo/Redo', () => {
    it('should undo node deletion', async () => {
      const initialCount = store.nodes.length
      store.deleteNode('node-1')
      expect(store.nodes.length).toBe(initialCount - 1)
      store.undo()
      expect(store.nodes.length).toBe(initialCount)
    })
  })
  
  describe('Collaboration', () => {
    it('should show collaborator cursors', async () => {
      // 模拟其他用户加入
      // 验证光标显示
    })
  })
})
```
