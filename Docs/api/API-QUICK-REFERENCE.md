# Flowly API 快速参考卡

> 打印此页或保存为浏览器书签，方便快速查阅

---

## API 基础

```
Base URL: /api/v1
认证方式: Bearer Token (JWT)
Content-Type: application/json
```

---

## 认证端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/auth/login/` | POST | 否 | `{username, password}` |
| `/auth/register/` | POST | 否 | `{username, email, password, password_confirm}` |
| `/auth/refresh/` | POST | 否 | `{refresh}` |
| `/auth/user/` | GET | 是 | - |
| `/auth/change-password/` | POST | 是 | `{old_password, new_password, new_password_confirm}` |

---

## 工作流端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/workflows/` | GET | 是 | - |
| `/workflows/` | POST | 是 | `{name, description}` |
| `/workflows/{id}/` | GET/PATCH/DELETE | 是 | `{name, status}` |
| `/workflows/{id}/execute/` | POST | 是 | `{inputs, is_async}` |
| `/workflows/{id}/duplicate/` | POST | 是 | - |
| `/workflows/{id}/export/` | GET | 是 | - |
| `/workflows/import/` | POST | 是 | `{workflow_json}` |
| `/workflows/nodes/` | GET/POST | 是 | `{workflow, node_type, config}` |
| `/workflows/edges/` | GET/POST | 是 | `{source, target}` |
| `/workflows/executions/` | GET | 是 | - |
| `/workflows/executions/{id}/cancel/` | POST | 是 | - |

---

## Agent 端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/agents/` | GET/POST | 是 | `{name, model}` |
| `/agents/{id}/` | GET/PATCH/DELETE | 是 | `{name, system_prompt}` |
| `/agents/{id}/chat/` | POST | 是 | `{message, conversation_id}` |
| `/agents/{id}/stream_chat/` | POST | 是 | `{message}` |
| `/agents/{id}/tools/` | GET/POST | 是 | `{tools: [...]}` |
| `/agents/{id}/tools_remove/` | POST | 是 | `{tool}` |
| `/agents/{id}/skills/` | GET | 是 | - |
| `/agents/{id}/update_skills/` | PATCH | 是 | `{skills: [...]}` |
| `/agents/{id}/debug/` | POST | 是 | `{message}` |
| `/conversations/` | GET | 是 | - |

---

## NL 工作流端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/nl-workflow/sessions/` | GET/POST | 是 | `{description, name}` |
| `/nl-workflow/sessions/{id}/` | GET/DELETE | 是 | - |
| `/nl-workflow/sessions/{id}/message/` | POST | 是 | `{message}` |
| `/nl-workflow/sessions/{id}/confirm/` | POST | 是 | - |
| `/nl-workflow/preview/` | POST | 是 | `{description}` |

---

## 监控端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/monitoring/logs/` | GET | 是 | - |
| `/monitoring/alerts/` | GET/POST | 是 | `{name, condition}` |
| `/monitoring/alerts/{id}/acknowledge/` | POST | 是 | - |
| `/monitoring/alerts/{id}/resolve/` | POST | 是 | `{note}` |
| `/monitoring/rules/` | GET/POST | 是 | `{name, threshold}` |
| `/monitoring/metrics/` | GET | 是 | - |
| `/monitoring/metrics/dashboard/` | GET | 是 | - |
| `/monitoring/metrics/export/` | GET | 是 | - |
| `/monitoring/channels/` | GET/POST | 是 | `{name, type}` |

---

## RAG 端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/rag/vector-stores/` | GET/POST | 是 | `{name, provider}` |
| `/rag/collections/` | GET/POST | 是 | `{name}` |
| `/rag/collections/{id}/add_document/` | POST | 是 | `{title, content}` |
| `/rag/collections/{id}/query/` | POST | 是 | `{query, top_k}` |
| `/rag/pipelines/` | GET/POST | 是 | `{name}` |
| `/rag/pipelines/{id}/query/` | POST | 是 | `{query}` |

---

## 计费端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/billing/prices/plans/` | GET | 是 | - |
| `/billing/subscriptions/my/` | GET | 是 | - |
| `/billing/subscriptions/subscribe/` | POST | 是 | `{plan_type}` |
| `/billing/subscriptions/usage/` | GET | 是 | - |
| `/billing/invoices/` | GET | 是 | - |

---

## 集成端点

| 端点 | 方法 | 认证 | 请求体 |
|------|------|------|--------|
| `/integrations/webhooks/` | GET/POST | 是 | `{name, url, events}` |
| `/integrations/webhooks/{id}/test/` | POST | 是 | - |
| `/integrations/integrations/` | GET/POST | 是 | `{name, type}` |
| `/integrations/integrations/{id}/connect/` | POST | 是 | - |

---

## 常用响应格式

### 分页响应
```json
{
  "count": 100,
  "next": "/api/v1/workflows/?page=2",
  "previous": null,
  "results": [...]
}
```

### 错误响应
```json
{
  "error": "Validation error",
  "detail": "name: This field is required."
}
```

---

## 状态码速查

| 状态码 | 含义 | 何时使用 |
|--------|------|----------|
| 200 | OK | 成功获取/更新 |
| 201 | Created | 成功创建 |
| 204 | No Content | 成功删除 |
| 400 | Bad Request | 参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 500 | Server Error | 服务器错误 |

---

## 字段命名转换

```
后端 → 前端 (自动转换)

created_at → createdAt
updated_at → updatedAt
user_id → userId
is_active → isActive
node_count → nodeCount
```

---

## 请求示例

### 登录
```javascript
POST /auth/login/
{
  "username": "user@example.com",
  "password": "password123"
}
```

### 创建工作流
```javascript
POST /workflows/
{
  "name": "My Workflow",
  "description": "A test workflow"
}
```

### 执行工作流
```javascript
POST /workflows/1/execute/
{
  "inputs": { "user_input": "Hello" },
  "is_async": false
}
```

### Agent 对话
```javascript
POST /agents/1/chat/
{
  "message": "Hello, how are you?",
  "conversation_id": null
}
```

### 流式对话
```javascript
POST /agents/1/stream_chat/
{ "message": "Hello" }
// 响应: text/event-stream
```

---

## 前端 API 调用示例

```javascript
import { workflowApi } from '@/api/workflow'
import { agentApi } from '@/api/agent'

// 获取工作流列表
const workflows = await workflowApi.getList({ page: 1, page_size: 20 })

// 创建工作流
const workflow = await workflowApi.create({ name: 'New Workflow' })

// Agent 对话
const response = await agentApi.sendMessage(1, { 
  message: 'Hello',
  conversation_id: null 
})

// 流式对话
agentApi.streamChat(1, { message: 'Hello' })
  .then(response => {
    // 处理流式响应
  })
```

---

## 类型定义示例

```typescript
// api-types.ts

interface Workflow {
  id: number;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused';
  nodes: Node[];
  edges: Edge[];
  created_at: string;  // snake_case
  updated_at: string;
}

interface Agent {
  id: number;
  name: string;
  model: string;
  tools: string[];
  skills: string[];
  system_prompt?: string;
  temperature: number;
}
```

---

*版本: 1.0.0 | 更新: 2026-05-09*
