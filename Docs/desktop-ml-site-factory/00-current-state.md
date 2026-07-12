# 00 — Desktop ML 站点工厂现状诊断

> 状态：**M1–M4 P0 + P1 自动化已落地**（2026-06-18）  
> 进度源：[`PROGRESS.md`](PROGRESS.md) · 剩余：**Desktop 人工走查 D-01–D05**

---

## 一、目标

记录 **站点工厂 M1–M4 完成后的** 真实代码状态，供后续维护与 Desktop 实机验收对照。

---

## 二、技术栈快照

| 层级 | 组件 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Vite | 工作流编辑器、站点工厂节点 UI |
| 后端 | Django + DRF + Daphne | 工作流执行、训练 API、WS |
| Desktop | Electron + Python 子进程 | YOLO 训练、CLIP 索引、`runtime:*` / `clipIndex:*` IPC |
| 生成站 | Flask + Vue 3 + SQLite | `website_generator/generators/*` |
| 平台 DB | MySQL | `GeneratedSite`、TrainingJob、Agent、RAG |
| 生成站 DB | SQLite | `backend/db/schema.sql` + `init_db.py`（M1） |

---

## 三、已完成项（基线 + M1–M4）

| # | 能力 | 代码位置 |
|---|------|----------|
| 1 | 训练页迁移；`/training` 重定向 | `TrainingRedirect.vue` |
| 2 | YOLO 节点 + WS 监控 | `YoloTrainingNode.vue`, `useYoloTrainingMonitor.js` |
| 3 | YOLO 九节点模板（含 profiler + M1 链 + agent） | `yoloWorkflowTemplate.js` |
| 4 | `environment_provision` / `site_qa` / `site_preview` | `langchain_service.py` + 节点 Vue |
| 5 | QA L1–L4 + 绿/黄/红 | `site_factory/qa_runner.py`, `qa_thresholds.py` |
| 6 | Desktop 预览 runtime | `Desktop/main.js` → `runtime:startSite` |
| 7 | `project_profiler` + `TrainingSiteWizard` | `project_profiler.py`, `TrainingSiteWizard.vue` |
| 8 | `project_agent` + 改码强制 QA | `project_agent.py`, `ProjectAgentNode.vue` |
| 9 | CLIP 分类/检索 + 检索站 | `clip_service.py`, `clip_retrieval.py` |
| 10 | Desktop CLIP 索引 | `build_clip_index.py`, `useClipIndexDesktop.js` |
| 11 | 全链路验收 | `site_factory_full_acceptance.py`, `p1_site_factory_automated_test.py` |

---

## 四、工作流节点链（当前）

**YOLO 检测**：

```
dataset_upload → yolo_training → project_profiler → website_generator
  → environment_provision → site_qa → site_preview → project_agent
```

**CLIP 检索**：

```
dataset_upload(image_text_pairs) → clip_retrieval → project_profiler
  → website_generator(clip_retrieval) → EP → QA → preview → agent
```

---

## 五、Desktop 运行时（当前）

| 能力 | 状态 |
|------|------|
| 加载 Frontend SPA | ✅ |
| 本地 YOLO 训练 | ✅ |
| 起停 Flask 预览 `runtime:startSite` | ✅ |
| CLIP 索引 `clipIndex:start` | ✅ |
| Playwright QA（服务端） | ✅ 检索站 Tab1/2/4；检测站静态+可选 Playwright |

**待人工**：Preview iframe 首次权限弹窗、Wizard/Agent UI 交互（见 `05-acceptance-checklist.md` D-01–D05）。

---

## 六、网站生成器（当前）

| 模板 | 后端 | 前端 | SQLite | 备注 |
|------|------|------|--------|------|
| detection | Flask | Vue 3 | ✅ | YOLO `/predict` |
| classification | Flask | Vue 3 | ✅ | 含 `framework=clip` 零样本 |
| clip_retrieval | Flask | Vue 3 | ✅ | 四 Tab + `/search/*` |
| regression | Flask | Vue 3 | ✅ | |
| nlp | Flask | Vue 3 | ✅ | |

---

## 七、风险与遗留

1. **CodeGraph `PROJECT_CONFIGS` 内存态** — 重启丢失；不阻塞发布。  
2. **RAG E2E** — M3.10 已实现写入逻辑；VectorStore 环境需人工验 M3-M02。  
3. **T-2 全链路** — 需 Flowly Desktop 实机跑 YOLO→Agent 改色。  
4. **T-5 API 冒烟** — 需后端 Daphne 在线：`frontend_user_api_smoke_test.py`。

---

## 八、备注

- 路径速查：[`references/key-files-index.md`](references/key-files-index.md)  
- 节点契约：[`references/node-io-contracts.md`](references/node-io-contracts.md)  
- 历史训练文档：[`05-training-workflow/`](../project-audits/05-training-workflow/README.md)（只读参考）
