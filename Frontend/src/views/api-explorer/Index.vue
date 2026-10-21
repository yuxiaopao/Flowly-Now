<template>
  <div class="api-explorer">
    <PageHeader
      title="API 测试工具"
      subtitle="测试和调试 Flowly API 接口"
    />

    <div class="explorer-layout">
      <!-- 左侧: API 端点列表 -->
      <div class="endpoints-sidebar">
        <div class="sidebar-header">
          <h3>API 端点</h3>
          <el-input
            v-model="endpointSearch"
            placeholder="搜索端点..."
            aria-label="搜索 API 端点"
            :prefix-icon="Search"
            clearable
            size="small"
          />
        </div>

        <div class="endpoints-list">
          <div
            v-for="category in filteredEndpoints"
            :key="category.name"
            class="endpoint-category"
          >
            <div
              class="category-header"
              role="button"
              tabindex="0"
              :aria-expanded="expandedCategories.includes(category.name)"
              @keydown.enter.self="toggleCategory(category.name)"
              @keydown.space.self.prevent="toggleCategory(category.name)"
              @click="toggleCategory(category.name)"
            >
              <el-icon :class="{ expanded: expandedCategories.includes(category.name) }">
                <ArrowRight />
              </el-icon>
              <span>{{ category.label }}</span>
              <el-tag
                size="small"
                type="info"
              >
                {{ category.endpoints.length }}
              </el-tag>
            </div>

            <div
              v-show="expandedCategories.includes(category.name)"
              class="category-endpoints"
            >
              <div
                v-for="endpoint in category.endpoints"
                :key="endpoint.path"
                class="endpoint-item"
                role="button"
                tabindex="0"
                :aria-label="`${endpoint.method} ${endpoint.path}`"
                :class="{ active: selectedEndpoint?.path === endpoint.path }"
                @keydown.enter.self="selectEndpoint(endpoint)"
                @keydown.space.self.prevent="selectEndpoint(endpoint)"
                @click="selectEndpoint(endpoint)"
              >
                <el-tag
                  :type="getMethodType(endpoint.method)"
                  size="small"
                >
                  {{ endpoint.method }}
                </el-tag>
                <span class="endpoint-path">{{ endpoint.path }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间: 请求编辑器 -->
      <div class="request-panel">
        <div
          v-if="selectedEndpoint"
          class="request-content"
        >
          <!-- URL 栏 -->
          <div class="url-bar">
            <el-select
              v-model="requestConfig.method"
              size="large"
              style="width: 120px"
            >
              <el-option
                label="GET"
                value="GET"
              />
              <el-option
                label="POST"
                value="POST"
              />
              <el-option
                label="PUT"
                value="PUT"
              />
              <el-option
                label="PATCH"
                value="PATCH"
              />
              <el-option
                label="DELETE"
                value="DELETE"
              />
            </el-select>
            <el-input
              v-model="requestConfig.url"
              placeholder="输入请求 URL"
              aria-label="请求 URL"
              size="large"
              class="url-input"
            />
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="sendRequest"
            >
              发送
            </el-button>
          </div>

          <!-- 请求选项卡 -->
          <el-tabs
            v-model="requestTab"
            class="request-tabs"
          >
            <!-- 参数 -->
            <el-tab-pane
              label="参数"
              name="params"
            >
              <div class="key-value-editor">
                <div class="kv-header">
                  <span>参数名</span>
                  <span>值</span>
                  <span>描述</span>
                  <span />
                </div>
                <div
                  v-for="(param, index) in requestConfig.params"
                  :key="index"
                  class="kv-row"
                >
                  <el-input
                    v-model="param.key"
                    placeholder="参数名"
                  />
                  <el-input
                    v-model="param.value"
                    placeholder="值"
                  />
                  <el-input
                    v-model="param.description"
                    placeholder="描述"
                  />
                  <el-button
                    text
                    type="danger"
                    @click="removeParam(index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <el-button
                  text
                  type="primary"
                  @click="addParam"
                >
                  <el-icon><Plus /></el-icon> 添加参数
                </el-button>
              </div>
            </el-tab-pane>

            <!-- 请求头 -->
            <el-tab-pane
              label="请求头"
              name="headers"
            >
              <div class="key-value-editor">
                <div class="kv-header">
                  <span>Header</span>
                  <span>值</span>
                  <span />
                </div>
                <div
                  v-for="(header, index) in requestConfig.headers"
                  :key="index"
                  class="kv-row"
                >
                  <el-select
                    v-model="header.key"
                    placeholder="选择或输入"
                    allow-create
                    filterable
                  >
                    <el-option
                      label="Content-Type"
                      value="Content-Type"
                    />
                    <el-option
                      label="Authorization"
                      value="Authorization"
                    />
                    <el-option
                      label="X-Request-ID"
                      value="X-Request-ID"
                    />
                    <el-option
                      label="X-Tenant"
                      value="X-Tenant"
                    />
                  </el-select>
                  <el-input
                    v-model="header.value"
                    placeholder="值"
                  />
                  <el-button
                    text
                    type="danger"
                    @click="removeHeader(index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <el-button
                  text
                  type="primary"
                  @click="addHeader"
                >
                  <el-icon><Plus /></el-icon> 添加 Header
                </el-button>
              </div>
            </el-tab-pane>

            <!-- 请求体 -->
            <el-tab-pane
              label="请求体"
              name="body"
            >
              <div class="body-editor">
                <div class="body-type-selector">
                  <el-radio-group v-model="requestConfig.bodyType">
                    <el-radio value="none">
                      无
                    </el-radio>
                    <el-radio value="json">
                      JSON
                    </el-radio>
                    <el-radio value="form">
                      Form Data
                    </el-radio>
                    <el-radio value="raw">
                      Raw
                    </el-radio>
                  </el-radio-group>
                </div>

                <div
                  v-if="requestConfig.bodyType === 'json'"
                  class="json-editor"
                >
                  <el-input
                    v-model="requestConfig.bodyJson"
                    type="textarea"
                    :rows="12"
                    placeholder="&#123;&quot;key&quot;: &quot;value&quot;&#125;"
                    class="body-textarea"
                    style="font-family: monospace"
                  />
                  <el-button
                    text
                    size="small"
                    @click="formatJson"
                  >
                    格式化
                  </el-button>
                </div>

                <div
                  v-else-if="requestConfig.bodyType === 'form'"
                  class="key-value-editor"
                >
                  <div class="kv-header">
                    <span>键</span>
                    <span>值</span>
                    <span />
                  </div>
                  <div
                    v-for="(field, index) in requestConfig.formData"
                    :key="index"
                    class="kv-row"
                  >
                    <el-input
                      v-model="field.key"
                      placeholder="键"
                    />
                    <el-input
                      v-model="field.value"
                      placeholder="值"
                    />
                    <el-button
                      text
                      type="danger"
                      @click="removeFormField(index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button
                    text
                    type="primary"
                    @click="addFormField"
                  >
                    <el-icon><Plus /></el-icon> 添加字段
                  </el-button>
                </div>

                <div
                  v-else-if="requestConfig.bodyType === 'raw'"
                  class="raw-editor"
                >
                  <div class="content-type-selector">
                    <el-select
                      v-model="requestConfig.rawContentType"
                      size="small"
                    >
                      <el-option
                        label="Text"
                        value="text/plain"
                      />
                      <el-option
                        label="JSON"
                        value="application/json"
                      />
                      <el-option
                        label="XML"
                        value="application/xml"
                      />
                      <el-option
                        label="HTML"
                        value="text/html"
                      />
                    </el-select>
                  </div>
                  <el-input
                    v-model="requestConfig.bodyRaw"
                    type="textarea"
                    :rows="10"
                    class="body-textarea"
                    style="font-family: monospace"
                  />
                </div>
              </div>
            </el-tab-pane>

            <!-- 认证 -->
            <el-tab-pane
              label="认证"
              name="auth"
            >
              <div class="auth-editor">
                <el-radio-group
                  v-model="requestConfig.authType"
                  class="auth-type-selector"
                >
                  <el-radio value="none">
                    无认证
                  </el-radio>
                  <el-radio value="bearer">
                    Bearer Token
                  </el-radio>
                  <el-radio value="apiKey">
                    API Key
                  </el-radio>
                  <el-radio value="basic">
                    Basic Auth
                  </el-radio>
                </el-radio-group>

                <div
                  v-if="requestConfig.authType === 'bearer'"
                  class="auth-config"
                >
                  <el-form label-width="100px">
                    <el-form-item label="Token">
                      <el-input
                        v-model="requestConfig.bearerToken"
                        placeholder="输入你的 Token"
                        type="password"
                        show-password
                      />
                    </el-form-item>
                  </el-form>
                </div>

                <div
                  v-else-if="requestConfig.authType === 'apiKey'"
                  class="auth-config"
                >
                  <el-form label-width="100px">
                    <el-form-item label="Key 名">
                      <el-input
                        v-model="requestConfig.apiKeyName"
                        placeholder="X-API-Key"
                      />
                    </el-form-item>
                    <el-form-item label="值">
                      <el-input
                        v-model="requestConfig.apiKeyValue"
                        placeholder="API Key 值"
                        type="password"
                        show-password
                      />
                    </el-form-item>
                    <el-form-item label="附加位置">
                      <el-select v-model="requestConfig.apiKeyLocation">
                        <el-option
                          label="请求头"
                          value="header"
                        />
                        <el-option
                          label="查询参数"
                          value="query"
                        />
                      </el-select>
                    </el-form-item>
                  </el-form>
                </div>

                <div
                  v-else-if="requestConfig.authType === 'basic'"
                  class="auth-config"
                >
                  <el-form label-width="100px">
                    <el-form-item label="用户名">
                      <el-input
                        v-model="requestConfig.basicUsername"
                        placeholder="用户名"
                      />
                    </el-form-item>
                    <el-form-item label="密码">
                      <el-input
                        v-model="requestConfig.basicPassword"
                        placeholder="密码"
                        type="password"
                        show-password
                      />
                    </el-form-item>
                  </el-form>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <div
          v-else
          class="no-endpoint-selected"
        >
          <el-empty description="选择一个端点开始测试">
            <template #image>
              <el-icon :size="64">
                <Document />
              </el-icon>
            </template>
          </el-empty>
        </div>
      </div>

      <!-- 右侧: 响应 -->
      <div class="response-panel">
        <div class="response-header">
          <h3>响应</h3>
          <div
            v-if="response"
            class="response-meta"
          >
            <el-tag :type="getStatusType(response.status)">
              {{ response.status }} {{ response.statusText }}
            </el-tag>
            <span class="response-time">{{ response.time }}ms</span>
            <span class="response-size">{{ formatSize(response.size) }}</span>
          </div>
        </div>

        <div
          v-if="response"
          class="response-content"
        >
          <el-tabs
            v-model="responseTab"
            class="response-tabs"
          >
            <el-tab-pane
              label="响应体"
              name="body"
            >
              <div class="response-body">
                <div class="response-toolbar">
                  <el-button-group>
                    <el-button
                      size="small"
                      @click="formatResponse"
                    >
                      格式化
                    </el-button>
                    <el-button
                      size="small"
                      @click="copyResponse"
                    >
                      复制
                    </el-button>
                  </el-button-group>
                </div>
                <el-input
                  v-model="responseBody"
                  type="textarea"
                  readonly
                  :rows="20"
                  class="response-textarea"
                  style="font-family: monospace"
                />
              </div>
            </el-tab-pane>

            <el-tab-pane
              label="响应头"
              name="headers"
            >
              <div class="response-headers">
                <table class="headers-table">
                  <tbody>
                    <tr
                      v-for="(value, key) in response.headers"
                      :key="key"
                    >
                      <td class="header-key">
                        {{ key }}
                      </td>
                      <td class="header-value">
                        {{ value }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </el-tab-pane>

            <el-tab-pane
              label="信息"
              name="info"
            >
              <div class="response-info">
                <div class="info-item">
                  <span class="info-label">状态码</span>
                  <span class="info-value">{{ response.status }} {{ response.statusText }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">响应时间</span>
                  <span class="info-value">{{ response.time }}ms</span>
                </div>
                <div class="info-item">
                  <span class="info-label">响应大小</span>
                  <span class="info-value">{{ formatSize(response.size) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Content-Type</span>
                  <span class="info-value">{{ response.contentType }}</span>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <div
          v-else
          class="no-response"
        >
          <el-empty description="发送请求后查看响应">
            <template #image>
              <el-icon :size="64">
                <ChatDotRound />
              </el-icon>
            </template>
          </el-empty>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import PageHeader from '@/components/layout/PageHeader.vue'
import { ref, computed, reactive, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import {
  Search, ArrowRight, Delete, Plus, Document, ChatDotRound
} from '@element-plus/icons-vue'
import { getApiUrl } from '@/config'

const appStore = useAppStore()

// API Endpoints
const endpoints = [
  {
    name: 'workflows',
    label: '工作流',
    endpoints: [
      { path: '/workflows/', method: 'GET', description: '获取工作流列表' },
      { path: '/workflows/', method: 'POST', description: '创建工作流' },
      { path: '/workflows/:id/', method: 'GET', description: '获取工作流详情' },
      { path: '/workflows/:id/', method: 'PUT', description: '更新工作流' },
      { path: '/workflows/:id/', method: 'DELETE', description: '删除工作流' },
      { path: '/workflows/:id/execute/', method: 'POST', description: '执行工作流' }
    ]
  },
  {
    name: 'agents',
    label: 'Agent',
    endpoints: [
      { path: '/agents/', method: 'GET', description: '获取 Agent 列表' },
      { path: '/agents/', method: 'POST', description: '创建 Agent' },
      { path: '/agents/:id/', method: 'GET', description: '获取 Agent 详情' },
      { path: '/agents/:id/', method: 'PUT', description: '更新 Agent' },
      { path: '/agents/:id/', method: 'DELETE', description: '删除 Agent' },
      { path: '/agents/:id/execute/', method: 'POST', description: '执行 Agent' }
    ]
  },
  {
    name: 'models',
    label: '模型管理',
    endpoints: [
      { path: '/gateway/api-keys/', method: 'GET', description: '获取统一凭证兼容列表' },
      { path: '/gateway/api-keys/', method: 'POST', description: '通过兼容接口创建统一凭证' },
      { path: '/gateway/models/', method: 'GET', description: '获取模型列表' },
      { path: '/gateway/models/:id/', method: 'GET', description: '获取模型详情' },
      { path: '/gateway/chat/', method: 'POST', description: '发送聊天请求' },
      { path: '/gateway/embeddings/', method: 'POST', description: '获取 embeddings' }
    ]
  },
  {
    name: 'rag',
    label: 'RAG / 知识库',
    endpoints: [
      { path: '/rag/vector-stores/', method: 'GET', description: '获取向量存储列表' },
      { path: '/rag/vector-stores/', method: 'POST', description: '创建向量存储' },
      { path: '/rag/collections/', method: 'GET', description: '获取文档集合列表' },
      { path: '/rag/collections/', method: 'POST', description: '创建文档集合' },
      { path: '/rag/collections/:id/documents/', method: 'POST', description: '上传文档' },
      { path: '/rag/collections/:id/search/', method: 'POST', description: '搜索文档' }
    ]
  },
  {
    name: 'nl-workflow',
    label: '语创',
    endpoints: [
      { path: '/nl-workflow/generate/', method: 'POST', description: '生成工作流' },
      { path: '/nl-workflow/generate/stream/', method: 'POST', description: '流式生成工作流' },
      { path: '/nl-workflow/validate/', method: 'POST', description: '验证工作流' }
    ]
  },
  {
    name: 'analytics',
    label: '数据分析',
    endpoints: [
      { path: '/monitoring/analytics/overview/', method: 'GET', description: '获取概览数据' },
      { path: '/monitoring/analytics/trends/', method: 'GET', description: '获取趋势数据' },
      { path: '/monitoring/executions/', method: 'GET', description: '获取执行记录' },
      { path: '/monitoring/logs/', method: 'GET', description: '获取日志' }
    ]
  },
  {
    name: 'auth',
    label: '认证',
    endpoints: [
      { path: '/auth/login/', method: 'POST', description: '用户登录' },
      { path: '/auth/register/', method: 'POST', description: '用户注册' },
      { path: '/auth/logout/', method: 'POST', description: '用户登出' },
      { path: '/auth/me/', method: 'GET', description: '获取当前用户' },
      { path: '/auth/refresh/', method: 'POST', description: '刷新 Token' }
    ]
  }
]

// State
const endpointSearch = ref('')
const expandedCategories = ref(['workflows', 'agents'])
const selectedEndpoint = ref(null)
const requestTab = ref('params')
const responseTab = ref('body')
const loading = ref(false)
const response = ref(null)

const requestConfig = reactive({
  method: 'GET',
  url: '',
  params: [],
  headers: [
    { key: 'Content-Type', value: 'application/json' }
  ],
  bodyType: 'json',
  bodyJson: '',
  formData: [],
  rawContentType: 'application/json',
  bodyRaw: '',
  authType: 'bearer',
  bearerToken: '',
  apiKeyName: 'X-API-Key',
  apiKeyValue: '',
  apiKeyLocation: 'header',
  basicUsername: '',
  basicPassword: ''
})

const responseBody = ref('')

// Computed
const filteredEndpoints = computed(() => {
  if (!endpointSearch.value) return endpoints
  const search = endpointSearch.value.toLowerCase()
  return endpoints.map(category => ({
    ...category,
    endpoints: category.endpoints.filter(
      e => e.path.toLowerCase().includes(search) ||
           e.description.toLowerCase().includes(search) ||
           e.method.toLowerCase().includes(search)
    )
  })).filter(c => c.endpoints.length > 0)
})

// Methods
const toggleCategory = (name) => {
  const index = expandedCategories.value.indexOf(name)
  if (index > -1) {
    expandedCategories.value.splice(index, 1)
  } else {
    expandedCategories.value.push(name)
  }
}

const selectEndpoint = (endpoint) => {
  selectedEndpoint.value = endpoint
  requestConfig.method = endpoint.method
  requestConfig.url = getApiUrl(endpoint.path)

  // Reset request config
  requestConfig.params = []
  requestConfig.bodyJson = ''
  requestConfig.formData = []
  requestConfig.bodyRaw = ''
  response.value = null
  responseBody.value = ''
}

const addParam = () => {
  requestConfig.params.push({ key: '', value: '', description: '' })
}

const removeParam = (index) => {
  requestConfig.params.splice(index, 1)
}

const addHeader = () => {
  requestConfig.headers.push({ key: '', value: '' })
}

const removeHeader = (index) => {
  requestConfig.headers.splice(index, 1)
}

const addFormField = () => {
  requestConfig.formData.push({ key: '', value: '' })
}

const removeFormField = (index) => {
  requestConfig.formData.splice(index, 1)
}

const formatJson = () => {
  try {
    const obj = JSON.parse(requestConfig.bodyJson)
    requestConfig.bodyJson = JSON.stringify(obj, null, 2)
  } catch (e) {
    appStore.error('Invalid JSON')
  }
}

const sendRequest = async () => {
  if (!requestConfig.url) {
    appStore.warning('请输入请求 URL')
    return
  }

  loading.value = true
  const startTime = Date.now()

  try {
    // Build URL with params
    let url = requestConfig.url
    if (requestConfig.params.length > 0) {
      const searchParams = new URLSearchParams()
      requestConfig.params.forEach(p => {
        if (p.key) searchParams.append(p.key, p.value)
      })
      url += (url.includes('?') ? '&' : '?') + searchParams.toString()
    }

    // Build headers
    const headers = {}
    requestConfig.headers.forEach(h => {
      if (h.key) headers[h.key] = h.value
    })

    // Add auth
    if (requestConfig.authType === 'bearer' && requestConfig.bearerToken) {
      headers['Authorization'] = `Bearer ${requestConfig.bearerToken}`
    } else if (requestConfig.authType === 'apiKey' && requestConfig.apiKeyValue) {
      if (requestConfig.apiKeyLocation === 'header') {
        headers[requestConfig.apiKeyName] = requestConfig.apiKeyValue
      } else {
        url += (url.includes('?') ? '&' : '?') + `${requestConfig.apiKeyName}=${requestConfig.apiKeyValue}`
      }
    } else if (requestConfig.authType === 'basic' && requestConfig.basicUsername) {
      const credentials = btoa(`${requestConfig.basicUsername}:${requestConfig.basicPassword}`)
      headers['Authorization'] = `Basic ${credentials}`
    }

    // Build body
    let body = undefined
    if (['POST', 'PUT', 'PATCH'].includes(requestConfig.method)) {
      if (requestConfig.bodyType === 'json' && requestConfig.bodyJson) {
        body = requestConfig.bodyJson
      } else if (requestConfig.bodyType === 'form' && requestConfig.formData.length > 0) {
        const formData = new FormData()
        requestConfig.formData.forEach(f => {
          if (f.key) formData.append(f.key, f.value)
        })
        body = formData
        delete headers['Content-Type'] // Let browser set Content-Type for FormData
      } else if (requestConfig.bodyType === 'raw') {
        body = requestConfig.bodyRaw
        headers['Content-Type'] = requestConfig.rawContentType
      }
    }

    // Send request
    const result = await fetch(url, {
      method: requestConfig.method,
      headers,
      body,
      credentials: 'include'
    })

    const responseText = await result.text()
    const endTime = Date.now()

    // Try to parse as JSON
    let parsedBody = responseText
    try {
      const jsonBody = JSON.parse(responseText)
      parsedBody = JSON.stringify(jsonBody, null, 2)
    } catch (e) {
      // Response is not JSON; keep raw text.
    }

    response.value = {
      status: result.status,
      statusText: result.statusText,
      headers: Object.fromEntries(result.headers.entries()),
      body: parsedBody,
      time: endTime - startTime,
      size: new Blob([responseText]).size,
      contentType: result.headers.get('content-type') || ''
    }
    responseBody.value = parsedBody

  } catch (error) {
    response.value = {
      status: 0,
      statusText: 'Network Error',
      headers: {},
      body: error.message,
      time: Date.now() - startTime,
      size: 0,
      contentType: ''
    }
    responseBody.value = error.message
  } finally {
    loading.value = false
  }
}

const formatResponse = () => {
  try {
    const obj = JSON.parse(responseBody.value)
    responseBody.value = JSON.stringify(obj, null, 2)
  } catch (e) {
    appStore.info('响应内容不是有效 JSON')
  }
}

const copyResponse = async () => {
  try {
    await navigator.clipboard.writeText(responseBody.value)
    appStore.success('响应内容已复制到剪贴板')
  } catch (e) {
    appStore.error('Failed to copy')
  }
}

const getMethodType = (method) => {
  const types = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    PATCH: 'warning',
    DELETE: 'danger'
  }
  return types[method] || 'info'
}

const getStatusType = (status) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(() => {
  const savedToken = localStorage.getItem('access_token')
  if (savedToken) {
    requestConfig.bearerToken = savedToken
  }
})
</script>

<style scoped>
.api-explorer {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.explorer-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) minmax(280px, 360px);
  gap: 16px;
  min-height: 0;
}

/* Sidebar */
.endpoints-sidebar {
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-primary);
}

.sidebar-header h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
}

.endpoints-list {
  flex: 1;
  overflow-y: auto;
}

.endpoint-category {
  border-bottom: 1px solid var(--border-primary);
}

.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  font-weight: 500;
  font-size: 13px;
}

.category-header:hover {
  background: var(--bg-hover);
}

.category-header .el-icon {
  transition: transform 0.2s;
}

.category-header .el-icon.expanded {
  transform: rotate(90deg);
}

.category-endpoints {
  padding: 0 0 8px 0;
}

.endpoint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 8px 40px;
  cursor: pointer;
  font-size: 12px;
}

.endpoint-item:hover {
  background: var(--bg-hover);
}

.endpoint-item.active {
  background: var(--bg-active);
}

.endpoint-path {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: monospace;
}

/* Request Panel */
.request-panel {
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.request-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.url-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.url-input {
  flex: 1;
}

.request-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.request-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
}

.request-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.no-endpoint-selected {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Key-Value Editor */
.key-value-editor {
  padding: 16px;
}

.kv-header {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 40px;
  gap: 8px;
  padding: 8px 0;
  font-size: 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.kv-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 40px;
  gap: 8px;
  padding: 8px 0;
  align-items: center;
}

/* Body Editor */
.body-editor {
  padding: 16px;
}

.body-type-selector {
  margin-bottom: 16px;
}

.json-editor {
  position: relative;
}

.json-editor .el-button {
  position: absolute;
  top: 8px;
  right: 8px;
}

.body-textarea {
  font-size: 12px;
}

/* Auth Editor */
.auth-editor {
  padding: 16px;
}

.auth-type-selector {
  margin-bottom: 16px;
}

.auth-config {
  max-width: 400px;
}

/* Response Panel */
.response-panel {
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-primary);
}

.response-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.response-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.response-time,
.response-size {
  font-size: 12px;
  color: var(--text-secondary);
}

.response-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.response-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.response-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
}

.response-body {
  padding: 16px;
}

.response-toolbar {
  margin-bottom: 8px;
}

.response-textarea {
  font-size: 12px;
}

.response-headers {
  padding: 16px;
}

.headers-table {
  width: 100%;
}

.headers-table td {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-primary);
}

.header-key {
  font-weight: 500;
  color: var(--text-primary);
  width: 200px;
}

.header-value {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.response-info {
  padding: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-primary);
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  font-weight: 500;
}

.no-response {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
@media (max-width: 1250px) {
  .api-explorer { height: auto; min-height: calc(100dvh - var(--header-height)); }
  .explorer-layout { grid-template-columns: 220px minmax(0, 1fr); }
  .endpoints-sidebar { grid-row: span 2; max-height: 900px; }
  .response-panel { grid-column: 2; min-height: 280px; }
}
@media (max-width: 768px) {
  .explorer-layout { grid-template-columns: minmax(0, 1fr); }
  .endpoints-sidebar { grid-row: auto; max-height: 280px; }
  .request-panel { min-height: 240px; }
  .response-panel { grid-column: 1; }
  .request-content, .response-header, .key-value-editor, .body-editor, .auth-editor { padding: 12px; }
  .url-bar { flex-wrap: wrap; }
  .url-input { flex: 1 0 100%; order: -1; min-width: 0; }
  .kv-header, .kv-row { grid-template-columns: repeat(3, minmax(0, 1fr)) 32px; gap: 4px; }
  .response-header, .response-meta { flex-wrap: wrap; gap: 8px; }
  .header-key { width: auto; padding-right: 12px; }
}
</style>
