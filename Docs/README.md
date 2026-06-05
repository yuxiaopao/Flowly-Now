# Flowly 项目文档

> Flowly 是一个 AI Agent 工作流编排平台，支持多模型统一管理、可视化流程编辑和自然语言工作流生成。

## 目录结构

```
Docs/
├── README.md                  # 本文档
├── guides/                   # 使用指南
│   ├── getting-started.md     # 快速开始
│   └── deployment/            # 部署指南
│       ├── local-dev.md      # 本地开发
│       └── docker.md         # Docker 部署
├── api/                      # API 文档
│   ├── api-spec.yaml         # OpenAPI 规范
│   ├── api-types.ts          # TypeScript 类型
│   └── API-*.md              # API 使用指南
├── phases/                   # 项目改进阶段文档
│   ├── PHASE-0-SECURITY-HARDENING.md
│   ├── PHASE-1-TEST-COVERAGE.md
│   ├── PHASE-2-HARDCODE-QUALITY.md
│   ├── PHASE-3-FRONTEND-ARCH.md
│   └── PHASE-5-DEVOPS-DOCS.md
├── tasks/                    # 任务追踪
│   ├── README.md
│   └── TASK-*.md
├── superpowers/plans/        # Agent 规划
└── archive/                  # 归档
    ├── student-assignments/  # 历史学生作业
    └── legacy/               # 历史版本文档
```

## 快速导航

| 场景 | 文档 |
|------|------|
| 新手入门 | [快速开始](guides/getting-started.md) |
| 本地开发 | [本地开发指南](guides/deployment/local-dev.md) |
| Docker 部署 | [Docker 部署](guides/deployment/docker.md) |
| API 文档 | [API 参考](api/) |
| 项目改进计划 | [阶段文档](phases/) |
| 任务追踪 | [任务列表](tasks/) |

## 项目技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Django 5.0 + Django REST Framework |
| 数据库 | MySQL 8.0 + PostgreSQL (pgvector) |
| 异步任务 | Celery + Redis |
| 实时通信 | Channels + WebSocket |
| 前端框架 | Vue 3 + Vite + Pinia |
| AI 集成 | LangChain + OpenAI + Anthropic |
| 部署 | Docker Compose + GitHub Actions |
