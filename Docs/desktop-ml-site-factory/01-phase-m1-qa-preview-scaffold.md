# M1 — QA + Preview + SQLite Scaffold + Desktop Runtime

> **优先级**：P0（文档验收后首个代码里程碑）  
> **目标**：生成站可本地跑通、可全面自查、可在工作流节点内真实预览。  
> **状态**：✅ 代码与冒烟已验收（2026-06-12）

---

## 一、为什么要先做 M1

- 用户（尤其非技术用户）需要 **「能看、能测、报告能读懂」**，再扩展 CLIP/Agent。  
- 无 QA 守门，后续 AI 改站会堆 bug。  
- SQLite + 固定 scaffold 降低生成随机性，为 M2/M3 填槽打基础。

---

## 二、范围

### 包含

- 生成站 **Flask + Vue + SQLite** 固定 scaffold（先 **detection** 模板，其他模板 M1 末或 M2 跟进）
- 新工作流节点：`environment_provision`、`site_qa`、`site_preview`
- Desktop runtime API（起停服务、端口分配、权限 manifest）
- QA L1–L4 + 报告 + Profile 判定
- 工作流模板扩展：`website_generator → EP → QA → PV`
- 文档/测试：`e2e-interaction-audit.md`、冒烟（如有 REST）

### 不包含

- `project_profiler`（M2）
- `project_agent`（M3）
- CLIP 节点（M4）
- 云端 sandbox

---

## 三、任务清单

### 3.1 Scaffold + SQLite

- [x] **M1.1** `DetectionGenerator` 增加 `backend/db/`：`schema.sql` + `init_db.py` + SQLAlchemy/peewee 二选一（与现有 Flask 风格一致优先 **原生 sqlite3**）
- [x] **M1.2** 固定表：`inference_logs(id, created_at, input_summary, output_summary, latency_ms)`、`app_settings(key, value)`、`feedback(id, message, rating, created_at)`
- [x] **M1.3** Flask `app.py`：启动时 init DB；`/predict` 写 `inference_logs`
- [x] **M1.4** `requirements.txt` 锁定版本；禁止 AI 生成阶段改依赖 major 版本

### 3.2 Desktop Runtime

- [x] **M1.5** `Desktop/main.js`：`runtime.startSite({ outputDir, port, env })` / `runtime.stopSite(siteId)`
- [x] **M1.6** `preload.js` 暴露 `window.flowlyDesktop.runtime.*`
- [x] **M1.7** 端口池：49152–49252 自动选取；冲突检测
- [x] **M1.8** 权限 manifest：用户首次确认 `{ paths, allowSubprocess, allowLocalhost }`

### 3.3 节点 `environment_provision`

- [x] **M1.9** 后端 `run_environment_provision_node()`：汇总 Python/Node/CUDA/磁盘/权重可读
- [x] **M1.10** Desktop 模式：调用 runtime 预检；输出 `runtime_manifest`
- [x] **M1.11** 前端 `EnvironmentProvisionNode.vue` + Config checklist UI

### 3.4 节点 `site_qa`

- [x] **M1.12** 后端 `run_site_qa_node()`：编排 L1–L4（Desktop 调 Playwright 或 subprocess）
- [x] **M1.13** L1：目录、依赖 install dry-run、权重、SQLite 文件可创建
- [x] **M1.14** L2：`runtime.startSite` → GET `/health` → POST `/predict`（检测）或 `/search/text`（检索，M4 后）
- [x] **M1.15** L3：Playwright 脚本 1 条主路径；截图存 `outputDir/.flowly/qa/screenshots/`（无 Playwright 时静态首页检查 + skip 标注）
- [x] **M1.16** L4：读取上游 `metrics` 或现场跑验证集；调用 [`qa-threshold-matrix.md`](references/qa-threshold-matrix.md)
- [x] **M1.17** 输出 `qa_report.json` + `summary_zh` + `gate`: `green|yellow|red`
- [x] **M1.18** 前端 `SiteQaNode.vue`：展开报告、红黄绿 badge

### 3.5 节点 `site_preview`

- [x] **M1.19** 依赖 QA `gate != red`（`research` Profile 允许 yellow）
- [x] **M1.20** iframe `previewUrl`；可选每 30s 截图缩略图（路径占位 `.flowly/preview/latest.png`）
- [x] **M1.21** 前端 `SitePreviewNode.vue`

### 3.6 集成

- [x] **M1.22** `nodeRegistry.js`、`nodeComponents.js`、`langchain_service.py` 注册
- [x] **M1.23** 更新 YOLO 模板边：`website_generator → environment_provision → site_qa → site_preview`
- [x] **M1.24** `GeneratedSite` 可选字段：`last_qa_report`、`last_preview_url`（migration 0003）
- [x] **M1.25** E2E 审计 + `test-reports/site-qa-sample.json` 样例

---

## 四、M1 节点 I/O 摘要

完整契约：[`references/node-io-contracts.md`](references/node-io-contracts.md)

### `environment_provision`

**输入**：`outputDir`, `modelPath`, `siteId`, `runtimeMode: desktop|cloud`

**输出**：
```json
{
  "ready": true,
  "runtime_manifest": {
    "python": "3.10",
    "cuda_available": true,
    "disk_free_gb": 42,
    "assigned_port": 49152,
    "paths_granted": ["E:/projects/site-xxx/generated_site"]
  },
  "checks": [{ "key": "gpu", "ok": true, "detail": "..." }]
}
```

### `site_qa`

**输入**：`generatedSiteId`, `outputDir`, `modelPath`, `websiteType`, `qaProfile`, `validationSetPath?`

**输出**：
```json
{
  "gate": "green",
  "layers": { "l1": "pass", "l2": "pass", "l3": "pass", "l4": "pass" },
  "metrics": { "map50": 0.78 },
  "report_path": ".flowly/qa/qa_report.json",
  "summary_zh": "全部检查通过，mAP50 78%，可进行预览。"
}
```

### `site_preview`

**输入**：`generatedSiteId`, `port`, `qaGate`

**输出**：
```json
{
  "preview_url": "http://127.0.0.1:49152",
  "screenshot_path": ".flowly/preview/latest.png",
  "status": "live"
}
```

---

## 五、状态机（M1 相关）

见 [`references/state-machines.md`](references/state-machines.md) — 站点 `draft → qa_pending → preview_ready`。

---

## 六、完成标准

1. YOLO 模板工作流跑通至 **Preview 节点 iframe 可见上传检测结果**  
2. QA 故意失败（坏权重）时 **红灯 + 中文报告**，Preview 阻断（default Profile）  
3. Desktop 重启后 **同 outputDir 可再次 EP + QA**  
4. 文档契约与实现一致，M1 验收清单全勾  

**自动化验证（2026-06-12）**：

```bash
cd Backend && python scripts/m1_site_factory_smoke_test.py
```

输出：`test-reports/m1-smoke-result.json`（绿灯路径 gate=green，红灯路径 gate=red）

**待 Desktop 人工验**：iframe 预览 UI、Playwright L3 全量、首次权限弹窗。

---

## 七、风险

| 风险 | 缓解 |
|------|------|
| Playwright 体积大 | Desktop 可选组件；无 Playwright 时 L3 skip + 报告标注 |
| Windows 路径权限 | manifest 明确列出 granted paths |
| 验证集缺失 | L4 skip，gate 最高 yellow |
| YOLO 与建站共用 output_dir | 建站默认写入 `{output_dir}/generated_site` |

---

## 八、关键代码（预计修改）

见 [`references/key-files-index.md`](references/key-files-index.md) M1 节。
