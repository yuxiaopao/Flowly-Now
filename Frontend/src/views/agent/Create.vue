<template>
  <PageShell
    width="wide"
    class="agent-create"
  >
    <div class="page-header">
      <div class="header-left">
        <el-button
          :icon="ArrowLeft"
          @click="handleBack"
        >
          返回
        </el-button>
        <h1 class="page-title">
          {{ isEdit ? '编辑 Agent' : '创建 Agent' }}
        </h1>
      </div>
      <div class="header-actions">
        <el-button @click="handleBack">
          取消
        </el-button>
        <AppButton
          variant="primary"
          :loading="isSaving"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存更改' : '创建' }}
        </AppButton>
      </div>
    </div>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      class="agent-form"
    >
      <div class="form-grid">
        <!-- 左侧：基本信息 -->
        <div class="form-section">
          <h3 class="section-title">
            基本信息
          </h3>

          <el-form-item
            label="名称"
            prop="name"
          >
            <el-input
              v-model="form.name"
              placeholder="输入 Agent 名称"
            />
          </el-form-item>

          <el-form-item
            label="描述"
            prop="description"
          >
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="描述 Agent 的功能和用途"
            />
          </el-form-item>

          <el-form-item
            label="类型"
            prop="agent_type"
          >
            <el-select
              v-model="form.agent_type"
              placeholder="选择 Agent 类型"
            >
              <el-option
                label="对话型"
                value="conversational"
              >
                <div class="type-option">
                  <MessageCircle class="type-icon" />
                  <span>对话型 - 适用于聊天交互</span>
                </div>
              </el-option>
              <el-option
                label="任务型"
                value="task"
              >
                <div class="type-option">
                  <CheckSquare class="type-icon" />
                  <span>任务型 - 适用于完成特定任务</span>
                </div>
              </el-option>
              <el-option
                label="研究型"
                value="research"
              >
                <div class="type-option">
                  <Search class="type-icon" />
                  <span>研究型 - 适用于信息搜索和分析</span>
                </div>
              </el-option>
              <el-option
                label="编程型"
                value="coding"
              >
                <div class="type-option">
                  <Code class="type-icon" />
                  <span>编程型 - 适用于代码生成和调试</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="状态">
            <el-switch
              v-model="form.is_active"
              active-text="启用"
              inactive-text="禁用"
            />
          </el-form-item>

          <el-form-item label="所属团队">
            <el-select
              v-model="form.tenant"
              placeholder="仅个人可见（不选择团队）"
              style="width: 100%"
              clearable
            >
              <el-option
                v-for="t in tenantStore.tenants"
                :key="t.id"
                :label="t.name"
                :value="t.id"
              />
            </el-select>
            <span class="input-hint">选择团队后，该团队所有成员均可查看和使用此 Agent</span>
          </el-form-item>
        </div>

        <!-- 右侧：AI 配置 -->
        <div class="form-section">
          <h3 class="section-title">
            AI 配置
          </h3>

          <el-form-item
            label="模型"
            prop="model"
          >
            <el-select
              v-model="form.model"
              placeholder="选择 AI 模型"
              filterable
            >
              <el-option-group
                v-for="(models, provider) in agentModelOptions"
                :key="provider"
                :label="provider"
              >
                <el-option
                  v-for="opt in models"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-option-group>
            </el-select>
          </el-form-item>

          <el-form-item label="温度参数">
            <div class="slider-container">
              <el-slider
                v-model="form.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                :marks="temperatureMarks"
              />
              <span class="slider-value">{{ form.temperature }}</span>
            </div>
            <div class="slider-hints">
              <span>精确</span>
              <span>创意</span>
            </div>
          </el-form-item>

          <el-form-item label="最大 Token 数">
            <el-input-number
              v-model="form.max_tokens"
              :min="100"
              :max="32000"
              :step="100"
            />
          </el-form-item>

          <el-form-item label="上下文窗口">
            <el-input-number
              v-model="form.context_window"
              :min="1"
              :max="50"
              :step="1"
            />
            <span class="input-hint">保留最近的对话轮数</span>
          </el-form-item>
        </div>
      </div>

      <!-- 系统提示词 -->
      <div class="form-section full-width">
        <h3 class="section-title">
          系统提示词
        </h3>
        <el-form-item prop="system_prompt">
          <el-input
            v-model="form.system_prompt"
            type="textarea"
            :rows="6"
            placeholder="定义 Agent 的角色和行为。例如：你是一个专业的客服助手，可以帮助用户解决产品相关的问题..."
          />
        </el-form-item>
        <div class="prompt-tips">
          <el-alert
            title="提示"
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              <p>系统提示词定义了 Agent 的角色定位和回复风格。建议包含：</p>
              <ul>
                <li>Agent 的身份和职责</li>
                <li>Agent 的能力和限制</li>
                <li>回复的风格和格式</li>
              </ul>
            </template>
          </el-alert>
        </div>
      </div>

      <!-- 工具配置 -->
      <div class="form-section full-width">
        <h3 class="section-title">
          工具配置
        </h3>

        <div class="tools-grid">
          <div
            v-for="tool in availableTools"
            :key="tool.id"
            :class="['tool-card', { selected: isToolSelected(tool.id) }]"
            @click="toggleTool(tool.id)"
          >
            <div class="tool-header">
              <component
                :is="getToolIcon(tool.id)"
                class="tool-icon"
              />
              <el-checkbox
                :model-value="isToolSelected(tool.id)"
                @click.stop
                @change="toggleTool(tool.id)"
              />
            </div>
            <h4 class="tool-name">
              {{ tool.name }}
            </h4>
            <p class="tool-desc">
              {{ tool.description }}
            </p>
          </div>
        </div>
      </div>

      <!-- 知识库关联 -->
      <div
        v-if="isToolSelected('knowledge_base')"
        class="form-section full-width"
      >
        <h3 class="section-title">
          关联知识库
        </h3>
        <el-form-item>
          <el-select
            v-model="form.knowledge_collections"
            multiple
            filterable
            placeholder="选择该 Agent 可检索的知识库集合"
            style="width: 100%"
          >
            <el-option
              v-for="c in availableCollections"
              :key="c.id"
              :label="c.tenant_name ? `${c.name}（团队: ${c.tenant_name}）` : `${c.name}（个人）`"
              :value="c.id"
            />
          </el-select>
          <div
            v-if="!availableCollections.length"
            class="input-hint"
          >
            暂无可用知识库，请先前往「知识库」页面创建文档集合
          </div>
          <div
            v-else
            class="input-hint"
          >
            已启用「知识库检索」工具，Agent 会在回答时自动检索所选集合中的相关内容
          </div>
        </el-form-item>
      </div>
    </el-form>
  </PageShell>
</template>

<script setup>
import PageShell from '@/components/layout/PageShell.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useAppStore } from '@/stores/app'
import { useWorkflowStore } from '@/stores/workflow'
import { useRAGStore } from '@/stores/rag'
import { useTenantStore } from '@/stores/tenant'
import { agentApi } from '@/api/agent'
import { APP_CONFIG } from '@/config'
import {
  ArrowLeft, MessageCircle, CheckSquare, Search, Code,
  Calculator, Globe, Terminal, Cloud, FileJson, Clock, BookOpen
} from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()
const appStore = useAppStore()
const workflowStore = useWorkflowStore()
const ragStore = useRAGStore()
const tenantStore = useTenantStore()

const formRef = ref(null)
const isSaving = computed(() => agentStore.isSaving)

const agentId = computed(() => route.params.id)
const isEdit = computed(() => !!agentId.value && agentId.value !== 'new')

const form = reactive({
  name: '',
  description: '',
  agent_type: 'conversational',
  is_active: true,
  tenant: null,
  model: APP_CONFIG.llm.defaultModel,
  temperature: 0.7,
  max_tokens: 2000,
  context_window: 10,
  system_prompt: '',
  tools: [],
  skills: [],
  knowledge_collections: []
})

const rules = {
  name: [
    { required: true, message: '请输入 Agent 名称', trigger: 'blur' }
  ],
  agent_type: [
    { required: true, message: '请选择 Agent 类型', trigger: 'change' }
  ],
  model: [
    { required: true, message: '请选择 AI 模型', trigger: 'change' }
  ]
}

const temperatureMarks = {
  0: '0',
  0.5: '0.5',
  1: '1',
  1.5: '1.5',
  2: '2'
}

const availableTools = ref([])
const availableCollections = computed(() => ragStore.collections)

const TOOL_DISPLAY_META = {
  calculator: { name: '计算器', icon: Calculator, description: '数学计算和表达式求值' },
  search: { name: '网络搜索', icon: Search, description: '搜索互联网信息' },
  weather: { name: '天气查询', icon: Cloud, description: '查询指定城市的天气信息' },
  web_scraper: { name: '网页抓取', icon: Globe, description: '抓取并提取网页正文内容' },
  text_template: { name: '文本模板', icon: FileJson, description: '按模板生成结构化文本' },
  json_parser: { name: 'JSON 解析', icon: Code, description: '解析和处理 JSON 数据' },
  datetime: { name: '日期时间', icon: Clock, description: '获取和计算日期时间' },
  knowledge_base: { name: '知识库检索', icon: BookOpen, description: '检索团队/个人知识库中的相关内容作答' }
}

async function loadAvailableTools() {
  try {
    const types = await agentApi.getAvailableToolTypes()
    availableTools.value = (types || []).map((t) => ({
      id: t.name,
      name: TOOL_DISPLAY_META[t.name]?.name || t.name,
      description: TOOL_DISPLAY_META[t.name]?.description || t.description || '',
      icon: TOOL_DISPLAY_META[t.name]?.icon || Terminal
    }))
  } catch (err) {
    appStore.error('加载工具列表失败')
  }
}

const agentModelOptions = computed(() => {
  const models = workflowStore.availableModels
  if (models && models.length > 0) {
    const grouped = {}
    models.forEach(m => {
      const provider = m.provider || 'Unknown'
      if (!grouped[provider]) grouped[provider] = []
      grouped[provider].push({
        value: m.modelId || m.model_id || m.id,
        label: m.name,
      })
    })
    return grouped
  }
  return { '加载中': [{ value: '', label: '正在加载模型列表...'}] }
})

onMounted(async () => {
  workflowStore.fetchAvailableModels({ type: 'chat' })
  await Promise.all([
    loadAvailableTools(),
    ragStore.fetchCollections(),
    tenantStore.fetchTenants()
  ])
  if (isEdit.value) {
    try {
      await agentStore.fetchAgent(agentId.value)
      const agent = agentStore.currentAgent
      if (agent) {
        form.name = agent.name || ''
        form.description = agent.description || ''
        form.agent_type = agent.agent_type || 'conversational'
        form.is_active = agent.is_active ?? true
        form.tenant = agent.tenant || null
        form.model = agent.model || ''
        form.temperature = agent.temperature || 0.7
        form.max_tokens = agent.max_tokens || 2000
        form.context_window = agent.context_window || 10
        form.system_prompt = agent.system_prompt || ''
        form.tools = agent.tools || []
        form.skills = agent.skills || []
        form.knowledge_collections = agent.knowledge_collections || []
      }
    } catch (err) {
      appStore.error('加载 Agent 失败')
    }
  }
})

function isToolSelected(toolId) {
  return form.tools.includes(toolId)
}

function toggleTool(toolId) {
  const index = form.tools.indexOf(toolId)
  if (index === -1) {
    form.tools.push(toolId)
  } else {
    form.tools.splice(index, 1)
  }
}

function getToolIcon(toolId) {
  return availableTools.value.find((t) => t.id === toolId)?.icon || Terminal
}

function handleBack() {
  router.push('/agents')
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    const data = { ...form }

    if (isEdit.value) {
      await agentStore.updateAgent(agentId.value, data)
      appStore.success('Agent 已更新')
    } else {
      const result = await agentStore.createAgent(data)
      appStore.success('Agent 创建成功')
      router.replace(`/agents/${result.id}/edit`)
    }
  } catch (err) {
    appStore.error(isEdit.value ? '更新失败' : '创建失败')
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.agent-create {
  min-height: calc(100vh - #{$header-height} - #{$spacing-12});
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-4;
}

.page-title {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: $spacing-3;
}

.agent-form {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-6;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-8;
}

.form-section {
  &.full-width {
    grid-column: 1 / -1;
    margin-top: $spacing-4;
  }
}

.section-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-4;
  padding-bottom: $spacing-2;
  border-bottom: 1px solid var(--border-primary);
}

.type-option {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.type-icon {
  width: 18px;
  height: 18px;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: $spacing-4;

  .el-slider {
    flex: 1;
  }
}

.slider-value {
  min-width: 40px;
  text-align: center;
  font-weight: $font-weight-medium;
}

.slider-hints {
  display: flex;
  justify-content: space-between;
  font-size: $font-size-xs;
    color: var(--text-tertiary);
  margin-top: $spacing-1;
}

.input-hint {
  display: block;
  font-size: $font-size-xs;
    color: var(--text-tertiary);
  margin-top: $spacing-1;
}

.prompt-tips {
  margin-top: $spacing-4;

  p {
    margin: $spacing-2 0;
  }

  ul {
    margin: $spacing-2 0;
    padding-left: $spacing-4;
  }

  li {
    margin: $spacing-1 0;
  }
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: $spacing-4;
}

.tool-card {
  padding: $spacing-4;
  background-color: var(--bg-tertiary);
  border: 2px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: var(--accent-primary);
  }

  &.selected {
    border-color: $color-primary;
    background-color: rgba($color-primary, 0.1);
  }
}

.tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-3;
}

.tool-icon {
  width: 24px;
  height: 24px;
  color: $color-primary;
}

.tool-name {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  margin: 0 0 $spacing-1;
}

.tool-desc {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin: 0;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

