# Flowly 用户端全链路交互审计

> 验证标准：UI 点击 → Network 2xx → 后端处理 → DB 变更 → UI 反馈  
> 环境：前端 `http://localhost:5200` · 后端 Daphne `127.0.0.1:8000` · 账号 `nlwftest@flowly.test`

## 记录模板

| 模块 | 路由 | 操作/按钮 | 实用案例 | 期望 API | DB 断言 | 实际结果 | 状态 |
|------|------|-----------|----------|----------|---------|----------|------|
| 示例 | `/workflows` | 新建 | 创建空工作流 | `POST /workflows/` | `workflows` 表 +1 | — | ⬜ |

**状态图例**：✅ 通过 · ❌ 失败 · ⚠️ 部分（需外部凭证）· ⬜ 未测

---

## 阶段 0 — 基线

| 项 | 命令/检查 | 结果 |
|----|-----------|------|
| 种子数据 | `python manage.py seed_demo_data --email=nlwftest@flowly.test` | ✅ 含向量存储 + Gateway Ollama 模型 |
| 冒烟 61 项 | `python scripts/frontend_user_api_smoke_test.py` | ✅ 66/66 |
| LLM 探针 | `python scripts/llm_probe_test.py` | ✅ `qwen2.5-coder:7b` 返回 pong |
| 动作集成 | `python scripts/frontend_user_action_integration_test.py` | ✅ 12/12 |

---

## 架构决策（训练与助手去重）

| 原则 | 说明 |
|------|------|
| 训练仅在工作流内 | 已删除 `/training`、`/training/yolo/*` 独立页；旧 URL `/training` 重定向提示页 |
| 数据页保留 | `/datasets`、`/dataset-recommend`、标注/增强页仍作为节点上游数据源 |
| YOLO 单入口 | 后端 YOLO 仅走 `yolo_training` 节点 + `POST /training/yolo-runs/`；`model_training` 拒绝 ultralytics/yolo |
| 标准模板 | `yolo-detection-project`：`dataset_upload → yolo_training → project_profiler → website_generator → environment_provision → site_qa → site_preview` |
| 助手合并 | 「工作流优化助手」已并入 `WorkflowAssistant` 的 `/optimize` 指令（规则引擎，不消耗 LLM） |
| 识别项目导航 | `website_generator` 完成后写入侧栏「识别项目」→ `/projects/:id`，并绑定 CodeGraph |
| 站点工厂 M1–M4 | 见 [`Docs/desktop-ml-site-factory/README.md`](../../desktop-ml-site-factory/README.md) |

### M1 站点工厂（2026-06-12 实现）

| 项 | 状态 | 说明 |
|----|------|------|
| SQLite scaffold（detection） | ✅ | `backend/db/schema.sql` + `init_db.py` |
| 节点 `environment_provision` | ✅ | 后端 runner + `EnvironmentProvisionNode.vue` |
| 节点 `site_qa` | ✅ | L1–L4 + `qa_report.json` + 绿/黄/红 |
| 节点 `site_preview` | ✅ | iframe 预览；红灯阻断 |
| Desktop runtime IPC | ✅ | `runtime.startSite` / `stopSite` + 权限 manifest |
| YOLO 模板四节点链 | ✅ | `yoloWorkflowTemplate.js` + seed 命令 |
| Migration 0003 | ✅ | `last_qa_gate` / `last_qa_report` / `last_preview_url` |
| QA 样例报告 | ✅ | `test-reports/site-qa-sample.json` |
| M2 正式验收 | ✅ | `python Backend/scripts/m2_acceptance_test.py` → `M2_ACCEPTANCE_REPORT.md` |
| Playwright L3 全量 E2E | ✅ | 检索站 Tab1/2/4（`qa_runner._run_l3_clip_retrieval_playwright`）；检测站待 Desktop 实机 |
| P1 自动化验收 | ✅ | `python Backend/scripts/p1_site_factory_automated_test.py` → 19/19 |
| 全链路聚合 | ✅ | `python Backend/scripts/site_factory_full_acceptance.py` |

### M2 Profiler + Wizard（2026-06-18）

| 项 | 状态 | 说明 |
|----|------|------|
| `project_profiler` 节点 | ✅ | 规则引擎 + 可选 LLM；输出 `profile.json` |
| `TrainingSiteWizard` 四步 | ✅ | 场景/品牌/合规/输出；必填校验 |
| YOLO 模板含 profiler | ✅ | `yoloWorkflowTemplate.js` 九节点链 |
| classification profile 注入 | ✅ | `build_project_profile` 支持 classification |
| Wizard CLIP 专用字段 | ✅ | `indexDir` / `exampleQueries` / `topK`（clip_retrieval） |

### M3 Project Agent（2026-06-18）

| 项 | 状态 | 说明 |
|----|------|------|
| `POST /website-generator/{id}/agent/message/` | ✅ | 沙箱改码 + 强制 QA |
| `ProjectAgentNode.vue` | ✅ | 节点内迷你对话（**UI 人工走查待补**） |
| QA red 阻断 preview | ✅ | `project_agent.py` + preview_status |
| RAG `project-{site_id}` | ✅ | 有 VectorStore 时写入（**E2E 检索待补**） |
| 正式验收 | ✅ | `python Backend/scripts/m3_acceptance_test.py` |

### M4 CLIP（2026-06-18）

| 项 | 状态 | 说明 |
|----|------|------|
| `clip_classification` / `clip_retrieval` | ✅ | runner + WS + TrainingJob |
| `ClipRetrievalGenerator` 四 Tab | ✅ | CLIP runtime `_query_vector_text` |
| Desktop GPU 索引 | ✅ | `clipIndex:start` + `build_clip_index.py` + `indexMode=desktop` |
| 标注导出 `image_text_pairs` | ✅ | `POST .../export/?format=image_text_pairs` |
| 模板 `clip-retrieval-project` | ✅ | seed + Editor `?template=clip-retrieval` |
| 正式验收 | ✅ | `python Backend/scripts/m4_acceptance_test.py`（22/22） |

---

## 阶段 1 — P0 Mock 修复

| 模块 | 修复项 | 文件 | 状态 |
|------|--------|------|------|
| 知识库详情 | 上传/搜索/删除/设置接真实 API | `CollectionDetail.vue` | ✅ |
| 数据管理 | 导出/历史接 `data-export` API；下载改 blob | `DataExport.vue` + `audit_views.py` | ✅ |
| 数据集详情 | 下载接 `datasets/{id}/download/` | `DatasetDetail.vue` + `training/views.py` | ✅ |
| 认证 | resetPassword uid+token | `auth.js`, `ResetPassword.vue` | ✅ |
| API 层 | token refresh 解包 `{code,data}` + blob | `api/index.js` | ✅ |
| 工作流变量 | CRUD/轮换失败 toast | `VariablePanel.vue` | ✅ |
| RAG 文档列表 | `?collection=` 过滤 | `rag/views.py` | ✅ |
| RAG 嵌入/Chroma | 无效 OpenAI Key 回退 + 集合名修复 | `rag/services.py` | ✅ |
| NL Stream | 创建会话时 `workflow_name`/`workflow_json` 不可为 NULL | `nl_to_workflow/views.py` | ✅ |

---

## 阶段 2A — 核心路径（NL / 工作流 / 执行 / Agent / 模板）

| 模块 | 实用案例 | E2E | LLM | DB 验证 |
|------|----------|-----|-----|---------|
| NL 创建 | 描述「文本总结」→ 生成 5 节点 | chrome-devtools ✅ stream 200 | ✅ Ollama | `nl_sessions` |
| 工作流 | 创建 → 保存 → 编辑页 | chrome-devtools ✅ POST workflows | — | `workflows` |
| 执行历史 | 列表/详情/WS | 冒烟 ✅ | — | `workflow_executions` |
| Agent | 列表/创建 | chrome-devtools ✅ POST agents 201 | — | `agents` |
| 模板市场 | 列表/安装 | chrome-devtools ✅ create_from_template 201 | — | `workflows` |
| 数据导出 | 点击导出 → POST request_export | chrome-devtools ✅ | — | `data_exports` |
| 数据集下载 | 详情页下载 | chrome-devtools ✅ GET download 200 | — | 文件 blob |

---

## 阶段 2B-D — 其余模块

| 模块 | 状态 | 备注 |
|------|------|------|
| 数据集列表/预览/统计 | ✅ 冒烟 + 页面 | |
| RAG 集合/文档 | ✅ 动作测试 + 详情页 E2E | stats 已修复 |
| 凭证 CRUD | ✅ 动作测试 | verify 需真实 API Key |
| 向量存储 | ✅ 种子 + 详情页 E2E | 路由已修复 |
| 团队管理 | ✅ chrome-devtools E2E | 邀请/技能/任务/分配已验 |
| 设置/监控/分析 | ✅ 冒烟 + 监控告警 E2E | |
| 模型训练 | ✅ 重试/取消 + YOLO 新建/详情 | |
| Admin 后台 | ✅ chrome-devtools（`admin@example.com`） | 清缓存/健康检查/用户列表 |
| 备份恢复/删除全部数据 | ⚠️ 明确提示未开放 | 无假成功 |

---

## 验收清单

- [x] P0 模块实用案例跑通（数据导出、数据集下载、RAG 文档、NL 会话）
- [x] P0 页面无 `setTimeout` 假 API 成功
- [x] 数据导出/下载路径 Console 0 error（chrome-devtools 验证）
- [x] 写操作有 DB/API 记录（动作集成测试）
- [x] NL + Gateway LLM 真实调用成功（Ollama `qwen2.5-coder:7b`）
- [x] `frontend_user_api_smoke_test.py` 66/66
- [x] `frontend_user_action_integration_test.py` 12/12
- [x] `llm_probe_test.py` 通过
- [x] Frontend ESLint 0 error
- [ ] 全模块逐按钮矩阵 E2E（建议后续按模块迭代补充本表）

---

## 自查报告（2026-06-12）

### 自动化回归

| 脚本 | 结果 |
|------|------|
| `frontend_user_api_smoke_test.py` | ✅ 66/66（含 yolo-runs-create / tenants-skills） |
| `frontend_user_action_integration_test.py` | ✅ 12/12（含 skill-assign + task-assign_user） |
| `llm_probe_test.py` | ✅ `qwen2.5-coder:7b` → pong |

### chrome-devtools 抽检

| 模块 | 操作 | Network | 结果 |
|------|------|---------|------|
| NL 创建 | 选模型 → 生成工作流 → 发送 | `POST .../message/stream/` **200** | ✅ 已生成「文本总结工作流」5 节点 |
| 数据导出 | 点击下载 export_15 | `GET .../download/` **200** blob | ✅ |
| 知识库详情 | 点击集合卡片 | collections + documents **200** | ✅ |
| 模板市场 | 点击「使用」| `POST create_from_template/` **201** | ✅ |
| 执行监控 | 添加告警规则 | `POST /monitoring/rules/` **201** | ✅ |
| Agent | 创建 Agent | `POST /agents/` **201** | ✅ |
| Agent Debugger | 流式对话 | `POST .../stream_chat/` **200** SSE → Ollama `pong` | ✅ |
| 工作流编辑器 | 添加节点+保存 | `POST /workflows/` → 跳转 edit | ✅ |
| 工作流编辑器 | 验证/保存/执行 | 本地验证 + `PATCH` + `execute` **200** | ✅ |
| Admin 系统管理 | 刷新状态 / 清理缓存 / 用户列表 | `GET health/usage/users` + `POST cache/clear/` **200** | ✅ |
| 执行历史 | 查看详情 | `GET executions/{id}/` + timeline **200** | ✅ |
| 凭证管理 | 添加凭证 | `POST /credentials/` **201** | ✅ |
| 团队 | 打开工作区详情 | `GET tenants/tenants/{id}/members/` **200** | ✅ |
| 向量存储 | 查看集合 | 跳转 `/vector-stores/:id` | ✅ |
| 数据分析 | 加载概览 | `GET monitoring/analytics/overview/` **200** | ✅ |
| 向量存储详情 | 测试连接 | `POST .../test_connection/` **200** | ✅ |
| 数据集列表 | 查看统计 | `GET .../datasets/{id}/stats/` **200** | ✅ |
| 个人资料 | 加载页面 | `GET /auth/user/` **200** | ✅ |
| 代码图谱 | 加载图谱 | `GET codegraph/projects/` + graph **200** | ✅ |
| API 测试 | 发送 GET workflows | `GET /workflows/` **200** | ✅ |
| 模型训练 | 查看详情 | 弹窗展示训练任务信息 | ✅ |
| 团队 | 邀请成员 | `POST .../invite/` **200** | ✅ |
| 模型训练 | 重试失败任务 | `POST .../retry/` **200** | ✅ |
| 模型训练 | 取消运行中任务 | `POST .../cancel/` **200** | ✅ |
| YOLO 训练 | 工作流 YOLO 节点 | 展开面板实时图表 | `ws/training/{id}/` + `GET yolo-runs/{id}/` | ✅ |
| YOLO 训练 | 工作流模板 | 一键创建 YOLO 链路 | `GET /workflows/new?template=yolo-detection` | ✅ |
| 团队 | 创建技能 | `POST /tenants/skills/` **201** | ✅ |
| 团队 | 创建任务 | `POST /tenants/tasks/` **201** | ✅ |
| 团队 | 分配技能 | `POST /tenants/skills/{id}/assign/` **200** | ✅ |
| 个人资料 | 保存简介 | `PATCH /auth/user/` **200** | ✅ |

### 本轮修复（续）

| 问题 | 根因 | 修复 |
|------|------|------|
| 知识库卡片点击无跳转 | `appStore.$router` 不存在 | `Index.vue` 改用 `useRouter()` |
| 集合 stats 500 | `models.Count` 未导入 | `rag/views.py` 补 `Count` |
| 数据导出 ElTag 警告 | `workflows` 类型 tag 为空字符串 | `getTypeTag` 默认 `primary` |
| 告警规则创建 400 | 前端传 `type` 后端要 `condition` | `Index.vue` 映射 payload |
| 告警规则创建无 id | `AlertRuleCreateSerializer` 缺 `id` | 序列化器补 `id` 只读字段 |
| 暂停执行假成功 | `pauseExecution` 无 API 调用 | 接 `workflow.pauseExecution` |
| Agent Debugger 空回复 | `qwen2.5` 被误判 OpenAI，请求 `/chat/completions` 404 | `agents/engine.py` 优先识别 Ollama 模型/端点 |
| Admin 用户表 ElTag 警告 | `member` 角色 tag 为空字符串 | `getRoleTagType` / `getTenantStatusType` 默认 `primary` |
| 团队成员/usage 404 | `tenant.js` 路径缺 `tenants` 段 | 统一为 `/tenants/tenants/{id}/...` |
| 向量存储「查看集合」跳首页 | 路由写成 `/vector-store/:id` | 改为 `/vector-stores/:id` |
| 团队邀请 400 | `invite` 误用 `TenantMembershipCreateSerializer`（要求用户已注册） | 新增 `TenantInviteSerializer`；测试租户 `max_users=5` |
| YOLO 新建 400 | `YoloTrainingRunCreateSerializer` 缺 `framework`/`model_type` 默认值 | `extra_kwargs` 设 `required=False` + 默认 ultralytics/detection |
| YOLO 新建跳 `/undefined` | 创建响应未含 `id` | 创建序列化器补 `read_only_fields = ['id']` |
| 技能分配 404 | `TeamSkillViewSet.get_queryset` 无 `tenant_id` 时返回空集 | 详情/assign 改为按用户所属租户过滤 |
| 任务分配 500 | `assign_user` 未导入 `TaskAssigneeSerializer` | `views.py` 补 import |

### 按钮矩阵（已测）

| 模块 | 路由 | 操作 | 期望 API | 状态 |
|------|------|------|----------|------|
| 数据管理 | `/settings/data-export` | 导出工作流 | `POST request_export/` | ✅ |
| 数据管理 | `/settings/data-export` | 下载历史 | `GET .../download/` blob | ✅ |
| 知识库 | `/knowledge` | 进入集合详情 | `GET collections/{id}/` | ✅ |
| 知识库 | `/knowledge/:id` | 加载文档列表 | `GET documents/?collection=` | ✅ |
| 模板市场 | `/marketplace` | 使用模板 | `POST create_from_template/` | ✅ |
| NL 创建 | `/nl-create` | 生成工作流 | `POST .../message/stream/` | ✅ |
| 数据集 | `/datasets/:id` | 下载 | `GET .../download/` | ✅ |
| 执行监控 | `/monitoring` | 添加告警规则 | `POST /monitoring/rules/` | ✅ |
| Agent | `/agents/new` | 创建 Agent | `POST /agents/` | ✅ |
| Agent Debugger | `/agents/:id/debug` | 发送消息（流式） | `POST .../stream_chat/` | ✅ |
| 工作流编辑器 | `/workflows/new` | 添加节点+保存 | `POST /workflows/` | ✅ |
| 工作流编辑器 | `/workflows/:id/edit` | 验证/保存/执行 | `PATCH` + execute | ✅ |
| Admin | `/admin` | 刷新状态 / 清理缓存 | `GET health/usage` + `POST cache/clear/` | ✅ |
| 执行历史 | `/executions` | 查看详情 | `GET executions/{id}/` | ✅ |
| 凭证 | `/settings/credentials` | 添加凭证 | `POST /credentials/` | ✅ |
| 团队 | `/team` | 打开工作区 / 成员列表 | `GET .../members/` + `usage/` | ✅ |
| 团队 | `/team` | 邀请成员 | `POST .../invite/` | ✅ |
| 工作流编辑器 | `/workflows/new` | YOLO 节点环境检测 | 节点内 checklist | ✅ |
| 识别项目 | `/projects/:id` | 部署 / 下载 / CodeGraph | `POST deploy/` + `GET download/` | ✅ |
| 训练重定向 | `/training` | 跳转工作流模板 | 提示 + 创建 YOLO 模板按钮 | ✅ |
| 团队 | `/team` | 创建技能 | `POST /tenants/skills/` | ✅ |
| 团队 | `/team` | 创建任务 | `POST /tenants/tasks/` | ✅ |
| 团队 | `/team` | 分配技能 | `POST /tenants/skills/{id}/assign/` | ✅ |
| 个人资料 | `/settings/profile` | 保存更改 | `PATCH /auth/user/` | ✅ |
| 向量存储 | `/vector-stores` | 查看集合 | 跳转详情页 | ✅ |
| 数据分析 | `/analytics` | 加载仪表盘 | `GET analytics/overview/` | ✅ |
| 向量存储详情 | `/vector-stores/:id` | 测试连接 | `POST .../test_connection/` | ✅ |
| 数据集 | `/datasets` | 查看统计 | `GET .../stats/` | ✅ |
| 个人资料 | `/settings/profile` | 加载用户信息 | `GET /auth/user/` | ✅ |
| 代码图谱 | `/codegraph` | 加载项目图谱 | `GET codegraph/projects/` | ✅ |
| API 测试 | `/api-explorer` | 发送 GET workflows | `GET /workflows/` | ✅ |
| 工作流助手 | `/workflows/:id/edit` | `/optimize` 优化工作流 | `POST /workflows/optimize/` | ✅ |

### 本轮修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 数据导出下载无效 | `file_url` 错路径 `/api/exports/`；`window.open` 无鉴权 | 后端 `download` 返回真实 JSON blob；前端改 `dataExportApi.download()` + `<a download>` |
| NL stream 500（历史） | `workflow_name`/`workflow_json` NULL | `nl_to_workflow/views.py` 默认值 |
| Admin 假成功（历史） | 清缓存/备份/日志 Mock | `admin/Index.vue` 接真实 API |

### Mock 扫描

- 用户端 `views`：**无** `setTimeout` 假成功 / `开发中` 文案
- `setTimeout` 仅存：搜索防抖、轮询、图表重绘（合法用途）
- 备份恢复 / 删除全部数据：**明确提示未开放**（非假成功）

### 已知限制

1. 凭证 verify 用假 key 时 SSL 错误属预期
2. 全模块逐按钮矩阵 E2E 未 100% 覆盖（品牌定制/通知 SMTP 等设置子页深层写操作可继续迭代）
3. 数据导出 `usage` 类型暂无独立数据源（`full`/`workflows`/`executions`/`audit_logs` 已生成真实 JSON）
4. Admin 测试账号：`admin@example.com` / `admin123`（superuser，与用户端 `nlwftest@flowly.test` 分离）
