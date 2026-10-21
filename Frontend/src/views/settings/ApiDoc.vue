<template>
  <div class="api-sdk-page">
    <PageHeader
      compact
      title="API 文档"
      subtitle="使用 Flowly API 构建您自己的应用"
    >
      <template #actions>
        <el-button @click="showApiKeyDialog = true">
          <Key class="btn-icon" />
          管理 API Key
        </el-button>
      </template>
    </PageHeader>

    <!-- Quick Start -->
    <div class="section">
      <h2>快速开始</h2>
      <el-card
        shadow="never"
        class="quick-start-card"
      >
        <div class="quick-start-steps">
          <div class="step">
            <div class="step-number">
              1
            </div>
            <div class="step-content">
              <h4>获取 API Key</h4>
              <p>在设置页面获取您的 API Key</p>
            </div>
          </div>
          <div class="step">
            <div class="step-number">
              2
            </div>
            <div class="step-content">
              <h4>安装 SDK</h4>
              <p>使用 npm 或 yarn 安装客户端库</p>
            </div>
          </div>
          <div class="step">
            <div class="step-number">
              3
            </div>
            <div class="step-content">
              <h4>开始调用</h4>
              <p>使用 API Key 进行身份验证并调用接口</p>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Tabs -->
    <el-tabs
      v-model="activeTab"
      class="api-tabs"
    >
      <!-- SDK Tab -->
      <el-tab-pane
        label="SDK"
        name="sdk"
      >
        <div class="sdk-section">
          <h3>安装</h3>
          <el-tabs
            v-model="sdkLanguage"
            class="inner-tabs"
          >
            <el-tab-pane
              label="JavaScript"
              name="javascript"
            >
              <div class="code-block">
                <div class="code-header">
                  <span>JavaScript / TypeScript</span>
                  <el-button
                    size="small"
                    text
                    @click="copyCode('npm install')"
                  >
                    <Copy class="copy-icon" />
                    复制
                  </el-button>
                </div>
                <pre class="code-content"><code>npm install @flowly/sdk</code></pre>
              </div>
            </el-tab-pane>
            <el-tab-pane
              label="Python"
              name="python"
            >
              <div class="code-block">
                <div class="code-header">
                  <span>Python</span>
                  <el-button
                    size="small"
                    text
                    @click="copyCode('pip install flowly-sdk')"
                  >
                    <Copy class="copy-icon" />
                    复制
                  </el-button>
                </div>
                <pre class="code-content"><code>pip install flowly-sdk</code></pre>
              </div>
            </el-tab-pane>
          </el-tabs>

          <h3>初始化客户端</h3>
          <div class="code-block">
            <div class="code-header">
              <span>JavaScript</span>
              <el-button
                size="small"
                text
                @click="copyCode(jsInitCode)"
              >
                <Copy class="copy-icon" />
                复制
              </el-button>
            </div>
            <pre class="code-content"><code>{{ jsInitCode }}</code></pre>
          </div>

          <h3>示例代码</h3>

          <!-- Execute Workflow -->
          <div class="example-card">
            <h4>执行工作流</h4>
            <div class="code-block">
              <div class="code-header">
                <span>JavaScript</span>
                <el-button
                  size="small"
                  text
                  @click="copyCode(jsExecuteCode)"
                >
                  <Copy class="copy-icon" />
                  复制
                </el-button>
              </div>
              <pre class="code-content"><code>{{ jsExecuteCode }}</code></pre>
            </div>
          </div>

          <!-- List Workflows -->
          <div class="example-card">
            <h4>获取工作流列表</h4>
            <div class="code-block">
              <div class="code-header">
                <span>JavaScript</span>
                <el-button
                  size="small"
                  text
                  @click="copyCode(jsListCode)"
                >
                  <Copy class="copy-icon" />
                  复制
                </el-button>
              </div>
              <pre class="code-content"><code>{{ jsListCode }}</code></pre>
            </div>
          </div>

          <!-- Run Agent -->
          <div class="example-card">
            <h4>运行 Agent</h4>
            <div class="code-block">
              <div class="code-header">
                <span>JavaScript</span>
                <el-button
                  size="small"
                  text
                  @click="copyCode(jsAgentCode)"
                >
                  <Copy class="copy-icon" />
                  复制
                </el-button>
              </div>
              <pre class="code-content"><code>{{ jsAgentCode }}</code></pre>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- REST API Tab -->
      <el-tab-pane
        label="REST API"
        name="rest"
      >
        <div class="rest-section">
          <h3>基础 URL</h3>
          <div class="base-url">
            <code>https://api.flowly.com/v1</code>
          </div>

          <h3>认证</h3>
          <p>所有 API 请求需要在 Header 中包含 API Key：</p>
          <div class="code-block">
            <pre class="code-content"><code>Authorization: Bearer YOUR_API_KEY</code></pre>
          </div>

          <h3>端点</h3>

          <!-- Workflows -->
          <div class="endpoint-group">
            <h4>工作流</h4>

            <div class="endpoint">
              <div class="endpoint-header">
                <el-tag
                  type="success"
                  size="small"
                >
                  GET
                </el-tag>
                <code>/workflows</code>
                <span class="endpoint-desc">获取工作流列表</span>
              </div>
              <div class="endpoint-body">
                <p><strong>参数：</strong></p>
                <ul>
                  <li><code>page</code> - 页码（默认 1）</li>
                  <li><code>page_size</code> - 每页数量（默认 20）</li>
                  <li><code>status</code> - 状态过滤</li>
                </ul>
                <p><strong>响应：</strong></p>
                <pre class="code-content small"><code>{
  "count": 100,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": "wf_xxx",
      "name": "我的工作流",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}</code></pre>
              </div>
            </div>

            <div class="endpoint">
              <div class="endpoint-header">
                <el-tag
                  type="primary"
                  size="small"
                >
                  POST
                </el-tag>
                <code>/workflows/:id/execute</code>
                <span class="endpoint-desc">执行工作流</span>
              </div>
              <div class="endpoint-body">
                <p><strong>请求体：</strong></p>
                <pre class="code-content small"><code>{
  "input": {
    "query": "Hello world"
  }
}</code></pre>
                <p><strong>响应：</strong></p>
                <pre class="code-content small"><code>{
  "execution_id": "exec_xxx",
  "status": "running",
  "result": null
}</code></pre>
              </div>
            </div>
          </div>

          <!-- Agents -->
          <div class="endpoint-group">
            <h4>Agents</h4>

            <div class="endpoint">
              <div class="endpoint-header">
                <el-tag
                  type="success"
                  size="small"
                >
                  GET
                </el-tag>
                <code>/agents</code>
                <span class="endpoint-desc">获取 Agent 列表</span>
              </div>
            </div>

            <div class="endpoint">
              <div class="endpoint-header">
                <el-tag
                  type="primary"
                  size="small"
                >
                  POST
                </el-tag>
                <code>/agents/:id/run</code>
                <span class="endpoint-desc">运行 Agent</span>
              </div>
            </div>
          </div>

          <!-- Webhooks -->
          <div class="endpoint-group">
            <h4>Webhooks</h4>

            <div class="endpoint">
              <div class="endpoint-header">
                <el-tag
                  type="info"
                  size="small"
                >
                  POST
                </el-tag>
                <code>/webhooks</code>
                <span class="endpoint-desc">创建 Webhook</span>
              </div>
            </div>

            <div class="endpoint">
              <div class="endpoint-header">
                <el-tag
                  type="warning"
                  size="small"
                >
                  DELETE
                </el-tag>
                <code>/webhooks/:id</code>
                <span class="endpoint-desc">删除 Webhook</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Webhooks Tab -->
      <el-tab-pane
        label="Webhooks"
        name="webhooks"
      >
        <div class="webhooks-section">
          <h3>配置 Webhook</h3>
          <p>Webhook 允许您在工作流执行完成或特定事件发生时接收通知。</p>

          <div class="code-block">
            <div class="code-header">
              <span>Webhook 事件格式</span>
            </div>
            <pre class="code-content"><code>{
  "event": "workflow.completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "workflow_id": "wf_xxx",
    "execution_id": "exec_xxx",
    "status": "success",
    "result": { ... },
    "duration_ms": 2500
  }
}</code></pre>
          </div>

          <h3>支持的事件</h3>
          <el-table
            :data="webhookEvents"
            stripe
          >
            <el-table-column
              prop="event"
              label="事件"
              width="200"
            >
              <template #default="{ row }">
                <code>{{ row.event }}</code>
              </template>
            </el-table-column>
            <el-table-column
              prop="description"
              label="描述"
            />
          </el-table>

          <h3>验证签名</h3>
          <div class="code-block">
            <pre class="code-content"><code>const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(payload))
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}</code></pre>
          </div>
        </div>
      </el-tab-pane>

      <!-- SDK Examples Tab -->
      <el-tab-pane
        label="Python SDK"
        name="python-sdk"
      >
        <div class="python-section">
          <h3>初始化</h3>
          <div class="code-block">
            <pre class="code-content"><code>from flowly import FlowlyClient

client = FlowlyClient(api_key="your_api_key")</code></pre>
          </div>

          <h3>执行工作流</h3>
          <div class="code-block">
            <pre class="code-content"><code># 执行工作流
result = client.workflows.execute(
    workflow_id="wf_xxx",
    input={"query": "Hello world"}
)

# 等待结果
execution = client.workflows.wait(result["execution_id"])
print(execution.result)</code></pre>
          </div>

          <h3>流式响应</h3>
          <div class="code-block">
            <pre class="code-content"><code># 流式执行
for chunk in client.workflows.stream(
    workflow_id="wf_xxx",
    input={"query": "Hello"}
):
    print(chunk, end="")</code></pre>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- API Key Dialog -->
    <el-dialog
      v-model="showApiKeyDialog"
      title="管理 API Key"
      width="600px"
    >
      <div class="api-key-list">
        <div
          v-for="key in apiKeys"
          :key="key.id"
          class="api-key-item"
        >
          <div class="key-info">
            <span class="key-name">{{ key.name }}</span>
            <span class="key-prefix">{{ key.prefix }}***</span>
            <span class="key-created">{{ formatDate(key.created_at) }}</span>
          </div>
          <el-button
            type="danger"
            size="small"
            text
            @click="revokeKey(key)"
          >
            撤销
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showApiKeyDialog = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="showCreateKeyDialog = true"
        >
          创建新 Key
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Key, Copy } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import PageHeader from '@/components/layout/PageHeader.vue'

const appStore = useAppStore()
const activeTab = ref('sdk')
const sdkLanguage = ref('javascript')
const showApiKeyDialog = ref(false)
const showCreateKeyDialog = ref(false)

const apiKeys = ref([
  { id: 1, name: '生产环境', prefix: 'fl_live_', created_at: '2024-01-01' },
  { id: 2, name: '测试环境', prefix: 'fl_test_', created_at: '2024-01-15' }
])

const webhookEvents = ref([
  { event: 'workflow.started', description: '工作流开始执行' },
  { event: 'workflow.completed', description: '工作流执行完成' },
  { event: 'workflow.failed', description: '工作流执行失败' },
  { event: 'agent.message', description: 'Agent 收到新消息' },
  { event: 'execution.failed', description: '执行失败' }
])

// 使用配置文件获取 API URL
const getBaseUrl = () => {
  if (typeof import.meta.env.VITE_API_URL !== 'undefined') {
    return `${import.meta.env.VITE_API_URL}${import.meta.env.VITE_API_PREFIX || '/api/v1'}`
  }
  return window.location.origin
}

const jsInitCode = `import { Flowly } from '@flowly/sdk';

const client = new Flowly({
  apiKey: 'YOUR_API_KEY',
  baseUrl: '${getBaseUrl()}'
});`

const jsExecuteCode = `// 执行工作流
const execution = await client.workflows.execute({
  workflowId: 'wf_xxx',
  input: { query: 'Hello world' }
});

console.log('Execution ID:', execution.id);
console.log('Status:', execution.status);

// 轮询结果
const result = await client.workflows.wait(execution.id);
console.log('Result:', result);`

const jsListCode = `// 获取工作流列表
const workflows = await client.workflows.list({
  page: 1,
  pageSize: 20,
  status: 'active'
});

workflows.results.forEach(wf => {
  console.log(wf.id, wf.name);
});`

const jsAgentCode = `// 运行 Agent
const response = await client.agents.run({
  agentId: 'agent_xxx',
  message: '帮我分析今天的天气',
  stream: true
});

// 流式处理
for await (const chunk of response) {
  process.stdout.write(chunk);
}`

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

const copyCode = async (code) => {
  try {
    await navigator.clipboard.writeText(code)
    appStore.success('已复制到剪贴板')
  } catch {
    appStore.error('复制失败')
  }
}

const revokeKey = (key) => {
  apiKeys.value = apiKeys.value.filter(k => k.id !== key.id)
  appStore.success('API Key 已撤销')
}
</script>

<style lang="scss" scoped>

.btn-icon {
  width: 16px;
  height: 16px;
}

.section {
  margin-bottom: 32px;

  h2 {
    margin: 0 0 16px;
    font-size: 20px;
    font-weight: 600;
  }
}

.quick-start-card {
  background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-tertiary) 100%);
  border: 1px solid var(--border-primary);

  :deep(.el-card__body) {
    padding: 32px;
  }
}

.quick-start-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;

  .step {
    display: flex;
    align-items: flex-start;
    gap: 16px;

    .step-number {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--surface-strong);
      color: var(--text-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      flex-shrink: 0;
    }

    .step-content {
      h4 {
        margin: 0;
        color: var(--text-primary);
        font-size: 16px;
      }

      p {
        margin: 4px 0 0;
        color: var(--text-secondary);
        font-size: 14px;
      }
    }
  }
}

.api-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 24px;
  }
}

.sdk-section,
.rest-section,
.webhooks-section,
.python-section {
  h3 {
    margin: 24px 0 16px;
    font-size: 18px;
    font-weight: 600;

    &:first-child {
      margin-top: 0;
    }
  }

  h4 {
    margin: 16px 0 12px;
    font-size: 16px;
    font-weight: 600;
  }

  p {
    margin: 8px 0;
    color: var(--el-text-color-secondary);
  }
}

.base-url {
  background: var(--el-fill-color-light);
  padding: 12px 16px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
}

.code-block {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.2s ease;

  &:hover {
    border-color: var(--border-hover);
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background: var(--code-surface);
    border-bottom: 1px solid var(--code-border);

    span {
      color: var(--code-muted);
      font-size: 13px;
    }
  }

  .code-content {
    margin: 0;
    padding: 16px;
    color: var(--code-text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre;

    &.small {
      font-size: 12px;
    }
  }

  .copy-icon {
    width: 14px;
    height: 14px;
    color: var(--code-muted);
  }
}

.example-card {
  margin: 24px 0;
  padding: 20px;
  background: var(--el-fill-color-lighter);
  border-radius: 12px;

  h4 {
    margin: 0 0 16px;
  }
}

.endpoint-group {
  margin-bottom: 32px;

  h4 {
    margin: 0 0 16px;
    font-size: 18px;
  }
}

.endpoint {
  margin-bottom: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;

  .endpoint-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--el-fill-color-light);

    code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 14px;
    }

    .endpoint-desc {
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }
  }

  .endpoint-body {
    padding: 16px;

    p {
      margin: 8px 0;

      &:first-child {
        margin-top: 0;
      }
    }

    ul {
      margin: 8px 0;
      padding-left: 24px;

      li {
        margin: 4px 0;
      }
    }
  }
}

.api-key-list {
  .api-key-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);

    &:last-child {
      border-bottom: none;
    }

    .key-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .key-name {
        font-weight: 600;
      }

      .key-prefix {
        font-family: 'JetBrains Mono', monospace;
        color: var(--el-text-color-secondary);
      }

      .key-created {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.inner-tabs {
  margin-bottom: 16px;
}
</style>
