# Phase 5: DevOps 与文档完善详细方案

> 项目: Flowly-now  
> 技术栈: Django 5.0+ / Vue 3 / Docker Compose / GitHub Actions  
> 创建日期: 2026-06-03

---

## 一、CI/CD 完善方案

### 1.1 现状分析

**已配置的工作流 (`.github/workflows/ci.yml`):**

| Job | 状态 | 描述 |
|-----|------|------|
| `backend-test` | ✅ 完整 | Python 3.12, MySQL 8.0, Redis 7, pytest + coverage |
| `frontend-test` | ✅ 完整 | Node 20, npm ci, lint, vitest coverage |
| `docker-build` | ⚠️ 占位 | 仅输出日志，无实际部署命令 |
| `deploy-staging` | ❌ 空 | 仅注释占位 |
| `deploy-production` | ❌ 空 | 仅注释占位 |

**关键缺陷:**

1. **缺少依赖锁定**: `requirements.txt` 使用浮动版本 (`>=5.0,<6.0`)
2. **部署命令缺失**: staging/production 部署均为空实现
3. **缺少环境变量管理**: 无 secrets 配置指导
4. **缺少 CD 触发条件**: 未配置 tag 发布的 production 部署
5. **缺少回滚机制**: 无版本回滚流程
6. **缺少通知集成**: 无 Slack/Discord 部署通知

### 1.2 缺失流程清单

| 流程 | 优先级 | 实现方案 |
|------|--------|----------|
| requirements.lock 生成 | P1 | 使用 `pip-compile` 生成锁定版本 |
| Staging 自动部署 | P1 | SSH 到服务器 + docker-compose pull |
| Production 蓝绿部署 | P1 | Docker tag 管理 + 健康检查 |
| Docker 镜像版本标签 | P1 | 添加 `latest`, `staging`, `v*` 标签 |
| 回滚脚本 | P2 | 保存历史镜像 + 一键回滚 |
| 部署通知 | P2 | Slack/Discord webhook 集成 |
| 安全扫描 | P2 | Trivy 镜像扫描集成 |
| 依赖更新工作流 | P3 | Dependabot 配置 |

### 1.3 整改执行

**Step 1: 添加 requirements.lock**
```bash
# 安装 pip-tools
pip install pip-tools
# 生成锁定文件
pip-compile requirements.in -o requirements.lock
```

**Step 2: 创建部署工作流 (`.github/workflows/deploy.yml`)**
- 新建独立部署工作流
- 添加 staging 环境: `on: push: branches: [develop]`
- 添加 production 环境: `on: release: types: [published]`
- 实现 SSH 部署脚本

**Step 3: 添加 Docker 安全扫描**
```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: '${{ secrets.DOCKERHUB_USERNAME }}/flowly-backend:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
```

---

## 二、依赖管理方案

### 2.1 当前状态

**Python 依赖 (`requirements.txt` - 47行):**
```
核心框架: Django>=5.0,<6.0, djangorestframework>=3.14
数据库: mysqlclient>=2.2, django-redis>=5.4
异步任务: celery>=5.3, redis>=5.0, flower>=2.0
WebSocket: channels>=4.0, channels-redis>=4.1, daphne>=4.0
AI集成: anthropic>=0.18, langchain>=0.1, openai>=1.0
其他: PyJWT>=2.8, PyYAML>=6.0, httpx>=0.26
测试: pytest>=7.4, pytest-django>=4.7, pytest-cov>=4.1
```

**Node 依赖 (`Frontend/package.json`):**
```
框架: vue@^3.4.21, vue-router@^4.3.0, pinia@^2.1.7
UI: element-plus@^2.5.6, @element-plus/icons-vue
可视化: @vue-flow/core@^1.33.5, echarts@^5.5.0, chart.js@^4.5.1
工具: axios@^1.6.8, dayjs@^1.11.10, js-cookie@^3.0.5
构建: vite@^5.1.6, @vitejs/plugin-vue@^5.0.4
测试: vitest@^1.3.1, @playwright/test@^1.42.1
```

### 2.2 存在的问题

| 问题 | 影响 | 整改方案 |
|------|------|----------|
| requirements.txt 无锁版本 | CI 可能安装不一致版本 | 生成 requirements.lock |
| 无 Backend/requirements.txt | Dockerfile 引用路径错误 | 创建独立依赖文件 |
| package-lock.json 未确认 | 需验证是否正确生成 | 检查并规范化 |
| 无依赖审计 | 潜在安全漏洞 | 添加 pip-audit/npm audit |

### 2.3 整改执行

**Step 1: 创建 Backend/requirements.txt**
当前 `requirements.txt` 位于项目根目录，但 Dockerfile 引用 `Backend/requirements.txt`，需要统一或修正路径。

**Step 2: 生成锁定文件**
```bash
# Python
pip-compile requirements.in -o requirements.lock

# Node (确认存在)
cd Frontend && npm install --package-lock-only
```

**Step 3: 添加依赖审计**
```yaml
# .github/workflows/audit.yml
- name: Security audit
  run: |
    pip-audit || true
    npm audit --audit-level=high
```

---

## 三、监控与日志方案

### 3.1 当前实现 (`Backend/monitoring/`)

**已实现模块:**

| 模块 | 文件 | 功能 |
|------|------|------|
| 模型 | `models.py` | ExecutionLog, AlertRule, Alert, Metric, NotificationChannel, Notification |
| 视图 | `views.py` | API 端点 |
| 序列化 | `serializers.py` | DRF 序列化器 |
| URL路由 | `urls.py` | 路由配置 |
| 任务 | `tasks.py` | Celery 异步任务 |
| 信号 | `signals.py` | Django 信号集成 |
| 管理 | `admin.py` | Django Admin |

### 3.2 缺失功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 日志聚合 | P1 | 当前仅 DB 存储，无 ELK/Loki 集成 |
| 指标可视化 | P1 | 无 Grafana 仪表板 |
| 告警通知 | P2 | 模型存在但通知发送未实现 |
| 链路追踪 | P2 | 无 OpenTelemetry/Jaeger |
| 性能监控 | P2 | 无 APM 集成 |
|Flower集成 | P2 | requirements.txt 包含但未配置 |

### 3.3 整改执行

**Step 1: 添加日志配置**
```python
# config/logging.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'json'},
        'file': {'class': 'logging.handlers.RotatingFileHandler', 'filename': 'logs/app.log'},
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
}
```

**Step 2: 添加健康检查端点**
```python
# Backend/health/views.py
from django.http import JsonResponse
from django.db import connection
from redis import Redis

def health_check(request):
    checks = {
        'database': check_database(),
        'redis': check_redis(),
    }
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return JsonResponse({'status': status, 'checks': checks}, status=200 if status == 'healthy' else 503)
```

**Step 3: 配置 Flower**
```yaml
# docker-compose.yml 添加
flower:
  command: celery -A config flower --port=5555
  ports:
    - "5555:5555"
```

---

## 四、文档重构方案

### 4.1 当前 Docs 目录结构

```
Docs/
├── phases/                      # 阶段文档
│   ├── PHASE-0-SECURITY-HARDENING.md
│   ├── PHASE-3-FRONTEND-ARCH.md
│   └── PHASE-5-DEVOPS-DOCS.md
├── api/                        # API 文档
│   ├── api-spec.yaml
│   ├── api-types.ts
│   ├── API-*.md
│   └── api-schemas.json
├── tasks/                      # 任务追踪
│   ├── TASK-*.md (6个文件)
│   └── README.md
├── superpowers/plans/          # Agent 规划
│   └── 2026-05-18-*.md
├── *.md                        # 根目录文档
│   ├── PROJECT-*.md
│   ├── setup-guide.md
│   └── plan.md
├── task.json
└── [学生作业文档]               # 待清理
    ├── 刘院明*.md
    ├── 徐正德*.md
    └── ...
```

### 4.2 问题识别

| 问题 | 分类 | 处理方案 |
|------|------|----------|
| 学生作业文档混杂 | 清理 | 移动到 `Docs/archive/student-assignments/` |
| 根目录文档过多 | 重构 | 保留核心文档，移动其他到 `Docs/archive/` |
| 文档版本不同步 | 规范 | 创建文档更新 checklist |
| 缺少部署文档 | 补全 | 创建 `Docs/deployment/` 目录 |

### 4.3 目标目录结构

```
Docs/
├── README.md                   # 文档索引 (新建)
├── guides/                     # 使用指南
│   ├── getting-started.md
│   ├── deployment/            # 部署指南 (新建)
│   │   ├── local-dev.md
│   │   ├── docker.md
│   │   └── production.md
│   └── troubleshooting.md
├── api/                        # API 文档 (保留)
├── phases/                     # 阶段文档 (保留)
├── tasks/                      # 任务追踪 (保留)
├── archive/                    # 归档 (新建)
│   ├── student-assignments/   # 学生作业 (移动)
│   └── legacy/                # 历史版本文档 (移动)
└── superpowers/               # Agent 规划 (保留)
```

### 4.4 执行步骤

**Step 1: 创建新目录结构**
```bash
mkdir -p Docs/guides/deployment
mkdir -p Docs/archive/student-assignments
mkdir -p Docs/archive/legacy
```

**Step 2: 移动学生作业文档**
```bash
git mv "Docs/刘院明 24230701024测试CI-CD与生产部署.md" "Docs/archive/student-assignments/"
git mv "Docs/徐正德24230701033监控与NL生成工作流.md" "Docs/archive/student-assignments/"
git mv "Docs/马运福24230701027AI_Agent与LLM网关.md" "Docs/archive/student-assignments/"
# ... 其他学生文档
```

**Step 3: 创建 Docs/README.md**
```markdown
# Flowly 项目文档

## 目录结构

- [快速开始](guides/getting-started.md)
- [部署指南](guides/deployment/)
- [API 文档](api/)
- [阶段文档](phases/)
- [任务追踪](tasks/)
```

---

## 五、执行检查清单

### CI/CD 完善

- [ ] 创建 `requirements.lock` 锁定 Python 依赖版本
- [ ] 确认/修正 `Backend/requirements.txt` 路径问题
- [ ] 创建 `.github/workflows/deploy.yml` 部署工作流
- [ ] 添加 Docker 镜像版本标签策略
- [ ] 实现 Staging 环境自动部署
- [ ] 实现 Production 环境手动触发部署
- [ ] 添加 Trivy 安全扫描
- [ ] 添加部署通知 (Slack/Discord)
- [ ] 验证 CI 流程通过

### 依赖管理

- [ ] 生成 `requirements.lock`
- [ ] 规范化 Python 依赖文件位置
- [ ] 确认 `Frontend/package-lock.json` 存在
- [ ] 添加依赖安全审计工作流
- [ ] 清理 `requirements.txt` 中未使用的依赖

### 监控与日志

- [ ] 添加结构化日志配置
- [ ] 实现 `/health` 健康检查端点
- [ ] 集成 Flower Celery 监控
- [ ] 创建 Grafana 仪表板配置
- [ ] 实现告警通知发送逻辑
- [ ] 配置日志轮转策略

### 文档重构

- [ ] 创建 `Docs/guides/` 目录结构
- [ ] 编写 `Docs/guides/getting-started.md`
- [ ] 编写 `Docs/guides/deployment/docker.md`
- [ ] 编写 `Docs/guides/deployment/production.md`
- [ ] 创建 `Docs/README.md` 文档索引
- [ ] 移动学生作业文档到 `Docs/archive/student-assignments/`
- [ ] 清理历史文档到 `Docs/archive/legacy/`

### 验收标准

- [ ] CI/CD 流水线全部 Job 通过
- [ ] Python 依赖版本锁定
- [ ] Docker 镜像无安全漏洞 (Critical/High)
- [ ] 健康检查端点可访问
- [ ] 文档结构清晰，可快速定位
- [ ] 部署文档覆盖本地/Docker/生产环境

---

## 六、优先级排序

| 优先级 | 任务 | 工作量 | 价值 |
|--------|------|--------|------|
| P0 | 创建 requirements.lock | 0.5h | 保障 CI 一致性 |
| P0 | 修复 CI/CD 占位命令 | 1h | 启用自动部署 |
| P1 | 创建部署文档 | 2h | 降低运维成本 |
| P1 | 添加健康检查 | 1h | 部署必备 |
| P2 | Docker 安全扫描 | 1h | 提升安全性 |
| P2 | 文档重构 | 2h | 提升可维护性 |
| P3 | 监控可视化 | 4h | 提升可观测性 |

---

## 七、风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 部署脚本需要服务器访问权限 | 阻塞生产部署 | 先实现 Staging 部署 |
| 学生作业文档可能包含重要信息 | 误删关键内容 | 先备份再移动 |
| Docker 镜像大小影响构建速度 | CI 时间增加 | 使用多阶段构建优化 |
