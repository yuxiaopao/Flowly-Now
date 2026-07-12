# 设计系统对照表 — f-* 组件 ↔ Jazzmin / Bootstrap

> Phase B 实施时逐项对齐。  
> 最后更新：2026-06-12

---

## 一、CSS 变量（目标：统一到 flowly_tokens.css）

| Flowly token | 当前值 | Jazzmin / custom_admin 对应 |
|--------------|--------|----------------------------|
| `--f-accent` / `--accent` | `#1d4ed8` | `--flowly-blue-700`, `.btn-primary` |
| `--f-accent-hover` | `#1e40af` | `--flowly-accent-hover` |
| `--f-bg` | `#f0f6fc` | `body`, `.content-wrapper` |
| `--f-surface` | `#fefefe` | `.card`, `.f-page-header` |
| `--f-text` | `#0f172a` | `--text-primary` |
| `--f-muted` | `#64748b` | `--text-muted`, `.breadcrumb-item.active` |
| `--f-border` | `rgba(15,40,71,0.1)` | `.card border`, `.form-control border` |
| `--f-radius-sm` | `8px` | `.btn`, `.form-control` |
| `--f-radius-lg` | `12px` | `.card`, `.f-page-header` |

---

## 二、布局与壳层

| Flowly 类/元素 | 用途 | Jazzmin 对应 | 对齐要点 |
|----------------|------|--------------|----------|
| `.flowly-shell` | Panel 外层 | — | 仅 Flowly 页 |
| `.flowly-tab-bar` | Tab 栏 | — | sticky top |
| `.f-page-header` | 紧凑页头 | `.content-header` | 白底、h2 1.25rem/800 |
| `.flowly-content-wrap` | 内容 padding | `.content` | max-width 1440px |
| `.f-panel-body` | 面板主体 | `.card-body` | 圆角 16px → 建议统一 12px |

---

## 三、表单

| Flowly | Jazzmin / Django | 对齐属性 |
|--------|------------------|----------|
| `.f-input` | `.form-control` | padding 11px 16px; border 1.5px; radius 8px |
| `.f-input:focus` | `.form-control:focus` | border `#1d4ed8`; box-shadow `0 0 0 4px rgba(29,78,216,0.2)` |
| `.f-select` | `select.form-control` | 自定义下拉箭头 SVG |
| `.f-toggle` | — | 无直接对应；Admin 布尔字段仍用 checkbox |
| `.f-search` | `#searchbar` | Jazzmin 列表搜索框同样圆角 |

---

## 四、按钮

| Flowly | Jazzmin | 对齐属性 |
|--------|---------|----------|
| `.f-btn` | `.btn` | font-weight 600; radius 8px |
| `.f-btn-primary` | `.btn-primary` | 纯色 `#1d4ed8`，非渐变 |
| `.f-btn-outline` | `.btn-outline-primary` | border 1.5px accent |
| `.f-btn-ghost` | `.btn-secondary` / `.btn-default` | 浅底 hover |
| `.f-btn-sm` | `.btn-sm` | padding 7px 14px |
| `.f-btn-danger` | `.btn-danger` | 删除确认链 |

| Jazzmin 特有 | 说明 |
|--------------|------|
| `.object-tools a` | 列表页「增加」按钮 → 对齐 `f-btn-primary` |
| `.submit-row input[type=submit]` | 表单底栏保存 → 对齐 primary |

---

## 五、表格

| Flowly | Jazzmin | 对齐属性 |
|--------|---------|----------|
| `.f-table-wrap` | `.card` + table 容器 | 白底圆角 overflow hidden |
| `.f-table th` | `.table thead th` | 0.72rem uppercase; padding 13px 16px |
| `.f-table td` | `.table tbody td` | padding 12px 16px |
| `.f-table tbody tr:hover` | `.table tbody tr:hover td` | `rgba(29,78,216,0.02)` |
| `.badge-*` | Django admin 状态标签 | 圆角 pill |

---

## 六、卡片与统计

| Flowly | Jazzmin | 对齐要点 |
|--------|---------|----------|
| `.f-card` | `.card` | border + shadow-sm; hover 微抬升 |
| `.f-card-title` | `.card-header` | 小字 uppercase label |
| `.f-stat` | `.small-box`（若使用） | 顶条 3px 色条可保留 |
| `.f-stat-value` | — | **纯色数字**，禁止 gradient text |
| `.f-stat-label` | — | 0.72rem muted uppercase |

---

## 七、反馈与状态

| Flowly | Jazzmin | 说明 |
|--------|---------|------|
| `.toast` / `#toastPortal` | `.messages li` | custom_admin.js 已转 toast |
| `#flowly-loading-bar` | — | 顶栏 fixed 3px |
| `.sk` / skeleton | — | Panel API 加载 |
| `.f-empty` | `.empty-form` | 空列表文案 |
| `.f-health-dot.*` | — | 系统 Panel 专用 |

---

## 八、模态与分页

| Flowly | Jazzmin | 对齐 |
|--------|---------|------|
| `.f-modal-overlay` | Bootstrap modal | 圆角 xl; backdrop blur 轻量 |
| `.f-page-btn` | `.pagination .page-link` | 36px 方钮; active 蓝底 |

---

## 九、反模式对照（禁止迁移到 Jazzmin 页）

| 反模式 | Flowly 现状 | Jazzmin 页禁止 |
|--------|-------------|----------------|
| Gradient text | 已移除 f-stat-value 渐变 | 禁止引入 |
| border-left 3px accent | f-cat-header 已改全边框 | 禁止 |
| 装饰 glassmorphism | f-panel-body 已改实色 | 禁止默认卡片 blur |
| 紫色 #6366f1 | 已清除 | 禁止 |

---

## 十、实施检查命令

```bash
# 查找仍使用渐变文字的残留
rg "background-clip:\s*text" Backend/templates/admin Backend/admin_static

# 查找硬编码旧紫色
rg "6366f1|9b59b6" Backend/templates/admin Backend/admin_static
```

---

## 十一、相关文件

- Flowly 组件定义：[`flowly_base.html`](../../Backend/templates/admin/flowly_base.html)（待迁至 `flowly_components.css`）
- Shell：[`flowly_shell.css`](../../Backend/admin_static/admin/css/flowly_shell.css)
- Jazzmin：[`custom_admin.css`](../../Backend/admin_static/admin/css/custom_admin.css)
