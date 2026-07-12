# 状态机

> 站点生命周期、QA 门禁、Agent 改码闭环  
> 版本：1.0（2026-06-12）

---

## 1. GeneratedSite 平台态（MySQL）

```mermaid
stateDiagram-v2
  [*] --> generating: website_generator 创建
  generating --> completed: 生成成功
  generating --> failed: 生成失败
  completed --> qa_pending: site_qa 开始
  qa_pending --> qa_passed: gate=green
  qa_pending --> qa_warning: gate=yellow
  qa_pending --> qa_failed: gate=red
  qa_passed --> preview_ready: site_preview OK
  qa_warning --> preview_ready: research Profile
  qa_warning --> preview_blocked: default Profile 可选策略
  qa_failed --> preview_blocked
  preview_ready --> iterating: project_agent 改码
  iterating --> qa_pending: 强制重跑 QA
  preview_ready --> published: 用户确认发布
```

### 字段建议

| 字段 | 值 |
|------|-----|
| `status` | generating, completed, failed, iterating |
| `qa_gate` | green, yellow, red, null |
| `preview_status` | live, blocked, stale |

---

## 2. QA 层内状态（单次 site_qa 执行）

```mermaid
stateDiagram-v2
  [*] --> L1
  L1 --> L1_fail: 结构失败
  L1 --> L2: pass
  L1_fail --> [*]: gate=red
  L2 --> L2_fail: API 失败
  L2 --> L3: pass
  L2_fail --> [*]: gate=red
  L3 --> L3_fail: Playwright 失败
  L3 --> L4: pass或skip
  L3_fail --> [*]: gate=red
  L4 --> green: 指标≥绿线
  L4 --> yellow: 指标在黄区
  L4 --> red: 指标<红线或L4 fail
  green --> [*]
  yellow --> [*]
  red --> [*]
```

**Skip 规则**：

- 无 Playwright：L3=skip，gate 最高 yellow（若 L4 通过）
- 无 validationSet：L4=skip，gate 由 L1–L3 决定，报告须注明

---

## 3. Project Agent 改码闭环（M3）

```mermaid
sequenceDiagram
  participant U as 用户
  participant PA as project_agent
  participant FS as output_dir 文件
  participant QA as site_qa
  participant PV as site_preview

  U->>PA: 修改需求
  PA->>FS: write_file (白名单)
  PA->>QA: 强制触发
  alt gate=red
    QA-->>PA: 报告摘要
    PA-->>U: 失败说明 + 建议
  else gate=green或yellow
    QA->>PV: refresh
    PV-->>U: 新 preview_url
  end
```

---

## 4. Desktop Runtime 进程态

| 状态 | 含义 |
|------|------|
| `idle` | 未启动 |
| `starting` | 子进程拉起中 |
| `live` | 端口监听 |
| `unhealthy` | 健康检查失败 |
| `stopped` | 用户或 QA 结束 |

`environment_provision` 只负责 manifest；`site_qa` / `site_preview` 调用 runtime 起停。

---

## 5. 工作流模板边（推荐）

```
dataset_upload → yolo_training → project_profiler → website_generator
  → environment_provision → site_qa → site_preview → project_agent
```

`project_agent` 执行后 **虚线回边** 至 `site_qa`（实现可以是 runner 内部调用，不必画物理边）。

---

## 6. 与 Profile 的交叉

| qaProfile | gate=yellow | preview | publish |
|-----------|-------------|---------|---------|
| default | 允许 preview 带 Banner 或阻断（**M1 默认：允许 preview + 强 Banner**） | 可选 | 禁止 |
| research | 允许 | 允许 | 禁止直至 green |

**M1 实现默认**：default + yellow → preview 可开，UI 显示「指标未达生产标准」Banner；red → 阻断。
