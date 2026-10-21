<template>
  <div
    :style="{ '--node-accent': nodeColor }"
    class="domain-node web-gen-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" />
      <button
        class="action-btn"
        @click.stop="toggleExpand"
      >
        <ChevronDown
          class="action-icon"
          :class="{ rotated: isExpanded }"
        />
      </button>
    </div>

    <div class="node-name-section">
      <input
        :id="id ? `node-label-${id}` : undefined"
        v-model="localName"
        name="node-label"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div
        v-if="localConfig.websiteType || localConfig.frontendFramework"
        class="info-row"
      >
        <span class="info-label">类型</span>
        <span class="info-value">{{ localConfig.websiteType || localConfig.frontendFramework || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description, 35) }}</span>
      </div>
      <div
        v-if="localConfig.style"
        class="info-row"
      >
        <span class="info-label">风格</span>
        <span class="info-value">{{ localConfig.style }}</span>
      </div>
      <div
        class="status-bar"
        :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
      >
        <div
          v-if="isRunning"
          class="status-running"
        >
          <Loader class="status-icon spinning" />
          <span>生成中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>执行失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="browser-zone"
    >
      <div class="browser-chrome">
        <div class="browser-dots">
          <span class="dot dot-red" />
          <span class="dot dot-yellow" />
          <span class="dot dot-green" />
        </div>
        <div class="browser-url-bar">
          <Globe class="url-icon" />
          <span
            v-if="outputUrl"
            class="url-text"
          >{{ truncate(outputUrl, 25) }}</span>
          <span
            v-else-if="isRunning"
            class="url-text placeholder-url"
          >生成中...</span>
          <span
            v-else
            class="url-text placeholder-url"
          >网站预览</span>
        </div>
      </div>
      <div class="browser-content">
        <div
          v-if="isRunning"
          class="building-animation"
        >
          <div class="build-progress">
            <div class="build-bar">
              <div
                class="build-fill"
                :style="{ width: buildProgress + '%' }"
              />
            </div>
            <span class="build-label">正在构建网站...</span>
          </div>
        </div>
        <img
          v-else-if="previewImage"
          :src="previewImage"
          class="preview-screenshot"
          alt="Website preview"
        >
        <div
          v-else
          class="content-placeholder"
        >
          <Layout class="placeholder-icon" />
          <span class="placeholder-text">网站预览</span>
        </div>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">网站类型</label>
          <el-select
            v-model="localConfig.websiteType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="landing"
              label="落地页"
            />
            <el-option
              value="blog"
              label="博客"
            />
            <el-option
              value="ecommerce"
              label="电商"
            />
            <el-option
              value="portfolio"
              label="作品集"
            />
            <el-option
              value="dashboard"
              label="仪表盘"
            />
            <el-option
              value="custom"
              label="自定义"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">前端框架</label>
          <el-select
            v-model="localConfig.frontendFramework"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="react"
              label="React"
            />
            <el-option
              value="vue"
              label="Vue"
            />
            <el-option
              value="nextjs"
              label="Next.js"
            />
            <el-option
              value="nuxt"
              label="Nuxt"
            />
            <el-option
              value="html"
              label="HTML/CSS"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">设计描述</label>
          <el-input
            v-model="localConfig.description"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="描述网站的设计和功能..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">输出目录</label>
          <el-input
            v-model="localConfig.outputDir"
            size="small"
            placeholder="生成的网站输出路径"
            @change="handleChange"
          >
            <template
              v-if="isDesktop"
              #append
            >
              <el-button
                size="small"
                @click="pickOutputDir"
              >
                <FolderOpen class="btn-icon-inline" />
              </el-button>
            </template>
          </el-input>
          <p
            v-if="isDesktop"
            class="config-hint"
          >
            将写入你选择的本地文件夹
          </p>
        </div>
        <div class="config-section">
          <label class="config-label">样式</label>
          <el-select
            v-model="localConfig.style"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="modern"
              label="现代"
            />
            <el-option
              value="minimal"
              label="简约"
            />
            <el-option
              value="corporate"
              label="企业"
            />
            <el-option
              value="creative"
              label="创意"
            />
          </el-select>
        </div>
      </div>
    </Transition>

    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Globe, ChevronDown, Layout, Loader, FolderOpen } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useDesktopRuntime } from '@/composables/useDesktopRuntime'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'website_generator'
const { nodeColor } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()
const { isDesktop, selectDirectory } = useDesktopRuntime()

async function pickOutputDir() {
  const dir = await selectDirectory({ title: '选择网站生成的本地文件夹' })
  if (dir) {
    localConfig.value.outputDir = dir
    handleChange()
  }
}

const isExpanded = ref(false)

const localName = ref(props.data.label || '网站生成')
const localConfig = ref({
  websiteType: props.data.config?.websiteType || 'landing',
  frontendFramework: props.data.config?.frontendFramework || 'react',
  description: props.data.config?.description || '',
  outputDir: props.data.config?.outputDir || '',
  style: props.data.config?.style || 'modern'
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const previewImage = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  if (nodeOutput.value.screenshot) return nodeOutput.value.screenshot
  if (nodeOutput.value.preview) return nodeOutput.value.preview
  if (nodeOutput.value.url) return nodeOutput.value.url
  return null
})

const outputUrl = computed(() => {
  if (!nodeOutput.value) return null
  if (nodeOutput.value.url) return nodeOutput.value.url
  if (nodeOutput.value.outputUrl) return nodeOutput.value.outputUrl
  return null
})

const buildProgress = ref(0)
let buildInterval = null

watch(isRunning, (running) => {
  if (running) {
    buildProgress.value = 0
    buildInterval = setInterval(() => {
      buildProgress.value = Math.min(buildProgress.value + Math.random() * 15, 90)
    }, 500)
  } else {
    buildProgress.value = 100
    if (buildInterval) { clearInterval(buildInterval); buildInterval = null }
  }
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '网站生成'
    localConfig.value = { websiteType: d.config?.websiteType || 'landing', frontendFramework: d.config?.frontendFramework || 'react', description: d.config?.description || '', outputDir: d.config?.outputDir || '', style: d.config?.style || 'modern', ...d.config }
  }
}, { deep: true })

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
}

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.web-gen-node {
  &.is-running { animation: web-pulse 1.8s ease-in-out infinite; }
  &.is-completed .browser-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes web-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(139, 92, 246, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(139, 92, 246, 0); }
}

.browser-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px dashed rgba(139, 92, 246, 0.25);
  background: rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.browser-chrome {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.browser-dots {
  display: flex;
  gap: 4px;

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.dot-red { background: #ff5f57; }
    &.dot-yellow { background: #febc2e; }
    &.dot-green { background: #28c840; }
  }
}

.browser-url-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 2px 6px;
  min-width: 0;

  .url-icon { width: 10px; height: 10px; color: rgba(255, 255, 255, 0.3); flex-shrink: 0; }
  .url-text { font-size: 9px; color: rgba(255, 255, 255, 0.5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .placeholder-url { color: rgba(139, 92, 246, 0.5); }
}

.browser-content {
  height: 80px;
  overflow: hidden;
  position: relative;
}

.preview-screenshot {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.content-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: rgba(139, 92, 246, 0.05);

  .placeholder-icon { width: 24px; height: 24px; color: rgba(139, 92, 246, 0.2); }
  .placeholder-text { font-size: 9px; color: rgba(255, 255, 255, 0.2); }
}

.building-animation {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.build-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 80%;
}

.build-bar {
  width: 100%;
  height: 4px;
  background: rgba(139, 92, 246, 0.15);
  border-radius: 2px;
  overflow: hidden;
}

.build-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #a78bfa);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.build-label {
  font-size: 9px;
  color: rgba(139, 92, 246, 0.7);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.domain-node {
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, v-bind(nodeColor));
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected { box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent); transform: translateY(-2px); }
  &:hover:not(.selected) { box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent); transform: translateY(-1px); }
}

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: rgba(255, 255, 255, 0.02); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; border: 1px solid; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; .badge-icon { width: 11px; height: 11px; } }

.action-btn {
  width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;
  cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease;
  &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); }
  .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } }
}

.node-name-section { padding: 10px 12px 6px; }
.node-name-input {
  width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;
  padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e5e5e5); outline: none; transition: all 0.15s ease;
  &::placeholder { color: rgba(255, 255, 255, 0.3); }
  &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); }
}
.compact-view { padding: 0 12px 10px; display: flex; flex-direction: column; gap: 4px; }
.info-row { display: flex; align-items: center; gap: 6px; .info-label { font-size: 10px; color: rgba(255, 255, 255, 0.4); } .info-value { font-size: 11px; color: rgba(255, 255, 255, 0.7); font-family: 'JetBrains Mono', monospace; } }
.preview-row .preview-text { font-size: 10px; color: rgba(255, 255, 255, 0.6); line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
.config-hint { margin: 2px 0 0; font-size: 9px; color: rgba(255, 255, 255, 0.35); }
.btn-icon-inline { width: 14px; height: 14px; }
:deep(.el-select), :deep(.el-input), :deep(.el-input-number) { width: 100%; .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; border-radius: 6px; } .el-input__inner { color: var(--node-text, #e5e5e5) !important; font-size: 12px !important; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: rgba(10, 10, 18, 0.95); border: 2px solid v-bind(nodeColor); border-radius: 50%; &:hover { background: v-bind(nodeColor); transform: scale(1.3); } }
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #8b5cf6; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #8b5cf6; --node-text: #1e1e2e; } }
</style>
