<template>
  <div class="file-tree">
    <div class="tree-header">
      <span class="tree-title">文件树</span>
      <span class="file-count">{{ files.length }} 文件</span>
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
import { fileNodes } from '@/utils/codeGraph'
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
const files = computed(() => fileNodes(props.nodes))

const treeProps = {
  children: 'children',
  label: 'label',
}

const treeData = computed(() => {
  // 按模块组织文件
  const modules = Object.create(null)

  files.value.forEach(node => {
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
    const moduleKey = `module-${newNode.module || 'root'}`
    if (!expandedKeys.value.includes(moduleKey)) {
      expandedKeys.value.push(moduleKey)
    }
    if (treeRef.value) {
      treeRef.value.setCurrentKey(newNode.id)
      const parent = treeRef.value.getNode(moduleKey)
      if (parent) parent.expanded = true
    }
  } else {
    treeRef.value?.setCurrentKey(null)
  }
}, { flush: 'post' })
</script>

<style lang="scss" scoped>
.file-tree {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 160px;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.tree-title {
  font-weight: 600;
  color: var(--text-primary);
}

.file-count {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(34, 211, 238, 0.25);
  color: #67e8f9;
  background: rgba(34, 211, 238, 0.08);
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px 12px;

  :deep(.el-tree) {
    background: transparent;
    --el-tree-node-hover-bg-color: transparent;

    .el-tree-node__content {
      height: 30px;
      border-radius: 8px;
      border: 1px solid transparent;
      transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;

      &:hover {
        background: rgba(34, 211, 238, 0.06);
        border-color: rgba(34, 211, 238, 0.18);
      }
    }

    .el-tree-node.is-current > .el-tree-node__content {
      background: rgba(34, 211, 238, 0.1);
      border-color: rgba(34, 211, 238, 0.3);
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
    color: #22d3ee;
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
    background: rgba(255, 255, 255, 0.05);
    padding: 0 6px;
    border-radius: 10px;
  }
}
</style>
