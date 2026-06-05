# e-Flowly - AI Agent 工作流编排平台

> 一个功能强大的 AI Agent 工作流编排平台，支持自然语言生成工作流、可视化编辑器、多模态模型集成。

---

## 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [核心功能](#核心功能)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 接口](#api-接口)
- [前端路由](#前端路由)
- [数据库模型](#数据库模型)
- [环境变量](#环境变量)
- [部署架构](#部署架构)

---

## 项目概述

**e-Flowly** 是一个企业级 AI Agent 工作流编排平台，核心特性包括：

- **自然语言生成工作流**：通过自然语言描述自动生成工作流
- **可视化工作流编辑器**：基于 Vue Flow 的拖拽式编辑器
- **多模态模型支持**：集成 LLM、图像生成、视频生成、音频处理等多种 AI 能力
- **RAG 知识库**：支持向量检索增强生成
- **团队协作**：多租户、权限管理、模板市场
- **模型训练**：支持自定义模型训练流程

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 用户层                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Web UI    │  │  Admin UI   │  │  API Client │  │   CLI       │       │
│  │  (Vue.js)   │  │ (Jazzmin)   │  │   (REST)    │  │             │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘       │
└─────────┼────────────────┼────────────────┼─────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 网关层                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Django REST Framework                          │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │  │
│  │  │ Workflow│ │  Agent  │ │ NL→WF   │ │  RAG    │ │ Gateway │      │  │
│  │  │  APIs   │ │  APIs   │ │  APIs   │ │  APIs   │ │  APIs   │      │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │ ASGI (Daphne)                                │
└──────────────────────────────┼─────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     MySQL       │  │  PostgreSQL     │  │     Redis       │
│  (主数据库)      │  │ (+pgvector)     │  │  (缓存/队列)     │
│   Port: 3306    │  │   Port: 5432    │  │   Port: 6379    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                    │                    │
          │                    │                    ▼
          │                    │            ┌─────────────────┐
          │                    │            │  Celery Worker  │
          │                    │            │  (异步任务)       │
          │                    │            └─────────────────┘
          │                    │
          │                    ▼
          │            ┌─────────────────┐
          │            │  LLM Provider   │
          │            │  (OpenAI/Ollama)│
          │            └─────────────────┘
          │                    │
          ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     AI 能力层                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  LLM      │ │  Image    │ │  Video    │ │  Audio    │  │
│  │  生成     │ │  生成      │ │  生成      │ │  处理     │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  RAG      │ │  知识库   │ │ 代码执行   │ │  工作流   │  │
│  │  检索     │ │  管理     │ │ (沙箱)     │ │  执行器   │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 技术栈

### 后端

| 类别 | 技术 | 说明 |
|------|------|------|
| 框架 | Django 5.x + Django REST Framework | Web 框架 |
| 异步 | Channels + Daphne | WebSocket 支持 |
| 任务队列 | Celery + Redis | 异步任务处理 |
| AI | LangChain + LangGraph | LLM 编排 |
| 向量存储 | pgvector (PostgreSQL) | 向量检索 |
| 主数据库 | MySQL 8.0 | 业务数据 |
| 缓存 | Redis 7 | 会话/缓存 |

### 前端

| 类别 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 + Composition API | UI 框架 |
| 路由 | Vue Router 4 | 页面路由 |
| 状态管理 | Pinia | 状态管理 |
| UI 组件 | Element Plus | UI 组件库 |
| 工作流 | Vue Flow | 可视化编辑器 |
| 图表 | ECharts | 数据可视化 |
| 构建 | Vite 5 | 开发/构建 |

### 基础设施

| 类别 | 技术 | 说明 |
|------|------|------|
| 容器化 | Docker + Docker Compose | 容器编排 |
| 反向代理 | Nginx | 负载均衡 |
| API 文档 | drf-spectacular | OpenAPI 文档 |

---

## 核心功能

### 1. 工作流管理

- 可视化拖拽式工作流编辑器
- 支持 20+ 种节点类型
- 版本控制与历史记录
- 工作流对比与差异分析
- 触发器配置（定时、Webhook、API）

### 2. 自然语言生成 (NL to Workflow)

```
用户输入 ──► LLM 解析 ──► 工作流生成 ──► 可视化预览 ──► 编辑确认
              │                          │
              ▼                          ▼
         意图分析                   JSON 结构
         节点建议                   错误修复
```

### 3. Agent 管理

- 多模型支持（OpenAI、Ollama、本地模型）
- Prompt 模板管理
- Agent 调试器
- 工具绑定与配置

### 4. RAG 知识库

- 多集合管理
- 向量存储配置
- 文档上传与处理
- 语义检索

### 5. 数据集管理

- 数据集上传与管理
- 数据标注工作台
- 数据增强任务
- 数据集推荐

### 6. 模型训练

- 训练任务管理
- 训练进度监控
- 模型权重管理
- 训练环境配置

### 7. 团队与权限

- 多租户支持
- 角色权限管理
- API Key 管理
- 团队协作

---

## 项目结构

```
e-Flowly-now/
├── Backend/                          # Django 后端
│   ├── config/                       # 项目配置
│   │   ├── settings.py              # Django 设置
│   │   ├── urls.py                  # 根路由
│   │   ├── asgi.py                  # ASGI 配置
│   │   ├── wsgi.py                 # WSGI 配置
│   │   └── constants.py             # 常量定义
│   │
│   ├── core/                        # 核心模块
│   │   ├── models.py               # 通用模型
│   │   ├── views/                  # 通用视图
│   │   └── serializers/            # 序列化器
│   │
│   ├── users/                       # 用户认证
│   │   ├── models.py               # 用户模型
│   │   ├── views.py               # 认证视图
│   │   └── urls.py                # 路由
│   │
│   ├── workflows/                  # 工作流模块
│   │   ├── models.py              # 工作流/节点/边模型
│   │   ├── views.py              # API 视图
│   │   ├── services/             # 业务逻辑
│   │   │   ├── langgraph_executor.py   # LangGraph 执行器
│   │   │   └── langchain_service.py    # LangChain 服务
│   │   └── urls.py
│   │
│   ├── nl_to_workflow/            # 自然语言生成工作流
│   │   ├── services.py           # NL 处理服务
│   │   ├── output_parser.py     # 输出解析
│   │   ├── recommender.py        # 模板推荐
│   │   ├── vector_store.py       # 向量存储
│   │   ├── memory.py             # 会话记忆
│   │   ├── prompts.py            # Prompt 模板
│   │   ├── constants.py          # 常量配置
│   │   └── urls.py
│   │
│   ├── agents/                     # Agent 管理
│   ├── datasets/                   # 数据集管理
│   ├── rag/                       # RAG 知识库
│   ├── gateway/                   # AI 网关（多模型）
│   │   └── providers/            # 模型提供者
│   ├── training/                  # 模型训练
│   ├── evaluation/                # 评估模块
│   ├── augmentation/             # 数据增强
│   ├── annotations/               # 标注工具
│   ├── prompts/                   # Prompt 模板
│   ├── templates/                 # 工作流模板
│   ├── marketplace/               # 模板市场
│   ├── tenants/                   # 多租户
│   ├── billing/                   # 计费管理
│   ├── integrations/              # 第三方集成
│   ├── branding/                  # 品牌定制
│   ├── monitoring/                # 监控中心
│   ├── features/                  # 特性开关
│   ├── reports/                   # 报表
│   ├── website_generator/         # 网站生成器
│   ├── dataset_recommend/         # 数据集推荐
│   ├── admin/                     # 自定义 Admin
│   ├── utils/                     # 工具函数
│   ├── prompts/                   # Prompt 库
│   ├── scripts/                   # 脚本
│   ├── logs/                      # 日志
│   └── requirements.txt           # Python 依赖
│
├── Frontend/                       # Vue 3 前端
│   ├── src/
│   │   ├── api/                  # API 封装
│   │   ├── assets/               # 静态资源
│   │   ├── components/           # 公共组件
│   │   │   ├── common/           # 通用组件
│   │   │   ├── workflow/        # 工作流组件
│   │   │   ├── editor/          # 编辑器组件
│   │   │   └── layout/          # 布局组件
│   │   ├── composables/          # 组合式函数
│   │   ├── config/               # 配置
│   │   ├── layouts/              # 页面布局
│   │   ├── router/               # 路由配置
│   │   │   ├── index.js         # 路由实例
│   │   │   └── routes.js        # 路由定义
│   │   ├── stores/               # Pinia 状态
│   │   │   ├── auth.js          # 认证状态
│   │   │   ├── workflow.js      # 工作流状态
│   │   │   └── nlWorkflow.js    # NL 生成状态
│   │   ├── types/                # TypeScript 类型
│   │   ├── utils/                # 工具函数
│   │   └── views/                # 页面视图
│   │       ├── auth/             # 认证页面
│   │       ├── dashboard/        # 仪表盘
│   │       ├── workflow/         # 工作流
│   │       ├── nl-workflow/      # NL 生成
│   │       ├── agent/            # Agent
│   │       ├── dataset/          # 数据集
│   │       ├── knowledge/        # 知识库
│   │       ├── prompt/           # Prompt
│   │       ├── model/            # 模型
│   │       ├── vector-store/     # 向量存储
│   │       ├── training/         # 训练
│   │       ├── execution/        # 执行历史
│   │       ├── marketplace/      # 市场
│   │       ├── monitoring/       # 监控
│   │       ├── analytics/       # 分析
│   │       ├── admin/           # 管理
│   │       ├── team/            # 团队
│   │       ├── settings/         # 设置
│   │       └── api-explorer/    # API 测试
│   ├── public/                   # 公共资源
│   ├── tests/                    # 测试
│   ├── package.json              # Node 依赖
│   └── vite.config.js           # Vite 配置
│
├── docker/                        # Docker 配置
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.nginx
│   └── nginx/
│       └── conf.d/
│
├── tests/                        # 测试
│   ├── backend/
│   ├── frontend/
│   ├── e2e/
│   └── nl_workflow/
│
├── Scripts/                      # 工具脚本
├── Docs/                        # 文档
├── .env.example                 # 环境变量示例
├── docker-compose.yml           # Docker Compose
├── requirements.txt            # Python 依赖
└── README.md                   # 本文件
```

---

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- MySQL 8.0
- PostgreSQL 16 + pgvector
- Redis 7
- Docker & Docker Compose（可选）

### 1. 克隆项目

```bash
git clone <repository-url>
cd e-Flowly-now
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

关键配置项：
```bash
# 数据库
DB_NAME=flowly
DB_USER=flowly
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# 向量数据库
PG_NAME=flowly_vector
PG_USER=flowly
PG_PASSWORD=your_password
PG_HOST=localhost
PG_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI
OPENAI_API_KEY=sk-xxx
```

### 3. 使用 Docker 启动（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 本地开发启动

#### 后端

```bash
cd Backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

#### 前端

```bash
cd Frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 5. 访问应用

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| Admin 后台 | http://localhost:8000/admin/ |
| API 文档 | http://localhost:8000/api/docs/ |

---

## API 接口

### 基础信息

- **Base URL**: `/api/v1/`
- **认证方式**: Token 认证 (`Authorization: Token <token>`)
- **响应格式**: JSON

### 主要模块接口

| 模块 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/v1/auth/` | 登录、注册、密码重置 |
| 工作流 | `/api/v1/` | CRUD、执行、版本控制 |
| NL 生成 | `/api/v1/nl-workflow/` | 自然语言生成工作流 |
| Agent | `/api/v1/agents/` | Agent 管理 |
| 知识库 | `/api/v1/rag/` | RAG 集合管理 |
| 数据集 | `/api/v1/datasets/` | 数据集管理 |
| 网关 | `/api/v1/gateway/` | AI 模型网关 |
| 模板 | `/api/v1/templates/` | 工作流模板 |
| 市场 | `/api/v1/marketplace/` | 模板市场 |
| 团队 | `/api/v1/tenants/` | 租户/团队管理 |
| 监控 | `/api/v1/monitoring/` | 系统监控 |
| 账单 | `/api/v1/billing/` | 计费管理 |

### NL to Workflow 接口详情

```
POST /api/v1/nl-workflow/sessions/
    创建新会话

GET /api/v1/nl-workflow/sessions/
    获取会话列表

GET /api/v1/nl-workflow/sessions/{session_id}/
    获取会话详情

POST /api/v1/nl-workflow/sessions/{session_id}/message/
    发送消息（同步）

POST /api/v1/nl-workflow/sessions/{session_id}/message/stream/
    发送消息（流式）

POST /api/v1/nl-workflow/sessions/{session_id}/confirm/
    确认生成工作流

POST /api/v1/nl-workflow/preview/
    预览生成的工作流 JSON

POST /api/v1/nl-workflow/stream/
    流式生成工作流

POST /api/v1/nl-workflow/analyze-intent/
    分析用户意图

POST /api/v1/nl-workflow/suggest/
    获取修改建议

GET /api/v1/nl-workflow/models/
    获取可用模型列表
```

---

## 前端路由

### 公开路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Landing | 首页/落地页 |
| `/login` | Login | 登录 |
| `/register` | Register | 注册 |
| `/forgot-password` | ForgotPassword | 忘记密码 |
| `/reset-password` | ResetPassword | 重置密码 |

### 需要认证

| 路径 | 页面 | 说明 |
|------|------|------|
| `/home` | Dashboard | 仪表盘 |
| `/workflows` | WorkflowList | 工作流列表 |
| `/workflows/new` | WorkflowCreate | 创建工作流 |
| `/workflows/:id/edit` | WorkflowEdit | 编辑工作流 |
| `/workflows/:id` | WorkflowDetail | 工作流详情 |
| `/workflows/:id/execute` | WorkflowExecute | 执行工作流 |
| `/workflows/diff` | WorkflowDiff | 工作流对比 |
| `/agents` | AgentList | Agent 列表 |
| `/agents/new` | AgentCreate | 创建 Agent |
| `/agents/:id/edit` | AgentEdit | 编辑 Agent |
| `/agents/:id/debug` | AgentDebugger | Agent 调试 |
| `/nl-create` | NLCreator | 自然语言创建 |
| `/knowledge` | KnowledgeBase | 知识库 |
| `/knowledge/:id` | CollectionDetail | 集合详情 |
| `/datasets` | DatasetList | 数据集列表 |
| `/datasets/:id` | DatasetDetail | 数据集详情 |
| `/dataset-recommend` | DatasetRecommend | 数据集推荐 |
| `/augmentations` | AugmentationStatus | 数据增强 |
| `/annotations/:id` | AnnotationWorkspace | 标注工作台 |
| `/training` | TrainingProgress | 训练进度 |
| `/prompts` | PromptList | Prompt 列表 |
| `/models` | ModelList | 模型管理 |
| `/vector-stores` | VectorStoreList | 向量存储 |
| `/vector-stores/:id` | VectorStoreDetail | 向量存储详情 |
| `/executions` | ExecutionHistory | 执行历史 |
| `/marketplace` | Marketplace | 模板市场 |
| `/marketplace/:id` | TemplateDetail | 模板详情 |
| `/my-templates` | MyTemplates | 我的模板 |
| `/team` | Team | 团队管理 |
| `/integrations` | Integrations | 集成 |
| `/monitoring` | Monitoring | 监控中心 |
| `/analytics` | Analytics | 数据分析 |
| `/api-explorer` | ApiExplorer | API 测试 |
| `/admin` | Admin | 系统管理 |

### 设置页面 (子路由)

| 路径 | 页面 |
|------|------|
| `/settings` | Settings (容器) |
| `/settings/profile` | Profile |
| `/settings/preferences` | Preferences |
| `/settings/api-keys` | ApiKeys |
| `/settings/credentials` | Credentials |
| `/settings/billing` | Billing |
| `/settings/integrations` | Integrations |
| `/settings/branding` | Branding |
| `/settings/data-export` | DataExport |

---

## 数据库模型

### 核心模型

#### Workflow
```python
class Workflow(models.Model):
    id: UUID              # 主键
    tenant: Tenant        # 所属租户
    owner: User           # 所有者
    name: str             # 工作流名称
    description: str      # 描述
    version: int          # 版本号
    status: str           # draft/published/archived
    category: str         # 分类
    tags: JSON            # 标签
    config: JSON          # 配置
    # 统计
    total_executions: int
    successful_executions: int
    avg_execution_time_ms: int
    # 权限
    is_public: bool
    share_token: str
```

#### Node
```python
class Node(models.Model):
    workflow: Workflow
    type: str             # start/end/llm/condition/tool/code/input/output...
    name: str
    position: JSON        # {"x": 100, "y": 200}
    config: JSON          # 节点配置
    inputs: JSON          # 输入定义
    outputs: JSON         # 输出定义
    # 执行
    retry_config: JSON
    timeout_seconds: int
```

#### Edge
```python
class Edge(models.Model):
    workflow: Workflow
    source: Node
    target: Node
    label: str            # 连线标签
    config: JSON
```

### 执行相关

#### WorkflowExecution
```python
class WorkflowExecution(models.Model):
    workflow: Workflow
    trigger_type: str     # manual/api/schedule/webhook
    status: str            # pending/running/success/failed
    input_data: JSON
    output_data: JSON
    error: Text
    started_at: DateTime
    completed_at: DateTime
    execution_time_ms: int
```

#### NLSession
```python
class NLSession(models.Model):
    user: User
    model: str            # 使用的模型
    messages: JSON         # 对话历史
    context: JSON          # 上下文
    generated_workflow: JSON
    status: str
```

### RAG 相关

#### Collection
```python
class Collection(models.Model):
    user: User
    name: str
    description: str
    embedding_model: str
    vector_store_config: JSON
    document_count: int
```

---

## 环境变量

### 必需变量

```bash
# 应用
APP_NAME=Flowly
DEBUG=true
SECRET_KEY=your-secret-key

# 主数据库
DB_NAME=flowly
DB_USER=root
DB_PASSWORD=xxx
DB_HOST=localhost
DB_PORT=3306

# 向量数据库
PG_NAME=flowly_vector
PG_USER=flowly
PG_PASSWORD=xxx
PG_HOST=localhost
PG_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI
OPENAI_API_KEY=sk-xxx
```

### 可选变量

```bash
# LangSmith 追踪
LANGSMITH_API_KEY=xxx
LANGSMITH_TRACING=true

# Docker 沙箱
DOCKER_ENABLED=auto
DOCKER_MEMORY_LIMIT=256
DOCKER_TIMEOUT=60
```

---

## 部署架构

### Docker Compose 服务

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `nginx` | 自定义 | 80, 443 | 反向代理 |
| `backend` | 自定义 | 8000 | Django 应用 |
| `frontend` | 自定义 | 5173 | Vue 前端 |
| `celery` | 自定义 | - | Celery Worker |
| `celery-beat` | 自定义 | - | 定时任务 |
| `db` | mysql:8.0 | 3306 | MySQL |
| `pgvector` | pgvector/pgvector:pg16 | 5432 | PostgreSQL + pgvector |
| `redis` | redis:7-alpine | 6379 | Redis |

### 生产部署建议

1. **数据库**: 使用托管数据库服务 (RDS, Cloud SQL)
2. **缓存**: 使用 ElastiCache 或 Memorystore
3. **存储**: 使用 S3/GCS 存储静态文件和媒体
4. **负载均衡**: 使用云负载均衡器
5. **SSL**: 使用 Let's Encrypt 或云证书
6. **监控**: 集成 Prometheus + Grafana
7. **日志**: 集成 ELK Stack

---

## 开发指南

### 添加新模块

1. 创建 Django app: `python manage.py startapp new_module`
2. 在 `settings.py` 的 `INSTALLED_APPS` 添加
3. 创建 models、views、serializers
4. 在 `urls.py` 注册路由
5. 前端创建对应页面和 API 封装

### 添加新节点类型

1. 在 `workflows/models.py` 的 `Node.NODE_TYPE_CHOICES` 添加
2. 在前端 `components/workflow/nodes/` 创建渲染组件
3. 实现节点配置面板
4. 在执行器中添加处理逻辑

### API 开发

```bash
# 生成 API 文档
python manage.py spectacular --file ./schema.yml

# 验证 schema
python manage.py spectacular --validate
```

---

## 测试

### 后端测试

```bash
cd Backend
pytest --cov=. --cov-report=html
```

### 前端测试

```bash
cd Frontend

# 单元测试
npm run test

# E2E 测试
npm run test:e2e

# 覆盖率
npm run test:coverage
```

---

## License

MIT License
