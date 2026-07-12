# Phase B — 视觉统一（Panel + Jazzmin）

> 状态：未开始  
> 预估：1–2 天 | 优先级：**P0**  
> 最后更新：2026-06-12

---

## 一、目标（做完什么算成功）

从欢迎页 → Tab Panel → 侧栏 Model 列表/编辑/保存，**全程像同一套产品设计**，无「进侧栏就换皮」的断层。

---

## 二、背景与问题

当前存在 **双轨视觉**：

| 轨道 | 样式来源 | 页面 |
|------|----------|------|
| Flowly | `f-*` 类 + `flowly_shell.css` + `flowly_base` 内联 CSS | 7 个 Panel + 欢迎页 |
| Jazzmin | `custom_admin.css` + AdminLTE | Model changelist / changeform |

此外：

- `:root` token 在 `flowly_base.html` 与 `custom_admin.css` 重复定义
- `flowly_base.html` 内联 CSS 约 600 行，难维护
- 登录页与登录后 Tab chrome 尚未完全统一

---

## 三、任务清单

### B1 — 抽取 `flowly_tokens.css`

- [ ] **B1.1** 新建 [`Backend/admin_static/admin/css/flowly_tokens.css`](../../Backend/admin_static/admin/css/flowly_tokens.css)
- [ ] **B1.2** 合并 `:root` 变量（accent、navy、radius、shadow、semantic colors）
- [ ] **B1.3** 在以下文件 `@import` 或 `<link>` 引用 tokens（顺序：tokens → components → shell → custom）
  - `flowly_base.html`（extrahead）
  - `custom_admin.css`（文件顶部 `@import url('flowly_tokens.css')` 或 Jazzmin 增加一条 custom_css）
  - `flowly_shell.css`（改用 `var(--f-accent)` 等统一命名）

**完成标准**：

- 修改主色只需改 **一处** tokens 文件
- 无冲突的重复 `:root` 块

**建议 token 命名**：

```css
:root {
  --f-accent: #1d4ed8;
  --f-accent-hover: #1e40af;
  --f-surface: #fefefe;
  --f-bg: #f0f6fc;
  --f-text: #0f172a;
  --f-muted: #64748b;
  --f-border: rgba(15, 40, 71, 0.1);
  --f-radius-sm: 8px;
  --f-radius-lg: 12px;
  /* ... */
}
```

---

### B2 — 抽离 `flowly_components.css`

- [ ] **B2.1** 新建 `flowly_components.css`，从 `flowly_base.html` 迁出：
  - `.f-btn*`、`.f-input`、`.f-select`、`.f-toggle`
  - `.f-card`、`.f-stat`、`.f-table*`、`.f-panel-body`
  - `.f-feature-item`、`.f-modal*`、`.f-pagination`、`.f-empty`
  - toast / skeleton / loading bar（若仍内联）
- [ ] **B2.2** `flowly_base.html` 内联 `<style>` 减少 **70%+**
- [ ] **B2.3** 保留各 Panel `extra_js` 块中的 **页面特有** 样式（如 dashboard 图表布局）

**完成标准**：

- `flowly_base.html` extrastyle 仅保留极少数页面级 override（若有）
- 组件样式单文件可 grep 维护

---

### B3 — Jazzmin 列表/表单/详情对齐

- [ ] **B3.1** 对照 [`references/design-system-map.md`](references/design-system-map.md) 逐项统一
- [ ] **B3.2** `.form-control` 与 `.f-input` 同高（padding ~11px）、同 border-radius、同 focus 环
- [ ] **B3.3** `.table` 与 `.f-table` 表头字重、间距、hover 一致
- [ ] **B3.4** `.card` 圆角 12px、边框色与 `--f-border` 一致
- [ ] **B3.5** `.submit-row` 背景 `#f8fafc`，主按钮使用 `--f-accent`
- [ ] **B3.6** `.object-tools a` 与 `.f-btn-primary` 视觉一致

**完成标准**：

- 打开 `/admin/workflows/workflow/` 与 `/admin/flowly/` 并排对比，圆角/主色/字体无违和

---

### B4 — 登录页纳入品牌体系

- [ ] **B4.1** Tab chrome 条同色：`#0a1628 → #1d4ed8` 渐变高度 3px 装饰（可选）
- [ ] **B4.2** 登录卡片圆角、阴影与 Panel 卡片一致（12–16px）
- [ ] **B4.3** Logo 使用 `{% static 'admin/img/logo.png' %}`（与用户端一致）
- [ ] **B4.4**（与 D4 联动）站点标题读配置或 context `site_name`

**完成标准**：

- 登录 → 欢迎页过渡无「两个产品」感

---

### B5 — 原生页 content-header 样式

- [ ] **B5.1** 非 Flowly 页（无 `.flowly-shell`）保留 `.content-header`
- [ ] **B5.2** 样式对齐 `f-page-header`：白底、12px 圆角、标题字重 800
- [ ] **B5.3** 面包屑字号 0.82rem，链接色 `--f-accent`

**完成标准**：

- Model 列表页标题区与 Panel 页头视觉同级（高度/字号接近）

---

## 四、涉及文件清单

| 文件 | 操作 |
|------|------|
| `admin_static/admin/css/flowly_tokens.css` | 新建 |
| `admin_static/admin/css/flowly_components.css` | 新建 |
| `admin_static/admin/css/flowly_shell.css` | 改引用 token |
| `admin_static/admin/css/custom_admin.css` | 扩展 Jazzmin 对齐 |
| `templates/admin/flowly_base.html` | 删内联 CSS，加 link |
| `templates/admin/login.html` | 品牌对齐 |
| `config/settings.py` | 若需增加 custom_css 条目 |

---

## 五、依赖与阻塞

| 项 | 说明 |
|----|------|
| 建议 after A | 导航收敛后再统一 Jazzmin，避免改完链接又动布局 |
| 阻塞 C | 无；B 与 C 可部分并行 |

---

## 六、验收标准

- [ ] token 单文件，主色修改一处生效
- [ ] `flowly_base` 内联 CSS < 200 行
- [ ] 工作流 changelist + changeform 与 Panel 视觉一致
- [ ] 登录页与 Tab chrome 同色系的深蓝白

---

## 七、备注 / 决策记录

### 禁止项（Impeccable / 项目规范）

- 不用紫色主色
- 不用 gradient text（`background-clip: text`）
- 不用装饰性 glassmorphism 作为默认卡片样式
- 不用 >1px 的 `border-left` 色条做分类 accent

### 参考对照

详见 [`references/design-system-map.md`](references/design-system-map.md)
