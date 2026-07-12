# QA 阈值矩阵

> 依据行业常见 POC/上线口径 + Flowly 双 Profile  
> 版本：1.0（2026-06-12）  
> 样本量不足时 **不得给出 green**，最高 yellow。

---

## 1. 样本量规则

| 验证集规模 | 行为 |
|------------|------|
| ≥ 50 张/对/query | 正常判定 |
| 20–49 | 指标仅供参考，最高 yellow |
| < 20 | L4 skip，gate 由 L1–L3 决定 |

---

## 2. 目标检测（YOLO）— mAP@0.5

| 档位 | mAP50 | default Profile | research Profile |
|------|-------|-----------------|----------------|
| 绿 | ≥ **0.75** | 可发布 | 可发布 |
| 黄 | **0.50 – 0.75** | 可预览 + Banner；不可发布 | 可预览；不可发布 |
| 红 | **< 0.50** | 阻断 preview | 阻断 preview |

**参考**：自定义小数据集常见 0.5–0.8；工业大屏上线内部常要求 ≥0.85（作租户「严格模式」preset，后续可选）。

---

## 3. 图像分类 — Top-1 Accuracy

| 档位 | Accuracy | 说明 |
|------|----------|------|
| 绿 | ≥ **0.90** | |
| 黄 | **0.75 – 0.90** | 类数 >20 时改用 Macro-F1，绿 ≥0.85 |
| 红 | **< 0.75** | |

---

## 4. CLIP 检索 — Recall@K

| 档位 | R@5 | R@1（报告展示） |
|------|-----|-----------------|
| 绿 | ≥ **0.80** | 建议 ≥0.60 |
| 黄 | **0.60 – 0.80** | |
| 红 | **< 0.60** | |

图库 **>10k** 时：R@5 绿线可降至 **0.70**（须在报告中标注「大规模库」）。

---

## 5. 非指标硬门槛（全 Profile）

| 检查 | 失败则 |
|------|--------|
| L1 依赖/权重/SQLite | gate=red |
| L2 /health + 主 API | gate=red |
| L3 Playwright 主路径 | gate=red |

---

## 6. qaProfile 汇总

| Profile | 适用 | 发布 | 预览 |
|---------|------|------|------|
| `default` | 工作流默认、小白 | 仅 green | green/yellow；red 否 |
| `research` | 模板「学术研究」 | 仅 green | yellow 可；red 否 |

---

## 7. 报告字段（qa_report.json）

```json
{
  "gate": "yellow",
  "profile": "default",
  "website_type": "detection",
  "metrics": {
    "map50": 0.68,
    "validation_count": 80
  },
  "thresholds_used": {
    "green_map50": 0.75,
    "yellow_map50": 0.5
  },
  "layers": { "l1": "pass", "l2": "pass", "l3": "pass", "l4": "pass" },
  "summary_zh": "检测模型 mAP50 为 68%，处于可演示但未达上线标准。",
  "recommendations": [
    "增加低照度样本",
    "尝试 yolov8m 基础权重"
  ]
}
```

---

## 8. 节点 config 示例

```json
{
  "qaProfile": "default",
  "websiteType": "detection",
  "strictMode": false
}
```

`strictMode: true`（后续）：绿线 mAP50 提升至 0.85。
