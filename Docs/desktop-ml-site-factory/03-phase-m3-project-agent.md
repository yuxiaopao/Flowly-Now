# M3 — Project Agent + 改码强制 QA

> **状态（2026-06-18）**：P0 **已验收**；P1 对话 UI / RAG E2E **待 Desktop 人工**  
> **复验**：`cd Backend && python scripts/m3_acceptance_test.py`

---

## 一、范围

- 节点 `project_agent`（绑定 `generated_site_id` + `output_dir`）
- 项目级 Conversation + RAG 集合（有 VectorStore 时）
- 改码工具：限定在 `output_dir` 内写文件
- **任何代码变更 → site_qa 全量 → 通过才刷新 preview**

---

## 二、任务清单

### 2.1 数据模型

- [x] **M3.1** 扩展 `GeneratedSite`：`iterating` / `preview_status` / `rag_collection_id` / `last_agent_reply`
- [x] **M3.2** API：`POST /website-generator/{id}/agent/message/`

### 2.2 节点与 UI

- [x] **M3.3** `project_agent` runner：读站点上下文 + QA 最近报告
- [x] **M3.4** `ProjectAgentNode.vue`：节点内迷你对话（**UI 人工走查：M3-M01**）
- [x] **M3.5** 工具白名单：`read_file`, `write_file`, `list_dir`（限 output_dir）

### 2.3 改码 → QA 闭环

- [x] **M3.6** Agent 改码后自动 `run_site_qa`
- [x] **M3.7** QA red → 不更新 preview
- [x] **M3.8** QA green/yellow → 刷新 preview_url
- [x] **M3.9** 状态持久化 `iterating` / `preview_status`

### 2.4 记忆与知识库

- [x] **M3.10** RAG collection `project-{site_id}`（有 VectorStore 时）
- [ ] **M3.11** 同步全局 Agent「项目记忆」（可选，未做）
- [x] **M3.12** 导出 `conversation.json` + `audit.jsonl`

### 2.5 安全

- [x] **M3.13** 核心文件保护 + 删 `app.py` 拒绝
- [x] **M3.14** 审计 `audit.jsonl`

---

## 三、完成标准

1. [x] 改 Vue/CSS → QA → preview 更新（自动化 + `project_agent.py`）
2. [x] 删 `app.py` → 拒绝
3. [x] L2 失败 → 红灯，preview 不更新
4. [ ] 对话摘要 RAG 可检索（**P1 人工 M3-M02**）

---

## 四、依赖

- M1 `site_qa` + `site_preview`  
- 现有 `agents` app + RAG collections  

实现：`Backend/website_generator/site_factory/project_agent.py`
