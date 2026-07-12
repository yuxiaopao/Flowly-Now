# Flowly 配置文件全集索引

> 本文档按类别汇总项目中所有配置文件及其用途，方便集中查阅。
> 所有路径均为项目根目录 `e:\Flowly-now\` 的相对路径。

---

## 一、根目录配置（构建/运行级）

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [.gitignore](file:///e:/Flowly-now/.gitignore) | Git 忽略规则 | Python 缓存、虚拟环境、IDE 文件、.env、Celery 文件 |
| [requirements.txt](file:///e:/Flowly-now/requirements.txt) | Python 依赖清单 | Django 5.x、DRF、Celery、Channels、LangChain、OpenAI、PyTorch 等 57 行 |
| [requirements.in](file:///e:/Flowly-now/requirements.in) | pip-compile 源文件 | 与 requirements.txt 几乎相同，多了一行 diffusers git 依赖（冗余） |
| [pytest.ini](file:///e:/Flowly-now/pytest.ini) | Python 测试配置 | DJANGO_SETTINGS_MODULE=config.settings，测试路径 tests/backend |
| [pyrightconfig.json](file:///e:/Flowly-now/pyrightconfig.json) | Python 类型检查 | Python 3.12，include Backend/，typeCheckingMode 关闭 |
| [.env.example](file:///e:/Flowly-now/.env.example) | 环境变量模板 | 数据库/Redis/AI 模型/前端 API/日志 等 110 行 |

### 根目录 Agent / IDE 规则文件

| 文件 | 用途 | 说明 |
|------|------|------|
| [AGENTS.md](file:///e:/Flowly-now/AGENTS.md) | **全局开发规范（最完整）** | 10 节强制规则：巡检/死代码/硬编码/规范/流程/交互/Chrome MCP |
| [.cursorrules](file:///e:/Flowly-now/.cursorrules) | Cursor IDE 规则 | 与 AGENTS.md 高度重复（少第十节 Chrome MCP 规范） |
| [.cursor/rules/global-rules.md](file:///e:/Flowly-now/.cursor/rules/global-rules.md) | Cursor 规则目录副本 | 与 .cursorrules **完全一致**（第三份冗余） |
| [.mcp.json](file:///e:/Flowly-now/.mcp.json) | MCP 服务器配置 | 4 个服务：playwright / ollama-coder / chrome-devtools / codegraphcontext |
| [.claude/settings.local.json](file:///e:/Flowly-now/.claude/settings.local.json) | Claude 本地权限 | Bash 白名单、MCP 工具调用权限、技能启用列表 |
| [skills-lock.json](file:///e:/Flowly-now/skills-lock.json) | 技能版本锁定 | design-taste-frontend 技能版本 |
| [.agents/skills/](file:///e:/Flowly-now/.agents/skills/) | 技能定义目录 | 5 个自定义技能 (design-taste-frontend / frontend-design / impeccable / ui-ux-pro-max / web-design-guidelines) |

---

## 二、前端配置 (Frontend/)

### 构建与编译

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Frontend/package.json](file:///e:/Flowly-now/Frontend/package.json) | 前端依赖与脚本 | Vue 3.4 / Vite 5 / Element Plus 2.5 / Pinia 2.1 / Axios 1.6，9 个 npm 脚本 |
| [Frontend/vite.config.js](file:///e:/Flowly-now/Frontend/vite.config.js) | Vite 构建配置 | 端口 5200，路径别名 `@` → src，代码分包（element-plus/vue-flow/echarts） |
| [Frontend/tsconfig.json](file:///e:/Flowly-now/Frontend/tsconfig.json) | TypeScript 配置 | strict 模式，ES2020，moduleResolution bundler，noEmit |
| [Frontend/tsconfig.node.json](file:///e:/Flowly-now/Frontend/tsconfig.node.json) | TypeScript Node 配置 | composite 模式，仅含 vite.config 文件 |

### 代码质量

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Frontend/.eslintrc.cjs](file:///e:/Flowly-now/Frontend/.eslintrc.cjs) | ESLint 规则 | eslint:recommended + vue/vue3-recommended，关闭 multi-word-component-names |

### 测试

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Frontend/vitest.config.ts](file:///e:/Flowly-now/Frontend/vitest.config.ts) | Vitest 单元测试配置 | jsdom 环境，V8 覆盖率，10s 超时 |
| [Frontend/playwright.config.js](file:///e:/Flowly-now/Frontend/playwright.config.js) | Playwright E2E 配置 | 3 浏览器并行，baseURL localhost:5200，自动启动 dev server |

### 应用配置

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Frontend/src/config/index.js](file:///e:/Flowly-now/Frontend/src/config/index.js) | **前端全局配置入口** | API 地址/前缀/超时、WS URL、向量存储默认值、分页、LLM 默认参数、文档链接 |
| [Frontend/src/config/toolConfig.js](file:///e:/Flowly-now/Frontend/src/config/toolConfig.js) | 工具与模型配置 | 7 种工具中文标签，10 种默认模型选项 |

### 环境变量

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Frontend/.env.example](file:///e:/Flowly-now/Frontend/.env.example) | 前端环境变量模板 | VITE_API_URL / VITE_API_PREFIX / VITE_WS_URL / 向量存储 / 域名 / OAuth |
| [Frontend/.env.production](file:///e:/Flowly-now/Frontend/.env.production) | 生产环境变量 | VITE_API_URL=https://api.flowly.example.com，关闭 Debug |

### 其他

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Frontend/.gitignore](file:///e:/Flowly-now/Frontend/.gitignore) | 前端 Git 忽略规则 | dist/、node_modules/、.env |
| [Frontend/skills-lock.json](file:///e:/Flowly-now/Frontend/skills-lock.json) | 前端技能锁 | 7 个测试技能（api-contract-testing / api-testing / frontend-testing 等） |
| [Frontend/.cgcignore](file:///e:/Flowly-now/Frontend/.cgcignore) | CodeGraphContext 忽略 | 排除索引的目录 |
| [Frontend/nginx/frontend.conf](file:///e:/Flowly-now/Frontend/nginx/frontend.conf) | 前端 Nginx 配置 | 静态文件服务 + SPA 路由回退 |

---

## 三、后端配置 (Backend/)

### Django 核心

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Backend/config/settings.py](file:///e:/Flowly-now/Backend/config/settings.py) | **Django 核心配置（558 行）** | 安全/Debug/数据库/Jazzmin/DRF/CORS/Channels/Celery/AI 模型/NL-Workflow/日志，22 个 INSTALLED_APPS |
| [Backend/config/urls.py](file:///e:/Flowly-now/Backend/config/urls.py) | Django URL 路由入口 | 所有 API 前缀注册（/api/v1/、/api/、/admin/） |
| [Backend/config/asgi.py](file:///e:/Flowly-now/Backend/config/asgi.py) | ASGI 应用入口 | 组合 4 个 App 的 WebSocket 路由（workflows/training/codegraph/agents） |
| [Backend/config/constants.py](file:///e:/Flowly-now/Backend/config/constants.py) | 常量枚举 | WorkflowStatus、NodeType（43 种）、ExecutionStatus、TriggerType 等 |
| [Backend/config/renderers.py](file:///e:/Flowly-now/Backend/config/renderers.py) | 统一响应渲染器 | 包装为 `{code, message, data}` 格式 |
| [Backend/config/exception_handlers.py](file:///e:/Flowly-now/Backend/config/exception_handlers.py) | 全局异常处理器 | DRF 异常 → `{code, message, data:null, errors}` |

### 测试

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Backend/pytest.ini](file:///e:/Flowly-now/Backend/pytest.ini) | 后端 pytest 配置 | — |
| [Backend/conftest.py](file:///e:/Flowly-now/Backend/conftest.py) | 后端测试 fixtures | — |

### 环境与依赖

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Backend/.env.example](file:///e:/Flowly-now/Backend/.env.example) | 后端环境变量模板 | — |
| [Backend/requirements.txt](file:///e:/Flowly-now/Backend/requirements.txt) | 后端 Python 依赖 | — |

### CodeGraphContext

| 文件 | 用途 |
|------|------|
| [Backend/.cgcignore](file:///e:/Flowly-now/Backend/.cgcignore) | 根 .cgcignore |
| [Backend/config/.cgcignore](file:///e:/Flowly-now/Backend/config/.cgcignore) | config 目录忽略 |
| [Backend/core/.cgcignore](file:///e:/Flowly-now/Backend/core/.cgcignore) | core 目录忽略 |

---

## 四、Docker 部署配置 (docker/)

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [docker/.env.example](file:///e:/Flowly-now/docker/.env.example) | Docker 环境变量模板 | 生产部署变量 |
| [docker/Dockerfile.backend](file:///e:/Flowly-now/docker/Dockerfile.backend) | 后端镜像 | Django + Daphne (ASGI) |
| [docker/Dockerfile.frontend](file:///e:/Flowly-now/docker/Dockerfile.frontend) | 前端镜像 | Nginx + 构建好的静态文件 |
| [docker/Dockerfile.nginx](file:///e:/Flowly-now/docker/Dockerfile.nginx) | Nginx 镜像 | 反向代理配置 |
| [docker/nginx/conf.d/default.conf](file:///e:/Flowly-now/docker/nginx/conf.d/default.conf) | Nginx 默认站点 | — |
| [docker/nginx/conf.d/frontend.conf](file:///e:/Flowly-now/docker/nginx/conf.d/frontend.conf) | Nginx 前端站点 | — |
| [docker/redis/redis.conf](file:///e:/Flowly-now/docker/redis/redis.conf) | Redis 配置 | — |

---

## 五、测试配置 (tests/)

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [tests/e2e/.env.example](file:///e:/Flowly-now/tests/e2e/.env.example) | E2E 测试环境变量 | — |
| [tests/e2e/pytest.ini](file:///e:/Flowly-now/tests/e2e/pytest.ini) | E2E 测试配置 | — |
| [tests/e2e/requirements-e2e.txt](file:///e:/Flowly-now/tests/e2e/requirements-e2e.txt) | E2E 测试依赖 | — |
| [tests/frontend/jest.config.json](file:///e:/Flowly-now/tests/frontend/jest.config.json) | 前端 Jest 配置 | — |
| [tests/frontend/babel.config.js](file:///e:/Flowly-now/tests/frontend/babel.config.js) | Babel 配置 | — |
| [tests/frontend/package.json](file:///e:/Flowly-now/tests/frontend/package.json) | 前端测试依赖 | — |

---

## 六、桌面端配置 (Desktop/)

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [Desktop/package.json](file:///e:/Flowly-now/Desktop/package.json) | Electron 桌面应用 | GPU 加速 YOLO 训练执行器，支持 Win/Mac/Linux 构建 |

---

## 七、CI/CD 配置

| 文件 | 用途 | 关键内容 |
|------|------|----------|
| [.github/workflows/ci.yml](file:///e:/Flowly-now/.github/workflows/ci.yml) | GitHub Actions CI | — |

---

## 八、环境变量文件汇总 (6 个 .env.example + 1 个 .env.production)

| # | 文件 | 作用域 |
|---|------|--------|
| 1 | [.env.example](file:///e:/Flowly-now/.env.example) | 项目全局 |
| 2 | [Backend/.env.example](file:///e:/Flowly-now/Backend/.env.example) | 后端 |
| 3 | [Frontend/.env.example](file:///e:/Flowly-now/Frontend/.env.example) | 前端开发 |
| 4 | [Frontend/.env.production](file:///e:/Flowly-now/Frontend/.env.production) | 前端生产 |
| 5 | [docker/.env.example](file:///e:/Flowly-now/docker/.env.example) | Docker 部署 |
| 6 | [tests/e2e/.env.example](file:///e:/Flowly-now/tests/e2e/.env.example) | E2E 测试 |

> ⚠️ 6 个 .env.example 存在内容冗余，后续可考虑合并精简。

---

## 九、Git 忽略文件

| 文件 | 作用域 |
|------|--------|
| [.gitignore](file:///e:/Flowly-now/.gitignore) | 项目全局 |
| [Frontend/.gitignore](file:///e:/Flowly-now/Frontend/.gitignore) | 前端 |

---

## 十、Python 依赖文件

| 文件 | 说明 |
|------|------|
| [requirements.txt](file:///e:/Flowly-now/requirements.txt) | 根依赖清单 |
| [requirements.in](file:///e:/Flowly-now/requirements.in) | pip-compile 源（与 .txt 冗余） |
| [Backend/requirements.txt](file:///e:/Flowly-now/Backend/requirements.txt) | 后端依赖 |
| [tests/e2e/requirements-e2e.txt](file:///e:/Flowly-now/tests/e2e/requirements-e2e.txt) | E2E 测试依赖 |

---

## 十一、已发现的冗余问题

| 问题 | 涉及文件 | 建议 |
|------|----------|------|
| 规则文件三层冗余 | AGENTS.md / .cursorrules / .cursor/rules/global-rules.md | 保留 AGENTS.md，删除另外两份 |
| Python 依赖文件冗余 | requirements.txt / requirements.in | 保留 .txt，删除 .in 或将 diffusers git 依赖合并到 .txt |
| 环境变量模板 6 份 | 各目录 .env.example | 可合并为一个根级 .env.example |
| 前端类型重复定义 | types/api.ts / types/request.d.ts | 统一到一个文件 |

---

## 十二、配置热力图（修改频率预估）

```
高频修改（开发阶段）:
  Frontend/src/config/index.js       ← API 地址/模型/分页
  Backend/config/settings.py         ← 数据库/Redis/AI Key
  各 .env 文件                        ← 环境切换

中频修改（迭代阶段）:
  Frontend/vite.config.js            ← 代理/端口/分包
  Frontend/package.json              ← 依赖增减
  Backend/config/constants.py        ← 节点类型/状态枚举
  Backend/config/urls.py             ← 路由注册

低频修改（稳定后）:
  Docker 配置                         ← 镜像/端口
  CI/CD 配置                          ← 流水线
  ESLint/TS/Pytest 配置               ← 代码规范
```
