# CLIP 检索站规格

> 产品形态：**演示站为主 + API/导出 Tab 为辅**  
> 版本：1.0（2026-06-12）

---

## 1. 技术栈（固定）

| 层 | 选型 |
|----|------|
| 前端 | Vue 3 + Vite + Element Plus |
| 后端 | Flask |
| 索引 | FAISS 或 numpy + 本地文件（由 `clip_retrieval` 节点产出） |
| 数据库 | SQLite（推理/搜索历史，M1 schema） |
| 推理 | CLIP encoder + 索引检索 |

---

## 2. 页面结构（四 Tab）

### Tab1 — 文本搜图

- 输入框 + 搜索按钮  
- 结果：Top-K 网格（K 默认 12，config 可调）  
- 每项：缩略图、相似度 0–100%、原 metadata  caption（若有）  
- 空态：提示索引规模与示例 query  

### Tab2 — 以图搜图

- 拖拽/点击上传  
- 可选：从 Tab3 图库点选作为 query  
- 结果布局同 Tab1  

### Tab3 — 图库浏览

- 分页网格（每页 24）  
- 搜索框过滤 filename / caption  
- 显示索引总数、构建时间、模型名  

### Tab4 — API & 导出

- OpenAPI 摘要（Markdown 渲染）  
- 端点列表：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/search/text` | body: `{ "query": "...", "top_k": 12 }` |
| POST | `/search/image` | multipart image + `top_k` |
| GET | `/gallery` | 分页 `?page=1&page_size=24` |
| GET | `/stats` | 索引规模、模型、metrics |

- 导出按钮：打包 `index/` + `metadata.json` + `README.txt`  
- cURL 示例（中文注释）  

### 侧栏指标（全局）

- 上次 QA：R@1 / R@5、gate 颜色  
- 索引向量数、CLIP 模型名  
- 链接 Flowly 项目页 `/projects/{id}`  

---

## 3. 后端 API 契约

### POST `/search/text`

**Request**
```json
{ "query": "一只橘猫", "top_k": 12 }
```

**Response**
```json
{
  "results": [
    {
      "id": "img_001",
      "score": 0.892,
      "image_url": "/media/img_001.jpg",
      "caption": "orange cat on sofa"
    }
  ],
  "latency_ms": 45
}
```

### POST `/search/image`

`multipart/form-data`: `file`, `top_k`

**Response** 结构同 `/search/text`

---

## 4. 生成目录结构

```text
{output_dir}/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── db/
│   │   ├── schema.sql
│   │   └── app.db          # SQLite，运行时生成
│   └── index/              #  symlink 或 copy 自 clip_retrieval 输出
│       ├── vectors.npy
│       └── metadata.json
├── frontend/
│   ├── src/
│   │   ├── App.vue         # Tab 容器
│   │   ├── views/
│   │   │   ├── TextSearch.vue
│   │   │   ├── ImageSearch.vue
│   │   │   ├── Gallery.vue
│   │   │   └── ApiDocs.vue
│   │   └── components/ResultGrid.vue
│   └── package.json
└── .flowly/
    └── qa/                 # QA 报告与截图
```

---

## 5. QA L3 Playwright 主路径（M4）

1. 打开首页 → 默认 Tab1  
2. 输入示例 query → 等待结果 grid ≥1  
3. 切换 Tab2 → 上传 fixture 图 → 结果 grid ≥1  
4. Tab4 → 可见 `/search/text` 文档标题  

L4：使用 hold-out query 集算 R@5，阈值见 [`qa-threshold-matrix.md`](qa-threshold-matrix.md)

---

## 6. 与检测站差异

| 项 | 检测站 | 检索站 |
|----|--------|--------|
| 主交互 | 上传→画框 | 文本/以图搜索 |
| 主 API | `/predict` | `/search/*` |
| 模型产物 | `.pt` | index + encoder |
| Vue 页面 | 单页 upload | 四 Tab |

**禁止**复用 `DetectionGenerator` 的前端 Vue 单页作为检索 UI。

---

## 7. Profiler 推荐（M2）

当 `website_type=clip_retrieval` 且类名/样本含「商品」「人脸」等关键词时，profiler 输出：

- `scenario`: 电商图搜 / 相册检索 / 文献配图检索  
- `copy_hints`: 示例 query 列表  
- `ui_tone`: gallery_minimal | commerce | research  

---

## 8. 工作流模板 `clip-retrieval-project`

```
dataset_upload(format=image_text_pairs)
  → clip_retrieval
  → project_profiler
  → website_generator(websiteType=clip_retrieval)
  → environment_provision
  → site_qa(websiteType=clip_retrieval)
  → site_preview
  → project_agent
```
