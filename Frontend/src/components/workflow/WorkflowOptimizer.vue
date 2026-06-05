<template>
  <el-drawer
    v-model="visible"
    title="AI 工作流优化助手"
    size="580px"
    direction="rtl"
  >
    <!-- 分析触发区 -->
    <div class="optimizer-header">
      <div class="header-info">
        <Brain class="brain-icon" />
        <div>
          <h4>智能优化建议</h4>
          <p>基于 AI 分析当前工作流，提供性能、错误处理、可维护性等方面的优化建议</p>
        </div>
      </div>
      <el-button 
        type="primary" 
        :loading="analyzing"
        :disabled="analyzing"
        @click="analyzeWorkflow"
      >
        <Sparkles
          v-if="!analyzing"
          class="icon"
        />
        {{ analyzing ? '分析中...' : '开始分析' }}
      </el-button>
    </div>

    <!-- 分析维度选择 -->
    <div
      v-if="!analyzing && suggestions.length === 0"
      class="dimension-select"
    >
      <p class="dimension-hint">
        选择要分析的维度（默认全选）
      </p>
      <el-checkbox-group
        v-model="selectedDimensions"
        class="dimension-group"
      >
        <el-checkbox value="performance">
          <div class="dimension-item">
            <Zap class="dim-icon performance" />
            <div>
              <span class="dim-label">执行效率</span>
              <span class="dim-desc">并行化、超时设置、缓存策略</span>
            </div>
          </div>
        </el-checkbox>
        <el-checkbox value="error_handling">
          <div class="dimension-item">
            <Shield class="dim-icon error_handling" />
            <div>
              <span class="dim-label">错误处理</span>
              <span class="dim-desc">缺失的异常处理、死循环保护</span>
            </div>
          </div>
        </el-checkbox>
        <el-checkbox value="maintainability">
          <div class="dimension-item">
            <Code class="dim-icon maintainability" />
            <div>
              <span class="dim-label">可维护性</span>
              <span class="dim-desc">节点命名、注释、结构优化</span>
            </div>
          </div>
        </el-checkbox>
        <el-checkbox value="cost">
          <div class="dimension-item">
            <DollarSign class="dim-icon cost" />
            <div>
              <span class="dim-label">成本优化</span>
              <span class="dim-desc">LLM 调用次数、token 消耗</span>
            </div>
          </div>
        </el-checkbox>
        <el-checkbox value="security">
          <div class="dimension-item">
            <Lock class="dim-icon security" />
            <div>
              <span class="dim-label">安全性</span>
              <span class="dim-desc">敏感数据处理、凭证管理</span>
            </div>
          </div>
        </el-checkbox>
      </el-checkbox-group>
    </div>

    <!-- 加载状态 -->
    <div
      v-if="analyzing"
      class="analyzing-state"
    >
      <div class="analyzing-animation">
        <div class="pulse-ring" />
        <Brain class="brain-pulse" />
      </div>
      <p class="analyzing-text">
        正在分析工作流...
      </p>
      <p class="analyzing-sub">
        正在检查 {{ currentCheck }} / {{ totalChecks }}
      </p>
      <el-skeleton
        :rows="3"
        animated
      />
    </div>

    <!-- 建议列表 -->
    <div
      v-if="!analyzing && suggestions.length > 0"
      class="suggestions-container"
    >
      <!-- 统计概览 -->
      <div class="suggestion-stats">
        <div class="stats-grid">
          <div class="stat-item">
            <el-tag type="danger">
              {{ criticalCount }} 严重
            </el-tag>
          </div>
          <div class="stat-item">
            <el-tag type="warning">
              {{ warningCount }} 警告
            </el-tag>
          </div>
          <div class="stat-item">
            <el-tag type="info">
              {{ infoCount }} 建议
            </el-tag>
          </div>
          <div class="stat-item">
            <el-tag type="success">
              {{ autoApplicableCount }} 可自动修复
            </el-tag>
          </div>
        </div>
        <el-tooltip
          content="重新分析工作流"
          placement="bottom"
        >
          <el-button
            size="small"
            @click="reAnalyze"
          >
            <RefreshCw class="icon-sm" /> 重新分析
          </el-button>
        </el-tooltip>
      </div>

      <!-- 饼图 -->
      <div
        v-if="suggestions.length > 0"
        class="suggestion-chart"
      >
        <div
          ref="chartRef"
          class="pie-chart"
          style="height: 180px;"
        />
      </div>

      <!-- 建议卡片列表 -->
      <div class="suggestions-list">
        <el-card
          v-for="(suggestion, index) in suggestions"
          :key="index"
          class="suggestion-card"
          :class="suggestion.severity"
          shadow="never"
        >
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-tag 
                  size="small" 
                  :type="getSeverityTagType(suggestion.severity)"
                >
                  {{ getSeverityLabel(suggestion.severity) }}
                </el-tag>
                <el-tag
                  size="small"
                  :type="getTypeTagType(suggestion.type)"
                >
                  {{ getTypeLabel(suggestion.type) }}
                </el-tag>
              </div>
              <div class="header-actions">
                <el-tooltip content="查看受影响的节点">
                  <el-button 
                    v-if="suggestion.affectedNodes?.length > 0"
                    size="small" 
                    link
                    @click="highlightNodes(suggestion.affectedNodes)"
                  >
                    <MapPin class="icon-sm" />
                  </el-button>
                </el-tooltip>
                <el-tooltip
                  content="自动应用此优化建议"
                  placement="top"
                >
                  <el-button
                    v-if="suggestion.autoApplicable"
                    type="primary"
                    size="small"
                    link
                    @click="applySuggestion(suggestion)"
                  >
                    <Wand class="icon-sm" /> 一键应用
                  </el-button>
                </el-tooltip>
                <el-tooltip
                  content="关闭此建议"
                  placement="top"
                >
                  <el-button
                    size="small"
                    link
                    @click="dismissSuggestion(index)"
                  >
                    <X class="icon-sm" />
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </template>
          
          <div class="suggestion-content">
            <h4 class="suggestion-title">
              {{ suggestion.title }}
            </h4>
            <p class="suggestion-description">
              {{ suggestion.description }}
            </p>
            
            <div
              v-if="suggestion.expectedBenefit"
              class="benefit-tag"
            >
              <TrendingUp class="benefit-icon" />
              {{ suggestion.expectedBenefit }}
            </div>

            <!-- 修复建议详情 -->
            <el-collapse v-if="suggestion.fix">
              <el-collapse-item
                title="修复建议"
                name="fix"
              >
                <pre class="fix-code">{{ suggestion.fix }}</pre>
              </el-collapse-item>
            </el-collapse>

            <!-- 受影响节点 -->
            <div
              v-if="suggestion.affectedNodes?.length > 0"
              class="affected-nodes"
            >
              <span class="affected-label">受影响节点:</span>
              <el-tag 
                v-for="nodeId in suggestion.affectedNodes" 
                :key="nodeId"
                size="small"
                class="node-tag"
                @click="highlightNode(nodeId)"
              >
                {{ getNodeLabel(nodeId) }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-if="!analyzing && suggestions.length === 0 && hasAnalyzed"
      class="empty-suggestions"
    >
      <CheckCircle class="empty-icon success" />
      <h4>工作流状态良好</h4>
      <p>未发现需要优化的问题</p>
    </div>

    <div
      v-if="!analyzing && suggestions.length === 0 && !hasAnalyzed"
      class="empty-initial"
    >
      <Brain class="empty-icon" />
      <h4>点击上方按钮开始分析</h4>
      <p>AI 将从多个维度分析你的工作流并提供优化建议</p>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Brain, Sparkles, Zap, Shield, Code, DollarSign, Lock,
  TrendingUp, MapPin, Wand, X, RefreshCw, CheckCircle
} from 'lucide-vue-next'
import * as echarts from 'echarts'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  workflowId: {
    type: [String, Number],
    default: null
  },
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'highlight-nodes', 'apply-fix'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 分析状态
const analyzing = ref(false)
const hasAnalyzed = ref(false)
const suggestions = ref([])
const selectedDimensions = ref(['performance', 'error_handling', 'maintainability', 'cost', 'security'])
const currentCheck = ref('')
const totalChecks = ref(5)
const chartRef = ref(null)

// 统计数据
const criticalCount = computed(() => suggestions.value.filter(s => s.severity === 'critical').length)
const warningCount = computed(() => suggestions.value.filter(s => s.severity === 'warning').length)
const infoCount = computed(() => suggestions.value.filter(s => s.severity === 'info').length)
const autoApplicableCount = computed(() => suggestions.value.filter(s => s.autoApplicable).length)

// 分析进度
const checks = [
  '分析节点结构',
  '检查执行路径',
  '评估错误处理',
  '检查性能瓶颈',
  '生成优化建议'
]

async function analyzeWorkflow() {
  analyzing.value = true
  hasAnalyzed.value = true
  suggestions.value = []
  currentCheck.value = ''

  try {
    // 模拟分步分析
    for (let i = 0; i < checks.length; i++) {
      currentCheck.value = checks[i]
      await sleep(400)
    }

    // 构建工作流数据
    const workflowData = {
      nodes: props.nodes.map(n => ({
        id: n.id,
        type: n.type,
        label: n.data?.label,
        config: n.data?.config
      })),
      edges: props.edges,
      dimensions: selectedDimensions.value
    }

    // 调用后端 LLM 分析
    const result = await callOptimizerAPI(workflowData)
    suggestions.value = result.suggestions || []

    // 初始化图表
    await nextTick()
    initChart()

    if (suggestions.value.length === 0) {
      ElMessage.success('工作流分析完成，未发现问题')
    } else {
      ElMessage.success(`分析完成，发现 ${suggestions.value.length} 条建议`)
    }
  } catch (e) {
    console.error('Analysis failed:', e)
    ElMessage.error('分析失败: ' + e.message)
    // 如果 API 失败，生成 mock 建议用于演示
    suggestions.value = generateMockSuggestions()
    await nextTick()
    initChart()
  } finally {
    analyzing.value = false
    currentCheck.value = ''
  }
}

async function callOptimizerAPI(workflowData) {
  // 调用后端 API
  try {
    const { optimizeWorkflow } = await import('@/api/workflow')
    return await optimizeWorkflow(workflowData)
  } catch {
    // API 不存在时抛出错误，触发 mock 数据
    throw new Error('API not available')
  }
}

function generateMockSuggestions() {
  // Mock 数据用于演示
  return [
    {
      type: 'performance',
      severity: 'warning',
      title: 'LLM 节点未设置超时',
      description: 'LLM 节点 "AI处理" 没有配置超时时间，可能导致工作流长时间等待响应。',
      affectedNodes: ['node-2'],
      expectedBenefit: '预计减少 20% 异常响应时间',
      autoApplicable: true,
      fix: `将 LLM 节点的超时配置设置为 60 秒:
{
  "timeout": 60,
  "retryPolicy": {
    "maxRetries": 2,
    "retryDelay": 1000
  }
}`
    },
    {
      type: 'error_handling',
      severity: 'critical',
      title: '缺少错误处理分支',
      description: 'HTTP 请求节点 "获取数据" 没有配置错误处理策略，请求失败时工作流将直接终止。',
      affectedNodes: ['node-3'],
      expectedBenefit: '提高工作流健壮性',
      autoApplicable: false,
      fix: '建议添加错误处理策略，如重试机制或备用数据源。'
    },
    {
      type: 'maintainability',
      severity: 'info',
      title: '变量命名可优化',
      description: '部分变量使用了简短的命名（如 a, b, c），建议使用更描述性的名称以提高可读性。',
      affectedNodes: ['node-5', 'node-6'],
      expectedBenefit: '提高代码可读性 30%',
      autoApplicable: false
    },
    {
      type: 'cost',
      severity: 'warning',
      title: 'LLM 调用可合并',
      description: '检测到连续的 LLM 节点，可以考虑合并提示词减少 API 调用次数。',
      affectedNodes: ['node-2', 'node-4'],
      expectedBenefit: '预计节省 25% LLM 成本',
      autoApplicable: false
    }
  ]
}

function initChart() {
  if (!chartRef.value || suggestions.value.length === 0) return
  
  const chart = echarts.getInstanceByDom(chartRef.value) || echarts.init(chartRef.value)
  
  const typeCount = {}
  for (const s of suggestions.value) {
    typeCount[s.type] = (typeCount[s.type] || 0) + 1
  }
  
  const colorMap = {
    performance: '#f59e0b',
    error_handling: '#ef4444',
    maintainability: '#6366f1',
    cost: '#10b981',
    security: '#8b5cf6'
  }
  
  const option = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { 
        show: true, 
        formatter: '{b}: {c}',
        fontSize: 11
      },
      data: Object.entries(typeCount).map(([type, count]) => ({
        name: getTypeLabel(type),
        value: count,
        itemStyle: { color: colorMap[type] || '#999' }
      }))
    }]
  }
  
  chart.setOption(option)
}

function highlightNodes(nodeIds) {
  emit('highlight-nodes', nodeIds)
}

function highlightNode(nodeId) {
  emit('highlight-nodes', [nodeId])
}

function getNodeLabel(nodeId) {
  const node = props.nodes.find(n => n.id === nodeId)
  return node?.data?.label || node?.type || nodeId
}

function applySuggestion(suggestion) {
  emit('apply-fix', suggestion)
  suggestions.value = suggestions.value.filter(s => s !== suggestion)
  ElMessage.success('已应用修复建议')
}

function dismissSuggestion(index) {
  suggestions.value.splice(index, 1)
}

function reAnalyze() {
  suggestions.value = []
  analyzeWorkflow()
}

function getSeverityTagType(severity) {
  return { critical: 'danger', warning: 'warning', info: 'info' }[severity] || 'info'
}

function getSeverityLabel(severity) {
  return { critical: '严重', warning: '警告', info: '建议' }[severity] || severity
}

function getTypeTagType(type) {
  return { performance: 'warning', error_handling: 'danger', maintainability: '', cost: 'success', security: 'info' }[type] || ''
}

function getTypeLabel(type) {
  return {
    performance: '性能',
    error_handling: '错误处理',
    maintainability: '可维护性',
    cost: '成本',
    security: '安全'
  }[type] || type
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// 图表 resize
watch(visible, (val) => {
  if (val) {
    nextTick(() => {
      if (chartRef.value && suggestions.value.length > 0) {
        const chart = echarts.getInstanceByDom(chartRef.value)
        chart?.resize()
      }
    })
  }
})
</script>

<style lang="scss" scoped>
.optimizer-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  margin-bottom: 16px;

  .header-info {
    display: flex;
    gap: 12px;
    color: white;

    .brain-icon {
      width: 40px;
      height: 40px;
      flex-shrink: 0;
    }

    h4 {
      margin: 0 0 4px;
      font-size: 16px;
    }

    p {
      margin: 0;
      font-size: 12px;
      opacity: 0.8;
    }
  }
}

.dimension-select {
  padding: 0 16px 16px;

  .dimension-hint {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    margin-bottom: 12px;
  }

  .dimension-group {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .dimension-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px;
      border-radius: 6px;
      cursor: pointer;

      &:hover {
        background: var(--el-fill-color-light);
      }

      .dim-icon {
        width: 20px;
        height: 20px;
        flex-shrink: 0;

        &.performance { color: #f59e0b; }
        &.error_handling { color: #ef4444; }
        &.maintainability { color: #6366f1; }
        &.cost { color: #10b981; }
        &.security { color: #8b5cf6; }
      }

      .dim-label {
        display: block;
        font-weight: 500;
        font-size: 13px;
      }

      .dim-desc {
        display: block;
        font-size: 11px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.analyzing-state {
  padding: 40px 16px;
  text-align: center;

  .analyzing-animation {
    position: relative;
    width: 80px;
    height: 80px;
    margin: 0 auto 20px;

    .pulse-ring {
      position: absolute;
      inset: 0;
      border: 3px solid var(--el-color-primary);
      border-radius: 50%;
      animation: pulse-ring 1.5s ease-out infinite;
    }

    .brain-pulse {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 40px;
      height: 40px;
      color: var(--el-color-primary);
    }
  }

  .analyzing-text {
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 4px;
  }

  .analyzing-sub {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(1.4); opacity: 0; }
}

.suggestions-container {
  .suggestion-stats {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px 12px;

    .stats-grid {
      display: flex;
      gap: 8px;
    }
  }

  .suggestion-chart {
    padding: 0 16px 16px;
  }

  .suggestions-list {
    padding: 0 16px 16px;
    max-height: calc(100vh - 400px);
    overflow-y: auto;
  }
}

.suggestion-card {
  margin-bottom: 12px;
  border-left: 3px solid;

  &.critical { border-left-color: var(--el-color-danger); }
  &.warning { border-left-color: var(--el-color-warning); }
  &.info { border-left-color: var(--el-color-info); }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-left {
      display: flex;
      gap: 6px;
    }

    .header-actions {
      display: flex;
      gap: 4px;
    }
  }

  .suggestion-title {
    margin: 0 0 8px;
    font-size: 14px;
    font-weight: 600;
  }

  .suggestion-description {
    margin: 0 0 12px;
    font-size: 13px;
    color: var(--el-text-color-regular);
    line-height: 1.6;
  }

  .benefit-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
    border-radius: 12px;
    font-size: 12px;
    margin-bottom: 12px;

    .benefit-icon {
      width: 12px;
      height: 12px;
    }
  }

  .fix-code {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    white-space: pre-wrap;
    overflow-x: auto;
  }

  .affected-nodes {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 12px;

    .affected-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }

    .node-tag {
      cursor: pointer;
      &:hover {
        opacity: 0.8;
      }
    }
  }
}

.empty-suggestions, .empty-initial {
  text-align: center;
  padding: 60px 20px;

  .empty-icon {
    width: 64px;
    height: 64px;
    color: var(--el-text-color-secondary);
    opacity: 0.5;
    margin-bottom: 16px;
    &.success { color: var(--el-color-success); }
  }

  h4 { margin: 0 0 8px; }
  p { margin: 0; color: var(--el-text-color-secondary); font-size: 13px; }
}

.icon { width: 16px; height: 16px; }
.icon-sm { width: 14px; height: 14px; }
</style>
