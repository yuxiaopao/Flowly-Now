# Flowly-now 项目完善计划

> 制定时间：2026-06-03
> 项目：Flowly-now (AI 工作流自动化平台)
> 技术栈：Django + DRF (Backend) / Vue 3 + Pinia + Vue Flow (Frontend)
> 状态：初版完成，存在多个可优化方向

---

## 一、安全加固（优先级：P0 — 必须修复）

### 1.1 密钥与密钥管理

**问题：**
- `config/settings.py` 中存在硬编码的默认 `SECRET_KEY`，包含不安全的 fallback 值
- `.env.example` 中暴露了示例 API Key (`LANGSMITH_API_KEY`)
- Docker Compose 中部分服务存在默认密码

**整改措施：**
- [ ] 移除所有 `SECRET_KEY` 的不安全 fallback 值，改为启动时必填或随机生成
- [ ] 从 `.env.example` 中移除所有真实的或类似真实的 API Key 示例
- [ ] 统一使用 `python-dotenv` + 环境变量，所有密钥不得有默认值
- [ ] 在 Docker Compose 中，所有密码必须通过 `.env` 文件注入，禁止写死
- [ ] 添加 `SECRET_KEY` 长度验证（最短 50 字符）

**涉及文件：**
- `Backend/config/settings.py`
- `.env.example`
- `docker-compose.yml`
- `docker/.env.example`

### 1.2 CORS 与权限配置

**问题：**
- CORS 配置中 `allow_all_origins` 可能过于宽松
- 部分 endpoint 缺少显式的权限注解

**整改措施：**
- [ ] 审查 `config/settings.py` 中的 `CORS_ALLOWED_ORIGINS`，确保只有受信任的域名
- [ ] 为所有 DRF ViewSet 添加明确的 `permission_classes`
- [ ] 添加 IP 白名单机制（可选，针对内网部署场景）

**涉及文件：**
- `Backend/config/settings.py`
- `Backend/**/views.py`

### 1.3 输入验证与 SQL 注入防护

**问题：**
- 部分 Serializer 的字段缺少 `max_length` 或 `min_length` 限制
- 用户上传文件缺少类型和大小校验

**整改措施：**
- [ ] 全面审查所有 Serializer，为所有 CharField 添加 `max_length`
- [ ] 为文件上传添加 MIME 类型白名单和大小限制（最大 50MB）
- [ ] 添加请求体大小限制（全局 `DATA_UPLOAD_MAX_MEMORY_SIZE`）
- [ ] 对所有用户可控的字符串字段添加防注入过滤

**涉及文件：**
- `Backend/**/serializers.py`

---

## 二、测试覆盖（优先级：P0 — 核心功能保障）

### 2.1 当前测试现状

| 模块 | 测试文件数 | 覆盖内容 | 缺口 |
|------|-----------|---------|------|
| `nl_workflow` | 6 | API、验证、速率限制、成本计算 | 无缺口 |
| `workflows/executor` | 4 | 执行器、错误处理、上下文 | Serializer 未测 |
| `e2e` | 6 | 后端 API、流式输出、模型训练 | 无缺口 |
| `frontend/unit` | 15 | API 客户端 | 组件测试缺失 |
| `gateway` | 0 | 无测试 | **重大缺口** |
| `agents` | 0 | 无测试 | **重大缺口** |
| `rag` | 0 | 无测试 | **重大缺口** |
| `billing` | 0 | 无测试 | **重大缺口** |

### 2.2 补测计划

**Phase 1 — 核心模块测试（4 周）：**
- [ ] `gateway` 模块：Provider 切换逻辑、Token 计数、Cost 计算
- [ ] `agents` 模块：会话管理、断点调试、Execution Trace
- [ ] `rag` 模块：向量检索、Chunking 策略、召回率评估
- [ ] `workflows/serializers.py`：全量 Serializer 单元测试

**Phase 2 — 集成测试（3 周）：**
- [ ] 工作流端到端执行测试（含 Celery 异步任务）
- [ ] WebSocket 连接与消息流测试
- [ ] JWT 认证与 Token 刷新流程测试

**Phase 3 — 前端 E2E 测试（3 周）：**
- [ ] Playwright 覆盖核心用户路径：
  - 工作流创建 → 编辑 → 保存 → 执行 → 查看结果
  - NL 自然语言创建工作流完整流程
  - Agent 对话与调试流程
  - 多租户隔离验证

**涉及文件：**
- `tests/backend/`
- `tests/nl_workflow/`
- `tests/e2e/`
- `tests/frontend/`
- `Frontend/playwright.config.ts`（需创建）

---

## 三、硬编码整改（优先级：P1 — 代码可维护性）

### 3.1 Magic Number 清理

**问题：** 代码中存在大量魔法数字，分散在各处

**整改措施 — 建立统一的常量枚举体系：**

| 常量类别 | 当前状态 | 整改方案 |
|---------|---------|---------|
| Token/LLM 配置 | 分散在 `services.py` | 统一到 `config/constants.py` |
| 分页配置 | 分散在各 ViewSet | 统一到 `config/pagination.py` |
| 工作流节点默认值 | 内联写死 | 统一到 `workflows/constants.py` |
| 前端 API 超时 | 硬编码 `timeout: 30000` | 统一到 `Frontend/src/config/index.js` |
| 节点类型 ID | 分散在前端各处 | 统一到 `Frontend/src/utils/workflow-constants.js` |

**涉及文件：**
- `Backend/config/constants.py`（需创建）
- `Backend/config/pagination.py`（需创建）
- `Backend/workflows/constants.py`（需创建）
- `Frontend/src/config/index.js`
- `Frontend/src/utils/workflow-schema.js`

### 3.2 API URL 硬编码清理

**问题：**
- `nl_to_workflow/services.py` 中的示例 URL 混在业务逻辑中
- 前端 API 前缀硬编码

**整改措施：**
- [ ] 将所有示例 URL 移至注释或独立测试文件
- [ ] 后端所有外部 HTTP 请求统一通过 `config/external_urls.py` 管理
- [ ] 前端 API 前缀从环境变量读取（`VITE_API_PREFIX`）

**涉及文件：**
- `Backend/nl_to_workflow/services.py`
- `Frontend/src/api/index.js`

---

## 四、代码质量统一（优先级：P1 — 长期可维护）

### 4.1 命名规范统一

**前端 Store 命名问题：**
- 部分 action 使用 `fetchXxx`，部分使用 `loadXxx`
- Route name 命名不统一：`NLCreator` vs `WorkflowList`（PascalCase vs camelCase）

**整改措施：**
- [ ] 制定前端命名规范文档（README in `Frontend/src/stores/`）
- [ ] 统一所有 Store action 命名：`fetchXxx`（从 API 获取）、`loadXxx`（本地加载）、`saveXxx`（提交到 API）
- [ ] 统一 Route name 使用 PascalCase
- [ ] 建立 ESLint 规则强制命名规范

**涉及文件：**
- `Frontend/src/stores/*.js`
- `Frontend/src/router/routes.js`
- `Frontend/.eslintrc.js`（需创建）

### 4.2 Backend 模块一致性

**问题：**
- `integrations` 和 `branding` 模块只有 Model，无 View/Serializer
- `templates` 模块只有 Model 和 urls
- `core` 模块采用 `views/` 子目录结构，与其他模块的扁平原文件不一致

**整改措施：**
- [ ] `integrations`：补齐 ViewSet、Serializer、URLs，暴露 REST API
- [ ] `branding`：补齐 ViewSet、Serializer
- [ ] `templates`：补齐 ViewSet、Serializer
- [ ] `core`：统一为 `views.py`、`serializers.py` 扁平原文件结构
- [ ] `prompts`、`marketplace`、`evaluation`：补齐 `admin.py`

**涉及文件：**
- `Backend/integrations/views.py`（需创建）
- `Backend/branding/views.py`（需创建）
- `Backend/templates/views.py`（需创建）
- `Backend/core/views/` → `Backend/core/views.py`（需重构）

### 4.3 异常处理规范化

**问题：**
- 部分 View 使用过于宽泛的 `except Exception as e:`
- 错误响应格式不一致

**整改措施：**
- [ ] 建立统一的异常类层次：`BaseAPIException` → 业务异常类
- [ ] 在 `config/exception_handlers.py` 中确保所有异常返回统一格式：
  ```json
  {
    "error": { "code": "WORKFLOW_NOT_FOUND", "message": "...", "details": {} },
    "request_id": "uuid"
  }
  ```
- [ ] 将所有 `except Exception` 替换为具体的异常类型
- [ ] 为所有异步 Celery Task 添加统一异常处理包装器

**涉及文件：**
- `Backend/config/exceptions.py`（需创建）
- `Backend/config/exception_handlers.py`（需增强）
- `Backend/**/views.py`

---

## 五、业务流程完善（优先级：P1 — 功能完整性）

### 5.1 工作流引擎增强

**当前能力：**
- 38 种节点类型
- Vue Flow 可视化编辑器
- NL 自然语言生成
- LangChain Agent 执行引擎
- 执行监控与时间线

**待完善功能：**

| 功能 | 当前状态 | 优先级 |
|------|---------|-------|
| 工作流版本控制 | 无 | P1 |
| 工作流模板市场 | 有 Model，无前端页面 | P1 |
| 工作流导入/导出 | 无 | P1 |
| 子工作流嵌套调用 | 有 `SubworkflowNode`，执行逻辑待验证 | P1 |
| 断点调试（运行时） | Agent debugger 有，前端无断点 UI | P2 |
| 并行分支执行优化 | 当前串行执行 | P2 |
| 工作流执行限流 | 无 | P2 |
| 多语言节点国际化 | 无（前端全中文硬编码） | P2 |

**整改措施：**
- [ ] 实现工作流版本管理（Schema Migration）
- [ ] 完成模板市场前端页面（Marketplace views 已有，缺 API 对接）
- [ ] 添加工作流 JSON 导入/导出功能
- [ ] 实现子工作流嵌套执行的递归深度限制
- [ ] 前端添加断点设置 UI 和调试面板

**涉及文件：**
- `Backend/workflows/models.py`
- `Frontend/src/views/workflow/`
- `Frontend/src/nodes/`

### 5.2 前端交互体验完善

**根据 Cursor 规范中的交互体验完善要求：**

| 功能 | 当前状态 | 整改方案 |
|------|---------|---------|
| Loading 动画 | 分散，部分缺失 | 统一 `useRequest` hook 加载状态 |
| 空状态 UI | 部分视图缺失 | 为所有列表视图补齐空状态组件 |
| 表单校验 | 分散，不一致 | 统一使用 `useForm` composable |
| 错误 Toast | 部分有，部分无 | 全局统一 error/success toast |
| 确认对话框 | 有 `ConfirmDialog`，但未全局注册 | 全局注册，所有危险操作强制确认 |
| 脱敏日志 | 部分 DEBUG 日志残留 | 移除所有生产环境泄露日志 |

**涉及文件：**
- `Frontend/src/composables/useRequest.js`（需增强）
- `Frontend/src/components/common/`（需补空状态组件）
- `Frontend/src/views/**/Editor.vue`

---

## 六、前端架构优化（优先级：P2 — 长期健康度）

### 6.1 TypeScript 迁移

**现状：** 项目使用 JavaScript（`.js`），有 `types/` 目录但未被充分利用

**整改措施：**
- [ ] 将 `types/index.d.ts` 转为 `src/types/index.ts`，启用完整类型检查
- [ ] 为所有 API Response 建立类型定义
- [ ] 为 Pinia Store 添加 State/Getter/Action 类型注解
- [ ] 配置 `tsconfig.json` 严格模式

**涉及文件：**
- `Frontend/src/types/`
- `Frontend/tsconfig.json`（需创建）
- `Frontend/src/api/`

### 6.2 组件库规范化

**问题：**
- `components/common/` 仅 8 个组件，重复 UI 代码较多
- 无统一的错误边界（Error Boundary）
- 38 个 Node 组件存在重复的表单逻辑

**整改措施：**
- [ ] 抽取公共表单控件：`AppInput`、`AppSelect`、`AppSwitch`、`AppSlider` 等
- [ ] 建立 `components/ui/` 基础 UI 库
- [ ] 为所有页面添加 Error Boundary
- [ ] 抽取 `configs/` 中的表单配置为可复用 Schema 定义

**涉及文件：**
- `Frontend/src/components/common/`
- `Frontend/src/components/ui/`（需创建）
- `Frontend/src/configs/`

### 6.3 性能优化

| 优化项 | 当前问题 | 整改方案 |
|--------|---------|---------|
| Vue Flow 性能 | 大型工作流渲染卡顿 | 虚拟化 viewport，只渲染可视区域节点 |
| API 请求 | 重复请求未缓存 | 实现 API 响应缓存策略（TTL 5min） |
| 前端依赖 | 多个 echarts 实例 | 统一图表库实例，共享 |
| 图片资源 | Logo/图标未压缩 | SVG 化，去除冗余 PNG |
| 代码分割 | 单 Bundle 过大 | 路由级动态导入（`defineAsyncComponent`） |

**涉及文件：**
- `Frontend/src/views/workflow/Editor.vue`
- `Frontend/src/router/routes.js`
- `Frontend/src/components/workflow/`

---

## 七、DevOps 与部署（优先级：P2 — 可维护性）

### 7.1 CI/CD 完善

**当前状态：** `.github/workflows/` 存在但内容待确认

**整改措施：**
- [ ] 添加 Backend CI：`pytest` + coverage 报告 + lint（ruff）
- [ ] 添加 Frontend CI：`npm run test` + `npm run lint` + type check
- [ ] 添加 E2E CI：Playwright 测试在 PR 阶段运行
- [ ] 配置 GitHub Actions 缓存（pip/npm 依赖）
- [ ] 添加 Docker 构建缓存优化（multi-stage build）
- [ ] 添加 Dependabot 自动依赖更新

### 7.2 环境配置管理

**问题：**
- `environment.yml`（Conda）与 `requirements.txt`（pip）并存，可能不同步
- `.env.example` 与实际 `.env` 字段不完全匹配

**整改措施：**
- [ ] 统一为 `requirements.txt`（pip），移除 `environment.yml`
- [ ] 同步更新 `.env.example`，每个字段添加注释说明
- [ ] 添加 `requirements-dev.txt`（测试、lint 相关依赖）
- [ ] 使用 `pip-compile` 生成锁文件 `requirements.lock`

### 7.3 监控与日志

**当前状态：** `monitoring` 模块已有基础实现

**待完善：**
- [ ] 添加 Sentry/错误追踪集成（Backend + Frontend）
- [ ] 结构化日志（JSON 格式）替代纯文本日志
- [ ] Prometheus 指标暴露（request count, latency, error rate）
- [ ] Grafana Dashboard 模板（工作流执行监控）

---

## 八、文档完善（优先级：P2 — 知识传承）

### 8.1 项目文档结构重整

**问题：** `Docs/` 目录混入了学生课程作业文档

**整改措施：**
- [ ] 将学生作业文档移至 `Docs/archived/student-work/`
- [ ] 重整项目文档结构：

```
Docs/
├── README.md                    # 项目文档总入口
├── architecture/               # 架构文档
│   ├── SYSTEM-DESIGN.md
│   ├── API-REFERENCE.md
│   └── DATABASE-SCHEMA.md
├── development/                # 开发指南
│   ├── SETUP.md               # 覆盖 setup-guide.md
│   ├── TESTING.md
│   ├── CODING-STANDARDS.md
│   └── DEPLOYMENT.md
└── api/                       # API 规范
    └── openapi.yaml
```

### 8.2 API 文档自动化

**整改措施：**
- [ ] 启用 `drf-spectacular`（已安装）生成 OpenAPI 3.0 Schema
- [ ] 配置 `/api/docs/` Swagger UI
- [ ] 将 Schema 导出到 `Docs/api/openapi.yaml`
- [ ] 为前端生成 TypeScript API 类型（`openapi-typescript-codegen`）

---

## 九、执行路线图

```
Phase 0: 安全修复 (1 周)
├── 移除不安全 SECRET_KEY fallback
├── 清理 .env.example 中的暴露密钥
└── CORS 与权限审查

Phase 1: 测试覆盖 (4 周)
├── gateway / agents / rag 模块测试
├── workflows serializers 测试
└── Playwright E2E 核心流程

Phase 2: 硬编码整改 + 代码质量 (3 周)
├── 常量枚举体系建立
├── 模块一致性修复
├── 异常处理规范化
└── 命名规范统一

Phase 3: 业务功能完善 (4 周)
├── 工作流版本控制
├── 模板市场完整实现
├── 子工作流嵌套执行
└── 前端交互体验补全

Phase 4: 架构优化 (3 周)
├── TypeScript 迁移
├── 组件库规范化
├── 性能优化
└── 错误边界

Phase 5: DevOps + 文档 (2 周)
├── CI/CD 完善
├── 依赖管理统一
├── 监控集成
└── 文档结构重整
```

**总工时估算：约 17 周**

---

## 十、附：CodeGraphContext 在本项目的应用

安装 CodeGraphContext 后，可通过以下方式辅助以上计划的执行：

| 计划阶段 | CodeGraphContext 查询示例 |
|---------|------------------------|
| 安全审查 | `cgc analyze callers config/settings.py:SECRET_KEY` — 追踪密钥使用链 |
| 测试缺口 | `cgc find type Function --exclude-decorator test` — 找未测试的业务函数 |
| 硬编码查找 | `cgc find pattern "localhost:8000"` — 全局 URL 硬编码排查 |
| 依赖分析 | `cgc analyze deps workflows/` — 查看 workflows 模块依赖关系 |
| 死代码检测 | `cgc analyze dead-code` — 找未使用的函数（已发现 50+） |
| 重构影响分析 | `cgc analyze impact Backend/core/models/` — 查看模型变更影响范围 |

---

*本文档由 AI Agent 基于 CodeGraphContext 代码图谱分析 + 全局代码审查生成*
