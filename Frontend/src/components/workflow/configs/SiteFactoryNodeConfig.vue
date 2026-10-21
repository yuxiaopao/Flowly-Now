<template>
  <div class="site-factory-config">
    <el-form
      label-position="top"
      size="small"
    >
      <template v-if="nodeType === 'environment_provision'">
        <el-form-item label="运行模式">
          <el-select
            :model-value="config.runtimeMode || 'desktop'"
            @update:model-value="patch('runtimeMode', $event)"
          >
            <el-option
              label="Desktop 本地"
              value="desktop"
            />
            <el-option
              label="云端（预留）"
              value="cloud"
              disabled
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据库引擎">
          <el-select
            :model-value="config.dbEngine || 'mysql'"
            @update:model-value="patch('dbEngine', $event)"
          >
            <el-option
              label="MySQL（默认）"
              value="mysql"
            />
            <el-option
              label="SQLite（显式）"
              value="sqlite"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="要求路径授权">
          <el-switch
            :model-value="Boolean(config.requirePathGrant)"
            @update:model-value="patch('requirePathGrant', $event)"
          />
        </el-form-item>
        <el-form-item label="自定义授权路径">
          <el-input
            type="textarea"
            :rows="2"
            :model-value="customPathsText"
            placeholder="每行一个路径，或逗号分隔（数据集/权重/日志目录）"
            @update:model-value="onCustomPathsInput"
          />
          <p class="hint">
            开启「要求路径授权」后，至少需授权一个可读可写路径。
          </p>
        </el-form-item>
        <el-form-item label="MySQL Host">
          <el-input
            :model-value="mysqlConfig.host || ''"
            placeholder="127.0.0.1"
            @update:model-value="patchMysql('host', $event)"
          />
        </el-form-item>
        <el-form-item label="MySQL Port">
          <el-input-number
            :model-value="Number(mysqlConfig.port || 3306)"
            :min="1"
            :max="65535"
            @update:model-value="patchMysql('port', $event)"
          />
        </el-form-item>
        <el-form-item label="MySQL Database">
          <el-input
            :model-value="mysqlConfig.database || ''"
            placeholder="flowly_site"
            @update:model-value="patchMysql('database', $event)"
          />
        </el-form-item>
      </template>

      <template v-else-if="nodeType === 'site_qa'">
        <el-form-item label="站点类型">
          <el-select
            :model-value="config.websiteType || 'detection'"
            @update:model-value="patch('websiteType', $event)"
          >
            <el-option
              label="目标检测"
              value="detection"
            />
            <el-option
              label="分类"
              value="classification"
            />
            <el-option
              label="检索"
              value="retrieval"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="QA Profile">
          <el-select
            :model-value="config.qaProfile || 'default'"
            @update:model-value="patch('qaProfile', $event)"
          >
            <el-option
              label="默认（严格）"
              value="default"
            />
            <el-option
              label="研究（允许黄灯预览）"
              value="research"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="跳过 Playwright">
          <el-switch
            :model-value="Boolean(config.skipPlaywright)"
            @update:model-value="patch('skipPlaywright', $event)"
          />
        </el-form-item>
        <el-form-item label="失败自动修复">
          <el-switch
            :model-value="config.autoFix !== false"
            @update:model-value="patch('autoFix', $event)"
          />
        </el-form-item>
        <el-form-item label="自动修复轮次">
          <el-input-number
            :model-value="config.maxFixRounds || 2"
            :min="1"
            :max="5"
            :disabled="config.autoFix === false"
            @update:model-value="patch('maxFixRounds', $event)"
          />
          <p class="hint">
            红/黄灯时调用代码复查再重跑 QA。
          </p>
        </el-form-item>
      </template>

      <template v-else-if="nodeType === 'site_preview'">
        <el-form-item label="QA Profile">
          <el-select
            :model-value="config.qaProfile || 'default'"
            @update:model-value="patch('qaProfile', $event)"
          >
            <el-option
              label="默认（红灯阻断）"
              value="default"
            />
            <el-option
              label="研究（黄灯可预览）"
              value="research"
            />
          </el-select>
        </el-form-item>
        <p class="hint">
          预览 URL 来自上游 QA / 环境节点分配的端口。
        </p>
      </template>

      <template v-else-if="isRoleAgentNode">
        <el-form-item label="Agent 模式">
          <el-select
            :model-value="config.agentMode || 'auto'"
            @update:model-value="patch('agentMode', $event)"
          >
            <el-option
              label="自动（规则优先 + LLM）"
              value="auto"
            />
            <el-option
              label="仅规则"
              value="rules"
            />
            <el-option
              label="仅 LLM"
              value="llm"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="nodeType === 'backend_setup'"
          label="允许改 core 文件"
        >
          <el-switch
            :model-value="config.allowCoreEdit !== false"
            @update:model-value="patch('allowCoreEdit', $event)"
          />
        </el-form-item>
        <el-form-item
          v-if="nodeType === 'site_code_review'"
          label="最大修复轮次"
        >
          <el-input-number
            :model-value="config.maxRounds || 2"
            :min="1"
            :max="5"
            @update:model-value="patch('maxRounds', $event)"
          />
        </el-form-item>
        <el-form-item label="改码后自动 QA">
          <el-switch
            :model-value="config.autoQaAfterEdit !== false"
            @update:model-value="patch('autoQaAfterEdit', $event)"
          />
        </el-form-item>
        <el-form-item label="自定义指令">
          <el-input
            type="textarea"
            :rows="2"
            :model-value="config.instruction || ''"
            placeholder="可选：覆盖默认 Agent 任务描述"
            @update:model-value="patch('instruction', $event)"
          />
        </el-form-item>
      </template>

      <template v-else-if="nodeType === 'project_agent'">
        <el-form-item label="Agent 模式">
          <el-select
            :model-value="config.agentMode || 'auto'"
            @update:model-value="patch('agentMode', $event)"
          >
            <el-option
              label="自动（规则优先 + LLM）"
              value="auto"
            />
            <el-option
              label="仅规则"
              value="rules"
            />
            <el-option
              label="仅 LLM"
              value="llm"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="站点 ID（上游自动填充）">
          <el-input
            :model-value="config.generatedSiteId || ''"
            placeholder="website_generator 输出的 site_id"
            @update:model-value="patch('generatedSiteId', $event)"
          />
        </el-form-item>
        <el-form-item label="工作流预置消息">
          <el-input
            type="textarea"
            :rows="2"
            :model-value="config.message || ''"
            placeholder="可选：运行工作流时自动发送的修改指令"
            @update:model-value="patch('message', $event)"
          />
        </el-form-item>
        <el-form-item label="改码后自动 QA">
          <el-switch
            :model-value="config.autoQaAfterEdit !== false"
            @update:model-value="patch('autoQaAfterEdit', $event)"
          />
        </el-form-item>
        <el-form-item label="同步到系统 Agent / 知识库">
          <el-switch
            :model-value="config.syncSystemAgent !== false"
            @update:model-value="patch('syncSystemAgent', $event)"
          />
          <p class="hint">
            将对话写入系统 Agent 记忆，并绑定站点 RAG 集合。
          </p>
        </el-form-item>
        <el-form-item label="启用 Agent 记忆">
          <el-switch
            :model-value="config.agentMemoryEnabled !== false"
            @update:model-value="patch('agentMemoryEnabled', $event)"
          />
        </el-form-item>
        <el-form-item label="QA Profile">
          <el-select
            :model-value="config.qaProfile || 'default'"
            @update:model-value="patch('qaProfile', $event)"
          >
            <el-option
              label="默认（严格）"
              value="default"
            />
            <el-option
              label="研究（允许黄灯）"
              value="research"
            />
          </el-select>
        </el-form-item>
      </template>
    </el-form>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  nodeType: { type: String, required: true },
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change'])

const config = computed(() => props.modelValue || {})

const isRoleAgentNode = computed(() => (
  ['backend_setup', 'frontend_setup', 'ui_beautify', 'site_code_review'].includes(props.nodeType)
))

const mysqlConfig = computed(() => {
  const raw = config.value.mysqlConfig || config.value.mysql || {}
  return typeof raw === 'object' && raw ? raw : {}
})

const customPathsText = computed(() => {
  const paths = config.value.customPaths
  if (Array.isArray(paths)) return paths.join('\n')
  if (typeof paths === 'string') return paths
  return ''
})

function patch(key, value) {
  const next = { ...props.modelValue, [key]: value }
  emit('update:modelValue', next)
  emit('change', next)
}

function patchMysql(key, value) {
  const nextMysql = { ...mysqlConfig.value, [key]: value }
  patch('mysqlConfig', nextMysql)
}

function onCustomPathsInput(text) {
  const lines = String(text || '')
    .split(/[\n,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
  patch('customPaths', lines)
}
</script>

<style scoped>
.hint { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
</style>
