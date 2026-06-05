# Flowly 项目结构详解

## 项目概述

Flowly 是一个**可视化 AI 工作流编排平台**，用于构建、部署和管理 AI 驱动的自动化工作流。

## 技术栈

### 前端
- **框架**: Vue 3 + Vite
- **语言**: TypeScript
- **状态管理**: Pinia
- **UI 组件库**: Element Plus
- **可视化编辑器**: Vue Flow
- **图表**: ECharts

### 后端
- **框架**: Django 5 + Django REST Framework
- **异步任务**: Celery
- **实时通信**: Django Channels (WebSocket)
- **数据库**: MySQL 8.0+
- **缓存/消息队列**: Redis 7+

### AI 集成
- LangChain
- OpenAI
- Anthropic

---

## 后端结构 (Backend/)

```
Backend/
├── config/              # Django 配置
│   ├── settings.py      # 主配置
│   ├── urls.py          # 主路由
│   ├── asgi.py          # ASGI 配置 (WebSocket)
│   └── wsgi.py          # WSGI 配置
│
├── 核心业务模块
│   ├── workflows/       # 工作流模块 (核心)
│   │   ├── models.py    # 工作流数据模型
│   │   ├── views.py     # API 视图
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── consumers.py # WebSocket 消费者
│   │   ├── signals.py   # Django 信号
│   │   ├── import_export.py
│   │   ├── services/    # 业务逻辑
│   │   │   ├── workflow_executor.py  # 工作流执行器
│   │   │   ├── tool_executor.py      # 工具执行器
│   │   │   ├── langchain_service.py  # LangChain 集成
│   │   │   ├── monitoring.py         # 监控服务
│   │   │   ├── context.py            # 执行上下文
│   │   │   └── error_handler.py      # 错误处理
│   │   └── migrations/  # 数据库迁移
│   │
│   ├── agents/          # AI Agent 模块
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── engine.py    # Agent 引擎
│   │   ├── debugger.py  # 调试器
│   │   ├── multi_agent.py # 多 Agent 支持
│   │   └── migrations/
│   │
│   ├── nl_to_workflow/  # 自然语言生成工作流
│   │   ├── models.py
│   │   ├── services.py
│   │   └── migrations/
│   │
│   ├── gateway/         # LLM 网关 (多模型支持)
│   │   ├── providers/   # 不同 LLM 提供商
│   │   │   ├── base.py           # 基类
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   └── registry.py       # 提供商注册表
│   │   ├── serializers.py
│   │   └── migrations/
│   │
│   ├── rag/             # RAG (检索增强生成)
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── prompts/         # 提示词管理
│   │   ├── models.py
│   │   ├── views.py
│   │   └── serializers.py
│   │
│   ├── monitoring/      # 监控模块
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── tasks.py     # Celery 任务
│   │   └── urls.py
│   │
│   ├── billing/         # 计费模块
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── tenants/         # 多租户支持
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── users/           # 用户管理
│   │   ├── models.py
│   │   └── views.py
│   │
│   ├── integrations/    # 第三方集成
│   │   ├── models.py
│   │   └── serializers.py
│   │
│   ├── marketplace/     # 市场模块
│   │   ├── models.py
│   │   └── serializers.py
│   │
│   ├── branding/        # 品牌定制
│   │   └── admin.py
│   │
│   └── admin/           # 后台管理
│       └── views.py
│
├── core/                # 核心模块
│   └── models/
│       └── workspace.py # 工作空间模型
│
├── utils/               # 工具函数
├── scripts/             # 脚本
├── templates/           # 模板
├── static/              # 静态文件
├── media/               # 媒体文件
├── logs/                # 日志
│
├── manage.py            # Django 管理脚本
├── requirements.txt     # Python 依赖
├── pytest.ini           # 测试配置
├── conftest.py          # 测试配置
└── .env                 # 环境变量
```

### 后端关键模块说明

| 模块 | 功能 |
|------|------|
| **workflows** | 工作流的 CRUD、执行、版本控制 |
| **agents** | AI Agent 创建、管理、调试 |
| **gateway** | 统一 LLM 接口，支持 OpenAI、Anthropic 等 |
| **nl_to_workflow** | 用自然语言描述自动生成工作流 |
| **rag** | 知识库检索增强生成 |
| **monitoring** | 工作流执行监控、日志记录 |
| **billing** | 使用量计费和配额管理 |
| **tenants** | 多租户隔离支持 |

---

## 前端结构 (Frontend/src/)

```
Frontend/src/
├── App.vue              # 根组件
├── main.js              # 入口文件
│
├── api/                 # API 模块
│   ├── index.js         # API 入口
│   ├── auth.js          # 认证 API
│   ├── agent.js         # Agent API
│   ├── gateway.js       # 网关 API
│   ├── monitoring.js    # 监控 API
│   ├── rag.js           # RAG API
│   ├── billing.js       # 计费 API
│   ├── nl-workflow.js   # NL 转工作流 API
│   └── websocket.js     # WebSocket 连接
│
├── views/               # 页面视图
│   ├── Landing.vue      # 落地页
│   ├── NotFound.vue     # 404 页面
│   │
│   ├── auth/            # 认证相关
│   │   ├── Login.vue
│   │   ├── Register.vue
│   │   ├── ForgotPassword.vue
│   │   └── ResetPassword.vue
│   │
│   ├── workflow/        # 工作流管理
│   │   ├── List.vue     # 工作流列表
│   │   ├── Editor.vue   # 可视化编辑器
│   │   ├── Detail.vue   # 工作流详情
│   │   ├── Execute.vue  # 执行界面
│   │   └── Diff.vue     # 版本对比
│   │
│   ├── agent/           # Agent 管理
│   │   ├── List.vue     # Agent 列表
│   │   ├── Create.vue   # 创建 Agent
│   │   └── Debugger.vue # Agent 调试器
│   │
│   ├── nl-workflow/     # 自然语言生成
│   │   └── Creator.vue  # NL 创建器
│   │
│   ├── knowledge/       # 知识库管理
│   │   ├── Index.vue
│   │   └── CollectionDetail.vue
│   │
│   ├── vector-store/    # 向量存储
│   │   ├── Index.vue
│   │   └── Detail.vue
│   │
│   ├── monitoring/      # 监控
│   │   └── Index.vue
│   │
│   ├── analytics/       # 分析
│   │   └── Index.vue
│   │
│   ├── execution/       # 执行历史
│   │   └── History.vue
│   │
│   ├── prompt/          # 提示词管理
│   │   └── List.vue
│   │
│   ├── model/           # 模型管理
│   │   └── Index.vue
│   │
│   ├── marketplace/     # 市场
│   │   └── Index.vue
│   │
│   ├── team/            # 团队管理
│   │   └── Index.vue
│   │
│   ├── admin/           # 管理后台
│   │   └── Index.vue
│   │
│   ├── api-explorer/    # API 浏览器
│   │   └── Index.vue
│   │
│   ├── dashboard/       # 仪表盘
│   │   └── Home.vue
│   │
│   └── settings/        # 设置
│       ├── Settings.vue
│       ├── Profile.vue
│       ├── ApiKeys.vue
│       ├── ApiDoc.vue
│       ├── Integrations.vue
│       ├── Branding.vue
│       ├── Billing.vue
│       ├── Preferences.vue
│       └── DataExport.vue
│
├── components/          # 组件
│   ├── common/          # 通用组件
│   │   ├── AppButton.vue
│   │   ├── AppCard.vue
│   │   ├── AppInput.vue
│   │   ├── AppModal.vue
│   │   ├── ToastContainer.vue
│   │   ├── NotificationCenter.vue
│   │   ├── ThemeSwitcher.vue
│   │   ├── ThemeLogo.vue
│   │   ├── CommandPalette.vue
│   │   └── index.js
│   │
│   ├── workflow/        # 工作流组件
│   │   ├── WorkflowCanvas.vue    # 画布
│   │   ├── NodePanel.vue         # 节点面板
│   │   ├── NodeConfigForm.vue    # 节点配置表单
│   │   ├── PropertyPanel.vue     # 属性面板
│   │   ├── ExecutionHistory.vue  # 执行历史
│   │   ├── ExecutionResult.vue   # 执行结果
│   │   ├── StreamExecutionPanel.vue # 流式执行面板
│   │   │
│   │   └── nodes/       # 节点类型
│   │       ├── StartNode.vue      # 开始节点
│   │       ├── EndNode.vue        # 结束节点
│   │       ├── InputNode.vue      # 输入节点
│   │       ├── OutputNode.vue     # 输出节点
│   │       ├── LLMNode.vue        # LLM 节点
│   │       ├── HttpNode.vue       # HTTP 请求节点
│   │       ├── ConditionNode.vue  # 条件节点
│   │       ├── SwitchNode.vue     # 分支节点
│   │       ├── LoopNode.vue       # 循环节点
│   │       ├── VariableNode.vue   # 变量节点
│   │       ├── PromptNode.vue     # 提示词节点
│   │       ├── ToolNode.vue       # 工具节点
│   │       ├── CodeNode.vue       # 代码节点
│   │       └── DelayNode.vue      # 延迟节点
│   │
│   └── workspace/       # 工作空间组件
│       └── WorkspaceManager.vue
│
├── stores/              # Pinia 状态管理
│   ├── auth.js          # 认证状态
│   ├── app.js           # 应用状态
│   ├── workflow.js      # 工作流状态
│   ├── nlWorkflow.js    # NL 工作流状态
│   ├── agent.js         # Agent 状态
│   ├── prompt.js        # 提示词状态
│   ├── rag.js           # RAG 状态
│   ├── gateway.js       # 网关状态
│   ├── tenant.js        # 租户状态
│   ├── monitoring.js    # 监控状态
│   └── index.js         # 入口
│
├── router/              # 路由配置
│   └── routes.js        # 路由定义
│
├── composables/         # 组合式函数
│   ├── useRequest.js    # 请求封装
│   ├── useForm.js       # 表单处理
│   └── useThemeFavicon.js # 主题图标
│
├── utils/               # 工具函数
│   ├── request.ts       # HTTP 请求
│   ├── storage.js       # 本地存储
│   ├── formatters.js    # 格式化函数
│   ├── performance.js   # 性能优化
│   └── workflowTransform.js # 工作流转换
│
├── types/               # TypeScript 类型
│   └── api.ts           # API 类型定义
│
├── config/              # 配置文件
│
├── assets/              # 静态资源
│   ├── styles/          # 样式
│   │   ├── global.scss  # 全局样式
│   │   └── themes.scss  # 主题样式
│   └── logos/           # Logo 文件
│
├── layouts/             # 布局组件
│   └── AppLayout.vue    # 主布局
│
├── auto-imports.d.ts    # 自动导入声明
└── components.d.ts      # 组件类型声明
```

### 前端关键模块说明

| 模块 | 功能 |
|------|------|
| **views/workflow** | 工作流的列表、编辑、执行界面 |
| **components/workflow** | 可视化工作流编辑器的核心组件 |
| **components/workflow/nodes** | 14 种不同类型的工作流节点 |
| **stores** | Pinia 状态管理，处理数据和 UI 状态 |
| **api** | 封装所有后端 API 调用 |
| **composables** | 可复用的组合式函数 |

---

## 其他重要目录

### docker/ - Docker 配置
```
docker/
├── Dockerfile.backend   # 后端镜像
├── Dockerfile.frontend  # 前端镜像
├── Dockerfile.nginx     # Nginx 镜像
├── nginx/               # Nginx 配置
├── redis/               # Redis 配置
└── .env.example         # 环境变量示例
```

### Docs/ - 文档
```
Docs/
├── setup-guide.md       # 安装指南
├── api/                 # API 文档
│   ├── api-spec.yaml    # OpenAPI 规范
│   ├── api-schemas.json # JSON Schema
│   ├── API-QUICK-REFERENCE.md
│   ├── API-CONSISTENCY-GUIDE.md
│   └── API-DEVELOPMENT-PROMPT.md
└── tasks/               # 任务相关文档
```

### tests/ - 测试
```
tests/
├── backend/             # 后端测试
└── frontend/            # 前端测试
```

---

## 数据流架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   Database  │
│  (Vue 3)    │     │  (Django)   │     │   (MySQL)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       │            │   Redis     │            │
       │            │  (Cache)    │            │
       │            └─────────────┘            │
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       │            │   Celery    │            │
       │            │  (Tasks)    │            │
       │            └─────────────┘            │
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       └───────────▶│  WebSocket  │◀───────────┘
                    │  (Channels) │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  LLM APIs   │
                    │ (OpenAI,    │
                    │  Anthropic) │
                    └─────────────┘
```

---

## 核心功能模块关系

1. **工作流引擎**: `workflows` 模块负责工作流的定义、存储、执行
2. **AI 集成**: `gateway` 模块统一封装不同 LLM 提供商
3. **Agent 系统**: `agents` 模块提供 AI Agent 的创建和调试
4. **自然语言**: `nl_to_workflow` 模块将自然语言转换为工作流
5. **知识库**: `rag` 模块提供检索增强生成能力
6. **实时监控**: `monitoring` 模块跟踪工作流执行状态
7. **多租户**: `tenants` 模块支持多用户隔离

---

## 开发环境要求

### 后端
- Python 3.12+
- MySQL 8.0+
- Redis 7+

### 前端
- Node.js 20+
- npm 或 yarn

### 可选
- Docker & Docker Compose (容器化部署)

---

## 快速启动

### 后端启动
```bash
cd Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 前端启动
```bash
cd Frontend
npm install
npm run dev
```

### Docker 启动
```bash
docker-compose up -d
```

---

## API 端点概览

### 认证
- `POST /api/v1/auth/register/` - 用户注册
- `POST /api/v1/auth/login/` - 用户登录
- `POST /api/v1/auth/refresh/` - 刷新令牌

### 工作流
- `GET /api/v1/workflows/` - 获取工作流列表
- `POST /api/v1/workflows/` - 创建工作流
- `GET /api/v1/workflows/{id}/` - 获取工作流详情
- `PATCH /api/v1/workflows/{id}/` - 更新工作流
- `DELETE /api/v1/workflows/{id}/` - 删除工作流
- `POST /api/v1/workflows/{id}/execute/` - 执行工作流

### Agent
- `GET /api/v1/agents/` - 获取 Agent 列表
- `POST /api/v1/agents/` - 创建 Agent
- `POST /api/v1/agents/{id}/chat/` - 与 Agent 对话

---

*本文档由 Cline 生成，最后更新：2026-05-11*