# Flowly - AI Agent 工作流编排平台

> 企业级 AI Agent 工作流编排平台，支持自然语言生成工作流、可视化编辑器、多模态模型集成、桌面端 GPU 训练与平台级管理后台。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![Vue.js 3](https://img.shields.io/badge/Vue-3-42b883.svg)](https://vuejs.org/)
[![Django 5.x](https://img.shields.io/badge/Django-5.x-red.svg)](https://www.djangoproject.com/)

---

## 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [管理后台](#管理后台)
- [NL to Workflow 工作原理](#nl-to-workflow-工作原理)
- [多 Agent 协作系统](#多-agent-协作系统)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [核心模块详解](#核心模块详解)
- [API 接口](#api-接口)
- [前端路由](#前端路由)
- [数据库模型](#数据库模型)
- [环境变量](#环境变量)
- [部署与基础设施](#部署与基础设施)
- [测试体系](#测试体系)
- [文档索引](#文档索引)
- [贡献指南](#贡献指南)
- [License](#license)

---

## 项目概述

**Flowly** 是一个企业级 AI Agent 工作流编排平台，旨在降低 AI 工作流的创建门槛，让用户通过自然语言即可快速构建复杂的 AI 工作流。

平台核心围绕两大能力构建：**自然语言生成工作流**（NL to Workflow）和**可视化工作流编辑**，结合多模型网关、多租户协作、RAG 知识库、模型训练、网站生成器以及**三层管理后台**等企业级功能，适用于问答机器人、数据处理流水线、内容生成系统、智能客服、ML 站点工厂等多种业务场景。

---

## 核心特性

### 自然语言生成工作流

通过自然语言描述，自动解析用户意图并生成完整的工作流定义（DAG 结构）。系统支持多轮对话修改、流式响应、DAG 验证，覆盖问答机器人、数据处理、翻译、内容生成等 7 种工作流类型。

### 可视化工作流编辑器

基于 Vue Flow 构建的拖拽式编辑器，支持 20+ 节点类型（LLM、条件分支、代码执行、工具调用、邮件、网页抓取、YOLO 训练等），提供版本控制、历史记录和工作流对比功能。

### 多 Agent 协作系统

基于 ReAct 模式实现的多 Agent 编排，支持 Planner（规划）、Executor（执行）、Critic（评审）、Reporter（报告）、Coordinator（协调）等多种角色，通过消息队列实现 Agent 间协作。

### AI 模型网关

统一的 AI 模型接入层，支持 OpenAI、Anthropic Claude、Ollama、DashScope 等多模型，通过 `ProviderRegistry` 注册机制灵活扩展，内置 Token 用量统计和成本估算。

### RAG 知识库

支持 Qdrant、Milvus、Chroma、Pinecone 等主流向量数据库，提供文档上传、分块策略、语义检索全链路能力。

### 桌面客户端（Desktop）

Electron 桌面端加载与 Web 相同的 Frontend UI，并通过本地 WebSocket Agent 提供 GPU 训练能力（YOLO / ultralytics），适合离线训练与本地算力场景。

### 企业级功能

- **多租户隔离**：基于 Tenant / Workspace 的资源隔离与成员管理
- **权限体系**：RBAC 角色权限控制，精确到接口级别的权限配置
- **工作流模板市场**：用户可发布、分享、复用工作流模板
- **完整执行链路**：支持手动、定时、Webhook、API 多种触发方式
- **平台管理后台**：Jazzmin 美化 Admin + REST Admin API + Vue 管理页

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 用户层                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web UI    │  │  Admin UI   │  │  Desktop    │  │  API Client │         │
│  │  (Vue 3)    │  │  (Jazzmin + │  │ (Electron)  │  │   (REST)    │         │
│  │  :5200      │  │  Vue /admin)│  │             │  │             │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                  │                │                │
          ▼                  ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API 网关层                                        │
│              Django REST Framework + ASGI (Daphne)                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │Workflow │ │  Agent  │ │ NL→WF   │ │  RAG    │ │ Gateway │ │  Admin  │  │
│  │  APIs   │ │  APIs   │ │  APIs   │ │  APIs   │ │  APIs   │ │  APIs   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   ┌─────────────┐        ┌─────────────┐         ┌─────────────┐
   │    MySQL    │        │ PostgreSQL  │         │    Redis    │
   │  (主数据库)  │        │ (pgvector,  │         │ (缓存/队列)  │
   │             │        │  可选向量)   │         │             │
   └─────────────┘        └─────────────┘         └──────┬──────┘
          │                      │                       │
          │                      │                       ▼
          │                      │               ┌─────────────┐
          │                      │               │ Celery      │
          │                      │               │  Worker     │
          │                      │               └─────────────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
            ┌─────────────┐
            │ AI Provider │
            │ (OpenAI /   │
            │  Claude /   │
            │  Ollama)    │
            └─────────────┘
```

---

## 技术栈

### 后端技术

| 类别 | 技术 | 说明 |
|------|------|------|
| Web 框架 | Django 5.x + Django REST Framework | 高性能 REST API |
| 管理后台 | Jazzmin + 自定义 FlowlyAdminSite | 美化 Django Admin |
| 异步通信 | Channels + Daphne | WebSocket + ASGI 支持 |
| 任务队列 | Celery + Redis | 异步任务处理 |
| AI 编排 | LangChain + LangGraph | LLM 编排与 Agent 构建 |
| 主数据库 | MySQL 8.0 | 业务数据持久化 |
| 向量存储 | PostgreSQL + pgvector / Qdrant | 可选向量检索 |
| 缓存层 | Redis 7 | 会话缓存 + 消息队列 |
| API 文档 | drf-spectacular | OpenAPI 3.0 自动生成 |

### 前端技术

| 类别 | 技术 | 说明 |
|------|------|------|
| UI 框架 | Vue 3 + Composition API | 现代化响应式框架 |
| 路由管理 | Vue Router 4 | SPA 路由控制 |
| 状态管理 | Pinia | 轻量级状态管理 |
| UI 组件库 | Element Plus | 企业级组件库 |
| 工作流编辑器 | Vue Flow | 拖拽式 DAG 编辑器 |
| 数据可视化 | ECharts | 图表与监控面板 |
| 构建工具 | Vite 5 | 开发端口 **5200**（`strictPort: true`） |
| HTTP 客户端 | Axios | 请求拦截与统一封装 |

### 基础设施

| 类别 | 技术 | 说明 |
|------|------|------|
| 桌面端 | Electron | 本地 GPU 训练 Agent |
| 容器化 | Docker（可选） | 当前仓库提供 Qdrant 开发 compose |
| 反向代理 | Nginx | 生产部署参考（见 `docker/`） |
| 追踪监控 | LangSmith | LLM 调用追踪（可选） |

---

## 管理后台

Flowly 提供**三层管理能力**，覆盖平台运营、系统配置与运维监控：

```
┌─────────────────────────────────────────────────────────────────┐
│                     管理后台三层架构                              │
├─────────────────────────────────────────────────────────────────┤
│  ① Django Admin (Jazzmin)     http://localhost:8000/admin/      │
│     完整平台管理 · 模型 CRUD · 仪表盘 · 配置中心 · 功能开关      │
├─────────────────────────────────────────────────────────────────┤
│  ② Admin REST API             http://localhost:8000/api/v1/admin/ │
│     超级用户 Token 认证 · 程序化运维 · 前端管理页数据源          │
├─────────────────────────────────────────────────────────────────┤
│  ③ Vue 管理页（实验性）        http://localhost:5200/admin        │
│     部分功能已对接 API · 告警规则等为占位实现                     │
└─────────────────────────────────────────────────────────────────┘
```

### ① Django Admin（推荐，功能最全）

基于 **Jazzmin** 美化主题 + 自定义 `FlowlyAdminSite`，是日常平台管理的主入口。

| 访问地址 | 说明 |
|----------|------|
| `http://localhost:8000/admin/` | 管理后台首页（欢迎页） |
| `/admin/flowly/` | 运营仪表盘（用户/工作流/执行统计） |
| `/admin/flowly/settings/` | 平台配置中心（9 大模块） |
| `/admin/flowly/features/` | 动态功能开关面板 |
| `/admin/flowly/ai-models/` | AI 模型与 Provider 管理 |
| `/admin/flowly/audit/` | 审计日志面板 |
| `/admin/flowly/system/` | 系统健康状态面板 |

**Django Admin 可管理的业务模型包括：**

- 用户与权限（`users`）
- 租户与成员（`tenants`）
- 工作流 / 节点 / 执行记录（`workflows`）
- Agent 与对话（`agents`）
- AI 网关与 API Key（`gateway`）
- RAG 知识库（`rag`）
- 模板与市场（`templates` / `marketplace`）
- 平台配置模型（`admin` 应用）

**平台配置模型（`Backend/admin/models.py`）：**

| 模型 | 说明 |
|------|------|
| `SystemSetting` | 键值型全局系统设置 |
| `LegalDocument` | 服务条款 / 隐私政策 / 登录协议（版本化） |
| `UserTermsAcceptance` | 用户条款同意记录 |
| `FeatureVisibilityRule` | 按全局/角色/用户组的功能可见性规则 |
| `GatewayRouteRule` | API 网关路由与限流规则 |
| `PaymentProviderConfig` | Stripe / 支付宝 / 微信 / PayPal 配置 |
| `EmailSendLog` | 邮件发送审计日志 |
| `BackupRecord` | 数据备份记录 |

**9 大配置模块**（`admin/constants.py`）：

`general` · `terms` · `features` · `security` · `user_defaults` · `gateway` · `payment` · `email` · `backup`

### ② Admin REST API

前缀：`/api/v1/admin/`，**需要超级用户权限**（`is_superuser`）。

**认证方式：** `Authorization: Token <token>`

| 分类 | 端点 | 能力 |
|------|------|------|
| 用户管理 | `GET/POST/PATCH/DELETE /users/` | 用户 CRUD |
| | `POST /users/{id}/reset-password/` | 重置密码 |
| 租户管理 | `CRUD /tenants/` | 租户全生命周期 |
| 资源只读 | `GET /workflows/`、`GET /agents/` | 工作流与 Agent 列表 |
| API Key | `GET /api-keys/`、`POST /api-keys/{id}/revoke/` | 网关 Key 管理 |
| 法律文档 | `CRUD /legal-documents/` | 条款版本管理 |
| 条款记录 | `GET /terms-acceptances/` | 用户同意记录 |
| 功能可见性 | `CRUD /feature-visibility/` | 功能开关规则 |
| 网关路由 | `CRUD /gateway-routes/` | 路由与限流 |
| 支付配置 | `CRUD /payment-providers/` | 支付渠道 |
| 邮件 | `GET /email-logs/`、`POST /email/test/` | 邮件日志与测试 |
| 备份 | `GET/POST /backup/`、`GET /backup-records/{id}/download/` | 创建/下载/删除备份 |
| 系统 | `GET /usage/`、`GET /health/` | 用量与健康检查 |
| 设置 | `GET/PATCH /settings/` | 扁平系统设置 |
| | `GET/PATCH /settings/modules/{module}/` | 按模块读写配置 |
| 运维 | `GET /logs/`、`POST /cache/clear/` | 审计日志、清缓存 |

**公开配置接口**（无需管理员权限，供前端运行时读取）：

| 端点 | 说明 |
|------|------|
| `GET /api/v1/public/site-config/` | 站点信息、认证开关、条款版本、功能可见性、支付配置 |
| `POST /api/v1/public/auth-assistant/chat/` | 登录页 AI 助手对话 |

### ③ Vue 管理页（实验性）

路由：`http://localhost:5200/admin`

| Tab | 状态 |
|-----|------|
| 系统概览 | 已对接（健康检查、用量统计、清缓存、备份） |
| 用户管理 | 部分对接（列表/删除；创建/编辑待完善） |
| 租户管理 | 部分对接 |
| 系统配置 | 部分对接（通用/API/邮件子集） |
| 告警规则 | 占位数据，未接后端 |
| 操作日志 | 已对接审计日志 API |

> **权限说明：** Vue 管理页要求 `is_staff || is_superuser`；Admin REST API 要求 `is_superuser`。Staff 用户可进入 Vue 页面，但部分 API 调用会返回 403。

### 管理后台初始化

```bash
cd Backend

# 1. 数据库迁移
python manage.py migrate

# 2. 创建超级用户（Django Admin 登录账号）
python manage.py createsuperuser

# 3. 种子数据：默认法律文档（服务条款、隐私政策、登录协议）
python manage.py seed_platform_config

# 4. 可选：演示数据与冒烟测试账号
python scripts/ensure_smoke_test_user.py
python manage.py seed_demo_data --email=nlwftest@flowly.test

# 5. 启动后端（WebSocket 场景用 Daphne）
python manage.py runserver 127.0.0.1:8000
# 或
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

默认冒烟测试账号：`nlwftest@flowly.test` / `Test123456!`

### 管理后台相关代码

| 路径 | 说明 |
|------|------|
| `Backend/admin/` | Admin 应用（模型、REST API、配置服务） |
| `Backend/config/admin_site.py` | 自定义 FlowlyAdminSite 与面板路由 |
| `Backend/config/settings.py` | Jazzmin 主题与 Admin 配置 |
| `Backend/templates/admin/` | Admin 自定义模板 |
| `Backend/admin_static/` | Admin 自定义 CSS/JS |
| `Frontend/src/views/admin/Index.vue` | Vue 管理页 |
| `Frontend/src/api/admin.js` | Admin API 客户端 |
| `Docs/admin-ui-optimization/` | Admin UI 优化专项文档 |

---

## NL to Workflow 工作原理

NL to Workflow 是 e-Flowly 的核心能力，将自然语言描述转换为可执行的工作流定义。流程分为以下阶段：

### 第一阶段：意图识别与分类

系统分析用户输入，识别操作意图（创建/修改/删除）和工作流类型。系统支持 7 种工作流域分类：问答机器人、数据处理、翻译、内容生成、工作流编排、自动化流程和 Agent。

### 第二阶段：Prompt 组装

根据识别出的域类型，选择对应的专业 Prompt 模板，注入 Few-shot 示例和格式说明，构建完整的 LLM 上下文。

### 第三阶段：LLM 调用

通过 ProviderRegistry 统一路由到配置的 AI 模型（OpenAI GPT-4、Claude、Ollama 等），支持 SSE 流式输出，实时返回生成进度。

### 第四阶段：双模解析

采用双重解析策略保证鲁棒性：

- **主模式**：PydanticOutputParser 结构化解析，直接映射到工作流 Schema
- **降级模式**：正则表达式兜底提取，在 LLM 输出格式偏离时启用

解析后进行字段归一化，自动填充默认节点参数。

### 第五阶段：DAG 验证

生成的工作流 JSON 必须通过严格的 DAG 校验：

- **循环检测**：深度优先搜索确保无环
- **连通性检查**：所有节点可达
- **多起点检测**：工作流必须恰好有一个 Start 节点
- **成本估算**：评估执行所需 Token 和费用

```
用户输入（自然语言）
        │
        ▼
┌───────────────────┐
│  意图识别与分类    │  ──►  域类型判定（7 种工作流域）
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Prompt 组装      │  ──►  领域模板 + Few-shot + 格式说明
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  LLM 调用         │  ──►  ProviderRegistry 路由 → SSE 流式输出
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  双模解析         │  ──►  Pydantic 解析 + Regex 降级
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  DAG 验证         │  ──►  循环检测 + 连通性 + 成本估算
└─────────┬─────────┘
          │
          ▼
   工作流 JSON 输出
```

---

## 多 Agent 协作系统

e-Flowly 实现了基于 ReAct（Reasoning + Acting）模式的多 Agent 协作框架。各 Agent 角色定义清晰，通过消息队列实现异步通信：

| Agent 角色 | 职责 | 核心能力 |
|-----------|------|---------|
| **Planner** | 任务分解与规划 | 意图分解、执行计划编排 |
| **Executor** | 任务执行与工具调用 | 工具绑定、ReAct 循环 |
| **Critic** | 输出评审与反馈 | 结果校验、质量评估 |
| **Reporter** | 结果综合与报告生成 | 数据汇总、格式输出 |
| **Coordinator** | 全局协调与调度 | Agent 编排、状态同步 |

Agent 执行引擎支持：

- 单步调试（Step-through debugger）
- 中断与恢复执行
- 执行路径可视化
- 工具调用日志追踪

---

## 项目结构

```
Flowly-now/
├── Backend/                              # Django 后端
│   ├── config/                           # 项目配置
│   │   ├── settings.py                  # Django 设置（含 Jazzmin）
│   │   ├── urls.py                      # 根路由
│   │   ├── admin_site.py                # 自定义 FlowlyAdminSite
│   │   ├── asgi.py / wsgi.py            # ASGI / WSGI
│   │   └── constants.py                 # 全局常量
│   │
│   ├── admin/                            # ★ 平台管理后台模块
│   │   ├── models.py                    # 系统设置、法律文档、备份等
│   │   ├── views.py                     # Admin REST API
│   │   ├── module_views.py              # 模块化配置 + 公开站点配置
│   │   ├── services/config_service.py   # 配置校验与缓存
│   │   └── management/commands/
│   │       └── seed_platform_config.py  # 法律文档种子数据
│   │
│   ├── users/                            # 用户认证（注册/登录/Token）
│   ├── workflows/                        # 工作流引擎与节点执行
│   ├── nl_to_workflow/                   # 自然语言生成工作流
│   ├── agents/                           # Agent 管理与多 Agent 协作
│   ├── gateway/                          # AI 模型网关
│   ├── rag/                              # RAG 知识库
│   ├── tenants/                          # 多租户
│   ├── marketplace/                      # 模板市场
│   ├── templates/                        # 工作流模板
│   ├── monitoring/                       # 监控与告警
│   ├── training/                         # 模型训练（YOLO 等）
│   ├── website_generator/                # ML 站点工厂
│   ├── datasets/                         # 数据集管理
│   ├── annotations/                      # 数据标注
│   ├── augmentation/                     # 数据增强
│   ├── billing/                          # 计费
│   ├── branding/                         # 品牌定制
│   ├── features/                         # 动态功能开关
│   ├── core/                             # 通知、审计、登录历史
│   ├── scripts/                          # E2E 测试与管理脚本
│   ├── templates/admin/                  # Admin 自定义模板
│   ├── admin_static/                     # Admin 静态资源
│   └── requirements.txt
│
├── Frontend/                             # Vue 3 前端（端口 5200）
│   ├── src/
│   │   ├── api/                         # API 封装（含 admin.js）
│   │   ├── components/                  # 组件（workflow、auth 等）
│   │   ├── composables/                 # 组合式函数
│   │   ├── router/                      # 路由配置
│   │   ├── stores/                      # Pinia 状态
│   │   └── views/                       # 页面视图
│   │       ├── admin/                   # Vue 管理页
│   │       ├── workflow/                # 工作流
│   │       ├── agent/                   # Agent
│   │       └── ...
│   └── vite.config.js                   # 开发端口 5200
│
├── Desktop/                              # Electron 桌面客户端
│   ├── main.js                          # 主进程
│   ├── preload.js                       # 预加载脚本
│   ├── renderer/                        # 打包后的 Frontend SPA
│   └── training-scripts/                # 本地 GPU 训练脚本
│
├── docker/                               # Dockerfile 与 Nginx 配置
├── docker-compose.dev.yml                # 开发基础设施（Qdrant）
├── tests/                                # 测试套件
├── Docs/                                 # 项目文档中心
├── Scripts/                              # 工具脚本
├── .env.example                          # 环境变量模板
└── README.md                             # 本文件
```

---

## 快速开始

### 前置要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.12+ | 后端运行环境 |
| Node.js | 20+ | 前端构建工具 |
| MySQL | 8.0+ | 主业务数据库 |
| Redis | 7+ | 缓存与消息队列（Celery / WebSocket） |
| PostgreSQL | 16+ | 可选，pgvector 向量存储 |
| Docker | Latest | 可选，启动 Qdrant 等基础设施 |

### 方式一：本地开发（推荐）

#### 1. 克隆与环境配置

```bash
git clone <repository-url>
cd Flowly-now

# 复制环境变量（根目录或 Backend 目录均可）
cp .env.example .env
# 编辑 .env，至少配置：DJANGO_SECRET_KEY、DB_PASSWORD
```

#### 2. 后端

```bash
cd Backend

# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户 + 平台种子数据
python manage.py createsuperuser
python manage.py seed_platform_config

# 启动开发服务器
python manage.py runserver 127.0.0.1:8000

# 需要 WebSocket（训练进度、工作流实时推送）时使用 Daphne：
# daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

#### 3. 前端

```bash
cd Frontend
npm install
npm run dev
# → http://localhost:5200
```

#### 4. Celery Worker（异步任务，可选）

```bash
cd Backend
# Redis 需已启动
celery -A config worker -l INFO -P solo   # Windows 建议 -P solo
celery -A config beat -l INFO             # 定时任务
```

#### 5. 可选基础设施

```bash
# Qdrant 向量库（本地开发）
docker compose -f docker-compose.dev.yml up -d qdrant
# → http://localhost:6333

# Redis（Windows 可用 Docker）
docker run -d -p 6379:6379 redis:7
```

### 方式二：Docker 部署

> 仓库根目录**暂无**完整的 `docker-compose.yml` 全栈编排文件。`docker/` 目录提供 Dockerfile 与 Nginx 配置参考；`docker-compose.dev.yml` 仅包含 Qdrant 服务。完整 Docker 部署步骤见 [`Docs/guides/deployment/docker.md`](Docs/guides/deployment/docker.md)。

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 用户前端 | http://localhost:5200 | Vite 开发服务器 |
| 后端 API | http://localhost:8000 | Django / Daphne |
| Django Admin | http://localhost:8000/admin/ | **主管理后台**（Jazzmin） |
| Vue 管理页 | http://localhost:5200/admin | 实验性管理界面 |
| API 文档 | http://localhost:8000/api/docs/ | Swagger UI |
| Admin API | http://localhost:8000/api/v1/admin/ | 超级用户 REST API |

---

## 核心模块详解

### 工作流执行引擎

工作流以 DAG（有向无环图）形式存储，通过拓扑排序实现可靠执行：

- **节点并发**：具有独立依赖的节点可并行执行
- **状态追踪**：每个节点记录 pending / running / success / failed 状态
- **重试机制**：支持节点级别的重试配置和超时控制
- **执行日志**：完整的输入输出记录，支持执行回放

### AI 模型网关

采用注册中心模式，通过 `ProviderRegistry` 统一管理 AI 模型提供者：

```python
from gateway.providers.registry import get_registry, register_default_providers

register_default_providers()
registry = get_registry()
response = registry.get("openai").generate(
    messages=messages,
    model=config.model,
    stream=True,
)
```

支持 OpenAI GPT 系列、Anthropic Claude 系列、Ollama 本地模型、DashScope 等。

### Agent 执行引擎

基于 ReAct 模式的 Agent 引擎，支持工具定义与动态绑定、多轮推理循环、工具调用错误处理与恢复、执行路径可视化追踪。

### RAG 检索服务

| 向量库 | 类型 | 说明 |
|--------|------|------|
| Qdrant | 云/自托管 | 高性能向量检索（`docker-compose.dev.yml`） |
| pgvector | PostgreSQL 扩展 | 轻量级向量存储 |
| Milvus | 云/自托管 | 分布式向量引擎 |
| Chroma | 本地 | 轻量级嵌入式向量库 |
| Pinecone | 云服务 | 全托管向量数据库 |

### 平台配置服务

`admin/services/config_service.py` 统一管理：

- 系统设置读写与校验
- 公开站点配置缓存（`GET /api/v1/public/site-config/`）
- 功能可见性规则合并
- SMTP 参数提取与邮件发送

---

## API 接口

### 认证方式

- **Token 认证**：`Authorization: Token <token>`
- **Session 认证**：Cookie 会话（Django Admin 使用）
- **WebSocket 鉴权**：`?token=<JWT>`（浏览器握手无法带 Authorization 头）

### 主要接口

| 模块 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/v1/auth/` | 登录、注册、Token 刷新、密码重置 |
| 工作流 | `/api/v1/workflows/` | CRUD、执行、版本控制 |
| NL 生成 | `/api/v1/nl-workflow/` | 自然语言生成工作流 |
| Agent | `/api/v1/agents/` | Agent 创建、调试、执行 |
| RAG | `/api/v1/rag/` | 知识库集合管理 |
| 数据集 | `/api/v1/datasets/` | 数据集上传与管理 |
| AI 网关 | `/api/v1/gateway/` | 模型配置与用量统计 |
| 模板 | `/api/v1/templates/` | 工作流模板 |
| 市场 | `/api/v1/marketplace/` | 模板发布与发现 |
| 团队 | `/api/v1/tenants/` | 多租户管理 |
| 监控 | `/api/v1/monitoring/` | 系统运行监控 |
| 训练 | `/api/v1/training/` | YOLO 等训练任务 |
| 建站 | `/api/v1/website-generator/` | ML 站点工厂 |
| **管理后台** | `/api/v1/admin/` | 平台管理 REST API（超级用户） |
| **公开配置** | `/api/v1/public/site-config/` | 前端运行时配置 |
| **登录助手** | `/api/v1/public/auth-assistant/chat/` | 登录页 AI 助手 |

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register/` | 用户注册 |
| POST | `/api/v1/auth/login/` | 用户登录 |
| POST | `/api/v1/auth/logout/` | 退出登录 |
| POST | `/api/v1/auth/refresh/` | Token 刷新 |
| GET/PATCH | `/api/v1/auth/user/` | 用户资料 |
| POST | `/api/v1/auth/change-password/` | 修改密码 |
| POST | `/api/v1/auth/password-reset/` | 请求密码重置 |
| POST | `/api/v1/auth/password-reset/confirm/` | 确认密码重置 |

### NL to Workflow 核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/nl-workflow/sessions/` | 创建新会话 |
| GET | `/api/v1/nl-workflow/sessions/` | 获取会话列表 |
| POST | `/api/v1/nl-workflow/sessions/{id}/message/` | 发送消息（同步） |
| POST | `/api/v1/nl-workflow/sessions/{id}/message/stream/` | 发送消息（SSE 流式） |
| POST | `/api/v1/nl-workflow/sessions/{id}/confirm/` | 确认生成工作流 |
| POST | `/api/v1/nl-workflow/preview/` | 预览生成的工作流 JSON |
| POST | `/api/v1/nl-workflow/analyze-intent/` | 分析用户意图 |
| GET | `/api/v1/nl-workflow/models/` | 获取可用模型列表 |

---

## 前端路由

### 公开路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Landing | 首页落地页 |
| `/login` | Login | 登录页 |
| `/register` | Register | 注册页 |
| `/forgot-password` | ForgotPassword | 忘记密码 |
| `/reset-password` | ResetPassword | 重置密码 |

### 工作流相关

| 路径 | 页面 | 说明 |
|------|------|------|
| `/workflows` | WorkflowList | 工作流列表 |
| `/workflows/new` | WorkflowCreate | 创建工作流 |
| `/workflows/:id/edit` | WorkflowEdit | 编辑工作流 |
| `/workflows/:id` | WorkflowDetail | 工作流详情 |
| `/workflows/:id/execute` | WorkflowExecute | 执行工作流 |
| `/workflows/diff` | WorkflowDiff | 工作流对比 |
| `/nl-create` | NLCreator | 自然语言创建工作流 |

### Agent 与知识库

| 路径 | 页面 | 说明 |
|------|------|------|
| `/agents` | AgentList | Agent 列表 |
| `/agents/new` | AgentCreate | 创建 Agent |
| `/agents/:id/edit` | AgentEdit | 编辑 Agent |
| `/agents/:id/debug` | AgentDebugger | Agent 调试器 |
| `/knowledge` | KnowledgeBase | 知识库首页 |
| `/knowledge/:id` | CollectionDetail | 集合详情页 |
| `/vector-stores` | VectorStoreList | 向量存储列表 |

### 数据与训练

| 路径 | 页面 | 说明 |
|------|------|------|
| `/datasets` | DatasetList | 数据集列表 |
| `/datasets/:id` | DatasetDetail | 数据集详情 |
| `/dataset-recommend` | DatasetRecommend | 数据集推荐 |
| `/augmentations` | AugmentationStatus | 数据增强状态 |
| `/annotations/:id` | AnnotationWorkspace | 标注工作台 |
| `/training` | TrainingRedirect | 训练已迁移至工作流 |
| `/projects/:id` | GeneratedSiteDetail | ML 站点工厂输出 |

### 设置与管理

| 路径 | 页面 | 说明 |
|------|------|------|
| `/settings` | Settings | 设置（容器） |
| `/settings/profile` | Profile | 个人资料 |
| `/settings/api-keys` | ApiKeys | API Key 管理 |
| `/settings/billing` | Billing | 账单管理 |
| `/team` | Team | 团队管理 |
| `/monitoring` | Monitoring | 系统监控 |
| `/admin` | Admin | Vue 管理页（需 staff/superuser） |

---

## 数据库模型

项目使用 **Django ORM + Migration** 管理数据库，无独立 `.sql` 初始化文件。登录/注册相关表通过迁移自动创建。

> **完整表名清单（120 张表，按模块分类）：** [`Docs/reference/database-tables.md`](Docs/reference/database-tables.md)

### 认证与用户

| 表名 | 来源 | 说明 |
|------|------|------|
| `users` | `users/models.py` | 自定义 User 模型（扩展角色、执行限额等） |
| `login_history` | `core/models/audit.py` | 登录历史审计 |
| `authtoken_token` | DRF authtoken | API Token 认证 |
| `auth_*` | Django 内置 | 权限、组等 |

查看迁移对应 SQL：

```bash
cd Backend
python manage.py sqlmigrate users 0001
python manage.py sqlmigrate core 0001
```

### 核心模型关系

```
Tenant
    │
    ├── TenantMembership
    │
    ├── Workflow
    │     ├── Node
    │     │     └── NodeExecution
    │     ├── Edge
    │     └── WorkflowExecution
    │
    ├── Agent
    │     └── AgentExecution
    │
    ├── NLSession
    │
    ├── VectorStore
    │     └── Collection
    │
    └── Dataset
          └── DatasetRecord
```

### 平台管理模型

```
SystemSetting          # 全局键值配置
LegalDocument          # 法律文档（版本化）
UserTermsAcceptance    # 条款同意记录
FeatureVisibilityRule  # 功能可见性
GatewayRouteRule       # 网关路由
PaymentProviderConfig  # 支付配置
EmailSendLog           # 邮件日志
BackupRecord           # 备份记录
```

---

## 环境变量

### 必需配置

```bash
# 应用
APP_NAME=Flowly
DEBUG=true
DJANGO_SECRET_KEY=your-secret-key-here   # python -c "import secrets; print(secrets.token_urlsafe(50))"

# 主数据库（MySQL）
DB_NAME=flowly_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306          # 根目录 .env.example 默认为 3307，按实际环境调整

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0

# 前端
FRONTEND_URL=http://localhost:5200
CORS_ALLOWED_ORIGINS=http://localhost:5200,http://127.0.0.1:5200
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### 可选配置

```bash
# 向量数据库（PostgreSQL + pgvector，可选）
PG_NAME=flowly_vector
PG_USER=flowly
PG_PASSWORD=your_password
PG_HOST=localhost
PG_PORT=5432

# AI 模型
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=sk-ant-xxx
OLLAMA_BASE_URL=http://localhost:11434

# LangSmith 追踪
LANGSMITH_API_KEY=xxx
LANGSMITH_TRACING=true

# Docker 沙箱（代码执行）
DOCKER_ENABLED=auto
DOCKER_MEMORY_LIMIT=256
DOCKER_TIMEOUT=60

# 备份目录
BACKUP_DIR=Backend/backups
```

环境变量模板：

| 文件 | 说明 |
|------|------|
| `.env.example` | 根目录 monorepo 模板 |
| `Backend/.env.example` | 后端专用（含 `FRONTEND_URL`） |
| `Frontend/.env.example` | 前端 Vite 变量 |
| `docker/.env.example` | Docker 部署变量 |

---

## 部署与基础设施

### 当前仓库提供的 Docker 资源

| 资源 | 说明 |
|------|------|
| `docker-compose.dev.yml` | 仅 Qdrant（端口 6333/6334） |
| `docker/Dockerfile.backend` | 后端镜像 |
| `docker/Dockerfile.frontend` | 前端镜像 |
| `docker/Dockerfile.nginx` | Nginx 镜像 |
| `docker/nginx/` | Nginx 配置 |

### 生产部署建议

1. **数据库**：使用托管 MySQL，启用自动备份
2. **缓存**：Redis 主从或集群
3. **对象存储**：S3 / GCS 存储媒体文件
4. **负载均衡**：多实例 + 云负载均衡器
5. **SSL**：Let's Encrypt 或云证书
6. **监控**：Prometheus + Grafana
7. **管理后台**：限制 `/admin/` 访问 IP，启用 `require_2fa_for_admin`

详细部署文档：[`Docs/guides/deployment/docker.md`](Docs/guides/deployment/docker.md)

---

## 测试体系

### 测试覆盖范围

| 测试类型 | 工具 | 覆盖范围 |
|---------|------|---------|
| 后端单元测试 | pytest + Django TestCase | 模型、视图、序列化器、业务逻辑 |
| NL 模块专项测试 | pytest | 意图识别、双模解析、DAG 验证 |
| E2E 端到端测试 | Playwright | 用户注册、NL 生成、工作流执行 |
| 前端单元测试 | Vitest | 组件、Composables、工具函数 |
| 冒烟测试 | `Backend/scripts/` | API + WebSocket 全链路验证 |

### 运行测试

```bash
# 后端测试
cd Backend
pytest --cov=. --cov-report=html --cov-report=term

# NL 模块专项测试
pytest tests/nl_workflow/ -v

# API 冒烟测试（需 Daphne 运行中）
python scripts/frontend_user_api_smoke_test.py

# E2E 测试
cd Frontend
npm run test:e2e

# 前端单元测试
npm run test
```

---

## 文档索引

| 场景 | 文档 |
|------|------|
| 本地开发 | [`Docs/guides/deployment/local-dev.md`](Docs/guides/deployment/local-dev.md) |
| Docker 部署 | [`Docs/guides/deployment/docker.md`](Docs/guides/deployment/docker.md) |
| 项目结构参考 | [`Docs/reference/PROJECT-STRUCTURE.md`](Docs/reference/PROJECT-STRUCTURE.md) |
| **数据库表名参考** | [`Docs/reference/database-tables.md`](Docs/reference/database-tables.md) |
| 搭建手册 | [`Docs/reference/setup-guide.md`](Docs/reference/setup-guide.md) |
| Admin UI 优化 | [`Docs/admin-ui-optimization/README.md`](Docs/admin-ui-optimization/README.md) |
| 桌面端 ML 站点工厂 | [`Docs/desktop-ml-site-factory/README.md`](Docs/desktop-ml-site-factory/README.md) |
| 桌面客户端 | [`Desktop/README.md`](Desktop/README.md) |
| 文档中心总览 | [`Docs/README.md`](Docs/README.md) |

---

## 贡献指南

欢迎提交 Pull Request 和 Issue。在提交前，请确保：

- 代码符合项目的命名规范和编码风格
- 新功能包含对应的测试用例
- 所有测试通过
- 文档已更新（如有必要）
- 管理后台相关变更需同步更新 Admin 文档或 `Docs/admin-ui-optimization/`

---

## License

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。
