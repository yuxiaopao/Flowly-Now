# 节点 I/O 契约

> 版本：1.1（2026-06-18）  
> 实现后若字段变更，须同步更新本文 + [`PROGRESS.md`](../PROGRESS.md)

字段命名：**REST/WS 用 snake_case**；前端节点 config 可用 camelCase，runner 内统一 snake。

---

## 1. `dataset_upload`（已有，M4 扩展）

### 输出（context 下游可读）

```json
{
  "dataset_id": "uuid",
  "dataset_path": "/path/to/data",
  "format": "yolo|image_folder|image_text_pairs|classification_folders",
  "class_names": ["a", "b"],
  "stats": { "image_count": 1200, "label_count": 1200 }
}
```

---

## 2. `yolo_training`（已有）

### 输出

```json
{
  "training_run_id": "uuid",
  "best_weight_path": "/path/best.pt",
  "last_weight_path": "/path/last.pt",
  "class_names": ["helmet", "no_helmet"],
  "metrics": { "map50": 0.72, "fitness": 0.85 },
  "websocket_url": "/ws/training/{id}/"
}
```

---

## 3. `model_training`（已有，非 YOLO）

### 输出

```json
{
  "training_run_id": "uuid",
  "model_path": "/path/model.pt",
  "framework": "pytorch|transformers",
  "labels": ["cat", "dog"]
}
```

---

## 4. `clip_classification`（M4）

### config

```json
{
  "mode": "zero_shot|finetune",
  "classNames": ["cat", "dog"],
  "baseModel": "ViT-B/32",
  "epochs": 10,
  "outputDir": "/path/out",
  "trainingMode": "local|cloud"
}
```

### 输出

```json
{
  "training_run_id": "uuid",
  "training_status": "completed|running",
  "websocket_url": "/ws/training/{id}/",
  "model_path": "/path/clip.pt",
  "class_names": ["cat", "dog"],
  "metrics": { "accuracy": 0.91, "mode": "zero_shot" },
  "mode": "zero_shot",
  "base_model": "ViT-B/32"
}
```

**建站**：`training_kind=clip_cls` 时 `website_generator` 自动设 `framework=clip`，零样本走 `ClassificationGenerator` CLIP 相似度推理站（M4.7）。

---

## 5. `clip_retrieval`（M4）

### config

```json
{
  "indexType": "flat|hnsw",
  "indexMode": "server|desktop",
  "baseModel": "ViT-B/32|simple-bow",
  "outputDir": "/path/index",
  "prebuiltIndexDir": "/path/index",
  "trainingMode": "local|cloud"
}
```

| 字段 | 说明 |
|------|------|
| `indexMode=server` | 默认；索引在 Flowly 服务端子进程构建 |
| `indexMode=desktop` | Flowly Desktop 执行工作流前本机 GPU 构建，结果写入 `prebuiltIndexDir` 后 runner 跳过服务端构建 |
| `prebuiltIndexDir` | Desktop 预构建或节点内「本地 GPU 构建」完成后填入 |

### 输出

```json
{
  "training_run_id": "uuid",
  "training_status": "running|completed",
  "execution_mode": "local|desktop",
  "index_mode": "server|desktop",
  "built_on": "server|desktop",
  "websocket_url": "/ws/training/{id}/",
  "gpu_info": { "available": true, "name": "NVIDIA ...", "recommended_batch_size": 32 },
  "index_dir": "/path/index",
  "metadata_path": "/path/index/metadata.json",
  "encoder": "clip|bow|pending",
  "metrics": { "r_at_1": 0.65, "r_at_5": 0.82, "r_at_10": 0.88 },
  "image_count": 120,
  "duration_ms": 4500
}
```

**Desktop IPC（M4.14）**：Electron `agentAPI.startClipIndex(jobConfig)` → `clipIndex:start` → `build_clip_index.py`；进度事件 `clipIndex:progress` / `clipIndex:complete`。

---

## 6. `project_profiler`（M2）

### config

```json
{
  "websiteType": "detection|classification|clip_retrieval",
  "useLlmEnrich": false,
  "classNames": [],
  "modelPath": "",
  "sampleImagePaths": []
}
```

### 输出

```json
{
  "profile": {
    "domain": "工业安全",
    "scenario": "安全帽佩戴检测",
    "ui_tone": "industrial_warning",
    "copy_hints": ["上传现场照片", "红框标注未佩戴区域"],
    "risk_notes": ["低照度场景误检率可能升高"],
    "recommended_template": "detection",
    "class_display_names": { "helmet": "已佩戴安全帽", "no_helmet": "未佩戴安全帽" },
    "class_names": ["helmet", "no_helmet"],
    "profiler_version": "1.0-rules"
  },
  "profile_path": ".flowly/profile.json",
  "domain": "工业安全",
  "scenario": "安全帽佩戴检测",
  "recommended_template": "detection"
}
```

**实现**：规则引擎（类名关键词）优先；`useLlmEnrich=true` 且配置 OpenAI Key 时可润色文案，不生成代码。

### `website_generator` wizard 输入（M2）

```json
{
  "wizard": {
    "siteName": "必填",
    "usageDescription": "必填",
    "primaryColor": "#f59e0b",
    "disclaimer": "",
    "outputDir": "",
    "port": 5000,
    "qaProfile": "default",
    "indexDir": "",
    "exampleQueries": "一只橘猫, 工业现场",
    "topK": 12,
    "wizardCompleted": true
  },
  "profile": {}
}
```

执行时 `wizardCompleted=true` 且缺 `siteName` → 节点失败。

---

## 7. `website_generator`（已有，M1/M2 增强）

### config

```json
{
  "websiteType": "detection|classification|clip_retrieval",
  "framework": "pytorch|ultralytics|clip",
  "modelPath": "",
  "indexDir": "",
  "labels": "",
  "outputDir": "",
  "port": 5000,
  "frontendFramework": "vue",
  "backendFramework": "flask",
  "trainingRunId": "",
  "profile": {},
  "wizard": {
    "siteName": "",
    "logoUrl": "",
    "primaryColor": "",
    "contactEmail": "",
    "disclaimer": ""
  }
}
```

### 输出

```json
{
  "site_id": "uuid",
  "status": "generating|completed|failed",
  "output_dir": "",
  "website_output_dir": "",
  "url": "/projects/{site_id}",
  "inference_endpoint": "http://localhost:5000/predict",
  "website_type": "detection|classification|clip_retrieval"
}
```

`clip_retrieval` 时 `inference_endpoint` 为 `http://localhost:{port}/search/text`；`framework=clip` 分类站为 `/predict`（CLIP 相似度）。

**路径约定**：若上游 `yolo_training` 已占用 `output_dir`（含权重），建站默认写入 `{output_dir}/generated_site`；下游 EP/QA/Preview 应读 `output_dir`（建站节点输出）或 context 合并后的同名字段。

---

## 8. `environment_provision`（M1）

### config

```json
{
  "outputDir": "",
  "modelPath": "",
  "siteId": "",
  "runtimeMode": "desktop"
}
```

### 输出

```json
{
  "ready": true,
  "runtime_manifest": {
    "python": "3.10",
    "platform": "Windows",
    "cuda_available": true,
    "disk_free_gb": 42.0,
    "assigned_port": 49152,
    "paths_granted": ["E:/projects/site-xxx/generated_site"],
    "runtime_mode": "desktop",
    "site_id": "uuid",
    "backend_dir": "E:/projects/site-xxx/generated_site/backend"
  },
  "checks": [
    { "key": "python", "label": "Python 版本", "ok": true, "detail": "3.10" },
    { "key": "output_dir", "label": "输出目录", "ok": true, "detail": "..." },
    { "key": "backend_app", "label": "Flask 后端", "ok": true, "detail": "..." },
    { "key": "port", "label": "分配端口", "ok": true, "detail": "49152" }
  ],
  "assigned_port": 49152,
  "output_dir": "",
  "model_path": "",
  "site_id": "uuid"
}
```

**说明**：`model_path` / `cuda` 检查失败不阻断 `ready`（Demo 模式可继续）；`output_dir` 与 `backend/app.py` 必须存在。

---

## 9. `site_qa`（M1）

### config

```json
{
  "generatedSiteId": "",
  "outputDir": "",
  "modelPath": "",
  "websiteType": "detection",
  "qaProfile": "default|research",
  "validationSetPath": "",
  "skipPlaywright": false
}
```

### 输出

```json
{
  "gate": "green|yellow|red",
  "layers": {
    "l1": "pass|fail|skip",
    "l2": "pass|fail|skip",
    "l3": "pass|fail|skip",
    "l4": "pass|fail|skip"
  },
  "metrics": {},
  "report_path": "",
  "summary_zh": "",
  "screenshots": []
}
```

---

## 10. `site_preview`（M1）

### config

```json
{
  "generatedSiteId": "",
  "outputDir": "",
  "port": 49152,
  "qaGate": "green|yellow|red",
  "qaProfile": "default|research"
}
```

### 输出

```json
{
  "preview_url": "http://127.0.0.1:49152",
  "screenshot_path": "",
  "status": "live|blocked|failed"
}
```

### Desktop 预览（M1 P1 / M4.17）

`SitePreviewNode` → `SiteFactoryNodeShell` 在 Flowly Desktop 中：

| 属性 | 说明 |
|------|------|
| `enable-desktop-preview` | 展开节点时调用 `runtime.startSite({ outputDir, port, siteId })` |
| `effectivePreviewUrl` | Desktop 返回的 `http://127.0.0.1:{port}`，浏览器模式回退 `preview_url` |
| `blocked` | `qaGate=red` 且 `qaProfile=default` 时不启动服务、不渲染 iframe |

**IPC**：`window.flowlyDesktop.runtime.startSite` / `stopSite`（见 `Desktop/main.js` + `useDesktopRuntime.js`）。

**阻断规则**：

- `qaProfile=default`：`gate=red` → `status=blocked`
- `qaProfile=research`：`gate=red` → blocked；`yellow` → live + warning

---

## 11. `project_agent`（M3）

### config

```json
{
  "generatedSiteId": "",
  "outputDir": "",
  "agentId": "",
  "autoQaAfterEdit": true
}
```

### 输入 message（用户）

```json
{
  "role": "user",
  "content": "把首页改成深色主题"
}
```

### 输出

```json
{
  "reply": "",
  "files_changed": ["frontend/src/App.vue"],
  "qa_triggered": true,
  "qa_gate": "green",
  "preview_url": ""
}
```

---

## 13. `backend_setup`（v2 AI 分工）

### config

```json
{
  "outputDir": "",
  "websiteType": "detection",
  "agentMode": "auto|rules|llm",
  "allowCoreEdit": true,
  "autoQaAfterEdit": true,
  "instruction": ""
}
```

### 输出

```json
{
  "backend_ready": true,
  "backend_files_changed": ["backend/app.py"],
  "backend_endpoints": ["/health", "/api/info", "/predict"],
  "llm_skipped": false
}
```

---

## 14. `frontend_setup` / `ui_beautify` / `site_code_review`

### frontend_setup 输出

```json
{
  "frontend_ready": true,
  "layout_version": "2.0",
  "files_changed": ["frontend/src/App.vue"]
}
```

### ui_beautify 输出

```json
{
  "ui_score": 80,
  "theme_applied": true,
  "files_changed": ["frontend/src/styles/theme.css"]
}
```

### site_code_review 输出

```json
{
  "review_gate": "green|yellow|red",
  "issues_fixed": ["backend/app.py"],
  "review_report_path": ".flowly/review/review_report.json"
}
```

---

## 15. 上下文传递约定（更新）

工作流 executor 合并上游 output 到 context 时：

| 键 | 来源 |
|----|------|
| `best_weight_path` | yolo_training |
| `model_path` | training / clip_* |
| `class_names` | 任意训练节点 |
| `index_dir` | clip_retrieval |
| `prebuilt_index_dir` | clip_retrieval（Desktop 预构建） |
| `profile` | project_profiler |
| `site_id` / `generated_site_id` | website_generator |
| `website_output_dir` | website_generator（建站专用子目录，避免与训练 output_dir 冲突） |
| `qa_gate` | site_qa |
| `preview_url` | site_preview |
| `runtime_manifest` | environment_provision |
