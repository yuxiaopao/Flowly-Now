# M4 — CLIP 节点 + 多素材数据集

> **优先级**：P2（M1 完成后；M2/M3 可并行部分 UI）  
> **目标**：CLIP 分类与检索训练；图文数据集 format；检索演示站模板。  
> **状态**：**P0 已验收**（见 [`PROGRESS.md`](PROGRESS.md)）

---

## 一、范围

- `dataset_upload` 扩展 format
- 节点：`clip_classification`、`clip_retrieval`
- 生成器：`ClipRetrievalGenerator`（见 clip-retrieval-site-spec）
- 工作流模板：`clip-retrieval-project`

---

## 二、数据集 format

| format | 用途 | 目录结构示例 |
|--------|------|--------------|
| `yolo` | 检测（现有） | `images/` + `labels/` + `data.yaml` |
| `image_folder` | 以图搜图 | `images/*` + 可选 `metadata.json` |
| `image_text_pairs` | 检索/对齐 | `pairs.jsonl`：`{"image":"...", "text":"..."}` |
| `classification_folders` | 分类 | `train/class_a/*` |

### 任务

- [x] **M4.1** `DatasetUploadNode` + 后端校验各 format
- [x] **M4.2** `/datasets` 页说明各 format 适用节点
- [x] **M4.3** 标注页导出 `image_text_pairs`（可选）

---

## 三、`clip_classification`

- [x] **M4.4** runner：零样本 / fine-tune 两 mode
- [x] **M4.5** 输出：`model_path` + `class_names` + `metrics`
- [x] **M4.6** Wizard 步骤：数据 → 模式 → 类名 → 环境 → 输出
- [x] **M4.7** 建站 `framework=clip` 零样本 UI（`ClassificationGenerator`）

---

## 四、`clip_retrieval`

- [x] **M4.8** runner：构建 embedding 索引（BOW MVP / CLIP 向量）
- [x] **M4.9** 输出：`index_dir`, `metadata.json`, `metrics`: `R@1`, `R@5`, `R@10`
- [x] **M4.10** QA L4 使用 R@5 阈值（见 qa-threshold-matrix）
- [x] **M4.11** `ClipRetrievalGenerator` 四 Tab UI + API
- [x] **M4.12** 模板 `clip-retrieval-project`：upload → clip_retrieval → profiler → WG → M1 链

---

## 五、训练后端

- [x] **M4.13** `TrainingJob.training_kind`: `clip_cls` | `clip_ret`
- [x] **M4.14** Desktop 支持 CLIP 索引构建（`clipIndex:start` + GPU 可选）
- [x] **M4.15** WS 进度：索引进度 %

---

## 六、完成标准

1. 50 对图文 `pairs.jsonl` → 索引 → 检索站文本搜图 Top5 合理  
2. QA L3 覆盖两个 Tab 主路径  
3. 学者可导出 API Tab cURL + index 目录  

---

## 七、依赖

- M1 QA/Preview 链  
- M2 profiler/wizard（推荐，非硬依赖）  

详细检索站规格：[`references/clip-retrieval-site-spec.md`](references/clip-retrieval-site-spec.md)
