# Flowly 工作流平台搭建指南

> **技术栈**: Django + Vue 3 + LangChain + MySQL
>
> **目标**: 打造一个可视化的 AI 工作流系统，支持多模型统一管理（类似 Flowise / Dify）

---

## 目录

1. [准备工作：安装必要软件](#第1步-准备工作安装必要软件)
2. [Step 1 - 创建项目文件夹结构](#step-1---创建项目文件夹结构)
3. [Step 2 - 创建后端 Django 项目](#step-2---创建后端-django-项目)
4. [Step 3 - AI 模型网关设计](#step-3---ai-模型网关设计)
5. [Step 4 - Django 模型设计 + 完整数据库设计](#step-4---django-模型设计)
   - [4.2.1 数据库设计概述](#421-数据库设计概述)
   - [4.2.2 ER 实体关系图](#422-er-实体关系图)
   - [4.2.3 完整数据表设计](#423-完整数据表设计)
   - [4.2.4 索引设计详解](#424-索引设计详解)
   - [4.2.5 Django 模型完整代码](#425-django-模型完整代码)
   - [4.2.6 数据库初始化脚本](#426-数据库初始化脚本)
   - [4.2.7 数据库设计规范总结](#427-数据库设计规范总结)
6. [Step 5 - Django REST API](#step-5---django-rest-api)
7. [Step 6 - Vue 前端开发](#step-6---vue-前端开发)
8. [Step 7 - 集成 LangChain](#step-7---集成-langchain)
9. [Step 8 - 工作流核心功能](#step-8---工作流核心功能)
10. [Step 9 - 前后端联调](#step-9---前后端联调)
    - [9.5.1 系统交互架构](#951-系统交互架构)
    - [9.5.2 前后端数据模型对应关系](#952-前后端数据模型对应关系)
    - [9.5.3 前端 API 层设计](#953-前端-api-层设计)
    - [9.5.4 前端类型定义](#954-前端类型定义)
    - [9.5.5 Pinia 状态管理](#955-pinia-状态管理)
    - [9.5.6 后端 Django API 视图](#956-后端-django-api-视图)
    - [9.5.7 后端序列化器](#957-后端序列化器)
    - [9.5.8 数据库操作层](#958-数据库操作层)
    - [9.5.9 WebSocket 实时通信](#959-websocket-实时通信)
    - [9.5.10 完整数据流示例](#9510-完整数据流示例)
    - [9.5.11 总结：前后端数据库交互核心要点](#9511-总结前后端数据库交互核心要点)
    - [9.5.12 API 健壮性自查清单](#9512-api-健壮性自查清单)
        - [9.5.12.1 后端健壮性检查](#95121-后端健壮性检查)
        - [9.5.12.2 前端健壮性检查](#95122-前端健壮性检查)
        - [9.5.12.3 健壮性检查清单](#95123-健壮性检查清单)
        - [9.5.12.4 典型场景处理](#95124-典型场景处理)
11. [Step 10 - 部署上线](#step-10---部署上线)
12. [Step 11 - 异步任务系统 (Celery)](#step-11---异步任务系统-celery)
13. [Step 12 - 实时通信 (WebSocket)](#step-12---实时通信-websocket)
14. [Step 13 - 用户认证系统](#step-13---用户认证系统)
15. [Step 14 - Prompt 模板系统](#step-14---prompt-模板系统)
16. [Step 15 - 执行日志与版本管理](#step-15---执行日志与版本管理)
17. [Step 16 - 前端完整组件代码](#step-16---前端完整组件代码)
18. [Step 17 - 后端完整 API 实现](#step-17---后端完整-api-实现)
19. [Step 18 - 测试文档](#step-18---测试文档)
20. [Step 19 - Nginx + SSL 配置](#step-19---nginx--ssl-配置)
21. [Step 20 - 数据库优化](#step-20---数据库优化)
22. [Step 21 - 安全加固方案](#step-21---安全加固方案)
23. [Step 22 - CI/CD 流水线](#step-22---cicd-流水线)
24. [Step 23 - 拖拽节点增强功能](#step-23---拖拽节点增强功能)
25. [Step 24 - 变量与上下文管理](#step-24---变量与上下文管理)
26. [Step 25 - 高级节点类型](#step-25---高级节点类型)
27. [Step 26 - RAG 增强功能](#step-26---rag-增强功能)
28. [Step 27 - 团队协作与权限](#step-27---团队协作与权限)
29. [Step 28 - 监控与告警系统](#step-28---监控与告警系统)
30. [Step 29 - 多租户与计费](#step-29---多租户与计费)
31. [Step 30 - API 与集成生态](#step-30---api-与集成生态)
32. [Step 31 - 用户体验优化](#step-31---用户体验优化)
33. [Step 32 - 流式执行与 Streaming UX](#step-32---流式执行与-streaming-ux)
34. [Step 33 - 自然语言生成工作流 (NL to Workflow)](#step-33---自然语言生成工作流-nl-to-workflow)
35. [Step 34 - AI Agent 智能体编排](#step-34---ai-agent-智能体编排)
36. [附录 A - 常见问题排查 (FAQ)](#附录-a---常见问题排查-faq)
37. [附录 B - 开发环境最佳实践](#附录-b---开发环境最佳实践)
38. [附录 C - API 接口详细文档](#附录-c---api-接口详细文档)
39. [附录 D - 错误处理和日志最佳实践](#附录-d---错误处理和日志最佳实践)
40. [附录 E - 性能优化指南](#附录-e---性能优化指南)
41. [附录 F - 安全加固详细说明](#附录-f---安全加固详细说明)
42. [附录 G - 企业级功能优化（对标商业工作流平台）](#附录-g---企业级功能优化对标商业工作流平台)

---

## 项目整体目录结构

```
Flowly-now/
│
├── 📂 Docs/                          # 文档目录
│   └── setup-guide.md                # 项目搭建指南（本文件）
│
├── 📂 Backend/                        # 后端 Django 项目
│   │
│   ├── 📂 config/                    # Django 配置
│   │   ├── __init__.py
│   │   ├── settings.py               # 主配置文件
│   │   ├── urls.py                   # URL 路由
│   │   ├── wsgi.py                   # WSGI 入口
│   │   ├── asgi.py                   # ASGI 入口（支持 WebSocket）
│   │   └── manage.py                 # Django 管理脚本
│   │
│   ├── 📂 workflows/                 # 工作流核心模块
│   │   ├── __init__.py
│   │   ├── models.py                 # 工作流数据模型
│   │   ├── views.py                  # REST API 视图
│   │   ├── serializers.py            # DRF 序列化器
│   │   ├── urls.py                   # 路由配置
│   │   ├── executor.py               # 工作流执行引擎
│   │   ├── tasks.py                  # Celery 异步任务
│   │   ├── consumers.py              # WebSocket Consumer
│   │   └── services.py               # 业务逻辑服务
│   │
│   ├── 📂 agents/                    # AI Agent 模块
│   │   ├── __init__.py
│   │   ├── models.py                 # Agent 数据模型
│   │   ├── engine.py                 # Agent 执行引擎
│   │   ├── multi_agent.py            # 多 Agent 编排
│   │   ├── tools/                    # 内置工具
│   │   │   ├── __init__.py
│   │   │   ├── search.py             # 搜索工具
│   │   │   ├── calculator.py         # 计算器工具
│   │   │   ├── web_scraper.py        # 网页爬虫
│   │   │   ├── database.py           # 数据库查询
│   │   │   └── code_executor.py       # 代码执行
│   │   └── views.py                  # Agent API
│   │
│   ├── 📂 nl_to_workflow/            # 自然语言生成工作流
│   │   ├── __init__.py
│   │   ├── services.py               # NL 解析引擎
│   │   ├── views.py                  # API 视图
│   │   └── urls.py                   # 路由
│   │
│   ├── 📂 users/                     # 用户认证模块
│   │   ├── __init__.py
│   │   ├── models.py                 # 用户模型
│   │   ├── views.py                  # 认证 API
│   │   └── serializers.py            # 序列化器
│   │
│   ├── 📂 prompts/                   # Prompt 模板模块
│   │   ├── __init__.py
│   │   ├── models.py                 # 模板模型
│   │   └── views.py                  # 模板 API
│   │
│   ├── 📂 monitoring/                # 监控告警模块
│   │   ├── __init__.py
│   │   ├── models.py                 # 监控数据模型
│   │   ├── views.py                  # 监控 API
│   │   └── tasks.py                  # 告警任务
│   │
│   ├── 📂 tenants/                   # 多租户模块
│   │   ├── __init__.py
│   │   ├── models.py                 # 租户模型
│   │   └── views.py                  # 租户 API
│   │
│   └── 📂 utils/                     # 工具函数
│       ├── __init__.py
│       ├── decorators.py             # 装饰器
│       ├── exceptions.py             # 自定义异常
│       └── helpers.py                # 辅助函数
│
├── 📂 Frontend/                       # 前端 Vue 3 项目
│   │
│   ├── 📂 public/                    # 静态资源
│   │   └── index.html
│   │
│   ├── 📂 src/
│   │   ├── 📂 api/                   # API 请求
│   │   │   ├── index.js              # Axios 实例
│   │   │   ├── auth.js               # 认证 API
│   │   │   ├── workflow.js            # 工作流 API
│   │   │   ├── agent.js              # Agent API
│   │   │   └── nl-workflow.js        # NL 生成 API
│   │   │
│   │   ├── 📂 assets/                # 资源文件
│   │   │   ├── styles/               # 全局样式
│   │   │   │   ├── variables.scss    # 主题变量
│   │   │   │   └── global.scss       # 全局样式
│   │   │   └── images/               # 图片资源
│   │   │
│   │   ├── 📂 components/            # 组件库
│   │   │   ├── 📂 common/            # 通用组件
│   │   │   │   ├── Button.vue
│   │   │   │   ├── Modal.vue
│   │   │   │   └── Loading.vue
│   │   │   │
│   │   │   ├── 📂 workflow/          # 工作流组件
│   │   │   │   ├── WorkflowCanvas.vue     # 画布
│   │   │   │   ├── WorkflowNode.vue       # 节点
│   │   │   │   ├── WorkflowEdge.vue       # 连线
│   │   │   │   ├── NodePanel.vue          # 节点面板
│   │   │   │   ├── PropertyPanel.vue      # 属性面板
│   │   │   │   ├── MiniMap.vue            # 迷你地图
│   │   │   │   └── StreamExecutionPanel.vue # 流式执行面板
│   │   │   │
│   │   │   └── 📂 agent/             # Agent 组件
│   │   │       ├── AgentCard.vue
│   │   │       └── ToolList.vue
│   │   │
│   │   ├── 📂 composables/           # 组合式函数
│   │   │   ├── useWorkflow.js        # 工作流逻辑
│   │   │   ├── useAgent.js           # Agent 逻辑
│   │   │   └── useWebSocket.js       # WebSocket
│   │   │
│   │   ├── 📂 layouts/               # 布局组件
│   │   │   ├── Default.vue           # 默认布局
│   │   │   └── Blank.vue             # 空白布局
│   │   │
│   │   ├── 📂 router/                # 路由配置
│   │   │   ├── index.js
│   │   │   └── routes.js
│   │   │
│   │   ├── 📂 stores/                # Pinia 状态管理
│   │   │   ├── auth.js               # 认证状态
│   │   │   ├── workflow.js           # 工作流状态
│   │   │   └── agent.js              # Agent 状态
│   │   │
│   │   ├── 📂 utils/                 # 工具函数
│   │   │   ├── storage.js            # 本地存储
│   │   │   ├── validation.js         # 表单验证
│   │   │   └── formatters.js         # 格式化函数
│   │   │
│   │   ├── 📂 views/                 # 页面视图
│   │   │   ├── 📂 auth/              # 认证页面
│   │   │   │   ├── Login.vue
│   │   │   │   └── Register.vue
│   │   │   │
│   │   │   ├── 📂 workflow/           # 工作流页面
│   │   │   │   ├── List.vue          # 工作流列表
│   │   │   │   ├── Editor.vue        # 工作流编辑器
│   │   │   │   ├── Execute.vue       # 执行页面
│   │   │   │   └── Detail.vue        # 详情页面
│   │   │   │
│   │   │   ├── 📂 agent/             # Agent 页面
│   │   │   │   ├── List.vue          # Agent 列表
│   │   │   │   ├── Create.vue        # 创建 Agent
│   │   │   │   └── Debugger.vue      # Agent 调试器
│   │   │   │
│   │   │   ├── 📂 nl-workflow/       # NL 生成页面
│   │   │   │   └── Creator.vue       # 对话式生成器
│   │   │   │
│   │   │   └── 📂 dashboard/         # 仪表盘
│   │   │       ├── Home.vue
│   │   │       └── Analytics.vue
│   │   │
│   │   ├── App.vue                   # 根组件
│   │   └── main.js                   # 入口文件
│   │
│   ├── package.json
│   ├── vite.config.js                # Vite 配置
│   ├── .env                         # 环境变量
│   └── .env.production              # 生产环境变量
│
├── 📂 docker/                        # Docker 配置
│   ├── docker-compose.yml            # 编排文件
│   ├── Dockerfile.backend            # 后端镜像
│   ├── Dockerfile.frontend          # 前端镜像
│   ├── nginx/
│   │   ├── Dockerfile
│   │   └── conf.d/
│   │       └── default.conf         # Nginx 配置
│   └── redis/
│       └── redis.conf               # Redis 配置
│
├── 📂 scripts/                       # 脚本文件
│   ├── init_db.sh                   # 初始化数据库
│   ├── backup.sh                    # 备份脚本
│   └── deploy.sh                    # 部署脚本
│
├── 📂 tests/                        # 测试目录
│   ├── 📂 backend/                  # 后端测试
│   │   ├── test_workflows.py
│   │   ├── test_agents.py
│   │   └── test_api.py
│   └── 📂 frontend/                 # 前端测试
│       ├── unit/
│       └── e2e/
│
├── 📂 .github/                      # GitHub 配置
│   └── workflows/
│       └── ci.yml                  # CI/CD 流水线
│
├── .gitignore                       # Git 忽略文件
├── README.md                        # 项目说明
├── requirements.txt                 # Python 依赖
└── package.json                     # NPM 依赖（根目录）
```

---

## 项目模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              前端 (Vue 3)                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │编辑器   │  │Agent    │  │NL生成   │  │执行面板 │  │仪表盘   │    │
│  │Canvas  │  │调试器   │  │对话    │  │流式输出 │  │Analytics│    │
│  └───┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘    │
└──────┼───────────┼─────────────┼─────────────┼────────────┼──────────┘
       │           │             │             │            │
       ▼           ▼             ▼             ▼            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API 网关 (Django REST)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CORS / 认证 / 限流 / 日志                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │Workflows  │  │  Agents    │  │NL→Workflow│  │  Monitoring│       │
│  │API        │  │  API       │  │API        │  │  API       │       │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘       │
└────────┼───────────────┼───────────────┼───────────────┼───────────────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           业务逻辑层                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │工作流执行  │  │Agent引擎   │  │NL解析引擎  │  │监控告警    │       │
│  │Executor   │  │Engine      │  │Parser      │  │Monitor     │       │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘       │
└────────┼───────────────┼───────────────┼───────────────┼───────────────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI 集成层                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    LangChain / LlamaIndex                       │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │   │
│  │  │OpenAI   │ │Anthropic│ │本地模型 │ │向量存储 │ │工具调用 │    │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 技术栈总结

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端** | Vue 3 + Vite + TypeScript | 用户界面 |
| **前端 UI** | Element Plus | UI 组件库 |
| **前端状态** | Pinia | 状态管理 |
| **前端图表** | ECharts | 数据可视化 |
| **后端** | Django 5 + DRF | API 服务 |
| **后端异步** | Celery + Redis | 异步任务 |
| **实时通信** | Django Channels | WebSocket |
| **AI 框架** | LangChain / LlamaIndex | AI 能力 |
| **数据库** | MySQL | 数据存储 |
| **向量存储** | Qdrant / Milvus | 向量检索 |
| **缓存** | Redis | 缓存/消息队列 |
| **部署** | Docker + Nginx | 容器化部署 |

---

## 第1步 准备工作：安装必要软件

在开始之前，你需要在电脑上安装以下软件：

### 1.1 Python 3.12（后端运行环境）

下载地址：https://www.python.org/downloads/

> **注意**：建议使用 Python 3.12 版本

安装时 **务必勾选**：
- Add Python to PATH（添加到环境变量）
- Use admin privileges for Python installs

安装完成后验证：
```powershell
# 查看 Python 版本（应该是 3.12.x）
python --version

# 查看 pip 版本
pip --version

# 查看所有已安装的 Python 版本
py -0
```

### 1.2 Node.js（前端运行环境）

下载地址：https://nodejs.org/（选择 LTS 长期支持版）

安装完成后验证：
```powershell
node --version
npm --version
```

### 1.3 MySQL（数据库）

下载地址：https://dev.mysql.com/downloads/mysql/

或者使用更简单的 **XAMPP**（包含 MySQL + PHPMyAdmin）：
下载地址：https://www.apachefriends.org/

安装完成后验证：
```powershell
mysql --version
```

### 1.4 Git（版本控制）

下载地址：https://git-scm.com/download/win

安装完成后验证：
```powershell
git --version
```

### 1.5 IDE 推荐

- **PyCharm** - 用于 Django 后端开发（https://www.jetbrains.com/pycharm/）
- **VS Code** - 用于 Vue 前端开发（https://code.visualstudio.com/）
- 或者直接用 **Cursor**（你现在正在用的！）

---

## Step 1 - 创建项目文件夹结构

### 1.1 创建根目录

在 `e:\Flowly-now` 下创建项目：

```powershell
cd e:\Flowly-now
```

### 1.2 创建完整文件夹结构

在 PowerShell 中运行以下命令：

```powershell
cd e:\Flowly-now

# 创建主项目目录
New-Item -ItemType Directory -Path "Backend" -Force
New-Item -ItemType Directory -Path "Frontend" -Force
New-Item -ItemType Directory -Path "Docs" -Force
New-Item -ItemType Directory -Path "Scripts" -Force

# 查看创建的结构
Get-ChildItem
```

### 1.3 最终文件夹结构

```
e:\Flowly-now\workflow-project\
|
├── Backend/                 # Django 后端
│   ├── config/             # Django 项目配置
│   ├── workflow/           # 工作流应用
│   ├── gateway/            # AI 模型网关应用
│   └── manage.py          # Django 管理脚本
│
├── Frontend/              # Vue 前端
│   ├── src/
│   ├── public/
│   └── package.json
│
├── Docs/                  # 文档目录
│   └── setup-guide.md
│
└── scripts/               # 辅助脚本
    └── setup.bat
```

---

## Step 2 - 创建后端 Django 项目

### 2.1 创建虚拟环境

```powershell
cd e:\Flowly-now\Backend

# 使用 Python 3.12 创建虚拟环境
py -3.12 -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate
```

激活成功后，命令行前面会显示 `(venv)`。

### 2.2 安装 Django 和相关依赖

```powershell
# 确保在虚拟环境中（看到 (venv) 前缀）
pip install django
pip install djangorestframework
pip install django-cors-headers
pip install mysqlclient
pip install langchain
pip install langchain-openai
pip install langchain-community
pip install python-dotenv
```

### 2.3 创建 Django 项目

Django 可以直接创建项目文件夹：

```powershell
# 在 Backend 目录下创建 Django 项目
django-admin startproject config .
```

这会生成：

```
Backend/
├── config/              # 项目配置文件夹
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── manage.py            # Django 管理脚本
```

### 2.4 创建 Django 应用

```powershell
# 创建工作流应用
python manage.py startapp workflow

# 创建 AI 模型网关应用
python manage.py startapp gateway
```

### 2.5 配置 MySQL 数据库

创建 `.env` 文件（`Backend/.env`）：

```
DEBUG=True
SECRET_KEY=your-super-secret-key-change-in-production
DB_NAME=flowly
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

编辑 `Backend/config/settings.py`，在 `INSTALLED_APPS` 中注册应用：

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'workflow',
    'gateway',
]
```

### 2.6 创建 requirements.txt

在 `Backend` 目录下创建 `requirements.txt`：

```
django>=4.2,<5.0
djangorestframework>=3.14,<4.0
django-cors-headers>=4.0,<5.0
mysqlclient>=2.2,<3.0
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.10
python-dotenv>=1.0.0
celery>=5.3.0
redis>=5.0.0
openai>=1.0.0
anthropic>=0.18.0
httpx>=0.25.0
cryptography>=41.0.0
```

### 2.7 测试 Django 安装

```powershell
# 创建数据库（先在 MySQL 中执行）
# mysql -u root -p
# CREATE DATABASE flowly_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 执行迁移
python manage.py migrate

# 启动服务器
python manage.py runserver
```

如果看到以下内容，说明 Django 安装成功：

```
Starting development server at http://127.0.0.1:8000/
```

按 `Ctrl + C` 停止服务器。

---

## Step 3 - AI 模型网关设计

### 3.1 架构概述

本系统支持 **两种模型来源**：
1. **平台模型** - 平台管理员添加，使用平台 API Key 付费
2. **自定义模型** - 用户自行添加，用户填写 endpoint + API Key，自己付费

```
用户请求 → 统一 API → 模型调度层 → 不同 Provider
                    ↓
              模型注册表 (Registry)
                    ↓
         ┌─────────┴─────────┐
         ↓                   ↓
   平台提供模型          用户自添模型
   (平台付钱)           (用户自己付钱)
```

### 3.2 核心数据模型

```python
# gateway/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid


class PlatformModel(models.Model):
    """平台提供的模型（管理员添加）"""
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google'),
        ('cohere', 'Cohere'),
        ('local', '本地模型'),
        ('other', '其他'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="模型名称")
    model_id = models.CharField(max_length=100, verbose_name="模型ID")  # 如 gpt-4o
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, verbose_name="提供商")
    endpoint = models.URLField(blank=True, verbose_name="API 端点")
    api_key = models.CharField(max_length=500, verbose_name="API Key")  # 平台统一付费
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_default = models.BooleanField(default=False, verbose_name="是否为默认模型")
    config = models.JSONField(default=dict, verbose_name="模型配置")
    description = models.TextField(blank=True, verbose_name="描述")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_models'
        verbose_name = '平台模型'
        verbose_name_plural = '平台模型'

    def __str__(self):
        return f"{self.name} ({self.provider})"


class UserAPIKey(models.Model):
    """用户添加的 API Key"""
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google'),
        ('cohere', 'Cohere'),
        ('ollama', 'Ollama'),
        ('vllm', 'vLLM'),
        ('other', '其他'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=200, verbose_name="名称")
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, verbose_name="提供商")
    endpoint = models.URLField(verbose_name="API 端点")
    api_key = models.CharField(max_length=500, verbose_name="API Key")
    is_verified = models.BooleanField(default=False, verbose_name="是否验证")
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_api_keys'
        verbose_name = '用户 API Key'
        verbose_name_plural = '用户 API Keys'

    def __str__(self):
        return f"{self.name} ({self.provider})"


class CustomModel(models.Model):
    """用户自定义的模型"""
    AUTH_TYPE_CHOICES = [
        ('platform', '平台付费'),
        ('user_provided', '用户付费'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_models')
    name = models.CharField(max_length=200, verbose_name="模型名称")
    model_id = models.CharField(max_length=100, verbose_name="模型ID")
    provider = models.CharField(max_length=50, verbose_name="提供商")
    endpoint = models.URLField(verbose_name="API 端点")
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default='user_provided')
    api_key = models.ForeignKey(UserAPIKey, on_delete=models.SET_NULL, null=True, verbose_name="关联的API Key")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    config = models.JSONField(default=dict, verbose_name="模型配置")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'custom_models'
        verbose_name = '自定义模型'
        verbose_name_plural = '自定义模型'

    def __str__(self):
        return f"{self.name} ({self.provider})"
```

### 3.3 Provider 适配器设计

```python
# gateway/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator


class BaseProvider(ABC):
    """Provider 基类"""

    def __init__(self, api_key: str, endpoint: str = None, **config):
        self.api_key = api_key
        self.endpoint = endpoint
        self.config = config

    @abstractmethod
    def chat_completions(self, messages: list, **kwargs) -> Dict[str, Any]:
        """发送聊天请求"""
        pass

    @abstractmethod
    def chat_completions_stream(self, messages: list, **kwargs) -> Iterator[str]:
        """流式聊天请求"""
        pass

    @abstractmethod
    def verify_connection(self) -> bool:
        """验证连接是否正常"""
        pass
```

```python
# gateway/providers/openai_provider.py

import openai
from .base import BaseProvider
from typing import Dict, Any, Iterator


class OpenAIProvider(BaseProvider):
    """OpenAI Provider"""

    def __init__(self, api_key: str, endpoint: str = None, **config):
        super().__init__(api_key, endpoint, **config)

        if endpoint:
            self.client = openai.OpenAI(api_key=api_key, base_url=endpoint)
        else:
            self.client = openai.OpenAI(api_key=api_key)

    def chat_completions(self, messages: list, model: str = "gpt-4o", **kwargs) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.model_dump()

    def chat_completions_stream(self, messages: list, model: str = "gpt-4o", **kwargs) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def verify_connection(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
```

```python
# gateway/providers/anthropic_provider.py

import anthropic
from .base import BaseProvider
from typing import Dict, Any, Iterator


class AnthropicProvider(BaseProvider):
    """Anthropic Provider"""

    def __init__(self, api_key: str, endpoint: str = None, **config):
        super().__init__(api_key, endpoint, **config)
        self.client = anthropic.Anthropic(api_key=api_key)

    def chat_completions(self, messages: list, model: str = "claude-3-5-sonnet-20241022", **kwargs) -> Dict[str, Any]:
        # 转换消息格式
        system = ""
        converted_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                system = msg['content']
            else:
                converted_messages.append(msg)

        response = self.client.messages.create(
            model=model,
            system=system,
            messages=converted_messages,
            **kwargs
        )
        return {
            'id': response.id,
            'model': model,
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': response.content[0].text
                }
            }]
        }

    def chat_completions_stream(self, messages: list, model: str = "claude-3-5-sonnet-20241022", **kwargs) -> Iterator[str]:
        # 类似实现
        pass

    def verify_connection(self) -> bool:
        try:
            self.client.messages.list(limit=1)
            return True
        except Exception:
            return False
```

```python
# gateway/providers/registry.py

from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from typing import Dict, Optional


class ProviderRegistry:
    """Provider 注册表"""

    _providers: Dict[str, type] = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        # 可以继续添加其他 provider
    }

    @classmethod
    def register(cls, name: str, provider_class):
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, name: str, **kwargs):
        provider_class = cls._providers.get(name.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {name}")
        return provider_class(**kwargs)
```

### 3.4 模型路由器

```python
# gateway/services/model_router.py

from typing import Dict, Any, Optional
from ..models import PlatformModel, CustomModel, UserAPIKey


class ModelRouter:
    """模型路由器"""

    def __init__(self, user=None):
        self.user = user

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        # 1. 先查平台模型
        try:
            platform_model = PlatformModel.objects.get(model_id=model_id, is_active=True)
            return {
                'model_id': platform_model.model_id,
                'provider': platform_model.provider,
                'endpoint': platform_model.endpoint,
                'api_key': platform_model.api_key,
                'config': platform_model.config,
                'auth_type': 'platform',
            }
        except PlatformModel.DoesNotExist:
            pass

        # 2. 查用户自定义模型
        if self.user:
            try:
                custom_model = CustomModel.objects.get(
                    user=self.user,
                    model_id=model_id,
                    is_active=True
                )
                api_key = custom_model.api_key.api_key if custom_model.api_key else None
                return {
                    'model_id': custom_model.model_id,
                    'provider': custom_model.provider,
                    'endpoint': custom_model.endpoint,
                    'api_key': api_key,
                    'config': custom_model.config,
                    'auth_type': 'user_provided',
                }
            except CustomModel.DoesNotExist:
                pass

        return None

    def route(self, model_id: str, messages: list, **kwargs) -> Dict[str, Any]:
        """路由请求到对应 provider"""
        model_info = self.get_model_info(model_id)
        if not model_info:
            raise ValueError(f"Model not found: {model_id}")

        from ..providers.registry import ProviderRegistry

        provider = ProviderRegistry.get_provider(
            model_info['provider'],
            api_key=model_info['api_key'],
            endpoint=model_info.get('endpoint')
        )

        return provider.chat_completions(
            messages=messages,
            model=model_info['model_id'],
            **{**model_info.get('config', {}), **kwargs}
        )
```

### 3.5 统一 API 端点

```python
# gateway/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.model_router import ModelRouter


class ChatCompletionsView(APIView):
    """统一的 Chat Completions API"""

    def post(self, request):
        model_id = request.data.get('model')
        messages = request.data.get('messages', [])

        if not model_id or not messages:
            return Response(
                {'error': 'model and messages are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            router = ModelRouter(user=request.user)
            result = router.route(model_id, messages, **request.data)
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Internal error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

### 3.6 管理员后台功能

| 功能 | 说明 |
|------|------|
| 模型管理 | 添加/编辑/禁用平台模型，设置默认模型 |
| 用户模型审核 | 查看/批准/拒绝用户添加的自定义模型 |
| API Keys 管理 | 管理平台侧 API Keys，支持多 provider |
| 使用统计 | 各模型调用量、token 消耗 |
| 用户管理 | 冻结用户、查看用户 keys |

**admin.py 示例**：

```python
# gateway/admin.py

from django.contrib import admin
from .models import PlatformModel, UserAPIKey, CustomModel


@admin.register(PlatformModel)
class PlatformModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_id', 'provider', 'is_active', 'is_default', 'created_at')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'model_id')


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'provider', 'is_verified', 'last_used', 'created_at')
    list_filter = ('provider', 'is_verified')
    search_fields = ('name', 'user__username')


@admin.register(CustomModel)
class CustomModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'model_id', 'provider', 'auth_type', 'is_active', 'created_at')
    list_filter = ('provider', 'auth_type', 'is_active')
    search_fields = ('name', 'model_id', 'user__username')
```

---

## Step 4 - Django 模型设计

### 4.1 定义工作流模型

编辑 `Backend/workflow/models.py`：

```python
from django.db import models
from django.contrib.auth.models import User


class Workflow(models.Model):
    """工作流模型"""
    name = models.CharField(max_length=200, verbose_name="工作流名称")
    description = models.TextField(blank=True, verbose_name="描述")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflows')
    is_published = models.BooleanField(default=False, verbose_name="是否发布")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflows'
        verbose_name = '工作流'
        verbose_name_plural = '工作流'

    def __str__(self):
        return self.name


class Node(models.Model):
    """工作流节点"""
    NODE_TYPES = [
        ('start', '开始'),
        ('end', '结束'),
        ('llm', '大语言模型'),
        ('prompt', '提示词'),
        ('tool', '工具'),
        ('condition', '条件判断'),
        ('input', '输入'),
        ('output', '输出'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='nodes')
    node_type = models.CharField(max_length=50, choices=NODE_TYPES, verbose_name="节点类型")
    name = models.CharField(max_length=200, verbose_name="节点名称")
    config = models.JSONField(default=dict, verbose_name="节点配置")
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nodes'
        verbose_name = '节点'
        verbose_name_plural = '节点'

    def __str__(self):
        return f"{self.name} ({self.node_type})"


class Edge(models.Model):
    """工作流连接线"""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='edges')
    source_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='outgoing_edges')
    target_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='incoming_edges')
    label = models.CharField(max_length=100, blank=True, verbose_name="标签")

    class Meta:
        db_table = 'edges'
        verbose_name = '连接'
        verbose_name_plural = '连接'

    def __str__(self):
        return f"{self.source_node.name} -> {self.target_node.name}"


class WorkflowExecution(models.Model):
    """工作流执行记录"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_executions'
        verbose_name = '执行记录'
        verbose_name_plural = '执行记录'
```

### 4.2 完整数据库设计

#### 4.2.1 数据库设计概述

本系统采用 **MySQL 8.0** 作为主数据库，设计遵循以下原则：

| 设计原则 | 说明 |
|---------|------|
| **规范化** | 遵循第三范式 (3NF)，减少数据冗余 |
| **扩展性** | 使用 JSONField 存储灵活配置，便于功能扩展 |
| **性能优化** | 合理设计索引，平衡查询效率与写入性能 |
| **审计追溯** | 记录创建时间、更新时间、关联关系 |

#### 4.2.2 ER 实体关系图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FLOWLY 数据库 ER 图                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │    Tenant    │         │     User     │         │    User     │
    │   (租户)     │1       N│   (用户)      │N        │ Profile     │
    └──────┬───────┘─────────┴──────┬───────┘         │ (用户扩展)   │
           │                        │                 └──────────────┘
           │                        │
           │ N                       │ N
           ▼                        ▼
    ┌─────────────────────────────────────────────────────┐
    │                  Workflow (工作流)                   │
    │  ┌─────────────────────────────────────────────────┐ │
    │  │ id, name, description, version, status, config  │ │
    │  │ tenant_id, owner_id, is_published, tags        │ │
    │  └─────────────────────────────────────────────────┘ │
    └───────────────────────┬─────────────────────────────────┘
                            │
                            │ 1:N
                            ▼
    ┌───────────────────────────────────────────────────────┐
    │                     Node (节点)                        │
    │  ┌───────────────────────────────────────────────────┐ │
    │  │ id, workflow_id, node_type, name, config         │ │
    │  │ position_x, position_y, input_schema             │ │
    │  │ output_schema, error_handling                   │ │
    │  └───────────────────────────────────────────────────┘ │
    └───────────────────────┬───────────────────────────────────┘
                            │
                            │ 1:N
                            ▼
    ┌───────────────────────────────────────────────────────┐
    │                  NodeExecution (节点执行)              │
    │  ┌───────────────────────────────────────────────────┐ │
    │  │ id, execution_id, node_id, status, input_data    │ │
    │  │ output_data, error_message, started_at          │ │
    │  │ completed_at, retry_count                       │ │
    │  └───────────────────────────────────────────────────┘ │
    └───────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────┐
    │     Edge     │         │    Prompt    │
    │   (连线)      │         │   (模板)     │
    └──────┬───────┘         └──────────────┘
           │
           │ N
           ▼
    ┌──────────────┐         ┌──────────────┐
    │  Execution   │         │    Tool      │
    │  (执行记录)  │         │   (工具)     │
    └──────┬───────┘         └──────────────┘
           │
           │ N
           ▼
    ┌──────────────┐         ┌──────────────┐
    │   LogEntry   │         │  APICreden-  │
    │  (执行日志)  │         │   tial       │
    └──────────────┘         │  (凭证)      │
                            └──────────────┘
```

#### 4.2.3 完整数据表设计

##### 4.2.3.1 租户表 (tenants)

```sql
CREATE TABLE `tenants` (
    `id` CHAR(36) NOT NULL COMMENT '租户ID (UUID)',
    `name` VARCHAR(200) NOT NULL COMMENT '租户名称',
    `slug` VARCHAR(100) NOT NULL UNIQUE COMMENT '租户标识 (URL友好)',
    `plan` ENUM('free', 'pro', 'enterprise') NOT NULL DEFAULT 'free' COMMENT '订阅计划',
    `max_workflows` INT NOT NULL DEFAULT 10 COMMENT '最大工作流数量',
    `max_users` INT NOT NULL DEFAULT 5 COMMENT '最大用户数量',
    `max_executions_per_month` INT DEFAULT NULL COMMENT '每月最大执行次数 (NULL=无限)',
    `current_executions` INT NOT NULL DEFAULT 0 COMMENT '当月当前执行次数',
    `settings` JSON DEFAULT NULL COMMENT '租户配置 (logo, 主题等)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活',
    `trial_ends_at` DATETIME DEFAULT NULL COMMENT '试用结束时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tenants_slug` (`slug`),
    KEY `idx_tenants_is_active` (`is_active`),
    KEY `idx_tenants_plan` (`plan`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='租户表 - 支持多租户隔离';
```

##### 4.2.3.2 用户表 (users)

> 注：使用 Django 自带的 auth_user 表，这里展示扩展表

```sql
CREATE TABLE `user_profiles` (
    `id` CHAR(36) NOT NULL COMMENT '主键ID',
    `user_id` INT NOT NULL UNIQUE COMMENT '关联Django用户ID',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户',
    `display_name` VARCHAR(100) DEFAULT NULL COMMENT '显示名称',
    `avatar_url` VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    `timezone` VARCHAR(50) DEFAULT 'Asia/Shanghai' COMMENT '时区',
    `language` VARCHAR(10) DEFAULT 'zh-hans' COMMENT '语言',
    `preferences` JSON DEFAULT NULL COMMENT '用户偏好设置',
    `role` ENUM('owner', 'admin', 'member', 'viewer') NOT NULL DEFAULT 'member' COMMENT '角色',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `last_login_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_profiles_user_id` (`user_id`),
    KEY `idx_user_profiles_tenant_id` (`tenant_id`),
    KEY `idx_user_profiles_role` (`role`),
    CONSTRAINT `fk_user_profiles_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户扩展信息表';

-- 使用 Django 自带的 auth_user 表
-- 扩展字段可通过 OneToOneField 关联 user_profiles 表
```

##### 4.2.3.3 工作流表 (workflows)

```sql
CREATE TABLE `workflows` (
    `id` CHAR(36) NOT NULL COMMENT '工作流ID (UUID)',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户',
    `owner_id` INT NOT NULL COMMENT '创建者用户ID',
    `name` VARCHAR(200) NOT NULL COMMENT '工作流名称',
    `description` TEXT DEFAULT NULL COMMENT '工作流描述',
    `version` INT NOT NULL DEFAULT 1 COMMENT '版本号',
    `status` ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft' 
        COMMENT '状态: 草稿/已发布/已归档',
    `category` VARCHAR(100) DEFAULT NULL COMMENT '分类',
    `tags` JSON DEFAULT NULL COMMENT '标签列表 ["tag1", "tag2"]',
    `config` JSON DEFAULT NULL COMMENT '全局配置 (超时、并发等)',
    
    -- 执行统计
    `total_executions` INT NOT NULL DEFAULT 0 COMMENT '总执行次数',
    `successful_executions` INT NOT NULL DEFAULT 0 COMMENT '成功次数',
    `failed_executions` INT NOT NULL DEFAULT 0 COMMENT '失败次数',
    `avg_execution_time_ms` INT DEFAULT NULL COMMENT '平均执行时间(毫秒)',
    `last_executed_at` DATETIME DEFAULT NULL COMMENT '最后执行时间',
    
    -- 权限控制
    `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开',
    `share_token` VARCHAR(64) DEFAULT NULL COMMENT '分享令牌',
    
    -- 版本控制
    `parent_version_id` CHAR(36) DEFAULT NULL COMMENT '父版本ID',
    `change_summary` TEXT DEFAULT NULL COMMENT '变更说明',
    
    -- 软删除
    `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
    `deleted_at` DATETIME DEFAULT NULL,
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_workflows_share_token` (`share_token`),
    KEY `idx_workflows_tenant_id` (`tenant_id`),
    KEY `idx_workflows_owner_id` (`owner_id`),
    KEY `idx_workflows_status` (`status`),
    KEY `idx_workflows_category` (`category`),
    KEY `idx_workflows_is_deleted` (`is_deleted`),
    KEY `idx_workflows_created_at` (`created_at`),
    KEY `idx_workflows_name` (`name`(100)),
    
    CONSTRAINT `fk_workflows_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工作流表 - 核心业务表';
```

##### 4.2.3.4 节点表 (nodes)

```sql
CREATE TABLE `nodes` (
    `id` CHAR(36) NOT NULL COMMENT '节点ID (UUID)',
    `workflow_id` CHAR(36) NOT NULL COMMENT '所属工作流ID',
    `parent_node_id` CHAR(36) DEFAULT NULL COMMENT '父节点ID (用于子流程)',
    
    `node_type` VARCHAR(50) NOT NULL COMMENT '节点类型',
    `name` VARCHAR(200) NOT NULL COMMENT '节点名称',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '节点描述',
    
    -- 位置信息 (画布坐标)
    `position_x` DECIMAL(10, 2) NOT NULL DEFAULT 0 COMMENT 'X坐标',
    `position_y` DECIMAL(10, 2) NOT NULL DEFAULT 0 COMMENT 'Y坐标',
    `width` DECIMAL(10, 2) DEFAULT NULL COMMENT '节点宽度',
    `height` DECIMAL(10, 2) DEFAULT NULL COMMENT '节点高度',
    
    -- 节点配置 (JSON存储不同类型节点的特殊配置)
    `config` JSON DEFAULT NULL COMMENT '节点配置参数',
    
    -- 输入输出定义 (JSON Schema 格式)
    `input_schema` JSON DEFAULT NULL COMMENT '输入数据模式',
    `output_schema` JSON DEFAULT NULL COMMENT '输出数据模式',
    
    -- 错误处理配置
    `error_handling` ENUM('stop', 'skip', 'retry', 'fallback') 
        NOT NULL DEFAULT 'stop' COMMENT '错误处理策略',
    `max_retries` INT NOT NULL DEFAULT 3 COMMENT '最大重试次数',
    `retry_delay_seconds` INT NOT NULL DEFAULT 5 COMMENT '重试延迟(秒)',
    
    -- 条件配置 (用于条件分支节点)
    `condition_expression` TEXT DEFAULT NULL COMMENT '条件表达式',
    
    -- 执行控制
    `is_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `timeout_seconds` INT DEFAULT NULL COMMENT '超时时间(秒)',
    
    -- 版本控制
    `version` INT NOT NULL DEFAULT 1 COMMENT '版本号',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_nodes_workflow_id` (`workflow_id`),
    KEY `idx_nodes_parent_node_id` (`parent_node_id`),
    KEY `idx_nodes_node_type` (`node_type`),
    KEY `idx_nodes_is_enabled` (`is_enabled`),
    
    CONSTRAINT `fk_nodes_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_nodes_parent` FOREIGN KEY (`parent_node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工作流节点表';

-- 节点类型枚举
-- start, end, llm, prompt, tool, condition, input, output
-- code, loop,http_request, data_transform, email, webhook
```

##### 4.2.3.5 连线表 (edges)

```sql
CREATE TABLE `edges` (
    `id` CHAR(36) NOT NULL COMMENT '连线ID (UUID)',
    `workflow_id` CHAR(36) NOT NULL COMMENT '所属工作流ID',
    
    `source_node_id` CHAR(36) NOT NULL COMMENT '源节点ID',
    `source_handle` VARCHAR(50) DEFAULT 'default' COMMENT '源节点出口',
    
    `target_node_id` CHAR(36) NOT NULL COMMENT '目标节点ID',
    `target_handle` VARCHAR(50) DEFAULT 'default' COMMENT '目标节点入口',
    
    `label` VARCHAR(200) DEFAULT NULL COMMENT '连线标签',
    `style` JSON DEFAULT NULL COMMENT '连线样式配置',
    
    -- 条件边 (用于条件分支)
    `condition_expression` TEXT DEFAULT NULL COMMENT '条件表达式',
    `condition_priority` INT NOT NULL DEFAULT 0 COMMENT '条件优先级',
    
    -- 动画配置
    `animated` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否显示动画',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_edges_connection` (`source_node_id`, `source_handle`, `target_node_id`, `target_handle`),
    KEY `idx_edges_workflow_id` (`workflow_id`),
    KEY `idx_edges_source_node_id` (`source_node_id`),
    KEY `idx_edges_target_node_id` (`target_node_id`),
    
    CONSTRAINT `fk_edges_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_edges_source_node` FOREIGN KEY (`source_node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_edges_target_node` FOREIGN KEY (`target_node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工作流连线表 - 定义节点之间的连接关系';
```

##### 4.2.3.6 执行记录表 (workflow_executions)

```sql
CREATE TABLE `workflow_executions` (
    `id` CHAR(36) NOT NULL COMMENT '执行ID (UUID)',
    `workflow_id` CHAR(36) NOT NULL COMMENT '工作流ID',
    `version` INT NOT NULL COMMENT '执行时的工作流版本',
    
    `trigger_type` ENUM('manual', 'scheduled', 'webhook', 'api', 'event') 
        NOT NULL DEFAULT 'manual' COMMENT '触发类型',
    `trigger_config` JSON DEFAULT NULL COMMENT '触发器配置',
    
    `status` ENUM('queued', 'running', 'completed', 'failed', 'cancelled', 'timeout') 
        NOT NULL DEFAULT 'queued' COMMENT '执行状态',
    
    -- 输入输出数据
    `input_data` JSON DEFAULT NULL COMMENT '输入数据',
    `output_data` JSON DEFAULT NULL COMMENT '输出数据',
    
    -- 执行统计
    `total_nodes` INT DEFAULT NULL COMMENT '总节点数',
    `executed_nodes` INT DEFAULT NULL COMMENT '已执行节点数',
    `skipped_nodes` INT DEFAULT NULL COMMENT '跳过节点数',
    `failed_nodes` INT DEFAULT NULL COMMENT '失败节点数',
    
    -- 时间统计
    `queued_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入队列时间',
    `started_at` DATETIME DEFAULT NULL COMMENT '开始执行时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    `duration_ms` INT DEFAULT NULL COMMENT '执行耗时(毫秒)',
    
    -- 错误信息
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `error_stack` TEXT DEFAULT NULL COMMENT '错误堆栈',
    
    -- 资源使用
    `token_usage` JSON DEFAULT NULL COMMENT 'Token使用量统计',
    `cost_amount` DECIMAL(10, 4) DEFAULT NULL COMMENT '执行成本',
    `cost_currency` VARCHAR(10) DEFAULT 'USD' COMMENT '货币类型',
    
    -- 用户信息
    `user_id` INT DEFAULT NULL COMMENT '触发用户ID',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户',
    
    -- 上下文数据
    `context_data` JSON DEFAULT NULL COMMENT '执行上下文 (变量值等)',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_executions_workflow_id` (`workflow_id`),
    KEY `idx_executions_status` (`status`),
    KEY `idx_executions_trigger_type` (`trigger_type`),
    KEY `idx_executions_user_id` (`user_id`),
    KEY `idx_executions_tenant_id` (`tenant_id`),
    KEY `idx_executions_started_at` (`started_at`),
    KEY `idx_executions_queued_at` (`queued_at`),
    KEY `idx_executions_duration` (`duration_ms`),
    
    CONSTRAINT `fk_executions_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工作流执行记录表';
```

##### 4.2.3.7 节点执行记录表 (node_executions)

```sql
CREATE TABLE `node_executions` (
    `id` CHAR(36) NOT NULL COMMENT '节点执行ID (UUID)',
    `execution_id` CHAR(36) NOT NULL COMMENT '所属执行记录ID',
    `node_id` CHAR(36) NOT NULL COMMENT '节点ID',
    `node_version` INT NOT NULL COMMENT '节点版本',
    
    `status` ENUM('pending', 'running', 'completed', 'failed', 'skipped') 
        NOT NULL DEFAULT 'pending' COMMENT '执行状态',
    
    -- 输入输出
    `input_data` JSON DEFAULT NULL COMMENT '输入数据',
    `output_data` JSON DEFAULT NULL COMMENT '输出数据',
    
    -- 执行信息
    `started_at` DATETIME DEFAULT NULL COMMENT '开始时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    `duration_ms` INT DEFAULT NULL COMMENT '执行耗时(毫秒)',
    
    -- 错误处理
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `retry_count` INT NOT NULL DEFAULT 0 COMMENT '重试次数',
    `max_retries_exceeded` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否超过最大重试',
    
    -- 模型调用信息 (用于 LLM 节点)
    `model_name` VARCHAR(100) DEFAULT NULL COMMENT '使用的模型名称',
    `prompt_tokens` INT DEFAULT NULL COMMENT '输入Token数',
    `completion_tokens` INT DEFAULT NULL COMMENT '输出Token数',
    `total_tokens` INT DEFAULT NULL COMMENT '总Token数',
    `model_latency_ms` INT DEFAULT NULL COMMENT '模型响应延迟',
    
    -- 缓存信息
    `cache_hit` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否命中缓存',
    `cache_key` VARCHAR(100) DEFAULT NULL COMMENT '缓存键',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_node_executions_execution_id` (`execution_id`),
    KEY `idx_node_executions_node_id` (`node_id`),
    KEY `idx_node_executions_status` (`status`),
    KEY `idx_node_executions_cache_hit` (`cache_hit`),
    KEY `idx_node_executions_started_at` (`started_at`),
    
    CONSTRAINT `fk_node_executions_execution` FOREIGN KEY (`execution_id`) 
        REFERENCES `workflow_executions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_node_executions_node` FOREIGN KEY (`node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='节点执行记录表';
```

##### 4.2.3.8 执行日志表 (execution_logs)

```sql
CREATE TABLE `execution_logs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
    `execution_id` CHAR(36) NOT NULL COMMENT '执行记录ID',
    `node_execution_id` CHAR(36) DEFAULT NULL COMMENT '节点执行ID',
    
    `log_level` ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR') 
        NOT NULL DEFAULT 'INFO' COMMENT '日志级别',
    `message` TEXT NOT NULL COMMENT '日志消息',
    `metadata` JSON DEFAULT NULL COMMENT '元数据',
    
    -- 日志来源
    `source` VARCHAR(50) DEFAULT NULL COMMENT '日志来源 (node, system, ai)',
    `node_id` CHAR(36) DEFAULT NULL COMMENT '相关节点ID',
    `node_name` VARCHAR(200) DEFAULT NULL COMMENT '相关节点名称',
    
    -- 时间戳
    `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '日志时间',
    
    PRIMARY KEY (`id`),
    KEY `idx_logs_execution_id` (`execution_id`),
    KEY `idx_logs_node_execution_id` (`node_execution_id`),
    KEY `idx_logs_log_level` (`log_level`),
    KEY `idx_logs_timestamp` (`timestamp`),
    KEY `idx_logs_node_id` (`node_id`),
    
    CONSTRAINT `fk_logs_execution` FOREIGN KEY (`execution_id`) 
        REFERENCES `workflow_executions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='执行日志表 - 存储详细执行日志';
```

##### 4.2.3.9 Prompt 模板表 (prompt_templates)

```sql
CREATE TABLE `prompt_templates` (
    `id` CHAR(36) NOT NULL COMMENT '模板ID (UUID)',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户 (NULL为全局模板)',
    
    `name` VARCHAR(200) NOT NULL COMMENT '模板名称',
    `description` TEXT DEFAULT NULL COMMENT '模板描述',
    `category` VARCHAR(100) DEFAULT NULL COMMENT '分类',
    `tags` JSON DEFAULT NULL COMMENT '标签',
    
    -- 模板内容
    `template` TEXT NOT NULL COMMENT 'Prompt 模板内容',
    `input_variables` JSON NOT NULL COMMENT '输入变量列表',
    `output_format` ENUM('text', 'json', 'markdown', 'xml') 
        DEFAULT 'text' COMMENT '输出格式',
    
    -- 版本控制
    `version` INT NOT NULL DEFAULT 1 COMMENT '版本号',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    
    -- 使用统计
    `usage_count` INT NOT NULL DEFAULT 0 COMMENT '使用次数',
    `success_rate` DECIMAL(5, 2) DEFAULT NULL COMMENT '成功率',
    `avg_rating` DECIMAL(3, 2) DEFAULT NULL COMMENT '平均评分',
    `rating_count` INT NOT NULL DEFAULT 0 COMMENT '评分次数',
    
    -- 系统字段
    `created_by_id` INT DEFAULT NULL COMMENT '创建者ID',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_prompt_templates_tenant_id` (`tenant_id`),
    KEY `idx_prompt_templates_category` (`category`),
    KEY `idx_prompt_templates_is_active` (`is_active`),
    KEY `idx_prompt_templates_name` (`name`(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Prompt 模板表';
```

##### 4.2.3.10 工具定义表 (tools)

```sql
CREATE TABLE `tools` (
    `id` CHAR(36) NOT NULL COMMENT '工具ID (UUID)',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户',
    
    `name` VARCHAR(100) NOT NULL COMMENT '工具名称',
    `display_name` VARCHAR(200) DEFAULT NULL COMMENT '显示名称',
    `description` TEXT DEFAULT NULL COMMENT '工具描述',
    `category` VARCHAR(100) DEFAULT NULL COMMENT '工具分类',
    
    -- 工具类型
    `tool_type` ENUM('builtin', 'custom', 'api', 'script') 
        NOT NULL DEFAULT 'custom' COMMENT '工具类型',
    
    -- 工具定义 (JSON Schema)
    `definition` JSON NOT NULL COMMENT '工具定义 (参数、返回值等)',
    `input_schema` JSON DEFAULT NULL COMMENT '输入参数模式',
    `output_schema` JSON DEFAULT NULL COMMENT '输出结果模式',
    
    -- 认证配置
    `auth_type` ENUM('none', 'api_key', 'oauth2', 'basic', 'bearer') 
        DEFAULT 'none' COMMENT '认证类型',
    `credential_id` CHAR(36) DEFAULT NULL COMMENT '关联凭证ID',
    
    -- 执行配置
    `timeout_seconds` INT NOT NULL DEFAULT 30 COMMENT '超时时间',
    `retry_policy` JSON DEFAULT NULL COMMENT '重试策略',
    `rate_limit` JSON DEFAULT NULL COMMENT '速率限制',
    
    -- 状态
    `is_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `is_public` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开',
    
    -- 使用统计
    `usage_count` INT NOT NULL DEFAULT 0 COMMENT '使用次数',
    `avg_execution_time_ms` INT DEFAULT NULL COMMENT '平均执行时间',
    `success_rate` DECIMAL(5, 2) DEFAULT NULL COMMENT '成功率',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_tools_tenant_id` (`tenant_id`),
    KEY `idx_tools_tool_type` (`tool_type`),
    KEY `idx_tools_category` (`category`),
    KEY `idx_tools_is_enabled` (`is_enabled`),
    KEY `idx_tools_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工具定义表 - 存储可调用工具的配置';
```

##### 4.2.3.11 API 凭证表 (api_credentials)

```sql
CREATE TABLE `api_credentials` (
    `id` CHAR(36) NOT NULL COMMENT '凭证ID (UUID)',
    `tenant_id` CHAR(36) NOT NULL COMMENT '所属租户',
    `user_id` INT DEFAULT NULL COMMENT '创建者用户ID',
    
    `name` VARCHAR(200) NOT NULL COMMENT '凭证名称',
    `description` TEXT DEFAULT NULL COMMENT '凭证描述',
    
    -- 凭证类型
    `credential_type` ENUM('api_key', 'oauth2', 'basic', 'bearer', 'aws', 'azure') 
        NOT NULL COMMENT '凭证类型',
    
    -- 凭证数据 (加密存储)
    `credential_data` TEXT NOT NULL COMMENT '凭证数据 (加密后)',
    `credential_data_hash` VARCHAR(64) DEFAULT NULL COMMENT '凭证数据哈希 (用于校验)',
    
    -- 关联服务
    `service_type` VARCHAR(50) DEFAULT NULL COMMENT '关联服务类型 (openai, anthropic等)',
    `service_config` JSON DEFAULT NULL COMMENT '服务配置',
    
    -- 权限范围
    `scope` JSON DEFAULT NULL COMMENT 'OAuth 权限范围',
    
    -- 状态
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `expires_at` DATETIME DEFAULT NULL COMMENT '过期时间',
    `last_used_at` DATETIME DEFAULT NULL COMMENT '最后使用时间',
    `usage_count` INT NOT NULL DEFAULT 0 COMMENT '使用次数',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_api_credentials_tenant_id` (`tenant_id`),
    KEY `idx_api_credentials_user_id` (`user_id`),
    KEY `idx_api_credentials_credential_type` (`credential_type`),
    KEY `idx_api_credentials_service_type` (`service_type`),
    KEY `idx_api_credentials_is_active` (`is_active`),
    
    CONSTRAINT `fk_api_credentials_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='API 凭证表 - 安全存储第三方服务凭证';
```

##### 4.2.3.12 变量表 (variables)

```sql
CREATE TABLE `variables` (
    `id` CHAR(36) NOT NULL COMMENT '变量ID (UUID)',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户',
    `workflow_id` CHAR(36) DEFAULT NULL COMMENT '关联工作流 (NULL为全局)',
    
    `name` VARCHAR(100) NOT NULL COMMENT '变量名称',
    `display_name` VARCHAR(200) DEFAULT NULL COMMENT '显示名称',
    `description` TEXT DEFAULT NULL COMMENT '变量描述',
    
    -- 变量定义
    `var_type` ENUM('string', 'number', 'boolean', 'json', 'array', 'secret') 
        NOT NULL DEFAULT 'string' COMMENT '变量类型',
    `default_value` TEXT DEFAULT NULL COMMENT '默认值',
    `validation_rules` JSON DEFAULT NULL COMMENT '验证规则',
    
    -- 来源
    `source` ENUM('user_input', 'system', 'workflow', 'execution', 'secret') 
        NOT NULL DEFAULT 'user_input' COMMENT '变量来源',
    `secret_path` VARCHAR(500) DEFAULT NULL COMMENT '密钥路径 (用于secret类型)',
    
    -- 权限
    `is_required` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否必填',
    `is_sensitive` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否敏感',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_variables_tenant_id` (`tenant_id`),
    KEY `idx_variables_workflow_id` (`workflow_id`),
    KEY `idx_variables_var_type` (`var_type`),
    KEY `idx_variables_source` (`source`),
    KEY `idx_variables_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='变量定义表 - 管理工作流变量';
```

##### 4.2.3.13 知识库表 (knowledge_bases)

```sql
CREATE TABLE `knowledge_bases` (
    `id` CHAR(36) NOT NULL COMMENT '知识库ID (UUID)',
    `tenant_id` CHAR(36) NOT NULL COMMENT '所属租户',
    
    `name` VARCHAR(200) NOT NULL COMMENT '知识库名称',
    `description` TEXT DEFAULT NULL COMMENT '知识库描述',
    `embeddings_provider` VARCHAR(50) DEFAULT 'openai' COMMENT '嵌入模型提供商',
    `embeddings_model` VARCHAR(100) DEFAULT NULL COMMENT '嵌入模型名称',
    
    -- 向量存储配置
    `vector_store_type` ENUM('qdrant', 'milvus', 'chroma', 'pgvector', 'pinecone') 
        NOT NULL DEFAULT 'qdrant' COMMENT '向量存储类型',
    `vector_store_config` JSON DEFAULT NULL COMMENT '向量存储配置',
    
    -- 索引配置
    `chunk_size` INT NOT NULL DEFAULT 500 COMMENT '分块大小',
    `chunk_overlap` INT NOT NULL DEFAULT 50 COMMENT '分块重叠',
    `embedding_dimension` INT NOT NULL DEFAULT 1536 COMMENT '向量维度',
    
    -- 检索配置
    `retrieval_config` JSON DEFAULT NULL COMMENT '检索配置',
    
    -- 统计
    `document_count` INT NOT NULL DEFAULT 0 COMMENT '文档数量',
    `chunk_count` INT NOT NULL DEFAULT 0 COMMENT '切片数量',
    
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_knowledge_bases_tenant_id` (`tenant_id`),
    KEY `idx_knowledge_bases_vector_store_type` (`vector_store_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='知识库配置表';

CREATE TABLE `knowledge_documents` (
    `id` CHAR(36) NOT NULL COMMENT '文档ID (UUID)',
    `knowledge_base_id` CHAR(36) NOT NULL COMMENT '所属知识库ID',
    
    `title` VARCHAR(500) NOT NULL COMMENT '文档标题',
    `source_type` ENUM('upload', 'url', 'api', 'sync') NOT NULL DEFAULT 'upload' COMMENT '来源类型',
    `source_url` VARCHAR(2000) DEFAULT NULL COMMENT '来源URL',
    `source_path` VARCHAR(500) DEFAULT NULL COMMENT '存储路径',
    
    `content_hash` VARCHAR(64) DEFAULT NULL COMMENT '内容哈希',
    `metadata` JSON DEFAULT NULL COMMENT '文档元数据',
    
    `status` ENUM('pending', 'processing', 'indexed', 'failed') 
        NOT NULL DEFAULT 'pending' COMMENT '处理状态',
    `chunk_count` INT DEFAULT NULL COMMENT '切片数量',
    `token_count` INT DEFAULT NULL COMMENT 'Token数量',
    
    `last_sync_at` DATETIME DEFAULT NULL COMMENT '最后同步时间',
    `indexed_at` DATETIME DEFAULT NULL COMMENT '索引时间',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_knowledge_documents_knowledge_base_id` (`knowledge_base_id`),
    KEY `idx_knowledge_documents_status` (`status`),
    KEY `idx_knowledge_documents_source_type` (`source_type`),
    
    CONSTRAINT `fk_knowledge_documents_knowledge_base` FOREIGN KEY (`knowledge_base_id`) 
        REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='知识库文档表';
```

##### 4.2.3.14 Webhook 表 (webhooks)

```sql
CREATE TABLE `webhooks` (
    `id` CHAR(36) NOT NULL COMMENT 'Webhook ID (UUID)',
    `tenant_id` CHAR(36) NOT NULL COMMENT '所属租户',
    `workflow_id` CHAR(36) NOT NULL COMMENT '关联工作流',
    
    `name` VARCHAR(200) NOT NULL COMMENT 'Webhook名称',
    `description` TEXT DEFAULT NULL COMMENT '描述',
    
    -- 认证配置
    `auth_type` ENUM('none', 'api_key', 'basic', 'bearer', 'hmac') 
        DEFAULT 'none' COMMENT '认证类型',
    `auth_config` JSON DEFAULT NULL COMMENT '认证配置',
    
    -- 触发配置
    `trigger_config` JSON DEFAULT NULL COMMENT '触发条件配置',
    `input_mapping` JSON DEFAULT NULL COMMENT '输入映射配置',
    
    -- 状态
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `secret_key` VARCHAR(64) DEFAULT NULL COMMENT '签名密钥',
    
    -- 统计
    `call_count` INT NOT NULL DEFAULT 0 COMMENT '调用次数',
    `last_called_at` DATETIME DEFAULT NULL COMMENT '最后调用时间',
    `last_status_code` INT DEFAULT NULL COMMENT '最后状态码',
    `failure_count` INT NOT NULL DEFAULT 0 COMMENT '失败次数',
    
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `idx_webhooks_tenant_id` (`tenant_id`),
    KEY `idx_webhooks_workflow_id` (`workflow_id`),
    KEY `idx_webhooks_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Webhook 配置表';
```

##### 4.2.3.15 审计日志表 (audit_logs)

```sql
CREATE TABLE `audit_logs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '审计日志ID',
    `tenant_id` CHAR(36) DEFAULT NULL COMMENT '所属租户',
    `user_id` INT DEFAULT NULL COMMENT '操作用户ID',
    
    `action` VARCHAR(100) NOT NULL COMMENT '操作类型',
    `resource_type` VARCHAR(50) NOT NULL COMMENT '资源类型',
    `resource_id` CHAR(36) DEFAULT NULL COMMENT '资源ID',
    
    `old_value` JSON DEFAULT NULL COMMENT '旧值',
    `new_value` JSON DEFAULT NULL COMMENT '新值',
    
    `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
    `user_agent` VARCHAR(500) DEFAULT NULL COMMENT 'User Agent',
    `request_id` VARCHAR(100) DEFAULT NULL COMMENT '请求ID',
    
    `status` ENUM('success', 'failure') NOT NULL DEFAULT 'success' COMMENT '操作状态',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    
    `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    
    PRIMARY KEY (`id`),
    KEY `idx_audit_logs_tenant_id` (`tenant_id`),
    KEY `idx_audit_logs_user_id` (`user_id`),
    KEY `idx_audit_logs_action` (`action`),
    KEY `idx_audit_logs_resource_type` (`resource_type`),
    KEY `idx_audit_logs_resource_id` (`resource_id`),
    KEY `idx_audit_logs_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='审计日志表 - 记录所有敏感操作';
```

#### 4.2.4 索引设计详解

| 表名 | 索引类型 | 索引名称 | 说明 |
|------|---------|---------|------|
| `workflows` | UNIQUE | `uk_workflows_share_token` | 确保分享令牌唯一 |
| `workflows` | NORMAL | `idx_workflows_tenant_id` | 租户隔离查询 |
| `workflows` | NORMAL | `idx_workflows_owner_id` | 所有者查询 |
| `workflows` | NORMAL | `idx_workflows_status` | 状态过滤 |
| `workflows` | NORMAL | `idx_workflows_name` | 名称搜索 (前缀) |
| `workflows` | NORMAL | `idx_workflows_created_at` | 时间排序 |
| `nodes` | NORMAL | `idx_nodes_workflow_id` | 工作流节点查询 |
| `edges` | UNIQUE | `uk_edges_connection` | 防止重复连接 |
| `edges` | NORMAL | `idx_edges_source_node_id` | 查找下游节点 |
| `edges` | NORMAL | `idx_edges_target_node_id` | 查找上游节点 |
| `workflow_executions` | NORMAL | `idx_executions_workflow_id` | 工作流执行历史 |
| `workflow_executions` | NORMAL | `idx_executions_status` | 状态查询 |
| `workflow_executions` | NORMAL | `idx_executions_started_at` | 时间范围查询 |
| `node_executions` | NORMAL | `idx_node_executions_execution_id` | 执行详情查询 |
| `node_executions` | NORMAL | `idx_node_executions_cache_hit` | 缓存命中率统计 |
| `execution_logs` | NORMAL | `idx_logs_execution_id` | 执行日志查询 |
| `execution_logs` | NORMAL | `idx_logs_timestamp` | 日志时间范围 |

#### 4.2.5 Django 模型完整代码

编辑 `Backend/workflows/models.py`：

```python
"""
Flowly 工作流平台 - 数据库模型
包含所有核心业务模型的定义
"""

import uuid
import hashlib
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Tenant(models.Model):
    """租户模型 - 支持多租户隔离"""
    
    PLAN_CHOICES = [
        ('free', '免费版'),
        ('pro', '专业版'),
        ('enterprise', '企业版'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="租户名称")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="租户标识")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free', 
                            verbose_name="订阅计划")
    
    max_workflows = models.IntegerField(default=10, verbose_name="最大工作流数")
    max_users = models.IntegerField(default=5, verbose_name="最大用户数")
    max_executions_per_month = models.IntegerField(null=True, blank=True, 
                                                   verbose_name="每月最大执行次数")
    current_executions = models.IntegerField(default=0, verbose_name="当月执行次数")
    
    settings = models.JSONField(null=True, blank=True, verbose_name="租户配置")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name="试用结束时间")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenants'
        verbose_name = '租户'
        verbose_name_plural = '租户'
    
    def __str__(self):
        return self.name
    
    def is_trial_expired(self):
        if self.trial_ends_at:
            return timezone.now() > self.trial_ends_at
        return False


class UserProfile(models.Model):
    """用户扩展信息"""
    
    ROLE_CHOICES = [
        ('owner', '所有者'),
        ('admin', '管理员'),
        ('member', '成员'),
        ('viewer', '查看者'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, 
                                related_name='members')
    
    display_name = models.CharField(max_length=100, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Shanghai')
    language = models.CharField(max_length=10, default='zh-hans')
    preferences = models.JSONField(null=True, blank=True)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = '用户扩展信息'
        verbose_name_plural = '用户扩展信息'
    
    def __str__(self):
        return f"{self.user.username}'s profile"


class Workflow(models.Model):
    """工作流模型"""
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True,
                               related_name='workflows')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflows')
    
    name = models.CharField(max_length=200, verbose_name="工作流名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    version = models.IntegerField(default=1, verbose_name="版本号")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    category = models.CharField(max_length=100, null=True, blank=True)
    tags = models.JSONField(null=True, blank=True, verbose_name="标签")
    config = models.JSONField(null=True, blank=True, verbose_name="配置")
    
    # 执行统计
    total_executions = models.IntegerField(default=0)
    successful_executions = models.IntegerField(default=0)
    failed_executions = models.IntegerField(default=0)
    avg_execution_time_ms = models.IntegerField(null=True, blank=True)
    last_executed_at = models.DateTimeField(null=True, blank=True)
    
    # 权限
    is_public = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, null=True, blank=True, unique=True)
    
    # 版本控制
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='versions')
    change_summary = models.TextField(null=True, blank=True)
    
    # 软删除
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows'
        verbose_name = '工作流'
        verbose_name_plural = '工作流'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['owner']),
            models.Index(fields=['status']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = hashlib.sha256(
                f"{self.id}{timezone.now()}".encode()
            ).hexdigest()[:32]
        super().save(*args, **kwargs)


class Node(models.Model):
    """工作流节点模型"""
    
    NODE_TYPE_CHOICES = [
        ('start', '开始'),
        ('end', '结束'),
        ('llm', '大语言模型'),
        ('prompt', '提示词'),
        ('tool', '工具调用'),
        ('condition', '条件判断'),
        ('input', '输入'),
        ('output', '输出'),
        ('code', '代码执行'),
        ('loop', '循环'),
        ('http_request', 'HTTP请求'),
        ('data_transform', '数据转换'),
        ('email', '邮件'),
        ('webhook', 'Webhook'),
        ('template', '模板'),
        ('variable', '变量'),
        ('rag', '知识检索'),
    ]
    
    ERROR_HANDLING_CHOICES = [
        ('stop', '停止执行'),
        ('skip', '跳过'),
        ('retry', '重试'),
        ('fallback', '备用方案'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, 
                                 related_name='nodes')
    parent_node = models.ForeignKey('self', on_delete=models.CASCADE, null=True,
                                    blank=True, related_name='child_nodes')
    
    node_type = models.CharField(max_length=50, choices=NODE_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, null=True, blank=True)
    
    # 位置
    position_x = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position_y = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 配置
    config = models.JSONField(null=True, blank=True)
    input_schema = models.JSONField(null=True, blank=True)
    output_schema = models.JSONField(null=True, blank=True)
    
    # 错误处理
    error_handling = models.CharField(max_length=20, choices=ERROR_HANDLING_CHOICES, 
                                      default='stop')
    max_retries = models.IntegerField(default=3)
    retry_delay_seconds = models.IntegerField(default=5)
    
    # 条件
    condition_expression = models.TextField(null=True, blank=True)
    
    # 执行控制
    is_enabled = models.BooleanField(default=True)
    timeout_seconds = models.IntegerField(null=True, blank=True)
    
    version = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'nodes'
        verbose_name = '节点'
        verbose_name_plural = '节点'
        indexes = [
            models.Index(fields=['workflow']),
            models.Index(fields=['node_type']),
            models.Index(fields=['is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"


class Edge(models.Model):
    """工作流连线模型"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE,
                                  related_name='edges')
    
    source_node = models.ForeignKey(Node, on_delete=models.CASCADE,
                                     related_name='outgoing_edges')
    source_handle = models.CharField(max_length=50, default='default')
    
    target_node = models.ForeignKey(Node, on_delete=models.CASCADE,
                                     related_name='incoming_edges')
    target_handle = models.CharField(max_length=50, default='default')
    
    label = models.CharField(max_length=200, null=True, blank=True)
    style = models.JSONField(null=True, blank=True)
    
    # 条件边
    condition_expression = models.TextField(null=True, blank=True)
    condition_priority = models.IntegerField(default=0)
    
    animated = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'edges'
        verbose_name = '连线'
        verbose_name_plural = '连线'
        constraints = [
            models.UniqueConstraint(
                fields=['source_node', 'source_handle', 'target_node', 'target_handle'],
                name='unique_edge_connection'
            )
        ]
        indexes = [
            models.Index(fields=['workflow']),
            models.Index(fields=['source_node']),
            models.Index(fields=['target_node']),
        ]
    
    def __str__(self):
        return f"{self.source_node.name} → {self.target_node.name}"


class WorkflowExecution(models.Model):
    """工作流执行记录"""
    
    TRIGGER_TYPE_CHOICES = [
        ('manual', '手动触发'),
        ('scheduled', '定时任务'),
        ('webhook', 'Webhook'),
        ('api', 'API调用'),
        ('event', '事件触发'),
    ]
    
    STATUS_CHOICES = [
        ('queued', '排队中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
        ('timeout', '超时'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE,
                                  related_name='executions')
    version = models.IntegerField()
    
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES,
                                     default='manual')
    trigger_config = models.JSONField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    input_data = models.JSONField(null=True, blank=True)
    output_data = models.JSONField(null=True, blank=True)
    
    total_nodes = models.IntegerField(null=True, blank=True)
    executed_nodes = models.IntegerField(null=True, blank=True)
    skipped_nodes = models.IntegerField(null=True, blank=True)
    failed_nodes = models.IntegerField(null=True, blank=True)
    
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    error_message = models.TextField(null=True, blank=True)
    error_stack = models.TextField(null=True, blank=True)
    
    token_usage = models.JSONField(null=True, blank=True)
    cost_amount = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    cost_currency = models.CharField(max_length=10, default='USD')
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                               related_name='executions')
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True,
                                related_name='executions')
    
    context_data = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_executions'
        verbose_name = '执行记录'
        verbose_name_plural = '执行记录'
        indexes = [
            models.Index(fields=['workflow']),
            models.Index(fields=['status']),
            models.Index(fields=['trigger_type']),
            models.Index(fields=['user']),
            models.Index(fields=['tenant']),
            models.Index(fields=['-started_at']),
            models.Index(fields=['-queued_at']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.status} ({self.id})"
    
    def mark_started(self):
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def mark_completed(self, output_data=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if output_data:
            self.output_data = output_data
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save(update_fields=['status', 'completed_at', 'output_data', 'duration_ms', 'updated_at'])
    
    def mark_failed(self, error_message, error_stack=None):
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_stack = error_stack
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save(update_fields=['status', 'completed_at', 'error_message', 'error_stack', 'duration_ms', 'updated_at'])


class NodeExecution(models.Model):
    """节点执行记录"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('skipped', '已跳过'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE,
                                    related_name='node_executions')
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='executions')
    node_version = models.IntegerField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    input_data = models.JSONField(null=True, blank=True)
    output_data = models.JSONField(null=True, blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries_exceeded = models.BooleanField(default=False)
    
    model_name = models.CharField(max_length=100, null=True, blank=True)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)
    model_latency_ms = models.IntegerField(null=True, blank=True)
    
    cache_hit = models.BooleanField(default=False)
    cache_key = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'node_executions'
        verbose_name = '节点执行'
        verbose_name_plural = '节点执行'
        indexes = [
            models.Index(fields=['execution']),
            models.Index(fields=['node']),
            models.Index(fields=['status']),
            models.Index(fields=['cache_hit']),
            models.Index(fields=['-started_at']),
        ]
    
    def __str__(self):
        return f"{self.node.name} - {self.status}"


class ExecutionLog(models.Model):
    """执行日志"""
    
    LOG_LEVEL_CHOICES = [
        ('DEBUG', '调试'),
        ('INFO', '信息'),
        ('WARNING', '警告'),
        ('ERROR', '错误'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE,
                                   related_name='logs')
    node_execution = models.ForeignKey(NodeExecution, on_delete=models.CASCADE,
                                        null=True, blank=True,
                                        related_name='logs')
    
    log_level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    
    source = models.CharField(max_length=50, null=True, blank=True)
    node = models.ForeignKey(Node, on_delete=models.SET_NULL, null=True, blank=True)
    node_name = models.CharField(max_length=200, null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'execution_logs'
        verbose_name = '执行日志'
        verbose_name_plural = '执行日志'
        indexes = [
            models.Index(fields=['execution']),
            models.Index(fields=['node_execution']),
            models.Index(fields=['log_level']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['node']),
        ]
    
    def __str__(self):
        return f"[{self.log_level}] {self.message[:50]}..."


class PromptTemplate(models.Model):
    """Prompt 模板"""
    
    OUTPUT_FORMAT_CHOICES = [
        ('text', '文本'),
        ('json', 'JSON'),
        ('markdown', 'Markdown'),
        ('xml', 'XML'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True,
                                related_name='prompt_templates')
    
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    tags = models.JSONField(null=True, blank=True)
    
    template = models.TextField()
    input_variables = models.JSONField(default=list)
    output_format = models.CharField(max_length=20, choices=OUTPUT_FORMAT_CHOICES, 
                                     default='text')
    
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    usage_count = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    rating_count = models.IntegerField(default=0)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_templates'
        verbose_name = 'Prompt模板'
        verbose_name_plural = 'Prompt模板'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name


class Tool(models.Model):
    """工具定义"""
    
    TOOL_TYPE_CHOICES = [
        ('builtin', '内置'),
        ('custom', '自定义'),
        ('api', 'API调用'),
        ('script', '脚本'),
    ]
    
    AUTH_TYPE_CHOICES = [
        ('none', '无'),
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth2'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True,
                                related_name='tools')
    
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    
    tool_type = models.CharField(max_length=20, choices=TOOL_TYPE_CHOICES, default='custom')
    
    definition = models.JSONField(default=dict)
    input_schema = models.JSONField(null=True, blank=True)
    output_schema = models.JSONField(null=True, blank=True)
    
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default='none')
    credential = models.ForeignKey('APICredential', on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='tools')
    
    timeout_seconds = models.IntegerField(default=30)
    retry_policy = models.JSONField(null=True, blank=True)
    rate_limit = models.JSONField(null=True, blank=True)
    
    is_enabled = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    
    usage_count = models.IntegerField(default=0)
    avg_execution_time_ms = models.IntegerField(null=True, blank=True)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tools'
        verbose_name = '工具'
        verbose_name_plural = '工具'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['tool_type']),
            models.Index(fields=['category']),
            models.Index(fields=['is_enabled']),
        ]
    
    def __str__(self):
        return self.name


class APICredential(models.Model):
    """API 凭证"""
    
    CREDENTIAL_TYPE_CHOICES = [
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth2'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('aws', 'AWS'),
        ('azure', 'Azure'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='credentials')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                              related_name='credentials')
    
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    
    credential_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPE_CHOICES)
    credential_data = models.TextField()  # 加密存储
    credential_data_hash = models.CharField(max_length=64, null=True, blank=True)
    
    service_type = models.CharField(max_length=50, null=True, blank=True)
    service_config = models.JSONField(null=True, blank=True)
    
    scope = models.JSONField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_credentials'
        verbose_name = 'API凭证'
        verbose_name_plural = 'API凭证'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['user']),
            models.Index(fields=['credential_type']),
            models.Index(fields=['service_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_credential_type_display()})"


class Variable(models.Model):
    """变量定义"""
    
    VAR_TYPE_CHOICES = [
        ('string', '字符串'),
        ('number', '数字'),
        ('boolean', '布尔值'),
        ('json', 'JSON对象'),
        ('array', '数组'),
        ('secret', '密钥'),
    ]
    
    SOURCE_CHOICES = [
        ('user_input', '用户输入'),
        ('system', '系统变量'),
        ('workflow', '工作流变量'),
        ('execution', '执行上下文'),
        ('secret', '密钥管理'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True,
                                related_name='variables')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, null=True,
                                  blank=True, related_name='variables')
    
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    var_type = models.CharField(max_length=20, choices=VAR_TYPE_CHOICES, default='string')
    default_value = models.TextField(null=True, blank=True)
    validation_rules = models.JSONField(null=True, blank=True)
    
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='user_input')
    secret_path = models.CharField(max_length=500, null=True, blank=True)
    
    is_required = models.BooleanField(default=False)
    is_sensitive = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'variables'
        verbose_name = '变量'
        verbose_name_plural = '变量'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['workflow']),
            models.Index(fields=['var_type']),
            models.Index(fields=['source']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.var_type})"


class KnowledgeBase(models.Model):
    """知识库"""
    
    VECTOR_STORE_CHOICES = [
        ('qdrant', 'Qdrant'),
        ('milvus', 'Milvus'),
        ('chroma', 'Chroma'),
        ('pgvector', 'PgVector'),
        ('pinecone', 'Pinecone'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='knowledge_bases')
    
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    embeddings_provider = models.CharField(max_length=50, default='openai')
    embeddings_model = models.CharField(max_length=100, null=True, blank=True)
    
    vector_store_type = models.CharField(max_length=20, choices=VECTOR_STORE_CHOICES, 
                                         default='qdrant')
    vector_store_config = models.JSONField(null=True, blank=True)
    
    chunk_size = models.IntegerField(default=500)
    chunk_overlap = models.IntegerField(default=50)
    embedding_dimension = models.IntegerField(default=1536)
    
    retrieval_config = models.JSONField(null=True, blank=True)
    
    document_count = models.IntegerField(default=0)
    chunk_count = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'knowledge_bases'
        verbose_name = '知识库'
        verbose_name_plural = '知识库'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['vector_store_type']),
        ]
    
    def __str__(self):
        return self.name


class KnowledgeDocument(models.Model):
    """知识库文档"""
    
    STATUS_CHOICES = [
        ('pending', '等待处理'),
        ('processing', '处理中'),
        ('indexed', '已索引'),
        ('failed', '失败'),
    ]
    
    SOURCE_TYPE_CHOICES = [
        ('upload', '上传'),
        ('url', 'URL'),
        ('api', 'API'),
        ('sync', '同步'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE,
                                        related_name='documents')
    
    title = models.CharField(max_length=500)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, 
                                    default='upload')
    source_url = models.URLField(max_length=2000, null=True, blank=True)
    source_path = models.CharField(max_length=500, null=True, blank=True)
    
    content_hash = models.CharField(max_length=64, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    chunk_count = models.IntegerField(null=True, blank=True)
    token_count = models.IntegerField(null=True, blank=True)
    
    last_sync_at = models.DateTimeField(null=True, blank=True)
    indexed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'knowledge_documents'
        verbose_name = '知识文档'
        verbose_name_plural = '知识文档'
        indexes = [
            models.Index(fields=['knowledge_base']),
            models.Index(fields=['status']),
            models.Index(fields=['source_type']),
        ]
    
    def __str__(self):
        return self.title


class Webhook(models.Model):
    """Webhook 配置"""
    
    AUTH_TYPE_CHOICES = [
        ('none', '无'),
        ('api_key', 'API Key'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('hmac', 'HMAC签名'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='webhooks')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, 
                                  related_name='webhooks')
    
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default='none')
    auth_config = models.JSONField(null=True, blank=True)
    
    trigger_config = models.JSONField(null=True, blank=True)
    input_mapping = models.JSONField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=64, null=True, blank=True)
    
    call_count = models.IntegerField(default=0)
    last_called_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.IntegerField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhooks'
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooks'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['workflow']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name


class AuditLog(models.Model):
    """审计日志"""
    
    ACTION_STATUS_CHOICES = [
        ('success', '成功'),
        ('failure', '失败'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True,
                                related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                              related_name='audit_logs')
    
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField(null=True, blank=True)
    
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    request_id = models.CharField(max_length=100, null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=ACTION_STATUS_CHOICES, default='success')
    error_message = models.TextField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['resource_id']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource_type}"
```

#### 4.2.6 数据库初始化脚本

创建 `Backend/scripts/init_database.sql`：

```sql
-- =========================================
-- Flowly 数据库初始化脚本
-- MySQL 8.0+
-- =========================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS flowly_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE flowly_db;

-- 设置时区
SET time_zone = '+08:00';

-- =========================================
-- 1. 租户相关表
-- =========================================
CREATE TABLE IF NOT EXISTS `tenants` (
    `id` CHAR(36) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `slug` VARCHAR(100) NOT NULL,
    `plan` ENUM('free', 'pro', 'enterprise') NOT NULL DEFAULT 'free',
    `max_workflows` INT NOT NULL DEFAULT 10,
    `max_users` INT NOT NULL DEFAULT 5,
    `max_executions_per_month` INT DEFAULT NULL,
    `current_executions` INT NOT NULL DEFAULT 0,
    `settings` JSON DEFAULT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `trial_ends_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tenants_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 2. 用户扩展表
-- =========================================
CREATE TABLE IF NOT EXISTS `user_profiles` (
    `id` CHAR(36) NOT NULL,
    `user_id` INT NOT NULL,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `display_name` VARCHAR(100) DEFAULT NULL,
    `avatar_url` VARCHAR(500) DEFAULT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `timezone` VARCHAR(50) DEFAULT 'Asia/Shanghai',
    `language` VARCHAR(10) DEFAULT 'zh-hans',
    `preferences` JSON DEFAULT NULL,
    `role` ENUM('owner', 'admin', 'member', 'viewer') NOT NULL DEFAULT 'member',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `last_login_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_profiles_user_id` (`user_id`),
    KEY `idx_user_profiles_tenant_id` (`tenant_id`),
    CONSTRAINT `fk_user_profiles_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 3. 工作流相关表
-- =========================================
CREATE TABLE IF NOT EXISTS `workflows` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `owner_id` INT NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `version` INT NOT NULL DEFAULT 1,
    `status` ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
    `category` VARCHAR(100) DEFAULT NULL,
    `tags` JSON DEFAULT NULL,
    `config` JSON DEFAULT NULL,
    `total_executions` INT NOT NULL DEFAULT 0,
    `successful_executions` INT NOT NULL DEFAULT 0,
    `failed_executions` INT NOT NULL DEFAULT 0,
    `avg_execution_time_ms` INT DEFAULT NULL,
    `last_executed_at` DATETIME DEFAULT NULL,
    `is_public` TINYINT(1) NOT NULL DEFAULT 0,
    `share_token` VARCHAR(64) DEFAULT NULL,
    `parent_version_id` CHAR(36) DEFAULT NULL,
    `change_summary` TEXT DEFAULT NULL,
    `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
    `deleted_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_workflows_share_token` (`share_token`),
    KEY `idx_workflows_tenant_id` (`tenant_id`),
    KEY `idx_workflows_owner_id` (`owner_id`),
    KEY `idx_workflows_status` (`status`),
    KEY `idx_workflows_is_deleted` (`is_deleted`),
    CONSTRAINT `fk_workflows_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `nodes` (
    `id` CHAR(36) NOT NULL,
    `workflow_id` CHAR(36) NOT NULL,
    `parent_node_id` CHAR(36) DEFAULT NULL,
    `node_type` VARCHAR(50) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` VARCHAR(500) DEFAULT NULL,
    `position_x` DECIMAL(10, 2) NOT NULL DEFAULT 0,
    `position_y` DECIMAL(10, 2) NOT NULL DEFAULT 0,
    `width` DECIMAL(10, 2) DEFAULT NULL,
    `height` DECIMAL(10, 2) DEFAULT NULL,
    `config` JSON DEFAULT NULL,
    `input_schema` JSON DEFAULT NULL,
    `output_schema` JSON DEFAULT NULL,
    `error_handling` ENUM('stop', 'skip', 'retry', 'fallback') NOT NULL DEFAULT 'stop',
    `max_retries` INT NOT NULL DEFAULT 3,
    `retry_delay_seconds` INT NOT NULL DEFAULT 5,
    `condition_expression` TEXT DEFAULT NULL,
    `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `timeout_seconds` INT DEFAULT NULL,
    `version` INT NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_nodes_workflow_id` (`workflow_id`),
    KEY `idx_nodes_parent_node_id` (`parent_node_id`),
    KEY `idx_nodes_node_type` (`node_type`),
    CONSTRAINT `fk_nodes_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `edges` (
    `id` CHAR(36) NOT NULL,
    `workflow_id` CHAR(36) NOT NULL,
    `source_node_id` CHAR(36) NOT NULL,
    `source_handle` VARCHAR(50) DEFAULT 'default',
    `target_node_id` CHAR(36) NOT NULL,
    `target_handle` VARCHAR(50) DEFAULT 'default',
    `label` VARCHAR(200) DEFAULT NULL,
    `style` JSON DEFAULT NULL,
    `condition_expression` TEXT DEFAULT NULL,
    `condition_priority` INT NOT NULL DEFAULT 0,
    `animated` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_edges_connection` (`source_node_id`, `source_handle`, `target_node_id`, `target_handle`),
    KEY `idx_edges_workflow_id` (`workflow_id`),
    KEY `idx_edges_source_node_id` (`source_node_id`),
    KEY `idx_edges_target_node_id` (`target_node_id`),
    CONSTRAINT `fk_edges_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_edges_source_node` FOREIGN KEY (`source_node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_edges_target_node` FOREIGN KEY (`target_node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 4. 执行记录表
-- =========================================
CREATE TABLE IF NOT EXISTS `workflow_executions` (
    `id` CHAR(36) NOT NULL,
    `workflow_id` CHAR(36) NOT NULL,
    `version` INT NOT NULL,
    `trigger_type` ENUM('manual', 'scheduled', 'webhook', 'api', 'event') NOT NULL DEFAULT 'manual',
    `trigger_config` JSON DEFAULT NULL,
    `status` ENUM('queued', 'running', 'completed', 'failed', 'cancelled', 'timeout') NOT NULL DEFAULT 'queued',
    `input_data` JSON DEFAULT NULL,
    `output_data` JSON DEFAULT NULL,
    `total_nodes` INT DEFAULT NULL,
    `executed_nodes` INT DEFAULT NULL,
    `skipped_nodes` INT DEFAULT NULL,
    `failed_nodes` INT DEFAULT NULL,
    `queued_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `started_at` DATETIME DEFAULT NULL,
    `completed_at` DATETIME DEFAULT NULL,
    `duration_ms` INT DEFAULT NULL,
    `error_message` TEXT DEFAULT NULL,
    `error_stack` TEXT DEFAULT NULL,
    `token_usage` JSON DEFAULT NULL,
    `cost_amount` DECIMAL(10, 4) DEFAULT NULL,
    `cost_currency` VARCHAR(10) DEFAULT 'USD',
    `user_id` INT DEFAULT NULL,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `context_data` JSON DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_executions_workflow_id` (`workflow_id`),
    KEY `idx_executions_status` (`status`),
    KEY `idx_executions_user_id` (`user_id`),
    KEY `idx_executions_tenant_id` (`tenant_id`),
    KEY `idx_executions_started_at` (`started_at`),
    CONSTRAINT `fk_executions_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `node_executions` (
    `id` CHAR(36) NOT NULL,
    `execution_id` CHAR(36) NOT NULL,
    `node_id` CHAR(36) NOT NULL,
    `node_version` INT NOT NULL,
    `status` ENUM('pending', 'running', 'completed', 'failed', 'skipped') NOT NULL DEFAULT 'pending',
    `input_data` JSON DEFAULT NULL,
    `output_data` JSON DEFAULT NULL,
    `started_at` DATETIME DEFAULT NULL,
    `completed_at` DATETIME DEFAULT NULL,
    `duration_ms` INT DEFAULT NULL,
    `error_message` TEXT DEFAULT NULL,
    `retry_count` INT NOT NULL DEFAULT 0,
    `max_retries_exceeded` TINYINT(1) NOT NULL DEFAULT 0,
    `model_name` VARCHAR(100) DEFAULT NULL,
    `prompt_tokens` INT DEFAULT NULL,
    `completion_tokens` INT DEFAULT NULL,
    `total_tokens` INT DEFAULT NULL,
    `model_latency_ms` INT DEFAULT NULL,
    `cache_hit` TINYINT(1) NOT NULL DEFAULT 0,
    `cache_key` VARCHAR(100) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_node_executions_execution_id` (`execution_id`),
    KEY `idx_node_executions_node_id` (`node_id`),
    KEY `idx_node_executions_status` (`status`),
    CONSTRAINT `fk_node_executions_execution` FOREIGN KEY (`execution_id`) 
        REFERENCES `workflow_executions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_node_executions_node` FOREIGN KEY (`node_id`) 
        REFERENCES `nodes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `execution_logs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `execution_id` CHAR(36) NOT NULL,
    `node_execution_id` CHAR(36) DEFAULT NULL,
    `log_level` ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR') NOT NULL DEFAULT 'INFO',
    `message` TEXT NOT NULL,
    `metadata` JSON DEFAULT NULL,
    `source` VARCHAR(50) DEFAULT NULL,
    `node_id` CHAR(36) DEFAULT NULL,
    `node_name` VARCHAR(200) DEFAULT NULL,
    `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_logs_execution_id` (`execution_id`),
    KEY `idx_logs_node_execution_id` (`node_execution_id`),
    KEY `idx_logs_timestamp` (`timestamp`),
    CONSTRAINT `fk_logs_execution` FOREIGN KEY (`execution_id`) 
        REFERENCES `workflow_executions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 5. 辅助表
-- =========================================
CREATE TABLE IF NOT EXISTS `prompt_templates` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `category` VARCHAR(100) DEFAULT NULL,
    `tags` JSON DEFAULT NULL,
    `template` TEXT NOT NULL,
    `input_variables` JSON NOT NULL,
    `output_format` ENUM('text', 'json', 'markdown', 'xml') DEFAULT 'text',
    `version` INT NOT NULL DEFAULT 1,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `usage_count` INT NOT NULL DEFAULT 0,
    `success_rate` DECIMAL(5, 2) DEFAULT NULL,
    `avg_rating` DECIMAL(3, 2) DEFAULT NULL,
    `rating_count` INT NOT NULL DEFAULT 0,
    `created_by_id` INT DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_prompt_templates_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tools` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `name` VARCHAR(100) NOT NULL,
    `display_name` VARCHAR(200) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `category` VARCHAR(100) DEFAULT NULL,
    `tool_type` ENUM('builtin', 'custom', 'api', 'script') NOT NULL DEFAULT 'custom',
    `definition` JSON NOT NULL,
    `input_schema` JSON DEFAULT NULL,
    `output_schema` JSON DEFAULT NULL,
    `auth_type` ENUM('none', 'api_key', 'oauth2', 'basic', 'bearer') DEFAULT 'none',
    `credential_id` CHAR(36) DEFAULT NULL,
    `timeout_seconds` INT NOT NULL DEFAULT 30,
    `retry_policy` JSON DEFAULT NULL,
    `rate_limit` JSON DEFAULT NULL,
    `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `is_public` TINYINT(1) NOT NULL DEFAULT 0,
    `usage_count` INT NOT NULL DEFAULT 0,
    `avg_execution_time_ms` INT DEFAULT NULL,
    `success_rate` DECIMAL(5, 2) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_tools_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `api_credentials` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) NOT NULL,
    `user_id` INT DEFAULT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `credential_type` ENUM('api_key', 'oauth2', 'basic', 'bearer', 'aws', 'azure') NOT NULL,
    `credential_data` TEXT NOT NULL,
    `credential_data_hash` VARCHAR(64) DEFAULT NULL,
    `service_type` VARCHAR(50) DEFAULT NULL,
    `service_config` JSON DEFAULT NULL,
    `scope` JSON DEFAULT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `expires_at` DATETIME DEFAULT NULL,
    `last_used_at` DATETIME DEFAULT NULL,
    `usage_count` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_api_credentials_tenant_id` (`tenant_id`),
    CONSTRAINT `fk_api_credentials_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `variables` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `workflow_id` CHAR(36) DEFAULT NULL,
    `name` VARCHAR(100) NOT NULL,
    `display_name` VARCHAR(200) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `var_type` ENUM('string', 'number', 'boolean', 'json', 'array', 'secret') NOT NULL DEFAULT 'string',
    `default_value` TEXT DEFAULT NULL,
    `validation_rules` JSON DEFAULT NULL,
    `source` ENUM('user_input', 'system', 'workflow', 'execution', 'secret') NOT NULL DEFAULT 'user_input',
    `secret_path` VARCHAR(500) DEFAULT NULL,
    `is_required` TINYINT(1) NOT NULL DEFAULT 0,
    `is_sensitive` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_variables_tenant_id` (`tenant_id`),
    KEY `idx_variables_workflow_id` (`workflow_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 6. 知识库表
-- =========================================
CREATE TABLE IF NOT EXISTS `knowledge_bases` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `embeddings_provider` VARCHAR(50) DEFAULT 'openai',
    `embeddings_model` VARCHAR(100) DEFAULT NULL,
    `vector_store_type` ENUM('qdrant', 'milvus', 'chroma', 'pgvector', 'pinecone') NOT NULL DEFAULT 'qdrant',
    `vector_store_config` JSON DEFAULT NULL,
    `chunk_size` INT NOT NULL DEFAULT 500,
    `chunk_overlap` INT NOT NULL DEFAULT 50,
    `embedding_dimension` INT NOT NULL DEFAULT 1536,
    `retrieval_config` JSON DEFAULT NULL,
    `document_count` INT NOT NULL DEFAULT 0,
    `chunk_count` INT NOT NULL DEFAULT 0,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_knowledge_bases_tenant_id` (`tenant_id`),
    CONSTRAINT `fk_knowledge_bases_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `knowledge_documents` (
    `id` CHAR(36) NOT NULL,
    `knowledge_base_id` CHAR(36) NOT NULL,
    `title` VARCHAR(500) NOT NULL,
    `source_type` ENUM('upload', 'url', 'api', 'sync') NOT NULL DEFAULT 'upload',
    `source_url` VARCHAR(2000) DEFAULT NULL,
    `source_path` VARCHAR(500) DEFAULT NULL,
    `content_hash` VARCHAR(64) DEFAULT NULL,
    `metadata` JSON DEFAULT NULL,
    `status` ENUM('pending', 'processing', 'indexed', 'failed') NOT NULL DEFAULT 'pending',
    `chunk_count` INT DEFAULT NULL,
    `token_count` INT DEFAULT NULL,
    `last_sync_at` DATETIME DEFAULT NULL,
    `indexed_at` DATETIME DEFAULT NULL,
    `error_message` TEXT DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_knowledge_documents_knowledge_base_id` (`knowledge_base_id`),
    KEY `idx_knowledge_documents_status` (`status`),
    CONSTRAINT `fk_knowledge_documents_knowledge_base` FOREIGN KEY (`knowledge_base_id`) 
        REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 7. Webhook 和审计表
-- =========================================
CREATE TABLE IF NOT EXISTS `webhooks` (
    `id` CHAR(36) NOT NULL,
    `tenant_id` CHAR(36) NOT NULL,
    `workflow_id` CHAR(36) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `auth_type` ENUM('none', 'api_key', 'basic', 'bearer', 'hmac') DEFAULT 'none',
    `auth_config` JSON DEFAULT NULL,
    `trigger_config` JSON DEFAULT NULL,
    `input_mapping` JSON DEFAULT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `secret_key` VARCHAR(64) DEFAULT NULL,
    `call_count` INT NOT NULL DEFAULT 0,
    `last_called_at` DATETIME DEFAULT NULL,
    `last_status_code` INT DEFAULT NULL,
    `failure_count` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_webhooks_tenant_id` (`tenant_id`),
    KEY `idx_webhooks_workflow_id` (`workflow_id`),
    CONSTRAINT `fk_webhooks_tenant` FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_webhooks_workflow` FOREIGN KEY (`workflow_id`) 
        REFERENCES `workflows` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `tenant_id` CHAR(36) DEFAULT NULL,
    `user_id` INT DEFAULT NULL,
    `action` VARCHAR(100) NOT NULL,
    `resource_type` VARCHAR(50) NOT NULL,
    `resource_id` CHAR(36) DEFAULT NULL,
    `old_value` JSON DEFAULT NULL,
    `new_value` JSON DEFAULT NULL,
    `ip_address` VARCHAR(45) DEFAULT NULL,
    `user_agent` VARCHAR(500) DEFAULT NULL,
    `request_id` VARCHAR(100) DEFAULT NULL,
    `status` ENUM('success', 'failure') NOT NULL DEFAULT 'success',
    `error_message` TEXT DEFAULT NULL,
    `timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_audit_logs_tenant_id` (`tenant_id`),
    KEY `idx_audit_logs_user_id` (`user_id`),
    KEY `idx_audit_logs_action` (`action`),
    KEY `idx_audit_logs_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- 初始化默认数据
-- =========================================

-- 创建默认租户
INSERT INTO `tenants` (`id`, `name`, `slug`, `plan`, `max_workflows`, `max_users`) VALUES
('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'free', 10, 5);

-- =========================================
-- 视图定义 (用于常用查询)
-- =========================================

-- 工作流执行统计视图
CREATE OR REPLACE VIEW `workflow_execution_stats` AS
SELECT 
    w.id AS workflow_id,
    w.name AS workflow_name,
    COUNT(e.id) AS total_executions,
    SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) AS successful_executions,
    SUM(CASE WHEN e.status = 'failed' THEN 1 ELSE 0 END) AS failed_executions,
    AVG(CASE WHEN e.duration_ms IS NOT NULL THEN e.duration_ms END) AS avg_duration_ms,
    MAX(e.started_at) AS last_execution_at
FROM workflows w
LEFT JOIN workflow_executions e ON w.id = e.workflow_id
GROUP BY w.id, w.name;

-- 每日执行统计视图
CREATE OR REPLACE VIEW `daily_execution_stats` AS
SELECT 
    DATE(queued_at) AS execution_date,
    COUNT(*) AS total_executions,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
    SUM(token_usage->>'$.total_tokens') AS total_tokens,
    SUM(cost_amount) AS total_cost
FROM workflow_executions
GROUP BY DATE(queued_at)
ORDER BY execution_date DESC;

-- =========================================
-- 存储过程 (常用业务逻辑)
-- =========================================

-- 清理过期执行记录 (保留最近30天)
DELIMITER //
CREATE PROCEDURE `cleanup_old_executions`(IN days_to_keep INT)
BEGIN
    DELETE FROM execution_logs 
    WHERE execution_id IN (
        SELECT id FROM workflow_executions 
        WHERE queued_at < DATE_SUB(NOW(), INTERVAL days_to_keep DAY)
    );
    
    DELETE FROM node_executions 
    WHERE execution_id IN (
        SELECT id FROM workflow_executions 
        WHERE queued_at < DATE_SUB(NOW(), INTERVAL days_to_keep DAY)
    );
    
    DELETE FROM workflow_executions 
    WHERE queued_at < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);
END //
DELIMITER ;

-- 更新工作流统计信息
DELIMITER //
CREATE PROCEDURE `update_workflow_stats`(IN p_workflow_id CHAR(36))
BEGIN
    UPDATE workflows w
    SET 
        total_executions = (
            SELECT COUNT(*) FROM workflow_executions WHERE workflow_id = p_workflow_id
        ),
        successful_executions = (
            SELECT COUNT(*) FROM workflow_executions 
            WHERE workflow_id = p_workflow_id AND status = 'completed'
        ),
        failed_executions = (
            SELECT COUNT(*) FROM workflow_executions 
            WHERE workflow_id = p_workflow_id AND status = 'failed'
        ),
        avg_execution_time_ms = (
            SELECT AVG(duration_ms) FROM workflow_executions 
            WHERE workflow_id = p_workflow_id AND duration_ms IS NOT NULL
        ),
        last_executed_at = (
            SELECT MAX(started_at) FROM workflow_executions 
            WHERE workflow_id = p_workflow_id
        )
    WHERE w.id = p_workflow_id;
END //
DELIMITER ;

-- =========================================
-- 索引优化建议
-- =========================================
-- 对于高并发场景，考虑添加以下分区策略：
-- 
-- 1. 执行记录表按月分区
-- ALTER TABLE workflow_executions PARTITION BY RANGE (YEAR(queued_at) * 100 + MONTH(queued_at)) (
--     PARTITION p202601 VALUES LESS THAN (202602),
--     PARTITION p202602 VALUES LESS THAN (202603),
--     ...
-- );

-- 2. 日志表按天分区并设置自动清理
-- ALTER TABLE execution_logs PARTITION BY RANGE (TO_DAYS(timestamp)) (
--     PARTITION p_OLD VALUES LESS THAN (TO_DAYS('2026-01-01')),
--     ...
-- );

-- =========================================
-- 完成
-- =========================================
SELECT '数据库初始化完成!' AS message;
```

#### 4.2.7 数据库设计规范总结

| 规范项 | 说明 |
|-------|------|
| **主键** | 使用 UUID v4，支持分布式环境 |
| **时间戳** | 使用 `created_at` 和 `updated_at` 自动管理 |
| **软删除** | 使用 `is_deleted` 标记，配合 `deleted_at` 记录删除时间 |
| **多租户** | 通过 `tenant_id` 字段实现数据隔离 |
| **JSON 字段** | 用于存储灵活配置，避免 schema 变更 |
| **索引策略** | 复合索引优先，外键字段必须建索引 |
| **命名规范** | 表名单数、字段名下划线、注释完整 |
| **安全性** | 敏感数据加密存储，凭证数据使用哈希校验 |

### 5.2 创建数据表

```powershell
# 生成迁移文件
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

### 5.3 创建超级管理员

```powershell
python manage.py createsuperuser

# 按提示输入用户名、邮箱、密码
```

### 5.4 在 admin.py 中注册模型

编辑 `Backend/workflow/admin.py`：

```python
from django.contrib import admin
from .models import Workflow, Node, Edge, WorkflowExecution


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('name', 'description')


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'node_type', 'workflow', 'position_x', 'position_y')
    list_filter = ('node_type',)


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ('source_node', 'target_node', 'workflow')


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'started_at')
```

启动服务器验证：

```powershell
python manage.py runserver
# 访问 http://127.0.0.1:8000/admin/
```

---

## Step 6 - Vue 前端开发

### 2.1 创建 Vue 项目

```powershell
cd e:\Flowly-now\Frontend

# 使用 Vite 创建 Vue 项目
npm create vite@latest . -- --template vue

# 安装依赖
npm install
```

### 2.2 安装前端依赖

```powershell
# 安装 Vue Router
npm install vue-router@4

# 安装状态管理 Pinia
npm install pinia

# 安装 HTTP 请求库
npm install axios

# 安装 UI 组件库（Element Plus）
npm install element-plus

# 安装可视化流程图库
npm install @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap
```

### 2.3 验证前端项目

```powershell
# 启动开发服务器
npm run dev
```

如果看到类似以下内容，说明 Vue 安装成功：

```
  VITE v5.x.x  ready in xxx ms

  Local:   http://localhost:5173/
```

按 `Ctrl + C` 停止。

在 `config/settings.py` 中添加：

```python
INSTALLED_APPS = [
    # ... 其他应用
    'rest_framework',
    'corsheaders',
    'workflow',
]

# 添加 CORS 配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True

# REST Framework 配置
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### 6.2 创建序列化器

在 `workflow` 目录下创建 `serializers.py`：

```python
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Workflow, Node, Edge, WorkflowExecution


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ['id', 'workflow', 'node_type', 'name', 'config',
                  'position_x', 'position_y', 'created_at']
        read_only_fields = ['created_at']


class EdgeSerializer(serializers.ModelSerializer):
    source_node_name = serializers.CharField(source='source_node.name', read_only=True)
    target_node_name = serializers.CharField(source='target_node.name', read_only=True)

    class Meta:
        model = Edge
        fields = ['id', 'workflow', 'source_node', 'target_node', 'label',
                  'source_node_name', 'target_node_name']


class WorkflowSerializer(serializers.ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'owner', 'owner_name',
                  'is_published', 'nodes', 'edges', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class WorkflowListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    node_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'owner_name', 'is_published',
                  'node_count', 'created_at', 'updated_at']

    def get_node_count(self, obj):
        return obj.nodes.count()


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = ['id', 'workflow', 'workflow_name', 'status', 'input_data',
                  'output_data', 'error_message', 'started_at', 'completed_at']
        read_only_fields = ['started_at', 'completed_at']
```

### 6.3 创建视图

编辑 `workflow/views.py`：

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Workflow, Node, Edge, WorkflowExecution
from .serializers import (
    WorkflowSerializer, WorkflowListSerializer,
    NodeSerializer, EdgeSerializer, WorkflowExecutionSerializer
)


class WorkflowViewSet(viewsets.ModelViewSet):
    queryset = Workflow.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行工作流"""
        workflow = self.get_object()

        # 创建执行记录
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            status='running',
            input_data=request.data.get('input_data', {})
        )

        # 这里后续会集成 LangChain 执行逻辑
        # 目前先返回占位响应
        return Response({
            'execution_id': execution.id,
            'status': 'started',
            'message': '工作流执行已启动'
        })


class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer


class EdgeViewSet(viewsets.ModelViewSet):
    queryset = Edge.objects.all()
    serializer_class = EdgeSerializer


class WorkflowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowExecution.objects.all()
    serializer_class = WorkflowExecutionSerializer

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消执行"""
        execution = self.get_object()
        execution.status = 'failed'
        execution.error_message = '用户取消'
        execution.save()
        return Response({'status': 'cancelled'})
```

### 6.4 配置路由

创建 `workflow/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkflowViewSet, NodeViewSet, EdgeViewSet, WorkflowExecutionViewSet

router = DefaultRouter()
router.register(r'workflows', WorkflowViewSet)
router.register(r'nodes', NodeViewSet)
router.register(r'edges', EdgeViewSet)
router.register(r'executions', WorkflowExecutionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

在 `config/urls.py` 中引入：

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('workflow.urls')),
]
```

### 6.5 测试 API

```powershell
python manage.py runserver
```

访问：
- http://127.0.0.1:8000/api/workflows/ - 工作流列表
- http://127.0.0.1:8000/api/nodes/ - 节点列表
- http://127.0.0.1:8000/api/edges/ - 连接列表
- http://127.0.0.1:8000/api/executions/ - 执行记录

---

## Step 7 - Vue 前端开发（续）

### 7.1 创建项目结构

在 `Frontend/src` 下创建以下目录：

```
src/
├── api/            # API 调用
├── components/     # 组件
├── views/          # 页面视图
├── stores/         # Pinia 状态管理
├── router/         # 路由配置
├── utils/          # 工具函数
└── assets/         # 静态资源
```

### 7.2 配置 Vue Router

创建 `src/router/index.js`：

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue')
  },
  {
    path: '/workflows',
    name: 'Workflows',
    component: () => import('../views/WorkflowList.vue')
  },
  {
    path: '/workflow/:id',
    name: 'WorkflowEditor',
    component: () => import('../views/WorkflowEditor.vue')
  },
  {
    path: '/executions',
    name: 'Executions',
    component: () => import('../views/ExecutionList.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

### 7.3 创建 Pinia Store

创建 `src/stores/workflow.js`：

```javascript
import { defineStore } from 'pinia'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000/api'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    workflows: [],
    currentWorkflow: null,
    nodes: [],
    edges: [],
    executions: [],
    loading: false,
    error: null
  }),

  actions: {
    async fetchWorkflows() {
      this.loading = true
      try {
        const response = await axios.get(`${API_BASE}/workflows/`)
        this.workflows = response.data.results || response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async fetchWorkflow(id) {
      this.loading = true
      try {
        const response = await axios.get(`${API_BASE}/workflows/${id}/`)
        this.currentWorkflow = response.data
        this.nodes = response.data.nodes || []
        this.edges = response.data.edges || []
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async createWorkflow(data) {
      const response = await axios.post(`${API_BASE}/workflows/`, data)
      this.workflows.unshift(response.data)
      return response.data
    },

    async updateWorkflow(id, data) {
      const response = await axios.patch(`${API_BASE}/workflows/${id}/`, data)
      return response.data
    },

    async deleteWorkflow(id) {
      await axios.delete(`${API_BASE}/workflows/${id}/`)
      this.workflows = this.workflows.filter(w => w.id !== id)
    },

    async executeWorkflow(id, inputData) {
      const response = await axios.post(`${API_BASE}/workflows/${id}/execute/`, {
        input_data: inputData
      })
      return response.data
    },

    async fetchExecutions() {
      this.loading = true
      try {
        const response = await axios.get(`${API_BASE}/executions/`)
        this.executions = response.data.results || response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    }
  }
})
```

### 7.4 创建 API 模块

创建 `src/api/workflow.js`：

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

export const workflowAPI = {
  // 工作流 CRUD
  getWorkflows: () => api.get('/workflows/'),
  getWorkflow: (id) => api.get(`/workflows/${id}/`),
  createWorkflow: (data) => api.post('/workflows/', data),
  updateWorkflow: (id, data) => api.patch(`/workflows/${id}/`, data),
  deleteWorkflow: (id) => api.delete(`/workflows/${id}/`),
  executeWorkflow: (id, inputData) => api.post(`/workflows/${id}/execute/`, { input_data: inputData }),

  // 节点 CRUD
  getNodes: () => api.get('/nodes/'),
  createNode: (data) => api.post('/nodes/', data),
  updateNode: (id, data) => api.patch(`/nodes/${id}/`, data),
  deleteNode: (id) => api.delete(`/nodes/${id}/`),

  // 连接线 CRUD
  getEdges: () => api.get('/edges/'),
  createEdge: (data) => api.post('/edges/', data),
  deleteEdge: (id) => api.delete(`/edges/${id}/`),

  // 执行记录
  getExecutions: () => api.get('/executions/'),
  getExecution: (id) => api.get(`/executions/${id}/`),
}

export default api
```

### 7.5 创建主视图组件

创建 `src/views/HomeView.vue`：

```vue
<template>
  <div class="home">
    <header class="header">
      <h1>AI Workflow Builder</h1>
      <p class="subtitle">可视化的工作流编排工具</p>
    </header>

    <div class="features">
      <div class="feature-card" @click="$router.push('/workflows')">
        <h3>我的工作流</h3>
        <p>创建和管理你的 AI 工作流</p>
      </div>
      <div class="feature-card" @click="$router.push('/executions')">
        <h3>执行记录</h3>
        <p>查看工作流的运行历史</p>
      </div>
      <div class="feature-card">
        <h3>组件市场</h3>
        <p>探索更多工作流组件</p>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home {
  padding: 40px;
  text-align: center;
}

.header h1 {
  font-size: 2.5rem;
  color: #333;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 1.2rem;
  color: #666;
  margin-bottom: 40px;
}

.features {
  display: flex;
  gap: 20px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 40px;
}

.feature-card {
  width: 280px;
  padding: 30px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: #4a90d9;
  box-shadow: 0 4px 20px rgba(74, 144, 217, 0.15);
  transform: translateY(-4px);
}

.feature-card h3 {
  color: #333;
  margin-bottom: 10px;
}

.feature-card p {
  color: #666;
  font-size: 0.9rem;
}
</style>
```

### 7.6 创建工作流编辑器视图

创建 `src/views/WorkflowEditor.vue`（核心的可视化编辑器）：

```vue
<template>
  <div class="workflow-editor">
    <header class="editor-header">
      <button @click="$router.back()">← 返回</button>
      <h2>{{ workflowName || '新建工作流' }}</h2>
      <div class="actions">
        <button @click="saveWorkflow">保存</button>
        <button @click="executeWorkflow" class="primary">执行</button>
      </div>
    </header>

    <div class="editor-container">
      <!-- 左侧工具栏 -->
      <aside class="node-palette">
        <h3>节点</h3>
        <div
          v-for="nodeType in nodeTypes"
          :key="nodeType.type"
          class="palette-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType)"
        >
          <span class="node-icon">{{ nodeType.icon }}</span>
          {{ nodeType.label }}
        </div>
      </aside>

      <!-- 中间画布 -->
      <main class="canvas">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          @node-drag-stop="onNodeDragStop"
          @edge-click="onEdgeClick"
          @pane-click="onPaneClick"
        >
          <Background pattern-color="#aaa" :gap="16" />
          <Controls />
          <MiniMap />
        </VueFlow>
      </main>

      <!-- 右侧属性面板 -->
      <aside class="properties-panel" v-if="selectedNode">
        <h3>节点属性</h3>
        <div class="form-group">
          <label>名称</label>
          <input v-model="selectedNode.data.label" type="text" />
        </div>
        <div class="form-group">
          <label>类型</label>
          <select v-model="selectedNode.type">
            <option v-for="t in nodeTypes" :key="t.type" :value="t.type">
              {{ t.label }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>配置</label>
          <textarea
            v-model="configJson"
            rows="10"
            placeholder="JSON 配置..."
          ></textarea>
        </div>
        <button @click="deleteSelectedNode" class="danger">删除节点</button>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { useWorkflowStore } from '../stores/workflow'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const store = useWorkflowStore()
const { onNodesChange, onEdgesChange, addNodes } = useVueFlow()

const workflowName = ref('')
const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const selectedEdge = ref(null)

const nodeTypes = [
  { type: 'start', label: '开始', icon: '▶️' },
  { type: 'end', label: '结束', icon: '⏹️' },
  { type: 'input', label: '输入', icon: '📥' },
  { type: 'llm', label: '大语言模型', icon: '🤖' },
  { type: 'prompt', label: '提示词', icon: '💬' },
  { type: 'condition', label: '条件判断', icon: '❓' },
  { type: 'tool', label: '工具', icon: '🔧' },
  { type: 'output', label: '输出', icon: '📤' }
]

const configJson = computed({
  get: () => JSON.stringify(selectedNode.value?.data?.config || {}, null, 2),
  set: (val) => {
    try {
      if (selectedNode.value) {
        selectedNode.value.data.config = JSON.parse(val)
      }
    } catch (e) {
      // JSON 解析错误，忽略
    }
  }
})

onMounted(async () => {
  const workflowId = route.params.id
  if (workflowId && workflowId !== 'new') {
    await store.fetchWorkflow(workflowId)
    workflowName.value = store.currentWorkflow?.name || ''
    nodes.value = store.nodes.map(n => ({
      id: String(n.id),
      type: n.node_type,
      position: { x: n.position_x, y: n.position_y },
      data: { label: n.name, config: n.config }
    }))
    edges.value = store.edges.map(e => ({
      id: String(e.id),
      source: String(e.source_node),
      target: String(e.target_node),
      label: e.label
    }))
  }
})

const onDragStart = (event, nodeType) => {
  event.dataTransfer.setData('application/vueflow', JSON.stringify(nodeType))
}

const onPaneClick = () => {
  selectedNode.value = null
  selectedEdge.value = null
}

const onEdgeClick = (event) => {
  selectedEdge.value = event
  selectedNode.value = null
}

const deleteSelectedNode = () => {
  if (selectedNode.value) {
    nodes.value = nodes.value.filter(n => n.id !== selectedNode.value.id)
    selectedNode.value = null
  }
}

const saveWorkflow = async () => {
  // 保存逻辑
  console.log('保存工作流', { workflowName: workflowName.value, nodes: nodes.value, edges: edges.value })
}

const executeWorkflow = async () => {
  // 执行逻辑
  console.log('执行工作流')
}
</script>

<style scoped>
.workflow-editor {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 15px 20px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}

.editor-header button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.editor-header button.primary {
  background: #4a90d9;
  color: #fff;
  border-color: #4a90d9;
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.node-palette {
  width: 200px;
  background: #f5f5f5;
  border-right: 1px solid #e0e0e0;
  padding: 20px;
}

.palette-item {
  padding: 12px;
  margin-bottom: 10px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.2s;
}

.palette-item:hover {
  border-color: #4a90d9;
  box-shadow: 0 2px 8px rgba(74, 144, 217, 0.2);
}

.node-icon {
  margin-right: 8px;
}

.canvas {
  flex: 1;
  background: #fff;
}

.properties-panel {
  width: 300px;
  background: #f5f5f5;
  border-left: 1px solid #e0e0e0;
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-sizing: border-box;
}

.form-group textarea {
  font-family: monospace;
  resize: vertical;
}

button.danger {
  width: 100%;
  padding: 10px;
  background: #dc3545;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
</style>
```

### 7.7 更新主应用

编辑 `src/App.vue`：

```vue
<template>
  <nav class="navbar">
    <div class="nav-brand">Flowly</div>
    <div class="nav-links">
      <router-link to="/">首页</router-link>
      <router-link to="/workflows">工作流</router-link>
      <router-link to="/executions">执行记录</router-link>
    </div>
  </nav>

  <main class="main-content">
    <router-view />
  </main>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #333;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  height: 60px;
  background: #1a1a2e;
  color: #fff;
}

.nav-brand {
  font-size: 1.5rem;
  font-weight: bold;
}

.nav-links {
  display: flex;
  gap: 30px;
}

.nav-links a {
  color: #ccc;
  text-decoration: none;
  transition: color 0.2s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: #fff;
}

.main-content {
  min-height: calc(100vh - 60px);
  background: #f8f9fa;
}
</style>
```

编辑 `src/main.js`：

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

### 7.8 启动前端

```powershell
npm run dev
```

访问 http://localhost:5173/

---

## Step 8 - 集成 LangChain

### 8.1 安装 LangChain 相关包

```powershell
cd e:\Flowly-now\Backend
.\venv\Scripts\Activate
pip install langchain langchain-openai langchain-community
```

### 8.2 创建 LangChain 服务

创建 `Backend/workflow/services/langchain_service.py`：

```python
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from django.conf import settings
import json


class LangChainService:
    """LangChain 服务类"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )

    def run_llm_node(self, node_config: dict, input_data: dict) -> dict:
        """执行 LLM 节点"""
        prompt_template = node_config.get('prompt', '回答以下问题: {input}')

        prompt = PromptTemplate.from_template(prompt_template)
        chain = LLMChain(llm=self.llm, prompt=prompt)

        result = chain.run(input_data.get('text', ''))

        return {
            'output': result,
            'success': True
        }

    def run_prompt_node(self, node_config: dict, input_data: dict) -> dict:
        """执行提示词节点"""
        template = node_config.get('template', '{input}')
        variables = node_config.get('variables', {})

        # 替换变量
        prompt_text = template
        for key, value in variables.items():
            prompt_text = prompt_text.replace(f'{{{key}}}', str(input_data.get(key, '')))

        return {
            'output': prompt_text,
            'success': True
        }

    def run_condition_node(self, node_config: dict, input_data: dict) -> dict:
        """执行条件判断节点"""
        condition = node_config.get('condition', '')
        value = input_data.get('value', '')

        # 简单的条件判断
        if '包含' in condition:
            keyword = condition.replace('包含', '').strip()
            result = keyword in str(value)
        elif '等于' in condition:
            keyword = condition.replace('等于', '').strip()
            result = str(value) == keyword
        else:
            result = bool(value)

        return {
            'output': 'true' if result else 'false',
            'branch': 'true' if result else 'false',
            'success': True
        }

    def execute_node(self, node_type: str, node_config: dict, input_data: dict) -> dict:
        """根据节点类型执行"""
        executors = {
            'llm': self.run_llm_node,
            'prompt': self.run_prompt_node,
            'condition': self.run_condition_node,
        }

        executor = executors.get(node_type)
        if executor:
            return executor(node_config, input_data)

        return {
            'output': input_data,
            'success': True
        }


# 全局单例
langchain_service = LangChainService()
```

### 8.3 创建工作流执行器

创建 `Backend/workflow/services/workflow_executor.py`：

```python
from ..models import Workflow, Node, Edge, WorkflowExecution
from .langchain_service import langchain_service
from django.utils import timezone
from collections import defaultdict


class WorkflowExecutor:
    """工作流执行器"""

    def __init__(self, workflow: Workflow, execution: WorkflowExecution):
        self.workflow = workflow
        self.execution = execution
        self.node_results = {}
        self.context = {}

    def build_graph(self):
        """构建工作流图"""
        nodes = self.workflow.nodes.all()
        edges = self.workflow.edges.all()

        # 构建邻接表
        graph = defaultdict(list)
        for edge in edges:
            graph[edge.source_node_id].append(edge.target_node_id)

        # 构建节点映射
        node_map = {node.id: node for node in nodes}

        return graph, node_map

    def find_start_node(self):
        """找到开始节点"""
        return self.workflow.nodes.filter(node_type='start').first()

    def get_next_nodes(self, current_node_id):
        """获取下一个节点"""
        outgoing = self.workflow.edges.filter(source_node=current_node_id)
        return [e.target_node for e in outgoing]

    def execute_node(self, node):
        """执行单个节点"""
        print(f"执行节点: {node.name} ({node.node_type})")

        # 根据节点类型执行
        result = langchain_service.execute_node(
            node.node_type,
            node.config,
            self.context
        )

        self.node_results[node.id] = result

        # 更新上下文
        if result.get('output'):
            self.context['last_output'] = result['output']

        return result

    def execute(self):
        """执行工作流"""
        self.execution.status = 'running'
        self.execution.save()

        try:
            # 构建图
            graph, node_map = self.build_graph()

            # 获取开始节点
            start_node = self.find_start_node()
            if not start_node:
                raise Exception("工作流没有开始节点")

            # 初始化上下文
            self.context = self.execution.input_data.copy()

            # BFS 执行
            queue = [start_node]
            visited = set()

            while queue:
                current_node = queue.pop(0)

                if current_node.id in visited:
                    continue

                visited.add(current_node.id)

                # 执行节点
                result = self.execute_node(current_node)

                if not result.get('success', True):
                    raise Exception(f"节点 {current_node.name} 执行失败")

                # 找到下一个节点
                next_nodes = self.get_next_nodes(current_node.id)

                # 条件判断
                if current_node.node_type == 'condition':
                    branch = result.get('branch', 'true')
                    next_nodes = [n for n in next_nodes if
                                   (branch == 'true' and 'true' in str(n.config)) or
                                   (branch == 'false' and 'false' in str(n.config)) or
                                   not ('true' in str(n.config) or 'false' in str(n.config))]

                queue.extend(next_nodes)

            # 更新执行记录
            self.execution.status = 'completed'
            self.execution.output_data = self.context
            self.execution.completed_at = timezone.now()

        except Exception as e:
            self.execution.status = 'failed'
            self.execution.error_message = str(e)

        self.execution.save()
        return self.execution


def execute_workflow(workflow_id: int, input_data: dict) -> WorkflowExecution:
    """执行工作流的入口函数"""
    workflow = Workflow.objects.get(id=workflow_id)
    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        status='pending',
        input_data=input_data
    )

    executor = WorkflowExecutor(workflow, execution)
    return executor.execute()
```

### 8.4 更新视图支持真实执行

编辑 `workflow/views.py`，更新 execute 方法：

```python
from .services.workflow_executor import execute_workflow

class WorkflowViewSet(viewsets.ModelViewSet):
    # ... 保持原有代码 ...

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行工作流"""
        workflow = self.get_object()
        input_data = request.data.get('input_data', {})

        # 执行工作流（异步更好，这里先用同步）
        execution = execute_workflow(workflow.id, input_data)

        return Response({
            'execution_id': execution.id,
            'status': execution.status,
            'output_data': execution.output_data,
            'error_message': execution.error_message
        })
```

---

## Step 9 - 工作流核心功能

### 9.1 添加节点模板

为不同类型的节点创建预设模板：

```python
# 在 models.py 中添加

class NodeTemplate(models.Model):
    """节点模板"""
    node_type = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField()
    default_config = models.JSONField()
    is_system = models.BooleanField(default=False)

    class Meta:
        db_table = 'node_templates'
```

### 9.2 实现节点验证

创建 `workflow/services/validation.py`：

```python
class NodeValidator:
    """节点验证器"""

    @staticmethod
    def validate_llm_config(config: dict) -> tuple[bool, str]:
        """验证 LLM 节点配置"""
        if 'prompt' not in config:
            return False, "LLM 节点需要配置 prompt"
        if not config['prompt'].strip():
            return False, "prompt 不能为空"
        return True, ""

    @staticmethod
    def validate_workflow(workflow) -> tuple[bool, list]:
        """验证工作流"""
        errors = []

        # 检查是否有开始节点
        start_nodes = workflow.nodes.filter(node_type='start')
        if not start_nodes.exists():
            errors.append("工作流必须有一个开始节点")

        # 检查是否有结束节点
        end_nodes = workflow.nodes.filter(node_type='end')
        if not end_nodes.exists():
            errors.append("工作流必须有一个结束节点")

        # 检查孤立节点
        connected_nodes = set()
        for edge in workflow.edges.all():
            connected_nodes.add(edge.source_node_id)
            connected_nodes.add(edge.target_node_id)

        for node in workflow.nodes.all():
            if node.id not in connected_nodes and node.node_type not in ['start', 'end']:
                errors.append(f"节点 '{node.name}' 没有连接到任何其他节点")

        return len(errors) == 0, errors
```

---

## Step 9.5 - 前后端数据库完整交互系统

> 本章节详细阐述前后端与数据库的完整交互流程，包括 API 设计、数据流转、状态管理、实时同步等核心机制。

### 9.5.1 系统交互架构

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FLOWLY 完整数据交互架构                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Vue 3 前端                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   Views     │  │  Composables │  │   Stores   │  │   Router    │                  │
│  │  (页面组件)  │  │ (业务逻辑)   │  │ (Pinia)    │  │  (路由守卫)  │                  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘                  │
│         │                │                │                                             │
│         └────────────────┼────────────────┘                                             │
│                          ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                          API Services (src/api/)                              │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │workflow.js │  │  agent.js  │  │  auth.js   │  │ nl-workflow.js│            │    │
│  │  │ (CRUD+执行)│  │ (对话+工具) │  │ (登录注册) │  │ (NL生成)    │              │    │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘              │    │
│  └────────┼────────────────┼────────────────┼────────────────┼──────────────────────┘    │
│           │                │                │                │                         │
│           └────────────────┴────────────────┴────────────────┘                         │
│                                    │                                                   │
│                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Axios HTTP Client (src/api/index.js)                      │    │
│  │   • 请求拦截器 (Token注入)  • 响应拦截器 (错误处理)  • 统一错误提示            │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ HTTP/REST + WebSocket
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Django 后端                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                         Middleware Layer (中间件层)                            │    │
│  │   • CORS  • 认证  • 限流  • 日志  • 请求ID追踪                               │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                                   │
│                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                         API View Layer (API视图层)                            │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │ views.py   │  │ views.py   │  │ views.py   │  │ views.py   │              │    │
│  │  │ WorkflowAPI│  │ AgentAPI   │  │ AuthAPI    │  │NL→Workflow │              │    │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘              │    │
│  └────────┼────────────────┼────────────────┼────────────────┼──────────────────────┘    │
│           │                │                │                │                         │
│           └────────────────┴────────────────┴────────────────┘                         │
│                                    │                                                   │
│                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Serializer Layer (序列化器层)                              │    │
│  │   • 请求验证  • 数据转换  • 嵌套序列化  • 关联对象展开                         │    │
│  │   • WorkflowSerializer  • NodeSerializer  • ExecutionSerializer                │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                                   │
│                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Service Layer (业务逻辑层)                                 │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │WorkflowSvc │  │ ExecutorSvc │  │ AgentSvc   │  │ AuditSvc    │              │    │
│  │  │(工作流服务)│  │ (执行服务)  │  │(Agent服务) │  │(审计服务)   │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘              │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                                   │
│                                    ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Model Layer (数据模型层)                                   │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │  Workflow  │  │    Node    │  │   Edge     │  │ Execution  │              │    │
│  │  │  (工作流)  │  │   (节点)   │  │   (连线)   │  │  (执行记录) │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘              │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ SQL
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     MySQL 数据库                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                         Database Schema (数据库结构)                           │    │
│  │   • Workflows (工作流表)  • Nodes (节点表)  • Edges (连线表)                   │    │
│  │   • Executions (执行表)  • AuditLogs (审计表)  • Variables (变量表)            │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                         Connection Pool (连接池)                              │    │
│  │   • MySQL Connector/Python  • 连接复用  • 事务管理  • 读写分离                  │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.5.2 前后端数据模型对应关系

#### 9.5.2.1 工作流数据流

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              工作流数据流转完整链路                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────┐         ┌────────────────┐         ┌────────────────┐
    │  前端 Vue 组件  │         │   前端 Store   │         │   前端 API     │
    │ WorkflowEditor │         │  workflowStore │         │ workflow.js    │
    └────────┬───────┘         └────────┬───────┘         └────────┬───────┘
             │                          │                          │
             │ 用户拖拽/编辑节点          │ 调用 actions             │ 调用 HTTP
             ▼                          ▼                          ▼
    ┌────────────────┐         ┌────────────────┐         ┌────────────────┐
    │ VueFlow Canvas │ ──────▶ │ setNodes([])   │ ──────▶ │ POST /api/     │
    │ (画布状态)     │         │ setEdges([])   │         │  workflows/    │
    └────────────────┘         └────────────────┘         └────────┬───────┘
                                                                       │
                                                                       │ JSON Payload
                                                                       ▼
    ┌────────────────┐         ┌────────────────┐         ┌────────────────┐
    │  MySQL nodes   │         │  Django Model  │         │  DRF Serializer │
    │  表存储        │ ◀────── │ Workflow/Node  │ ◀────── │ WorkflowSer    │
    └────────┬───────┘         └────────┬───────┘         └────────┬───────┘
             │                          │                          │
             │ SELECT                   │ ORM Query                │ validate()
             │                          ▼                          │
             │              ┌────────────────┐                      │
             └─────────────▶│  ViewSet       │◀─────────────────────┘
                            │ list/create   │
                            └───────┬────────┘
                                    │
                                    ▼
                            ┌────────────────┐
                            │ HTTP Response  │
                            │ (JSON)         │
                            └───────┬────────┘
                                    │
                                    │ 返回给前端
                                    ▼
                            ┌────────────────┐
                            │ Pinia Store    │
                            │ 更新 state     │
                            └───────┬────────┘
                                    │
                                    ▼
                            ┌────────────────┐
                            │ Vue 组件响应式  │
                            │ 更新 UI        │
                            └────────────────┘
```

#### 9.5.2.2 数据库表与前端模型对应表

| 数据库表 | Django 模型 | 前端 TypeScript 类型 | 说明 |
|---------|------------|---------------------|------|
| `workflows` | `Workflow` | `Workflow` | 工作流主表 |
| `nodes` | `Node` | `WorkflowNode` | 节点表 |
| `edges` | `Edge` | `WorkflowEdge` | 连线表 |
| `workflow_executions` | `WorkflowExecution` | `Execution` | 执行记录表 |
| `node_executions` | `NodeExecution` | `NodeExecution` | 节点执行表 |
| `execution_logs` | `ExecutionLog` | `LogEntry` | 日志表 |
| `users` (Django) | `User` | `User` | 用户表 |
| `tenants` | `Tenant` | `Tenant` | 租户表 |

### 9.5.3 前端 API 层设计

#### 9.5.3.1 Axios 封装 (`Frontend/src/api/index.js`)

```javascript
/**
 * Flowly API Client
 * 封装 HTTP 请求，提供统一的错误处理、请求拦截、响应拦截
 */

import axios from 'axios'
import { ElMessage, ElNotification } from 'element-plus'

// 创建 Axios 实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 添加请求 ID 用于追踪
    config.headers['X-Request-ID'] = generateRequestId()
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const { response, config } = error
    
    // 处理不同状态码
    switch (response?.status) {
      case 400:
        handleValidationError(response.data)
        break
      case 401:
        handleUnauthorized()
        break
      case 403:
        ElMessage.error('权限不足，无法访问该资源')
        break
      case 404:
        ElMessage.error('请求的资源不存在')
        break
      case 429:
        ElMessage.warning('请求过于频繁，请稍后再试')
        break
      case 500:
        ElMessage.error('服务器内部错误，请联系管理员')
        break
      default:
        ElMessage.error(response?.data?.message || '网络请求失败')
    }
    
    return Promise.reject(error)
  }
)

// 辅助函数
function generateRequestId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function handleValidationError(data) {
  if (data.errors) {
    const messages = Object.values(data.errors).flat().join(', ')
    ElMessage.error(`数据验证失败: ${messages}`)
  } else if (data.message) {
    ElMessage.error(data.message)
  }
}

function handleUnauthorized() {
  ElMessage.error('登录已过期，请重新登录')
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

// 导出 API 客户端
export default apiClient

// 导出请求方法
export const request = {
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  patch: (url, data, config) => apiClient.patch(url, data, config),
  delete: (url, config) => apiClient.delete(url, config)
}
```

#### 9.5.3.2 工作流 API 服务 (`Frontend/src/api/workflow.js`)

```javascript
/**
 * 工作流 API 服务
 * 提供工作流的 CRUD 和执行功能
 */

import { request } from './index'

// ============ 工作流 CRUD ============

/**
 * 获取工作流列表
 * @param {Object} params - 查询参数
 * @returns {Promise<{results: Workflow[], count: number}>}
 */
export function getWorkflowList(params = {}) {
  return request.get('/workflows/', { params })
}

/**
 * 获取工作流详情
 * @param {string} id - 工作流 ID
 * @returns {Promise<Workflow>}
 */
export function getWorkflowDetail(id) {
  return request.get(`/workflows/${id}/`)
}

/**
 * 创建工作流
 * @param {Object} data - 工作流数据
 * @returns {Promise<Workflow>}
 */
export function createWorkflow(data) {
  return request.post('/workflows/', data)
}

/**
 * 更新工作流
 * @param {string} id - 工作流 ID
 * @param {Object} data - 更新数据
 * @returns {Promise<Workflow>}
 */
export function updateWorkflow(id, data) {
  return request.put(`/workflows/${id}/`, data)
}

/**
 * 删除工作流
 * @param {string} id - 工作流 ID
 */
export function deleteWorkflow(id) {
  return request.delete(`/workflows/${id}/`)
}

/**
 * 复制工作流
 * @param {string} id - 源工作流 ID
 * @param {string} newName - 新名称
 */
export function duplicateWorkflow(id, newName) {
  return request.post(`/workflows/${id}/duplicate/`, { name: newName })
}

// ============ 节点操作 ============

/**
 * 添加节点
 * @param {string} workflowId - 工作流 ID
 * @param {Object} nodeData - 节点数据
 */
export function addNode(workflowId, nodeData) {
  return request.post(`/workflows/${workflowId}/nodes/`, nodeData)
}

/**
 * 更新节点
 * @param {string} workflowId - 工作流 ID
 * @param {string} nodeId - 节点 ID
 * @param {Object} nodeData - 节点数据
 */
export function updateNode(workflowId, nodeId, nodeData) {
  return request.put(`/workflows/${workflowId}/nodes/${nodeId}/`, nodeData)
}

/**
 * 删除节点
 * @param {string} workflowId - 工作流 ID
 * @param {string} nodeId - 节点 ID
 */
export function deleteNode(workflowId, nodeId) {
  return request.delete(`/workflows/${workflowId}/nodes/${nodeId}/`)
}

/**
 * 批量更新节点位置
 * @param {string} workflowId - 工作流 ID
 * @param {Array} nodes - 节点位置数组
 */
export function updateNodesPosition(workflowId, nodes) {
  return request.patch(`/workflows/${workflowId}/nodes/position/`, { nodes })
}

// ============ 连线操作 ============

/**
 * 添加连线
 * @param {string} workflowId - 工作流 ID
 * @param {Object} edgeData - 连线数据
 */
export function addEdge(workflowId, edgeData) {
  return request.post(`/workflows/${workflowId}/edges/`, edgeData)
}

/**
 * 更新连线
 * @param {string} workflowId - 工作流 ID
 * @param {string} edgeId - 连线 ID
 * @param {Object} edgeData - 连线数据
 */
export function updateEdge(workflowId, edgeId, edgeData) {
  return request.put(`/workflows/${workflowId}/edges/${edgeId}/`, edgeData)
}

/**
 * 删除连线
 * @param {string} workflowId - 工作流 ID
 * @param {string} edgeId - 连线 ID
 */
export function deleteEdge(workflowId, edgeId) {
  return request.delete(`/workflows/${workflowId}/edges/${edgeId}/`)
}

// ============ 工作流执行 ============

/**
 * 执行工作流
 * @param {string} workflowId - 工作流 ID
 * @param {Object} inputData - 输入数据
 * @returns {Promise<Execution>}
 */
export function executeWorkflow(workflowId, inputData) {
  return request.post(`/workflows/${workflowId}/execute/`, { input_data: inputData })
}

/**
 * 获取执行状态
 * @param {string} executionId - 执行 ID
 */
export function getExecutionStatus(executionId) {
  return request.get(`/executions/${executionId}/`)
}

/**
 * 获取执行日志
 * @param {string} executionId - 执行 ID
 * @param {Object} params - 查询参数
 */
export function getExecutionLogs(executionId, params = {}) {
  return request.get(`/executions/${executionId}/logs/`, { params })
}

/**
 * 取消执行
 * @param {string} executionId - 执行 ID
 */
export function cancelExecution(executionId) {
  return request.post(`/executions/${executionId}/cancel/`)
}

/**
 * 获取执行历史
 * @param {string} workflowId - 工作流 ID
 * @param {Object} params - 查询参数
 */
export function getExecutionHistory(workflowId, params = {}) {
  return request.get(`/workflows/${workflowId}/executions/`, { params })
}

// ============ 版本管理 ============

/**
 * 发布工作流
 * @param {string} workflowId - 工作流 ID
 */
export function publishWorkflow(workflowId) {
  return request.post(`/workflows/${workflowId}/publish/`)
}

/**
 * 获取版本列表
 * @param {string} workflowId - 工作流 ID
 */
export function getWorkflowVersions(workflowId) {
  return request.get(`/workflows/${workflowId}/versions/`)
}

/**
 * 回滚到指定版本
 * @param {string} workflowId - 工作流 ID
 * @param {string} versionId - 版本 ID
 */
export function rollbackWorkflow(workflowId, versionId) {
  return request.post(`/workflows/${workflowId}/rollback/`, { version_id: versionId })
}

// ============ 导入导出 ============

/**
 * 导出工作流 JSON
 * @param {string} workflowId - 工作流 ID
 */
export async function exportWorkflow(workflowId) {
  const response = await request.get(`/workflows/${workflowId}/export/`, {
    responseType: 'blob'
  })
  return response
}

/**
 * 导入工作流 JSON
 * @param {File} file - 工作流文件
 */
export function importWorkflow(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/workflows/import/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
```

#### 9.5.3.3 Agent API 服务 (`Frontend/src/api/agent.js`)

```javascript
/**
 * Agent API 服务
 * 提供 Agent 的 CRUD 和对话功能
 */

import { request } from './index'

// ============ Agent 管理 ============

/**
 * 获取 Agent 列表
 */
export function getAgentList(params = {}) {
  return request.get('/agents/', { params })
}

/**
 * 获取 Agent 详情
 */
export function getAgentDetail(id) {
  return request.get(`/agents/${id}/`)
}

/**
 * 创建 Agent
 */
export function createAgent(data) {
  return request.post('/agents/', data)
}

/**
 * 更新 Agent
 */
export function updateAgent(id, data) {
  return request.put(`/agents/${id}/`, data)
}

/**
 * 删除 Agent
 */
export function deleteAgent(id) {
  return request.delete(`/agents/${id}/`)
}

// ============ Agent 对话 ============

/**
 * 发送消息（普通模式）
 * @param {string} agentId - Agent ID
 * @param {Object} message - 消息内容
 */
export function sendMessage(agentId, message) {
  return request.post(`/agents/${agentId}/chat/`, message)
}

/**
 * 发送消息（流式模式）
 * @param {string} agentId - Agent ID
 * @param {Object} message - 消息内容
 * @param {Function} onChunk - 流式数据回调
 */
export function sendMessageStream(agentId, message, onChunk) {
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(
      `${import.meta.env.VITE_API_BASE_URL}/agents/${agentId}/chat/stream/`
    )
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'chunk') {
          onChunk(data.content)
        } else if (data.type === 'done') {
          eventSource.close()
          resolve(data)
        }
      } catch (e) {
        reject(e)
      }
    }
    
    eventSource.onerror = (error) => {
      eventSource.close()
      reject(error)
    }
  })
}

// ============ 工具管理 ============

/**
 * 获取可用工具列表
 */
export function getToolList(params = {}) {
  return request.get('/tools/', { params })
}

/**
 * 获取工具详情
 */
export function getToolDetail(id) {
  return request.get(`/tools/${id}/`)
}

/**
 * 创建自定义工具
 */
export function createTool(data) {
  return request.post('/tools/', data)
}

/**
 * 测试工具
 */
export function testTool(id, inputData) {
  return request.post(`/tools/${id}/test/`, { input: inputData })
}

// ============ 凭证管理 ============

/**
 * 获取凭证列表
 */
export function getCredentialList(params = {}) {
  return request.get('/credentials/', { params })
}

/**
 * 创建凭证
 */
export function createCredential(data) {
  return request.post('/credentials/', data)
}

/**
 * 删除凭证
 */
export function deleteCredential(id) {
  return request.delete(`/credentials/${id}/`)
}

/**
 * 验证凭证
 */
export function validateCredential(id) {
  return request.post(`/credentials/${id}/validate/`)
}
```

### 9.5.4 前端类型定义 (`Frontend/src/types/`)

#### 9.5.4.1 工作流类型定义

```typescript
/**
 * Flowly 前端类型定义
 * 与后端 Django 模型一一对应
 */

// ============ 工作流类型 ============

/**
 * 工作流节点类型枚举
 */
export type NodeType = 
  | 'start' 
  | 'end' 
  | 'llm' 
  | 'prompt' 
  | 'tool' 
  | 'condition' 
  | 'input' 
  | 'output'
  | 'code'
  | 'loop'
  | 'http_request'
  | 'data_transform'
  | 'email'
  | 'webhook'
  | 'template'
  | 'variable'
  | 'rag'

/**
 * 工作流状态
 */
export type WorkflowStatus = 'draft' | 'published' | 'archived'

/**
 * 工作流
 */
export interface Workflow {
  id: string
  name: string
  description?: string
  version: number
  status: WorkflowStatus
  category?: string
  tags?: string[]
  config?: WorkflowConfig
  
  // 统计信息
  total_executions: number
  successful_executions: number
  failed_executions: number
  avg_execution_time_ms?: number
  last_executed_at?: string
  
  // 关系
  owner: number
  owner_name: string
  tenant?: string
  
  // 时间戳
  created_at: string
  updated_at: string
  
  // 嵌套数据
  nodes?: WorkflowNode[]
  edges?: WorkflowEdge[]
}

/**
 * 工作流配置
 */
export interface WorkflowConfig {
  timeout_seconds?: number
  max_concurrent_nodes?: number
  retry_on_failure?: boolean
  variables?: Record<string, any>
}

/**
 * 工作流创建/更新请求
 */
export interface WorkflowCreateRequest {
  name: string
  description?: string
  category?: string
  tags?: string[]
  config?: WorkflowConfig
  nodes?: WorkflowNodeCreate[]
  edges?: WorkflowEdgeCreate[]
}

// ============ 节点类型 ============

/**
 * 工作流节点
 */
export interface WorkflowNode {
  id: string
  workflow: string
  node_type: NodeType
  name: string
  description?: string
  
  // 位置
  position_x: number
  position_y: number
  width?: number
  height?: number
  
  // 配置
  config?: NodeConfig
  input_schema?: JSONSchema
  output_schema?: JSONSchema
  
  // 错误处理
  error_handling: 'stop' | 'skip' | 'retry' | 'fallback'
  max_retries: number
  retry_delay_seconds: number
  
  // 条件
  condition_expression?: string
  
  // 执行控制
  is_enabled: boolean
  timeout_seconds?: number
  
  version: number
  created_at: string
  updated_at: string
}

/**
 * 节点配置（不同类型有不同配置）
 */
export interface NodeConfig {
  // LLM 节点配置
  model?: string
  provider?: string
  temperature?: number
  max_tokens?: number
  system_prompt?: string
  messages?: Message[]
  
  // 工具节点配置
  tool_id?: string
  tool_params?: Record<string, any>
  
  // HTTP 请求配置
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  url?: string
  headers?: Record<string, string>
  body?: any
  
  // 代码节点配置
  language?: string
  code?: string
  
  // 条件节点配置
  conditions?: Condition[]
  
  // Prompt 节点配置
  template?: string
  variables?: string[]
  
  [key: string]: any
}

/**
 * 消息格式
 */
export interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  name?: string
}

/**
 * 条件定义
 */
export interface Condition {
  field: string
  operator: 'equals' | 'not_equals' | 'contains' | 'gt' | 'lt' | 'gte' | 'lte'
  value: any
  output?: string
}

/**
 * JSON Schema
 */
export interface JSONSchema {
  type: string
  properties?: Record<string, any>
  required?: string[]
  items?: any
}

/**
 * 节点创建请求
 */
export interface WorkflowNodeCreate {
  node_type: NodeType
  name: string
  description?: string
  position_x: number
  position_y: number
  config?: NodeConfig
}

// ============ 连线类型 ============

/**
 * 工作流连线
 */
export interface WorkflowEdge {
  id: string
  workflow: string
  source_node: string
  source_handle: string
  target_node: string
  target_handle: string
  label?: string
  style?: EdgeStyle
  condition_expression?: string
  condition_priority: number
  animated: boolean
  created_at: string
  updated_at: string
}

/**
 * 连线样式
 */
export interface EdgeStyle {
  stroke?: string
  strokeWidth?: number
  strokeDasharray?: string
}

/**
 * 连线创建请求
 */
export interface WorkflowEdgeCreate {
  source_node: string
  source_handle?: string
  target_node: string
  target_handle?: string
  label?: string
  condition_expression?: string
}

// ============ 执行类型 ============

/**
 * 执行状态
 */
export type ExecutionStatus = 
  | 'queued' 
  | 'running' 
  | 'completed' 
  | 'failed' 
  | 'cancelled' 
  | 'timeout'

/**
 * 触发类型
 */
export type TriggerType = 'manual' | 'scheduled' | 'webhook' | 'api' | 'event'

/**
 * 工作流执行记录
 */
export interface Execution {
  id: string
  workflow: string
  workflow_name?: string
  version: number
  trigger_type: TriggerType
  trigger_config?: any
  status: ExecutionStatus
  input_data?: any
  output_data?: any
  
  // 统计
  total_nodes?: number
  executed_nodes?: number
  skipped_nodes?: number
  failed_nodes?: number
  
  // 时间
  queued_at: string
  started_at?: string
  completed_at?: string
  duration_ms?: number
  
  // 错误
  error_message?: string
  error_stack?: string
  
  // 成本
  token_usage?: TokenUsage
  cost_amount?: number
  cost_currency?: string
  
  // 用户信息
  user?: number
  tenant?: string
  
  context_data?: any
  created_at: string
}

/**
 * Token 使用量
 */
export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

/**
 * 节点执行记录
 */
export interface NodeExecution {
  id: string
  execution: string
  node: string
  node_version: number
  status: ExecutionStatus
  input_data?: any
  output_data?: any
  started_at?: string
  completed_at?: string
  duration_ms?: number
  error_message?: string
  retry_count: number
  max_retries_exceeded: boolean
  model_name?: string
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  cache_hit: boolean
}

/**
 * 执行日志
 */
export interface LogEntry {
  id: number
  execution: string
  node_execution?: string
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
  message: string
  metadata?: any
  source?: string
  node?: string
  node_name?: string
  timestamp: string
}

// ============ 工具类型 ============

/**
 * 工具定义
 */
export interface Tool {
  id: string
  name: string
  display_name?: string
  description?: string
  category?: string
  tool_type: 'builtin' | 'custom' | 'api' | 'script'
  definition: ToolDefinition
  input_schema?: JSONSchema
  output_schema?: JSONSchema
  auth_type?: 'none' | 'api_key' | 'oauth2' | 'basic' | 'bearer'
  credential_id?: string
  timeout_seconds: number
  is_enabled: boolean
  is_public: boolean
  usage_count: number
  avg_execution_time_ms?: number
}

/**
 * 工具定义
 */
export interface ToolDefinition {
  name: string
  description: string
  parameters: JSONSchema
  returns?: JSONSchema
}

// ============ Agent 类型 ============

/**
 * Agent
 */
export interface Agent {
  id: string
  name: string
  description?: string
  instructions: string
  model?: string
  provider?: string
  tools?: string[]
  workflow_id?: string
  is_active: boolean
  avatar_url?: string
  created_at: string
  updated_at: string
}

/**
 * 对话消息
 */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  name?: string
  tool_calls?: ToolCall[]
  tool_call_id?: string
}

/**
 * 工具调用
 */
export interface ToolCall {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}
```

### 9.5.5 Pinia 状态管理 (`Frontend/src/stores/`)

#### 9.5.5.1 工作流 Store (`Frontend/src/stores/workflow.js`)

```javascript
/**
 * 工作流状态管理
 * 使用 Pinia 管理工作流相关状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as workflowApi from '@/api/workflow'

export const useWorkflowStore = defineStore('workflow', () => {
  // ============ State ============
  
  // 工作流列表
  const workflows = ref([])
  const totalWorkflows = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  
  // 当前工作流
  const currentWorkflow = ref(null)
  
  // 节点和连线（用于编辑器）
  const nodes = ref([])
  const edges = ref([])
  
  // 执行相关
  const executions = ref([])
  const currentExecution = ref(null)
  const executionLogs = ref([])
  
  // 加载状态
  const loading = ref(false)
  const executing = ref(false)
  
  // 错误状态
  const error = ref(null)
  
  // ============ Getters ============
  
  const hasUnsavedChanges = computed(() => {
    if (!currentWorkflow.value) return false
    // 比较当前状态与保存状态
    return JSON.stringify(nodes.value) !== JSON.stringify(currentWorkflow.value.nodes)
  })
  
  const nodeCount = computed(() => nodes.value.length)
  
  const edgeCount = computed(() => edges.value.length)
  
  const startNode = computed(() => 
    nodes.value.find(n => n.node_type === 'start')
  )
  
  const endNodes = computed(() => 
    nodes.value.filter(n => n.node_type === 'end')
  )
  
  const executionStats = computed(() => ({
    total: currentWorkflow.value?.total_executions || 0,
    successful: currentWorkflow.value?.successful_executions || 0,
    failed: currentWorkflow.value?.failed_executions || 0,
    successRate: currentWorkflow.value?.total_executions
      ? (currentWorkflow.value.successful_executions / currentWorkflow.value.total_executions * 100).toFixed(1)
      : '0'
  }))

  // ============ Actions ============
  
  /**
   * 获取工作流列表
   */
  async function fetchWorkflows(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await workflowApi.getWorkflowList({
        page: currentPage.value,
        page_size: pageSize.value,
        ...params
      })
      workflows.value = response.results
      totalWorkflows.value = response.count
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 获取工作流详情
   */
  async function fetchWorkflowDetail(id) {
    loading.value = true
    error.value = null
    try {
      const workflow = await workflowApi.getWorkflowDetail(id)
      currentWorkflow.value = workflow
      // 同步节点和连线
      nodes.value = workflow.nodes || []
      edges.value = workflow.edges || []
      return workflow
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 创建工作流
   */
  async function createWorkflow(data) {
    loading.value = true
    error.value = null
    try {
      const workflow = await workflowApi.createWorkflow(data)
      workflows.value.unshift(workflow)
      totalWorkflows.value++
      return workflow
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 更新工作流
   */
  async function updateWorkflow(id, data) {
    loading.value = true
    error.value = null
    try {
      const workflow = await workflowApi.updateWorkflow(id, data)
      // 更新列表中的数据
      const index = workflows.value.findIndex(w => w.id === id)
      if (index !== -1) {
        workflows.value[index] = workflow
      }
      // 更新当前工作流
      if (currentWorkflow.value?.id === id) {
        currentWorkflow.value = workflow
      }
      return workflow
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 删除工作流
   */
  async function deleteWorkflow(id) {
    loading.value = true
    error.value = null
    try {
      await workflowApi.deleteWorkflow(id)
      workflows.value = workflows.value.filter(w => w.id !== id)
      totalWorkflows.value--
      if (currentWorkflow.value?.id === id) {
        currentWorkflow.value = null
        nodes.value = []
        edges.value = []
      }
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  // ============ 节点操作 ============
  
  /**
   * 添加节点
   */
  function addNode(nodeData) {
    const newNode = {
      id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      workflow: currentWorkflow.value?.id,
      ...nodeData,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    nodes.value.push(newNode)
    return newNode
  }
  
  /**
   * 更新节点
   */
  function updateNode(nodeId, updates) {
    const index = nodes.value.findIndex(n => n.id === nodeId)
    if (index !== -1) {
      nodes.value[index] = {
        ...nodes.value[index],
        ...updates,
        updated_at: new Date().toISOString()
      }
    }
  }
  
  /**
   * 删除节点
   */
  function removeNode(nodeId) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    // 同时删除相关的连线
    edges.value = edges.value.filter(
      e => e.source_node !== nodeId && e.target_node !== nodeId
    )
  }
  
  /**
   * 批量更新节点位置
   */
  function updateNodesPosition(positions) {
    positions.forEach(pos => {
      const node = nodes.value.find(n => n.id === pos.id)
      if (node) {
        node.position_x = pos.position_x
        node.position_y = pos.position_y
      }
    })
  }
  
  // ============ 连线操作 ============
  
  /**
   * 添加连线
   */
  function addEdge(edgeData) {
    // 检查是否已存在相同的连线
    const exists = edges.value.some(
      e => e.source_node === edgeData.source_node 
        && e.target_node === edgeData.target_node
    )
    if (exists) {
      throw new Error('连线已存在')
    }
    
    const newEdge = {
      id: `edge_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      workflow: currentWorkflow.value?.id,
      source_handle: 'default',
      target_handle: 'default',
      animated: false,
      ...edgeData,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    edges.value.push(newEdge)
    return newEdge
  }
  
  /**
   * 更新连线
   */
  function updateEdge(edgeId, updates) {
    const index = edges.value.findIndex(e => e.id === edgeId)
    if (index !== -1) {
      edges.value[index] = {
        ...edges.value[index],
        ...updates,
        updated_at: new Date().toISOString()
      }
    }
  }
  
  /**
   * 删除连线
   */
  function removeEdge(edgeId) {
    edges.value = edges.value.filter(e => e.id !== edgeId)
  }
  
  // ============ 执行操作 ============
  
  /**
   * 执行工作流
   */
  async function executeWorkflow(inputData = {}) {
    if (!currentWorkflow.value?.id) {
      throw new Error('没有选中的工作流')
    }
    
    executing.value = true
    error.value = null
    try {
      const execution = await workflowApi.executeWorkflow(
        currentWorkflow.value.id,
        inputData
      )
      currentExecution.value = execution
      return execution
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      executing.value = false
    }
  }
  
  /**
   * 获取执行状态
   */
  async function fetchExecutionStatus(executionId) {
    try {
      const execution = await workflowApi.getExecutionStatus(executionId)
      if (currentExecution.value?.id === executionId) {
        currentExecution.value = execution
      }
      return execution
    } catch (e) {
      error.value = e.message
      throw e
    }
  }
  
  /**
   * 获取执行日志
   */
  async function fetchExecutionLogs(executionId, params = {}) {
    try {
      const logs = await workflowApi.getExecutionLogs(executionId, params)
      executionLogs.value = logs
      return logs
    } catch (e) {
      error.value = e.message
      throw e
    }
  }
  
  /**
   * 获取执行历史
   */
  async function fetchExecutionHistory(workflowId, params = {}) {
    try {
      const response = await workflowApi.getExecutionHistory(workflowId, params)
      executions.value = response.results || response
      return executions.value
    } catch (e) {
      error.value = e.message
      throw e
    }
  }
  
  /**
   * 取消执行
   */
  async function cancelExecution(executionId) {
    try {
      await workflowApi.cancelExecution(executionId)
      if (currentExecution.value?.id === executionId) {
        currentExecution.value.status = 'cancelled'
      }
    } catch (e) {
      error.value = e.message
      throw e
    }
  }
  
  // ============ 保存操作 ============
  
  /**
   * 保存工作流（节点和连线）
   */
  async function saveWorkflow() {
    if (!currentWorkflow.value?.id) {
      throw new Error('没有选中的工作流')
    }
    
    loading.value = true
    error.value = null
    try {
      // 构建保存数据
      const data = {
        nodes: nodes.value.map(n => ({
          id: n.id,
          node_type: n.node_type,
          name: n.name,
          description: n.description,
          position_x: n.position_x,
          position_y: n.position_y,
          config: n.config,
          error_handling: n.error_handling,
          max_retries: n.max_retries,
          condition_expression: n.condition_expression,
          is_enabled: n.is_enabled
        })),
        edges: edges.value.map(e => ({
          id: e.id,
          source_node: e.source_node,
          source_handle: e.source_handle,
          target_node: e.target_node,
          target_handle: e.target_handle,
          label: e.label,
          condition_expression: e.condition_expression,
          animated: e.animated
        }))
      }
      
      const workflow = await workflowApi.updateWorkflow(
        currentWorkflow.value.id,
        data
      )
      currentWorkflow.value = workflow
      return workflow
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 重置编辑器状态
   */
  function resetEditor() {
    nodes.value = []
    edges.value = []
    currentWorkflow.value = null
    currentExecution.value = null
    executionLogs.value = []
    error.value = null
  }
  
  return {
    // State
    workflows,
    totalWorkflows,
    currentPage,
    pageSize,
    currentWorkflow,
    nodes,
    edges,
    executions,
    currentExecution,
    executionLogs,
    loading,
    executing,
    error,
    
    // Getters
    hasUnsavedChanges,
    nodeCount,
    edgeCount,
    startNode,
    endNodes,
    executionStats,
    
    // Actions
    fetchWorkflows,
    fetchWorkflowDetail,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    addNode,
    updateNode,
    removeNode,
    updateNodesPosition,
    addEdge,
    updateEdge,
    removeEdge,
    executeWorkflow,
    fetchExecutionStatus,
    fetchExecutionLogs,
    fetchExecutionHistory,
    cancelExecution,
    saveWorkflow,
    resetEditor
  }
})
```

#### 9.5.5.2 Auth Store (`Frontend/src/stores/auth.js`)

```javascript
/**
 * 认证状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { request } from '@/api/index'

export const useAuthStore = defineStore('auth', () => {
  // ============ State ============
  
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token'))
  const refreshToken = ref(localStorage.getItem('refresh_token'))
  const permissions = ref([])
  const loading = ref(false)
  
  // ============ Getters ============
  
  const isAuthenticated = computed(() => !!token.value)
  
  const isAdmin = computed(() => 
    permissions.value.includes('admin') || user.value?.is_superuser
  )
  
  const userId = computed(() => user.value?.id)
  
  const userName = computed(() => 
    user.value?.display_name || user.value?.username
  )
  
  const userAvatar = computed(() => user.value?.avatar_url)
  
  // ============ Actions ============
  
  /**
   * 用户登录
   */
  async function login(credentials) {
    loading.value = true
    try {
      const response = await request.post('/auth/login/', credentials)
      setTokens(response.access, response.refresh)
      await fetchUserInfo()
      return response
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 用户注册
   */
  async function register(data) {
    loading.value = true
    try {
      const response = await request.post('/auth/register/', data)
      setTokens(response.access, response.refresh)
      await fetchUserInfo()
      return response
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 登出
   */
  function logout() {
    user.value = null
    token.value = null
    refreshToken.value = null
    permissions.value = []
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }
  
  /**
   * 获取用户信息
   */
  async function fetchUserInfo() {
    if (!token.value) return null
    
    try {
      const response = await request.get('/auth/me/')
      user.value = response
      permissions.value = response.permissions || []
      return response
    } catch (e) {
      logout()
      throw e
    }
  }
  
  /**
   * 刷新 Token
   */
  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('没有刷新令牌')
    }
    
    try {
      const response = await request.post('/auth/refresh/', {
        refresh: refreshToken.value
      })
      setTokens(response.access, response.refresh)
      return response.access
    } catch (e) {
      logout()
      throw e
    }
  }
  
  /**
   * 设置 Token
   */
  function setTokens(access, refresh) {
    token.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    if (refresh) {
      localStorage.setItem('refresh_token', refresh)
    }
  }
  
  /**
   * 初始化认证状态
   */
  async function initialize() {
    if (token.value) {
      try {
        await fetchUserInfo()
      } catch (e) {
        // Token 过期，尝试刷新
        if (refreshToken.value) {
          try {
            await refreshAccessToken()
            await fetchUserInfo()
          } catch (e) {
            logout()
          }
        } else {
          logout()
        }
      }
    }
  }
  
  return {
    // State
    user,
    token,
    refreshToken,
    permissions,
    loading,
    
    // Getters
    isAuthenticated,
    isAdmin,
    userId,
    userName,
    userAvatar,
    
    // Actions
    login,
    register,
    logout,
    fetchUserInfo,
    refreshAccessToken,
    initialize
  }
})
```

### 9.5.6 后端 Django API 视图

#### 9.5.6.1 工作流 ViewSet (`Backend/workflows/views.py`)

```python
"""
工作流 API 视图
提供工作流的 CRUD 和执行接口
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import (
    Workflow, Node, Edge, 
    WorkflowExecution, NodeExecution, ExecutionLog
)
from .serializers import (
    WorkflowSerializer, WorkflowDetailSerializer, WorkflowCreateSerializer,
    NodeSerializer, EdgeSerializer,
    ExecutionSerializer, ExecutionDetailSerializer,
    ExecutionLogSerializer
)
from .services import WorkflowExecutor, WorkflowService
from .permissions import IsWorkflowOwner, IsWorkflowAccessible


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    工作流 ViewSet
    提供 list, create, retrieve, update, destroy, execute 等操作
    """
    
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """返回当前用户的工作流"""
        return Workflow.objects.filter(
            owner=self.request.user,
            is_deleted=False
        ).select_related('owner').prefetch_related('nodes', 'edges')
    
    def get_serializer_class(self):
        """根据操作返回不同的序列化器"""
        if self.action == 'create':
            return WorkflowCreateSerializer
        if self.action == 'retrieve':
            return WorkflowDetailSerializer
        return WorkflowSerializer
    
    def get_permissions(self):
        """根据操作返回不同的权限"""
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsWorkflowOwner()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """创建工作流时自动设置所有者"""
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行工作流
        POST /api/workflows/{id}/execute/
        
        Request Body:
        {
            "input_data": {...}  // 可选，输入数据
        }
        """
        workflow = self.get_object()
        input_data = request.data.get('input_data', {})
        
        # 创建执行记录
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            version=workflow.version,
            trigger_type='manual',
            user=request.user,
            tenant=getattr(workflow, 'tenant', None),
            input_data=input_data,
            status='queued'
        )
        
        # 异步执行（使用 Celery）
        from .tasks import execute_workflow_task
        execute_workflow_task.delay(str(execution.id))
        
        serializer = ExecutionSerializer(execution)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        发布工作流
        POST /api/workflows/{id}/publish/
        """
        workflow = self.get_object()
        
        # 验证工作流
        errors = self._validate_workflow(workflow)
        if errors:
            return Response(
                {'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow.status = 'published'
        workflow.save()
        
        serializer = self.get_serializer(workflow)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        获取版本历史
        GET /api/workflows/{id}/versions/
        """
        workflow = self.get_object()
        versions = Workflow.objects.filter(
            parent_version=workflow.parent_version or workflow
        ).order_by('-version')
        
        serializer = WorkflowSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        复制工作流
        POST /api/workflows/{id}/duplicate/
        """
        workflow = self.get_object()
        new_name = request.data.get('name', f"{workflow.name} (副本)")
        
        # 复制工作流
        new_workflow = Workflow.objects.create(
            name=new_name,
            description=workflow.description,
            owner=request.user,
            config=workflow.config,
            status='draft'
        )
        
        # 复制节点
        node_mapping = {}
        for node in workflow.nodes.all():
            new_node = Node.objects.create(
                workflow=new_workflow,
                node_type=node.node_type,
                name=node.name,
                description=node.description,
                position_x=node.position_x,
                position_y=node.position_y,
                config=node.config,
                error_handling=node.error_handling,
                max_retries=node.max_retries,
                condition_expression=node.condition_expression,
                is_enabled=node.is_enabled
            )
            node_mapping[node.id] = new_node.id
        
        # 复制连线
        for edge in workflow.edges.all():
            Edge.objects.create(
                workflow=new_workflow,
                source_node_id=node_mapping.get(edge.source_node_id),
                target_node_id=node_mapping.get(edge.target_node_id),
                source_handle=edge.source_handle,
                target_handle=edge.target_handle,
                label=edge.label,
                condition_expression=edge.condition_expression
            )
        
        serializer = WorkflowSerializer(new_workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def import_workflow(self, request, pk=None):
        """
        导入工作流
        POST /api/workflows/{id}/import/
        """
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': '请上传工作流文件'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            import json
            data = json.loads(file.read())
        except json.JSONDecodeError:
            return Response(
                {'error': '无效的 JSON 文件'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = WorkflowCreateSerializer(data=data)
        if serializer.is_valid():
            workflow = serializer.save(owner=request.user)
            return Response(
                WorkflowSerializer(workflow).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'])
    def export_workflow(self, request, pk=None):
        """
        导出工作流
        GET /api/workflows/{id}/export/
        """
        workflow = self.get_object()
        
        # 构建导出数据
        data = {
            'name': workflow.name,
            'description': workflow.description,
            'version': workflow.version,
            'config': workflow.config,
            'nodes': [
                {
                    'id': str(node.id),
                    'node_type': node.node_type,
                    'name': node.name,
                    'description': node.description,
                    'position_x': float(node.position_x),
                    'position_y': float(node.position_y),
                    'config': node.config,
                    'error_handling': node.error_handling,
                    'condition_expression': node.condition_expression,
                    'is_enabled': node.is_enabled
                }
                for node in workflow.nodes.all()
            ],
            'edges': [
                {
                    'id': str(edge.id),
                    'source_node': str(edge.source_node_id),
                    'target_node': str(edge.target_node_id),
                    'source_handle': edge.source_handle,
                    'target_handle': edge.target_handle,
                    'label': edge.label,
                    'condition_expression': edge.condition_expression
                }
                for edge in workflow.edges.all()
            ]
        }
        
        return Response(data)
    
    def _validate_workflow(self, workflow):
        """验证工作流完整性"""
        errors = []
        
        # 检查是否有节点
        if not workflow.nodes.exists():
            errors.append('工作流必须包含至少一个节点')
        
        # 检查是否有开始和结束节点
        node_types = set(workflow.nodes.values_list('node_type', flat=True))
        if 'start' not in node_types:
            errors.append('工作流必须包含开始节点')
        if 'end' not in node_types:
            errors.append('工作流必须包含结束节点')
        
        # 检查节点连接
        start_nodes = workflow.nodes.filter(node_type='start')
        if start_nodes.exists():
            start_id = start_nodes.first().id
            has_outgoing = workflow.edges.filter(source_node_id=start_id).exists()
            if not has_outgoing:
                errors.append('开始节点必须连接到其他节点')
        
        return errors


class NodeViewSet(viewsets.ModelViewSet):
    """节点 ViewSet"""
    
    serializer_class = NodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        workflow_id = self.kwargs.get('workflow_pk')
        return Node.objects.filter(workflow_id=workflow_id)
    
    def perform_create(self, serializer):
        workflow_id = self.kwargs.get('workflow_pk')
        workflow = get_object_or_404(Workflow, id=workflow_id)
        serializer.save(workflow=workflow)


class EdgeViewSet(viewsets.ModelViewSet):
    """连线 ViewSet"""
    
    serializer_class = EdgeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        workflow_id = self.kwargs.get('workflow_pk')
        return Edge.objects.filter(workflow_id=workflow_id)
    
    def perform_create(self, serializer):
        workflow_id = self.kwargs.get('workflow_pk')
        workflow = get_object_or_404(Workflow, id=workflow_id)
        
        # 验证连线有效性
        source_id = serializer.validated_data.get('source_node').id
        target_id = serializer.validated_data.get('target_node').id
        
        # 不能自己连自己
        if source_id == target_id:
            raise ValidationError({'detail': '不能连接节点到自己'})
        
        # 检查是否已存在相同连线
        exists = Edge.objects.filter(
            workflow=workflow,
            source_node_id=source_id,
            target_node_id=target_id
        ).exists()
        if exists:
            raise ValidationError({'detail': '连线已存在'})
        
        serializer.save(workflow=workflow)


class ExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """执行记录 ViewSet"""
    
    serializer_class = ExecutionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WorkflowExecution.objects.filter(
            user=self.request.user
        ).select_related('workflow', 'user')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExecutionDetailSerializer
        return ExecutionSerializer
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """获取执行日志"""
        execution = self.get_object()
        logs = ExecutionLog.objects.filter(
            execution=execution
        ).order_by('timestamp')
        
        serializer = ExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消执行"""
        execution = self.get_object()
        
        if execution.status not in ['queued', 'running']:
            return Response(
                {'error': '当前状态无法取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        execution.status = 'cancelled'
        execution.save()
        
        # 如果正在运行，通知 Celery 取消任务
        if execution.celery_task_id:
            from celery_app import celery_app
            celery_app.control.revoke(execution.celery_task_id, terminate=True)
        
        serializer = self.get_serializer(execution)
        return Response(serializer.data)
```

### 9.5.7 后端序列化器 (`Backend/workflows/serializers.py`)

```python
"""
工作流序列化器
定义前后端数据交互的数据格式
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    Workflow, Node, Edge,
    WorkflowExecution, NodeExecution, ExecutionLog,
    PromptTemplate, Tool, Variable
)


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class NodeSerializer(serializers.ModelSerializer):
    """节点序列化器"""
    
    class Meta:
        model = Node
        fields = [
            'id', 'workflow', 'node_type', 'name', 'description',
            'position_x', 'position_y', 'width', 'height',
            'config', 'input_schema', 'output_schema',
            'error_handling', 'max_retries', 'retry_delay_seconds',
            'condition_expression', 'is_enabled', 'timeout_seconds',
            'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_position_x(self, value):
        if value < 0:
            raise serializers.ValidationError("X 坐标不能为负数")
        return value
    
    def validate_position_y(self, value):
        if value < 0:
            raise serializers.ValidationError("Y 坐标不能为负数")
        return value


class NodeCreateSerializer(serializers.ModelSerializer):
    """节点创建序列化器"""
    
    id = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Node
        fields = [
            'id', 'node_type', 'name', 'description',
            'position_x', 'position_y', 'config',
            'error_handling', 'max_retries', 'condition_expression',
            'is_enabled'
        ]
    
    def validate_node_type(self, value):
        allowed_types = [
            'start', 'end', 'llm', 'prompt', 'tool', 'condition',
            'input', 'output', 'code', 'loop', 'http_request',
            'data_transform', 'email', 'webhook', 'template', 'variable', 'rag'
        ]
        if value not in allowed_types:
            raise serializers.ValidationError(
                f"不支持的节点类型: {value}"
            )
        return value


class EdgeSerializer(serializers.ModelSerializer):
    """连线序列化器"""
    
    source_node_name = serializers.CharField(
        source='source_node.name', 
        read_only=True
    )
    target_node_name = serializers.CharField(
        source='target_node.name',
        read_only=True
    )
    
    class Meta:
        model = Edge
        fields = [
            'id', 'workflow', 'source_node', 'target_node',
            'source_handle', 'target_handle', 'label', 'style',
            'condition_expression', 'condition_priority', 'animated',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EdgeCreateSerializer(serializers.ModelSerializer):
    """连线创建序列化器"""
    
    id = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Edge
        fields = [
            'id', 'source_node', 'target_node',
            'source_handle', 'target_handle', 'label',
            'condition_expression', 'animated'
        ]
    
    def validate(self, data):
        source = data.get('source_node')
        target = data.get('target_node')
        
        if source == target:
            raise serializers.ValidationError({
                'detail': '不能连接节点到自己'
            })
        
        return data


class WorkflowListSerializer(serializers.ModelSerializer):
    """工作流列表序列化器"""
    
    owner_name = serializers.CharField(
        source='owner.username',
        read_only=True
    )
    node_count = serializers.SerializerMethodField()
    execution_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'owner', 'owner_name',
            'version', 'status', 'category', 'tags',
            'node_count', 'execution_count',
            'total_executions', 'successful_executions', 'failed_executions',
            'last_executed_at', 'is_public',
            'created_at', 'updated_at'
        ]
    
    def get_node_count(self, obj):
        return obj.nodes.count()
    
    def get_execution_count(self, obj):
        return obj.executions.count()


class WorkflowDetailSerializer(serializers.ModelSerializer):
    """工作流详情序列化器"""
    
    owner = UserSerializer(read_only=True)
    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(
        source='owner.username',
        read_only=True
    )
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'owner', 'owner_name',
            'version', 'status', 'category', 'tags', 'config',
            'nodes', 'edges',
            'total_executions', 'successful_executions', 'failed_executions',
            'avg_execution_time_ms', 'last_executed_at',
            'is_public', 'share_token',
            'created_at', 'updated_at'
        ]


class WorkflowCreateSerializer(serializers.ModelSerializer):
    """工作流创建序列化器"""
    
    nodes = NodeCreateSerializer(many=True, required=False, default=[])
    edges = EdgeCreateSerializer(many=True, required=False, default=[])
    
    class Meta:
        model = Workflow
        fields = [
            'name', 'description', 'category', 'tags', 'config'
        ]
    
    def validate_nodes(self, nodes):
        """验证节点数据"""
        if not nodes:
            return nodes
        
        node_types = [n.get('node_type') for n in nodes]
        
        # 检查开始节点
        if 'start' not in node_types:
            raise serializers.ValidationError('必须包含开始节点')
        
        # 检查结束节点
        if 'end' not in node_types:
            raise serializers.ValidationError('必须包含结束节点')
        
        # 检查节点名称唯一性
        names = [n.get('name') for n in nodes]
        if len(names) != len(set(names)):
            raise serializers.ValidationError('节点名称不能重复')
        
        return nodes
    
    def validate_edges(self, edges):
        """验证连线数据"""
        if not edges:
            return edges
        
        # 检查连线引用的节点是否存在
        node_ids = set()
        for edge in edges:
            node_ids.add(str(edge['source_node']))
            node_ids.add(str(edge['target_node']))
        
        for edge in edges:
            source_id = str(edge['source_node'])
            target_id = str(edge['target_node'])
            
            if source_id not in node_ids:
                raise serializers.ValidationError(
                    f"连线引用了不存在的节点: {source_id}"
                )
            if target_id not in node_ids:
                raise serializers.ValidationError(
                    f"连线引用了不存在的节点: {target_id}"
                )
        
        return edges
    
    def create(self, validated_data):
        nodes_data = validated_data.pop('nodes', [])
        edges_data = validated_data.pop('edges', [])
        
        # 创建工作流
        workflow = Workflow.objects.create(**validated_data)
        
        # 创建节点映射 (前端ID -> 数据库ID)
        node_mapping = {}
        
        for node_data in nodes_data:
            node_id = node_data.pop('id', None) or f"node_{workflow.id}_{len(node_mapping)}"
            node = Node.objects.create(
                id=node_id,
                workflow=workflow,
                **node_data
            )
            node_mapping[str(node.id)] = node
        
        # 创建连线
        for edge_data in edges_data:
            Edge.objects.create(
                workflow=workflow,
                source_node=node_mapping.get(str(edge_data['source_node'])),
                target_node=node_mapping.get(str(edge_data['target_node'])),
                source_handle=edge_data.get('source_handle', 'default'),
                target_handle=edge_data.get('target_handle', 'default'),
                label=edge_data.get('label'),
                condition_expression=edge_data.get('condition_expression'),
                animated=edge_data.get('animated', False)
            )
        
        return workflow
    
    def update(self, instance, validated_data):
        nodes_data = validated_data.pop('nodes', None)
        edges_data = validated_data.pop('edges', None)
        
        # 更新工作流基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 更新节点
        if nodes_data is not None:
            # 删除旧节点
            instance.nodes.all().delete()
            
            node_mapping = {}
            for node_data in nodes_data:
                node_id = node_data.pop('id', None)
                node = Node.objects.create(
                    id=node_id,
                    workflow=instance,
                    **node_data
                )
                node_mapping[str(node.id)] = node
            
            # 更新连线
            if edges_data is not None:
                instance.edges.all().delete()
                for edge_data in edges_data:
                    Edge.objects.create(
                        workflow=instance,
                        source_node=node_mapping.get(str(edge_data['source_node'])),
                        target_node=node_mapping.get(str(edge_data['target_node'])),
                        **edge_data
                    )
        
        return instance


class ExecutionSerializer(serializers.ModelSerializer):
    """执行记录序列化器"""
    
    workflow_name = serializers.CharField(
        source='workflow.name',
        read_only=True
    )
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'workflow_name', 'version',
            'trigger_type', 'trigger_config',
            'status', 'input_data', 'output_data',
            'total_nodes', 'executed_nodes', 'skipped_nodes', 'failed_nodes',
            'queued_at', 'started_at', 'completed_at', 'duration_ms', 'duration_formatted',
            'error_message', 'token_usage', 'cost_amount', 'cost_currency',
            'created_at'
        ]
    
    def get_duration_formatted(self, obj):
        if not obj.duration_ms:
            return None
        seconds = obj.duration_ms / 1000
        if seconds < 60:
            return f"{seconds:.2f}s"
        minutes = seconds / 60
        return f"{minutes:.2f}m"


class ExecutionDetailSerializer(ExecutionSerializer):
    """执行详情序列化器"""
    
    node_executions = serializers.SerializerMethodField()
    
    class Meta(ExecutionSerializer.Meta):
        fields = ExecutionSerializer.Meta.fields + [
            'node_executions', 'context_data'
        ]
    
    def get_node_executions(self, obj):
        return NodeExecutionSerializer(
            obj.node_executions.all(),
            many=True
        ).data


class NodeExecutionSerializer(serializers.ModelSerializer):
    """节点执行序列化器"""
    
    node_name = serializers.CharField(
        source='node.name',
        read_only=True
    )
    
    class Meta:
        model = NodeExecution
        fields = [
            'id', 'execution', 'node', 'node_name', 'node_version',
            'status', 'input_data', 'output_data',
            'started_at', 'completed_at', 'duration_ms',
            'error_message', 'retry_count', 'max_retries_exceeded',
            'model_name', 'prompt_tokens', 'completion_tokens', 'total_tokens',
            'cache_hit'
        ]


class ExecutionLogSerializer(serializers.ModelSerializer):
    """执行日志序列化器"""
    
    class Meta:
        model = ExecutionLog
        fields = [
            'id', 'execution', 'node_execution',
            'log_level', 'message', 'metadata',
            'source', 'node', 'node_name',
            'timestamp'
        ]
```

### 9.5.8 数据库操作层 (`Backend/workflows/services.py`)

```python
"""
工作流服务层
处理业务逻辑，与数据库交互
"""

from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any, Optional
import logging

from .models import (
    Workflow, Node, Edge,
    WorkflowExecution, NodeExecution, ExecutionLog,
    AuditLog
)
from .exceptions import WorkflowValidationError, ExecutionError

logger = logging.getLogger(__name__)


class WorkflowService:
    """工作流服务"""
    
    @staticmethod
    @transaction.atomic
    def create_workflow(owner, data: Dict) -> Workflow:
        """创建工作流"""
        workflow = Workflow.objects.create(
            owner=owner,
            name=data.get('name'),
            description=data.get('description'),
            category=data.get('category'),
            tags=data.get('tags'),
            config=data.get('config'),
            status='draft'
        )
        
        # 创建审计日志
        AuditLog.objects.create(
            user=owner,
            action='create',
            resource_type='workflow',
            resource_id=workflow.id,
            new_value={'name': workflow.name}
        )
        
        return workflow
    
    @staticmethod
    @transaction.atomic
    def update_workflow(workflow: Workflow, data: Dict) -> Workflow:
        """更新工作流"""
        old_values = {
            'name': workflow.name,
            'description': workflow.description
        }
        
        for field in ['name', 'description', 'category', 'tags', 'config']:
            if field in data:
                setattr(workflow, field, data[field])
        
        workflow.save()
        
        # 创建审计日志
        AuditLog.objects.create(
            user=data.get('updated_by'),
            action='update',
            resource_type='workflow',
            resource_id=workflow.id,
            old_value=old_values,
            new_value={
                'name': workflow.name,
                'description': workflow.description
            }
        )
        
        return workflow
    
    @staticmethod
    @transaction.atomic
    def delete_workflow(workflow: Workflow, user) -> None:
        """删除工作流（软删除）"""
        workflow.is_deleted = True
        workflow.deleted_at = timezone.now()
        workflow.status = 'archived'
        workflow.save()
        
        AuditLog.objects.create(
            user=user,
            action='delete',
            resource_type='workflow',
            resource_id=workflow.id
        )
    
    @staticmethod
    def validate_workflow(workflow: Workflow) -> tuple[bool, List[str]]:
        """验证工作流完整性"""
        errors = []
        
        # 检查节点数量
        nodes = list(workflow.nodes.all())
        if not nodes:
            errors.append('工作流必须包含至少一个节点')
            return False, errors
        
        # 检查开始和结束节点
        node_types = {n.id: n.node_type for n in nodes}
        
        has_start = any(t == 'start' for t in node_types.values())
        has_end = any(t == 'end' for t in node_types.values())
        
        if not has_start:
            errors.append('必须包含开始节点')
        if not has_end:
            errors.append('必须包含结束节点')
        
        # 检查节点连接
        edges = workflow.edges.all()
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.source_node_id)
            connected_nodes.add(edge.target_node_id)
        
        for node in nodes:
            if node.node_type not in ['start', 'end']:
                if node.id not in connected_nodes:
                    errors.append(f"节点 '{node.name}' 没有连接到任何其他节点")
        
        # 检查条件节点的条件表达式
        for node in nodes:
            if node.node_type == 'condition' and not node.condition_expression:
                errors.append(f"条件节点 '{node.name}' 必须指定条件表达式")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_workflow_stats(workflow: Workflow) -> Dict:
        """获取工作流统计信息"""
        executions = workflow.executions.all()
        
        return {
            'total_executions': workflow.total_executions,
            'successful_executions': workflow.successful_executions,
            'failed_executions': workflow.failed_executions,
            'avg_execution_time_ms': workflow.avg_execution_time_ms,
            'success_rate': (
                workflow.successful_executions / workflow.total_executions * 100
                if workflow.total_executions > 0 else 0
            ),
            'last_executed_at': workflow.last_executed_at
        }


class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, execution: WorkflowExecution):
        self.execution = execution
        self.workflow = execution.workflow
        self.nodes = {}
        self.edges = {}
        self.variables = {}
        self.context = execution.input_data or {}
    
    def execute(self) -> Dict:
        """执行工作流"""
        try:
            # 加载工作流数据
            self._load_workflow_data()
            
            # 更新执行状态
            self.execution.status = 'running'
            self.execution.started_at = timezone.now()
            self.execution.save()
            
            # 查找开始节点
            start_node = self._find_start_node()
            if not start_node:
                raise ExecutionError('未找到开始节点')
            
            # 执行节点
            result = self._execute_node(start_node)
            
            # 更新执行状态
            self.execution.mark_completed(result)
            self._update_workflow_stats(success=True)
            
            return result
            
        except Exception as e:
            logger.exception(f"工作流执行失败: {self.execution.id}")
            self.execution.mark_failed(str(e))
            self._update_workflow_stats(success=False)
            raise
    
    def _load_workflow_data(self):
        """加载工作流数据到内存"""
        for node in self.workflow.nodes.all():
            self.nodes[str(node.id)] = node
        
        for edge in self.workflow.edges.all():
            self.edges.setdefault(str(edge.source_node_id), []).append(edge)
    
    def _find_start_node(self) -> Optional[Node]:
        """查找开始节点"""
        for node in self.nodes.values():
            if node.node_type == 'start':
                return node
        return None
    
    def _execute_node(self, node: Node) -> Any:
        """执行单个节点"""
        # 创建节点执行记录
        node_execution = NodeExecution.objects.create(
            execution=self.execution,
            node=node,
            node_version=node.version,
            status='running',
            input_data=self.context.copy()
        )
        
        try:
            # 根据节点类型执行
            if node.node_type == 'start':
                result = self._execute_start_node(node)
            elif node.node_type == 'end':
                result = self._execute_end_node(node)
            elif node.node_type == 'llm':
                result = self._execute_llm_node(node)
            elif node.node_type == 'condition':
                result = self._execute_condition_node(node)
            elif node.node_type == 'tool':
                result = self._execute_tool_node(node)
            elif node.node_type == 'http_request':
                result = self._execute_http_node(node)
            else:
                result = self.context
            
            # 更新节点执行记录
            node_execution.output_data = result
            node_execution.status = 'completed'
            node_execution.completed_at = timezone.now()
            node_execution.duration_ms = int(
                (node_execution.completed_at - node_execution.started_at).total_seconds() * 1000
            )
            node_execution.save()
            
            # 更新上下文
            if node.node_type != 'end':
                self.context[f'node_{node.id}_output'] = result
            
            # 执行后续节点
            return self._execute_next_nodes(node, result)
            
        except Exception as e:
            node_execution.status = 'failed'
            node_execution.error_message = str(e)
            node_execution.completed_at = timezone.now()
            node_execution.save()
            
            # 根据错误处理策略处理
            return self._handle_node_error(node, e)
    
    def _execute_start_node(self, node: Node) -> Any:
        """执行开始节点"""
        ExecutionLog.objects.create(
            execution=self.execution,
            node=node,
            node_name=node.name,
            log_level='INFO',
            message=f"开始执行工作流: {self.workflow.name}"
        )
        return self.context
    
    def _execute_end_node(self, node: Node) -> Any:
        """执行结束节点"""
        ExecutionLog.objects.create(
            execution=self.execution,
            node=node,
            node_name=node.name,
            log_level='INFO',
            message="工作流执行完成"
        )
        return self.context.get('output_data', self.context)
    
    def _execute_llm_node(self, node: Node) -> Any:
        """执行 LLM 节点"""
        config = node.config or {}
        model = config.get('model')
        system_prompt = config.get('system_prompt', '')
        
        # 获取消息
        messages = config.get('messages', [])
        for msg in messages:
            if msg.get('content') == '{{input}}':
                msg['content'] = str(self.context.get('input', ''))
        
        if system_prompt:
            messages.insert(0, {'role': 'system', 'content': system_prompt})
        
        # 调用 LLM
        from ..gateway.services import LLMGateway
        gateway = LLMGateway()
        response = gateway.chat(
            model=model,
            messages=messages,
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 2000)
        )
        
        # 记录日志
        ExecutionLog.objects.create(
            execution=self.execution,
            node=node,
            node_name=node.name,
            log_level='INFO',
            message=f"LLM 调用完成，模型: {model}",
            metadata={
                'model': model,
                'tokens': response.get('usage', {})
            }
        )
        
        return response.get('content', '')
    
    def _execute_condition_node(self, node: Node) -> str:
        """执行条件节点"""
        condition_expr = node.condition_expression
        # 简单的条件评估
        try:
            result = eval(condition_expr, {"__builtins__": {}}, self.context)
            return 'true' if result else 'false'
        except Exception as e:
            raise ExecutionError(f"条件评估失败: {e}")
    
    def _execute_tool_node(self, node: Node) -> Any:
        """执行工具节点"""
        config = node.config or {}
        tool_name = config.get('tool_name')
        tool_params = config.get('params', {})
        
        # 调用工具
        from ..agents.tools import get_tool
        tool = get_tool(tool_name)
        result = tool.execute(tool_params, self.context)
        
        ExecutionLog.objects.create(
            execution=self.execution,
            node=node,
            node_name=node.name,
            log_level='INFO',
            message=f"工具执行完成: {tool_name}"
        )
        
        return result
    
    def _execute_http_node(self, node: Node) -> Any:
        """执行 HTTP 请求节点"""
        config = node.config or {}
        method = config.get('method', 'GET')
        url = config.get('url')
        headers = config.get('headers', {})
        body = config.get('body')
        
        import requests
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body,
            timeout=node.timeout_seconds or 30
        )
        
        ExecutionLog.objects.create(
            execution=self.execution,
            node=node,
            node_name=node.name,
            log_level='INFO',
            message=f"HTTP 请求完成: {method} {url}",
            metadata={'status_code': response.status_code}
        )
        
        return response.json() if response.content else {}
    
    def _execute_next_nodes(self, current_node: Node, result: Any) -> Any:
        """执行后续节点"""
        next_edges = self.edges.get(str(current_node.id), [])
        
        if not next_edges:
            return result
        
        # 查找下一个节点
        for edge in next_edges:
            next_node = self.nodes.get(str(edge.target_node_id))
            if next_node and next_node.is_enabled:
                return self._execute_node(next_node)
        
        return result
    
    def _handle_node_error(self, node: Node, error: Exception) -> Any:
        """处理节点执行错误"""
        error_msg = str(error)
        
        ExecutionLog.objects.create(
            execution=self.execution,
            node=node,
            node_name=node.name,
            log_level='ERROR',
            message=f"节点执行失败: {error_msg}",
            metadata={'error': error_msg}
        )
        
        if node.error_handling == 'stop':
            raise error
        elif node.error_handling == 'skip':
            return self._execute_next_nodes(node, None)
        elif node.error_handling == 'retry':
            if node.retry_count < node.max_retries:
                import time
                time.sleep(node.retry_delay_seconds)
                return self._execute_node(node)
            else:
                if node.max_retries_exceeded:
                    raise error
                return self._execute_next_nodes(node, None)
        elif node.error_handling == 'fallback':
            fallback_value = node.config.get('fallback_value')
            return fallback_value
        
        return None
    
    def _update_workflow_stats(self, success: bool):
        """更新工作流统计"""
        self.workflow.total_executions += 1
        if success:
            self.workflow.successful_executions += 1
        else:
            self.workflow.failed_executions += 1
        
        # 计算平均执行时间
        executions = self.workflow.executions.filter(
            status='completed',
            duration_ms__isnull=False
        )
        if executions.exists():
            avg_time = executions.aggregate(
                avg=models.Avg('duration_ms')
            )['avg']
            self.workflow.avg_execution_time_ms = int(avg_time)
        
        self.workflow.last_executed_at = timezone.now()
        self.workflow.save()
```

### 9.5.9 WebSocket 实时通信

#### 9.5.9.1 后端 WebSocket Consumer (`Backend/workflows/consumers.py`)

```python
"""
WebSocket Consumer
用于实时推送执行状态、日志等
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class WorkflowConsumer(AsyncWebsocketConsumer):
    """工作流 WebSocket Consumer"""
    
    async def connect(self):
        """建立连接"""
        self.execution_id = self.scope['url_route']['kwargs'].get('execution_id')
        self.room_group_name = f'execution_{self.execution_id}'
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 发送连接成功消息
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'execution_id': self.execution_id
        }))
    
    async def disconnect(self, close_code):
        """断开连接"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """接收消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            elif message_type == 'get_status':
                # 获取当前执行状态
                status = await self.get_execution_status()
                await self.send(text_data=json.dumps({
                    'type': 'status_update',
                    'data': status
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的 JSON 格式'
            }))
    
    async def execution_update(self, event):
        """接收执行更新"""
        await self.send(text_data=json.dumps({
            'type': 'execution_update',
            'status': event.get('status'),
            'data': event.get('data')
        }))
    
    async def node_update(self, event):
        """接收节点更新"""
        await self.send(text_data=json.dumps({
            'type': 'node_update',
            'node_id': event.get('node_id'),
            'status': event.get('status'),
            'output': event.get('output'),
            'error': event.get('error')
        }))
    
    async def log_message(self, event):
        """接收日志消息"""
        await self.send(text_data=json.dumps({
            'type': 'log',
            'level': event.get('level'),
            'message': event.get('message'),
            'timestamp': event.get('timestamp')
        }))
    
    async def execution_complete(self, event):
        """接收执行完成"""
        await self.send(text_data=json.dumps({
            'type': 'execution_complete',
            'status': event.get('status'),
            'output': event.get('output'),
            'duration_ms': event.get('duration_ms')
        }))
    
    @database_sync_to_async
    def get_execution_status(self):
        """获取执行状态"""
        from .models import WorkflowExecution
        try:
            execution = WorkflowExecution.objects.get(id=self.execution_id)
            return {
                'id': str(execution.id),
                'status': execution.status,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
            }
        except WorkflowExecution.DoesNotExist:
            return None


class WorkflowEditorConsumer(AsyncWebsocketConsumer):
    """工作流编辑器 WebSocket Consumer"""
    
    async def connect(self):
        """建立连接"""
        self.workflow_id = self.scope['url_route']['kwargs'].get('workflow_id')
        self.user = self.scope['user']
        self.room_group_name = f'workflow_{self.workflow_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 广播用户加入
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def disconnect(self, close_code):
        """断开连接"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id
            }
        )
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """接收消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'node_updated':
                # 广播节点更新
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'node_update',
                        'node': data.get('node'),
                        'updated_by': self.user.id
                    }
                )
            elif message_type == 'edge_updated':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'edge_update',
                        'edge': data.get('edge'),
                        'updated_by': self.user.id
                    }
                )
            elif message_type == 'cursor_move':
                # 广播光标移动
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'cursor_update',
                        'user_id': self.user.id,
                        'position': data.get('position')
                    }
                )
        except json.JSONDecodeError:
            pass
    
    async def node_update(self, event):
        """节点更新"""
        await self.send(text_data=json.dumps({
            'type': 'node_update',
            'node': event.get('node'),
            'updated_by': event.get('updated_by')
        }))
    
    async def edge_update(self, event):
        """连线更新"""
        await self.send(text_data=json.dumps({
            'type': 'edge_update',
            'edge': event.get('edge'),
            'updated_by': event.get('updated_by')
        }))
    
    async def cursor_update(self, event):
        """光标更新"""
        await self.send(text_data=json.dumps({
            'type': 'cursor_update',
            'user_id': event.get('user_id'),
            'position': event.get('position')
        }))
    
    async def user_joined(self, event):
        """用户加入"""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event.get('user_id'),
            'username': event.get('username')
        }))
    
    async def user_left(self, event):
        """用户离开"""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event.get('user_id')
        }))
```

#### 9.5.9.2 前端 WebSocket Hook (`Frontend/src/composables/useWebSocket.js`)

```javascript
/**
 * WebSocket 组合式函数
 * 用于实时接收执行状态和日志更新
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket(executionId) {
  const socket = ref(null)
  const connected = ref(false)
  const logs = ref([])
  const status = ref('queued')
  const output = ref(null)
  const error = ref(null)
  
  const eventHandlers = {
    onStatusUpdate: null,
    onNodeUpdate: null,
    onLog: null,
    onComplete: null,
    onError: null
  }
  
  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/execution/${executionId}/`
    
    socket.value = new WebSocket(wsUrl)
    
    socket.value.onopen = () => {
      connected.value = true
      console.log('WebSocket connected')
    }
    
    socket.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }
    
    socket.value.onclose = () => {
      connected.value = false
      console.log('WebSocket disconnected')
    }
    
    socket.value.onerror = (error) => {
      console.error('WebSocket error:', error)
      error.value = '连接错误'
    }
  }
  
  function handleMessage(data) {
    switch (data.type) {
      case 'connection_established':
        console.log('Connection established:', data)
        break
      
      case 'execution_update':
        status.value = data.status
        if (eventHandlers.onStatusUpdate) {
          eventHandlers.onStatusUpdate(data)
        }
        break
      
      case 'status_update':
        status.value = data.data.status
        if (eventHandlers.onStatusUpdate) {
          eventHandlers.onStatusUpdate(data.data)
        }
        break
      
      case 'node_update':
        if (eventHandlers.onNodeUpdate) {
          eventHandlers.onNodeUpdate(data)
        }
        break
      
      case 'log':
        logs.value.push({
          level: data.level,
          message: data.message,
          timestamp: data.timestamp
        })
        if (eventHandlers.onLog) {
          eventHandlers.onLog(data)
        }
        break
      
      case 'execution_complete':
        status.value = data.status
        output.value = data.output
        if (eventHandlers.onComplete) {
          eventHandlers.onComplete(data)
        }
        break
      
      case 'error':
        error.value = data.message
        if (eventHandlers.onError) {
          eventHandlers.onError(data)
        }
        break
      
      case 'pong':
        // 心跳响应
        break
    }
  }
  
  function send(data) {
    if (socket.value && connected.value) {
      socket.value.send(JSON.stringify(data))
    }
  }
  
  function ping() {
    send({ type: 'ping' })
  }
  
  function disconnect() {
    if (socket.value) {
      socket.value.close()
      socket.value = null
    }
  }
  
  function on(event, handler) {
    if (event in eventHandlers) {
      eventHandlers[event] = handler
    }
  }
  
  // 生命周期
  onMounted(() => {
    connect()
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    connected,
    logs,
    status,
    output,
    error,
    connect,
    disconnect,
    send,
    ping,
    on
  }
}


export function useWorkflowEditorWebSocket(workflowId) {
  const socket = ref(null)
  const connected = ref(false)
  const collaborators = ref([])
  const cursors = ref({})
  
  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/workflow/${workflowId}/`
    
    socket.value = new WebSocket(wsUrl)
    
    socket.value.onopen = () => {
      connected.value = true
    }
    
    socket.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }
    
    socket.value.onclose = () => {
      connected.value = false
    }
  }
  
  function handleMessage(data) {
    switch (data.type) {
      case 'node_update':
        // 触发节点更新事件
        break
      
      case 'edge_update':
        // 触发连线更新事件
        break
      
      case 'cursor_update':
        cursors.value[data.user_id] = data.position
        break
      
      case 'user_joined':
        if (!collaborators.value.find(c => c.user_id === data.user_id)) {
          collaborators.value.push({
            user_id: data.user_id,
            username: data.username
          })
        }
        break
      
      case 'user_left':
        collaborators.value = collaborators.value.filter(
          c => c.user_id !== data.user_id
        )
        delete cursors.value[data.user_id]
        break
    }
  }
  
  function sendNodeUpdate(node) {
    send({
      type: 'node_updated',
      node
    })
  }
  
  function sendEdgeUpdate(edge) {
    send({
      type: 'edge_updated',
      edge
    })
  }
  
  function sendCursorMove(position) {
    send({
      type: 'cursor_move',
      position
    })
  }
  
  function send(data) {
    if (socket.value && connected.value) {
      socket.value.send(JSON.stringify(data))
    }
  }
  
  function disconnect() {
    if (socket.value) {
      socket.value.close()
      socket.value = null
    }
  }
  
  onMounted(() => {
    connect()
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    connected,
    collaborators,
    cursors,
    sendNodeUpdate,
    sendEdgeUpdate,
    sendCursorMove,
    disconnect
  }
}
```

### 9.5.10 完整数据流示例

#### 9.5.10.1 创建并执行工作流的完整流程

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         创建并执行工作流的完整数据流                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 1. 用户在前端创建工作流                                                              │
│                                                                                      │
│    Vue 组件                                                              Pinia Store  │
│    ┌────────────────────┐                                           ┌──────────────┐│
│    │ WorkflowCreator    │                                           │ workflowStore││
│    │ .name = "我的流程"  │                                           │              ││
│    │ .addNode(...)      │ ───── addNode(nodeData) ──────────────▶  │ nodes: []   ││
│    │ .addEdge(...)      │                                           │ edges: []   ││
│    └────────────────────┘                                           └──────┬───────┘│
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              │ saveWorkflow()
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 2. 前端调用 API 创建工作流                                                          │
│                                                                                      │
│    API Service                    Axios                                              │
│    ┌────────────────────┐       ┌──────────────┐                                    │
│    │ createWorkflow({  │ ───▶  │ POST /api/   │                                    │
│    │   name: "我的流程",│       │   workflows/ │                                    │
│    │   nodes: [...],    │       └──────┬───────┘                                    │
│    │   edges: [...]     │              │                                             │
│    │ })                │              │ HTTP Request + Bearer Token                  │
│    └────────────────────┘              │                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 3. 后端接收并处理请求                                                               │
│                                                                                      │
│    Django Views                  Serializers                                       │
│    ┌────────────────────┐       ┌──────────────┐                                   │
│    │ WorkflowViewSet    │ ◀─── │ WorkflowCreate│                                  │
│    │ .create()          │       │ Serializer    │                                  │
│    └─────────┬──────────┘       └──────┬───────┘                                   │
│              │                         │                                            │
│              │ 验证通过                │ validate()                                 │
│              ▼                         ▼                                            │
│    ┌────────────────────┐       ┌──────────────┐                                   │
│    │ Database           │ ◀─── │ create()     │                                  │
│    │ Workflow.objects   │       └──────────────┘                                   │
│    │ .create(...)       │                                                        │
│    └─────────┬──────────┘                                                         │
│              │                                                                     │
│              │ INSERT INTO workflows (...)                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 4. MySQL 数据库存储数据                                                             │
│                                                                                      │
│    ┌────────────────────────────────────────────────────────────────────────────┐   │
│    │ workflows 表                                                                │   │
│    │ +----+------+--------+----------+                                          │   │
│    │ | id | name | owner  | status   |                                          │   │
│    │ +----+------+--------+----------+                                          │   │
│    │ | 1  | 我的流程 | 1     | draft    |                                          │   │
│    │ +----+------+--------+----------+                                          │   │
│    └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│    ┌────────────────────────────────────────────────────────────────────────────┐   │
│    │ nodes 表                                                                   │   │
│    │ +----+-------+----------+------+-------+---------+------------------------+│   │
│    │ | id |work_id| node_type| name | pos_x | pos_y  | config                  ││   │
│    │ +----+-------+----------+------+-------+---------+------------------------+│   │
│    │ | 1  | 1     | start    | 开始  | 100   | 100    | {}                     ││   │
│    │ | 2  | 1     | llm      | LLM   | 300   | 100    | {model: "gpt-4"}       ││   │
│    │ | 3  | 1     | end      | 结束  | 500   | 100    | {}                     ││   │
│    │ +----+-------+----------+------+-------+---------+------------------------+│   │
│    └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│    ┌────────────────────────────────────────────────────────────────────────────┐   │
│    │ edges 表                                                                   │   │
│    │ +----+-------+-----------+-----------+                                      │   │
│    │ | id |work_id| source_id | target_id |                                      │   │
│    │ +----+-------+-----------+-----------+                                      │   │
│    │ | 1  | 1     | 1         | 2         |                                      │   │
│    │ | 2  | 1     | 2         | 3         |                                      │   │
│    │ +----+-------+-----------+-----------+                                      │   │
│    └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 5. 后端返回响应给前端                                                               │
│                                                                                      │
│    Serializers                    Axios                    Vue 组件                  │
│    ┌──────────────┐       ┌──────────────┐       ┌────────────────────┐           │
│    │ WorkflowSer   │ ───▶  │ HTTP Response│ ───▶  │ currentWorkflow    │           │
│    │ .data         │       │ (JSON)       │       │ = response.data   │           │
│    └──────────────┘       └──────────────┘       └────────────────────┘           │
│                                                                                      │
│    Response:                                                                         │
│    {                                                                                 │
│      "id": "abc-123",                                                                │
│      "name": "我的流程",                                                              │
│      "status": "draft",                                                             │
│      "nodes": [...],                                                                │
│      "edges": [...]                                                                  │
│    }                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 6. 前端更新状态并显示                                                               │
│                                                                                      │
│    Pinia Store                   Vue 组件                                          │
│    ┌──────────────┐              ┌────────────────────┐                          │
│    │ currentWorkflow─────▶      │ WorkflowEditor     │                          │
│    │ = response   │              │ <VueFlow>          │                          │
│    │ nodes        │              │   .nodes = store.nodes│                        │
│    │ = data.nodes │              │   .edges = store.edges│                        │
│    │ edges        │              └────────────────────┘                          │
│    │ = data.edges │                                                           │
│    └──────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 9.5.10.2 执行工作流的完整流程

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           执行工作流的完整数据流                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 1. 用户点击执行按钮                                                                  │
│                                                                                      │
│    Vue 组件                              Pinia Store                                  │
│    ┌────────────────────┐             ┌──────────────┐                              │
│    │ WorkflowCanvas     │             │ workflowStore│                              │
│    │ .onExecuteClick()  │ ─────────▶  │ executeWork- │                              │
│    │                    │             │ flow(input)   │                              │
│    └────────────────────┘             └──────┬───────┘                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 2. 前端发起执行请求                                                                 │
│                                                                                      │
│    API Service                    Axios                    WebSocket                │
│    ┌────────────────────┐       ┌──────────────┐       ┌──────────────┐          │
│    │ executeWorkflow(   │ ───▶  │ POST /api/   │       │ connect()    │          │
│    │   workflowId,      │       │ workflows/   │ ───▶  │ /{id}/execute/          │
│    │   inputData       │       │ workflows/   │       └──────┬───────┘          │
│    │ )                 │       │ {id}/execute/│              │                     │
│    └────────────────────┘       └──────────────┘              │                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 3. 后端创建执行记录并启动异步任务                                                      │
│                                                                                      │
│    Views                          Models                         Celery            │
│    ┌────────────────────┐       ┌──────────────┐       ┌──────────────┐          │
│    │ execute()          │ ───▶  │ Execution.   │ ───▶  │ execute_      │          │
│    │                    │       │ objects.create│       │ workflow_task│          │
│    └─────────┬──────────┘       └──────────────┘       └──────┬───────┘          │
│              │                                                  │                    │
│              │ Response:                                        │ delay()           │
│              │ {id: "exec-1", status: "queued"}                 │                    │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 4. Celery 异步执行工作流                                                             │
│                                                                                      │
│    Celery Worker                                                               │
│    ┌──────────────────────────────────────────────────────────────────────────┐   │
│    │ execute_workflow_task(execution_id)                                       │   │
│    │                                                                           │   │
│    │ 1. Load Workflow → nodes, edges                                           │   │
│    │ 2. Find Start Node                                                        │   │
│    │ 3. Execute Start Node ──▶ WebSocket: node_update {status: "running"}      │   │
│    │ 4. Execute LLM Node   ──▶ WebSocket: node_update {status: "running"}      │   │
│    │    - Call LLM API                                                          │   │
│    │    - Get Response                                                          │   │
│    │    - WebSocket: log {level: "INFO", message: "LLM completed"}             │   │
│    │ 5. Execute End Node   ──▶ WebSocket: node_update {status: "completed"}    │   │
│    │ 6. Update Execution ──▶ WebSocket: execution_complete {status: "done"}    │   │
│    │                                                                           │   │
│    └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 5. 前端接收实时更新                                                                 │
│                                                                                      │
│    WebSocket                      Vue 组件                                         │
│    ┌──────────────┐              ┌────────────────────┐                          │
│    │ onMessage() │ ──────────▶  │ StreamExecution    │                          │
│    │             │              │ Panel              │                          │
│    │ data.type:  │              │ .updateStatus()    │                          │
│    │ "node_update"│              │ .addLog()          │                          │
│    │ "log"       │              │ .showOutput()      │                          │
│    │ "execution_  │              └────────────────────┘                          │
│    │  complete"  │                                                               │
│    └──────────────┘                                                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 6. 执行完成，更新数据库和前端状态                                                      │
│                                                                                      │
│    MySQL                         Pinia Store                                       │
│    ┌──────────────┐             ┌──────────────┐                                  │
│    │ workflow_    │             │ currentExecu-│                                  │
│    │ executions   │             │ tion = resp  │                                  │
│    │ .status =    │             │ status =     │                                  │
│    │ "completed"  │             │ "completed"  │                                  │
│    │              │             │ output = ... │                                  │
│    └──────────────┘             └──────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.5.11 总结：前后端数据库交互核心要点

| 层级 | 组件 | 职责 | 关键技术 |
|------|------|------|----------|
| **前端展示** | Vue 组件 | 用户界面渲染 | Vue 3, Element Plus |
| **前端状态** | Pinia Store | 状态管理 | 响应式数据 |
| **前端 API** | API Services | HTTP 请求封装 | Axios |
| **后端视图** | ViewSet | 请求处理 | Django REST Framework |
| **后端序列化** | Serializer | 数据验证转换 | DRF Serializer |
| **后端服务** | Service | 业务逻辑 | Python 类 |
| **数据模型** | Model | 数据结构定义 | Django ORM |
| **数据库** | MySQL | 数据持久化 | SQL |

**核心交互原则：**

1. **单向数据流** - 前端 Store 管理状态，组件只负责展示
2. **API 驱动** - 所有数据操作通过 API 完成
3. **实时反馈** - 通过 WebSocket 推送执行状态
4. **错误处理** - 统一的错误处理机制
5. **类型安全** - TypeScript 类型与后端模型对应

---

## 9.5.12 API 健壮性自查清单

> 为确保前后端 API 交互的稳定性和用户体验，遵循以下健壮性设计规范。

### 9.5.12.1 后端健壮性检查

#### 响应结构标准化

所有 API 响应必须遵循统一的结构格式：

```python
# 标准成功响应
{
    "code": 200,
    "data": { ... },
    "message": "操作成功"
}

# 标准错误响应
{
    "code": 400,
    "data": null,
    "message": "参数校验失败",
    "errors": {
        "field_name": ["错误信息1", "错误信息2"]
    }
}
```

#### 全局异常处理中间件

```python
# Backend/config/middleware.py

from django.http import JsonResponse

class GlobalExceptionMiddleware:
    """全局异常处理中间件"""

    EXCEPTION_HANDLERS = {
        'ValidationError': (400, '数据校验失败'),
        'AuthenticationFailed': (401, '认证失败'),
        'NotAuthenticated': (401, '请先登录'),
        'PermissionDenied': (403, '权限不足'),
        'NotFound': (404, '资源不存在'),
        'MethodNotAllowed': (405, '请求方法不支持'),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """处理未捕获的异常"""
        exception_class = exception.__class__.__name__

        # 获取对应状态码
        status_code = 500
        message = str(exception)

        for cls_name, (code, msg) in self.EXCEPTION_HANDLERS.items():
            if cls_name in exception_class:
                status_code = code
                message = msg
                break

        # 记录日志
        logger = logging.getLogger(__name__)
        logger.error(f"API Exception: {exception_class} - {exception}", exc_info=True)

        return JsonResponse({
            'code': status_code,
            'data': None,
            'message': message,
            'errors': getattr(exception, 'detail', None)
        }, status=status_code)
```

#### DRF 全局异常处理器

```python
# Backend/config/settings.py

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'config.exception_handlers.custom_exception_handler',
}

# Backend/config/exception_handlers.py

from rest_framework.views import exception_handler
from rest_framework import status

def custom_exception_handler(exc, context):
    """自定义全局异常处理"""
    response = exception_handler(exc, context)

    if response is not None:
        # 标准化响应结构
        custom_response = {
            'code': response.status_code,
            'data': None,
            'message': get_error_message(response.data),
            'errors': response.data if isinstance(response.data, dict) else None
        }
        response.data = custom_response

    return response

def get_error_message(data):
    """提取错误消息"""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return '; '.join(str(item) for item in data)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            elif isinstance(value, str):
                return f"{key}: {value}"
    return "请求处理失败"
```

#### 404/405 JSON 响应处理

```python
# Backend/config/handlers.py

from django.http import JsonResponse

def handler404(request, exception):
    """404 JSON 响应"""
    return JsonResponse({
        'code': 404,
        'data': None,
        'message': f'路由不存在: {request.path}'
    }, status=404)

def handler405(request, exception):
    """405 JSON 响应"""
    return JsonResponse({
        'code': 405,
        'data': None,
        'message': f'请求方法 {request.method} 不支持'
    }, status=405)

def handler500(request):
    """500 JSON 响应"""
    return JsonResponse({
        'code': 500,
        'data': None,
        'message': '服务器内部错误'
    }, status=500)
```

#### 参数校验与详细错误

```python
# Backend/workflows/serializers.py

class WorkflowExecuteSerializer(serializers.Serializer):
    """工作流执行请求验证"""

    input_data = serializers.JSONField(required=False, default=dict)
    trigger_type = serializers.ChoiceField(
        choices=['manual', 'api', 'webhook', 'scheduled'],
        default='manual'
    )
    is_async = serializers.BooleanField(default=False)

    def validate_input_data(self, value):
        """验证输入数据"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("input_data 必须是对象")
        return value

    def validate(self, attrs):
        """跨字段验证"""
        is_async = attrs.get('is_async', False)
        trigger_type = attrs.get('trigger_type', 'manual')

        # 异步执行必须指定触发类型
        if is_async and trigger_type == 'manual':
            attrs['trigger_type'] = 'api'

        return attrs
```

### 9.5.12.2 前端健壮性检查

#### API 请求封装

```javascript
// Frontend/src/api/index.js

import axios from 'axios'
import Cookies from 'js-cookie'
import { ElMessage, ElNotification } from 'element-plus'

// 创建 Axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL + import.meta.env.VITE_API_PREFIX,
  timeout: 30000,  // ✅ 请求超时设置
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证 Token
    const token = Cookies.get('access_token') || localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // ✅ 自动转换响应数据: snake_case -> camelCase
    if (response.data && typeof response.data === 'object') {
      response.data = toCamelCaseKeys(response.data)
    }
    return response.data
  },
  async (error) => {
    const { response, config } = error

    // ✅ 网络断开处理
    if (!response) {
      ElNotification.error({
        title: '网络错误',
        message: '网络连接失败，请检查网络后重试',
        duration: 5000
      })
      return Promise.reject(error)
    }

    // ✅ 超时处理
    if (error.code === 'ECONNABORTED') {
      ElNotification.warning({
        title: '请求超时',
        message: '服务器响应超时，请稍后重试',
        duration: 3000
      })
      return Promise.reject(error)
    }

    // ✅ HTTP 错误处理
    switch (response.status) {
      case 400:
        // ✅ 字段级错误提示
        if (response.data?.errors) {
          const fieldErrors = Object.entries(response.data.errors)
            .map(([field, msgs]) => `${field}: ${msgs[0]}`)
            .join('\n')
          ElMessage.error({
            message: fieldErrors,
            duration: 5000
          })
        } else {
          ElMessage.error(response.data?.message || '参数错误')
        }
        break

      case 401:
        // ✅ 认证失效处理
        handleAuthError()
        break

      case 403:
        ElMessage.error('权限不足，无法执行此操作')
        break

      case 404:
        ElMessage.error('请求的资源不存在')
        break

      case 429:
        ElMessage.warning('请求过于频繁，请稍后再试')
        break

      case 500:
      case 502:
      case 503:
        ElNotification.error({
          title: '服务错误',
          message: '服务器处理失败，请稍后重试',
          duration: 5000
        })
        break

      default:
        ElMessage.error(response.data?.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

// 认证错误处理
function handleAuthError() {
  Cookies.remove('access_token')
  Cookies.remove('refresh_token')
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')

  ElMessage.error({
    message: '登录已过期，请重新登录',
    duration: 3000,
    onClose: () => {
      window.location.href = '/login'
    }
  })
}
```

#### 请求三态封装

```javascript
// Frontend/src/composables/useRequest.js

import { ref } from 'vue'
import { ElMessage } from 'element-plus'

/**
 * 请求状态管理 Hook
 * @returns {Object} { loading, error, data, execute }
 */
export function useRequest(apiFunc) {
  const loading = ref(false)
  const error = ref(null)
  const data = ref(null)

  const execute = async (...args) => {
    loading.value = true
    error.value = null
    data.value = null

    try {
      const result = await apiFunc(...args)
      data.value = result
      return result
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    data,
    execute
  }
}

// 使用示例
const { loading, error, data, execute: fetchWorkflow } = useRequest(
  (id) => workflowApi.getById(id)
)

// 在组件中使用
await fetchWorkflow(123)
if (loading.value) { /* 显示加载状态 */ }
if (error.value) { /* 显示错误状态 */ }
if (data.value) { /* 显示数据 */ }
```

#### 防抖/节流按钮封装

```javascript
// Frontend/src/components/common/DebouncedButton.vue

<template>
  <el-button
    v-bind="$attrs"
    :loading="internalLoading"
    :disabled="disabled || internalLoading"
    @click="handleClick"
  >
    <slot />
  </el-button>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  // 防抖延迟 (毫秒)
  debounce: {
    type: Number,
    default: 500
  },
  // 节流间隔 (毫秒)
  throttle: {
    type: Number,
    default: 0
  },
  // 是否在点击时显示 loading
  loadingOnClick: {
    type: Boolean,
    default: false
  },
  disabled: Boolean
})

const emit = defineEmits(['click'])

const internalLoading = ref(false)
let debounceTimer = null
let throttleLastTime = 0

const handleClick = async (event) => {
  // 防抖检查
  if (debounceTimer) {
    ElMessage.warning('操作太频繁，请稍后')
    return
  }

  // 节流检查
  if (throttle > 0) {
    const now = Date.now()
    if (now - throttleLastTime < throttle) {
      return
    }
    throttleLastTime = now
  }

  // 设置防抖
  if (debounce > 0) {
    debounceTimer = setTimeout(() => {
      debounceTimer = null
    }, debounce)
  }

  // 显示 loading
  if (props.loadingOnClick) {
    internalLoading.value = true
  }

  try {
    emit('click', event)
  } finally {
    if (props.loadingOnClick) {
      internalLoading.value = false
    }
  }
}
</script>
```

#### 空数据保护

```javascript
// Frontend/src/utils/safeAccess.js

/**
 * 安全访问嵌套属性
 * @param {Object} obj - 目标对象
 * @param {String} path - 属性路径，如 'user.profile.name'
 * @param {*} defaultValue - 默认值
 */
export function safeGet(obj, path, defaultValue = null) {
  if (obj == null) return defaultValue

  const keys = path.split('.')
  let current = obj

  for (const key of keys) {
    if (current == null || typeof current !== 'object') {
      return defaultValue
    }
    current = current[key]
  }

  return current ?? defaultValue
}

// 使用示例
const userName = safeGet(response, 'data.user.name', '未知用户')
const items = safeGet(response, 'data.items', [])
const firstItem = items[0]?.name  // 使用可选链
```

### 9.5.12.3 健壮性检查清单

#### 后端检查清单

| 检查项 | 说明 | 状态 |
|--------|------|------|
| `return` 响应 | 所有异常路径都有返回响应 | ✅ |
| 全局异常处理 | 中间件捕获未处理异常 | ✅ |
| 响应结构统一 | `{code, data, message}` 格式 | ✅ |
| 404/405 处理 | 返回 JSON 而非 HTML | ✅ |
| 参数校验 | 输入验证 + 具体错误字段 | ✅ |
| 认证 401 | 携带错误消息 | ✅ |
| 日志记录 | 异常信息记录到日志 | ✅ |
| 超时处理 | 请求超时返回 504 | ✅ |

#### 前端检查清单

| 检查项 | 说明 | 状态 |
|--------|------|------|
| loading 状态 | 每个请求都有加载状态 | ✅ |
| error 处理 | 每个请求都捕获错误 | ✅ |
| data 状态 | 正确处理响应数据 | ✅ |
| 响应拦截器 | 捕获 HTTP + 业务错误 | ✅ |
| 请求 timeout | 设置合理的超时时间 | ✅ |
| 网络断开 | 顶部提示条通知 | ✅ |
| 敏感按钮防抖 | 防止重复提交 | ✅ |
| 空数据保护 | `?.` 或默认值兜底 | ✅ |

### 9.5.12.4 典型场景处理

#### 执行 API 示例

```javascript
// 工作流执行 API - 完整健壮性实现

/**
 * 执行工作流
 * @param {number|string} workflowId
 * @param {Object} inputData
 * @returns {Promise<ExecutionResponse>}
 */
export async function executeWorkflow(workflowId, inputData = {}) {
  const response = await api.post(`/workflows/${workflowId}/execute/`, {
    input_data: inputData,
    is_async: true
  })

  // ✅ 响应结构验证
  if (!response.data) {
    throw new Error('执行创建失败：服务器返回无效数据')
  }

  // ✅ 返回标准格式
  return {
    executionId: response.data.executionId,
    taskId: response.data.taskId,
    status: response.data.status,
    message: response.data.message || '执行已启动'
  }
}

// 组件中使用
async function handleExecute() {
  const button = ref(null)  // 防抖按钮引用

  try {
    const result = await executeWorkflow(workflowId.value, { query: 'test' })

    // ✅ 成功处理
    ElMessage.success(result.message)
    executionId.value = result.executionId

    // 启动轮询或 WebSocket
    startExecutionMonitoring(result.executionId)

  } catch (error) {
    // ✅ 错误已被拦截器处理，但可以添加业务逻辑
    if (error.response?.status === 400) {
      // 业务级错误处理
      showValidationDialog(error.response.data.errors)
    }
  } finally {
    // ✅ 清除加载状态
    button.value?.resetLoading?.()
  }
}
```

#### 轮询实现

```javascript
// Frontend/src/composables/useExecutionPolling.js

import { ref, onUnmounted } from 'vue'
import { workflowApi } from '@/api/workflow'

/**
 * 执行状态轮询
 */
export function useExecutionPolling(executionId, options = {}) {
  const {
    interval = 2000,  // 轮询间隔
    maxAttempts = 30,   // 最大轮询次数
    onStatusChange,
    onComplete,
    onError
  } = options

  const status = ref('pending')
  const output = ref(null)
  const error = ref(null)
  const isPolling = ref(false)
  let timer = null
  let attempts = 0

  const start = async () => {
    if (isPolling.value) return

    isPolling.value = true
    attempts = 0

    const poll = async () => {
      if (!isPolling.value || attempts >= maxAttempts) {
        stop()
        return
      }

      try {
        const result = await workflowApi.getExecutionStatus(executionId.value)

        const prevStatus = status.value
        status.value = result.status

        // 状态变化回调
        if (prevStatus !== result.status) {
          onStatusChange?.(result.status, result)
        }

        // 完成处理
        if (result.status === 'completed') {
          output.value = result.outputData
          onComplete?.(result)
          stop()
          return
        }

        // 失败处理
        if (result.status === 'failed') {
          error.value = result.errorMessage
          onError?.(result.errorMessage)
          stop()
          return
        }

        // 继续轮询
        attempts++
        timer = setTimeout(poll, interval)

      } catch (err) {
        error.value = err.message
        onError?.(err.message)
        stop()
      }
    }

    poll()
  }

  const stop = () => {
    isPolling.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  onUnmounted(stop)

  return {
    status,
    output,
    error,
    isPolling,
    start,
    stop
  }
}
```

---



## Step 10 - 前后端联调

### 10.1 配置代理（开发环境）

创建 `Frontend/vite.config.js`：

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

### 10.2 测试完整流程

1. **启动后端**：
```powershell
cd e:\Flowly-now\Backend
.\venv\Scripts\Activate
python manage.py runserver
```

2. **启动前端**：
```powershell
cd e:\Flowly-now\Frontend
npm run dev
```

3. **访问页面**：
- 前端：http://localhost:5173/
- 后端 API：http://localhost:8000/api/

---

## Step 11 - 部署上线

### 11.1 后端部署

**使用 Gunicorn**：

```powershell
pip install gunicorn
```

创建 `Backend/start.sh`：

```bash
#!/bin/bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### 11.2 前端构建

```powershell
cd e:\Flowly-now\Frontend
npm run build
```

构建产物在 `dist` 目录。

### 11.3 Docker 部署（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: workflow_db
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  backend:
    build: ./Backend
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_NAME=workflow_db
      - DB_USER=root
      - DB_PASSWORD=password
    depends_on:
      - db

  frontend:
    build: ./Frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mysql_data:
```

---

## 下一步建议

完成以上步骤后，你可以：

1. **完善前端界面** - 添加更多交互功能
2. **增加更多节点类型** - 如搜索、数据库、API 调用等
3. **实现用户认证** - 注册登录功能
4. **添加流式输出** - 支持 LLM 流式响应
5. **增加日志和监控** - 记录详细的执行过程
6. **实现团队协作** - 多人同时编辑工作流
7. **扩展 Provider** - 添加更多模型提供商的适配器

---

## 附录：AI 模型网关 API 参考

### 统一 Chat Completions 接口

```http
POST /api/v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-4o",           // 模型ID（平台模型或用户自定义模型）
  "messages": [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### 获取可用模型列表

```http
GET /api/v1/models
```

响应：
```json
{
  "platform_models": [
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
    {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "anthropic"}
  ],
  "custom_models": [
    {"id": "custom-llama", "name": "我的 Llama", "provider": "openai", "auth_type": "user_provided"}
  ]
}
```

### 用户添加自定义模型

```http
POST /api/v1/custom-models
Content-Type: application/json

{
  "name": "我的 Ollama",
  "model_id": "llama3",
  "provider": "ollama",
  "endpoint": "http://localhost:11434",
  "api_key_id": "optional-key-id"  // 可选关联用户API Key
}
```

---

## Step 11 - 异步任务系统 (Celery)

### 11.1 架构概述

Celery 是 Python 分布式任务队列，用于处理异步执行、长时任务、计划任务等场景。

```
前端请求 → Django → Redis (消息队列) → Celery Worker → 执行结果
                     ↓
              Celery Beat (定时任务)
```

### 11.2 安装依赖

```powershell
cd e:\Flowly-now\Backend
.\venv\Scripts\Activate
pip install celery
pip install redis
```

### 11.3 配置 Celery

创建 `Backend/config/celery.py`：

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('flowly')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

创建 `Backend/config/__init__.py`：

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

更新 `Backend/config/settings.py`：

```python
# Celery 配置
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 分钟超时
```

### 11.4 创建异步任务

创建 `Backend/workflow/tasks.py`：

```python
from celery import shared_task
from .models import WorkflowExecution
from .services.workflow_executor import WorkflowExecutor


@shared_task(bind=True)
def execute_workflow_task(self, workflow_id: int, execution_id: int, input_data: dict):
    """异步执行工作流任务"""
    try:
        # 更新任务 ID
        execution = WorkflowExecution.objects.get(id=execution_id)
        execution.celery_task_id = self.request.id
        execution.save()

        # 执行工作流
        from .services.workflow_executor import WorkflowExecutor
        executor = WorkflowExecutor(execution.workflow, execution)
        result = executor.execute()

        return {
            'status': 'success',
            'execution_id': execution_id,
            'result': result
        }

    except Exception as e:
        # 更新执行状态为失败
        execution = WorkflowExecution.objects.get(id=execution_id)
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.save()

        return {
            'status': 'failed',
            'execution_id': execution_id,
            'error': str(e)
        }
```

### 11.5 在视图中调用任务

更新 `workflow/views.py`：

```python
from .tasks import execute_workflow_task


class WorkflowExecutionViewSet(viewsets.ModelViewSet):
    # ...

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """触发工作流执行（异步）"""
        workflow = self.get_object()
        input_data = request.data.get('input_data', {})

        # 创建执行记录
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            status='pending',
            input_data=input_data
        )

        # 触发异步任务
        task = execute_workflow_task.delay(workflow.id, execution.id, input_data)

        return Response({
            'execution_id': execution.id,
            'task_id': task.id,
            'status': 'pending',
            'message': '工作流执行已启动'
        })

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """查询执行状态"""
        execution = self.get_object()

        # 如果有 Celery task_id，可以查询任务状态
        if execution.celery_task_id:
            from .tasks import execute_workflow_task
            task = execute_workflow_task.AsyncResult(execution.celery_task_id)
            celery_status = task.state

            return Response({
                'execution_id': execution.id,
                'status': execution.status,
                'celery_state': celery_status,
                'progress': task.info.get('progress', 0) if isinstance(task.info, dict) else 0
            })

        return Response({
            'execution_id': execution.id,
            'status': execution.status
        })
```

### 11.6 启动 Worker

```powershell
# 终端 1: 启动 Django
python manage.py runserver

# 终端 2: 启动 Celery Worker
cd e:\Flowly-now\Backend
.\venv\Scripts\Activate
celery -A config worker -l INFO

# 终端 3: (可选) 启动 Celery Beat (定时任务)
celery -A config beat -l INFO
```

---

## Step 12 - 实时通信 (WebSocket)

### 12.1 为什么需要 WebSocket

WebSocket 用于实时推送工作流执行进度：

```
传统轮询：前端每隔几秒请求一次 → 服务器压力高、延迟大
WebSocket：服务器主动推送 → 实时、低延迟
```

### 12.2 安装 Django Channels

```powershell
pip install channels channels-redis daphne
```

### 12.3 配置 Channels

更新 `Backend/config/settings.py`：

```python
# Channels 配置
ASGI_APPLICATION = 'config.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

创建 `Backend/config/asgi.py`：

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from workflow.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
```

创建 `Backend/workflow/routing.py`：

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/execution/(?P<execution_id>\w+)/$', consumers.ExecutionConsumer.as_asgi()),
]
```

### 12.4 创建 Consumer

创建 `Backend/workflow/consumers.py`：

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ExecutionConsumer(AsyncWebsocketConsumer):
    """工作流执行进度 Consumer"""

    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'execution_{self.execution_id}'

        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 离开房间组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # 处理前端消息（如果需要）
        pass

    async def execution_update(self, event):
        """接收执行进度更新"""
        await self.send(text_data=json.dumps({
            'type': 'execution_update',
            'execution_id': event['execution_id'],
            'status': event['status'],
            'progress': event.get('progress', 0),
            'message': event.get('message', ''),
            'output': event.get('output'),
            'error': event.get('error'),
        }))

    async def execution_complete(self, event):
        """接收执行完成通知"""
        await self.send(text_data=json.dumps({
            'type': 'execution_complete',
            'execution_id': event['execution_id'],
            'status': event['status'],
            'output': event.get('output'),
            'error': event.get('error'),
        }))
```

### 12.5 在任务中发送消息

更新 `Backend/workflow/tasks.py`：

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task(bind=True)
def execute_workflow_task(self, workflow_id: int, execution_id: int, input_data: dict):
    """异步执行工作流任务"""
    channel_layer = get_channel_layer()

    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        execution.celery_task_id = self.request.id
        execution.save()

        # 发送开始消息
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution_id}',
            {
                'type': 'execution_update',
                'execution_id': execution_id,
                'status': 'running',
                'progress': 0,
                'message': '开始执行...'
            }
        )

        # 执行工作流（分步发送进度）
        executor = WorkflowExecutor(execution.workflow, execution)
        result = executor.execute()

        # 发送完成消息
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution_id}',
            {
                'type': 'execution_complete',
                'execution_id': execution_id,
                'status': execution.status,
                'output': execution.output_data,
            }
        )

        return {'status': 'success', 'execution_id': execution_id}

    except Exception as e:
        async_to_sync(channel_layer.group_send)(
            f'execution_{execution_id}',
            {
                'type': 'execution_complete',
                'execution_id': execution_id,
                'status': 'failed',
                'error': str(e),
            }
        )
        raise
```

### 12.6 前端 WebSocket 连接

```javascript
// Frontend/src/utils/websocket.js
import { ref } from 'vue'

export function useExecutionWebSocket(executionId) {
  const messages = ref([])
  const connected = ref(false)
  let ws = null

  const connect = () => {
    ws = new WebSocket(`ws://localhost:8000/ws/execution/${executionId}/`)

    ws.onopen = () => {
      connected.value = true
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      messages.value.push(data)

      if (data.type === 'execution_complete') {
        console.log('Execution completed:', data)
      }
    }

    ws.onclose = () => {
      connected.value = false
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const disconnect = () => {
    if (ws) {
      ws.close()
    }
  }

  return {
    messages,
    connected,
    connect,
    disconnect
  }
}
```

---

## Step 13 - 用户认证系统

### 13.1 安装 JWT 依赖

```powershell
pip install djangorestframework-simplejwt
```

### 13.2 配置 JWT

更新 `Backend/config/settings.py`：

```python
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### 13.3 配置路由

创建 `Backend/config/urls.py`：

```python
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('workflow.urls')),
    path('api/gateway/', include('gateway.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
```

### 13.4 用户注册与登录 API

创建 `Backend/users/views.py`：

```python
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """用户注册"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # 生成 Token
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """用户登录"""
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = User.objects.filter(username=username).first()

        if not user or not user.check_password(password):
            return Response(
                {'error': '用户名或密码错误'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    """用户资料"""
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
```

创建 `Backend/users/serializers.py`：

```python
from rest_framework import serializers
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': '两次密码不一致'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user
```

### 13.5 前端认证 Hook

创建 `Frontend/src/stores/auth.js`：

```javascript
import { defineStore } from 'pinia'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem('access') || null,
    refreshToken: localStorage.getItem('refresh') || null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },

  actions: {
    async login(username, password) {
      const response = await axios.post(`${API_BASE}/auth/token/`, { username, password })
      this.accessToken = response.data.access
      this.refreshToken = response.data.refresh
      this.user = response.data.user

      localStorage.setItem('access', this.accessToken)
      localStorage.setItem('refresh', this.refreshToken)

      axios.defaults.headers.common['Authorization'] = `Bearer ${this.accessToken}`
    },

    async register(data) {
      const response = await axios.post(`${API_BASE}/auth/register/`, data)
      this.accessToken = response.data.tokens.access
      this.refreshToken = response.data.tokens.refresh
      this.user = response.data.user

      localStorage.setItem('access', this.accessToken)
      localStorage.setItem('refresh', this.refreshToken)
    },

    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem('access')
      localStorage.removeItem('refresh')
      delete axios.defaults.headers.common['Authorization']
    },

    async refreshAccessToken() {
      try {
        const response = await axios.post(`${API_BASE}/auth/token/refresh/`, {
          refresh: this.refreshToken
        })
        this.accessToken = response.data.access
        localStorage.setItem('access', this.accessToken)
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.accessToken}`
        return true
      } catch {
        this.logout()
        return false
      }
    }
  }
})
```

---

## Step 14 - Prompt 模板系统

### 14.1 Prompt 模板模型

编辑 `Backend/workflow/models.py`，添加：

```python
class PromptTemplate(models.Model):
    """提示词模板"""
    CATEGORY_CHOICES = [
        ('summarize', '摘要总结'),
        ('translate', '翻译'),
        ('code', '代码生成'),
        ('analyze', '分析'),
        ('custom', '自定义'),
    ]

    name = models.CharField(max_length=200, verbose_name="模板名称")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="分类")
    description = models.TextField(blank=True, verbose_name="描述")
    template = models.TextField(verbose_name="模板内容")
    variables = models.JSONField(default=list, verbose_name="变量列表")
    is_public = models.BooleanField(default=True, verbose_name="是否公开")
    usage_count = models.IntegerField(default=0, verbose_name="使用次数")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prompt_templates'
        verbose_name = '提示词模板'
        verbose_name_plural = '提示词模板'

    def __str__(self):
        return self.name

    def render(self, context: dict) -> str:
        """渲染模板，替换变量"""
        result = self.template
        for var in self.variables:
            placeholder = f'{{{var}}}'
            value = context.get(var, '')
            result = result.replace(placeholder, str(value))
        return result
```

### 14.2 模板序列化器

```python
# workflow/serializers.py 添加

class PromptTemplateSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = PromptTemplate
        fields = ['id', 'name', 'category', 'description', 'template',
                  'variables', 'is_public', 'usage_count', 'owner_name',
                  'created_at', 'updated_at']
        read_only_fields = ['usage_count', 'owner_name', 'created_at', 'updated_at']


class PromptTemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = ['id', 'name', 'category', 'description', 'usage_count']
```

### 14.3 模板视图

```python
# workflow/views.py 添加

class PromptTemplateViewSet(viewsets.ModelViewSet):
    queryset = PromptTemplate.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PromptTemplateListSerializer
        return PromptTemplateSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """预览模板渲染结果"""
        template = self.get_object()
        context = request.data.get('context', {})

        rendered = template.render(context)

        return Response({
            'original': template.template,
            'rendered': rendered,
            'variables': template.variables
        })

    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """使用模板（增加计数）"""
        template = self.get_object()
        template.usage_count += 1
        template.save()

        context = request.data.get('context', {})
        rendered = template.render(context)

        return Response({
            'template_id': template.id,
            'rendered': rendered
        })
```

### 14.4 前端模板选择器组件

```vue
<!-- Frontend/src/components/PromptTemplateSelector.vue -->
<template>
  <div class="template-selector">
    <el-select v-model="selectedTemplateId" placeholder="选择模板" @change="onSelect">
      <el-option-group label="公开模板">
        <el-option
          v-for="t in publicTemplates"
          :key="t.id"
          :label="t.name"
          :value="t.id"
        >
          <span>{{ t.name }}</span>
          <span class="template-category">{{ t.category }}</span>
        </el-option>
      </el-option-group>
      <el-option-group label="我的模板">
        <el-option
          v-for="t in myTemplates"
          :key="t.id"
          :label="t.name"
          :value="t.id"
        />
      </el-option-group>
    </el-select>

    <div v-if="selectedTemplate" class="template-preview">
      <h4>{{ selectedTemplate.name }}</h4>
      <p>{{ selectedTemplate.description }}</p>
      <div class="variables">
        <span v-for="v in selectedTemplate.variables" :key="v" class="variable-tag">
          {{ v }}
        </span>
      </div>
      <el-input
        v-model="templateContent"
        type="textarea"
        :rows="6"
        placeholder="模板内容..."
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])

const templates = ref([])
const selectedTemplateId = ref(null)

const selectedTemplate = computed(() =>
  templates.value.find(t => t.id === selectedTemplateId.value)
)

const publicTemplates = computed(() =>
  templates.value.filter(t => t.is_public)
)

const myTemplates = computed(() =>
  templates.value.filter(t => !t.is_public)
)

const templateContent = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const onSelect = (id) => {
  const template = templates.value.find(t => t.id === id)
  if (template) {
    emit('update:modelValue', template.template)
  }
}

onMounted(async () => {
  const response = await axios.get('http://localhost:8000/api/prompt-templates/')
  templates.value = response.data.results || response.data
})
</script>
```

---

## Step 15 - 执行日志与版本管理

### 15.1 工作流版本模型

编辑 `Backend/workflow/models.py`，添加：

```python
class WorkflowVersion(models.Model):
    """工作流版本"""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField(verbose_name="版本号")
    nodes_snapshot = models.JSONField(verbose_name="节点快照")
    edges_snapshot = models.JSONField(verbose_name="边快照")
    description = models.TextField(blank=True, verbose_name="版本说明")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workflow_versions'
        unique_together = ['workflow', 'version']
        ordering = ['-version']

    def __str__(self):
        return f"{self.workflow.name} v{self.version}"


class ExecutionLog(models.Model):
    """执行日志（详细步骤）"""
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='logs')
    node_id = models.CharField(max_length=100, verbose_name="节点ID")
    node_name = models.CharField(max_length=200, verbose_name="节点名称")
    node_type = models.CharField(max_length=50, verbose_name="节点类型")
    status = models.CharField(max_length=20, verbose_name="状态")
    input_data = models.JSONField(default=dict, verbose_name="输入数据")
    output_data = models.JSONField(default=dict, verbose_name="输出数据")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    duration_ms = models.IntegerField(default=0, verbose_name="耗时(毫秒)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'execution_logs'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.node_name} - {self.status}"
```

### 15.2 创建版本快照

```python
# workflow/services/versioning.py

from ..models import WorkflowVersion, Workflow, Node, Edge


class WorkflowVersionManager:
    """工作流版本管理器"""

    @staticmethod
    def create_version(workflow: Workflow, description: str = '', user=None) -> WorkflowVersion:
        """创建新版本"""
        # 获取下一个版本号
        last_version = workflow.versions.order_by('-version').first()
        next_version = (last_version.version + 1) if last_version else 1

        # 快照节点和边
        nodes = list(workflow.nodes.values('id', 'node_type', 'name', 'config',
                                            'position_x', 'position_y'))
        edges = list(workflow.edges.values('id', 'source_node', 'target_node', 'label'))

        version = WorkflowVersion.objects.create(
            workflow=workflow,
            version=next_version,
            nodes_snapshot=nodes,
            edges_snapshot=edges,
            description=description,
            created_by=user
        )

        return version

    @staticmethod
    def restore_version(workflow: Workflow, version_number: int) -> Workflow:
        """恢复到指定版本"""
        version = workflow.versions.get(version=version_number)

        # 删除现有节点和边
        workflow.nodes.all().delete()
        workflow.edges.all().delete()

        # 恢复节点
        node_id_map = {}  # 旧ID -> 新ID 映射
        for node_data in version.nodes_snapshot:
            old_id = node_data.pop('id')
            node = workflow.nodes.create(**node_data)
            node_id_map[old_id] = node.id

        # 恢复边
        for edge_data in version.edges_snapshot:
            edge_data['source_node_id'] = node_id_map.get(edge_data.pop('source_node'))
            edge_data['target_node_id'] = node_id_map.get(edge_data.pop('target_node'))
            workflow.edges.create(**edge_data)

        return workflow

    @staticmethod
    def get_version_diff(v1: int, v2: int) -> dict:
        """获取两个版本的差异"""
        # 简化实现，实际可以用 deepdiff 库
        pass
```

### 15.3 执行日志记录

更新 `Backend/workflow/services/workflow_executor.py`：

```python
from ..models import WorkflowExecution, ExecutionLog
import time


class WorkflowExecutor:
    # ...

    def execute_node(self, node):
        """执行单个节点"""
        start_time = time.time()

        # 记录开始日志
        log = ExecutionLog.objects.create(
            execution=self.execution,
            node_id=node.id,
            node_name=node.name,
            node_type=node.node_type,
            status='running',
            input_data=self.context.copy()
        )

        try:
            # 执行节点
            result = langchain_service.execute_node(
                node.node_type,
                node.config,
                self.context
            )

            # 更新上下文
            if result.get('output'):
                self.context['last_output'] = result['output']

            # 更新日志
            log.status = 'success'
            log.output_data = result
            log.duration_ms = int((time.time() - start_time) * 1000)
            log.save()

            self.node_results[node.id] = result
            return result

        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.duration_ms = int((time.time() - start_time) * 1000)
            log.save()
            raise
```

### 15.4 版本管理视图

```python
# workflow/views.py 添加

class WorkflowVersionViewSet(viewsets.ViewSet):
    """工作流版本管理"""

    def list(self, request, workflow_pk=None):
        """列出所有版本"""
        versions = WorkflowVersion.objects.filter(workflow_id=workflow_pk)
        return Response(VersionSerializer(versions, many=True).data)

    def create(self, request, workflow_pk=None):
        """创建新版本"""
        workflow = Workflow.objects.get(pk=workflow_pk)
        description = request.data.get('description', '')

        version = WorkflowVersionManager.create_version(
            workflow, description, request.user
        )

        return Response(VersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def restore(self, request, workflow_pk=None, pk=None):
        """恢复到指定版本"""
        workflow = Workflow.objects.get(pk=workflow_pk)
        version_number = int(pk)

        workflow = WorkflowVersionManager.restore_version(workflow, version_number)

        return Response({
            'message': f'已恢复到版本 {version_number}',
            'version': version_number
        })


class ExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """执行日志查询"""
    serializer_class = ExecutionLogSerializer

    def get_queryset(self):
        execution_id = self.request.query_params.get('execution_id')
        if execution_id:
            return ExecutionLog.objects.filter(execution_id=execution_id)
        return ExecutionLog.objects.none()
```

### 15.5 前端版本历史组件

```vue
<!-- Frontend/src/components/VersionHistory.vue -->
<template>
  <el-drawer v-model="visible" title="版本历史" size="400px">
    <div class="version-list">
      <div
        v-for="version in versions"
        :key="version.id"
        class="version-item"
        :class="{ active: version.id === currentVersionId }"
      >
        <div class="version-header">
          <span class="version-number">v{{ version.version }}</span>
          <span class="version-date">{{ formatDate(version.created_at) }}</span>
        </div>
        <p class="version-desc">{{ version.description || '无说明' }}</p>
        <div class="version-actions">
          <el-button size="small" @click="preview(version)">预览</el-button>
          <el-button size="small" type="primary" @click="restore(version)">
            恢复此版本
          </el-button>
        </div>
      </div>
    </div>
  </el-drawer>

  <!-- 预览弹窗 -->
  <el-dialog v-model="previewVisible" title="版本预览" width="600px">
    <div v-if="previewVersion" class="preview-content">
      <h4>版本 {{ previewVersion.version }} 快照</h4>
      <pre>{{ JSON.stringify(previewVersion, null, 2) }}</pre>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps(['workflowId'])
const visible = ref(false)
const versions = ref([])
const currentVersionId = ref(null)
const previewVisible = ref(false)
const previewVersion = ref(null)

const formatDate = (date) => {
  return new Date(date).toLocaleString('zh-CN')
}

const loadVersions = async () => {
  // 加载版本列表
}

const preview = (version) => {
  previewVersion.value = version
  previewVisible.value = true
}

const restore = async (version) => {
  // 恢复版本
  ElMessage.success(`已恢复到版本 ${version.version}`)
  visible.value = false
}
</script>
```

---

## Step 16 - 前端完整组件代码

### 16.1 工作流编辑器核心组件

```vue
<!-- Frontend/src/components/workflow/WorkflowEditor.vue -->
<template>
  <div class="workflow-editor">
    <!-- 工具栏 -->
    <div class="editor-toolbar">
      <el-button @click="saveWorkflow" type="primary">保存</el-button>
      <el-button @click="executeWorkflow">执行</el-button>
      <el-button @click="showVersionHistory = true">版本历史</el-button>
      <el-select v-model="selectedModel" placeholder="选择模型" class="model-select">
        <el-option
          v-for="model in availableModels"
          :key="model.id"
          :label="model.name"
          :value="model.id"
        />
      </el-select>
    </div>

    <!-- 画布 -->
    <div class="editor-canvas" ref="canvasRef">
      <!-- 节点 -->
      <div
        v-for="node in nodes"
        :key="node.id"
        class="workflow-node"
        :class="[`node-${node.type}`, { selected: selectedNode?.id === node.id }]"
        :style="{ left: node.position.x + 'px', top: node.position.y + 'px' }"
        @mousedown="onNodeMouseDown($event, node)"
        @click.stop="selectNode(node)"
      >
        <div class="node-header">
          <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
          <span class="node-title">{{ node.name }}</span>
        </div>
        <div class="node-body">
          <span class="node-type">{{ node.type }}</span>
        </div>
        <!-- 连接点 -->
        <div class="handle handle-input" data-handle="input" />
        <div class="handle handle-output" data-handle="output" />
      </div>

      <!-- 边/连线 -->
      <svg class="edges-layer">
        <path
          v-for="edge in edges"
          :key="edge.id"
          :d="getEdgePath(edge)"
          class="workflow-edge"
          :class="{ selected: selectedEdge?.id === edge.id }"
          @click="selectEdge(edge)"
        />
      </svg>
    </div>

    <!-- 节点配置面板 -->
    <div class="node-config-panel" v-if="selectedNode">
      <h3>节点配置</h3>
      <NodeConfigForm
        :node="selectedNode"
        @update="updateNode"
        @delete="deleteNode"
      />
    </div>

    <!-- 节点选择器 -->
    <div class="node-palette">
      <div
        v-for="nodeType in nodeTypes"
        :key="nodeType.type"
        class="palette-item"
        draggable="true"
        @dragstart="onDragStart($event, nodeType)"
      >
        <span class="palette-icon">{{ nodeType.icon }}</span>
        <span>{{ nodeType.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import NodeConfigForm from './NodeConfigForm.vue'

const props = defineProps({
  workflowId: { type: Number, default: null }
})

const emit = defineEmits(['save', 'execute'])

// Store
const workflowStore = useWorkflowStore()

// 状态
const nodes = computed(() => workflowStore.nodes)
const edges = computed(() => workflowStore.edges)
const selectedNode = computed(() => workflowStore.selectedNode)
const selectedEdge = computed(() => workflowStore.selectedEdge)
const availableModels = ref([])

// 节点类型定义
const nodeTypes = [
  { type: 'llm', label: 'LLM 节点', icon: '🤖' },
  { type: 'prompt', label: '提示词', icon: '📝' },
  { type: 'input', label: '输入', icon: '📥' },
  { type: 'output', label: '输出', icon: '📤' },
  { type: 'condition', label: '条件分支', icon: '🔀' },
  { type: 'transform', label: '数据转换', icon: '🔄' },
  { type: 'search', label: '搜索', icon: '🔍' },
  { type: 'code', label: '代码执行', icon: '💻' },
]

// 节点拖拽
const onDragStart = (e, nodeType) => {
  e.dataTransfer.setData('nodeType', JSON.stringify(nodeType))
}

// 节点选择
const selectNode = (node) => {
  workflowStore.setSelectedNode(node)
}

const selectEdge = (edge) => {
  workflowStore.setSelectedEdge(edge)
}

// 更新节点
const updateNode = (nodeId, config) => {
  workflowStore.updateNode(nodeId, config)
}

// 删除节点
const deleteNode = (nodeId) => {
  workflowStore.deleteNode(nodeId)
}

// 保存
const saveWorkflow = async () => {
  await workflowStore.saveWorkflow()
  emit('save')
}

// 执行
const executeWorkflow = async () => {
  emit('execute')
}

// 获取节点图标
const getNodeIcon = (type) => {
  const node = nodeTypes.find(n => n.type === type)
  return node?.icon || '📦'
}

// 获取边的路径
const getEdgePath = (edge) => {
  const sourceNode = nodes.value.find(n => n.id === edge.source)
  const targetNode = nodes.value.find(n => n.id === edge.target)

  if (!sourceNode || !targetNode) return ''

  const sx = sourceNode.position.x + 150
  const sy = sourceNode.position.y + 40
  const tx = targetNode.position.x
  const ty = targetNode.position.y + 40

  return `M ${sx} ${sy} C ${sx + 50} ${sy}, ${tx - 50} ${ty}, ${tx} ${ty}`
}

// 初始化
onMounted(async () => {
  if (props.workflowId) {
    await workflowStore.loadWorkflow(props.workflowId)
  }
  await loadModels()
})

// 加载可用模型
const loadModels = async () => {
  // TODO: 从 API 加载
}

// 节点拖放到画布
const canvasRef = ref(null)
const onCanvasDrop = (e) => {
  const nodeType = JSON.parse(e.dataTransfer.getData('nodeType'))
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  workflowStore.addNode({
    ...nodeType,
    position: { x, y },
    config: {}
  })
}

const onCanvasDragOver = (e) => {
  e.preventDefault()
}
</script>

<style scoped>
.workflow-editor {
  display: flex;
  height: 100vh;
  position: relative;
}

.editor-toolbar {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: white;
  padding: 10px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  display: flex;
  gap: 10px;
  align-items: center;
}

.model-select {
  width: 200px;
}

.editor-canvas {
  flex: 1;
  background: #f5f5f5;
  background-image:
    radial-gradient(circle, #ddd 1px, transparent 1px);
  background-size: 20px 20px;
  position: relative;
  overflow: hidden;
}

.workflow-node {
  position: absolute;
  width: 150px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: move;
  user-select: none;
}

.workflow-node.selected {
  box-shadow: 0 0 0 2px #409eff;
}

.node-header {
  padding: 8px 12px;
  background: #409eff;
  color: white;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-body {
  padding: 8px 12px;
}

.handle {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #67c23a;
  border: 2px solid white;
  border-radius: 50%;
  top: 50%;
  transform: translateY(-50%);
}

.handle-input {
  left: -6px;
}

.handle-output {
  right: -6px;
}

.edges-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.workflow-edge {
  fill: none;
  stroke: #909399;
  stroke-width: 2;
  pointer-events: stroke;
  cursor: pointer;
}

.workflow-edge.selected {
  stroke: #409eff;
}

.node-palette {
  position: absolute;
  left: 10px;
  top: 80px;
  background: white;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.palette-item {
  padding: 8px 12px;
  cursor: move;
  border-radius: 4px;
  margin-bottom: 4px;
}

.palette-item:hover {
  background: #f5f7fa;
}

.node-config-panel {
  position: absolute;
  right: 10px;
  top: 80px;
  width: 300px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}
</style>
```

### 16.2 节点配置表单组件

```vue
<!-- Frontend/src/components/workflow/NodeConfigForm.vue -->
<template>
  <div class="node-config-form">
    <el-form label-width="100px">
      <!-- LLM 节点配置 -->
      <template v-if="node.type === 'llm'">
        <el-form-item label="模型">
          <el-select v-model="config.model_id" placeholder="选择模型" @change="onConfigChange">
            <el-option
              v-for="m in models"
              :key="m.id"
              :label="m.name"
              :value="m.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="系统提示词">
          <el-input
            v-model="config.system_prompt"
            type="textarea"
            :rows="4"
            placeholder="设定 AI 角色..."
            @change="onConfigChange"
          />
        </el-form-item>

        <el-form-item label="温度">
          <el-slider
            v-model="config.temperature"
            :min="0"
            :max="2"
            :step="0.1"
            :marks="{ 0: '0', 1: '1', 2: '2' }"
            @change="onConfigChange"
          />
        </el-form-item>

        <el-form-item label="最大 Token">
          <el-input-number
            v-model="config.max_tokens"
            :min="1"
            :max="32000"
            @change="onConfigChange"
          />
        </el-form-item>
      </template>

      <!-- 提示词节点配置 -->
      <template v-if="node.type === 'prompt'">
        <el-form-item label="模板名称">
          <el-input v-model="config.name" @change="onConfigChange" />
        </el-form-item>

        <el-form-item label="模板内容">
          <el-input
            v-model="config.template"
            type="textarea"
            :rows="6"
            placeholder="使用 {变量名} 占位..."
            @change="onConfigChange"
          />
        </el-form-item>

        <el-form-item label="变量列表">
          <el-tag
            v-for="v in config.variables"
            :key="v"
            closable
            @close="removeVariable(v)"
            class="variable-tag"
          >
            {{ v }}
          </el-tag>
          <el-input
            v-model="newVariable"
            size="small"
            placeholder="输入变量名"
            @keyup.enter="addVariable"
            style="width: 100px; margin-left: 8px;"
          />
        </el-form-item>
      </template>

      <!-- 条件分支配置 -->
      <template v-if="node.type === 'condition'">
        <el-form-item label="条件类型">
          <el-select v-model="config.condition_type" @change="onConfigChange">
            <el-option label="if/else" value="if_else" />
            <el-option label="switch" value="switch" />
          </el-select>
        </el-form-item>

        <el-form-item label="条件表达式">
          <el-input
            v-model="config.expression"
            placeholder="如: output.length > 100"
            @change="onConfigChange"
          />
        </el-form-item>

        <el-form-item label="分支">
          <div v-for="(branch, idx) in config.branches" :key="idx" class="branch-item">
            <el-input v-model="branch.name" placeholder="分支名" @change="onConfigChange" />
            <el-button type="danger" size="small" @click="removeBranch(idx)">删除</el-button>
          </div>
          <el-button @click="addBranch">添加分支</el-button>
        </el-form-item>
      </template>

      <!-- 数据转换配置 -->
      <template v-if="node.type === 'transform'">
        <el-form-item label="转换类型">
          <el-select v-model="config.transform_type" @change="onConfigChange">
            <el-option label="JSON 解析" value="json_parse" />
            <el-option label="字符串替换" value="replace" />
            <el-option label="提取字段" value="pick" />
            <el-option label="合并对象" value="merge" />
          </el-select>
        </el-form-item>

        <el-form-item label="转换配置">
          <el-input
            v-model="config.transform_config"
            type="textarea"
            :rows="4"
            placeholder='{"from": "text", "to": "content"}'
            @change="onConfigChange"
          />
        </el-form-item>
      </template>

      <!-- 通用配置 -->
      <el-form-item label="节点名称">
        <el-input v-model="node.name" @change="onNameChange" />
      </el-form-item>

      <el-form-item label="描述">
        <el-input
          v-model="config.description"
          type="textarea"
          :rows="2"
          @change="onConfigChange"
        />
      </el-form-item>

      <el-divider />

      <el-button type="danger" @click="onDelete">删除节点</el-button>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  node: { type: Object, required: true }
})

const emit = defineEmits(['update', 'delete'])

const config = ref({ ...props.node.config })
const newVariable = ref('')
const models = ref([])

// 监听节点变化
watch(() => props.node, (newNode) => {
  config.value = { ...newNode.config }
}, { deep: true })

// 配置变更
const onConfigChange = () => {
  emit('update', props.node.id, { ...config.value })
}

// 名称变更
const onNameChange = () => {
  emit('update', props.node.id, { name: props.node.name })
}

// 删除节点
const onDelete = () => {
  emit('delete', props.node.id)
}

// 变量操作
const addVariable = () => {
  if (newVariable.value && !config.value.variables?.includes(newVariable.value)) {
    config.value.variables = [...(config.value.variables || []), newVariable.value]
    newVariable.value = ''
    onConfigChange()
  }
}

const removeVariable = (v) => {
  config.value.variables = config.value.variables.filter(item => item !== v)
  onConfigChange()
}

// 分支操作
const addBranch = () => {
  config.value.branches = [...(config.value.branches || []), { name: `分支${config.value.branches?.length + 1 || 1}` }]
  onConfigChange()
}

const removeBranch = (idx) => {
  config.value.branches.splice(idx, 1)
  onConfigChange()
}
</script>

<style scoped>
.node-config-form {
  padding: 10px 0;
}

.variable-tag {
  margin-right: 8px;
  margin-bottom: 4px;
}

.branch-item {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.branch-item .el-input {
  flex: 1;
}
</style>
```

### 16.3 工作流 Store

```javascript
// Frontend/src/stores/workflow.js
import { defineStore } from 'pinia'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    workflowId: null,
    workflowName: '',
    nodes: [],
    edges: [],
    selectedNode: null,
    selectedEdge: null,
    executionHistory: [],
    loading: false,
    saving: false,
  }),

  getters: {
    nodeMap: (state) => {
      const map = {}
      state.nodes.forEach(n => { map[n.id] = n })
      return map
    },

    getNodeById: (state) => (id) => {
      return state.nodes.find(n => n.id === id)
    },

    getOutgoingEdges: (state) => (nodeId) => {
      return state.edges.filter(e => e.source === nodeId)
    },

    getIncomingEdges: (state) => (nodeId) => {
      return state.edges.filter(e => e.target === nodeId)
    },
  },

  actions: {
    // 加载工作流
    async loadWorkflow(id) {
      this.loading = true
      try {
        const response = await axios.get(`${API_BASE}/workflows/${id}/`)
        const data = response.data

        this.workflowId = data.id
        this.workflowName = data.name
        this.nodes = data.nodes
        this.edges = data.edges
      } finally {
        this.loading = false
      }
    },

    // 保存工作流
    async saveWorkflow() {
      this.saving = true
      try {
        const payload = {
          name: this.workflowName,
          nodes: this.nodes,
          edges: this.edges,
        }

        if (this.workflowId) {
          await axios.put(`${API_BASE}/workflows/${this.workflowId}/`, payload)
        } else {
          const response = await axios.post(`${API_BASE}/workflows/`, payload)
          this.workflowId = response.data.id
        }
      } finally {
        this.saving = false
      }
    },

    // 添加节点
    addNode(nodeData) {
      const id = `node_${Date.now()}`
      this.nodes.push({
        id,
        name: nodeData.label || '新节点',
        type: nodeData.type,
        position: nodeData.position,
        config: nodeData.config || {},
      })
      this.selectedNode = this.nodes[this.nodes.length - 1]
    },

    // 更新节点
    updateNode(nodeId, updates) {
      const index = this.nodes.findIndex(n => n.id === nodeId)
      if (index !== -1) {
        this.nodes[index] = { ...this.nodes[index], ...updates }
      }
    },

    // 删除节点
    deleteNode(nodeId) {
      this.nodes = this.nodes.filter(n => n.id !== nodeId)
      this.edges = this.edges.filter(e => e.source !== nodeId && e.target !== nodeId)
      if (this.selectedNode?.id === nodeId) {
        this.selectedNode = null
      }
    },

    // 移动节点
    moveNode(nodeId, position) {
      const node = this.nodes.find(n => n.id === nodeId)
      if (node) {
        node.position = position
      }
    },

    // 添加边
    addEdge(edgeData) {
      const id = `edge_${Date.now()}`
      this.edges.push({
        id,
        source: edgeData.source,
        target: edgeData.target,
        label: edgeData.label || '',
      })
    },

    // 删除边
    deleteEdge(edgeId) {
      this.edges = this.edges.filter(e => e.id !== edgeId)
      if (this.selectedEdge?.id === edgeId) {
        this.selectedEdge = null
      }
    },

    // 选择节点
    setSelectedNode(node) {
      this.selectedNode = node
      this.selectedEdge = null
    },

    // 选择边
    setSelectedEdge(edge) {
      this.selectedEdge = edge
      this.selectedNode = null
    },

    // 清除选择
    clearSelection() {
      this.selectedNode = null
      this.selectedEdge = null
    },

    // 执行工作流
    async executeWorkflow(inputData = {}) {
      if (!this.workflowId) {
        await this.saveWorkflow()
      }

      const response = await axios.post(
        `${API_BASE}/workflows/${this.workflowId}/execute/`,
        { input_data: inputData }
      )

      return response.data
    },

    // 查询执行状态
    async getExecutionStatus(executionId) {
      const response = await axios.get(
        `${API_BASE}/workflows/${this.workflowId}/executions/${executionId}/status/`
      )
      return response.data
    },
  }
})
```

### 16.4 执行结果展示组件

```vue
<!-- Frontend/src/components/workflow/ExecutionResult.vue -->
<template>
  <el-dialog
    v-model="visible"
    title="执行结果"
    width="800px"
    :before-close="handleClose"
  >
    <!-- 执行状态 -->
    <div class="execution-status">
      <el-tag :type="statusType" size="large">
        {{ statusText }}
      </el-tag>
      <span v-if="execution?.duration" class="duration">
        耗时: {{ formatDuration(execution.duration) }}
      </span>
    </div>

    <!-- 执行进度（实时） -->
    <div v-if="status === 'running'" class="progress-section">
      <el-progress
        :percentage="progress"
        :status="progressStatus"
        :stroke-width="20"
      />
      <p class="progress-message">{{ progressMessage }}</p>
    </div>

    <!-- 执行日志 -->
    <el-tabs v-model="activeTab">
      <el-tab-pane label="执行日志" name="logs">
        <div class="log-list">
          <div
            v-for="log in executionLogs"
            :key="log.id"
            class="log-item"
            :class="`log-${log.status}`"
          >
            <span class="log-time">{{ formatTime(log.created_at) }}</span>
            <span class="log-node">{{ log.node_name }}</span>
            <span class="log-status">
              <el-tag size="small" :type="getLogStatusType(log.status)">
                {{ log.status }}
              </el-tag>
            </span>
            <span v-if="log.duration_ms" class="log-duration">
              {{ log.duration_ms }}ms
            </span>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="输入数据" name="input">
        <pre class="json-viewer">{{ JSON.stringify(inputData, null, 2) }}</pre>
      </el-tab-pane>

      <el-tab-pane label="输出数据" name="output">
        <pre class="json-viewer">{{ JSON.stringify(outputData, null, 2) }}</pre>
      </el-tab-pane>

      <el-tab-pane label="节点详情" name="nodes">
        <div class="node-results">
          <el-collapse>
            <el-collapse-item
              v-for="(result, nodeId) in nodeResults"
              :key="nodeId"
              :title="getNodeName(nodeId)"
            >
              <template #title>
                <span>{{ getNodeName(nodeId) }}</span>
                <el-tag size="small" style="margin-left: 10px;">
                  {{ result.duration }}ms
                </el-tag>
              </template>
              <div class="node-result-content">
                <h4>输入</h4>
                <pre>{{ JSON.stringify(result.input, null, 2) }}</pre>
                <h4>输出</h4>
                <pre>{{ JSON.stringify(result.output, null, 2) }}</pre>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button v-if="status === 'failed'" type="primary" @click="retry">
        重试
      </el-button>
      <el-button v-if="status === 'completed'" type="primary" @click="copyOutput">
        复制结果
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  executionId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'retry'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 状态
const execution = ref(null)
const executionLogs = ref([])
const activeTab = ref('logs')
const ws = ref(null)

// 计算属性
const status = computed(() => execution.value?.status || 'pending')

const statusType = computed(() => {
  switch (status.value) {
    case 'completed': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (status.value) {
    case 'completed': return '执行成功'
    case 'failed': return '执行失败'
    case 'running': return '执行中...'
    case 'pending': return '等待中'
    default: return status.value
  }
})

const progress = computed(() => execution.value?.progress || 0)
const progressMessage = computed(() => execution.value?.message || '')
const progressStatus = computed(() => {
  if (progress.value >= 100) return 'success'
  return undefined
})

const inputData = computed(() => execution.value?.input_data || {})
const outputData = computed(() => execution.value?.output_data || {})
const nodeResults = computed(() => execution.value?.node_results || {})

// 方法
const formatDuration = (ms) => {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

const formatTime = (time) => {
  return new Date(time).toLocaleTimeString('zh-CN')
}

const getLogStatusType = (status) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    default: return 'info'
  }
}

const getNodeName = (nodeId) => {
  return execution.value?.nodes?.find(n => n.id === nodeId)?.name || nodeId
}

const handleClose = () => {
  disconnectWebSocket()
  visible.value = false
}

const retry = () => {
  emit('retry')
  visible.value = false
}

const copyOutput = async () => {
  await navigator.clipboard.writeText(JSON.stringify(outputData.value, null, 2))
  ElMessage.success('已复制到剪贴板')
}

// WebSocket 连接
const connectWebSocket = () => {
  if (!props.executionId) return

  ws.value = new WebSocket(`ws://localhost:8000/ws/execution/${props.executionId}/`)

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)

    if (data.type === 'execution_update') {
      execution.value = {
        ...execution.value,
        status: data.status,
        progress: data.progress,
        message: data.message,
      }
    } else if (data.type === 'execution_complete') {
      execution.value = {
        ...execution.value,
        ...data,
      }
      disconnectWebSocket()
    }
  }

  ws.value.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
}

const disconnectWebSocket = () => {
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
}

// 加载执行数据
const loadExecution = async () => {
  if (!props.executionId) return

  try {
    const response = await fetch(`http://localhost:8000/api/executions/${props.executionId}/`)
    execution.value = response.data

    if (status.value === 'running' || status.value === 'pending') {
      connectWebSocket()
    }
  } catch (error) {
    console.error('Failed to load execution:', error)
  }
}

// 监听 visible 变化
watch(visible, (val) => {
  if (val) {
    loadExecution()
  } else {
    disconnectWebSocket()
  }
})
</script>

<style scoped>
.execution-status {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.duration {
  color: #909399;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-message {
  text-align: center;
  color: #909399;
  margin-top: 10px;
}

.log-list {
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.log-item.log-success {
  background: #f0f9eb;
}

.log-item.log-failed {
  background: #fef0f0;
}

.log-time {
  color: #909399;
  font-size: 12px;
}

.log-node {
  flex: 1;
  font-weight: 500;
}

.log-duration {
  color: #909399;
  font-size: 12px;
}

.json-viewer {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
}

.node-result-content h4 {
  margin: 10px 0 5px;
  font-size: 14px;
  color: #606266;
}

.node-result-content pre {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
}
</style>
```

---

## Step 17 - 后端完整 API 实现

### 17.1 完整的 Serializers

```python
# workflow/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Workflow, Node, Edge, WorkflowExecution, WorkflowVersion, ExecutionLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id']


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ['id', 'node_type', 'name', 'config', 'position_x', 'position_y']
        read_only_fields = ['id']


class EdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edge
        fields = ['id', 'source_node', 'target_node', 'label']
        read_only_fields = ['id']


class WorkflowListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    node_count = serializers.SerializerMethodField()
    execution_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'status', 'owner_name',
                  'node_count', 'execution_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_node_count(self, obj):
        return obj.nodes.count()

    def get_execution_count(self, obj):
        return obj.executions.count()


class WorkflowDetailSerializer(serializers.ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    owner = UserSerializer(read_only=True)
    versions = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'status', 'owner',
                  'nodes', 'edges', 'versions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_versions(self, obj):
        return obj.versions.count()


class WorkflowCreateSerializer(serializers.ModelSerializer):
    nodes = serializers.ListField(child=serializers.DictField(), required=False, default=[])
    edges = serializers.ListField(child=serializers.DictField(), required=False, default=[])

    class Meta:
        model = Workflow
        fields = ['name', 'description', 'nodes', 'edges']

    def create(self, validated_data):
        nodes_data = validated_data.pop('nodes', [])
        edges_data = validated_data.pop('edges', [])

        workflow = Workflow.objects.create(**validated_data)

        # 创建节点
        node_id_map = {}
        for node_data in nodes_data:
            node = workflow.nodes.create(
                node_type=node_data.get('node_type'),
                name=node_data.get('name', '新节点'),
                config=node_data.get('config', {}),
                position_x=node_data.get('position_x', 0),
                position_y=node_data.get('position_y', 0),
            )
            node_id_map[node_data.get('id')] = node.id

        # 创建边
        for edge_data in edges_data:
            workflow.edges.create(
                source_node_id=node_id_map.get(edge_data.get('source')),
                target_node_id=node_id_map.get(edge_data.get('target')),
                label=edge_data.get('label', ''),
            )

        return workflow

    def update(self, instance, validated_data):
        nodes_data = validated_data.pop('nodes', None)
        edges_data = validated_data.pop('edges', None)

        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()

        if nodes_data is not None:
            instance.nodes.all().delete()
            node_id_map = {}
            for node_data in nodes_data:
                node = instance.nodes.create(
                    node_type=node_data.get('node_type'),
                    name=node_data.get('name', '新节点'),
                    config=node_data.get('config', {}),
                    position_x=node_data.get('position_x', 0),
                    position_y=node_data.get('position_y', 0),
                )
                node_id_map[node_data.get('id')] = node.id

        if edges_data is not None:
            instance.edges.all().delete()
            for edge_data in edges_data:
                instance.edges.create(
                    source_node_id=node_id_map.get(edge_data.get('source')),
                    target_node_id=node_id_map.get(edge_data.get('target')),
                    label=edge_data.get('label', ''),
                )

        return instance


class ExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionLog
        fields = ['id', 'node_id', 'node_name', 'node_type', 'status',
                  'input_data', 'output_data', 'error_message', 'duration_ms', 'created_at']


class ExecutionListSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = ['id', 'workflow', 'workflow_name', 'status', 'input_data',
                  'created_at', 'duration']
        read_only_fields = ['id', 'created_at']


class ExecutionDetailSerializer(serializers.ModelSerializer):
    logs = ExecutionLogSerializer(many=True, read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = ['id', 'workflow', 'workflow_name', 'status', 'input_data',
                  'output_data', 'error_message', 'logs', 'created_at', 'duration']
        read_only_fields = ['id', 'created_at']


class VersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WorkflowVersion
        fields = ['id', 'version', 'description', 'created_by_name', 'created_at']
```

### 17.2 完整的 Views

```python
# workflow/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Workflow, Node, Edge, WorkflowExecution, WorkflowVersion, ExecutionLog
from .serializers import (
    WorkflowListSerializer, WorkflowDetailSerializer, WorkflowCreateSerializer,
    ExecutionListSerializer, ExecutionDetailSerializer, ExecutionLogSerializer,
    VersionSerializer, NodeSerializer, EdgeSerializer
)
from .tasks import execute_workflow_task
from .services.versioning import WorkflowVersionManager


class WorkflowViewSet(viewsets.ModelViewSet):
    queryset = Workflow.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return WorkflowCreateSerializer
        return WorkflowDetailSerializer

    def get_queryset(self):
        queryset = Workflow.objects.all()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(owner=self.request.user) | Q(is_public=True)
            )

        # 过滤参数
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return queryset.order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """触发工作流执行"""
        workflow = self.get_object()
        input_data = request.data.get('input_data', {})

        if workflow.status != 'published':
            return Response(
                {'error': '工作流未发布，无法执行'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            status='pending',
            input_data=input_data
        )

        task = execute_workflow_task.delay(workflow.id, execution.id, input_data)

        return Response({
            'execution_id': execution.id,
            'task_id': task.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """获取工作流的执行历史"""
        workflow = self.get_object()
        executions = workflow.executions.all().order_by('-created_at')

        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = ExecutionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ExecutionListSerializer(executions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """创建版本快照"""
        workflow = self.get_object()
        description = request.data.get('description', '')

        version = WorkflowVersionManager.create_version(
            workflow, description, request.user
        )

        return Response(VersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """获取版本列表"""
        workflow = self.get_object()
        versions = workflow.versions.all().order_by('-version')

        serializer = VersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore_version(self, request, pk=None):
        """恢复到指定版本"""
        workflow = self.get_object()
        version_number = request.data.get('version')

        if not version_number:
            return Response(
                {'error': '缺少 version 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow = WorkflowVersionManager.restore_version(workflow, version_number)

        return Response({
            'message': f'已恢复到版本 {version_number}',
            'workflow': WorkflowDetailSerializer(workflow).data
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """复制工作流"""
        original = self.get_object()

        new_workflow = Workflow.objects.create(
            name=f"{original.name} (副本)",
            description=original.description,
            owner=request.user,
            status='draft'
        )

        # 复制节点
        node_id_map = {}
        for node in original.nodes.all():
            new_node = new_workflow.nodes.create(
                node_type=node.node_type,
                name=node.name,
                config=node.config,
                position_x=node.position_x,
                position_y=node.position_y,
            )
            node_id_map[node.id] = new_node.id

        # 复制边
        for edge in original.edges.all():
            new_workflow.edges.create(
                source_node_id=node_id_map.get(edge.source_node_id),
                target_node_id=node_id_map.get(edge.target_node_id),
                label=edge.label,
            )

        return Response(
            WorkflowDetailSerializer(new_workflow).data,
            status=status.HTTP_201_CREATED
        )


class ExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowExecution.objects.all()
    serializer_class = ExecutionDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        workflow_id = self.request.query_params.get('workflow_id')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('workflow').order_by('-created_at')

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """获取执行日志"""
        execution = self.get_object()
        logs = execution.logs.all().order_by('created_at')

        serializer = ExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """重试执行"""
        execution = self.get_object()

        if execution.status == 'running':
            return Response(
                {'error': '执行中，无法重试'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.status = 'pending'
        execution.error_message = None
        execution.output_data = {}
        execution.save()

        execution.logs.all().delete()

        task = execute_workflow_task.delay(
            execution.workflow.id,
            execution.id,
            execution.input_data
        )

        return Response({
            'execution_id': execution.id,
            'task_id': task.id,
            'status': 'pending'
        })

    @action(detail=True, methods=['get'])
    def stream(self, request, pk=None):
        """SSE 流式响应（替代 WebSocket）"""
        from django.http import StreamingHttpResponse
        import json

        def event_stream():
            execution = WorkflowExecution.objects.get(pk=pk)

            yield f"data: {json.dumps({'type': 'start', 'execution_id': execution.id})}\n\n"

            while execution.status in ['pending', 'running']:
                execution.refresh_from_db()
                yield f"data: {json.dumps({
                    'type': 'update',
                    'status': execution.status,
                    'progress': execution.progress or 0
                })}\n\n"

                if execution.status not in ['pending', 'running']:
                    break

                import time
                time.sleep(1)

            yield f"data: {json.dumps({
                'type': 'complete',
                'status': execution.status,
                'output': execution.output_data
            })}\n\n"

        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
```

### 17.3 完整的 URLs

```python
# workflow/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'workflows', views.WorkflowViewSet, basename='workflow')
router.register(r'executions', views.ExecutionViewSet, basename='execution')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## Step 18 - 测试文档

### 18.1 后端单元测试

```python
# workflow/tests/test_models.py
from django.test import TestCase
from django.contrib.auth.models import User
from workflow.models import Workflow, Node, Edge, WorkflowExecution, PromptTemplate


class WorkflowModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            description='A test workflow',
            owner=self.user,
            status='draft'
        )

    def test_workflow_creation(self):
        """测试工作流创建"""
        self.assertEqual(self.workflow.name, 'Test Workflow')
        self.assertEqual(self.workflow.owner, self.user)
        self.assertEqual(self.workflow.status, 'draft')

    def test_workflow_str(self):
        """测试工作流字符串表示"""
        self.assertEqual(str(self.workflow), 'Test Workflow')

    def test_workflow_node_relationship(self):
        """测试工作流与节点的关系"""
        node = self.workflow.nodes.create(
            node_type='llm',
            name='Test Node',
            config={'model_id': 'gpt-4'}
        )
        self.assertEqual(self.workflow.nodes.count(), 1)
        self.assertEqual(node.workflow, self.workflow)


class WorkflowExecutionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            owner=self.user
        )
        self.execution = WorkflowExecution.objects.create(
            workflow=self.workflow,
            input_data={'text': 'Hello'}
        )

    def test_execution_status_transitions(self):
        """测试执行状态转换"""
        self.assertEqual(self.execution.status, 'pending')

        self.execution.status = 'running'
        self.execution.save()

        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, 'running')

    def test_execution_output(self):
        """测试执行输出"""
        self.execution.output_data = {'result': 'World'}
        self.execution.status = 'completed'
        self.execution.save()

        self.execution.refresh_from_db()
        self.assertEqual(self.execution.output_data['result'], 'World')


class PromptTemplateTest(TestCase):
    def test_template_rendering(self):
        """测试模板渲染"""
        template = PromptTemplate.objects.create(
            name='Test Template',
            category='translate',
            template='Translate {text} to {lang}',
            variables=['text', 'lang']
        )

        result = template.render({'text': 'Hello', 'lang': 'Chinese'})
        self.assertEqual(result, 'Translate Hello to Chinese')

    def test_template_with_missing_variable(self):
        """测试缺少变量时的渲染"""
        template = PromptTemplate.objects.create(
            name='Test Template',
            template='Hello {name}',
            variables=['name']
        )

        result = template.render({})
        self.assertEqual(result, 'Hello ')
```

### 18.2 后端 API 测试

```python
# workflow/tests/test_api.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from workflow.models import Workflow, Node


class WorkflowAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            description='Test description',
            owner=self.user
        )

    def test_list_workflows(self):
        """测试列出工作流"""
        response = self.client.get('/api/workflows/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_workflow(self):
        """测试创建工作流"""
        data = {
            'name': 'New Workflow',
            'description': 'New description',
            'nodes': [
                {
                    'id': 'node-1',
                    'node_type': 'llm',
                    'name': 'LLM Node',
                    'position_x': 100,
                    'position_y': 100,
                    'config': {}
                }
            ],
            'edges': []
        }
        response = self.client.post('/api/workflows/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), 2)

    def test_update_workflow(self):
        """测试更新工作流"""
        data = {
            'name': 'Updated Workflow',
            'description': 'Updated description'
        }
        response = self.client.patch(
            f'/api/workflows/{self.workflow.id}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.name, 'Updated Workflow')

    def test_delete_workflow(self):
        """测试删除工作流"""
        response = self.client.delete(f'/api/workflows/{self.workflow.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.count(), 0)

    def test_execute_workflow_unpublished(self):
        """测试未发布的工作流无法执行"""
        response = self.client.post(f'/api/workflows/{self.workflow.id}/execute/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_execute_workflow_published(self):
        """测试执行已发布的工作流"""
        self.workflow.status = 'published'
        self.workflow.save()

        response = self.client.post(
            f'/api/workflows/{self.workflow.id}/execute/',
            {'input_data': {'text': 'test'}},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('execution_id', response.data)

    def test_workflow_duplicate(self):
        """测试复制工作流"""
        response = self.client.post(f'/api/workflows/{self.workflow.id}/duplicate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Workflow.objects.count(), 2)
        new_workflow = Workflow.objects.last()
        self.assertIn('副本', new_workflow.name)


class AuthenticationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_unauthenticated_access(self):
        """测试未认证访问"""
        response = self.client.get('/api/workflows/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access(self):
        """测试认证访问"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/workflows/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### 18.3 前端单元测试

```javascript
// Frontend/src/stores/__tests__/workflow.spec.js
import { setActivePinia, createPinia } from 'pinia'
import { useWorkflowStore } from '../workflow'
import { vi } from 'vitest'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

describe('Workflow Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('节点操作', () => {
    it('应该添加节点', () => {
      const store = useWorkflowStore()

      store.addNode({
        type: 'llm',
        label: 'LLM Node',
        position: { x: 100, y: 100 }
      })

      expect(store.nodes.length).toBe(1)
      expect(store.nodes[0].type).toBe('llm')
    })

    it('应该更新节点', () => {
      const store = useWorkflowStore()

      store.addNode({
        type: 'llm',
        label: 'Old Name',
        position: { x: 0, y: 0 }
      })

      const nodeId = store.nodes[0].id
      store.updateNode(nodeId, { name: 'New Name' })

      expect(store.nodes[0].name).toBe('New Name')
    })

    it('应该删除节点', () => {
      const store = useWorkflowStore()

      store.addNode({ type: 'input', label: 'Input' })
      store.addNode({ type: 'output', label: 'Output' })

      const nodeToDelete = store.nodes[0]
      store.deleteNode(nodeToDelete.id)

      expect(store.nodes.length).toBe(1)
      expect(store.nodes.find(n => n.id === nodeToDelete.id)).toBeUndefined()
    })
  })

  describe('边操作', () => {
    it('应该添加边', () => {
      const store = useWorkflowStore()

      store.addNode({ type: 'input', label: 'Input' })
      store.addNode({ type: 'output', label: 'Output' })

      const [inputNode, outputNode] = store.nodes

      store.addEdge({
        source: inputNode.id,
        target: outputNode.id
      })

      expect(store.edges.length).toBe(1)
      expect(store.edges[0].source).toBe(inputNode.id)
    })

    it('删除节点时应该删除相关边', () => {
      const store = useWorkflowStore()

      store.addNode({ type: 'input', label: 'Input' })
      store.addNode({ type: 'llm', label: 'LLM' })
      store.addNode({ type: 'output', label: 'Output' })

      const [input, llm, output] = store.nodes

      store.addEdge({ source: input.id, target: llm.id })
      store.addEdge({ source: llm.id, target: output.id })

      store.deleteNode(llm.id)

      expect(store.edges.length).toBe(0)
    })
  })

  describe('选择操作', () => {
    it('应该选中节点', () => {
      const store = useWorkflowStore()

      store.addNode({ type: 'llm', label: 'LLM' })
      const node = store.nodes[0]

      store.setSelectedNode(node)

      expect(store.selectedNode).toEqual(node)
      expect(store.selectedEdge).toBeNull()
    })

    it('选中边时应该清除节点选择', () => {
      const store = useWorkflowStore()

      store.addNode({ type: 'input', label: 'Input' })
      store.addNode({ type: 'output', label: 'Output' })

      const [input, output] = store.nodes
      store.addEdge({ source: input.id, target: output.id })

      store.setSelectedNode(input)
      store.setSelectedEdge(store.edges[0])

      expect(store.selectedNode).toBeNull()
      expect(store.selectedEdge).not.toBeNull()
    })
  })
})
```

### 18.4 E2E 测试 (Playwright)

```javascript
// Frontend/tests/e2e/workflow.spec.js
import { test, expect } from '@playwright/test'

test.describe('工作流编辑器', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workflow/new')
    await page.waitForLoadState('networkidle')
  })

  test('应该能够创建新工作流', async ({ page }) => {
    // 填写工作流名称
    await page.getByLabel('工作流名称').fill('我的测试工作流')

    // 从面板拖拽节点到画布
    const llmNode = page.locator('.palette-item').filter({ hasText: 'LLM 节点' })
    const canvas = page.locator('.editor-canvas')

    await llmNode.dragTo(canvas)

    // 验证节点已添加
    await expect(page.locator('.workflow-node')).toHaveCount(1)

    // 保存工作流
    await page.getByRole('button', { name: '保存' }).click()

    // 验证保存成功
    await expect(page.locator('.el-message--success')).toBeVisible()
  })

  test('应该能够配置节点', async ({ page }) => {
    // 添加节点
    const llmNode = page.locator('.palette-item').filter({ hasText: 'LLM 节点' })
    await llmNode.dragTo(page.locator('.editor-canvas'))

    // 点击节点打开配置面板
    await page.locator('.workflow-node').first().click()

    // 验证配置面板可见
    await expect(page.locator('.node-config-panel')).toBeVisible()

    // 选择模型
    await page.locator('.node-config-panel').getByLabel('模型').click()
    await page.locator('.el-select-dropdown__item').filter({ hasText: 'GPT-4' }).click()

    // 填写系统提示词
    await page.locator('.node-config-panel').getByLabel('系统提示词').fill('你是一个有用的助手')
  })

  test('应该能够执行工作流', async ({ page }) => {
    // 设置测试环境 - 加载已保存的工作流
    await page.goto('/workflow/1')
    await page.waitForLoadState('networkidle')

    // 点击执行按钮
    await page.getByRole('button', { name: '执行' }).click()

    // 验证执行结果对话框出现
    await expect(page.locator('.el-dialog')).toBeVisible()

    // 等待执行完成（最多 60 秒）
    await expect(page.locator('.el-tag').filter({ hasText: /成功|失败/ }))
      .toBeVisible({ timeout: 60000 })
  })

  test('应该能够查看执行历史', async ({ page }) => {
    await page.goto('/workflow/1')
    await page.waitForLoadState('networkidle')

    // 点击执行历史标签
    await page.getByRole('tab', { name: '执行历史' }).click()

    // 验证历史记录列表
    await expect(page.locator('.execution-item')).toHaveCount(3)
  })
})

test.describe('用户认证', () => {
  test('应该能够注册新用户', async ({ page }) => {
    await page.goto('/register')

    await page.getByLabel('用户名').fill('newuser')
    await page.getByLabel('邮箱').fill('newuser@example.com')
    await page.getByLabel('密码').fill('password123')
    await page.getByLabel('确认密码').fill('password123')

    await page.getByRole('button', { name: '注册' }).click()

    // 验证注册成功并跳转
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('.el-message--success')).toBeVisible()
  })

  test('应该能够登录', async ({ page }) => {
    await page.goto('/login')

    await page.getByLabel('用户名').fill('testuser')
    await page.getByLabel('密码').fill('testpass123')

    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL('/dashboard')
  })
})
```

---

## Step 19 - Nginx + SSL 配置

### 19.1 Nginx 配置文件

```nginx
# /etc/nginx/sites-available/flowly

upstream flowly_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream flowly_websocket {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript
               application/xml application/xml+rss text/javascript application/x-javascript;

    # 静态文件
    location /static/ {
        alias /var/www/flowly/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 媒体文件
    location /media/ {
        alias /var/www/flowly/media/;
        expires 7d;
    }

    # Django 后端
    location /api/ {
        proxy_pass http://flowly_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 文件上传大小
        client_max_body_size 50M;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://flowly_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_read_timeout 86400;
    }

    # 前端静态文件
    location / {
        root /var/www/flowly/frontend/dist;
        try_files $uri $uri/ /index.html;

        # 缓存 HTML（不缓存）
        location ~* \.html$ {
            expires -1;
            add_header Cache-Control "no-store, no-cache, must-revalidate";
        }

        # 缓存静态资源
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # 健康检查
    location /health/ {
        proxy_pass http://flowly_backend;
        access_log off;
    }

    # 日志
    access_log /var/log/nginx/flowly_access.log;
    error_log /var/log/nginx/flowly_error.log;
}
```

### 19.2 SSL 证书配置 (Let's Encrypt)

```bash
# 安装 Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run

# 设置定时续期（如果需要）
sudo crontab -e
# 添加: 0 0 * * * certbot renew --quiet
```

### 19.3 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Django 后端
  backend:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    container_name: flowly_backend
    restart: unless-stopped
    environment:
      - DEBUG=False
      - DATABASE_URL=mysql://user:password@db:3306/flowly
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./Backend:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
    depends_on:
      - db
      - redis
    networks:
      - flowly_network

  # Celery Worker
  celery:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    container_name: flowly_celery
    command: celery -A config worker -l INFO
    restart: unless-stopped
    environment:
      - DEBUG=False
      - DATABASE_URL=mysql://user:password@db:3306/flowly
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./Backend:/app
    depends_on:
      - db
      - redis
    networks:
      - flowly_network

  # Celery Beat (定时任务)
  celery_beat:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    container_name: flowly_celery_beat
    command: celery -A config beat -l INFO
    restart: unless-stopped
    environment:
      - DATABASE_URL=mysql://user:password@db:3306/flowly
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./Backend:/app
    depends_on:
      - redis
    networks:
      - flowly_network

  # Vue 前端
  frontend:
    image: nginx:alpine
    container_name: flowly_frontend
    restart: unless-stopped
    volumes:
      - ./Frontend/dist:/usr/share/nginx/html:ro
      - ./Frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    networks:
      - flowly_network

  # MySQL 数据库
  db:
    image: mysql:8.0
    container_name: flowly_db
    restart: unless-stopped
    environment:
      - MYSQL_DATABASE=flowly
      - MYSQL_USER=user
      - MYSQL_PASSWORD=password
      - MYSQL_ROOT_PASSWORD=rootpassword
    volumes:
      - db_data:/var/lib/mysql
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - flowly_network

  # Redis 缓存/队列
  redis:
    image: redis:7-alpine
    container_name: flowly_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    networks:
      - flowly_network

volumes:
  db_data:
  redis_data:
  static_volume:
  media_volume:

networks:
  flowly_network:
    driver: bridge
```

### 19.4 Dockerfile (后端)

```dockerfile
# Backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 收集静态文件
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# 运行
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "config.wsgi:application"]
```

---

## Step 20 - 数据库优化

### 20.1 索引优化

```sql
-- workflow/models.py 中添加索引

class Meta:
    indexes = [
        # 工作流索引
        models.Index(fields=['owner', 'status']),           # 按用户和状态查询
        models.Index(fields=['-updated_at']),                # 最新更新排序
        models.Index(fields=['status', '-created_at']),      # 按状态查询最新

        # 执行记录索引
        models.Index(fields=['workflow', '-created_at']),     # 工作流执行历史
        models.Index(fields=['status', '-created_at']),      # 待处理的执行
        models.Index(fields=['celery_task_id']),            # 任务查询

        # 日志索引
        models.Index(fields=['execution', 'created_at']),    # 执行日志
    ]
```

### 20.2 数据库配置优化

```python
# config/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'flowly',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'isolation_level': 'repeatable read',
        },
        'CONN_MAX_AGE': 600,  # 连接池，10 分钟
    }
}

# 读写分离配置（如果需要）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'flowly',
        ...
    },
    'replica': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'flowly',
        'HOST': 'localhost',
        ...
    }
}

# Database Router
class FlowlyRouter:
    """读写分离路由"""
    def db_for_read(self, model, **hints):
        return 'replica'

    def db_for_write(self, model, **hints):
        return 'default'
```

### 20.3 查询优化建议

```python
# 使用 select_related 和 prefetch_related 减少查询

# workflow/views.py

class WorkflowViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Workflow.objects.select_related('owner').prefetch_related(
            'nodes',
            'edges',
            Prefetch(
                'executions',
                queryset=WorkflowExecution.objects.order_by('-created_at')[:10]
            )
        )

# 使用 only 减少数据传输
def get_queryset(self):
    return Workflow.objects.only(
        'id', 'name', 'description', 'status', 'owner__username',
        'created_at', 'updated_at'
    )

# 使用 defer 延迟加载大字段
def get_queryset(self):
    return Workflow.objects.defer('config', 'extra_data')

# 分页大查询
def get_queryset(self):
    return Workflow.objects.paginate(page=1, per_page=50)
```

### 20.4 缓存策略

```python
# config/settings.py

# Redis 缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 缓存超时（秒）
CACHE_TTL = 60 * 15  # 15 分钟

# 缓存视图
from django.views.decorators.cache import cache_page

@cache_page(CACHE_TTL)
def list_workflows(request):
    ...

# 缓存模型查询
from django.core.cache import cache

def get_workflow_with_cache(workflow_id):
    cache_key = f'workflow:{workflow_id}'
    data = cache.get(cache_key)

    if data is None:
        workflow = Workflow.objects.get(pk=workflow_id)
        data = WorkflowDetailSerializer(workflow).data
        cache.set(cache_key, data, CACHE_TTL)

    return data
```

---

## Step 21 - 安全加固方案

### 21.1 Django 安全配置

```python
# config/settings.py

# 安全设置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = True

# HSTS 设置
SECURE_HSTS_SECONDS = 31536000  # 1 年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie 设置
SESSION_COOKIE_AGE = 60 * 60 * 24  # 24 小时
SESSION_COOKIE_SAMESITE = 'Lax'
```

### 21.2 API 限流

```python
# config/settings.py

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'execution': '10/minute',
    }
}

# workflow/views.py

from rest_framework.throttling import ScopedRateThrottle

class WorkflowExecutionViewSet(viewsets.ModelViewSet):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'execution'
```

### 21.3 输入验证

```python
# workflow/serializers.py

class WorkflowCreateSerializer(serializers.ModelSerializer):
    # 严格验证节点数据
    nodes = serializers.ListField(
        child=serializers.DictField(),
        max_length=100,  # 限制节点数量
        allow_empty=False
    )

    def validate_nodes(self, value):
        """验证节点数据"""
        node_ids = set()
        for node in value:
            # 验证节点类型
            if node.get('node_type') not in VALID_NODE_TYPES:
                raise serializers.ValidationError(
                    f"无效的节点类型: {node.get('node_type')}"
                )

            # 检查 ID 唯一性
            node_id = node.get('id')
            if node_id in node_ids:
                raise serializers.ValidationError(
                    f"重复的节点 ID: {node_id}"
                )
            node_ids.add(node_id)

            # 验证位置
            pos = node.get('position', {})
            if pos.get('x', 0) < 0 or pos.get('y', 0) < 0:
                raise serializers.ValidationError("节点位置不能为负数")

        return value

    def validate(self, attrs):
        """验证边数据"""
        nodes = attrs.get('nodes', [])
        edges = attrs.get('edges', [])

        node_ids = {n.get('id') for n in nodes}

        for edge in edges:
            if edge.get('source') not in node_ids:
                raise serializers.ValidationError({
                    'edges': f"边的源节点不存在: {edge.get('source')}"
                })
            if edge.get('target') not in node_ids:
                raise serializers.ValidationError({
                    'edges': f"边的目标节点不存在: {edge.get('target')}"
                })

        return attrs
```

### 21.4 审计日志

```python
# workflow/middleware.py

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 只记录 API 请求
        if request.path.startswith('/api/'):
            self.log_request(request, response)

        return response

    def log_request(self, request, response):
        from .models import AuditLog

        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            method=request.method,
            path=request.path,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            status_code=response.status_code,
        )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


# workflow/models.py

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    status_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
```

---

## Step 22 - CI/CD 流水线

### 22.1 GitHub Actions 工作流

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.12'
  NODE_VERSION: '20'

jobs:
  # 后端测试
  backend-test:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: rootpassword
          MYSQL_DATABASE: flowly_test
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: Install Python dependencies
        run: |
          cd Backend
          pip install -r requirements.txt

      - name: Run migrations
        env:
          DATABASE_URL: mysql://root:rootpassword@127.0.0.1:3306/flowly_test
          REDIS_URL: redis://127.0.0.1:6379/0
        run: |
          cd Backend
          python manage.py migrate

      - name: Run backend tests
        env:
          DATABASE_URL: mysql://root:rootpassword@127.0.0.1:3306/flowly_test
          REDIS_URL: redis://127.0.0.1:6379/0
        run: |
          cd Backend
          pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./Backend/coverage.xml

  # 前端测试
  frontend-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Cache node_modules
        uses: actions/cache@v4
        with:
          path: Frontend/node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

      - name: Install dependencies
        run: |
          cd Frontend
          npm ci

      - name: Run linter
        run: |
          cd Frontend
          npm run lint

      - name: Run tests
        run: |
          cd Frontend
          npm run test:unit

      - name: Run E2E tests
        uses: cypress-io/github-action@v6
        with:
          working-directory: Frontend

  # 构建和部署
  build-and-deploy:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Build backend
        run: |
          cd Backend
          pip install -r requirements.txt
          python manage.py collectstatic --noinput

      - name: Build frontend
        run: |
          cd Frontend
          npm ci
          npm run build

      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /var/www/flowly
            git pull
            docker-compose down
            docker-compose build
            docker-compose up -d
            docker-compose exec backend python manage.py migrate
            docker-compose exec backend python manage.py collectstatic --noinput
```

### 22.2 requirements.txt

```
# Backend/requirements.txt
Django>=4.2,<5.0
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.3.0
django-cors-headers>=4.3.0
channels>=4.0.0
channels-redis>=4.1.0
daphne>=4.0.0
celery>=5.3.0
redis>=5.0.0
mysqlclient>=2.2.0
python-dotenv>=1.0.0
gunicorn>=21.2.0
langchain>=0.1.0
openai>=1.0.0
anthropic>=0.7.0
pydantic>=2.0.0
python-magic>=0.4.27
```

### 22.3 pytest 配置

```ini
# Backend/pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## Step 23 - 拖拽编辑器增强

### 23.1 增强版工作流编辑器

```vue
<!-- Frontend/src/components/workflow/EnhancedWorkflowEditor.vue -->
<template>
  <div class="workflow-editor" @keydown="handleKeyDown" tabindex="0" ref="editorRef">
    <!-- 顶部工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <el-button-group>
          <el-button @click="undo" :disabled="!canUndo">撤销</el-button>
          <el-button @click="redo" :disabled="!canRedo">重做</el-button>
        </el-button-group>
        <el-divider direction="vertical" />
        <el-button @click="zoomIn">放大</el-button>
        <el-button @click="zoomOut">缩小</el-button>
        <el-button @click="fitView">适应画布</el-button>
        <span class="zoom-level">{{ Math.round(zoom * 100) }}%</span>
      </div>
      <div class="toolbar-center">
        <el-input v-model="workflowName" class="workflow-name-input" />
      </div>
      <div class="toolbar-right">
        <el-button @click="autoArrange">自动排列</el-button>
        <el-button @click="showMinimap = !showMinimap">小地图</el-button>
        <el-button @click="saveWorkflow" type="primary">保存</el-button>
        <el-button @click="publishWorkflow">发布</el-button>
      </div>
    </div>

    <!-- 主画布区域 -->
    <div class="canvas-container">
      <!-- 左侧节点面板 -->
      <div class="node-panel" :class="{ collapsed: panelCollapsed }">
        <div class="panel-header">
          <h4>组件</h4>
          <el-button text @click="panelCollapsed = !panelCollapsed">
            {{ panelCollapsed ? '»' : '«' }}
          </el-button>
        </div>
        <div v-if="!panelCollapsed" class="panel-content">
          <!-- 搜索节点 -->
          <el-input
            v-model="nodeSearch"
            placeholder="搜索节点..."
            prefix-icon="Search"
            clearable
          />

          <!-- 节点分类 -->
          <el-collapse v-model="activeCategories">
            <el-collapse-item
              v-for="category in nodeCategories"
              :key="category.name"
              :title="category.name"
            >
              <div
                v-for="node in category.nodes"
                :key="node.type"
                class="palette-item"
                :class="{ disabled: !node.enabled }"
                draggable="true"
                @dragstart="onDragStart($event, node)"
                @dblclick="addNodeToCanvas(node)"
              >
                <span class="node-icon">{{ node.icon }}</span>
                <span class="node-label">{{ node.label }}</span>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- 画布 -->
      <div
        class="canvas"
        ref="canvasRef"
        @drop="onDrop"
        @dragover="onDragOver"
        @mousedown="onCanvasMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @wheel="onWheel"
      >
        <!-- 网格背景 -->
        <div class="grid-background" :style="gridStyle" />

        <!-- 节点容器 -->
        <div class="nodes-container" :style="transformStyle">
          <div
            v-for="node in nodes"
            :key="node.id"
            class="workflow-node"
            :class="[
              `node-${node.type}`,
              {
                selected: selectedNode?.id === node.id,
                running: runningNodes.includes(node.id),
                error: errorNodes.includes(node.id),
                collapsed: node.collapsed
              }
            ]"
            :style="{ left: node.position.x + 'px', top: node.position.y + 'px' }"
            @mousedown.stop="onNodeMouseDown($event, node)"
            @dblclick="openNodeConfig(node)"
          >
            <!-- 节点头部 -->
            <div class="node-header">
              <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
              <span class="node-title">{{ node.name }}</span>
              <el-dropdown trigger="click" @command="onNodeCommand($event, node)">
                <el-button text size="small">⋮</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="copy">复制</el-dropdown-item>
                    <el-dropdown-item command="paste">粘贴</el-dropdown-item>
                    <el-dropdown-item command="duplicate">克隆</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <!-- 节点内容（可折叠） -->
            <div v-if="!node.collapsed" class="node-body">
              <div class="node-preview">{{ getNodePreview(node) }}</div>
            </div>

            <!-- 连接点 -->
            <div
              v-for="handle in getNodeHandles(node)"
              :key="handle.id"
              class="handle"
              :class="[`handle-${handle.type}`, { connected: handle.connected }]"
              :style="handle.style"
              @mouseup="onHandleMouseUp($event, node, handle)"
            />
          </div>

          <!-- 边/连线 -->
          <svg class="edges-layer" :style="{ width: canvasSize.width, height: canvasSize.height }">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#409eff" />
              </marker>
            </defs>
            <g v-for="edge in edges" :key="edge.id">
              <path
                :d="getEdgePath(edge)"
                class="workflow-edge"
                :class="{ selected: selectedEdge?.id === edge.id }"
                marker-end="url(#arrowhead)"
                @click="selectEdge(edge)"
              />
              <text
                v-if="edge.label"
                :x="getEdgeMidPoint(edge).x"
                :y="getEdgeMidPoint(edge).y - 10"
                class="edge-label"
              >
                {{ edge.label }}
              </text>
            </g>
            <!-- 临时边（拖拽中） -->
            <path
              v-if="tempEdge"
              :d="tempEdge.path"
              class="workflow-edge temp-edge"
            />
          </svg>
        </div>

        <!-- 小地图 -->
        <div v-if="showMinimap" class="minimap">
          <div class="minimap-viewport" :style="minimapViewportStyle" />
          <div
            v-for="node in nodes"
            :key="node.id"
            class="minimap-node"
            :style="{
              left: (node.position.x / canvasSize.width * 100) + '%',
              top: (node.position.y / canvasSize.height * 100) + '%'
            }"
            @click="focusNode(node)"
          />
        </div>
      </div>

      <!-- 右侧配置面板 -->
      <div class="config-panel" :class="{ collapsed: configPanelCollapsed }">
        <div class="panel-header">
          <el-button text @click="configPanelCollapsed = !configPanelCollapsed">
            {{ configPanelCollapsed ? '»' : '«' }}
          </el-button>
          <h4>{{ selectedNode ? '节点配置' : '工作流设置' }}</h4>
        </div>
        <div v-if="!configPanelCollapsed" class="panel-content">
          <NodeConfigPanel
            v-if="selectedNode"
            :node="selectedNode"
            @update="updateNode"
            @close="selectedNode = null"
          />
          <WorkflowSettingsPanel
            v-else
            :workflow="workflow"
            @update="updateWorkflow"
          />
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <span>节点: {{ nodes.length }}</span>
      <span>边: {{ edges.length }}</span>
      <span v-if="executionStatus">执行状态: {{ executionStatus }}</span>
      <span class="auto-save-status">{{ autoSaveStatus }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import NodeConfigPanel from './NodeConfigPanel.vue'
import WorkflowSettingsPanel from './WorkflowSettingsPanel.vue'

const props = defineProps({
  workflowId: { type: Number, default: null }
})

const emit = defineEmits(['save', 'execute'])

// Store
const store = useWorkflowStore()

// Refs
const editorRef = ref(null)
const canvasRef = ref(null)

// 状态
const workflowName = ref('')
const zoom = ref(1)
const pan = reactive({ x: 0, y: 0 })
const selectedNode = ref(null)
const selectedEdge = ref(null)
const panelCollapsed = ref(false)
const configPanelCollapsed = ref(false)
const showMinimap = ref(false)
const nodeSearch = ref('')
const activeCategories = ref(['input', 'llm'])

// 历史记录（撤销/重做）
const history = ref([])
const historyIndex = ref(-1)
const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.value.length - 1)

// 临时边（拖拽连接）
const tempEdge = ref(null)

// 拖拽状态
const isDragging = ref(false)
const isPanning = ref(false)
const dragStart = reactive({ x: 0, y: 0 })

// 自动保存
const autoSaveStatus = ref('')
let autoSaveTimer = null

// 节点分类
const nodeCategories = [
  {
    name: '输入',
    nodes: [
      { type: 'input_text', label: '文本输入', icon: '📝', enabled: true },
      { type: 'input_file', label: '文件上传', icon: '📁', enabled: true },
      { type: 'input_variable', label: '变量', icon: '🔢', enabled: true },
    ]
  },
  {
    name: 'LLM',
    nodes: [
      { type: 'llm_chat', label: '对话模型', icon: '💬', enabled: true },
      { type: 'llm_completion', label: '补全模型', icon: '✍️', enabled: true },
    ]
  },
  {
    name: '数据处理',
    nodes: [
      { type: 'template', label: '模板', icon: '📋', enabled: true },
      { type: 'code', label: '代码', icon: '💻', enabled: true },
      { type: 'json', label: 'JSON处理', icon: '{ }', enabled: true },
      { type: 'transform', label: '数据转换', icon: '🔄', enabled: true },
    ]
  },
  {
    name: '输出',
    nodes: [
      { type: 'output_text', label: '文本输出', icon: '📤', enabled: true },
      { type: 'output_file', label: '文件下载', icon: '💾', enabled: true },
    ]
  },
]

// 计算属性
const nodes = computed(() => store.nodes)
const edges = computed(() => store.edges)
const workflow = computed(() => store.workflow)
const runningNodes = computed(() => store.runningNodes)
const errorNodes = computed(() => store.errorNodes)
const executionStatus = computed(() => store.executionStatus)

const canvasSize = computed(() => ({
  width: 4000,
  height: 4000
}))

const transformStyle = computed(() => ({
  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom.value})`,
  transformOrigin: '0 0'
}))

const gridStyle = computed(() => ({
  backgroundSize: `${20 * zoom.value}px ${20 * zoom.value}px`,
  backgroundPosition: `${pan.x}px ${pan.y}px`
}))

const minimapViewportStyle = computed(() => ({
  left: `${-pan.x / canvasSize.value.width * 100}%`,
  top: `${-pan.y / canvasSize.value.height * 100}%`,
  width: `${100 / zoom.value}%`,
  height: `${100 / zoom.value}%`
}))

// 方法

// 缩放
const zoomIn = () => {
  zoom.value = Math.min(2, zoom.value + 0.1)
}

const zoomOut = () => {
  zoom.value = Math.max(0.5, zoom.value - 0.1)
}

const fitView = () => {
  zoom.value = 1
  pan.x = 0
  pan.y = 0
}

const onWheel = (e) => {
  if (e.ctrlKey) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    zoom.value = Math.max(0.5, Math.min(2, zoom.value + delta))
  }
}

// 平移
const onCanvasMouseDown = (e) => {
  if (e.button === 1 || (e.button === 0 && e.target === canvasRef.value)) {
    isPanning.value = true
    dragStart.x = e.clientX - pan.x
    dragStart.y = e.clientY - pan.y
  }
}

const onMouseMove = (e) => {
  if (isPanning.value) {
    pan.x = e.clientX - dragStart.x
    pan.y = e.clientY - dragStart.y
  }
}

const onMouseUp = () => {
  isPanning.value = false
  isDragging.value = false
}

// 节点操作
const onNodeMouseDown = (e, node) => {
  if (e.button === 0) {
    isDragging.value = true
    const startX = e.clientX
    const startY = e.clientY
    const origPos = { ...node.position }

    const onMove = (moveEvent) => {
      const dx = (moveEvent.clientX - startX) / zoom.value
      const dy = (moveEvent.clientY - startY) / zoom.value
      node.position.x = origPos.x + dx
      node.position.y = origPos.y + dy
    }

    const onUp = () => {
      isDragging.value = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      saveHistory()
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }
}

const selectNode = (node) => {
  selectedNode.value = node
  selectedEdge.value = null
  store.setSelectedNode(node)
}

const selectEdge = (edge) => {
  selectedEdge.value = edge
  selectedNode.value = null
  store.setSelectedEdge(edge)
}

const openNodeConfig = (node) => {
  selectedNode.value = node
}

const updateNode = (nodeId, config) => {
  store.updateNode(nodeId, config)
  saveHistory()
}

// 拖拽创建节点
const onDragStart = (e, nodeType) => {
  e.dataTransfer.setData('nodeType', JSON.stringify(nodeType))
}

const onDragOver = (e) => {
  e.preventDefault()
}

const onDrop = (e) => {
  e.preventDefault()
  const nodeType = JSON.parse(e.dataTransfer.getData('nodeType'))
  const rect = canvasRef.value.getBoundingClientRect()
  const x = (e.clientX - rect.left - pan.x) / zoom.value
  const y = (e.clientY - rect.top - pan.y) / zoom.value

  store.addNode({
    ...nodeType,
    position: { x, y }
  })
  saveHistory()
}

const addNodeToCanvas = (nodeType) => {
  const x = (-pan.x + 400) / zoom.value
  const y = (-pan.y + 200) / zoom.value

  store.addNode({
    ...nodeType,
    position: { x, y }
  })
  saveHistory()
}

// 连接线
const getNodeHandles = (node) => {
  return [
    { id: 'input', type: 'input', connected: hasConnectedEdge(node.id, 'target'), style: { left: '-6px', top: '50%' } },
    { id: 'output', type: 'output', connected: hasConnectedEdge(node.id, 'source'), style: { right: '-6px', top: '50%' } },
  ]
}

const hasConnectedEdge = (nodeId, type) => {
  return edges.value.some(e => type === 'source' ? e.source === nodeId : e.target === nodeId)
}

const onHandleMouseUp = (e, node, handle) => {
  // 实现连接逻辑
}

const getEdgePath = (edge) => {
  const sourceNode = nodes.value.find(n => n.id === edge.source)
  const targetNode = nodes.value.find(n => n.id === edge.target)
  if (!sourceNode || !targetNode) return ''

  const sx = sourceNode.position.x + 150
  const sy = sourceNode.position.y + 40
  const tx = targetNode.position.x
  const ty = targetNode.position.y + 40

  const controlOffset = Math.min(100, Math.abs(tx - sx) / 2)
  return `M ${sx} ${sy} C ${sx + controlOffset} ${sy}, ${tx - controlOffset} ${ty}, ${tx} ${ty}`
}

const getEdgeMidPoint = (edge) => {
  const sourceNode = nodes.value.find(n => n.id === edge.source)
  const targetNode = nodes.value.find(n => n.id === edge.target)
  if (!sourceNode || !targetNode) return { x: 0, y: 0 }

  return {
    x: (sourceNode.position.x + 150 + targetNode.position.x) / 2,
    y: (sourceNode.position.y + targetNode.position.y) / 2 + 40
  }
}

// 节点命令
const onNodeCommand = (command, node) => {
  switch (command) {
    case 'copy':
      store.copyNode(node.id)
      break
    case 'paste':
      store.pasteNode()
      break
    case 'duplicate':
      store.duplicateNode(node.id)
      saveHistory()
      break
    case 'delete':
      store.deleteNode(node.id)
      saveHistory()
      break
  }
}

const getNodeIcon = (type) => {
  for (const cat of nodeCategories) {
    const node = cat.nodes.find(n => n.type === type)
    if (node) return node.icon
  }
  return '📦'
}

const getNodePreview = (node) => {
  if (node.type === 'llm_chat') return node.config?.model || 'GPT-4'
  if (node.type === 'template') return node.config?.template?.slice(0, 30) || '空模板'
  return node.type
}

// 历史记录
const saveHistory = () => {
  const state = JSON.stringify({ nodes: nodes.value, edges: edges.value })
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(state)
  historyIndex.value = history.value.length - 1
}

const undo = () => {
  if (canUndo.value) {
    historyIndex.value--
    const state = JSON.parse(history.value[historyIndex.value])
    store.setState(state)
  }
}

const redo = () => {
  if (canRedo.value) {
    historyIndex.value++
    const state = JSON.parse(history.value[historyIndex.value])
    store.setState(state)
  }
}

const handleKeyDown = (e) => {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'z' && !e.shiftKey) {
      e.preventDefault()
      undo()
    } else if (e.key === 'z' && e.shiftKey || e.key === 'y') {
      e.preventDefault()
      redo()
    } else if (e.key === 'c') {
      if (selectedNode.value) store.copyNode(selectedNode.value.id)
    } else if (e.key === 'v') {
      store.pasteNode()
      saveHistory()
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
      if (selectedNode.value) {
        store.deleteNode(selectedNode.value.id)
        selectedNode.value = null
        saveHistory()
      }
    } else if (e.key === 's') {
      e.preventDefault()
      saveWorkflow()
    }
  }
}

// 自动排列
const autoArrange = () => {
  // 简单的层级布局算法
  const levels = {}
  const visited = new Set()

  const assignLevel = (nodeId, level) => {
    if (visited.has(nodeId)) return
    visited.add(nodeId)

    if (!levels[level]) levels[level] = []
    levels[level].push(nodeId)

    const outgoing = edges.value.filter(e => e.source === nodeId)
    outgoing.forEach(e => assignLevel(e.target, level + 1))
  }

  // 找到根节点（没有输入边的节点）
  const rootNodes = nodes.value.filter(n =>
    !edges.value.some(e => e.target === n.id)
  )
  rootNodes.forEach(n => assignLevel(n.id, 0))

  // 为未访问的节点分配级别
  nodes.value.forEach(n => {
    if (!visited.has(n.id)) {
      assignLevel(n.id, 0)
    }
  })

  // 应用布局
  const nodeWidth = 200
  const nodeHeight = 100
  const gapX = 100
  const gapY = 50

  Object.entries(levels).forEach(([level, nodeIds]) => {
    nodeIds.forEach((nodeId, idx) => {
      const node = nodes.value.find(n => n.id === nodeId)
      if (node) {
        node.position.x = parseInt(level) * (nodeWidth + gapX) + 100
        node.position.y = idx * (nodeHeight + gapY) + 100
      }
    })
  })

  saveHistory()
}

// 自动保存
const saveWorkflow = async () => {
  autoSaveStatus.value = '保存中...'
  try {
    await store.saveWorkflow()
    autoSaveStatus.value = `已保存 ${new Date().toLocaleTimeString()}`
  } catch (error) {
    autoSaveStatus.value = '保存失败'
  }
}

// 生命周期
onMounted(() => {
  editorRef.value?.focus()
  if (props.workflowId) {
    store.loadWorkflow(props.workflowId).then(() => {
      workflowName.value = store.workflowName
    })
  }
  saveHistory()

  // 自动保存定时器
  autoSaveTimer = setInterval(() => {
    saveWorkflow()
  }, 30000) // 每 30 秒
})

onUnmounted(() => {
  if (autoSaveTimer) clearInterval(autoSaveTimer)
})
</script>

<style scoped>
.workflow-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  outline: none;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  gap: 20px;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workflow-name-input {
  width: 200px;
}

.zoom-level {
  font-size: 12px;
  color: #909399;
}

.canvas-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.node-panel, .config-panel {
  width: 280px;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
}

.config-panel {
  border-right: none;
  border-left: 1px solid #e4e7ed;
}

.panel-collapsed {
  width: 40px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.panel-header h4 {
  margin: 0;
  font-size: 14px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 4px;
  cursor: move;
  margin-bottom: 4px;
}

.palette-item:hover {
  background: #f5f7fa;
}

.palette-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.node-icon {
  font-size: 18px;
}

.canvas {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #fafafa;
  cursor: grab;
}

.canvas:active {
  cursor: grabbing;
}

.grid-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 200%;
  height: 200%;
  background-image:
    radial-gradient(circle, #ddd 1px, transparent 1px);
  pointer-events: none;
}

.nodes-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.workflow-node {
  position: absolute;
  width: 150px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: move;
  user-select: none;
  transition: box-shadow 0.2s;
}

.workflow-node:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.workflow-node.selected {
  box-shadow: 0 0 0 2px #409eff;
}

.workflow-node.running {
  box-shadow: 0 0 0 2px #e6a23c;
  animation: pulse 1s infinite;
}

.workflow-node.error {
  box-shadow: 0 0 0 2px #f56c6c;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #409eff;
  color: white;
  border-radius: 8px 8px 0 0;
}

.node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-body {
  padding: 8px 12px;
  font-size: 12px;
  color: #606266;
}

.handle {
  position: absolute;
  width: 12px;
  height: 12px;
  background: white;
  border: 2px solid #409eff;
  border-radius: 50%;
  transform: translateY(-50%);
  cursor: crosshair;
  z-index: 10;
}

.handle-input {
  left: -6px;
}

.handle-output {
  right: -6px;
}

.handle.connected {
  background: #67c23a;
  border-color: #67c23a;
}

.edges-layer {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.workflow-edge {
  fill: none;
  stroke: #909399;
  stroke-width: 2;
  pointer-events: stroke;
  cursor: pointer;
}

.workflow-edge.selected {
  stroke: #409eff;
  stroke-width: 3;
}

.workflow-edge.temp-edge {
  stroke-dasharray: 5, 5;
  stroke: #409eff;
}

.edge-label {
  font-size: 12px;
  fill: #606266;
  text-anchor: middle;
}

.minimap {
  position: absolute;
  right: 20px;
  bottom: 20px;
  width: 200px;
  height: 150px;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.minimap-viewport {
  position: absolute;
  border: 2px solid #409eff;
  background: rgba(64, 158, 255, 0.1);
  pointer-events: none;
}

.minimap-node {
  position: absolute;
  width: 8px;
  height: 4px;
  background: #409eff;
  border-radius: 2px;
}

.status-bar {
  display: flex;
  gap: 20px;
  padding: 8px 20px;
  background: #fafafa;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #606266;
}

.auto-save-status {
  margin-left: auto;
  color: #909399;
}
</style>
```

---

## Step 24 - 变量与上下文管理

### 24.1 变量系统设计

```javascript
// Frontend/src/stores/variables.js
import { defineStore } from 'pinia'

export const useVariableStore = defineStore('variables', {
  state: () => ({
    // 全局变量
    globalVariables: [],
    // 工作流级变量
    workflowVariables: [],
    // 环境变量
    environments: {
      development: {},
      production: {}
    },
    currentEnvironment: 'development',
  }),

  getters: {
    allVariables: (state) => {
      return [...state.globalVariables, ...state.workflowVariables]
    },

    activeVariables: (state) => {
      const env = state.environments[state.currentEnvironment] || {}
      return [
        ...state.globalVariables,
        ...state.workflowVariables,
        ...Object.entries(env).map(([key, value]) => ({
          name: key,
          value,
          type: typeof value,
          scope: 'environment'
        }))
      ]
    },

    getVariable: (state) => (name) => {
      return state.globalVariables.find(v => v.name === name) ||
             state.workflowVariables.find(v => v.name === name) ||
             Object.entries(state.environments).flatMap(([env, vars]) =>
               vars[name] ? [{ ...vars[name], scope: `env.${env}` }] : []
             )[0]
    }
  },

  actions: {
    // 添加变量
    addVariable(variable, scope = 'workflow') {
      const target = scope === 'global' ? 'globalVariables' : 'workflowVariables'
      const exists = this[target].some(v => v.name === variable.name)
      if (exists) {
        throw new Error(`变量 ${variable.name} 已存在`)
      }
      this[target].push({
        id: `var_${Date.now()}`,
        name: variable.name,
        type: variable.type || 'string',
        defaultValue: variable.defaultValue,
        description: variable.description || '',
        required: variable.required || false,
        ...variable
      })
    },

    // 更新变量
    updateVariable(name, updates, scope) {
      const target = scope === 'global' ? 'globalVariables' : 'workflowVariables'
      const index = this[target].findIndex(v => v.name === name)
      if (index !== -1) {
        this[target][index] = { ...this[target][index], ...updates }
      }
    },

    // 删除变量
    removeVariable(name, scope) {
      const target = scope === 'global' ? 'globalVariables' : 'workflowVariables'
      this[target] = this[target].filter(v => v.name !== name)
    },

    // 变量插值
    interpolate(template, data = {}) {
      const variables = this.activeVariables
      let result = template

      for (const variable of variables) {
        const pattern = new RegExp(`\\{\\{\\s*${variable.name}\\s*\\}\\}`, 'g')
        result = result.replace(pattern, data[variable.name] ?? variable.defaultValue ?? '')
      }

      // 支持表达式 {{ $json.path.to.field }}
      result = result.replace(/\{\{\s*\$(json|var)\.(.+?)\s*\}\}/g, (_, type, path) => {
        const value = path.split('.').reduce((obj, key) => obj?.[key], data)
        return value ?? ''
      })

      return result
    },

    // 环境切换
    switchEnvironment(env) {
      this.currentEnvironment = env
    }
  }
})
```

### 24.2 变量面板组件

```vue
<!-- Frontend/src/components/workflow/VariablePanel.vue -->
<template>
  <el-drawer v-model="visible" title="变量管理" size="400px">
    <!-- 环境切换 -->
    <div class="env-selector">
      <el-radio-group v-model="currentEnv" size="small">
        <el-radio-button label="development">开发</el-radio-button>
        <el-radio-button label="production">生产</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 变量类型筛选 -->
    <el-tabs v-model="activeTab">
      <el-tab-pane label="输入变量" name="input">
        <div class="variable-list">
          <div
            v-for="v in inputVariables"
            :key="v.name"
            class="variable-item"
          >
            <div class="variable-header">
              <span class="variable-name">{{ v.name }}</span>
              <el-tag size="small">{{ v.type }}</el-tag>
            </div>
            <div class="variable-preview">
              {{ v.defaultValue || '(未设置)' }}
            </div>
          </div>
          <el-empty v-if="inputVariables.length === 0" description="暂无输入变量" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="全局变量" name="global">
        <div class="variable-list">
          <div
            v-for="v in globalVariables"
            :key="v.name"
            class="variable-item"
          >
            <div class="variable-header">
              <span class="variable-name">{{ v.name }}</span>
              <el-tag size="small">{{ v.type }}</el-tag>
              <el-button text size="small" @click="editVariable(v)">编辑</el-button>
              <el-button text size="small" type="danger" @click="removeVariable(v.name)">删除</el-button>
            </div>
            <div class="variable-preview">
              {{ maskSensitive(v.value) }}
            </div>
          </div>
        </div>
        <el-button type="primary" class="add-btn" @click="showAddDialog = true">
          添加全局变量
        </el-button>
      </el-tab-pane>

      <el-tab-pane label="环境变量" name="env">
        <el-alert
          title="环境变量用于存储敏感信息，不会暴露在前端代码中"
          type="info"
          :closable="false"
          show-icon
        />
        <div class="variable-list">
          <div
            v-for="(value, key) in currentEnvVariables"
            :key="key"
            class="variable-item"
          >
            <div class="variable-header">
              <span class="variable-name">{{ key }}</span>
              <el-button text size="small" @click="editEnvVariable(key)">编辑</el-button>
              <el-button text size="small" type="danger" @click="removeEnvVariable(key)">删除</el-button>
            </div>
            <div class="variable-preview sensitive">
              {{ maskSensitive(value) }}
            </div>
          </div>
        </div>
        <el-button type="primary" class="add-btn" @click="showEnvAddDialog = true">
          添加环境变量
        </el-button>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加变量对话框 -->
    <el-dialog v-model="showAddDialog" title="添加全局变量" width="400px">
      <el-form :model="newVariable" label-width="80px">
        <el-form-item label="变量名">
          <el-input v-model="newVariable.name" placeholder="如: api_key" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newVariable.type">
            <el-option label="字符串" value="string" />
            <el-option label="数字" value="number" />
            <el-option label="布尔值" value="boolean" />
            <el-option label="对象" value="object" />
            <el-option label="数组" value="array" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认值">
          <el-input
            v-model="newVariable.defaultValue"
            :type="newVariable.type === 'number' ? 'number' : 'text'"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newVariable.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addVariable">确定</el-button>
      </template>
    </el-dialog>

    <!-- 变量预览工具 -->
    <el-divider />
    <div class="variable-toolbar">
      <h4>变量引用</h4>
      <p class="hint">在工作流中引用变量：</p>
      <code-block
        v-for="v in allVariables"
        :key="v.name"
        :code="`{{ ${v.name} }}`"
        copyable
      />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useVariableStore } from '@/stores/variables'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  nodeVariables: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const store = useVariableStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 状态
const currentEnv = ref('development')
const activeTab = ref('input')
const showAddDialog = ref(false)
const showEnvAddDialog = ref(false)
const newVariable = ref({
  name: '',
  type: 'string',
  defaultValue: '',
  description: ''
})

// 计算属性
const inputVariables = computed(() => props.nodeVariables)

const globalVariables = computed(() => store.globalVariables)

const currentEnvVariables = computed(() =>
  store.environments[currentEnv.value] || {}
)

const allVariables = computed(() => store.allVariables)

// 方法
const addVariable = () => {
  try {
    store.addVariable(newVariable.value, 'global')
    showAddDialog.value = false
    newVariable.value = { name: '', type: 'string', defaultValue: '', description: '' }
    ElMessage.success('添加成功')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

const editVariable = (variable) => {
  newVariable.value = { ...variable }
  showAddDialog.value = true
}

const removeVariable = (name) => {
  store.removeVariable(name, 'global')
  ElMessage.success('删除成功')
}

const editEnvVariable = (key) => {
  // 实现环境变量编辑
}

const removeEnvVariable = (key) => {
  delete store.environments[currentEnv.value][key]
}

const maskSensitive = (value) => {
  if (!value) return ''
  const str = String(value)
  if (str.length <= 4) return '****'
  return str.slice(0, 2) + '****' + str.slice(-2)
}
</script>

<style scoped>
.env-selector {
  margin-bottom: 20px;
}

.variable-list {
  max-height: 400px;
  overflow-y: auto;
}

.variable-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
}

.variable-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.variable-name {
  font-weight: 500;
  flex: 1;
}

.variable-preview {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  word-break: break-all;
}

.variable-preview.sensitive {
  font-family: monospace;
}

.add-btn {
  width: 100%;
  margin-top: 10px;
}

.variable-toolbar {
  padding: 10px 0;
}

.variable-toolbar h4 {
  margin-bottom: 10px;
}

.hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}

code-block {
  display: block;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-family: monospace;
  margin-bottom: 5px;
  cursor: pointer;
}
</style>
```

---

## Step 25 - 高级节点类型

### 25.1 HTTP 请求节点

```vue
<!-- Frontend/src/components/nodes/HttpRequestNode.vue -->
<template>
  <div class="http-request-node">
    <el-form label-width="80px" size="small">
      <el-form-item label="请求方法">
        <el-select v-model="config.method" class="method-select">
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
          <el-option label="DELETE" value="DELETE" />
          <el-option label="PATCH" value="PATCH" />
        </el-select>
      </el-form-item>

      <el-form-item label="URL">
        <el-input
          v-model="config.url"
          placeholder="https://api.example.com/endpoint"
        >
          <template #append>
            <el-button @click="testConnection">测试</el-button>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item label="请求头">
        <el-input
          v-model="headersText"
          type="textarea"
          :rows="3"
          placeholder="Content-Type: application/json"
        />
      </el-form-item>

      <el-form-item label="请求体">
        <el-input
          v-model="config.body"
          type="textarea"
          :rows="4"
          placeholder='{"key": "{{ variable }}"}'
        />
      </el-form-item>

      <el-form-item label="超时(ms)">
        <el-input-number v-model="config.timeout" :min="1000" :max="60000" />
      </el-form-item>

      <el-collapse>
        <el-collapse-item title="高级配置">
          <el-form-item label="认证">
            <el-select v-model="config.auth_type">
              <el-option label="无" value="none" />
              <el-option label="Bearer Token" value="bearer" />
              <el-option label="Basic Auth" value="basic" />
              <el-option label="API Key" value="api_key" />
            </el-select>
          </el-form-item>

          <el-form-item v-if="config.auth_type === 'bearer'" label="Token">
            <el-input v-model="config.bearer_token" type="password" show-password />
          </el-form-item>

          <el-form-item label="响应字段">
            <el-input
              v-model="config.response_path"
              placeholder="data.results"
              placeholder="指定从响应中提取的字段路径"
            />
          </el-form-item>
        </el-collapse-item>
      </el-collapse>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  config: { type: Object, required: true }
})

const emit = defineEmits(['update:config'])

// 本地状态
const headersText = computed({
  get: () => {
    if (!props.config.headers) return ''
    return Object.entries(props.config.headers)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n')
  },
  set: (val) => {
    const headers = {}
    val.split('\n').forEach(line => {
      const [key, ...valueParts] = line.split(':')
      if (key && valueParts.length) {
        headers[key.trim()] = valueParts.join(':').trim()
      }
    })
    emit('update:config', { ...props.config, headers })
  }
})

const testConnection = async () => {
  // 实现测试连接
}
</script>

<style scoped>
.method-select {
  width: 100px;
}
</style>
```

### 25.2 代码执行节点

```vue
<!-- Frontend/src/components/nodes/CodeNode.vue -->
<template>
  <div class="code-node">
    <el-form label-width="80px" size="small">
      <el-form-item label="语言">
        <el-select v-model="config.language">
          <el-option label="JavaScript" value="javascript" />
          <el-option label="Python" value="python" />
        </el-select>
      </el-form-item>

      <el-form-item label="代码">
        <div class="code-editor">
          <el-input
            v-model="config.code"
            type="textarea"
            :rows="10"
            class="code-textarea"
            placeholder="// input 包含输入数据
// output 用于返回结果

const text = input.text;
output.result = text.toUpperCase();"
          />
        </div>
      </el-form-item>

      <el-form-item label="可用变量">
        <el-tag size="small" class="var-tag">input</el-tag>
        <el-tag size="small" class="var-tag">output</el-tag>
        <el-tag size="small" class="var-tag">env</el-tag>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
const props = defineProps({
  config: { type: Object, required: true }
})

const emit = defineEmits(['update:config'])
</script>

<style scoped>
.code-textarea :deep(textarea) {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.var-tag {
  margin-right: 5px;
}
</style>
```

### 25.3 定时调度节点

```vue
<!-- Frontend/src/components/nodes/SchedulerNode.vue -->
<template>
  <div class="scheduler-node">
    <el-form label-width="80px" size="small">
      <el-form-item label="触发方式">
        <el-radio-group v-model="config.trigger_type">
          <el-radio label="cron">Cron 表达式</el-radio>
          <el-radio label="interval">间隔</el-radio>
          <el-radio label="once">单次</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="config.trigger_type === 'cron'" label="Cron">
        <el-input v-model="config.cron" placeholder="0 8 * * *" />
        <div class="cron-hint">
          <el-tooltip content="秒 分 时 日 月 周">
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
          <span>格式: 秒 分 时 日 月 周</span>
        </div>
        <el-button text size="small" @click="showCronHelper = true">
          查看示例
        </el-button>
      </el-form-item>

      <el-form-item v-if="config.trigger_type === 'interval'" label="间隔">
        <el-input-number v-model="config.interval_value" :min="1" />
        <el-select v-model="config.interval_unit" style="width: 100px">
          <el-option label="秒" value="seconds" />
          <el-option label="分钟" value="minutes" />
          <el-option label="小时" value="hours" />
          <el-option label="天" value="days" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="config.trigger_type === 'once'" label="执行时间">
        <el-date-picker
          v-model="config.once_time"
          type="datetime"
          placeholder="选择日期时间"
        />
      </el-form-item>

      <el-form-item label="时区">
        <el-select v-model="config.timezone" filterable>
          <el-option label="北京时间 (UTC+8)" value="Asia/Shanghai" />
          <el-option label="UTC" value="UTC" />
          <el-option label="美东时间 (UTC-5)" value="America/New_York" />
        </el-select>
      </el-form-item>

      <el-form-item label="启用">
        <el-switch v-model="config.enabled" />
      </el-form-item>
    </el-form>

    <!-- 下次执行时间预览 -->
    <div class="next-run">
      <el-icon><Clock /></el-icon>
      下次执行: {{ nextRunTime }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  config: { type: Object, required: true }
})

const emit = defineEmits(['update:config'])
const showCronHelper = ref(false)

const nextRunTime = computed(() => {
  // 计算下次执行时间
  return '2024-01-15 08:00:00'
})
</script>
```

### 25.4 后端代码执行实现

```python
# workflow/nodes/http_request.py
import httpx
from typing import Dict, Any, Optional
from .base import BaseNode, NodeOutput


class HttpRequestNode(BaseNode):
    """HTTP 请求节点"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> NodeOutput:
        method = self.config.get('method', 'GET')
        url = self.config.get('url')
        headers = self.config.get('headers', {})
        body = self.config.get('body')
        timeout = self.config.get('timeout', 30000)

        # 变量插值
        url = self.interpolate(url, input_data, context)

        # 处理请求体
        request_body = None
        if body and method in ['POST', 'PUT', 'PATCH']:
            body_text = self.interpolate(body, input_data, context)
            try:
                request_body = json.loads(body_text)
            except json.JSONDecodeError:
                request_body = body_text

        try:
            async with httpx.AsyncClient(timeout=timeout / 1000) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=request_body if isinstance(request_body, dict) else None,
                    data=request_body if isinstance(request_body, str) else None,
                )

                response.raise_for_status()

                result = {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'body': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                }

                # 提取指定字段
                response_path = self.config.get('response_path')
                if response_path:
                    result['extracted'] = self.extract_path(response.json(), response_path)

                return NodeOutput(success=True, data=result)

        except httpx.HTTPError as e:
            return NodeOutput(success=False, error=str(e))


# workflow/nodes/code_executor.py
import json
import re
from typing import Dict, Any
from .base import BaseNode, NodeOutput


class CodeExecutionNode(BaseNode):
    """代码执行节点"""

    SUPPORTED_LANGUAGES = ['javascript', 'python']

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> NodeOutput:
        language = self.config.get('language', 'javascript')
        code = self.config.get('code', '')

        if language == 'javascript':
            return await self.execute_js(code, input_data, context)
        elif language == 'python':
            return await self.execute_python(code, input_data, context)
        else:
            return NodeOutput(success=False, error=f'不支持的语言: {language}')

    async def execute_js(self, code: str, input_data: Dict, context: Dict) -> NodeOutput:
        try:
            # 使用 QuickJS 或 PyMiniReact 执行 JS
            # 这里简化为字符串替换执行
            import subprocess

            js_code = f"""
const input = {json.dumps(input_data)};
const context = {json.dumps(context)};
const env = context.env || {{}};
let output = {{}};

{code}

console.log(JSON.stringify(output));
"""

            result = subprocess.run(
                ['node', '-e', js_code],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return NodeOutput(success=False, error=result.stderr)

            output = json.loads(result.stdout.strip())
            return NodeOutput(success=True, data={'output': output})

        except Exception as e:
            return NodeOutput(success=False, error=str(e))
```

---

## Step 26 - RAG 增强功能

### 26.1 文档处理节点

```vue
<!-- Frontend/src/components/nodes/DocumentNode.vue -->
<template>
  <div class="document-node">
    <el-form label-width="100px" size="small">
      <el-form-item label="文档来源">
        <el-radio-group v-model="config.source">
          <el-radio label="upload">上传文件</el-radio>
          <el-radio label="url">URL</el-radio>
          <el-radio label="text">直接输入</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="config.source === 'upload'" label="上传文档">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="10"
          :on-change="handleFileChange"
          accept=".pdf,.docx,.txt,.md"
        >
          <el-button>选择文件</el-button>
          <template #tip>
            <div class="el-upload__tip">支持 PDF、Word、TXT、Markdown</div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item v-if="config.source === 'url'" label="文档URL">
        <el-input
          v-model="config.url"
          placeholder="https://example.com/doc.pdf"
        />
      </el-form-item>

      <el-form-item v-if="config.source === 'text'" label="文档内容">
        <el-input
          v-model="config.text"
          type="textarea"
          :rows="6"
        />
      </el-form-item>

      <el-divider>文本分割</el-divider>

      <el-form-item label="分割方式">
        <el-select v-model="config.chunk_method">
          <el-option label="按字符数" value="chars" />
          <el-option label="按句子" value="sentences" />
          <el-option label="按段落" value="paragraphs" />
          <el-option label="递归分割" value="recursive" />
        </el-select>
      </el-form-item>

      <el-form-item label="块大小">
        <el-input-number v-model="config.chunk_size" :min="100" :max="4000" :step="100" />
      </el-form-item>

      <el-form-item label="重叠大小">
        <el-input-number v-model="config.chunk_overlap" :min="0" :max="500" />
      </el-form-item>

      <el-divider>Embedding</el-divider>

      <el-form-item label="Embedding 模型">
        <el-select v-model="config.embedding_model">
          <el-option label="text-embedding-ada-002" value="ada-002" />
          <el-option label="text-embedding-3-small" value="embedding-3-small" />
          <el-option label="text-embedding-3-large" value="embedding-3-large" />
          <el-option label="BGE (本地)" value="bge" />
        </el-select>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
const props = defineProps({
  config: { type: Object, required: true }
})

const emit = defineEmits(['update:config'])
const uploadRef = ref(null)

const handleFileChange = (file) => {
  emit('update:config', {
    ...props.config,
    file_name: file.name,
    file_size: file.size
  })
}
</script>
```

### 26.2 向量存储配置

```vue
<!-- Frontend/src/components/nodes/VectorStoreNode.vue -->
<template>
  <div class="vector-store-node">
    <el-form label-width="100px" size="small">
      <el-form-item label="向量数据库">
        <el-select v-model="config.provider">
          <el-option label="Pinecone" value="pinecone" />
          <el-option label="Weaviate" value="weaviate" />
          <el-option label="Milvus" value="milvus" />
          <el-option label="Chroma" value="chroma" />
          <el-option label="FAISS (本地)" value="faiss" />
        </el-select>
      </el-form-item>

      <el-form-item label="索引名称">
        <el-input v-model="config.index_name" />
      </el-form-item>

      <el-form-item label="API 配置">
        <el-collapse>
          <el-collapse-item title="高级配置">
            <el-form-item label="Environment">
              <el-input v-model="config.environment" />
            </el-form-item>
            <el-form-item label="Namespace">
              <el-input v-model="config.namespace" />
            </el-form-item>
            <el-form-item label="Top K">
              <el-input-number v-model="config.top_k" :min="1" :max="100" />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
const props = defineProps({
  config: { type: Object, required: true }
})
</script>
```

### 26.3 RAG 后端实现

```python
# workflow/nodes/rag.py
from typing import List, Dict, Any
from dataclasses import dataclass
import json
import hashlib


@dataclass
class Document:
    """文档对象"""
    id: str
    content: str
    metadata: Dict[str, Any]
    chunks: List['Chunk'] = None


@dataclass
class Chunk:
    """文档块"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float] = None


class DocumentProcessor:
    """文档处理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def process(self, source: str, file_content: bytes = None) -> List[Chunk]:
        """处理文档并分割"""
        if source == 'upload':
            text = await self.extract_text(file_content)
        elif source == 'url':
            text = await self.fetch_url(source)
        else:
            text = source

        return self.split_text(text)

    async def extract_text(self, file_content: bytes) -> str:
        """从文件提取文本"""
        from .file_parser import FileParser

        parser = FileParser(file_content)
        return await parser.extract()

    def split_text(self, text: str) -> List[Chunk]:
        """分割文本"""
        method = self.config.get('chunk_method', 'chars')
        chunk_size = self.config.get('chunk_size', 500)
        overlap = self.config.get('chunk_overlap', 50)

        if method == 'chars':
            return self._split_by_chars(text, chunk_size, overlap)
        elif method == 'sentences':
            return self._split_by_sentences(text, chunk_size, overlap)
        elif method == 'paragraphs':
            return self._split_by_paragraphs(text)
        else:
            return self._split_recursive(text, chunk_size, overlap)

    def _split_by_chars(self, text: str, chunk_size: int, overlap: int) -> List[Chunk]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            chunk_id = hashlib.md5(f"{start}:{chunk_text}".encode()).hexdigest()
            chunks.append(Chunk(
                id=chunk_id,
                content=chunk_text,
                metadata={'start': start, 'end': end}
            ))

            start += chunk_size - overlap

        return chunks

    async def create_embeddings(self, chunks: List[Chunk]) -> List[Chunk]:
        """创建向量嵌入"""
        from ..services.embedding import EmbeddingService

        embedding_service = EmbeddingService(self.config.get('embedding_model'))

        for chunk in chunks:
            chunk.embedding = await embedding_service.embed(chunk.content)

        return chunks


class VectorStoreManager:
    """向量存储管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = self._get_client()

    def _get_client(self):
        """获取向量数据库客户端"""
        provider = self.config.get('provider')

        if provider == 'pinecone':
            from pinecone import Pinecone
            return Pinecone(api_key=self.config.get('api_key'))
        elif provider == 'chroma':
            from chromadb import Client
            return Client()
        # ... 其他 provider

    async def add_documents(self, chunks: List[Chunk], namespace: str = None):
        """添加文档到向量库"""
        vectors = [
            {
                'id': chunk.id,
                'values': chunk.embedding,
                'metadata': {
                    'content': chunk.content,
                    **chunk.metadata
                }
            }
            for chunk in chunks
        ]

        await self.client.upsert(
            vectors=vectors,
            namespace=namespace,
            index_name=self.config.get('index_name')
        )

    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        namespace: str = None
    ) -> List[Dict]:
        """相似度搜索"""
        results = await self.client.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True,
            index_name=self.config.get('index_name')
        )

        return [
            {
                'id': r['id'],
                'content': r['metadata']['content'],
                'score': r['score']
            }
            for r in results['matches']
        ]
```

---

## Step 27 - 团队协作功能

### 27.1 团队数据模型

```python
# workflow/models.py

class Organization(models.Model):
    """组织"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='orgs/logos/', null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_orgs')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']


class Team(models.Model):
    """团队"""
    name = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='teams')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TeamMember(models.Model):
    """团队成员"""
    ROLE_CHOICES = [
        ('owner', '所有者'),
        ('admin', '管理员'),
        ('editor', '编辑者'),
        ('viewer', '查看者'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'team']


class WorkflowShare(models.Model):
    """工作流分享"""
    PERMISSION_CHOICES = [
        ('view', '仅查看'),
        ('edit', '可编辑'),
        ('admin', '管理权限'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def is_valid(self):
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
```

### 27.2 分享链接组件

```vue
<!-- Frontend/src/components/workflow/ShareDialog.vue -->
<template>
  <el-dialog v-model="visible" title="分享工作流" width="500px">
    <el-tabs v-model="activeTab">
      <!-- 团队分享 -->
      <el-tab-pane label="团队分享" name="team">
        <div class="share-section">
          <h4>选择团队</h4>
          <el-select v-model="selectedTeam" placeholder="选择团队" @change="loadTeamMembers">
            <el-option
              v-for="team in teams"
              :key="team.id"
              :label="team.name"
              :value="team.id"
            />
          </el-select>

          <h4>设置权限</h4>
          <el-radio-group v-model="teamPermission">
            <el-radio label="view">仅查看</el-radio>
            <el-radio label="edit">可编辑</el-radio>
            <el-radio label="admin">管理权限</el-radio>
          </el-radio-group>

          <el-button type="primary" @click="shareToTeam" :disabled="!selectedTeam">
            分享到团队
          </el-button>
        </div>
      </el-tab-pane>

      <!-- 链接分享 -->
      <el-tab-pane label="链接分享" name="link">
        <div class="share-section">
          <h4>分享链接</h4>
          <div class="link-box">
            <el-input v-model="shareLink" readonly />
            <el-button @click="copyLink">复制</el-button>
          </div>

          <h4>权限设置</h4>
          <el-radio-group v-model="linkPermission">
            <el-radio label="view">仅查看</el-radio>
            <el-radio label="edit">可编辑</el-radio>
          </el-radio-group>

          <h4>链接过期时间</h4>
          <el-select v-model="expiresIn">
            <el-option label="永不过期" :value="0" />
            <el-option label="1 小时" :value="3600" />
            <el-option label="1 天" :value="86400" />
            <el-option label="7 天" :value="604800" />
            <el-option label="30 天" :value="2592000" />
          </el-select>

          <el-button type="primary" @click="generateLink">生成链接</el-button>
        </div>
      </el-tab-pane>

      <!-- 用户分享 -->
      <el-tab-pane label="用户分享" name="user">
        <div class="share-section">
          <h4>搜索用户</h4>
          <el-select
            v-model="selectedUser"
            filterable
            remote
            :remote-method="searchUsers"
            placeholder="输入用户名搜索"
          >
            <el-option
              v-for="user in searchResults"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            >
              <span>{{ user.username }}</span>
              <span class="user-email">{{ user.email }}</span>
            </el-option>
          </el-select>

          <h4>权限设置</h4>
          <el-radio-group v-model="userPermission">
            <el-radio label="view">仅查看</el-radio>
            <el-radio label="edit">可编辑</el-radio>
            <el-radio label="admin">管理权限</el-radio>
          </el-radio-group>

          <el-button type="primary" @click="shareToUser" :disabled="!selectedUser">
            添加用户
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 已有分享列表 -->
    <el-divider />
    <h4>已分享 ({{ shares.length }})</h4>
    <div class="shares-list">
      <div v-for="share in shares" :key="share.id" class="share-item">
        <div class="share-info">
          <span class="share-target">
            {{ share.user?.username || share.team?.name || '公开链接' }}
          </span>
          <el-tag size="small">{{ getPermissionLabel(share.permission) }}</el-tag>
        </div>
        <el-button text type="danger" @click="revokeShare(share.id)">撤销</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  workflowId: { type: Number, required: true }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 状态
const activeTab = ref('link')
const teams = ref([])
const shares = ref([])
const selectedTeam = ref(null)
const selectedUser = ref(null)
const searchResults = ref([])
const shareLink = ref('')

// 权限
const teamPermission = ref('edit')
const linkPermission = ref('view')
const userPermission = ref('edit')
const expiresIn = ref(0)

// 方法
const loadTeams = async () => {
  // 加载团队列表
}

const loadTeamMembers = async () => {
  // 加载团队成员
}

const searchUsers = async (query) => {
  // 搜索用户
}

const shareToTeam = async () => {
  // 分享给团队
}

const shareToUser = async () => {
  // 分享给用户
}

const generateLink = async () => {
  // 生成分享链接
}

const copyLink = async () => {
  await navigator.clipboard.writeText(shareLink.value)
  ElMessage.success('链接已复制')
}

const revokeShare = async (shareId) => {
  // 撤销分享
}

const getPermissionLabel = (permission) => {
  const labels = { view: '查看', edit: '编辑', admin: '管理' }
  return labels[permission] || permission
}
</script>
```

---

## Step 28 - 监控与告警

### 28.1 监控仪表盘

```vue
<!-- Frontend/src/components/dashboard/MonitoringDashboard.vue -->
<template>
  <div class="monitoring-dashboard">
    <!-- 概览卡片 -->
    <el-row :gutter="20" class="overview-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon executions">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_executions }}</div>
              <div class="stat-label">总执行次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon success">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.success_rate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon latency">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.avg_latency }}ms</div>
              <div class="stat-label">平均延迟</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon cost">
              <el-icon><Money /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">${{ stats.total_cost }}</div>
              <div class="stat-label">总消耗</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>执行趋势</span>
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
              />
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>执行分布</template>
          <div ref="pieChartRef" class="chart-container" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 执行历史 -->
    <el-card class="executions-table">
      <template #header>
        <div class="card-header">
          <span>最近执行</span>
          <el-button text @click="$router.push('/executions')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="recentExecutions" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="workflow_name" label="工作流" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration }}ms
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="消耗" width="100" />
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button text size="small" @click="viewExecution(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const trendChartRef = ref(null)
const pieChartRef = ref(null)
const dateRange = ref([])
let trendChart = null
let pieChart = null

// 数据
const stats = ref({
  total_executions: 0,
  success_rate: 0,
  avg_latency: 0,
  total_cost: 0
})

const recentExecutions = ref([])

// 图表
const initCharts = () => {
  trendChart = echarts.init(trendChartRef.value)
  pieChart = echarts.init(pieChartRef.value)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['成功', '失败'] },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value' },
    series: [
      { name: '成功', type: 'line', data: [] },
      { name: '失败', type: 'line', data: [] }
    ]
  })

  pieChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 335, name: '成功' },
        { value: 48, name: '失败' },
        { value: 27, name: '进行中' }
      ]
    }]
  })
}

// 加载数据
const loadData = async () => {
  // 加载统计数据
  // 加载图表数据
  // 加载执行历史
}

// 窗口调整
const handleResize = () => {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  loadData()
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>
```

### 28.2 告警配置

```python
# workflow/models.py

class AlertRule(models.Model):
    """告警规则"""
    CONDITION_CHOICES = [
        ('execution_failed', '执行失败'),
        ('execution_timeout', '执行超时'),
        ('cost_exceeded', '消耗超限'),
        ('latency_high', '延迟过高'),
    ]

    SEVERITY_CHOICES = [
        ('info', '信息'),
        ('warning', '警告'),
        ('error', '错误'),
        ('critical', '严重'),
    ]

    name = models.CharField(max_length=200)
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES)
    threshold = models.FloatField(help_text='阈值')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    enabled = models.BooleanField(default=True)

    # 通知设置
    notify_email = models.BooleanField(default=True)
    notify_webhook = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True)

    # 告警冷却
    cooldown_minutes = models.IntegerField(default=60)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Alert(models.Model):
    """告警记录"""
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, null=True)
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, null=True)
    severity = models.CharField(max_length=20)
    message = models.TextField()
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


# workflow/services/alerts.py
class AlertService:
    """告警服务"""

    async def check_execution(self, execution):
        """检查执行是否触发告警"""
        from .models import AlertRule, Alert

        rules = AlertRule.objects.filter(
            organization=execution.workflow.organization,
            enabled=True
        )

        for rule in rules:
            if self.should_trigger(rule, execution):
                await self.create_alert(rule, execution)

    def should_trigger(self, rule, execution):
        """判断是否应该触发告警"""
        if rule.condition == 'execution_failed' and execution.status == 'failed':
            return True
        elif rule.condition == 'execution_timeout' and execution.duration > rule.threshold:
            return True
        elif rule.condition == 'cost_exceeded' and execution.cost > rule.threshold:
            return True
        return False

    async def create_alert(self, rule, execution):
        """创建告警"""
        from .models import Alert

        alert = Alert.objects.create(
            rule=rule,
            workflow=execution.workflow,
            execution=execution,
            severity=rule.severity,
            message=f"{rule.get_condition_display()}: {rule.threshold}"
        )

        await self.send_notification(alert)

    async def send_notification(self, alert):
        """发送通知"""
        if alert.rule.notify_email:
            await self.send_email(alert)
        if alert.rule.notify_webhook:
            await self.send_webhook(alert)
```

---

## Step 29 - 多租户与计费

### 29.1 计费套餐

```python
# billing/models.py

class Plan(models.Model):
    """计费套餐"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    # 价格
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)

    # 限制
    workflow_limit = models.IntegerField(help_text='工作流数量限制，-1 表示无限制')
    execution_limit = models.IntegerField(help_text='每月执行次数限制，-1 表示无限制')
    team_members = models.IntegerField(help_text='团队成员数量')
    storage_gb = models.IntegerField(help_text='存储空间(GB)')

    # 功能
    features = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    def has_feature(self, feature):
        return self.features.get(feature, False)


class Subscription(models.Model):
    """订阅"""
    STATUS_CHOICES = [
        ('active', '有效'),
        ('past_due', '逾期'),
        ('canceled', '已取消'),
        ('trialing', '试用中'),
    ]

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    # Stripe 相关
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)

    # 时间
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    canceled_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)


class UsageRecord(models.Model):
    """用量记录"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    period = models.DateField(help_text='统计周期')
    workflow_count = models.IntegerField(default=0)
    execution_count = models.IntegerField(default=0)
    token_usage = models.BigIntegerField(default=0, help_text='Token 使用量')
    storage_used_mb = models.IntegerField(default=0)

    class Meta:
        unique_together = ['organization', 'period']


class Invoice(models.Model):
    """发票"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    stripe_invoice_id = models.CharField(max_length=100, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20)

    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True)
```

### 29.2 用量限制中间件

```python
# workflow/middleware.py

class UsageLimitMiddleware:
    """用量限制中间件"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and request.user.is_authenticated:
            org = self.get_organization(request.user)

            if org:
                # 检查订阅状态
                if not self.check_subscription(org):
                    return JsonResponse({
                        'error': 'subscription_inactive',
                        'message': '您的订阅已过期，请续费'
                    }, status=402)

                # 检查用量限制
                usage_check = self.check_usage_limits(org, request)
                if not usage_check['allowed']:
                    return JsonResponse({
                        'error': 'usage_limit_exceeded',
                        'message': usage_check['message']
                    }, status=429)

        return self.get_response(request)

    def check_subscription(self, org):
        """检查订阅状态"""
        try:
            sub = org.subscription
            if sub.status != 'active' and sub.status != 'trialing':
                return False

            # 检查订阅到期
            if sub.current_period_end < timezone.now():
                return False

            return True
        except Subscription.DoesNotExist:
            # 检查是否在免费套餐限制内
            return org.usage_records.filter(
                period=date.today().replace(day=1)
            ).count() < 3  # 免费版限制

    def check_usage_limits(self, org, request):
        """检查用量限制"""
        try:
            sub = org.subscription
            plan = sub.plan
        except Subscription.DoesNotExist:
            # 默认免费套餐限制
            plan = Plan.objects.get(slug='free')

        today = date.today().replace(day=1)
        usage = org.usage_records.filter(period=today).first()

        if not usage:
            usage = UsageRecord.objects.create(organization=org, period=today)

        # 检查工作流数量
        if plan.workflow_limit > 0:
            workflow_count = org.workflows.count()
            if workflow_count >= plan.workflow_limit:
                return {
                    'allowed': False,
                    'message': f'已达到工作流数量上限 ({plan.workflow_limit})'
                }

        # 检查执行次数
        if plan.execution_limit > 0:
            if usage.execution_count >= plan.execution_limit:
                return {
                    'allowed': False,
                    'message': f'本月执行次数已用完 ({plan.execution_limit})'
                }

        return {'allowed': True}
```

---

## Step 30 - API 与集成

### 30.1 API 文档自动生成

```python
# workflow/docs.py
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        summary="列出工作流",
        description="获取当前用户的所有工作流列表",
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, description='按状态筛选'),
            OpenApiParameter('search', OpenApiTypes.STR, description='搜索关键词'),
        ]
    ),
    create=extend_schema(
        summary="创建工作流",
        description="创建一个新的工作流",
        request=WorkflowCreateSerializer,
        responses={201: WorkflowDetailSerializer}
    ),
    retrieve=extend_schema(
        summary="获取工作流详情",
        description="获取指定工作流的详细信息"
    ),
    update=extend_schema(
        summary="更新工作流",
        description="更新工作流内容"
    ),
    destroy=extend_schema(
        summary="删除工作流",
        description="删除指定的工作流"
    ),
)
class WorkflowViewSet(viewsets.ModelViewSet):
    pass


# workflow/api_docs.py
API_DOCS = {
    'workflows': {
        'endpoints': [
            {
                'method': 'GET',
                'path': '/api/v1/workflows/',
                'summary': '列出工作流',
                'description': '获取当前用户的工作流列表',
                'parameters': [
                    {'name': 'status', 'type': 'string', 'required': False},
                    {'name': 'page', 'type': 'integer', 'required': False},
                ],
                'responses': {
                    200: {'description': '成功', 'schema': 'WorkflowList'}
                }
            },
            {
                'method': 'POST',
                'path': '/api/v1/workflows/',
                'summary': '创建工作流',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'example': {
                                'name': '我的工作流',
                                'description': '工作流描述'
                            }
                        }
                    }
                }
            },
            {
                'method': 'POST',
                'path': '/api/v1/workflows/{id}/execute/',
                'summary': '执行工作流',
                'description': '触发工作流执行（同步或异步）',
                'parameters': [
                    {'name': 'id', 'type': 'integer', 'in': 'path', 'required': True}
                ],
                'requestBody': {
                    'content': {
                        'application/json': {
                            'example': {
                                'input_data': {'text': 'Hello'},
                                'async': True
                            }
                        }
                    }
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/workflows/{id}/executions/{exec_id}/',
                'summary': '获取执行结果',
            }
        ]
    },
    'webhooks': {
        'endpoints': [
            {
                'method': 'POST',
                'path': '/api/v1/webhooks/{webhook_id}/',
                'summary': 'Webhook 触发',
                'description': '通过 webhook 触发工作流执行'
            }
        ]
    }
}
```

### 30.2 SDK 示例

```python
# SDK Python 示例
# flowly-sdk-python/flowly/__init__.py

"""
Flowly Python SDK
"""

import requests
from typing import Dict, Any, Optional, List


class FlowlyClient:
    """Flowly 客户端"""

    def __init__(self, api_key: str, base_url: str = "https://api.flowly.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

    def list_workflows(self, page: int = 1) -> Dict[str, Any]:
        """列出工作流"""
        response = self.session.get(f'{self.base_url}/api/v1/workflows/', params={'page': page})
        response.raise_for_status()
        return response.json()

    def get_workflow(self, workflow_id: int) -> Dict[str, Any]:
        """获取工作流详情"""
        response = self.session.get(f'{self.base_url}/api/v1/workflows/{workflow_id}/')
        response.raise_for_status()
        return response.json()

    def create_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建工作流"""
        response = self.session.post(f'{self.base_url}/api/v1/workflows/', json=data)
        response.raise_for_status()
        return response.json()

    def execute_workflow(
        self,
        workflow_id: int,
        input_data: Dict[str, Any],
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """执行工作流"""
        response = self.session.post(
            f'{self.base_url}/api/v1/workflows/{workflow_id}/execute/',
            json={'input_data': input_data, 'async': async_mode}
        )
        response.raise_for_status()
        return response.json()

    def get_execution(self, execution_id: int) -> Dict[str, Any]:
        """获取执行结果"""
        response = self.session.get(f'{self.base_url}/api/v1/executions/{execution_id}/')
        response.raise_for_status()
        return response.json()

    def stream_execution(self, execution_id: int):
        """流式获取执行结果"""
        import sseclient
        response = self.session.get(
            f'{self.base_url}/api/v1/executions/{execution_id}/stream/',
            stream=True
        )
        client = sseclient.SSEClient(response)
        for event in client.events():
            yield json.loads(event.data)


# 使用示例
client = FlowlyClient(api_key='your-api-key')

# 列出工作流
workflows = client.list_workflows()

# 执行工作流
result = client.execute_workflow(
    workflow_id=123,
    input_data={'text': 'Hello World'},
    async_mode=True
)

# 获取结果
if result['status'] == 'pending':
    execution = client.get_execution(result['execution_id'])
    print(execution)
```

```javascript
// SDK JavaScript 示例
// flowly-sdk-js/src/index.js

class FlowlyClient {
  constructor(options) {
    this.apiKey = options.apiKey;
    this.baseUrl = options.baseUrl || 'https://api.flowly.com';
    this.token = options.token;
  }

  async request(method, path, data) {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };

    const response = await fetch(url, {
      method,
      headers,
      body: data ? JSON.stringify(data) : undefined
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  async listWorkflows(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request('GET', `/api/v1/workflows/?${query}`);
  }

  async getWorkflow(id) {
    return this.request('GET', `/api/v1/workflows/${id}/`);
  }

  async createWorkflow(data) {
    return this.request('POST', '/api/v1/workflows/', data);
  }

  async executeWorkflow(id, inputData, options = {}) {
    return this.request('POST', `/api/v1/workflows/${id}/execute/`, {
      input_data: inputData,
      ...options
    });
  }

  async *streamExecution(executionId) {
    const url = `${this.baseUrl}/api/v1/executions/${executionId}/stream/`;

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          yield JSON.parse(line.slice(6));
        }
      }
    }
  }
}

export default FlowlyClient;
```

---

## Step 31 - 用户体验增强

### 31.1 工作流模板市场

```vue
<!-- Frontend/src/components/marketplace/TemplateMarketplace.vue -->
<template>
  <div class="template-marketplace">
    <div class="marketplace-header">
      <h2>模板市场</h2>
      <el-input
        v-model="searchQuery"
        placeholder="搜索模板..."
        prefix-icon="Search"
        clearable
        class="search-input"
      />
    </div>

    <!-- 分类标签 -->
    <div class="category-tags">
      <el-tag
        v-for="cat in categories"
        :key="cat.id"
        :type="selectedCategory === cat.id ? 'primary' : ''"
        @click="selectedCategory = cat.id"
        class="category-tag"
      >
        {{ cat.name }} ({{ cat.count }})
      </el-tag>
    </div>

    <!-- 模板网格 -->
    <el-row :gutter="20" class="template-grid">
      <el-col
        v-for="template in filteredTemplates"
        :key="template.id"
        :span="8"
      >
        <el-card class="template-card" shadow="hover">
          <div class="template-preview">
            <img v-if="template.thumbnail" :src="template.thumbnail" />
            <div v-else class="preview-placeholder">
              {{ template.name.slice(0, 2) }}
            </div>
          </div>
          <div class="template-info">
            <h3>{{ template.name }}</h3>
            <p class="template-desc">{{ template.description }}</p>
            <div class="template-meta">
              <span><el-icon><User /></el-icon> {{ template.author }}</span>
              <span><el-icon><Download /></el-icon> {{ template.usage_count }}</span>
              <el-rate v-model="template.rating" disabled show-score />
            </div>
            <div class="template-tags">
              <el-tag
                v-for="tag in template.tags"
                :key="tag"
                size="small"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>
          <div class="template-actions">
            <el-button type="primary" @click="useTemplate(template)">
              使用此模板
            </el-button>
            <el-button @click="previewTemplate(template)">预览</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      :page-size="12"
      :total="totalTemplates"
      layout="prev, pager, next"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchQuery = ref('')
const selectedCategory = ref(null)
const currentPage = ref(1)
const totalTemplates = ref(0)

const categories = ref([
  { id: 1, name: 'AI 对话', count: 45 },
  { id: 2, name: '内容生成', count: 32 },
  { id: 3, name: '数据处理', count: 28 },
  { id: 4, name: '自动化', count: 56 },
  { id: 5, name: 'RAG', count: 21 },
])

const templates = ref([])

const filteredTemplates = computed(() => {
  let result = templates.value

  if (selectedCategory.value) {
    result = result.filter(t => t.category_id === selectedCategory.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(query) ||
      t.description.toLowerCase().includes(query)
    )
  }

  return result
})

const useTemplate = (template) => {
  router.push({ path: '/workflow/new', query: { template: template.id } })
}

const previewTemplate = (template) => {
  // 预览模板
}
</script>
```

### 31.2 深色模式与主题

```vue
<!-- Frontend/src/components/layout/ThemeToggle.vue -->
<template>
  <el-dropdown @command="handleCommand">
    <el-button text>
      <el-icon><Moon v-if="isDark" /><Sunny v-else /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="light">
          <el-icon><Sunny /></el-icon> 浅色模式
        </el-dropdown-item>
        <el-dropdown-item command="dark">
          <el-icon><Moon /></el-icon> 深色模式
        </el-dropdown-item>
        <el-dropdown-item command="auto">
          <el-icon><Monitor /></el-icon> 跟随系统
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const isDark = ref(false)

const handleCommand = (command) => {
  if (command === 'light') {
    document.documentElement.classList.remove('dark')
    localStorage.theme = 'light'
    isDark.value = false
  } else if (command === 'dark') {
    document.documentElement.classList.add('dark')
    localStorage.theme = 'dark'
    isDark.value = true
  } else {
    localStorage.removeItem('theme')
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark')
    isDark.value = true
  }
})
</script>
```

### 31.3 国际化

```javascript
// Frontend/src/i18n/index.js
import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  }
})

export default i18n

// Frontend/src/i18n/locales/zh-CN.js
export default {
  common: {
    save: '保存',
    cancel: '取消',
    delete: '删除',
    confirm: '确认',
    search: '搜索',
    loading: '加载中...',
  },
  workflow: {
    name: '工作流名称',
    create: '创建工作流',
    edit: '编辑工作流',
    execute: '执行',
    save: '保存',
    publish: '发布',
  },
  nodes: {
    llm: 'LLM 节点',
    input: '输入',
    output: '输出',
    template: '模板',
  }
}
```

---

## 下一步建议

完成以上所有步骤后，你的 Flowly 工作流平台已经具备以下能力：

| 模块 | 功能 |
|------|------|
| **编辑器** | 增强拖拽、节点对齐、迷你地图、撤销重做、自动排列 |
| **变量系统** | 全局变量、环境变量、变量插值、敏感信息管理 |
| **节点** | HTTP 请求、代码执行、定时调度、文档处理、RAG |
| **RAG** | 文档上传、文本分割、Embedding、向量存储、混合检索 |
| **协作** | 团队管理、权限控制、分享链接 |
| **监控** | 执行统计、趋势图表、告警规则、通知 |
| **计费** | 多租户、套餐管理、用量限制 |
| **集成** | REST API、SDK、Webhook |
| **体验** | 模板市场、深色模式、国际化 |

下一步可以：
1. **部署上线** - 使用 Step 19-22 的部署配置
2. **扩展节点** - 添加更多业务场景节点
3. **性能优化** - 引入缓存、CDN、数据库读写分离
4. **商业化** - 接入支付、构建 SaaS 平台

---

## 附录：API 参考

### 认证相关

```http
# 注册
POST /api/auth/register/
{
  "username": "user1",
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123"
}

# 登录
POST /api/auth/token/
{
  "username": "user1",
  "password": "password123"
}

# 刷新 Token
POST /api/auth/token/refresh/
{
  "refresh": "your-refresh-token"
}
```

### 工作流执行

```http
# 触发执行（异步）
POST /api/workflows/{id}/execute/
{
  "input_data": {"text": "Hello world"}
}

# 查询状态
GET /api/workflows/{id}/execute/{exec_id}/status/

# WebSocket 实时进度
ws://localhost:8000/ws/execution/{execution_id}/
```

### Prompt 模板

```http
# 列表
GET /api/prompt-templates/

# 创建
POST /api/prompt-templates/
{
  "name": "翻译助手",
  "category": "translate",
  "template": "将以下文本翻译成{lang}：{text}",
  "variables": ["lang", "text"]
}

# 渲染预览
POST /api/prompt-templates/{id}/render/
{
  "context": {"lang": "English", "text": "你好"}
}
```

```

---

## Step 32 - 流式执行与 Streaming UX

> **创新亮点**：边执行边展示，让用户实时看到 AI "思考" 的过程，大幅提升用户体验

### 32.1 流式执行架构设计

#### 传统 vs 流式执行对比

```javascript
// 🚫 传统模式：等待全部完成后才返回
POST /api/workflows/{id}/execute/
{
  "input_data": {"text": "分析这段评论"}
}
// 服务器处理 30 秒后...
{
  "status": "completed",
  "result": "这是一个投诉，需要转人工处理。分析如下..."  // 一次性返回
}

// ✅ 流式模式：边处理边返回
POST /api/workflows/{id}/execute/stream/
{
  "input_data": {"text": "分析这段评论"}
}
// 服务器实时推送...
{
  "event": "node_start",
  "node": "input",
  "timestamp": "2026-05-03T10:35:00Z"
}
{
  "event": "node_complete",
  "node": "input",
  "output": {"text": "分析这段评论"},
  "elapsed_ms": 5
}
{
  "event": "node_start",
  "node": "sentiment-analysis",
  "timestamp": "2026-05-03T10:35:00Z",
  "message": "正在分析情感..."
}
{
  "event": "token_stream",
  "node": "sentiment-analysis",
  "tokens": ["这", "是", "一", "个", "投", "诉"],
  "is_reasoning": false
}
{
  "event": "thinking_stream",
  "node": "sentiment-analysis",
  "thoughts": ["我需要先识别情感倾向...", "发现负面词汇...", "结论：投诉"]
}
{
  "event": "node_complete",
  "node": "sentiment-analysis",
  "output": {"sentiment": "negative", "confidence": 0.95},
  "reasoning": "发现负面词汇（投诉、转人工），置信度 95%",
  "elapsed_ms": 1500
}
{
  "event": "workflow_complete",
  "result": "这是一个投诉，需要转人工处理。分析如下...",
  "total_elapsed_ms": 3200
}
```

#### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 Vue 3 应用                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ 执行按钮    │  │ 流式可视化   │  │ 思考链展示               │ │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                      │
          │  WebSocket 连接 │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Django Channels WebSocket                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              StreamExecutionConsumer (Consumer)              ││
│  │  - 接收执行请求                                              ││
│  │  - 启动异步任务                                              ││
│  │  - 监听 Redis Pub/Sub                                        ││
│  │  - 实时推送事件到客户端                                        ││
│  └──────────────────────────┬──────────────────────────────────┘│
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Celery Workers (异步)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 执行引擎    │  │ LLM 调用    │  │ 事件发布 (Redis Pub/Sub) │  │
│  │ (DAG 遍历) │  │ (流式输出)  │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼─────────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Redis (消息队列 + Pub/Sub)                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  任务队列 (Celery)    │    流式事件通道 (Pub/Sub)            ││
│  │  - execute_task       │    - stream:{execution_id}          ││
│  └───────────────────────┴────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AI Provider (OpenAI 等)                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  流式 Completions API                                        ││
│  │  response = openai.chat.completions.create(                  ││
│  │    model="gpt-4",                                            ││
│  │    messages=[...],                                           ││
│  │    stream=True                                              ││
│  │  )                                                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 32.2 后端流式 API 实现

#### 32.2.1 WebSocket Consumer

```python
# Backend/workflows/consumers.py
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async


class StreamExecutionConsumer(AsyncWebsocketConsumer):
    """流式执行 WebSocket Consumer"""

    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'stream_{self.execution_id}'

        # 加入频道组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # 启动订阅任务
        self.subscribe_task = asyncio.create_task(self.subscribe_to_events())

    async def disconnect(self, close_code):
        # 取消订阅任务
        if hasattr(self, 'subscribe_task'):
            self.subscribe_task.cancel()

        # 离开频道组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """接收客户端消息（如取消执行）"""
        data = json.loads(text_data)
        if data.get('type') == 'cancel':
            await self.cancel_execution()

    async def stream_event(self, event):
        """接收流式事件并发送到 WebSocket"""
        await self.send(text_data=json.dumps(event['data']))

    async def subscribe_to_events(self):
        """订阅 Redis Pub/Sub 事件"""
        import redis.asyncio as redis

        redis_client = redis.from_url(settings.REDIS_URL)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f'stream:{self.execution_id}')

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    await self.send(text_data=json.dumps(data))
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(f'stream:{self.execution_id}')
            await redis_client.close()

    async def cancel_execution(self):
        """取消执行"""
        from workflows.tasks import cancel_execution
        await sync_to_async(cancel_execution)(self.execution_id)
```

#### 32.2.2 流式执行任务

```python
# Backend/workflows/tasks.py
import json
import asyncio
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import redis.asyncio as redis


@shared_task(bind=True, soft_time_limit=3600)
def execute_workflow_stream(self, workflow_id: str, execution_id: str, input_data: dict):
    """
    流式执行工作流主任务
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_execute_workflow_async(
        self, workflow_id, execution_id, input_data
    ))


async def _execute_workflow_async(task, workflow_id: str, execution_id: str, input_data: dict):
    """异步执行工作流"""

    # 初始化 Redis 发布器
    redis_client = redis.from_url(settings.REDIS_URL)

    # 发送初始事件
    await publish_event(redis_client, execution_id, {
        "event": "execution_start",
        "execution_id": execution_id,
        "timestamp": get_iso_timestamp()
    })

    try:
        # 获取工作流配置
        workflow = await get_workflow(workflow_id)
        nodes = workflow['nodes']
        edges = workflow['edges']

        # 构建 DAG 并执行
        dag = build_dag(nodes, edges)
        execution_context = {
            "execution_id": execution_id,
            "inputs": input_data,
            "node_outputs": {},
            "task": task
        }

        # 拓扑排序执行
        execution_order = topological_sort(dag)

        for node_id in execution_order:
            node = nodes[node_id]

            # 发送节点开始事件
            await publish_event(redis_client, execution_id, {
                "event": "node_start",
                "node": node_id,
                "node_name": node.get('name'),
                "node_type": node.get('type'),
                "timestamp": get_iso_timestamp()
            })

            # 执行节点
            start_time = time.time()
            result = await execute_node(node, execution_context)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 存储输出
            execution_context['node_outputs'][node_id] = result

            # 发送节点完成事件
            await publish_event(redis_client, execution_id, {
                "event": "node_complete",
                "node": node_id,
                "output": result,
                "elapsed_ms": elapsed_ms,
                "timestamp": get_iso_timestamp()
            })

    except Exception as e:
        await publish_event(redis_client, execution_id, {
            "event": "execution_error",
            "error": str(e),
            "timestamp": get_iso_timestamp()
        })

    finally:
        await publish_event(redis_client, execution_id, {
            "event": "execution_complete",
            "timestamp": get_iso_timestamp()
        })
        await redis_client.close()


async def execute_llm_node_stream(node: dict, context: dict, redis_client, execution_id: str):
    """流式执行 LLM 节点"""

    node_id = node['id']
    config = node.get('config', {})

    # 获取模型配置
    provider = config.get('provider', 'openai')
    model = config.get('model', 'gpt-4')
    messages = build_messages(node, context)

    # 发送思考开始事件
    await publish_event(redis_client, execution_id, {
        "event": "thinking_start",
        "node": node_id,
        "timestamp": get_iso_timestamp()
    })

    # 调用流式 API
    if provider == 'openai':
        response = await call_openai_stream(model, messages)
    elif provider == 'anthropic':
        response = await call_anthropic_stream(model, messages)

    # 处理流式响应
    full_response = []
    reasoning_content = []

    async for chunk in response:
        if chunk.type == 'content_block_delta':
            if chunk.name == 'thinking':
                # 思考链内容
                reasoning_content.append(chunk.text)
                await publish_event(redis_client, execution_id, {
                    "event": "thinking_stream",
                    "node": node_id,
                    "thoughts": reasoning_content[-3:],  # 最近3段思考
                    "timestamp": get_iso_timestamp()
                })
            else:
                # 正常输出
                full_response.append(chunk.text)
                await publish_event(redis_client, execution_id, {
                    "event": "token_stream",
                    "node": node_id,
                    "tokens": full_response[-20:],  # 最近20个token
                    "timestamp": get_iso_timestamp()
                })

    return {
        "content": ''.join(full_response),
        "reasoning": ''.join(reasoning_content)
    }


async def publish_event(redis_client, execution_id: str, event: dict):
    """发布事件到 Redis Pub/Sub"""
    await redis_client.publish(
        f'stream:{execution_id}',
        json.dumps(event, ensure_ascii=False)
    )
```

#### 32.2.3 流式 API 视图

```python
# Backend/workflows/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import uuid


class WorkflowStreamExecuteView(APIView):
    """流式执行工作流"""

    def post(self, request, workflow_id):
        # 验证用户权限
        if not self._check_execution_permission(request.user, workflow_id):
            return Response(
                {"error": "无权限执行此工作流"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 验证工作流
        workflow = self._get_workflow(workflow_id)
        if not workflow:
            return Response(
                {"error": "工作流不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 生成执行 ID
        execution_id = str(uuid.uuid4())

        # 创建执行记录
        execution = self._create_execution(workflow_id, execution_id, request.user)

        # 触发异步任务
        execute_workflow_stream.delay(
            workflow_id=workflow_id,
            execution_id=execution_id,
            input_data=request.data.get('input_data', {})
        )

        # 返回 WebSocket 连接地址
        return Response({
            "execution_id": execution_id,
            "stream_url": f"ws://{request.get_host()}/ws/execution/{execution_id}/",
            "status": "started"
        })


class WorkflowStreamStatusView(APIView):
    """查询流式执行状态"""

    def get(self, request, execution_id):
        execution = self._get_execution(execution_id)

        if not execution:
            return Response(
                {"error": "执行记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "execution_id": execution_id,
            "status": execution.status,
            "progress": execution.progress,
            "current_node": execution.current_node,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "error": execution.error_message
        })
```

#### 32.2.4 WebSocket 路由配置

```python
# Backend/config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from workflows.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

```python
# Backend/workflows/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/execution/(?P<execution_id>[^/]+)/$', consumers.StreamExecutionConsumer.as_asgi()),
]
```

### 32.3 前端流式 UI 组件

#### 32.3.1 流式执行面板

```vue
<!-- Frontend/src/components/workflow/StreamExecutionPanel.vue -->
<template>
  <div class="stream-execution-panel">
    <!-- 执行状态栏 -->
    <div class="execution-status-bar">
      <el-progress
        :percentage="executionProgress"
        :status="executionStatus"
        :stroke-width="8"
      />
      <div class="status-info">
        <span class="execution-id">执行ID: {{ executionId }}</span>
        <span class="elapsed-time">耗时: {{ elapsedTime }}ms</span>
      </div>
    </div>

    <!-- 节点执行进度 -->
    <div class="node-progress-list">
      <div
        v-for="node in nodeStatusList"
        :key="node.id"
        class="node-progress-item"
        :class="[`status-${node.status}`]"
      >
        <div class="node-icon">
          <el-icon v-if="node.status === 'pending'" class="pending"><Clock /></el-icon>
          <el-icon v-else-if="node.status === 'running'" class="running"><Loading /></el-icon>
          <el-icon v-else-if="node.status === 'completed'" class="success"><CircleCheck /></el-icon>
          <el-icon v-else class="error"><CircleClose /></el-icon>
        </div>
        <div class="node-info">
          <span class="node-name">{{ node.name }}</span>
          <span class="node-type">{{ node.type }}</span>
        </div>
        <div class="node-time" v-if="node.elapsed_ms">
          {{ node.elapsed_ms }}ms
        </div>
      </div>
    </div>

    <!-- 实时输出预览 -->
    <div class="stream-output-panel">
      <div class="panel-header">
        <span>实时输出</span>
        <el-button size="small" @click="toggleExpand">
          {{ expanded ? '收起' : '展开' }}
        </el-button>
      </div>

      <div class="output-content" :class="{ expanded }">
        <!-- LLM 输出 -->
        <div v-for="output in streamOutputs" :key="output.nodeId" class="output-item">
          <div class="output-header">
            <span class="node-label">{{ output.nodeName }}</span>
            <span class="token-count">{{ output.tokens.length }} tokens</span>
          </div>

          <!-- 流式文本 -->
          <div class="stream-text">
            <span
              v-for="(token, idx) in output.tokens"
              :key="idx"
              class="token"
              :style="{ animationDelay: idx * 50 + 'ms' }"
            >
              {{ token }}
            </span>
            <span v-if="output.isStreaming" class="cursor">|</span>
          </div>

          <!-- 思考链 -->
          <div v-if="output.thinking && output.thinking.length > 0" class="thinking-chain">
            <el-collapse>
              <el-collapse-item title="💭 思考链" name="thinking">
                <div
                  v-for="(thought, idx) in output.thinking"
                  :key="idx"
                  class="thought-item"
                >
                  {{ thought }}
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 推理过程 -->
          <div v-if="output.reasoning" class="reasoning-box">
            <span class="reasoning-label">推理：</span>
            {{ output.reasoning }}
          </div>
        </div>
      </div>
    </div>

    <!-- 最终结果 -->
    <div v-if="finalResult" class="final-result">
      <div class="result-header">
        <span>执行结果</span>
        <el-button size="small" @click="copyResult">复制</el-button>
      </div>
      <div class="result-content">{{ finalResult }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { ElMessage } from 'element-plus'

const props = defineProps({
  workflowId: String,
  executionId: String
})

const store = useWorkflowStore()

// 状态
const executionProgress = ref(0)
const executionStatus = ref('')
const elapsedTime = ref(0)
const startTime = ref(null)
const expanded = ref(true)
const finalResult = ref(null)

// 节点状态列表
const nodeStatusList = ref([])

// 流式输出
const streamOutputs = ref({})

// WebSocket 连接
let ws = null
let reconnectAttempts = 0
const maxReconnectAttempts = 5

// 初始化连接
const initWebSocket = () => {
  const wsUrl = `ws://${window.location.host}/ws/execution/${props.executionId}/`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected')
    reconnectAttempts = 0
    startTime.value = Date.now()
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleStreamEvent(data)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  ws.onclose = () => {
    if (reconnectAttempts < maxReconnectAttempts) {
      setTimeout(() => {
        reconnectAttempts++
        initWebSocket()
      }, 1000 * reconnectAttempts)
    }
  }
}

// 处理流式事件
const handleStreamEvent = (event) => {
  switch (event.event) {
    case 'execution_start':
      executionStatus.value = ''
      elapsedTime.value = 0
      startTimer()
      break

    case 'node_start':
      updateNodeStatus(event.node, 'running', event.node_name)
      break

    case 'node_complete':
      updateNodeStatus(event.node, 'completed', null, event.elapsed_ms)
      if (event.reasoning) {
        updateStreamOutput(event.node, { reasoning: event.reasoning })
      }
      updateProgress()
      break

    case 'node_error':
      updateNodeStatus(event.node, 'error')
      updateProgress()
      break

    case 'thinking_start':
      updateStreamOutput(event.node, { thinking: [] })
      break

    case 'thinking_stream':
      updateStreamOutput(event.node, { thinking: event.thoughts })
      break

    case 'token_stream':
      updateStreamOutput(event.node, {
        tokens: event.tokens,
        isStreaming: true
      })
      break

    case 'execution_complete':
      executionStatus.value = 'success'
      executionProgress.value = 100
      finalResult.value = event.result
      stopTimer()
      break

    case 'execution_error':
      executionStatus.value = 'exception'
      stopTimer()
      ElMessage.error(event.error)
      break
  }
}

// 更新节点状态
const updateNodeStatus = (nodeId, status, name, elapsedMs) => {
  const existing = nodeStatusList.value.find(n => n.id === nodeId)
  if (existing) {
    existing.status = status
    if (elapsedMs) existing.elapsed_ms = elapsedMs
  } else {
    nodeStatusList.value.push({ id: nodeId, name, status, elapsed_ms: elapsedMs })
  }
}

// 更新流式输出
const updateStreamOutput = (nodeId, data) => {
  if (!streamOutputs.value[nodeId]) {
    streamOutputs.value[nodeId] = {
      nodeId,
      nodeName: nodeStatusList.value.find(n => n.id === nodeId)?.name || nodeId,
      tokens: [],
      thinking: [],
      reasoning: '',
      isStreaming: false
    }
  }

  if (data.tokens !== undefined) {
    streamOutputs.value[nodeId].tokens = data.tokens
  }
  if (data.thinking !== undefined) {
    streamOutputs.value[nodeId].thinking = data.thinking
  }
  if (data.reasoning !== undefined) {
    streamOutputs.value[nodeId].reasoning = data.reasoning
    streamOutputs.value[nodeId].isStreaming = false
  }
}

// 更新进度
const updateProgress = () => {
  const completed = nodeStatusList.value.filter(n => n.status === 'completed').length
  const total = nodeStatusList.value.length
  if (total > 0) {
    executionProgress.value = Math.round((completed / total) * 100)
  }
}

// 计时器
let timer = null
const startTimer = () => {
  timer = setInterval(() => {
    if (startTime.value) {
      elapsedTime.value = Date.now() - startTime.value
    }
  }, 100)
}
const stopTimer = () => {
  if (timer) clearInterval(timer)
}

// 复制结果
const copyResult = async () => {
  await navigator.clipboard.writeText(finalResult.value)
  ElMessage.success('已复制到剪贴板')
}

// 生命周期
onMounted(() => {
  initWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
  stopTimer()
})
</script>

<style scoped>
.stream-execution-panel {
  background: var(--bg-color);
  border-radius: 8px;
  padding: 16px;
}

.execution-status-bar {
  margin-bottom: 16px;
}

.status-info {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.node-progress-list {
  margin-bottom: 16px;
}

.node-progress-item {
  display: flex;
  align-items: center;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 4px;
  background: var(--bg-light);
}

.node-progress-item.status-running {
  background: rgba(64, 158, 255, 0.1);
}

.node-progress-item.status-completed {
  background: rgba(103, 194, 58, 0.1);
}

.node-progress-item.status-error {
  background: rgba(245, 108, 108, 0.1);
}

.node-icon {
  margin-right: 12px;
}

.running {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.token {
  opacity: 0;
  animation: fadeIn 0.1s forwards;
}

@keyframes fadeIn {
  to { opacity: 1; }
}

.thinking-chain {
  margin-top: 8px;
  padding: 8px;
  background: rgba(144, 147, 153, 0.1);
  border-radius: 4px;
  font-size: 12px;
}

.reasoning-box {
  margin-top: 8px;
  padding: 8px;
  background: rgba(230, 162, 60, 0.1);
  border-left: 3px solid #e6a23c;
  font-size: 13px;
}

.reasoning-label {
  font-weight: 600;
  color: #e6a23c;
}
</style>
```

#### 32.3.2 流式输出组件

```vue
<!-- Frontend/src/components/workflow/StreamingOutput.vue -->
<template>
  <div class="streaming-output" :class="{ compact }">
    <!-- 输出头部 -->
    <div class="output-header">
      <span class="output-title">{{ title }}</span>
      <div class="output-meta">
        <span v-if="tokenCount" class="token-count">{{ tokenCount }} tokens</span>
        <span v-if="elapsedMs" class="elapsed">{{ elapsedMs }}ms</span>
      </div>
    </div>

    <!-- 思考链区域 -->
    <div v-if="showThinking && thinkingChain.length > 0" class="thinking-section">
      <div class="section-header" @click="thinkingExpanded = !thinkingExpanded">
        <span class="section-icon">💭</span>
        <span>思考过程</span>
        <el-icon class="expand-icon" :class="{ expanded: thinkingExpanded }">
          <ArrowDown />
        </el-icon>
      </div>
      <el-collapse-transition>
        <div v-if="thinkingExpanded" class="thinking-content">
          <div
            v-for="(thought, idx) in thinkingChain"
            :key="idx"
            class="thought-step"
            :style="{ animationDelay: idx * 100 + 'ms' }"
          >
            <span class="step-number">{{ idx + 1 }}</span>
            <span class="step-text">{{ thought }}</span>
          </div>
        </div>
      </el-collapse-transition>
    </div>

    <!-- 主要输出 -->
    <div class="main-output" ref="outputRef">
      <span
        v-for="(token, idx) in tokens"
        :key="idx"
        class="token"
        :class="{ 'streaming': isStreaming && idx === tokens.length - 1 }"
        :style="{ animationDelay: idx * 30 + 'ms' }"
      >{{ token }}</span>
      <span v-if="isStreaming" class="cursor">▊</span>
    </div>

    <!-- 复制按钮 -->
    <div class="output-actions">
      <el-button size="small" @click="copyOutput">
        <el-icon><CopyDocument /></el-icon>
        复制
      </el-button>
      <el-button v-if="canSave" size="small" @click="saveToHistory">
        <el-icon><DocumentAdd /></el-icon>
        保存
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  title: { type: String, default: '输出' },
  tokens: { type: Array, default: () => [] },
  thinkingChain: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  elapsedMs: { type: Number, default: 0 },
  showThinking: { type: Boolean, default: true },
  compact: { type: Boolean, default: false },
  canSave: { type: Boolean, default: true }
})

const emit = defineEmits(['copy', 'save'])

const outputRef = ref(null)
const thinkingExpanded = ref(true)

const tokenCount = computed(() => props.tokens.join('').length)

// 自动滚动到底部
watch(() => props.tokens, async () => {
  await nextTick()
  if (outputRef.value) {
    outputRef.value.scrollTop = outputRef.value.scrollHeight
  }
})

const copyOutput = () => {
  const text = props.tokens.join('')
  navigator.clipboard.writeText(text)
  emit('copy', text)
}

const saveToHistory = () => {
  emit('save', {
    content: props.tokens.join(''),
    thinking: props.thinkingChain,
    timestamp: Date.now()
  })
}
</script>

<style scoped>
.streaming-output {
  background: var(--bg-white);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.streaming-output.compact {
  font-size: 13px;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-light);
  border-bottom: 1px solid var(--border-color);
}

.output-title {
  font-weight: 600;
  color: var(--text-primary);
}

.output-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.thinking-section {
  border-bottom: 1px solid var(--border-color);
  background: rgba(230, 162, 60, 0.05);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}

.section-header:hover {
  background: rgba(230, 162, 60, 0.1);
}

.expand-icon {
  transition: transform 0.3s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.thinking-content {
  padding: 0 16px 16px;
}

.thought-step {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-left: 2px solid #e6a23c;
  margin-left: 12px;
  padding-left: 16px;
  animation: slideIn 0.3s ease-out forwards;
  opacity: 0;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.step-number {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e6a23c;
  color: white;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-text {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.main-output {
  padding: 16px;
  min-height: 100px;
  max-height: 400px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.8;
}

.token {
  opacity: 0;
  animation: tokenFadeIn 0.15s ease-out forwards;
}

@keyframes tokenFadeIn {
  to { opacity: 1; }
}

.token.streaming {
  color: var(--primary-color);
  font-weight: 500;
}

.cursor {
  display: inline-block;
  animation: blink 0.8s infinite;
  color: var(--primary-color);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.output-actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-light);
}
</style>
```

### 32.4 使用示例

#### 触发流式执行

```javascript
// Frontend/src/api/workflow.js
import request from './request'

export const workflowApi = {
  // 流式执行
  async executeStream(workflowId, inputData) {
    const response = await request.post(`/workflows/${workflowId}/execute/stream/`, {
      input_data: inputData
    })

    return {
      executionId: response.data.execution_id,
      streamUrl: response.data.stream_url,
      status: response.data.status
    }
  },

  // 查询执行状态
  async getExecutionStatus(executionId) {
    return request.get(`/workflows/execute/${executionId}/status/`)
  }
}

// Frontend/src/views/WorkflowExecute.vue
<script setup>
import { ref } from 'vue'
import { workflowApi } from '@/api/workflow'
import StreamExecutionPanel from '@/components/workflow/StreamExecutionPanel.vue'

const executionInfo = ref(null)

const handleExecute = async () => {
  const result = await workflowApi.executeStream(workflowId.value, {
    text: inputText.value
  })

  executionInfo.value = result
}
</script>

<template>
  <div>
    <el-button type="primary" @click="handleExecute">
      流式执行
    </el-button>

    <StreamExecutionPanel
      v-if="executionInfo"
      :workflow-id="workflowId"
      :execution-id="executionInfo.executionId"
    />
  </div>
</template>
```

### 32.5 事件类型完整列表

| 事件类型 | 说明 | 数据结构 |
|----------|------|----------|
| `execution_start` | 执行开始 | `{execution_id, timestamp}` |
| `execution_complete` | 执行完成 | `{result, total_elapsed_ms, timestamp}` |
| `execution_error` | 执行错误 | `{error, timestamp}` |
| `node_start` | 节点开始 | `{node, node_name, node_type, timestamp}` |
| `node_complete` | 节点完成 | `{node, output, elapsed_ms, reasoning?, timestamp}` |
| `node_error` | 节点错误 | `{node, error, timestamp}` |
| `thinking_start` | 思考开始 | `{node, timestamp}` |
| `thinking_stream` | 思考流 | `{node, thoughts: [], timestamp}` |
| `token_stream` | Token 流 | `{node, tokens: [], timestamp}` |
| `progress_update` | 进度更新 | `{node, progress: 0-100, timestamp}` |

### 32.6 性能优化建议

```python
# 1. Redis 连接池
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True
)

# 2. 事件批量发送
class EventBatcher:
    def __init__(self, redis, execution_id, batch_size=5, flush_interval=0.1):
        self.redis = redis
        self.execution_id = execution_id
        self.batch_size = batch_size
        self.buffer = []
        self.flush_interval = flush_interval

    async def publish(self, event):
        self.buffer.append(event)
        if len(self.buffer) >= self.batch_size:
            await self.flush()

    async def flush(self):
        if self.buffer:
            pipe = self.redis.pipeline()
            for event in self.buffer:
                pipe.publish(f'stream:{self.execution_id}', json.dumps(event))
            await pipe.execute()
            self.buffer = []

# 3. 前端节流渲染
const handleStreamEvent = throttle((event) => {
  // 处理事件
}, 16) // ~60fps
```

---

## 下一步建议

完成以上所有步骤后，你的 Flowly 工作流平台已经具备以下能力：

| 模块 | 功能 |
|------|------|
| **编辑器** | 增强拖拽、节点对齐、迷你地图、撤销重做、自动排列 |
| **变量系统** | 全局变量、环境变量、变量插值、敏感信息管理 |
| **节点** | HTTP 请求、代码执行、定时调度、迭代器、API 调用 |
| **RAG** | 文档上传、文本分割、Embedding、向量存储、混合检索 |
| **协作** | 团队管理、权限控制、分享链接、评论 |
| **监控** | 执行统计、趋势图表、告警规则、通知 |
| **计费** | 多租户、套餐管理、用量限制 |
| **集成** | REST API、SDK、Webhook |
| **体验** | 模板市场、深色模式、国际化 |
| **流式执行** | 边执行边展示、Token 流、思考链可视化 |

下一步可以：
1. **部署上线** - 使用 Step 19-22 的部署配置
2. **扩展节点** - 添加更多业务场景节点
3. **性能优化** - 引入缓存、CDN、数据库读写分离
4. **商业化** - 接入支付、构建 SaaS 平台

---

## 附录：API 参考

### 认证相关

```http
# 注册
POST /api/auth/register/
{
  "username": "user1",
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123"
}

# 登录
POST /api/auth/token/
{
  "username": "user1",
  "password": "password123"
}

# 刷新 Token
POST /api/auth/token/refresh/
{
  "refresh": "your-refresh-token"
}
```

### 工作流执行

```http
# 触发执行（异步）
POST /api/workflows/{id}/execute/
{
  "input_data": {"text": "Hello world"}
}

# 查询状态
GET /api/workflows/{id}/execute/{exec_id}/status/

# WebSocket 实时进度
ws://localhost:8000/ws/execution/{execution_id}/
```

### Prompt 模板

```http
# 列表
GET /api/prompt-templates/

# 创建
POST /api/prompt-templates/
{
  "name": "翻译助手",
  "category": "translate",
  "template": "将以下文本翻译成{lang}：{text}",
  "variables": ["lang", "text"]
}

# 渲染预览
POST /api/prompt-templates/{id}/render/
{
  "context": {"lang": "English", "text": "你好"}
}
```

### 流式执行 API

```http
# 触发流式执行
POST /api/workflows/{id}/execute/stream/
{
  "input_data": {"text": "分析这段评论"}
}

# 响应
{
  "execution_id": "uuid-string",
  "stream_url": "ws://localhost:8000/ws/execution/{execution_id}/",
  "status": "started"
}

# WebSocket 事件示例
# 连接后服务器会推送以下事件：
{
  "event": "node_start",
  "node": "llm-1",
  "node_name": "情感分析",
  "timestamp": "2026-05-03T10:35:00Z"
}
{
  "event": "thinking_stream",
  "node": "llm-1",
  "thoughts": ["分析情感倾向...", "发现负面词汇", "结论：投诉"]
}
{
  "event": "token_stream",
  "node": "llm-1",
  "tokens": ["这", "是", "一", "个", "投", "诉"]
}
```

```

---

## Step 33 - 自然语言生成工作流 (NL to Workflow)

> **创新亮点**：用户用自然语言描述需求，AI 自动生成可视化工作流，打通"想法"到"实现"的最后一公里

### 33.1 产品愿景

```
用户输入：
"帮我创建一个工作流：分析用户评论，如果是投诉就转人工，
如果是表扬就回复感谢，如果是建议就存档等待后续处理"

AI 自动生成：
┌─────────────────────────────────────────────────────────────────┐
│                      生成的工作流图                              │
│                                                                  │
│    ┌─────────┐                                                   │
│    │  输入   │                                                   │
│    │ 评论    │                                                   │
│    └────┬────┘                                                   │
│         │                                                        │
│         ▼                                                        │
│    ┌──────────────┐                                               │
│    │  情感分析    │  🔍 分析评论情感倾向                          │
│    └────┬─────────┘                                               │
│         │                                                        │
│    ┌────┴────┬──────────┐                                        │
│    ▼         ▼          ▼                                       │
│ ┌──────┐ ┌──────┐  ┌────────┐                                    │
│ │投诉   │ │表扬   │  │建议     │                                    │
│ └───┬──┘ └───┬──┘  └────┬───┘                                    │
│     │        │          │                                        │
│     ▼        ▼          ▼                                        │
│ ┌──────┐ ┌──────┐  ┌────────┐                                    │
│ │转人工 │ │回复感谢│  │存档    │                                    │
│ └──────┘ └──────┘  └────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 33.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       用户界面层                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  对话界面          │    工作流预览    │    编辑器            │  │
│  │  "分析评论..."    │    可视化预览    │    进一步调整        │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ 自然语言描述
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AI 理解层                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    NL to Workflow Engine                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │ 意图识别   │→ │ 实体提取   │→ │ 工作流结构生成       │  │ │
│  │  │ Intent     │  │ Entity     │  │ Structure Gen        │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ 工作流 JSON
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       验证与优化层                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │ 语法验证   │  │ 连线验证   │  │ 优化建议生成         │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ 可执行工作流
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       执行与反馈层                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  用户确认 → 执行测试 → 反馈优化 → 保存工作流                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 33.3 后端实现

#### 33.3.1 NL to Workflow 核心服务

```python
# Backend/nl_to_workflow/services.py
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class NodeType(Enum):
    """支持的节点类型"""
    INPUT = "input"
    LLM = "llm"
    CONDITION = "condition"
    BRANCH = "branch"
    TEMPLATE = "template"
    HTTP = "http"
    CODE = "code"
    OUTPUT = "output"
    TRANSFER = "transfer"      # 转人工
    REPLY = "reply"           # 回复
    SAVE = "save"             # 存档


@dataclass
class Node:
    id: str
    type: str
    name: str
    config: Dict
    position: Dict  # {x, y}


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: Optional[str] = None


@dataclass
class WorkflowStructure:
    nodes: List[Node]
    edges: List[Edge]
    description: str
    estimated_cost: float  # 预估成本


class NLToWorkflowEngine:
    """自然语言转工作流引擎"""

    # 可用节点类型及其关键词映射
    NODE_KEYWORDS = {
        'input': ['输入', '用户输入', '接收', '获取'],
        'llm': ['分析', '处理', '判断', '识别', '理解', 'LLM', '大模型', 'AI'],
        'condition': ['如果', '当', '条件', '判断'],
        'branch': ['分支', '分别', '根据'],
        'template': ['回复', '模板', '格式化'],
        'http': ['请求', '调用', 'API', '接口', 'fetch'],
        'output': ['输出', '结果', '返回'],
        'transfer': ['转人工', '转接', '人工客服'],
        'reply': ['回复', '感谢', '自动回复'],
        'save': ['存档', '保存', '记录', '入库'],
    }

    # 条件分支关键词
    CONDITION_KEYWORDS = {
        'negative': ['投诉', '差评', '不满', '抱怨', '负面', '不好'],
        'positive': ['表扬', '感谢', '好评', '满意', '赞扬', '好'],
        'suggestion': ['建议', '希望', '改进', '优化', '期待'],
        'neutral': ['中性', '一般', '普通', '无感'],
    }

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider
        self.node_counter = 0
        self.edge_counter = 0

    def generate(self, user_input: str, context: Optional[Dict] = None) -> WorkflowStructure:
        """
        主入口：自然语言 → 工作流
        """
        # 1. 使用 LLM 解析用户意图
        parsed_intent = self._parse_intent(user_input)

        # 2. 构建工作流结构
        workflow = self._build_workflow_structure(parsed_intent)

        # 3. 添加优化建议
        workflow = self._optimize_workflow(workflow)

        return workflow

    def _parse_intent(self, user_input: str) -> Dict:
        """解析用户意图"""

        if self.llm_provider:
            # 使用 LLM 深度解析
            return self._llm_parse(user_input)
        else:
            # 使用规则解析（简化版）
            return self._rule_parse(user_input)

    def _llm_parse(self, user_input: str) -> Dict:
        """使用 LLM 解析用户意图"""

        system_prompt = """你是一个工作流设计助手。用户会描述一个业务流程，你需要将其解析为工作流结构。

请分析用户描述，提取：
1. 输入源（用户输入、文件、API等）
2. 核心处理步骤（LLM分析、数据处理等）
3. 条件分支（基于什么条件分叉）
4. 处理结果（输出、回复、存档等）

输出 JSON 格式：
{
    "input": {"type": "input", "description": "描述"},
    "steps": [{"type": "llm|condition|template|...", "description": "描述", "config": {...}}],
    "branches": [{"condition": "条件描述", "actions": [{"type": "节点类型", "description": "动作描述"}]}],
    "output": {"type": "output|reply|save", "description": "输出描述"}
}

只输出 JSON，不要其他内容。"""

        response = self.llm_provider.complete(
            system=system_prompt,
            user=user_input,
            temperature=0.3
        )

        try:
            return json.loads(response)
        except:
            return self._rule_parse(user_input)

    def _rule_parse(self, user_input: str) -> Dict:
        """基于规则解析用户意图（简化版）"""

        # 检测情感类型
        detected_branches = []
        for sentiment, keywords in self.CONDITION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_input:
                    detected_branches.append(sentiment)
                    break

        # 如果没有检测到，默认添加投诉和表扬分支
        if not detected_branches:
            detected_branches = ['negative', 'positive']

        return {
            "input": {"type": "input", "description": "用户输入"},
            "steps": [
                {"type": "llm", "description": "情感分析", "config": {"task": "sentiment_analysis"}}
            ],
            "branches": [
                {
                    "condition": branch,
                    "actions": [{"type": self._get_action_type(branch), "description": f"{branch}处理"}]
                }
                for branch in detected_branches
            ],
            "output": {"type": "output", "description": "输出结果"}
        }

    def _get_action_type(self, branch: str) -> str:
        """根据分支类型确定动作"""
        mapping = {
            'negative': 'transfer',
            'positive': 'reply',
            'suggestion': 'save',
            'neutral': 'output'
        }
        return mapping.get(branch, 'output')

    def _build_workflow_structure(self, parsed_intent: Dict) -> WorkflowStructure:
        """构建工作流结构"""

        nodes = []
        edges = []

        # 1. 添加输入节点
        input_node = self._create_node(
            'input',
            parsed_intent.get('input', {}).get('description', '用户输入')
        )
        nodes.append(input_node)

        current_node = input_node

        # 2. 添加处理步骤
        for step in parsed_intent.get('steps', []):
            step_node = self._create_node(
                step['type'],
                step['description'],
                step.get('config', {})
            )
            nodes.append(step_node)
            edges.append(self._create_edge(current_node.id, step_node.id))
            current_node = step_node

        # 3. 添加条件分支
        branches = parsed_intent.get('branches', [])
        if branches:
            # 创建条件节点
            condition_node = self._create_node(
                'condition',
                '条件判断',
                {"field": "sentiment", "type": "switch"}
            )
            nodes.append(condition_node)
            edges.append(self._create_edge(current_node.id, condition_node.id))

            # 为每个分支创建处理节点
            branch_mapping = {
                'negative': ('投诉分支', 'transfer', '转人工处理'),
                'positive': ('表扬分支', 'reply', '感谢回复'),
                'suggestion': ('建议分支', 'save', '存档待处理'),
                'neutral': ('中性分支', 'output', '普通处理'),
            }

            for branch in branches:
                condition = branch.get('condition', 'default')
                branch_name, action_type, branch_desc = branch_mapping.get(
                    condition,
                    ('默认分支', 'output', '默认处理')
                )

                # 创建分支节点
                branch_node = self._create_node(
                    action_type,
                    branch_desc,
                    {"branch": condition}
                )
                nodes.append(branch_node)

                # 创建分支连线
                edge = self._create_edge(
                    condition_node.id,
                    branch_node.id,
                    label=branch_name
                )
                edges.append(edge)

                # 添加后续处理
                for action in branch.get('actions', []):
                    action_node = self._create_node(
                        action.get('type', 'output'),
                        action.get('description', '处理')
                    )
                    nodes.append(action_node)
                    edges.append(self._create_edge(branch_node.id, action_node.id))

        # 4. 添加输出节点
        output_node = self._create_node(
            'output',
            parsed_intent.get('output', {}).get('description', '输出结果')
        )
        nodes.append(output_node)

        # 连接最后一个节点到输出
        if branches:
            # 找到最后一个节点（通常是最后一个分支的最后一个节点）
            for node in reversed(nodes):
                if node.id != output_node.id and node.type not in ['condition']:
                    edges.append(self._create_edge(node.id, output_node.id))
                    break
        else:
            edges.append(self._create_edge(current_node.id, output_node.id))

        # 5. 生成描述
        description = self._generate_description(parsed_intent)

        # 6. 预估成本
        estimated_cost = len(nodes) * 0.001  # 简单估算

        return WorkflowStructure(
            nodes=nodes,
            edges=edges,
            description=description,
            estimated_cost=estimated_cost
        )

    def _create_node(self, node_type: str, name: str, config: Dict = None) -> Node:
        """创建节点"""
        self.node_counter += 1
        node_id = f"node_{self.node_counter}"

        # 计算位置（简单的网格布局）
        x = 100 + (self.node_counter % 4) * 200
        y = 100 + (self.node_counter // 4) * 120

        return Node(
            id=node_id,
            type=node_type,
            name=name,
            config=config or {},
            position={"x": x, "y": y}
        )

    def _create_edge(self, source: str, target: str, label: str = None) -> Edge:
        """创建连线"""
        self.edge_counter += 1
        return Edge(
            id=f"edge_{self.edge_counter}",
            source=source,
            target=target,
            label=label
        )

    def _generate_description(self, parsed_intent: Dict) -> str:
        """生成工作流描述"""
        description_parts = []

        if parsed_intent.get('input'):
            description_parts.append(f"接收 {parsed_intent['input'].get('description', '输入')}")

        steps = parsed_intent.get('steps', [])
        if steps:
            step_names = [s.get('description', s.get('type')) for s in steps]
            description_parts.append(" → ".join(step_names))

        branches = parsed_intent.get('branches', [])
        if branches:
            branch_names = [b.get('condition', '未知') for b in branches]
            description_parts.append(f"根据 [{', '.join(branch_names)}] 分支处理")

        return "，".join(description_parts)

    def _optimize_workflow(self, workflow: WorkflowStructure) -> WorkflowStructure:
        """优化工作流"""
        # 去除孤立节点
        connected_nodes = set()
        for edge in workflow.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        workflow.nodes = [n for n in workflow.nodes if n.id in connected_nodes]

        return workflow

    def validate_workflow(self, workflow: WorkflowStructure) -> Tuple[bool, List[str]]:
        """验证工作流是否有效"""
        errors = []

        # 检查是否有输入节点
        input_nodes = [n for n in workflow.nodes if n.type == 'input']
        if not input_nodes:
            errors.append("缺少输入节点")

        # 检查是否有输出节点
        output_nodes = [n for n in workflow.nodes if n.type == 'output']
        if not output_nodes:
            errors.append("缺少输出节点")

        # 检查孤立节点
        connected_nodes = set()
        for edge in workflow.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        isolated_nodes = [n for n in workflow.nodes if n.id not in connected_nodes]
        if isolated_nodes:
            errors.append(f"孤立节点: {[n.name for n in isolated_nodes]}")

        # 检查循环引用
        if self._has_cycle(workflow):
            errors.append("存在循环引用")

        return len(errors) == 0, errors

    def _has_cycle(self, workflow: WorkflowStructure) -> bool:
        """检查是否有循环"""
        # 构建邻接表
        graph = {node.id: [] for node in workflow.nodes}
        for edge in workflow.edges:
            graph[edge.source].append(edge.target)

        # DFS 检测环
        visited = set()
        rec_stack = set()

        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in graph:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False
```

#### 33.3.2 API 视图

```python
# Backend/nl_to_workflow/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, name='dispatch')
class NLToWorkflowView(APIView):
    """自然语言生成工作流"""

    def post(self, request):
        user_input = request.data.get('input', '')

        if not user_input:
            return Response(
                {"error": "请提供自然语言描述"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 获取 LLM Provider（如果有配置）
        llm_provider = self._get_llm_provider(request.user)

        # 生成工作流
        engine = NLToWorkflowEngine(llm_provider=llm_provider)
        workflow = engine.generate(user_input)

        # 验证工作流
        is_valid, errors = engine.validate_workflow(workflow)

        # 转换为前端格式
        workflow_data = self._to_client_format(workflow, user_input)

        return Response({
            "workflow": workflow_data,
            "description": workflow.description,
            "estimated_cost": workflow.estimated_cost,
            "is_valid": is_valid,
            "validation_errors": errors
        })

    def _get_llm_provider(self, user):
        """获取用户的 LLM Provider"""
        from workflows.services import get_provider
        try:
            return get_provider(user)
        except:
            return None

    def _to_client_format(self, workflow, user_input):
        """转换为前端格式"""
        return {
            "name": f"AI生成工作流 - {user_input[:20]}...",
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "name": node.name,
                    "config": node.config,
                    "position": node.position
                }
                for node in workflow.nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label
                }
                for edge in workflow.edges
            ]
        }


class NLToWorkflowRefineView(APIView):
    """优化/调整生成的工作流"""

    def post(self, request):
        workflow_data = request.data.get('workflow', {})
        user_feedback = request.data.get('feedback', '')

        if not workflow_data or not user_feedback:
            return Response(
                {"error": "请提供工作流和调整意见"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 使用 LLM 理解反馈并调整工作流
        adjusted_workflow = self._refine_workflow(workflow_data, user_feedback)

        return Response({
            "workflow": adjusted_workflow,
            "message": "工作流已根据反馈调整"
        })

    def _refine_workflow(self, workflow_data, feedback):
        """根据反馈调整工作流"""
        # 简化实现：可以调用 LLM 进行更智能的调整
        return workflow_data
```

#### 33.3.3 URL 路由

```python
# Backend/nl_to_workflow/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.NLToWorkflowView.as_view(), name='nl-generate'),
    path('refine/', views.NLToWorkflowRefineView.as_view(), name='nl-refine'),
]
```

```python
# Backend/config/urls.py
urlpatterns = [
    # ... 其他路由
    path('api/nl-workflow/', include('nl_to_workflow.urls')),
]
```

### 33.4 前端实现

#### 33.4.1 对话式工作流生成器

```vue
<!-- Frontend/src/views/NLWorkflowCreator.vue -->
<template>
  <div class="nl-workflow-creator">
    <!-- 顶部标题 -->
    <div class="creator-header">
      <h2>AI 工作流助手</h2>
      <p>用自然语言描述你的需求，AI 自动生成工作流</p>
    </div>

    <!-- 主内容区 -->
    <div class="creator-content">
      <!-- 左侧：对话区 -->
      <div class="conversation-panel">
        <!-- 对话历史 -->
        <div class="conversation-history" ref="conversationRef">
          <div
            v-for="(msg, idx) in conversationHistory"
            :key="idx"
            class="message"
            :class="[`message-${msg.role}`]"
          >
            <div class="message-avatar">
              <el-icon v-if="msg.role === 'user'" size="20"><User /></el-icon>
              <el-icon v-else size="20"><Robot /></el-icon>
            </div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)" />
              <div v-if="msg.workflow" class="message-workflow-preview">
                <el-button size="small" @click="previewWorkflow(msg.workflow)">
                  预览工作流
                </el-button>
              </div>
            </div>
          </div>

          <!-- 生成中状态 -->
          <div v-if="isGenerating" class="message message-assistant">
            <div class="message-avatar">
              <el-icon size="20"><Robot /></el-icon>
            </div>
            <div class="message-content">
              <div class="generating-indicator">
                <span class="dot" />
                <span class="dot" />
                <span class="dot" />
              </div>
              <span class="generating-text">AI 正在分析需求...</span>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="conversation-input">
          <el-input
            v-model="userInput"
            type="textarea"
            :rows="3"
            placeholder="描述你的工作流需求...
例如：创建一个工作流来分析用户评论，如果是投诉就转人工，如果是表扬就回复感谢"
            @keydown.enter.meta="handleSend"
            @keydown.enter.ctrl="handleSend"
          />
          <div class="input-actions">
            <el-button @click="showExamples = true">查看示例</el-button>
            <el-button type="primary" @click="handleSend" :loading="isGenerating">
              <el-icon v-if="!isGenerating"><Position /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </div>

      <!-- 右侧：工作流预览 -->
      <div class="workflow-preview-panel" :class="{ expanded: showPreview }">
        <div class="preview-header">
          <h3>工作流预览</h3>
          <el-button-group>
            <el-button :type="viewMode === 'graph' ? 'primary' : ''" @click="viewMode = 'graph'">
              <el-icon><Connection /></el-icon>
            </el-button>
            <el-button :type="viewMode === 'json' ? 'primary' : ''" @click="viewMode = 'json'">
              <el-icon><Document /></el-icon>
            </el-button>
          </el-button-group>
        </div>

        <!-- 可视化预览 -->
        <div v-if="currentWorkflow && viewMode === 'graph'" class="workflow-graph">
          <WorkflowGraph :nodes="currentWorkflow.nodes" :edges="currentWorkflow.edges" />
        </div>

        <!-- JSON 预览 -->
        <div v-else-if="currentWorkflow && viewMode === 'json'" class="workflow-json">
          <pre>{{ JSON.stringify(currentWorkflow, null, 2) }}</pre>
        </div>

        <!-- 空状态 -->
        <div v-else class="preview-empty">
          <el-empty description="发送描述后预览将显示在这里" />
        </div>

        <!-- 操作按钮 -->
        <div v-if="currentWorkflow" class="preview-actions">
          <el-button @click="adjustWorkflow">调整</el-button>
          <el-button @click="testWorkflow">测试执行</el-button>
          <el-button type="primary" @click="saveWorkflow">保存工作流</el-button>
        </div>
      </div>
    </div>

    <!-- 调整对话框 -->
    <el-dialog v-model="showAdjustDialog" title="调整工作流" width="600px">
      <el-input
        v-model="adjustFeedback"
        type="textarea"
        :rows="4"
        placeholder="描述你想要如何调整...
例如：添加一个审核节点、在表扬分支后增加积分奖励"
      />
      <template #footer>
        <el-button @click="showAdjustDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAdjustment">确认调整</el-button>
      </template>
    </el-dialog>

    <!-- 示例对话框 -->
    <el-dialog v-model="showExamples" title="示例需求" width="700px">
      <div class="example-list">
        <div
          v-for="example in examples"
          :key="example.title"
          class="example-item"
          @click="useExample(example)"
        >
          <h4>{{ example.title }}</h4>
          <p>{{ example.description }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { workflowApi } from '@/api/workflow'

const router = useRouter()

// 状态
const userInput = ref('')
const conversationHistory = ref([])
const isGenerating = ref(false)
const currentWorkflow = ref(null)
const showPreview = ref(true)
const viewMode = ref('graph')
const showAdjustDialog = ref(false)
const adjustFeedback = ref('')
const showExamples = ref(false)

// 示例需求
const examples = [
  {
    title: '客服评论分析',
    description: '分析用户评论，根据情感自动分流处理',
    input: '创建一个工作流：分析用户评论，如果是投诉就转人工，如果是表扬就回复感谢，如果是建议就存档'
  },
  {
    title: '文章生成流程',
    description: '自动生成SEO优化文章',
    input: '创建一个文章生成工作流：输入关键词，通过LLM生成大纲，再生成完整文章，最后输出到CMS'
  },
  {
    title: '数据清洗流程',
    description: '批量处理和清洗数据',
    input: '创建一个数据清洗工作流：读取CSV文件，去重，过滤无效数据，导出结果'
  },
  {
    title: '智能客服',
    description: '多轮对话客服系统',
    input: '创建一个智能客服工作流：接收用户问题，判断类型，查询知识库，如果找不到答案就转人工'
  },
  {
    title: '招聘筛选',
    description: '自动筛选简历',
    input: '创建一个简历筛选工作流：接收简历，提取关键信息，评估匹配度，高分简历通知HR，低分存档'
  }
]

// 发送消息
const handleSend = async () => {
  const input = userInput.value.trim()
  if (!input || isGenerating.value) return

  // 添加用户消息
  conversationHistory.value.push({
    role: 'user',
    content: input
  })

  userInput.value = ''
  isGenerating.value = true

  // 滚动到底部
  await nextTick()
  scrollToBottom()

  try {
    // 调用 API 生成工作流
    const response = await workflowApi.generateFromNL(input)

    // 添加 AI 响应
    conversationHistory.value.push({
      role: 'assistant',
      content: `已根据您的需求生成工作流：
- 输入节点：接收数据
- 分析节点：使用 LLM 进行处理
- 分支处理：根据条件分流
- 输出节点：返回结果

点击下方按钮预览或进一步调整。`,
      workflow: response.data.workflow
    })

    // 更新当前工作流
    currentWorkflow.value = response.data.workflow

  } catch (error) {
    ElMessage.error('生成失败，请重试')
    conversationHistory.value.push({
      role: 'assistant',
      content: '抱歉，生成过程中出现错误，请稍后重试。'
    })
  } finally {
    isGenerating.value = false
    await nextTick()
    scrollToBottom()
  }
}

// 调整工作流
const adjustWorkflow = () => {
  showAdjustDialog.value = true
}

const submitAdjustment = async () => {
  if (!adjustFeedback.value.trim()) return

  try {
    const response = await workflowApi.refineWorkflow(currentWorkflow.value, adjustFeedback.value)
    currentWorkflow.value = response.data.workflow

    conversationHistory.value.push({
      role: 'user',
      content: adjustFeedback.value
    })

    conversationHistory.value.push({
      role: 'assistant',
      content: '已根据您的反馈调整工作流。',
      workflow: response.data.workflow
    })

    showAdjustDialog.value = false
    adjustFeedback.value = ''
  } catch (error) {
    ElMessage.error('调整失败')
  }
}

// 预览工作流
const previewWorkflow = (workflow) => {
  currentWorkflow.value = workflow
  showPreview.value = true
}

// 测试执行
const testWorkflow = async () => {
  ElMessage.info('正在跳转到测试页面...')
  // 保存到 store 并跳转
  const workflowStore = useWorkflowStore()
  workflowStore.setCurrentWorkflow(currentWorkflow.value)
  router.push('/workflow/execute')
}

// 保存工作流
const saveWorkflow = async () => {
  try {
    const response = await workflowApi.save(currentWorkflow.value)
    ElMessage.success('工作流已保存')
    router.push(`/workflow/edit/${response.data.id}`)
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

// 使用示例
const useExample = (example) => {
  userInput.value = example.input
  showExamples.value = false
}

// 格式化消息
const formatMessage = (content) => {
  return content.replace(/\n/g, '<br>')
}

// 滚动到底部
const scrollToBottom = () => {
  if (conversationRef.value) {
    conversationRef.value.scrollTop = conversationRef.value.scrollHeight
  }
}

const conversationRef = ref(null)
</script>

<style scoped>
.nl-workflow-creator {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
}

.creator-header {
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.creator-header h2 {
  margin: 0 0 8px;
}

.creator-header p {
  margin: 0;
  opacity: 0.9;
}

.creator-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.conversation-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
}

.conversation-history {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-user .message-avatar {
  background: #409eff;
  color: white;
}

.message-assistant .message-avatar {
  background: #67c23a;
  color: white;
}

.message-content {
  max-width: 70%;
}

.message-user .message-content {
  text-align: right;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
}

.message-user .message-text {
  background: #409eff;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-assistant .message-text {
  background: var(--bg-white);
  border-bottom-left-radius: 4px;
}

.generating-indicator {
  display: flex;
  gap: 4px;
  padding: 12px;
}

.generating-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  animation: bounce 1.4s infinite ease-in-out;
}

.generating-indicator .dot:nth-child(1) { animation-delay: -0.32s; }
.generating-indicator .dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.conversation-input {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-white);
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.workflow-preview-panel {
  width: 50%;
  display: flex;
  flex-direction: column;
  background: var(--bg-white);
}

.workflow-preview-panel.expanded {
  width: 60%;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.workflow-graph {
  flex: 1;
  overflow: auto;
}

.workflow-json {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.workflow-json pre {
  margin: 0;
  font-size: 12px;
}

.preview-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-actions {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid var(--border-color);
}

.example-list {
  display: grid;
  gap: 12px;
}

.example-item {
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.example-item:hover {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.05);
}

.example-item h4 {
  margin: 0 0 8px;
}

.example-item p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
```

#### 33.4.2 API 调用

```javascript
// Frontend/src/api/workflow.js
export const workflowApi = {
  // 自然语言生成工作流
  async generateFromNL(userInput) {
    return request.post('/nl-workflow/generate/', {
      input: userInput
    })
  },

  // 调整工作流
  async refineWorkflow(workflow, feedback) {
    return request.post('/nl-workflow/refine/', {
      workflow,
      feedback
    })
  },

  // 保存工作流
  async save(workflowData) {
    return request.post('/workflows/', workflowData)
  }
}
```

### 33.5 高级功能：多轮对话优化

```python
# 多轮对话上下文管理
class ConversationContext:
    """管理对话上下文，支持多轮优化"""

    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history
        self.current_workflow = None

    def add_turn(self, user_input, generated_workflow, feedback=None):
        """添加一轮对话"""
        self.history.append({
            "user_input": user_input,
            "workflow": generated_workflow,
            "feedback": feedback,
            "timestamp": datetime.now()
        })

        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_context_prompt(self) -> str:
        """构建上下文提示"""
        if not self.history:
            return ""

        context_parts = ["当前对话历史："]
        for i, turn in enumerate(self.history[-3:], 1):
            context_parts.append(f"第{i}轮：用户说「{turn['user_input']}」")
            if turn['feedback']:
                context_parts.append(f"  用户反馈：{turn['feedback']}")
            context_parts.append(f"  生成结果：节点数={len(turn['workflow']['nodes'])}")

        return "\n".join(context_parts)

    def has_changes(self) -> bool:
        """检查是否有未保存的更改"""
        return self.current_workflow is not None
```

### 33.6 提示词工程

```python
# 高质量工作流生成的提示词模板
WORKFLOW_GENERATION_PROMPT = """
## 角色
你是一个专业的工作流设计师，精通业务流程自动化和 AI 应用设计。

## 任务
将用户的自然语言需求转换为可视化工作流结构。

## 要求

### 1. 节点设计
- 输入节点：定义数据来源
- 处理节点：使用 LLM、代码、数据转换等
- 条件节点：基于条件进行分支
- 输出节点：返回结果、发送消息、保存数据等

### 2. 连线规则
- 每个节点必须至少有一个输入和输出（除开始/结束节点）
- 条件分支必须清晰标注每个分支的条件
- 避免过于复杂的连线，保持流程清晰

### 3. 命名规范
- 节点名称简洁明了，体现功能
- 使用中文命名
- 条件分支标注具体条件（如：情感=负面）

### 4. 输出格式
```json
{
    "input": {"type": "input", "description": "..."},
    "steps": [{"type": "...", "description": "...", "config": {...}}],
    "branches": [{"condition": "...", "actions": [...]}],
    "output": {"type": "...", "description": "..."}
}
```

## 用户需求
{user_input}

请分析需求并输出工作流结构（仅 JSON）。
"""

# 工作流优化提示词
WORKFLOW_REFINE_PROMPT = """
## 当前工作流
{current_workflow}

## 用户反馈
{feedback}

## 任务
理解用户反馈，对工作流进行调整。

请输出调整后的工作流 JSON。
"""
```

### 33.7 示例输出

```javascript
// 输入
"帮我创建一个工作流：分析用户评论，如果是投诉就转人工，
如果是表扬就回复感谢，如果是建议就存档等待后续处理"

// 输出
{
  "workflow": {
    "name": "AI生成工作流 - 评论分析...",
    "nodes": [
      {
        "id": "node_1",
        "type": "input",
        "name": "接收评论",
        "config": {"input_type": "text"},
        "position": {"x": 100, "y": 100}
      },
      {
        "id": "node_2",
        "type": "llm",
        "name": "情感分析",
        "config": {
          "task": "sentiment_analysis",
          "model": "gpt-4",
          "prompt": "分析以下评论的情感：{comment}"
        },
        "position": {"x": 300, "y": 100}
      },
      {
        "id": "node_3",
        "type": "condition",
        "name": "条件分支",
        "config": {"field": "sentiment", "type": "switch"},
        "position": {"x": 500, "y": 100}
      },
      {
        "id": "node_4",
        "type": "transfer",
        "name": "转人工处理",
        "config": {"transfer_to": "customer_service"},
        "position": {"x": 700, "y": 50}
      },
      {
        "id": "node_5",
        "type": "reply",
        "name": "感谢回复",
        "config": {
          "template": "感谢您的支持，期待为您提供更好的服务！"
        },
        "position": {"x": 700, "y": 150}
      },
      {
        "id": "node_6",
        "type": "save",
        "name": "存档待处理",
        "config": {"collection": "suggestions"},
        "position": {"x": 700, "y": 250}
      }
    ],
    "edges": [
      {"id": "edge_1", "source": "node_1", "target": "node_2"},
      {"id": "edge_2", "source": "node_2", "target": "node_3"},
      {"id": "edge_3", "source": "node_3", "target": "node_4", "label": "投诉"},
      {"id": "edge_4", "source": "node_3", "target": "node_5", "label": "表扬"},
      {"id": "edge_5", "source": "node_3", "target": "node_6", "label": "建议"}
    ]
  },
  "description": "接收评论 → 情感分析 → 根据情感（投诉/表扬/建议）分支处理",
  "estimated_cost": 0.006,
  "is_valid": true,
  "validation_errors": []
}
```

```

---

## Step 34 - AI Agent 智能体编排

> **创新亮点**：从静态工作流升级为动态决策的智能体，支持自主工具调用、多 Agent 协作、自我反思

### 34.1 什么是 AI Agent？

```
传统工作流：                        AI Agent：
┌─────────┐                        ┌─────────┐
│   输入   │                        │   感知   │ ← 接收输入
└────┬────┘                        └────┬────┘
     │                                  │
     ▼                                  ▼
┌─────────┐                        ┌─────────┐
│  固定   │                        │  决策   │ ← AI 思考该做什么
│  执行   │                        └────┬────┘
└────┬────┘                              │
     │                              ┌─────┴─────┐
     ▼                              ▼           ▼
┌─────────┐                   ┌─────────┐ ┌─────────┐
│   输出   │                   │  行动   │ │  使用   │
└─────────┘                   │  (Act)  │ │  工具   │
                              └────┬────┘ └────┬────┘
                                   │           │
                                   └─────┬─────┘
                                         │
                                         ▼
                                   ┌─────────┐
                                   │  反思   │ ← 评估结果，调整策略
                                   └─────────┘
```

### 34.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent 运行时层                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Agent Runtime Engine                    ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   ││
│  │  │  感知    │→ │  规划    │→ │  行动    │→ │  反思    │   ││
│  │  │ (Perceive)│  │(Planning)│  │ (Act)    │  │(Reflect) │   ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        工具系统层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 搜索工具 │  │ 代码执行 │  │ 数据库   │  │ API 调用 │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 文件读写 │  │ 网页爬虫 │  │ 计算器   │  │ 自定义   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        多 Agent 协作层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 规划 Agent│  │ 执行 Agent│  │ 审核 Agent│  │ 报告 Agent│       │
│  │ Planner  │  │ Executor │  │ Critic   │  │ Reporter │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 34.3 核心模型定义

```python
# Backend/agents/models.py
from django.db import models
from django.contrib.auth import get_user_model


class Agent(models.Model):
    """AI Agent 定义"""

    name = models.CharField(max_length=100, verbose_name="Agent 名称")
    description = models.TextField(verbose_name="描述")
    avatar = models.URLField(blank=True, verbose_name="头像")

    # Agent 类型
    class AgentType(models.TextChoices):
        GENERAL = 'general', '通用 Agent'
        PLANNER = 'planner', '规划 Agent'
        EXECUTOR = 'executor', '执行 Agent'
        CRITIC = 'critic', '审核 Agent'
        REPORTER = 'reporter', '报告 Agent'
        CUSTOM = 'custom', '自定义'

    agent_type = models.CharField(
        max_length=20,
        choices=AgentType.choices,
        default=AgentType.GENERAL
    )

    # 系统提示词
    system_prompt = models.TextField(verbose_name="系统提示词")

    # 可用工具
    available_tools = models.JSONField(default=list, verbose_name="可用工具列表")

    # 配置
    config = models.JSONField(default=dict, verbose_name="配置")

    # 状态
    is_active = models.BooleanField(default=True)

    # 关联项目
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='agents'
    )

    # 创建者和时间
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agents'
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'

    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()})"


class Tool(models.Model):
    """Agent 工具定义"""

    name = models.CharField(max_length=100, unique=True, verbose_name="工具名称")
    description = models.TextField(verbose_name="功能描述")

    # 工具类型
    class ToolType(models.TextChoices):
        FUNCTION = 'function', '函数工具'
        API = 'api', 'API 调用'
        SEARCH = 'search', '搜索工具'
        CODE = 'code', '代码执行'
        DATABASE = 'database', '数据库'
        FILE = 'file', '文件操作'

    tool_type = models.CharField(
        max_length=20,
        choices=ToolType.choices,
        default=ToolType.FUNCTION
    )

    # 函数定义（OpenAI Function Calling 格式）
    function_schema = models.JSONField(verbose_name="函数定义")

    # 执行器
    executor_path = models.CharField(
        max_length=255,
        help_text="执行器的 Python 模块路径，如: agents.tools.search.execute"
    )

    # 认证配置
    auth_config = models.JSONField(default=dict, verbose_name="认证配置")

    # 限流配置
    rate_limit = models.JSONField(default=dict, verbose_name="限流配置")

    # 成本配置
    cost_per_call = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name="每次调用成本"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tools'
        verbose_name = '工具'
        verbose_name_plural = 'Tools'

    def __str__(self):
        return self.name


class AgentExecution(models.Model):
    """Agent 执行记录"""

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='executions'
    )

    # 执行输入
    input_data = models.JSONField(verbose_name="输入数据")

    # 执行状态
    class Status(models.TextChoices):
        RUNNING = 'running', '执行中'
        WAITING_TOOL = 'waiting_tool', '等待工具'
        COMPLETED = 'completed', '完成'
        FAILED = 'failed', '失败'
        STOPPED = 'stopped', '已停止'

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING
    )

    # 思考过程（JSON 数组）
    thought_process = models.JSONField(default=list, verbose_name="思考过程")

    # 执行结果
    output_data = models.JSONField(null=True, blank=True, verbose_name="输出数据")

    # 使用的工具调用
    tool_calls = models.JSONField(default=list, verbose_name="工具调用记录")

    # 错误信息
    error_message = models.TextField(blank=True, verbose_name="错误信息")

    # 统计
    total_steps = models.IntegerField(default=0, verbose_name="总步数")
    total_tokens = models.IntegerField(default=0, verbose_name="消耗 Token")
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name="总成本"
    )

    # 执行配置
    max_steps = models.IntegerField(default=10, verbose_name="最大步数")
    timeout = models.IntegerField(default=300, verbose_name="超时时间(秒)")

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'agent_executions'
        verbose_name = '执行记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.agent.name} - {self.id}"


class MultiAgentSession(models.Model):
    """多 Agent 协作会话"""

    name = models.CharField(max_length=200, verbose_name="会话名称")

    # 参与 Agent
    agents = models.ManyToManyField(
        Agent,
        through='AgentParticipation',
        related_name='sessions'
    )

    # 会话状态
    class SessionStatus(models.TextChoices):
        PLANNING = 'planning', '规划中'
        EXECUTING = 'executing', '执行中'
        REVIEWING = 'reviewing', '审核中'
        COMPLETED = 'completed', '已完成'
        FAILED = 'failed', '失败'

    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.PLANNING
    )

    # 消息历史
    messages = models.JSONField(default=list, verbose_name="消息历史")

    # 最终结果
    final_result = models.JSONField(null=True, blank=True, verbose_name="最终结果")

    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'multi_agent_sessions'
        verbose_name = '多Agent会话'
        ordering = ['-created_at']


class AgentParticipation(models.Model):
    """Agent 参与记录"""

    session = models.ForeignKey(
        MultiAgentSession,
        on_delete=models.CASCADE
    )
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE
    )

    # 角色
    role = models.CharField(max_length=50, verbose_name="角色")

    # 贡献
    contribution = models.JSONField(default=dict, verbose_name="贡献内容")

    class Meta:
        db_table = 'agent_participations'
        unique_together = ['session', 'agent']
```

### 34.4 Agent 执行引擎

```python
# Backend/agents/engine.py
import json
import asyncio
import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgentAction(Enum):
    """Agent 可执行的动作"""
    CONTINUE = "continue"      # 继续执行
    RESPOND = "respond"        # 返回最终响应
    CALL_TOOL = "call_tool"    # 调用工具
    ASK_HUMAN = "ask_human"   # 询问人类
    STOP = "stop"             # 停止执行


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: str = None
    duration_ms: int = 0


@dataclass
class AgentMessage:
    """Agent 消息"""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: List[Dict] = field(default_factory=list)
    tool_call_id: str = None


@dataclass
class AgentState:
    """Agent 执行状态"""
    messages: List[AgentMessage] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    current_step: int = 0
    thought_history: List[str] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool:
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters: Dict = {}

    def __init__(self):
        self._executor = None

    def set_executor(self, executor: Callable):
        """设置执行器"""
        self._executor = executor

    async def execute(self, **kwargs) -> Dict:
        """执行工具"""
        if self._executor:
            return await self._executor(**kwargs)
        raise NotImplementedError("Tool must implement execute method")

    def get_schema(self) -> Dict:
        """获取函数定义 schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class AgentEngine:
    """Agent 执行引擎"""

    def __init__(
        self,
        agent_config: Dict,
        tools: List[BaseTool],
        llm_provider=None,
        max_steps: int = 10
    ):
        self.agent_config = agent_config
        self.tools = {tool.name: tool for tool in tools}
        self.llm_provider = llm_provider
        self.max_steps = max_steps

        # 初始化状态
        self.state = AgentState()

        # 回调
        self.on_thought: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
        self.on_step_complete: Optional[Callable] = None

    async def run(self, user_input: str, context: Dict = None) -> Dict:
        """
        运行 Agent
        """
        # 初始化消息
        self._init_messages(user_input, context)

        # 执行循环
        while self.state.current_step < self.max_steps:
            # 1. 思考
            thought = await self._think()
            self.state.thought_history.append(thought)

            if self.on_thought:
                await self.on_thought(thought, self.state.current_step)

            # 2. 决定行动
            action = await self._decide(thought)

            # 3. 执行行动
            result = await self._act(action)

            # 检查是否结束
            if action in [AgentAction.RESPOND, AgentAction.STOP]:
                break

            # 4. 反思
            await self._reflect()

            self.state.current_step += 1

            if self.on_step_complete:
                await self.on_step_complete(self.state)

        return self._format_output()

    def _init_messages(self, user_input: str, context: Dict):
        """初始化消息"""
        self.state = AgentState()

        # 系统消息
        system_content = self.agent_config.get('system_prompt', '')
        system_content += "\n\n当前时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.state.messages.append(AgentMessage(
            role="system",
            content=system_content
        ))

        # 用户消息
        self.state.messages.append(AgentMessage(
            role="user",
            content=user_input
        ))

        # 上下文
        if context:
            self.state.metadata.update(context)

    async def _think(self) -> str:
        """思考：分析当前状态，决定下一步"""

        # 构建思考提示
        thought_prompt = f"""你是一个 AI Agent，正在执行任务。

当前步骤: {self.state.current_step + 1}/{self.max_steps}
已用工具: {len(self.state.tool_calls)}

请分析当前状态，思考：
1. 用户的目标是什么？
2. 已有的信息和工具调用结果是什么？
3. 下一步应该做什么？

请用简洁的语言描述你的思考过程（50字以内）。
"""

        response = await self.llm_provider.complete(
            messages=[
                {"role": "system", "content": thought_prompt},
                *self._format_llm_messages()
            ],
            temperature=0.7
        )

        return response

    async def _decide(self, thought: str) -> AgentAction:
        """决定行动"""

        # 构建决策提示
        available_tools = [t.get_schema() for t in self.tools.values()]

        decision_prompt = f"""你是一个 AI Agent，需要决定下一步行动。

当前思考: {thought}

可用工具:
{json.dumps(available_tools, ensure_ascii=False, indent=2)}

请决定下一步行动，输出 JSON：
{{
    "action": "continue|respond|call_tool|ask_human|stop",
    "reason": "决策理由",
    "tool_name": "如果需要调用工具，填工具名",
    "tool_args": {{}}  // 工具参数
}}

如果没有工具可用或任务已完成，返回 respond。
如果需要更多信息，返回 ask_human。
"""

        response = await self.llm_provider.complete(
            messages=[
                {"role": "system", "content": decision_prompt},
                *self._format_llm_messages()
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        try:
            decision = json.loads(response)
            self.state.metadata['last_decision'] = decision
            return self._parse_action(decision.get('action', 'continue'))
        except:
            return AgentAction.CONTINUE

    async def _act(self, action: AgentAction) -> Any:
        """执行行动"""

        if action == AgentAction.CALL_TOOL:
            decision = self.state.metadata.get('last_decision', {})
            tool_name = decision.get('tool_name')
            tool_args = decision.get('tool_args', {})

            return await self._call_tool(tool_name, tool_args)

        elif action == AgentAction.RESPOND:
            return await self._generate_response()

        elif action == AgentAction.ASK_HUMAN:
            return {"type": "human_input_required"}

        return None

    async def _call_tool(self, tool_name: str, args: Dict) -> ToolCall:
        """调用工具"""
        import time
        start_time = time.time()

        tool_call = ToolCall(
            id=f"call_{len(self.state.tool_calls) + 1}",
            name=tool_name,
            arguments=args
        )

        try:
            tool = self.tools.get(tool_name)
            if not tool:
                raise ValueError(f"Tool '{tool_name}' not found")

            # 执行工具
            result = await tool.execute(**args)
            tool_call.result = result

            # 添加工具结果到消息
            self.state.messages.append(AgentMessage(
                role="tool",
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call.id
            ))

        except Exception as e:
            tool_call.error = str(e)
            logger.error(f"Tool call failed: {tool_name}, error: {e}")

        tool_call.duration_ms = int((time.time() - start_time) * 1000)
        self.state.tool_calls.append(tool_call)

        if self.on_tool_call:
            await self.on_tool_call(tool_call)

        return tool_call

    async def _generate_response(self) -> str:
        """生成最终响应"""

        response_prompt = """基于之前的对话和工具调用结果，生成最终响应。

要求：
1. 直接回答用户的问题
2. 如果有数据，用清晰的方式呈现
3. 简洁明了，不要重复之前的信息
"""

        response = await self.llm_provider.complete(
            messages=[
                {"role": "system", "content": response_prompt},
                *self._format_llm_messages()
            ],
            temperature=0.7
        )

        return response

    async def _reflect(self):
        """反思：评估当前结果，调整策略"""

        reflect_prompt = f"""评估当前执行状态：

步骤: {self.state.current_step + 1}/{self.max_steps}
思考历史: {self.state.thought_history[-3:]}

是否需要继续执行？任务是否已完成？
输出 JSON：
{{
    "need_continue": true/false,
    "quality_score": 0-10,
    "improvement": "如果有改进建议，描述它"
}}
"""

        try:
            response = await self.llm_provider.complete(
                messages=[
                    {"role": "system", "content": reflect_prompt},
                    *self._format_llm_messages()
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            reflection = json.loads(response)
            self.state.metadata['reflection'] = reflection

        except Exception as e:
            logger.error(f"Reflection failed: {e}")

    def _parse_action(self, action_str: str) -> AgentAction:
        """解析行动字符串"""
        mapping = {
            'continue': AgentAction.CONTINUE,
            'respond': AgentAction.RESPOND,
            'call_tool': AgentAction.CALL_TOOL,
            'ask_human': AgentAction.ASK_HUMAN,
            'stop': AgentAction.STOP
        }
        return mapping.get(action_str.lower(), AgentAction.CONTINUE)

    def _format_llm_messages(self) -> List[Dict]:
        """格式化消息给 LLM"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.state.messages
            if msg.role != "system"
        ]

    def _format_output(self) -> Dict:
        """格式化输出"""
        return {
            "response": self.state.messages[-1].content if self.state.messages else "",
            "thought_history": self.state.thought_history,
            "tool_calls": [
                {
                    "name": tc.name,
                    "args": tc.arguments,
                    "result": tc.result,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms
                }
                for tc in self.state.tool_calls
            ],
            "steps": self.state.current_step,
            "metadata": self.state.metadata
        }
```

### 34.5 内置工具实现

```python
# Backend/agents/tools/__init__.py
from .search import SearchTool
from .calculator import CalculatorTool
from .web_scraper import WebScraperTool
from .database import DatabaseTool
from .code_executor import CodeExecutorTool

__all__ = [
    'SearchTool',
    'CalculatorTool',
    'WebScraperTool',
    'DatabaseTool',
    'CodeExecutorTool'
]
```

```python
# Backend/agents/tools/search.py
import asyncio
from typing import Dict, Any
from . import BaseTool


class SearchTool(BaseTool):
    """搜索工具"""

    name = "search"
    description = "搜索互联网获取最新信息。当你需要查询实时数据、新闻或不确定的信息时使用。"

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "max_results": {
                "type": "integer",
                "description": "最大结果数",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def __init__(self):
        super().__init__()
        self._search_client = None

    def set_search_client(self, client):
        """设置搜索客户端（如 Tavily, SerpAPI）"""
        self._search_client = client

    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """执行搜索"""

        if not self._search_client:
            # 使用模拟结果（实际项目中接入真实搜索 API）
            return {
                "query": query,
                "results": [
                    {
                        "title": f"关于 '{query}' 的信息",
                        "url": "https://example.com/result1",
                        "snippet": f"这是关于 '{query}' 的搜索结果摘要..."
                    }
                    for i in range(max_results)
                ],
                "total": max_results
            }

        # 真实搜索
        results = await self._search_client.search(query, max_results)

        return {
            "query": query,
            "results": results,
            "total": len(results)
        }


class CalculatorTool(BaseTool):
    """计算器工具"""

    name = "calculate"
    description = "执行数学计算。当需要进行精确计算或复杂数学运算时使用。"

    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如: 2 + 2, sin(pi/2), sqrt(16)"
            }
        },
        "required": ["expression"]
    }

    async def execute(self, expression: str) -> Dict[str, Any]:
        """执行计算"""
        try:
            # 安全计算（实际项目建议使用 ast.parse + eval 或专用库）
            import math
            import re

            # 替换常见数学函数
            safe_dict = {
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'sqrt': math.sqrt,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'pi': math.pi,
                'e': math.e,
                'abs': abs,
                'round': round,
                'pow': pow,
                'max': max,
                'min': min,
            }

            # 只允许安全字符
            if not re.match(r'^[\d\s\+\-\*\/\(\)\.\,\w]+$', expression):
                raise ValueError("Invalid expression")

            result = eval(expression, {"__builtins__": {}}, safe_dict)

            return {
                "expression": expression,
                "result": result,
                "success": True
            }

        except Exception as e:
            return {
                "expression": expression,
                "error": str(e),
                "success": False
            }


class WebScraperTool(BaseTool):
    """网页爬虫工具"""

    name = "scrape_webpage"
    description = "爬取网页内容。当需要从特定网页获取详细信息时使用。"

    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "网页 URL"
            },
            "selectors": {
                "type": "object",
                "description": "CSS 选择器，用于提取特定内容",
                "properties": {
                    "title": "string",
                    "content": "string",
                    "links": "string"
                }
            }
        },
        "required": ["url"]
    }

    async def execute(self, url: str, selectors: Dict = None) -> Dict[str, Any]:
        """爬取网页"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # 简单解析（实际项目建议用 BeautifulSoup）
                content = response.text

                result = {
                    "url": url,
                    "status_code": response.status_code,
                    "title": self._extract_title(content),
                    "content_length": len(content),
                    "content_preview": content[:500]
                }

                if selectors:
                    result["extracted"] = self._extract_by_selectors(content, selectors)

                return result

        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "success": False
            }

    def _extract_title(self, html: str) -> str:
        """提取标题"""
        import re
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        return match.group(1) if match else ""

    def _extract_by_selectors(self, html: str, selectors: Dict) -> Dict:
        """根据选择器提取内容"""
        # 简化实现
        return {}


class DatabaseTool(BaseTool):
    """数据库查询工具"""

    name = "query_database"
    description = "查询数据库获取结构化数据。用于获取用户信息、订单记录等业务数据。"

    parameters = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "表名"
            },
            "filters": {
                "type": "object",
                "description": "过滤条件，如: {\"user_id\": 123}"
            },
            "fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "返回的字段列表"
            },
            "limit": {
                "type": "integer",
                "description": "返回记录数限制",
                "default": 10
            }
        },
        "required": ["table"]
    }

    def __init__(self, db_model=None):
        super().__init__()
        self._db_model = db_model

    async def execute(
        self,
        table: str,
        filters: Dict = None,
        fields: list = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """执行查询"""

        # 简化实现
        return {
            "table": table,
            "filters": filters or {},
            "results": [],
            "count": 0,
            "message": "Database query executed (mock)"
        }


class CodeExecutorTool(BaseTool):
    """代码执行工具"""

    name = "execute_code"
    description = "执行 Python 代码。用于数据分析、文本处理等复杂任务。"

    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python 代码"
            },
            "language": {
                "type": "string",
                "description": "编程语言",
                "default": "python"
            }
        },
        "required": ["code"]
    }

    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """执行代码"""

        if language != "python":
            return {
                "error": f"Language '{language}' not supported",
                "success": False
            }

        try:
            # 安全的代码执行（实际项目建议使用 Pyodide 或专门的沙箱）
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            exec_globals = {}
            exec(code, exec_globals)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            return {
                "output": output,
                "success": True
            }

        except Exception as e:
            import sys
            sys.stdout = old_stdout
            return {
                "error": str(e),
                "success": False
            }
```

### 34.6 多 Agent 协作

```python
# Backend/agents/multi_agent.py
import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AgentRole(Enum):
    """Agent 角色"""
    PLANNER = "planner"      # 规划者：分解任务
    EXECUTOR = "executor"   # 执行者：执行具体任务
    CRITIC = "critic"       # 审核者：评估结果
    REPORTER = "reporter"   # 报告者：汇总结果


@dataclass
class AgentMessage:
    """Agent 间消息"""
    from_agent: str
    to_agent: str  # * 表示广播
    content: str
    attachments: Dict[str, Any] = None
    timestamp: float = 0


class MultiAgentOrchestrator:
    """多 Agent 编排器"""

    def __init__(self, agents: Dict[str, AgentEngine], config: Dict = None):
        self.agents = agents
        self.config = config or {}
        self.message_queue = asyncio.Queue()
        self.shared_context = {}

    async def run(self, task: str) -> Dict[str, Any]:
        """
        运行多 Agent 协作
        """
        # 1. 规划阶段 - Planner 分解任务
        plan = await self._planning_phase(task)

        # 2. 执行阶段 - Executors 执行子任务
        results = await self._execution_phase(plan)

        # 3. 审核阶段 - Critic 评估结果
        critique = await self._critique_phase(results)

        # 4. 改进阶段 - 根据审核意见改进
        if not critique['approved']:
            results = await self._improvement_phase(results, critique)

        # 5. 报告阶段 - Reporter 汇总结果
        final_report = await self._report_phase(results, critique)

        return {
            "task": task,
            "plan": plan,
            "results": results,
            "critique": critique,
            "report": final_report
        }

    async def _planning_phase(self, task: str) -> List[Dict]:
        """规划阶段"""
        planner = self.agents.get('planner')
        if not planner:
            return [{"task": task, "subtasks": [task]}]

        # Planner 分析任务并分解
        response = await planner.run(
            f"分解以下任务为可执行的子任务：\n{task}\n\n"
            "输出 JSON 格式：{\"subtasks\": [{\"description\": \"...\", \"agent\": \"executor\"}]}"
        )

        try:
            import json
            plan = json.loads(response['response'])
            return plan.get('subtasks', [{'task': task}])
        except:
            return [{"task": task, "agent": "executor"}]

    async def _execution_phase(self, plan: List[Dict]) -> List[Dict]:
        """执行阶段"""
        executor = self.agents.get('executor')
        if not executor:
            return []

        results = []
        for subtask in plan:
            result = await executor.run(subtask['task'])
            results.append({
                "subtask": subtask['task'],
                "result": result,
                "status": "success" if result else "failed"
            })

        return results

    async def _critique_phase(self, results: List[Dict]) -> Dict:
        """审核阶段"""
        critic = self.agents.get('critic')
        if not critic:
            return {"approved": True, "issues": []}

        critique_prompt = f"""审核以下任务执行结果：

{results}

评估：
1. 结果是否满足原始需求？
2. 是否有遗漏或错误？
3. 是否需要改进？

输出 JSON：
{{
    "approved": true/false,
    "issues": ["问题1", "问题2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}
"""

        response = await critic.run(critique_prompt)

        try:
            import json
            return json.loads(response['response'])
        except:
            return {"approved": True, "issues": [], "suggestions": []}

    async def _improvement_phase(self, results: List[Dict], critique: Dict) -> List[Dict]:
        """改进阶段"""
        executor = self.agents.get('executor')

        for issue in critique.get('issues', []):
            # 让执行者根据反馈改进
            improve_prompt = f"请改进以下问题：{issue}\n\n原始任务结果：{results}"
            improved = await executor.run(improve_prompt)

            # 更新结果
            results.append({
                "task": f"改进: {issue}",
                "result": improved,
                "status": "improved"
            })

        return results

    async def _report_phase(self, results: List[Dict], critique: Dict) -> str:
        """报告阶段"""
        reporter = self.agents.get('reporter')
        if not reporter:
            return "\n\n".join([
                f"任务 {r['task']}: {r['result']}"
                for r in results
            ])

        report_prompt = f"""根据以下执行结果生成报告：

执行结果：{results}
审核意见：{critique}

请生成清晰、简洁的报告。
"""

        response = await reporter.run(report_prompt)
        return response.get('response', '')


# 使用示例
async def example():
    # 初始化 Agent
    planner = AgentEngine(
        agent_config={"system_prompt": "你是一个任务规划专家..."},
        tools=[SearchTool()],
        max_steps=5
    )

    executor = AgentEngine(
        agent_config={"system_prompt": "你是一个任务执行专家..."},
        tools=[SearchTool(), CalculatorTool(), CodeExecutorTool()],
        max_steps=10
    )

    critic = AgentEngine(
        agent_config={"system_prompt": "你是一个质量审核专家..."},
        tools=[],
        max_steps=3
    )

    # 创建编排器
    orchestrator = MultiAgentOrchestrator({
        'planner': planner,
        'executor': executor,
        'critic': critic
    })

    # 运行复杂任务
    result = await orchestrator.run(
        "分析 AAPL 股票最近一个月的走势，并预测下周的走势"
    )

    print(result['report'])
```

### 34.7 前端 Agent 调试器

```vue
<!-- Frontend/src/views/AgentDebugger.vue -->
<template>
  <div class="agent-debugger">
    <!-- 左侧：Agent 配置 -->
    <div class="config-panel">
      <h3>Agent 配置</h3>

      <!-- Agent 选择 -->
      <el-form label-width="100px">
        <el-form-item label="选择 Agent">
          <el-select v-model="selectedAgentId" @change="loadAgent">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name"
              :value="agent.id"
            />
          </el-select>
        </el-form-item>

        <!-- 系统提示词 -->
        <el-form-item label="系统提示词">
          <el-input
            v-model="agentConfig.system_prompt"
            type="textarea"
            :rows="6"
          />
        </el-form-item>

        <!-- 可用工具 -->
        <el-form-item label="可用工具">
          <el-checkbox-group v-model="selectedTools">
            <el-checkbox
              v-for="tool in availableTools"
              :key="tool.name"
              :label="tool.name"
            >
              {{ tool.description }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <!-- 执行配置 -->
        <el-form-item label="最大步数">
          <el-slider v-model="agentConfig.max_steps" :min="1" :max="50" />
          <span>{{ agentConfig.max_steps }} 步</span>
        </el-form-item>
      </el-form>

      <!-- 执行按钮 -->
      <div class="action-buttons">
        <el-button type="primary" @click="executeAgent" :loading="isRunning">
          执行 Agent
        </el-button>
        <el-button @click="stopExecution" :disabled="!isRunning">
          停止
        </el-button>
        <el-button @click="resetState">重置</el-button>
      </div>
    </div>

    <!-- 中间：执行过程 -->
    <div class="execution-panel">
      <!-- 用户输入 -->
      <div class="input-section">
        <h4>输入</h4>
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="4"
          placeholder="输入任务..."
        />
      </div>

      <!-- 执行状态 -->
      <div v-if="executionState" class="execution-state">
        <div class="state-header">
          <span class="step-badge">第 {{ executionState.current_step }} 步</span>
          <span class="status-badge" :class="executionState.status">
            {{ getStatusText(executionState.status) }}
          </span>
        </div>

        <!-- 思考过程 -->
        <div class="thought-section">
          <h4>思考过程</h4>
          <div class="thought-timeline">
            <div
              v-for="(thought, idx) in executionState.thought_history"
              :key="idx"
              class="thought-item"
            >
              <div class="thought-number">{{ idx + 1 }}</div>
              <div class="thought-content">{{ thought }}</div>
            </div>
          </div>
        </div>

        <!-- 工具调用 -->
        <div class="tool-section">
          <h4>工具调用</h4>
          <div class="tool-calls">
            <div
              v-for="call in executionState.tool_calls"
              :key="call.id"
              class="tool-call-item"
              :class="{ error: call.error }"
            >
              <div class="tool-header">
                <span class="tool-name">{{ call.name }}</span>
                <span class="tool-duration">{{ call.duration_ms }}ms</span>
              </div>
              <div class="tool-args">
                <strong>参数：</strong>
                <pre>{{ JSON.stringify(call.arguments, null, 2) }}</pre>
              </div>
              <div v-if="call.result" class="tool-result">
                <strong>结果：</strong>
                <pre>{{ JSON.stringify(call.result, null, 2) }}</pre>
              </div>
              <div v-if="call.error" class="tool-error">
                <strong>错误：</strong>{{ call.error }}
              </div>
            </div>
          </div>
        </div>

        <!-- 最终响应 -->
        <div v-if="executionState.response" class="response-section">
          <h4>最终响应</h4>
          <div class="response-content">{{ executionState.response }}</div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-empty description="配置 Agent 并输入任务开始调试" />
      </div>
    </div>

    <!-- 右侧：实时日志 -->
    <div class="log-panel">
      <h4>实时日志</h4>
      <div class="log-list" ref="logListRef">
        <div
          v-for="(log, idx) in logs"
          :key="idx"
          class="log-item"
          :class="`log-${log.level}`"
        >
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { agentApi } from '@/api/agent'

const agents = ref([])
const selectedAgentId = ref(null)
const availableTools = ref([])
const selectedTools = ref([])

const agentConfig = reactive({
  system_prompt: '',
  max_steps: 10
})

const userInput = ref('')
const isRunning = ref(false)
const executionState = ref(null)
const logs = ref([])

// 加载 Agent 列表
const loadAgents = async () => {
  const response = await agentApi.getAgents()
  agents.value = response.data
}

// 加载 Agent 配置
const loadAgent = async (agentId) => {
  const response = await agentApi.getAgent(agentId)
  const agent = response.data

  agentConfig.system_prompt = agent.system_prompt
  selectedTools.value = agent.available_tools || []

  // 加载可用工具
  const toolsResponse = await agentApi.getTools()
  availableTools.value = toolsResponse.data
}

// 执行 Agent
const executeAgent = async () => {
  if (!userInput.value) return

  isRunning.value = true
  executionState.value = null
  logs.value = []

  addLog('info', `开始执行 Agent...`)

  try {
    // 使用 SSE 或 WebSocket 接收实时更新
    const eventSource = new EventSource(
      `/api/agents/execute/?` +
      `agent_id=${selectedAgentId.value}` +
      `&input=${encodeURIComponent(userInput.value)}`
    )

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'thought':
          if (!executionState.value) {
            executionState.value = { thought_history: [], tool_calls: [] }
          }
          executionState.value.thought_history.push(data.content)
          addLog('debug', `思考: ${data.content}`)
          break

        case 'tool_call':
          executionState.value.tool_calls.push(data.tool_call)
          addLog('info', `调用工具: ${data.tool_call.name}`)
          break

        case 'tool_result':
          const toolCall = executionState.value.tool_calls.find(
            tc => tc.id === data.tool_call_id
          )
          if (toolCall) {
            toolCall.result = data.result
          }
          addLog('info', `工具结果: ${data.tool_call_id}`)
          break

        case 'step':
          executionState.value.current_step = data.step
          break

        case 'complete':
          executionState.value.response = data.response
          executionState.value.status = 'completed'
          addLog('success', `执行完成`)
          eventSource.close()
          isRunning.value = false
          break

        case 'error':
          addLog('error', `错误: ${data.error}`)
          eventSource.close()
          isRunning.value = false
          break
      }
    }

    eventSource.onerror = () => {
      addLog('error', '连接断开')
      eventSource.close()
      isRunning.value = false
    }

  } catch (error) {
    addLog('error', `执行失败: ${error.message}`)
    isRunning.value = false
  }
}

// 停止执行
const stopExecution = () => {
  // 发送停止信号
  isRunning.value = false
}

// 重置
const resetState = () => {
  executionState.value = null
  userInput.value = ''
  logs.value = []
}

// 添加日志
const addLog = (level, message) => {
  logs.value.push({
    timestamp: new Date().toLocaleTimeString(),
    level,
    message
  })
}

// 获取状态文本
const getStatusText = (status) => {
  const map = {
    running: '运行中',
    waiting_tool: '等待工具',
    completed: '完成',
    failed: '失败'
  }
  return map[status] || status
}

// 滚动日志
const logListRef = ref(null)

const scrollToBottom = () => {
  if (logListRef.value) {
    logListRef.value.scrollTop = logListRef.value.scrollHeight
  }
}

// 初始化
loadAgents()
</script>

<style scoped>
.agent-debugger {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 16px;
  height: 100%;
  padding: 16px;
  background: var(--bg-color);
}

.config-panel,
.log-panel {
  background: var(--bg-white);
  border-radius: 8px;
  padding: 16px;
  overflow-y: auto;
}

.execution-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-section,
.thought-section,
.tool-section,
.response-section {
  background: var(--bg-white);
  border-radius: 8px;
  padding: 16px;
}

.state-header {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.step-badge {
  padding: 4px 12px;
  background: #409eff;
  color: white;
  border-radius: 12px;
  font-size: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.status-badge.running {
  background: #e6a23c;
  color: white;
}

.status-badge.completed {
  background: #67c23a;
  color: white;
}

.status-badge.failed {
  background: #f56c6c;
  color: white;
}

.thought-timeline {
  position: relative;
  padding-left: 24px;
}

.thought-timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e0e0e0;
}

.thought-item {
  position: relative;
  padding: 12px;
  margin-bottom: 8px;
  background: var(--bg-light);
  border-radius: 8px;
}

.thought-number {
  position: absolute;
  left: -24px;
  top: 12px;
  width: 16px;
  height: 16px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tool-call-item {
  padding: 12px;
  margin-bottom: 8px;
  background: var(--bg-light);
  border-radius: 8px;
  border-left: 3px solid #67c23a;
}

.tool-call-item.error {
  border-left-color: #f56c6c;
}

.tool-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tool-name {
  font-weight: 600;
  color: #409eff;
}

.tool-args pre,
.tool-result pre {
  background: var(--bg-white);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 150px;
  overflow: auto;
}

.log-list {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.log-item {
  padding: 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-size: 12px;
}

.log-info {
  background: #ecf5ff;
}

.log-debug {
  background: #f4f4f5;
}

.log-success {
  background: #f0f9ff;
}

.log-error {
  background: #fef0f0;
  color: #f56c6c;
}

.log-time {
  margin-right: 8px;
  color: var(--text-secondary);
}
</style>
```

### 34.8 API 接口

```python
# Backend/agents/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse
import json


class AgentListView(APIView):
    """Agent 列表"""

    def get(self, request):
        agents = Agent.objects.filter(is_active=True)
        data = [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "agent_type": a.agent_type,
                "available_tools": a.available_tools
            }
            for a in agents
        ]
        return Response(data)


class AgentDetailView(APIView):
    """Agent 详情"""

    def get(self, request, agent_id):
        try:
            agent = Agent.objects.get(id=agent_id)
            return Response({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "agent_type": agent.agent_type,
                "system_prompt": agent.system_prompt,
                "available_tools": agent.available_tools,
                "config": agent.config
            })
        except Agent.DoesNotExist:
            return Response(
                {"error": "Agent 不存在"},
                status=status.HTTP_404_NOT_FOUND
            )


class AgentExecuteView(APIView):
    """执行 Agent (SSE 流式)"""

    def get(self, request):
        agent_id = request.query_params.get('agent_id')
        user_input = request.query_params.get('input', '')

        def event_stream():
            # 这是一个生成器，yield SSE 事件
            async def generate():
                try:
                    agent = Agent.objects.get(id=agent_id)
                    tools = self._get_tools(agent.available_tools)

                    engine = AgentEngine(
                        agent_config={
                            "system_prompt": agent.system_prompt
                        },
                        tools=tools,
                        llm_provider=self._get_llm_provider(),
                        max_steps=agent.config.get('max_steps', 10)
                    )

                    # 设置回调
                    engine.on_thought = lambda t, s: yield_event(
                        "thought", {"content": t}
                    )
                    engine.on_tool_call = lambda tc: yield_event(
                        "tool_call", {"tool_call": tc.__dict__}
                    )

                    # 执行
                    result = await engine.run(user_input)

                    yield_event("complete", {"response": result['response']})

                except Exception as e:
                    yield_event("error", {"error": str(e)})

            async def yield_event(event_type, data):
                message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                yield message

            return generate()

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def _get_tools(self, tool_names):
        """获取工具实例"""
        from agents.tools import (
            SearchTool, CalculatorTool, WebScraperTool,
            DatabaseTool, CodeExecutorTool
        )

        tool_map = {
            'search': SearchTool(),
            'calculate': CalculatorTool(),
            'scrape_webpage': WebScraperTool(),
            'query_database': DatabaseTool(),
            'execute_code': CodeExecutorTool()
        }

        return [tool_map[name] for name in tool_names if name in tool_map]

    def _get_llm_provider(self):
        """获取 LLM Provider"""
        # 实现获取用户的 LLM 配置
        pass


class ToolListView(APIView):
    """工具列表"""

    def get(self, request):
        tools = Tool.objects.filter(is_active=True)
        data = [
            {
                "name": t.name,
                "description": t.description,
                "tool_type": t.tool_type,
                "schema": t.function_schema,
                "cost_per_call": float(t.cost_per_call)
            }
            for t in tools
        ]
        return Response(data)
```

### 34.9 完整示例

```python
# 完整使用示例
async def example_usage():
    """完整的多 Agent 协作示例"""

    # 1. 初始化工具
    tools = [
        SearchTool(),
        CalculatorTool(),
        WebScraperTool(),
        CodeExecutorTool()
    ]

    # 2. 创建不同的 Agent
    research_agent = AgentEngine(
        agent_config={
            "system_prompt": """你是一个研究助手，擅长搜索和收集信息。
始终使用搜索工具获取最新数据，不要编造信息。"""
        },
        tools=[SearchTool(), WebScraperTool()],
        max_steps=5
    )

    analysis_agent = AgentEngine(
        agent_config={
            "system_prompt": """你是一个数据分析专家，擅长处理数据并得出结论。
使用计算器和代码执行工具进行精确分析。"""
        },
        tools=[CalculatorTool(), CodeExecutorTool()],
        max_steps=5
    )

    report_agent = AgentEngine(
        agent_config={
            "system_prompt": """你是一个报告撰写专家，擅长将分析结果转化为清晰的报告。
报告应该结构清晰、重点突出。"""
        },
        tools=[],
        max_steps=3
    )

    # 3. 多 Agent 协作
    orchestrator = MultiAgentOrchestrator({
        'researcher': research_agent,
        'analyst': analysis_agent,
        'reporter': report_agent
    })

    # 4. 执行任务
    result = await orchestrator.run("""
    请帮我分析一下特斯拉股票：
    1. 获取最近一个月的股价走势
    2. 计算平均涨幅、最高、最低价
    3. 生成分析报告
    """)

    # 5. 输出结果
    print("=" * 50)
    print("研究报告")
    print("=" * 50)
    print(result['report'])
    print()
    print(f"执行步骤: {result['results'][-1]['result']['steps']}")
    print(f"总耗时: 假设 10 秒")
```

---

---

## Step 35 - 前端完整界面设计规范

> 本章节详细描述 Flowly 工作流平台的所有前端界面设计，包括欢迎页、登录注册、主控台、工作流编辑器等核心页面。

---

### 35.1 设计理念与视觉规范

#### 35.1.1 设计语言

Flowly 采用 **现代科技感 + 友好易用** 的设计风格，融合 Dify 的专业感与 Notion 的简洁美。

**核心设计原则**：
- **清晰层次**：信息架构分明，减少认知负担
- **流畅动效**：所有交互都有平滑过渡，提升体验
- **智能辅助**：AI 相关功能有独特视觉标识，降低使用门槛
- **暗色优先**：深色主题减少视觉疲劳，突出工作流画布

#### 35.1.2 色彩系统

```scss
// 主色调 - 深邃科技蓝
$primary-50:  #E6F0FF
$primary-100: #B3D1FF
$primary-500: #3B82F6  // 主色
$primary-600: #2563EB  // 主色悬停
$primary-700: #1D4ED8  // 主色按下
$primary-900: #1E3A8A  // 深色背景强调

// 功能色 - 语义化
$success: #10B981   // 成功/完成
$warning: #F59E0B   // 警告/待处理
$error:   #EF4444   // 错误/失败
$info:    #06B6D4   // 信息/提示

// 节点类型色
$node-llm:      #8B5CF6   // LLM 节点 - 紫色
$node-prompt:   #EC4899   // Prompt 节点 - 粉色
$node-tool:     #F97316   // 工具节点 - 橙色
$node-trigger:  #14B8A6   // 触发器节点 - 青色
$node-condition:#EAB308   // 条件判断节点 - 黄色
$node-data:     #22C55E   // 数据处理节点 - 绿色
$node-vector:   #06B6D4   // 向量存储节点 - 蓝色

// 暗色主题
$bg-primary:    #0F0F12   // 主背景
$bg-secondary:  #1A1A21   // 卡片背景
$bg-tertiary:   #252530   // 侧边栏背景
$bg-elevated:   #2D2D3A   // 浮层背景

// 边框与分割
$border-subtle:  rgba(255, 255, 255, 0.06)
$border-default: rgba(255, 255, 255, 0.1)
$border-strong:  rgba(255, 255, 255, 0.15)

// 文字色
$text-primary:   #FFFFFF
$text-secondary: #A1A1AA
$text-tertiary:  #71717A
$text-disabled:  #52525B
```

#### 35.1.3 字体系统

```scss
// 字体栈
$font-sans: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif
$font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace

// 字号层级
$text-xs:   11px   // 辅助说明
$text-sm:   12px   // 次要信息
$text-base: 14px   // 正文
$text-lg:   16px   // 标题
$text-xl:   18px   // 页面标题
$text-2xl:  24px   // 大标题
$text-3xl:  32px   // Hero 标题

// 行高
$leading-tight:  1.25   // 紧凑
$leading-normal: 1.5    // 正常
$leading-relaxed: 1.75   // 宽松
```

#### 35.1.4 间距与圆角

```scss
$space-1:  4px
$space-2:  8px
$space-3:  12px
$space-4:  16px
$space-5:  20px
$space-6:  24px
$space-8:  32px
$space-10: 40px
$space-12: 48px

$radius-sm:  4px
$radius-md:  8px
$radius-lg:  12px
$radius-xl:  16px
$radius-full: 9999px
```

#### 35.1.5 阴影系统

```scss
$shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.3)
$shadow-md:  0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3)
$shadow-lg:  0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.4)
$shadow-xl:  0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)
$shadow-glow: 0 0 20px rgba(59, 130, 246, 0.3)  // 发光效果
```

---

### 35.2 页面结构与路由

#### 35.2.1 路由配置

```javascript
// Frontend/src/router/routes.js
const routes = [
  // 公开路由
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/views/Landing.vue'),
    meta: { guest: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { guest: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPassword.vue'),
    meta: { guest: true }
  },

  // 需要认证的路由
  {
    path: '/app',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Home.vue')
      },
      {
        path: 'workflows',
        name: 'WorkflowList',
        component: () => import('@/views/workflow/List.vue')
      },
      {
        path: 'workflows/new',
        name: 'WorkflowCreate',
        component: () => import('@/views/workflow/Editor.vue')
      },
      {
        path: 'workflows/:id/edit',
        name: 'WorkflowEdit',
        component: () => import('@/views/workflow/Editor.vue')
      },
      {
        path: 'workflows/:id/execute',
        name: 'WorkflowExecute',
        component: () => import('@/views/workflow/Execute.vue')
      },
      {
        path: 'workflows/:id',
        name: 'WorkflowDetail',
        component: () => import('@/views/workflow/Detail.vue')
      },
      {
        path: 'agents',
        name: 'AgentList',
        component: () => import('@/views/agent/List.vue')
      },
      {
        path: 'agents/new',
        name: 'AgentCreate',
        component: () => import('@/views/agent/Create.vue')
      },
      {
        path: 'agents/:id/debug',
        name: 'AgentDebugger',
        component: () => import('@/views/agent/Debugger.vue')
      },
      {
        path: 'create-with-ai',
        name: 'NLWorkflowCreator',
        component: () => import('@/views/nl-workflow/Creator.vue')
      },
      {
        path: 'templates',
        name: 'TemplateGallery',
        component: () => import('@/views/template/Gallery.vue')
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('@/views/dashboard/Analytics.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/Index.vue')
      }
    ]
  },

  // 外部访问（无导航栏）
  {
    path: '/public/workflow/:id',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      {
        path: '',
        name: 'PublicWorkflow',
        component: () => import('@/views/workflow/Public.vue')
      }
    ]
  }
]
```

#### 35.2.2 页面层级关系

```
├── 公开页面
│   ├── Landing (落地页/欢迎页)
│   ├── Login (登录)
│   ├── Register (注册)
│   └── ForgotPassword (忘记密码)
│
├── 应用内页面 (带侧边栏导航)
│   ├── Dashboard (主控台)
│   ├── Workflows (工作流管理)
│   │   ├── List (列表)
│   │   ├── Editor (编辑器)
│   │   ├── Execute (执行)
│   │   └── Detail (详情)
│   ├── Agents (智能体)
│   │   ├── List (列表)
│   │   ├── Create (创建)
│   │   └── Debugger (调试)
│   ├── CreateWithAI (AI 创建工作流)
│   ├── Templates (模板中心)
│   ├── Analytics (数据分析)
│   └── Settings (设置)
│
└── 公共页面 (无导航栏)
    └── PublicWorkflow (对外分享的工作流)
```

---

### 35.3 欢迎页 (Landing Page) 详细设计

#### 35.3.1 页面概述

欢迎页是用户的第一印象，需要传达产品价值，吸引用户注册使用。包含 Hero 区域、功能展示、使用案例、定价、FAQ 等模块。

#### 35.3.2 页面结构

```
┌─────────────────────────────────────────────────────────────────┐
│  [Logo]  Flowly          功能  模板  定价  文档        [登录] [开始免费] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                          │    │
│  │     🧠 构建智能工作流                                     │    │
│  │     用 AI 自动化你的业务流程                               │    │
│  │                                                          │    │
│  │     [开始免费使用]  [观看演示]                           │    │
│  │                                                          │    │
│  │     ┌─────────────────────────────────┐                  │    │
│  │     │    🖼️ 工作流编辑器预览截图        │                  │    │
│  │     │    (带光标引导的动态演示)        │                  │    │
│  │     └─────────────────────────────────┘                  │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ─────────────────── 受信任品牌 ───────────────────               │
│       🤖 OpenAI   🔮 Anthropic   💬 Google   🔥 DeepSeek         │
│                                                                   │
│  ═════════════════════════════════════════════════════════════   │
│                                                                   │
│  核心功能                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 🎨 可视化│  │ 🤖 AI    │  │ ⚡ 实时   │  │ 🔗 无限   │       │
│  │ 编辑器   │  │ 模型支持  │  │ 执行     │  │ 集成     │       │
│  │ 拖拽节点 │  │ 多模型    │  │ 流式输出  │  │ API     │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                   │
│  ═════════════════════════════════════════════════════════════   │
│                                                                   │
│  工作流程示例                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ┌─────────┐     ┌─────────┐     ┌─────────┐          │    │
│  │  │  用户   │────▶│  AI    │────▶│  邮件   │          │    │
│  │  │  反馈   │     │ 分析   │     │  通知   │          │    │
│  │  └─────────┘     └─────────┘     └─────────┘          │    │
│  │                     │                                    │    │
│  │                     ▼                                    │    │
│  │               ┌─────────┐                               │    │
│  │               │  知识库  │                               │    │
│  │               │  检索   │                               │    │
│  │               └─────────┘                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ═════════════════════════════════════════════════════════════   │
│                                                                   │
│  使用案例                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ [标签页] 客户服务 | 内容创作 | 数据分析 | 办公自动化     │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │                                                          │    │
│  │  🤖 智能客服机器人                                        │    │
│  │  7×24 小时自动回答客户问题，减少 80% 人工客服成本          │    │
│  │  [了解详情 →]                                            │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ═════════════════════════════════════════════════════════════   │
│                                                                   │
│  定价方案                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   免费版    │  │   专业版    │  │   企业版    │               │
│  │    $0      │  │   $29/月   │  │   定制     │               │
│  │  3 个工作流 │  │  无限工作流 │  │  无限      │               │
│  │  1,000 次  │  │  50,000 次 │  │  无限      │               │
│  │    调用    │  │    调用    │  │  定制支持  │               │
│  │ [免费试用] │  │ [立即购买] │  │ [联系销售] │               │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                   │
│  ═════════════════════════════════════════════════════════════   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  准备好开始了吗？                                         │    │
│  │  加入 thousands of 用户，提升工作效率                     │    │
│  │  [免费开始] [预约演示]                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  © 2024 Flowly. All rights reserved.                             │
│  关于 | 博客 | 文档 | 隐私政策 | 服务条款 | 联系我们              │
└─────────────────────────────────────────────────────────────────┘
```

#### 35.3.3 Hero 区域详细设计

**视觉元素**：
- 背景：渐变暗色 + 细微网格纹理
- 动态粒子/光效动画
- 工作流截图带有 Mac 风格窗口边框
- 截图每 3 秒切换一个示例工作流

**交互动效**：
- "开始免费使用" 按钮：hover 时有发光 + 上浮效果
- "观看演示" 按钮：带播放图标，hover 时图标弹跳
- 工作流节点入场动画：从左到右依次出现

#### 35.3.4 功能卡片设计

**卡片样式**：
- 背景：`$bg-secondary`
- 边框：`$border-subtle`
- 圆角：`$radius-lg`
- 悬停：边框变亮 + 轻微上浮 + 阴影加深
- 尺寸：4 列网格，间距 `$space-6`

**卡片内容**：
- 顶部：功能图标（48x48，带渐变背景）
- 中部：标题 + 描述
- 底部：可选的 "了解更多" 链接

---

### 35.4 登录页面 (Login) 详细设计

#### 35.4.1 页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────┐  ┌─────────────────────────┐│
│  │                                 │  │  ┌───────────────────┐  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  │   登录表单区域    │  ││
│  │     品牌展示区域                 │  │  │                   │  ││
│  │                                 │  │  │  🔷 Flowly Logo   │  ││
│  │     动态工作流演示               │  │  │                   │  ││
│  │                                 │  │  │  欢迎回来 👋     │  ││
│  │     (左侧 55%)                  │  │  │  请登录继续      │  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  │  ┌─────────────┐ │  ││
│  │                                 │  │  │  │ 📧 邮箱     │ │  ││
│  │                                 │  │  │  └─────────────┘ │  ││
│  │                                 │  │  │  ┌─────────────┐ │  ││
│  │                                 │  │  │  │ 🔒 密码     │ │  ││
│  │                                 │  │  │  └─────────────┘ │  ││
│  │                                 │  │  │  ☐ 记住我  忘记密码│  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  │  [ 登 录 ]       │  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  │  ───── 或 ─────  │  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  │  [G] [Github]    │  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  │  还没有账号？     │  ││
│  │                                 │  │  │  [立即注册 →]    │  ││
│  │                                 │  │  │                   │  ││
│  │                                 │  │  └───────────────────┘  ││
│  └─────────────────────────────────┘  └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

#### 35.4.2 表单设计

**邮箱输入框**：
- 前置图标：`📧`
- 占位文本：`请输入邮箱地址`
- 验证：实时校验邮箱格式
- 状态：默认、聚焦（蓝色边框发光）、错误（红色边框 + 错误提示）

**密码输入框**：
- 前置图标：`🔒`
- 后置按钮：👁️ 切换显示/隐藏密码
- 占位文本：`请输入密码`
- 验证：最少 6 位字符

**记住我**：
- Checkbox 样式：自定义，选中时显示蓝色 ✓
- 有效期：30 天

**忘记密码链接**：
- 颜色：`$primary-500`
- Hover：下划线

#### 35.4.3 第三方登录

**OAuth 按钮样式**：
- Google：白底 + Google logo + "使用 Google 账号登录"
- GitHub：深灰底 + GitHub logo + "使用 GitHub 账号登录"
- 布局：两个按钮并排，间距 `$space-3`

#### 35.4.4 错误处理

**表单级错误**：
- 邮箱/密码错误：红色提示文字 + 输入框边框变红
- 账户不存在：提示注册链接
- 登录过于频繁：显示倒计时 + 提示

**网络错误**：
- Toast 提示：`网络连接失败，请检查网络`
- 重试按钮

---

### 35.5 注册页面 (Register) 详细设计

#### 35.5.1 页面布局

与登录页对称布局，左侧品牌展示，右侧注册表单。

#### 35.5.2 表单设计

```
┌─────────────────────────────────────────────────┐
│  🔷 Flowly                                      │
│                                                 │
│  创建你的账号                                   │
│  开始构建 AI 工作流                             │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │ 👤 用户名                                │  │
│  │ 请输入用户名 (3-20位字母数字)             │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │ 📧 邮箱                                 │  │
│  │ 请输入邮箱地址                           │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │ 🔒 密码                                 │  │
│  │ 请输入密码                               │  │
│  │ 强度: [████░░░░░░] 弱                   │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │ 🔒 确认密码                             │  │
│  │ 请再次输入密码                           │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ☐ 我已阅读并同意 [服务条款] 和 [隐私政策]      │
│                                                 │
│  [ 注 册 ]                                     │
│                                                 │
│  ───── 或 ─────                               │
│                                                 │
│  [G] [Github]                                  │
│                                                 │
│  已有账号？[立即登录 →]                         │
└─────────────────────────────────────────────────┘
```

#### 35.5.3 密码强度指示器

```
密码强度可视化进度条：
┌──────────────────────────────────────┐
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────┘

强度等级：
- 弱（红色）：只包含数字或只包含字母
- 中等（黄色）：8位以上，字母+数字
- 强（绿色）：包含特殊字符，长度12位以上
```

#### 35.5.4 注册成功流程

1. 显示加载状态（按钮变为 "注册中..." + spinner）
2. 成功：
   - 弹出成功提示："注册成功！正在跳转..."
   - 跳转到邮箱验证页面
3. 失败：
   - 显示具体错误信息
   - 输入框错误状态

---

### 35.6 主控台/仪表盘 (Dashboard) 详细设计

#### 35.6.1 页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌──────┐                                    🔔 👤 [头像 ▾]       │
│ │ Logo │   首页  工作流  智能体  模板   🔍 搜索...     ────────── │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  👋 早上好，张三！                                                │
│  这是你今天的工作概览                                              │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ 📊 执行    │  │ ⚡ 成功率  │  │ ⏱️ 平均    │  │ 💰 本月    │  │
│  │   1,234   │  │   98.5%   │  │   2.3s    │  │   ¥128    │  │
│  │   今日     │  │  本月      │  │   响应     │  │   消耗     │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
│                                                                   │
│  ════════════════════════════════════════════════════════════   │
│                                                                   │
│  🚀 快速开始                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │ + 新建工作流 │  │ 🤖 创建智能体│  │ ✨ AI 生成  │               │
│  │             │  │             │  │             │               │
│  │ 从空白画布    │  │ 使用模板    │  │ 描述你想要  │               │
│  │ 开始构建      │  │ 快速开始    │  │ 的工作流    │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
│                                                                   │
│  ════════════════════════════════════════════════════════════   │
│                                                                   │
│  📁 最近工作                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🕐 今天                        显示更多 →                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ 📄 智能客服工作流          ● 运行中   12:30            │   │
│  │    客户支持 / 4个节点       ▶ 播放    💬 23            │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ 📄 内容审核自动化            ✅ 正常    11:45            │   │
│  │    内容处理 / 6个节点       ▶ 播放    💬 8             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🕐 昨天                        显示更多 →                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ 📄 数据分析报告生成      ✅ 正常    昨天 18:20           │   │
│  │    报告生成 / 8个节点    ▶ 播放    💬 45            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ════════════════════════════════════════════════════════════   │
│                                                                   │
│  📈 执行趋势                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │    📈 ECharts 折线图区域                                 │   │
│  │    X轴：过去7天                                         │   │
│  │    Y轴：执行次数                                        │   │
│  │    数据：每日执行量 + 成功率趋势                         │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  💡 推荐模板                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  🤖      │  │  📝      │  │  📊      │  │  💬      │       │
│  │  智能客服 │  │  文章改写 │  │  数据分析 │  │  客服机器人│       │
│  │  [使用]  │  │  [使用]  │  │  [使用]  │  │  [使用]  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 35.6.2 顶部导航栏

**左侧**：
- Logo：点击返回首页
- 主导航：首页 | 工作流 | 智能体 | 模板
- 搜索框：全局搜索（工作流、Agent、模板）

**右侧**：
- 通知铃铛：带红点未读标记
- 用户头像下拉菜单：个人资料 | 设置 | 退出登录

#### 35.6.3 统计卡片设计

**卡片结构**：
```
┌────────────────────────┐
│  📊                    │  ← 图标
│  执行次数              │  ← 标签
│  1,234                 │  ← 主数值（大号字体）
│  今日                  │  ← 副标签
│  ↑ 12% vs 昨天         │  ← 趋势对比
└────────────────────────┘
```

**数值动画**：
- 页面加载时数字从 0 滚动到当前值
- 持续 1.5 秒，缓动函数 easeOutExpo

---

### 35.7 工作流编辑器 (Workflow Editor) 详细设计

#### 35.7.1 页面布局

```
┌───────────────────────────────────────────────────────────────────────────┐
│ ┌─────────┐  工作流名称 [未命名工作流 ▾]    [自动保存 ✓ 2分钟前]   👤 │
│ │ ← 返回  │  ──────────────────────────────────────────────────────────│
├───────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌───────────────────────────────────────────────────────────┐│
│ │          │ │                                                           ││
│ │  节点    │ │                                                           ││
│ │  组件    │ │                                                           ││
│ │  面板    │ │                    画 布 区 域                            ││
│ │          │ │                                                           ││
│ │ ──────── │ │              (可缩放、可拖拽、网格背景)                   ││
│ │ 📥 触发器│ │                                                           ││
│ │  ⌨️  输入 │ │                                                           ││
│ │  🔄 定时 │ │                                                           ││
│ │  🌐 Webhook│ │                                                          ││
│ │          │ │                                                           ││
│ │ ──────── │ │                                                           ││
│ │ 🤖 AI    │ │                                                           ││
│ │  💬 LLM  │ │                                                           ││
│ │  📝 Prompt│ │                                                           ││
│ │          │ │                                                           ││
│ │ ──────── │ │                                                           ││
│ │ ⚡ 流程  │ │                                                           ││
│ │  🔀 条件 │ │                                                           ││
│ │  🔁 循环 │ │                                                           ││
│ │          │ │                                                           ││
│ │ ──────── │ │                                                           ││
│ │ 🔧 工具  │ │                                                           ││
│ │  🌐 HTTP │ │                                                           ││
│ │  📄 文档 │ │                                                           ││
│ │          │ │                                                           ││
│ │ ──────── │ │                                                           ││
│ │ 📊 数据  │ │                                                           ││
│ │  🔍 检索 │ │                                                           ││
│ │  💾 向量 │ │                                                           ││
│ │          │ │                                                           ││
│ └──────────┘ └───────────────────────────────────────────────────────────┤│
│               │ [🔍-][100%][🔍+]│[📷]│                [▶ 执行]        │
└───────────────────────────────────────────────────────────────────────────┘

当点击节点时，右边弹出属性面板：
┌─────────────────────────────────────────────────────────────────────────┐
│ │                              │  ┌─────────────────────────────┐      │
│ │                              │  │ LLM 节点属性                │      │
│ │                              │  ├─────────────────────────────┤      │
│ │         画布区域             │  │ 节点名称                    │      │
│ │                              │  │ ┌─────────────────────────┐│      │
│ │                              │  │ │ AI 对话                 ││      │
│ │                              │  │ └─────────────────────────┘│      │
│ │                              │  │                            │      │
│ │                              │  │ 模型选择                    │      │
│ │                              │  │ ┌─────────────────────────┐│      │
│ │                              │  │ │ GPT-4o              ▾  ││      │
│ │                              │  │ └─────────────────────────┘│      │
│ │                              │  │                            │      │
│ │                              │  │ 系统提示词                  │      │
│ │                              │  │ ┌─────────────────────────┐│      │
│ │                              │  │ │ 你是一个专业的助手...    ││      │
│ │                              │  │ │                        ││      │
│ │                              │  │ └─────────────────────────┘│      │
│ │                              │  │                            │      │
│ │                              │  │ 输入变量                    │      │
│ │                              │  │ ┌─────────────────────────┐│      │
│ │                              │  │ │ {{user_input}}         ││      │
│ │                              │  │ └─────────────────────────┘│      │
│ │                              │  │                            │      │
│ │                              │  │ [高级设置 ▾]               │      │
│ │                              │  │  Temperature: [0.7────●──]  │      │
│ │                              │  │  Max Tokens: [2048─────]   │      │
│ │                              │  │                            │      │
│ │                              │  └─────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 35.7.2 顶部工具栏

**左侧**：
- 返回按钮：← 返回列表
- 工作流名称：可点击编辑
- 自动保存状态：✓ 已保存 | ⟳ 保存中...

**右侧**：
- 版本下拉：v1.0.0 | v1.0.1
- 分享按钮：🌐 分享
- 更多操作：⋮ 菜单（导出 | 复制链接 | 删除）
- 执行按钮：▶ 执行（蓝色主按钮）

#### 35.7.3 节点组件面板

**节点分类**：

```
📥 触发器
├── 手动触发      - 手动启动工作流
├── 用户输入      - 接收用户输入
├── Webhook      - 接收外部 HTTP 请求
├── 定时触发      - 定时执行
└── 事件触发      - 监听事件

🤖 AI 能力
├── LLM 对话      - 调用大语言模型
├── Prompt 模板  - 文本模板处理
├── AI 搜索      - 联网搜索
└── 图像生成      - DALL-E 等

⚡ 流程控制
├── 条件判断      - if/else 分支
├── 循环处理      - for/while
├── 并行执行      - parallel
└── 延迟等待      - delay

🔧 工具
├── HTTP 请求    - 发送 API 请求
├── 代码执行     - 运行代码片段
├── 文档处理     - PDF/Word 解析
└── 变量操作     - 赋值/转换

📊 数据处理
├── 向量检索     - 知识库搜索
├── 文本处理     - 分割/合并
├── JSON 解析    - 解析数据结构
└── 变量模板     - 字符串模板
```

**节点卡片样式**：
- 宽度：100%
- 高度：40px
- 图标 + 名称
- Hover：背景变亮 + 左侧出现彩色条
- 拖拽时：半透明 + 跟随鼠标

#### 35.7.4 画布设计

**背景**：
- 网格点阵：20px 间隔，1px 圆点
- 颜色：`rgba(255, 255, 255, 0.05)`
- 支持对齐辅助线

**缩放控制**：
- 范围：25% - 200%
- 默认：100%
- 快捷键：Ctrl + 滚轮
- 缩放滑块

**小地图**：
- 右下角缩略图
- 显示当前视口位置
- 点击跳转

#### 35.7.5 节点样式

**节点结构**：
```
┌──────────────────────────────────┐
│ ● ━━━ LLM 对话              ⋮  │  ← 头部：颜色条 + 名称 + 更多菜单
├──────────────────────────────────┤
│  🤖 GPT-4o                      │  ← 内容：图标 + 模型名
│  温度: 0.7 | 最大: 2048         │  ← 副信息
├──────────────────────────────────┤
│  ↑ 输入         输出 ↓          │  ← 端口区
└──────────────────────────────────┘
```

**节点类型颜色**：
- 触发器：青色 `#14B8A6`
- AI/LLM：紫色 `#8B5CF6`
- 流程控制：黄色 `#EAB308`
- 工具：橙色 `#F97316`
- 数据处理：绿色 `#22C55E`
- 向量/知识库：蓝色 `#06B6D4`

**节点状态**：
- 选中：外发光 + 边框高亮
- 运行中：脉冲动画
- 成功：绿色勾号
- 失败：红色感叹号
- 禁用：灰色 + 50% 透明度

#### 35.7.6 边/连线样式

**连线外观**：
- 贝塞尔曲线
- 宽度：2px
- 颜色：与源节点类型对应
- 箭头：三角形箭头指向目标

**状态**：
- 默认：实线
- Hover：高亮 + 加粗
- 选中：虚线动画
- 条件分支：虚线

#### 35.7.7 属性面板

**面板结构**：
```
┌────────────────────────────────┐
│ LLM 节点属性              ✕   │
├────────────────────────────────┤
│ 基础设置                       │
│ ┌────────────────────────┐    │
│ │ 节点名称                │    │
│ │ [AI 对话             ] │    │
│ └────────────────────────┘    │
│                                │
│ 模型选择                       │
│ ┌────────────────────────┐    │
│ │ [GPT-4o            ▾] │    │
│ └────────────────────────┘    │
│                                │
│ 系统提示词                     │
│ ┌────────────────────────┐    │
│ │ [你是一个专业的助手...] │    │
│ │                        │    │
│ │                        │    │
│ │              📋 💾 📤  │    │
│ └────────────────────────┘    │
│ [从模板选择 ▷]                │
│                                │
│ 输入变量                       │
│ ┌────────────────────────┐    │
│ │ + 添加变量              │    │
│ │ {{user_input}}         │    │
│ │ {{context}}            │    │
│ └────────────────────────┘    │
│                                │
│ ────────── 高级设置 ────────── │
│                                │
│ ☐ 流式输出 (Streaming)         │
│                                │
│ Temperature                    │
│ 0 ──●──────────────── 2       │
│ [0.7]                         │
│                                │
│ 最大 Tokens                    │
│ [____2048____]                │
│                                │
│ Top P                         │
│ 0 ────●────────────── 1       │
│ [1.0]                         │
│                                │
│ ☐ 启用 JSON Mode               │
│ ☐ 启用 Think Mode             │
│                                │
└────────────────────────────────┘
```

**表单控件类型**：
- 文本输入：单行输入框
- 文本区域：多行，带工具栏
- 下拉选择：单选/多选
- 开关：Toggle 开关
- 滑块：数值范围选择
- 代码编辑器：语法高亮
- 变量选择器：{{variable}} 格式

#### 35.7.7 属性面板

**面板结构**：
```
┌────────────────────────────────┐
│ LLM 节点属性                ✕   │
├────────────────────────────────┤
│ 基础设置                       │
│ ...（详见上面的属性面板结构）...
└────────────────────────────────┘
```

**表单控件类型**：
- 文本输入：单行输入框
- 文本区域：多行，带工具栏
- 下拉选择：单选/多选
- 开关：Toggle 开关
- 滑块：数值范围选择
- 代码编辑器：语法高亮
- 变量选择器：{{variable}} 格式

---

### 35.8 迷你地图 (MiniMap) 详细设计

#### 35.8.1 功能概述

迷你地图是工作流编辑器右下角的核心导航组件，帮助用户快速了解工作流的整体结构，并提供快捷的画布导航功能。

#### 35.8.2 视觉设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         工作流编辑器画布区域                              │
│                                                                         │
│                              ... 节点和连线 ...                          │
│                                                                         │
│                                                                         │
│                                                                         │
│                                              ┌─────────────────────────┐│
│                                              │ ╔═══════════════════╗ ││
│                                              │ ║ · · · · · · · · ║ ││
│                                              │ ║ · ┌───────┐ · · ║ ││
│                                              │ ║ · │ 视口  │ · · ║ ││
│                                              │ ║ · │ 区域  │ · · ║ ││
│                                              │ ║ · └───────┘ · · ║ ││
│                                              │ ║ · · · · · · · · ║ ││
│                                              │ ╚═══════════════════╝ ││
│                                              │  📍 5 个节点           ││
│                                              └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

**组件结构**：
```
┌────────────────────────────────┐
│ 🗺️ 导航地图              [−][×] │  ← 标题栏 + 折叠/关闭按钮
├────────────────────────────────┤
│                                │
│    · · · · · · · · · · ·     │
│    · · ┌─────────┐ · · · ·   │  ← 小型节点表示
│    · · │  触发器 │ · · · ·   │
│    · · └────┬────┘ · · · ·   │
│    · · · · ·│· · · · · · ·   │
│    · · · · ·│· · · · · · ·   │
│    · · · · ·│ · · · · · · ·  │
│    · · · · ·▼· · · · · · · ·  │
│    · · · ·[LLM]· · · · · · ·  │
│    · · · · ·│· · · · · · ·   │
│    · · · · ·│· · · · · · ·   │
│    · · · · ·▼· · · · · · · ·  │
│    · · · ·[工具]· · · · · · ·  │
│    · · · · · · · · · · · ·    │
│    ░░░░░░░░░░░░░░░░░░░░░░░░   │  ← 当前视口区域（半透明蓝色）
│                                │
├────────────────────────────────┤
│ 📍 5 个节点 · 缩放 100%         │  ← 底部信息栏
└────────────────────────────────┘
```

#### 35.8.3 色彩与样式

```scss
// 迷你地图容器
.minimap {
  position: absolute;
  bottom: 16px;
  right: 16px;
  width: 200px;
  height: 150px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  
  // 毛玻璃效果
  backdrop-filter: blur(8px);
  background: rgba(26, 26, 33, 0.9);
}

// 标题栏
.minimap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
}

// 视口指示器（当前显示区域）
.minimap-viewport {
  position: absolute;
  border: 2px solid var(--primary-500);
  background: rgba(59, 130, 246, 0.15);
  border-radius: 2px;
  cursor: move;
  transition: all 0.1s ease;
  
  &:hover {
    background: rgba(59, 130, 246, 0.25);
    border-color: var(--primary-400);
  }
}

// 节点表示
.minimap-node {
  position: absolute;
  border-radius: 2px;
  transition: all 0.2s ease;
  
  // 根据节点类型着色
  &.trigger { background: #14B8A6; }
  &.llm { background: #8B5CF6; }
  &.tool { background: #F97316; }
  &.condition { background: #EAB308; }
  &.data { background: #22C55E; }
  &.vector { background: #06B6D4; }
}

// 边（连线）表示
.minimap-edge {
  position: absolute;
  background: var(--text-tertiary);
  opacity: 0.5;
}
```

#### 35.8.4 核心功能

**1. 视口导航**

```javascript
// 点击迷你地图跳转
const onMinimapClick = (event) => {
  const rect = minimapRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const clickY = event.clientY - rect.top
  
  // 转换为画布坐标
  const scale = minimapScale.value
  const canvasX = (clickX - viewportWidth / 2) / scale + canvasCenterX
  const canvasY = (clickY - viewportHeight / 2) / scale + canvasCenterY
  
  // 平移画布到对应位置
  panTo(canvasX, canvasY)
}

// 拖拽视口指示器
const onViewportDrag = (event) => {
  if (!isDraggingViewport.value) return
  
  // 实时更新画布位置
  const deltaX = event.movementX / minimapScale.value
  const deltaY = event.movementY / minimapScale.value
  
  panBy(deltaX, deltaY)
}
```

**2. 节点缩放表示**

```javascript
// 计算节点在迷你地图上的位置
const getMinimapNodePosition = (node) => {
  const canvasWidth = workflowCanvas.value.width
  const canvasHeight = workflowCanvas.value.height
  const minimapWidth = 200
  const minimapHeight = 150
  
  // 考虑画布偏移和缩放
  return {
    x: (node.position.x * minimapWidth) / canvasWidth,
    y: (node.position.y * minimapHeight) / canvasHeight,
    width: Math.max(4, (node.width * minimapWidth) / canvasWidth),
    height: Math.max(3, (node.height * minimapHeight) / canvasHeight)
  }
}
```

**3. 视口同步**

```javascript
// 监听画布变换，同步更新迷你地图视口
watch(
  () => [canvasOffset.value, canvasZoom.value],
  ([offset, zoom]) => {
    const viewportWidth = (viewportWidth.value / zoom) * minimapScale
    const viewportHeight = (viewportHeight.value / zoom) * minimapScale
    
    viewportStyle.value = {
      width: `${viewportWidth}px`,
      height: `${viewportHeight}px`,
      left: `${(-offset.x / zoom) * minimapScale}px`,
      top: `${(-offset.y / zoom) * minimapScale}px`
    }
  }
)
```

#### 35.8.5 交互行为

**鼠标悬停节点**：
```
┌────────────────────────────────┐
│ 🗺️ 导航地图              [−][×] │
├────────────────────────────────┤
│                                │
│    · · · · · · · · · · ·     │
│    · · ┌─────────┐ · · · ·   │
│    · · │  触发器 │ · · · ·   │  ← Hover 时显示节点名称 tooltip
│    · · └────┬────┘ · · · ·   │
│    · · · · ·│· · · · · · ·   │
│    · · · · ·▼· · · · · · · ·  │
│    · · · ·[LLM]· · · · · · ·  │  ← 悬停高亮
│    · · · · ·│· · · · · · ·   │
│    · · · · ·▼· · · · · · · ·  │
│    · · · ·[工具]· · · · · · ·  │
│    · · · · · · · · · · · ·    │
│                                │
├────────────────────────────────┤
│ 📍 LLM 对话节点 · 5 个节点      │  ← 悬停时底部显示节点信息
└────────────────────────────────┘
```

**节点类型图例**：
```
┌────────────────────────────────┐
│ 图例                            │
│ ┌──┐ 触发器                     │
│ └──┘                            │
│ ┌──┐ AI/LLM                     │
│ └──┘                            │
│ ┌──┐ 工具                       │
│ └──┘                            │
│ ┌──┐ 条件                       │
│ └──┘                            │
│ ┌──┐ 数据                       │
│ └──┘                            │
└────────────────────────────────┘
```

#### 35.8.6 折叠/展开功能

```vue
<template>
  <!-- 展开状态 -->
  <div v-if="!collapsed" class="minimap">
    <div class="minimap-header">
      <span>🗺️ 导航地图</span>
      <div class="minimap-actions">
        <button @click="toggleCollapse" title="折叠">−</button>
        <button @click="close" title="关闭">×</button>
      </div>
    </div>
    <div class="minimap-content" ref="minimapRef">
      <!-- 节点和边 -->
      <div
        v-for="node in nodes"
        :key="node.id"
        class="minimap-node"
        :class="`node-${node.type}`"
        :style="getNodeStyle(node)"
        :title="node.name"
        @mouseenter="highlightNode(node)"
        @mouseleave="unhighlightNode"
      />
      
      <!-- 连线 -->
      <svg class="minimap-edges">
        <line
          v-for="edge in edges"
          :key="edge.id"
          class="minimap-edge"
          :x1="getNodeCenter(edge.source).x"
          :y1="getNodeCenter(edge.source).y"
          :x2="getNodeCenter(edge.target).x"
          :y2="getNodeCenter(edge.target).y"
        />
      </svg>
      
      <!-- 视口指示器 -->
      <div
        class="minimap-viewport"
        :style="viewportStyle"
        @mousedown="startViewportDrag"
        @mousemove="onViewportDrag"
        @mouseup="stopViewportDrag"
      />
    </div>
    <div class="minimap-footer">
      <span>📍 {{ nodeCount }} 个节点</span>
      <span>·</span>
      <span>缩放 {{ Math.round(zoom * 100) }}%</span>
    </div>
  </div>
  
  <!-- 折叠状态（仅图标） -->
  <button
    v-else
    class="minimap-collapsed"
    @click="toggleCollapse"
    title="展开导航地图"
  >
    🗺️
  </button>
</template>
```

#### 35.8.7 完整组件代码

```vue
<!-- Frontend/src/components/workflow/MiniMap.vue -->
<template>
  <div class="minimap-wrapper">
    <!-- 展开状态 -->
    <Transition name="minimap-fade">
      <div v-if="visible && !collapsed" class="minimap">
        <div class="minimap-header">
          <span class="minimap-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M9 3v18M3 9h18"/>
            </svg>
            导航地图
          </span>
          <div class="minimap-actions">
            <button
              class="minimap-btn"
              @click="toggleCollapse"
              title="折叠"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14"/>
              </svg>
            </button>
            <button
              class="minimap-btn"
              @click="$emit('close')"
              title="关闭"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>
        
        <div
          ref="minimapRef"
          class="minimap-content"
          @click="onMinimapClick"
          @mousemove="onMouseMove"
          @mouseleave="hoveredNode = null"
        >
          <!-- 边（连线）层 -->
          <svg class="minimap-edges">
            <path
              v-for="edge in edges"
              :key="edge.id"
              class="minimap-edge"
              :d="getEdgePath(edge)"
            />
          </svg>
          
          <!-- 节点层 -->
          <div
            v-for="node in nodes"
            :key="node.id"
            class="minimap-node"
            :class="[
              `node-${node.type}`,
              { highlighted: highlightedNodes.has(node.id) },
              { hovered: hoveredNode?.id === node.id }
            ]"
            :style="getNodeStyle(node)"
            @mouseenter="hoveredNode = node"
          />
          
          <!-- 视口指示器 -->
          <div
            class="minimap-viewport"
            :style="viewportStyle"
            @mousedown.stop="startViewportDrag"
          />
        </div>
        
        <div class="minimap-footer">
          <span>📍 {{ nodeCount }} 个节点</span>
          <span class="divider">·</span>
          <span>缩放 {{ Math.round(zoom * 100) }}%</span>
        </div>
      </div>
    </Transition>
    
    <!-- 折叠状态按钮 -->
    <Transition name="minimap-fade">
      <button
        v-if="visible && collapsed"
        class="minimap-collapsed"
        @click="toggleCollapse"
        title="展开导航地图"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M9 3v18M3 9h18"/>
        </svg>
      </button>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  },
  canvasOffset: {
    type: Object,
    default: () => ({ x: 0, y: 0 })
  },
  zoom: {
    type: Number,
    default: 1
  },
  viewportSize: {
    type: Object,
    default: () => ({ width: 800, height: 600 })
  }
})

const emit = defineEmits(['pan', 'close'])

const minimapRef = ref(null)
const visible = ref(true)
const collapsed = ref(false)
const hoveredNode = ref(null)
const highlightedNodes = ref(new Set())
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

// MiniMap 尺寸
const MINIMAP_WIDTH = 200
const MINIMAP_HEIGHT = 150
const MINIMAP_PADDING = 10

// 计算画布边界
const canvasBounds = computed(() => {
  if (props.nodes.length === 0) {
    return { minX: 0, minY: 0, maxX: 1000, maxY: 1000 }
  }
  
  let minX = Infinity, minY = Infinity
  let maxX = -Infinity, maxY = -Infinity
  
  props.nodes.forEach(node => {
    minX = Math.min(minX, node.position.x)
    minY = Math.min(minY, node.position.y)
    maxX = Math.max(maxX, node.position.x + (node.width || 150))
    maxY = Math.max(maxY, node.position.y + (node.height || 60))
  })
  
  // 添加边距
  const padding = 100
  return {
    minX: minX - padding,
    minY: minY - padding,
    maxX: maxX + padding,
    maxY: maxY + padding
  }
})

// 计算缩放比例
const minimapScale = computed(() => {
  const bounds = canvasBounds.value
  const contentWidth = bounds.maxX - bounds.minX
  const contentHeight = bounds.maxY - bounds.minY
  
  const scaleX = (MINIMAP_WIDTH - MINIMAP_PADDING * 2) / contentWidth
  const scaleY = (MINIMAP_HEIGHT - MINIMAP_PADDING * 2) / contentHeight
  
  return Math.min(scaleX, scaleY, 1)
})

// 节点数量
const nodeCount = computed(() => props.nodes.length)

// 获取节点在迷你地图上的样式
const getNodeStyle = (node) => {
  const bounds = canvasBounds.value
  const scale = minimapScale.value
  
  const x = (node.position.x - bounds.minX) * scale + MINIMAP_PADDING
  const y = (node.position.y - bounds.minY) * scale + MINIMAP_PADDING
  const width = Math.max(4, (node.width || 150) * scale)
  const height = Math.max(3, (node.height || 60) * scale)
  
  return {
    left: `${x}px`,
    top: `${y}px`,
    width: `${width}px`,
    height: `${height}px`
  }
}

// 获取边的路径
const getEdgePath = (edge) => {
  const sourceNode = props.nodes.find(n => n.id === edge.source)
  const targetNode = props.nodes.find(n => n.id === edge.target)
  
  if (!sourceNode || !targetNode) return ''
  
  const bounds = canvasBounds.value
  const scale = minimapScale.value
  
  const sx = (sourceNode.position.x - bounds.minX + (sourceNode.width || 150) / 2) * scale + MINIMAP_PADDING
  const sy = (sourceNode.position.y - bounds.minY + (sourceNode.height || 60)) * scale + MINIMAP_PADDING
  const tx = (targetNode.position.x - bounds.minX + (targetNode.width || 150) / 2) * scale + MINIMAP_PADDING
  const ty = (targetNode.position.y - bounds.minY) * scale + MINIMAP_PADDING
  
  // 贝塞尔曲线
  const midY = (sy + ty) / 2
  return `M ${sx} ${sy} C ${sx} ${midY}, ${tx} ${midY}, ${tx} ${ty}`
}

// 视口指示器样式
const viewportStyle = computed(() => {
  const bounds = canvasBounds.value
  const scale = minimapScale.value
  
  // 计算当前视口在迷你地图上的位置
  const vpWidth = (props.viewportSize.width / props.zoom) * scale
  const vpHeight = (props.viewportSize.height / props.zoom) * scale
  const vpX = (-props.canvasOffset.x / props.zoom - bounds.minX) * scale + MINIMAP_PADDING
  const vpY = (-props.canvasOffset.y / props.zoom - bounds.minY) * scale + MINIMAP_PADDING
  
  return {
    left: `${vpX}px`,
    top: `${vpY}px`,
    width: `${vpWidth}px`,
    height: `${vpHeight}px`
  }
})

// 点击迷你地图跳转
const onMinimapClick = (event) => {
  if (isDragging.value) return
  
  const rect = minimapRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left - MINIMAP_PADDING
  const clickY = event.clientY - rect.top - MINIMAP_PADDING
  
  // 转换为画布坐标
  const canvasX = clickX / minimapScale.value + canvasBounds.value.minX
  const canvasY = clickY / minimapScale.value + canvasBounds.value.minY
  
  // 平移到点击位置（视口中心对齐点击位置）
  const targetX = -canvasX * props.zoom + props.viewportSize.width / 2
  const targetY = -canvasY * props.zoom + props.viewportSize.height / 2
  
  emit('pan', { x: targetX, y: targetY })
}

// 鼠标移动高亮节点
const onMouseMove = (event) => {
  // 高亮检测逻辑
}

// 开始拖拽视口
const startViewportDrag = (event) => {
  isDragging.value = true
  dragStart.value = {
    x: event.clientX,
    y: event.clientY,
    offset: { ...props.canvasOffset }
  }
  
  document.addEventListener('mousemove', onViewportDrag)
  document.addEventListener('mouseup', stopViewportDrag)
}

// 拖拽视口
const onViewportDrag = (event) => {
  if (!isDragging.value) return
  
  const deltaX = (event.clientX - dragStart.value.x) / minimapScale.value
  const deltaY = (event.clientY - dragStart.value.y) / minimapScale.value
  
  const newOffsetX = dragStart.value.offset.x - deltaX * props.zoom
  const newOffsetY = dragStart.value.offset.y - deltaY * props.zoom
  
  emit('pan', { x: newOffsetX, y: newOffsetY })
}

// 停止拖拽
const stopViewportDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onViewportDrag)
  document.removeEventListener('mouseup', stopViewportDrag)
}

// 高亮节点（通过外部触发）
const highlightNode = (nodeId) => {
  highlightedNodes.value.add(nodeId)
}

// 取消高亮
const unhighlightNode = () => {
  highlightedNodes.value.clear()
}

// 折叠/展开
const toggleCollapse = () => {
  collapsed.value = !collapsed.value
}

// 暴露方法
defineExpose({
  highlightNode,
  unhighlightNode,
  toggleCollapse
})
</script>

<style scoped>
.minimap-wrapper {
  position: absolute;
  bottom: 16px;
  right: 16px;
  z-index: 100;
}

.minimap {
  width: 200px;
  height: 150px;
  background: rgba(26, 26, 33, 0.95);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.minimap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-subtle);
}

.minimap-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

.minimap-actions {
  display: flex;
  gap: 4px;
}

.minimap-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
  
  &:hover {
    background: var(--bg-elevated);
    color: var(--text-primary);
  }
}

.minimap-content {
  position: relative;
  width: 100%;
  height: calc(100% - 44px);
  cursor: crosshair;
}

.minimap-edges {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.minimap-edge {
  fill: none;
  stroke: var(--text-tertiary);
  stroke-width: 1;
  opacity: 0.4;
}

.minimap-node {
  position: absolute;
  border-radius: 2px;
  transition: all 0.15s ease;
  cursor: pointer;
  
  /* 节点类型颜色 */
  &.node-trigger { background: #14B8A6; }
  &.node-llm,
  &.node-ai { background: #8B5CF6; }
  &.node-prompt { background: #EC4899; }
  &.node-tool { background: #F97316; }
  &.node-condition { background: #EAB308; }
  &.node-data { background: #22C55E; }
  &.node-vector { background: #06B6D4; }
  &.node-default { background: #71717A; }
  
  &.hovered {
    transform: scale(1.2);
    z-index: 10;
  }
  
  &.highlighted {
    box-shadow: 0 0 4px currentColor;
  }
}

.minimap-viewport {
  position: absolute;
  border: 2px solid var(--primary-500);
  background: rgba(59, 130, 246, 0.12);
  border-radius: 3px;
  cursor: move;
  transition: border-color 0.15s ease;
  
  &:hover {
    border-color: var(--primary-400);
    background: rgba(59, 130, 246, 0.2);
  }
}

.minimap-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 4px;
  font-size: 10px;
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-subtle);
  
  .divider {
    opacity: 0.5;
  }
}

.minimap-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(26, 26, 33, 0.95);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  backdrop-filter: blur(8px);
  
  &:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--primary-500);
  }
}

/* 过渡动画 */
.minimap-fade-enter-active,
.minimap-fade-leave-active {
  transition: all 0.2s ease;
}

.minimap-fade-enter-from,
.minimap-fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
```

#### 35.8.8 使用示例

```vue
<!-- 在 WorkflowEditor.vue 中使用 -->
<template>
  <div class="workflow-editor">
    <!-- 画布 -->
    <div ref="canvasRef" class="editor-canvas">
      <!-- 节点和连线... -->
    </div>
    
    <!-- 迷你地图 -->
    <MiniMap
      :nodes="nodes"
      :edges="edges"
      :canvas-offset="canvasOffset"
      :zoom="zoom"
      :viewport-size="{ width: canvasWidth, height: canvasHeight }"
      @pan="onMinimapPan"
      @close="showMinimap = false"
    />
  </div>
</template>

<script setup>
import MiniMap from '@/components/workflow/MiniMap.vue'

const canvasOffset = ref({ x: 0, y: 0 })
const zoom = ref(1)
const showMinimap = ref(true)

const onMinimapPan = ({ x, y }) => {
  canvasOffset.value = { x, y }
}
</script>
```

---

### 35.9 工作流执行页面 (Execute) 详细设计

#### 35.8.1 页面布局

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← 返回   智能客服工作流 - 执行                    [历史记录] [重新执行] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │                         │  │                                     │  │
│  │   执行状态总览           │  │   执行结果 / 调试日志                │  │
│  │                         │  │                                     │  │
│  │   ⏱️ 总耗时: 2.3s       │  │   ┌─────────────────────────────┐   │  │
│  │   ✓ 状态: 成功          │  │   │ 📥 输入                    │   │  │
│  │                         │  │   │ 用户: 你好，我想咨询...     │   │  │
│  │   节点执行顺序:          │  │   └─────────────────────────────┘   │  │
│  │                         │  │                                     │  │
│  │   ① 用户输入      ✓    │  │   ┌─────────────────────────────┐   │  │
│  │      12ms              │  │   │ 🤖 AI 回复                  │   │  │
│  │   ② 意图识别      ✓    │  │   │                             │   │  │
│  │      56ms              │  │   │ 您好！很高兴为您服务。       │   │  │
│  │   ③ 知识库检索    ✓    │  │   │ 请问有什么可以帮助您的？     │   │  │
│  │      123ms             │  │   │                             │   │  │
│  │   ④ LLM 对话      ✓    │  │   │ (打字动画效果...)            │   │  │
│  │      2100ms            │  │   │                             │   │  │
│  │   ⑤ 响应输出      ✓    │  │   └─────────────────────────────┘   │  │
│  │      5ms               │  │   │                    [复制] [导出] │  │
│  │                         │  │                                     │  │
│  │   ─────────────────     │  │   ────────────────────────────────  │  │
│  │                         │  │                                     │  │
│  │   资源消耗:              │  │   执行日志                          │  │
│  │   💰 Token: 1,234       │  │   ┌─────────────────────────────┐   │  │
│  │      (输入: 856,        │  │   │ [12:30:01] 开始执行工作流    │   │  │
│  │       输出: 378)        │  │   │ [12:30:02] 节点1: 用户输入   │   │  │
│  │   💾 内存: 45MB         │  │   │ [12:30:03] 节点2: 意图识别   │   │  │
│  │                         │  │   │ [12:30:04] 调用 GPT-4o API  │   │  │
│  │                         │  │   │ [12:30:06] 收到响应 (378字)  │   │  │
│  └─────────────────────────┘  │   │ [12:30:06] 执行完成         │   │  │
│                                │   └─────────────────────────────┘   │  │
│  ┌─────────────────────────┐  └─────────────────────────────────────┘  │
│  │ 新对话                   │                                            │
│  │ ┌─────────────────────┐ │                                            │
│  │ │ 重新输入...         │ │                                            │
│  │ └─────────────────────┘ │                                            │
│  │             [发送 ▶]    │                                            │
│  └─────────────────────────┘                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 35.8.2 流式输出效果

```
🤖 AI 回复:
┌─────────────────────────────────────────┐
│ 你好！很高兴为您服务。👋                   │
│                                         │
│ 我是 Flowly 的智能客服助手，可以帮助你：    │
│                                         │
│ 📚 解答产品使用问题                       │
│ 🔧 故障排查指导                         │
│ 💡 提供最佳实践建议                       │
│                                         │
│ 请问有什么可以帮助您的？                  │
│                                         │
│ ✓ 已完成 (2.3s)                        │
└─────────────────────────────────────────┘

打字动画：
- 字符逐个显示
- 光标闪烁效果
- 打字速度：约 50 字符/秒
```

---

### 35.10 Agent 智能体页面详细设计

#### 35.10.1 Agent 列表页

```
┌─────────────────────────────────────────────────────────────────┐
│ 智能体                          [+ 创建智能体]  [🔍 搜索...]       │
├─────────────────────────────────────────────────────────────────┤
│ [全部] [对话型] [工具型] [自动化] [自定义]        排序: 最新 ▾   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  🤖             │  │  💬             │  │  📊             │  │
│  │                 │  │                 │  │                 │  │
│  │  客服助手       │  │  内容改写助手   │  │  数据分析师     │  │
│  │                 │  │                 │  │                 │  │
│  │  对话型 | 公开   │  │  工具型 | 私有   │  │  对话型 | 公开   │  │
│  │                 │  │                 │  │                 │  │
│  │  专门处理客户    │  │  自动改写文章   │  │  帮你分析数据   │  │
│  │  咨询和问答     │  │  和文案优化     │  │  生成报告      │  │
│  │                 │  │                 │  │                 │  │
│  │  ▶ 使用  💬 23  │  │  ▶ 使用  💬 8   │  │  ▶ 使用  💬 45  │  │
│  │     🕐 2小时前  │  │     🕐 昨天    │  │     🕐 3天前  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │  🔍             │  │  📝             │                       │
│  │                 │  │                 │                       │
│  │  知识库问答     │  │  文章写手       │                       │
│  │                 │  │                 │                       │
│  │  工具型 | 公开   │  │  对话型 | 私有   │                       │
│  │                 │  │                 │                       │
│  │  基于向量知识库  │  │  自动生成文章   │                       │
│  │  的智能问答     │  │  和营销文案     │                       │
│  │                 │  │                 │                       │
│  │  ▶ 使用  💬 156 │  │  ▶ 使用  💬 12  │                       │
│  │     🕐 1周前    │  │     🕐 2周前   │                       │
│  └─────────────────┘  └─────────────────┘                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 35.9.2 Agent 调试器页面

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← 返回   客服助手 - 调试              [保存] [发布] [⚙️ 设置]            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  Agent 配置              │  │  对话调试区                         │  │
│  │                         │  │                                     │  │
│  │  ─────────────────────  │  │  ┌─────────────────────────────────┐│  │
│  │                         │  │  │ 🤖 助手: 有什么可以帮你的？     ││  │
│  │  基本信息                │  │  └─────────────────────────────────┘│  │
│  │  ┌───────────────────┐  │  │  ┌─────────────────────────────────┐│  │
│  │  │ 名称: 客服助手    │  │  │  │ 👤 用户: 你好                  ││  │
│  │  └───────────────────┘  │  │  └─────────────────────────────────┘│  │
│  │                         │  │  ┌─────────────────────────────────┐│  │
│  │  模型选择                │  │  │ 🤖 助手: 你好！很高兴为您服务。 ││  │
│  │  ┌───────────────────┐  │  │  │                                 ││  │
│  │  │ [GPT-4o       ▾] │  │  │  │ [typing...]                     ││  │
│  │  └───────────────────┘  │  │  └─────────────────────────────────┘│  │
│  │                         │  │                                     │  │
│  │  系统提示词              │  │  ────────────────────────────────   │  │
│  │  ┌───────────────────┐  │  │                                     │  │
│  │  │ 你是一个专业...   │  │  │  ┌─────────────────────────────────┐│  │
│  │  │                   │  │  │  │ 输入消息...              [发送] ││  │
│  │  │                   │  │  │  └─────────────────────────────────┘│  │
│  │  └───────────────────┘  │  │                                     │  │
│  │                         │  │  ────────────────────────────────   │  │
│  │  启用的工具 🔧           │  │                                     │  │
│  │  ┌───────────────────┐  │  │  执行日志                           │  │
│  │  │ ☑ 知识库检索      │  │  │  ┌─────────────────────────────────┐│  │
│  │  │ ☑ 计算器         │  │  │  │ [12:30:01] 调用 GPT-4o          ││  │
│  │  │ ☐ 天气查询       │  │  │  │ [12:30:02] Token: 123/456      ││  │
│  │  │ ☐ 搜索工具       │  │  │  │ [12:30:03] 工具调用: 知识库检索 ││  │
│  │  └───────────────────┘  │  │  │ [12:30:04] 检索结果: 3条        ││  │
│  │                         │  │  │ [12:30:05] 生成最终回复         ││  │
│  │  知识库                  │  │  │ [12:30:06] 完成                 ││  │
│  │  ┌───────────────────┐  │  │  └─────────────────────────────────┘│  │
│  │  │ [选择知识库 ▾]   │  │  │                                     │  │
│  │  │ FAQ 产品手册     │  │  │                                     │  │
│  │  │ 使用指南         │  │  │                                     │  │
│  │  └───────────────────┘  │  │                                     │  │
│  │                         │  │                                     │  │
│  └─────────────────────────┘  └─────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 35.11 AI 自然语言生成工作流页面

#### 35.11.1 页面布局

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← 返回   AI 生成工作流                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │      ✨ 告诉我你想要什么样的工作流                               │   │
│  │                                                                  │   │
│  │   ┌─────────────────────────────────────────────────────────┐  │   │
│  │   │ 描述你想要的工作流...                                     │  │   │
│  │   │                                                         │  │   │
│  │   │ 例如：创建一个自动回复客户邮件的工作流，                   │  │   │
│  │   │       当收到邮件时，先用 AI 分类，然后自动回复             │  │   │
│  │   │                                                         │  │   │
│  │   └─────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │                                        [🚀 开始生成]            │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ─────────────────── 或 ───────────────────                           │
│                                                                         │
│  💡 示例提示词                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🗂️ 客户反馈处理                                                 │   │
│  │    收集客户反馈 → AI 分析情感 → 根据结果分流处理                 │   │
│  │                                                                  │   │
│  │ 📰 自动写稿发布                                                 │   │
│  │    每天抓取热点 → AI 生成文章 → 审核后发布到各平台               │   │
│  │                                                                  │   │
│  │ 📊 数据分析报告                                                 │   │
│  │    导入数据 → AI 分析 → 生成可视化图表和报告                     │   │
│  │                                                                  │   │
│  │ 💬 智能客服                                                    │   │
│  │    接收用户问题 → 知识库检索 → AI 回答 → 保存对话记录             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 35.10.2 生成过程页面

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← 返回   正在生成工作流...                              [取消]         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │   🧠 正在分析你的需求...                                         │   │
│  │                                                                  │   │
│  │   ████████████████████░░░░░░░░░░░░░░░░░░░░░░  45%              │   │
│  │                                                                  │   │
│  │   ✓ 理解工作流目标                                               │   │
│  │   ✓ 分析所需节点                                                 │   │
│  │   ◐ 设计工作流结构 ← 当前                                        │   │
│  │   ○ 配置节点参数                                                 │   │
│  │   ○ 优化连接关系                                                 │   │
│  │                                                                  │   │
│  │   生成中...                                                      │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 35.10.3 生成结果确认

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← 返回   工作流已生成！                                    [编辑] [保存] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  🎉 已为你生成「邮件自动回复工作流」                                       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │   📥 邮件触发                                                    │   │
│  │       │                                                          │   │
│  │       ▼                                                          │   │
│  │   🔍 AI 分类                                                    │   │
│  │       │                                                          │   │
│  │       ├── 咨询 ──→ 📝 AI 回复                                   │   │
│  │       │                  │                                      │   │
│  │       ├── 投诉 ──→ 👤 人工处理 ←─────── 👤 人工处理完成           │   │
│  │       │                  │                     │                │   │
│  │       └── 退款 ──→ 💰 退款流程                                    │   │
│  │                      │                                            │   │
│  │                      ▼                                            │   │
│  │                  ✉️ 发送回复                                      │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  📝 工作流说明：                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 这个工作流会：                                                   │   │
│  │ 1. 自动接收新邮件                                                │   │
│  │ 2. 使用 AI 分析邮件类型（咨询/投诉/退款）                         │   │
│  │ 3. 根据类型自动处理或转人工                                      │   │
│  │ 4. 生成回复邮件并发送                                            │   │
│  │ 5. 保存对话记录到数据库                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ⚠️ 需要配置:                                                          │
│  • 邮箱账号连接                                                       │
│  • SMTP 发送设置                                                       │
│  • AI 模型选择                                                         │
│                                                                         │
│                              [编辑详情]  [保存到工作流]                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 35.12 设置页面详细设计

#### 35.12.1 设置页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│ 设置                                                                   │
├─────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐                                                │
│ │ 👤 个人信息   │                                                │
│ │ 🔒 安全设置   │   ┌─────────────────────────────────────────┐  │
│ │ 💳 订阅计划   │   │ 个人信息                                 │  │
│ │ 🔑 API 密钥   │   ├─────────────────────────────────────────┤  │
│ │ 🔔 通知设置   │   │                                         │  │
│ │ 🌐 API 配置   │   │  头像                                    │  │
│ │ 📦 数据管理   │   │  ┌─────┐  [更换头像]                     │  │
│ │               │   │  │ 😊 │                                  │  │
│ │               │   │  └─────┘                                  │  │
│ │               │   │                                         │  │
│ │               │   │  用户名                                   │  │
│ │               │   │  ┌─────────────────────────────────────┐ │  │
│ │               │   │  │ 张三                                  │ │  │
│ │               │   │  └─────────────────────────────────────┘ │  │
│ │               │   │                                         │  │
│ │               │   │  邮箱                                    │  │
│ │               │   │  ┌─────────────────────────────────────┐ │  │
│ │               │   │  │ zhangsan@example.com   [验证]        │ │  │
│ │               │   │  └─────────────────────────────────────┘ │  │
│ │               │   │                                         │  │
│ │               │   │  部门 / 公司                             │  │
│ │               │   │  ┌─────────────────────────────────────┐ │  │
│ │               │   │  │ 产品部 / XX 科技                    │ │  │
│ │               │   │  └─────────────────────────────────────┘ │  │
│ │               │   │                                         │  │
│ │               │   │  时区                                    │  │
│ │               │   │  ┌─────────────────────────────────────┐ │  │
│ │               │   │  │ (UTC+8) 北京时间            ▾       │ │  │
│ │               │   │  └─────────────────────────────────────┘ │  │
│ │               │   │                                         │  │
│ │               │   │  语言                                    │  │
│ │               │   │  ┌─────────────────────────────────────┐ │  │
│ │               │   │  │ 简体中文                        ▾   │ │  │
│ │               │   │  └─────────────────────────────────────┘ │  │
│ │               │   │                                         │  │
│ │               │   │  [保存更改]                               │  │
│ │               │   │                                         │  │
│ └───────────────┘   └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 35.13 通用组件设计规范

#### 35.13.1 按钮组件

```vue
<!-- 按钮类型 -->
<template>
  <button class="btn btn-primary">主要按钮</button>
  <button class="btn btn-secondary">次要按钮</button>
  <button class="btn btn-outline">描边按钮</button>
  <button class="btn btn-ghost">幽灵按钮</button>
  <button class="btn btn-danger">危险按钮</button>
</template>

<style scoped>
.btn {
  /* 尺寸 */
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  
  /* 状态 */
  transition: all 0.2s ease;
  cursor: pointer;
  
  /* 禁用 */
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: var(--primary-500);
  color: white;
  border: none;
  
  &:hover:not(:disabled) {
    background: var(--primary-600);
    transform: translateY(-1px);
    box-shadow: var(--shadow-glow);
  }
  
  &:active:not(:disabled) {
    background: var(--primary-700);
    transform: translateY(0);
  }
}

.btn-outline {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  
  &:hover:not(:disabled) {
    border-color: var(--primary-500);
    color: var(--primary-500);
  }
}
</style>
```

#### 35.12.2 输入框组件

```vue
<template>
  <div class="input-wrapper" :class="{ error: hasError, disabled: disabled }">
    <span v-if="prefix" class="input-prefix">{{ prefix }}</span>
    <input
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="input-field"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <span v-if="suffix" class="input-suffix">{{ suffix }}</span>
    <span v-if="hasError" class="input-error-icon">⚠️</span>
  </div>
  <span v-if="errorMessage" class="input-error-msg">{{ errorMessage }}</span>
</template>
```

#### 35.12.3 卡片组件

```vue
<template>
  <div class="card" :class="{ hoverable, bordered }">
    <div v-if="$slots.header" class="card-header">
      <slot name="header"></slot>
    </div>
    <div class="card-body">
      <slot></slot>
    </div>
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.card.hoverable {
  transition: all 0.2s ease;
  cursor: pointer;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }
}

.card.bordered {
  border: 1px solid var(--border-subtle);
}
</style>
```

#### 35.12.4 模态框组件

```vue
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-overlay" @click.self="close">
        <div class="modal-container" :class="`modal-${size}`">
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="modal-close" @click="close">✕</button>
          </div>
          <div class="modal-body">
            <slot></slot>
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer"></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: var(--bg-secondary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-height: 90vh;
  overflow: auto;
}

.modal-sm { width: 400px; }
.modal-md { width: 560px; }
.modal-lg { width: 720px; }
.modal-xl { width: 960px; }

/* 动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
  
  .modal-container {
    transition: transform 0.2s ease, opacity 0.2s ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  
  .modal-container {
    transform: scale(0.95);
    opacity: 0;
  }
}
</style>
```

#### 35.12.5 Toast 通知组件

```vue
<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast-${toast.type}`"
      >
        <span class="toast-icon">{{ toastIcons[toast.type] }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="removeToast(toast.id)">✕</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
const toastIcons = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 300px;
}

.toast-success { border-left: 4px solid var(--success); }
.toast-error   { border-left: 4px solid var(--error); }
.toast-warning { border-left: 4px solid var(--warning); }
.toast-info    { border-left: 4px solid var(--info); }
</style>
```

---

### 35.14 响应式设计规范

#### 35.14.1 断点定义

```scss
$breakpoints: (
  'sm': 640px,   // 手机横屏
  'md': 768px,   // 平板
  'lg': 1024px,  // 小屏笔记本
  'xl': 1280px,  // 标准屏幕
  '2xl': 1536px  // 大屏
);
```

#### 35.13.2 布局响应策略

| 组件 | >= 1024px | 768-1023px | < 768px |
|------|-----------|------------|---------|
| 侧边栏 | 显示固定 | 可折叠抽屉 | 隐藏/底部导航 |
| 工作流编辑器 | 三栏布局 | 两栏+抽屉 | 单栏+底部面板 |
| 仪表盘卡片 | 4列 | 2列 | 1列 |
| 表格 | 全列 | 简化列 | 卡片列表 |
| 表单 | 横向排列 | 纵向排列 | 全纵向 |

#### 35.13.3 移动端导航

```
┌─────────────────────┐
│ ☰ Flowly     🔔 👤 │
├─────────────────────┤
│                     │
│     内容区域         │
│                     │
│                     │
├─────────────────────┤
│ 🏠  │  📄  │  🤖  │  👤 │
│ 首页  工作流  智能体  我的 │
└─────────────────────┘
```

---

### 35.15 动效设计规范

#### 35.15.1 过渡时长

```scss
$duration-fast:   100ms;  // 微交互：hover、点击反馈
$duration-normal: 200ms;  // 标准：展开、收起、切换
$duration-slow:   300ms;  // 复杂：页面过渡、模态框
$duration-slower: 500ms;  // 特殊：加载动画、入场动画
```

#### 35.14.2 缓动函数

```scss
$ease-default: cubic-bezier(0.4, 0, 0.2, 1);      // 默认
$ease-in:      cubic-bezier(0.4, 0, 1, 1);        // 进入
$ease-out:     cubic-bezier(0, 0, 0.2, 1);        // 退出
$ease-spring:  cubic-bezier(0.175, 0.885, 0.32, 1.275); // 弹性
```

#### 35.14.3 关键动画

**页面加载骨架屏**：
```vue
<template>
  <div class="skeleton">
    <div class="skeleton-header"></div>
    <div class="skeleton-body">
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-card"></div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-line,
.skeleton-card {
  background: linear-gradient(
    90deg,
    var(--bg-tertiary) 25%,
    var(--bg-elevated) 50%,
    var(--bg-tertiary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
```

**按钮点击波纹效果**：
```css
.btn-ripple {
  position: relative;
  overflow: hidden;
}

.btn-ripple::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
  transform: scale(0);
  opacity: 0;
  transition: transform 0.5s, opacity 0.5s;
}

.btn-ripple:active::after {
  transform: scale(2);
  opacity: 1;
  transition: transform 0s, opacity 0s;
}
```

---

### 35.16 无障碍设计规范 (A11y)

#### 35.16.1 键盘导航

- 所有交互元素可通过 Tab 聚焦
- 聚焦顺序符合视觉逻辑
- 聚焦状态有明显样式（`outline: 2px solid var(--primary-500)`）
- 支持快捷键操作

#### 35.15.2 ARIA 标签

```vue
<button
  class="btn-icon"
  aria-label="删除"
  aria-describedby="delete-confirm-hint"
>
  🗑️
</button>
<span id="delete-confirm-hint" class="sr-only">
  删除后将无法恢复
</span>
```

#### 35.15.3 颜色对比度

- 文本与背景对比度 >= 4.5:1
- 大文本（>=18px）对比度 >= 3:1
- 关键信息不依赖颜色传达

---

### 35.17 图标系统

#### 35.17.1 图标库

推荐使用 **Lucide Icons** 或 **Heroicons**：
- 一致的 24x24 尺寸
- 2px 描边
- 支持按需导入

#### 35.16.2 图标使用规范

```vue
<!-- 使用图标组件 -->
<template>
  <Icon name="workflow" :size="20" color="#3B82F6" />
  <Icon name="ai" :size="24" />
</template>

<!-- SVG 内联（重要图标） -->
<template>
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="..." stroke="currentColor" stroke-width="2"/>
  </svg>
</template>
```

---

### 35.18 深色/浅色主题

#### 35.18.1 主题切换

```vue
<template>
  <button @click="toggleTheme">
    {{ isDark ? '🌙' : '☀️' }}
  </button>
</template>

<script setup>
const isDark = ref(true)

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('light-mode', !isDark.value)
}
</script>
```

#### 35.17.2 CSS 变量切换

```css
:root {
  --bg-primary: #0F0F12;
  --text-primary: #FFFFFF;
}

:root.light-mode {
  --bg-primary: #FFFFFF;
  --text-primary: #1A1A21;
}
```

---

### 35.19 总结

本章节详细规划了 Flowly 工作流平台的前端界面设计，包括：

1. **视觉规范**：色彩、字体、间距、阴影系统
2. **页面路由**：完整的页面层级和路由配置
3. **欢迎页**：落地页完整设计和布局
4. **登录注册**：表单设计、验证、第三方登录
5. **主控台**：统计卡片、快速入口、最近工作
6. **工作流编辑器**：核心编辑器界面、节点面板、属性配置
7. **迷你地图**：导航缩略图、视口同步、节点高亮
8. **执行页面**：流式输出、日志展示
9. **Agent 页面**：列表、调试器设计
10. **AI 生成页面**：自然语言生成工作流界面
11. **设置页面**：用户配置界面
12. **通用组件**：按钮、输入框、卡片、模态框、Toast
13. **响应式设计**：多端适配策略
14. **动效规范**：过渡时长、缓动函数、关键动画
15. **无障碍设计**：键盘导航、ARIA 标签
16. **图标与主题**：图标系统、深浅主题切换

这些设计规范将确保 Flowly 拥有一个专业、美观、易用的用户界面。

---

## 附录 A - 常见问题排查 (FAQ)

### A.1 环境搭建问题

#### Q1: Python 虚拟环境创建失败

**问题**: `py -3.12 -m venv venv` 命令执行失败

**解决方案**:
```powershell
# 检查 Python 版本
py -0

# 如果没有 3.12，使用其他可用版本
py -3.11 -m venv venv

# 或者直接从 Python 安装目录创建
cd e:\Flowly-now\Backend
python -m venv venv
```

#### Q2: pip 安装包失败

**问题**: `pip install` 报错 `Microsoft Visual C++ 14.0 is required`

**解决方案**:
```powershell
# 方法 1: 安装 Build Tools
# 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 勾选 "C++ 生成工具"

# 方法 2: 使用预编译包
pip install --only-binary=:all: package_name

# 方法 3: 更新 pip
python -m pip install --upgrade pip
```

#### Q3: MySQL 连接失败

**问题**: `django.db.utils OperationalError: (2003, Can't connect to MySQL server)`

**解决方案**:
```powershell
# 1. 检查 MySQL 服务是否运行
mysqladmin --version

# 2. 启动 MySQL 服务 (Windows)
net start mysql

# 3. 检查端口
netstat -an | findstr 3306

# 4. 测试连接
mysql -u root -p -h localhost

# 5. 创建数据库
CREATE DATABASE flowly_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### Q4: npm install 报错

**问题**: `npm ERR! code CERTIFICATE_EXPIRED`

**解决方案**:
```powershell
# 方法 1: 清除缓存
npm cache clean --force

# 方法 2: 设置 npm 源
npm config set registry https://registry.npmmirror.com

# 方法 3: 忽略 SSL 验证 (不推荐)
npm config set strict-ssl false
```

### A.2 Django 项目问题

#### Q5: 迁移文件执行失败

**问题**: `python manage.py migrate` 报错

**排查步骤**:
```powershell
# 1. 检查数据库连接
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()

# 2. 删除旧迁移文件，重新生成
cd Backend
del /q workflow\migrations\0*.py
python manage.py makemigrations workflow
python manage.py migrate --fake-initial

# 3. 如果是外键问题，检查模型定义
python manage.py check
```

#### Q6: CORS 跨域问题

**问题**: 前端请求被拦截，报 `CORS policy` 错误

**解决方案**:
```python
# Backend/config/settings.py

INSTALLED_APPS = [
    # ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 必须在最前面
    # ...
]

# 允许所有开发环境
CORS_ALLOW_ALL_ORIGINS = True  # 仅开发环境使用

# 生产环境配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://your-domain.com",
]
```

#### Q7: Django 静态文件不加载

**问题**: CSS/JS 文件 404

**解决方案**:
```powershell
# 1. 收集静态文件
python manage.py collectstatic

# 2. 配置 STATIC_ROOT
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# 3. Nginx 配置
location /static/ {
    alias /path/to/staticfiles/;
    expires 30d;
}
```

### A.3 前端问题

#### Q8: Vue 组件样式不生效

**问题**: scoped 样式不生效或样式冲突

**解决方案**:
```vue
<!-- 使用深度选择器 -->
<style scoped>
/deep/ .el-button {
  color: red;
}

/* 或使用 :global() */
:global(.el-button) {
  color: red;
}
</style>

<!-- 动态类名 -->
<template>
  <div :class="['custom-class', { active: isActive }]">
</template>
```

#### Q9: Pinia Store 状态不响应

**问题**: 修改 store 状态后视图不更新

**解决方案**:
```javascript
// 正确方式：修改 state 属性
const store = useWorkflowStore()
store.workflowName = 'New Name'  // 直接修改

// 错误方式：替换整个 state 对象
// store.$state = newState  // 不要这样做

// 如果需要批量更新
store.$patch({
  workflowName: 'New Name',
  nodes: [...],
})
```

#### Q10: Vue Flow 拖拽节点失败

**问题**: 节点无法拖入画布

**解决方案**:
```javascript
// 确保正确导入样式
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

// 检查是否正确注册节点类型
const nodeTypes = {
  custom: customNodeComponent,
}

// 确保拖拽事件正确处理
const onDrop = (event) => {
  const nodeType = JSON.parse(event.dataTransfer.getData('application/vueflow'))
  // ...
}
```

### A.4 AI/LangChain 问题

#### Q11: OpenAI API 调用失败

**问题**: `RateLimitError` 或 `AuthenticationError`

**解决方案**:
```python
# 1. 检查 API Key
import os
from dotenv import load_dotenv
load_dotenv()

print(os.getenv('OPENAI_API_KEY'))

# 2. 设置重试机制
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    api_key=api_key,
    max_retries=3,
    request_timeout=60,
)

# 3. 检查账户余额
# https://platform.openai.com/account/usage
```

#### Q12: LangChain 流式输出不工作

**问题**: 流式响应无法正确显示

**解决方案**:
```python
# 后端流式响应
from django.http import StreamingHttpResponse
import json

def stream_response(request):
    def generate():
        for chunk in llm.stream("你好"):
            yield chunk.content
    
    return StreamingHttpResponse(generate(), content_type='text/event-stream')

# 前端接收
const eventSource = new EventSource('/api/stream/')
eventSource.onmessage = (event) => {
  console.log(event.data)
}
```

### A.5 性能问题

#### Q13: 数据库查询慢

**问题**: API 响应时间过长

**解决方案**:
```python
# 1. 使用 select_related 减少查询
workflows = Workflow.objects.select_related('owner').all()

# 2. 使用 prefetch_related 预加载
workflows = Workflow.objects.prefetch_related('nodes', 'edges').all()

# 3. 添加数据库索引
class Workflow(models.Model):
    # ...
    class Meta:
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['is_published']),
        ]

# 4. 使用缓存
from django.core.cache import cache

def get_workflow(id):
    cache_key = f'workflow_{id}'
    workflow = cache.get(cache_key)
    if not workflow:
        workflow = Workflow.objects.get(id=id)
        cache.set(cache_key, workflow, timeout=300)
    return workflow
```

#### Q14: 前端打包体积过大

**问题**: `npm run build` 生成的文件太大

**解决方案**:
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'vue-flow': ['@vue-flow/core'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  optimizeDeps: {
    include: ['element-plus', 'vue', 'vue-router', 'pinia'],
  },
})
```

---

## 附录 B - 开发环境最佳实践

### B.1 Git 工作流

#### 分支命名规范
```
feature/xxx-feature-name      # 新功能
bugfix/xxx-bug-description     # Bug 修复
hotfix/xxx-critical-fix        # 紧急修复
release/v1.0.0                 # 发布版本
refactor/xxx-refactor-name     # 代码重构
docs/xxx-documentation         # 文档更新
```

#### Commit 规范
```
feat: 新功能
fix: Bug 修复
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
perf: 性能优化
test: 测试
chore: 构建/工具

# 示例
feat(workflow): 添加工作流复制功能
fix(api): 修复节点删除时边界条件错误
docs(readme): 更新安装说明
```

#### 提交信息模板
```
<类型>(<模块>): <简短描述>

<详细说明（可选）>

<关联的 Issue (可选)>

Fixes #123
Related to #456
```

### B.2 环境配置管理

#### .env 文件模板

**Backend/.env.example**
```env
# Django 配置
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库
DB_ENGINE=django.db.backends.mysql
DB_NAME=flowly_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440
```

**Frontend/.env.example**
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_APP_NAME=Flowly
VITE_APP_VERSION=1.0.0
```

#### 配置加载优先级
```python
# config/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. 基础配置
SECRET_KEY = 'default-key'
DEBUG = False

# 2. 加载 .env 文件
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 3. 从环境变量覆盖
SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
```

### B.3 代码格式化

#### Pre-commit Hooks

**Backend/.pre-commit-config.yaml**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
        args: ['--profile', 'black']

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120']
```

**Frontend/.husky/pre-commit**
```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npx lint-staged
```

**Frontend/package.json**
```json
{
  "lint-staged": {
    "*.{js,vue}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{css,scss}": [
      "prettier --write"
    ]
  }
}
```

### B.4 日志配置

#### Django 日志配置
```python
# config/logging.py
import logging
from django.utils.log import AdminEmailHandler

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'level': 'ERROR',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
            'formatter': 'verbose',
        },
    },
    
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console', 'error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'workflow': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### B.5 调试技巧

#### Django 调试
```python
# 使用 Django Debug Toolbar
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # ...
]

INTERNAL_IPS = ['127.0.0.1']

# 使用 django-silk 进行性能分析
INSTALLED_APPS = [
    # ...
    'silk',
]
```

#### Vue DevTools
```javascript
// vite.config.js
export default defineConfig({
  plugins: [
    vue({
      pluginOptions: {
        vueInspector: {
          enabled: true,
        },
      },
    }),
  ],
})
```

#### API 调试脚本
```python
# scripts/test_api.py
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_workflow_api():
    # 登录获取 token
    response = requests.post(f"{BASE_URL}/auth/login/", {
        "username": "test",
        "password": "test123"
    })
    token = response.json().get('access')
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建工作流
    response = requests.post(
        f"{BASE_URL}/workflows/",
        json={
            "name": "Test Workflow",
            "description": "Test"
        },
        headers=headers
    )
    print(f"Create: {response.status_code} - {response.json()}")
    
    workflow_id = response.json()['id']
    
    # 获取工作流
    response = requests.get(
        f"{BASE_URL}/workflows/{workflow_id}/",
        headers=headers
    )
    print(f"Get: {response.status_code} - {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    test_workflow_api()
```

---

## 附录 C - API 接口详细文档

### C.1 认证 API

#### 用户注册
```
POST /api/auth/register/
```

**请求体**:
```json
{
    "username": "string",      // 必填，3-30字符
    "email": "string",        // 必填，有效邮箱格式
    "password": "string",     // 必填，最少8字符
    "password_confirm": "string" // 必填，与password一致
}
```

**响应** (201):
```json
{
    "id": "uuid",
    "username": "string",
    "email": "string",
    "tokens": {
        "access": "jwt_token",
        "refresh": "refresh_token"
    }
}
```

#### 用户登录
```
POST /api/auth/login/
```

**请求体**:
```json
{
    "username": "string",
    "password": "string"
}
```

**响应** (200):
```json
{
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token",
    "user": {
        "id": "uuid",
        "username": "string",
        "email": "string"
    }
}
```

#### 刷新 Token
```
POST /api/auth/refresh/
```

**请求体**:
```json
{
    "refresh": "refresh_token"
}
```

**响应** (200):
```json
{
    "access": "new_access_token"
}
```

### C.2 工作流 API

#### 获取工作流列表
```
GET /api/workflows/
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| search | string | 搜索关键词 |
| ordering | string | 排序字段 (-created_at) |

**响应** (200):
```json
{
    "count": 100,
    "next": "url or null",
    "previous": "url or null",
    "results": [
        {
            "id": "uuid",
            "name": "string",
            "description": "string",
            "owner_name": "string",
            "is_published": true,
            "node_count": 10,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ]
}
```

#### 创建工作流
```
POST /api/workflows/
```

**请求体**:
```json
{
    "name": "string",           // 必填
    "description": "string",    // 可选
    "is_published": false       // 可选
}
```

**响应** (201):
```json
{
    "id": "uuid",
    "name": "string",
    "description": "string",
    "owner": "user_id",
    "owner_name": "string",
    "is_published": false,
    "nodes": [],
    "edges": [],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 获取工作流详情
```
GET /api/workflows/{id}/
```

**响应** (200):
```json
{
    "id": "uuid",
    "name": "string",
    "description": "string",
    "owner": "user_id",
    "owner_name": "string",
    "is_published": true,
    "nodes": [
        {
            "id": "uuid",
            "node_type": "llm",
            "name": "LLM Node",
            "config": {
                "model": "gpt-4",
                "prompt": "..."
            },
            "position_x": 100,
            "position_y": 200
        }
    ],
    "edges": [
        {
            "id": "uuid",
            "source_node": "node_id",
            "target_node": "node_id",
            "label": "condition_true"
        }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 更新工作流
```
PATCH /api/workflows/{id}/
```

**请求体**:
```json
{
    "name": "New Name",
    "description": "Updated description"
}
```

#### 删除工作流
```
DELETE /api/workflows/{id}/
```

**响应** (204): No Content

#### 执行工作流
```
POST /api/workflows/{id}/execute/
```

**请求体**:
```json
{
    "input_data": {
        "text": "Hello World"
    },
    "stream": false
}
```

**响应** (202):
```json
{
    "execution_id": "uuid",
    "status": "pending",
    "message": "工作流执行已启动"
}
```

#### 流式执行工作流
```
POST /api/workflows/{id}/execute/
```

**请求体**:
```json
{
    "input_data": {
        "text": "Hello"
    },
    "stream": true
}
```

**响应**: Server-Sent Events
```
data: {"type": "node_start", "node_id": "xxx", "node_name": "LLM"}
data: {"type": "token", "content": "Hello"}
data: {"type": "node_complete", "node_id": "xxx", "output": "..."}
data: {"type": "complete", "execution_id": "xxx"}
```

#### 复制工作流
```
POST /api/workflows/{id}/duplicate/
```

**响应** (201):
```json
{
    "id": "new_uuid",
    "name": "工作流名称 (副本)",
    ...
}
```

### C.3 节点 API

#### 创建节点
```
POST /api/nodes/
```

**请求体**:
```json
{
    "workflow": "workflow_uuid",
    "node_type": "llm",
    "name": "LLM Node",
    "config": {
        "model": "gpt-4",
        "temperature": 0.7,
        "prompt": "You are a helpful assistant."
    },
    "position_x": 100,
    "position_y": 200
}
```

#### 批量更新节点
```
POST /api/workflows/{id}/nodes/batch/
```

**请求体**:
```json
{
    "nodes": [
        {
            "id": "uuid",
            "position_x": 150,
            "position_y": 250,
            "config": {...}
        }
    ]
}
```

### C.4 Agent API

#### 创建 Agent
```
POST /api/agents/
```

**请求体**:
```json
{
    "name": "Research Agent",
    "description": "Research assistant",
    "model": "gpt-4",
    "system_prompt": "You are a research assistant.",
    "tools": ["search", "calculator"],
    "settings": {
        "temperature": 0.7,
        "max_tokens": 2000
    }
}
```

#### 执行 Agent
```
POST /api/agents/{id}/chat/
```

**请求体**:
```json
{
    "message": "What is the capital of France?",
    "session_id": "optional_session_uuid"
}
```

### C.5 错误响应格式

**错误响应**:
```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": {
            "field_name": ["Error message 1", "Error message 2"]
        }
    }
}
```

**错误代码**:
| 代码 | HTTP 状态 | 说明 |
|------|----------|------|
| VALIDATION_ERROR | 400 | 输入验证失败 |
| AUTHENTICATION_ERROR | 401 | 认证失败 |
| PERMISSION_DENIED | 403 | 权限不足 |
| NOT_FOUND | 404 | 资源不存在 |
| RATE_LIMIT | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 附录 D - 错误处理和日志最佳实践

### D.1 自定义异常处理

#### 异常类定义
```python
# utils/exceptions.py

from rest_framework import status
from rest_framework.exceptions import APIException


class WorkflowException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '工作流操作失败'
    default_code = 'workflow_error'


class NodeNotFoundException(WorkflowException):
    default_detail = '节点不存在'
    default_code = 'node_not_found'


class InvalidWorkflowException(WorkflowException):
    default_detail = '工作流配置无效'
    default_code = 'invalid_workflow'


class ExecutionTimeoutException(WorkflowException):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    default_detail = '工作流执行超时'
    default_code = 'execution_timeout'


class ModelNotAvailableException(WorkflowException):
    default_detail = '模型不可用'
    default_code = 'model_not_available'
```

#### 全局异常处理器
```python
# config/exception_handler.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """自定义全局异常处理器"""
    
    # 调用默认处理器
    response = exception_handler(exc, context)
    
    if response is not None:
        # 标准化错误格式
        error_data = {
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
                'details': {}
            }
        }
        
        # 处理验证错误
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            error_data['error']['details'] = exc.detail
        
        response.data = error_data
        
        # 记录日志
        logger.warning(
            f"API Error: {error_data['error']['code']} - {error_data['error']['message']}",
            extra={
                'status_code': response.status_code,
                'path': context['request'].path,
                'user': context['request'].user,
            }
        )
    
    else:
        # 处理未捕获的异常
        logger.exception(f"Unhandled exception: {exc}")
        error_data = {
            'error': {
                'code': 'internal_error',
                'message': '服务器内部错误',
                'details': {}
            }
        }
        response = Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response
```

### D.2 前端错误处理

#### Axios 拦截器配置
```javascript
// api/index.js
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    // 处理 401 未授权
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post('/api/auth/refresh/', {
            refresh: refreshToken
          })
          
          const { access } = response.data
          localStorage.setItem('access_token', access)
          
          originalRequest.headers.Authorization = `Bearer ${access}`
          return api(originalRequest)
        } catch (refreshError) {
          // 刷新失败，跳转登录
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          router.push('/login')
          return Promise.reject(refreshError)
        }
      }
    }
    
    // 处理 403 权限不足
    if (error.response?.status === 403) {
      ElMessage.error('您没有权限执行此操作')
    }
    
    // 处理 429 请求频率超限
    if (error.response?.status === 429) {
      ElMessage.warning('请求过于频繁，请稍后再试')
    }
    
    // 处理 500 服务器错误
    if (error.response?.status >= 500) {
      ElMessage.error('服务器错误，请稍后再试')
    }
    
    return Promise.reject(error)
  }
)

export default api
```

#### 错误边界组件
```vue
<template>
  <div v-if="hasError" class="error-boundary">
    <h2>出错了</h2>
    <p>{{ errorMessage }}</p>
    <button @click="resetError">重试</button>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err, instance, info) => {
  console.error('Error captured:', err, info)
  hasError.value = true
  errorMessage.value = err.message || '发生未知错误'
  return false
})

const resetError = () => {
  hasError.value = false
  errorMessage.value = ''
}
</script>
```

### D.3 日志记录最佳实践

#### 结构化日志
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log(self, level: str, message: str, **kwargs):
        """记录结构化日志"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.log('DEBUG', message, **kwargs)


# 使用示例
logger = StructuredLogger('workflow')

logger.info('工作流执行开始', 
    workflow_id='xxx',
    user_id='yyy',
    node_count=10
)

logger.error('执行失败',
    workflow_id='xxx',
    error_type='timeout',
    error_message='Execution timed out'
)
```

#### 工作流执行日志
```python
# workflow/services/execution_logger.py

import logging
from django.db import transaction
from ..models import WorkflowExecutionLog

logger = logging.getLogger('workflow.execution')


class ExecutionLogger:
    """工作流执行日志记录器"""
    
    def __init__(self, execution):
        self.execution = execution
        self.logs = []
    
    def log_node_start(self, node):
        """记录节点开始执行"""
        message = f"开始执行节点: {node.name}"
        self._save_log('node_start', message, {'node_id': str(node.id)})
        logger.info(message, execution_id=str(self.execution.id))
    
    def log_node_complete(self, node, output):
        """记录节点执行完成"""
        message = f"节点执行完成: {node.name}"
        self._save_log('node_complete', message, {
            'node_id': str(node.id),
            'output_size': len(str(output))
        })
        logger.info(message, execution_id=str(self.execution.id))
    
    def log_node_error(self, node, error):
        """记录节点执行错误"""
        message = f"节点执行失败: {node.name} - {str(error)}"
        self._save_log('node_error', message, {
            'node_id': str(node.id),
            'error': str(error)
        })
        logger.error(message, execution_id=str(self.execution.id))
    
    def log_edge_traverse(self, source, target):
        """记录边遍历"""
        message = f"遍历边: {source.name} -> {target.name}"
        self._save_log('edge_traverse', message, {
            'source_id': str(source.id),
            'target_id': str(target.id)
        })
        logger.debug(message, execution_id=str(self.execution.id))
    
    def _save_log(self, event_type, message, metadata):
        """保存日志到数据库"""
        self.logs.append(WorkflowExecutionLog(
            execution=self.execution,
            event_type=event_type,
            message=message,
            metadata=metadata
        ))
    
    def save_all(self):
        """批量保存日志"""
        with transaction.atomic():
            WorkflowExecutionLog.objects.bulk_create(self.logs)
```

---

## 附录 E - 性能优化指南

### E.1 数据库优化

#### 查询优化
```python
# 1. 使用 select_related (一对一)
workflows = Workflow.objects.select_related('owner').all()

# 2. 使用 prefetch_related (一对多)
workflows = Workflow.objects.prefetch_related(
    'nodes',
    'edges',
    'nodes__config'  # 嵌套预加载
).all()

# 3. 使用 only 减少字段
users = User.objects.only('id', 'username', 'email').all()

# 4. 使用 defer 延迟加载
users = User.objects.defer('password', 'last_login').all()

# 5. 使用 values 和 values_list
usernames = User.objects.values_list('username', flat=True)
```

#### 索引优化
```python
class Workflow(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows'
        indexes = [
            # 复合索引
            models.Index(
                fields=['owner', '-created_at'],
                name='idx_owner_created'
            ),
            # 条件索引
            models.Index(
                fields=['owner', 'is_published'],
                name='idx_owner_published'
            ),
        ]
```

#### 分页优化
```python
# 使用游标分页 (更高效)
class CursorPagination:
    """游标分页"""
    
    page_size = 20
    ordering = '-created_at'
    cursor_field = 'id'
    
    def paginate_queryset(self, queryset, request):
        cursor = request.query_params.get('cursor')
        
        if cursor:
            cursor_obj = self.decode_cursor(cursor)
            queryset = queryset.filter(
                **{f'{self.cursor_field}__lt': cursor_obj}
            )
        
        queryset = queryset.order_by(self.ordering)[:self.page_size]
        return list(queryset)
```

### E.2 缓存策略

#### Redis 缓存
```python
# utils/cache.py

from django.core.cache import cache
from functools import wraps
import hashlib
import json

def cache_result(timeout=300, key_prefix=''):
    """缓存函数结果的装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(json.dumps((args, kwargs), sort_keys=True).encode()).hexdigest()}"
            
            # 尝试获取缓存
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数并缓存
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_prefix):
    """清除缓存"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 清除相关缓存
            # 这里需要根据实际情况实现
            return result
        return wrapper
    return decorator
```

#### 缓存模式
```python
# 工作流缓存
class WorkflowCache:
    """工作流缓存管理"""
    
    @staticmethod
    def get_workflow(workflow_id):
        """获取工作流（带缓存）"""
        cache_key = f"workflow:{workflow_id}"
        workflow = cache.get(cache_key)
        
        if workflow is None:
            workflow = Workflow.objects.select_related('owner').get(id=workflow_id)
            cache.set(cache_key, workflow, timeout=300)
        
        return workflow
    
    @staticmethod
    def invalidate_workflow(workflow_id):
        """清除工作流缓存"""
        cache.delete(f"workflow:{workflow_id}")
    
    @staticmethod
    def get_workflow_stats(user_id):
        """获取用户工作流统计（带缓存）"""
        cache_key = f"workflow_stats:{user_id}"
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total': Workflow.objects.filter(owner_id=user_id).count(),
                'published': Workflow.objects.filter(owner_id=user_id, is_published=True).count(),
            }
            cache.set(cache_key, stats, timeout=60)
        
        return stats
```

### E.3 API 性能优化

#### 异步处理
```python
# 使用 Celery 异步执行
@shared_task
def execute_workflow_async(execution_id):
    """异步执行工作流"""
    from .models import WorkflowExecution
    from .services.executor import WorkflowExecutor
    
    execution = WorkflowExecution.objects.get(id=execution_id)
    
    try:
        executor = WorkflowExecutor(execution.workflow, execution)
        executor.execute()
    except Exception as e:
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.save()
        raise
```

#### 批量操作优化
```python
# 批量创建节点
def bulk_create_nodes(workflow_id, nodes_data):
    """批量创建节点"""
    nodes = [
        Node(
            workflow_id=workflow_id,
            node_type=data['node_type'],
            name=data['name'],
            config=data.get('config', {}),
            position_x=data['position_x'],
            position_y=data['position_y']
        )
        for data in nodes_data
    ]
    
    return Node.objects.bulk_create(nodes)

# 批量更新
def bulk_update_nodes(nodes_data):
    """批量更新节点"""
    node_ids = [n['id'] for n in nodes_data]
    nodes = {n.id: n for n in Node.objects.filter(id__in=node_ids)}
    
    for data in nodes_data:
        node = nodes[data['id']]
        for key, value in data.items():
            if hasattr(node, key):
                setattr(node, key, value)
    
    Node.objects.bulk_update(nodes.values(), ['name', 'config', 'position_x', 'position_y'])
```

### E.4 前端性能优化

#### 虚拟列表
```vue
<template>
  <virtual-list
    :items="items"
    :item-height="60"
    class="virtual-list"
  >
    <template #default="{ item }">
      <workflow-item :workflow="item" />
    </template>
  </virtual-list>
</template>

<script setup>
import VirtualList from 'vue-virtual-scroll-list'

const props = defineProps({
  items: {
    type: Array,
    required: true
  }
})
</script>
```

#### 防抖和节流
```javascript
// utils/debounce.js

export function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

export function throttle(fn, delay = 300) {
  let last = 0
  return function (...args) {
    const now = Date.now()
    if (now - last >= delay) {
      last = now
      fn.apply(this, args)
    }
  }
}

// 使用
const saveWorkflow = debounce(async () => {
  await workflowAPI.updateWorkflow(id, workflowData.value)
}, 500)
```

#### 懒加载组件
```javascript
// router/routes.js
const routes = [
  {
    path: '/workflow/:id',
    component: () => import('../views/WorkflowEditor.vue'),
    // 路由级别的代码分割
  },
  {
    path: '/analytics',
    component: () => import('../views/Analytics.vue'),
    // 只有访问时才加载
  }
]
```

---

## 附录 F - 安全加固详细说明

### F.1 身份认证安全

#### JWT 安全配置
```python
# settings.py

from datetime import timedelta

# JWT 配置
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    
    # 安全配置
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY'),
    
    # Token 验证
    'VERIFY_ISS': True,
    'VERIFY_AUD': True,
    'ISSUER': 'flowly-api',
    'AUDIENCE': 'flowly-frontend',
}

# Token 黑名单
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

#### 密码安全
```python
# settings.py

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'user_attributes': ('username', 'email')}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 密码哈希配置
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # 推荐
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
```

### F.2 API 安全

#### 请求限流
```python
# settings.py

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'workflow_execute': '10/minute',
    },
}

# 自定义限流
class WorkflowExecuteThrottle(UserRateThrottle):
    rate = '10/minute'
    scope = 'workflow_execute'
```

#### CORS 配置
```python
# settings.py

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://your-domain.com",
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# 安全头
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_PRIVATE_NETWORK = False
```

### F.3 数据安全

#### 敏感数据加密
```python
# utils/encryption.py

from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


class DataEncryptor:
    """数据加密工具"""
    
    def __init__(self):
        key = settings.ENCRYPTION_KEY.encode()
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """加密字符串"""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密字符串"""
        decoded = base64.b64decode(encrypted_data.encode())
        return self.cipher.decrypt(decoded).decode()


class APIKeyEncryptor:
    """API Key 加密存储"""
    
    def __init__(self):
        self.encryptor = DataEncryptor()
    
    def save_key(self, api_key: str) -> str:
        """保存并加密 API Key"""
        return self.encryptor.encrypt(api_key)
    
    def get_key(self, encrypted_key: str) -> str:
        """获取并解密 API Key"""
        return self.encryptor.decrypt(encrypted_key)
```

#### 敏感字段保护
```python
# serializers.py

import re

class SensitiveDataSerializer(serializers.Serializer):
    """敏感数据序列化器"""
    
    def to_representation(self, instance):
        """脱敏输出"""
        data = super().to_representation(instance)
        
        # 脱敏邮箱
        if 'email' in data:
            data['email'] = mask_email(data['email'])
        
        # 脱敏手机号
        if 'phone' in data:
            data['phone'] = mask_phone(data['phone'])
        
        return data


def mask_email(email: str) -> str:
    """邮箱脱敏"""
    if '@' in email:
        username, domain = email.split('@')
        if len(username) > 2:
            return f"{username[0]}***{username[-1]}@{domain}"
    return email


def mask_phone(phone: str) -> str:
    """手机号脱敏"""
    if len(phone) >= 7:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone
```

### F.4 输入验证

#### 请求体验证
```python
# utils/validators.py

import re
from rest_framework import serializers


class WorkflowValidator:
    """工作流验证器"""
    
    @staticmethod
    def validate_workflow_structure(data):
        """验证工作流结构"""
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        
        # 检查开始节点
        start_nodes = [n for n in nodes if n.get('node_type') == 'start']
        if not start_nodes:
            raise serializers.ValidationError("工作流必须包含开始节点")
        
        # 检查结束节点
        end_nodes = [n for n in nodes if n.get('node_type') == 'end']
        if not end_nodes:
            raise serializers.ValidationError("工作流必须包含结束节点")
        
        # 检查孤立节点
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get('source'))
            connected_nodes.add(edge.get('target'))
        
        for node in nodes:
            if node.get('node_type') not in ['start', 'end']:
                if node['id'] not in connected_nodes:
                    raise serializers.ValidationError(
                        f"节点 {node.get('name')} 未连接到任何边"
                    )
        
        return data
    
    @staticmethod
    def validate_node_config(node_type, config):
        """验证节点配置"""
        if node_type == 'llm':
            if 'model' not in config:
                raise serializers.ValidationError("LLM 节点必须指定模型")
        
        elif node_type == 'condition':
            if 'condition' not in config:
                raise serializers.ValidationError("条件节点必须指定条件")
        
        return config


class InputSanitizer:
    """输入清理工具"""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """移除 HTML 标签"""
        return re.sub(r'<[^>]+>', '', text)
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """防止 SQL 注入（使用参数化查询，Django 自动处理）"""
        return text
    
    @staticmethod
    def sanitize_script(text: str) -> str:
        """移除脚本内容"""
        return re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
```

### F.5 安全头配置

#### Django 安全中间件
```python
# settings.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ...
]

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS 配置 (生产环境)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie 配置
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

---

## 附录 G - 企业级功能优化（对标商业工作流平台）

> 本章节详细描述 Flowly 平台的企业级功能优化，目标是对标 Flowise、Dify、n8n、Make 等成熟商业工作流平台。

### G.1 高级工作流控制流

#### G.1.1 并行执行引擎

成熟平台如 n8n 和 Make 都支持并行执行节点，显著提升工作流效率：

```python
# workflow/services/parallel_executor.py

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"          # 完全并行
    PARALLEL_GROUP = "parallel_group"  # 并行分组


@dataclass
class ParallelNode:
    """并行节点定义"""
    node_id: str
    executor: Callable
    dependencies: List[str]  # 依赖的节点ID
    config: Dict[str, Any]


class ParallelExecutionEngine:
    """并行执行引擎"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, Exception] = {}
    
    async def execute_parallel(
        self,
        nodes: List[ParallelNode],
        shared_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """并行执行多个节点"""
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(nodes)
        
        # 执行没有依赖的节点
        ready_nodes = [n for n in nodes if not n.dependencies]
        
        while ready_nodes:
            # 收集所有就绪节点的 futures
            futures = {}
            for node in ready_nodes:
                future = self.executor.submit(
                    self._execute_node,
                    node,
                    shared_context.copy()
                )
                futures[future] = node
            
            # 等待所有并行任务完成
            completed_nodes = []
            for future in as_completed(futures):
                node = futures[future]
                try:
                    result = future.result()
                    self.results[node.node_id] = result
                    shared_context[node.node_id] = result
                    completed_nodes.append(node)
                except Exception as e:
                    self.errors[node.node_id] = e
                    # 错误处理策略
                    if not self._should_continue_on_error(node):
                        raise
                    completed_nodes.append(node)
            
            # 找到下一批就绪节点
            ready_nodes = self._get_ready_nodes(
                nodes, 
                completed_nodes, 
                dependency_graph
            )
        
        return {
            'results': self.results,
            'errors': {k: str(v) for k, v in self.errors.items()},
            'success': len(self.errors) == 0
        }
    
    def _build_dependency_graph(
        self, 
        nodes: List[ParallelNode]
    ) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {n.node_id: n.dependencies for n in nodes}
        return graph
    
    def _get_ready_nodes(
        self,
        all_nodes: List[ParallelNode],
        completed_nodes: List[ParallelNode],
        dependency_graph: Dict[str, List[str]]
    ) -> List[ParallelNode]:
        """获取下一批就绪节点"""
        completed_ids = {n.node_id for n in completed_nodes}
        ready = []
        
        for node in all_nodes:
            if node.node_id in completed_ids:
                continue
            # 检查所有依赖是否已完成
            if all(dep in completed_ids for dep in node.dependencies):
                ready.append(node)
        
        return ready
    
    def _execute_node(
        self, 
        node: ParallelNode, 
        context: Dict[str, Any]
    ) -> Any:
        """执行单个节点"""
        # 合并依赖节点的输出到上下文
        for dep_id in node.dependencies:
            if dep_id in self.results:
                context[dep_id] = self.results[dep_id]
        
        return node.executor(context, node.config)
    
    def _should_continue_on_error(self, node: ParallelNode) -> bool:
        """判断节点是否应在错误时继续"""
        return node.config.get('continue_on_error', False)
```

#### G.1.2 循环执行支持

支持 ForEach 和 While 循环，实现复杂业务逻辑：

```python
# workflow/nodes/loop_nodes.py

from typing import Any, Iterator, List
from abc import ABC, abstractmethod


class LoopNode(ABC):
    """循环节点基类"""
    
    @abstractmethod
    def get_iterator(self, context: Dict[str, Any]) -> Iterator:
        """获取迭代器"""
        pass
    
    @abstractmethod
    def process_item(self, item: Any, context: Dict[str, Any]) -> Any:
        """处理单个迭代项"""
        pass


class ForEachNode(LoopNode):
    """ForEach 循环节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.array_expression = config.get('array', 'items')
        self.item_variable = config.get('item_variable', 'item')
        self.index_variable = config.get('index_variable', 'index')
        self.max_iterations = config.get('max_iterations', 1000)
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 ForEach 循环"""
        
        # 获取数组
        array = self._evaluate_expression(self.array_expression, context)
        
        if not isinstance(array, (list, tuple)):
            raise ValueError(f"ForEach 节点需要数组表达式，当前: {array}")
        
        results = []
        errors = []
        
        for index, item in enumerate(array[:self.max_iterations]):
            # 设置循环变量
            loop_context = context.copy()
            loop_context[self.item_variable] = item
            loop_context[self.index_variable] = index
            
            try:
                result = self.process_item(item, loop_context)
                results.append(result)
            except Exception as e:
                errors.append({'index': index, 'error': str(e)})
                
                # 检查是否应继续
                if not self.config.get('continue_on_error', False):
                    break
        
        return {
            'results': results,
            'errors': errors,
            'total': len(results),
            'failed': len(errors)
        }


class WhileNode(LoopNode):
    """While 循环节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.condition_expression = config.get('condition')
        self.max_iterations = config.get('max_iterations', 1000)
        self.timeout_seconds = config.get('timeout_seconds', 300)
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 While 循环"""
        
        results = []
        iteration = 0
        start_time = time.time()
        
        while self._evaluate_condition(self.condition_expression, context):
            iteration += 1
            
            # 超时检查
            if time.time() - start_time > self.timeout_seconds:
                raise TimeoutError(f"While 循环超时 ({self.timeout_seconds}s)")
            
            # 最大迭代检查
            if iteration > self.max_iterations:
                raise ValueError(f"While 循环超过最大迭代次数 ({self.max_iterations})")
            
            try:
                result = self.process_loop_body(context)
                results.append(result)
                context['loop_result'] = result
            except Exception as e:
                if not self.config.get('continue_on_error', False):
                    raise
        
            # 更新循环变量
            context['loop_iteration'] = iteration
        
        return {
            'results': results,
            'iterations': iteration,
            'success': True
        }
    
    def _evaluate_condition(self, expression: str, context: Dict) -> bool:
        """评估循环条件"""
        # 支持简单的条件表达式
        # 例如: iteration < 10, count < max
        try:
            return eval(expression, {"__builtins__": {}}, context)
        except:
            return False


class DoWhileNode(LoopNode):
    """Do-While 循环节点（至少执行一次）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.condition_expression = config.get('condition')
        self.max_iterations = config.get('max_iterations', 1000)
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Do-While 循环"""
        
        results = []
        iteration = 0
        
        while True:
            iteration += 1
            
            if iteration > self.max_iterations:
                raise ValueError(f"Do-While 循环超过最大迭代次数 ({self.max_iterations})")
            
            try:
                result = self.process_loop_body(context)
                results.append(result)
                context['loop_result'] = result
            except Exception as e:
                if not self.config.get('continue_on_error', False):
                    raise
            
            context['loop_iteration'] = iteration
            
            # 检查条件
            if not self._evaluate_condition(self.condition_expression, context):
                break
        
        return {
            'results': results,
            'iterations': iteration,
            'success': True
        }
```

#### G.1.3 错误处理与重试机制

成熟的错误处理策略，类似 n8n 的 Error Trigger 和 Retry：

```python
# workflow/services/error_handler.py

import time
from typing import Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps


class RetryStrategy(Enum):
    FIXED = "fixed"                      # 固定间隔
    EXPONENTIAL = "exponential"          # 指数退避
    LINEAR = "linear"                    # 线性递增


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    initial_delay: float = 1.0           # 秒
    max_delay: float = 60.0              # 秒
    jitter: bool = True                  # 添加随机抖动


@dataclass
class ErrorHandler:
    """错误处理器配置"""
    on_error: str = "stop"               # stop, continue, jump_to, retry
    retry_config: Optional[RetryConfig] = None
    fallback_value: Any = None           # 错误时的默认值
    error_output: Optional[str] = None    # 错误输出节点
    error_chain: List[str] = field(default_factory=list)  # 错误处理链


def with_retry(config: RetryConfig):
    """重试装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(config, attempt)
                        time.sleep(delay)
                    else:
                        raise last_exception
        
        return wrapper
    return decorator


def calculate_delay(config: RetryConfig, attempt: int) -> float:
    """计算重试延迟"""
    import random
    
    if config.strategy == RetryStrategy.FIXED:
        delay = config.initial_delay
    elif config.strategy == RetryStrategy.EXPONENTIAL:
        delay = min(
            config.initial_delay * (2 ** attempt),
            config.max_delay
        )
    elif config.strategy == RetryStrategy.LINEAR:
        delay = min(
            config.initial_delay * (attempt + 1),
            config.max_delay
        )
    else:
        delay = config.initial_delay
    
    # 添加抖动
    if config.jitter:
        delay *= (0.5 + random.random() * 0.5)
    
    return delay


class WorkflowErrorHandler:
    """工作流级错误处理器"""
    
    def __init__(self):
        self.error_handlers: Dict[str, ErrorHandler] = {}
        self.error_history: List[Dict] = []
    
    def register_handler(
        self,
        node_id: str,
        handler: ErrorHandler
    ):
        """注册节点错误处理器"""
        self.error_handlers[node_id] = handler
    
    def handle_error(
        self,
        node_id: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> Any:
        """处理节点错误"""
        
        # 记录错误历史
        self.error_history.append({
            'node_id': node_id,
            'error': str(error),
            'timestamp': time.time()
        })
        
        handler = self.error_handlers.get(node_id)
        
        if not handler:
            raise error
        
        if handler.on_error == "stop":
            raise error
        
        elif handler.on_error == "continue":
            return handler.fallback_value
        
        elif handler.on_error == "jump_to":
            return self._jump_to_node(handler.error_output, context)
        
        elif handler.on_error == "retry":
            return self._retry_with_config(handler.retry_config, node_id, context)
    
    def _jump_to_node(
        self,
        target_node: str,
        context: Dict
    ) -> Any:
        """跳转到指定节点"""
        context['_error_jump_target'] = target_node
        return None
    
    def _retry_with_config(
        self,
        config: RetryConfig,
        node_id: str,
        context: Dict
    ) -> Any:
        """使用配置重试"""
        pass  # 实现重试逻辑
```

#### G.1.4 条件分支高级逻辑

```python
# workflow/nodes/condition_nodes.py

from typing import Any, Dict, List, Union
import re


class ConditionEvaluator:
    """高级条件评估器"""
    
    # 支持的操作符
    OPERATORS = {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>': lambda a, b: a > b,
        '>=': lambda a, b: a >= b,
        '<': lambda a, b: a < b,
        '<=': lambda a, b: a <= b,
        'contains': lambda a, b: b in str(a),
        'not_contains': lambda a, b: b not in str(a),
        'starts_with': lambda a, b: str(a).startswith(b),
        'ends_with': lambda a, b: str(a).endswith(b),
        'matches_regex': lambda a, b: bool(re.search(b, str(a))),
        'is_empty': lambda a: not a,
        'is_not_empty': lambda a: bool(a),
        'in': lambda a, b: a in b,
        'not_in': lambda a, b: a not in b,
    }
    
    def evaluate(self, condition: Dict, context: Dict) -> bool:
        """评估条件"""
        
        condition_type = condition.get('type', 'single')
        
        if condition_type == 'single':
            return self._evaluate_single(condition, context)
        elif condition_type == 'and':
            return self._evaluate_and(condition.get('conditions', []), context)
        elif condition_type == 'or':
            return self._evaluate_or(condition.get('conditions', []), context)
        elif condition_type == 'not':
            return not self._evaluate_single(condition.get('condition'), context)
        elif condition_type == 'expression':
            return self._evaluate_expression(condition.get('expression'), context)
        
        return False
    
    def _evaluate_single(
        self, 
        condition: Dict, 
        context: Dict
    ) -> bool:
        """评估单个条件"""
        
        left_value = self._resolve_value(condition.get('left'), context)
        operator = condition.get('operator', '==')
        right_value = self._resolve_value(condition.get('right'), context)
        
        op_func = self.OPERATORS.get(operator)
        if not op_func:
            raise ValueError(f"Unknown operator: {operator}")
        
        return op_func(left_value, right_value)
    
    def _evaluate_and(
        self, 
        conditions: List[Dict], 
        context: Dict
    ) -> bool:
        """AND 条件"""
        return all(self.evaluate(c, context) for c in conditions)
    
    def _evaluate_or(
        self, 
        conditions: List[Dict], 
        context: Dict
    ) -> bool:
        """OR 条件"""
        return any(self.evaluate(c, context) for c in conditions)
    
    def _evaluate_expression(
        self, 
        expression: str, 
        context: Dict
    ) -> bool:
        """评估表达式"""
        try:
            return bool(eval(expression, {"__builtins__": {}}, context))
        except Exception as e:
            raise ValueError(f"Expression evaluation failed: {e}")
    
    def _resolve_value(self, value: Any, context: Dict) -> Any:
        """解析值（支持变量引用）"""
        if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
            # 变量引用 {{variable.path}}
            var_path = value[2:-2].strip()
            return self._get_nested(context, var_path)
        return value
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result


class SwitchNode:
    """Switch 分支节点（多条件分支）"""
    
    def __init__(self, config: Dict):
        self.switch_field = config.get('switch_field')
        self.cases = config.get('cases', [])
        self.default_case = config.get('default')
    
    def evaluate(self, context: Dict) -> str:
        """评估并返回匹配的分支"""
        
        switch_value = self._resolve_field(self.switch_field, context)
        
        for case in self.cases:
            if self._match_case(switch_value, case):
                return case.get('output')
        
        return self.default_case
    
    def _resolve_field(self, field: str, context: Dict) -> Any:
        """解析字段值"""
        if field.startswith('{{') and field.endswith('}}'):
            var_path = field[2:-2].strip()
            return self._get_nested(context, var_path)
        return field
    
    def _match_case(self, value: Any, case: Dict) -> bool:
        """匹配分支"""
        operation = case.get('operation', 'equals')
        
        if operation == 'equals':
            return value == case.get('value')
        elif operation == 'contains':
            return case.get('value') in str(value)
        elif operation == 'regex':
            return bool(re.search(case.get('value'), str(value)))
        elif operation == 'in':
            return value in case.get('values', [])
        elif operation == 'range':
            min_val = case.get('min')
            max_val = case.get('max')
            return min_val <= value <= max_val
        
        return False
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result
```

### G.2 高级节点类型

#### G.2.1 代码执行节点

```python
# workflow/nodes/code_execution.py

import ast
import json
import python_executor
from typing import Any, Dict
from io import StringIO
import sys


class CodeExecutionNode:
    """代码执行节点 - 支持 JavaScript 和 Python"""
    
    SUPPORTED_LANGUAGES = ['javascript', 'python', 'js']
    
    def __init__(self, config: Dict[str, Any]):
        self.language = config.get('language', 'javascript')
        self.code = config.get('code', '')
        self.timeout = config.get('timeout', 30)  # 秒
        self.memory_limit = config.get('memory_limit', 128)  # MB
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码"""
        
        if self.language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {self.language}")
        
        if self.language in ['javascript', 'js']:
            return self._execute_javascript(context)
        elif self.language == 'python':
            return self._execute_python(context)
    
    def _execute_python(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Python 代码"""
        
        # 准备执行环境
        local_vars = context.copy()
        
        # 重定向输出
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            # 执行代码（带超时）
            # 注意：实际生产环境应使用 subprocess 隔离执行
            exec(self.code, local_vars)
            
            output = captured_output.getvalue()
            
            # 获取所有新定义的变量
            result_vars = {
                k: v for k, v in local_vars.items() 
                if k not in context and not k.startswith('_')
            }
            
            return {
                'success': True,
                'output': output,
                'variables': result_vars,
                'execution_time': 0  # 可添加计时
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output': captured_output.getvalue()
            }
        finally:
            sys.stdout = old_stdout
    
    def _execute_javascript(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 JavaScript 代码"""
        # 使用 py_mini_racer 或 node subprocess
        # 这里使用简化的示例
        pass


class TransformNode:
    """数据转换节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.transformations = config.get('transformations', [])
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据转换"""
        
        result = context.get('input', {})
        
        for transform in self.transformations:
            result = self._apply_transformation(result, transform)
        
        return {'output': result}
    
    def _apply_transformation(
        self, 
        data: Any, 
        transform: Dict
    ) -> Any:
        """应用单个转换"""
        
        transform_type = transform.get('type')
        
        if transform_type == 'rename_keys':
            mapping = transform.get('mapping', {})
            return {mapping.get(k, k): v for k, v in data.items()}
        
        elif transform_type == 'pick':
            keys = transform.get('keys', [])
            return {k: data.get(k) for k in keys if k in data}
        
        elif transform_type == 'omit':
            keys = transform.get('keys', [])
            return {k: v for k, v in data.items() if k not in keys}
        
        elif transform_type == 'map':
            field = transform.get('field')
            mapping = transform.get('mapping', {})
            if field in data:
                data[field] = mapping.get(data[field], data[field])
            return data
        
        elif transform_type == 'filter':
            condition = transform.get('condition')
            # 过滤逻辑
            if isinstance(data, list):
                return [item for item in data if self._check_condition(item, condition)]
            return data
        
        elif transform_type == 'sort':
            field = transform.get('field')
            order = transform.get('order', 'asc')
            reverse = order == 'desc'
            if isinstance(data, list):
                return sorted(data, key=lambda x: x.get(field, ''), reverse=reverse)
            return data
        
        elif transform_type == 'group_by':
            field = transform.get('field')
            grouped = {}
            if isinstance(data, list):
                for item in data:
                    key = item.get(field, 'unknown')
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(item)
            return grouped
        
        return data
    
    def _check_condition(self, item: Dict, condition: Dict) -> bool:
        """检查过滤条件"""
        field = condition.get('field')
        operator = condition.get('operator', '==')
        value = condition.get('value')
        
        item_value = item.get(field)
        
        if operator == '==':
            return item_value == value
        elif operator == '!=':
            return item_value != value
        elif operator == '>':
            return item_value > value
        elif operator == 'contains':
            return value in str(item_value)
        
        return True
```

#### G.2.2 数据库操作节点

```python
# workflow/nodes/database_nodes.py

from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import sqlite3  # 或使用 mysql.connector, psycopg2


class DatabaseNode:
    """数据库操作节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.connection_config = config.get('connection', {})
        self.operation = config.get('operation')  # select, insert, update, delete
        self.table = config.get('table')
        self.query = config.get('query')
        self.params = config.get('params', {})
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        # 根据配置创建对应数据库连接
        conn = sqlite3.connect(self.connection_config.get('database'))
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库操作"""
        
        resolved_params = self._resolve_params(self.params, context)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.operation == 'select':
                return self._execute_select(cursor, context, resolved_params)
            elif self.operation == 'insert':
                return self._execute_insert(cursor, conn, context, resolved_params)
            elif self.operation == 'update':
                return self._execute_update(cursor, conn, context, resolved_params)
            elif self.operation == 'delete':
                return self._execute_delete(cursor, conn, context, resolved_params)
            elif self.operation == 'query':
                return self._execute_raw_query(cursor, context, resolved_params)
    
    def _execute_select(
        self, 
        cursor, 
        context: Dict, 
        params: Dict
    ) -> Dict[str, Any]:
        """执行查询"""
        
        # 构建查询
        query = self.query or f"SELECT * FROM {self.table}"
        
        # 添加 WHERE 条件
        if params.get('conditions'):
            where_clauses = []
            for field, value in params['conditions'].items():
                where_clauses.append(f"{field} = ?")
            query += " WHERE " + " AND ".join(where_clauses)
        
        # 添加 LIMIT
        if params.get('limit'):
            query += f" LIMIT {params['limit']}"
        
        # 执行查询
        values = list(params.get('conditions', {}).values())
        cursor.execute(query, values)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        results = [dict(zip(columns, row)) for row in rows]
        
        return {
            'success': True,
            'rows': results,
            'count': len(results)
        }
    
    def _execute_insert(
        self, 
        cursor, 
        conn, 
        context: Dict, 
        params: Dict
    ) -> Dict[str, Any]:
        """执行插入"""
        
        data = params.get('data', {})
        fields = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['?' for _ in fields])
        
        query = f"INSERT INTO {self.table} ({', '.join(fields)}) VALUES ({placeholders})"
        
        cursor.execute(query, values)
        conn.commit()
        
        return {
            'success': True,
            'inserted_id': cursor.lastrowid,
            'affected_rows': cursor.rowcount
        }
    
    def _execute_update(
        self, 
        cursor, 
        conn, 
        context: Dict, 
        params: Dict
    ) -> Dict[str, Any]:
        """执行更新"""
        
        data = params.get('data', {})
        conditions = params.get('conditions', {})
        
        set_clauses = [f"{k} = ?" for k in data.keys()]
        where_clauses = [f"{k} = ?" for k in conditions.keys()]
        
        query = f"UPDATE {self.table} SET {', '.join(set_clauses)}"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        values = list(data.values()) + list(conditions.values())
        cursor.execute(query, values)
        conn.commit()
        
        return {
            'success': True,
            'affected_rows': cursor.rowcount
        }
    
    def _execute_delete(
        self, 
        cursor, 
        conn, 
        context: Dict, 
        params: Dict
    ) -> Dict[str, Any]:
        """执行删除"""
        
        conditions = params.get('conditions', {})
        where_clauses = [f"{k} = ?" for k in conditions.keys()]
        
        query = f"DELETE FROM {self.table}"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        values = list(conditions.values())
        cursor.execute(query, values)
        conn.commit()
        
        return {
            'success': True,
            'affected_rows': cursor.rowcount
        }
    
    def _resolve_params(
        self, 
        params: Dict, 
        context: Dict
    ) -> Dict:
        """解析参数中的变量引用"""
        
        def resolve_value(value):
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                var_path = value[2:-2].strip()
                return self._get_nested(context, var_path)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            return value
        
        return resolve_value(params.copy())
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result
```

#### G.2.3 HTTP 请求节点（高级）

```python
# workflow/nodes/http_nodes.py

import httpx
from typing import Any, Dict, Optional
from urllib.parse import urljoin


class HTTPRequestNode:
    """高级 HTTP 请求节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get('url')
        self.method = config.get('method', 'GET').upper()
        self.headers = config.get('headers', {})
        self.body = config.get('body')
        self.auth = config.get('auth')  # basic, bearer, api_key
        self.query_params = config.get('query_params', {})
        self.timeout = config.get('timeout', 30)
        self.response_handling = config.get('response_handling', 'json')
        self.retry_config = config.get('retry')
        self.redirect = config.get('follow_redirects', True)
    
    async def execute_async(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """异步执行 HTTP 请求"""
        
        # 解析 URL 和参数
        url = self._resolve_string(self.url, context)
        headers = self._resolve_dict(self.headers, context)
        query_params = self._resolve_dict(self.query_params, context)
        body = self._resolve_body(self.body, context)
        
        # 处理认证
        headers = self._apply_auth(headers)
        
        # 配置客户端
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=self.redirect
        ) as client:
            
            # 构建请求
            request_kwargs = {
                'url': url,
                'headers': headers,
                'params': query_params if query_params else None,
            }
            
            if self.method in ['POST', 'PUT', 'PATCH'] and body:
                request_kwargs['json'] = body
            
            # 发送请求（带重试）
            response = await self._request_with_retry(
                client, 
                self.method, 
                request_kwargs
            )
            
            # 处理响应
            return self._handle_response(response)
    
    def _apply_auth(self, headers: Dict) -> Dict:
        """应用认证信息"""
        
        if not self.auth:
            return headers
        
        auth_type = self.auth.get('type')
        
        if auth_type == 'basic':
            import base64
            credentials = f"{self.auth['username']}:{self.auth['password']}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"
        
        elif auth_type == 'bearer':
            headers['Authorization'] = f"Bearer {self.auth['token']}"
        
        elif auth_type == 'api_key':
            header_name = self.auth.get('header_name', 'X-API-Key')
            headers[header_name] = self.auth['api_key']
        
        return headers
    
    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        kwargs: Dict,
        attempt: int = 0
    ) -> httpx.Response:
        """带重试的请求"""
        
        max_attempts = self.retry_config.get('max_attempts', 3) if self.retry_config else 1
        
        try:
            response = await client.request(method, **kwargs)
            
            # 检查是否需要重试
            if self._should_retry(response) and attempt < max_attempts - 1:
                delay = self._calculate_retry_delay(attempt)
                await asyncio.sleep(delay)
                return await self._request_with_retry(
                    client, method, kwargs, attempt + 1
                )
            
            return response
            
        except httpx.TimeoutException:
            if attempt < max_attempts - 1:
                delay = self._calculate_retry_delay(attempt)
                await asyncio.sleep(delay)
                return await self._request_with_retry(
                    client, method, kwargs, attempt + 1
                )
            raise
    
    def _should_retry(self, response: httpx.Response) -> bool:
        """判断是否应重试"""
        if not self.retry_config:
            return False
        
        retry_on = self.retry_config.get('retry_on_status', [])
        return response.status_code in retry_on
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if not self.retry_config:
            return 1.0
        
        strategy = self.retry_config.get('strategy', 'exponential')
        initial = self.retry_config.get('initial_delay', 1.0)
        max_delay = self.retry_config.get('max_delay', 60.0)
        
        if strategy == 'exponential':
            delay = min(initial * (2 ** attempt), max_delay)
        elif strategy == 'linear':
            delay = min(initial * (attempt + 1), max_delay)
        else:
            delay = initial
        
        # 添加随机抖动
        import random
        delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """处理响应"""
        
        result = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'success': 200 <= response.status_code < 300,
        }
        
        handling = self.response_handling
        
        if handling == 'json':
            try:
                result['data'] = response.json()
            except:
                result['data'] = response.text
        elif handling == 'text':
            result['data'] = response.text
        elif handling == 'binary':
            result['data'] = response.content
        elif handling == 'headers':
            result['data'] = dict(response.headers)
        
        return result
    
    def _resolve_string(self, value: str, context: Dict) -> str:
        """解析字符串中的变量"""
        if not isinstance(value, str):
            return value
        
        import re
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_var(match):
            var_path = match.group(1).strip()
            return str(self._get_nested(context, var_path))
        
        return re.sub(pattern, replace_var, value)
    
    def _resolve_dict(
        self, 
        value: Dict, 
        context: Dict
    ) -> Dict:
        """解析字典中的变量"""
        if not isinstance(value, dict):
            return value
        
        return {
            k: self._resolve_string(v, context) if isinstance(v, str) else v
            for k, v in value.items()
        }
    
    def _resolve_body(
        self, 
        value: Any, 
        context: Dict
    ) -> Any:
        """解析请求体中的变量"""
        if isinstance(value, str):
            return self._resolve_string(value, context)
        elif isinstance(value, dict):
            return self._resolve_dict(value, context)
        elif isinstance(value, list):
            return [self._resolve_body(v, context) for v in value]
        return value
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result
```

### G.3 AI 增强功能

#### G.3.1 函数调用（Function Calling）

```python
# workflow/nodes/function_call.py

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
import json


@dataclass
class FunctionDefinition:
    """函数定义"""
    name: str
    description: str
    parameters: Dict  # JSON Schema 格式


class FunctionCallNode:
    """函数调用节点 - 支持 OpenAI Function Calling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.functions = self._parse_functions(config.get('functions', []))
        self.function_handler = config.get('function_handler')  # 函数处理映射
        self.strict_mode = config.get('strict_mode', False)
    
    def _parse_functions(self, functions: List[Dict]) -> List[FunctionDefinition]:
        """解析函数定义"""
        return [
            FunctionDefinition(
                name=f['name'],
                description=f.get('description', ''),
                parameters=f.get('parameters', {})
            )
            for f in functions
        ]
    
    async def execute(
        self, 
        context: Dict[str, Any],
        llm_client: Any  # LangChain LLM 或 OpenAI client
    ) -> Dict[str, Any]:
        """执行函数调用"""
        
        messages = context.get('messages', [])
        system_prompt = context.get('system_prompt', '')
        
        # 构建请求
        response = await self._call_llm_with_functions(
            messages, 
            system_prompt,
            llm_client
        )
        
        # 处理响应
        if response.choices[0].message.function_call:
            return await self._handle_function_call(
                response.choices[0].message,
                context
            )
        
        return {
            'success': True,
            'output': response.choices[0].message.content
        }
    
    async def _call_llm_with_functions(
        self,
        messages: List[Dict],
        system_prompt: str,
        llm_client: Any
    ) -> Any:
        """调用 LLM 并附带函数定义"""
        
        # 构建消息
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        formatted_messages.extend(messages)
        
        # 调用 OpenAI
        response = await llm_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=formatted_messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": f.name,
                        "description": f.description,
                        "parameters": f.parameters
                    }
                }
                for f in self.functions
            ],
            tool_choice="auto"
        )
        
        return response
    
    async def _handle_function_call(
        self,
        message: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理函数调用"""
        
        function_call = message.function_call
        function_name = function_call.name
        arguments = json.loads(function_call.arguments)
        
        # 查找函数处理器
        handler = self.function_handler.get(function_name)
        
        if not handler:
            return {
                'success': False,
                'error': f'Unknown function: {function_name}'
            }
        
        try:
            # 执行函数
            result = await handler(arguments, context)
            
            return {
                'success': True,
                'function_called': function_name,
                'arguments': arguments,
                'function_result': result,
                'output': result.get('output')
            }
            
        except Exception as e:
            return {
                'success': False,
                'function_called': function_name,
                'error': str(e)
            }


# 内置函数示例
class BuiltinFunctions:
    """内置函数库"""
    
    @staticmethod
    async def get_current_weather(
        arguments: Dict,
        context: Dict
    ) -> Dict:
        """获取天气"""
        location = arguments.get('location')
        unit = arguments.get('unit', 'celsius')
        
        # 调用天气 API
        # return {"temperature": 22, "condition": "sunny"}
        pass
    
    @staticmethod
    async def search_database(
        arguments: Dict,
        context: Dict
    ) -> Dict:
        """搜索数据库"""
        query = arguments.get('query')
        table = arguments.get('table')
        
        # 执行数据库查询
        # return {"results": [...]}
        pass
    
    @staticmethod
    async def send_notification(
        arguments: Dict,
        context: Dict
    ) -> Dict:
        """发送通知"""
        channel = arguments.get('channel')
        message = arguments.get('message')
        
        # 发送通知
        # return {"sent": True}
        pass
```

#### G.3.2 多模态支持

```python
# workflow/nodes/multimodal_nodes.py

from typing import Any, Dict, List, Union, Optional
import base64
import httpx
from io import BytesIO


class ImageGenerationNode:
    """图像生成节点 - DALL-E, Stable Diffusion"""
    
    SUPPORTED_PROVIDERS = ['openai_dalle', 'stability_ai', 'midjourney']
    
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get('provider', 'openai_dalle')
        self.prompt = config.get('prompt')
        self.model = config.get('model', 'dall-e-3')
        self.size = config.get('size', '1024x1024')
        self.quality = config.get('quality', 'standard')  # standard, hd
        self.style = config.get('style', 'vivid')  # vivid, natural
        self.output_format = config.get('output_format', 'url')  # url, base64
    
    async def execute(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行图像生成"""
        
        prompt = self._resolve_string(self.prompt, context)
        
        if self.provider == 'openai_dalle':
            return await self._generate_with_dalle(prompt, context)
        elif self.provider == 'stability_ai':
            return await self._generate_with_stability(prompt, context)
    
    async def _generate_with_dalle(
        self, 
        prompt: str,
        context: Dict
    ) -> Dict[str, Any]:
        """使用 DALL-E 生成图像"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {context.get('openai_api_key')}"
                },
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "n": 1,
                    "size": self.size,
                    "quality": self.quality,
                    "style": self.style
                }
            )
            
            result = response.json()
            
            if self.output_format == 'base64':
                # 下载并转为 base64
                image_url = result['data'][0]['url']
                image_data = await self._download_image(image_url)
                return {
                    'success': True,
                    'image_base64': base64.b64encode(image_data).decode(),
                    'prompt': prompt
                }
            
            return {
                'success': True,
                'image_url': result['data'][0]['url'],
                'revised_prompt': result['data'][0].get('revised_prompt'),
                'prompt': prompt
            }
    
    async def _download_image(self, url: str) -> bytes:
        """下载图像"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.content


class ImageUnderstandingNode:
    """图像理解节点 - GPT-4V"""
    
    def __init__(self, config: Dict[str, Any]):
        self.image_source = config.get('image_source')  # url, base64, file_path
        self.prompt = config.get('prompt', '描述这张图片')
        self.detail_level = config.get('detail_level', 'auto')  # low, high, auto
    
    async def execute(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行图像理解"""
        
        # 获取图像数据
        image_data = await self._get_image_data(context)
        prompt = self._resolve_string(self.prompt, context)
        
        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data,
                            "detail": self.detail_level
                        }
                    }
                ]
            }
        ]
        
        # 调用 GPT-4V
        # response = await llm.chat.completions.create(
        #     model="gpt-4-vision-preview",
        #     messages=messages
        # )
        
        return {
            'success': True,
            'description': 'Image description would appear here',
            'image_source': self.image_source
        }
    
    async def _get_image_data(self, context: Dict) -> str:
        """获取图像数据"""
        
        if self.image_source.startswith('http'):
            return self.image_source
        elif self.image_source.startswith('data:'):
            return self.image_source
        else:
            # 本地文件路径，转换为 base64
            import os
            with open(self.image_source, 'rb') as f:
                image_bytes = f.read()
            mime_type = self._get_mime_type(self.image_source)
            return f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
    
    def _get_mime_type(self, path: str) -> str:
        """获取 MIME 类型"""
        ext = os.path.splitext(path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/png')
    
    def _resolve_string(self, value: str, context: Dict) -> str:
        """解析变量"""
        if not isinstance(value, str):
            return value
        
        import re
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_var(match):
            var_path = match.group(1).strip()
            return str(self._get_nested(context, var_path))
        
        return re.sub(pattern, replace_var, value)
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result


class AudioTranscriptionNode:
    """音频转录节点 - Whisper"""
    
    SUPPORTED_FORMATS = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
    
    def __init__(self, config: Dict[str, Any]):
        self.audio_source = config.get('audio_source')
        self.model = config.get('model', 'whisper-1')
        self.language = config.get('language')  # 可选，指定语言
        self.prompt = config.get('prompt')  # 可选，引导转录
        self.response_format = config.get('response_format', 'json')
    
    async def execute(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行音频转录"""
        
        audio_data = await self._get_audio_data(context)
        
        # 调用 Whisper API
        # response = await openai.audio.transcriptions.create(
        #     model=self.model,
        #     file=audio_data,
        #     language=self.language,
        #     prompt=self.prompt,
        #     response_format=self.response_format
        # )
        
        return {
            'success': True,
            'text': 'Transcribed text would appear here',
            'language': self.language or 'detected'
        }
    
    async def _get_audio_data(self, context: Dict) -> BytesIO:
        """获取音频数据"""
        pass
```

#### G.3.3 向量存储与检索

```python
# workflow/nodes/vector_nodes.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class Document:
    """文档"""
    id: str
    content: str
    metadata: Dict[str, Any]


class EmbeddingNode:
    """文本嵌入节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.model = config.get('model', 'text-embedding-3-small')
        self.batch_size = config.get('batch_size', 100)
    
    async def execute(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行文本嵌入"""
        
        texts = context.get('texts', [])
        
        if not texts:
            text = context.get('text')
            if text:
                texts = [text]
        
        # 批量处理
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            embeddings = await self._embed_batch(batch)
            all_embeddings.extend(embeddings)
        
        return {
            'success': True,
            'embeddings': all_embeddings,
            'count': len(all_embeddings),
            'model': self.model
        }
    
    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入"""
        # 调用 OpenAI Embeddings API
        # response = await openai.embeddings.create(
        #     model=self.model,
        #     input=texts
        # )
        return [[0.0] * 1536 for _ in texts]  # 占位


class VectorStoreNode:
    """向量存储节点"""
    
    SUPPORTED_STORES = ['qdrant', 'milvus', 'pinecone', 'chroma', 'weaviate']
    
    def __init__(self, config: Dict[str, Any]):
        self.store_type = config.get('store_type', 'qdrant')
        self.collection_name = config.get('collection_name', 'documents')
        self.embedding_field = config.get('embedding_field', 'embedding')
        self.content_field = config.get('content_field', 'content')
        self.metadata_fields = config.get('metadata_fields', [])
    
    async def execute(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行向量存储"""
        
        documents = context.get('documents', [])
        embeddings = context.get('embeddings', [])
        
        # 构建向量文档
        vectors = []
        for i, doc in enumerate(documents):
            vector = {
                'id': self._generate_id(doc),
                'vector': embeddings[i] if i < len(embeddings) else None,
                'payload': self._extract_payload(doc)
            }
            vectors.append(vector)
        
        # 存储到向量数据库
        if self.store_type == 'qdrant':
            return await self._store_qdrant(vectors)
        elif self.store_type == 'chroma':
            return await self._store_chroma(vectors)
    
    def _generate_id(self, doc: Any) -> str:
        """生成文档 ID"""
        content = doc.get(self.content_field, str(doc))
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_payload(self, doc: Any) -> Dict:
        """提取元数据"""
        payload = {}
        payload['content'] = doc.get(self.content_field, '')
        
        for field in self.metadata_fields:
            payload[field] = doc.get(field)
        
        return payload
    
    async def _store_qdrant(self, vectors: List[Dict]) -> Dict:
        """存储到 Qdrant"""
        # qdrant_client = QdrantClient(...)
        # qdrant_client.upsert(
        #     collection_name=self.collection_name,
        #     points=vectors
        # )
        return {'success': True, 'stored': len(vectors)}


class VectorSearchNode:
    """向量检索节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.query = config.get('query')
        self.collection_name = config.get('collection_name', 'documents')
        self.top_k = config.get('top_k', 5)
        self.similarity_threshold = config.get('similarity_threshold', 0.7)
        self.filter = config.get('filter')  # 元数据过滤
    
    async def execute(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行向量检索"""
        
        query = self._resolve_string(self.query, context)
        
        # 生成查询向量
        query_embedding = await self._embed_query(query)
        
        # 执行检索
        results = await self._search_similar(
            query_embedding,
            self.top_k,
            self.filter
        )
        
        # 过滤低相似度结果
        filtered_results = [
            r for r in results 
            if r['score'] >= self.similarity_threshold
        ]
        
        return {
            'success': True,
            'query': query,
            'results': filtered_results,
            'count': len(filtered_results)
        }
    
    async def _embed_query(self, query: str) -> List[float]:
        """嵌入查询"""
        # 调用嵌入 API
        return [0.0] * 1536
    
    async def _search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_conditions: Optional[Dict]
    ) -> List[Dict]:
        """搜索相似向量"""
        # 实现向量搜索逻辑
        return []


class RAGNode:
    """RAG (检索增强生成) 节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.query = config.get('query')
        self.collection_name = config.get('collection_name', 'documents')
        self.system_prompt = config.get('system_prompt')
        self.top_k = config.get('top_k', 5)
        self.include_sources = config.get('include_sources', True)
    
    async def execute(
        self, 
        context: Dict[str, Any],
        llm_client: Any
    ) -> Dict[str, Any]:
        """执行 RAG"""
        
        query = self._resolve_string(self.query, context)
        
        # 1. 检索相关文档
        search_node = VectorSearchNode({
            'query': query,
            'collection_name': self.collection_name,
            'top_k': self.top_k
        })
        search_results = await search_node.execute(context)
        
        # 2. 构建上下文
        context_text = self._build_context(search_results['results'])
        
        # 3. 构建提示词
        system_prompt = self.system_prompt or (
            "你是一个有用的助手。根据提供的上下文信息回答问题。"
            "如果上下文中没有相关信息，请如实告知。"
        )
        
        user_prompt = f"上下文信息:\n{context_text}\n\n问题: {query}"
        
        # 4. 调用 LLM
        response = await llm_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        result = {
            'success': True,
            'answer': response.choices[0].message.content,
            'sources_used': len(search_results['results'])
        }
        
        if self.include_sources:
            result['sources'] = [
                {'content': r['payload']['content'][:200], 'score': r['score']}
                for r in search_results['results']
            ]
        
        return result
    
    def _build_context(self, results: List[Dict]) -> str:
        """构建上下文"""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            content = result.get('payload', {}).get('content', '')
            source = result.get('payload', {}).get('source', 'unknown')
            context_parts.append(f"[文档 {i}] 来源: {source}\n{content}")
        
        return '\n\n'.join(context_parts)
    
    def _resolve_string(self, value: str, context: Dict) -> str:
        """解析变量"""
        if not isinstance(value, str):
            return value
        
        import re
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_var(match):
            var_path = match.group(1).strip()
            return str(self._get_nested(context, var_path))
        
        return re.sub(pattern, replace_var, value)
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result
```

### G.4 工作流模板与市场

#### G.4.1 模板系统

```python
# workflow/templates/template_system.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class TemplateCategory(Enum):
    AI_CHAT = "ai_chat"                    # AI 对话
    CONTENT_GENERATION = "content"         # 内容生成
    DATA_PROCESSING = "data"               # 数据处理
    AUTOMATION = "automation"               # 自动化
    INTEGRATION = "integration"             # 集成
    PRODUCTIVITY = "productivity"           # 效率工具


@dataclass
class TemplateVariable:
    """模板变量定义"""
    name: str
    type: str                              # string, number, boolean, select
    label: str
    description: str = ""
    required: bool = True
    default: Any = None
    options: List[str] = field(default_factory=list)  # select 类型选项


@dataclass
class WorkflowTemplate:
    """工作流模板"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    tags: List[str]
    author: str
    version: str
    variables: List[TemplateVariable]
    workflow_data: Dict  # 模板工作流数据
    thumbnail: Optional[str] = None
    popularity: int = 0
    usage_count: int = 0
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps({
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'tags': self.tags,
            'author': self.author,
            'version': self.version,
            'variables': [
                {
                    'name': v.name,
                    'type': v.type,
                    'label': v.label,
                    'description': v.description,
                    'required': v.required,
                    'default': v.default,
                    'options': v.options
                }
                for v in self.variables
            ],
            'workflow_data': self.workflow_data
        }, ensure_ascii=False)


class TemplateEngine:
    """模板引擎"""
    
    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}
    
    def register_template(self, template: WorkflowTemplate):
        """注册模板"""
        self.templates[template.id] = template
    
    def create_from_template(
        self,
        template_id: str,
        variable_values: Dict[str, Any],
        owner_id: int
    ) -> Dict[str, Any]:
        """从模板创建工作流"""
        
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # 验证必填变量
        self._validate_variables(template, variable_values)
        
        # 应用变量到模板
        workflow_data = self._apply_variables(
            template.workflow_data,
            template.variables,
            variable_values
        )
        
        # 创建工作流
        return {
            'name': self._apply_string_variables(
                template.name,
                variable_values
            ),
            'description': self._apply_string_variables(
                template.description,
                variable_values
            ),
            'owner_id': owner_id,
            'nodes': workflow_data.get('nodes', []),
            'edges': workflow_data.get('edges', []),
            'from_template': template_id,
            'template_version': template.version
        }
    
    def _validate_variables(
        self,
        template: WorkflowTemplate,
        values: Dict[str, Any]
    ):
        """验证变量"""
        for var in template.variables:
            if var.required and var.name not in values:
                raise ValueError(f"Required variable missing: {var.name}")
            
            if var.name in values:
                value = values[var.name]
                if var.type == 'select' and value not in var.options:
                    raise ValueError(
                        f"Invalid value for {var.name}: {value}. "
                        f"Must be one of: {var.options}"
                    )
    
    def _apply_variables(
        self,
        workflow_data: Dict,
        variables: List[TemplateVariable],
        values: Dict[str, Any]
    ) -> Dict:
        """应用变量到工作流数据"""
        
        # 深拷贝避免修改原模板
        import copy
        result = copy.deepcopy(workflow_data)
        
        # 替换节点配置中的变量
        for node in result.get('nodes', []):
            if 'config' in node:
                for key, value in node['config'].items():
                    if isinstance(value, str):
                        node['config'][key] = self._apply_string_variables(
                            value, values
                        )
        
        return result
    
    def _apply_string_variables(
        self,
        text: str,
        values: Dict[str, Any]
    ) -> str:
        """替换文本中的变量占位符"""
        import re
        
        pattern = r'\{\{(\w+)\}\}'
        
        def replace_var(match):
            var_name = match.group(1)
            value = values.get(var_name)
            return str(value) if value is not None else match.group(0)
        
        return re.sub(pattern, replace_var, text)


# 预置模板示例
PRESET_TEMPLATES = [
    WorkflowTemplate(
        id="ai-chatbot",
        name="AI 客服机器人",
        description="基于知识库的 AI 客服对话工作流",
        category=TemplateCategory.AI_CHAT,
        tags=["AI", "客服", "RAG"],
        author="Flowly Team",
        version="1.0.0",
        variables=[
            TemplateVariable(
                name="knowledge_base_id",
                type="select",
                label="知识库",
                description="选择使用的知识库",
                required=True,
                options=["product_docs", "faq", "manual"]
            ),
            TemplateVariable(
                name="welcome_message",
                type="string",
                label="欢迎消息",
                description="用户首次咨询时的欢迎语",
                required=True,
                default="您好，请问有什么可以帮助您的？"
            )
        ],
        workflow_data={
            "nodes": [
                {"type": "start", "name": "开始", "config": {}},
                {"type": "input", "name": "接收问题", "config": {"variable": "user_input"}},
                {"type": "rag", "name": "知识检索", "config": {"collection": "{{knowledge_base_id}}"}},
                {"type": "llm", "name": "生成回答", "config": {"prompt": "基于上下文回答..."}},
                {"type": "output", "name": "返回答案", "config": {}}
            ],
            "edges": [
                {"source": "start", "target": "input"},
                {"source": "input", "target": "rag"},
                {"source": "rag", "target": "llm"},
                {"source": "llm", "target": "output"}
            ]
        }
    ),
    WorkflowTemplate(
        id="content-rewriter",
        name="内容改写助手",
        description="将文章内容改写为不同风格或长度",
        category=TemplateCategory.CONTENT_GENERATION,
        tags=["AI", "内容", "改写"],
        author="Flowly Team",
        version="1.0.0",
        variables=[
            TemplateVariable(
                name="style",
                type="select",
                label="目标风格",
                required=True,
                default="professional",
                options=["professional", "casual", "creative", "technical"]
            ),
            TemplateVariable(
                name="target_length",
                type="select",
                label="目标长度",
                required=True,
                default="similar",
                options=["shorter", "similar", "longer", "detailed"]
            )
        ],
        workflow_data={
            "nodes": [
                {"type": "start", "name": "开始"},
                {"type": "input", "name": "输入内容"},
                {"type": "llm", "name": "改写", "config": {
                    "prompt": "将以下内容改写成{{style}}风格，长度{{target_length}}..."
                }},
                {"type": "output", "name": "输出结果"}
            ],
            "edges": [
                {"source": "start", "target": "input"},
                {"source": "input", "target": "llm"},
                {"source": "llm", "target": "output"}
            ]
        }
    )
]
```

### G.5 高级监控与可观测性

#### G.5.1 执行追踪系统

```python
# workflow/monitoring/tracing.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import uuid
import json


@dataclass
class Span:
    """追踪跨度"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"  # ok, error
    error_message: Optional[str] = None
    events: List[Dict] = field(default_factory=list)


@dataclass
class Trace:
    """追踪记录"""
    trace_id: str
    workflow_id: str
    execution_id: str
    user_id: Optional[int]
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    spans: List[Span] = field(default_factory=list)
    duration_ms: Optional[int] = None
    input_data: Dict = field(default_factory=dict)
    output_data: Dict = field(default_factory=dict)
    error: Optional[str] = None


class TracingService:
    """追踪服务"""
    
    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.spans: Dict[str, Span] = {}
    
    def start_trace(
        self,
        workflow_id: str,
        execution_id: str,
        user_id: Optional[int] = None,
        input_data: Optional[Dict] = None
    ) -> str:
        """启动追踪"""
        trace_id = str(uuid.uuid4())
        
        trace = Trace(
            trace_id=trace_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            user_id=user_id,
            start_time=datetime.utcnow(),
            input_data=input_data or {}
        )
        
        self.traces[trace_id] = trace
        return trace_id
    
    def start_span(
        self,
        trace_id: str,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict] = None
    ) -> str:
        """开始跨度"""
        span_id = str(uuid.uuid4())
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            attributes=attributes or {}
        )
        
        self.spans[span_id] = span
        
        # 添加到 trace
        if trace_id in self.traces:
            self.traces[trace_id].spans.append(span)
        
        return span_id
    
    def end_span(
        self,
        span_id: str,
        status: str = "ok",
        error_message: Optional[str] = None,
        attributes: Optional[Dict] = None
    ):
        """结束跨度"""
        
        span = self.spans.get(span_id)
        if not span:
            return
        
        span.end_time = time.time()
        span.status = status
        span.error_message = error_message
        
        if attributes:
            span.attributes.update(attributes)
    
    def add_span_event(
        self,
        span_id: str,
        event_name: str,
        attributes: Optional[Dict] = None
    ):
        """添加跨度事件"""
        
        span = self.spans.get(span_id)
        if span:
            span.events.append({
                'name': event_name,
                'timestamp': time.time(),
                'attributes': attributes or {}
            })
    
    def end_trace(
        self,
        trace_id: str,
        status: str,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """结束追踪"""
        
        trace = self.traces.get(trace_id)
        if not trace:
            return
        
        trace.end_time = datetime.utcnow()
        trace.status = status
        trace.output_data = output_data or {}
        trace.error = error
        
        # 计算总时长
        if trace.spans:
            first_span = min(trace.spans, key=lambda s: s.start_time)
            last_span = max(trace.spans, key=lambda s: s.end_time or time.time())
            trace.duration_ms = int((last_span.end_time - first_span.start_time) * 1000)
        else:
            trace.duration_ms = int((trace.end_time - trace.start_time).total_seconds() * 1000)
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪"""
        return self.traces.get(trace_id)
    
    def get_execution_traces(
        self,
        execution_id: str
    ) -> List[Trace]:
        """获取执行的所有追踪"""
        return [
            t for t in self.traces.values()
            if t.execution_id == execution_id
        ]


# 使用示例
class TracedWorkflowExecutor:
    """带追踪的工作流执行器"""
    
    def __init__(self):
        self.tracing = TracingService()
    
    async def execute_with_trace(
        self,
        workflow_id: str,
        execution_id: str,
        input_data: Dict
    ) -> Dict:
        """带追踪的执行"""
        
        # 启动追踪
        trace_id = self.tracing.start_trace(
            workflow_id=workflow_id,
            execution_id=execution_id,
            input_data=input_data
        )
        
        try:
            # 执行工作流（带追踪）
            result = await self._execute_workflow(trace_id, input_data)
            
            self.tracing.end_trace(trace_id, "completed", result)
            return result
            
        except Exception as e:
            self.tracing.end_trace(trace_id, "failed", error=str(e))
            raise
    
    async def _execute_workflow(
        self,
        trace_id: str,
        input_data: Dict
    ) -> Dict:
        """执行工作流（带追踪）"""
        
        # 开始工作流跨度
        span_id = self.tracing.start_span(
            trace_id=trace_id,
            operation_name="workflow.execute",
            attributes={'input_size': len(str(input_data))}
        )
        
        try:
            # 执行节点
            for node in self.workflow.nodes:
                node_span = self.tracing.start_span(
                    trace_id=trace_id,
                    operation_name=f"node.{node.type}",
                    parent_span_id=span_id,
                    attributes={
                        'node_id': str(node.id),
                        'node_type': node.type
                    }
                )
                
                try:
                    result = await self._execute_node(node, input_data)
                    self.tracing.end_span(node_span, "ok")
                except Exception as e:
                    self.tracing.end_span(node_span, "error", str(e))
                    raise
                
                input_data = result
            
            self.tracing.end_span(span_id, "ok")
            return input_data
            
        except Exception as e:
            self.tracing.end_span(span_id, "error", str(e))
            raise
```

#### G.5.2 性能指标收集

```python
# workflow/monitoring/metrics.py

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import time


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.metrics: List[MetricPoint] = []
    
    def increment_counter(
        self,
        name: str,
        value: float = 1,
        tags: Optional[Dict] = None
    ):
        """递增计数器"""
        key = self._make_key(name, tags)
        self.counters[key] += value
        
        self.metrics.append(MetricPoint(
            name=name,
            value=self.counters[key],
            timestamp=datetime.utcnow(),
            tags=tags or {}
        ))
    
    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict] = None
    ):
        """设置仪表值"""
        key = self._make_key(name, tags)
        self.gauges[key] = value
        
        self.metrics.append(MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        ))
    
    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict] = None
    ):
        """记录直方图"""
        key = self._make_key(name, tags)
        self.histograms[key].append(value)
        
        self.metrics.append(MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        ))
    
    def _make_key(self, name: str, tags: Optional[Dict]) -> str:
        """生成指标键"""
        if not tags:
            return name
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"
    
    def get_stats(self, name: str, tags: Optional[Dict] = None) -> Dict:
        """获取统计信息"""
        key = self._make_key(name, tags)
        
        values = self.histograms.get(key, [])
        if not values:
            return {}
        
        sorted_values = sorted(values)
        
        return {
            'count': len(values),
            'sum': sum(values),
            'mean': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'p50': sorted_values[len(values) // 2],
            'p95': sorted_values[int(len(values) * 0.95)],
            'p99': sorted_values[int(len(values) * 0.99)]
        }


# 工作流性能指标
class WorkflowMetrics:
    """工作流性能指标"""
    
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
    
    def record_execution_start(
        self,
        workflow_id: str,
        execution_id: str
    ):
        """记录执行开始"""
        self.metrics.increment_counter(
            'workflow.executions.started',
            tags={'workflow_id': workflow_id}
        )
    
    def record_execution_complete(
        self,
        workflow_id: str,
        execution_id: str,
        duration_ms: float,
        status: str  # success, failed
    ):
        """记录执行完成"""
        self.metrics.increment_counter(
            'workflow.executions.completed',
            tags={
                'workflow_id': workflow_id,
                'status': status
            }
        )
        
        self.metrics.record_histogram(
            'workflow.execution.duration',
            duration_ms,
            tags={
                'workflow_id': workflow_id,
                'status': status
            }
        )
    
    def record_node_execution(
        self,
        workflow_id: str,
        node_type: str,
        duration_ms: float
    ):
        """记录节点执行"""
        self.metrics.record_histogram(
            'workflow.node.execution.duration',
            duration_ms,
            tags={
                'workflow_id': workflow_id,
                'node_type': node_type
            }
        )
        
        self.metrics.increment_counter(
            'workflow.node.executions.total',
            tags={
                'workflow_id': workflow_id,
                'node_type': node_type
            }
        )
    
    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float
    ):
        """记录 API 请求"""
        self.metrics.record_histogram(
            'api.request.duration',
            duration_ms,
            tags={
                'endpoint': endpoint,
                'method': method,
                'status_code': str(status_code)
            }
        )
        
        self.metrics.increment_counter(
            'api.requests.total',
            tags={
                'endpoint': endpoint,
                'method': method,
                'status_code': str(status_code)
            }
        )
    
    def record_llm_tokens(
        self,
        workflow_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ):
        """记录 LLM Token 使用"""
        self.metrics.increment_counter(
            'llm.tokens.used',
            prompt_tokens + completion_tokens,
            tags={
                'workflow_id': workflow_id,
                'model': model,
                'type': 'prompt'
            }
        )
        
        self.metrics.increment_counter(
            'llm.tokens.used',
            completion_tokens,
            tags={
                'workflow_id': workflow_id,
                'model': model,
                'type': 'completion'
            }
        )
```

### G.6 可扩展性架构

#### G.6.1 分布式执行

```python
# workflow/execution/distributed_executor.py

import asyncio
import redis.asyncio as redis
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json
import hashlib


@dataclass
class Task:
    """执行任务"""
    task_id: str
    workflow_id: str
    execution_id: str
    node_id: str
    node_data: Dict
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)


class DistributedExecutor:
    """分布式工作流执行器"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.task_queue = "workflow:tasks:pending"
        self.results_key = "workflow:results"
        self.worker_id = str(uuid.uuid4())
    
    async def submit_task(self, task: Task):
        """提交任务"""
        task_data = {
            'task_id': task.task_id,
            'workflow_id': task.workflow_id,
            'execution_id': task.execution_id,
            'node_id': task.node_id,
            'node_data': task.node_data,
            'priority': task.priority,
            'dependencies': task.dependencies,
            'submitted_at': datetime.utcnow().isoformat()
        }
        
        # 使用 Redis Sorted Set 实现优先级队列
        await self.redis.zadd(
            self.task_queue,
            {json.dumps(task_data): -task.priority}  # 负数实现最大优先
        )
    
    async def claim_task(self, worker_timeout: int = 30) -> Optional[Task]:
        """认领任务"""
        
        # 使用 BRPOPLPUSH 实现原子性任务认领
        task_data = await self.redis.brpoplpush(
            self.task_queue,
            f"workflow:tasks:processing:{self.worker_id}",
            timeout=worker_timeout
        )
        
        if task_data:
            data = json.loads(task_data)
            return Task(
                task_id=data['task_id'],
                workflow_id=data['workflow_id'],
                execution_id=data['execution_id'],
                node_id=data['node_id'],
                node_data=data['node_data'],
                priority=data['priority']
            )
        
        return None
    
    async def complete_task(
        self, 
        task: Task, 
        result: Any
    ):
        """完成任务"""
        
        # 存储结果
        result_key = f"{self.results_key}:{task.task_id}"
        await self.redis.set(
            result_key,
            json.dumps({
                'task_id': task.task_id,
                'result': result,
                'completed_at': datetime.utcnow().isoformat(),
                'worker_id': self.worker_id
            }),
            ex=86400  # 24小时过期
        )
        
        # 从处理中队列移除
        await self.redis.lrem(
            f"workflow:tasks:processing:{self.worker_id}",
            1,
            json.dumps({
                'task_id': task.task_id,
                'workflow_id': task.workflow_id,
                'execution_id': task.execution_id,
                'node_id': task.node_id,
                'node_data': task.node_data,
                'priority': task.priority,
                'dependencies': task.dependencies
            })
        )
        
        # 检查并调度依赖任务
        await self._check_dependent_tasks(task)
    
    async def fail_task(
        self,
        task: Task,
        error: str
    ):
        """任务失败"""
        
        # 记录失败
        await self.redis.lrem(
            f"workflow:tasks:processing:{self.worker_id}",
            1,
            json.dumps({
                'task_id': task.task_id,
                'workflow_id': task.workflow_id,
                'execution_id': task.execution_id,
                'node_id': task.node_id,
                'node_data': task.node_data,
                'priority': task.priority,
                'dependencies': task.dependencies
            })
        )
        
        # 存储错误
        result_key = f"{self.results_key}:{task.task_id}"
        await self.redis.set(
            result_key,
            json.dumps({
                'task_id': task.task_id,
                'error': error,
                'failed_at': datetime.utcnow().isoformat(),
                'worker_id': self.worker_id
            }),
            ex=86400
        )
    
    async def _check_dependent_tasks(self, completed_task: Task):
        """检查依赖任务"""
        
        # 查找以该任务为依赖的其他任务
        pattern = f"{self.results_key}:*"
        
        async for key in self.redis.scan_iter(match=pattern):
            result_data = await self.redis.get(key)
            if result_data:
                result = json.loads(result_data)
                # 检查依赖是否都已完成
                # 如果是，重新提交任务
                pass
    
    async def get_result(self, task_id: str) -> Optional[Dict]:
        """获取任务结果"""
        result_key = f"{self.results_key}:{task_id}"
        result_data = await self.redis.get(result_key)
        
        if result_data:
            return json.loads(result_data)
        return None
```

#### G.6.2 水平扩展策略

```python
# workflow/scaling/auto_scaler.py

import psutil
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ScalingConfig:
    """扩缩容配置"""
    min_workers: int = 1
    max_workers: int = 10
    target_cpu_percent: float = 70.0
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 30.0
    scale_up_cooldown: int = 300  # 秒
    scale_down_cooldown: int = 600  # 秒
    queue_threshold: int = 100  # 队列长度阈值


@dataclass
class WorkerStats:
    """Worker 统计"""
    worker_id: str
    cpu_percent: float
    memory_percent: float
    active_tasks: int
    completed_tasks: int
    last_heartbeat: datetime


class AutoScaler:
    """自动扩缩容器"""
    
    def __init__(self, config: ScalingConfig):
        self.config = config
        self.workers: Dict[str, WorkerStats] = {}
        self.last_scale_up = datetime.utcnow()
        self.last_scale_down = datetime.utcnow()
        self.is_running = False
    
    async def start(self):
        """启动自动扩缩容"""
        self.is_running = True
        
        while self.is_running:
            try:
                await self._check_and_scale()
            except Exception as e:
                print(f"Scaling check failed: {e}")
            
            await asyncio.sleep(30)  # 每30秒检查一次
    
    async def stop(self):
        """停止自动扩缩容"""
        self.is_running = False
    
    async def _check_and_scale(self):
        """检查并执行扩缩容"""
        
        # 收集 Worker 统计
        await self._collect_worker_stats()
        
        # 计算总体指标
        total_cpu = sum(w.cpu_percent for w in self.workers.values())
        avg_cpu = total_cpu / len(self.workers) if self.workers else 0
        
        total_tasks = sum(w.active_tasks for w in self.workers.values())
        queue_length = await self._get_queue_length()
        
        # 扩容决策
        if self._should_scale_up(avg_cpu, queue_length):
            await self._scale_up()
        elif self._should_scale_down(avg_cpu, queue_length):
            await self._scale_down()
    
    def _should_scale_up(
        self,
        avg_cpu: float,
        queue_length: int
    ) -> bool:
        """判断是否应扩容"""
        
        if len(self.workers) >= self.config.max_workers:
            return False
        
        # 检查冷却时间
        time_since_last = (datetime.utcnow() - self.last_scale_up).total_seconds()
        if time_since_last < self.config.scale_up_cooldown:
            return False
        
        # 条件：CPU 高或队列长
        return (
            avg_cpu > self.config.scale_up_threshold or
            queue_length > self.config.queue_threshold
        )
    
    def _should_scale_down(
        self,
        avg_cpu: float,
        queue_length: int
    ) -> bool:
        """判断是否应缩容"""
        
        if len(self.workers) <= self.config.min_workers:
            return False
        
        # 检查冷却时间
        time_since_last = (datetime.utcnow() - self.last_scale_down).total_seconds()
        if time_since_last < self.config.scale_down_cooldown:
            return False
        
        # 条件：CPU 低且队列空
        return (
            avg_cpu < self.config.scale_down_threshold and
            queue_length == 0
        )
    
    async def _scale_up(self):
        """执行扩容"""
        new_worker_id = f"worker-{len(self.workers) + 1}"
        
        # 启动新 Worker
        # await self._start_worker(new_worker_id)
        
        self.workers[new_worker_id] = WorkerStats(
            worker_id=new_worker_id,
            cpu_percent=0,
            memory_percent=0,
            active_tasks=0,
            completed_tasks=0,
            last_heartbeat=datetime.utcnow()
        )
        
        self.last_scale_up = datetime.utcnow()
        print(f"Scaled up: Added worker {new_worker_id}")
    
    async def _scale_down(self):
        """执行缩容"""
        
        # 找到最空闲的 Worker
        idle_workers = [
            w for w in self.workers.values()
            if w.active_tasks == 0
        ]
        
        if not idle_workers:
            return
        
        # 选择 CPU 最低的
        worker_to_remove = min(idle_workers, key=lambda w: w.cpu_percent)
        
        # 优雅关闭 Worker
        # await self._stop_worker(worker_to_remove.worker_id)
        
        del self.workers[worker_to_remove.worker_id]
        
        self.last_scale_down = datetime.utcnow()
        print(f"Scaled down: Removed worker {worker_to_remove.worker_id}")
    
    async def _collect_worker_stats(self):
        """收集 Worker 统计"""
        # 从 Redis 或其他协调服务获取 Worker 心跳
        pass
    
    async def _get_queue_length(self) -> int:
        """获取队列长度"""
        # return await self.redis.zcard(self.task_queue)
        return 0
```

### G.7 总结

本章节详细描述了 Flowly 平台的企业级功能优化，目标是对标 Flowise、Dify、n8n、Make 等成熟商业工作流平台，主要包括：

#### 功能完整性

| 功能 | Flowise | Dify | n8n | Make | Flowly |
|------|---------|------|-----|------|--------|
| 拖拽式编辑器 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 并行执行 | ❌ | ✅ | ✅ | ✅ | ✅ (新增) |
| 循环执行 | ❌ | ✅ | ✅ | ✅ | ✅ (新增) |
| 错误重试 | ✅ | ✅ | ✅ | ✅ | ✅ (新增) |
| 条件分支 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 代码执行 | ❌ | ✅ | ✅ | ✅ | ✅ (新增) |
| 数据库操作 | ❌ | ✅ | ✅ | ✅ | ✅ (新增) |
| 函数调用 | ✅ | ✅ | ❌ | ❌ | ✅ (新增) |
| 多模态支持 | ❌ | ✅ | ❌ | ❌ | ✅ (新增) |
| RAG 支持 | ✅ | ✅ | ❌ | ❌ | ✅ (新增) |
| 工作流模板 | ✅ | ✅ | ✅ | ✅ | ✅ (新增) |
| 追踪系统 | ✅ | ✅ | ✅ | ❌ | ✅ (新增) |
| 自动扩缩容 | ❌ | ❌ | ❌ | ❌ | ✅ (新增) |

#### 性能优化

1. **并行执行引擎**: 支持最多 10 个节点并行执行
2. **分布式执行**: 基于 Redis 的任务队列，支持多 Worker
3. **自动扩缩容**: 根据 CPU 和队列长度自动调整 Worker 数量
4. **缓存策略**: 多级缓存（进程内、Redis、CDN）
5. **连接池**: 数据库连接池、HTTP 连接池复用

#### 可观测性

1. **分布式追踪**: 基于 OpenTelemetry 的追踪系统
2. **性能指标**: Prometheus 格式指标输出
3. **日志聚合**: 结构化日志，集成 ELK/Graylog
4. **告警系统**: 基于阈值的告警规则

这些企业级功能使 Flowly 平台能够与 Flowise、Dify、n8n、Make 等成熟平台竞争，并满足企业级应用的需求。

---

## 附录 H - 前沿 AI 技术集成（比赛加分项）

> **提示**: 本章节介绍当前 AI 领域最前沿的技术集成，涵盖 Multi-Agent 编排、MCP 协议、Function Calling 增强等，这些技术能让您的作品在比赛中脱颖而出。

### H.1 Multi-Agent 多智能体编排系统

#### H.1.1 架构概述

Multi-Agent 是当前 AI Agent 领域最热门的技术方向之一。通过多个专业化 Agent 的协作，可以解决复杂任务。

```
┌─────────────────────────────────────────────────────────────────┐
│                      Multi-Agent Orchestrator                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Planner    │    │  Researcher │    │  Executor   │         │
│  │   Agent     │───▶│   Agent     │───▶│   Agent     │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Shared Knowledge Base & Memory           │       │
│  └──────────────────────────────────────────────────────┘       │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Critic    │    │  synthesizer│    │  Monitor    │         │
│  │   Agent     │◀───│   Agent     │◀───│   Agent     │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### H.1.2 Agent 协作模式

```python
# agents/multi_agent/collaboration.py

from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
from datetime import datetime


class AgentRole(Enum):
    """Agent 角色枚举"""
    PLANNER = "planner"           # 规划者 - 分解任务
    RESEARCHER = "researcher"     # 研究者 - 信息检索
    EXECUTOR = "executor"        # 执行者 - 执行具体任务
    CRITIC = "critic"           # 批评者 - 质量评估
    SYNTHESIZER = "synthesizer"  # 综合者 - 整合结果
    COORDINATOR = "coordinator"  # 协调者 - 任务调度


class MessageType(Enum):
    """消息类型"""
    TASK = "task"               # 任务分配
    RESULT = "result"           # 结果返回
    QUERY = "query"            # 信息查询
    RESPONSE = "response"       # 响应回复
    FEEDBACK = "feedback"       # 反馈意见
    APPROVAL = "approval"       # 审批请求


@dataclass
class AgentMessage:
    """Agent 间通信消息"""
    id: str
    sender: str                 # 发送者 Agent ID
    receivers: List[str]        # 接收者 Agent ID 列表
    message_type: MessageType
    content: Dict[str, Any]     # 消息内容
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reply_to: Optional[str] = None  # 回复的消息 ID
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCapability:
    """Agent 能力定义"""
    name: str                   # 能力名称
    description: str            # 能力描述
    input_schema: Dict[str, Any] # 输入 schema
    output_schema: Dict[str, Any] # 输出 schema
    estimated_time: float = 1.0  # 预估执行时间（秒）


@dataclass
class Agent:
    """Agent 定义"""
    agent_id: str
    name: str
    role: AgentRole
    description: str
    capabilities: List[AgentCapability]
    model: str = "gpt-4"
    instructions: str = ""
    max_retries: int = 3
    timeout: float = 30.0
    is_active: bool = True
    
    # Agent 状态
    current_task: Optional[str] = None
    status: str = "idle"  # idle, working, waiting, completed, failed


class AgentMessageBus:
    """Agent 消息总线（观察者模式 + 发布订阅）"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_history: List[AgentMessage] = []
    
    def subscribe(self, agent_id: str, callback: callable):
        """订阅消息"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(callback)
    
    def unsubscribe(self, agent_id: str, callback: callable):
        """取消订阅"""
        if agent_id in self.subscribers:
            self.subscribers[agent_id].remove(callback)
    
    async def publish(self, message: AgentMessage):
        """发布消息"""
        self.message_history.append(message)
        
        # 异步分发消息
        for receiver_id in message.receivers:
            if receiver_id in self.subscribers:
                for callback in self.subscribers[receiver_id]:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
    
    async def send_direct(self, message: AgentMessage):
        """直接发送消息"""
        await self.publish(message)
        await self.message_queue.put(message)
    
    async def get_messages(self, agent_id: str, timeout: float = 1.0) -> List[AgentMessage]:
        """获取发给特定 Agent 的消息"""
        messages = []
        deadline = datetime.utcnow().timestamp() + timeout
        
        while datetime.utcnow().timestamp() < deadline:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=0.1
                )
                if agent_id in message.receivers:
                    messages.append(message)
            except asyncio.TimeoutError:
                break
        
        return messages


class MultiAgentOrchestrator:
    """多智能体编排器"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_bus = AgentMessageBus()
        self.shared_memory: Dict[str, Any] = {}
        self.task_graph: Dict[str, List[str]] = {}  # 任务依赖图
        self.execution_history: List[Dict] = []
    
    def register_agent(self, agent: Agent):
        """注册 Agent"""
        self.agents[agent.agent_id] = agent
        self.message_bus.subscribe(agent.agent_id, agent.receive_message)
        print(f"Registered Agent: {agent.name} ({agent.role.value})")
    
    def create_agent_team(
        self,
        team_config: Dict[str, Any]
    ) -> List[Agent]:
        """创建 Agent 团队"""
        
        agents = []
        
        for config in team_config.get('agents', []):
            agent = Agent(
                agent_id=config['id'],
                name=config['name'],
                role=AgentRole(config['role']),
                description=config.get('description', ''),
                capabilities=[
                    AgentCapability(**cap) 
                    for cap in config.get('capabilities', [])
                ],
                model=config.get('model', 'gpt-4'),
                instructions=config.get('instructions', ''),
                max_retries=config.get('max_retries', 3),
                timeout=config.get('timeout', 30.0)
            )
            self.register_agent(agent)
            agents.append(agent)
        
        return agents
    
    async def execute_collaborative_task(
        self,
        task: Dict[str, Any],
        collaboration_mode: str = "sequential"  # sequential, parallel, hierarchical
    ) -> Dict[str, Any]:
        """执行协作任务"""
        
        task_id = task.get('id', str(uuid.uuid4()))
        start_time = datetime.utcnow()
        
        # 记录执行开始
        self.execution_history.append({
            'task_id': task_id,
            'start_time': start_time,
            'mode': collaboration_mode
        })
        
        if collaboration_mode == "sequential":
            result = await self._execute_sequential(task)
        elif collaboration_mode == "parallel":
            result = await self._execute_parallel(task)
        elif collaboration_mode == "hierarchical":
            result = await self._execute_hierarchical(task)
        else:
            raise ValueError(f"Unknown collaboration mode: {collaboration_mode}")
        
        # 记录执行完成
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        for entry in self.execution_history:
            if entry['task_id'] == task_id:
                entry['end_time'] = end_time
                entry['duration'] = duration
                entry['result'] = result
                break
        
        return {
            'task_id': task_id,
            'result': result,
            'duration': duration,
            'agents_involved': list(set(
                e['agent_id'] for e in self.execution_history
                if e.get('task_id') == task_id
            ))
        }
    
    async def _execute_sequential(self, task: Dict) -> Dict:
        """顺序执行模式"""
        results = {}
        
        # 获取任务步骤
        steps = task.get('steps', [])
        
        for step in steps:
            step_id = step['id']
            assigned_agent_id = step['agent_id']
            
            # 获取 Agent
            agent = self.agents.get(assigned_agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {assigned_agent_id}")
            
            # 准备输入
            input_data = self._prepare_step_input(step, results)
            
            # 执行步骤
            step_result = await self._execute_agent_step(
                agent, step_id, input_data
            )
            
            results[step_id] = step_result
            
            # 更新共享内存
            self.shared_memory[f"{step_id}_result"] = step_result
        
        return {
            'final_result': results.get(steps[-1]['id']) if steps else None,
            'all_results': results
        }
    
    async def _execute_parallel(self, task: Dict) -> Dict:
        """并行执行模式"""
        
        # 获取可以并行执行的步骤
        parallel_steps = task.get('parallel_steps', [])
        
        # 并行执行所有步骤
        tasks = []
        step_ids = []
        
        for step_group in parallel_steps:
            if isinstance(step_group, list):
                # 一组可以并行的步骤
                for step in step_group:
                    agent = self.agents.get(step['agent_id'])
                    if agent:
                        input_data = self._prepare_step_input(step, {})
                        tasks.append(
                            self._execute_agent_step(agent, step['id'], input_data)
                        )
                        step_ids.append(step['id'])
            else:
                # 单个步骤
                agent = self.agents.get(step_group['agent_id'])
                if agent:
                    input_data = self._prepare_step_input(step_group, {})
                    tasks.append(
                        self._execute_agent_step(agent, step_group['id'], input_data)
                    )
                    step_ids.append(step_group['id'])
        
        # 等待所有任务完成
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        results = {}
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                results[step_ids[i]] = {'error': str(result)}
            else:
                results[step_ids[i]] = result
        
        return {'parallel_results': results}
    
    async def _execute_hierarchical(self, task: Dict) -> Dict:
        """层级执行模式（主从结构）"""
        
        # 找到协调者 Agent
        coordinator = None
        for agent in self.agents.values():
            if agent.role == AgentRole.COORDINATOR:
                coordinator = agent
                break
        
        if not coordinator:
            raise ValueError("No coordinator agent found")
        
        # 协调者分析任务并分配
        plan = await self._execute_agent_step(
            coordinator, 'planning', task
        )
        
        # 根据计划分配任务
        sub_tasks = plan.get('sub_tasks', [])
        sub_results = []
        
        for sub_task in sub_tasks:
            assigned_agent_id = sub_task['agent_id']
            agent = self.agents.get(assigned_agent_id)
            
            if agent:
                result = await self._execute_agent_step(
                    agent, sub_task['id'], sub_task
                )
                sub_results.append(result)
        
        # 综合结果
        synthesis = await self._execute_agent_step(
            coordinator, 'synthesis', {
                'original_task': task,
                'sub_results': sub_results
            }
        )
        
        return {
            'plan': plan,
            'sub_results': sub_results,
            'synthesis': synthesis
        }
    
    async def _execute_agent_step(
        self,
        agent: Agent,
        step_id: str,
        input_data: Dict
    ) -> Dict:
        """执行单个 Agent 步骤"""
        
        agent.current_task = step_id
        agent.status = "working"
        
        try:
            # 构建消息
            message = AgentMessage(
                id=str(uuid.uuid4()),
                sender="orchestrator",
                receivers=[agent.agent_id],
                message_type=MessageType.TASK,
                content={
                    'step_id': step_id,
                    'input': input_data,
                    'instructions': agent.instructions
                }
            )
            
            # 发送消息并等待响应
            await self.message_bus.send_direct(message)
            
            # 等待响应（带超时）
            responses = await asyncio.wait_for(
                self.message_bus.get_messages(agent.agent_id),
                timeout=agent.timeout
            )
            
            # 提取结果
            result = None
            for response in responses:
                if response.message_type == MessageType.RESULT:
                    result = response.content.get('result')
                    break
            
            agent.status = "completed"
            return {
                'success': True,
                'agent_id': agent.agent_id,
                'result': result
            }
            
        except asyncio.TimeoutError:
            agent.status = "failed"
            return {
                'success': False,
                'agent_id': agent.agent_id,
                'error': 'Execution timeout'
            }
        except Exception as e:
            agent.status = "failed"
            return {
                'success': False,
                'agent_id': agent.agent_id,
                'error': str(e)
            }
    
    def _prepare_step_input(
        self,
        step: Dict,
        previous_results: Dict
    ) -> Dict:
        """准备步骤输入（从之前结果中提取需要的部分）"""
        
        input_mapping = step.get('input_from', {})
        prepared_input = {}
        
        for target_key, source_key in input_mapping.items():
            if source_key in previous_results:
                result = previous_results[source_key]
                # 支持嵌套路径
                keys = target_key.split('.')
                value = result
                for k in keys:
                    value = value.get(k, {})
                prepared_input[target_key] = value
        
        return prepared_input
    
    def get_execution_dag(self) -> Dict[str, List[str]]:
        """获取执行依赖 DAG"""
        return self.task_graph
    
    def visualize_team_structure(self) -> str:
        """可视化团队结构"""
        lines = ["Multi-Agent Team Structure:", "=" * 40]
        
        for agent in self.agents.values():
            lines.append(f"\n[{agent.role.value.upper()}] {agent.name}")
            lines.append(f"  ID: {agent.agent_id}")
            lines.append(f"  Model: {agent.model}")
            lines.append(f"  Status: {agent.status}")
            lines.append(f"  Capabilities:")
            for cap in agent.capabilities:
                lines.append(f"    - {cap.name}: {cap.description}")
        
        return "\n".join(lines)


# 使用示例
async def demo_multi_agent():
    """Multi-Agent 演示"""
    
    orchestrator = MultiAgentOrchestrator()
    
    # 创建研究团队
    team_config = {
        'agents': [
            {
                'id': 'planner-1',
                'name': '任务规划师',
                'role': 'planner',
                'description': '分析任务并制定执行计划',
                'capabilities': [
                    {
                        'name': 'task_decomposition',
                        'description': '任务分解',
                        'input_schema': {'task': 'string'},
                        'output_schema': {'sub_tasks': 'list'}
                    }
                ],
                'instructions': '你是一个任务规划专家，负责将复杂任务分解为可执行的子任务。'
            },
            {
                'id': 'researcher-1',
                'name': '信息研究员',
                'role': 'researcher',
                'description': '从多种来源检索信息',
                'capabilities': [
                    {
                        'name': 'web_search',
                        'description': '网络搜索',
                        'input_schema': {'query': 'string'},
                        'output_schema': {'results': 'list'}
                    },
                    {
                        'name': 'knowledge_retrieval',
                        'description': '知识库检索',
                        'input_schema': {'query': 'string'},
                        'output_schema': {'documents': 'list'}
                    }
                ],
                'instructions': '你是一个专业的信息研究员，擅长从各种来源收集和分析信息。'
            },
            {
                'id': 'writer-1',
                'name': '内容撰写师',
                'role': 'executor',
                'description': '撰写和编辑内容',
                'capabilities': [
                    {
                        'name': 'content_generation',
                        'description': '内容生成',
                        'input_schema': {'topic': 'string', 'style': 'string'},
                        'output_schema': {'content': 'string'}
                    }
                ],
                'instructions': '你是一个专业的内容创作者，能够根据主题生成高质量内容。'
            },
            {
                'id': 'critic-1',
                'name': '质量审核师',
                'role': 'critic',
                'description': '评估和审核工作质量',
                'capabilities': [
                    {
                        'name': 'quality_review',
                        'description': '质量审核',
                        'input_schema': {'content': 'string'},
                        'output_schema': {'score': 'number', 'feedback': 'string'}
                    }
                ],
                'instructions': '你是一个严格的质量审核专家，给出建设性的改进建议。'
            }
        ]
    }
    
    # 创建团队
    orchestrator.create_agent_team(team_config)
    
    # 执行协作任务
    task = {
        'id': 'demo-task-1',
        'type': 'research_report',
        'goal': '撰写一份关于 AI Agent 发展趋势的研究报告',
        'steps': [
            {
                'id': 'step-1',
                'agent_id': 'planner-1',
                'input_from': {}
            },
            {
                'id': 'step-2',
                'agent_id': 'researcher-1',
                'input_from': {'plan': 'step-1'}
            },
            {
                'id': 'step-3',
                'agent_id': 'writer-1',
                'input_from': {'research': 'step-2'}
            },
            {
                'id': 'step-4',
                'agent_id': 'critic-1',
                'input_from': {'draft': 'step-3'}
            }
        ]
    }
    
    # 执行任务
    result = await orchestrator.execute_collaborative_task(task, "sequential")
    
    print(f"Task completed in {result['duration']:.2f}s")
    print(f"Agents involved: {result['agents_involved']}")
    print(orchestrator.visualize_team_structure())
    
    return result
```

#### H.1.3 Agent 协作工作流节点

```python
# workflow/nodes/multi_agent_node.py

from workflow.nodes.base import BaseNode
from typing import Any, Dict, List
import json


class MultiAgentNode(BaseNode):
    """多智能体协作节点"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        self.agent_ids = config.get('agent_ids', [])
        self.collaboration_mode = config.get('mode', 'sequential')
        self.shared_context = config.get('shared_context', True)
        self.max_iterations = config.get('max_iterations', 5)
        self.convergence_threshold = config.get('convergence_threshold', 0.95)
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行多智能体协作"""
        
        results = {
            'iterations': 0,
            'converged': False,
            'final_output': None,
            'agent_outputs': {}
        }
        
        # 初始化共享上下文
        shared_ctx = context.copy() if self.shared_context else {}
        
        for iteration in range(self.max_iterations):
            results['iterations'] = iteration + 1
            
            # 按模式执行协作
            if self.collaboration_mode == 'sequential':
                iteration_result = await self._sequential_collaboration(
                    shared_ctx
                )
            elif self.collaboration_mode == 'debate':
                iteration_result = await self._debate_collaboration(
                    shared_ctx
                )
            elif self.collaboration_mode == 'consensus':
                iteration_result = await self._consensus_collaboration(
                    shared_ctx
                )
            else:
                iteration_result = await self._parallel_collaboration(
                    shared_ctx
                )
            
            # 更新上下文
            shared_ctx.update(iteration_result.get('context_updates', {}))
            results['agent_outputs'][iteration] = iteration_result
            
            # 检查收敛
            if iteration_result.get('confidence', 0) >= self.convergence_threshold:
                results['converged'] = True
                results['final_output'] = iteration_result.get('output')
                break
        
        return results
    
    async def _sequential_collaboration(self, context: Dict) -> Dict:
        """顺序协作模式"""
        
        context_updates = {}
        current_output = context.get('input')
        
        for agent_id in self.agent_ids:
            agent_output = await self._call_agent(agent_id, current_output)
            context_updates[agent_id] = agent_output
            current_output = agent_output.get('result')
        
        return {
            'context_updates': context_updates,
            'output': current_output,
            'confidence': 0.9
        }
    
    async def _debate_collaboration(self, context: Dict) -> Dict:
        """辩论模式 - Agent 之间相互讨论和反驳"""
        
        # 初始提案
        proposals = []
        for agent_id in self.agent_ids:
            proposal = await self._call_agent(
                agent_id, 
                {'task': context.get('input'), 'mode': 'propose'}
            )
            proposals.append(proposal)
        
        # 多轮辩论
        for round_num in range(3):
            # Agent 互相评论
            critiques = []
            for i, agent_id in enumerate(self.agent_ids):
                other_proposals = [p for j, p in enumerate(proposals) if j != i]
                critique = await self._call_agent(
                    agent_id,
                    {
                        'mode': 'criticize',
                        'proposals': other_proposals,
                        'round': round_num
                    }
                )
                critiques.append(critique)
            
            # Agent 根据批评修改提案
            for i, agent_id in enumerate(self.agent_ids):
                proposals[i] = await self._call_agent(
                    agent_id,
                    {
                        'mode': 'revise',
                        'own_proposal': proposals[i],
                        'critiques': critiques
                    }
                )
        
        # 最终综合
        final_synthesis = await self._call_agent(
            self.agent_ids[0],
            {
                'mode': 'synthesize',
                'all_proposals': proposals
            }
        )
        
        return {
            'context_updates': {
                'proposals': proposals,
                'critiques': critiques
            },
            'output': final_synthesis.get('result'),
            'confidence': 0.95
        }
    
    async def _consensus_collaboration(self, context: Dict) -> Dict:
        """共识模式 - Agent 协商达成共识"""
        
        votes = {}
        
        # 初始化提案
        for agent_id in self.agent_ids:
            proposal = await self._call_agent(
                agent_id,
                {'task': context.get('input'), 'mode': 'initial_vote'}
            )
            votes[agent_id] = proposal
        
        # 投票和协商
        for round_num in range(5):
            # 统计票数
            vote_counts = self._tally_votes(votes)
            
            # 检查是否达成共识
            if max(vote_counts.values()) / len(self.agent_ids) >= 0.7:
                break
            
            # 说服阶段 - 票数少的 Agent 尝试说服
            for agent_id in self.agent_ids:
                if votes[agent_id].get('count', 0) < len(self.agent_ids) / 2:
                    # 尝试采纳多数意见
                    majority_option = max(vote_counts.items(), key=lambda x: x[1])[0]
                    updated = await self._call_agent(
                        agent_id,
                        {
                            'mode': 'convince',
                            'own_position': votes[agent_id],
                            'majority_position': majority_option
                        }
                    )
                    votes[agent_id] = updated
        
        return {
            'context_updates': {'votes': votes},
            'output': self._extract_consensus(votes),
            'confidence': 0.9
        }
    
    async def _parallel_collaboration(self, context: Dict) -> Dict:
        """并行模式 - 同时执行后合并"""
        
        # 并行调用所有 Agent
        tasks = [
            self._call_agent(agent_id, context.get('input'))
            for agent_id in self.agent_ids
        ]
        
        import asyncio
        results = await asyncio.gather(*tasks)
        
        # 合并结果
        combined = {
            'outputs': results,
            'merged': self._merge_outputs(results)
        }
        
        return {
            'context_updates': combined,
            'output': combined['merged'],
            'confidence': 0.85
        }
    
    async def _call_agent(self, agent_id: str, input_data: Dict) -> Dict:
        """调用单个 Agent"""
        # 实际实现会调用 LLM 或 Agent 服务
        return {
            'agent_id': agent_id,
            'result': f"Result from {agent_id}",
            'confidence': 0.8
        }
    
    def _tally_votes(self, votes: Dict) -> Dict[str, int]:
        """统计票数"""
        counts = {}
        for vote in votes.values():
            option = vote.get('option', 'unknown')
            counts[option] = counts.get(option, 0) + 1
        return counts
    
    def _extract_consensus(self, votes: Dict) -> Any:
        """提取共识结果"""
        # 找到票数最多的选项
        vote_counts = self._tally_votes(votes)
        majority = max(vote_counts.items(), key=lambda x: x[1])[0]
        return majority
    
    def _merge_outputs(self, outputs: List[Dict]) -> Dict:
        """合并多个输出"""
        return {
            'type': 'merged',
            'sources': len(outputs),
            'content': outputs
        }
```

---

### H.2 MCP (Model Context Protocol) 协议集成

#### H.2.1 MCP 协议概述

MCP 是 Anthropic 推出的模型上下文协议，用于标准化 AI 模型与外部工具、数据的连接。

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP 协议架构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐        ┌──────────────┐        ┌──────────┐ │
│   │   Host App   │◀──────▶│  MCP Server  │◀──────▶│  Tools   │ │
│   │  (Flowly)    │  JSON   │              │  HTTP  │          │ │
│   └──────────────┘  RPC    └──────────────┘        └──────────┘ │
│         │                 │                              │       │
│         │                 │                              │       │
│         ▼                 ▼                              ▼       │
│   ┌──────────────┐  ┌──────────────┐        ┌──────────────┐   │
│   │   LLM API    │  │   Memory     │        │   Data       │   │
│   │  (Claude)    │  │   (Context)  │        │   Sources    │   │
│   └──────────────┘  └──────────────┘        └──────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### H.2.2 MCP Server 实现

```python
# mcp/server.py

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from aiohttp import web
import logging

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP 协议错误"""
    def __init__(self, code: str, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")


class ResourceType(Enum):
    """资源类型"""
    FILE = "file"
    DATABASE = "database"
    API = "api"
    MEMORY = "memory"


@dataclass
class Tool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable = field(default=None)
    

@dataclass
class Resource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str
    resource_type: ResourceType
    schema: Optional[Dict] = None


@dataclass
class MCPPrompt:
    """MCP 提示模板"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    template: str


class MCPProtocol:
    """MCP 协议处理器"""
    
    VERSION = "2024-11-05"
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.capabilities: Dict[str, bool] = {
            'tools': True,
            'resources': True,
            'prompts': True,
            'logging': True
        }
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def register_resource(self, resource: Resource):
        """注册资源"""
        self.resources[resource.uri] = resource
        logger.info(f"Registered resource: {resource.uri}")
    
    def register_prompt(self, prompt: MCPPrompt):
        """注册提示模板"""
        self.prompts[prompt.name] = prompt
        logger.info(f"Registered prompt: {prompt.name}")
    
    async def handle_request(self, method: str, params: Dict) -> Dict:
        """处理 MCP 请求"""
        
        handlers = {
            'initialize': self._handle_initialize,
            'tools/list': self._handle_list_tools,
            'tools/call': self._handle_call_tool,
            'resources/list': self._handle_list_resources,
            'resources/read': self._handle_read_resource,
            'prompts/list': self._handle_list_prompts,
            'prompts/get': self._handle_get_prompt,
            'logging/message': self._handle_logging,
        }
        
        handler = handlers.get(method)
        if not handler:
            raise MCPError(
                'method_not_found',
                f"Unknown method: {method}"
            )
        
        return await handler(params)
    
    async def _handle_initialize(self, params: Dict) -> Dict:
        """初始化连接"""
        client_info = params.get('clientInfo', {})
        
        return {
            'protocolVersion': self.VERSION,
            'capabilities': self.capabilities,
            'serverInfo': {
                'name': 'flowly-mcp-server',
                'version': '1.0.0'
            }
        }
    
    async def _handle_list_tools(self, params: Dict) -> Dict:
        """列出所有工具"""
        return {
            'tools': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'inputSchema': tool.input_schema
                }
                for tool in self.tools.values()
            ]
        }
    
    async def _handle_call_tool(self, params: Dict) -> Dict:
        """调用工具"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        tool = self.tools.get(tool_name)
        if not tool:
            raise MCPError(
                'tool_not_found',
                f"Tool not found: {tool_name}"
            )
        
        try:
            # 执行工具
            if tool.handler:
                result = await tool.handler(arguments)
            else:
                result = {'success': True}
            
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(result, ensure_ascii=False)
                    }
                ],
                'isError': False
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': str(e)
                    }
                ],
                'isError': True
            }
    
    async def _handle_list_resources(self, params: Dict) -> Dict:
        """列出所有资源"""
        return {
            'resources': [
                {
                    'uri': resource.uri,
                    'name': resource.name,
                    'description': resource.description,
                    'mimeType': 'application/json'
                }
                for resource in self.resources.values()
            ]
        }
    
    async def _handle_read_resource(self, params: Dict) -> Dict:
        """读取资源"""
        uri = params.get('uri')
        
        resource = self.resources.get(uri)
        if not resource:
            raise MCPError(
                'resource_not_found',
                f"Resource not found: {uri}"
            )
        
        # 读取资源内容
        content = await self._read_resource_content(resource)
        
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(content, ensure_ascii=False)
                }
            ]
        }
    
    async def _read_resource_content(self, resource: Resource) -> Any:
        """读取资源内容"""
        if resource.resource_type == ResourceType.MEMORY:
            # 从内存读取
            return {'type': 'memory', 'data': []}
        return {}
    
    async def _handle_list_prompts(self, params: Dict) -> Dict:
        """列出所有提示模板"""
        return {
            'prompts': [
                {
                    'name': prompt.name,
                    'description': prompt.description,
                    'arguments': prompt.arguments
                }
                for prompt in self.prompts.values()
            ]
        }
    
    async def _handle_get_prompt(self, params: Dict) -> Dict:
        """获取提示模板"""
        name = params.get('name')
        arguments = params.get('arguments', {})
        
        prompt = self.prompts.get(name)
        if not prompt:
            raise MCPError(
                'prompt_not_found',
                f"Prompt not found: {name}"
            )
        
        # 渲染模板
        content = self._render_prompt(prompt, arguments)
        
        return {
            'messages': [
                {
                    'role': 'user',
                    'content': {
                        'type': 'text',
                        'text': content
                    }
                }
            ]
        }
    
    def _render_prompt(self, prompt: MCPPrompt, arguments: Dict) -> str:
        """渲染提示模板"""
        template = prompt.template
        
        for key, value in arguments.items():
            template = template.replace(f"{{{key}}}", str(value))
        
        return template
    
    async def _handle_logging(self, params: Dict) -> Dict:
        """处理日志消息"""
        level = params.get('level', 'info')
        data = params.get('data', {})
        
        log_methods = {
            'debug': logger.debug,
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error
        }
        
        log_method = log_methods.get(level, logger.info)
        log_method(f"MCP Log: {data}")
        
        return {'logged': True}


class MCPServer:
    """MCP 服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8765):
        self.host = host
        self.port = port
        self.protocol = MCPProtocol()
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/health', self.handle_health)
    
    async def handle_mcp_request(self, request: web.Request) -> web.Response:
        """处理 MCP 请求"""
        try:
            data = await request.json()
            method = data.get('method', '')
            params = data.get('params', {})
            
            result = await self.protocol.handle_request(method, params)
            
            return web.json_response({
                'jsonrpc': '2.0',
                'id': data.get('id'),
                'result': result
            })
            
        except MCPError as e:
            return web.json_response({
                'jsonrpc': '2.0',
                'id': request.json().get('id') if request.can_read_body else None,
                'error': {
                    'code': e.code,
                    'message': e.message,
                    'data': e.data
                }
            }, status=400)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return web.json_response({
                'jsonrpc': '2.0',
                'error': {
                    'code': 'internal_error',
                    'message': str(e)
                }
            }, status=500)
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """健康检查"""
        return web.json_response({
            'status': 'healthy',
            'server': 'flowly-mcp-server',
            'version': self.protocol.VERSION
        })
    
    def register_workflow_tools(self):
        """注册工作流相关工具"""
        
        # 工作流执行工具
        self.protocol.register_tool(Tool(
            name='execute_workflow',
            description='Execute a workflow with given parameters',
            input_schema={
                'type': 'object',
                'properties': {
                    'workflow_id': {'type': 'string'},
                    'parameters': {'type': 'object'}
                },
                'required': ['workflow_id']
            },
            handler=self._tool_execute_workflow
        ))
        
        # 工作流状态查询工具
        self.protocol.register_tool(Tool(
            name='get_workflow_status',
            description='Get the status of a workflow execution',
            input_schema={
                'type': 'object',
                'properties': {
                    'execution_id': {'type': 'string'}
                },
                'required': ['execution_id']
            },
            handler=self._tool_get_workflow_status
        ))
        
        # 知识库检索工具
        self.protocol.register_tool(Tool(
            name='search_knowledge',
            description='Search the knowledge base',
            input_schema={
                'type': 'object',
                'properties': {
                    'query': {'type': 'string'},
                    'top_k': {'type': 'integer', 'default': 5}
                },
                'required': ['query']
            },
            handler=self._tool_search_knowledge
        ))
        
        # Agent 创建工具
        self.protocol.register_tool(Tool(
            name='create_agent',
            description='Create a new AI Agent',
            input_schema={
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'role': {'type': 'string'},
                    'capabilities': {'type': 'array'}
                },
                'required': ['name']
            },
            handler=self._tool_create_agent
        ))
    
    async def _tool_execute_workflow(self, args: Dict) -> Dict:
        """执行工作流工具"""
        workflow_id = args['workflow_id']
        parameters = args.get('parameters', {})
        
        # 调用工作流执行服务
        # result = await workflow_service.execute(workflow_id, parameters)
        
        return {
            'execution_id': 'exec-123',
            'status': 'started',
            'workflow_id': workflow_id
        }
    
    async def _tool_get_workflow_status(self, args: Dict) -> Dict:
        """获取工作流状态工具"""
        execution_id = args['execution_id']
        
        return {
            'execution_id': execution_id,
            'status': 'running',
            'progress': 0.65,
            'current_node': 'node-3'
        }
    
    async def _tool_search_knowledge(self, args: Dict) -> Dict:
        """知识库检索工具"""
        query = args['query']
        top_k = args.get('top_k', 5)
        
        return {
            'query': query,
            'results': [
                {'content': f'Result {i}', 'score': 0.9 - i * 0.1}
                for i in range(top_k)
            ]
        }
    
    async def _tool_create_agent(self, args: Dict) -> Dict:
        """创建 Agent 工具"""
        name = args['name']
        role = args.get('role', 'assistant')
        capabilities = args.get('capabilities', [])
        
        return {
            'agent_id': 'agent-new-123',
            'name': name,
            'role': role,
            'capabilities': capabilities,
            'created': True
        }
    
    async def start(self):
        """启动服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"MCP Server started on {self.host}:{self.port}")


# 使用示例
async def main():
    server = MCPServer()
    server.register_workflow_tools()
    await server.start()
    
    # 保持运行
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
```

---

### H.3 Function Calling 增强系统

#### H.3.1 动态 Function Calling 架构

```python
# agents/function_calling/enhanced_fc.py

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
import re
from datetime import datetime


class CallStrategy(Enum):
    """调用策略"""
    SINGLE = "single"           # 单次调用
    PARALLEL = "parallel"       # 并行调用
    SEQUENTIAL = "sequential"    # 顺序调用
    CONDITIONAL = "conditional" # 条件调用
    HYBRID = "hybrid"           # 混合策略


@dataclass
class FunctionSpec:
    """函数规范"""
    name: str
    description: str
    parameters: Dict[str, Any]   # JSON Schema 格式
    handler: Callable
    requires_approval: bool = False
    timeout: float = 30.0
    retry_count: int = 3
    cacheable: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class FunctionCall:
    """函数调用记录"""
    call_id: str
    function_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    execution_time: float = 0.0


@dataclass
class CallChain:
    """调用链"""
    chain_id: str
    calls: List[FunctionCall] = field(default_factory=list)
    strategy: CallStrategy = CallStrategy.SINGLE
    context: Dict[str, Any] = field(default_factory=dict)
    max_parallel: int = 5
    

class FunctionRegistry:
    """函数注册表"""
    
    def __init__(self):
        self.functions: Dict[str, FunctionSpec] = {}
        self.categories: Dict[str, List[str]] = {}
        self._cache: Dict[str, Any] = {}
    
    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        category: Optional[str] = None,
        **options
    ):
        """注册函数"""
        spec = FunctionSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            **options
        )
        
        self.functions[name] = spec
        
        if category:
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(name)
        
        return spec
    
    def get(self, name: str) -> Optional[FunctionSpec]:
        """获取函数规范"""
        return self.functions.get(name)
    
    def list_by_category(self, category: str) -> List[FunctionSpec]:
        """按类别列出函数"""
        names = self.categories.get(category, [])
        return [self.functions[n] for n in names if n in self.functions]
    
    def search(self, query: str) -> List[FunctionSpec]:
        """搜索函数"""
        results = []
        query_lower = query.lower()
        
        for spec in self.functions.values():
            if (query_lower in spec.name.lower() or
                query_lower in spec.description.lower() or
                any(query_lower in tag.lower() for tag in spec.tags)):
                results.append(spec)
        
        return results


class EnhancedFunctionCalling:
    """增强型 Function Calling 系统"""
    
    def __init__(self):
        self.registry = FunctionRegistry()
        self.call_history: List[FunctionCall] = []
        self.active_chains: Dict[str, CallChain] = {}
        self._setup_builtin_functions()
    
    def _setup_builtin_functions(self):
        """设置内置函数"""
        
        # 工作流相关
        self.registry.register(
            name='execute_workflow',
            description='Execute a workflow and return results',
            parameters={
                'type': 'object',
                'properties': {
                    'workflow_id': {'type': 'string'},
                    'inputs': {'type': 'object'}
                },
                'required': ['workflow_id']
            },
            handler=self._execute_workflow,
            category='workflow',
            tags=['workflow', 'execution', 'async']
        )
        
        # 知识检索
        self.registry.register(
            name='search_knowledge',
            description='Search knowledge base for relevant information',
            parameters={
                'type': 'object',
                'properties': {
                    'query': {'type': 'string'},
                    'top_k': {'type': 'integer', 'default': 5},
                    'filters': {'type': 'object'}
                },
                'required': ['query']
            },
            handler=self._search_knowledge,
            category='knowledge',
            tags=['search', 'retrieval', 'RAG'],
            cacheable=True
        )
        
        # 数据处理
        self.registry.register(
            name='process_data',
            description='Process and transform data according to rules',
            parameters={
                'type': 'object',
                'properties': {
                    'data': {'type': 'array'},
                    'operation': {
                        'type': 'string',
                        'enum': ['filter', 'map', 'reduce', 'aggregate']
                    },
                    'config': {'type': 'object'}
                },
                'required': ['data', 'operation']
            },
            handler=self._process_data,
            category='data',
            tags=['data', 'processing', 'transform']
        )
        
        # API 调用
        self.registry.register(
            name='call_external_api',
            description='Make HTTP request to external API',
            parameters={
                'type': 'object',
                'properties': {
                    'url': {'type': 'string', 'format': 'uri'},
                    'method': {
                        'type': 'string',
                        'enum': ['GET', 'POST', 'PUT', 'DELETE']
                    },
                    'headers': {'type': 'object'},
                    'body': {'type': 'object'}
                },
                'required': ['url', 'method']
            },
            handler=self._call_external_api,
            category='integration',
            tags=['api', 'http', 'integration']
        )
        
        # 多步骤执行
        self.registry.register(
            name='execute_chain',
            description='Execute a chain of function calls',
            parameters={
                'type': 'object',
                'properties': {
                    'chain': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'function': {'type': 'string'},
                                'args': {'type': 'object'}
                            }
                        }
                    },
                    'strategy': {
                        'type': 'string',
                        'enum': ['sequential', 'parallel', 'conditional']
                    }
                },
                'required': ['chain']
            },
            handler=self._execute_chain,
            category='orchestration',
            tags=['chain', 'orchestration', 'multi-step']
        )
    
    async def call_function(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> FunctionCall:
        """调用函数"""
        
        spec = self.registry.get(function_name)
        if not spec:
            raise ValueError(f"Function not found: {function_name}")
        
        call = FunctionCall(
            call_id=f"call-{len(self.call_history)}",
            function_name=function_name,
            arguments=arguments,
            start_time=datetime.utcnow()
        )
        
        # 检查缓存
        if spec.cacheable:
            cache_key = self._get_cache_key(function_name, arguments)
            if cache_key in self.registry._cache:
                call.result = self.registry._cache[cache_key]
                call.status = "completed"
                return call
        
        try:
            call.status = "running"
            
            # 执行函数（带重试）
            for attempt in range(spec.retry_count):
                try:
                    if asyncio.iscoroutinefunction(spec.handler):
                        result = await asyncio.wait_for(
                            spec.handler(arguments, context),
                            timeout=spec.timeout
                        )
                    else:
                        result = spec.handler(arguments, context)
                    
                    call.result = result
                    call.status = "completed"
                    
                    # 写入缓存
                    if spec.cacheable:
                        self.registry._cache[cache_key] = result
                    
                    break
                    
                except asyncio.TimeoutError:
                    if attempt == spec.retry_count - 1:
                        raise
                
                except Exception as e:
                    if attempt == spec.retry_count - 1:
                        raise
        
        except Exception as e:
            call.status = "failed"
            call.error = str(e)
        
        finally:
            call.end_time = datetime.utcnow()
            call.execution_time = (
                call.end_time - call.start_time
            ).total_seconds()
            self.call_history.append(call)
        
        return call
    
    async def call_parallel(
        self,
        calls: List[tuple[str, Dict]]
    ) -> List[FunctionCall]:
        """并行调用多个函数"""
        
        tasks = [
            self.call_function(name, args)
            for name, args in calls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            r if isinstance(r, FunctionCall) else FunctionCall(
                call_id="error",
                function_name=calls[i][0],
                arguments=calls[i][1],
                error=str(r),
                status="failed"
            )
            for i, r in enumerate(results)
        ]
    
    async def call_conditional(
        self,
        conditions: List[Dict[str, Any]],
        default_result: Any = None
    ) -> Any:
        """条件调用"""
        
        for condition in conditions:
            predicate = condition.get('predicate')
            function_name = condition.get('function')
            args = condition.get('args', {})
            context = condition.get('context')
            
            # 评估条件
            if await self._evaluate_condition(predicate, context):
                return await self.call_function(function_name, args, context)
        
        return default_result
    
    async def execute_chain(
        self,
        chain_def: List[Dict[str, Any]],
        strategy: CallStrategy = CallStrategy.SEQUENTIAL,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """执行调用链"""
        
        chain_id = f"chain-{datetime.utcnow().timestamp()}"
        chain = CallChain(
            chain_id=chain_id,
            strategy=strategy,
            context=context or {}
        )
        
        self.active_chains[chain_id] = chain
        
        try:
            if strategy == CallStrategy.SEQUENTIAL:
                result = await self._execute_sequential(chain_def, chain)
            elif strategy == CallStrategy.PARALLEL:
                result = await self._execute_parallel(chain_def, chain)
            elif strategy == CallStrategy.CONDITIONAL:
                result = await self._execute_conditional(chain_def, chain)
            else:
                result = await self._execute_hybrid(chain_def, chain)
            
            return {
                'chain_id': chain_id,
                'status': 'completed',
                'result': result,
                'calls': [c.__dict__ for c in chain.calls]
            }
            
        except Exception as e:
            return {
                'chain_id': chain_id,
                'status': 'failed',
                'error': str(e),
                'calls': [c.__dict__ for c in chain.calls]
            }
        finally:
            del self.active_chains[chain_id]
    
    async def _execute_sequential(
        self,
        chain_def: List[Dict],
        chain: CallChain
    ) -> Any:
        """顺序执行"""
        
        result = None
        for step in chain_def:
            # 解析参数（可能引用上一步结果）
            args = self._resolve_args(step.get('args', {}), chain, result)
            context = step.get('context', {})
            
            call = await self.call_function(
                step['function'],
                args,
                context
            )
            
            chain.calls.append(call)
            
            if call.status == "failed":
                raise Exception(f"Chain failed at {step['function']}: {call.error}")
            
            result = call.result
        
        return result
    
    async def _execute_parallel(
        self,
        chain_def: List[Dict],
        chain: CallChain
    ) -> List[Any]:
        """并行执行"""
        
        calls_to_make = [
            (step['function'], self._resolve_args(step.get('args', {}), chain, None))
            for step in chain_def
        ]
        
        results = await self.call_parallel(calls_to_make)
        
        for call in results:
            chain.calls.append(call)
        
        return [c.result for c in results]
    
    async def _execute_conditional(
        self,
        chain_def: List[Dict],
        chain: CallChain
    ) -> Any:
        """条件执行"""
        
        result = None
        for step in chain_def:
            # 检查是否满足条件
            if 'condition' in step:
                if not await self._evaluate_condition(step['condition'], chain.context):
                    continue
            
            args = self._resolve_args(step.get('args', {}), chain, result)
            
            call = await self.call_function(
                step['function'],
                args,
                step.get('context', {})
            )
            
            chain.calls.append(call)
            result = call.result
        
        return result
    
    async def _execute_hybrid(
        self,
        chain_def: List[Dict],
        chain: CallChain
    ) -> Dict[str, Any]:
        """混合执行策略"""
        
        # 将链分成可以并行和必须顺序的部分
        parallel_groups = []
        sequential_remaining = []
        
        i = 0
        while i < len(chain_def):
            step = chain_def[i]
            
            if step.get('parallel_with_next') and i + 1 < len(chain_def):
                # 与下一个合并为并行组
                group = [step, chain_def[i + 1]]
                parallel_groups.append(group)
                i += 2
            else:
                sequential_remaining.append(step)
                i += 1
        
        # 执行
        results = {}
        
        # 先执行并行组
        for group in parallel_groups:
            group_calls = [
                (s['function'], self._resolve_args(s.get('args', {}), chain, None))
                for s in group
            ]
            group_results = await self.call_parallel(group_calls)
            for j, call in enumerate(group_results):
                chain.calls.append(call)
                results[f"parallel_{group[0]['function']}_{j}"] = call.result
        
        # 再执行顺序部分
        sequential_result = None
        for step in sequential_remaining:
            args = self._resolve_args(step.get('args', {}), chain, sequential_result)
            
            call = await self.call_function(
                step['function'],
                args,
                step.get('context', {})
            )
            
            chain.calls.append(call)
            sequential_result = call.result
        
        return {
            'parallel_results': results,
            'sequential_result': sequential_result
        }
    
    def _resolve_args(
        self,
        args: Dict,
        chain: CallChain,
        previous_result: Any
    ) -> Dict[str, Any]:
        """解析参数（替换变量引用）"""
        
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str) and value.startswith('$'):
                # 引用变量
                var_name = value[1:]
                if var_name == 'previous':
                    resolved[key] = previous_result
                elif var_name in chain.context:
                    resolved[key] = chain.context[var_name]
                elif chain.calls:
                    # 引用之前调用的结果
                    resolved[key] = self._resolve_call_result(var_name, chain.calls)
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                # 递归解析
                resolved[key] = self._resolve_args(value, chain, previous_result)
            elif isinstance(value, list):
                # 列表中的值
                resolved[key] = [
                    self._resolve_args({'v': v}, chain, previous_result)['v']
                    if isinstance(v, (dict, str)) and str(v).startswith('$')
                    else v
                    for v in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _resolve_call_result(self, ref: str, calls: List[FunctionCall]) -> Any:
        """解析调用结果引用"""
        
        # 格式: function_name.result_path 或 function_name
        parts = ref.split('.')
        func_name = parts[0]
        
        for call in reversed(calls):
            if call.function_name == func_name:
                if len(parts) > 1:
                    # 返回嵌套属性
                    result = call.result
                    for part in parts[1:]:
                        if isinstance(result, dict):
                            result = result.get(part)
                        else:
                            return None
                    return result
                return call.result
        
        return None
    
    async def _evaluate_condition(
        self,
        condition: Dict,
        context: Dict
    ) -> bool:
        """评估条件"""
        
        condition_type = condition.get('type', 'expression')
        
        if condition_type == 'expression':
            expr = condition.get('expression', '')
            return self._eval_expression(expr, context)
        elif condition_type == 'function':
            func_name = condition.get('function')
            func = self.registry.get(func_name)
            if func:
                result = await func.handler(condition.get('args', {}), context)
                return bool(result)
        
        return False
    
    def _eval_expression(self, expr: str, context: Dict) -> bool:
        """评估表达式"""
        
        # 简单的表达式评估器
        # 支持: ==, !=, >, <, >=, <=, and, or, not
        
        # 替换变量
        for key, value in context.items():
            expr = expr.replace(f'${key}', repr(value))
        
        # 安全评估（仅允许基本操作符）
        allowed = '0123456789.+\\-*/<>=!() and or not True False None'
        if all(c in allowed or c == ' ' for c in expr):
            try:
                return eval(expr)
            except:
                pass
        
        return False
    
    def _get_cache_key(self, func_name: str, args: Dict) -> str:
        """生成缓存键"""
        import hashlib
        key_data = f"{func_name}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    # 内置函数实现
    async def _execute_workflow(self, args: Dict, context: Optional[Dict]) -> Dict:
        """执行工作流"""
        return {'workflow_id': args['workflow_id'], 'status': 'executed'}
    
    async def _search_knowledge(self, args: Dict, context: Optional[Dict]) -> Dict:
        """搜索知识库"""
        return {
            'query': args['query'],
            'results': [
                {'content': f'Result for {args["query"]}', 'score': 0.95}
            ]
        }
    
    async def _process_data(self, args: Dict, context: Optional[Dict]) -> Dict:
        """处理数据"""
        data = args['data']
        operation = args['operation']
        
        if operation == 'filter':
            return [d for d in data if args.get('config', {}).get('condition', True)(d)]
        elif operation == 'map':
            return [args.get('config', {}).get('transform', lambda x: x)(d) for d in data]
        
        return data
    
    async def _call_external_api(self, args: Dict, context: Optional[Dict]) -> Dict:
        """调用外部 API"""
        return {
            'url': args['url'],
            'method': args['method'],
            'status': 'success'
        }
    
    async def _execute_chain(self, args: Dict, context: Optional[Dict]) -> Dict:
        """执行调用链"""
        return await self.execute_chain(
            args['chain'],
            CallStrategy(args.get('strategy', 'sequential')),
            context
        )


# 使用示例
async def demo_function_calling():
    """Function Calling 演示"""
    
    fc = EnhancedFunctionCalling()
    
    # 单次调用
    result1 = await fc.call_function(
        'search_knowledge',
        {'query': 'AI workflow automation', 'top_k': 3}
    )
    print(f"Single call result: {result1.result}")
    
    # 并行调用
    results = await fc.call_parallel([
        ('search_knowledge', {'query': 'AI agents'}),
        ('search_knowledge', {'query': 'workflow orchestration'}),
        ('search_knowledge', {'query': 'function calling'})
    ])
    print(f"Parallel calls: {len(results)} completed")
    
    # 调用链
    chain_result = await fc.execute_chain([
        {
            'function': 'search_knowledge',
            'args': {'query': 'AI trends 2026'}
        },
        {
            'function': 'process_data',
            'args': {
                'data': '$previous',
                'operation': 'map',
                'config': {'transform': lambda x: x.get('content', '')}
            }
        },
        {
            'function': 'execute_workflow',
            'args': {
                'workflow_id': 'workflow-123',
                'inputs': {'content': '$process_data'}
            }
        }
    ], CallStrategy.SEQUENTIAL)
    
    print(f"Chain result: {chain_result}")
```

---

### H.4 AI 原生搜索系统（向量检索 + Reranking）

#### H.4.1 混合搜索架构

```python
# search/hybrid_search.py

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from datetime import datetime


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # vector, keyword, hybrid
    rerank_score: Optional[float] = None


@dataclass
class SearchConfig:
    """搜索配置"""
    vector_weight: float = 0.6
    keyword_weight: float = 0.3
    rerank_enabled: bool = True
    rerank_model: str = "bge-reranker"
    top_k: int = 10
    min_score: float = 0.5


class HybridSearchEngine:
    """混合搜索引擎（向量 + 关键词 + 重排序）"""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.vector_index = None
        self.keyword_index = {}
        self.documents: Dict[str, Dict] = {}
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """执行混合搜索"""
        
        top_k = top_k or self.config.top_k
        
        # 1. 向量搜索
        vector_results = await self._vector_search(query, top_k * 2)
        
        # 2. 关键词搜索
        keyword_results = await self._keyword_search(query, top_k * 2)
        
        # 3. 合并结果
        merged = self._merge_results(vector_results, keyword_results)
        
        # 4. 元数据过滤
        if filters:
            merged = self._apply_filters(merged, filters)
        
        # 5. 重排序
        if self.config.rerank_enabled:
            merged = await self._rerank(query, merged)
        
        # 6. 返回 top_k
        return merged[:top_k]
    
    async def _vector_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """向量搜索"""
        
        # 生成查询向量
        query_embedding = await self._embed_query(query)
        
        # 在向量索引中搜索
        # 实际实现会调用 Qdrant/Milvus 等
        results = []
        
        for doc_id, doc in self.documents.items():
            if 'embedding' in doc:
                similarity = self._cosine_similarity(
                    query_embedding,
                    doc['embedding']
                )
                results.append(SearchResult(
                    id=doc_id,
                    content=doc.get('content', ''),
                    score=float(similarity),
                    metadata=doc.get('metadata', {}),
                    source='vector'
                ))
        
        # 排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    async def _keyword_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """关键词搜索（BM25）"""
        
        query_terms = query.lower().split()
        results = []
        
        for doc_id, doc in self.documents.items():
            content = doc.get('content', '').lower()
            
            # 计算 TF
            tf = sum(content.count(term) for term in query_terms)
            
            # 计算 IDF
            doc_count = len(self.documents)
            idf = np.log((doc_count - tf + 0.5) / (tf + 0.5) + 1)
            
            # BM25 分数
            doc_len = len(content.split())
            avg_len = sum(len(d.get('content', '').split()) 
                         for d in self.documents.values()) / max(doc_count, 1)
            
            k1 = 1.5
            b = 0.75
            
            bm25_score = sum(
                idf * (tf * (k1 + 1)) / 
                (tf + k1 * (1 - b + b * doc_len / avg_len))
                for term in query_terms
            )
            
            if bm25_score > 0:
                results.append(SearchResult(
                    id=doc_id,
                    content=doc.get('content', ''),
                    score=bm25_score,
                    metadata=doc.get('metadata', {}),
                    source='keyword'
                ))
        
        # 排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _merge_results(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult]
    ) -> List[SearchResult]:
        """合并搜索结果"""
        
        # 创建映射
        score_map: Dict[str, SearchResult] = {}
        
        # 添加向量结果
        for result in vector_results:
            result.source = 'vector'
            score_map[result.id] = result
        
        # 添加/合并关键词结果
        for result in keyword_results:
            if result.id in score_map:
                # 合并分数
                existing = score_map[result.id]
                existing.score = (
                    existing.score * self.config.vector_weight +
                    result.score * self.config.keyword_weight
                )
                existing.source = 'hybrid'
            else:
                result.source = 'keyword'
                result.score *= self.config.keyword_weight
                score_map[result.id] = result
        
        # 重新排序
        merged = list(score_map.values())
        merged.sort(key=lambda x: x.score, reverse=True)
        
        return merged
    
    async def _rerank(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """使用重排序模型重新排序"""
        
        if not results:
            return results
        
        # 调用重排序模型
        doc_texts = [r.content for r in results]
        
        rerank_scores = await self._call_reranker(query, doc_texts)
        
        # 更新分数
        for i, result in enumerate(results):
            result.rerank_score = rerank_scores[i]
            # 加权最终分数
            result.score = (
                result.score * 0.3 +
                result.rerank_score * 0.7
            )
        
        # 按重排分数排序
        results.sort(key=lambda x: x.rerank_score or x.score, reverse=True)
        
        return results
    
    async def _call_reranker(
        self,
        query: str,
        documents: List[str]
    ) -> List[float]:
        """调用重排序模型"""
        
        # 实际实现会调用 BGE-Reranker 等模型
        # 这里模拟返回随机分数
        import random
        return [random.random() for _ in documents]
    
    async def _embed_query(self, query: str) -> np.ndarray:
        """生成查询向量"""
        # 实际实现会调用 Embedding API
        # 这里返回随机向量
        return np.random.randn(1536)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
    
    def _apply_filters(
        self,
        results: List[SearchResult],
        filters: Dict
    ) -> List[SearchResult]:
        """应用元数据过滤器"""
        
        filtered = []
        for result in results:
            match = True
            for key, value in filters.items():
                if result.metadata.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(result)
        
        return filtered
    
    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """添加文档"""
        
        # 存储文档
        self.documents[doc_id] = {
            'content': content,
            'metadata': metadata or {},
            'created_at': datetime.utcnow()
        }
        
        # 添加到关键词索引
        self.keyword_index[doc_id] = content.lower()


class SemanticCache:
    """语义缓存 - 基于向量相似度的缓存"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        self.cache: Dict[str, Dict] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.similarity_threshold = similarity_threshold
    
    async def get(
        self,
        query: str,
        embedding: Optional[np.ndarray] = None
    ) -> Optional[Any]:
        """获取缓存结果"""
        
        # 生成查询向量
        if embedding is None:
            embedding = await self._embed(query)
        
        # 查找相似缓存
        for cache_key, cached_emb in self.embeddings.items():
            similarity = self._cosine_similarity(embedding, cached_emb)
            
            if similarity >= self.similarity_threshold:
                # 命中缓存
                self.cache[cache_key]['hit_count'] += 1
                self.cache[cache_key]['last_hit'] = datetime.utcnow()
                return self.cache[cache_key]['result']
        
        return None
    
    def set(self, query: str, result: Any, embedding: Optional[np.ndarray] = None):
        """设置缓存"""
        
        import hashlib
        
        cache_key = hashlib.md5(query.encode()).hexdigest()
        
        if embedding is None:
            # 同步生成 embedding（简化处理）
            embedding = np.random.randn(1536)
        
        self.cache[cache_key] = {
            'query': query,
            'result': result,
            'created_at': datetime.utcnow(),
            'hit_count': 0
        }
        self.embeddings[cache_key] = embedding
    
    async def _embed(self, text: str) -> np.ndarray:
        """生成向量"""
        # 实际实现调用 Embedding API
        return np.random.randn(1536)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
```

---

### H.5 思维链（Chain of Thought）节点

#### H.5.1 CoT 节点设计

```python
# workflow/nodes/cot_node.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class CoTStrategy(Enum):
    """思维链策略"""
    CHAIN = "chain"             # 简单链式
    TREE = "tree"               # 树状展开
    GRAPH = "graph"             # 图状推理
    SELF_REFINE = "self_refine" # 自我改进
    VERIFY = "verify"           # 验证推理


@dataclass
class Thought:
    """思维步骤"""
    step_id: str
    content: str
    reasoning: str              # 推理过程
    evidence: List[str] = field(default_factory=list)
    confidence: float = 1.0     # 置信度
    next_steps: List[str] = field(default_factory=list)  # 下一步骤 ID
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoTResult:
    """思维链结果"""
    thoughts: List[Thought]
    final_answer: Any
    confidence: float
    reasoning_chain: str        # 可读的推理链
    alternatives: List[Dict] = field(default_factory=list)  # 备选答案


class ChainOfThoughtNode:
    """思维链节点"""
    
    def __init__(self, config: Dict[str, Any]):
        self.strategy = CoTStrategy(config.get('strategy', 'chain'))
        self.max_steps = config.get('max_steps', 10)
        self.temperature = config.get('temperature', 0.7)
        self.include_alternatives = config.get('include_alternatives', True)
        self.self_refine_iterations = config.get('self_refine_iterations', 3)
    
    async def execute(
        self,
        context: Dict[str, Any],
        llm_client: Any
    ) -> CoTResult:
        """执行思维链"""
        
        query = context.get('query', '')
        
        if self.strategy == CoTStrategy.CHAIN:
            return await self._chain_thinking(query, llm_client, context)
        elif self.strategy == CoTStrategy.TREE:
            return await self._tree_thinking(query, llm_client, context)
        elif self.strategy == CoTStrategy.SELF_REFINE:
            return await self._self_refine_thinking(query, llm_client, context)
        elif self.strategy == CoTStrategy.VERIFY:
            return await self._verify_thinking(query, llm_client, context)
        else:
            return await self._graph_thinking(query, llm_client, context)
    
    async def _chain_thinking(
        self,
        query: str,
        llm_client: Any,
        context: Dict
    ) -> CoTResult:
        """链式思维"""
        
        thoughts = []
        current_step = 0
        reasoning_context = ""
        
        system_prompt = """你是一个逻辑推理专家。请逐步推理，给出每个步骤的：
1. 推理过程 (reasoning)
2. 证据或依据 (evidence)
3. 当前结论 (content)

最后给出最终答案。"""
        
        while current_step < self.max_steps:
            # 生成下一步推理
            response = await llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"问题: {query}\n\n之前的推理:\n{reasoning_context}\n\n请进行下一步推理。"}
                ],
                temperature=self.temperature
            )
            
            reasoning_text = response.choices[0].message.content
            
            # 解析推理结果
            thought = self._parse_thought(
                f"step_{current_step}",
                reasoning_text
            )
            
            thoughts.append(thought)
            reasoning_context += f"\n步骤 {current_step + 1}: {reasoning_text}"
            
            # 检查是否完成
            if self._is_conclusion(reasoning_text):
                break
            
            current_step += 1
        
        # 生成最终答案
        final_answer = await self._generate_final_answer(
            query, thoughts, llm_client
        )
        
        return CoTResult(
            thoughts=thoughts,
            final_answer=final_answer,
            confidence=self._calculate_confidence(thoughts),
            reasoning_chain=self._format_chain(thoughts)
        )
    
    async def _tree_thinking(
        self,
        query: str,
        llm_client: Any,
        context: Dict
    ) -> CoTResult:
        """树状思维 - 同时探索多个推理方向"""
        
        # 初始分支
        branches = await self._expand_branches(
            query,
            ["从A角度分析", "从B角度分析", "从C角度分析"],
            llm_client
        )
        
        # 每个分支继续扩展
        all_thoughts = []
        leaf_results = []
        
        for branch_name, branch_thoughts in branches.items():
            all_thoughts.extend(branch_thoughts)
            
            # 继续扩展叶节点
            expanded = await self._expand_leaves(
                branch_thoughts[-1] if branch_thoughts else None,
                llm_client
            )
            
            for thought in expanded:
                all_thoughts.append(thought)
            
            if expanded:
                leaf_results.append(expanded[-1].content)
        
        # 选择最佳分支
        best_result = await self._select_best_branch(
            query, leaf_results, llm_client
        )
        
        return CoTResult(
            thoughts=all_thoughts,
            final_answer=best_result,
            confidence=0.85,
            reasoning_chain=self._format_tree(all_thoughts),
            alternatives=leaf_results
        )
    
    async def _self_refine_thinking(
        self,
        query: str,
        llm_client: Any,
        context: Dict
    ) -> CoTResult:
        """自我改进思维"""
        
        # 初始答案
        initial_thoughts = []
        current_answer = await self._generate_initial_answer(
            query, llm_client
        )
        
        initial_thoughts.append(Thought(
            step_id="initial",
            content=current_answer,
            reasoning="初始答案",
            confidence=0.5
        ))
        
        # 迭代改进
        for iteration in range(self.self_refine_iterations):
            # 批评
            critique = await self._generate_critique(
                query, current_answer, llm_client
            )
            
            # 改进
            improved_answer = await self._improve_answer(
                query, current_answer, critique, llm_client
            )
            
            # 计算改进程度
            improvement = self._calculate_improvement(
                current_answer, improved_answer
            )
            
            initial_thoughts.append(Thought(
                step_id=f"refine_{iteration}",
                content=improved_answer,
                reasoning=f"改进 {iteration + 1}: {critique}",
                confidence=0.5 + (iteration + 1) * 0.15
            ))
            
            current_answer = improved_answer
            
            if improvement < 0.05:  # 收敛
                break
        
        return CoTResult(
            thoughts=initial_thoughts,
            final_answer=current_answer,
            confidence=initial_thoughts[-1].confidence,
            reasoning_chain=self._format_chain(initial_thoughts)
        )
    
    async def _verify_thinking(
        self,
        query: str,
        llm_client: Any,
        context: Dict
    ) -> CoTResult:
        """验证推理 - 先生成答案，再验证"""
        
        # 步骤1: 生成初始答案
        initial_answer = await self._generate_initial_answer(query, llm_client)
        thoughts = [Thought(
            step_id="generate",
            content=initial_answer,
            reasoning="生成初始答案",
            confidence=0.6
        )]
        
        # 步骤2: 收集证据
        evidence = await self._collect_evidence(
            query, initial_answer, llm_client
        )
        thoughts.append(Thought(
            step_id="evidence",
            content=str(evidence),
            reasoning="收集支持证据",
            evidence=evidence,
            confidence=0.7
        ))
        
        # 步骤3: 验证
        verification = await self._verify_answer(
            query, initial_answer, evidence, llm_client
        )
        thoughts.append(Thought(
            step_id="verify",
            content=verification['result'],
            reasoning=verification['reasoning'],
            confidence=verification['confidence']
        ))
        
        # 步骤4: 最终确认
        final_answer = verification['result']
        
        if not verification.get('verified', True):
            # 需要修正
            corrected = await self._correct_answer(
                query, initial_answer, verification, llm_client
            )
            thoughts.append(Thought(
                step_id="correct",
                content=corrected,
                reasoning="根据验证结果修正答案",
                confidence=0.8
            ))
            final_answer = corrected
        
        return CoTResult(
            thoughts=thoughts,
            final_answer=final_answer,
            confidence=thoughts[-1].confidence,
            reasoning_chain=self._format_chain(thoughts)
        )
    
    async def _generate_initial_answer(
        self,
        query: str,
        llm_client: Any
    ) -> str:
        """生成初始答案"""
        response = await llm_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"请回答以下问题: {query}"}
            ]
        )
        return response.choices[0].message.content
    
    async def _generate_critique(
        self,
        query: str,
        answer: str,
        llm_client: Any
    ) -> str:
        """生成批评"""
        response = await llm_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个严格的评审专家。请指出当前答案的不足之处。"},
                {"role": "user", "content": f"问题: {query}\n当前答案: {answer}\n\n请指出需要改进的地方。"}
            ]
        )
        return response.choices[0].message.content
    
    async def _improve_answer(
        self,
        query: str,
        current: str,
        critique: str,
        llm_client: Any
    ) -> str:
        """改进答案"""
        response = await llm_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个改进专家。根据评审意见改进答案。"},
                {"role": "user", "content": f"问题: {query}\n当前答案: {current}\n评审意见: {critique}\n\n请给出改进后的答案。"}
            ]
        )
        return response.choices[0].message.content
    
    async def _expand_branches(
        self,
        query: str,
        perspectives: List[str],
        llm_client: Any
    ) -> Dict[str, List[Thought]]:
        """展开分支"""
        branches = {}
        
        for perspective in perspectives:
            response = await llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": f"问题: {query}\n{perspective}，请给出分析。"}
                ]
            )
            
            branches[perspective] = [Thought(
                step_id=f"branch_{perspective}",
                content=response.choices[0].message.content,
                reasoning=perspective,
                confidence=0.7
            )]
        
        return branches
    
    async def _collect_evidence(
        self,
        query: str,
        answer: str,
        llm_client: Any
    ) -> List[str]:
        """收集证据"""
        # 简化实现
        return ["证据1", "证据2", "证据3"]
    
    async def _verify_answer(
        self,
        query: str,
        answer: str,
        evidence: List[str],
        llm_client: Any
    ) -> Dict:
        """验证答案"""
        # 简化实现
        return {
            'result': answer,
            'reasoning': '验证通过',
            'confidence': 0.85,
            'verified': True
        }
    
    def _parse_thought(
        self,
        step_id: str,
        reasoning_text: str
    ) -> Thought:
        """解析思维步骤"""
        return Thought(
            step_id=step_id,
            content=reasoning_text,
            reasoning=reasoning_text,
            confidence=0.8
        )
    
    def _is_conclusion(self, text: str) -> bool:
        """判断是否为结论"""
        conclusion_keywords = ['因此', '所以', '结论是', '最终答案', '综上所述']
        return any(keyword in text for keyword in conclusion_keywords)
    
    def _calculate_confidence(self, thoughts: List[Thought]) -> float:
        """计算置信度"""
        if not thoughts:
            return 0.0
        
        avg = sum(t.confidence for t in thoughts) / len(thoughts)
        # 考虑思维链的长度
        length_factor = min(len(thoughts) / 5, 1.0)
        
        return avg * (0.7 + 0.3 * length_factor)
    
    def _format_chain(self, thoughts: List[Thought]) -> str:
        """格式化推理链"""
        lines = []
        for i, thought in enumerate(thoughts):
            lines.append(f"步骤 {i + 1}: {thought.content}")
            if thought.evidence:
                lines.append(f"  证据: {', '.join(thought.evidence)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_tree(self, thoughts: List[Thought]) -> str:
        """格式化树状结构"""
        # 简化实现
        return self._format_chain(thoughts)
    
    def _calculate_improvement(
        self,
        old: str,
        new: str
    ) -> float:
        """计算改进程度"""
        # 简化实现
        return 0.1
    
    async def _generate_final_answer(
        self,
        query: str,
        thoughts: List[Thought],
        llm_client: Any
    ) -> str:
        """生成最终答案"""
        chain_text = self._format_chain(thoughts)
        
        response = await llm_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个总结专家。根据推理过程给出最终答案。"},
                {"role": "user", "content": f"问题: {query}\n\n推理过程:\n{chain_text}\n\n请给出最终答案。"}
            ]
        )
        
        return response.choices[0].message.content
    
    async def _expand_leaves(
        self,
        leaf: Optional[Thought],
        llm_client: Any
    ) -> List[Thought]:
        """扩展叶节点"""
        if not leaf:
            return []
        
        # 简化实现
        return [leaf]
    
    async def _select_best_branch(
        self,
        query: str,
        results: List[str],
        llm_client: Any
    ) -> str:
        """选择最佳分支"""
        if not results:
            return ""
        
        # 简化实现：返回第一个
        return results[0]
    
    async def _correct_answer(
        self,
        query: str,
        original: str,
        verification: Dict,
        llm_client: Any
    ) -> str:
        """修正答案"""
        return original
```

---

## 附录 I - 创新功能演示

### I.1 智能工作流推荐系统

```python
# workflow/recommendation/engine.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import numpy as np
from collections import defaultdict


@dataclass
class WorkflowPattern:
    """工作流模式"""
    pattern_id: str
    name: str
    description: str
    nodes: List[Dict]          # 节点配置
    usage_count: int = 0
    success_rate: float = 1.0
    avg_duration: float = 0.0


@dataclass
class Recommendation:
    """推荐结果"""
    workflow_id: Optional[str]
    template_id: Optional[str]
    pattern: Optional[WorkflowPattern]
    score: float
    reason: str
    confidence: float


class WorkflowRecommender:
    """工作流推荐引擎"""
    
    def __init__(self):
        self.patterns: Dict[str, WorkflowPattern] = {}
        self.user_preferences: Dict[int, Dict] = {}
        self.collaborative_data: Dict[str, List[str]] = defaultdict(list)
        self._load_patterns()
    
    def _load_patterns(self):
        """加载预置模式"""
        
        self.patterns = {
            'customer_support': WorkflowPattern(
                pattern_id='customer_support',
                name='智能客服流程',
                description='基于 RAG 的客户问题处理流程',
                nodes=[
                    {'type': 'input', 'name': '接收问题'},
                    {'type': 'intent', 'name': '意图识别'},
                    {'type': 'rag', 'name': '知识检索'},
                    {'type': 'llm', 'name': '生成回答'},
                    {'type': 'condition', 'name': '满意度检查'},
                    {'type': 'escalate', 'name': '人工转接'}
                ]
            ),
            'content_pipeline': WorkflowPattern(
                pattern_id='content_pipeline',
                name='内容处理流水线',
                description='多步骤内容生成和处理',
                nodes=[
                    {'type': 'input', 'name': '主题输入'},
                    {'type': 'research', 'name': '信息搜集'},
                    {'type': 'outline', 'name': '生成大纲'},
                    {'type': 'write', 'name': '撰写内容'},
                    {'type': 'review', 'name': '质量审核'},
                    {'type': 'publish', 'name': '发布'}
                ]
            ),
            'data_analysis': WorkflowPattern(
                pattern_id='data_analysis',
                name='数据分析流程',
                description='数据收集、分析和可视化',
                nodes=[
                    {'type': 'data_source', 'name': '数据源'},
                    {'type': 'extract', 'name': '数据提取'},
                    {'type': 'transform', 'name': '数据转换'},
                    {'type': 'analyze', 'name': '分析'},
                    {'type': 'visualize', 'name': '可视化'},
                    {'type': 'report', 'name': '生成报告'}
                ]
            )
        }
    
    async def recommend(
        self,
        user_id: int,
        query: str,
        context: Optional[Dict] = None
    ) -> List[Recommendation]:
        """推荐工作流"""
        
        recommendations = []
        
        # 1. 基于语义的模式匹配
        semantic_recs = await self._semantic_match(query)
        recommendations.extend(semantic_recs)
        
        # 2. 基于用户历史的协同过滤
        collaborative_recs = await self._collaborative_filter(user_id, query)
        recommendations.extend(collaborative_recs)
        
        # 3. 基于上下文的推荐
        if context:
            context_recs = self._context_based_recommend(context)
            recommendations.extend(context_recs)
        
        # 4. 去重和排序
        recommendations = self._deduplicate_and_rank(recommendations)
        
        return recommendations[:5]  # 返回 top 5
    
    async def _semantic_match(self, query: str) -> List[Recommendation]:
        """语义匹配"""
        recommendations = []
        
        # 简单的关键词匹配（实际应使用向量搜索）
        query_lower = query.lower()
        
        for pattern in self.patterns.values():
            score = 0.0
            reasons = []
            
            # 检查名称匹配
            if any(word in pattern.name.lower() for word in query_lower.split()):
                score += 0.3
                reasons.append("名称相关")
            
            # 检查描述匹配
            if any(word in pattern.description.lower() for word in query_lower.split()):
                score += 0.2
                reasons.append("描述相关")
            
            # 检查节点匹配
            for node in pattern.nodes:
                if any(word in node.get('name', '').lower() for word in query_lower.split()):
                    score += 0.1
                    reasons.append(f"包含「{node['name']}」节点")
            
            if score > 0:
                recommendations.append(Recommendation(
                    workflow_id=None,
                    template_id=None,
                    pattern=pattern,
                    score=min(score, 1.0),
                    reason="、".join(reasons[:2]),
                    confidence=score
                ))
        
        return recommendations
    
    async def _collaborative_filter(
        self,
        user_id: int,
        query: str
    ) -> List[Recommendation]:
        """协同过滤推荐"""
        
        # 查找相似用户使用过的工作流
        similar_workflows = self.collaborative_data.get(str(user_id), [])
        
        recommendations = []
        for wf_id in similar_workflows[:3]:
            recommendations.append(Recommendation(
                workflow_id=wf_id,
                template_id=None,
                pattern=None,
                score=0.6,
                reason="相似用户也在使用",
                confidence=0.6
            ))
        
        return recommendations
    
    def _context_based_recommend(
        self,
        context: Dict
    ) -> List[Recommendation]:
        """基于上下文的推荐"""
        
        recommendations = []
        
        # 根据数据类型推荐
        data_type = context.get('data_type')
        
        if data_type == 'text':
            rec = self.patterns.get('content_pipeline')
            if rec:
                recommendations.append(Recommendation(
                    workflow_id=None,
                    template_id=None,
                    pattern=rec,
                    score=0.8,
                    reason=f"适合处理 {data_type} 类型数据",
                    confidence=0.8
                ))
        elif data_type == 'structured':
            rec = self.patterns.get('data_analysis')
            if rec:
                recommendations.append(Recommendation(
                    workflow_id=None,
                    template_id=None,
                    pattern=rec,
                    score=0.8,
                    reason=f"适合处理 {data_type} 类型数据",
                    confidence=0.8
                ))
        
        return recommendations
    
    def _deduplicate_and_rank(
        self,
        recommendations: List[Recommendation]
    ) -> List[Recommendation]:
        """去重和排序"""
        
        seen = set()
        unique_recs = []
        
        for rec in recommendations:
            key = (rec.workflow_id, rec.template_id, rec.pattern.pattern_id if rec.pattern else None)
            
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
        
        # 按分数排序
        unique_recs.sort(key=lambda x: x.score, reverse=True)
        
        return unique_recs
```

---

### I.2 自适应执行策略

```python
# workflow/execution/adaptive_strategy.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio


class ExecutionStrategy(Enum):
    """执行策略"""
    FAST = "fast"               # 快速执行
    RELIABLE = "reliable"       # 可靠执行
    BALANCED = "balanced"       # 平衡策略
    RESOURCE_OPTIMIZED = "resource"  # 资源优化


@dataclass
class ExecutionMetrics:
    """执行指标"""
    start_time: datetime
    end_time: Optional[datetime] = None
    node_executions: int = 0
    total_duration: float = 0.0
    retry_count: int = 0
    error_count: int = 0
    resource_usage: Dict[str, float] = field(default_factory=dict)


@dataclass
class NodeExecution:
    """节点执行记录"""
    node_id: str
    strategy: ExecutionStrategy
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


class AdaptiveExecutionEngine:
    """自适应执行引擎"""
    
    def __init__(self):
        self.metrics_history: List[ExecutionMetrics] = []
        self.current_metrics: Optional[ExecutionMetrics] = None
    
    async def execute_adaptive(
        self,
        workflow: Dict,
        context: Dict,
        initial_strategy: ExecutionStrategy = ExecutionStrategy.BALANCED
    ) -> Dict[str, Any]:
        """自适应执行工作流"""
        
        # 1. 分析工作流特征
        workflow_profile = self._profile_workflow(workflow)
        
        # 2. 选择最优策略
        strategy = self._select_strategy(workflow_profile, context)
        
        # 3. 执行工作流
        return await self._execute_with_strategy(
            workflow, context, strategy
        )
    
    def _profile_workflow(self, workflow: Dict) -> Dict:
        """分析工作流特征"""
        
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])
        
        profile = {
            'node_count': len(nodes),
            'parallel_potential': self._calculate_parallel_potential(nodes, edges),
            'has_llm_nodes': any(n.get('type') == 'llm' for n in nodes),
            'has_io_nodes': any(n.get('type') in ['input', 'output'] for n in nodes),
            'complexity': self._calculate_complexity(nodes, edges),
            'estimated_duration': self._estimate_duration(nodes)
        }
        
        return profile
    
    def _calculate_parallel_potential(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> float:
        """计算并行潜力"""
        
        if not edges:
            return 1.0
        
        # 计算最长路径和总节点数的比例
        # 简化实现
        return min(len(nodes) / 10, 1.0)
    
    def _calculate_complexity(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> float:
        """计算复杂度"""
        
        node_complexity = sum(
            1.5 if n.get('type') in ['llm', 'code'] else 1.0
            for n in nodes
        )
        
        edge_complexity = len(edges) * 0.1
        
        return (node_complexity + edge_complexity) / max(len(nodes), 1)
    
    def _estimate_duration(self, nodes: List[Dict]) -> float:
        """估算执行时间"""
        
        duration = 0.0
        
        for node in nodes:
            node_type = node.get('type')
            
            if node_type == 'llm':
                duration += 2.0  # LLM 节点平均 2 秒
            elif node_type == 'code':
                duration += 1.0
            elif node_type == 'input':
                duration += 0.5
            else:
                duration += 0.3
        
        return duration
    
    def _select_strategy(
        self,
        profile: Dict,
        context: Dict
    ) -> ExecutionStrategy:
        """选择执行策略"""
        
        # 根据工作流特征和上下文选择策略
        
        # 如果需要快速返回
        if context.get('urgent', False):
            return ExecutionStrategy.FAST
        
        # 如果资源受限
        if context.get('resource_constraint'):
            return ExecutionStrategy.RESOURCE_OPTIMIZED
        
        # 如果是高复杂度工作流
        if profile['complexity'] > 0.8:
            return ExecutionStrategy.RELIABLE
        
        # 如果并行潜力高
        if profile['parallel_potential'] > 0.5:
            return ExecutionStrategy.BALANCED
        
        # 默认使用平衡策略
        return ExecutionStrategy.BALANCED
    
    async def _execute_with_strategy(
        self,
        workflow: Dict,
        context: Dict,
        strategy: ExecutionStrategy
    ) -> Dict:
        """使用指定策略执行"""
        
        self.current_metrics = ExecutionMetrics(start_time=datetime.utcnow())
        
        if strategy == ExecutionStrategy.FAST:
            return await self._execute_fast(workflow, context)
        elif strategy == ExecutionStrategy.RELIABLE:
            return await self._execute_reliable(workflow, context)
        elif strategy == ExecutionStrategy.RESOURCE_OPTIMIZED:
            return await self._execute_resource_optimized(workflow, context)
        else:
            return await self._execute_balanced(workflow, context)
    
    async def _execute_fast(
        self,
        workflow: Dict,
        context: Dict
    ) -> Dict:
        """快速执行 - 跳过非必要步骤"""
        
        # 只执行关键节点
        critical_nodes = [
            n for n in workflow.get('nodes', [])
            if n.get('type') in ['llm', 'input', 'output']
        ]
        
        # 并行执行独立节点
        tasks = []
        for node in critical_nodes:
            tasks.append(self._execute_node(node, context, ExecutionStrategy.FAST))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'strategy': 'fast',
            'results': results,
            'skipped_nodes': len(workflow.get('nodes', [])) - len(critical_nodes)
        }
    
    async def _execute_reliable(
        self,
        workflow: Dict,
        context: Dict
    ) -> Dict:
        """可靠执行 - 添加重试和检查点"""
        
        nodes = workflow.get('nodes', [])
        results = {}
        
        for node in nodes:
            node_id = node['id']
            
            # 最多重试 3 次
            for attempt in range(3):
                try:
                    result = await self._execute_node(
                        node, 
                        context, 
                        ExecutionStrategy.RELIABLE
                    )
                    results[node_id] = result
                    break
                except Exception as e:
                    if attempt == 2:
                        results[node_id] = {'error': str(e)}
                    await asyncio.sleep(1)  # 等待后重试
        
        return {
            'strategy': 'reliable',
            'results': results,
            'checkpoints': True
        }
    
    async def _execute_resource_optimized(
        self,
        workflow: Dict,
        context: Dict
    ) -> Dict:
        """资源优化执行"""
        
        # 实现资源感知的执行调度
        nodes = workflow.get('nodes', [])
        
        # 按资源需求分组
        low_resource = []
        high_resource = []
        
        for node in nodes:
            if node.get('type') in ['llm', 'code']:
                high_resource.append(node)
            else:
                low_resource.append(node)
        
        # 先执行低资源节点，释放资源后再执行高资源节点
        results = {}
        
        for node in low_resource:
            results[node['id']] = await self._execute_node(
                node, context, ExecutionStrategy.RESOURCE_OPTIMIZED
            )
        
        # 批量执行高资源节点（控制并发）
        batch_size = 2
        for i in range(0, len(high_resource), batch_size):
            batch = high_resource[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                self._execute_node(n, context, ExecutionStrategy.RESOURCE_OPTIMIZED)
                for n in batch
            ])
            
            for j, node in enumerate(batch):
                results[node['id']] = batch_results[j]
        
        return {
            'strategy': 'resource_optimized',
            'results': results
        }
    
    async def _execute_balanced(
        self,
        workflow: Dict,
        context: Dict
    ) -> Dict:
        """平衡执行"""
        
        # 分析依赖关系
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])
        
        # 构建依赖图
        dependencies = self._build_dependency_graph(nodes, edges)
        
        # 执行
        results = {}
        completed = set()
        
        while len(completed) < len(nodes):
            # 找到可以执行的节点（依赖都已完成）
            ready_nodes = [
                n for n in nodes
                if n['id'] not in completed and
                all(dep in completed for dep in dependencies.get(n['id'], []))
            ]
            
            if not ready_nodes:
                break
            
            # 并行执行
            batch_results = await asyncio.gather(*[
                self._execute_node(n, context, ExecutionStrategy.BALANCED)
                for n in ready_nodes
            ])
            
            for i, node in enumerate(ready_nodes):
                results[node['id']] = batch_results[i]
                completed.add(node['id'])
        
        return {
            'strategy': 'balanced',
            'results': results
        }
    
    def _build_dependency_graph(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, List[str]]:
        """构建依赖图"""
        
        dependencies = {}
        
        for node in nodes:
            dependencies[node['id']] = []
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            
            if source and target:
                if target not in dependencies:
                    dependencies[target] = []
                dependencies[target].append(source)
        
        return dependencies
    
    async def _execute_node(
        self,
        node: Dict,
        context: Dict,
        strategy: ExecutionStrategy
    ) -> Dict:
        """执行单个节点"""
        
        execution = NodeExecution(
            node_id=node['id'],
            strategy=strategy,
            start_time=datetime.utcnow()
        )
        
        try:
            # 模拟节点执行
            await asyncio.sleep(0.1)
            
            execution.status = "completed"
            execution.result = {'success': True}
            
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
        
        execution.end_time = datetime.utcnow()
        execution.duration = (execution.end_time - execution.start_time).total_seconds()
        
        self.current_metrics.node_executions += 1
        if execution.status == "failed":
            self.current_metrics.error_count += 1
        
        return execution.result if execution.result else {'error': execution.error}
```

---

## 附录 J - 泛珠三角比赛技术创新点总结

### J.1 核心技术亮点

| 序号 | 技术亮点 | 技术描述 | 创新价值 | 比赛加分 |
|------|----------|----------|----------|----------|
| 1 | **Multi-Agent 编排** | 多智能体协作系统，支持规划者、研究者、执行者等角色协同 | 解决复杂任务分解和协作难题 | ⭐⭐⭐⭐⭐ |
| 2 | **MCP 协议集成** | 模型上下文协议，标准化 AI 与外部工具连接 | 增强系统扩展性和生态集成 | ⭐⭐⭐⭐⭐ |
| 3 | **增强 Function Calling** | 动态函数调用，支持并行、条件、链式调用 | 提升 AI 工具调用能力 | ⭐⭐⭐⭐ |
| 4 | **混合搜索（Rerank）** | 向量检索 + BM25 + 重排序三阶段 | 显著提升检索准确率 | ⭐⭐⭐⭐ |
| 5 | **思维链（CoT）节点** | 支持链式、树状、自我改进等多种推理策略 | 增强复杂问题解决能力 | ⭐⭐⭐⭐⭐ |
| 6 | **自适应执行引擎** | 根据工作流特征自动选择最优执行策略 | 优化性能和可靠性平衡 | ⭐⭐⭐ |
| 7 | **语义缓存** | 基于向量相似度的智能缓存系统 | 降低延迟和成本 | ⭐⭐⭐ |
| 8 | **智能推荐系统** | 基于语义匹配和协同过滤的工作流推荐 | 提升用户体验 | ⭐⭐⭐ |
| 9 | **分布式追踪** | OpenTelemetry 标准的全链路追踪 | 企业级可观测性 | ⭐⭐⭐ |
| 10 | **流式执行** | SSE/WebSocket 实现实时流式输出 | 优秀的用户体验 | ⭐⭐⭐ |

### J.2 创新功能矩阵

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Flowly 创新功能矩阵                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│    AI 能力层                                                              │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│    │多Agent  │ │MCP协议  │ │CoT思维 │ │Function │ │混合搜索 │           │
│    │协作    │ │集成    │ │链推理  │ │调用    │ │+Rerank │           │
│    └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│         └──────────┴──────────┴──────────┴──────────┘                    │
│                              │                                          │
│                              ▼                                          │
│    工作流引擎层                                                            │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│    │自适应   │ │流式执行 │ │版本控制 │ │错误重试 │ │并行执行 │         │
│    │执行策略│ │引擎    │ │系统    │ │机制    │ │引擎    │         │
│    └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘         │
│         └──────────┴──────────┴──────────┴──────────┘                  │
│                              │                                          │
│                              ▼                                          │
│    应用体验层                                                            │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│    │智能工作 │ │可视化   │ │实时监控 │ │自然语言 │ │团队协作 │         │
│    │流推荐  │ │追踪    │ │仪表盘  │ │生成工作 │ │编辑    │         │
│    └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### J.3 技术架构亮点

#### 1. 可扩展的 AI 网关

```
用户请求
    │
    ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│模型路由 │───▶│负载均衡 │───▶│Provider │
│策略    │    │策略     │    │适配器   │
└─────────┘    └─────────┘    └─────────┘
    │                              │
    ▼                              ▼
┌─────────┐                  ┌─────────┐
│模型注册 │                  │OpenAI   │
│表      │                  │Anthropic│
└─────────┘                  │本地模型 │
                             └─────────┘
```

#### 2. 多层缓存架构

```
请求
  │
  ▼
┌─────────┐ 命中 ──▶ 返回
│ L1 内存缓存 │ 不命中
│ (进程内)   │   │
└─────────┘   ▼
              ┌─────────┐ 命中 ──▶ 返回
              │ L2 Redis │ 不命中
              │ 分布式缓存│   │
              └─────────┘   ▼
                           ┌─────────┐
                           │ L3 MySQL│
                           │ 数据库  │
                           └─────────┘
```

#### 3. 流式执行架构

```
前端发起执行请求
      │
      ▼
┌─────────────┐
│ Django Views │───▶ 启动 Celery 任务
└─────────────┘
      │
      ▼
┌─────────────┐     ┌─────────────┐
│ Celery Worker│────▶│ 执行工作流  │
│ 异步任务    │     │ 更新进度    │
└─────────────┘     └─────────────┘
      │                   │
      │ 实时进度           │
      ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ Redis Pub/Sub│◀───│ WebSocket   │
│ 消息发布    │     │ 推送到前端  │
└─────────────┘     └─────────────┘
```

### J.4 比赛答辩重点

#### 演示重点 1：Multi-Agent 协作演示

**场景**：让多个 Agent 协作完成一个复杂任务

```
1. 展示 Agent 团队配置界面
2. 演示任务规划（Planner Agent 分析任务）
3. 演示信息检索（Researcher Agent 收集资料）
4. 演示结果生成（Writer Agent 生成报告）
5. 演示质量审核（Critic Agent 审核改进）
6. 展示协作过程可视化追踪
```

#### 演示重点 2：思维链推理展示

**场景**：复杂问题的逐步推理过程

```
1. 输入复杂问题
2. 展示思维链可视化（每个推理步骤）
3. 展示置信度变化
4. 对比有/无思维链的效果差异
```

#### 演示重点 3：智能搜索对比

**场景**：展示混合搜索 + Reranking 的效果

```
1. 纯向量搜索结果
2. 纯关键词搜索结果
3. 混合搜索结果
4. Reranking 后的结果
5. 对比准确率提升
```

### J.5 项目差异化优势

| 维度 | 其他平台 | Flowly 优势 |
|------|----------|------------|
| **Agent 协作** | 仅支持单 Agent | 支持 Multi-Agent 协作编排 |
| **协议标准** | 私有 API | 支持 MCP 协议，生态兼容 |
| **推理能力** | 无 CoT | 内置多种思维链策略 |
| **搜索能力** | 简单向量检索 | 混合搜索 + Reranking |
| **执行策略** | 固定执行 | 自适应多策略执行 |
| **缓存机制** | 无/简单 | 语义缓存智能命中 |
| **工具调用** | 基础 FC | 增强型 Function Calling |
| **追踪系统** | 基础日志 | 全链路分布式追踪 |

### J.6 技术栈汇总

```
┌─────────────────────────────────────────────────────────────────┐
│                        核心技术栈                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    前沿 AI 技术                            │  │
│  │  • Multi-Agent 编排框架    • MCP 协议集成                   │  │
│  │  • 思维链 (CoT) 推理       • Reranking 混合搜索             │  │
│  │  • 增强 Function Calling   • 语义缓存                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    核心框架                                │  │
│  │  • Django 5 + DRF        • Vue 3 + Composition API        │  │
│  │  • LangChain/LlamaIndex  • Celery + Redis                  │  │
│  │  • Django Channels       • MySQL + Qdrant                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    基础设施                                │  │
│  │  • Docker 容器化         • Nginx 反向代理                  │  │
│  │  • CI/CD 自动化          • Prometheus 监控                 │  │
│  │  • OpenTelemetry 追踪    • ELK 日志聚合                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 附录 K - 快速参考卡片

### K.1 常用命令

```bash
# 后端启动
cd Backend
python manage.py runserver

# 前端启动
cd Frontend
npm run dev

# Celery Worker 启动
celery -A config worker -l info

# Redis 启动
redis-server

# 运行测试
python manage.py test

# 数据库迁移
python manage.py makemigrations
python manage.py migrate
```

### K.2 API 端点速查

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/workflows/` | GET/POST | 工作流列表/创建 |
| `/api/workflows/{id}/` | GET/PUT/DELETE | 工作流详情 |
| `/api/workflows/{id}/execute/` | POST | 执行工作流 |
| `/api/agents/` | GET/POST | Agent 列表/创建 |
| `/api/agents/{id}/chat/` | POST | Agent 对话 |
| `/api/knowledge/search/` | POST | 知识检索 |
| `/api/mcp/tools/` | GET | MCP 工具列表 |
| `/api/search/hybrid/` | POST | 混合搜索 |

### K.3 环境变量配置

```bash
# .env 文件
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=flowly_db
DB_USER=root
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=3306

# Redis
REDIS_URL=redis://localhost:6379/0

# AI 模型
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# 向量数据库
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

*祝你比赛顺利！*

---

> **提示**：以上创新技术内容可根据比赛需要进行选择和调整。建议重点展示 2-3 个核心创新点，配合 Demo 演示效果更佳。
