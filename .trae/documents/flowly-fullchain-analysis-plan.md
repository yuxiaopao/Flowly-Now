# Flowly 项目全链路分析

> 本文档基于 CodeGraph + 多代理并行搜索对项目进行的全链路深度梳理结果。

---

## 一、项目概览

**Flowly** (e-Flowly) 是一个 **AI Agent 工作流编排平台**，采用全栈 Monorepo 架构。核心定位是让用户通过可视化拖拽 + 自然语言的方式构建 AI 工作流，支持多 Agent 协作、模型网关、RAG 知识检索、YOLO 训练等能力。

### 项目规模
- 前端：Vue 3 + Vite 5 + Element Plus，约 25 个视图模块、50+ 节点类型
- 后端：Django 5 + DRF + Celery + Channels，26 个 Django App
- 桌面端：Electron 28，GPU 加速 YOLO 训练
- 配套：毕业论文、PPT 展示、Docker 部署、CI/CD

---

## 二、技术栈总览

| 层级 | 前端 | 后端 | 基础设施 |
|------|------|------|----------|
| **框架** | Vue 3.4 (Composition API) | Django 5.0 | Docker Compose |
| **构建** | Vite 5.1 (port 5200) | - | Nginx |
| **UI 库** | Element Plus 2.5 + Vue Flow | - | - |
| **状态管理** | Pinia 2.1 (18 Stores) | - | - |
| **路由** | Vue Router 4.3 (60+ routes) | DRF Router | - |
| **HTTP** | Axios 1.6 (snake/camel 转换) | DRF (UnifiedJSONRenderer) | - |
| **样式** | SCSS + CSS Variables (4 主题) | - | - |
| **WebSocket** | 原生 WS + 自封装 | Django Channels + Daphne | Redis Channel Layer |
| **数据库** | - | MySQL 8 (mysqlclient) | Redis 7 |
| **任务队列** | - | Celery 5 + Flower | Redis Broker |
| **认证** | JWT + Cookie/Storage 双重 | JWT + DRF Token + Session | - |
| **AI** | - | LangChain + OpenAI + Anthropic | Ollama |
| **测试** | Vitest + Playwright (3 browsers) | pytest + pytest-django | - |

---

## 三、项目目录架构 (顶层)

```
e:\Flowly-now\
├── Backend/          # Django 后端 (26 个 App)
├── Frontend/         # Vue 3 前端
├── Desktop/          # Electron 桌面客户端
├── Docs/             # 项目文档 (API/部署/阶段计划/审计)
├── PPT/              # 参赛作品 PPT 生成工具
├── Thesis/           # 毕业论文
├── Scripts/          # 部署/训练脚本
├── docker/           # Docker 部署配置
├── tests/            # 多级测试 (后端/前端/E2E/NL 模块)
├── test-reports/     # 测试报告
├── AGENTS.md         # Agent 开发规范 (最完整)
├── .cursorrules      # Cursor 规则 (与 AGENTS.md 冗余)
├── .mcp.json         # MCP 服务器配置 (4 个服务)
└── .github/workflows/ # CI/CD pipeline
```

---

## 四、前端架构全链路

### 4.1 入口与布局系统

```
main.js → App.vue → 路由 meta.layout 驱动动态布局:
  ├── 'blank'    → <div> (Landing/登录/注册)
  ├── 'editor'   → EditorLayout (全屏工作流编辑器)
  ├── 'public'   → PublicLayout (居中卡片)
  └── 'default'  → AppLayout (侧边栏 + 顶栏 + 主内容区)
```

全局挂载组件：CommandPalette、ToastContainer、GlobalModal、ConfirmDialog、ErrorBoundary。

### 4.2 数据流链路

```
Vue 页面 → Composable (useWorkflow/useRequest/...) → Pinia Store (18个)
  → API 模块 (25个) → Axios 请求拦截器:
      1. pending 计数器 +1
      2. 注入 Bearer Token (Cookie + localStorage 双源)
      3. data 字段 camelCase → snake_case
  → 后端 REST API → 响应拦截器:
      4. 提取 {code, message, data} 中的 data 字段
      5. data 字段 snake_case → camelCase
      6. pending 计数器 -1
      7. 错误码映射 Toast 通知
  → Store/Composable 更新 → 视图响应式刷新
```

### 4.3 路由模块 (60+ routes, 5 公开 + 50+ 认证)

| 模块 | 路由数 | 核心页面 |
|------|--------|----------|
| 认证 | 5 | Landing/Login/Register/Forgot/Reset |
| 仪表盘 | 1 | Home |
| 工作流 | 7 | List/Editor/Detail/Execute/Diff/Trigger/Variable |
| Agent | 4 | List/Create/Debugger |
| NL 创建 | 1 | Creator (自然语言→工作流) |
| 知识库/RAG | 2 | Index/CollectionDetail |
| 数据集 | 4 | List/Detail/Recommend/Augmentation |
| 训练 | 4 | Progress/YOLO List/YOLO Dashboard/YOLO Project |
| 设置 | 10 | Profile/API Doc/Notifications/Billing/DesktopAgent... |
| 模板市场 | 3 | Marketplace/Detail/MyTemplates |
| 其他 | 8 | Monitoring/Analytics/Admin/CodeGraph/ApiExplorer/... |

### 4.4 Pinia Store 体系 (18 个)

| Store ID | 职责 |
|----------|------|
| app | 主题切换(4套)、侧边栏、设备检测、Toast/Modal/Confirm、面包屑 |
| auth | 登录/注册/登出/JWT Token 管理/用户信息 |
| workflow | 工作流 CRUD、节点/连线/画布状态、模型/工具列表 |
| execution | 执行全生命周期：同步/异步/流式、WS 实时状态、Token 统计 |
| agent | Agent CRUD、调试会话、SSE 流式对话 |
| nlWorkflow | NL→工作流 会话、SSE 流式生成、意图分析 |
| marketplace | 模板市场分页/筛选/安装/评分/发布 |
| tenant | 租户/团队、成员邀请/角色/任务 |
| gateway | AI 模型网关管理 |
| monitoring/analytics/billing/branding/integrations/prompt/rag/variables/codeGraph/yoloTraining | 各自业务领域 |

### 4.5 Composable 组合函数层 (9 个)

- **useWorkflow** — 工作流编辑器核心：节点/连线/UndoRedo 栈(50步)/自动保存(30s)/快捷键
- **useWebSocket** — 通用 WS 客户端：自动重连(5次)、心跳(30s)、消息路由
- **useRequest** — 通用请求 Hook：loading/error/data + Element Plus Loading
- **useCRUDStore** — 通用 CRUD Store 工厂函数
- **useForm** — 表单提交处理/字段验证/服务器错误映射
- **useAgent** — Agent 对话逻辑
- **useExecutionProgress** — 执行进度追踪
- **useExecutionCache** — 执行缓存管理
- **useTrainingWebSocket** — 训练进度 WS

### 4.6 API 模块 (25 个)

统一使用 `request` 对象 (Axios 实例) 发起请求。支持普通 HTTP + 流式(SSE via Fetch)双通道。

### 4.7 工作流编辑器核心能力
- 基于 @vue-flow/core，50+ 节点类型渲染组件
- DAG 自动布局（Kahn 拓扑分层）
- Schema 校验引擎（结构/连通性/节点配置/循环引用）
- 前后端数据格式互转（workflowTransform.js）
- 撤销/重做栈、自动保存、键盘快捷键

### 4.8 样式与主题系统
- SCSS 变量 + CSS Variables 双引擎
- 4 套主题：dark/light/pure-bw/high-contrast
- 100+ 原子工具类 (类似 Tailwind 风格)
- 响应式断点：768px / 1024px

---

## 五、后端架构全链路

### 5.1 Django App 清单 (26 个)

| App | 职责 |
|-----|------|
| config | 全局 settings/urls/constants/异常处理/admin |
| users | 用户模型、JWT 认证 |
| core | 审计日志、通知、工作区、健康检查 |
| workflows | **核心工作流引擎** (节点/边/执行/版本/导入导出/定时/WS) |
| agents | Agent 管理、多 Agent 编排、调试器 |
| nl_to_workflow | 自然语言→工作流 (LLM + Vector Store) |
| prompts | Prompt 模板管理 |
| tenants | 多租户/团队管理 |
| monitoring | 系统监控 (日志/性能/告警) |
| rag | RAG 知识检索 (向量存储/检索) |
| gateway | AI 模型网关 (OpenAI/Ollama 提供者 + 路由) |
| billing | 计费/订阅管理 |
| branding | 品牌定制 (白标) |
| marketplace | 工作流模板市场 |
| training | 模型训练 (YOLO + WS 实时进度) |
| codegraph | 代码图谱分析 |
| datasets/dataset_recommend/annotations/augmentation | 数据管理全流程 |
| integrations/templates/admin/website_generator/evaluation/features | 辅助模块 |

### 5.2 API 路由体系

```
/api/                  ← 健康检查/通知/审计
/api/v1/auth/          ← 用户认证
/api/v1/               ← 工作流 (核心)
/api/v1/datasets/      ← 数据集
/api/v1/agents/        ← Agent
/api/v1/nl-workflow/   ← NL 转工作流
/api/v1/gateway/       ← 模型网关
/api/v1/training/      ← 训练
/api/v1/codegraph/     ← 代码图谱
/api/schema/           ← OpenAPI Schema
/api/docs/             ← Swagger UI
/admin/                ← Jazzmin 美化后台
```

### 5.3 WebSocket 路由

4 个 App 的 WebSocket 组合：
- workflows — 工作流执行实时推送
- training — 训练进度实时推送
- codegraph — 代码图谱实时分析
- agents — Agent 调试会话

### 5.4 后端基础设施
- 数据库：MySQL (mysqlclient)
- 缓存/消息队列：Redis (django-redis + Celery broker)
- 异步任务：Celery Worker
- WSGI/ASGI：WSGI (HTTP) + Daphne (WebSocket)
- 统一响应格式：`{code, message, data}` (UnifiedJSONRenderer)
- 异常处理：`{code, message, data: null, errors}` (custom_exception_handler)

---

## 六、前后端交互全链路

```
Browser (localhost:5200)
  │
  ▼
Vite Dev Server → Vue 3 App
  │
  ├── HTTP (Axios, baseURL: VITE_API_URL+/api/v1)
  │   ├── 拦截器: Token 注入 + camelCase↔snake_case 转换
  │   ├── 成功: 提取 {code,message,data} 中的 data
  │   └── 失败: HTTP 状态码 → Toast 通知 (401 自动刷新 Token)
  │
  └── WebSocket (Channels)
      ├── /ws/execution/{id}/ — 执行实时进度
      ├── /ws/workflow/{id}/ — 多人协作编辑
      └── /ws/training/ — 训练进度
  │
  ▼
Django Backend (localhost:8000)
  ├── REST API (DRF) — {code, message, data} 统一格式
  ├── WebSocket (Daphne + Channels) — 实时推送
  ├── Celery Workers — 异步任务
  ├── Redis — 缓存/消息队列/Channel Layer
  └── MySQL — 持久化存储
```

---

## 七、部署架构

```
Docker Compose:
├── nginx          — 反向代理 (80/443)
├── frontend       — Nginx + 静态文件
├── backend        — Django + Daphne (ASGI)
├── redis          — 缓存/队列
├── celery_worker  — 异步任务
└── mysql          — 数据库
```

---

## 八、全链路数据流 (核心业务)

### 8.1 用户认证流
```
login() → POST /api/v1/auth/login/ → {access, refresh, user}
  → authStore: access_token → Cookie(1天) + localStorage
  → 所有后续请求自动注入 Authorization header
  → 401 → 拦截器自动 refresh_token → 重放请求
  → refresh 失败 → 清除 Token → 跳转 /login
```

### 8.2 工作流创建与执行流
```
创建工作流:
  WorkflowEditor → WorkflowCanvas → 拖拽节点 → PropertyPanel 配置
  → useWorkflow.save() → workflowStore → workflowAPI.create()
  → POST /api/v1/workflows/ → MySQL

执行工作流:
  workflowAPI.executeAsync(id) → POST /api/v1/workflows/{id}/execute/
  → 获得 executionId → ExecutionWebSocket.connect(id)
  → WS 事件流:
     execution_start → status='running'
     node_start → nodeStatusMap[id]='running'
     node_complete → nodeStatusMap[id]='completed'
     stream_output → streamingOutput 累加
     token_update → tokenStats 累加
     execution_complete → status='completed'
```

### 8.3 NL to Workflow 流
```
NLCreator → 用户输入自然语言 → POST /api/v1/nl-workflow/chat/
  → 后端 LLM (qwen2.5-coder:7b) + Vector Store (Chroma)
  → SSE 流式返回工作流 JSON → nlWorkflowStore → 实时渲染预览
  → 确认后 → workflowStore.create() → 保存为正式工作流
```

---

## 九、关键发现

### 冗余与重复
1. **规则文件三层冗余**：AGENTS.md、.cursorrules、.cursor/rules/global-rules.md
2. **Python 依赖文件冗余**：requirements.txt 与 requirements.in 几乎相同
3. **环境变量模板冗余**：6 个 .env.example 文件
4. **前端类型定义重复**：`PaginatedResponse`/`ListResponse` 在 api.ts 和 request.d.ts 中同时定义

### 配置集中度
- 前端：config/index.js 统一管理 (部分分页值仍为硬编码)
- 后端：config/constants.py 管理枚举常量
- 环境变量通过 .env 文件 + import.meta.env 读取

### 架构亮点
- 自动 camelCase ↔ snake_case 字段转换，前后端命名风格解耦
- Token 双重存储 + 401 无感刷新
- 18 个 Pinia Store 按领域拆分，职责清晰
- WebSocket 心跳保活 + 指数退避重连
- SSE 流式渲染 (NL/Agent/执行三个场景)
- 4 套完整主题系统，CSS Variables 驱动
