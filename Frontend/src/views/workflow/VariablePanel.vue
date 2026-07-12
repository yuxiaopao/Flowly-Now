<template>
  <el-drawer
    v-model="visible"
    title="变量管理"
    size="560px"
    direction="rtl"
    :show-close="true"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    class="variable-panel-drawer"
    :before-close="handleClose"
  >
    <el-tabs
      v-model="activeTab"
      class="variable-tabs"
    >
      <!-- 环境变量 Tab -->
      <el-tab-pane
        label="环境变量"
        name="environment"
      >
        <div class="panel-toolbar">
          <el-tooltip
            content="添加新的环境变量"
            placement="bottom"
          >
            <el-button
              type="primary"
              size="small"
              @click="addVariable('env')"
            >
              <Plus class="icon" /> 添加变量
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="从 JSON 文件导入变量"
            placement="bottom"
          >
            <el-button
              size="small"
              @click="showImportDialog = true"
            >
              <Upload class="icon" /> 导入
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="导出变量为 JSON 文件"
            placement="bottom"
          >
            <el-button
              size="small"
              @click="handleExport"
            >
              <Download class="icon" /> 导出
            </el-button>
          </el-tooltip>
        </div>

        <el-table
          :data="envVariables"
          stripe
          size="small"
          class="variable-table"
        >
          <el-table-column
            label="名称"
            width="140"
          >
            <template #default="{ row }">
              <el-input
                v-if="row._editing"
                v-model="row.name"
                size="small"
                placeholder="变量名"
                :class="{ 'is-error': row._nameError }"
                @blur="validateVarName(row)"
              />
              <span
                v-else
                class="var-name-cell"
              >{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="值"
            min-width="160"
          >
            <template #default="{ row }">
              <el-input
                v-if="row._editing"
                v-model="row.value"
                :type="row.type === 'secret' ? 'password' : 'text'"
                size="small"
                placeholder="变量值"
                show-password
              />
              <span
                v-else
                class="value-display"
              >
                {{ row.type === 'secret' ? '••••••••' : (row.value || '-') }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            label="类型"
            width="90"
          >
            <template #default="{ row }">
              <el-select
                v-if="row._editing"
                v-model="row.type"
                size="small"
              >
                <el-option
                  value="string"
                  label="字符串"
                />
                <el-option
                  value="number"
                  label="数字"
                />
                <el-option
                  value="boolean"
                  label="布尔"
                />
                <el-option
                  value="json"
                  label="JSON"
                />
                <el-option
                  value="secret"
                  label="密钥"
                />
              </el-select>
              <el-tag
                v-else
                size="small"
                :type="getTypeTagType(row.type)"
              >
                {{ row.type || 'string' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="环境"
            width="90"
          >
            <template #default="{ row }">
              <el-select
                v-if="row._editing"
                v-model="row.environment"
                size="small"
              >
                <el-option
                  value="development"
                  label="开发"
                />
                <el-option
                  value="production"
                  label="生产"
                />
                <el-option
                  value="staging"
                  label="预发"
                />
              </el-select>
              <el-tag
                v-else
                size="small"
                type="info"
              >
                {{ getEnvLabel(row.environment) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="100"
          >
            <template #default="{ row, $index }">
              <template v-if="row._editing">
                <el-button
                  size="small"
                  link
                  type="primary"
                  @click="saveVariable(row)"
                >
                  保存
                </el-button>
                <el-button
                  size="small"
                  link
                  @click="cancelEdit(row, $index)"
                >
                  取消
                </el-button>
              </template>
              <template v-else>
                <el-button
                  size="small"
                  link
                  @click="editVariable(row)"
                >
                  编辑
                </el-button>
                <el-popconfirm
                  title="确定删除？"
                  @confirm="removeVariable(row, 'env')"
                >
                  <template #reference>
                    <el-button
                      size="small"
                      link
                      type="danger"
                    >
                      删除
                    </el-button>
                  </template>
                </el-popconfirm>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="envVariables.length === 0"
          description="暂无环境变量，点击添加"
        />
      </el-tab-pane>

      <!-- 运行时变量 Tab -->
      <el-tab-pane
        label="运行时变量"
        name="runtime"
      >
        <div class="panel-toolbar">
          <el-tooltip
            content="刷新运行时变量列表"
            placement="bottom"
          >
            <el-button
              size="small"
              @click="refreshRuntime"
            >
              <RefreshCw
                class="icon"
                :class="{ 'is-loading': refreshing }"
              /> 刷新
            </el-button>
          </el-tooltip>
          <span class="runtime-hint">从节点配置自动提取</span>
        </div>

        <div
          v-if="runtimeVariables.length > 0"
          class="runtime-var-list"
        >
          <div
            v-for="v in runtimeVariables"
            :key="`${v.nodeId}-${v.name}`"
            class="runtime-var-item"
          >
            <div class="var-info">
              <el-tag
                size="small"
                :type="getSourceTagType(v.source)"
              >
                {{ getSourceLabel(v.source) }}
              </el-tag>
              <code class="var-name">{{ v.name }}</code>
            </div>
            <div class="var-meta">
              <span class="var-node">节点: {{ v.nodeName || v.nodeId }}</span>
              <span class="var-type">类型: {{ v.type }}</span>
            </div>
            <div class="var-preview">
              <span class="preview-label">值:</span>
              <code class="preview-value">{{ v.value || '(未设置)' }}</code>
            </div>
          </div>
        </div>
        <el-empty
          v-else
          description="当前工作流无运行时变量"
        >
          <template #image>
            <Variable class="empty-icon" />
          </template>
        </el-empty>
      </el-tab-pane>

      <!-- Secret 变量 Tab -->
      <el-tab-pane
        label="密钥变量"
        name="secret"
      >
        <div class="secret-info">
          <el-alert
            title="密钥安全说明"
            type="warning"
            :closable="false"
            show-icon
          >
            <template #default>
              密钥变量的值在前端不存储明文。
              它们通过加密通道传输，在需要时由后端实时获取。
              支持 API 密钥、OAuth 凭证、数据库密码等敏感数据。
            </template>
          </el-alert>
        </div>

        <div class="panel-toolbar">
          <el-tooltip
            content="添加新的密钥变量"
            placement="bottom"
          >
            <el-button
              type="primary"
              size="small"
              @click="addVariable('secret')"
            >
              <Plus class="icon" /> 添加密钥
            </el-button>
          </el-tooltip>
        </div>

        <el-table
          :data="secretVariables"
          stripe
          size="small"
          class="variable-table"
        >
          <el-table-column
            label="名称"
            prop="name"
            width="160"
          />
          <el-table-column
            label="描述"
            prop="description"
            width="140"
          >
            <template #default="{ row }">
              {{ row.description || '-' }}
            </template>
          </el-table-column>
          <el-table-column
            label="创建时间"
            prop="createdAt"
            width="140"
          >
            <template #default="{ row }">
              {{ formatDate(row.createdAt) }}
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-tooltip
                content="轮换密钥值"
                placement="top"
              >
                <el-button
                  size="small"
                  link
                  @click="handleRotateSecret(row)"
                >
                  <Key class="icon" /> 轮换
                </el-button>
              </el-tooltip>
              <el-popconfirm
                title="确定删除？"
                @confirm="removeVariable(row, 'secret')"
              >
                <template #reference>
                  <el-button
                    size="small"
                    link
                    type="danger"
                  >
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="secretVariables.length === 0"
          description="暂无密钥变量"
        >
          <template #image>
            <Key class="empty-icon" />
          </template>
        </el-empty>
      </el-tab-pane>
    </el-tabs>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入变量"
      width="500px"
      append-to-body
    >
      <el-input
        v-model="importJson"
        type="textarea"
        :rows="8"
        placeholder="粘贴 JSON 格式的变量数据，示例：
[
  {&quot;name&quot;: &quot;API_KEY&quot;, &quot;value&quot;: &quot;xxx&quot;, &quot;type&quot;: &quot;secret&quot;},
  {&quot;name&quot;: &quot;BASE_URL&quot;, &quot;value&quot;: &quot;https://api.example.com&quot;}
]"
        class="import-textarea"
      />
      <div
        v-if="importErrors.length"
        class="import-errors"
      >
        <el-alert
          type="error"
          :closable="false"
        >
          <template #title>
            导入失败 ({{ importErrors.length }} 个错误)
          </template>
          <ul>
            <li
              v-for="(err, idx) in importErrors"
              :key="idx"
            >
              {{ err }}
            </li>
          </ul>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="showImportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="importing"
          @click="handleImport"
        >
          导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑变量对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="editingVar ? '编辑变量' : '添加变量'"
      width="480px"
      append-to-body
    >
      <el-form
        :model="editForm"
        label-width="80px"
        class="edit-form"
      >
        <el-form-item
          label="变量名"
          required
        >
          <el-input
            v-model="editForm.name"
            placeholder="my_variable"
            :disabled="!!editingVar"
          />
          <div class="form-hint">
            只能包含字母、数字和下划线
          </div>
        </el-form-item>
        <el-form-item label="变量值">
          <el-input
            v-model="editForm.value"
            :type="editForm.type === 'secret' ? 'password' : 'text'"
            :placeholder="editForm.type === 'secret' ? '输入密钥值' : '输入变量值'"
            show-password
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="editForm.type"
            style="width: 100%"
          >
            <el-option
              value="string"
              label="字符串"
            />
            <el-option
              value="number"
              label="数字"
            />
            <el-option
              value="boolean"
              label="布尔"
            />
            <el-option
              value="json"
              label="JSON"
            />
            <el-option
              value="secret"
              label="密钥"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="环境">
          <el-select
            v-model="editForm.environment"
            style="width: 100%"
          >
            <el-option
              value="development"
              label="开发环境"
            />
            <el-option
              value="staging"
              label="预发环境"
            />
            <el-option
              value="production"
              label="生产环境"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="2"
            placeholder="变量描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSaveEdit"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <div class="drawer-footer">
      <el-button
        type="default"
        @click="handleClose"
      >
        关闭
      </el-button>
      <el-button
        type="primary"
        :loading="saving"
        @click="handleSaveAll"
      >
        保存全部
      </el-button>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useVariableStore } from '@/stores/variables'
import { useAppStore } from '@/stores/app'
import {
  Plus, Upload, Download, RefreshCw, Key, Variable
} from 'lucide-vue-next'

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
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const variableStore = useVariableStore()
const appStore = useAppStore()

// 双向绑定
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 状态
const activeTab = ref('environment')
const saving = ref(false)
const refreshing = ref(false)
const showImportDialog = ref(false)
const showEditDialog = ref(false)
const importing = ref(false)
const importJson = ref('')
const importErrors = ref([])
const editingVar = ref(null)

// 表单数据
const editForm = reactive({
  name: '',
  value: '',
  type: 'string',
  environment: 'development',
  description: ''
})

// 本地变量数据
const envVariables = ref([])
const secretVariables = ref([])
const runtimeVariables = ref([])

// 初始化数据
async function initData() {
  if (props.workflowId) {
    try {
      const { getVariables } = await import('@/api/variable')
      const results = await getVariables(props.workflowId)
      const list = results.results || results || []
      envVariables.value = list
        .filter(v => v.type !== 'secret')
        .map(v => ({
          ...v,
          _editing: false,
          _nameError: false,
        }))
      secretVariables.value = list
        .filter(v => v.type === 'secret')
        .map(v => ({
          ...v,
          createdAt: v.createdAt || v.created_at || new Date().toISOString(),
        }))
      refreshRuntime()
      return
    } catch (error) {
      console.error('Failed to load workflow variables:', error)
      appStore.error('加载工作流变量失败')
    }
  }

  // 从 store 加载环境变量（无 workflowId 时）
  const allVars = variableStore.allVariables
  envVariables.value = Object.entries(allVars)
    .filter(([key]) => !key.includes('_description'))
    .map(([name, value]) => ({
      name,
      value: typeof value === 'object' ? value.value : value,
      type: typeof value === 'object' ? value.type : typeof value,
      environment: typeof value === 'object' ? value.environment : 'development',
      description: typeof value === 'object' ? value.description : '',
      _editing: false,
      _nameError: false
    }))

  // 加载密钥变量
  const envEnvs = variableStore.environments
  secretVariables.value = Object.entries(envEnvs)
    .flatMap(([env, vars]) =>
      Object.entries(vars)
        .filter(([, val]) => typeof val === 'object' && val.isSecret)
        .map(([name, val]) => ({
          name,
          value: val.value,
          type: 'secret',
          environment: env,
          description: val.description || '',
          createdAt: val.createdAt || new Date().toISOString()
        }))
    )

  // 提取运行时变量
  refreshRuntime()
}

// 刷新运行时变量
function refreshRuntime() {
  refreshing.value = true
  try {
    runtimeVariables.value = variableStore.extractRuntimeVariables(props.nodes || [])
  } finally {
    refreshing.value = false
  }
}

// 监听 nodes 变化
watch(() => props.nodes, () => {
  if (activeTab.value === 'runtime') {
    refreshRuntime()
  }
}, { deep: true })

// 监听打开
watch(visible, (val) => {
  if (val) {
    initData()
  }
})

// 类型标签样式
function getTypeTagType(type) {
  const map = {
    string: 'info',
    number: 'success',
    boolean: 'warning',
    json: 'info',
    secret: 'danger'
  }
  return map[type] || 'info'
}

// 来源标签样式
function getSourceTagType(source) {
  const map = {
    input: 'primary',
    variable: 'success',
    code: 'warning',
    llm: 'info',
    prompt: '',
    http: 'danger',
    condition: 'warning'
  }
  return map[source] || 'info'
}

// 来源标签文字
function getSourceLabel(source) {
  const map = {
    input: '输入',
    variable: '变量',
    code: '代码',
    llm: 'LLM',
    prompt: '提示词',
    http: 'HTTP',
    condition: '条件'
  }
  return map[source] || source
}

// 环境标签文字
function getEnvLabel(env) {
  const map = {
    development: '开发',
    staging: '预发',
    production: '生产'
  }
  return map[env] || env
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 添加变量
function addVariable(type) {
  if (type === 'secret') {
    showEditDialog.value = true
    editingVar.value = null
    Object.assign(editForm, {
      name: '',
      value: '',
      type: 'secret',
      environment: 'development',
      description: ''
    })
  } else {
    envVariables.value.push({
      name: '',
      value: '',
      type: 'string',
      environment: 'development',
      description: '',
      _editing: true,
      _nameError: false
    })
  }
}

// 编辑变量
function editVariable(row) {
  row._editing = true
  row._nameError = false
}

// 验证变量名
function validateVarName(row) {
  const pattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/
  if (!pattern.test(row.name)) {
    row._nameError = true
    appStore.error('变量名必须以字母或下划线开头，只能包含字母、数字和下划线')
    return false
  }

  // 检查重复
  const duplicate = envVariables.value.find(
    (v) => v !== row && v.name === row.name
  )
  if (duplicate) {
    row._nameError = true
    appStore.error(`变量名 "${row.name}" 已存在`)
    return false
  }

  row._nameError = false
  return true
}

// 保存变量（行内编辑）
async function saveVariable(row) {
  if (!row.name.trim()) {
    appStore.error('变量名不能为空')
    return
  }

  if (!validateVarName(row)) {
    return
  }

  if (props.workflowId) {
    try {
      const { createVariable, updateVariable } = await import('@/api/variable')
      const payload = {
        name: row.name,
        value: row.value,
        type: row.type,
        environment: row.environment,
        description: row.description,
      }
      if (row.id) {
        await updateVariable(row.id, payload)
      } else {
        const created = await createVariable(props.workflowId, payload)
        row.id = created.id
      }
    } catch (error) {
      console.error('Failed to save variable:', error)
      appStore.error('保存变量失败')
      return
    }
  } else {
    variableStore.setEnvironmentVariable(row.name, {
      value: row.value,
      type: row.type,
      environment: row.environment,
      description: row.description,
    }, row.environment)
  }

  row._editing = false
  appStore.success('变量已保存')
  emit('change', { [row.name]: row })
}

// 取消编辑
function cancelEdit(row, index) {
  if (!row.name && index !== undefined) {
    envVariables.value.splice(index, 1)
  } else {
    row._editing = false
  }
}

// 删除变量
async function removeVariable(row, type) {
  if (props.workflowId && row.id) {
    try {
      const { deleteVariable } = await import('@/api/variable')
      await deleteVariable(row.id)
    } catch (error) {
      console.error('Failed to delete variable:', error)
      appStore.error('删除变量失败')
      return
    }
  }

  if (type === 'secret') {
    const idx = secretVariables.value.findIndex(v => v.name === row.name)
    if (idx !== -1) {
      secretVariables.value.splice(idx, 1)
    }
  } else {
    const idx = envVariables.value.findIndex(v => v.name === row.name)
    if (idx !== -1) {
      envVariables.value.splice(idx, 1)
    }
  }
  appStore.success('变量已删除')
}

// 保存编辑
function handleSaveEdit() {
  if (!editForm.name.trim()) {
    appStore.error('变量名不能为空')
    return
  }

  const pattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/
  if (!pattern.test(editForm.name)) {
    appStore.error('变量名格式不正确')
    return
  }

  if (editForm.type === 'secret') {
    // 添加到密钥变量
    const idx = secretVariables.value.findIndex(v => v.name === editForm.name)
    if (idx !== -1) {
      secretVariables.value[idx] = {
        ...secretVariables.value[idx],
        description: editForm.description,
        environment: editForm.environment
      }
    } else {
      secretVariables.value.push({
        name: editForm.name,
        value: editForm.value,
        type: 'secret',
        environment: editForm.environment,
        description: editForm.description,
        createdAt: new Date().toISOString()
      })
    }
    appStore.success('密钥变量已保存')
  } else {
    // 添加到环境变量
    const idx = envVariables.value.findIndex(v => v.name === editForm.name || (!v.name && !v._editing))
    const newVar = {
      name: editForm.name,
      value: editForm.value,
      type: editForm.type,
      environment: editForm.environment,
      description: editForm.description,
      _editing: false,
      _nameError: false
    }

    if (idx !== -1) {
      envVariables.value[idx] = newVar
    } else {
      envVariables.value.push(newVar)
    }
    appStore.success('环境变量已保存')
  }

  showEditDialog.value = false
}

// 导入变量
async function handleImport() {
  importErrors.value = []

  if (!importJson.value.trim()) {
    importErrors.value.push('导入数据不能为空')
    return
  }

  importing.value = true

  try {
    let data
    try {
      data = JSON.parse(importJson.value)
    } catch (e) {
      importErrors.value.push('JSON 格式解析失败')
      return
    }

    const items = Array.isArray(data) ? data : [data]

    for (const item of items) {
      if (!item.name) {
        importErrors.value.push(`缺少变量名: ${JSON.stringify(item)}`)
        continue
      }

      const pattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/
      if (!pattern.test(item.name)) {
        importErrors.value.push(`变量名非法: ${item.name}`)
        continue
      }

      if (item.type === 'secret') {
        secretVariables.value.push({
          name: item.name,
          value: item.value || '',
          type: 'secret',
          environment: item.environment || 'development',
          description: item.description || '',
          createdAt: new Date().toISOString()
        })
      } else {
        envVariables.value.push({
          name: item.name,
          value: item.value || '',
          type: item.type || 'string',
          environment: item.environment || 'development',
          description: item.description || '',
          _editing: false,
          _nameError: false
        })
      }
    }

    if (importErrors.value.length === 0) {
      appStore.success(`成功导入 ${items.length} 个变量`)
      showImportDialog.value = false
      importJson.value = ''
    }
  } finally {
    importing.value = false
  }
}

// 导出变量
function handleExport() {
  const data = [...envVariables.value, ...secretVariables.value].map(v => ({
    name: v.name,
    value: v.type === 'secret' ? '' : v.value,
    type: v.type,
    environment: v.environment,
    description: v.description
  }))

  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `variables-${props.workflowId || 'export'}-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)

  appStore.success('变量已导出')
}

// 轮换密钥
async function handleRotateSecret(row) {
  if (!row.id) {
    appStore.warning('该密钥未保存到服务器，无法轮换')
    return
  }
  try {
    const { rotateSecret } = await import('@/api/variable')
    await rotateSecret(row.id)
    appStore.success('密钥已轮换')
    if (props.workflowId) {
      await initData()
    }
  } catch (error) {
    console.error('Failed to rotate secret:', error)
    appStore.error('密钥轮换失败')
  }
}

// 保存全部
async function handleSaveAll() {
  saving.value = true

  try {
    // 验证所有变量
    const vars = {}
    for (const v of envVariables.value) {
      if (v.name) {
        vars[v.name] = {
          value: v.value,
          type: v.type,
          environment: v.environment,
          description: v.description
        }
      }
    }

    const validation = variableStore.validateVariableDefinitions(vars)
    if (!validation.valid) {
      appStore.error(validation.errors[0])
      saving.value = false
      return
    }

    // 保存到 store
    for (const [name, varDef] of Object.entries(vars)) {
      variableStore.setEnvironmentVariable(name, varDef, varDef.environment)
    }

    // 如果有 workflowId，尝试同步到后端
    if (props.workflowId) {
      await variableStore.saveVariables(props.workflowId, vars)
    }

    appStore.success('所有变量已保存')
    emit('change', vars)
  } catch (error) {
    console.error('Failed to save all variables:', error)
    appStore.error('保存变量失败')
  } finally {
    saving.value = false
  }
}

// 关闭前确认
function handleClose() {
  visible.value = false
}
</script>

<style lang="scss" scoped>
.variable-tabs {
  height: calc(100% - 60px);

  :deep(.el-tabs__header) {
    margin: 0 0 16px;
    padding: 0 16px;
  }

  :deep(.el-tabs__content) {
    padding: 0 16px;
  }

  :deep(.el-tab-pane) {
    height: calc(100% - 50px);
    overflow-y: auto;
  }
}

.panel-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;

  .icon {
    width: 14px;
    height: 14px;
    margin-right: 4px;
  }

  .is-loading {
    animation: spin 1s linear infinite;
  }
}

.runtime-hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-tertiary, #999);
}

.variable-table {
  margin-bottom: 16px;

  .is-error {
    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px var(--el-color-danger) inset;
    }
  }

  .var-name-cell {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
    color: var(--text-primary, #333);
  }

  .value-display {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 12px;
    color: var(--text-secondary, #666);
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: block;
  }
}

.runtime-var-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.runtime-var-item {
  padding: 12px;
  background: var(--bg-tertiary, #f5f7fa);
  border: 1px solid var(--border-primary, #e4e7ed);
  border-radius: 8px;

  .var-info {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .var-name {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary, #333);
    background: none;
    padding: 0;
  }

  .var-meta {
    display: flex;
    gap: 16px;
    margin-bottom: 8px;
    font-size: 12px;
    color: var(--text-tertiary, #999);

    .var-node,
    .var-type {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }

  .var-preview {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    background: var(--bg-secondary, #fff);
    border-radius: 4px;

    .preview-label {
      font-size: 12px;
      color: var(--text-tertiary, #999);
    }

    .preview-value {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 12px;
      color: var(--text-secondary, #666);
      background: none;
      padding: 0;
      word-break: break-all;
    }
  }
}

.secret-info {
  margin-bottom: 16px;
}

.import-textarea {
  :deep(.el-textarea__inner) {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 12px;
  }
}

.import-errors {
  margin-top: 12px;

  ul {
    margin: 8px 0 0;
    padding-left: 20px;

    li {
      font-size: 12px;
      margin-bottom: 4px;
    }
  }
}

.edit-form {
  .form-hint {
    font-size: 12px;
    color: var(--text-tertiary, #999);
    margin-top: 4px;
  }
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid var(--border-primary, #e4e7ed);
  background: var(--bg-secondary, #fff);
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--text-tertiary, #c0c4cc);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
