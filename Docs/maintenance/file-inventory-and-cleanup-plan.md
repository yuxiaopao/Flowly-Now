# Flowly-now 项目文件清单与整理建议

生成日期：2026-06-12

---

## 一、文件分类总览

### 1. 后端核心代码（Django Backend）

> 路径：`Backend/` - Django 项目主体，共 28 个应用模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `admin` | `Backend/admin/` | 管理后台入口 |
| `agents` | `Backend/agents/` | AI Agent 管理（含 Desktop、Multi-Agent） |
| `annotations` | `Backend/annotations/` | 数据标注模块 |
| `augmentation` | `Backend/augmentation/` | 数据增强 |
| `billing` | `Backend/billing/` | 计费模块 |
| `branding` | `Backend/branding/` | 品牌定制 |
| `codegraph` | `Backend/codegraph/` | 代码图谱（WebSocket） |
| `config` | `Backend/config/` | Django 配置（settings、celery、asgi） |
| `core` | `Backend/core/` | 核心工具类 |
| `dataset_recommend` | `Backend/dataset_recommend/` | 数据集推荐 |
| `datasets` | `Backend/datasets/` | 数据集管理 |
| `evaluation` | `Backend/evaluation/` | 模型评估 |
| `features` | `Backend/features/` | 特性开关 |
| `gateway` | `Backend/gateway/` | LLM 网关服务 |
| `integrations` | `Backend/integrations/` | 三方集成 |
| `marketplace` | `Backend/marketplace/` | 模板市场 |
| `monitoring` | `Backend/monitoring/` | 监控模块 |
| `nl_to_workflow` | `Backend/nl_to_workflow/` | 自然语言转工作流（核心） |
| `prompts` | `Backend/prompts/` | 提示词管理 |
| `rag` | `Backend/rag/` | RAG 检索增强 |
| `templates` | `Backend/templates/` | 模板管理 |
| `tenants` | `Backend/tenants/` | 多租户 |
| `training` | `Backend/training/` | 模型训练（WebSocket） |
| `users` | `Backend/users/` | 用户认证 |
| `utils` | `Backend/utils/` | 工具函数（缓存、中间件、验证器） |
| `website_generator` | `Backend/website_generator/` | 网站生成器 |
| `workflows` | `Backend/workflows/` | 工作流引擎（核心） |
| `scripts` | `Backend/scripts/` | 运维/检查脚本 |
| `reports` | `Backend/reports/` | API 检查报告（临时） |

**核心入口文件**：`Backend/manage.py`、`Backend/conftest.py`、`Backend/requirements.txt`、`Backend/.env.example`

---

### 2. 前端核心代码（Vue.js Frontend）

> 路径：`Frontend/` - Vue 3 + Vite + TypeScript

| 类别 | 路径 | 说明 |
|------|------|------|
| 路由入口 | `Frontend/src/main.js`、`Frontend/src/App.vue` | 应用入口 |
| 仪表盘 | `Frontend/src/views/dashboard/Home.vue` | 首页 |
| 认证 | `Frontend/src/views/auth/` | 登录/注册/找回密码（3 文件） |
| 工作流 | `Frontend/src/views/workflow/` | 工作流编辑器/列表/执行/版本对比（4 文件） |
| NL 工作流 | `Frontend/src/views/nl-workflow/Creator.vue` | NL 转工作流创建器 |
| 代码图谱 | `Frontend/src/views/codegraph/` | 代码图谱可视化（7 文件） |
| 训练 | `Frontend/src/views/training/` | YOLO 训练进度面板（1 文件） |
| 设置 | `Frontend/src/views/settings/` | 设置/计费/品牌/集成/桌面 Agent（5 文件） |
| 数据集 | `Frontend/src/views/datasets/` + `dataset/` | 数据集浏览/标注/推荐（5 文件） |
| 知识库 | `Frontend/src/views/knowledge/` | RAG 知识库（2 文件） |
| 向量存储 | `Frontend/src/views/vector-store/` | 向量存储管理（1 文件） |
| 提示词 | `Frontend/src/views/prompt/List.vue` | 提示词列表 |
| 模型 | `Frontend/src/views/model/Index.vue` | 模型管理 |
| 模板市场 | `Frontend/src/views/marketplace/` | 模板市场/详情/我的模板（3 文件） |
| 团队 | `Frontend/src/views/team/Index.vue` | 团队管理 |
| 监控 | `Frontend/src/views/monitoring/Index.vue` | 监控面板 |
| 执行历史 | `Frontend/src/views/execution/History.vue` | 执行历史 |
| 落地页 | `Frontend/src/views/Landing.vue` | 首页落地页 |
| 404 | `Frontend/src/views/NotFound.vue` | 404 页面 |

**配置文件**：`package.json`、`vite.config.js`、`tsconfig.json`、`tsconfig.node.json`、`vitest.config.ts`、`playwright.config.js`、`.eslintrc.cjs`、`.env.example`、`.env.production`

**测试**：`Frontend/tests/`（E2E + 单元测试 + mocks）

---

### 3. 桌面应用（Electron Desktop）

> 路径：`Desktop/`

| 文件 | 说明 |
|------|------|
| `main.js` | Electron 主进程 |
| `preload.js` | 预加载脚本 |
| `electron.html` | 窗口页面 |
| `package.json` | 依赖配置 |
| `assets/README.md` | 资源目录说明 |

---

### 4. 项目文档（Docs）

> 路径：`Docs/` - 共 50+ 份文档

| 子目录 | 说明 | 文件数 |
|--------|------|--------|
| `Docs/project-audits/` | 项目审计：架构审计、迁移记录、领域设计、行动计划、训练工作流蓝图 | ~20 |
| `Docs/phases/` | 分阶段优化计划（Phase 0-5） | 6 |
| `Docs/tasks/` | 团队任务分配（TASK-001 至 006） | 7 |
| `Docs/api/` | API 规范文档、一致性指南、快速参考 | 4 |
| `Docs/guides/` | 部署/本地开发指南 | 2 |
| `Docs/superpowers/` | 开发计划与验证 | 2 |
| `Docs/archive/student-assignments/` | 学生作业归档 | 6 |
| `Docs/软件著作权/` | 软著申请材料 | 3 |
| `Docs/` 根目录 | 项目执行索引、改进计划、结构文档、答辩问题库 | 5 |

---

### 5. 毕业论文（Thesis）

> 路径：`Thesis/` - 毕业论文全套材料

| 子目录 | 说明 | 文件数 |
|--------|------|--------|
| `Thesis/chapter/` | 论文章节 00-09（摘要到总结展望） | 10 |
| `Thesis/figures/` | 图表说明文档 | 5 |
| `Thesis/experiments/` | 实验脚本与评估数据 | 5 |
| `Thesis/references/` | 参考文献笔记 | 1 |
| 根目录 | 论文草稿 v1、README | 2 |

---

### 6. PPT 演示

> 路径：`PPT/`

| 文件 | 说明 |
|------|------|
| `Flowly_NL2WF_参赛作品.pptx` | 参赛演示文稿 |
| `check_table.py` | PPT 数据检查脚本 |
| `qa_check.py` | QA 检查脚本 |
| `generate.js` | PPT 生成辅助脚本 |
| `package.json` + `package-lock.json` | Node 依赖 |

---

### 7. 测试代码

> 路径：`tests/`

| 子目录 | 说明 |
|--------|------|
| `tests/frontend/unit/` | 前端 API 单元测试（25 个 spec） |
| `tests/frontend/` 根目录 | Jest 配置 |
| `tests/nl_workflow/` | NL 工作流测试（含 conftest，6 个测试） |
| `tests/` 根目录 | `debug_auth.py`、`debug_conv.py`、`debug_conv2.py`、`test_agent_comprehensive.py` 等临时调试文件 |

---

### 8. 测试报告与截图

> 路径：`tests/artifacts/acceptance/`、`tests/artifacts/manual-screenshots/`、`Backend/reports/`、`Frontend/tests/artifacts/manual-screenshots/`

| 路径 | 内容 | 建议 |
|------|------|------|
| `tests/artifacts/acceptance/` | NL 模块 E2E 测试报告 + 12 张截图 | 归档后可清理 |
| `tests/artifacts/manual-screenshots/` | 主视图测试截图（5 张） | 归档后可清理 |
| `Backend/reports/` | 5 个 API 检查 JSON 报告（2026-05-10） | 临时文件，可删除 |
| `Frontend/tests/artifacts/manual-screenshots/` | 失败测试的截图、视频、错误日志 | 修复后可清理 |

---

### 9. CI/CD 与 Docker

> 路径：`docker/`、`.github/`

| 路径 | 说明 |
|------|------|
| `.github/workflows/ci.yml` | GitHub Actions CI 配置 |
| `docker/Dockerfile.backend` | 后端 Dockerfile |
| `docker/Dockerfile.frontend` | 前端 Dockerfile |
| `docker/Dockerfile.nginx` | Nginx Dockerfile |
| `docker/.env.example` | Docker 环境变量示例 |

---

### 10. 脚本与工具

> 路径：`Scripts/`

| 文件 | 说明 |
|------|------|
| `setup.bat` | 环境初始化脚本 |
| `train_model.py` | 独立训练脚本（与 Backend/scripts/train_model.py 内容不同） |

---

### 11. IDE/编辑器配置

| 路径 | 说明 |
|------|------|
| `.vscode/settings.json` | VS Code 工作区设置 |
| `.idea/` | JetBrains IDE 配置（若干文件） |
| `.cursor/rules/global-rules.md` | Cursor AI 规则 |
| `.claude/settings.local.json` | Claude 本地设置 |
| `.cursorrules` | Cursor 规则（根目录） |

---

### 12. 根目录配置文件

| 文件 | 说明 |
|------|------|
| `README.md` | 项目说明 |
| `AGENTS.md` | AI Agent 约定 |
| `.gitignore` | Git 忽略规则 |
| `.env.example` | 环境变量示例 |
| `.env` | **实际环境变量（含密钥）** |
| `.mcp.json` | MCP 配置 |
| `pyrightconfig.json` | Python 类型检查配置 |
| `pytest.ini` | pytest 配置 |
| `requirements.txt` | Python 依赖（根目录） |
| `requirements.in` | Python 依赖声明（根目录，与 requirements.txt 功能重复） |
| `skills-lock.json` | 技能锁定文件（根目录） |

---

### 13. 虚拟环境与依赖缓存

| 路径 | 说明 |
|------|------|
| `.venv/` | Python 虚拟环境（200+ 文件） |
| `Frontend/node_modules/` | 前端 Node 依赖 |
| `Desktop/node_modules/` | Electron 依赖 |
| `tests/frontend/node_modules/` | 测试 Node 依赖 |

> 这些目录应通过 `.gitignore` 管理，不应提交到版本控制。

---

### 14. Playwright 浏览器录制（可清理）

> 路径：`.playwright-mcp/` - 64 个 YAML 文件
> 时间范围：2026-05-10 07:36 ~ 09:56
> 说明：浏览器自动化录制快照，临时调试产物

---

### 15. pytest 缓存

| 路径 |
|------|
| `.pytest_cache/` |
| `Backend/.pytest_cache/` |

> 可通过 `.gitignore` 忽略或直接删除。

---

## 二、重复文件识别

| 序号 | 文件组 | 类型 | 说明 |
|------|--------|------|------|
| 1 | `Backend/check_user.py` / `check_user2.py` / `check_user3.py` / `check_user4.py` | 临时调试 | 4 个文件均调试同一用户 `sucker`，功能高度重复 |
| 2 | `Backend/test_login.py` / `test_login2.py` / `test_login3.py` / `test_login4.py` | 临时调试 | 4 个文件测试同一登录流程，逐步迭代版本 |
| 3 | `Backend/test_api_login.py` / `test_api_login2.py` / `test_api_login3.py` | 临时调试 | 3 个文件测试 API 登录 |
| 4 | `Backend/test_http_login.py` / `test_http_login2.py` | 临时调试 | 2 个文件测试 HTTP 登录 |
| 5 | `Backend/scan_passwords.py` / `scan_passwords2.py` | 临时调试 | 2 个文件扫描密码哈希，`scan_passwords2.py` 为精简版 |
| 6 | `Scripts/train_model.py` vs `Backend/scripts/train_model.py` | 功能重复 | 同为训练脚本但内容差异大；建议保留 Backend 版本（功能更全），Scripts 目录改为引用 |
| 7 | 根目录 `requirements.txt` vs `requirements.in` | 配置冗余 | `requirements.in` 为源声明，`requirements.txt` 为锁定版本；保留 `requirements.in`，`requirements.txt` 由 `pip-compile` 生成 |
| 8 | 根目录 `skills-lock.json` vs `Frontend/skills-lock.json` | 配置重复 | 建议仅保留一份 |

---

## 三、建议删除的文件

### 高优先级（安全/敏感信息）

| 文件 | 原因 |
|------|------|
| `Backend/password_hash.txt` | 包含密码哈希片段 `pbkdf2_sha256\`，存在安全隐患 |
| `.env` | 包含实际密钥配置，确认已将必需变量迁移到 `.env.example` 后可删除 |

### 中优先级（临时调试脚本，约 20 个文件）

| 文件列表 |
|----------|
| `Backend/check_user.py` |
| `Backend/check_user2.py` |
| `Backend/check_user3.py` |
| `Backend/check_user4.py` |
| `Backend/test_login.py` |
| `Backend/test_login2.py` |
| `Backend/test_login3.py` |
| `Backend/test_login4.py` |
| `Backend/test_api_login.py` |
| `Backend/test_api_login2.py` |
| `Backend/test_api_login3.py` |
| `Backend/test_http_login.py` |
| `Backend/test_http_login2.py` |
| `Backend/scan_passwords.py` |
| `Backend/scan_passwords2.py` |
| `Backend/fix_password.py` |
| `Backend/test_hash.py` |
| `Backend/test_email_nl.py` |
| `tests/debug_auth.py` |
| `tests/debug_conv.py` |
| `tests/debug_conv2.py` |

> 说明：均为一次性调试脚本，功能已由正式测试覆盖。如需保留记录，建议移动到 `Docs/archive/debug-scripts/` 归档而非直接删除。

### 低优先级（临时产物与缓存）

| 路径 | 文件数 | 说明 |
|------|--------|------|
| `.playwright-mcp/` | 64 | 浏览器录制快照，调试残留 |
| `Backend/reports/api_check_*.json` | 5 | 临时 API 检查报告 |
| `tests/artifacts/acceptance/*.png` | 12 | E2E 测试截图（可归档） |
| `tests/artifacts/manual-screenshots/*.png` | 5 | 测试截图（可归档） |
| `Frontend/tests/artifacts/manual-screenshots/` | 3 | 失败测试视频/截图/日志 |
| `Frontend/vite-out.log` | 1 | Vite 构建输出日志 |
| `Frontend/vite-err.log` | 1 | Vite 错误日志 |
| `.pytest_cache/`（2 处） | - | pytest 缓存目录 |
| `tests/frontend/junit.xml` | 1 | 测试结果 XML |

---

## 四、整理建议优先级

### 立即处理

1. 删除 `Backend/password_hash.txt`
2. 将 `.env` 从版本控制中移除（确认 `.gitignore` 已包含）
3. 清理 20 个 Backend 根目录临时调试脚本

### 本次处理

4. 清理 `.playwright-mcp/` 目录（64 个 YAML）
5. 清理 `Backend/reports/` 中 5 个临时 JSON
6. 删除 `Frontend/vite-out.log` 和 `Frontend/vite-err.log`
7. 清理 `.pytest_cache/` 目录

### 可选优化

8. 合并 `tests/artifacts/acceptance/` 和 `tests/artifacts/manual-screenshots/` 目录
9. 统一 `requirements` 管理（保留 `.in`，删除由编译生成的 `.txt`）
10. 决定 `skills-lock.json` 保留一份
11. 合并 `Scripts/train_model.py` 到 Backend 版本，或明确区分用途
12. 整理 `Docs/archive/` 中的学生作业归档
