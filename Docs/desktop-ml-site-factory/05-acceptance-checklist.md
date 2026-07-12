# 统一验收清单

> 每里程碑完成后勾选对应章节；全项目收尾勾选「总验收」  
> 最后更新：2026-06-12

---

## 文档验收（写代码前）

- [x] [`README.md`](README.md) 第七节 6 项已全部勾选
- [x] [`00-product-decisions.md`](00-product-decisions.md) 七项决策均标记已定稿
- [x] [`references/node-io-contracts.md`](references/node-io-contracts.md) M1 节点（§8–10）完整
- [x] [`references/state-machines.md`](references/state-machines.md) 与 Profile 交叉规则一致
- [x] [`references/qa-threshold-matrix.md`](references/qa-threshold-matrix.md) 与 decisions 一致
- [x] [`PROGRESS.md`](PROGRESS.md) 阶段总览已初始化

---

## M1 验收 — QA + Preview + Scaffold

> **正式验收报告**：[`test-reports/M1_ACCEPTANCE_REPORT.md`](../../test-reports/M1_ACCEPTANCE_REPORT.md)  
> **复验命令**：`cd Backend && python scripts/m1_acceptance_test.py`  
> **结论（2026-06-18）**：P0 **52/52 通过**；P1 待补验 **3 项**（不阻断进入 M2）

### 功能

- [x] M1-F1 检测站生成物含 `backend/db/schema.sql` 与 SQLite 初始化
- [x] M1-F2 `/predict` 写入 `inference_logs` 表（`inference_logs_count≥1`）
- [x] M1-F3 `environment_provision` 输出 runtime_manifest（后端 + Desktop IPC）
- [x] M1-F4 `site_qa` L1–L4 均可执行并生成 `qa_report.json`
- [x] M1-F5 L2 失败时 gate=red，summary_zh 可读（M1-L02）
- [x] M1-F6 L3 Playwright 主路径（**P1**：默认 skip + 静态首页检查；全量 Playwright 待 Desktop 补验）
- [x] M1-F7 L4 mAP50 阈值与 threshold matrix 一致（M1-T01–T06）
- [ ] M1-F8 `site_preview` iframe 加载本地 preview_url（**P1**：组件已实现，Desktop UI 待人工验）
- [x] M1-F9 default Profile + red gate 阻断 preview（M1-P01–P05）
- [x] M1-F10 YOLO 模板边含 EP → QA → PV（M1-S17）

### 质量

- [x] M1-Q1 无 Mock 假成功（QA 来自真实 L1/L2/subprocess）
- [x] M1-Q2 Desktop 停服后端口释放（M1-S14）
- [x] M1-Q3 节点 IO 与 node-io-contracts 一致

### 文档与测试

- [x] M1-D1 `e2e-interaction-audit.md` 增加 M1 节
- [x] M1-D2 `test-reports/` 样例 + `M1_ACCEPTANCE_REPORT.md`
- [x] M1-D3 `PROGRESS.md` M1 任务全勾

### P1 待补验（不阻断 M2）

> 与下方 **Desktop 人工走查 D-01–D03** 对应；自动化已覆盖组件存在性（P1 脚本 22/22）。

- [ ] M1-M01 / **D-01** Desktop iframe Preview 节点 UI
- [x] M1-M02 Playwright L3 检索站 Tab（自动化）；检测站全路径待 Desktop
- [ ] M1-M03 / **D-01** Desktop 权限 manifest 首次弹窗

---

## M2 验收 — Profiler + Wizard

> **正式验收报告**：[`test-reports/M2_ACCEPTANCE_REPORT.md`](../../test-reports/M2_ACCEPTANCE_REPORT.md)  
> **复验命令**：`cd Backend && python scripts/m2_acceptance_test.py`  
> **结论（2026-06-18）**：P0 **全部通过**；P1 待优化 **2 项**（不阻断 M3）

### 功能

- [x] M2-F1 profiler 输出 scenario 与 class_names 语义一致（M2-P01–P06）
- [x] M2-F2 Wizard 四步必填校验（M2-W01–W05）
- [x] M2-F3 生成站首页文案来自 wizard/profile（M2-G01–G04）
- [x] M2-F4 YOLO 模板含 profiler 节点（M2-T01–T05）
- [x] M2-F5 SQLite schema 未被 generator 改写（M2-G05）
- [x] M2-F6 M1 回归仍通过（M2-R01）

### 质量

- [x] M2-Q1 节点 IO 与 node-io-contracts §6 一致（M2-D01–D02）
- [x] M2-Q2 规则引擎优先，LLM 润色可选且可跳过

### P1 待补验（不阻断 M2）

- [x] M2-M01 classification 生成器 profile/wizard 注入（`ClassificationGenerator` + profiler）
- [ ] M2-M02 PropertyPanel Wizard 四步 UI 人工走查

---

## Desktop 人工走查（站点工厂收尾）

> 环境：Flowly Desktop + 后端 Daphne `127.0.0.1:8000` + 前端或 Desktop 内嵌页  
> 账号：`nlwftest@flowly.test` · 模板：`yolo-detection-project` / `clip-retrieval-project`

| ID | 步骤 | 期望 | 状态 |
|----|------|------|------|
| D-01 | 展开 `site_preview`，首次授权目录/localhost | iframe 显示生成站首页 | 🟡 配置面板 OK；iframe/权限需 Desktop 执行工作流后验 |
| D-02 | Wizard 四步完成建站 | `wizardCompleted=true` 写入节点 config | ✅ 浏览器四步+完成 Toast；节点 outputDir 回显 |
| D-03 | ProjectAgent 改主色/标题 | 文件变更 + QA 重跑 + preview 刷新 | 🟡 Agent 配置面板 OK；E2E 改码需已生成站点 |
| D-04 | CLIP `indexMode=desktop` 执行 | Desktop 日志索引进度 0→100% | 🟡 UI+脚本链 OK（P1-G01/build_clip_index 冒烟通过）；IPC 进度需 Desktop 内执行 |
| D-05 | YOLO 全链路 T-2 | 训练→建站→QA→预览→Agent→再QA 无断层 | 🟡 `?template=yolo` 已修复别名，8 节点链 OK；全链路执行待数据集 |

---

## M3 验收 — Project Agent

> **正式验收报告**：[`test-reports/M3_ACCEPTANCE_REPORT.md`](../../test-reports/M3_ACCEPTANCE_REPORT.md)  
> **复验命令**：`cd Backend && python scripts/m3_acceptance_test.py`  
> **结论（2026-06-18）**：P0 **自动化通过**；P1 对话 UI / RAG E2E 待人工

- [x] M3-1 改 Vue 文案后自动 QA 并刷新 preview（`project_agent.py` + runner 强制 QA）
- [x] M3-2 删 core infer 文件被拒绝或二次确认（沙箱保护 `app.py`）
- [x] M3-3 QA 失败时不更新 preview（gate=red 阻断）
- [ ] M3-4 对话摘要写入项目 RAG 可检索（**P1 人工**：需 VectorStore 环境）
- [x] M3-5 状态机 iterating → qa_pending 正确（`GeneratedSite` 字段 + migration）

### P1 待补验

- [ ] M3-M01 ProjectAgentNode 迷你对话 UI 人工走查
- [ ] M3-M02 RAG collection 检索 E2E

---

## M4 验收 — CLIP

> **正式验收报告**：[`test-reports/M4_ACCEPTANCE_REPORT.md`](../../test-reports/M4_ACCEPTANCE_REPORT.md)  
> **P1 自动化**：[`test-reports/P1_SITE_FACTORY_AUTOMATED.md`](../../test-reports/P1_SITE_FACTORY_AUTOMATED.md)  
> **复验命令**：`cd Backend && python scripts/m4_acceptance_test.py && python scripts/p1_site_factory_automated_test.py`

- [x] M4-1 `image_text_pairs` 上传校验通过（`ml_format_validators.py`）
- [x] M4-2 检索站四 Tab 可访问（生成 HTML + L3 Playwright）
- [x] M4-3 `/search/text` 与 `/search/image` 返回 Top-K（L2 + generator API）
- [x] M4-4 QA L4 R@5 阈值正确（`qa_thresholds.py` + P1-Q01）
- [x] M4-5 API Tab cURL 可复制执行（Tab4 模板 + curl 示例）
- [x] M4-6 `clip-retrieval-project` 模板一键创建（seed + Editor 路由）

---

## 总验收（M1–M4 完成后）

- [x] T-1 训练去重基线仍成立（无独立训练页回归）
- [ ] T-2 Desktop 端到端：YOLO 训练 → 建站 → QA → 预览 → Agent 改色 → 再 QA（**P1 人工**）
- [x] T-3 CLIP 检索链端到端可演示（`m4_chain_smoke_test.py` + 全链路验收）
- [x] T-4 学者 Profile 黄灯可预览；小白 Profile 发布仅绿灯（threshold matrix + M1-T01–T06）
- [x] T-5 冒烟测试无回归（`frontend_user_api_smoke_test.py` 2026-06-18 通过）
- [x] T-6 架构决策节与实现一致（node-io-contracts + PROGRESS）
- [x] T-7 无 `cursor-ide-browser` 测试违规（chrome-devtools only）

---

## 验收签字

| 里程碑 | 验收人 | 日期 | 备注 |
|--------|--------|------|------|
| 文档 | | 2026-06-12 | 6/6 |
| M1 | Agent | 2026-06-18 | P0 52/52 通过；见 `test-reports/M1_ACCEPTANCE_REPORT.md` |
| M2 | Agent | 2026-06-18 | P0 通过；见 `test-reports/M2_ACCEPTANCE_REPORT.md` |
| M3 | Agent | 2026-06-18 | P0 自动化通过；见 `test-reports/M3_ACCEPTANCE_REPORT.md` |
| M4 | Agent | 2026-06-18 | P0+P1 自动化通过；见 `test-reports/M4_ACCEPTANCE_REPORT.md` |
| 总验收 | Agent | 2026-06-18 | M1–M4+P1 自动化 + T-5；T-2 Desktop E2E 待人工 |
