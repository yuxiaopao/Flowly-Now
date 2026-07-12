# 关键代码文件索引

> 实施 M1–M4 时的路径速查  
> 最后更新：2026-06-18（M1–M4 已实现）

---

## 工作流与节点

| 用途 | 路径 |
|------|------|
| 节点注册（文案） | `Frontend/src/config/nodeRegistry.js` |
| 节点组件映射 | `Frontend/src/config/nodeComponents.js` |
| 执行器 dispatch | `Backend/workflows/services/langchain_service.py` |
| YOLO 模板 | `Frontend/src/config/yoloWorkflowTemplate.js` |
| 种子模板 | `Backend/workflows/management/commands/seed_domain_templates.py` |

---

## 训练（已有）

| 用途 | 路径 |
|------|------|
| YOLO 节点 UI | `Frontend/src/components/workflow/nodes/YoloTrainingNode.vue` |
| WS 监控 | `Frontend/src/composables/useYoloTrainingMonitor.js` |
| 训练 API | `Frontend/src/api/training.js` |
| YOLO runner | `langchain_service.py` → `run_yolo_training_node` |
| 通用训练 runner | `langchain_service.py` → `run_model_training_node` |
| TrainingJob | `Backend/training/models.py` |
| WS 路由 | `Backend/training/routing.py`, `consumers.py` |

---

## 网站生成（已有 + M1 改）

| 用途 | 路径 |
|------|------|
| 模型 | `Backend/website_generator/models.py` |
| API | `Backend/website_generator/views.py` |
| CodeGraph 注册 | `register_site_codegraph()` in views.py |
| 检测站生成器 | `Backend/website_generator/generators/detection.py` |
| 基类 | `Backend/website_generator/generators/base.py` |
| 建站 runner | `langchain_service.py` → `run_website_generator_node` |
| 节点 UI | `Frontend/src/components/workflow/nodes/WebsiteGeneratorNode.vue` |
| 配置面板 | `Frontend/src/components/workflow/configs/WebsiteGeneratorConfig.vue` |
| 项目页 | `Frontend/src/views/projects/GeneratedSiteDetail.vue` |
| API 客户端 | `Frontend/src/api/websiteGenerator.js` |

---

## M1 已实现

| 用途 | 路径 |
|------|------|
| EP 节点 UI | `Frontend/src/components/workflow/nodes/EnvironmentProvisionNode.vue` |
| QA 节点 UI | `Frontend/src/components/workflow/nodes/SiteQaNode.vue` |
| Preview 节点 UI | `Frontend/src/components/workflow/nodes/SitePreviewNode.vue` |
| 节点壳（Desktop 预览） | `Frontend/src/components/workflow/nodes/SiteFactoryNodeShell.vue` |
| EP / QA / Preview runner | `langchain_service.py` → `run_environment_provision_node` 等 |
| QA 服务 | `Backend/website_generator/site_factory/qa_runner.py` |
| Playwright L3 检索站 | `qa_runner.py` → `_run_l3_clip_retrieval_playwright` |
| Desktop runtime | `Desktop/main.js`, `preload.js`, `useDesktopRuntime.js` |
| SQLite schema | `Backend/website_generator/site_factory/db_templates.py` |

---

## M2 已实现

| 用途 | 路径 |
|------|------|
| Profiler | `Backend/website_generator/site_factory/project_profiler.py` |
| Profiler UI | `Frontend/src/components/workflow/nodes/ProjectProfilerNode.vue` |
| Wizard | `Frontend/src/components/workflow/configs/TrainingSiteWizard.vue` |

---

## M3 已实现

| 用途 | 路径 |
|------|------|
| Project Agent | `Backend/website_generator/site_factory/project_agent.py` |
| Project Agent UI | `Frontend/src/components/workflow/nodes/ProjectAgentNode.vue` |
| Agent API | `Backend/website_generator/views.py` → `agent_message` |

---

## Desktop

| 用途 | 路径 |
|------|------|
| 说明 | `Desktop/README.md` |
| 主进程 | `Desktop/main.js`（`runtime:*` + `clipIndex:*` IPC） |
| 预加载 API | `Desktop/preload.js`（`agentAPI.startClipIndex`） |
| 训练脚本 | `Desktop/training-scripts/train_model.py` |
| CLIP 索引脚本 | `Desktop/training-scripts/build_clip_index.py` |
| 前端桥接 | `Frontend/src/composables/useClipIndexDesktop.js` |

---

## M4 已实现

| 用途 | 路径 |
|------|------|
| CLIP 分类 runner | `langchain_service.py` → `run_clip_classification_node` |
| CLIP 检索 runner | `langchain_service.py` → `run_clip_retrieval_node` |
| CLIP 零样本分类站 | `generators/classification.py` → `_generate_clip_classification_backend` |
| 检索站生成器 | `generators/clip_retrieval.py` |
| 索引构建脚本 | `Backend/scripts/build_clip_index.py` |
| 模板 | `Frontend/src/config/clipRetrievalWorkflowTemplate.js` |
| Wizard | `Frontend/src/components/workflow/configs/ClipClassificationWizard.vue` |

---

## 文档与测试

| 用途 | 路径 |
|------|------|
| 本专题 | `Docs/desktop-ml-site-factory/` |
| 节点契约 | `Docs/desktop-ml-site-factory/references/node-io-contracts.md` |
| E2E 审计 | `Docs/project-audits/03-action-plans/e2e-interaction-audit.md` |
| 全链路验收 | `Backend/scripts/site_factory_full_acceptance.py` |
| P1 自动化 | `Backend/scripts/p1_site_factory_automated_test.py` |
| Desktop 预检 | `Backend/scripts/desktop_manual_preflight_test.py` |
| 冒烟 | `Backend/scripts/frontend_user_api_smoke_test.py` |
| M1–M4 验收 | `Backend/scripts/m1_acceptance_test.py` … `m4_acceptance_test.py` |
| 测试报告 | `test-reports/` |

---

## Agent / RAG（M3 复用）

| 用途 | 路径 |
|------|------|
| Agent 节点 | `Frontend/src/components/workflow/nodes/AgentNode.vue` |
| Memory 节点 | `Frontend/src/components/workflow/nodes/MemoryNode.vue` |
| RAG API | `Frontend/src/api/`（knowledge / rag 相关） |
| Agents 后端 | `Backend/agents/` |
