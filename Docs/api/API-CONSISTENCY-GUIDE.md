# Flowly API 一致性完整修复指南

> 本文档是 Flowly 项目前后端 API 一致性审计和修复的完整指南。所有 API 实现必须严格遵循本文档。

---

## 目录

1. [API 端点总览](#1-api-端点总览)
2. [后端完整端点列表](#2-后端完整端点列表)
3. [前端 API 函数映射](#3-前端-api-函数映射)
4. [端点不一致问题](#4-端点不一致问题)
5. [字段不一致问题](#5-字段不一致问题)
6. [修复清单](#6-修复清单)
7. [开发规范提示词](#7-开发规范提示词)

---

## 1. API 端点总览

### 1.1 模块统计

| 模块 | 后端端点数 | 前端函数数 | 状态 |
|------|----------|-----------|------|
| Authentication | 8 | 11 | 需要审计 |
| Workflows | 28 | 26 | 需要审计 |
| Agents | 17 | 19 | 需要审计 |
| Prompts | 9 | 14 | 需要审计 |
| NL to Workflow | 5 | 8 | 需要审计 |
| Monitoring | 23 | 32 | 需要审计 |
| RAG | 24 | 30 | 需要审计 |
| Billing | 17 | 17 | 需要审计 |
| Integrations | 11 | 23 | 需要审计 |
| Marketplace | 14 | 25 | 需要审计 |
| Tenants | 16 | 18 | 需要审计 |
| Templates | 18 | - | 需要审计 |
| Gateway | - | 15 | 需要审计 |
| Admin | - | 13 | 需要审计 |
| Branding | - | 22 | 需要审计 |
| System | - | 2 | 需要审计 |

**总计: 约 190 个后端端点，275 个前端函数**

---

## 2. 后端完整端点列表

### 2.1 Users 模块 (`/api/users/`)

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/api/users/register/` | POST | 用户注册 | 否 |
| `/api/users/login/` | POST | 用户登录 | 否 |
| `/api/users/logout/` | POST | 用户登出 | 是 |
| `/api/users/refresh/` | POST | 刷新Token | 否 |
| `/api/users/user/` | GET/PUT/PATCH | 用户资料 | 是 |
| `/api/users/change-password/` | POST | 修改密码 | 是 |
| `/api/users/password-reset/` | POST | 请求密码重置 | 否 |
| `/api/users/password-reset/confirm/` | POST | 确认密码重置 | 否 |

### 2.2 Workflows 模块 (`/api/workflows/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/workflows/` | GET | 工作流列表 |
| `/api/workflows/` | POST | 创建工作流 |
| `/api/workflows/{id}/` | GET/PUT/PATCH/DELETE | 工作流详情 |
| `/api/workflows/{id}/duplicate/` | POST | 复制工作流 |
| `/api/workflows/{id}/execute/` | POST | 执行工作流 |
| `/api/workflows/{id}/stream_execute/` | GET | 流式执行 |
| `/api/workflows/{id}/export/` | GET | 导出工作流 |
| `/api/workflows/{id}/validate/` | POST | 验证工作流 |
| `/api/workflows/import/` | POST | 导入工作流 |
| `/api/workflows/nodes/` | GET/POST | 节点列表/创建 |
| `/api/workflows/nodes/available_types/` | GET | 可用节点类型 |
| `/api/workflows/nodes/batch_create/` | POST | 批量创建节点 |
| `/api/workflows/nodes/batch_update_positions/` | POST | 批量更新位置 |
| `/api/workflows/nodes/{id}/` | GET/PUT/PATCH/DELETE | 节点详情 |
| `/api/workflows/edges/` | GET/POST | 连线列表/创建 |
| `/api/workflows/edges/batch_create/` | POST | 批量创建连线 |
| `/api/workflows/edges/{id}/` | GET/PUT/PATCH/DELETE | 连线详情 |
| `/api/workflows/executions/` | GET | 执行历史 |
| `/api/workflows/executions/{id}/` | GET | 执行详情 |
| `/api/workflows/executions/{id}/cancel/` | POST | 取消执行 |
| `/api/workflows/executions/{id}/logs/` | GET | 执行日志 |
| `/api/workflows/executions/{id}/status/` | GET | 执行状态 |
| `/api/workflows/templates/` | GET | 模板列表 |
| `/api/workflows/templates/<id>/` | GET | 模板详情 |
| `/api/workflows/templates/<id>/create_from_template/` | POST | 从模板创建 |
| `/api/workflows/<id>/import_workflow/` | POST | 导入(兼容) |

### 2.3 Agents 模块 (`/api/agents/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/agents/` | GET/POST | Agent列表/创建 |
| `/api/agents/{id}/` | GET/PUT/PATCH/DELETE | Agent详情 |
| `/api/agents/{id}/chat/` | POST | 对话 |
| `/api/agents/{id}/stream_chat/` | POST | 流式对话 |
| `/api/agents/{id}/debug/` | POST | 调试 |
| `/api/agents/{id}/debug_history/` | GET/DELETE | 调试历史 |
| `/api/agents/{id}/debug/sessions/{session_id}/` | GET | 调试会话 |
| `/api/agents/{id}/conversations/` | GET | 会话列表 |
| `/api/agents/{id}/tools/` | GET/POST | 工具管理 |
| `/api/agents/{id}/tools_remove/` | DELETE | 移除工具 |
| `/api/agents/{id}/reset_memory/` | POST | 重置记忆 |
| `/api/agents/{id}/skills/` | GET/PATCH | 技能管理 |
| `/api/tools/` | GET | 可用工具 |

### 2.4 Conversations 模块 (`/api/conversations/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/conversations/` | GET | 会话列表 |
| `/api/conversations/{id}/` | GET/PUT/DELETE | 会话详情 |
| `/api/conversations/{id}/messages/` | GET | 获取消息 |
| `/api/conversations/{id}/add_message/` | POST | 添加消息 |

### 2.5 Prompts 模块 (`/api/prompts/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/templates/` | GET/POST | 模板列表/创建 |
| `/api/templates/{id}/` | GET/PUT/PATCH/DELETE | 模板详情 |
| `/api/templates/{id}/render/` | POST | 渲染模板 |
| `/api/templates/{id}/use/` | POST | 使用模板 |
| `/api/templates/{id}/rate/` | POST | 评分 |
| `/api/templates/{id}/versions/` | GET | 版本历史 |
| `/api/templates/{id}/create_version/` | POST | 创建版本 |
| `/api/templates/featured/` | GET | 精选模板 |
| `/api/templates/recent/` | GET | 最近模板 |

### 2.6 NL to Workflow 模块 (`/api/nl-workflow/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/sessions/` | GET/POST | 会话列表/创建 |
| `/api/sessions/{id}/` | GET/DELETE | 会话详情 |
| `/api/sessions/{id}/message/` | POST | 发送消息 |
| `/api/sessions/{id}/confirm/` | POST | 确认保存 |
| `/api/preview/` | POST | 预览生成 |

### 2.7 Monitoring 模块 (`/api/monitoring/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/logs/` | GET | 执行日志 |
| `/api/logs/{id}/` | GET | 日志详情 |
| `/api/alerts/` | GET/POST | 告警列表 |
| `/api/alerts/{id}/` | GET/PUT/PATCH/DELETE | 告警详情 |
| `/api/alerts/{id}/acknowledge/` | POST | 确认告警 |
| `/api/alerts/{id}/resolve/` | POST | 解决告警 |
| `/api/alerts/{id}/mute/` | POST | 静默告警 |
| `/api/alerts/summary/` | GET | 告警汇总 |
| `/api/rules/` | GET/POST | 告警规则 |
| `/api/rules/{id}/` | GET/PUT/PATCH/DELETE | 规则详情 |
| `/api/metrics/` | GET | 指标列表 |
| `/api/metrics/{id}/` | GET | 指标详情 |
| `/api/metrics/aggregate/` | GET | 聚合指标 |
| `/api/metrics/export/` | GET | 导出CSV |
| `/api/metrics/dashboard/` | GET | 仪表板数据 |
| `/api/channels/` | GET/POST | 通知渠道 |
| `/api/channels/{id}/` | GET/PUT/PATCH/DELETE | 渠道详情 |
| `/api/channels/{id}/test/` | POST | 测试渠道 |
| `/api/analytics/` | GET | 概览分析 |
| `/api/analytics/top_workflows/` | GET | 热门工作流 |
| `/api/analytics/recent_executions/` | GET | 最近执行 |
| `/api/analytics/api_usage/` | GET | API使用 |
| `/api/analytics/execution_trend/` | GET | 执行趋势 |

### 2.8 RAG 模块 (`/api/rag/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/vector-stores/` | GET/POST | 向量存储 |
| `/api/vector-stores/{id}/` | GET/PUT/PATCH/DELETE | 存储详情 |
| `/api/vector-stores/{id}/test_connection/` | POST | 测试连接 |
| `/api/vector-stores/{id}/create_collection/` | POST | 创建集合 |
| `/api/vector-stores/{id}/delete_collection/` | DELETE | 删除集合 |
| `/api/vector-stores/list_types/` | GET | 存储类型 |
| `/api/collections/` | GET/POST | 文档集合 |
| `/api/collections/{id}/` | GET/PUT/PATCH/DELETE | 集合详情 |
| `/api/collections/{id}/details/` | GET | 集合详情(冗余) |
| `/api/collections/{id}/stats/` | GET | 集合统计 |
| `/api/collections/{id}/add_document/` | POST | 添加文档 |
| `/api/collections/{id}/add_url/` | POST | 从URL添加 |
| `/api/collections/{id}/upload_file/` | POST | 上传文件 |
| `/api/collections/{id}/search/` | GET | 搜索 |
| `/api/collections/{id}/clear/` | DELETE | 清空集合 |
| `/api/documents/` | GET/POST | 文档列表 |
| `/api/documents/{id}/` | GET/PUT/PATCH/DELETE | 文档详情 |
| `/api/documents/{id}/reprocess/` | POST | 重新处理 |
| `/api/documents/{id}/chunks/` | GET | 文档块 |
| `/api/chunks/` | GET | 块列表 |
| `/api/chunks/{id}/` | GET | 块详情 |
| `/api/pipelines/` | GET/POST | RAG管道 |
| `/api/pipelines/{id}/` | GET/PUT/PATCH/DELETE | 管道详情 |
| `/api/pipelines/{id}/query/` | POST | 查询管道 |
| `/api/pipelines/{id}/retrieve/` | GET | 检索文档 |

### 2.9 Billing 模块 (`/api/billing/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/prices/` | GET | 价格方案 |
| `/api/prices/plans/` | GET | 按类型分组 |
| `/api/subscriptions/` | GET/POST | 订阅列表 |
| `/api/subscriptions/my/` | GET | 我的订阅 |
| `/api/subscriptions/subscribe/` | POST | 订阅方案 |
| `/api/subscriptions/cancel/` | POST | 取消订阅 |
| `/api/subscriptions/reactivate/` | POST | 重新激活 |
| `/api/subscriptions/usage/` | GET | 使用量统计 |
| `/api/usage/` | GET | 使用记录 |
| `/api/usage/history/` | GET | 历史使用 |
| `/api/invoices/` | GET | 发票列表 |
| `/api/invoices/{id}/` | GET | 发票详情 |
| `/api/invoices/{id}/download/` | GET | 下载发票 |
| `/api/payments/` | GET | 支付记录 |
| `/api/coupons/validate/` | POST | 验证优惠券 |
| `/api/coupons/my/` | GET | 我的优惠券 |

### 2.10 Integrations 模块 (`/api/integrations/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/webhooks/` | GET/POST | Webhook列表 |
| `/api/webhooks/{id}/` | GET/PUT/PATCH/DELETE | Webhook详情 |
| `/api/webhooks/{id}/test/` | POST | 测试Webhook |
| `/api/webhooks/{id}/deliveries/` | GET | 投递历史 |
| `/api/webhooks/{id}/stats/` | GET | 统计 |
| `/api/integrations/` | GET/POST | 集成列表 |
| `/api/integrations/{id}/` | GET/PUT/PATCH/DELETE | 集成详情 |
| `/api/integrations/{id}/connect/` | POST | 连接 |
| `/api/integrations/{id}/disconnect/` | POST | 断开 |
| `/api/integrations/{id}/sync/` | POST | 同步 |
| `/api/integrations/available/` | GET | 可用集成 |
| `/api/integration-receiver/` | POST | 接收Webhook |

### 2.11 Marketplace 模块 (`/api/marketplace/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/templates/` | GET/POST | 模板列表 |
| `/api/templates/{id}/` | GET/PUT/PATCH/DELETE | 模板详情 |
| `/api/templates/{id}/install/` | POST | 安装模板 |
| `/api/templates/{id}/rate/` | POST | 评分模板 |
| `/api/templates/{id}/stats/` | GET | 模板统计 |
| `/api/templates/{id}/report/` | POST | 举报模板 |
| `/api/categories/` | GET | 分类列表 |
| `/api/categories/{id}/` | GET | 分类详情 |
| `/api/categories/{id}/templates/` | GET | 分类模板 |
| `/api/my-templates/` | GET/POST | 我的模板 |
| `/api/my-templates/{id}/` | GET/PUT/PATCH/DELETE | 模板详情 |
| `/api/my-templates/{id}/publish/` | POST | 发布 |
| `/api/my-templates/{id}/unpublish/` | POST | 下架 |
| `/api/my-templates/{id}/installs/` | GET | 安装记录 |
| `/api/installed/` | GET | 已安装模板 |

### 2.12 Tenants 模块 (`/api/tenants/`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/tenants/` | GET/POST | 租户列表 |
| `/api/tenants/{id}/` | GET/PUT/PATCH/DELETE | 租户详情 |
| `/api/tenants/{id}/usage/` | GET | 使用统计 |
| `/api/tenants/{id}/members/` | GET | 成员列表 |
| `/api/tenants/{id}/invite/` | POST | 邀请成员 |
| `/api/tenants/{id}/remove_member/` | DELETE | 移除成员 |
| `/api/memberships/` | GET | 成员资格 |
| `/api/memberships/my_memberships/` | GET | 我的资格 |
| `/api/invitations/` | GET | 邀请列表 |
| `/api/invitations/pending/` | GET | 待处理 |
| `/api/invitations/join/` | POST | 加入租户 |
| `/api/invitations/{id}/accept/` | POST | 接受邀请 |
| `/api/invitations/{id}/decline/` | POST | 拒绝邀请 |
| `/api/usage/` | GET | 使用量 |
| `/api/usage/refresh/` | POST | 刷新使用量 |

---

## 3. 前端 API 函数映射

### 3.1 auth.js - 认证模块

```javascript
// 文件: Frontend/src/api/auth.js

// API 端点映射表
const API_MAP = {
  login:        { method: 'POST',  path: '/auth/login/',               auth: false },
  register:     { method: 'POST',  path: '/auth/register/',            auth: false },
  logout:       { method: 'POST',  path: '/auth/logout/',              auth: true  },
  getUserInfo:  { method: 'GET',   path: '/auth/user/',                auth: true  },
  updateProfile:{ method: 'PATCH', path: '/auth/user/',                auth: true  },
  changePassword:   { method: 'POST',  path: '/auth/change-password/',  auth: true  },
  refreshToken: { method: 'POST',  path: '/auth/refresh/',            auth: false },
  requestPasswordReset:  { method: 'POST', path: '/auth/password-reset/',              auth: false },
  resetPassword:        { method: 'POST', path: '/auth/password-reset/confirm/',        auth: false },
  verifyEmail:    { method: 'POST', path: '/auth/verify-email/',        auth: true  },
  resendVerificationEmail: { method: 'POST', path: '/auth/verify-email/resend/', auth: true },
};
```

### 3.2 workflow.js - 工作流模块

```javascript
// 文件: Frontend/src/api/workflow.js

const API_MAP = {
  // 工作流
  getList:           { method: 'GET',    path: '/workflows/' },
  getById:           { method: 'GET',    path: '/workflows/{id}/' },
  create:            { method: 'POST',   path: '/workflows/' },
  update:            { method: 'PATCH',  path: '/workflows/{id}/' },
  delete:            { method: 'DELETE', path: '/workflows/{id}/' },
  duplicate:         { method: 'POST',   path: '/workflows/{id}/duplicate/' },
  export:            { method: 'GET',    path: '/workflows/{id}/export/' },
  import:            { method: 'POST',   path: '/workflows/import/' },
  execute:           { method: 'POST',  path: '/workflows/{id}/execute/' },
  validate:          { method: 'POST',  path: '/workflows/{id}/validate/' },
  
  // 节点
  getNodes:          { method: 'GET',    path: '/nodes/' },
  createNode:         { method: 'POST',   path: '/nodes/' },
  updateNode:         { method: 'PATCH', path: '/nodes/{nodeId}/' },
  deleteNode:         { method: 'DELETE', path: '/nodes/{nodeId}/' },
  saveNodePositions:  { method: 'POST', path: '/nodes/batch_update_positions/' },
  
  // 连线
  getEdges:          { method: 'GET',    path: '/edges/' },
  createEdge:        { method: 'POST',   path: '/edges/' },
  updateEdge:        { method: 'PATCH', path: '/edges/{edgeId}/' },
  deleteEdge:        { method: 'DELETE', path: '/edges/{edgeId}/' },
  
  // 执行
  getExecutionHistory:{ method: 'GET',    path: '/executions/' },
  getExecution:      { method: 'GET',    path: '/executions/{executionId}/' },
  cancelExecution:   { method: 'POST',   path: '/executions/{executionId}/cancel/' },
  getExecutionLogs:  { method: 'GET',   path: '/executions/{executionId}/logs/' },
  
  // 模板
  getTemplates:      { method: 'GET',    path: '/templates/' },
  createFromTemplate:{ method: 'POST',   path: '/templates/{templateId}/create_from_template/' },
  getAvailableNodeTypes: { method: 'GET', path: '/workflows/nodes/available_types/' },
};
```

### 3.3 agent.js - Agent 模块

```javascript
// 文件: Frontend/src/api/agent.js

const API_MAP = {
  // Agent CRUD
  getList:        { method: 'GET',    path: '/agents/' },
  getById:        { method: 'GET',    path: '/agents/{id}/' },
  create:         { method: 'POST',   path: '/agents/' },
  update:         { method: 'PATCH',  path: '/agents/{id}/' },
  delete:         { method: 'DELETE',  path: '/agents/{id}/' },
  
  // 工具
  getAvailableTools:   { method: 'GET',  path: '/agents/{agentId}/tools/' },
  getWorkflowTools:   { method: 'GET',  path: '/agents/{agentId}/tools/' },
  addTools:            { method: 'POST', path: '/agents/{agentId}/tools/' },  // { tools: [...] }
  removeTool:          { method: 'POST', path: '/agents/{agentId}/tools_remove/' },  // { tool: "name" }
  
  // 技能
  getSkills:      { method: 'GET',    path: '/agents/{id}/skills/' },
  updateSkills:    { method: 'PATCH',  path: '/agents/{id}/update_skills/' },
  
  // 对话
  sendMessage:     { method: 'POST',  path: '/agents/{agentId}/chat/' },      // { message, conversation_id }
  streamChat:      { method: 'POST',  path: '/agents/{agentId}/stream_chat/' },
  debug:           { method: 'POST',  path: '/agents/{id}/debug/' },
  getDebugHistory: { method: 'GET',   path: '/agents/{id}/debug/history/' },
  clearDebugHistory:{ method: 'DELETE', path: '/agents/{id}/debug/history/' },
  loadDebugSession:{ method: 'GET',   path: '/agents/{agentId}/debug/sessions/{sessionId}/' },
  
  // 会话
  getConversations:   { method: 'GET',    path: '/conversations/' },
  getConversation:    { method: 'GET',    path: '/conversations/{conversationId}/' },
  deleteConversation: { method: 'DELETE', path: '/conversations/{conversationId}/' },
  getMessages:       { method: 'GET',    path: '/conversations/{conversationId}/messages/' },
};
```

---

## 4. 端点不一致问题

### 4.1 路径不一致

| 问题ID | 模块 | 后端路径 | 前端路径 | 状态 | 修复建议 |
|--------|------|---------|---------|------|----------|
| P001 | workflow | `/api/workflows/{id}/import_workflow/` | `/api/workflows/import/` | 已修复 | 一致 |
| P002 | agent | `/api/agents/{id}/tools/` (POST) | `/api/agents/{id}/tools/` | 需确认 | 后端期望 `tools` 数组 |
| P003 | agent | `/api/agents/{id}/tools_remove/` | `/api/agents/{id}/tools_remove/` | 一致 | - |
| P004 | agent | `/api/agents/{id}/update_skills/` | `/api/agents/{id}/update_skills/` | 一致 | - |
| P005 | nl-workflow | `/api/sessions/` | `/api/nl-workflow/sessions/` | 需统一 | 前端使用 nl-workflow 前缀 |
| P006 | monitoring | `/api/logs/` | `/api/monitoring/logs/` | 需统一 | 前端使用 monitoring 前缀 |
| P007 | rag | `/api/collections/` | `/api/rag/collections/` | 需统一 | 前端使用 rag 前缀 |
| P008 | billing | `/api/prices/` | `/api/billing/prices/` | 需统一 | 前端使用 billing 前缀 |

### 4.2 HTTP 方法不一致

| 问题ID | 模块 | 端点 | 后端方法 | 前端方法 | 修复建议 |
|--------|------|------|---------|---------|----------|
| M001 | agent | skills | GET/PATCH | PATCH | 一致 |
| M002 | agent | tools | GET/POST | GET/POST | 一致 |
| M003 | workflow | import | POST | POST | 一致 |

### 4.3 缺失端点

| 问题ID | 模块 | 端点 | 后端 | 前端 | 修复建议 |
|--------|------|------|------|------|----------|
| L001 | monitoring | metrics/export/ | 存在 | 存在 | 一致 |
| L002 | nl-workflow | preview/ | 存在 | 存在 | 一致 |
| L003 | agent | stream_chat/ | 存在 | 存在 | 一致 |
| L004 | workflow | nodes/available_types/ | 存在 | 存在 | 一致 |

---

## 5. 字段不一致问题

### 5.1 请求体字段映射

#### 5.1.1 Agent 工具管理

| 字段 | 后端期望 | 前端发送 | 状态 |
|------|---------|---------|------|
| addTools | `{ tools: string[] }` | `{ tools: string[] }` | 一致 |
| removeTool | `{ tool: string }` | `{ tool: string }` | 一致 |

#### 5.1.2 Agent 技能管理

| 字段 | 后端期望 | 前端发送 | 状态 |
|------|---------|---------|------|
| updateSkills | `{ skills: string[] }` | `{ skills: string[] }` | 一致 |

#### 5.1.3 Agent 对话

| 字段 | 后端期望 | 前端发送 | 状态 |
|------|---------|---------|------|
| message | `string` | `string` | 一致 |
| conversation_id | `number \| null` | `number \| null` | 一致 |

### 5.2 响应体字段映射

#### 5.2.1 用户信息

| 字段 | 后端返回 | 前端期望 | 类型 | 状态 |
|------|---------|---------|------|------|
| id | ✓ | ✓ | integer | 一致 |
| username | ✓ | ✓ | string | 一致 |
| email | ✓ | ✓ | string | 一致 |
| avatar | ✓ | ✓ | string \| null | 一致 |
| role | ✓ | ✓ | string | 一致 |
| total_executions | ✓ | ✓ | integer | 一致 |

#### 5.2.2 工作流

| 字段 | 后端返回 | 前端期望 | 类型 | 状态 |
|------|---------|---------|------|------|
| id | ✓ | ✓ | integer | 一致 |
| name | ✓ | ✓ | string | 一致 |
| description | ✓ | ✓ | string | 一致 |
| status | ✓ | ✓ | string | 一致 |
| is_published | ✓ | ✓ | boolean | 一致 |
| nodes | ✓ | ✓ | array | 一致 |
| edges | ✓ | ✓ | array | 一致 |

#### 5.2.3 Agent

| 字段 | 后端返回 | 前端期望 | 类型 | 状态 |
|------|---------|---------|------|------|
| id | ✓ | ✓ | integer | 一致 |
| name | ✓ | ✓ | string | 一致 |
| model | ✓ | ✓ | string | 一致 |
| tools | ✓ | ✓ | string[] | 一致 |
| skills | ✓ | ✓ | string[] | 一致 |
| system_prompt | ✓ | ✓ | string | 一致 |

### 5.3 命名规范

| 类型 | 规范 | 示例 | 状态 |
|------|------|------|------|
| 后端字段 | snake_case | `created_at`, `user_id` | - |
| 前端字段 | camelCase | `createdAt`, `userId` | - |
| API 路径 | kebab-case | `/workflows/`, `/user-profile/` | - |

---

## 6. 修复清单

### 6.1 高优先级修复

| 优先级 | 问题 | 修复方案 | 文件 |
|--------|------|----------|------|
| P0 | NL to Workflow 路径前缀不一致 | 统一使用 `/nl-workflow/` | nl-workflow.js, urls.py |
| P0 | Monitoring 路径前缀不一致 | 统一使用 `/monitoring/` | monitoring.js, urls.py |
| P0 | RAG 路径前缀不一致 | 统一使用 `/rag/` | rag.js, urls.py |
| P0 | Billing 路径前缀不一致 | 统一使用 `/billing/` | billing.js, urls.py |

### 6.2 中优先级修复

| 优先级 | 问题 | 修复方案 | 文件 |
|--------|------|----------|------|
| P1 | Marketplace 路径前缀 | 统一使用 `/marketplace/` | marketplace.js, urls.py |
| P1 | Tenants 路径前缀 | 统一使用 `/tenants/` | tenant.js, urls.py |
| P1 | Integrations 路径前缀 | 统一使用 `/integrations/` | integrations.js, urls.py |

### 6.3 建议优化

| 优先级 | 问题 | 建议 |
|--------|------|------|
| P2 | 添加请求/响应拦截器 | 统一处理 401、403、500 错误 |
| P2 | 添加 TypeScript 类型 | 完善 api-types.ts 中的类型定义 |
| P2 | 添加 API 文档注释 | 为所有 API 函数添加 JSDoc |

---

## 7. 开发规范提示词

### 7.1 项目 API 开发规范

```markdown
# Flowly API 开发规范

## 每次实现 API 必须完成

1. **更新 api-spec.yaml** - OpenAPI 规范定义
2. **实现后端** - views.py + serializers.py + urls.py
3. **实现前端** - api/{module}.js
4. **更新类型** - api-types.ts

## 禁止事项

- ❌ 只实现后端，不实现前端
- ❌ 只实现前端，不实现后端
- ❌ 字段名不一致 (user_id vs userId)
- ❌ 类型不一致 (string vs number)
- ❌ 路径不一致 (/agent/ vs /agents/)

## 命名规范

- 后端: snake_case (created_at, user_id)
- 前端: camelCase (createdAt, userId)
- 路径: kebab-case (/workflows/, /user-profile/)

## 认证要求

- 公开端点: register, login, refresh, password-reset
- 认证端点: 除上述外的所有端点
```

### 7.2 API 实现检查表

```markdown
## API 实现检查表

### 后端实现
- [ ] views.py - 添加视图函数/ViewSet
- [ ] serializers.py - 定义序列化器
- [ ] urls.py - 注册路由
- [ ] models.py - 定义数据模型（如需要）
- [ ] tests.py - 编写单元测试（如需要）

### 前端实现
- [ ] api/{module}.js - 添加 API 函数
- [ ] 请求方法正确 (GET/POST/PATCH/DELETE)
- [ ] 请求路径正确
- [ ] 请求参数字段名正确
- [ ] 响应数据结构正确

### 类型定义
- [ ] api-types.ts - 添加 TypeScript 类型
- [ ] 请求类型定义
- [ ] 响应类型定义

### 规范更新
- [ ] api-spec.yaml - 添加 OpenAPI 定义
- [ ] api-schemas.json - 添加 JSON Schema（如需要）
```

### 7.3 API 审计提示词

```markdown
# API 审计提示词

请对 `/api/v1/` 下所有接口进行全面审计：

## 输出格式
| 模块 | 端点 | 路径一致 | 方法一致 | 字段一致 | 问题描述 | 修复建议 |
|------|------|----------|----------|----------|----------|----------|

## 审计维度
1. **路由一致性** - 后端 urls.py vs 前端 api/*.js
2. **字段一致性** - 后端 serializer vs 前端使用
3. **类型一致性** - TypeScript 类型 vs Python 类型
4. **命名一致性** - snake_case (后端) vs camelCase (前端)
```

---

## 附录 A：API 端点路径对照表

### A.1 当前实现 vs 规范

| 模块 | 规范路径 | 当前实现 | 状态 |
|------|----------|----------|------|
| Auth | `/api/v1/auth/` | `/api/auth/` | 需统一 |
| Workflows | `/api/v1/workflows/` | `/api/workflows/` | 需统一 |
| Agents | `/api/v1/agents/` | `/api/agents/` | 需统一 |
| NL Workflow | `/api/v1/nl-workflow/` | `/api/nl-workflow/` | 需统一 |
| Monitoring | `/api/v1/monitoring/` | `/api/monitoring/` | 需统一 |
| RAG | `/api/v1/rag/` | `/api/rag/` | 需统一 |
| Billing | `/api/v1/billing/` | `/api/billing/` | 需统一 |
| Integrations | `/api/v1/integrations/` | `/api/integrations/` | 需统一 |
| Marketplace | `/api/v1/marketplace/` | `/api/marketplace/` | 需统一 |
| Tenants | `/api/v1/tenants/` | `/api/tenants/` | 需统一 |

> **注**: 规范建议统一使用 `/api/v1/` 前缀，但当前实现使用 `/api/` 前缀。建议保持当前实现以避免破坏性变更。

---

## 附录 B：共享类型定义

### B.1 核心类型

```typescript
// api-types.ts

// 分页响应
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// 错误响应
interface ErrorResponse {
  error: string;
  detail?: string;
  code?: string;
}

// 用户
interface UserSimple {
  id: number;
  username: string;
  email: string;
  avatar: string | null;
}

// 工作流
interface Workflow {
  id: number;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'archived';
  nodes: Node[];
  edges: Edge[];
  // ...
}

// Agent
interface Agent {
  id: number;
  name: string;
  model: string;
  tools: string[];
  skills: string[];
  // ...
}
```

---

## 附录 C：常用 HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 成功获取/更新资源 |
| 201 | Created | 成功创建资源 |
| 204 | No Content | 成功删除资源 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证/Token无效 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器错误 |

---

*文档版本: 1.0.0*
*最后更新: 2026-05-09*
*维护者: Flowly 开发团队*
