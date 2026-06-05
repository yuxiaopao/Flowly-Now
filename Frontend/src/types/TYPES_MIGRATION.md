# 前端 TypeScript 迁移指南

> 当前状态：**进行中** — 已完成 tsconfig.json + 新增 gateway/billing/rag/request 类型定义 + API JSDoc 注解

## 已完成工作

### 类型定义文件

| 文件 | 内容 | 状态 |
|------|------|------|
| `types/api.ts` | API 响应、分页、请求配置类型 | 已有 |
| `types/workflow.ts` | 工作流、节点、边类型（已重构消除重复） | 已有 |
| `types/execution.d.ts` | 执行状态、事件、日志类型 | 已有 |
| `types/nodes.d.ts` | 所有节点类型的配置接口 | 已有 |
| `types/agent.d.ts` | Agent、工具、消息类型 | 已有 |
| `types/trigger.ts` | 触发器类型 | 已有 |
| `types/variable.d.ts` | 变量类型 | 已有 |
| `types/index.ts` | 统一导出入口 | 已有 |
| `types/request.d.ts` | Request 工具层类型 | **新增** |
| `types/gateway.d.ts` | Gateway API 类型（ModelProvider, AIModel, UserAPIKey 等） | **新增** |
| `types/billing.d.ts` | Billing API 类型（PriceTier, Subscription, UsageSummary 等） | **新增** |
| `types/rag.d.ts` | RAG API 类型（VectorStore, Document, RAGPipeline 等） | **新增** |

### tsconfig.json

已创建 `Frontend/tsconfig.json` + `Frontend/tsconfig.node.json`，支持：
- `@/*` 路径别名（与 vite.config.js 同步）
- 严格类型检查（strict mode）
- Vue 单文件组件（`.vue`）
- 类型声明文件（`.d.ts`）

### API JSDoc 注解

| 文件 | 状态 |
|------|------|
| `api/gateway.js` | **已注解** — 所有函数含 `@returns` 和 `@param` |
| `api/billing.js` | **已注解** — 使用 `@typedef` + `@type` |
| `api/rag.js` | **已注解** — 使用 `@typedef` + `@type` |
| `api/agent.js` | **已注解** — 使用 `@typedef` + `@type` |
| `api/workflow.js` | 待注解 |
| `api/auth.js` | 待注解 |
| 其他 API 文件 | 待注解 |

## 类型使用示例

```javascript
// @ts-check
import type {
  GatewayHealth,
  PriceTier,
  Subscription,
  RAGPipeline,
  PaginatedResponse,
  ApiError,
} from '@/types'

// 使用类型注解
/** @type {PaginatedResponse<PriceTier>} */
const tiers = await billingApi.getPriceTiers()
```

## 剩余迁移任务

### 高优先级

1. **API 层类型注解**
   - [ ] `api/workflow.js` — WorkflowListParams, WorkflowCreateData 等
   - [ ] `api/auth.js` — LoginData, TokenResponse, User 等
   - [ ] `api/nl-workflow.js` — NLMessage, NLGenerationResult 等
   - [ ] `api/dataset.js` — Dataset, DatasetItem 等
   - [ ] `api/marketplace.js` — MarketplaceItem 等

2. **Store 层类型注解**
   - [ ] `stores/execution.js` — 添加 ExecutionState 类型
   - [ ] `stores/agent.js` — 添加 AgentState 类型
   - [ ] `stores/auth.js` — 添加 AuthState 类型
   - [ ] `stores/nlWorkflow.js` — 添加 NLWorkflowState 类型

3. **安装 TypeScript 依赖**
   ```bash
   cd Frontend
   npm install -D typescript @vue/tsconfig vue-tsc
   ```

4. **更新 package.json scripts**
   ```json
   {
     "scripts": {
       "type-check": "vue-tsc --noEmit",
       "build": "vue-tsc --noEmit && vite build"
     }
   }
   ```

### 中优先级

5. **清理 `// @ts-nocheck`**
   - [ ] `src/auto-imports.d.ts` — 移除 `// @ts-nocheck`
   - [ ] `src/components.d.ts` — 移除 `// @ts-nocheck`

6. **组件类型注解**
   - [ ] 关键视图组件（`views/`）
   - [ ] 工作流编辑器组件

### 低优先级

7. **渐进式 `.js` → `.ts` 迁移**
   - 从独立工具文件开始
   - 迁移 API 层
   - 迁移 Store 层
   - 最终迁移视图层

## 已知类型重复（已解决）

| 类型 | 解决方式 |
|------|----------|
| `ExecutionStatus` | 统一从 `execution.d.ts` 导出 |
| `NodeExecutionStatus` | 统一从 `execution.d.ts` 导出 |
| `ToolParameter` | 统一从 `agent.d.ts` 导出 |
| `WorkflowNode`/`WorkflowEdge` | 保留在 `workflow.ts`（workflow 专用） |

## 依赖安装

```bash
cd Frontend
npm install -D typescript @vue/tsconfig vue-tsc
```
