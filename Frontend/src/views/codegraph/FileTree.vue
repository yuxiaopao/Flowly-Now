<template>
  <div class="file-tree">
    <div class="tree-header">
      <span class="tree-title">文件树</span>
      <span class="file-count">{{ nodes.length }} 文件</span>
    </div>

    <div class="tree-content">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="treeProps"
        node-key="id"
        :default-expanded-keys="expandedKeys"
        :current-node-key="selectedNode?.id"
        highlight-current
        @node-click="handleNodeClick"
        @node-expand="handleNodeExpand"
        @node-collapse="handleNodeCollapse"
      >
        <template #default="{ data }">
          <div class="tree-node-content">
            <component
              :is="getNodeIcon(data)"
              class="node-icon"
            />
            <span class="node-label">{{ data.label }}</span>
            <span
              v-if="data.fileCount"
              class="node-count"
            >{{ data.fileCount }}</span>
          </div>
        </template>
      </el-tree>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  Folder,
  FileCode,
  FileText,
  File,
  FileJson
} from 'lucide-vue-next'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  selectedNode: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['select'])

const treeRef = ref(null)
const expandedKeys = ref([])

const treeProps = {
  children: 'children',
  label: 'label',
}

const treeData = computed(() => {
  // 按模块组织文件
  const modules = {}

  props.nodes.forEach(node => {
    const moduleName = node.module || 'root'
    if (!modules[moduleName]) {
      modules[moduleName] = {
        id: `module-${moduleName}`,
        label: moduleName,
        type: 'module',
        children: [],
        fileCount: 0,
      }
    }
    modules[moduleName].children.push({
      id: node.id,
      label: node.name,
      type: node.type,
      path: node.path,
      module: node.module,
      data: node,
    })
    modules[moduleName].fileCount++
  })

  // 转换为数组并排序
  return Object.values(modules)
    .sort((a, b) => a.label.localeCompare(b.label))
    .map(module => ({
      ...module,
      children: module.children.sort((a, b) => a.label.localeCompare(b.label)),
    }))
})

function handleNodeClick(data) {
  if (data.type !== 'module') {
    emit('select', data.data)
  }
}

function handleNodeExpand(data) {
  if (!expandedKeys.value.includes(data.id)) {
    expandedKeys.value.push(data.id)
  }
}

function handleNodeCollapse(data) {
  const index = expandedKeys.value.indexOf(data.id)
  if (index > -1) {
    expandedKeys.value.splice(index, 1)
  }
}

function getNodeIcon(data) {
  if (data.type === 'module') {
    return Folder
  }

  const iconMap = {
    vue: FileCode,
    js: FileCode,
    ts: FileCode,
    jsx: FileCode,
    tsx: FileCode,
    py: FileCode,
    json: FileJson,
    md: FileText,
    txt: FileText,
  }

  return iconMap[data.type] || File
}

// 监听选中节点变化
watch(() => props.selectedNode, (newNode) => {
  if (newNode) {
    const moduleKey = `module-${newNode.module}`
    if (!expandedKeys.value.includes(moduleKey)) {
      expandedKeys.value.push(moduleKey)
    }
    if (treeRef.value) {
      treeRef.value.setCurrentKey(newNode.id)
    }
  }
})
</script>

<style lang="scss" scoped>
.file-tree {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 200px;
  border-bottom: 1px solid var(--border-color);
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.tree-title {
  font-weight: 500;
  color: var(--text-primary);
}

.file-count {
  font-size: 12px;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 12px;

  :deep(.el-tree) {
    background: transparent;

    .el-tree-node__content {
      height: 28px;
      border-radius: 4px;

      &:hover {
        background: var(--bg-hover);
      }
    }

    .el-tree-node.is-current > .el-tree-node__content {
      background: var(--color-primary-light-9);
    }
  }
}

.tree-node-content {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  font-size: 13px;

  .node-icon {
    width: 14px;
    height: 14px;
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .node-label {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .node-count {
    font-size: 11px;
    color: var(--text-secondary);
    background: var(--bg-hover);
    padding: 0 6px;
    border-radius: 10px;
  }
}
</style>
