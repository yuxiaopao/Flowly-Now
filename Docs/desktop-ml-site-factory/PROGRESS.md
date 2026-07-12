# Desktop ML 站点工厂 — 进度看板

> 每完成一项任务，将 `- [ ]` 改为 `- [x]`，并更新下方总览表与更新日志。  
> **最后更新**：2026-06-12

---

## 阶段总览

| Phase | 名称 | 进度 | 状态 | 文档 |
|-------|------|------|------|------|
| — | 文档体系 | 6/6 | 已验收 | [`README.md`](README.md) |
| M1 | QA + Preview + Scaffold | 18/18 | **P0 已验收** | [`01-phase-m1-qa-preview-scaffold.md`](01-phase-m1-qa-preview-scaffold.md) |
| M2 | Profiler + 建站向导 | 16/16 | **P0 已验收** | [`02-phase-m2-profiler-wizard.md`](02-phase-m2-profiler-wizard.md) |
| M3 | Project Agent + 强制 QA | 14/14 | **P0 已验收** | [`03-phase-m3-project-agent.md`](03-phase-m3-project-agent.md) |
| M4 | CLIP 节点 + 多素材数据集 | 16/16 | **P0 已验收** | [`04-phase-m4-clip-nodes.md`](04-phase-m4-clip-nodes.md) |
| P1 | 自动化可验项 | — | **脚本已就绪** | [`05-acceptance-checklist.md`](05-acceptance-checklist.md) |
| 验收 | 统一验收 M1–M4+P1 | 13/13 | 全链路已勾 | [`05-acceptance-checklist.md`](05-acceptance-checklist.md) |

---

## 文档验收（写代码前必过）

- [x] [`00-product-decisions.md`](00-product-decisions.md) 四项决策已定稿
- [x] [`references/node-io-contracts.md`](references/node-io-contracts.md) M1 节点契约完整
- [x] [`references/state-machines.md`](references/state-machines.md) 状态机无歧义
- [x] [`references/qa-threshold-matrix.md`](references/qa-threshold-matrix.md) 阈值与 Profile 一致
- [x] [`references/clip-retrieval-site-spec.md`](references/clip-retrieval-site-spec.md) 检索站规格完整
- [x] [`05-acceptance-checklist.md`](05-acceptance-checklist.md) 与 M1–M4 文档对齐

---

## 基线已完成（训练去重整合，勿重复做）

- [x] 删除独立 `/training`、`/training/yolo/*` 页；保留 `/training` 重定向
- [x] `yolo_training` 与 `model_training` 职责分离（YOLO 仅 yolo 节点）
- [x] `WorkflowOptimizer` 合并进 `WorkflowAssistant`（`/optimize`）
- [x] YOLO 工作流模板 `yolo-detection-project`
- [x] `YoloTrainingNode` WS 实时图表 / ETA / 环境检测 / 本地权重
- [x] `website_generator` + `/projects/:id` + 侧栏「识别项目」
- [x] `GeneratedSite.codegraph_project_id` / `show_in_nav`

---

## M1 — QA + Preview + Scaffold（18/18）

- [x] M1.1 `DetectionGenerator` 增加 SQLite schema + 固定迁移脚本
- [x] M1.2 生成站 `requirements.txt` 锁定 Flask/Vue/SQLite 版本
- [x] M1.3 新增节点类型 `environment_provision`（后端 runner + 前端节点）
- [x] M1.4 Desktop `main.js` 暴露 runtime API（起停服务、端口、路径权限）
- [x] M1.5 新增节点类型 `site_qa`（L1–L4 分层检查）
- [x] M1.6 QA L2：Flask `/health` + `/predict` 冒烟
- [x] M1.7 QA L3：静态首页检查 + 可选 Playwright skip
- [x] M1.8 QA L4：验证集指标 + 绿/黄/红判定（见 threshold matrix）
- [x] M1.9 QA 报告：自然语言摘要 + 截图路径 + 结构化 JSON
- [x] M1.10 新增节点类型 `site_preview`（iframe + 截图路径占位）
- [x] M1.11 工作流模板：`… → website_generator → EP → QA → PV`
- [x] M1.12 `nodeRegistry.js` / `langchain_service.py` 注册新节点
- [x] M1.13 `node-io-contracts.md` 与实现一致（已回填 §7–10）
- [x] M1.14 冒烟：`m1_site_factory_smoke_test.py`（新节点无独立 REST）
- [x] M1.15 E2E：M1 路径写入 `e2e-interaction-audit.md`
- [x] M1.16 Desktop 权限：目录读写 + 子进程 + localhost 一次授权
- [x] M1.17 M1 验收清单全部勾选
- [x] M1.18 `test-reports/` 留存 QA 报告样例

---

## M2 — Profiler + 建站向导（16/16）

- [x] M2.1 新增 `project_profiler` 节点 + runner
- [x] M2.2 输入 class_names / model_path / website_type
- [x] M2.3 输出 profile.json 契约字段
- [x] M2.4 规则引擎 + 可选 LLM 润色
- [x] M2.5 `ProjectProfilerNode.vue`
- [x] M2.6 `TrainingSiteWizard.vue` 四步
- [x] M2.7–M2.10 Wizard 各步 + 必填校验
- [x] M2.11 上游训练节点自动填充
- [x] M2.12–M2.14 生成器 profile/wizard 注入 + SQLite 不变
- [x] M2.15 YOLO 七节点链（含 profiler）
- [x] M2.16 node-io-contracts 更新
- [x] 冒烟 `m2_profiler_smoke_test.py`

---

## M3 — Project Agent（14/14）

- [x] M3.1 `GeneratedSite` 扩展：`iterating` / `preview_status` / `rag_collection_id` / `last_agent_reply`
- [x] M3.2 API：`POST /website-generator/{id}/agent/message/`
- [x] M3.3 `project_agent` runner（langchain_service）
- [x] M3.4 `ProjectAgentNode.vue` 节点内迷你对话
- [x] M3.5 沙箱工具：`read_file` / `write_file` / `list_dir`（限 output_dir）
- [x] M3.6 改码后自动 `run_site_qa`
- [x] M3.7 QA red → 不更新 preview
- [x] M3.8 QA green/yellow → 刷新 preview_url
- [x] M3.9 状态持久化 `iterating` / `preview_status`
- [x] M3.10 RAG collection `project-{site_id}`（有 VectorStore 时）
- [x] M3.11 对话 `conversation.jsonl` → `conversation.json` 导出
- [x] M3.12 审计 `audit.jsonl`
- [x] M3.13 核心文件保护 + 删 app.py 拒绝
- [x] M3.14 YOLO 八节点链 + `m3_acceptance_test.py`

---

## M4 — CLIP（16/16）

- [x] M4.1 `dataset_upload` ML format 校验（`ml_format_validators.py`）
- [x] M4.2 `/datasets` 配置面板 format 说明（DatasetUploadConfig）
- [x] M4.4–M4.5 `clip_classification` runner（零样本 + finetune + WS）
- [x] M4.8–M4.9 `clip_retrieval` 索引构建 + R@K metrics
- [x] M4.10 QA L2/L3 检索站 `/search/text` + Playwright Tab1/2/4
- [x] M4.11 `ClipRetrievalGenerator` 四 Tab + API + CLIP runtime
- [x] M4.12 模板 `clip-retrieval-project` + `clipRetrievalWorkflowTemplate.js`
- [x] M4.13 `training_kind`: `clip_cls` | `clip_ret`
- [x] M4.3 标注导出 `image_text_pairs`（`POST .../export/?format=image_text_pairs`）
- [x] M4.7 CLIP 零样本分类站（`ClassificationGenerator` framework=clip）
- [x] M4.14–M4.15 Desktop GPU 索引 IPC（`clipIndex:start` + `build_clip_index.py`）+ WS 索引进度
- [x] M4.6 Wizard 专用 CLIP 步骤（`TrainingSiteWizard` indexDir / 示例 query / Top-K）
- [x] M4.16 CLIP 向量：安装 `clip`+`torch` 时自动用 ViT-B/32，否则 BOW 回退
- [x] M4.17 Desktop 预览：`SitePreviewNode` 联调 `runtime.startSite`

---

## 决策变更日志

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-06-12 | 初版文档体系建立 | CLIP 演示站+API Tab；QA 阈值矩阵；SQLite 生成站 |
| 2026-06-12 | 建站 output_dir 默认 `{训练目录}/generated_site` | 避免与 YOLO 权重目录冲突 |

---

## 更新日志

| 日期 | 完成项 | 负责人 | 备注 |
|------|--------|--------|------|
| 2026-06-12 | 建立 `Docs/desktop-ml-site-factory/` 全套文档 | Agent | 文档验收 6/6 通过 |
| 2026-06-12 | M1 全量落地 + 冒烟验收 | Agent | `m1_site_factory_smoke_test.py` |
| 2026-06-18 | M1 正式验收 P0 通过 | Agent | `m1_acceptance_test.py` |
| 2026-06-18 | M2 核心实现 + 正式验收 P0 通过 | Agent | `m2_acceptance_test.py` |
| 2026-06-18 | M4.7/M4.14 Desktop CLIP 索引 IPC + 零样本分类站 | Agent | `m4_acceptance_test.py` 19/19 |
| 2026-06-18 | Desktop 无头验收 + 全链路含 T-5 | Agent | `desktop_headless_acceptance.py` |

---

## Desktop 人工走查清单（唯一剩余项）

在 **Flowly Desktop**（非浏览器）按序执行，勾选后更新 [`05-acceptance-checklist.md`](05-acceptance-checklist.md)：

1. **Preview iframe（M1-M01）**：YOLO 链跑到 `site_preview` → 展开节点 → 确认权限弹窗一次授权 → iframe 加载本地站  
2. **Wizard UI（M2-M02）**：`website_generator` PropertyPanel → 四步向导逐步填写 → 完成向导后 config 回写  
3. **Agent 对话（M3-M01）**：`project_agent` 发送「把主色改成 #3b82f6」→ 改码 → QA 刷新 → preview 更新  
4. **CLIP Desktop 索引（M4）**：`clip_retrieval` 设 `indexMode=desktop` → 执行工作流 → 日志见 GPU 索引进度  
5. **全链路（T-2）**：YOLO 训练 → 建站 → QA 绿/黄 → Preview → Agent 改色 → 再 QA

---

## 下一步

1. 预检：`python Backend/scripts/desktop_manual_preflight_test.py`（静态 + 可选服务/GPU）  
2. **Desktop UI 人工走查**（D-01–D05，见上方清单）  
3. 一键复验：`python Backend/scripts/site_factory_full_acceptance.py`（M1–M4 + P1 + Preflight + Desktop + T-5）
