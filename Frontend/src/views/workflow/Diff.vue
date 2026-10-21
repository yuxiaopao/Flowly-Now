<template>
  <PageShell
    width="wide"
    class="workflow-diff-page"
  >
    <PageHeader
      title="工作流对比"
      subtitle="比较两个工作流的差异"
    />

    <!-- Workflow Selection -->
    <el-card
      shadow="never"
      class="selection-card"
    >
      <div class="selection-row">
        <div class="selection-item">
          <label>选择工作流 A (源)</label>
          <el-select
            v-model="workflowA"
            placeholder="选择或搜索工作流"
            filterable
            remote
            :remote-method="searchWorkflowsA"
            :loading="searchingA"
            @change="loadWorkflowA"
          >
            <el-option
              v-for="wf in workflowListA"
              :key="wf.id"
              :label="wf.name"
              :value="wf.id"
            >
              <div class="workflow-option">
                <Workflow class="wf-icon" />
                <span>{{ wf.name }}</span>
                <span class="wf-date">{{ formatDate(wf.updatedAt || wf.updated_at) }}</span>
              </div>
            </el-option>
          </el-select>
        </div>

        <div class="vs-badge">
          VS
        </div>

        <div class="selection-item">
          <label>选择工作流 B (目标)</label>
          <el-select
            v-model="workflowB"
            placeholder="选择或搜索工作流"
            filterable
            remote
            :remote-method="searchWorkflowsB"
            :loading="searchingB"
            @change="loadWorkflowB"
          >
            <el-option
              v-for="wf in workflowListB"
              :key="wf.id"
              :label="wf.name"
              :value="wf.id"
            >
              <div class="workflow-option">
                <Workflow class="wf-icon" />
                <span>{{ wf.name }}</span>
                <span class="wf-date">{{ formatDate(wf.updatedAt || wf.updated_at) }}</span>
              </div>
            </el-option>
          </el-select>
        </div>

        <el-button
          type="primary"
          :disabled="!workflowA || !workflowB"
          @click="compareWorkflows"
        >
          <GitCompare class="btn-icon" />
          开始对比
        </el-button>
      </div>
    </el-card>

    <!-- Diff Results -->
    <div
      v-if="diffResult"
      class="diff-results"
    >
      <!-- Diff Summary -->
      <el-card
        shadow="never"
        class="summary-card"
      >
        <div class="summary-header">
          <h3>差异摘要</h3>
          <div class="summary-actions">
            <el-button
              size="small"
              @click="copyDiff"
            >
              <Copy class="btn-icon-small" />
              复制差异
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click="mergeChanges"
            >
              <GitMerge class="btn-icon-small" />
              合并到 A
            </el-button>
          </div>
        </div>
        <div class="summary-stats">
          <div class="stat-item added">
            <PlusCircle class="stat-icon" />
            <span class="stat-value">{{ diffResult.summary.nodesAdded + diffResult.summary.edgesAdded }}</span>
            <span class="stat-label">新增</span>
          </div>
          <div class="stat-item removed">
            <MinusCircle class="stat-icon" />
            <span class="stat-value">{{ diffResult.summary.nodesRemoved + diffResult.summary.edgesRemoved }}</span>
            <span class="stat-label">删除</span>
          </div>
          <div class="stat-item modified">
            <Edit class="stat-icon" />
            <span class="stat-value">{{ diffResult.summary.nodesModified }}</span>
            <span class="stat-label">修改</span>
          </div>
          <div class="stat-item unchanged">
            <Minus class="stat-icon" />
            <span class="stat-value">{{ diffResult.summary.unchanged }}</span>
            <span class="stat-label">未变</span>
          </div>
        </div>
      </el-card>

      <!-- Diff Content -->
      <div class="diff-content">
        <!-- Visual Diff -->
        <el-card
          shadow="never"
          class="visual-diff-card"
        >
          <template #header>
            <div class="card-header">
              <span>可视化对比</span>
              <el-radio-group
                v-model="visualView"
                size="small"
              >
                <el-radio-button value="side">
                  并排
                </el-radio-button>
                <el-radio-button value="unified">
                  统一
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <div class="visual-diff-container">
            <!-- Side by Side View -->
            <div
              v-if="visualView === 'side'"
              class="side-by-side"
            >
              <div class="diff-panel panel-a">
                <div class="panel-header">
                  <span class="panel-label">A</span>
                  <span class="panel-name">{{ workflowAName }}</span>
                  <el-tag size="small">
                    {{ workflowAData?.nodes?.length || 0 }} 节点
                  </el-tag>
                </div>
                <div class="panel-canvas">
                  <div class="mini-canvas">
                    <div
                      v-for="node in workflowAData?.nodes || []"
                      :key="node.id"
                      :class="['mini-node', getNodeStatus(node.id)]"
                      :style="getNodeStyle(node)"
                    >
                      {{ getNodeLabel(node) }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="diff-divider" />

              <div class="diff-panel panel-b">
                <div class="panel-header">
                  <span class="panel-label">B</span>
                  <span class="panel-name">{{ workflowBName }}</span>
                  <el-tag size="small">
                    {{ workflowBData?.nodes?.length || 0 }} 节点
                  </el-tag>
                </div>
                <div class="panel-canvas">
                  <div class="mini-canvas">
                    <div
                      v-for="node in workflowBData?.nodes || []"
                      :key="node.id"
                      :class="['mini-node', getNodeStatus(node.id)]"
                      :style="getNodeStyle(node)"
                    >
                      {{ getNodeLabel(node) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Unified View -->
            <div
              v-else
              class="unified-view"
            >
              <div class="diff-legend">
                <span class="legend-item added">新增</span>
                <span class="legend-item removed">删除</span>
                <span class="legend-item modified">修改</span>
                <span class="legend-item unchanged">未变</span>
              </div>
              <div class="nodes-list">
                <div
                  v-for="node in allNodes"
                  :key="node.id"
                  :class="['node-diff-item', node.diffStatus]"
                >
                  <div class="node-header">
                    <span class="node-status-icon">
                      <PlusCircle
                        v-if="node.diffStatus === 'added'"
                        class="icon added"
                      />
                      <MinusCircle
                        v-else-if="node.diffStatus === 'removed'"
                        class="icon removed"
                      />
                      <Edit
                        v-else-if="node.diffStatus === 'modified'"
                        class="icon modified"
                      />
                      <Minus
                        v-else
                        class="icon unchanged"
                      />
                    </span>
                    <span class="node-type">{{ node.type }}</span>
                    <span class="node-label">{{ getNodeLabel(node) }}</span>
                    <el-tag
                      size="small"
                      :type="getStatusTagType(node.diffStatus)"
                    >
                      {{ getStatusLabel(node.diffStatus) }}
                    </el-tag>
                  </div>
                  <div
                    v-if="node.diffStatus === 'modified'"
                    class="node-changes"
                  >
                    <div
                      v-for="(change, key) in node.changes"
                      :key="key"
                      class="change-item"
                    >
                      <span class="change-field">{{ key }}:</span>
                      <div class="change-values">
                        <code class="old-value">{{ change.old || '(无)' }}</code>
                        <ArrowRight class="arrow-icon" />
                        <code class="new-value">{{ change.new || '(无)' }}</code>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- Detailed Diff -->
        <el-card shadow="never">
          <template #header>
            <span>详细差异</span>
          </template>

          <el-tabs>
            <!-- Nodes Tab -->
            <el-tab-pane label="节点变化">
              <div class="diff-table">
                <el-table
                  :data="diffResult.nodes"
                  stripe
                >
                  <el-table-column
                    label="状态"
                    width="100"
                  >
                    <template #default="{ row }">
                      <el-tag
                        :type="getStatusTagType(row.status)"
                        size="small"
                      >
                        {{ getStatusLabel(row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column
                    prop="id"
                    label="节点ID"
                    width="150"
                  >
                    <template #default="{ row }">
                      <code>{{ row.id }}</code>
                    </template>
                  </el-table-column>
                  <el-table-column
                    prop="type"
                    label="类型"
                    width="120"
                  />
                  <el-table-column
                    label="名称"
                    min-width="150"
                  >
                    <template #default="{ row }">
                      {{ row.name || '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column
                    label="操作"
                    width="200"
                  >
                    <template #default="{ row }">
                      <div
                        v-if="row.status === 'modified'"
                        class="change-summary"
                      >
                        <span
                          v-for="(val, key) in row.changes"
                          :key="key"
                          class="change-tag"
                        >
                          {{ key }}: {{ val.old }} → {{ val.new }}
                        </span>
                      </div>
                      <span
                        v-else
                        class="no-change"
                      >-</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <!-- Edges Tab -->
            <el-tab-pane label="连接变化">
              <div class="diff-table">
                <el-table
                  :data="diffResult.edges"
                  stripe
                >
                  <el-table-column
                    label="状态"
                    width="100"
                  >
                    <template #default="{ row }">
                      <el-tag
                        :type="getStatusTagType(row.status)"
                        size="small"
                      >
                        {{ getStatusLabel(row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column
                    label="源节点"
                    width="150"
                  >
                    <template #default="{ row }">
                      <code>{{ row.source }}</code>
                    </template>
                  </el-table-column>
                  <el-table-column
                    label="目标节点"
                    width="150"
                  >
                    <template #default="{ row }">
                      <code>{{ row.target }}</code>
                    </template>
                  </el-table-column>
                  <el-table-column
                    label="连接标签"
                    min-width="150"
                  >
                    <template #default="{ row }">
                      {{ row.label || '-' }}
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <!-- JSON Tab -->
            <el-tab-pane label="JSON 对比">
              <div class="json-diff">
                <pre><code>{{ formatJson(diffResult.rawDiff) }}</code></pre>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else
      class="empty-state"
    >
      <GitCompare class="empty-icon" />
      <h3>选择两个工作流开始对比</h3>
      <p>选择上方的工作流 A 和工作流 B，系统将分析它们之间的差异</p>
    </div>
  </PageShell>
</template>

<script setup>
import PageHeader from '@/components/layout/PageHeader.vue'
import PageShell from '@/components/layout/PageShell.vue'
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Workflow, GitCompare, Copy, GitMerge,
  PlusCircle, MinusCircle, Edit, Minus, ArrowRight
} from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { getWorkflowList, getWorkflowById, updateWorkflow } from '@/api/workflow'

const appStore = useAppStore()
const route = useRoute()

function getNodeType(node) {
  return node?.type || node?.nodeType || node?.node_type || 'unknown'
}

function getNodeLabel(node) {
  return node?.data?.label || node?.name || getNodeType(node) || '未命名'
}

function normalizeWorkflowNode(node) {
  if (!node) return node
  const nodeType = getNodeType(node)
  return {
    ...node,
    type: nodeType,
    data: node.data || {
      label: node.name || nodeType,
      config: node.config || {},
    },
    position: node.position || {
      x: node.positionX ?? node.position_x ?? 0,
      y: node.positionY ?? node.position_y ?? 0,
    },
  }
}

function extractWorkflowGraph(data) {
  const workflowData = data?.workflowData || data?.workflow_data || {}
  const rawNodes = data?.nodes || workflowData.nodes || []
  const rawEdges = data?.edges || workflowData.edges || []
  return {
    nodes: rawNodes.map(normalizeWorkflowNode),
    edges: rawEdges,
  }
}

function unwrapList(response) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.results)) return response.results
  return []
}

const workflowA = ref(null)
const workflowB = ref(null)
const workflowListA = ref([])
const workflowListB = ref([])
const searchingA = ref(false)
const searchingB = ref(false)
const workflowAName = ref('')
const workflowBName = ref('')
const workflowAData = ref(null)
const workflowBData = ref(null)
const diffResult = ref(null)
const visualView = ref('side')

const searchWorkflowsA = async (query) => {
  searchingA.value = true
  try {
    const res = await getWorkflowList({ search: query, page_size: 20 })
    workflowListA.value = unwrapList(res)
  } catch (e) {
    appStore.error('加载工作流列表失败')
    workflowListA.value = []
  } finally {
    searchingA.value = false
  }
}

const searchWorkflowsB = async (query) => {
  searchingB.value = true
  try {
    const res = await getWorkflowList({ search: query, page_size: 20 })
    workflowListB.value = unwrapList(res)
  } catch (e) {
    appStore.error('加载工作流列表失败')
    workflowListB.value = []
  } finally {
    searchingB.value = false
  }
}

const loadWorkflowA = async (id) => {
  try {
    const data = await getWorkflowById(id)
    workflowAName.value = data.name
    workflowAData.value = extractWorkflowGraph(data)
  } catch (e) {
    appStore.error('加载工作流详情失败')
  }
}

const loadWorkflowB = async (id) => {
  try {
    const data = await getWorkflowById(id)
    workflowBName.value = data.name
    workflowBData.value = extractWorkflowGraph(data)
  } catch (e) {
    appStore.error('加载工作流详情失败')
  }
}

const compareWorkflows = async () => {
  if (!workflowAData.value || !workflowBData.value) return

  try {
    const nodesA = workflowAData.value.nodes
    const nodesB = workflowBData.value.nodes
    const edgesA = workflowAData.value.edges
    const edgesB = workflowBData.value.edges

  // Calculate diff
  const nodesAIds = new Set(nodesA.map(n => n.id))
  const nodesBIds = new Set(nodesB.map(n => n.id))

  const addedNodes = nodesB.filter(n => !nodesAIds.has(n.id))
  const removedNodes = nodesA.filter(n => !nodesBIds.has(n.id))
  const addedEdges = edgesB.filter(e => !edgesA.some(ex => ex.id === e.id))
  const removedEdges = edgesA.filter(e => !edgesB.some(ex => ex.id === e.id))

  const modifiedNodes = nodesA.filter(a => {
    const b = nodesB.find(n => n.id === a.id)
    if (!b) return false
    return JSON.stringify(a) !== JSON.stringify(b)
  }).map(a => ({
    ...a,
    name: getNodeLabel(a),
    changes: {
      config: {
        old: a.data?.config || a.config,
        new: nodesB.find(n => n.id === a.id)?.data?.config || nodesB.find(n => n.id === a.id)?.config
      }
    }
  }))

  const unchangedNodes = nodesA.filter(a => {
    const b = nodesB.find(n => n.id === a.id)
    if (!b) return false
    return JSON.stringify(a) === JSON.stringify(b)
  })

  diffResult.value = {
    summary: {
      nodesAdded: addedNodes.length,
      nodesRemoved: removedNodes.length,
      nodesModified: modifiedNodes.length,
      unchanged: unchangedNodes.length,
      edgesAdded: addedEdges.length,
      edgesRemoved: removedEdges.length,
    },
    nodes: [
      ...addedNodes.map(n => ({ id: n.id, type: getNodeType(n), name: getNodeLabel(n), status: 'added' })),
      ...removedNodes.map(n => ({ id: n.id, type: getNodeType(n), name: getNodeLabel(n), status: 'removed' })),
      ...modifiedNodes.map(n => ({ ...n, status: 'modified' })),
      ...unchangedNodes.map(n => ({ id: n.id, type: getNodeType(n), name: getNodeLabel(n), status: 'unchanged' }))
    ],
    edges: [
      ...addedEdges.map(e => ({ ...e, status: 'added' })),
      ...removedEdges.map(e => ({ ...e, status: 'removed' }))
    ],
    rawDiff: {
      nodes: { added: addedNodes, removed: removedNodes, modified: modifiedNodes },
      edges: { added: addedEdges, removed: removedEdges }
    }
  }
  } catch (e) {
    appStore.error('对比失败')
  }
}

const allNodes = computed(() => {
  if (!diffResult.value) return []
  return diffResult.value.nodes.map(n => ({
    ...n,
    diffStatus: n.status
  }))
})

const getNodeStatus = (nodeId) => {
  if (!diffResult.value) return 'unchanged'
  const node = diffResult.value.nodes.find(n => n.id === nodeId)
  return node?.status || 'unchanged'
}

const getNodeStyle = (node) => {
  return {
    left: `${(node.position?.x || 0) / 5}px`,
    top: `${(node.position?.y || 0) / 5}px`
  }
}

const getStatusTagType = (status) => {
  const types = { added: 'success', removed: 'danger', modified: 'warning', unchanged: 'info' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { added: '新增', removed: '删除', modified: '修改', unchanged: '未变' }
  return labels[status] || status
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

const formatJson = (obj) => {
  return JSON.stringify(obj, null, 2)
}

const copyDiff = () => {
  navigator.clipboard.writeText(formatJson(diffResult.value))
  appStore.success('差异已复制到剪贴板')
}

const mergeChanges = () => {
  ElMessageBox.confirm('确定要将 B 的变更合并到 A？此操作将覆盖工作流 A 的所有节点和连线。', '确认合并', {
    confirmButtonText: '确定合并',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await updateWorkflow(workflowA.value, {
        nodes: workflowBData.value.nodes,
        edges: workflowBData.value.edges
      })
      appStore.success('合并成功')
    } catch (e) {
      appStore.error('合并失败')
    }
  }).catch(() => {})
}

onMounted(async () => {
  await Promise.all([searchWorkflowsA(''), searchWorkflowsB('')])

  const queryA = route.query.a || route.query.workflowA
  const queryB = route.query.b || route.query.workflowB

  if (queryA && queryB) {
    workflowA.value = String(queryA)
    workflowB.value = String(queryB)
    await loadWorkflowA(workflowA.value)
    await loadWorkflowB(workflowB.value)
    compareWorkflows()
    return
  }

  const candidates = workflowListA.value.filter(item => item?.id)
  if (candidates.length >= 2 && route.query.auto === '1') {
    workflowA.value = candidates[0].id
    workflowB.value = candidates[1].id
    await loadWorkflowA(workflowA.value)
    await loadWorkflowB(workflowB.value)
    compareWorkflows()
  }
})
</script>

<style lang="scss" scoped>

.selection-card {
  margin-bottom: 24px;

  .selection-row {
    display: flex;
    align-items: flex-end;
    gap: 16px;

    .selection-item {
      flex: 1;

      label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
      }
    }

    .vs-badge {
      padding: 8px 16px;
      background: var(--el-fill-color);
      border-radius: 20px;
      font-weight: 600;
      color: var(--el-text-color-secondary);
    }
  }
}

.workflow-option {
  display: flex;
  align-items: center;
  gap: 8px;

  .wf-icon {
    width: 16px;
    height: 16px;
  }

  .wf-date {
    margin-left: auto;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-icon-small {
  width: 14px;
  height: 14px;
}

.summary-card {
  margin-bottom: 24px;

  .summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    h3 {
      margin: 0;
    }
  }

  .summary-stats {
    display: flex;
    gap: 32px;
    margin-top: 16px;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 8px;

    .stat-icon {
      width: 20px;
      height: 20px;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 700;
    }

    .stat-label {
      color: var(--el-text-color-secondary);
    }

    &.added {
      .stat-icon { color: var(--el-color-success); }
      .stat-value { color: var(--el-color-success); }
    }

    &.removed {
      .stat-icon { color: var(--el-color-danger); }
      .stat-value { color: var(--el-color-danger); }
    }

    &.modified {
      .stat-icon { color: var(--el-color-warning); }
      .stat-value { color: var(--el-color-warning); }
    }
  }
}

.visual-diff-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.side-by-side {
  display: flex;
  gap: 16px;

  .diff-panel {
    flex: 1;
    border: 1px solid var(--el-border-color);
    border-radius: 8px;
    overflow: hidden;

    .panel-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: var(--el-fill-color-light);

      .panel-label {
        padding: 2px 8px;
        background: var(--el-color-primary);
        color: white;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
      }

      .panel-name {
        font-weight: 500;
      }
    }

    .panel-canvas {
      height: 200px;
      overflow: auto;
    }
  }

  .diff-divider {
    width: 2px;
    background: var(--el-border-color);
  }
}

.mini-canvas {
  position: relative;
  min-height: 100%;
  padding: 20px;

  .mini-node {
    position: absolute;
    padding: 6px 12px;
    background: var(--el-fill-color);
    border-radius: 4px;
    font-size: 11px;
    white-space: nowrap;

    &.added { background: var(--success-bg); border: 1px solid var(--success); }
    &.removed { background: var(--error-bg); border: 1px solid var(--error); }
    &.modified { background: var(--warning-bg); border: 1px solid var(--warning); }
  }
}

.unified-view {
  .diff-legend {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;

    .legend-item {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;

      &.added { background: var(--success-bg); color: var(--success); }
      &.removed { background: var(--error-bg); color: var(--error); }
      &.modified { background: var(--warning-bg); color: var(--warning); }
      &.unchanged { background: var(--el-fill-color); }
    }
  }
}

.node-diff-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  background: var(--el-fill-color-light);

  &.added { background: var(--success-bg); border-left: 3px solid var(--success); }
  &.removed { background: var(--error-bg); border-left: 3px solid var(--error); }
  &.modified { background: var(--warning-bg); border-left: 3px solid var(--warning); }

  .node-header {
    display: flex;
    align-items: center;
    gap: 8px;

    .node-status-icon {
      .icon {
        width: 16px;
        height: 16px;
        &.added { color: var(--el-color-success); }
        &.removed { color: var(--el-color-danger); }
        &.modified { color: var(--el-color-warning); }
        &.unchanged { color: var(--el-text-color-secondary); }
      }
    }

    .node-type {
      padding: 2px 6px;
      background: var(--el-fill-color);
      border-radius: 4px;
      font-size: 12px;
    }

    .node-label {
      flex: 1;
      font-weight: 500;
    }
  }

  .node-changes {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--el-border-color-light);

    .change-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .change-field {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }

      .change-values {
        display: flex;
        align-items: center;
        gap: 8px;

        code {
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 12px;
          font-family: 'JetBrains Mono', monospace;
        }

        .old-value {
          background: var(--error-bg);
          color: var(--error);
        }

        .new-value {
          background: var(--success-bg);
          color: var(--success);
        }

        .arrow-icon {
          width: 14px;
          height: 14px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
}

.diff-table {
  code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }

  .change-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;

    .change-tag {
      padding: 2px 6px;
      background: var(--el-fill-color);
      border-radius: 4px;
      font-size: 11px;
    }
  }

  .no-change {
    color: var(--el-text-color-secondary);
  }
}

.json-diff {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  padding: 16px;
  overflow: auto;

  pre {
    margin: 0;
    color: var(--code-text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--el-text-color-secondary);
    opacity: 0.5;
    margin-bottom: 16px;
  }

  h3 {
    margin: 0 0 8px;
  }

  p {
    margin: 0;
    color: var(--el-text-color-secondary);
  }
}
</style>
