<template>
  <div class="node-panel">
    <div class="panel-header">
      <h3>节点组件</h3>
      <span class="node-count">{{ totalNodeCount }} 个节点</span>
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

      <!-- 分类列表 -->
      <div
        v-for="category in filteredCategories"
        :key="category.name"
        class="node-category"
      >
        <div
          class="category-header"
          :class="{ disabled: category.nodes.length === 0 }"
          @click="toggleCategory(category.name)"
        >
          <component
            :is="category.icon"
            class="category-icon"
            :style="{ color: category.color }"
          />
          <span class="category-name">{{ category.label }}</span>
          <span class="category-count">{{ category.nodes.length }}</span>
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
            @click="onDragStart($event, node)"
          >
            <div
              class="node-icon-wrap"
              :style="{ backgroundColor: node.bgColor }"
            >
              <component
                :is="node.icon"
                class="node-icon"
                :style="{ color: node.color }"
              />
            </div>
            <div class="node-info">
              <span class="node-label">{{ node.label }}</span>
              <span class="node-desc">{{ node.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部快捷键 -->
    <div class="panel-footer">
      <div class="shortcut-hints">
        <div class="shortcut-hint">
          <kbd>Ctrl</kbd>+<kbd>Z</kbd> 撤销
        </div>
        <div class="shortcut-hint">
          <kbd>Ctrl</kbd>+<kbd>Y</kbd> 重做
        </div>
        <div class="shortcut-hint">
          <kbd>Del</kbd> 删除选中
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Search, ArrowDown,
  PlayCircle, Circle, Zap, MessageSquare,
  GitBranch, Hammer, FileText, User, Webhook, Code, Key,
  BookOpen, Database, Cloud, Shield, RefreshCw, Brain,
  Image, Video, Volume2
} from 'lucide-vue-next'

const ImageIcon = Image
const VideoIcon = Video
const AudioIcon = Volume2

const emit = defineEmits(['drag-start'])

const searchQuery = ref('')
const expandedCategories = ref(['trigger', 'ai', 'control'])

const categories = [
  // ─── 触发器 ───
  {
    name: 'trigger',
    label: '触发器',
    icon: PlayCircle,
    color: '#10b981',
    nodes: [
      { type: 'start', label: '开始', icon: PlayCircle, color: '#10b981', bgColor: 'rgba(16,185,129,0.1)', description: '工作流入口，自动开始执行' },
      { type: 'end', label: '结束', icon: Circle, color: '#ef4444', bgColor: 'rgba(239,68,68,0.1)', description: '工作流出口，标记流程结束' },
      { type: 'manual', label: '手动触发', icon: PlayCircle, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '手动点击执行一次' },
      { type: 'schedule', label: '定时触发', icon: RefreshCw, color: '#06b6d4', bgColor: 'rgba(6,182,212,0.1)', description: '按 Cron 表达式定时执行' },
      { type: 'webhook', label: 'Webhook', icon: Webhook, color: '#3b82f6', bgColor: 'rgba(59,130,246,0.1)', description: '接收外部 HTTP 请求触发' },
      { type: 'form', label: '表单触发', icon: FileText, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '用户提交表单时触发' },
    ]
  },
  // ─── AI ───
  {
    name: 'ai',
    label: 'AI 模型',
    icon: Zap,
    color: '#3b82f6',
    nodes: [
      { type: 'llm', label: '大语言模型', icon: Zap, color: '#3b82f6', bgColor: 'rgba(59,130,246,0.1)', description: '调用 GPT/Claude/DeepSeek 等 LLM' },
      { type: 'prompt', label: '提示词', icon: MessageSquare, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '格式化提示词模板' },
      { type: 'agent', label: 'AI Agent', icon: User, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '自主规划执行的多步骤 AI Agent' },
      { type: 'planner', label: '规划器', icon: BookOpen, color: '#06b6d4', bgColor: 'rgba(6,182,212,0.1)', description: '将复杂任务拆解为步骤' },
      { type: 'executor', label: '执行器', icon: Hammer, color: '#f97316', bgColor: 'rgba(249,115,22,0.1)', description: '执行规划器分解的具体任务' },
      { type: 'memory', label: '记忆', icon: Database, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: '存储和检索对话上下文' },
    ]
  },
  // ─── 控制流 ───
  {
    name: 'control',
    label: '控制流',
    icon: GitBranch,
    color: '#3b82f6',
    nodes: [
      { type: 'condition', label: '条件判断', icon: GitBranch, color: '#3b82f6', bgColor: 'rgba(59,130,246,0.1)', description: '根据条件分流执行路径' },
      { type: 'switch', label: '分支选择', icon: GitBranch, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '多条件分支路由' },
      { type: 'loop', label: '循环', icon: RefreshCw, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '遍历数组重复执行' },
      { type: 'delay', label: '延时', icon: RefreshCw, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: '等待指定时间后继续' },
      { type: 'merge', label: '合并', icon: GitBranch, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: '合并多个分支路径' },
      { type: 'split', label: '拆分', icon: GitBranch, color: '#ec4899', bgColor: 'rgba(236,72,153,0.1)', description: '将批量数据拆分并行处理' },
      { type: 'filter', label: '过滤器', icon: Shield, color: '#f97316', bgColor: 'rgba(249,115,22,0.1)', description: '按条件过滤数据项' },
    ]
  },
  // ─── 数据处理 ───
  {
    name: 'data',
    label: '数据处理',
    icon: FileText,
    color: '#22c55e',
    nodes: [
      { type: 'input', label: '输入', icon: FileText, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: '接收用户输入数据' },
      { type: 'output', label: '输出', icon: User, color: '#84cc16', bgColor: 'rgba(132,204,22,0.1)', description: '返回结果给用户' },
      { type: 'variable', label: '变量', icon: Key, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: '变量赋值、读取、修改变量' },
      { type: 'code', label: '代码执行', icon: Code, color: '#f97316', bgColor: 'rgba(249,115,22,0.1)', description: '执行 Python / JavaScript 代码' },
      { type: 'transform', label: '数据转换', icon: RefreshCw, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '转换数据结构格式' },
      { type: 'csv_transform', label: 'CSV 处理', icon: FileText, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: 'CSV 解析、转换、生成' },
      { type: 'json_transform', label: 'JSON 处理', icon: Code, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: 'JSON 解析、构建、转换' },
      { type: 'set', label: '变量赋值', icon: Key, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: 'Set 节点，快速修改变量' },
    ]
  },
  // ─── HTTP 与 API ───
  {
    name: 'http',
    label: 'HTTP 与 API',
    icon: Webhook,
    color: '#f97316',
    nodes: [
      { type: 'http', label: 'HTTP 请求', icon: Webhook, color: '#f97316', bgColor: 'rgba(249,115,22,0.1)', description: '发送 GET/POST/PUT/DELETE 请求' },
      { type: 'web_scraper', label: '网页抓取', icon: BookOpen, color: '#f97316', bgColor: 'rgba(249,115,22,0.1)', description: '抓取网页内容并解析' },
      { type: 'file_reader', label: '文件读取', icon: FileText, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: '读取本地/云端文件' },
      { type: 'file_writer', label: '文件写入', icon: FileText, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: '写入数据到文件' },
      { type: 'document_loader', label: '文档加载', icon: BookOpen, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '加载 PDF/Word/Excel 文档' },
      { type: 'subworkflow', label: '子工作流', icon: GitBranch, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '调用另一个工作流' },
    ]
  },
  // ─── RAG 与检索 ───
  {
    name: 'rag',
    label: 'RAG 与检索',
    icon: Database,
    color: '#06b6d4',
    nodes: [
      { type: 'embedding', label: 'Embedding', icon: Database, color: '#06b6d4', bgColor: 'rgba(6,182,212,0.1)', description: '生成文本向量嵌入' },
      { type: 'vector_store', label: '向量数据库', icon: Database, color: '#3b82f6', bgColor: 'rgba(59,130,246,0.1)', description: '存储和检索向量' },
      { type: 'retriever', label: '检索器', icon: Search, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: '向量相似度检索' },
      { type: 'reranker', label: '重排序', icon: Shield, color: '#ec4899', bgColor: 'rgba(236,72,153,0.1)', description: '对检索结果重新排序' },
    ]
  },
  // ─── 通信 ───
  {
    name: 'communication',
    label: '通信',
    icon: MessageSquare,
    color: '#ec4899',
    nodes: [
      { type: 'email', label: '邮件', icon: MessageSquare, color: '#ec4899', bgColor: 'rgba(236,72,153,0.1)', description: '发送 HTML / 文本邮件' },
      { type: 'slack', label: 'Slack', icon: MessageSquare, color: '#4a154b', bgColor: 'rgba(74,21,75,0.1)', description: '发送 Slack 消息/频道通知' },
      { type: 'discord', label: 'Discord', icon: MessageSquare, color: '#5865f2', bgColor: 'rgba(88,101,242,0.1)', description: '发送 Discord Webhook 消息' },
      { type: 'twilio', label: 'Twilio', icon: MessageSquare, color: '#f22f46', bgColor: 'rgba(242,47,70,0.1)', description: '发送 SMS 短信' },
      { type: 'notification', label: '通知', icon: Zap, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '站内 / 推送通知' },
    ]
  },
  // ─── 工具 ───
  {
    name: 'tools',
    label: '工具',
    icon: Hammer,
    color: '#ec4899',
    nodes: [
      { type: 'tool', label: '工具调用', icon: Hammer, color: '#ec4899', bgColor: 'rgba(236,72,153,0.1)', description: '调用内置或自定义工具' },
      { type: 'datetime', label: '日期时间', icon: RefreshCw, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: '获取/格式化当前时间' },
    ]
  },
  // ─── 多模态 ───
  {
    name: 'multimodal',
    label: '多模态生成',
    icon: ImageIcon,
    color: '#ec4899',
    nodes: [
      { type: 'image_generation', label: '图像生成', icon: ImageIcon, color: '#ec4899', bgColor: 'rgba(236,72,153,0.1)', description: '生成 AI 图像（Midjourney/DALL-E/Stable Diffusion）' },
      { type: 'image_editing', label: '图像编辑', icon: ImageIcon, color: '#f97316', bgColor: 'rgba(249,115,22,0.1)', description: '局部重绘、扩图、修图' },
      { type: 'video_generation', label: '视频生成', icon: VideoIcon, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '文生视频、图生视频' },
      { type: 'audio_generation', label: '语音合成', icon: AudioIcon, color: '#06b6d4', bgColor: 'rgba(6,182,212,0.1)', description: 'TTS 文字转语音' },
      { type: 'subtitle_generation', label: '字幕生成', icon: FileText, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '从音频/视频生成字幕' },
    ]
  },
  // ─── MLOps ───
  {
    name: 'mlops',
    label: 'ML 与训练',
    icon: Database,
    color: '#ef4444',
    nodes: [
      { type: 'model_training', label: '模型训练', icon: Database, color: '#ef4444', bgColor: 'rgba(239,68,68,0.1)', description: '训练机器学习模型' },
      { type: 'yolo_training', label: 'YOLO 训练', icon: Database, color: '#ef4444', bgColor: 'rgba(239,68,68,0.1)', description: '目标检测 YOLO 模型训练' },
      { type: 'clip_classification', label: 'CLIP 分类', icon: Brain, color: '#6366f1', bgColor: 'rgba(99,102,241,0.1)', description: '零样本 / 微调 CLIP 图像分类' },
      { type: 'clip_retrieval', label: 'CLIP 检索', icon: Search, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: '图文对索引构建' },
      { type: 'model_evaluation', label: '模型评估', icon: Shield, color: '#3b82f6', bgColor: 'rgba(59,130,246,0.1)', description: '评估模型准确率/召回率' },
      { type: 'model_deployment', label: '模型部署', icon: Cloud, color: '#10b981', bgColor: 'rgba(16,185,129,0.1)', description: '部署模型为 API 服务' },
    ]
  },
  // ─── 数据集 ───
  {
    name: 'dataset',
    label: '数据集',
    icon: Database,
    color: '#22c55e',
    nodes: [
      { type: 'dataset_upload', label: '数据集上传', icon: Cloud, color: '#22c55e', bgColor: 'rgba(34,197,94,0.1)', description: '上传数据集到平台' },
      { type: 'data_annotation', label: '数据标注', icon: Shield, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: '对数据集进行人工标注' },
      { type: 'data_augmentation', label: '数据增强', icon: RefreshCw, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '对数据集进行增强扩增' },
    ]
  },
  // ─── 运营工具 ───
  {
    name: 'operations',
    label: '运营工具',
    icon: Hammer,
    color: '#8b5cf6',
    nodes: [
      { type: 'website_generator', label: '网站生成', icon: BookOpen, color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.1)', description: 'AI 生成静态网站' },
      { type: 'notification_sender', label: '消息推送', icon: Zap, color: '#f59e0b', bgColor: 'rgba(245,158,11,0.1)', description: '批量推送消息' },
      { type: 'report_generator', label: '报告生成', icon: FileText, color: '#14b8a6', bgColor: 'rgba(20,184,166,0.1)', description: '自动生成数据报告' },
    ]
  },
]

const totalNodeCount = computed(() => categories.reduce((sum, cat) => sum + cat.nodes.length, 0))

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
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  h3 {
    margin: 0;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }

  .node-count {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 10px;
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
    background-color: var(--bg-secondary);
    box-shadow: 0 0 0 1px var(--border-primary) inset;
  }
}

.node-category {
  margin-bottom: $spacing-2;
}

.category-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-2;
  cursor: pointer;
  border-radius: $radius-md;
  transition: background-color $transition-fast;

  &:hover:not(.disabled) {
    background-color: var(--bg-hover);
  }

  &.disabled {
    opacity: 0.5;
    cursor: default;
  }

  .category-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }

  .category-name {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
  }

  .category-count {
    font-size: 11px;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    padding: 1px 6px;
    border-radius: 8px;
    min-width: 20px;
    text-align: center;
  }

  .toggle-icon {
    width: 14px;
    height: 14px;
    color: var(--text-tertiary);
    transition: transform $transition-fast;

    &.expanded {
      transform: rotate(180deg);
    }
  }
}

.node-list {
  padding: $spacing-1 0 $spacing-2 $spacing-2;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-md;
  cursor: grab;
  transition: all $transition-fast;
  border: 1px solid transparent;

  &:hover {
    background-color: var(--bg-hover);
    border-color: var(--border-primary);
    transform: translateX(2px);
  }

  &:active {
    cursor: grabbing;
  }

  .node-icon-wrap {
    width: 32px;
    height: 32px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .node-icon {
    width: 16px;
    height: 16px;
  }

  .node-info {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
    flex: 1;

    .node-label {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .node-desc {
      font-size: $font-size-xs;
      color: var(--text-tertiary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.panel-footer {
  padding: $spacing-3;
  border-top: 1px solid var(--border-primary);
}

.shortcut-hints {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-2;
}

.shortcut-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  kbd {
    padding: 1px 5px;
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    font-family: 'Fira Code', monospace;
    font-size: 10px;
    color: var(--text-secondary);
  }
}
</style>



